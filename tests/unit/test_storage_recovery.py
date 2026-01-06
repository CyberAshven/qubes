"""
Tests for Database Backup and Recovery

Comprehensive tests for JSON block storage backup, restore, verify, and recovery operations.
"""

import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from storage.recovery import DatabaseRecovery
from core.exceptions import StorageError


@pytest.fixture
def temp_qube_dir():
    """Create temporary Qube data directory with JSON storage."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create blocks directory structure
    blocks_dir = temp_dir / "blocks" / "permanent"
    blocks_dir.mkdir(parents=True)

    # Create some dummy block files
    for i in range(3):
        block_file = blocks_dir / f"{i}_MESSAGE_{int(datetime.now(timezone.utc).timestamp())}.json"
        block_data = {
            "block_number": i,
            "content": {"message_body": f"Block {i} content"},
            "block_hash": f"hash_{i}"
        }
        with open(block_file, 'w') as f:
            json.dump(block_data, f)

    # Create chain metadata
    chain_dir = temp_dir / "chain"
    chain_dir.mkdir(parents=True)
    (chain_dir / "chain_state.json").write_text('{"chain_length": 3}')

    yield temp_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


class TestBackupCreation:
    """Test backup creation functionality."""

    @pytest.mark.unit
    def test_create_backup_with_auto_name(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup()

        assert backup_path.exists()
        assert backup_path.is_dir()
        assert backup_path.name.startswith("backup_")
        assert (backup_path / "blocks" / "permanent").exists()
        assert (backup_path / "chain").exists()

    @pytest.mark.unit
    def test_create_backup_with_custom_name(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("my_custom_backup")

        assert backup_path.name == "my_custom_backup"
        assert backup_path.exists()

    @pytest.mark.unit
    def test_create_backup_with_metadata(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("test_backup")
        metadata_file = backup_path / "backup_metadata.json"

        assert metadata_file.exists()

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata["backup_name"] == "test_backup"
        assert "backup_timestamp" in metadata
        assert "qube_data_dir" in metadata
        assert "data_size_bytes" in metadata
        assert "items" in metadata

    @pytest.mark.unit
    def test_create_backup_no_data_fails(self, temp_qube_dir):
        # Remove all data directories
        shutil.rmtree(temp_qube_dir / "blocks")
        shutil.rmtree(temp_qube_dir / "chain")

        recovery = DatabaseRecovery(temp_qube_dir)

        with pytest.raises(StorageError) as exc_info:
            recovery.create_backup()

        assert "No Qube data directories found" in str(exc_info.value)


class TestBackupRestoration:
    """Test backup restoration functionality."""

    @pytest.mark.unit
    def test_restore_backup_success(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("test_restore")

        # Modify current block content
        blocks_dir = temp_qube_dir / "blocks" / "permanent"
        block_file = next(blocks_dir.glob("0_*.json"))
        block_file.write_text('{"block_number": 0, "content": {"message_body": "modified"}}')

        recovery.restore_backup("test_restore", verify=False)

        restored_data = json.loads(block_file.read_text())
        assert restored_data["content"]["message_body"] == "Block 0 content"

    @pytest.mark.unit
    def test_restore_creates_temp_backup(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("original")
        recovery.restore_backup("original", verify=False)

        temp_backups = [
            d for d in (temp_qube_dir / "backups").iterdir()
            if d.is_dir() and "temp_pre_restore" in d.name
        ]
        assert temp_backups

    @pytest.mark.unit
    def test_restore_nonexistent_backup_fails(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        with pytest.raises(StorageError) as exc_info:
            recovery.restore_backup("nonexistent")

        assert "Backup not found" in str(exc_info.value)


class TestBackupVerification:
    """Test backup verification functionality."""

    @pytest.mark.unit
    def test_verify_backup_success(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("verified_backup")

        assert recovery.verify_backup("verified_backup") is True


class TestBackupManagement:
    """Test backup listing, deletion, and retention."""

    @pytest.mark.unit
    def test_list_backups(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("backup_a")
        recovery.create_backup("backup_b")

        backups = recovery.list_backups()
        backup_names = [b["backup_name"] for b in backups]

        assert "backup_a" in backup_names
        assert "backup_b" in backup_names

    @pytest.mark.unit
    def test_delete_backup(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("to_delete")
        recovery.delete_backup("to_delete")

        backups = recovery.list_backups()
        assert all(b["backup_name"] != "to_delete" for b in backups)

    @pytest.mark.unit
    def test_auto_backup_retention(self, temp_qube_dir):
        recovery = DatabaseRecovery(temp_qube_dir)

        for i in range(6):
            recovery.create_backup(f"backup_{i}")

        recovery.auto_backup(max_backups=3)

        backups = recovery.list_backups()
        assert len(backups) <= 3
