"""
luhn.py
-------
Implements the Luhn algorithm for PAN validation.
A full PAN passes Luhn. Masked and truncated PANs fail Luhn
because digits are missing or replaced.
"""

def luhn_check_digit(number: str) -> int:
    """
    Calculate the Luhn check digit for a partial number (without check digit).
    Used during generation to create valid full PANs.
    """
    digits = [int(d) for d in number]
    # Double every second digit from the right (starting from the check position)
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    total = sum(digits)
    return (10 - (total % 10)) % 10


def is_luhn_valid(number: str) -> bool:
    """
    Validate whether a full number passes the Luhn checksum.
    Returns True if the number is structurally a valid PAN format.
    Returns False for masked, truncated, or invalid numbers.
    """
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    total = 0
    # Process from right to left
    reverse = digits[::-1]
    for i, digit in enumerate(reverse):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return total % 10 == 0