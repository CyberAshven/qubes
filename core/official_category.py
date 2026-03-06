"""
Official Qubes Category ID

The category ID is the immutable on-chain identifier for all official Qubes NFTs.
This value is hardcoded and cannot be configured or overridden.

If an agent does not have this category ID, it is not a Qube.

This functions as a consensus rule - like Bitcoin nodes rejecting invalid blocks,
the Qubes network rejects agents without the official category ID.
"""

# The official Qubes CashToken category ID (mainnet)
# This is the genesis txid of the platform minting token
# Created: 2025-10-20
OFFICIAL_QUBES_CATEGORY = "c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f"

# The official covenant P2SH32 address (v2 — migrated 2026-03-06)
# This is the address holding the minting token; all mints go through this contract
OFFICIAL_COVENANT_ADDRESS = "bitcoincash:rdlqc0y2ulzyp0ulk3t6gn56lzrxt2fq7s2j232vzghww6m8mtqr7h0rx97sy"

# Platform public key (compressed secp256k1) used to deploy the covenant contract
# HASH160(this key) is the constructor arg for the CashScript contract
OFFICIAL_PLATFORM_PUBLIC_KEY = "02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741"


def is_official_qube(category_id: str) -> bool:
    """
    Check if a category ID matches the official Qubes category.

    Args:
        category_id: The CashToken category ID to check

    Returns:
        True if official, False otherwise
    """
    if not category_id:
        return False
    return category_id.lower() == OFFICIAL_QUBES_CATEGORY.lower()


def validate_official_qube(category_id: str, context: str = "") -> None:
    """
    Validate that a category ID is official. Raises exception if not.

    Args:
        category_id: The CashToken category ID to validate
        context: Optional context for error message (e.g., "P2P handshake")

    Raises:
        ValueError: If category ID is not official
    """
    if not is_official_qube(category_id):
        ctx = f" during {context}" if context else ""
        category_preview = category_id[:16] + "..." if category_id else "None"
        raise ValueError(
            f"Invalid category ID{ctx}. "
            f"Category '{category_preview}' "
            f"is not the official Qubes category. This agent is not a Qube."
        )
