"""
Qube Minting API Client

Client for the qube.cash minting service API.
Handles registration, payment submission, and status polling.
"""

import asyncio
import aiohttp
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass

from utils.logging import get_logger

logger = get_logger(__name__)


# API Configuration
API_BASE_URL = "https://qube.cash/api"
API_TIMEOUT = 30  # seconds


@dataclass
class PaymentInfo:
    """Payment details for minting fee"""
    address: str
    amount_bch: float
    amount_satoshis: int
    payment_uri: str
    qr_data: str
    op_return_data: str = ""
    op_return_hex: str = ""


@dataclass
class RegistrationResult:
    """Result of qube registration"""
    registration_id: str
    status: str
    payment: PaymentInfo
    websocket_url: str
    expires_at: datetime
    expires_in_seconds: int


@dataclass
class MintingResult:
    """Result of successful NFT minting"""
    registration_id: str
    category_id: str
    mint_txid: str
    bcmr_ipfs_cid: Optional[str]
    avatar_ipfs_cid: Optional[str]
    commitment: Optional[str]
    explorer_url: Optional[str]


class MintingAPIError(Exception):
    """Error from the minting API"""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class MintingAPIClient:
    """
    Client for the qube.cash minting API

    Usage:
        async with MintingAPIClient() as client:
            # Register qube
            result = await client.register_qube(...)

            # User pays...

            # Submit payment
            await client.submit_payment(result.registration_id, txid)

            # Or poll status
            status = await client.get_status(result.registration_id)
    """

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = API_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_session(self):
        """Ensure we have an active session"""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        params: dict = None
    ) -> dict:
        """Make an API request"""
        await self._ensure_session()

        url = f"{self.base_url}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                json=data,
                params=params
            ) as response:
                response_data = await response.json()

                if response.status >= 400:
                    # Handle FastAPI validation errors (detail is a list)
                    detail = response_data.get("detail") if isinstance(response_data, dict) else response_data
                    if isinstance(detail, list) and len(detail) > 0:
                        # Extract first validation error message
                        first_error = detail[0]
                        if isinstance(first_error, dict):
                            error_detail = first_error.get("msg", str(first_error))
                        else:
                            error_detail = str(first_error)
                    elif isinstance(detail, str):
                        error_detail = detail
                    else:
                        error_detail = str(response_data)
                    raise MintingAPIError(
                        f"API error: {error_detail}",
                        status_code=response.status,
                        details=response_data
                    )

                return response_data

        except aiohttp.ClientError as e:
            raise MintingAPIError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise MintingAPIError(f"Invalid JSON response: {str(e)}")

    async def get_fee(self) -> Dict[str, Any]:
        """
        Get current minting fee

        Returns:
            {
                "amount_bch": 0.0001,
                "amount_satoshis": 10000,
                "payment_address": "bitcoincash:qq..."
            }
        """
        logger.info("getting_minting_fee")
        return await self._request("GET", "/v2/fee")

    async def register_qube(
        self,
        qube_id: str,
        qube_name: str,
        genesis_block_hash: str,
        public_key: str,
        recipient_address: str,
        creator: str,
        birth_timestamp: int,
        genesis_prompt: Optional[str] = None,
        ai_model: Optional[str] = None,
        avatar_path: Optional[Path] = None,
        avatar_base64: Optional[str] = None,
        avatar_format: str = "png",
        avatar_source: str = "generated",
        avatar_ipfs_cid: Optional[str] = None,
        favorite_color: Optional[str] = None
    ) -> RegistrationResult:
        """
        Register a Qube for minting

        Args:
            qube_id: 8-character hex Qube ID
            qube_name: Name of the Qube
            genesis_block_hash: Hash of the genesis block
            public_key: Qube's compressed public key (66 chars)
            recipient_address: BCH address to receive the NFT
            creator: Creator username
            birth_timestamp: Unix timestamp of creation
            genesis_prompt: Optional genesis prompt
            ai_model: Optional AI model name
            avatar_path: Path to avatar image file
            avatar_base64: Base64-encoded avatar (alternative to path)
            avatar_format: Image format (png, jpeg, etc.)
            avatar_source: Source of avatar (generated, uploaded, default)
            avatar_ipfs_cid: Pre-uploaded avatar IPFS CID (if client already uploaded)
            favorite_color: Hex color code

        Returns:
            RegistrationResult with payment details
        """
        logger.info(
            "registering_qube_for_minting",
            qube_id=qube_id,
            qube_name=qube_name,
            recipient=recipient_address[:20] + "..."
        )

        # Build request data
        data = {
            "qube_id": qube_id,
            "qube_name": qube_name,
            "genesis_block_hash": genesis_block_hash,
            "public_key": public_key,
            "recipient_address": recipient_address,
            "creator": creator,
            "birth_timestamp": birth_timestamp
        }

        if genesis_prompt:
            data["genesis_prompt"] = genesis_prompt
        if ai_model:
            data["ai_model"] = ai_model
        if favorite_color:
            data["favorite_color"] = favorite_color

        # Handle avatar data
        if avatar_path and Path(avatar_path).exists():
            with open(avatar_path, "rb") as f:
                avatar_bytes = f.read()
            avatar_base64 = base64.b64encode(avatar_bytes).decode("utf-8")
            # Detect format from extension
            avatar_format = Path(avatar_path).suffix.lstrip(".").lower()
            if avatar_format == "jpg":
                avatar_format = "jpeg"

        if avatar_base64:
            data["avatar_data"] = {
                "base64_data": avatar_base64,
                "file_format": avatar_format,
                "source": avatar_source
            }
            # Include pre-uploaded IPFS CID if provided
            if avatar_ipfs_cid:
                data["avatar_data"]["ipfs_cid"] = avatar_ipfs_cid

        # Make request
        response = await self._request("POST", "/v2/register", data=data)

        # Parse response
        payment_data = response["payment"]
        payment = PaymentInfo(
            address=payment_data["address"],
            amount_bch=payment_data["amount_bch"],
            amount_satoshis=payment_data["amount_satoshis"],
            payment_uri=payment_data["payment_uri"],
            qr_data=payment_data["qr_data"],
            op_return_data=payment_data.get("op_return_data", ""),
            op_return_hex=payment_data.get("op_return_hex", "")
        )

        # Parse expiry time
        expires_at_str = response["expires_at"]
        if isinstance(expires_at_str, str):
            # Handle ISO format with or without timezone
            expires_at_str = expires_at_str.replace("Z", "+00:00")
            expires_at = datetime.fromisoformat(expires_at_str)
        else:
            expires_at = datetime.now(timezone.utc)

        result = RegistrationResult(
            registration_id=response["registration_id"],
            status=response["status"],
            payment=payment,
            websocket_url=response["websocket_url"],
            expires_at=expires_at,
            expires_in_seconds=response["expires_in_seconds"]
        )

        logger.info(
            "qube_registered_for_minting",
            registration_id=result.registration_id,
            payment_address=payment.address,
            amount_bch=payment.amount_bch
        )

        return result

    async def submit_payment(
        self,
        registration_id: str,
        txid: str
    ) -> Dict[str, Any]:
        """
        Submit transaction ID after payment

        Args:
            registration_id: Registration ID from register step
            txid: Transaction ID of the payment

        Returns:
            {
                "registration_id": "...",
                "status": "processing",
                "message": "Payment verified! NFT minting in progress..."
            }
        """
        logger.info(
            "submitting_payment",
            registration_id=registration_id,
            txid=txid[:16] + "..."
        )

        data = {
            "registration_id": registration_id,
            "txid": txid
        }

        response = await self._request("POST", "/v2/submit-payment", data=data)

        logger.info(
            "payment_submitted",
            registration_id=registration_id,
            status=response.get("status")
        )

        return response

    async def get_status(self, registration_id: str) -> Dict[str, Any]:
        """
        Get registration status

        Args:
            registration_id: Registration ID

        Returns:
            Status object with fields:
            - registration_id
            - qube_id
            - status: pending, paid, minting, complete, failed, expired
            - payment_txid (if paid)
            - category_id (if complete)
            - mint_txid (if complete)
            - bcmr_ipfs_cid (if complete)
            - error_message (if failed)
        """
        return await self._request("GET", f"/v2/status/{registration_id}")

    async def cancel_registration(self, registration_id: str) -> Dict[str, Any]:
        """
        Cancel a pending registration

        Only works if payment has not been received.

        Args:
            registration_id: Registration ID to cancel

        Returns:
            {"status": "cancelled", "registration_id": "..."}
        """
        logger.info("cancelling_registration", registration_id=registration_id)
        return await self._request("DELETE", f"/v2/register/{registration_id}")

    async def unregister_qube(self, qube_id: str) -> Dict[str, Any]:
        """
        Unregister a Qube from the BCMR registry

        Called when a user deletes their Qube. Removes the Qube
        from the public BCMR registry on qube.cash.

        Args:
            qube_id: The Qube ID to unregister (full 64-char or short 8-char)

        Returns:
            {"status": "removed", "qube_id": "..."}
        """
        logger.info("unregistering_qube", qube_id=qube_id[:16] + "...")
        return await self._request("DELETE", f"/v2/qube/{qube_id}")

    async def wait_for_completion(
        self,
        registration_id: str,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
        on_status_change: Optional[Callable[[str, Dict], None]] = None
    ) -> MintingResult:
        """
        Poll for minting completion

        Args:
            registration_id: Registration ID to monitor
            poll_interval: Seconds between polls
            timeout: Maximum time to wait
            on_status_change: Optional callback for status updates

        Returns:
            MintingResult on success

        Raises:
            MintingAPIError on failure or timeout
        """
        logger.info(
            "waiting_for_minting_completion",
            registration_id=registration_id,
            timeout=timeout
        )

        start_time = asyncio.get_event_loop().time()
        last_status = None

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise MintingAPIError(
                    f"Timeout waiting for minting completion after {timeout}s"
                )

            status = await self.get_status(registration_id)
            current_status = status.get("status")

            # Notify on status change
            if current_status != last_status:
                last_status = current_status
                if on_status_change:
                    try:
                        on_status_change(current_status, status)
                    except Exception as e:
                        logger.warning("status_callback_error", error=str(e))

            if current_status == "complete":
                logger.info(
                    "minting_complete",
                    registration_id=registration_id,
                    mint_txid=status.get("mint_txid")
                )
                return MintingResult(
                    registration_id=registration_id,
                    category_id=status.get("category_id"),
                    mint_txid=status.get("mint_txid"),
                    bcmr_ipfs_cid=status.get("bcmr_ipfs_cid"),
                    avatar_ipfs_cid=status.get("avatar_ipfs_cid"),
                    commitment=status.get("commitment"),
                    explorer_url=None  # Can be constructed from txid
                )

            if current_status == "failed":
                error_msg = status.get("error_message", "Unknown error")
                raise MintingAPIError(f"Minting failed: {error_msg}")

            if current_status == "expired":
                raise MintingAPIError("Registration expired before payment")

            await asyncio.sleep(poll_interval)


class WebSocketClient:
    """
    WebSocket client for real-time minting updates

    Usage:
        async with WebSocketClient(websocket_url) as ws:
            async for event in ws.events():
                print(event)
    """

    def __init__(self, websocket_url: str):
        self.url = websocket_url
        self._ws = None
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self.url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()

    async def events(self):
        """Async generator yielding events from the WebSocket"""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    yield data
                except json.JSONDecodeError:
                    continue
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                break

    async def send_ping(self):
        """Send ping to keep connection alive"""
        if self._ws:
            await self._ws.send_str("ping")


# Convenience function for one-shot API calls
async def get_minting_fee() -> Dict[str, Any]:
    """Get current minting fee (convenience function)"""
    async with MintingAPIClient() as client:
        return await client.get_fee()
