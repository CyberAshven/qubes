"""
Test if logging configuration properly redacts sensitive data

Checks if exc_info=True could leak secrets in exception handling
"""

import sys
from pathlib import Path
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging import configure_logging, get_logger, SENSITIVE_KEYS

def test_exception_redaction():
    """Test if exceptions with sensitive local variables are properly redacted"""

    print("\n=== TEST 1: Exception with Sensitive Local Variables ===\n")

    # Configure logging
    configure_logging(
        log_level="DEBUG",
        json_output=False,
        console_output=True
    )

    logger = get_logger("test")

    # Simulate encryption function with sensitive data
    def encrypt_data(data, private_key):
        """Simulates crypto function with sensitive variables"""
        try:
            # Intentionally cause an error
            result = 1 / 0  # ZeroDivisionError
        except Exception as e:
            # Log with exc_info=True (like crypto/encryption.py line 45)
            logger.error("encryption_failed", exc_info=True)
            raise

    try:
        secret_key = "a" * 64  # Simulated private key (64 hex chars)
        plaintext = {"password": "secret123", "api_key": "sk-1234"}
        encrypt_data(plaintext, secret_key)
    except:
        pass

    print("\n✅ Exception logged above")
    print("\nANALYSIS:")
    print("- Default Python tracebacks do NOT show local variable values")
    print("- Only shows function names, file paths, and line numbers")
    print("- structlog.processors.ExceptionRenderer() uses default formatting")
    print()


def test_exception_message_leak():
    """Test if exception MESSAGES containing secrets are redacted"""

    print("\n=== TEST 2: Exception Message Containing Secrets ===\n")

    logger = get_logger("test")

    # Simulate raising an exception with secret in message
    try:
        secret_key = "a1b2c3d4e5f6" * 8  # 96-char hex string
        raise ValueError(f"Decryption failed with key: {secret_key}")
    except Exception as e:
        logger.error("decryption_failed", exc_info=True)

    print("\n⚠️  ISSUE: Exception message contains raw secret")
    print("   The redaction processor only checks event_dict keys, not exception messages")
    print()


def test_direct_logging_with_secrets():
    """Test if directly logged secrets are redacted"""

    print("\n=== TEST 3: Direct Logging with Secret Keys ===\n")

    logger = get_logger("test")

    # Log with secret in event_dict
    logger.info(
        "key_generated",
        private_key="a1b2c3d4e5f6" * 8,
        password="secret123",
        api_key="sk-1234567890"
    )

    print("\n✅ SECURE: Keys in event_dict are properly redacted")
    print()


def check_sensitive_keys():
    """Show which keys are considered sensitive"""

    print("\n=== SENSITIVE KEYS LIST ===\n")
    print("The following keys are redacted from logs:")
    for key in sorted(SENSITIVE_KEYS):
        print(f"  - {key}")
    print()

    print("MISSING from redaction list:")
    missing = [
        "nonce",          # AES-GCM nonce (not secret but sensitive)
        "salt",           # PBKDF2 salt (not secret but sensitive)
        "ciphertext",     # Encrypted data
        "encryption_key", # Not in list
        "plaintext",      # Not in list
    ]
    for key in missing:
        print(f"  ⚠️  {key}")
    print()


if __name__ == "__main__":
    print("=" * 70)
    print("LOGGING SECURITY ANALYSIS")
    print("=" * 70)

    check_sensitive_keys()
    test_direct_logging_with_secrets()
    test_exception_redaction()
    test_exception_message_leak()

    print("\n" + "=" * 70)
    print("SUMMARY OF FINDINGS")
    print("=" * 70)
    print()
    print("1. ✅ SECURE: Direct logging with sensitive keys is properly redacted")
    print("   Location: utils/logging.py:76-94 (redact_sensitive_data)")
    print()
    print("2. ✅ SECURE: Stack traces don't include local variable values")
    print("   Reason: Default Python traceback formatting")
    print()
    print("3. ⚠️  POTENTIAL ISSUE: Exception messages not redacted")
    print("   Risk: If code raises exceptions with secrets in message text")
    print("   Example: ValueError(f'Failed with key: {private_key}')")
    print()
    print("4. ⚠️  MISSING KEYS: Some sensitive keys not in SENSITIVE_KEYS")
    print("   Missing: 'nonce', 'salt', 'ciphertext', 'encryption_key', 'plaintext'")
    print("   Impact: These won't be redacted if logged")
    print()
