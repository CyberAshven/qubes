"""
Master BCMR Registry Manager

Manages the master Bitcoin Cash Metadata Registry for all Qubes.
Implements the parsable NFT format with automatic sync to web server.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


class BCMRRegistryManager:
    """
    Manage master BCMR registry for all Qubes

    Features:
    - Single registry with all Qubes under one category_id
    - Parsable NFT format (nfts.parse.types)
    - Dual hosting (IPFS + HTTPS)
    - Auto-sync to web server via SCP
    - Paytaca indexer integration
    """

    def __init__(
        self,
        category_id: str,
        web_dir: Optional[Path] = None,
        registry_url: str = "https://qube.cash/.well-known/bitcoin-cash-metadata-registry.json"
    ):
        """
        Initialize BCMR registry manager

        Args:
            category_id: Platform minting token category ID
            web_dir: Local web directory (default: data/web)
            registry_url: Public URL for registry
        """
        self.category_id = category_id
        self.registry_url = registry_url

        # Setup directories
        self.web_dir = web_dir or Path("data/web")
        self.wellknown_dir = self.web_dir / ".well-known"
        self.wellknown_dir.mkdir(parents=True, exist_ok=True)

        self.registry_file = self.wellknown_dir / "bitcoin-cash-metadata-registry.json"

        logger.info(
            "bcmr_registry_manager_initialized",
            category_id=category_id[:16] + "...",
            registry_file=str(self.registry_file)
        )

    def create_or_update_registry(self, qubes: List[Any]) -> Dict[str, Any]:
        """
        Create or update the master BCMR registry with all Qubes

        Args:
            qubes: List of Qube instances

        Returns:
            Complete BCMR registry dictionary
        """
        logger.info("updating_master_registry", qube_count=len(qubes))

        # Create revision timestamp
        revision_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Build nfts.parse.types with all Qubes
        nft_types = {}

        for qube in qubes:
            qube_entry = self._create_qube_entry(qube)
            # Use qube_id as the key in parse.types
            nft_types[qube.qube_id] = qube_entry

        # Build complete registry
        registry = {
            "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0
            },
            "latestRevision": revision_timestamp,
            "registryIdentity": {
                "name": "Qubes Network",
                "description": "Sovereign AI Agent NFT Registry",
                "uris": {
                    "web": "https://qube.cash",
                    "registry": self.registry_url,
                    "support": "https://qube.cash/support"
                }
            },
            "identities": {
                self.category_id: {
                    revision_timestamp: {
                        "name": "Qubes",
                        "description": "Sovereign AI Agents with cryptographic identity and persistent memory. Each Qube is a unique self-sovereign digital entity.",
                        "token": {
                            "category": self.category_id,
                            "symbol": "QUBE",
                            "decimals": 0
                        },
                        "uris": {
                            "icon": "ipfs://QmNiPRSUMLdAgCWxZ777Cs5idvtipdWuSrim21cm57JDL7",
                            "image": "ipfs://QmNiPRSUMLdAgCWxZ777Cs5idvtipdWuSrim21cm57JDL7",
                            "web": "https://qube.cash",
                            "support": "https://qube.cash/support"
                        },
                        "nfts": {
                            "description": "Each Qube is a unique sovereign AI entity with its own personality, memory, and cryptographic identity. Qubes can form relationships, earn reputation, and participate in the decentralized AI economy.",
                            "parse": {
                                "types": nft_types
                            }
                        }
                    }
                }
            }
        }

        # Save to local file
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

        logger.info(
            "master_registry_updated",
            qube_count=len(qubes),
            file=str(self.registry_file),
            revision=revision_timestamp
        )

        return registry

    def _create_qube_entry(self, qube) -> Dict[str, Any]:
        """
        Create BCMR entry for a single Qube

        Args:
            qube: Qube instance

        Returns:
            BCMR entry dict for nfts.parse.types
        """
        # Get avatar IPFS CID
        avatar_cid = getattr(qube, 'avatar_ipfs_cid', '')

        # Build icon/image URIs
        if avatar_cid:
            icon_uri = f"ipfs://{avatar_cid}"
            image_uri = f"ipfs://{avatar_cid}"
        else:
            # Fallback to empty (wallet will show placeholder)
            icon_uri = ""
            image_uri = ""

        # Extract qube metadata
        qube_name = getattr(qube, 'name', f"Qube {qube.qube_id}")

        # Get genesis block for description
        if hasattr(qube, 'genesis_block'):
            genesis_prompt = getattr(qube.genesis_block, 'genesis_prompt', '')
            # Truncate to 500 chars for description
            description = genesis_prompt[:500] if genesis_prompt else f"Sovereign AI agent {qube_name}"
        else:
            description = f"Sovereign AI agent {qube_name}"

        # Build attributes
        attributes = self._extract_attributes(qube)

        return {
            "name": qube_name,
            "description": description,
            "uris": {
                "icon": icon_uri,
                "image": image_uri,
                "web": f"https://qube.cash/qube/{qube.qube_id}"
            },
            "extensions": {
                "attributes": attributes
            }
        }

    def _extract_attributes(self, qube) -> Dict[str, str]:
        """
        Extract attributes for a Qube

        Args:
            qube: Qube instance

        Returns:
            Attributes dictionary
        """
        attributes = {}

        # Basic attributes
        attributes["Qube ID"] = qube.qube_id

        if hasattr(qube, 'genesis_block'):
            attributes["Genesis Block Hash"] = qube.genesis_block.block_hash

            creator = getattr(qube.genesis_block, 'creator', None)
            if creator:
                attributes["Creator"] = creator

            birth_timestamp = getattr(qube.genesis_block, 'birth_timestamp', None)
            if birth_timestamp:
                attributes["Birth Date"] = str(birth_timestamp)

            ai_model = getattr(qube.genesis_block, 'ai_model', None)
            if ai_model:
                attributes["AI Model"] = ai_model

        # Blockchain attributes
        attributes["Home Blockchain"] = "Bitcoin Cash"

        # Memory block count
        if hasattr(qube, 'memory_chain') and hasattr(qube.memory_chain, 'get_block_count'):
            try:
                block_count = qube.memory_chain.get_block_count()
                attributes["Memory Blocks"] = str(block_count)
            except:
                pass

        return attributes

    def add_qube_to_registry(self, qube) -> Dict[str, Any]:
        """
        Add a single Qube to the existing registry

        Args:
            qube: Qube instance to add

        Returns:
            Updated registry
        """
        logger.info("adding_qube_to_registry", qube_id=qube.qube_id)

        # Load existing registry or create new
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                registry = json.load(f)
        else:
            logger.warning("registry_not_found_creating_new")
            # Create empty registry
            registry = self.create_or_update_registry([])

        # Get latest revision
        identities = registry.get("identities", {})
        category_data = identities.get(self.category_id, {})

        # Get latest timestamp
        if category_data:
            latest_timestamp = max(category_data.keys())
            latest_revision = category_data[latest_timestamp]
        else:
            # Create new revision
            latest_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            latest_revision = {
                "name": "Qubes",
                "description": "Sovereign AI Agent NFT Registry",
                "token": {
                    "category": self.category_id,
                    "symbol": "QUBE",
                    "decimals": 0
                },
                "uris": {
                    "icon": "ipfs://QmQubesLogoPlaceholder",
                    "web": "https://qube.cash"
                },
                "nfts": {
                    "description": "Sovereign AI Agents",
                    "parse": {
                        "types": {}
                    }
                }
            }

        # Add qube to parse.types
        qube_entry = self._create_qube_entry(qube)
        latest_revision["nfts"]["parse"]["types"][qube.qube_id] = qube_entry

        # Update registry
        registry["identities"][self.category_id] = {latest_timestamp: latest_revision}
        registry["latestRevision"] = latest_timestamp

        # Save
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

        logger.info("qube_added_to_registry", qube_id=qube.qube_id)

        return registry

    def sync_to_server(
        self,
        server_host: str = "YOUR_SERVER_IP",
        server_user: str = "root",
        server_path: str = "/var/www/your-domain/.well-known/",
        auto_sync: bool = True
    ) -> bool:
        """
        Sync BCMR registry to web server via SCP

        Args:
            server_host: Server hostname/IP
            server_user: SSH username
            server_path: Destination path on server
            auto_sync: If True, auto-sync; if False, just print command

        Returns:
            True if synced successfully, False otherwise
        """
        from utils.input_validation import validate_ssh_hostname, validate_user_id
        from core.exceptions import QubesError

        if not self.registry_file.exists():
            logger.error("cannot_sync_registry_not_found")
            return False

        # Validate SSH parameters to prevent command injection
        try:
            server_host = validate_ssh_hostname(server_host)
            server_user = validate_user_id(server_user)  # Reuse user_id validation (alphanumeric + dash/underscore)

            # Validate server_path (basic check for dangerous characters)
            if not re.match(r'^[a-zA-Z0-9/_.-]+$', server_path):
                raise QubesError(f"Invalid server path format: {server_path}")
        except QubesError as e:
            logger.error("ssh_parameter_validation_failed", error=str(e))
            print(f"\n❌ Invalid SSH parameters: {str(e)}\n")
            return False

        # Build SCP command (now validated)
        scp_command = [
            "scp",
            str(self.registry_file),
            f"{server_user}@{server_host}:{server_path}"
        ]

        if auto_sync:
            try:
                logger.info("syncing_to_server", host=server_host, path=server_path)

                result = subprocess.run(
                    scp_command,
                    check=True,
                    capture_output=True,
                    text=True
                )

                logger.info("registry_synced_to_server", host=server_host)
                return True

            except subprocess.CalledProcessError as e:
                logger.error(
                    "scp_failed",
                    error=e.stderr,
                    command=" ".join(scp_command)
                )
                print(f"\n❌ Auto-sync failed. Please run manually:")
                print(f"   {' '.join(scp_command)}\n")
                return False
            except FileNotFoundError:
                logger.error("scp_not_found")
                print(f"\n❌ SCP command not found. Please install OpenSSH client.")
                print(f"   Manual sync command:")
                print(f"   {' '.join(scp_command)}\n")
                return False
        else:
            # Just print the command
            print(f"\n📤 To sync BCMR to server, run:")
            print(f"   {' '.join(scp_command)}\n")
            return False

    async def upload_to_ipfs(self) -> Optional[str]:
        """
        Upload BCMR registry to IPFS via Pinata

        Returns:
            IPFS CID or None if upload fails
        """
        if not self.registry_file.exists():
            logger.error("cannot_upload_registry_not_found")
            return None

        try:
            from blockchain.ipfs import IPFSUploader

            # Use Pinata for registry uploads
            uploader = IPFSUploader(use_pinata=True)
            ipfs_uri = await uploader.upload_file(str(self.registry_file), pin=True)

            if ipfs_uri:
                cid = ipfs_uri.replace("ipfs://", "")
                logger.info("registry_uploaded_to_ipfs", cid=cid)
                return cid
            else:
                logger.warning("ipfs_upload_failed")
                return None

        except Exception as e:
            logger.error("ipfs_upload_error", error=str(e))
            return None

    def trigger_paytaca_reindex(self) -> bool:
        """
        Trigger Paytaca BCMR indexer to reindex this category

        Returns:
            True if reindex triggered successfully
        """
        try:
            import requests

            url = f"https://bcmr.paytaca.com/api/bcmr/{self.category_id}/reindex/"

            logger.info("triggering_paytaca_reindex", category_id=self.category_id[:16] + "...")

            response = requests.post(url, timeout=10)

            if response.status_code == 200:
                logger.info("paytaca_reindex_triggered")
                return True
            else:
                logger.warning(
                    "paytaca_reindex_failed",
                    status=response.status_code,
                    response=response.text
                )
                return False

        except Exception as e:
            logger.error("paytaca_reindex_error", error=str(e))
            return False

    def get_registry(self) -> Optional[Dict[str, Any]]:
        """
        Load current registry from disk

        Returns:
            Registry dict or None if not found
        """
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return None
