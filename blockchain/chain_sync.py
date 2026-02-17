"""
Chain Sync Service for Qube NFT-Bundled Storage

Orchestrates the sync/transfer/import of Qubes using:
- ECIES encryption (symmetric key encrypted to owner's public key)
- IPFS storage (encrypted Qube data on Pinata/local IPFS)
- BCMR metadata (CID + encrypted key stored in NFT metadata)
- CashToken NFT (ownership proof and metadata carrier)

Two main modes:
1. Sync to Pinata: Backup Qube to IPFS via Pinata, encrypted to self
2. Transfer: Re-encrypt to recipient, send NFT, delete local

From the NFT-Bundled Qube Transfer System plan.
"""

import json
import os
import shutil
import tempfile
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass

from crypto.ecies import (
    ecies_encrypt, ecies_decrypt,
    encrypt_symmetric_key_for_recipient,
    decrypt_symmetric_key,
    fetch_public_key_from_address
)
from crypto.keys import (
    serialize_public_key,
    deserialize_public_key,
    generate_key_pair
)
from blockchain.chain_package import (
    create_chain_package,
    unpack_chain_package,
    restore_qube_from_package,
    verify_package_integrity
)
from blockchain.bcmr import BCMRGenerator
from blockchain.ipfs import IPFSUploader
from blockchain.registry import QubeNFTRegistry
from blockchain.verifier import NFTVerifier
from core.exceptions import CryptoError, BlockchainError
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """Result of sync to chain operation"""
    success: bool
    ipfs_cid: Optional[str] = None
    encrypted_key: Optional[str] = None
    merkle_root: Optional[str] = None
    chain_length: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "ipfs_cid": self.ipfs_cid,
            "encrypted_key": self.encrypted_key,
            "merkle_root": self.merkle_root,
            "chain_length": self.chain_length,
            "error": self.error
        }


@dataclass
class TransferResult:
    """Result of transfer operation"""
    success: bool
    transfer_txid: Optional[str] = None
    recipient_address: Optional[str] = None
    ipfs_cid: Optional[str] = None
    local_deleted: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "transfer_txid": self.transfer_txid,
            "recipient_address": self.recipient_address,
            "ipfs_cid": self.ipfs_cid,
            "local_deleted": self.local_deleted,
            "error": self.error
        }


@dataclass
class ImportResult:
    """Result of import from wallet operation"""
    success: bool
    qube_id: Optional[str] = None
    qube_name: Optional[str] = None
    qube_dir: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "qube_id": self.qube_id,
            "qube_name": self.qube_name,
            "qube_dir": self.qube_dir,
            "error": self.error
        }


@dataclass
class WalletQubeInfo:
    """Information about a Qube found in a wallet"""
    qube_id: str
    qube_name: str
    category_id: str
    ipfs_cid: str
    chain_length: int
    sync_timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "qube_id": self.qube_id,
            "qube_name": self.qube_name,
            "category_id": self.category_id,
            "ipfs_cid": self.ipfs_cid,
            "chain_length": self.chain_length,
            "sync_timestamp": self.sync_timestamp
        }


class ChainSyncService:
    """
    Main orchestration service for NFT-bundled Qube storage

    Handles:
    - Syncing Qubes to IPFS (backup)
    - Transferring Qubes to new owners
    - Importing Qubes from wallet
    - Scanning wallets for owned Qubes
    """

    def __init__(
        self,
        use_pinata: bool = True,
        pinata_api_key: Optional[str] = None,
        network: str = "mainnet"
    ):
        """
        Initialize chain sync service

        Args:
            use_pinata: Use Pinata for IPFS (recommended)
            pinata_api_key: Pinata JWT token (or set PINATA_API_KEY env)
            network: "mainnet" or "chipnet"
        """
        self.use_pinata = use_pinata
        self.pinata_api_key = pinata_api_key or os.getenv("PINATA_API_KEY")
        self.network = network

        # Initialize components
        self.ipfs_uploader = IPFSUploader(
            use_pinata=use_pinata,
            pinata_api_key=self.pinata_api_key
        )
        self.bcmr_generator = BCMRGenerator()
        self.nft_registry = QubeNFTRegistry()
        self.nft_verifier = NFTVerifier()

        logger.info(
            "chain_sync_service_initialized",
            use_pinata=use_pinata,
            network=network
        )

    async def sync_to_chain(
        self,
        qube_dir: str,
        qube_id: str,
        qube_name: str,
        owner_public_key_hex: str,
        genesis_block: Any,
        user_id: str,
        category_id: str,
        encryption_key: Optional[bytes] = None
    ) -> SyncResult:
        """
        Sync Qube to chain (backup to IPFS)

        Process:
        1. Package all Qube data (blocks, relationships, skills, etc.)
        2. Encrypt package with AES-256-GCM
        3. Encrypt symmetric key with ECIES to owner's public key
        4. Upload encrypted package to IPFS
        5. Update BCMR metadata with CID and encrypted key

        Args:
            qube_dir: Path to Qube's data directory
            qube_id: Qube ID (8-char hex)
            qube_name: Qube's name
            owner_public_key_hex: Owner's secp256k1 public key (compressed hex)
            genesis_block: Qube's genesis block
            user_id: Current user ID
            category_id: NFT category ID

        Returns:
            SyncResult with IPFS CID and encrypted key
        """
        try:
            logger.info(
                "sync_to_chain_started",
                qube_id=qube_id,
                qube_name=qube_name
            )

            import sys
            print(f"\n🔄 Syncing {qube_name} to chain...", file=sys.stderr)

            # Step 1: Create encrypted chain package
            print("  📦 Packaging Qube data...", file=sys.stderr)
            encrypted_package, symmetric_key = create_chain_package(
                qube_dir=Path(qube_dir),  # Convert string to Path
                qube_id=qube_id,
                qube_name=qube_name,
                public_key=owner_public_key_hex,
                genesis_block=genesis_block,
                user_id=user_id,
                has_nft=True,
                nft_category_id=category_id,
                encryption_key=encryption_key
            )

            # Step 2: Encrypt symmetric key with ECIES to owner
            print("  🔐 Encrypting key to owner...", file=sys.stderr)
            encrypted_key = encrypt_symmetric_key_for_recipient(
                symmetric_key,
                owner_public_key_hex
            )

            # Step 3: Upload to IPFS
            print("  ☁️  Uploading to IPFS...", file=sys.stderr)

            # Write encrypted package to temp file for upload
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".qube.enc"
            ) as temp_file:
                temp_file.write(encrypted_package)
                temp_path = temp_file.name

            try:
                # Upload encrypted package
                ipfs_uri = await self.ipfs_uploader.upload_file(
                    temp_path,
                    custom_filename=f"{qube_name}_{qube_id}.qube.enc"
                )
            finally:
                # Clean up temp file
                os.unlink(temp_path)

            if not ipfs_uri:
                return SyncResult(
                    success=False,
                    error="Failed to upload to IPFS"
                )

            # Extract CID from ipfs:// URI
            ipfs_cid = ipfs_uri.replace("ipfs://", "")

            # Step 4: Count blocks from actual block files
            blocks_dir = Path(qube_dir) / "blocks" / "permanent"
            if blocks_dir.exists():
                chain_length = len(list(blocks_dir.glob("*.json")))
            else:
                chain_length = 0
            merkle_root = ""

            # Step 5: Update BCMR metadata
            print("  📝 Updating BCMR metadata...", file=sys.stderr)
            bcmr_uri = self.bcmr_generator.update_chain_sync_metadata(
                category_id=category_id,
                ipfs_cid=ipfs_cid,
                encrypted_key=encrypted_key,
                chain_length=chain_length,
                merkle_root=merkle_root
            )

            logger.info(
                "sync_to_chain_completed",
                qube_id=qube_id,
                ipfs_cid=ipfs_cid,
                chain_length=chain_length
            )

            print(f"\n✅ Sync complete!", file=sys.stderr)
            print(f"   IPFS CID: {ipfs_cid}", file=sys.stderr)
            print(f"   Gateway: https://gateway.pinata.cloud/ipfs/{ipfs_cid}\n", file=sys.stderr)

            return SyncResult(
                success=True,
                ipfs_cid=ipfs_cid,
                encrypted_key=encrypted_key,
                merkle_root=merkle_root,
                chain_length=chain_length
            )

        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            logger.error(
                "sync_to_chain_failed",
                qube_id=qube_id,
                error=error_details,
                traceback=traceback.format_exc()
            )
            # Print to stderr for visibility
            print(f"\n❌ Sync error: {error_details}", file=sys.stderr)
            print(f"   Traceback: {traceback.format_exc()}", file=sys.stderr)
            return SyncResult(
                success=False,
                error=error_details
            )

    async def transfer_qube(
        self,
        qube_dir: str,
        qube_id: str,
        qube_name: str,
        owner_private_key: Any,
        owner_public_key_hex: str,
        recipient_address: str,
        recipient_public_key_hex: str,
        genesis_block: Any,
        user_id: str,
        category_id: str,
        wallet_wif: str,
        encryption_key: Optional[bytes] = None
    ) -> TransferResult:
        """
        Transfer Qube to new owner

        Process:
        1. Sync latest state to IPFS (encrypted to self)
        2. Re-encrypt symmetric key with ECIES to recipient's public key
        3. Update BCMR metadata with new encrypted key
        4. Send NFT to recipient's address
        5. DELETE local Qube data (transfer is destructive)

        IMPORTANT: This is a destructive operation. The local Qube will be deleted
        after successful transfer. The only copy will be on IPFS.

        Args:
            qube_dir: Path to Qube's data directory
            qube_id: Qube ID
            qube_name: Qube's name
            owner_private_key: Owner's ECDSA private key
            owner_public_key_hex: Owner's public key hex
            recipient_address: Recipient's BCH address
            recipient_public_key_hex: Recipient's public key hex
            genesis_block: Qube's genesis block
            user_id: Current user ID
            category_id: NFT category ID
            wallet_wif: Owner's wallet WIF for NFT transfer

        Returns:
            TransferResult with transaction ID
        """
        try:
            logger.info(
                "transfer_qube_started",
                qube_id=qube_id,
                recipient=recipient_address
            )

            import sys
            print(f"\n🔄 Transferring {qube_name} to {recipient_address[:20]}...", file=sys.stderr)

            # Step 1: Sync to chain first (always sync before transfer)
            print("  📤 Syncing latest state...", file=sys.stderr)
            sync_result = await self.sync_to_chain(
                qube_dir=qube_dir,
                qube_id=qube_id,
                qube_name=qube_name,
                owner_public_key_hex=owner_public_key_hex,
                genesis_block=genesis_block,
                user_id=user_id,
                category_id=category_id,
                encryption_key=encryption_key
            )

            if not sync_result.success:
                return TransferResult(
                    success=False,
                    error=f"Sync failed: {sync_result.error}"
                )

            # Step 2: Decrypt symmetric key with owner's key
            print("  🔓 Decrypting symmetric key...", file=sys.stderr)
            symmetric_key = decrypt_symmetric_key(
                sync_result.encrypted_key,
                owner_private_key
            )

            # Step 3: Re-encrypt symmetric key with ECIES to recipient
            print("  🔐 Re-encrypting for recipient...", file=sys.stderr)
            new_encrypted_key = encrypt_symmetric_key_for_recipient(
                symmetric_key,
                recipient_public_key_hex
            )

            # Step 4: Get current key version and increment
            current_metadata = self.bcmr_generator.get_chain_sync_metadata(category_id)
            current_version = current_metadata.get("key_version", 1) if current_metadata else 1
            new_version = current_version + 1

            # Step 5: Update BCMR with new encrypted key
            print("  📝 Updating BCMR for new owner...", file=sys.stderr)
            self.bcmr_generator.update_encrypted_key_for_transfer(
                category_id=category_id,
                new_encrypted_key=new_encrypted_key,
                new_key_version=new_version
            )

            # Step 6: Send NFT to recipient
            print("  💸 Sending NFT to recipient...", file=sys.stderr)
            transfer_txid = await self._send_nft(
                category_id=category_id,
                recipient_address=recipient_address,
                wallet_wif=wallet_wif
            )

            if not transfer_txid:
                return TransferResult(
                    success=False,
                    error="Failed to send NFT - local data NOT deleted"
                )

            # Step 7: DELETE local Qube data (transfer is destructive)
            print("  🗑️  Deleting local copy...", file=sys.stderr)
            try:
                shutil.rmtree(qube_dir)
                local_deleted = True
                logger.info(
                    "local_qube_deleted",
                    qube_id=qube_id,
                    qube_dir=qube_dir
                )
            except Exception as e:
                logger.warning(
                    "local_delete_failed",
                    qube_id=qube_id,
                    error=str(e)
                )
                local_deleted = False

            # Step 8: Update registry
            self.nft_registry.registry[qube_id]["recipient_address"] = recipient_address
            self.nft_registry.registry[qube_id]["transferred_at"] = datetime.now(timezone.utc).isoformat()
            self.nft_registry.registry[qube_id]["transfer_txid"] = transfer_txid
            self.nft_registry._save_registry()

            logger.info(
                "transfer_qube_completed",
                qube_id=qube_id,
                transfer_txid=transfer_txid,
                recipient=recipient_address
            )

            print(f"\n✅ Transfer complete!", file=sys.stderr)
            print(f"   TX: {transfer_txid}", file=sys.stderr)
            print(f"   Explorer: https://blockchair.com/bitcoin-cash/transaction/{transfer_txid}\n", file=sys.stderr)

            return TransferResult(
                success=True,
                transfer_txid=transfer_txid,
                recipient_address=recipient_address,
                ipfs_cid=sync_result.ipfs_cid,
                local_deleted=local_deleted
            )

        except Exception as e:
            logger.error(
                "transfer_qube_failed",
                qube_id=qube_id,
                error=str(e),
                exc_info=True
            )
            return TransferResult(
                success=False,
                error=str(e)
            )

    async def import_from_wallet(
        self,
        wallet_wif: str,
        category_id: str,
        target_user_dir: str,
        master_password: str
    ) -> ImportResult:
        """
        Import Qube from wallet

        Process:
        1. Verify wallet owns NFT with this category
        2. Fetch BCMR metadata to get IPFS CID and encrypted key
        3. Download encrypted package from IPFS
        4. Decrypt symmetric key with wallet's private key
        5. Decrypt and unpack Qube data
        6. Re-encrypt Qube's private key with local master password
        7. Save Qube to local storage

        Args:
            wallet_wif: Wallet's WIF private key
            category_id: NFT category ID to import
            target_user_dir: User's qubes directory
            master_password: Local master password for re-encryption

        Returns:
            ImportResult with imported Qube info
        """
        try:
            from bitcash import PrivateKey

            logger.info(
                "import_from_wallet_started",
                category_id=category_id[:16] + "..."
            )

            import sys
            print(f"\n📥 Importing Qube from wallet...", file=sys.stderr)

            # Step 1: Parse wallet and get address
            bitcash_network = "test" if self.network == "chipnet" else "main"
            wallet = PrivateKey(wallet_wif, network=bitcash_network)
            wallet_address = wallet.cashtoken_address

            print(f"  🔑 Wallet: {wallet_address[:20]}...", file=sys.stderr)

            # Step 2: Verify wallet owns this NFT
            print("  🔍 Verifying NFT ownership...", file=sys.stderr)
            owns_nft = await self.nft_verifier.verify_ownership(
                category_id,
                wallet_address
            )

            if not owns_nft:
                return ImportResult(
                    success=False,
                    error="Wallet does not own NFT with this category"
                )

            # Step 3: Get chain_sync metadata from BCMR
            print("  📝 Fetching BCMR metadata...", file=sys.stderr)
            chain_sync = self.bcmr_generator.get_chain_sync_metadata(category_id)

            if not chain_sync:
                return ImportResult(
                    success=False,
                    error="No chain_sync metadata found in BCMR"
                )

            ipfs_cid = chain_sync.get("ipfs_cid")
            encrypted_key = chain_sync.get("encrypted_key")

            if not ipfs_cid or not encrypted_key:
                return ImportResult(
                    success=False,
                    error="Missing ipfs_cid or encrypted_key in BCMR"
                )

            # Step 4: Download encrypted package from IPFS
            print(f"  ☁️  Downloading from IPFS ({ipfs_cid[:16]}...)", file=sys.stderr)
            encrypted_package = await self._download_from_ipfs(ipfs_cid)

            if not encrypted_package:
                return ImportResult(
                    success=False,
                    error=f"Failed to download from IPFS: {ipfs_cid}"
                )

            # Step 5: Get wallet's private key for decryption
            # Convert bitcash private key to cryptography format
            wallet_private_key = self._bitcash_to_crypto_key(wallet)

            # Step 6: Decrypt symmetric key
            print("  🔓 Decrypting package...", file=sys.stderr)
            symmetric_key = decrypt_symmetric_key(
                encrypted_key,
                wallet_private_key
            )

            # Step 7: Unpack and decrypt Qube data
            package_data, package_metadata = unpack_chain_package(
                encrypted_package,
                symmetric_key
            )

            # Step 8: Check if Qube already exists locally
            qube_id = package_metadata.qube_id
            qube_name = package_metadata.qube_name

            existing_qubes = list(Path(target_user_dir).glob(f"*_{qube_id}"))
            if existing_qubes:
                return ImportResult(
                    success=False,
                    qube_id=qube_id,
                    qube_name=qube_name,
                    error=f"Qube {qube_name} ({qube_id}) already exists locally"
                )

            # Step 9: Restore Qube from package
            print("  📦 Restoring Qube...", file=sys.stderr)
            qube_dir = restore_qube_from_package(
                package_data=package_data,
                package_metadata=package_metadata,
                target_user_dir=target_user_dir,
                master_password=master_password
            )

            logger.info(
                "import_from_wallet_completed",
                qube_id=qube_id,
                qube_name=qube_name,
                qube_dir=qube_dir
            )

            print(f"\n✅ Import complete!", file=sys.stderr)
            print(f"   Qube: {qube_name} ({qube_id})", file=sys.stderr)
            print(f"   Location: {qube_dir}\n", file=sys.stderr)

            return ImportResult(
                success=True,
                qube_id=qube_id,
                qube_name=qube_name,
                qube_dir=qube_dir
            )

        except Exception as e:
            logger.error(
                "import_from_wallet_failed",
                category_id=category_id[:16] + "...",
                error=str(e),
                exc_info=True
            )
            return ImportResult(
                success=False,
                error=str(e)
            )

    async def scan_wallet_for_qubes(
        self,
        wallet_address: str
    ) -> List[WalletQubeInfo]:
        """
        Scan wallet for Qube NFTs

        Queries the blockchain for all CashToken NFTs owned by this wallet
        that have valid Qube BCMR metadata.

        Args:
            wallet_address: BCH address to scan

        Returns:
            List of WalletQubeInfo for each Qube found
        """
        try:
            logger.info(
                "scan_wallet_started",
                address=wallet_address[:20] + "..."
            )

            import sys
            print(f"\n🔍 Scanning wallet for Qubes...", file=sys.stderr)

            found_qubes: List[WalletQubeInfo] = []

            # Get all NFTs owned by this address from registry
            # (In production, would query blockchain directly)
            for qube_id, entry in self.nft_registry.registry.items():
                if entry.get("recipient_address") == wallet_address:
                    category_id = entry.get("category_id")

                    # Get chain_sync metadata
                    chain_sync = self.bcmr_generator.get_chain_sync_metadata(category_id)

                    if chain_sync:
                        # Get qube name from BCMR
                        bcmr = self.bcmr_generator.load_bcmr(category_id)
                        qube_name = qube_id  # Default

                        if bcmr:
                            try:
                                identities = bcmr.get("identities", {})
                                if category_id in identities:
                                    revisions = identities[category_id]
                                    latest_key = bcmr.get("latestRevision")
                                    if latest_key and latest_key in revisions:
                                        revision = revisions[latest_key]
                                        qube_name = revision.get("name", qube_id)
                            except Exception:
                                pass

                        found_qubes.append(WalletQubeInfo(
                            qube_id=qube_id,
                            qube_name=qube_name,
                            category_id=category_id,
                            ipfs_cid=chain_sync.get("ipfs_cid", ""),
                            chain_length=chain_sync.get("chain_length", 0),
                            sync_timestamp=chain_sync.get("sync_timestamp", 0)
                        ))

            logger.info(
                "scan_wallet_completed",
                address=wallet_address[:20] + "...",
                qubes_found=len(found_qubes)
            )

            print(f"   Found {len(found_qubes)} Qube(s)\n", file=sys.stderr)

            return found_qubes

        except Exception as e:
            logger.error(
                "scan_wallet_failed",
                address=wallet_address[:20] + "...",
                error=str(e),
                exc_info=True
            )
            return []

    async def resolve_recipient_public_key(
        self,
        recipient_address: str
    ) -> Optional[str]:
        """
        Resolve recipient's public key from address

        Attempts to find the public key by:
        1. Querying blockchain for transactions where address spent funds
        2. Extracting public key from signature script

        Args:
            recipient_address: BCH address

        Returns:
            Compressed public key hex or None if not found
        """
        logger.info(
            "resolving_public_key",
            address=recipient_address[:20] + "..."
        )

        public_key = await fetch_public_key_from_address(recipient_address)

        if public_key:
            logger.info(
                "public_key_resolved",
                address=recipient_address[:20] + "...",
                pubkey_prefix=public_key[:8]
            )
        else:
            logger.warning(
                "public_key_not_found",
                address=recipient_address[:20] + "..."
            )

        return public_key

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    async def _send_nft(
        self,
        category_id: str,
        recipient_address: str,
        wallet_wif: str
    ) -> Optional[str]:
        """
        Send NFT to recipient

        Creates a transaction that spends the NFT UTXO and sends
        the NFT to the recipient's address.

        Args:
            category_id: NFT category ID
            recipient_address: Recipient's BCH address
            wallet_wif: Sender's wallet WIF

        Returns:
            Transaction ID or None if failed
        """
        try:
            from bitcash import PrivateKey

            bitcash_network = "test" if self.network == "chipnet" else "main"
            wallet = PrivateKey(wallet_wif, network=bitcash_network)

            # Find NFT UTXO
            unspents = wallet.get_unspents()
            nft_utxo = None

            for utxo in unspents:
                if (hasattr(utxo, 'category_id') and
                    utxo.category_id == category_id and
                    hasattr(utxo, 'nft_capability')):
                    # Found NFT (immutable or any capability)
                    nft_utxo = utxo
                    break

            if not nft_utxo:
                logger.error(
                    "nft_utxo_not_found",
                    category_id=category_id[:16] + "..."
                )
                return None

            # Get commitment from UTXO
            commitment = getattr(nft_utxo, 'nft_commitment', b'')
            if isinstance(commitment, str):
                commitment = bytes.fromhex(commitment)

            # Create transfer transaction
            tx_outputs = [
                (
                    recipient_address,          # Send to recipient
                    1000,                       # 1000 satoshis
                    "satoshi",
                    category_id,                # Same category
                    "none",                     # Keep as immutable
                    commitment,                 # Keep same commitment
                    None                        # No fungible tokens
                )
            ]

            # Send transaction
            txid = wallet.send(
                tx_outputs,
                leftover=wallet.address  # Regular change to sender
            )

            logger.info(
                "nft_sent",
                txid=txid,
                category_id=category_id[:16] + "...",
                recipient=recipient_address
            )

            return txid

        except Exception as e:
            logger.error(
                "send_nft_failed",
                category_id=category_id[:16] + "...",
                error=str(e),
                exc_info=True
            )
            return None

    async def _download_from_ipfs(self, ipfs_cid: str) -> Optional[bytes]:
        """
        Download file from IPFS

        Tries multiple gateways in order.

        Args:
            ipfs_cid: IPFS content ID

        Returns:
            File contents or None if failed
        """
        import aiohttp

        gateways = [
            f"https://gateway.pinata.cloud/ipfs/{ipfs_cid}",
            f"https://ipfs.io/ipfs/{ipfs_cid}",
            f"https://cloudflare-ipfs.com/ipfs/{ipfs_cid}",
            f"https://dweb.link/ipfs/{ipfs_cid}"
        ]

        async with aiohttp.ClientSession() as session:
            for gateway_url in gateways:
                try:
                    logger.debug(
                        "trying_ipfs_gateway",
                        url=gateway_url
                    )

                    async with session.get(
                        gateway_url,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            content = await response.read()
                            logger.info(
                                "ipfs_download_successful",
                                cid=ipfs_cid,
                                size=len(content)
                            )
                            return content

                except Exception as e:
                    logger.warning(
                        "ipfs_gateway_failed",
                        url=gateway_url,
                        error=str(e)
                    )
                    continue

        logger.error(
            "all_ipfs_gateways_failed",
            cid=ipfs_cid
        )
        return None

    def _bitcash_to_crypto_key(self, bitcash_key) -> Any:
        """
        Convert bitcash PrivateKey to cryptography EllipticCurvePrivateKey

        Args:
            bitcash_key: bitcash PrivateKey instance

        Returns:
            cryptography EllipticCurvePrivateKey
        """
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend

        # Get the raw private key bytes from bitcash
        # bitcash stores it as an integer internally
        private_int = bitcash_key._pk.secret

        # Create cryptography private key
        private_key = ec.derive_private_key(
            private_int,
            ec.SECP256K1(),
            default_backend()
        )

        return private_key


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def sync_qube_to_chain(
    qube_dir: str,
    qube_id: str,
    qube_name: str,
    owner_public_key_hex: str,
    genesis_block: Any,
    user_id: str,
    category_id: str,
    encryption_key: Optional[bytes] = None
) -> SyncResult:
    """
    Quick utility to sync a Qube to chain

    Args:
        qube_dir: Path to Qube's data directory
        qube_id: Qube ID
        qube_name: Qube's name
        owner_public_key_hex: Owner's public key
        genesis_block: Genesis block
        user_id: User ID
        category_id: NFT category ID
        encryption_key: Optional encryption key for reading encrypted chain_state

    Returns:
        SyncResult
    """
    service = ChainSyncService()
    return await service.sync_to_chain(
        qube_dir=qube_dir,
        qube_id=qube_id,
        qube_name=qube_name,
        owner_public_key_hex=owner_public_key_hex,
        genesis_block=genesis_block,
        user_id=user_id,
        category_id=category_id,
        encryption_key=encryption_key
    )
