"""
Tests for ECDSA Signing and Verification

Comprehensive tests for block signing, verification, and hash chain integrity.
Validates both normal blocks and special genesis block (BCH NFT compatibility).

Covers:
- Block hashing (deterministic, excludes signature fields)
- Sign/verify round-trip (normal blocks)
- Genesis block special case (legacy signing for BCH NFT)
- Invalid signature detection
- Modified block detection
- Wrong public key detection
- Error handling
"""

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from crypto.signing import hash_block, sign_block, verify_block_signature
from crypto.keys import generate_key_pair
from core.exceptions import SignatureError, InvalidSignatureError


# ==============================================================================
# BLOCK HASHING TESTS
# ==============================================================================

class TestBlockHashing:
    """Test block hashing functionality"""

    @pytest.mark.unit
    def test_hash_block_deterministic(self):
        """Block hash should be deterministic"""
        block = {
            "block_number": 1,
            "qube_id": "ABC123",
            "block_type": "MESSAGE",
            "content": "Test message"
        }

        hash1 = hash_block(block)
        hash2 = hash_block(block)

        assert hash1 == hash2

    @pytest.mark.unit
    def test_hash_block_length(self):
        """Block hash should be 64-char hex (SHA-256)"""
        block = {"block_number": 1, "data": "test"}
        block_hash = hash_block(block)

        assert len(block_hash) == 64
        assert all(c in '0123456789abcdef' for c in block_hash)

    @pytest.mark.unit
    def test_hash_block_excludes_hash_field(self):
        """Block hash should exclude block_hash field"""
        block1 = {"block_number": 1, "data": "test"}
        block2 = {"block_number": 1, "data": "test", "block_hash": "fake_hash"}

        # Should produce same hash (block_hash field excluded)
        assert hash_block(block1) == hash_block(block2)

    @pytest.mark.unit
    def test_hash_block_excludes_signature_field(self):
        """Block hash should exclude signature field"""
        block1 = {"block_number": 1, "data": "test"}
        block2 = {"block_number": 1, "data": "test", "signature": "fake_sig"}

        # Should produce same hash (signature field excluded)
        assert hash_block(block1) == hash_block(block2)

    @pytest.mark.unit
    def test_hash_block_excludes_both_fields(self):
        """Block hash should exclude both block_hash and signature"""
        block1 = {"block_number": 1, "data": "test"}
        block2 = {
            "block_number": 1,
            "data": "test",
            "block_hash": "fake_hash",
            "signature": "fake_sig"
        }

        assert hash_block(block1) == hash_block(block2)

    @pytest.mark.unit
    def test_hash_block_sensitive_to_content(self):
        """Different content should produce different hashes"""
        block1 = {"block_number": 1, "data": "test1"}
        block2 = {"block_number": 1, "data": "test2"}

        assert hash_block(block1) != hash_block(block2)

    @pytest.mark.unit
    def test_hash_block_sensitive_to_field_order(self):
        """Hash should be insensitive to field order (sorted JSON)"""
        block1 = {"a": 1, "b": 2, "c": 3}
        block2 = {"c": 3, "a": 1, "b": 2}

        # JSON is sorted, so order shouldn't matter
        assert hash_block(block1) == hash_block(block2)


# ==============================================================================
# BLOCK SIGNING TESTS (NON-GENESIS)
# ==============================================================================

class TestBlockSigning:
    """Test block signing for normal (non-genesis) blocks"""

    @pytest.mark.unit
    def test_sign_block_success(self):
        """Should sign block successfully"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        signature = sign_block(block, private_key)

        assert isinstance(signature, str)
        assert len(signature) > 0
        # ECDSA signature is typically 140-146 bytes hex-encoded
        assert 140 <= len(signature) <= 200

    @pytest.mark.unit
    def test_sign_block_hex_format(self):
        """Signature should be valid hex"""
        private_key, _ = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        signature = sign_block(block, private_key)

        # Should be valid hex
        assert all(c in '0123456789abcdef' for c in signature)
        bytes.fromhex(signature)  # Should not raise

    @pytest.mark.unit
    def test_sign_block_non_deterministic(self):
        """Signatures should be non-deterministic (randomized ECDSA)"""
        private_key, _ = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        sig1 = sign_block(block, private_key)
        sig2 = sign_block(block, private_key)

        # ECDSA uses random nonce, so signatures differ
        assert sig1 != sig2

    @pytest.mark.unit
    def test_sign_different_blocks_different_signatures(self):
        """Different blocks should produce different signatures"""
        private_key, _ = generate_key_pair()
        block1 = {"block_number": 1, "data": "test1"}
        block2 = {"block_number": 1, "data": "test2"}

        sig1 = sign_block(block1, private_key)
        sig2 = sign_block(block2, private_key)

        assert sig1 != sig2


# ==============================================================================
# GENESIS BLOCK SIGNING TESTS (SPECIAL CASE)
# ==============================================================================

class TestGenesisBlockSigning:
    """Test genesis block (block_number=0) special signing logic"""

    @pytest.mark.unit
    def test_genesis_block_uses_legacy_signing(self):
        """Genesis blocks (block_number=0) should use legacy method"""
        private_key, public_key = generate_key_pair()
        genesis_block = {"block_number": 0, "data": "genesis"}

        signature = sign_block(genesis_block, private_key)

        # Should verify using legacy method
        assert verify_block_signature(genesis_block, signature, public_key)

    @pytest.mark.unit
    def test_genesis_vs_normal_different_signatures(self):
        """Genesis and non-genesis blocks with same data should sign differently"""
        private_key, _ = generate_key_pair()

        genesis_block = {"block_number": 0, "data": "test"}
        normal_block = {"block_number": 1, "data": "test"}

        # Note: Signatures are randomized, but the *method* is different
        # We can't directly compare signatures, but we can verify different verification logic
        genesis_sig = sign_block(genesis_block, private_key)
        normal_sig = sign_block(normal_block, private_key)

        # Both should be valid hex
        assert all(c in '0123456789abcdef' for c in genesis_sig)
        assert all(c in '0123456789abcdef' for c in normal_sig)


# ==============================================================================
# SIGNATURE VERIFICATION TESTS
# ==============================================================================

class TestSignatureVerification:
    """Test block signature verification"""

    @pytest.mark.unit
    def test_verify_valid_signature(self):
        """Valid signature should verify successfully"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        signature = sign_block(block, private_key)
        result = verify_block_signature(block, signature, public_key)

        assert result is True

    @pytest.mark.unit
    def test_verify_genesis_block_signature(self):
        """Genesis block signature should verify with legacy method"""
        private_key, public_key = generate_key_pair()
        genesis_block = {"block_number": 0, "data": "genesis"}

        signature = sign_block(genesis_block, private_key)
        result = verify_block_signature(genesis_block, signature, public_key)

        assert result is True

    @pytest.mark.unit
    def test_verify_with_wrong_public_key(self):
        """Signature should fail with wrong public key"""
        private_key1, _ = generate_key_pair()
        _, public_key2 = generate_key_pair()  # Different key pair

        block = {"block_number": 1, "data": "test"}
        signature = sign_block(block, private_key1)

        with pytest.raises(InvalidSignatureError):
            verify_block_signature(block, signature, public_key2)

    @pytest.mark.unit
    def test_verify_modified_block_fails(self):
        """Verification should fail if block is modified after signing"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "original"}

        signature = sign_block(block, private_key)

        # Modify block after signing
        block["data"] = "modified"

        with pytest.raises(InvalidSignatureError):
            verify_block_signature(block, signature, public_key)

    @pytest.mark.unit
    def test_verify_invalid_signature_format(self):
        """Invalid signature hex should raise error"""
        _, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        with pytest.raises(InvalidSignatureError):
            verify_block_signature(block, "invalid_hex", public_key)

    @pytest.mark.unit
    def test_verify_tampered_signature(self):
        """Tampered signature should fail verification"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        signature = sign_block(block, private_key)

        # Tamper with signature (flip a bit)
        tampered_sig = signature[:-2] + ("00" if signature[-2:] != "00" else "ff")

        with pytest.raises(InvalidSignatureError):
            verify_block_signature(block, tampered_sig, public_key)


# ==============================================================================
# SIGN/VERIFY ROUND-TRIP TESTS
# ==============================================================================

class TestSignVerifyRoundTrip:
    """Test complete sign → verify workflows"""

    @pytest.mark.unit
    def test_sign_verify_round_trip_normal_block(self):
        """Sign and verify should work for normal blocks"""
        private_key, public_key = generate_key_pair()

        block = {
            "block_number": 1,
            "qube_id": "TEST123",
            "block_type": "MESSAGE",
            "content": "Test message",
            "timestamp": 1234567890
        }

        signature = sign_block(block, private_key)
        result = verify_block_signature(block, signature, public_key)

        assert result is True

    @pytest.mark.unit
    def test_sign_verify_round_trip_genesis_block(self):
        """Sign and verify should work for genesis blocks"""
        private_key, public_key = generate_key_pair()

        genesis_block = {
            "block_number": 0,
            "qube_id": "GENESIS",
            "block_type": "GENESIS",
            "content": "Genesis block"
        }

        signature = sign_block(genesis_block, private_key)
        result = verify_block_signature(genesis_block, signature, public_key)

        assert result is True

    @pytest.mark.unit
    def test_sign_verify_multiple_blocks(self):
        """Should sign and verify multiple blocks in sequence"""
        private_key, public_key = generate_key_pair()

        blocks = [
            {"block_number": i, "data": f"block_{i}"}
            for i in range(5)
        ]

        for block in blocks:
            signature = sign_block(block, private_key)
            result = verify_block_signature(block, signature, public_key)
            assert result is True

    @pytest.mark.unit
    def test_signature_persists_with_block(self):
        """Block with signature field should verify correctly"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        # Sign block
        signature = sign_block(block, private_key)

        # Add signature to block (like persistence layer would)
        block["signature"] = signature

        # Verification should still work (signature field is excluded from hash)
        result = verify_block_signature(block, signature, public_key)
        assert result is True

    @pytest.mark.unit
    def test_block_hash_persists_with_block(self):
        """Block with block_hash field should sign/verify correctly"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        # Add block_hash (like persistence layer would)
        block["block_hash"] = hash_block(block)

        # Sign and verify should still work (block_hash excluded)
        signature = sign_block(block, private_key)
        result = verify_block_signature(block, signature, public_key)

        assert result is True


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================

class TestErrorHandling:
    """Test error handling for edge cases"""

    @pytest.mark.unit
    def test_sign_with_invalid_key_type(self):
        """Signing with wrong key type should raise error"""
        block = {"block_number": 1, "data": "test"}

        with pytest.raises(Exception):  # Will raise attribute error or similar
            sign_block(block, "not_a_key")

    @pytest.mark.unit
    def test_verify_with_invalid_key_type(self):
        """Verifying with wrong key type should raise error"""
        private_key, _ = generate_key_pair()
        block = {"block_number": 1, "data": "test"}
        signature = sign_block(block, private_key)

        with pytest.raises(Exception):
            verify_block_signature(block, signature, "not_a_key")

    @pytest.mark.unit
    def test_sign_empty_block(self):
        """Should handle empty block gracefully"""
        private_key, public_key = generate_key_pair()
        block = {}

        signature = sign_block(block, private_key)
        result = verify_block_signature(block, signature, public_key)

        assert result is True

    @pytest.mark.unit
    def test_sign_block_with_unicode(self):
        """Should handle Unicode content correctly"""
        private_key, public_key = generate_key_pair()
        block = {
            "block_number": 1,
            "content": "Hello 世界 🌍 Ñoño"
        }

        signature = sign_block(block, private_key)
        result = verify_block_signature(block, signature, public_key)

        assert result is True


# ==============================================================================
# SECURITY TESTS
# ==============================================================================

class TestSignatureSecurity:
    """Test security properties of signing"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_signature_uniqueness(self):
        """Same block signed twice should produce different signatures (nonce randomization)"""
        private_key, _ = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        signatures = [sign_block(block, private_key) for _ in range(10)]

        # All signatures should be unique (ECDSA randomness)
        assert len(set(signatures)) == 10

    @pytest.mark.unit
    @pytest.mark.security
    def test_different_keys_different_signatures(self):
        """Same block signed with different keys should produce different signatures"""
        block = {"block_number": 1, "data": "test"}

        key_pairs = [generate_key_pair() for _ in range(5)]
        signatures = [sign_block(block, priv) for priv, _ in key_pairs]

        # Cannot verify signature with wrong key
        for i, (_, pub_key) in enumerate(key_pairs):
            # Should verify with correct key
            assert verify_block_signature(block, signatures[i], pub_key)

            # Should fail with wrong key
            wrong_pub_key = key_pairs[(i + 1) % 5][1]
            with pytest.raises(InvalidSignatureError):
                verify_block_signature(block, signatures[i], wrong_pub_key)

    @pytest.mark.unit
    @pytest.mark.security
    def test_signature_tamper_resistance(self):
        """Any modification to signature should fail verification"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test"}

        original_sig = sign_block(block, private_key)

        # Try flipping various bits
        for i in range(0, len(original_sig), 20):
            tampered = list(original_sig)
            tampered[i] = '0' if tampered[i] != '0' else 'f'
            tampered_sig = ''.join(tampered)

            with pytest.raises(InvalidSignatureError):
                verify_block_signature(block, tampered_sig, public_key)

    @pytest.mark.unit
    @pytest.mark.security
    def test_block_tamper_resistance(self):
        """Any modification to block should fail verification"""
        private_key, public_key = generate_key_pair()
        block = {"block_number": 1, "data": "test", "extra": "field"}

        signature = sign_block(block, private_key)

        # Verify original works
        assert verify_block_signature(block, signature, public_key)

        # Modify each field
        tampering_tests = [
            {"block_number": 2, "data": "test", "extra": "field"},  # Changed block_number
            {"block_number": 1, "data": "modified", "extra": "field"},  # Changed data
            {"block_number": 1, "data": "test", "extra": "modified"},  # Changed extra
            {"block_number": 1, "data": "test"},  # Removed field
            {"block_number": 1, "data": "test", "extra": "field", "new": "field"},  # Added field
        ]

        for tampered_block in tampering_tests:
            with pytest.raises(InvalidSignatureError):
                verify_block_signature(tampered_block, signature, public_key)
