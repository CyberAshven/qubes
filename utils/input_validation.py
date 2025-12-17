"""
Input Validation & Sanitization

Provides secure input validation for all user inputs to prevent:
- Command injection
- Path traversal
- SQL injection
- XSS attacks
- Buffer overflow attacks
- SSRF (Server-Side Request Forgery)

Security Fix: CVE-02 - Critical input validation
Updated: 2025-01-05 - Enhanced URL validation and SSRF protection
"""

import re
import ipaddress
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from core.exceptions import QubesError

# ==============================================================================
# CONSTANTS
# ==============================================================================

MAX_QUBE_NAME_LENGTH = 64
MAX_USER_ID_LENGTH = 32
MAX_MESSAGE_LENGTH = 100000  # 100KB
MAX_QUBE_ID_LENGTH = 8
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

# Regex patterns for validation
QUBE_ID_PATTERN = re.compile(r'^[A-F0-9]{8}$')
USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')
QUBE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s_-]{1,64}$')
HEX_PATTERN = re.compile(r'^[a-fA-F0-9]+$')
BCH_ADDRESS_PATTERN = re.compile(r'^(bitcoincash|bchtest):[a-z0-9]{42}$')

# Dangerous characters for path traversal
DANGEROUS_PATH_CHARS = ['..', '/', '\\', '\x00']

# Dangerous shell characters for command injection
DANGEROUS_SHELL_CHARS = ['`', '$', '|', ';', '&', '\n', '\r', '<', '>']


# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

def validate_qube_id(qube_id: str) -> str:
    """
    Validate Qube ID format (8-character hex uppercase)

    Args:
        qube_id: Qube ID to validate

    Returns:
        Validated qube_id

    Raises:
        QubesError: If validation fails

    Example:
        >>> validate_qube_id("A3F2C1B8")
        "A3F2C1B8"
        >>> validate_qube_id("invalid")  # Raises QubesError
    """
    if not qube_id:
        raise QubesError("Qube ID cannot be empty", context={"qube_id": qube_id})

    if not isinstance(qube_id, str):
        raise QubesError(
            f"Qube ID must be string, got {type(qube_id)}",
            context={"qube_id": qube_id}
        )

    if not QUBE_ID_PATTERN.match(qube_id):
        raise QubesError(
            f"Invalid Qube ID format. Must be 8 uppercase hex characters, got: {qube_id}",
            context={"qube_id": qube_id}
        )

    return qube_id


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format (alphanumeric, dash, underscore, max 32 chars)

    Args:
        user_id: User ID to validate

    Returns:
        Validated user_id

    Raises:
        QubesError: If validation fails
    """
    if not user_id:
        raise QubesError("User ID cannot be empty", context={"user_id": user_id})

    if not isinstance(user_id, str):
        raise QubesError(
            f"User ID must be string, got {type(user_id)}",
            context={"user_id": user_id}
        )

    if not USER_ID_PATTERN.match(user_id):
        raise QubesError(
            f"Invalid User ID format. Must be alphanumeric with dash/underscore, max 32 chars",
            context={"user_id": user_id}
        )

    return user_id


def validate_qube_name(qube_name: str) -> str:
    """
    Validate and sanitize Qube name

    Args:
        qube_name: Qube name to validate

    Returns:
        Validated and sanitized qube_name

    Raises:
        QubesError: If validation fails
    """
    if not qube_name:
        raise QubesError("Qube name cannot be empty", context={"qube_name": qube_name})

    if not isinstance(qube_name, str):
        raise QubesError(
            f"Qube name must be string, got {type(qube_name)}",
            context={"qube_name": qube_name}
        )

    # Check length
    if len(qube_name) > MAX_QUBE_NAME_LENGTH:
        raise QubesError(
            f"Qube name too long. Max {MAX_QUBE_NAME_LENGTH} characters, got {len(qube_name)}",
            context={"qube_name": qube_name}
        )

    # Check for dangerous characters (path traversal)
    for dangerous_char in DANGEROUS_PATH_CHARS:
        if dangerous_char in qube_name:
            raise QubesError(
                f"Qube name contains dangerous character: {dangerous_char}",
                context={"qube_name": qube_name}
            )

    # Validate pattern
    if not QUBE_NAME_PATTERN.match(qube_name):
        raise QubesError(
            f"Invalid Qube name. Only alphanumeric, spaces, dash, underscore allowed",
            context={"qube_name": qube_name}
        )

    return qube_name.strip()


def validate_message(message: str) -> str:
    """
    Validate message content

    Args:
        message: Message content to validate

    Returns:
        Validated message

    Raises:
        QubesError: If validation fails

    Note:
        Previously checked for shell injection characters, but this was overly
        restrictive since messages are never passed to shell commands.
        Now only validates type and length.
    """
    if not isinstance(message, str):
        raise QubesError(
            f"Message must be string, got {type(message)}",
            context={"message_type": type(message).__name__}
        )

    # Check length
    if len(message) > MAX_MESSAGE_LENGTH:
        raise QubesError(
            f"Message too long. Max {MAX_MESSAGE_LENGTH} characters, got {len(message)}",
            context={"message_length": len(message)}
        )

    # NOTE: Removed shell injection character check (was overly restrictive)
    # Messages are stored in JSON and never passed to shell commands
    # If shell execution is needed in the future, validate at that point

    return message


def validate_hex_string(hex_str: str, expected_length: Optional[int] = None) -> str:
    """
    Validate hexadecimal string

    Args:
        hex_str: Hex string to validate
        expected_length: Optional expected length (in characters)

    Returns:
        Validated hex string

    Raises:
        QubesError: If validation fails
    """
    if not isinstance(hex_str, str):
        raise QubesError(
            f"Hex string must be string, got {type(hex_str)}",
            context={"hex_str": hex_str}
        )

    if not HEX_PATTERN.match(hex_str):
        raise QubesError(
            "Invalid hex string. Must contain only 0-9, a-f, A-F",
            context={"hex_str": hex_str[:32] + "..."}
        )

    if expected_length and len(hex_str) != expected_length:
        raise QubesError(
            f"Invalid hex string length. Expected {expected_length}, got {len(hex_str)}",
            context={"hex_str": hex_str[:32] + "...", "length": len(hex_str)}
        )

    return hex_str


def validate_file_path(file_path: str, allowed_base_dir: Optional[Path] = None) -> Path:
    """
    Validate file path and prevent path traversal attacks

    Args:
        file_path: File path to validate
        allowed_base_dir: Optional base directory to restrict access to

    Returns:
        Validated Path object

    Raises:
        QubesError: If validation fails or path traversal detected
    """
    if not isinstance(file_path, (str, Path)):
        raise QubesError(
            f"File path must be string or Path, got {type(file_path)}",
            context={"file_path": file_path}
        )

    # Convert to Path
    path = Path(file_path)

    # Check for path traversal
    path_str = str(path)
    for dangerous_char in DANGEROUS_PATH_CHARS[:2]:  # Check .. and /
        if dangerous_char in path_str:
            raise QubesError(
                f"Path traversal detected: {dangerous_char}",
                context={"file_path": file_path}
            )

    # If base directory specified, ensure path is within it
    if allowed_base_dir:
        allowed_base_dir = Path(allowed_base_dir).resolve()

        try:
            resolved_path = path.resolve()

            # Check if path is within allowed directory
            if not str(resolved_path).startswith(str(allowed_base_dir)):
                raise QubesError(
                    f"Access denied. Path outside allowed directory",
                    context={
                        "file_path": file_path,
                        "allowed_base": str(allowed_base_dir)
                    }
                )
        except (OSError, RuntimeError) as e:
            raise QubesError(
                f"Invalid file path: {str(e)}",
                context={"file_path": file_path},
                cause=e
            )

    return path


def validate_file_size(file_path: Path, max_size: int = MAX_FILE_SIZE) -> int:
    """
    Validate file size to prevent DoS attacks

    Args:
        file_path: Path to file
        max_size: Maximum allowed file size in bytes

    Returns:
        File size in bytes

    Raises:
        QubesError: If file too large or doesn't exist
    """
    if not file_path.exists():
        raise QubesError(
            f"File does not exist: {file_path}",
            context={"file_path": str(file_path)}
        )

    file_size = file_path.stat().st_size

    if file_size > max_size:
        raise QubesError(
            f"File too large. Max {max_size} bytes, got {file_size} bytes",
            context={
                "file_path": str(file_path),
                "file_size": file_size,
                "max_size": max_size
            }
        )

    return file_size


def validate_bch_address(address: str) -> str:
    """
    Validate Bitcoin Cash address format (CashAddr)

    Args:
        address: BCH address to validate

    Returns:
        Validated address

    Raises:
        QubesError: If validation fails
    """
    if not isinstance(address, str):
        raise QubesError(
            f"BCH address must be string, got {type(address)}",
            context={"address": address}
        )

    # Basic CashAddr format validation
    if not BCH_ADDRESS_PATTERN.match(address.lower()):
        raise QubesError(
            "Invalid Bitcoin Cash address format. Must be CashAddr format (bitcoincash:...)",
            context={"address": address}
        )

    return address


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    if not isinstance(filename, str):
        raise QubesError(
            f"Filename must be string, got {type(filename)}",
            context={"filename": filename}
        )

    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Keep only safe characters (alphanumeric, dash, underscore, dot)
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename


def validate_url_safe(url: str, allow_private: bool = False) -> str:
    """
    Validate URL with SSRF (Server-Side Request Forgery) protection

    Prevents access to:
    - localhost / 127.0.0.1 / ::1
    - Private IP ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    - Link-local addresses (169.254.x.x)
    - Cloud metadata endpoints (169.254.169.254)
    - file:// protocol
    - Other non-HTTP protocols

    Args:
        url: URL to validate
        allow_private: Allow private/internal IPs (default: False, for security)

    Returns:
        Validated URL

    Raises:
        QubesError: If URL is unsafe or malformed

    Example:
        >>> validate_url_safe("https://example.com")
        "https://example.com"
        >>> validate_url_safe("http://localhost:8080")  # Raises QubesError
        >>> validate_url_safe("http://192.168.1.1")  # Raises QubesError
    """
    if not isinstance(url, str):
        raise QubesError(
            f"URL must be string, got {type(url)}",
            context={"url": url}
        )

    # Basic prefix check
    if not url.startswith(("http://", "https://")):
        raise QubesError(
            "URL must start with http:// or https://",
            context={"url": url}
        )

    try:
        # Parse URL
        parsed = urlparse(url)

        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise QubesError(
                f"Invalid URL scheme. Only http:// and https:// allowed, got {parsed.scheme}://",
                context={"url": url, "scheme": parsed.scheme}
            )

        # Get hostname
        hostname = parsed.hostname
        if not hostname:
            raise QubesError(
                "URL must have a valid hostname",
                context={"url": url}
            )

        # Block localhost
        if hostname.lower() in ('localhost', 'localhost.localdomain'):
            raise QubesError(
                "Cannot access localhost. SSRF protection.",
                context={"url": url, "hostname": hostname}
            )

        # Try to resolve as IP address
        try:
            ip = ipaddress.ip_address(hostname)

            # Block loopback
            if ip.is_loopback:
                raise QubesError(
                    f"Cannot access loopback address {hostname}. SSRF protection.",
                    context={"url": url, "ip": str(ip)}
                )

            # Block private/internal IPs (unless explicitly allowed)
            if not allow_private:
                if ip.is_private:
                    raise QubesError(
                        f"Cannot access private IP address {hostname}. SSRF protection.",
                        context={"url": url, "ip": str(ip)}
                    )

                if ip.is_link_local:
                    raise QubesError(
                        f"Cannot access link-local address {hostname}. SSRF protection.",
                        context={"url": url, "ip": str(ip)}
                    )

                # Specifically block cloud metadata endpoint
                if str(ip) == '169.254.169.254':
                    raise QubesError(
                        "Cannot access cloud metadata endpoint. SSRF protection.",
                        context={"url": url, "ip": str(ip)}
                    )

        except ValueError:
            # Not an IP address - it's a domain name, which is fine
            # Domain resolution happens at request time
            pass

        return url

    except QubesError:
        # Re-raise our validation errors
        raise
    except Exception as e:
        raise QubesError(
            f"Invalid URL format: {str(e)}",
            context={"url": url},
            cause=e
        )


def validate_url_basic(url: str) -> str:
    """
    Basic URL validation (backward compatibility wrapper)

    For less strict validation where SSRF protection is not needed
    (e.g., user-configured trusted endpoints)

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        QubesError: If URL format is invalid
    """
    if not isinstance(url, str):
        raise QubesError(
            f"URL must be string, got {type(url)}",
            context={"url": url}
        )

    if not url.startswith(("http://", "https://")):
        raise QubesError(
            "URL must start with http:// or https://",
            context={"url": url}
        )

    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            raise QubesError(
                "URL must have a valid hostname",
                context={"url": url}
            )
        return url
    except Exception as e:
        raise QubesError(
            f"Invalid URL format: {str(e)}",
            context={"url": url},
            cause=e
        )


def validate_ssh_hostname(hostname: str) -> str:
    """
    Validate SSH hostname to prevent command injection

    Args:
        hostname: SSH hostname to validate

    Returns:
        Validated hostname

    Raises:
        QubesError: If hostname is invalid or contains dangerous characters

    Example:
        >>> validate_ssh_hostname("example.com")
        "example.com"
        >>> validate_ssh_hostname("192.168.1.1")
        "192.168.1.1"
        >>> validate_ssh_hostname("host; rm -rf /")  # Raises QubesError
    """
    if not isinstance(hostname, str):
        raise QubesError(
            f"Hostname must be string, got {type(hostname)}",
            context={"hostname": hostname}
        )

    # Allow alphanumeric, dots, hyphens only (standard hostname format)
    if not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
        raise QubesError(
            "Invalid hostname format. Only alphanumeric, dots, and hyphens allowed.",
            context={"hostname": hostname}
        )

    # Check length
    if len(hostname) > 253:  # Maximum DNS hostname length
        raise QubesError(
            f"Hostname too long. Max 253 characters, got {len(hostname)}",
            context={"hostname": hostname}
        )

    return hostname


def validate_integer_range(value: int, min_value: int, max_value: int, param_name: str = "value") -> int:
    """
    Validate integer is within specified range

    Args:
        value: Integer to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        param_name: Parameter name for error messages

    Returns:
        Validated integer

    Raises:
        QubesError: If value out of range

    Example:
        >>> validate_integer_range(50, 0, 100, "trust_score")
        50
        >>> validate_integer_range(150, 0, 100, "trust_score")  # Raises QubesError
    """
    if not isinstance(value, int):
        raise QubesError(
            f"{param_name} must be integer, got {type(value)}",
            context={param_name: value}
        )

    if value < min_value or value > max_value:
        raise QubesError(
            f"{param_name} must be between {min_value} and {max_value}, got {value}",
            context={param_name: value, "min": min_value, "max": max_value}
        )

    return value


# ==============================================================================
# VALIDATION DECORATOR
# ==============================================================================

def validate_inputs(**validators):
    """
    Decorator to validate function inputs

    Usage:
        @validate_inputs(qube_id=validate_qube_id, user_id=validate_user_id)
        def my_function(qube_id: str, user_id: str):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate kwargs
            for param_name, validator_func in validators.items():
                if param_name in kwargs:
                    kwargs[param_name] = validator_func(kwargs[param_name])

            return func(*args, **kwargs)

        return wrapper
    return decorator


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Test validation functions
    print("Testing input validation...")

    # Valid inputs
    assert validate_qube_id("A3F2C1B8") == "A3F2C1B8"
    assert validate_user_id("alice123") == "alice123"
    assert validate_qube_name("My Qube") == "My Qube"

    # Invalid inputs (should raise QubesError)
    try:
        validate_qube_id("invalid")
        assert False, "Should have raised QubesError"
    except QubesError:
        pass

    try:
        validate_qube_name("../../etc/passwd")
        assert False, "Should have raised QubesError"
    except QubesError:
        pass

    try:
        validate_message("hello`whoami`")
        assert False, "Should have raised QubesError"
    except QubesError:
        pass

    print("All validation tests passed!")
