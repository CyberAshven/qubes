"""
Optimized NFT Minter

Mints Qube NFTs using pre-existing platform minting token (SINGLE TRANSACTION).
From docs/10_Blockchain_Integration.md Section 7.8.2
"""

import os
import json
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path

from blockchain.platform_init import load_minting_token_config
from crypto.keys import derive_commitment
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class OptimizedNFTMinter:
    """
    Mint Qubes using pre-existing platform minting token

    Uses the optimized single-transaction approach:
    - Platform controls the minting token
    - Each Qube NFT is created in ONE transaction
    - NFT is sent directly to user's address
    """

    def __init__(self, network: str = "mainnet"):
        """
        Initialize NFT minter

        Args:
            network: "mainnet" or "chipnet"
        """
        from bitcash import PrivateKey

        self.network = network

        # Get platform private key from environment
        platform_wif = os.getenv("PLATFORM_BCH_MINTING_KEY")

        if not platform_wif:
            raise ValueError(
                "PLATFORM_BCH_MINTING_KEY environment variable not set"
            )

        # bitcash uses "main" for mainnet, "test" for chipnet
        bitcash_network = "test" if network == "chipnet" else "main"
        self.platform_key = PrivateKey(platform_wif, network=bitcash_network)

        # Load minting token configuration
        self.minting_config = load_minting_token_config()
        self.category_id = self.minting_config["category_id"]

        # Sanity check: verify minting config uses official Qubes category
        from core.official_category import is_official_qube
        if not is_official_qube(self.category_id):
            logger.critical(
                "minter_category_mismatch",
                loaded_category=self.category_id[:16] + "...",
                error="Minting token config does not match official Qubes category"
            )
            raise ValueError(
                "CRITICAL: Minting token configuration does not match official Qubes category. "
                "Check data/platform/minting_token.json - possible misconfiguration or compromise."
            )

        logger.info(
            "nft_minter_initialized",
            category_id=self.category_id[:16] + "...",
            network=network
        )

    async def mint_qube_nft(
        self,
        qube,
        recipient_address: str,
        ipfs_cid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mint Qube NFT in SINGLE transaction
        From docs Section 7.8.2

        Process:
        1. Find minting token UTXO
        2. Create tx with 2 outputs:
           - Immutable NFT → user
           - Minting token → platform (change)
        3. Broadcast

        Args:
            qube: Qube instance with genesis block
            recipient_address: Bitcoin Cash address (cashaddr format)
            ipfs_cid: Optional IPFS CID of encrypted backup (for Model 3)

        Returns:
            {
                "category_id": str,
                "mint_txid": str,
                "commitment": str,
                "ipfs_cid": str (if provided),
                "recipient_address": str,
                "network": str
            }
        """
        try:
            logger.info(
                "minting_qube_nft",
                qube_id=qube.qube_id,
                recipient=recipient_address
            )

            # Step 1: Create commitment from Qube metadata
            commitment = self._create_commitment(qube, ipfs_cid)

            logger.debug(
                "commitment_created",
                qube_id=qube.qube_id,
                commitment=commitment.hex()[:16] + "..."
            )

            # Step 2: Find minting token UTXO
            minting_utxo = await self._find_minting_token_utxo()

            if not minting_utxo:
                raise ValueError(
                    f"Minting token UTXO not found.\n"
                    f"Expected category: {self.category_id}\n"
                    f"Platform address: {self.platform_key.cashtoken_address}"
                )

            logger.debug(
                "minting_token_utxo_found",
                txid=minting_utxo.txid if hasattr(minting_utxo, 'txid') else "unknown"
            )

            # Step 3: Create transaction output
            # ONLY specify the user's immutable NFT
            # Bitcash will automatically return the minting token as change
            tx_outputs = [
                # Immutable NFT → user (no capability = immutable)
                (
                    recipient_address,          # Send to user
                    1000,                       # 1000 satoshis (minimum dust)
                    "satoshi",                  # Currency unit
                    self.category_id,           # Platform's category
                    "none",                     # capability="none" (immutable NFT - bitcash spec)
                    commitment,                 # Qube-specific commitment (bytes)
                    None                        # NFT-only (None = no fungible tokens - bitcash spec)
                )
            ]

            logger.info(
                "broadcasting_mint_transaction",
                qube_id=qube.qube_id
            )

            # Step 4: Broadcast transaction
            # Use all available UTXOs (minting token + regular BCH)
            # This ensures we have enough BCH for:
            # - 1000 sats for user's NFT output
            # - Minting token change output (will have combined BCH from both inputs)
            # - Transaction fees

            # Get all unspents to use both minting token UTXO and regular BCH UTXOs
            all_unspents = self.platform_key.get_unspents()

            mint_txid = self.platform_key.send(
                tx_outputs,
                unspents=all_unspents,  # Use ALL UTXOs (minting token + regular BCH)
                leftover=self.platform_key.cashtoken_address  # Return minting token to CashToken address
            )

            logger.info(
                "qube_nft_minted",
                qube_id=qube.qube_id,
                mint_txid=mint_txid,
                recipient=recipient_address
            )

            MetricsRecorder.record_blockchain_event("nft_minted", qube.qube_id)

            result = {
                "category_id": self.category_id,
                "mint_txid": mint_txid,
                "commitment": commitment.hex(),
                "recipient_address": recipient_address,
                "network": self.network,
                "explorer_url": f"https://blockchair.com/bitcoin-cash/transaction/{mint_txid}"
            }

            if ipfs_cid:
                result["ipfs_cid"] = ipfs_cid
                result["ipfs_url"] = f"https://gateway.pinata.cloud/ipfs/{ipfs_cid}"

            import sys
            print("\n" + "=" * 70, file=sys.stderr)
            print(f"🎉 QUBE NFT MINTED SUCCESSFULLY!", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(f"\nQube ID:        {qube.qube_id}", file=sys.stderr)
            print(f"Category ID:    {self.category_id}", file=sys.stderr)
            print(f"Mint TX:        {mint_txid}", file=sys.stderr)
            print(f"Recipient:      {recipient_address}", file=sys.stderr)
            print(f"Network:        {self.network}", file=sys.stderr)
            print(f"\nExplorer:", file=sys.stderr)
            print(f"  {result['explorer_url']}", file=sys.stderr)
            print("\n" + "=" * 70 + "\n", file=sys.stderr)

            return result

        except Exception as e:
            logger.error(
                "nft_minting_failed",
                qube_id=qube.qube_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def _find_minting_token_utxo(self):
        """
        Find UTXO containing the platform minting token

        Returns:
            UTXO with minting capability, or None if not found
        """
        try:
            unspents = self.platform_key.get_unspents()

            logger.debug(
                "searching_for_minting_token",
                total_utxos=len(unspents),
                category_id=self.category_id[:16] + "..."
            )

            # Find ALL minting token UTXOs, then pick the one with most BCH
            minting_utxos = []
            for utxo in unspents:
                # Check if this UTXO has the minting token
                # bitcash uses 'category_id' not 'token_category'
                if (hasattr(utxo, 'category_id') and
                    utxo.category_id == self.category_id and
                    hasattr(utxo, 'nft_capability') and
                    utxo.nft_capability == 'minting'):
                    minting_utxos.append(utxo)

            if minting_utxos:
                # Sort by amount (descending) and pick the largest
                minting_utxo = max(minting_utxos, key=lambda u: u.amount)
                logger.debug(
                    "minting_token_found",
                    amount=minting_utxo.amount,
                    total_minting_utxos=len(minting_utxos)
                )
                return minting_utxo

            logger.warning(
                "minting_token_not_found",
                category_id=self.category_id,
                utxos_checked=len(unspents)
            )

            return None

        except Exception as e:
            logger.error("find_minting_token_failed", error=str(e))
            return None

    def _create_commitment(self, qube, ipfs_cid: Optional[str] = None) -> bytes:
        """
        Create 32-byte commitment from Qube's public key.

        The commitment is SHA256(public_key), making it directly derivable
        from the Qube's cryptographic identity. The qube_id is simply the
        first 8 characters of this commitment (uppercase).

        This means:
        - commitment = "a3f2c1b8def456..." (64 hex chars / 32 bytes)
        - qube_id = "A3F2C1B8" (first 8 chars, uppercase)

        Args:
            qube: Qube instance (must have public_key attribute)
            ipfs_cid: Ignored (kept for API compatibility, stored in BCMR instead)

        Returns:
            32-byte commitment as bytes
        """
        # Derive commitment from public key - qube_id is prefix of this
        commitment_hex = derive_commitment(qube.public_key)
        commitment = bytes.fromhex(commitment_hex)

        # Verify qube_id matches commitment prefix
        expected_qube_id = commitment_hex[:8].upper()
        if qube.qube_id != expected_qube_id:
            logger.warning(
                "qube_id_commitment_mismatch",
                qube_id=qube.qube_id,
                expected=expected_qube_id,
                note="This Qube may have been created before the commitment refactor"
            )

        return commitment

    def get_minting_stats(self) -> Dict[str, Any]:
        """
        Get minting statistics

        Returns:
            Stats about platform minting token
        """
        return {
            "category_id": self.category_id,
            "platform_address": self.platform_key.cashtoken_address,
            "network": self.network,
            "minting_token_config": self.minting_config
        }


# Add blockchain metrics to MetricsRecorder
def _add_blockchain_metrics():
    """Add blockchain event recording to MetricsRecorder"""
    if not hasattr(MetricsRecorder, 'record_blockchain_event'):
        @staticmethod
        def record_blockchain_event(event_type: str, qube_id: str):
            """Record blockchain event (placeholder)"""
            logger.debug(
                "blockchain_event",
                event_type=event_type,
                qube_id=qube_id
            )

        MetricsRecorder.record_blockchain_event = record_blockchain_event


_add_blockchain_metrics()
