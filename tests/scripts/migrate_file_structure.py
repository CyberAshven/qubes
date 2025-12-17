"""
File Structure Migration Utility

Migrates existing Qubes from old structure to new user-based structure:

OLD:
  data/qubes/{name}_{qube_id}/
    ├── qube.json
    ├── chain_state.json
    ├── lmdb/
    └── sessions/

NEW:
  data/users/{user_name}/qubes/{name}_{qube_id}/
    ├── chain/
    │   ├── genesis.json
    │   └── chain_state.json
    ├── audio/
    ├── images/
    ├── blocks/
    │   └── session/
    └── lmdb/
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

def detect_old_qubes(old_base_dir: Path = Path("data/qubes")) -> List[Path]:
    """Find all Qube directories in old structure"""
    if not old_base_dir.exists():
        print(f"Old qubes directory not found: {old_base_dir}")
        return []

    qubes = []
    for qube_dir in old_base_dir.iterdir():
        if qube_dir.is_dir() and (qube_dir / "qube.json").exists():
            qubes.append(qube_dir)

    return qubes

def migrate_qube(old_qube_dir: Path, user_name: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Migrate a single Qube to new structure

    Args:
        old_qube_dir: Path to old Qube directory (e.g., data/qubes/Athena_A1B2C3D4/)
        user_name: Username to assign this Qube to
        dry_run: If True, only show what would be done

    Returns:
        Migration result dict
    """
    result = {
        "success": False,
        "old_path": str(old_qube_dir),
        "new_path": None,
        "actions": [],
        "errors": []
    }

    try:
        # Extract qube name and ID from directory name
        qube_dir_name = old_qube_dir.name  # e.g., "Athena_A1B2C3D4"

        # Read old qube.json
        old_qube_json = old_qube_dir / "qube.json"
        if not old_qube_json.exists():
            result["errors"].append("qube.json not found")
            return result

        with open(old_qube_json, 'r') as f:
            qube_data = json.load(f)

        # Create new directory structure
        new_base_dir = Path(f"data/users/{user_name}/qubes/{qube_dir_name}")
        result["new_path"] = str(new_base_dir)

        if dry_run:
            result["actions"].append(f"Would create: {new_base_dir}")
            result["actions"].append(f"Would create: {new_base_dir}/chain/")
            result["actions"].append(f"Would create: {new_base_dir}/audio/")
            result["actions"].append(f"Would create: {new_base_dir}/images/")
            result["actions"].append(f"Would create: {new_base_dir}/blocks/session/")
            result["success"] = True
            return result

        # Create directories
        new_base_dir.mkdir(parents=True, exist_ok=True)
        (new_base_dir / "chain").mkdir(exist_ok=True)
        (new_base_dir / "audio").mkdir(exist_ok=True)
        (new_base_dir / "images").mkdir(exist_ok=True)
        (new_base_dir / "blocks" / "session").mkdir(parents=True, exist_ok=True)

        result["actions"].append(f"Created directory structure at {new_base_dir}")

        # Migrate qube.json -> chain/genesis.json
        genesis_data = qube_data.get("genesis_block", qube_data)
        genesis_path = new_base_dir / "chain" / "genesis.json"
        with open(genesis_path, 'w') as f:
            json.dump(genesis_data, f, indent=2)
        result["actions"].append(f"Migrated qube.json -> chain/genesis.json")

        # Migrate chain_state.json -> chain/chain_state.json
        old_chain_state = old_qube_dir / "chain_state.json"
        if old_chain_state.exists():
            new_chain_state = new_base_dir / "chain" / "chain_state.json"
            shutil.copy2(old_chain_state, new_chain_state)
            result["actions"].append(f"Migrated chain_state.json -> chain/chain_state.json")

        # Migrate LMDB
        old_lmdb = old_qube_dir / "lmdb"
        if old_lmdb.exists():
            new_lmdb = new_base_dir / "lmdb"
            shutil.copytree(old_lmdb, new_lmdb, dirs_exist_ok=True)
            result["actions"].append(f"Migrated lmdb/ directory")

        # Migrate sessions -> blocks/session
        old_sessions = old_qube_dir / "sessions"
        if old_sessions.exists():
            new_sessions = new_base_dir / "blocks" / "session"
            for session_file in old_sessions.glob("*.json"):
                shutil.copy2(session_file, new_sessions / session_file.name)
            result["actions"].append(f"Migrated sessions/ -> blocks/session/")

        # Migrate any audio files
        old_audio = old_qube_dir / "audio"
        if old_audio.exists():
            new_audio = new_base_dir / "audio"
            for audio_file in old_audio.glob("*"):
                if audio_file.is_file():
                    shutil.copy2(audio_file, new_audio / audio_file.name)
            result["actions"].append(f"Migrated audio files")

        # Migrate shared_memory structure (if exists)
        old_shared_memory = old_qube_dir / "shared_memory"
        if old_shared_memory.exists():
            new_shared_memory = new_base_dir / "shared_memory"
            shutil.copytree(old_shared_memory, new_shared_memory, dirs_exist_ok=True)
            result["actions"].append(f"Migrated shared_memory/ directory")

        result["success"] = True

    except Exception as e:
        result["errors"].append(str(e))

    return result

def migrate_all_qubes(user_name: str, dry_run: bool = True):
    """
    Migrate all Qubes from old structure to new user-based structure

    Args:
        user_name: Username to assign all Qubes to
        dry_run: If True, only show what would be done
    """
    print(f"\n{'DRY RUN - ' if dry_run else ''}Migrating Qubes to new file structure")
    print(f"User: {user_name}")
    print("=" * 60)

    old_qubes = detect_old_qubes()

    if not old_qubes:
        print("No Qubes found in old structure (data/qubes/)")
        return

    print(f"\nFound {len(old_qubes)} Qube(s) to migrate:\n")

    results = []
    for old_qube_dir in old_qubes:
        print(f"\nMigrating: {old_qube_dir.name}")
        print("-" * 60)

        result = migrate_qube(old_qube_dir, user_name, dry_run=dry_run)
        results.append(result)

        if result["success"]:
            print(f"✅ Success")
            for action in result["actions"]:
                print(f"  • {action}")
        else:
            print(f"❌ Failed")
            for error in result["errors"]:
                print(f"  ⚠️  {error}")

    # Summary
    print("\n" + "=" * 60)
    print(f"\nMigration Summary:")
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no files were actually moved")
        print("Run with dry_run=False to perform the migration")
    else:
        print("\n✅ Migration complete!")
        print("\nOld Qubes remain in data/qubes/ - you can delete them after verifying the migration")


if __name__ == "__main__":
    import sys

    # Get user name from command line or use default
    user_name = sys.argv[1] if len(sys.argv) > 1 else "default_user"
    dry_run = "--execute" not in sys.argv

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     Qubes File Structure Migration Utility               ║
╚═══════════════════════════════════════════════════════════╝

This utility migrates Qubes from the old structure to the new
user-based structure with organized folders:

OLD:  data/qubes/{{name}}_{{qube_id}}/
NEW:  data/users/{{user_name}}/qubes/{{name}}_{{qube_id}}/
        ├── chain/
        │   ├── genesis.json (renamed from qube.json)
        │   └── chain_state.json
        ├── audio/
        ├── images/
        ├── blocks/
        │   └── session/
        └── lmdb/

Usage:
  python scripts/migrate_file_structure.py [user_name] [--execute]

  user_name:  Username to assign Qubes to (default: default_user)
  --execute:  Actually perform migration (without this, it's a dry run)

Examples:
  python scripts/migrate_file_structure.py                    # Dry run with default_user
  python scripts/migrate_file_structure.py myname             # Dry run with 'myname'
  python scripts/migrate_file_structure.py myname --execute   # Actually migrate
""")

    migrate_all_qubes(user_name, dry_run=dry_run)
