# PAN Classification Pipeline

A production-grade data engineering project that classifies card **Primary Account Numbers (PANs)** from South African bank transaction feeds into four types: **FULL_PAN**, **MASKED**, **TRUNCATED**, and **NULL**.

Built to mirror the data-quality challenges the South African Reserve Bank (SARB) faces when receiving mixed card data from commercial banks — where some records contain full PANs (a PCI compliance risk) and others are masked or truncated for display.

![Architecture](docs/architecture.svg)

## The Problem

When banks feed transaction records to downstream systems — analytics, monitoring, regulatory reporting — the PAN field is inconsistent:

- Some records carry the **full 16-digit PAN**, valid per ISO/IEC 7812 and passing the Luhn checksum.
- Some records are **masked** for display (first 6 + last 4 visible), per PCI DSS.
- Some records are **truncated** — digits are physically removed, not replaced.
- Some records are **null**.

Downstream systems cannot distinguish these cases reliably. A fraud model that treats a masked PAN as a full one will produce garbage. A regulatory report that counts masked PANs as full ones will overstate PCI compliance risk.

This pipeline solves the classification problem at scale, with a verified **100% accuracy** against ground-truth labels.

## Architecture
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Local Generation │───▶│ Unity Catalog │───▶│ Auto Loader │
│ (Python + Parquet)│ │ Volume │ │ (cloudFiles) │
└────────────────────┘ └────────────────────┘ └────────────────────┘
│
▼
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Quality Metrics │◀───│ PAN Classification│◀───│ Delta Lake │
│ (SQL) │ │ (Spark SQL + │ │ pan_raw │
│ │ │ luhn_check UDF) │ │ │
└────────────────────┘ └────────────────────┘ └────────────────────┘

text

**Flow:**

1. **Generate** synthetic bank feeds locally with a realistic mix of PAN variants and South African BIN ranges.
2. **Upload** Parquet batches to a Unity Catalog Volume.
3. **Ingest** incrementally with Auto Loader into a Delta table.
4. **Classify** using Spark SQL's built-in `luhn_check` UDF plus pattern rules.
5. **Measure** accuracy against ground-truth labels and validate BIN coverage.

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Generation | Python 3.14, pandas, pyarrow | Fast, well-understood, writes Parquet natively |
| Storage | Unity Catalog Volume (S3-backed) | Managed, governed, ideal for lakehouse |
| Ingestion | Databricks Auto Loader (`cloudFiles`) | Incremental, schema-aware, checkpointed |
| Storage format | Delta Lake | ACID, time-travel, schema evolution |
| Transformation | Spark SQL | Distributed, includes native `luhn_check` |
| Auth | OAuth (U2M) via Databricks CLI | Token-free local development |
| Environment | Databricks Free Edition | Serverless, no infrastructure to manage |

## Key Design Decisions

### 1. Rule ordering in the classification logic

Masked and truncated PANs **both contain asterisk characters**, so a naive rule order misclassifies every truncated record as masked. The first run produced **79.10% accuracy** because of this.

The fix: order the rules according to the **business definition**, not the syntax:

- **Truncated** — the BIN prefix is removed. Detect by checking whether the first 6 characters are all mask characters (`SUBSTR(pan, 1, 6) RLIKE '^[xX*]{6}$'`).
- **Masked** — the BIN prefix is visible. Detect by checking for mask characters *after* the truncation check has failed.

This change took accuracy from **79.10% → 100.00%**.

### 2. OAuth over Personal Access Tokens

Databricks Free Edition restricts PAT usage. The pipeline uses **OAuth user-to-machine** authentication via the Databricks CLI, storing credentials in `~/.databrickscfg`. No tokens are stored in code, `.env`, or version control.

### 3. Ground-truth verification

Every generated record carries a `pan_variant` label. The classification pipeline compares its output against this label, producing a measurable accuracy metric rather than an unverified claim.

### 4. BIN validation as a second-order quality control

Beyond classification, the pipeline validates that extracted BINs belong to known South African issuers. This catches foreign cards, test data, and new issuers — exactly the kind of control SARB oversight demands.

## Results

| Metric | Value |
|--------|-------|
| Total records classified | 1,000 |
| Classification accuracy | **100.00%** |
| FULL_PAN records | 371 |
| FULL_PAN with known SA issuer BIN | **100%** |
| Distinct SA BINs covered | 12 |
| Ingestion method | Auto Loader (`availableNow`) |
| Runtime (classification) | ~3 seconds |

## Getting Started

### Prerequisites

- Python 3.11+
- A Databricks Free Edition workspace
- Databricks CLI installed and authenticated (`databricks auth login`)

### Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd pan-classification

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Databricks host, HTTP path, catalog, and profile
Run the Pipeline

bash
# 1. Generate 1,000 synthetic PAN records locally
python -m src.generation.build_batch 1000 1

# 2. Upload the batch to a Unity Catalog Volume
python -m src.ingestion.upload_to_databricks

# 3. Run the Databricks notebooks (in order)
databricks workspace import "/Workspace/Users/<you>/pan-classification/01_autoloader_ingest" \
  --file databricks/notebooks/01_autoloader_ingest.py --language PYTHON --format SOURCE --overwrite

databricks workspace import "/Workspace/Users/<you>/pan-classification/02_pan_classification" \
  --file databricks/notebooks/02_pan_classification.sql --language SQL --format SOURCE --overwrite
Then open each notebook in the Databricks workspace and click Run all.

Run Tests

bash
pytest tests/ -v
Project Structure

text
.
├── databricks/
│   └── notebooks/
│       ├── 01_autoloader_ingest.py       # Auto Loader: Volume → Delta
│       └── 02_pan_classification.sql     # Classification + accuracy check
├── docs/
│   └── architecture.md                   # Deeper design notes
├── src/
│   ├── generation/
│   │   ├── build_batch.py                # Batch orchestrator
│   │   └── generate_pan.py               # PAN variant generator
│   ├── ingestion/
│   │   └── upload_to_databricks.py       # Volume upload via SDK
│   └── utils/
│       ├── constants.py                  # SA BIN ranges, SARB qualifiers
│       └── luhn.py                       # Luhn algorithm (local)
└── tests/
    └── test_luhn.py                      # Unit tests for Luhn
What I'd Do Next

Scheduling — Databricks Workflows to run ingestion and classification on a schedule
dbt — refactor transformation into dbt models with tests and lineage
Streaming — replace batch generation with a Kafka producer for real-time classification
Anomaly detection — flag PANs whose BIN doesn't match the expected issuer bank
Sensitive data governance — apply Unity Catalog row filters and column masks to the full PAN column in production
Author

Tshepo Tau — built as a portfolio project for data engineering roles in South African financial services.

License

MIT