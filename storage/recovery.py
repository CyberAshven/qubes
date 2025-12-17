"""
Database Corruption Recovery

Handles backup and recovery of JSON-based block storage for disaster recovery.
From docs/22_DevOps_Guide.md Part II Section 2.6
"""

import os
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.exceptions import StorageError
from utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseRecovery:
    """Database backup and recovery manager"""

    def __init__(self, qube_data_dir: Path):
        """
        Initialize recovery manager

        Args:
            qube_data_dir: Path to Qube's data directory (e.g., data/qubes/Alph_A4DE5430)
        """
        self.qube_data_dir = Path(qube_data_dir)
        self.lmdb_dir = self.qube_data_dir / "lmdb"
        self.backup_dir = self.qube_data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("recovery_manager_initialized", qube_dir=str(qube_data_dir))

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """
        Create a backup of the LMDB database

        Args:
            backup_name: Optional custom backup name. If None, uses timestamp.

        Returns:
            Path to backup directory

        Raises:
            StorageError: If backup fails
        """
        try:
            # Generate backup name
            if backup_name is None:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"

            backup_path = self.backup_dir / backup_name

            # Check if backup already exists
            if backup_path.exists():
                raise StorageError(
                    f"Backup already exists: {backup_name}",
                    context={"backup_path": str(backup_path)}
                )

            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)

            # Use LMDB's built-in backup (hot backup while DB is open)
            if self.lmdb_dir.exists():
                logger.info("creating_lmdb_backup", backup_name=backup_name)

                # Copy LMDB files
                backup_lmdb = backup_path / "lmdb"
                shutil.copytree(self.lmdb_dir, backup_lmdb)

                # Create metadata file
                metadata = {
                    "backup_name": backup_name,
                    "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                    "qube_data_dir": str(self.qube_data_dir),
                    "lmdb_size_bytes": self._get_dir_size(self.lmdb_dir)
                }

                metadata_file = backup_path / "backup_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

                logger.info(
                    "backup_created",
                    backup_name=backup_name,
                    backup_path=str(backup_path),
                    size_mb=round(metadata["lmdb_size_bytes"] / (1024**2), 2)
                )

                return backup_path

            else:
                raise StorageError(
                    f"LMDB directory not found: {self.lmdb_dir}",
                    context={"lmdb_dir": str(self.lmdb_dir)}
                )

        except Exception as e:
            logger.error("backup_failed", backup_name=backup_name, exc_info=True)
            raise StorageError(
                f"Failed to create backup: {str(e)}",
                context={"backup_name": backup_name},
                cause=e
            )

    def restore_backup(self, backup_name: str, verify: bool = True) -> None:
        """
        Restore database from backup

        Args:
            backup_name: Name of backup to restore
            verify: If True, verify backup integrity before restoring

        Raises:
            StorageError: If restore fails
        """
        try:
            backup_path = self.backup_dir / backup_name

            if not backup_path.exists():
                raise StorageError(
                    f"Backup not found: {backup_name}",
                    context={"backup_path": str(backup_path)}
                )

            logger.info("restoring_backup", backup_name=backup_name)

            # Verify backup if requested
            if verify:
                self.verify_backup(backup_name)

            # Create temporary backup of current database
            if self.lmdb_dir.exists():
                temp_backup_name = f"temp_pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                temp_backup_path = self.backup_dir / temp_backup_name
                shutil.copytree(self.lmdb_dir, temp_backup_path / "lmdb")
                logger.info("temp_backup_created", temp_backup=temp_backup_name)

            # Remove current database
            if self.lmdb_dir.exists():
                shutil.rmtree(self.lmdb_dir)

            # Restore from backup
            backup_lmdb = backup_path / "lmdb"
            shutil.copytree(backup_lmdb, self.lmdb_dir)

            logger.info("backup_restored", backup_name=backup_name)

        except Exception as e:
            logger.error("restore_failed", backup_name=backup_name, exc_info=True)
            raise StorageError(
                f"Failed to restore backup: {str(e)}",
                context={"backup_name": backup_name},
                cause=e
            )

    def verify_backup(self, backup_name: str) -> bool:
        """
        Verify backup integrity

        Args:
            backup_name: Name of backup to verify

        Returns:
            True if backup is valid

        Raises:
            StorageError: If backup is corrupted or invalid
        """
        try:
            backup_path = self.backup_dir / backup_name

            if not backup_path.exists():
                raise StorageError(
                    f"Backup not found: {backup_name}",
                    context={"backup_path": str(backup_path)}
                )

            # Check metadata file
            metadata_file = backup_path / "backup_metadata.json"
            if not metadata_file.exists():
                raise StorageError(
                    f"Backup metadata missing: {backup_name}",
                    context={"metadata_file": str(metadata_file)}
                )

            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Check blocks directory
            backup_blocks = backup_path / "blocks" / "permanent"
            if not backup_blocks.exists():
                raise StorageError(
                    f"Backup blocks directory missing: {backup_name}",
                    context={"blocks_dir": str(backup_blocks)}
                )

            # Verify JSON files are readable
            try:
                json_files = list(backup_blocks.glob("*.json"))
                if not json_files:
                    raise ValueError("No JSON block files found")

                # Test read first block to verify format
                with open(json_files[0], 'r') as f:
                    json.load(f)
            except Exception as e:
                raise StorageError(
                    f"Backup blocks corrupted: {backup_name}",
                    context={"error": str(e)},
                    cause=e
                )

            logger.info("backup_verified", backup_name=backup_name)
            return True

        except Exception as e:
            logger.error("backup_verification_failed", backup_name=backup_name, exc_info=True)
            raise StorageError(
                f"Backup verification failed: {str(e)}",
                context={"backup_name": backup_name},
                cause=e
            )

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups

        Returns:
            List of backup metadata dicts
        """
        try:
            backups = []

            if not self.backup_dir.exists():
                return backups

            for backup_path in self.backup_dir.iterdir():
                if backup_path.is_dir():
                    metadata_file = backup_path / "backup_metadata.json"

                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            backups.append(metadata)
                    else:
                        # Backup without metadata
                        backups.append({
                            "backup_name": backup_path.name,
                            "backup_timestamp": "unknown",
                            "has_metadata": False
                        })

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get("backup_timestamp", ""), reverse=True)

            return backups

        except Exception as e:
            logger.error("list_backups_failed", exc_info=True)
            return []

    def delete_backup(self, backup_name: str) -> None:
        """
        Delete a backup

        Args:
            backup_name: Name of backup to delete

        Raises:
            StorageError: If deletion fails
        """
        try:
            backup_path = self.backup_dir / backup_name

            if not backup_path.exists():
                raise StorageError(
                    f"Backup not found: {backup_name}",
                    context={"backup_path": str(backup_path)}
                )

            shutil.rmtree(backup_path)

            logger.info("backup_deleted", backup_name=backup_name)

        except Exception as e:
            logger.error("backup_deletion_failed", backup_name=backup_name, exc_info=True)
            raise StorageError(
                f"Failed to delete backup: {str(e)}",
                context={"backup_name": backup_name},
                cause=e
            )

    def auto_backup(self, max_backups: int = 10) -> Optional[Path]:
        """
        Create automatic backup and manage backup retention

        Args:
            max_backups: Maximum number of backups to keep (oldest deleted first)

        Returns:
            Path to created backup, or None if failed
        """
        try:
            # Create backup
            backup_path = self.create_backup()

            # Clean up old backups
            backups = self.list_backups()

            if len(backups) > max_backups:
                # Delete oldest backups
                backups_to_delete = backups[max_backups:]

                for backup in backups_to_delete:
                    try:
                        self.delete_backup(backup["backup_name"])
                        logger.info("old_backup_deleted", backup_name=backup["backup_name"])
                    except Exception as e:
                        logger.error(
                            "old_backup_deletion_failed",
                            backup_name=backup["backup_name"],
                            error=str(e)
                        )

            return backup_path

        except Exception as e:
            logger.error("auto_backup_failed", exc_info=True)
            return None

    def _get_dir_size(self, directory: Path) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size


def recover_from_corruption(qube_data_dir: Path) -> bool:
    """
    Attempt to recover from database corruption

    Args:
        qube_data_dir: Path to Qube's data directory

    Returns:
        True if recovery successful, False otherwise
    """
    try:
        recovery = DatabaseRecovery(qube_data_dir)

        # List available backups
        backups = recovery.list_backups()

        if not backups:
            logger.error("no_backups_available", qube_dir=str(qube_data_dir))
            return False

        # Try to restore from most recent backup
        latest_backup = backups[0]
        backup_name = latest_backup["backup_name"]

        logger.info("attempting_recovery", backup_name=backup_name)

        # Restore backup
        recovery.restore_backup(backup_name, verify=True)

        logger.info("recovery_successful", backup_name=backup_name)
        return True

    except Exception as e:
        logger.error("recovery_failed", qube_dir=str(qube_data_dir), exc_info=True)
        return False
