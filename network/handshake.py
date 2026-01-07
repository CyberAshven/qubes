"""
Authentication & Handshake Protocol

Implements NFT-based authentication and secure handshake for Qube connections.
From docs/08_P2P_Network_Discovery.md Section 5.3
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from core.exceptions import NetworkError, AuthenticationError
from network.discovery.resolver import discover_qube
from network.messaging import EncryptedSession
from utils.logging import get_logger
from utils.rate_limiter import RateLimiter
from utils.replay_protection import ReplayProtector
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)

# Rate limiter for handshake attempts (5 per hour per peer)
handshake_rate_limiter = RateLimiter(max_requests=5, window_seconds=3600)

# Replay protection for authentication messages
handshake_replay_protector = ReplayProtector(max_message_age=300, nonce_max_age=3600)


class QubeHandshake:
    """
    NFT-based authentication and handshake protocol
    From docs Section 5.3

    Establishes secure authenticated connections between Qubes using:
    - NFT ownership verification
    - ECDSA signature verification
    - Trust score evaluation
    - ECDH key exchange for encrypted sessions
    """

    def __init__(
        self,
        qube_id: str,
        private_key: ec.EllipticCurvePrivateKey,
        public_key: ec.EllipticCurvePublicKey,
        nft_contract: Optional[str] = None,
        nft_token_id: Optional[int] = None,
        home_blockchain: str = "ethereum",
        default_trust_level: float = 0.5
    ):
        """
        Initialize handshake handler

        Args:
            qube_id: This Qube's ID
            private_key: ECDSA private key for signing
            public_key: ECDSA public key
            nft_contract: NFT contract address (Phase 4)
            nft_token_id: NFT token ID (Phase 4)
            home_blockchain: Blockchain network name
            default_trust_level: Default trust score for new Qubes
        """
        self.qube_id = qube_id
        self.private_key = private_key
        self.public_key = public_key
        self.nft_contract = nft_contract
        self.nft_token_id = nft_token_id
        self.home_blockchain = home_blockchain
        self.default_trust_level = default_trust_level

        # Active sessions
        self.active_sessions: Dict[str, EncryptedSession] = {}

        # Relationship cache (will integrate with Phase 5)
        self.relationships: Dict[str, Dict[str, Any]] = {}

        logger.info("handshake_handler_initialized", qube_id=qube_id)

    async def initiate(
        self,
        target_qube_id: str,
        p2p_node,
        target_public_key: ec.EllipticCurvePublicKey
    ) -> Dict[str, Any]:
        """
        Initiate handshake with target Qube
        From docs Section 5.3

        Args:
            target_qube_id: Target Qube ID to connect to
            p2p_node: QubeP2PNode instance
            target_public_key: Target's ECDSA public key

        Returns:
            Handshake result with session, trust score, and relationship info
        """
        try:
            logger.info(
                "initiating_handshake",
                target_qube_id=target_qube_id
            )

            # Step 1: Discover target Qube
            target_address = await discover_qube(target_qube_id, p2p_node)

            if not target_address:
                raise AuthenticationError(
                    f"Target Qube not found: {target_qube_id}",
                    context={"target_qube_id": target_qube_id}
                )

            logger.debug(
                "target_qube_discovered",
                target_qube_id=target_qube_id,
                address=target_address
            )

            # Step 2: Generate authentication request
            nonce = self._generate_nonce()
            nft_proof = await self.get_nft_proof()

            auth_request = {
                "type": "AUTH_REQUEST",
                "from_qube": self.qube_id,
                "public_key": self._serialize_public_key(self.public_key),
                "nft_proof": nft_proof,
                "nonce": nonce,
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }

            # Sign the request
            auth_request["signature"] = self._sign_auth_request(auth_request)

            logger.debug(
                "auth_request_created",
                target_qube_id=target_qube_id,
                nonce=nonce[:8]  # Log partial nonce
            )

            # Step 3: Send authentication request
            # (Simplified - actual sending depends on libp2p API)
            response = await self._send_auth_request(
                target_address,
                auth_request,
                p2p_node
            )

            # Step 4: Verify response signature
            if not self._verify_response_signature(response, target_public_key):
                raise AuthenticationError(
                    "Invalid response signature",
                    context={"target_qube_id": target_qube_id}
                )

            logger.debug("response_signature_verified", target_qube_id=target_qube_id)

            # Step 5: Verify NFT ownership on blockchain
            if not await self._verify_nft_ownership(response.get("nft_proof", {})):
                logger.warning(
                    "nft_verification_failed",
                    target_qube_id=target_qube_id
                )
                # Note: NFT verification is optional until Phase 4
                # We continue but note the verification status

            # Step 6: Check existing relationship and trust score
            relationship = self._get_relationship(target_qube_id)
            if relationship:
                trust_score = relationship.get("overall_trust_score", self.default_trust_level)
                logger.debug(
                    "existing_relationship_found",
                    target_qube_id=target_qube_id,
                    trust_score=trust_score
                )
            else:
                trust_score = self.default_trust_level
                logger.debug(
                    "new_relationship",
                    target_qube_id=target_qube_id,
                    default_trust=trust_score
                )

            # Step 7: Query third-party reputation (Phase 5)
            third_party_rep = await self._query_reputation(target_qube_id)

            # Step 8: Establish encrypted channel using ECDH
            shared_secret = self.private_key.exchange(
                ec.ECDH(),
                target_public_key
            )

            # Derive encryption key using HKDF
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF

            encryption_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"qubes-handshake-session"
            ).derive(shared_secret)

            session = EncryptedSession(encryption_key)

            # Store active session
            self.active_sessions[target_qube_id] = session

            logger.info(
                "handshake_complete",
                target_qube_id=target_qube_id,
                trust_score=trust_score
            )

            MetricsRecorder.record_p2p_event("handshake_success", self.qube_id)

            # Step 9: Return interaction context
            return {
                "session": session,
                "trust_score": trust_score,
                "reputation": third_party_rep,
                "relationship": relationship,
                "target_qube_id": target_qube_id,
                "established_at": datetime.now(timezone.utc).isoformat()
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(
                "handshake_failed",
                target_qube_id=target_qube_id,
                error=str(e),
                exc_info=True
            )
            MetricsRecorder.record_p2p_event("handshake_failed", self.qube_id)
            raise AuthenticationError(
                f"Handshake failed: {str(e)}",
                context={"target_qube_id": target_qube_id},
                cause=e
            )

    async def handle_incoming_handshake(
        self,
        auth_request: Dict[str, Any],
        sender_public_key: ec.EllipticCurvePublicKey
    ) -> Dict[str, Any]:
        """
        Handle incoming handshake request from another Qube

        SECURITY: Includes rate limiting and replay protection

        Args:
            auth_request: Authentication request data
            sender_public_key: Sender's ECDSA public key

        Returns:
            Authentication response
        """
        try:
            sender_qube_id = auth_request.get("from_qube")

            logger.info(
                "handling_incoming_handshake",
                sender_qube_id=sender_qube_id
            )

            # SECURITY FIX (HIGH-01): Rate limiting
            if not handshake_rate_limiter.check(sender_qube_id):
                logger.warning(
                    "handshake_rate_limited",
                    sender_qube_id=sender_qube_id
                )
                raise AuthenticationError(
                    "Rate limit exceeded. Too many handshake attempts.",
                    context={"sender_qube_id": sender_qube_id}
                )

            # SECURITY FIX (HIGH-03): Replay protection
            nonce = auth_request.get("nonce")
            timestamp = auth_request.get("timestamp")
            if nonce and timestamp:
                try:
                    handshake_replay_protector.validate_message(
                        nonce, timestamp, sender_qube_id
                    )
                except Exception as e:
                    logger.warning(
                        "handshake_replay_or_expired",
                        sender_qube_id=sender_qube_id,
                        error=str(e)
                    )
                    raise AuthenticationError(
                        f"Message validation failed: {str(e)}",
                        context={"sender_qube_id": sender_qube_id},
                        cause=e
                    )

            # Verify request signature
            if not self._verify_request_signature(auth_request, sender_public_key):
                raise AuthenticationError(
                    "Invalid request signature",
                    context={"sender_qube_id": sender_qube_id}
                )

            # Verify NFT proof (if provided)
            nft_proof = auth_request.get("nft_proof", {})
            nft_verified = await self._verify_nft_ownership(nft_proof)

            # Check relationship and trust
            relationship = self._get_relationship(sender_qube_id)
            trust_score = relationship.get("overall_trust_score", self.default_trust_level) if relationship else self.default_trust_level

            # Generate response
            response_nonce = self._generate_nonce()
            nft_proof_response = await self.get_nft_proof()

            response = {
                "type": "AUTH_RESPONSE",
                "from_qube": self.qube_id,
                "to_qube": sender_qube_id,
                "public_key": self._serialize_public_key(self.public_key),
                "nft_proof": nft_proof_response,
                "nonce": response_nonce,
                "original_nonce": auth_request.get("nonce"),
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                "accepted": True
            }

            # Sign response
            response["signature"] = self._sign_auth_response(response)

            # Establish encrypted session
            shared_secret = self.private_key.exchange(
                ec.ECDH(),
                sender_public_key
            )

            from cryptography.hazmat.primitives.kdf.hkdf import HKDF

            encryption_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"qubes-handshake-session"
            ).derive(shared_secret)

            session = EncryptedSession(encryption_key)
            self.active_sessions[sender_qube_id] = session

            logger.info(
                "incoming_handshake_accepted",
                sender_qube_id=sender_qube_id,
                trust_score=trust_score,
                nft_verified=nft_verified
            )

            MetricsRecorder.record_p2p_event("handshake_accepted", self.qube_id)

            return response

        except Exception as e:
            logger.error(
                "incoming_handshake_failed",
                error=str(e),
                exc_info=True
            )
            MetricsRecorder.record_p2p_event("handshake_rejected", self.qube_id)
            raise

    async def get_nft_proof(self) -> Dict[str, Any]:
        """
        Generate NFT ownership proof for BCH CashTokens

        Returns proof containing:
        - Qube ID
        - Public key (from Qube's keypair)
        - Category ID (if NFT has been minted)
        - Signed timestamp (proves key ownership)

        Returns:
            NFT proof dictionary
        """
        try:
            from crypto.keys import serialize_public_key
            from blockchain.registry import QubeNFTRegistry

            # Get public key from our keypair
            public_key_hex = serialize_public_key(self.public_key)

            # Check if this Qube has an NFT
            registry = QubeNFTRegistry()
            nft_info = registry.get_nft_info(self.qube_id)

            timestamp = int(datetime.now(timezone.utc).timestamp())

            # Build proof
            proof = {
                "qube_id": self.qube_id,
                "public_key": public_key_hex,
                "timestamp": timestamp,
                "chain": "bitcoincash"
            }

            # Add NFT info if available
            if nft_info:
                proof["category_id"] = nft_info.get("category_id")
                proof["recipient_address"] = nft_info.get("recipient_address")
                proof["mint_txid"] = nft_info.get("mint_txid")
                proof["has_nft"] = True
            else:
                proof["has_nft"] = False

            # Sign the proof to demonstrate key ownership
            proof_data = json.dumps(
                {k: v for k, v in proof.items() if k != "signature"},
                sort_keys=True
            )
            proof["signature"] = self._sign_data(proof_data.encode())

            logger.debug(
                "nft_proof_generated",
                qube_id=self.qube_id,
                has_nft=proof["has_nft"]
            )

            return proof

        except Exception as e:
            logger.error("nft_proof_generation_failed", error=str(e))
            return {
                "qube_id": self.qube_id,
                "has_nft": False,
                "error": str(e)
            }

    async def _verify_nft_ownership(self, nft_proof: Dict[str, Any]) -> bool:
        """
        Verify NFT ownership on blockchain using BCH CashTokens

        Verifies that the claimed public key matches the NFT commitment
        and optionally verifies the NFT still exists on-chain.

        Args:
            nft_proof: NFT proof containing:
                - qube_id: Qube ID
                - public_key: Claimed public key (compressed hex)
                - category_id: CashToken category ID (optional)
                - signature: Signature proving key ownership (optional)

        Returns:
            True if NFT ownership is verified
        """
        try:
            if not nft_proof:
                logger.debug("nft_verification_skipped_no_proof")
                return False

            qube_id = nft_proof.get("qube_id")
            claimed_public_key = nft_proof.get("public_key")

            if not qube_id or not claimed_public_key:
                logger.debug(
                    "nft_verification_skipped_missing_fields",
                    has_qube_id=bool(qube_id),
                    has_public_key=bool(claimed_public_key)
                )
                return False

            # Import NFT authentication module
            from blockchain.nft_auth import NFTAuthenticator
            from blockchain.registry import QubeNFTRegistry

            registry = QubeNFTRegistry()
            nft_info = registry.get_nft_info(qube_id)

            if not nft_info:
                logger.debug(
                    "nft_verification_qube_not_registered",
                    qube_id=qube_id
                )
                return False

            # Get the public key from BCMR/commitment and compare
            authenticator = NFTAuthenticator(registry=registry)
            stored_public_key = await authenticator._get_qube_public_key(qube_id, nft_info)

            if not stored_public_key:
                logger.warning(
                    "nft_verification_no_stored_key",
                    qube_id=qube_id
                )
                return False

            # Verify claimed public key matches stored
            if claimed_public_key != stored_public_key:
                logger.warning(
                    "nft_verification_key_mismatch",
                    qube_id=qube_id,
                    claimed=claimed_public_key[:16] + "...",
                    stored=stored_public_key[:16] + "..."
                )
                return False

            # Optionally verify NFT still exists on-chain
            category_id = nft_info.get("category_id")
            recipient_address = nft_info.get("recipient_address")

            # Validate official Qubes category - reject unofficial agents
            from core.official_category import is_official_qube
            if not is_official_qube(category_id):
                logger.warning(
                    "p2p_handshake_rejected_unofficial",
                    qube_id=qube_id,
                    category_id=category_id[:16] + "..." if category_id else "None",
                    reason="Not official Qubes category"
                )
                return False

            if category_id and recipient_address:
                from blockchain.verifier import NFTVerifier
                verifier = NFTVerifier()
                on_chain_verified = await verifier.verify_ownership(
                    category_id,
                    recipient_address
                )

                if on_chain_verified:
                    logger.info(
                        "nft_ownership_verified",
                        qube_id=qube_id,
                        category_id=category_id[:16] + "..."
                    )
                else:
                    logger.warning(
                        "nft_not_found_on_chain",
                        qube_id=qube_id,
                        category_id=category_id[:16] + "..."
                    )
                    # Still return True - the key matches commitment
                    # NFT may have been transferred but identity is valid

            logger.info(
                "nft_verification_successful",
                qube_id=qube_id
            )
            return True

        except Exception as e:
            logger.error("nft_verification_error", error=str(e), exc_info=True)
            return False

    async def _query_reputation(self, target_qube_id: str) -> Dict[str, Any]:
        """
        Query third-party reputation for target Qube
        Phase 5 implementation

        Args:
            target_qube_id: Target Qube ID

        Returns:
            Reputation data
        """
        try:
            # Phase 5: Implement reputation system
            # For now, return default reputation

            logger.debug("reputation_query_pending_phase5", target_qube_id=target_qube_id)

            return {
                "available": False,
                "reason": "Reputation system not implemented (Phase 5)"
            }

        except Exception as e:
            logger.error("reputation_query_failed", error=str(e))
            return {
                "available": False,
                "error": str(e)
            }

    def _get_relationship(self, qube_id: str) -> Optional[Dict[str, Any]]:
        """
        Get existing relationship with Qube
        Integrates with Phase 5 relationship system

        Args:
            qube_id: Target Qube ID

        Returns:
            Relationship data or None
        """
        return self.relationships.get(qube_id)

    def _generate_nonce(self) -> str:
        """Generate random nonce for authentication"""
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def _sign_data(self, data: bytes) -> str:
        """Sign data with private key"""
        signature = self.private_key.sign(
            data,
            ec.ECDSA(hashes.SHA256())
        )
        import base64
        return base64.b64encode(signature).decode()

    def _sign_auth_request(self, request: Dict[str, Any]) -> str:
        """Sign authentication request"""
        # Remove signature field if present
        request_copy = {k: v for k, v in request.items() if k != "signature"}
        request_data = json.dumps(request_copy, sort_keys=True).encode()
        return self._sign_data(request_data)

    def _sign_auth_response(self, response: Dict[str, Any]) -> str:
        """Sign authentication response"""
        response_copy = {k: v for k, v in response.items() if k != "signature"}
        response_data = json.dumps(response_copy, sort_keys=True).encode()
        return self._sign_data(response_data)

    def _verify_response_signature(
        self,
        response: Dict[str, Any],
        public_key: ec.EllipticCurvePublicKey
    ) -> bool:
        """Verify authentication response signature"""
        try:
            import base64

            signature = response.get("signature")
            if not signature:
                return False

            signature_bytes = base64.b64decode(signature)

            # Reconstruct signed data
            response_copy = {k: v for k, v in response.items() if k != "signature"}
            response_data = json.dumps(response_copy, sort_keys=True).encode()

            # Verify signature
            public_key.verify(
                signature_bytes,
                response_data,
                ec.ECDSA(hashes.SHA256())
            )

            return True

        except Exception as e:
            logger.warning("signature_verification_failed", error=str(e))
            return False

    def _verify_request_signature(
        self,
        request: Dict[str, Any],
        public_key: ec.EllipticCurvePublicKey
    ) -> bool:
        """Verify authentication request signature"""
        try:
            import base64

            signature = request.get("signature")
            if not signature:
                return False

            signature_bytes = base64.b64decode(signature)

            # Reconstruct signed data
            request_copy = {k: v for k, v in request.items() if k != "signature"}
            request_data = json.dumps(request_copy, sort_keys=True).encode()

            # Verify signature
            public_key.verify(
                signature_bytes,
                request_data,
                ec.ECDSA(hashes.SHA256())
            )

            return True

        except Exception as e:
            logger.warning("signature_verification_failed", error=str(e))
            return False

    def _serialize_public_key(self, public_key: ec.EllipticCurvePublicKey) -> str:
        """Serialize public key to string"""
        from cryptography.hazmat.primitives import serialization
        import base64

        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(pem).decode()

    async def _send_auth_request(
        self,
        target_address: str,
        auth_request: Dict[str, Any],
        p2p_node
    ) -> Dict[str, Any]:
        """
        Send authentication request to target
        Simplified implementation - actual sending depends on libp2p API

        Args:
            target_address: Target multiaddr
            auth_request: Authentication request data
            p2p_node: P2P node instance

        Returns:
            Authentication response
        """
        # Mock response for development
        # Phase 3: Implement actual libp2p message sending

        logger.debug(
            "auth_request_sent_mock",
            target_address=target_address
        )

        # Mock successful response
        mock_response = {
            "type": "AUTH_RESPONSE",
            "from_qube": "mock_target",
            "to_qube": self.qube_id,
            "accepted": True,
            "nonce": self._generate_nonce(),
            "original_nonce": auth_request.get("nonce"),
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }

        return mock_response

    def get_session(self, qube_id: str) -> Optional[EncryptedSession]:
        """Get active encrypted session with Qube"""
        return self.active_sessions.get(qube_id)

    def close_session(self, qube_id: str) -> None:
        """Close encrypted session with Qube"""
        if qube_id in self.active_sessions:
            del self.active_sessions[qube_id]
            logger.info("session_closed", qube_id=qube_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get handshake statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "known_relationships": len(self.relationships)
        }
