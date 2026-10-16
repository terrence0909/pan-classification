"""
constants.py
------------
Domain constants for South African banking PAN classification.
Encodes real SA BIN ranges, SARB reporting qualifiers, and ISO 8583
response codes used in the BankservAfrica ACB clearing format.
"""

# --- South African Bank BIN Ranges ---
# These are real issuer identification numbers used by SA banks.
SA_BIN_RANGES = {
    # Capitec Bank
    "528497": {"bank": "CAPITEC", "scheme": "MASTERCARD", "card_type": "DEBIT"},
    "528498": {"bank": "CAPITEC", "scheme": "MASTERCARD", "card_type": "CREDIT"},
    # Standard Bank
    "512055": {"bank": "STANDARD BANK", "scheme": "MASTERCARD", "card_type": "CREDIT"},
    "432557": {"bank": "STANDARD BANK", "scheme": "VISA", "card_type": "DEBIT"},
    # Nedbank
    "432557": {"bank": "NEDBANK", "scheme": "VISA", "card_type": "CREDIT"},
    "377090": {"bank": "NEDBANK", "scheme": "AMEX", "card_type": "CREDIT"},
    # Absa
    "400001": {"bank": "ABSA", "scheme": "VISA", "card_type": "DEBIT"},
    "510001": {"bank": "ABSA", "scheme": "MASTERCARD", "card_type": "CREDIT"},
    # First National Bank (FNB)
    "400002": {"bank": "FNB", "scheme": "VISA", "card_type": "DEBIT"},
    "510002": {"bank": "FNB", "scheme": "MASTERCARD", "card_type": "CREDIT"},
    # Rand Merchant Bank (RMB)
    "491050": {"bank": "RMB", "scheme": "VISA", "card_type": "DEBIT"},
    # TymeBank
    "528499": {"bank": "TYMEBANK", "scheme": "MASTERCARD", "card_type": "DEBIT"},
    # Discovery Bank
    "400003": {"bank": "DISCOVERY BANK", "scheme": "VISA", "card_type": "CREDIT"},
}

# --- SARB FinSurv Reporting Qualifiers ---
# Used in BOPCARD RESIDENT module for regulatory reporting[citation:16].
REPORTING_QUALIFIERS = [
    "BOPCARD RESIDENT",
    "BOPCARD NON RESIDENT",
]

# --- SA Provinces (for address fields) ---
SA_PROVINCES = [
    "GAUTENG", "LIMPOPO", "NORTH WEST", "WESTERN CAPE",
    "EASTERN CAPE", "NORTHERN CAPE", "FREE STATE",
    "MPUMALANGA", "KWAZULU NATAL",
]

# --- ISO 8583 Response Codes (subset) ---
RESPONSE_CODES = {
    "00": "APPROVED",
    "05": "DECLINE",
    "51": "INSUFFICIENT FUNDS",
    "54": "EXPIRED CARD",
    "91": "ISSUER INOPERATIVE",
    "14": "INVALID CARD NUMBER",
    "43": "STOLEN CARD",
}

# --- POS Entry Modes ---
POS_ENTRY_MODES = ["05", "07", "91", "10"]  # Chip, contactless, manual, ecommerce

# --- Currency ---
CURRENCY_CODE = "ZAR"

# --- PAN Variant Distribution (realistic mix) ---
# 40% full, 35% masked, 20% truncated, 5% null
PAN_VARIANT_WEIGHTS = {
    "FULL_PAN": 0.40,
    "MASKED": 0.35,
    "TRUNCATED": 0.20,
    "NULL": 0.05,
}