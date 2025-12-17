"""
Merkle Tree for Memory Chain Integrity
"""

import hashlib
from typing import List
from math import ceil, log2


def compute_merkle_root(block_hashes: List[str]) -> str:
    """
    Compute Merkle root from list of block hashes

    Args:
        block_hashes: List of block hash strings

    Returns:
        Merkle root hash (64-char hex string)
    """
    if not block_hashes:
        return "0" * 64

    if len(block_hashes) == 1:
        return block_hashes[0]

    # Build Merkle tree bottom-up
    current_level = block_hashes[:]

    while len(current_level) > 1:
        next_level = []

        # Process pairs
        for i in range(0, len(current_level), 2):
            left = current_level[i]

            # If odd number, duplicate last hash
            if i + 1 >= len(current_level):
                right = left
            else:
                right = current_level[i + 1]

            # Hash concatenation
            combined = left + right
            parent_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(parent_hash)

        current_level = next_level

    return current_level[0]


def verify_merkle_proof(
    block_hash: str,
    block_index: int,
    proof: List[tuple],
    merkle_root: str
) -> bool:
    """
    Verify Merkle proof for a block

    Args:
        block_hash: Hash of the block to verify
        block_index: Index of block in chain
        proof: List of (hash, is_left) tuples for proof path
        merkle_root: Expected Merkle root

    Returns:
        True if proof is valid
    """
    current_hash = block_hash

    for sibling_hash, is_left in proof:
        if is_left:
            combined = sibling_hash + current_hash
        else:
            combined = current_hash + sibling_hash

        current_hash = hashlib.sha256(combined.encode()).hexdigest()

    return current_hash == merkle_root
