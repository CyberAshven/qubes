"""
IPFS Uploader for BCMR Metadata

Uploads BCMR metadata to IPFS for decentralized hosting.
From docs/10_Blockchain_Integration.md Section 7.5
"""

import json
import os
from typing import Dict, Any, Optional

from utils.logging import get_logger

logger = get_logger(__name__)


class IPFSUploader:
    """
    Upload BCMR metadata to IPFS

    Supports:
    - Local IPFS node (http://127.0.0.1:5001)
    - Pinata pinning service (cloud)
    - Fallback to local file storage
    """

    def __init__(
        self,
        ipfs_api: str = "/ip4/127.0.0.1/tcp/5001",
        use_pinata: bool = False,
        pinata_api_key: Optional[str] = None,
        pinata_secret_key: Optional[str] = None
    ):
        """
        Initialize IPFS uploader

        Args:
            ipfs_api: IPFS API multiaddr for local node
            use_pinata: Whether to use Pinata cloud pinning
            pinata_api_key: Pinata JWT token (or set PINATA_API_KEY env var)
            pinata_secret_key: Pinata secret (or set PINATA_SECRET_KEY env var)
        """
        self.ipfs_api = ipfs_api
        self.client = None
        self.use_pinata = use_pinata
        self.last_error: Optional[str] = None  # Store last error for better user feedback

        # Get Pinata credentials from args or environment
        self.pinata_api_key = pinata_api_key or os.getenv("PINATA_API_KEY")
        self.pinata_secret_key = pinata_secret_key or os.getenv("PINATA_SECRET_KEY")

        if use_pinata and not self.pinata_api_key:
            logger.warning(
                "pinata_credentials_missing",
                message="PINATA_API_KEY not set. Falling back to local IPFS."
            )
            self.use_pinata = False

        logger.info(
            "ipfs_uploader_initialized",
            api=ipfs_api,
            use_pinata=self.use_pinata
        )

    def connect(self) -> bool:
        """
        Connect to IPFS node

        Returns:
            True if connected successfully
        """
        try:
            import ipfshttpclient

            self.client = ipfshttpclient.connect(self.ipfs_api)

            # Test connection
            version = self.client.version()

            logger.info(
                "ipfs_connected",
                version=version.get('Version', 'unknown')
            )

            return True

        except ImportError:
            logger.error("ipfshttpclient_not_installed")
            return False

        except Exception as e:
            logger.warning(
                "ipfs_connection_failed",
                error=str(e)
            )
            return False

    async def upload_bcmr(
        self,
        bcmr_metadata: Dict[str, Any],
        pin: bool = True,
        qube_name: Optional[str] = None,
        qube_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload BCMR metadata to IPFS

        Uses Pinata cloud if configured, otherwise uses local IPFS node.

        Args:
            bcmr_metadata: BCMR metadata dict
            pin: Whether to pin the content
            qube_name: Optional qube name for custom IPFS filename
            qube_id: Optional qube ID for custom IPFS filename

        Returns:
            IPFS URI (ipfs://CID) or None if upload fails
        """
        # Try Pinata first if configured
        if self.use_pinata:
            ipfs_uri = await self._upload_to_pinata(bcmr_metadata, qube_name, qube_id)
            if ipfs_uri:
                return ipfs_uri

            logger.warning("pinata_upload_failed_trying_local")

        # Fallback to local IPFS node
        try:
            if not self.client:
                connected = self.connect()
                if not connected:
                    logger.warning("ipfs_upload_skipped_no_connection")
                    return None

            logger.info("uploading_to_local_ipfs")

            # Upload JSON to IPFS
            result = self.client.add_json(bcmr_metadata)
            cid = result

            logger.info(
                "bcmr_uploaded_to_ipfs",
                cid=cid
            )

            # Pin if requested
            if pin:
                try:
                    self.client.pin.add(cid)
                    logger.debug("bcmr_pinned", cid=cid)
                except Exception as e:
                    logger.warning("ipfs_pin_failed", error=str(e))

            ipfs_uri = f"ipfs://{cid}"

            print(f"\n📤 BCMR uploaded to IPFS!")
            print(f"   CID: {cid}")
            print(f"   URI: {ipfs_uri}")
            print(f"   Gateway: https://ipfs.io/ipfs/{cid}\n")

            return ipfs_uri

        except Exception as e:
            logger.error(
                "ipfs_upload_failed",
                error=str(e),
                exc_info=True
            )
            return None

    async def _upload_to_pinata(
        self,
        bcmr_metadata: Dict[str, Any],
        qube_name: Optional[str] = None,
        qube_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload BCMR metadata to Pinata cloud pinning service

        From docs Section 7.5 - IPFS Integration

        Args:
            bcmr_metadata: BCMR metadata dict
            qube_name: Optional qube name for custom IPFS filename
            qube_id: Optional qube ID for custom IPFS filename

        Returns:
            IPFS URI (ipfs://CID) or None if upload fails
        """
        try:
            import aiohttp

            logger.info("uploading_to_pinata")

            # Pinata API endpoint
            url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

            # Prepare headers
            # Modern Pinata API uses Bearer token (JWT) authentication
            headers = {
                "Authorization": f"Bearer {self.pinata_api_key}",
                "Content-Type": "application/json"
            }

            # Generate custom filename if qube_name and qube_id provided
            if qube_name and qube_id:
                # Create safe name (alphanumeric + - and _ only)
                safe_name = "".join(c for c in qube_name if c.isalnum() or c in ('-', '_'))
                filename = f"{safe_name}_{qube_id}.json"
            else:
                # Fallback to default naming
                filename = f"Qube_BCMR_{bcmr_metadata.get('latestRevision', 'unknown')}.json"

            # Prepare payload
            payload = {
                "pinataContent": bcmr_metadata,
                "pinataMetadata": {
                    "name": filename
                }
            }

            # Upload to Pinata
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        cid = result["IpfsHash"]

                        logger.info(
                            "bcmr_uploaded_to_pinata",
                            cid=cid,
                            filename=filename
                        )

                        ipfs_uri = f"ipfs://{cid}"

                        import sys
                        print(f"\n📤 BCMR uploaded to Pinata!", file=sys.stderr)
                        print(f"   Filename: {filename}", file=sys.stderr)
                        print(f"   CID: {cid}", file=sys.stderr)
                        print(f"   URI: {ipfs_uri}", file=sys.stderr)
                        print(f"   Gateway: https://gateway.pinata.cloud/ipfs/{cid}\n", file=sys.stderr)

                        return ipfs_uri
                    else:
                        error_text = await response.text()
                        logger.error(
                            "pinata_upload_failed",
                            status=response.status,
                            error=error_text
                        )
                        return None

        except ImportError:
            logger.error("aiohttp_not_installed_for_pinata")
            return None

        except Exception as e:
            logger.error(
                "pinata_upload_error",
                error=str(e),
                exc_info=True
            )
            return None

    async def _upload_file_to_pinata(
        self,
        file_path: str,
        custom_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload file to Pinata cloud pinning service

        Args:
            file_path: Path to file to upload
            custom_filename: Optional custom filename for IPFS (defaults to actual filename)

        Returns:
            IPFS URI (ipfs://CID) or None if upload fails
        """
        try:
            import aiohttp
            from pathlib import Path

            logger.info("uploading_file_to_pinata", path=file_path)

            # Pinata API endpoint for file uploads
            url = "https://api.pinata.cloud/pinning/pinFileToIPFS"

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.pinata_api_key}"
            }

            # Prepare file for upload
            file_path_obj = Path(file_path)
            # Use custom filename if provided, otherwise use actual filename
            file_name = custom_filename if custom_filename else file_path_obj.name

            # Upload to Pinata
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    form_data = aiohttp.FormData()
                    form_data.add_field('file', f, filename=file_name)

                    # Optional: Add metadata
                    pinata_metadata = {
                        "name": file_name
                    }
                    form_data.add_field('pinataMetadata', json.dumps(pinata_metadata))

                    async with session.post(url, data=form_data, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            cid = result["IpfsHash"]

                            logger.info(
                                "file_uploaded_to_pinata",
                                cid=cid,
                                file=file_name
                            )

                            ipfs_uri = f"ipfs://{cid}"
                            self.last_error = None  # Clear any previous error

                            import sys
                            print(f"\n📤 File uploaded to Pinata!", file=sys.stderr)
                            print(f"   File: {file_name}", file=sys.stderr)
                            print(f"   CID: {cid}", file=sys.stderr)
                            print(f"   URI: {ipfs_uri}", file=sys.stderr)
                            print(f"   Gateway: https://gateway.pinata.cloud/ipfs/{cid}\n", file=sys.stderr)

                            return ipfs_uri
                        else:
                            error_text = await response.text()
                            # Store detailed error for user feedback
                            if response.status == 401:
                                self.last_error = "Pinata authentication failed. Your JWT may have expired or lack pinning permissions."
                            elif response.status == 403:
                                self.last_error = "Pinata access forbidden. Ensure your JWT has 'pinFileToIPFS' permission enabled."
                            elif response.status == 429:
                                self.last_error = "Pinata rate limit exceeded. Please wait and try again."
                            else:
                                self.last_error = f"Pinata error ({response.status}): {error_text[:200]}"
                            logger.error(
                                "pinata_file_upload_failed",
                                status=response.status,
                                error=error_text,
                                file=file_name
                            )
                            return None

        except ImportError:
            self.last_error = "aiohttp library not installed. Please reinstall the application."
            logger.error("aiohttp_not_installed_for_pinata")
            return None

        except Exception as e:
            self.last_error = f"Upload error: {str(e)}"
            logger.error(
                "pinata_file_upload_error",
                error=str(e),
                file=file_path,
                exc_info=True
            )
            return None

    async def upload_file(
        self,
        file_path: str,
        pin: bool = True,
        custom_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload file to IPFS

        Uses Pinata cloud if configured, otherwise uses local IPFS node.

        Args:
            file_path: Path to file
            pin: Whether to pin the content
            custom_filename: Optional custom filename for IPFS (Pinata only)

        Returns:
            IPFS URI (ipfs://CID) or None if upload fails
        """
        # Try Pinata first if configured
        if self.use_pinata:
            ipfs_uri = await self._upload_file_to_pinata(file_path, custom_filename=custom_filename)
            if ipfs_uri:
                return ipfs_uri

            logger.warning("pinata_file_upload_failed_trying_local")

        # Fallback to local IPFS node
        try:
            if not self.client:
                connected = self.connect()
                if not connected:
                    return None

            logger.info("uploading_file_to_ipfs", path=file_path)

            # Upload file
            result = self.client.add(file_path)
            cid = result['Hash']

            logger.info("file_uploaded_to_ipfs", cid=cid)

            # Pin if requested
            if pin:
                try:
                    self.client.pin.add(cid)
                    logger.debug("file_pinned", cid=cid)
                except Exception as e:
                    logger.warning("ipfs_pin_failed", error=str(e))

            return f"ipfs://{cid}"

        except Exception as e:
            logger.error("ipfs_file_upload_failed", error=str(e))
            return None

    def get_gateway_url(self, ipfs_uri: str, gateway: str = "https://ipfs.io") -> str:
        """
        Convert IPFS URI to HTTP gateway URL

        Args:
            ipfs_uri: IPFS URI (ipfs://CID)
            gateway: Gateway base URL

        Returns:
            HTTP gateway URL
        """
        if ipfs_uri.startswith("ipfs://"):
            cid = ipfs_uri[7:]  # Remove ipfs:// prefix
            return f"{gateway}/ipfs/{cid}"

        return ipfs_uri

    def is_available(self) -> bool:
        """
        Check if IPFS is available

        Returns:
            True if IPFS node is reachable
        """
        if self.client:
            try:
                self.client.version()
                return True
            except:
                return False

        return self.connect()


# Utility function for quick IPFS uploads
async def upload_to_ipfs(
    bcmr_metadata: Dict[str, Any],
    ipfs_api: str = "/ip4/127.0.0.1/tcp/5001"
) -> Optional[str]:
    """
    Quick utility to upload BCMR to IPFS

    Args:
        bcmr_metadata: BCMR metadata dict
        ipfs_api: IPFS API multiaddr

    Returns:
        IPFS URI or None
    """
    uploader = IPFSUploader(ipfs_api=ipfs_api)
    return await uploader.upload_bcmr(bcmr_metadata)
