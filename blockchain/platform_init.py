"""
Platform Initialization for Bitcoin Cash CashTokens

Creates the master minting token for the Qubes platform (ONE-TIME SETUP).
From docs/10_Blockchain_Integration.md Section 7.8.1
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any

from utils.logging import get_logger

logger = get_logger(__name__)


class PlatformInitializer:
    """
    Initialize platform minting infrastructure (run ONCE)

    Creates a master minting token with unlimited minting capability.
    This token can mint unlimited child NFTs for Qubes.
    """

    @staticmethod
    def initialize_minting_token(network: str = "mainnet") -> Dict[str, Any]:
        """
        Create master minting token for Qubes platform

        This token can mint UNLIMITED child NFTs.
        From docs Section 7.8.1

        Args:
            network: "mainnet" or "chipnet" (BCH testnet)

        Returns:
            {
                "category_id": str,
                "genesis_txid": str,
                "platform_address": str,
                "network": str
            }
        """
        from bitcash import PrivateKey

        # Get platform's Bitcoin Cash private key from environment
        platform_wif = os.getenv("PLATFORM_BCH_MINTING_KEY")

        if not platform_wif:
            raise ValueError(
                "PLATFORM_BCH_MINTING_KEY environment variable not set.\n"
                "Generate a new BCH private key and set it in your .env file:\n"
                "  PLATFORM_BCH_MINTING_KEY=your_wif_key_here"
            )

        logger.info(
            "initializing_platform_minting_token",
            network=network
        )

        # bitcash uses "test" for chipnet, "main" for mainnet
        bitcash_network = "test" if network == "chipnet" else "main"

        key = PrivateKey(platform_wif, network=bitcash_network)

        # Platform metadata for the minting token
        metadata = {
            "platform": "Qubes Network",
            "purpose": "Master minting token for Qube NFTs",
            "version": "1.0",
            "created": "2025-10-04"
        }

        # Create 32-byte commitment from metadata
        commitment = hashlib.sha256(
            json.dumps(metadata, sort_keys=True).encode()
        ).digest()

        logger.debug(
            "minting_token_metadata_created",
            commitment=commitment.hex()[:16] + "..."
        )

        # Check if we have UTXOs to spend
        unspents = key.get_unspents()

        if not unspents:
            logger.error(
                "no_utxos_available",
                address=key.cashtoken_address,
                network=network
            )
            raise ValueError(
                f"No UTXOs available for address {key.cashtoken_address}.\n"
                f"Fund this address with at least 0.01 BCH ({network}) to create the minting token.\n"
                f"For mainnet: Send BCH to {key.cashtoken_address}\n"
                f"For chipnet testnet: Get free BCH from https://tbch.googol.cash/"
            )

        logger.info(
            "creating_genesis_transaction",
            utxos_available=len(unspents),
            total_satoshis=sum(u.amount for u in unspents)
        )

        # Create genesis transaction with 'minting' capability
        # For genesis tx, category_id must be empty string (will be set to this txid)
        # Full format: (address, amount, currency, category_id, nft_capability, nft_commitment, token_amount)
        # Use None for token_amount to indicate NFT-only (no fungible tokens)
        tx_outputs = [(
            key.cashtoken_address,  # Send to ourselves
            1000,                    # 1000 satoshis (minimum dust)
            "satoshi",               # Currency unit
            "",                      # Empty = genesis (category_id becomes this txid)
            "minting",               # UNLIMITED minting capability
            commitment,              # Platform metadata commitment (bytes)
            None                     # No fungible tokens (NFT-only)
        )]

        logger.info("broadcasting_genesis_transaction")

        # Broadcast transaction
        genesis_txid = key.send(tx_outputs)

        # Category ID is the genesis transaction ID
        category_id = genesis_txid

        logger.info(
            "minting_token_created",
            category_id=category_id,
            genesis_txid=genesis_txid,
            network=network
        )

        # Save configuration
        config = {
            "category_id": category_id,
            "genesis_txid": genesis_txid,
            "platform_address": key.cashtoken_address,
            "commitment": commitment.hex(),
            "network": network,
            "metadata": metadata
        }

        # Create data directory if it doesn't exist
        from utils.paths import get_app_data_dir
        data_dir = get_app_data_dir() / "platform"
        data_dir.mkdir(parents=True, exist_ok=True)

        config_path = data_dir / "minting_token.json"

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(
            "minting_token_config_saved",
            config_path=str(config_path)
        )

        print("\n" + "=" * 70)
        print("🎉 PLATFORM MINTING TOKEN CREATED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nCategory ID:    {category_id}")
        print(f"Genesis TX:     {genesis_txid}")
        print(f"Platform Addr:  {key.cashtoken_address}")
        print(f"Network:        {network}")
        print(f"\nTransaction Explorer:")
        print(f"  https://blockchair.com/bitcoin-cash/transaction/{genesis_txid}")
        print(f"\nConfiguration saved to: {config_path}")
        print("\n" + "=" * 70)
        print("⚠️  IMPORTANT: Keep your PLATFORM_BCH_MINTING_KEY secure!")
        print("   This key can mint unlimited Qube NFTs.")
        print("=" * 70 + "\n")

        return config


def _get_minting_token_path() -> Path:
    """Get the platform minting token config path."""
    from utils.paths import get_app_data_dir
    return get_app_data_dir() / "platform" / "minting_token.json"


def check_minting_token_exists() -> bool:
    """
    Check if platform minting token has been initialized

    Returns:
        True if minting token config exists
    """
    config_path = _get_minting_token_path()
    return config_path.exists()


def load_minting_token_config() -> Dict[str, Any]:
    """
    Load platform minting token configuration

    Returns:
        Minting token config dict

    Raises:
        FileNotFoundError: If minting token hasn't been initialized
    """
    config_path = _get_minting_token_path()

    if not config_path.exists():
        raise FileNotFoundError(
            "Platform minting token not initialized.\n"
            "Run: python -m blockchain.platform_init"
        )

    with open(config_path, 'r') as f:
        return json.load(f)


# CLI for initializing the platform
if __name__ == "__main__":
    import sys

    print("\n" + "=" * 70)
    print("QUBES PLATFORM INITIALIZATION")
    print("=" * 70)
    print("\nThis will create the master minting token for the Qubes platform.")
    print("This token can mint unlimited Qube NFTs.")
    print("\nYou only need to run this ONCE per network (mainnet/chipnet).")
    print("=" * 70 + "\n")

    # Check if already initialized
    if check_minting_token_exists():
        print("⚠️  Minting token already exists!")
        existing = load_minting_token_config()
        print(f"\nExisting Configuration:")
        print(f"  Category ID: {existing['category_id']}")
        print(f"  Network:     {existing['network']}")
        print(f"\nTo re-initialize, delete: data/platform/minting_token.json")
        sys.exit(1)

    # Get network from command line or default to mainnet
    network = sys.argv[1] if len(sys.argv) > 1 else "mainnet"

    if network not in ["mainnet", "chipnet"]:
        print("❌ Invalid network. Use 'mainnet' or 'chipnet'")
        sys.exit(1)

    print(f"Network: {network}")
    print("\nMake sure:")
    print("  1. PLATFORM_BCH_MINTING_KEY is set in your .env file")
    print(f"  2. The address has at least 0.01 BCH ({network})")

    if network == "chipnet":
        print("\n💡 Get free testnet BCH from: https://tbch.googol.cash/")

    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()

    try:
        config = PlatformInitializer.initialize_minting_token(network=network)
        print("\n✅ SUCCESS! Platform is ready to mint Qube NFTs.")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
