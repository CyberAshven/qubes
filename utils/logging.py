"""
Structured Logging for Qubes

Provides:
- Structured JSON logging with correlation IDs
- Sensitive data redaction (private keys, API keys)
- Context management for request tracing
- Multiple output formats (console, file, JSON)
- Integration with OpenTelemetry tracing
"""

import structlog
import logging
import logging.handlers
import sys
import uuid
from typing import Any, Dict, Optional
from contextvars import ContextVar
from pathlib import Path


# =============================================================================
# CONTEXT MANAGEMENT
# =============================================================================

# Correlation ID for distributed tracing
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Qube ID context (for multi-Qube scenarios)
qube_id_ctx: ContextVar[Optional[str]] = ContextVar("qube_id", default=None)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context"""
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str:
    """Get current correlation ID (generate if missing)"""
    correlation_id = correlation_id_ctx.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        correlation_id_ctx.set(correlation_id)
    return correlation_id


def set_qube_id(qube_id: str) -> None:
    """Set Qube ID for current context"""
    qube_id_ctx.set(qube_id)


def get_qube_id() -> Optional[str]:
    """Get current Qube ID"""
    return qube_id_ctx.get()


# =============================================================================
# SENSITIVE DATA REDACTION
# =============================================================================

SENSITIVE_KEYS = {
    "private_key",
    "secret_key",
    "api_key",
    "password",
    "token",
    "auth",
    "authorization",
    "wif",
    "mnemonic",
    "seed",
    "master_key",
    "encryption_key",
    "plaintext",
    "nonce",  # Not secret but sensitive
    "salt",   # Not secret but sensitive
    "ciphertext",  # Encrypted data
}


def redact_sensitive_data(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive data from logs

    Replaces values of sensitive keys with "***REDACTED***"
    """
    def _redact_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in d.items():
            if key.lower() in SENSITIVE_KEYS:
                d[key] = "***REDACTED***"
            elif isinstance(value, dict):
                d[key] = _redact_dict(value)
            elif isinstance(value, str):
                # Redact long hex strings (likely private keys)
                if len(value) > 32 and all(c in "0123456789abcdefABCDEF" for c in value):
                    d[key] = f"{value[:8]}...***REDACTED***"
        return d

    return _redact_dict(event_dict)


# =============================================================================
# CONTEXT INJECTION
# =============================================================================

def add_context(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add correlation ID and Qube ID to all log entries

    This processor runs on every log call to inject contextual information.
    """
    event_dict["correlation_id"] = get_correlation_id()

    qube_id = get_qube_id()
    if qube_id:
        event_dict["qube_id"] = qube_id

    return event_dict


# =============================================================================
# ERROR SERIALIZATION
# =============================================================================

def serialize_exception(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize exceptions for structured logging

    Extracts error details from QubesError exceptions.
    """
    exc_info = event_dict.get("exc_info")
    if exc_info:
        from core.exceptions import QubesError

        exc_type, exc_value, exc_tb = exc_info

        # If it's a QubesError, use structured serialization
        if isinstance(exc_value, QubesError):
            event_dict["error"] = exc_value.to_dict()
        else:
            # Standard exception handling
            event_dict["error"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
            }

    return event_dict


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_output: bool = False,
    console_output: bool = True,
) -> None:
    """
    Configure structured logging for Qubes

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_output: If True, output JSON format; else human-readable
        console_output: If True, also output to console
    """

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,           # Filter by log level
        structlog.stdlib.add_logger_name,           # Add logger name
        structlog.stdlib.add_log_level,             # Add log level
        structlog.processors.TimeStamper(fmt="iso"), # ISO 8601 timestamp
        add_context,                                 # Add correlation_id, qube_id
        structlog.processors.StackInfoRenderer(),   # Render stack traces
        structlog.processors.ExceptionRenderer(),   # Format exceptions (replaces format_exc_info)
        serialize_exception,                         # Serialize QubesError
        redact_sensitive_data,                       # Redact sensitive keys
    ]

    # Choose renderer based on output format
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging with UTF-8 encoding for emoji support
    # Clear any existing handlers first to ensure clean reconfiguration
    logging.root.handlers.clear()

    # Wrap sys.stdout with UTF-8 encoding to handle emoji on Windows
    import io
    if console_output:
        # Use UTF-8 encoding for stdout to support emoji and Unicode characters
        try:
            # Try to wrap stdout with UTF-8 encoding
            utf8_stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace',  # Replace unencodable characters instead of crashing
                line_buffering=True
            )
            stream = utf8_stdout
        except (AttributeError, io.UnsupportedOperation):
            # If stdout.buffer doesn't exist or is not writable, fall back to stdout
            # This can happen if stdout is already wrapped or redirected
            stream = sys.stdout
    else:
        stream = None

    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        stream=stream,
        force=True,  # Force reconfiguration even if handlers exist
    )

    # Add file handler if specified (with UTF-8 encoding)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,               # Keep 5 backup files
            encoding='utf-8',            # Use UTF-8 for emoji and Unicode support
        )
        file_handler.setLevel(numeric_level)
        logging.root.addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance

    Args:
        name: Logger name (typically __name__ of calling module)

    Returns:
        Structured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("qube_created", qube_id="A3F2C1B8", ai_model="gpt-4")
    """
    return structlog.get_logger(name)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log_function_call(func):
    """
    Decorator to log function entry/exit with timing

    Example:
        @log_function_call
        def create_qube(name: str):
            ...
    """
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        # Log entry
        logger.debug(
            "function_called",
            function=func.__name__,
            args=args[:3] if len(args) <= 3 else f"{args[:2]}... ({len(args)} total)",
            kwargs={k: v for k, v in list(kwargs.items())[:5]},  # First 5 kwargs
        )

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            # Log success
            logger.debug(
                "function_completed",
                function=func.__name__,
                elapsed_ms=round(elapsed * 1000, 2),
            )

            return result

        except Exception as e:
            elapsed = time.time() - start_time

            # Log failure
            logger.error(
                "function_failed",
                function=func.__name__,
                elapsed_ms=round(elapsed * 1000, 2),
                exc_info=True,
            )
            raise

    return wrapper


def log_async_function_call(func):
    """
    Decorator to log async function entry/exit with timing

    Example:
        @log_async_function_call
        async def mint_nft(qube_id: str):
            ...
    """
    import functools
    import time

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        # Log entry
        logger.debug(
            "async_function_called",
            function=func.__name__,
            args=args[:3] if len(args) <= 3 else f"{args[:2]}... ({len(args)} total)",
            kwargs={k: v for k, v in list(kwargs.items())[:5]},
        )

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time

            # Log success
            logger.debug(
                "async_function_completed",
                function=func.__name__,
                elapsed_ms=round(elapsed * 1000, 2),
            )

            return result

        except Exception as e:
            elapsed = time.time() - start_time

            # Log failure
            logger.error(
                "async_function_failed",
                function=func.__name__,
                elapsed_ms=round(elapsed * 1000, 2),
                exc_info=True,
            )
            raise

    return wrapper


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Configure logging (human-readable for development)
    configure_logging(
        log_level="DEBUG",
        log_file=Path("logs/qubes.log"),
        json_output=False,
        console_output=True,
    )

    # Get logger
    logger = get_logger(__name__)

    # Set context
    set_correlation_id("req-12345")
    set_qube_id("A3F2C1B8")

    # Log examples
    logger.info("qube_created", name="Athena", ai_model="gpt-4")
    logger.warning("api_rate_limit", provider="openai", retry_after=60)

    # Log with sensitive data (will be redacted)
    logger.debug("key_generated", private_key="a1b2c3d4e5f6...")

    # Log exception
    try:
        raise ValueError("Test error")
    except Exception:
        logger.error("operation_failed", operation="test", exc_info=True)
