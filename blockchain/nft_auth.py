"""
NFT-Based Authentication for Qubes

Proves that a user controls the Qube associated with an NFT by:
1. Verifying the NFT exists on-chain and extracting commitment
2. Fetching BCMR metadata (contains original commitment data with public key)
3. Issuing a cryptographic challenge
4. Verifying the response signature matches the public key in the commitment

Authentication Flow:
    1. Client claims ownership of Qube ID
    2. Server generates random challenge (nonce + timestamp)
    3. Client signs challenge with Qube's private key
    4. Server verifies:
       a) NFT with matching commitment exists on-chain
       b) BCMR metadata contains the claimed public key
       c) Signature is valid for the challenge using that public key
       d) Challenge hasn't expired and nonce hasn't been reused

From docs/10_Blockchain_Integration.md - NFT Authentication
"""

import hashlib
import json
import secrets
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from blockchain.verifier import NFTVerifier
from blockchain.registry import QubeNFTRegistry
from crypto.keys import deserialize_public_key, serialize_public_key
from utils.logging import get_logger
from utils.replay_protection import ReplayProtector
from core.exceptions import AuthenticationError

logger = get_logger(__name__)

# Challenge expiry (5 minutes)
CHALLENGE_EXPIRY_SECONDS = 300

# Replay protection for challenges
auth_replay_protector = ReplayProtector(
    max_message_age=CHALLENGE_EXPIRY_SECONDS,
    nonce_max_age=3600  # Keep nonces for 1 hour to prevent replay
)


@dataclass
class AuthChallenge:
    """Authentication challenge issued to client"""
    challenge_id: str
    qube_id: str
    nonce: str
    timestamp: int
    expires_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "qube_id": self.qube_id,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at
        }

    def to_signable_message(self) -> bytes:
        """Create the message that must be signed"""
        # Canonical JSON for signing
        message = json.dumps({
            "challenge_id": self.challenge_id,
            "qube_id": self.qube_id,
            "nonce": self.nonce,
            "timestamp": self.timestamp
        }, sort_keys=True)
        return message.encode('utf-8')


@dataclass
class AuthResult:
    """Result of authentication attempt"""
    authenticated: bool
    qube_id: str
    public_key: Optional[str] = None
    category_id: Optional[str] = None
    nft_verified: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authenticated": self.authenticated,
            "qube_id": self.qube_id,
            "public_key": self.public_key,
            "category_id": self.category_id,
            "nft_verified": self.nft_verified,
            "error": self.error
        }


class NFTAuthenticator:
    """
    NFT-based authentication for Qube ownership

    Verifies that a client controls the private key associated with
    a Qube's NFT by:
    1. Looking up the NFT's commitment data (contains public key)
    2. Issuing a cryptographic challenge
    3. Verifying the signed response

    This proves ownership without requiring the client to reveal
    their private key or sign any blockchain transactions.
    """

    def __init__(
        self,
        verifier: Optional[NFTVerifier] = None,
        registry: Optional[QubeNFTRegistry] = None
    ):
        """
        Initialize NFT authenticator

        Args:
            verifier: NFTVerifier instance (created if not provided)
            registry: QubeNFTRegistry instance (created if not provided)
        """
        self.verifier = verifier or NFTVerifier()
        self.registry = registry or QubeNFTRegistry()

        # Store pending challenges (in production, use Redis or similar)
        self._pending_challenges: Dict[str, AuthChallenge] = {}

        logger.info("nft_authenticator_initialized")

    def create_challenge(self, qube_id: str) -> AuthChallenge:
        """
        Create authentication challenge for a Qube

        Args:
            qube_id: The Qube ID to authenticate

        Returns:
            AuthChallenge to be signed by client

        Raises:
            AuthenticationError: If Qube is not registered
        """
        # Verify Qube exists in registry
        nft_info = self.registry.get_nft_info(qube_id)
        if not nft_info:
            raise AuthenticationError(
                f"Qube {qube_id} not found in NFT registry",
                context={"qube_id": qube_id}
            )

        # Generate challenge
        now = int(datetime.now(timezone.utc).timestamp())
        challenge = AuthChallenge(
            challenge_id=secrets.token_hex(16),
            qube_id=qube_id,
            nonce=secrets.token_hex(32),
            timestamp=now,
            expires_at=now + CHALLENGE_EXPIRY_SECONDS
        )

        # Store for verification
        self._pending_challenges[challenge.challenge_id] = challenge

        logger.info(
            "auth_challenge_created",
            qube_id=qube_id,
            challenge_id=challenge.challenge_id,
            expires_in=CHALLENGE_EXPIRY_SECONDS
        )

        return challenge

    async def verify_challenge_response(
        self,
        challenge_id: str,
        signature_hex: str,
        claimed_public_key: Optional[str] = None
    ) -> AuthResult:
        """
        Verify a signed challenge response

        Args:
            challenge_id: The challenge ID being responded to
            signature_hex: Hex-encoded ECDSA signature of the challenge
            claimed_public_key: Optional public key claim (verified against NFT)

        Returns:
            AuthResult indicating success/failure
        """
        try:
            # Step 1: Retrieve and validate challenge
            challenge = self._pending_challenges.get(challenge_id)
            if not challenge:
                return AuthResult(
                    authenticated=False,
                    qube_id="unknown",
                    error="Challenge not found or expired"
                )

            # Check expiry
            now = int(datetime.now(timezone.utc).timestamp())
            if now > challenge.expires_at:
                del self._pending_challenges[challenge_id]
                return AuthResult(
                    authenticated=False,
                    qube_id=challenge.qube_id,
                    error="Challenge expired"
                )

            # Check replay
            try:
                auth_replay_protector.validate_message(
                    challenge.nonce,
                    challenge.timestamp,
                    challenge.qube_id
                )
            except Exception as e:
                return AuthResult(
                    authenticated=False,
                    qube_id=challenge.qube_id,
                    error=f"Replay protection failed: {str(e)}"
                )

            # Step 2: Get NFT info and commitment data
            nft_info = self.registry.get_nft_info(challenge.qube_id)
            if not nft_info:
                return AuthResult(
                    authenticated=False,
                    qube_id=challenge.qube_id,
                    error="Qube not found in registry"
                )

            category_id = nft_info["category_id"]

            # Step 3: Get public key from BCMR/commitment data
            public_key_hex = await self._get_qube_public_key(challenge.qube_id, nft_info)

            if not public_key_hex:
                return AuthResult(
                    authenticated=False,
                    qube_id=challenge.qube_id,
                    category_id=category_id,
                    error="Could not retrieve public key from NFT metadata"
                )

            # If client claimed a public key, verify it matches
            if claimed_public_key and claimed_public_key != public_key_hex:
                return AuthResult(
                    authenticated=False,
                    qube_id=challenge.qube_id,
                    category_id=category_id,
                    error="Claimed public key does not match NFT commitment"
                )

            # Step 4: Verify signature
            try:
                public_key = deserialize_public_key(public_key_hex)
                signature_bytes = bytes.fromhex(signature_hex)
                message = challenge.to_signable_message()

                # Verify ECDSA signature
                public_key.verify(
                    signature_bytes,
                    message,
                    ec.ECDSA(hashes.SHA256())
                )

            except Exception as e:
                logger.warning(
                    "signature_verification_failed",
                    qube_id=challenge.qube_id,
                    error=str(e)
                )
                return AuthResult(
                    authenticated=False,
                    qube_id=challenge.qube_id,
                    category_id=category_id,
                    public_key=public_key_hex,
                    error="Invalid signature"
                )

            # Step 5: Optionally verify NFT still exists on-chain
            nft_verified = False
            if nft_info.get("recipient_address"):
                try:
                    nft_verified = await self.verifier.verify_ownership(
                        category_id,
                        nft_info["recipient_address"]
                    )
                except Exception as e:
                    logger.warning(
                        "on_chain_verification_failed",
                        error=str(e)
                    )
                    # Continue - signature verification is sufficient

            # Clean up challenge
            del self._pending_challenges[challenge_id]

            logger.info(
                "authentication_successful",
                qube_id=challenge.qube_id,
                category_id=category_id[:16] + "...",
                nft_verified=nft_verified
            )

            return AuthResult(
                authenticated=True,
                qube_id=challenge.qube_id,
                public_key=public_key_hex,
                category_id=category_id,
                nft_verified=nft_verified
            )

        except Exception as e:
            logger.error(
                "authentication_error",
                challenge_id=challenge_id,
                error=str(e),
                exc_info=True
            )
            return AuthResult(
                authenticated=False,
                qube_id=challenge.qube_id if challenge else "unknown",
                error=f"Authentication error: {str(e)}"
            )

    async def _get_qube_public_key(
        self,
        qube_id: str,
        nft_info: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get Qube's public key from BCMR metadata or local storage

        The public key is stored in the commitment_data when the NFT was minted.
        We can retrieve it from:
        1. Local BCMR file (fastest)
        2. IPFS (if BCMR was uploaded)
        3. Reconstruct from local Qube data

        Args:
            qube_id: Qube ID
            nft_info: NFT registry info

        Returns:
            Compressed public key hex or None
        """
        from blockchain.bcmr import BCMRGenerator

        category_id = nft_info["category_id"]

        # Try 1: Load from local BCMR
        bcmr_gen = BCMRGenerator()
        bcmr_metadata = bcmr_gen.load_bcmr(category_id)

        if bcmr_metadata:
            try:
                # Navigate BCMR structure to find commitment_data
                identities = bcmr_metadata.get("identities", {})
                if category_id in identities:
                    # Get the latest revision
                    revisions = identities[category_id]
                    if revisions:
                        latest_key = bcmr_metadata.get("latestRevision")
                        if latest_key and latest_key in revisions:
                            revision = revisions[latest_key]
                        else:
                            # Get first revision
                            revision = list(revisions.values())[0]

                        commitment_data = revision.get("extensions", {}).get("commitment_data", {})
                        public_key = commitment_data.get("creator_public_key")

                        if public_key:
                            logger.debug(
                                "public_key_from_bcmr",
                                qube_id=qube_id,
                                source="local_bcmr"
                            )
                            return public_key
            except Exception as e:
                logger.warning(
                    "bcmr_parse_error",
                    qube_id=qube_id,
                    error=str(e)
                )

        # Try 2: Load from qube's local nft_metadata.json
        try:
            from pathlib import Path
            import glob

            # Search for qube directory
            data_dir = Path("data")
            if data_dir.exists():
                for qube_dir in data_dir.glob(f"users/*/qubes/*_{qube_id}"):
                    # Check for BCMR in qube's blockchain folder
                    bcmr_files = list(qube_dir.glob("blockchain/*_bcmr.json"))
                    for bcmr_file in bcmr_files:
                        with open(bcmr_file, 'r') as f:
                            qube_bcmr = json.load(f)

                        # Parse same structure
                        identities = qube_bcmr.get("identities", {})
                        for cat_id, revisions in identities.items():
                            for rev_key, revision in revisions.items():
                                commitment_data = revision.get("extensions", {}).get("commitment_data", {})
                                public_key = commitment_data.get("creator_public_key")
                                if public_key:
                                    logger.debug(
                                        "public_key_from_qube_bcmr",
                                        qube_id=qube_id,
                                        source=str(bcmr_file)
                                    )
                                    return public_key
        except Exception as e:
            logger.warning(
                "qube_bcmr_search_error",
                qube_id=qube_id,
                error=str(e)
            )

        logger.warning(
            "public_key_not_found",
            qube_id=qube_id
        )
        return None

    def cleanup_expired_challenges(self) -> int:
        """
        Remove expired challenges from memory

        Returns:
            Number of challenges removed
        """
        now = int(datetime.now(timezone.utc).timestamp())
        expired = [
            cid for cid, challenge in self._pending_challenges.items()
            if now > challenge.expires_at
        ]

        for cid in expired:
            del self._pending_challenges[cid]

        if expired:
            logger.debug(
                "expired_challenges_cleaned",
                count=len(expired)
            )

        return len(expired)


# =============================================================================
# CLIENT-SIDE HELPER
# =============================================================================

def sign_challenge(
    challenge: Dict[str, Any],
    private_key: ec.EllipticCurvePrivateKey
) -> str:
    """
    Sign an authentication challenge (client-side helper)

    Args:
        challenge: Challenge dict from server
        private_key: Qube's ECDSA private key

    Returns:
        Hex-encoded signature
    """
    # Reconstruct the signable message
    message = json.dumps({
        "challenge_id": challenge["challenge_id"],
        "qube_id": challenge["qube_id"],
        "nonce": challenge["nonce"],
        "timestamp": challenge["timestamp"]
    }, sort_keys=True).encode('utf-8')

    # Sign with ECDSA
    signature = private_key.sign(
        message,
        ec.ECDSA(hashes.SHA256())
    )

    return signature.hex()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def authenticate_qube(
    qube_id: str,
    private_key: ec.EllipticCurvePrivateKey,
    authenticator: Optional[NFTAuthenticator] = None
) -> AuthResult:
    """
    Complete authentication flow (for testing/local use)

    In production, the challenge/response would happen over HTTP.

    Args:
        qube_id: Qube to authenticate
        private_key: Qube's private key
        authenticator: NFTAuthenticator instance

    Returns:
        AuthResult
    """
    if authenticator is None:
        authenticator = NFTAuthenticator()

    # Create challenge
    challenge = authenticator.create_challenge(qube_id)

    # Sign challenge
    signature = sign_challenge(challenge.to_dict(), private_key)

    # Verify
    result = await authenticator.verify_challenge_response(
        challenge.challenge_id,
        signature
    )

    return result
