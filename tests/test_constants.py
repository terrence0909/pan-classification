"""Structural tests for the constants module."""
from src.utils.constants import (
    SA_BIN_RANGES,
    RESPONSE_CODES,
    POS_ENTRY_MODES,
    CURRENCY_CODE,
    REPORTING_QUALIFIERS,
    SA_PROVINCES,
    PAN_VARIANT_WEIGHTS,
)


class TestSaBinRanges:
    def test_all_bins_are_six_digits(self):
        for bin_prefix in SA_BIN_RANGES:
            assert len(bin_prefix) == 6
            assert bin_prefix.isdigit()

    def test_all_bins_have_required_fields(self):
        required = {"bank", "scheme", "card_type"}
        for bin_prefix, info in SA_BIN_RANGES.items():
            assert required.issubset(info.keys()), f"{bin_prefix} missing fields"

    def test_covers_major_sa_banks(self):
        banks = {info["bank"] for info in SA_BIN_RANGES.values()}
        expected = {"CAPITEC", "STANDARD BANK", "NEDBANK", "ABSA", "FNB", "RMB"}
        assert expected.issubset(banks)


class TestResponseCodes:
    def test_codes_are_two_chars(self):
        for code in RESPONSE_CODES:
            assert len(code) == 2
            assert code.isdigit()

    def test_every_code_has_description(self):
        for code, description in RESPONSE_CODES.items():
            assert description and isinstance(description, str)

    def test_approved_code_present(self):
        assert "00" in RESPONSE_CODES
        assert RESPONSE_CODES["00"] == "APPROVED"


class TestOtherConstants:
    def test_currency_is_zar(self):
        assert CURRENCY_CODE == "ZAR"

    def test_variant_weights_sum_to_one(self):
        assert abs(sum(PAN_VARIANT_WEIGHTS.values()) - 1.0) < 1e-9

    def test_provinces_are_non_empty(self):
        assert len(SA_PROVINCES) == 9  # SA has 9 provinces
        for p in SA_PROVINCES:
            assert isinstance(p, str) and len(p) > 0

    def test_reporting_qualifiers_are_non_empty(self):
        assert len(REPORTING_QUALIFIERS) >= 1
        for q in REPORTING_QUALIFIERS:
            assert q.startswith("BOPCARD")

    def test_pos_entry_modes_are_non_empty(self):
        assert len(POS_ENTRY_MODES) >= 1
        for mode in POS_ENTRY_MODES:
            assert isinstance(mode, str)