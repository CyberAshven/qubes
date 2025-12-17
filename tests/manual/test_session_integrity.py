"""
Test session anchoring data integrity issues

ISSUE 1: Re-anchoring after crash creates duplicate data
ISSUE 2: Race condition in session block creation (no lock)
"""

import json
from pathlib import Path

def test_duplicate_anchoring_scenario():
    """
    Simulate crash scenario:
    1. Anchor session blocks 5, 6, 7
    2. Crash before cleanup
    3. Recovery loads same session blocks
    4. Re-anchor creates duplicates as blocks 8, 9, 10
    """
    print("\n=== TEST 1: Duplicate Anchoring After Crash ===\n")

    # Simulate post-anchor state (before cleanup)
    # Chain has blocks 0-7
    # Session directory still has files for blocks that became 5, 6, 7

    chain_length = 8  # Blocks 0-7 exist
    session_blocks_remain = True  # Cleanup didn't run due to crash

    print(f"✅ Permanent chain: blocks 0-{chain_length - 1}")
    print(f"⚠️  Session files still exist (cleanup crashed)")
    print()

    # Recovery scenario
    print("RECOVERY PROCESS:")
    print("1. Load session blocks from files")
    print("2. User calls anchor_to_chain() again")
    print()

    # Re-anchoring logic (from session.py line 238)
    for i, session_block_number in enumerate([-1, -2, -3]):
        new_permanent_number = chain_length + i
        print(f"   Session block {session_block_number} → Permanent block {new_permanent_number}")

    print()
    print("RESULT:")
    print("❌ CRITICAL: Data from blocks 5, 6, 7 now duplicated as 8, 9, 10")
    print("❌ Chain contains duplicate information with different block numbers")
    print()

    return False  # Test demonstrates vulnerability


def test_session_block_race_condition():
    """
    Session block creation has no file lock:
    - Two processes could create blocks simultaneously
    - Could corrupt JSON during concurrent writes
    - Could create blocks with conflicting negative indexes
    """
    print("\n=== TEST 2: Session Block Creation Race Condition ===\n")

    print("CODE ANALYSIS:")
    print()
    print("session.py:118 - _save_session_block() called WITHOUT lock")
    print("session.py:664 - _save_session_block() uses open(file, 'w') with NO locking")
    print()

    print("SCENARIO:")
    print("1. Process A: Creates session block -1, starts writing JSON")
    print("2. Process B: Creates session block -1, starts writing JSON")
    print("3. Both write to same file simultaneously")
    print()

    print("POTENTIAL RESULTS:")
    print("❌ Corrupted JSON (incomplete/invalid)")
    print("❌ One process's data overwrites the other")
    print("❌ Inconsistent session state between processes")
    print()

    print("PROTECTED OPERATIONS (with qube_session_lock):")
    print("✅ anchor_to_chain() - line 226")
    print()

    print("UNPROTECTED OPERATIONS (no lock):")
    print("❌ create_block() / _save_session_block() - line 118")
    print()

    return False  # Test demonstrates vulnerability


def test_cleanup_atomicity():
    """
    Session cleanup is NOT atomic with anchoring:
    - Anchoring completes successfully
    - Cleanup fails or crashes
    - Session files remain on disk
    - Next recovery will re-anchor them
    """
    print("\n=== TEST 3: Non-Atomic Cleanup ===\n")

    print("CODE FLOW (session.py anchor_to_chain):")
    print()
    print("Line 226: Acquire qube_session_lock")
    print("Line 234-271: Convert and save all permanent blocks ✅")
    print("Line 342-349: Update chain state ✅")
    print("Line 349: End session (releases lock)")
    print("Line 353: Clear session_blocks list ✅")
    print("Line 355: cleanup() - DELETE session files")
    print()

    print("CRASH WINDOW:")
    print("If crash occurs between line 349 and 355:")
    print("  - Lock is released (other processes can proceed)")
    print("  - Permanent blocks are saved")
    print("  - Session files still exist on disk")
    print("  - No marker indicating 'already anchored'")
    print()

    print("RECOVERY BEHAVIOR:")
    print("❌ recover_session() loads ALL JSON files from session directory")
    print("❌ No check if blocks were already anchored")
    print("❌ Re-anchoring creates duplicate data")
    print()

    return False


def check_actual_session_files():
    """Check if there are actual session files in test data"""
    print("\n=== CHECKING ACTUAL SESSION FILES ===\n")

    # Look for any Qube with session blocks
    data_dir = Path("data/users")
    if not data_dir.exists():
        print("No data directory found")
        return

    for user_dir in data_dir.iterdir():
        if not user_dir.is_dir():
            continue

        qubes_dir = user_dir / "qubes"
        if not qubes_dir.exists():
            continue

        for qube_dir in qubes_dir.iterdir():
            if not qube_dir.is_dir():
                continue

            session_dir = qube_dir / "blocks" / "session"
            if session_dir.exists():
                session_files = list(session_dir.glob("*.json"))
                if session_files:
                    print(f"Qube: {qube_dir.name}")
                    print(f"Session files: {len(session_files)}")
                    for file in session_files[:5]:  # Show first 5
                        print(f"  - {file.name}")
                    if len(session_files) > 5:
                        print(f"  ... and {len(session_files) - 5} more")
                    print()


if __name__ == "__main__":
    print("=" * 70)
    print("SESSION ANCHORING DATA INTEGRITY ANALYSIS")
    print("=" * 70)

    # Run theoretical tests
    test_duplicate_anchoring_scenario()
    test_session_block_race_condition()
    test_cleanup_atomicity()

    # Check actual files
    check_actual_session_files()

    print("\n" + "=" * 70)
    print("SUMMARY OF ISSUES FOUND")
    print("=" * 70)
    print()
    print("1. CRITICAL: Duplicate data after crash during cleanup")
    print("   Location: core/session.py:355 (cleanup not atomic)")
    print("   Impact: Re-anchoring creates duplicate blocks with new numbers")
    print()
    print("2. HIGH: Race condition in session block creation")
    print("   Location: core/session.py:118 (_save_session_block has no lock)")
    print("   Impact: Concurrent writes could corrupt JSON or create conflicts")
    print()
    print("3. MEDIUM: No 'already anchored' marker for session blocks")
    print("   Location: core/session.py:822 (recover_session)")
    print("   Impact: Cannot distinguish anchored vs unanchored session blocks")
    print()
