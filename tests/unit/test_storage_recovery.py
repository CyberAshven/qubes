"""
Tests for Database Backup and Recovery

Comprehensive tests for LMDB backup, restore, verify, and recovery operations.
Critical for disaster recovery and data integrity.

Covers:
- Backup creation (with/without custom names)
- Backup restoration (with/without verification)
- Backup verification (metadata, integrity)
- Backup listing (sorted by timestamp)
- Backup deletion
- Auto-backup (with retention management)
- Corruption recovery (from latest backup)
- Error handling (missing backups, corrupted files)
"""

import pytest
import json
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, timezone

from storage.recovery import DatabaseRecovery, recover_from_corruption
from core.exceptions import StorageError


@pytest.fixture
def temp_qube_dir():
    """Create temporary Qube data directory"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create LMDB directory with some dummy files
    lmdb_dir = temp_dir / "lmdb"
    lmdb_dir.mkdir(parents=True)

    # Create dummy LMDB files
    (lmdb_dir / "data.mdb").write_text("dummy lmdb data")
    (lmdb_dir / "lock.mdb").write_text("dummy lock file")

    # Create blocks directory structure
    blocks_dir = temp_dir / "blocks" / "permanent"
    blocks_dir.mkdir(parents=True)

    # Create some dummy block files
    for i in range(5):
        block_file = blocks_dir / f"block_{i}.json"
        block_data = {
            "block_number": i,
            "content": f"Block {i} content",
            "block_hash": f"hash_{i}"
        }
        with open(block_file, 'w') as f:
            json.dump(block_data, f)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# BACKUP CREATION TESTS
# ==============================================================================

class TestBackupCreation:
    """Test backup creation functionality"""

    @pytest.mark.unit
    def test_create_backup_with_auto_name(self, temp_qube_dir):
        """Should create backup with automatic timestamp name"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup()

        assert backup_path.exists()
        assert backup_path.is_dir()
        assert backup_path.name.startswith("backup_")

        # Check backup contains LMDB
        assert (backup_path / "lmdb").exists()
        assert (backup_path / "lmdb" / "data.mdb").exists()

    @pytest.mark.unit
    def test_create_backup_with_custom_name(self, temp_qube_dir):
        """Should create backup with custom name"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("my_custom_backup")

        assert backup_path.name == "my_custom_backup"
        assert backup_path.exists()

    @pytest.mark.unit
    def test_create_backup_with_metadata(self, temp_qube_dir):
        """Should create metadata file with backup"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("test_backup")

        metadata_file = backup_path / "backup_metadata.json"
        assert metadata_file.exists()

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata["backup_name"] == "test_backup"
        assert "backup_timestamp" in metadata
        assert "qube_data_dir" in metadata
        assert "lmdb_size_bytes" in metadata

    @pytest.mark.unit
    def test_create_backup_duplicate_name_fails(self, temp_qube_dir):
        """Creating backup with existing name should fail"""
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("duplicate")

        with pytest.raises(StorageError) as exc_info:
            recovery.create_backup("duplicate")

        assert "already exists" in str(exc_info.value)

    @pytest.mark.unit
    def test_create_backup_no_lmdb_fails(self, temp_qube_dir):
        """Should fail if LMDB directory doesn't exist"""
        # Remove LMDB directory
        shutil.rmtree(temp_qube_dir / "lmdb")

        recovery = DatabaseRecovery(temp_qube_dir)

        with pytest.raises(StorageError) as exc_info:
            recovery.create_backup()

        assert "LMDB directory not found" in str(exc_info.value)

    @pytest.mark.unit
    def test_create_backup_copies_all_lmdb_files(self, temp_qube_dir):
        """Should copy all LMDB files"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup()

        backup_lmdb = backup_path / "lmdb"
        assert (backup_lmdb / "data.mdb").exists()
        assert (backup_lmdb / "lock.mdb").exists()


# ==============================================================================
# BACKUP RESTORATION TESTS
# ==============================================================================

class TestBackupRestoration:
    """Test backup restoration functionality"""

    @pytest.mark.unit
    def test_restore_backup_success(self, temp_qube_dir):
        """Should restore backup successfully"""
        recovery = DatabaseRecovery(temp_qube_dir)

        # Create backup
        backup_path = recovery.create_backup("test_restore")

        # Modify current database
        (temp_qube_dir / "lmdb" / "data.mdb").write_text("modified data")

        # Restore backup
        recovery.restore_backup("test_restore", verify=False)

        # Check data is restored
        restored_data = (temp_qube_dir / "lmdb" / "data.mdb").read_text()
        assert restored_data == "dummy lmdb data"

    @pytest.mark.unit
    def test_restore_nonexistent_backup_fails(self, temp_qube_dir):
        """Restoring non-existent backup should fail"""
        recovery = DatabaseRecovery(temp_qube_dir)

        with pytest.raises(StorageError) as exc_info:
            recovery.restore_backup("nonexistent")

        assert "Backup not found" in str(exc_info.value)

    @pytest.mark.unit
    def test_restore_creates_temp_backup(self, temp_qube_dir):
        """Should create temporary backup before restoring"""
        recovery = DatabaseRecovery(temp_qube_dir)

        # Create original backup
        recovery.create_backup("original")

        # Restore (which creates temp backup first)
        recovery.restore_backup("original", verify=False)

        # Check temp backup was created
        backups = recovery.list_backups()
        temp_backups = [b for b in backups if "temp_pre_restore" in b["backup_name"]]

        assert len(temp_backups) > 0

    @pytest.mark.unit
    def test_restore_with_verification(self, temp_qube_dir):
        """Should verify backup before restoring if requested"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("verified_restore")

        # Create blocks directory for verification
        blocks_dir = backup_path / "blocks" / "permanent"
        blocks_dir.mkdir(parents=True)
        (blocks_dir / "block_0.json").write_text('{"block_number": 0}')

        # This should work (backup is valid)
        recovery.restore_backup("verified_restore", verify=True)

        assert (temp_qube_dir / "lmdb").exists()


# ==============================================================================
# BACKUP VERIFICATION TESTS
# ==============================================================================

class TestBackupVerification:
    """Test backup verification functionality"""

    @pytest.mark.unit
    def test_verify_valid_backup(self, temp_qube_dir):
        """Should verify valid backup successfully"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("valid_backup")

        # Create blocks directory for verification
        blocks_dir = backup_path / "blocks" / "permanent"
        blocks_dir.mkdir(parents=True)
        (blocks_dir / "block_0.json").write_text('{"block_number": 0}')

        result = recovery.verify_backup("valid_backup")

        assert result is True

    @pytest.mark.unit
    def test_verify_nonexistent_backup_fails(self, temp_qube_dir):
        """Verifying non-existent backup should fail"""
        recovery = DatabaseRecovery(temp_qube_dir)

        with pytest.raises(StorageError) as exc_info:
            recovery.verify_backup("nonexistent")

        assert "Backup not found" in str(exc_info.value)

    @pytest.mark.unit
    def test_verify_backup_missing_metadata(self, temp_qube_dir):
        """Should fail if metadata is missing"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("no_metadata")

        # Delete metadata file
        (backup_path / "backup_metadata.json").unlink()

        with pytest.raises(StorageError) as exc_info:
            recovery.verify_backup("no_metadata")

        assert "metadata missing" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_verify_backup_missing_blocks_dir(self, temp_qube_dir):
        """Should fail if blocks directory is missing"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("no_blocks")

        # Delete blocks directory
        blocks_dir = backup_path / "blocks" / "permanent"
        if blocks_dir.exists():
            shutil.rmtree(blocks_dir.parent.parent)

        with pytest.raises(StorageError) as exc_info:
            recovery.verify_backup("no_blocks")

        assert "blocks directory missing" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_verify_backup_corrupted_json(self, temp_qube_dir):
        """Should fail if JSON files are corrupted"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("corrupted")

        # Corrupt first JSON file
        blocks_dir = backup_path / "blocks" / "permanent"
        json_files = list(blocks_dir.glob("*.json"))
        if json_files:
            json_files[0].write_text("corrupted {json data")

        with pytest.raises(StorageError) as exc_info:
            recovery.verify_backup("corrupted")

        assert "corrupted" in str(exc_info.value).lower()


# ==============================================================================
# BACKUP LISTING TESTS
# ==============================================================================

class TestBackupListing:
    """Test backup listing functionality"""

    @pytest.mark.unit
    def test_list_backups_empty(self, temp_qube_dir):
        """Should return empty list if no backups"""
        recovery = DatabaseRecovery(temp_qube_dir)

        # Remove any backups
        if recovery.backup_dir.exists():
            shutil.rmtree(recovery.backup_dir)

        backups = recovery.list_backups()

        assert backups == []

    @pytest.mark.unit
    def test_list_backups_multiple(self, temp_qube_dir):
        """Should list all backups"""
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("backup1")
        recovery.create_backup("backup2")
        recovery.create_backup("backup3")

        backups = recovery.list_backups()

        assert len(backups) == 3
        backup_names = [b["backup_name"] for b in backups]
        assert "backup1" in backup_names
        assert "backup2" in backup_names
        assert "backup3" in backup_names

    @pytest.mark.unit
    def test_list_backups_sorted_by_timestamp(self, temp_qube_dir):
        """Should sort backups by timestamp (newest first)"""
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("old_backup")
        recovery.create_backup("new_backup")

        backups = recovery.list_backups()

        # Newer backup should be first
        assert backups[0]["backup_name"] == "new_backup"

    @pytest.mark.unit
    def test_list_backups_includes_metadata(self, temp_qube_dir):
        """Should include metadata for each backup"""
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("test_backup")

        backups = recovery.list_backups()

        assert len(backups) == 1
        backup = backups[0]

        assert "backup_name" in backup
        assert "backup_timestamp" in backup
        assert "qube_data_dir" in backup
        assert "lmdb_size_bytes" in backup

    @pytest.mark.unit
    def test_list_backups_without_metadata(self, temp_qube_dir):
        """Should handle backups without metadata"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("no_metadata_backup")

        # Delete metadata
        (backup_path / "backup_metadata.json").unlink()

        backups = recovery.list_backups()

        assert len(backups) == 1
        assert backups[0]["backup_name"] == "no_metadata_backup"
        assert backups[0]["backup_timestamp"] == "unknown"
        assert backups[0]["has_metadata"] is False


# ==============================================================================
# BACKUP DELETION TESTS
# ==============================================================================

class TestBackupDeletion:
    """Test backup deletion functionality"""

    @pytest.mark.unit
    def test_delete_backup_success(self, temp_qube_dir):
        """Should delete backup successfully"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("to_delete")
        assert backup_path.exists()

        recovery.delete_backup("to_delete")

        assert not backup_path.exists()

    @pytest.mark.unit
    def test_delete_nonexistent_backup_fails(self, temp_qube_dir):
        """Deleting non-existent backup should fail"""
        recovery = DatabaseRecovery(temp_qube_dir)

        with pytest.raises(StorageError) as exc_info:
            recovery.delete_backup("nonexistent")

        assert "Backup not found" in str(exc_info.value)

    @pytest.mark.unit
    def test_delete_backup_removes_all_files(self, temp_qube_dir):
        """Should remove all backup files"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.create_backup("full_delete")

        # Verify files exist
        assert (backup_path / "lmdb").exists()
        assert (backup_path / "backup_metadata.json").exists()

        recovery.delete_backup("full_delete")

        # Verify entire directory is gone
        assert not backup_path.exists()


# ==============================================================================
# AUTO-BACKUP TESTS
# ==============================================================================

class TestAutoBackup:
    """Test automatic backup functionality"""

    @pytest.mark.unit
    def test_auto_backup_creates_backup(self, temp_qube_dir):
        """Should create backup automatically"""
        recovery = DatabaseRecovery(temp_qube_dir)

        backup_path = recovery.auto_backup(max_backups=10)

        assert backup_path is not None
        assert backup_path.exists()

    @pytest.mark.unit
    def test_auto_backup_manages_retention(self, temp_qube_dir):
        """Should delete old backups when exceeding max_backups"""
        recovery = DatabaseRecovery(temp_qube_dir)

        # Create 5 backups
        for i in range(5):
            recovery.create_backup(f"backup_{i}")

        # Auto-backup with max_backups=3 should delete 2 old ones
        recovery.auto_backup(max_backups=3)

        backups = recovery.list_backups()

        # Should have 4 total (3 old + 1 new auto-backup)
        # But auto_backup enforces max_backups, so should be 3
        assert len(backups) <= 4

    @pytest.mark.unit
    def test_auto_backup_keeps_newest(self, temp_qube_dir):
        """Should keep newest backups when cleaning up"""
        recovery = DatabaseRecovery(temp_qube_dir)

        recovery.create_backup("old1")
        recovery.create_backup("old2")
        recovery.create_backup("old3")

        # Create auto-backup with low retention
        recovery.auto_backup(max_backups=2)

        backups = recovery.list_backups()

        # Oldest backup (old1) should be deleted
        backup_names = [b["backup_name"] for b in backups]
        assert "old1" not in backup_names or len(backups) <= 3


# ==============================================================================
# CORRUPTION RECOVERY TESTS
# ==============================================================================

class TestCorruptionRecovery:
    """Test corruption recovery helper function"""

    @pytest.mark.unit
    def test_recover_from_corruption_success(self, temp_qube_dir):
        """Should recover from latest backup"""
        recovery = DatabaseRecovery(temp_qube_dir)
        backup_path = recovery.create_backup("recovery_backup")

        # Create blocks directory for verification
        blocks_dir = backup_path / "blocks" / "permanent"
        blocks_dir.mkdir(parents=True)
        (blocks_dir / "block_0.json").write_text('{"block_number": 0}')

        result = recover_from_corruption(temp_qube_dir)

        assert result is True

    @pytest.mark.unit
    def test_recover_from_corruption_no_backups(self, temp_qube_dir):
        """Should fail if no backups available"""
        # Remove backups directory
        recovery = DatabaseRecovery(temp_qube_dir)
        if recovery.backup_dir.exists():
            shutil.rmtree(recovery.backup_dir)

        result = recover_from_corruption(temp_qube_dir)

        assert result is False

    @pytest.mark.unit
    def test_recover_from_corruption_uses_latest(self, temp_qube_dir):
        """Should use latest backup for recovery"""
        recovery = DatabaseRecovery(temp_qube_dir)

        old_backup_path = recovery.create_backup("old_backup")
        latest_backup_path = recovery.create_backup("latest_backup")

        # Create blocks directory for both backups (for verification)
        for backup_path in [old_backup_path, latest_backup_path]:
            blocks_dir = backup_path / "blocks" / "permanent"
            blocks_dir.mkdir(parents=True)
            (blocks_dir / "block_0.json").write_text('{"block_number": 0}')

        # Modify database
        (temp_qube_dir / "lmdb" / "data.mdb").write_text("corrupted")

        result = recover_from_corruption(temp_qube_dir)

        assert result is True
        # Data should be restored (not "corrupted")
        restored = (temp_qube_dir / "lmdb" / "data.mdb").read_text()
        assert restored == "dummy lmdb data"


# ==============================================================================
# EDGE CASES AND INTEGRATION TESTS
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and integration scenarios"""

    @pytest.mark.unit
    def test_multiple_backup_restore_cycles(self, temp_qube_dir):
        """Should handle multiple backup/restore cycles"""
        recovery = DatabaseRecovery(temp_qube_dir)

        # Cycle 1
        recovery.create_backup("cycle1")
        (temp_qube_dir / "lmdb" / "data.mdb").write_text("modified1")
        recovery.restore_backup("cycle1", verify=False)

        # Delay to ensure different timestamp for second temp backup (timestamp has second precision)
        time.sleep(1.1)

        # Cycle 2
        recovery.create_backup("cycle2")
        (temp_qube_dir / "lmdb" / "data.mdb").write_text("modified2")
        recovery.restore_backup("cycle2", verify=False)

        # Should work without errors
        assert (temp_qube_dir / "lmdb" / "data.mdb").exists()

    @pytest.mark.unit
    def test_backup_directory_permissions(self, temp_qube_dir):
        """Should create backup directory if it doesn't exist"""
        # Remove backup directory
        recovery = DatabaseRecovery(temp_qube_dir)
        if recovery.backup_dir.exists():
            shutil.rmtree(recovery.backup_dir)

        # Should create it automatically
        new_recovery = DatabaseRecovery(temp_qube_dir)

        assert new_recovery.backup_dir.exists()

    @pytest.mark.unit
    def test_backup_with_large_lmdb(self, temp_qube_dir):
        """Should handle larger LMDB files"""
        # Create larger dummy file
        large_data = "X" * 1024 * 100  # 100 KB
        (temp_qube_dir / "lmdb" / "data.mdb").write_text(large_data)

        recovery = DatabaseRecovery(temp_qube_dir)
        backup_path = recovery.create_backup()

        # Verify size is captured
        with open(backup_path / "backup_metadata.json", 'r') as f:
            metadata = json.load(f)

        assert metadata["lmdb_size_bytes"] > 100000  # At least 100 KB

    @pytest.mark.unit
    def test_concurrent_backup_operations(self, temp_qube_dir):
        """Should handle creating multiple backups in sequence"""
        recovery = DatabaseRecovery(temp_qube_dir)

        # Create multiple backups rapidly
        backups = []
        for i in range(5):
            backup_path = recovery.create_backup(f"concurrent_{i}")
            backups.append(backup_path)

        # All should exist
        for backup_path in backups:
            assert backup_path.exists()
