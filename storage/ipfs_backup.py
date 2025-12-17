"""
IPFS Backup & Restore for Qubes

Implements Model 3: NFT + IPFS Backup
- Encrypts full Qube data (memory chain + keys)
- Uploads to IPFS via Pinata
- Returns IPFS CID for embedding in NFT commitment
- Allows restore from IPFS + password on any device

From NFT_OWNERSHIP_VS_RUNNING_QUBES.md - Model 3
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import aiohttp
import asyncio

from crypto.encryption import generate_encryption_key
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class QubeBackup:
    """
    Backup and restore Qubes to/from IPFS

    Features:
    - Full memory chain export
    - AES-256-GCM encryption with password-derived key
    - IPFS upload via Pinata
    - Cross-device restore capability
    """

    def __init__(
        self,
        pinata_api_key: Optional[str] = None,
        ipfs_gateway: str = "https://gateway.pinata.cloud"
    ):
        """
        Initialize IPFS backup manager

        Args:
            pinata_api_key: Pinata JWT token (or from env)
            ipfs_gateway: IPFS gateway URL for downloads
        """
        self.pinata_api_key = pinata_api_key or os.getenv("PINATA_API_KEY")
        self.ipfs_gateway = ipfs_gateway

        if not self.pinata_api_key:
            logger.warning("pinata_api_key_not_set", msg="IPFS backup will fail without API key")

        logger.info("ipfs_backup_initialized", gateway=ipfs_gateway)

    async def backup_to_ipfs(
        self,
        qube,
        password: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Encrypt and upload Qube to IPFS

        Args:
            qube: Qube instance to backup
            password: Password for encryption (user-provided)
            metadata: Optional metadata to include

        Returns:
            {
                "ipfs_cid": str,
                "ipfs_url": str,
                "encrypted_size": int,
                "backup_timestamp": int
            }
        """
        try:
            logger.info("backing_up_qube_to_ipfs", qube_id=qube.qube_id)

            # Step 1: Export full Qube data
            backup_data = self._export_qube_data(qube, metadata)

            logger.debug(
                "qube_data_exported",
                qube_id=qube.qube_id,
                blocks=backup_data["chain_length"],
                size_kb=len(json.dumps(backup_data)) / 1024
            )

            # Step 2: Encrypt with password-derived key
            encrypted_data = self._encrypt_backup(backup_data, password)

            logger.debug(
                "backup_encrypted",
                qube_id=qube.qube_id,
                encrypted_size_kb=len(encrypted_data) / 1024
            )

            # Step 3: Upload to IPFS via Pinata
            ipfs_cid = await self._upload_to_pinata(
                encrypted_data,
                filename=f"qube_{qube.qube_id}_backup.enc"
            )

            logger.info(
                "qube_backed_up_to_ipfs",
                qube_id=qube.qube_id,
                ipfs_cid=ipfs_cid,
                size_kb=len(encrypted_data) / 1024
            )

            MetricsRecorder.record_blockchain_event("ipfs_backup_created", qube.qube_id)

            result = {
                "ipfs_cid": ipfs_cid,
                "ipfs_url": f"{self.ipfs_gateway}/ipfs/{ipfs_cid}",
                "encrypted_size": len(encrypted_data),
                "backup_timestamp": backup_data["backup_timestamp"]
            }

            return result

        except Exception as e:
            logger.error(
                "ipfs_backup_failed",
                qube_id=qube.qube_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def restore_from_ipfs(
        self,
        ipfs_cid: str,
        password: str,
        data_dir: Path
    ) -> Dict[str, Any]:
        """
        Download and decrypt Qube from IPFS

        Args:
            ipfs_cid: IPFS content ID
            password: Password for decryption
            data_dir: Directory to restore Qube to

        Returns:
            {
                "qube_id": str,
                "qube_name": str,
                "chain_length": int,
                "restored_path": str
            }
        """
        try:
            logger.info("restoring_qube_from_ipfs", ipfs_cid=ipfs_cid)

            # Step 1: Download from IPFS
            encrypted_data = await self._download_from_ipfs(ipfs_cid)

            logger.debug(
                "ipfs_download_complete",
                ipfs_cid=ipfs_cid,
                size_kb=len(encrypted_data) / 1024
            )

            # Step 2: Decrypt with password
            backup_data = self._decrypt_backup(encrypted_data, password)

            logger.debug(
                "backup_decrypted",
                qube_id=backup_data["qube_id"],
                chain_length=backup_data["chain_length"]
            )

            # Step 3: Import to local storage
            restored_path = self._import_qube_data(backup_data, data_dir)

            logger.info(
                "qube_restored_from_ipfs",
                qube_id=backup_data["qube_id"],
                qube_name=backup_data["qube_name"],
                path=restored_path
            )

            MetricsRecorder.record_blockchain_event("ipfs_restore_complete", backup_data["qube_id"])

            return {
                "qube_id": backup_data["qube_id"],
                "qube_name": backup_data["qube_name"],
                "chain_length": backup_data["chain_length"],
                "restored_path": restored_path
            }

        except Exception as e:
            logger.error(
                "ipfs_restore_failed",
                ipfs_cid=ipfs_cid,
                error=str(e),
                exc_info=True
            )
            raise

    def _export_qube_data(
        self,
        qube,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export full Qube data for backup

        Args:
            qube: Qube instance
            metadata: Optional additional metadata

        Returns:
            Complete Qube data as dict
        """
        from datetime import datetime, timezone

        # Export all blocks from storage
        chain_length = qube.memory_chain.get_chain_length()
        all_blocks = []
        for i in range(chain_length):
            block = qube.storage.read_block(qube.qube_id, i)
            if block:
                all_blocks.append(block.to_dict())

        # Compute merkle root from all block hashes
        from crypto.merkle import compute_merkle_root
        block_hashes = [block["block_hash"] for block in all_blocks]
        merkle_root = compute_merkle_root(block_hashes) if block_hashes else None

        backup_data = {
            # Qube identity
            "qube_id": qube.qube_id,
            "qube_name": qube.name,
            "public_key": qube.genesis_block.public_key,

            # Memory chain
            "chain_length": chain_length,
            "blocks": all_blocks,
            "merkle_root": merkle_root,

            # Chain state
            "chain_state": {
                "last_block_hash": qube.chain_state.state["last_block_hash"],
                "block_counts": qube.chain_state.state["block_counts"],
                "total_tokens_used": qube.chain_state.state["total_tokens_used"],
                "total_api_cost": qube.chain_state.state["total_api_cost"],
            },

            # Metadata
            "backup_timestamp": int(datetime.now(timezone.utc).timestamp()),
            "backup_version": "1.0",
            "metadata": metadata or {}
        }

        return backup_data

    def _encrypt_backup(self, backup_data: Dict[str, Any], password: str) -> bytes:
        """
        Encrypt backup data with password-derived key

        Args:
            backup_data: Qube data to encrypt
            password: User password

        Returns:
            Encrypted bytes (includes salt + nonce + ciphertext + tag)
        """
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        import os

        # Convert to JSON
        json_data = json.dumps(backup_data, indent=2)
        plaintext = json_data.encode('utf-8')

        # Generate salt
        salt = os.urandom(32)

        # Derive key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode('utf-8'))

        # Encrypt with AES-256-GCM
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets

        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Package: nonce (12 bytes) + ciphertext
        encrypted = nonce + ciphertext

        # Package: salt (32 bytes) + encrypted_data
        packaged = salt + encrypted

        return packaged

    def _decrypt_backup(self, encrypted_data: bytes, password: str) -> Dict[str, Any]:
        """
        Decrypt backup data with password

        Args:
            encrypted_data: Encrypted backup bytes
            password: User password

        Returns:
            Decrypted Qube data
        """
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend

        # Unpackage: extract salt
        salt = encrypted_data[:32]
        encrypted_payload = encrypted_data[32:]

        # Derive key from password + salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode('utf-8'))

        # Decrypt
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Unpack: nonce (12 bytes) + ciphertext
        nonce = encrypted_payload[:12]
        ciphertext = encrypted_payload[12:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # Parse JSON
        json_data = plaintext.decode('utf-8')
        backup_data = json.loads(json_data)

        return backup_data

    async def _upload_to_pinata(self, data: bytes, filename: str) -> str:
        """
        Upload data to IPFS via Pinata

        Args:
            data: Bytes to upload
            filename: Filename for the upload

        Returns:
            IPFS CID (content identifier)
        """
        if not self.pinata_api_key:
            raise ValueError("PINATA_API_KEY not set - cannot upload to IPFS")

        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"

        headers = {
            "Authorization": f"Bearer {self.pinata_api_key}"
        }

        # Create form data
        form = aiohttp.FormData()
        form.add_field(
            'file',
            data,
            filename=filename,
            content_type='application/octet-stream'
        )

        # Optional: Add metadata
        pinata_metadata = json.dumps({
            "name": filename,
            "keyvalues": {
                "type": "qube_backup",
                "encrypted": "true"
            }
        })
        form.add_field('pinataMetadata', pinata_metadata)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Pinata upload failed: {resp.status} - {error_text}")

                result = await resp.json()
                ipfs_cid = result['IpfsHash']

                logger.info(
                    "ipfs_upload_complete",
                    ipfs_cid=ipfs_cid,
                    size_kb=len(data) / 1024
                )

                return ipfs_cid

    async def _download_from_ipfs(self, ipfs_cid: str) -> bytes:
        """
        Download data from IPFS

        Args:
            ipfs_cid: IPFS content identifier

        Returns:
            Downloaded bytes
        """
        url = f"{self.ipfs_gateway}/ipfs/{ipfs_cid}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"IPFS download failed: {resp.status}")

                data = await resp.read()

                logger.info(
                    "ipfs_download_complete",
                    ipfs_cid=ipfs_cid,
                    size_kb=len(data) / 1024
                )

                return data

    def _import_qube_data(
        self,
        backup_data: Dict[str, Any],
        data_dir: Path
    ) -> str:
        """
        Import Qube data to local storage

        Args:
            backup_data: Decrypted backup data
            data_dir: Base data directory

        Returns:
            Path to restored Qube directory
        """
        from core.block import Block

        qube_id = backup_data["qube_id"]
        qube_name = backup_data["qube_name"]

        # Create Qube directory
        qube_dir_name = f"{qube_name}_{qube_id}"
        qube_path = data_dir / "qubes" / qube_dir_name
        qube_path.mkdir(parents=True, exist_ok=True)

        # Write all blocks to JSON files
        blocks_dir = qube_path / "blocks" / "permanent"
        blocks_dir.mkdir(parents=True, exist_ok=True)

        for block_dict in backup_data["blocks"]:
            block = Block.from_dict(block_dict)
            block_type_str = block_dict.get("block_type", "UNKNOWN")
            timestamp = block_dict.get("timestamp", 0)
            filename = f"{block.block_number}_{block_type_str}_{timestamp}.json"
            block_file = blocks_dir / filename

            with open(block_file, 'w') as f:
                json.dump(block_dict, f, indent=2)

        # Write chain state
        chain_state_path = qube_path / "chain_state.json"
        chain_state_data = {
            "qube_id": qube_id,
            "chain_length": backup_data["chain_length"],
            "last_block_number": backup_data["chain_length"] - 1,
            "last_block_hash": backup_data["chain_state"]["last_block_hash"],
            "block_counts": backup_data["chain_state"]["block_counts"],
            "total_tokens_used": backup_data["chain_state"]["total_tokens_used"],
            "total_api_cost": backup_data["chain_state"]["total_api_cost"],
            "restored_from_ipfs": True,
            "restored_at": int(__import__('time').time())
        }

        with open(chain_state_path, 'w') as f:
            json.dump(chain_state_data, f, indent=2)

        storage.close()

        logger.info(
            "qube_data_imported",
            qube_id=qube_id,
            path=str(qube_path),
            blocks=backup_data["chain_length"]
        )

        return str(qube_path)

    async def get_backup_info(self, ipfs_cid: str) -> Dict[str, Any]:
        """
        Get info about a backup without downloading/decrypting full data

        Args:
            ipfs_cid: IPFS content identifier

        Returns:
            Backup metadata (size, timestamp, etc.)
        """
        url = f"{self.ipfs_gateway}/ipfs/{ipfs_cid}"

        async with aiohttp.ClientSession() as session:
            async with session.head(url) as resp:
                if resp.status != 200:
                    raise Exception(f"IPFS HEAD request failed: {resp.status}")

                size = int(resp.headers.get('Content-Length', 0))

                return {
                    "ipfs_cid": ipfs_cid,
                    "ipfs_url": url,
                    "size_bytes": size,
                    "size_kb": size / 1024,
                    "size_mb": size / (1024 * 1024)
                }
