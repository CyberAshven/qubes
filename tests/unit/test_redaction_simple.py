"""Simple test to verify logging redaction works"""
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging import configure_logging, get_logger

# Configure logging
configure_logging(
    log_level="INFO",
    json_output=False,
    console_output=True
)

# Get logger
logger = get_logger("test")

print("=" * 60)
print("Testing Logging Redaction")
print("=" * 60)
print()

# Test 1: Log with sensitive keys
print("Test 1: Logging with sensitive keys")
print("Expected: Values should be ***REDACTED***")
print()

logger.info(
    "test_message",
    private_key="this_should_be_redacted",
    password="also_redacted",
    api_key="sk-redacted_too",
    normal_field="this_should_show"
)

print()
print("Test 2: Logging with new sensitive keys")
print()

logger.info(
    "test_message_2",
    encryption_key="should_be_redacted",
    plaintext="should_be_redacted",
    nonce="should_be_redacted",
    salt="should_be_redacted",
    ciphertext="should_be_redacted",
    normal_field="this_should_show"
)

print()
print("=" * 60)
print("If you see actual values above (not ***REDACTED***),")
print("then redaction is NOT working.")
print("=" * 60)
