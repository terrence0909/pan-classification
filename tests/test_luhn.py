"""
Unit tests for the Luhn algorithm implementation.

The Luhn check is the backbone of PAN classification. If it's wrong,
every FULL_PAN classification is suspect. These tests cover:

- Known good and bad PANs
- Edge cases (empty, non-numeric, wrong length)
- The check-digit generator
- Round-trip: generate a PAN, then verify it
"""
import pytest

from src.utils.luhn import luhn_check_digit, is_luhn_valid


# ---------- is_luhn_valid ----------

class TestIsLuhnValid:
    """Verify the validation function against known test vectors."""

    @pytest.mark.parametrize("pan", [
        "4111111111111111",   # classic Visa test PAN
        "4242424242424242",   # Stripe test Visa
        "5555555555554444",   # Mastercard test PAN
        "378282246310005",    # American Express test PAN
        "6011111111111117",   # Discover test PAN
        "4000011629514976",   # our generator's ABSA Visa output
        "5284976850413227",   # our generator's Capitec Mastercard output
        "4910503701885356",   # our generator's RMB Visa output
    ])
    def test_valid_pans_pass(self, pan):
        assert is_luhn_valid(pan) is True

    @pytest.mark.parametrize("pan", [
        "4111111111111112",   # last digit altered
        "4242424242424243",   # last digit altered
        "1234567890123456",   # random digits, almost certainly invalid
        "0000000000000001",   # leading zeros, invalid checksum
    ])
    def test_invalid_pans_fail(self, pan):
        assert is_luhn_valid(pan) is False

    @pytest.mark.parametrize("pan", [
        "411111******1111",   # masked — contains non-digits
        "************1111",   # truncated — contains non-digits
        "4111-1111-1111-1111", # dashes — our function strips them
    ])
    def test_masked_and_truncated_fail(self, pan):
        """Masked and truncated PANs must fail Luhn."""
        # Note: dashes are stripped, so this should actually pass
        if "-" in pan:
            assert is_luhn_valid(pan) is True
        else:
            assert is_luhn_valid(pan) is False

    def test_empty_string_fails(self):
        assert is_luhn_valid("") is False

    def test_none_handling(self):
        # Function expects a string; passing None should not crash silently
        with pytest.raises((TypeError, AttributeError)):
            is_luhn_valid(None)

    @pytest.mark.parametrize("pan", [
        "123456789012",        # 12 digits — too short
        "12345678901234567890", # 20 digits — too long
    ])
    def test_wrong_length_fails(self, pan):
        assert is_luhn_valid(pan) is False


# ---------- luhn_check_digit ----------

class TestLuhnCheckDigit:
    """Verify the check-digit calculation produces Luhn-valid PANs."""

    @pytest.mark.parametrize("partial,expected", [
        ("411111111111111", 1),   # classic Visa: check digit is 1
        ("424242424242424", 2),   # Stripe Visa: check digit is 2
        ("555555555555444", 4),   # Mastercard: check digit is 4
    ])
    def test_known_check_digits(self, partial, expected):
        assert luhn_check_digit(partial) == expected

    def test_generated_pans_are_valid(self):
        """Round-trip: any PAN built with luhn_check_digit must pass is_luhn_valid."""
        import random
        random.seed(42)  # deterministic
        for _ in range(100):
            partial = "".join(str(random.randint(0, 9)) for _ in range(15))
            check = str(luhn_check_digit(partial))
            full_pan = partial + check
            assert is_luhn_valid(full_pan) is True


# ---------- classification boundary cases ----------

class TestClassificationBoundaries:
    """
    Sanity check the boundary between FULL_PAN and INVALID.
    A 13-digit PAN is the shortest valid length; a 12-digit is not.
    """

    def test_13_digit_pan_accepted(self):
        # Build a 13-digit valid PAN
        partial = "4111111111111"
        full = partial[:12]  # 12 digits
        check = str(luhn_check_digit(full))
        thirteen_digit_pan = full + check
        assert len(thirteen_digit_pan) == 13
        assert is_luhn_valid(thirteen_digit_pan) is True

    def test_12_digit_pan_rejected(self):
        # Even if Luhn-valid, 12 digits is below the ISO/IEC 7812 minimum
        partial = "41111111111"
        check = str(luhn_check_digit(partial))
        twelve_digit = partial + check
        assert len(twelve_digit) == 12
        assert is_luhn_valid(twelve_digit) is False