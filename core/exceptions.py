"""
Qubes Exception Hierarchy

Provides structured exceptions for all system components with:
- Error codes for programmatic handling
- Contextual metadata for debugging
- Severity levels for logging/alerting
- Retry hints for transient failures
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels for logging and alerting"""
    LOW = "low"           # Minor issues, graceful degradation
    MEDIUM = "medium"     # Significant issues, partial failure
    HIGH = "high"         # Critical issues, major functionality lost
    CRITICAL = "critical" # System failure, immediate attention required


class QubesError(Exception):
    """
    Base exception for all Qubes errors

    All custom exceptions inherit from this base class to provide
    consistent error handling, logging, and monitoring.
    """

    error_code: str = "QUBES_ERROR"
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    retryable: bool = False

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize Qubes error

        Args:
            message: Human-readable error description
            context: Additional context (qube_id, block_number, etc.)
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error for logging/monitoring"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None
        }


# =============================================================================
# CRYPTOGRAPHY ERRORS
# =============================================================================

class CryptoError(QubesError):
    """Base class for cryptography errors"""
    error_code = "CRYPTO_ERROR"
    severity = ErrorSeverity.HIGH


class KeyGenerationError(CryptoError):
    """Failed to generate cryptographic keys"""
    error_code = "CRYPTO_KEY_GEN_FAILED"
    severity = ErrorSeverity.CRITICAL


class EncryptionError(CryptoError):
    """Failed to encrypt data"""
    error_code = "CRYPTO_ENCRYPT_FAILED"
    severity = ErrorSeverity.HIGH


class DecryptionError(CryptoError):
    """Failed to decrypt data"""
    error_code = "CRYPTO_DECRYPT_FAILED"
    severity = ErrorSeverity.HIGH


class SignatureError(CryptoError):
    """Failed to create or verify signature"""
    error_code = "CRYPTO_SIGNATURE_FAILED"
    severity = ErrorSeverity.HIGH


class InvalidSignatureError(CryptoError):
    """Signature verification failed - potential tampering"""
    error_code = "CRYPTO_INVALID_SIGNATURE"
    severity = ErrorSeverity.CRITICAL


class MerkleRootMismatchError(CryptoError):
    """Merkle root verification failed - memory chain corrupted"""
    error_code = "CRYPTO_MERKLE_MISMATCH"
    severity = ErrorSeverity.CRITICAL


# =============================================================================
# STORAGE ERRORS
# =============================================================================

class StorageError(QubesError):
    """Base class for storage errors"""
    error_code = "STORAGE_ERROR"
    severity = ErrorSeverity.HIGH


class DatabaseCorruptionError(StorageError):
    """Database file is corrupted"""
    error_code = "STORAGE_DB_CORRUPTED"
    severity = ErrorSeverity.CRITICAL
    retryable = False


class BlockNotFoundError(StorageError):
    """Requested memory block not found"""
    error_code = "STORAGE_BLOCK_NOT_FOUND"
    severity = ErrorSeverity.MEDIUM


class DiskFullError(StorageError):
    """Insufficient disk space"""
    error_code = "STORAGE_DISK_FULL"
    severity = ErrorSeverity.HIGH
    retryable = False


class IPFSError(StorageError):
    """IPFS operation failed"""
    error_code = "STORAGE_IPFS_FAILED"
    severity = ErrorSeverity.MEDIUM
    retryable = True


# =============================================================================
# AI/MODEL ERRORS
# =============================================================================

class AIError(QubesError):
    """Base class for AI/LLM errors"""
    error_code = "AI_ERROR"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class ModelNotAvailableError(AIError):
    """AI model is not available (API down, rate limited, etc.)"""
    error_code = "AI_MODEL_UNAVAILABLE"
    severity = ErrorSeverity.HIGH
    retryable = True


class ModelAPIError(AIError):
    """AI provider API returned error"""
    error_code = "AI_API_ERROR"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class ModelTimeoutError(AIError):
    """AI model request timed out"""
    error_code = "AI_TIMEOUT"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class ModelRateLimitError(AIError):
    """AI provider rate limit exceeded"""
    error_code = "AI_RATE_LIMIT"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class ModelInvalidResponseError(AIError):
    """AI model returned invalid/malformed response"""
    error_code = "AI_INVALID_RESPONSE"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class ToolExecutionError(AIError):
    """Tool execution failed during AI reasoning"""
    error_code = "AI_TOOL_EXECUTION_FAILED"
    severity = ErrorSeverity.MEDIUM
    retryable = False


class AllProvidersFailed(AIError):
    """All AI providers failed (primary + all fallbacks)"""
    error_code = "AI_ALL_PROVIDERS_FAILED"
    severity = ErrorSeverity.CRITICAL
    retryable = False


# Aliases for common AI errors
AIAPIError = ModelAPIError
AIRateLimitError = ModelRateLimitError
AIAuthenticationError = ModelAPIError  # Use generic API error for auth failures


# =============================================================================
# P2P NETWORK ERRORS
# =============================================================================

class NetworkError(QubesError):
    """Base class for P2P networking errors"""
    error_code = "NETWORK_ERROR"
    severity = ErrorSeverity.MEDIUM


class PeerDiscoveryError(NetworkError):
    """Failed to discover peers on DHT"""
    error_code = "NETWORK_PEER_DISCOVERY_FAILED"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class PeerConnectionError(NetworkError):
    """Failed to connect to peer"""
    error_code = "NETWORK_PEER_CONNECTION_FAILED"
    severity = ErrorSeverity.MEDIUM
    retryable = True


class HandshakeError(NetworkError):
    """P2P handshake failed (authentication)"""
    error_code = "NETWORK_HANDSHAKE_FAILED"
    severity = ErrorSeverity.HIGH


class AuthenticationError(NetworkError):
    """P2P authentication failed"""
    error_code = "NETWORK_AUTH_FAILED"
    severity = ErrorSeverity.HIGH


class MessageEncryptionError(NetworkError):
    """Failed to encrypt P2P message"""
    error_code = "NETWORK_MESSAGE_ENCRYPT_FAILED"
    severity = ErrorSeverity.HIGH


class MessageDecryptionError(NetworkError):
    """Failed to decrypt P2P message"""
    error_code = "NETWORK_MESSAGE_DECRYPT_FAILED"
    severity = ErrorSeverity.HIGH


class RateLimitExceededError(NetworkError):
    """Peer exceeded message rate limit (DoS protection)"""
    error_code = "NETWORK_RATE_LIMIT_EXCEEDED"
    severity = ErrorSeverity.MEDIUM


# =============================================================================
# BLOCKCHAIN ERRORS
# =============================================================================

class BlockchainError(QubesError):
    """Base class for blockchain errors"""
    error_code = "BLOCKCHAIN_ERROR"
    severity = ErrorSeverity.MEDIUM


class NFTMintError(BlockchainError):
    """Failed to mint NFT"""
    error_code = "BLOCKCHAIN_NFT_MINT_FAILED"
    severity = ErrorSeverity.HIGH
    retryable = True


class NFTVerificationError(BlockchainError):
    """Failed to verify NFT ownership"""
    error_code = "BLOCKCHAIN_NFT_VERIFY_FAILED"
    severity = ErrorSeverity.HIGH
    retryable = True


class TransactionError(BlockchainError):
    """Blockchain transaction failed"""
    error_code = "BLOCKCHAIN_TX_FAILED"
    severity = ErrorSeverity.HIGH
    retryable = True


class InsufficientFundsError(BlockchainError):
    """Insufficient BCH for transaction"""
    error_code = "BLOCKCHAIN_INSUFFICIENT_FUNDS"
    severity = ErrorSeverity.HIGH
    retryable = False


class ChaingraphError(BlockchainError):
    """Chaingraph API query failed"""
    error_code = "BLOCKCHAIN_CHAINGRAPH_FAILED"
    severity = ErrorSeverity.MEDIUM
    retryable = True


# =============================================================================
# MEMORY CHAIN ERRORS
# =============================================================================

class MemoryChainError(QubesError):
    """Base class for memory chain errors"""
    error_code = "MEMORY_CHAIN_ERROR"
    severity = ErrorSeverity.HIGH


class InvalidBlockError(MemoryChainError):
    """Block validation failed"""
    error_code = "MEMORY_INVALID_BLOCK"
    severity = ErrorSeverity.HIGH


class ChainIntegrityError(MemoryChainError):
    """Memory chain integrity compromised (hash mismatch)"""
    error_code = "MEMORY_CHAIN_INTEGRITY_FAILED"
    severity = ErrorSeverity.CRITICAL


class SessionRecoveryError(MemoryChainError):
    """Failed to recover session after crash"""
    error_code = "MEMORY_SESSION_RECOVERY_FAILED"
    severity = ErrorSeverity.HIGH


class AnchoringError(MemoryChainError):
    """Failed to anchor session blocks to permanent chain"""
    error_code = "MEMORY_ANCHORING_FAILED"
    severity = ErrorSeverity.HIGH


# =============================================================================
# RELATIONSHIP ERRORS
# =============================================================================

class RelationshipError(QubesError):
    """Base class for relationship management errors"""
    error_code = "RELATIONSHIP_ERROR"
    severity = ErrorSeverity.MEDIUM


class RelationshipNotFoundError(RelationshipError):
    """Relationship with specified entity not found"""
    error_code = "RELATIONSHIP_NOT_FOUND"
    severity = ErrorSeverity.LOW


class TrustScoreError(RelationshipError):
    """Trust score calculation failed"""
    error_code = "RELATIONSHIP_TRUST_SCORE_FAILED"
    severity = ErrorSeverity.MEDIUM


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================

class ConfigurationError(QubesError):
    """Base class for configuration errors"""
    error_code = "CONFIG_ERROR"
    severity = ErrorSeverity.HIGH
    retryable = False


class MissingConfigError(ConfigurationError):
    """Required configuration missing"""
    error_code = "CONFIG_MISSING"
    severity = ErrorSeverity.CRITICAL


class InvalidConfigError(ConfigurationError):
    """Configuration is invalid"""
    error_code = "CONFIG_INVALID"
    severity = ErrorSeverity.HIGH


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(QubesError):
    """Base class for validation errors"""
    error_code = "VALIDATION_ERROR"
    severity = ErrorSeverity.MEDIUM
    retryable = False


class InvalidInputError(ValidationError):
    """User input validation failed"""
    error_code = "VALIDATION_INVALID_INPUT"
    severity = ErrorSeverity.LOW


class InvalidQubeIDError(ValidationError):
    """Qube ID format invalid"""
    error_code = "VALIDATION_INVALID_QUBE_ID"
    severity = ErrorSeverity.MEDIUM
