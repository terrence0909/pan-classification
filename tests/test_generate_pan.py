"""
Unit tests for PAN variant generation.

The generator produces three variants:
- FULL_PAN: Luhn-valid 16-digit PAN
- MASKED:   first 6 + last 4 visible, middle replaced with *
- TRUNCATED: only last 4 visible, all else replaced with *
"""
import pytest

from src.utils.constants import SA_BIN_RANGES
from src.utils.luhn import is_luhn_valid
from src.generation.generate_pan import (
    generate_full_pan,
    mask_pan,
    truncate_pan,
    generate_pan_variant,
)


class TestGenerateFullPan:
    def test_returns_16_digit_pan(self):
        for bin_prefix in SA_BIN_RANGES:
            pan = generate_full_pan(bin_prefix)
            assert len(pan) == 16
            assert pan.isdigit()
            assert pan.startswith(bin_prefix)

    def test_pan_passes_luhn(self):
        for bin_prefix in SA_BIN_RANGES:
            for _ in range(10):
                pan = generate_full_pan(bin_prefix)
                assert is_luhn_valid(pan) is True

    def test_rejects_bin_longer_than_pan(self):
        with pytest.raises(ValueError):
            generate_full_pan("12345678901234567890")

    def test_multiple_pans_are_unique(self):
        """Probabilistic check — two PANs from the same BIN should differ."""
        pans = {generate_full_pan("528497") for _ in range(50)}
        assert len(pans) > 1


class TestMaskPan:
    def test_first_six_and_last_four_visible(self):
        pan = "5284971234567890"
        masked = mask_pan(pan)
        assert masked[:6] == "528497"
        assert masked[-4:] == "7890"
        assert masked[6:-4] == "*" * 6

    def test_short_pan_unchanged(self):
        """PAN shorter than 10 chars can't be meaningfully masked."""
        short = "12345"
        assert mask_pan(short) == short


class TestTruncatePan:
    def test_only_last_four_visible(self):
        pan = "5284971234567890"
        truncated = truncate_pan(pan)
        assert truncated[-4:] == "7890"
        assert truncated[:-4] == "*" * (len(pan) - 4)

    def test_first_six_are_masks(self):
        """Critical for the classification rule: truncation removes the BIN."""
        truncated = truncate_pan("5284971234567890")
        assert truncated[:6] == "******"


class TestGeneratePanVariant:
    def test_variant_is_one_of_four(self):
        allowed = {"FULL_PAN", "MASKED", "TRUNCATED", "NULL"}
        for _ in range(100):
            pan, variant = generate_pan_variant()
            assert variant in allowed

    def test_null_variant_returns_none(self):
        # Run repeatedly until we hit a NULL variant
        for _ in range(200):
            pan, variant = generate_pan_variant()
            if variant == "NULL":
                assert pan is None
                return
        pytest.skip("Did not generate NULL in 200 attempts")

    def test_full_pan_variant_is_luhn_valid(self):
        for _ in range(100):
            pan, variant = generate_pan_variant()
            if variant == "FULL_PAN":
                assert is_luhn_valid(pan) is True

    def test_masked_variant_has_bin_visible(self):
        for _ in range(100):
            pan, variant = generate_pan_variant()
            if variant == "MASKED":
                assert pan[:6].isdigit()

    def test_truncated_variant_has_bin_hidden(self):
        for _ in range(100):
            pan, variant = generate_pan_variant()
            if variant == "TRUNCATED":
                assert pan[:6] == "******"

    def test_distribution_is_roughly_correct(self):
        """Over many draws, variant distribution should approximate the weights."""
        from collections import Counter
        counts = Counter()
        n = 2000
        for _ in range(n):
            _, variant = generate_pan_variant()
            counts[variant] += 1

        # FULL_PAN target 40%, allow ±5 percentage points
        assert 0.35 <= counts["FULL_PAN"] / n <= 0.45
        # MASKED target 35%
        assert 0.30 <= counts["MASKED"] / n <= 0.40
        # TRUNCATED target 20%
        assert 0.15 <= counts["TRUNCATED"] / n <= 0.25
        # NULL target 5%
        assert 0.02 <= counts["NULL"] / n <= 0.10