"""
Unit tests for Official Qubes Category ID validation

Tests the core validation logic that enforces the official category ID
as a consensus rule for the Qubes network.
"""

import pytest
from core.official_category import (
    OFFICIAL_QUBES_CATEGORY,
    is_official_qube,
    validate_official_qube,
)


class TestOfficialCategory:
    """Tests for official category constant"""

    def test_official_category_is_64_hex_chars(self):
        """Official category ID should be 64 hex characters (32 bytes)"""
        assert len(OFFICIAL_QUBES_CATEGORY) == 64
        assert all(c in "0123456789abcdef" for c in OFFICIAL_QUBES_CATEGORY.lower())

    def test_official_category_is_lowercase(self):
        """Official category ID should be stored in lowercase"""
        assert OFFICIAL_QUBES_CATEGORY == OFFICIAL_QUBES_CATEGORY.lower()


class TestIsOfficialQube:
    """Tests for is_official_qube() function"""

    def test_official_category_returns_true(self):
        """Official category ID should return True"""
        assert is_official_qube(OFFICIAL_QUBES_CATEGORY) is True

    def test_official_category_uppercase_returns_true(self):
        """Case-insensitive: uppercase official category should return True"""
        assert is_official_qube(OFFICIAL_QUBES_CATEGORY.upper()) is True

    def test_official_category_mixed_case_returns_true(self):
        """Case-insensitive: mixed case should return True"""
        mixed = OFFICIAL_QUBES_CATEGORY[:32].upper() + OFFICIAL_QUBES_CATEGORY[32:].lower()
        assert is_official_qube(mixed) is True

    def test_unofficial_category_returns_false(self):
        """Unofficial category ID should return False"""
        fake_category = "abcd1234" * 8  # 64 chars but not official
        assert is_official_qube(fake_category) is False

    def test_all_zeros_returns_false(self):
        """All zeros category should return False"""
        zeros = "0" * 64
        assert is_official_qube(zeros) is False

    def test_all_fs_returns_false(self):
        """All f's category should return False"""
        all_fs = "f" * 64
        assert is_official_qube(all_fs) is False

    def test_none_returns_false(self):
        """None should return False"""
        assert is_official_qube(None) is False

    def test_empty_string_returns_false(self):
        """Empty string should return False"""
        assert is_official_qube("") is False

    def test_pending_minting_returns_false(self):
        """'pending_minting' placeholder should return False"""
        assert is_official_qube("pending_minting") is False

    def test_partial_match_returns_false(self):
        """Partial match (prefix) should return False"""
        partial = OFFICIAL_QUBES_CATEGORY[:32]
        assert is_official_qube(partial) is False

    def test_similar_category_returns_false(self):
        """Category differing by one character should return False"""
        # Change last character
        similar = OFFICIAL_QUBES_CATEGORY[:-1] + ("0" if OFFICIAL_QUBES_CATEGORY[-1] != "0" else "1")
        assert is_official_qube(similar) is False


class TestValidateOfficialQube:
    """Tests for validate_official_qube() function"""

    def test_official_category_does_not_raise(self):
        """Official category should not raise exception"""
        validate_official_qube(OFFICIAL_QUBES_CATEGORY)  # Should not raise

    def test_official_category_uppercase_does_not_raise(self):
        """Uppercase official category should not raise"""
        validate_official_qube(OFFICIAL_QUBES_CATEGORY.upper())  # Should not raise

    def test_unofficial_category_raises_valueerror(self):
        """Unofficial category should raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_official_qube("fake_category_id")
        assert "not the official Qubes category" in str(exc_info.value)
        assert "not a Qube" in str(exc_info.value)

    def test_none_raises_valueerror(self):
        """None should raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_official_qube(None)
        assert "None" in str(exc_info.value)

    def test_empty_string_raises_valueerror(self):
        """Empty string should raise ValueError"""
        with pytest.raises(ValueError):
            validate_official_qube("")

    def test_context_included_in_error_message(self):
        """Context parameter should be included in error message"""
        with pytest.raises(ValueError) as exc_info:
            validate_official_qube("fake", context="P2P handshake")
        assert "P2P handshake" in str(exc_info.value)

    def test_category_preview_in_error_message(self):
        """Category ID preview should be in error message"""
        long_fake = "a" * 64
        with pytest.raises(ValueError) as exc_info:
            validate_official_qube(long_fake)
        # Should show first 16 chars + "..."
        assert "aaaaaaaaaaaaaaaa..." in str(exc_info.value)

    def test_no_context_no_during_in_message(self):
        """Without context, 'during' should not appear in message"""
        with pytest.raises(ValueError) as exc_info:
            validate_official_qube("fake")
        assert " during " not in str(exc_info.value)
