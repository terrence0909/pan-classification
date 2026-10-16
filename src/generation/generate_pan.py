"""
generate_pan.py
---------------
Generates the four PAN variants that a bank's source systems produce:
FULL_PAN, MASKED, TRUNCATED, NULL.
"""
import random
from src.utils.constants import SA_BIN_RANGES
from src.utils.luhn import luhn_check_digit


def generate_full_pan(bin_prefix: str, length: int = 16) -> str:
    """Generate a Luhn-valid PAN with the given BIN prefix."""
    if len(bin_prefix) >= length:
        raise ValueError("BIN prefix must be shorter than PAN length")

    # Generate random middle digits
    middle_length = length - len(bin_prefix) - 1  # -1 for check digit
    middle = "".join(str(random.randint(0, 9)) for _ in range(middle_length))

    # Calculate check digit
    partial = bin_prefix + middle
    check = str(luhn_check_digit(partial))

    return partial + check


def mask_pan(pan: str) -> str:
    """
    Mask a PAN per PCI DSS: first 6 digits visible, last 4 visible,
    everything in between replaced with '*'.
    """
    if len(pan) < 10:
        return pan
    return pan[:6] + "*" * (len(pan) - 10) + pan[-4:]


def truncate_pan(pan: str) -> str:
    """
    Truncate a PAN: only the last 4 digits remain.
    Digits are removed, not replaced—so Luhn fails.
    """
    return "*" * (len(pan) - 4) + pan[-4:]


def generate_pan_variant() -> tuple[str, str]:
    """
    Returns (pan_value, variant_type) where variant_type is one of
    FULL_PAN, MASKED, TRUNCATED, NULL.
    """
    # Pick a random SA BIN
    bin_prefix = random.choice(list(SA_BIN_RANGES.keys()))

    # Generate the full PAN first
    full_pan = generate_full_pan(bin_prefix)

    # Decide which variant to return based on realistic weights
    variant = random.choices(
        ["FULL_PAN", "MASKED", "TRUNCATED", "NULL"],
        weights=[0.40, 0.35, 0.20, 0.05],
    )[0]

    if variant == "FULL_PAN":
        return full_pan, variant
    elif variant == "MASKED":
        return mask_pan(full_pan), variant
    elif variant == "TRUNCATED":
        return truncate_pan(full_pan), variant
    else:
        return None, variant