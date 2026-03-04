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

# The official covenant P2SH32 address (set after deploy.ts runs)
# This is the address holding the minting token; all mints go through this contract
OFFICIAL_COVENANT_ADDRESS = "bitcoincash:rvksvp7vuk4ck0asr3ns9v52h8d9zsywm6psx89hm7zsuqzldu4v5n4h9kyj7"


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
