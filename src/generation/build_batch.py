"""
build_batch.py
--------------
Orchestrates PAN batch generation and writes Parquet files for
ingestion into Databricks. Each batch is a realistic extract from
a bank source system destined for SARB.
"""
import os
import random
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.utils.constants import (
    SA_BIN_RANGES,
    RESPONSE_CODES,
    POS_ENTRY_MODES,
    CURRENCY_CODE,
    REPORTING_QUALIFIERS,
    SA_PROVINCES,
)
from src.generation.generate_pan import generate_pan_variant


def generate_batch(size: int, batch_id: int, output_dir: str = "data/raw"):
    """Generate `size` transaction records and write to a Parquet file."""
    records = []

    for _ in range(size):
        pan_value, variant = generate_pan_variant()

        # Extract BIN if PAN is not fully masked at the start
        if pan_value and not pan_value.startswith("*"):
            bin_prefix = pan_value[:6]
            bank_info = SA_BIN_RANGES.get(bin_prefix, {"bank": "UNKNOWN", "scheme": "UNKNOWN"})
        else:
            bin_prefix = None
            bank_info = {"bank": None, "scheme": None}

        record = {
            # --- Core transaction identifiers ---
            "record_identifier": "04",
            "pan": pan_value,
            "pan_variant": variant,  # Ground truth for validation (not sent to SARB)
            "card_scheme": bank_info.get("scheme"),
            "bin": bin_prefix,
            "issuer_bank": bank_info.get("bank"),

            # --- Amount & currency ---
            "transaction_amount": round(random.uniform(10, 5000), 2),
            "currency_code": CURRENCY_CODE,

            # --- Date & time ---
            "transaction_date": date.today(),
            "transaction_time": datetime.now().strftime("%H:%M:%S"),

            # --- Merchant & terminal ---
            "merchant_id": f"MERCH{random.randint(100000, 999999)}",
            "merchant_name": random.choice([
                "SPAZA SHOP", "TAXI ASSOC", "STOKVEL GROUP",
                "LOCAL GROCER", "FUEL STATION", "PHARMACY"
            ]),
            "terminal_id": f"TERM{random.randint(1, 50):03d}",
            "acquirer_id": f"ACQ{random.randint(1, 10):03d}",

            # --- Transaction mechanics ---
            "retrieval_reference": f"{random.randint(10**11, 10**12 - 1)}",
            "auth_code": f"{random.randint(100000, 999999)}",
            "response_code": random.choice(list(RESPONSE_CODES.keys())),
            "pos_entry_mode": random.choice(POS_ENTRY_MODES),
            "card_present": random.choice([True, False]),

            # --- SARB regulatory fields ---
            "reporting_qualifier": random.choice(REPORTING_QUALIFIERS),
            "province": random.choice(SA_PROVINCES),
        }
        records.append(record)

    df = pd.DataFrame(records)

    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Write to Parquet with date-based partitioning
    today = date.today().isoformat()
    filename = f"batch_{today}_{batch_id:04d}.parquet"
    filepath = os.path.join(output_dir, filename)
    df.to_parquet(filepath, index=False, engine="pyarrow")

    print(f"✓ Generated {len(df)} records → {filepath}")
    print(f"  Variant breakdown: {df['pan_variant'].value_counts().to_dict()}")
    return filepath


if __name__ == "__main__":
    import sys
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    batch_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    generate_batch(size, batch_id)