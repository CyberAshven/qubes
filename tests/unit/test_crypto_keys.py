"""
Tests for Cryptographic Key Management

Comprehensive tests for ECDSA secp256k1 key pair operations, serialization,
Qube ID derivation, and password-based key encryption.

Covers:
- Key pair generation (secp256k1)
- Public/private key serialization (PEM, compressed hex)
- Qube ID derivation from public key
- Password-based key derivation (PBKDF2)
- Private key encryption/decryption with Fernet
- Backward compatibility with legacy iteration counts
- Error handling and security
"""

import pytest
import base64
from cryptography.hazmat.primitives.asymmetric import ec

from crypto.keys import (
    generate_key_pair,
    serialize_private_key,
    serialize_public_key,
    deserialize_private_key,
    deserialize_public_key,
    derive_qube_id,
    derive_master_key_from_password,
    encrypt_private_key,
    decrypt_private_key
)
from core.exceptions import (
    KeyGenerationError,
    EncryptionError,
    DecryptionError,
    CryptoError
)


# ==============================================================================
# KEY GENERATION TESTS
# ==============================================================================

class TestKeyGeneration:
    """Test ECDSA secp256k1 key pair generation"""

    @pytest.mark.unit
    def test_generate_key_pair_success(self):
        """Should generate valid ECDSA secp256k1 key pair"""
        private_key, public_key = generate_key_pair()

        assert private_key is not None
        assert public_key is not None
        assert isinstance(private_key, ec.EllipticCurvePrivateKey)
        assert isinstance(public_key, ec.EllipticCurvePublicKey)

    @pytest.mark.unit
    def test_generate_key_pair_uses_secp256k1(self):
        """Should use secp256k1 curve (Bitcoin-compatible)"""
        private_key, public_key = generate_key_pair()

        # Verify curve type
        assert isinstance(private_key.curve, ec.SECP256K1)
        assert isinstance(public_key.curve, ec.SECP256K1)

    @pytest.mark.unit
    def test_generate_key_pair_creates_unique_keys(self):
        """Each call should generate different keys"""
        priv1, pub1 = generate_key_pair()
        priv2, pub2 = generate_key_pair()

        # Serialize to compare
        priv1_bytes = serialize_private_key(priv1)
        priv2_bytes = serialize_private_key(priv2)

        assert priv1_bytes != priv2_bytes  # Different private keys
        assert serialize_public_key(pub1) != serialize_public_key(pub2)  # Different public keys

    @pytest.mark.unit
    def test_public_key_derived_from_private(self):
        """Public key should be derivable from private key"""
        private_key, public_key = generate_key_pair()

        # Derive public key from private
        derived_public = private_key.public_key()

        # Compare serialized forms (should be identical)
        assert serialize_public_key(public_key) == serialize_public_key(derived_public)


# ==============================================================================
# SERIALIZATION TESTS
# ==============================================================================

class TestKeySerialization:
    """Test key serialization and deserialization"""

    @pytest.mark.unit
    def test_serialize_private_key_pem_format(self):
        """Private key should serialize to PEM format"""
        private_key, _ = generate_key_pair()

        pem_bytes = serialize_private_key(private_key)

        assert isinstance(pem_bytes, bytes)
        assert pem_bytes.startswith(b'-----BEGIN PRIVATE KEY-----')
        assert pem_bytes.endswith(b'-----END PRIVATE KEY-----\n')

    @pytest.mark.unit
    def test_serialize_public_key_compressed_format(self):
        """Public key should serialize to compressed hex (33 bytes = 66 hex chars)"""
        _, public_key = generate_key_pair()

        hex_str = serialize_public_key(public_key)

        assert isinstance(hex_str, str)
        assert len(hex_str) == 66  # 33 bytes * 2 hex chars
        assert hex_str.startswith('02') or hex_str.startswith('03')  # Compression prefix

    @pytest.mark.unit
    def test_private_key_round_trip(self):
        """Private key should survive serialization round-trip"""
        private_key, _ = generate_key_pair()

        # Serialize
        pem_bytes = serialize_private_key(private_key)

        # Deserialize
        restored_key = deserialize_private_key(pem_bytes)

        # Compare (should be identical)
        assert serialize_private_key(private_key) == serialize_private_key(restored_key)

    @pytest.mark.unit
    def test_public_key_round_trip(self):
        """Public key should survive serialization round-trip"""
        _, public_key = generate_key_pair()

        # Serialize
        hex_str = serialize_public_key(public_key)

        # Deserialize
        restored_key = deserialize_public_key(hex_str)

        # Compare (should be identical)
        assert serialize_public_key(public_key) == serialize_public_key(restored_key)

    @pytest.mark.unit
    def test_deserialize_invalid_private_key(self):
        """Should raise CryptoError for invalid PEM"""
        invalid_pem = b"not a valid PEM key"

        with pytest.raises(CryptoError) as exc_info:
            deserialize_private_key(invalid_pem)

        assert "Failed to deserialize private key" in str(exc_info.value)

    @pytest.mark.unit
    def test_deserialize_invalid_public_key(self):
        """Should raise CryptoError for invalid hex"""
        invalid_hex = "not_valid_hex"

        with pytest.raises(CryptoError) as exc_info:
            deserialize_public_key(invalid_hex)

        assert "Failed to deserialize public key" in str(exc_info.value)


# ==============================================================================
# QUBE ID DERIVATION TESTS
# ==============================================================================

class TestQubeIDDerivation:
    """Test Qube ID derivation from public key"""

    @pytest.mark.unit
    def test_derive_qube_id_format(self):
        """Qube ID should be 8-character uppercase hex string"""
        _, public_key = generate_key_pair()

        qube_id = derive_qube_id(public_key)

        assert isinstance(qube_id, str)
        assert len(qube_id) == 8
        assert qube_id.isupper()
        assert all(c in '0123456789ABCDEF' for c in qube_id)

    @pytest.mark.unit
    def test_derive_qube_id_deterministic(self):
        """Same public key should always produce same Qube ID"""
        private_key, public_key = generate_key_pair()

        qube_id1 = derive_qube_id(public_key)
        qube_id2 = derive_qube_id(public_key)

        assert qube_id1 == qube_id2

    @pytest.mark.unit
    def test_derive_qube_id_unique_for_different_keys(self):
        """Different public keys should produce different Qube IDs"""
        _, pub1 = generate_key_pair()
        _, pub2 = generate_key_pair()

        id1 = derive_qube_id(pub1)
        id2 = derive_qube_id(pub2)

        assert id1 != id2

    @pytest.mark.unit
    def test_derive_qube_id_after_round_trip(self):
        """Qube ID should be same after key serialization round-trip"""
        _, public_key = generate_key_pair()

        # Get original ID
        original_id = derive_qube_id(public_key)

        # Serialize and deserialize
        hex_str = serialize_public_key(public_key)
        restored_key = deserialize_public_key(hex_str)

        # Get ID from restored key
        restored_id = derive_qube_id(restored_key)

        assert original_id == restored_id


# ==============================================================================
# PASSWORD-BASED KEY DERIVATION TESTS
# ==============================================================================

class TestPasswordKeyDerivation:
    """Test PBKDF2 master key derivation"""

    @pytest.mark.unit
    def test_derive_master_key_format(self):
        """Master key should be 44-character base64 string (32 bytes)"""
        password = "test_password_123"
        salt = b"sixteen_bytes!16"

        master_key = derive_master_key_from_password(password, salt)

        assert isinstance(master_key, bytes)
        assert len(master_key) == 44  # 32 bytes base64-encoded

    @pytest.mark.unit
    def test_derive_master_key_deterministic(self):
        """Same password and salt should produce same key"""
        password = "test_password_123"
        salt = b"sixteen_bytes!16"

        key1 = derive_master_key_from_password(password, salt)
        key2 = derive_master_key_from_password(password, salt)

        assert key1 == key2

    @pytest.mark.unit
    def test_derive_master_key_different_password(self):
        """Different passwords should produce different keys"""
        salt = b"sixteen_bytes!16"

        key1 = derive_master_key_from_password("password1", salt)
        key2 = derive_master_key_from_password("password2", salt)

        assert key1 != key2

    @pytest.mark.unit
    def test_derive_master_key_different_salt(self):
        """Different salts should produce different keys"""
        password = "test_password_123"

        key1 = derive_master_key_from_password(password, b"salt_number_one!")
        key2 = derive_master_key_from_password(password, b"salt_number_two!")

        assert key1 != key2

    @pytest.mark.unit
    def test_derive_master_key_custom_iterations(self):
        """Should support custom iteration counts"""
        password = "test_password_123"
        salt = b"sixteen_bytes!16"

        # Different iteration counts should produce different keys
        key_100k = derive_master_key_from_password(password, salt, iterations=100000)
        key_600k = derive_master_key_from_password(password, salt, iterations=600000)

        assert key_100k != key_600k


# ==============================================================================
# PRIVATE KEY ENCRYPTION TESTS
# ==============================================================================

class TestPrivateKeyEncryption:
    """Test private key encryption and decryption"""

    @pytest.mark.unit
    def test_encrypt_private_key_structure(self):
        """Encrypted data should have required fields"""
        private_key, _ = generate_key_pair()
        password = "strong_master_password"

        encrypted_data = encrypt_private_key(private_key, password)

        assert isinstance(encrypted_data, dict)
        assert "encrypted_key" in encrypted_data
        assert "salt" in encrypted_data
        assert "kdf" in encrypted_data
        assert "iterations" in encrypted_data
        assert encrypted_data["kdf"] == "PBKDF2-SHA256"
        assert encrypted_data["iterations"] == 600000  # OWASP 2025 recommendation

    @pytest.mark.unit
    def test_encrypt_private_key_base64_encoding(self):
        """Encrypted key and salt should be base64-encoded"""
        private_key, _ = generate_key_pair()
        password = "strong_master_password"

        encrypted_data = encrypt_private_key(private_key, password)

        # Should be valid base64
        try:
            base64.b64decode(encrypted_data["encrypted_key"])
            base64.b64decode(encrypted_data["salt"])
        except Exception:
            pytest.fail("Encrypted data should be valid base64")

    @pytest.mark.unit
    def test_encrypt_decrypt_round_trip(self):
        """Private key should survive encryption/decryption round-trip"""
        private_key, _ = generate_key_pair()
        password = "strong_master_password"

        # Encrypt
        encrypted_data = encrypt_private_key(private_key, password)

        # Decrypt
        decrypted_key = decrypt_private_key(encrypted_data, password)

        # Compare (should be identical)
        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)

    @pytest.mark.unit
    def test_decrypt_with_wrong_password(self):
        """Decryption with wrong password should raise DecryptionError"""
        private_key, _ = generate_key_pair()

        encrypted_data = encrypt_private_key(private_key, "correct_password")

        with pytest.raises(DecryptionError) as exc_info:
            decrypt_private_key(encrypted_data, "wrong_password")

        assert "Failed to decrypt private key" in str(exc_info.value)

    @pytest.mark.unit
    def test_encrypt_with_custom_salt(self):
        """Should support custom salt for deterministic testing"""
        private_key, _ = generate_key_pair()
        password = "test_password"
        custom_salt = b"sixteen_bytes!16"

        encrypted1 = encrypt_private_key(private_key, password, salt=custom_salt)
        encrypted2 = encrypt_private_key(private_key, password, salt=custom_salt)

        # Salt should be the same
        assert encrypted1["salt"] == encrypted2["salt"]

        # Both should decrypt to same key (Fernet adds timestamp, so ciphertext differs)
        decrypted1 = decrypt_private_key(encrypted1, password)
        decrypted2 = decrypt_private_key(encrypted2, password)
        assert serialize_private_key(decrypted1) == serialize_private_key(decrypted2)

    @pytest.mark.unit
    def test_encrypt_with_random_salt(self):
        """Without custom salt, should use random salt"""
        private_key, _ = generate_key_pair()
        password = "test_password"

        encrypted1 = encrypt_private_key(private_key, password)
        encrypted2 = encrypt_private_key(private_key, password)

        # Random salts should produce different encrypted data
        assert encrypted1["encrypted_key"] != encrypted2["encrypted_key"]
        assert encrypted1["salt"] != encrypted2["salt"]

    @pytest.mark.unit
    def test_decrypt_backward_compatibility_old_iterations(self):
        """Should decrypt keys encrypted with old iteration count (100K)"""
        private_key, _ = generate_key_pair()
        password = "test_password"

        # Simulate old encrypted data (100K iterations)
        salt = b"sixteen_bytes!16"
        master_key = derive_master_key_from_password(password, salt, iterations=100000)
        from cryptography.fernet import Fernet
        cipher = Fernet(master_key)
        encrypted = cipher.encrypt(serialize_private_key(private_key))

        old_encrypted_data = {
            "encrypted_key": base64.b64encode(encrypted).decode(),
            "salt": base64.b64encode(salt).decode(),
            # No "iterations" field (backward compat test)
        }

        # Should successfully decrypt with old iteration count
        decrypted_key = decrypt_private_key(old_encrypted_data, password)

        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)

    @pytest.mark.unit
    def test_decrypt_with_explicit_iterations_field(self):
        """Should use explicit iterations field when present"""
        private_key, _ = generate_key_pair()
        password = "test_password"

        # Encrypt with 600K iterations (new format)
        encrypted_data = encrypt_private_key(private_key, password)

        # Should decrypt successfully with explicit iterations
        decrypted_key = decrypt_private_key(encrypted_data, password)

        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)

    @pytest.mark.unit
    def test_decrypt_corrupted_data(self):
        """Should raise DecryptionError for corrupted encrypted data"""
        private_key, _ = generate_key_pair()
        password = "test_password"

        encrypted_data = encrypt_private_key(private_key, password)

        # Corrupt the encrypted key
        encrypted_data["encrypted_key"] = "corrupted_base64_data!!!"

        with pytest.raises(DecryptionError):
            decrypt_private_key(encrypted_data, password)


# ==============================================================================
# SECURITY TESTS
# ==============================================================================

class TestSecurityProperties:
    """Test security properties of key management"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_different_passwords_produce_different_encrypted_keys(self):
        """Different passwords should produce different encrypted outputs"""
        private_key, _ = generate_key_pair()
        salt = b"sixteen_bytes!16"  # Use same salt to isolate password effect

        encrypted1 = encrypt_private_key(private_key, "password1", salt=salt)
        encrypted2 = encrypt_private_key(private_key, "password2", salt=salt)

        assert encrypted1["encrypted_key"] != encrypted2["encrypted_key"]

    @pytest.mark.unit
    @pytest.mark.security
    def test_salt_randomness(self):
        """Generated salts should be unique"""
        private_key, _ = generate_key_pair()
        password = "test_password"

        salts = []
        for _ in range(10):
            encrypted = encrypt_private_key(private_key, password)
            salts.append(encrypted["salt"])

        # All salts should be unique
        assert len(set(salts)) == 10

    @pytest.mark.unit
    @pytest.mark.security
    def test_qube_id_collision_resistance(self):
        """Qube IDs should be highly unlikely to collide"""
        # Generate 1000 Qube IDs and check for collisions
        qube_ids = set()

        for _ in range(1000):
            _, public_key = generate_key_pair()
            qube_id = derive_qube_id(public_key)
            qube_ids.add(qube_id)

        # Should have 1000 unique IDs (no collisions)
        assert len(qube_ids) == 1000

    @pytest.mark.unit
    @pytest.mark.security
    def test_private_key_not_in_public_serialization(self):
        """Serialized public key should not contain private key data"""
        private_key, public_key = generate_key_pair()

        public_hex = serialize_public_key(public_key)
        private_pem = serialize_private_key(private_key).decode()

        # Public key hex should be shorter than private key PEM
        assert len(public_hex) < len(private_pem)

        # Public hex should not contain private key material
        assert "PRIVATE KEY" not in public_hex

        # Public key should be exactly 66 hex chars (33 bytes compressed)
        assert len(public_hex) == 66


# ==============================================================================
# EDGE CASES TESTS
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_empty_password(self):
        """Should handle empty password (though not recommended)"""
        private_key, _ = generate_key_pair()
        password = ""

        encrypted_data = encrypt_private_key(private_key, password)
        decrypted_key = decrypt_private_key(encrypted_data, password)

        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)

    @pytest.mark.unit
    def test_very_long_password(self):
        """Should handle very long passwords"""
        private_key, _ = generate_key_pair()
        password = "x" * 1000  # 1000 character password

        encrypted_data = encrypt_private_key(private_key, password)
        decrypted_key = decrypt_private_key(encrypted_data, password)

        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)

    @pytest.mark.unit
    def test_unicode_password(self):
        """Should handle Unicode passwords"""
        private_key, _ = generate_key_pair()
        password = "pässwörd_🔐_密码"

        encrypted_data = encrypt_private_key(private_key, password)
        decrypted_key = decrypt_private_key(encrypted_data, password)

        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)

    @pytest.mark.unit
    def test_special_characters_in_password(self):
        """Should handle special characters in passwords"""
        private_key, _ = generate_key_pair()
        password = "p@$$w0rd!#%&*()[]{}|;:',.<>?/`~"

        encrypted_data = encrypt_private_key(private_key, password)
        decrypted_key = decrypt_private_key(encrypted_data, password)

        assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)
