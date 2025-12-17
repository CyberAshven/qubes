"""
Tests for AES-256-GCM Encryption

Comprehensive tests for block encryption, raw data encryption, and key derivation.
Validates AES-256-GCM authenticated encryption with proper nonce handling.

Covers:
- Block data encryption/decryption (dict → encrypted dict → dict)
- Raw data encryption/decryption (bytes → encrypted bytes → bytes)
- Key derivation (HKDF for per-block keys)
- Key generation (secure random keys)
- Error handling (wrong key, corrupted data)
- Security properties (nonce uniqueness, ciphertext randomness)
- Edge cases (empty data, large data, Unicode)
"""

import pytest
import secrets

from crypto.encryption import (
    encrypt_block_data,
    decrypt_block_data,
    derive_block_key,
    generate_encryption_key,
    encrypt_data,
    decrypt_data
)
from core.exceptions import EncryptionError, DecryptionError


# ==============================================================================
# BLOCK DATA ENCRYPTION TESTS
# ==============================================================================

class TestBlockDataEncryption:
    """Test block data encryption (dict → encrypted dict)"""

    @pytest.mark.unit
    def test_encrypt_block_data_success(self):
        """Should encrypt block data successfully"""
        key = secrets.token_bytes(32)
        data = {"content": "test message", "block_number": 1}

        encrypted = encrypt_block_data(data, key)

        assert "ciphertext" in encrypted
        assert "nonce" in encrypted
        assert "algorithm" in encrypted
        assert encrypted["algorithm"] == "AES-256-GCM"
        assert len(encrypted["ciphertext"]) > 0
        assert len(encrypted["nonce"]) == 24  # 12 bytes hex = 24 chars

    @pytest.mark.unit
    def test_encrypt_block_data_hex_format(self):
        """Encrypted data should be hex-encoded"""
        key = secrets.token_bytes(32)
        data = {"test": "data"}

        encrypted = encrypt_block_data(data, key)

        # Should be valid hex
        bytes.fromhex(encrypted["ciphertext"])  # Should not raise
        bytes.fromhex(encrypted["nonce"])  # Should not raise

    @pytest.mark.unit
    def test_encrypt_block_data_nonce_uniqueness(self):
        """Each encryption should use a unique nonce"""
        key = secrets.token_bytes(32)
        data = {"test": "data"}

        encrypted1 = encrypt_block_data(data, key)
        encrypted2 = encrypt_block_data(data, key)

        # Nonces should be different
        assert encrypted1["nonce"] != encrypted2["nonce"]
        # Ciphertexts should be different (due to different nonces)
        assert encrypted1["ciphertext"] != encrypted2["ciphertext"]

    @pytest.mark.unit
    def test_encrypt_block_data_different_data(self):
        """Different data should produce different ciphertexts"""
        key = secrets.token_bytes(32)

        encrypted1 = encrypt_block_data({"data": "test1"}, key)
        encrypted2 = encrypt_block_data({"data": "test2"}, key)

        assert encrypted1["ciphertext"] != encrypted2["ciphertext"]


# ==============================================================================
# BLOCK DATA DECRYPTION TESTS
# ==============================================================================

class TestBlockDataDecryption:
    """Test block data decryption"""

    @pytest.mark.unit
    def test_decrypt_block_data_success(self):
        """Should decrypt block data successfully"""
        key = secrets.token_bytes(32)
        original_data = {"content": "test message", "number": 42}

        encrypted = encrypt_block_data(original_data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == original_data

    @pytest.mark.unit
    def test_decrypt_block_data_with_wrong_key(self):
        """Decryption with wrong key should fail"""
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)

        data = {"test": "data"}
        encrypted = encrypt_block_data(data, key1)

        with pytest.raises(DecryptionError):
            decrypt_block_data(encrypted, key2)

    @pytest.mark.unit
    def test_decrypt_block_data_corrupted_ciphertext(self):
        """Corrupted ciphertext should fail decryption"""
        key = secrets.token_bytes(32)
        data = {"test": "data"}

        encrypted = encrypt_block_data(data, key)

        # Corrupt ciphertext
        corrupted = encrypted.copy()
        ciphertext_bytes = bytes.fromhex(encrypted["ciphertext"])
        corrupted_bytes = bytes([b ^ 0xFF for b in ciphertext_bytes[:10]]) + ciphertext_bytes[10:]
        corrupted["ciphertext"] = corrupted_bytes.hex()

        with pytest.raises(DecryptionError):
            decrypt_block_data(corrupted, key)

    @pytest.mark.unit
    def test_decrypt_block_data_corrupted_nonce(self):
        """Corrupted nonce should fail decryption"""
        key = secrets.token_bytes(32)
        data = {"test": "data"}

        encrypted = encrypt_block_data(data, key)

        # Corrupt nonce
        corrupted = encrypted.copy()
        corrupted["nonce"] = "000000000000000000000000"

        with pytest.raises(DecryptionError):
            decrypt_block_data(corrupted, key)


# ==============================================================================
# ENCRYPT/DECRYPT ROUND-TRIP TESTS
# ==============================================================================

class TestBlockEncryptionRoundTrip:
    """Test complete encryption → decryption workflows"""

    @pytest.mark.unit
    def test_round_trip_simple_data(self):
        """Simple data should round-trip successfully"""
        key = secrets.token_bytes(32)
        data = {"message": "Hello, World!"}

        encrypted = encrypt_block_data(data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_round_trip_complex_data(self):
        """Complex nested data should round-trip"""
        key = secrets.token_bytes(32)
        data = {
            "block_number": 42,
            "content": {
                "message": "test",
                "metadata": {
                    "timestamp": 1234567890,
                    "participants": ["qube1", "qube2"]
                }
            },
            "encrypted": True
        }

        encrypted = encrypt_block_data(data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_round_trip_unicode_data(self):
        """Unicode data should round-trip correctly"""
        key = secrets.token_bytes(32)
        data = {
            "message": "Hello 世界 🌍",
            "author": "Ñoño",
            "emoji": "🚀💻🔐"
        }

        encrypted = encrypt_block_data(data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_round_trip_empty_dict(self):
        """Empty dict should round-trip"""
        key = secrets.token_bytes(32)
        data = {}

        encrypted = encrypt_block_data(data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_round_trip_preserves_types(self):
        """Data types should be preserved"""
        key = secrets.token_bytes(32)
        data = {
            "int": 42,
            "float": 3.14,
            "str": "text",
            "bool": True,
            "list": [1, 2, 3],
            "null": None
        }

        encrypted = encrypt_block_data(data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == data
        assert type(decrypted["int"]) == int
        assert type(decrypted["float"]) == float
        assert type(decrypted["bool"]) == bool


# ==============================================================================
# RAW DATA ENCRYPTION TESTS
# ==============================================================================

class TestRawDataEncryption:
    """Test raw bytes encryption/decryption"""

    @pytest.mark.unit
    def test_encrypt_data_success(self):
        """Should encrypt raw bytes successfully"""
        key = secrets.token_bytes(32)
        data = b"Hello, World!"

        encrypted = encrypt_data(data, key)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > len(data)  # Includes nonce + auth tag
        assert encrypted != data

    @pytest.mark.unit
    def test_encrypt_data_nonce_included(self):
        """Encrypted data should include 12-byte nonce"""
        key = secrets.token_bytes(32)
        data = b"test data"

        encrypted = encrypt_data(data, key)

        # First 12 bytes are nonce
        nonce = encrypted[:12]
        assert len(nonce) == 12

    @pytest.mark.unit
    def test_encrypt_data_nonce_uniqueness(self):
        """Each encryption should use unique nonce"""
        key = secrets.token_bytes(32)
        data = b"test"

        encrypted1 = encrypt_data(data, key)
        encrypted2 = encrypt_data(data, key)

        # Different nonces
        assert encrypted1[:12] != encrypted2[:12]
        # Different ciphertexts
        assert encrypted1 != encrypted2

    @pytest.mark.unit
    def test_decrypt_data_success(self):
        """Should decrypt raw bytes successfully"""
        key = secrets.token_bytes(32)
        original = b"Hello, World!"

        encrypted = encrypt_data(original, key)
        decrypted = decrypt_data(encrypted, key)

        assert decrypted == original

    @pytest.mark.unit
    def test_decrypt_data_with_wrong_key(self):
        """Decryption with wrong key should fail"""
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)

        data = b"secret data"
        encrypted = encrypt_data(data, key1)

        with pytest.raises(DecryptionError):
            decrypt_data(encrypted, key2)

    @pytest.mark.unit
    def test_decrypt_data_corrupted(self):
        """Corrupted data should fail decryption"""
        key = secrets.token_bytes(32)
        data = b"test"

        encrypted = encrypt_data(data, key)

        # Corrupt ciphertext (after nonce)
        corrupted = bytearray(encrypted)
        corrupted[13] ^= 0xFF
        corrupted = bytes(corrupted)

        with pytest.raises(DecryptionError):
            decrypt_data(corrupted, key)


# ==============================================================================
# RAW DATA ROUND-TRIP TESTS
# ==============================================================================

class TestRawDataRoundTrip:
    """Test raw data encryption → decryption workflows"""

    @pytest.mark.unit
    def test_raw_round_trip_simple(self):
        """Simple bytes should round-trip"""
        key = secrets.token_bytes(32)
        data = b"Hello, World!"

        encrypted = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_raw_round_trip_empty(self):
        """Empty bytes should round-trip"""
        key = secrets.token_bytes(32)
        data = b""

        encrypted = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_raw_round_trip_large_data(self):
        """Large data should round-trip"""
        key = secrets.token_bytes(32)
        data = b"X" * 1024 * 100  # 100 KB

        encrypted = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key)

        assert decrypted == data

    @pytest.mark.unit
    def test_raw_round_trip_binary_data(self):
        """Binary data should round-trip"""
        key = secrets.token_bytes(32)
        data = bytes(range(256))  # All byte values

        encrypted = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key)

        assert decrypted == data


# ==============================================================================
# KEY DERIVATION TESTS
# ==============================================================================

class TestKeyDerivation:
    """Test HKDF key derivation"""

    @pytest.mark.unit
    def test_derive_block_key_success(self):
        """Should derive block-specific key"""
        master_key = secrets.token_bytes(32)

        block_key = derive_block_key(master_key, 1)

        assert isinstance(block_key, bytes)
        assert len(block_key) == 32

    @pytest.mark.unit
    def test_derive_block_key_deterministic(self):
        """Same inputs should produce same key"""
        master_key = secrets.token_bytes(32)

        key1 = derive_block_key(master_key, 1)
        key2 = derive_block_key(master_key, 1)

        assert key1 == key2

    @pytest.mark.unit
    def test_derive_block_key_unique_per_block(self):
        """Different block numbers should produce different keys"""
        master_key = secrets.token_bytes(32)

        key1 = derive_block_key(master_key, 1)
        key2 = derive_block_key(master_key, 2)
        key3 = derive_block_key(master_key, 100)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    @pytest.mark.unit
    def test_derive_block_key_unique_per_master(self):
        """Different master keys should produce different block keys"""
        master_key1 = secrets.token_bytes(32)
        master_key2 = secrets.token_bytes(32)

        key1 = derive_block_key(master_key1, 1)
        key2 = derive_block_key(master_key2, 1)

        assert key1 != key2

    @pytest.mark.unit
    def test_derive_block_key_with_encryption(self):
        """Derived key should work for encryption"""
        master_key = secrets.token_bytes(32)
        block_key = derive_block_key(master_key, 1)

        data = {"test": "data"}
        encrypted = encrypt_block_data(data, block_key)
        decrypted = decrypt_block_data(encrypted, block_key)

        assert decrypted == data


# ==============================================================================
# KEY GENERATION TESTS
# ==============================================================================

class TestKeyGeneration:
    """Test encryption key generation"""

    @pytest.mark.unit
    def test_generate_encryption_key_length(self):
        """Generated key should be 32 bytes"""
        key = generate_encryption_key()

        assert isinstance(key, bytes)
        assert len(key) == 32

    @pytest.mark.unit
    def test_generate_encryption_key_randomness(self):
        """Generated keys should be unique"""
        keys = [generate_encryption_key() for _ in range(10)]

        # All keys should be unique
        assert len(set(keys)) == 10

    @pytest.mark.unit
    def test_generate_encryption_key_works_with_encryption(self):
        """Generated key should work for encryption"""
        key = generate_encryption_key()
        data = {"test": "data"}

        encrypted = encrypt_block_data(data, key)
        decrypted = decrypt_block_data(encrypted, key)

        assert decrypted == data


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================

class TestErrorHandling:
    """Test error handling for edge cases"""

    @pytest.mark.unit
    def test_encrypt_with_invalid_key_size(self):
        """Encryption with invalid key size should fail"""
        key = secrets.token_bytes(15)  # Invalid size (AESGCM requires 16, 24, or 32)
        data = {"test": "data"}

        with pytest.raises(EncryptionError):
            encrypt_block_data(data, key)

    @pytest.mark.unit
    def test_decrypt_with_invalid_key_size(self):
        """Decryption with invalid key size should fail"""
        key_correct = secrets.token_bytes(32)
        key_invalid = secrets.token_bytes(15)  # Invalid size

        data = {"test": "data"}
        encrypted = encrypt_block_data(data, key_correct)

        with pytest.raises(DecryptionError):
            decrypt_block_data(encrypted, key_invalid)

    @pytest.mark.unit
    def test_decrypt_with_missing_fields(self):
        """Decryption with missing fields should fail"""
        key = secrets.token_bytes(32)

        # Missing nonce
        with pytest.raises(DecryptionError):
            decrypt_block_data({"ciphertext": "abc123"}, key)

        # Missing ciphertext
        with pytest.raises(DecryptionError):
            decrypt_block_data({"nonce": "abc123"}, key)

    @pytest.mark.unit
    def test_decrypt_with_invalid_hex(self):
        """Decryption with invalid hex should fail"""
        key = secrets.token_bytes(32)

        encrypted = {
            "ciphertext": "invalid_hex!@#",
            "nonce": "123456789012345678901234"
        }

        with pytest.raises(DecryptionError):
            decrypt_block_data(encrypted, key)

    @pytest.mark.unit
    def test_raw_decrypt_with_short_data(self):
        """Decrypting data shorter than nonce should fail"""
        key = secrets.token_bytes(32)
        short_data = b"short"  # Less than 12 bytes

        with pytest.raises(DecryptionError):
            decrypt_data(short_data, key)


# ==============================================================================
# SECURITY TESTS
# ==============================================================================

class TestEncryptionSecurity:
    """Test security properties"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_ciphertext_randomness(self):
        """Encrypting same data should produce different ciphertexts"""
        key = secrets.token_bytes(32)
        data = {"message": "test"}

        ciphertexts = [
            encrypt_block_data(data, key)["ciphertext"]
            for _ in range(10)
        ]

        # All ciphertexts should be unique (due to random nonces)
        assert len(set(ciphertexts)) == 10

    @pytest.mark.unit
    @pytest.mark.security
    def test_nonce_randomness(self):
        """Nonces should be unique across encryptions"""
        key = secrets.token_bytes(32)
        data = {"test": "data"}

        nonces = [
            encrypt_block_data(data, key)["nonce"]
            for _ in range(10)
        ]

        # All nonces should be unique
        assert len(set(nonces)) == 10

    @pytest.mark.unit
    @pytest.mark.security
    def test_authentication_prevents_tampering(self):
        """GCM authentication should detect tampering"""
        key = secrets.token_bytes(32)
        data = {"message": "important"}

        encrypted = encrypt_block_data(data, key)

        # Tamper with ciphertext
        ciphertext_bytes = bytes.fromhex(encrypted["ciphertext"])
        tampered_bytes = bytes([b ^ 0x01 for b in ciphertext_bytes[:10]]) + ciphertext_bytes[10:]
        encrypted["ciphertext"] = tampered_bytes.hex()

        # Should fail authentication
        with pytest.raises(DecryptionError):
            decrypt_block_data(encrypted, key)

    @pytest.mark.unit
    @pytest.mark.security
    def test_different_keys_cannot_decrypt(self):
        """Data encrypted with one key cannot be decrypted with another"""
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        data = {"secret": "data"}

        encrypted = encrypt_block_data(data, key1)

        with pytest.raises(DecryptionError):
            decrypt_block_data(encrypted, key2)

    @pytest.mark.unit
    @pytest.mark.security
    def test_block_key_isolation(self):
        """Block-specific keys should be isolated"""
        master_key = secrets.token_bytes(32)

        block1_key = derive_block_key(master_key, 1)
        block2_key = derive_block_key(master_key, 2)

        data = {"test": "data"}

        # Encrypt with block1 key
        encrypted = encrypt_block_data(data, block1_key)

        # Cannot decrypt with block2 key
        with pytest.raises(DecryptionError):
            decrypt_block_data(encrypted, block2_key)
