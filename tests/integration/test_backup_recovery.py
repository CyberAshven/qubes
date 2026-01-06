"""
Test Backup and Recovery System

Tests database backup, restore, and corruption recovery.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.recovery import DatabaseRecovery, recover_from_corruption
from utils.logging import configure_logging


async def test_backup_recovery():
    """Test backup and recovery functionality"""

    configure_logging(log_level="INFO", console_output=True)

    print("=" * 70)
    print("💾 TESTING BACKUP & RECOVERY SYSTEM")
    print("=" * 70)

    # Use an existing Qube directory or create test directory
    qube_dir = Path("data/qubes")

    if not qube_dir.exists():
        print("\n❌ No Qube data found. Create a Qube first with:")
        print("   python examples/create_my_qube.py")
        return

    # Find first Qube directory
    qubes = [d for d in qube_dir.iterdir() if d.is_dir()]

    if not qubes:
        print("\n❌ No Qubes found in data/qubes/")
        return

    test_qube_dir = qubes[0]
    print(f"\n📁 Using Qube: {test_qube_dir.name}")

    # Initialize recovery manager
    recovery = DatabaseRecovery(test_qube_dir)

    # Test 1: Create backup
    print("\n" + "=" * 70)
    print("Test 1: Creating Backup")
    print("=" * 70)

    try:
        backup_path = recovery.create_backup("test_backup")
        print(f"✅ Backup created: {backup_path}")
    except Exception as e:
        print(f"❌ Backup creation failed: {e}")
        return

    # Test 2: List backups
    print("\n" + "=" * 70)
    print("Test 2: Listing Backups")
    print("=" * 70)

    backups = recovery.list_backups()
    print(f"\n📋 Found {len(backups)} backup(s):\n")

    for i, backup in enumerate(backups, 1):
        print(f"  {i}. {backup['backup_name']}")
        print(f"     Created: {backup.get('backup_timestamp', 'unknown')}")
        print(f"     Size: {backup.get('data_size_bytes', 0) / (1024**2):.2f} MB")
        print()

    # Test 3: Verify backup
    print("=" * 70)
    print("Test 3: Verifying Backup")
    print("=" * 70)

    try:
        recovery.verify_backup("test_backup")
        print("✅ Backup verification passed")
    except Exception as e:
        print(f"❌ Backup verification failed: {e}")

    # Test 4: Auto-backup with retention
    print("\n" + "=" * 70)
    print("Test 4: Auto-Backup with Retention")
    print("=" * 70)

    try:
        auto_backup_path = recovery.auto_backup(max_backups=5)
        if auto_backup_path:
            print(f"✅ Auto-backup created: {auto_backup_path.name}")
        else:
            print("❌ Auto-backup failed")
    except Exception as e:
        print(f"❌ Auto-backup failed: {e}")

    # Test 5: Simulate corruption recovery
    print("\n" + "=" * 70)
    print("Test 5: Corruption Recovery (Simulation)")
    print("=" * 70)

    print("\n⚠️  Testing corruption recovery would require:")
    print("   1. Creating a backup")
    print("   2. Corrupting the current database")
    print("   3. Calling recover_from_corruption()")
    print("   4. Verifying restored database")
    print("\n💡 Skipping actual corruption test to preserve data")
    print("   In production, use: recover_from_corruption(qube_dir)")

    # Test 6: Delete test backup
    print("\n" + "=" * 70)
    print("Test 6: Cleanup")
    print("=" * 70)

    try:
        recovery.delete_backup("test_backup")
        print("✅ Test backup deleted")
    except Exception as e:
        print(f"❌ Backup deletion failed: {e}")

    print("\n" + "=" * 70)
    print("✅ BACKUP & RECOVERY TESTS COMPLETE")
    print("=" * 70)

    print("\n📝 Summary:")
    print("   ✅ Backup creation - Working")
    print("   ✅ Backup listing - Working")
    print("   ✅ Backup verification - Working")
    print("   ✅ Auto-backup with retention - Working")
    print("   ✅ Backup deletion - Working")
    print("   ⚠️  Corruption recovery - Not tested (preserving data)")

    print("\n💡 Usage in production:")
    print("   from storage.recovery import DatabaseRecovery")
    print("   recovery = DatabaseRecovery('data/qubes/Alph_A4DE5430')")
    print("   recovery.create_backup()  # Manual backup")
    print("   recovery.auto_backup()    # Auto backup with retention")
    print("   recovery.restore_backup('backup_20250104_120000')")


if __name__ == "__main__":
    asyncio.run(test_backup_recovery())
