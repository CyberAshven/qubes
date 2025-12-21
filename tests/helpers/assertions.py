"""
Custom assertions for Qubes testing.

Provides domain-specific assertion helpers for common validation patterns.
"""

from typing import Any, Optional, Dict
import re
import json


def assert_valid_qube_id(qube_id: str, message: Optional[str] = None):
    """
    Assert that a string is a valid Qube ID.

    Valid format: 8 uppercase hex characters
    Example: A1B2C3D4

    Args:
        qube_id: String to validate
        message: Optional custom error message

    Raises:
        AssertionError: If qube_id is invalid
    """
    msg = message or f"Invalid Qube ID: {qube_id}"

    assert isinstance(qube_id, str), f"{msg} (not a string)"
    assert len(qube_id) == 8, f"{msg} (length must be 8, got {len(qube_id)})"
    assert qube_id.isupper(), f"{msg} (must be uppercase)"
    assert all(c in "0123456789ABCDEF" for c in qube_id), f"{msg} (invalid characters)"


def assert_valid_block_structure(block: Dict[str, Any]):
    """
    Assert that a dictionary has valid block structure.

    Checks for required fields: block_number, block_type, qube_id,
    timestamp, signature, previous_hash, content.

    Args:
        block: Block dictionary to validate

    Raises:
        AssertionError: If block structure is invalid
    """
    required_fields = [
        "block_number",
        "block_type",
        "qube_id",
        "timestamp",
        "signature",
        "previous_hash",
        "content"
    ]

    for field in required_fields:
        assert field in block, f"Block missing required field: {field}"

    # Validate types
    assert isinstance(block["block_number"], int), "block_number must be int"
    assert isinstance(block["timestamp"], int), "timestamp must be int (Unix timestamp)"
    assert isinstance(block["content"], dict), "content must be dict"


def assert_valid_signature(signature: str):
    """
    Assert that a string is a valid ECDSA signature (hex format).

    Args:
        signature: Signature string to validate

    Raises:
        AssertionError: If signature is invalid
    """
    assert isinstance(signature, str), "Signature must be string"
    assert len(signature) > 0, "Signature cannot be empty"
    # Signature is DER-encoded, so length varies (typically 140-144 chars in hex)
    assert len(signature) >= 128, f"Signature too short: {len(signature)} chars"
    assert all(c in "0123456789abcdef" for c in signature.lower()), "Invalid signature format"


def assert_valid_timestamp(timestamp: int, tolerance_seconds: int = 60):
    """
    Assert that timestamp is reasonable (within tolerance of current time).

    Args:
        timestamp: Unix timestamp to validate
        tolerance_seconds: Acceptable drift from current time (default 60s)

    Raises:
        AssertionError: If timestamp is unreasonable
    """
    import time

    current = int(time.time())
    diff = abs(current - timestamp)

    assert diff <= tolerance_seconds, \
        f"Timestamp drift too large: {diff}s (tolerance: {tolerance_seconds}s)"


def assert_blocks_linked(block1: Dict[str, Any], block2: Dict[str, Any]):
    """
    Assert that two blocks are correctly linked (block2 follows block1).

    Checks:
    - block2.previous_hash == block1.block_hash
    - block2.block_number == block1.block_number + 1

    Args:
        block1: First block
        block2: Second block (should follow block1)

    Raises:
        AssertionError: If blocks are not properly linked
    """
    assert block2["previous_hash"] == block1["block_hash"], \
        "Blocks not linked: previous_hash mismatch"

    assert block2["block_number"] == block1["block_number"] + 1, \
        f"Blocks not sequential: {block1['block_number']} -> {block2['block_number']}"


def assert_encrypted_data(data: str):
    """
    Assert that data appears to be encrypted (hex format, reasonable length).

    Encrypted data should be:
    - Hex string
    - Longer than original (due to IV + padding)
    - Not human-readable

    Args:
        data: Data to check

    Raises:
        AssertionError: If data doesn't appear encrypted
    """
    assert isinstance(data, str), "Encrypted data must be string"
    assert len(data) > 0, "Encrypted data cannot be empty"
    assert all(c in "0123456789abcdef" for c in data.lower()), \
        "Encrypted data must be hex format"
    assert len(data) >= 64, f"Encrypted data suspiciously short: {len(data)} chars"


def assert_json_serializable(obj: Any):
    """
    Assert that an object can be serialized to JSON.

    Args:
        obj: Object to check

    Raises:
        AssertionError: If object is not JSON serializable
    """
    try:
        json.dumps(obj)
    except (TypeError, ValueError) as e:
        raise AssertionError(f"Object not JSON serializable: {e}")


def assert_valid_merkle_root(merkle_root: str):
    """
    Assert that a string is a valid Merkle root (64-char hex SHA-256 hash).

    Args:
        merkle_root: Merkle root to validate

    Raises:
        AssertionError: If merkle root is invalid
    """
    assert isinstance(merkle_root, str), "Merkle root must be string"
    assert len(merkle_root) == 64, f"Merkle root must be 64 chars (SHA-256), got {len(merkle_root)}"
    assert all(c in "0123456789abcdef" for c in merkle_root.lower()), \
        "Merkle root must be hex format"


def assert_valid_ipfs_cid(cid: str):
    """
    Assert that a string is a valid IPFS CID.

    Supports CIDv0 (Qm...) and CIDv1 (b...) formats.

    Args:
        cid: IPFS CID to validate

    Raises:
        AssertionError: If CID is invalid
    """
    assert isinstance(cid, str), "IPFS CID must be string"
    assert len(cid) > 0, "IPFS CID cannot be empty"

    # CIDv0 starts with Qm, CIDv1 starts with b
    assert cid.startswith("Qm") or cid.startswith("b"), \
        f"Invalid IPFS CID format: must start with 'Qm' (v0) or 'b' (v1), got '{cid[:2]}'"

    if cid.startswith("Qm"):
        # CIDv0: base58, ~46 chars
        assert len(cid) >= 44, f"CIDv0 too short: {len(cid)} chars"
    else:
        # CIDv1: base32, variable length
        assert len(cid) >= 50, f"CIDv1 too short: {len(cid)} chars"


def assert_chain_integrity(blocks: list):
    """
    Assert that a list of blocks forms a valid chain.

    Checks:
    - Sequential block numbers
    - Proper linking (previous_hash references)
    - All blocks signed

    Args:
        blocks: List of block dictionaries

    Raises:
        AssertionError: If chain integrity is broken
    """
    if len(blocks) == 0:
        return

    # Check first block (genesis)
    assert blocks[0]["block_number"] == 0, "First block must be genesis (block_number=0)"

    # Check all blocks are properly linked
    for i in range(1, len(blocks)):
        assert_blocks_linked(blocks[i-1], blocks[i])

    # Check all blocks have signatures
    for block in blocks:
        assert "signature" in block, f"Block {block['block_number']} missing signature"
        assert block["signature"], f"Block {block['block_number']} has empty signature"


def assert_trust_score_valid(score: int):
    """
    Assert that a trust score is in valid range (0-100).

    Args:
        score: Trust score to validate

    Raises:
        AssertionError: If score is out of range
    """
    assert isinstance(score, int), f"Trust score must be int, got {type(score)}"
    assert 0 <= score <= 100, f"Trust score must be 0-100, got {score}"
