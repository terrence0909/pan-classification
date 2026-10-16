# PAN Classification Pipeline

![CI](https://github.com/terrence0909/pan-classification/actions/workflows/ci.yml/badge.svg)

An end-to-end data engineering project that classifies card **Primary Account Numbers (PANs)** from South African bank transaction feeds into four types: **FULL_PAN**, **MASKED**, **TRUNCATED**, and **NULL**.

It is built to mirror the data-quality challenges the South African Reserve Bank (SARB) faces when receiving mixed card data from commercial banks, where some records contain full PANs (a PCI compliance risk) and others are masked or truncated for display.

> **Note:** All data in this project is synthetic. Accuracy figures are measured against labels produced by the project's own data generator, not against real bank data.

## The Problem

When banks feed transaction records to downstream systems (analytics, monitoring, regulatory reporting), the PAN field is inconsistent:

- Some records carry the **full 16-digit PAN**, valid per ISO/IEC 7812 and passing the Luhn checksum.
- Some records are **masked** for display (first 6 and last 4 digits visible), per PCI DSS.
- Some records are **truncated**: the leading digits (the BIN) are hidden, so the first six characters are mask characters and the issuer cannot be identified.
- Some records are **null**.

Downstream systems cannot tell these cases apart reliably. A fraud model that treats a masked PAN as a full one will produce bad results. A regulatory report that counts masked PANs as full ones will overstate PCI compliance risk.

This pipeline classifies each record automatically and measures its own accuracy against ground-truth labels.

## Architecture

![Architecture](docs/architecture.svg)

**Flow:**

1. **Generate** synthetic bank feeds locally, with a realistic mix of PAN variants and South African BIN ranges.
2. **Upload** Parquet batches to a Unity Catalog Volume.
3. **Ingest** incrementally with Auto Loader into a Delta table.
4. **Classify** using Spark SQL's built-in `luhn_check` function plus pattern rules.
5. **Measure** accuracy against ground-truth labels and validate BIN coverage.

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Generation | Python 3.11+, pandas, pyarrow | Fast, well-understood, writes Parquet natively |
| Storage | Unity Catalog Volume (S3-backed) | Managed, governed, well suited to a lakehouse |
| Ingestion | Databricks Auto Loader (`cloudFiles`) | Incremental, schema-aware, checkpointed |
| Storage format | Delta Lake | ACID transactions, time travel, schema evolution |
| Transformation | Spark SQL | Distributed, includes native `luhn_check` |
| Orchestration | Databricks Workflows | Serverless, dependency-managed |
| Auth | OAuth (U2M) via Databricks CLI | Token-free local development |
| CI | GitHub Actions | Multi-version testing on every push |
| Environment | Databricks Free Edition | Serverless, no infrastructure to manage |

## Key Design Decisions

### 1. Rule ordering in the classification logic

Masked and truncated PANs **both contain asterisk characters**, so a naive rule order labels every truncated record as masked. The first run produced **79.10% accuracy** because of this.

The fix is to order the rules by the **business definition**, not the syntax:

- **Truncated**: the BIN prefix is hidden. Detect it by checking whether the first 6 characters are all mask characters (`SUBSTR(pan, 1, 6) RLIKE '^[xX*]{6}$'`).
- **Masked**: the BIN prefix is visible. Detect it by checking for mask characters *after* the truncation check has failed.

This change took accuracy from **79.10% to 100.00%**. See [Lessons Learned](#lessons-learned) for the takeaway.

### 2. OAuth over Personal Access Tokens

Databricks Free Edition restricts PAT usage for external SDK access. The pipeline uses **OAuth user-to-machine (U2M)** authentication via the Databricks CLI, with credentials stored in `~/.databrickscfg`. No tokens are stored in code, `.env` files, or version control.

### 3. Ground-truth verification

Every generated record carries a `pan_variant` label. The classification step compares its output against this label, which gives a measurable accuracy figure instead of an unverified claim.

### 4. BIN validation as a second quality check

Beyond classification, the pipeline checks that extracted BINs belong to known South African issuers. This catches foreign cards, test data, and new issuers, which is the kind of control regulatory oversight calls for.

## Results

**Classification accuracy:** 100.00% (1,000 synthetic records, checked against the generator's ground-truth labels)

**Data breakdown:**

| Variant | Records | % |
|---------|---------|---|
| FULL_PAN | 371 | 37.1% |
| MASKED | 373 | 37.3% |
| TRUNCATED | 209 | 20.9% |
| NULL | 47 | 4.7% |

**BIN validation:** 100% of FULL_PAN records matched a known South African issuer BIN, across 8 banks (Capitec, Absa, FNB, Standard Bank, Nedbank, RMB, TymeBank, Discovery).

**Pipeline timing** (serverless, Standard mode, 1,000 records):

| Task | Duration |
|------|----------|
| `ingest` | ~57s |
| `classify` | ~24s |
| **Total (includes cold start)** | **~3m 42s** |

**Test suite:** 50 tests, 100% coverage on the measured modules (`luhn.py`, `constants.py`, `generate_pan.py`). CI runs on Python 3.11, 3.12, and 3.13.

## Scheduling

The pipeline runs as a **Databricks Workflow** on a daily schedule (02:00 SAST). The job definition lives at `databricks/workflows/pan_classification_job.json` and is deployed with the Databricks CLI:

```bash
databricks jobs create --json @databricks/workflows/pan_classification_job.json
```

The workflow has two sequential tasks:

1. **`ingest`** runs `01_autoloader_ingest`, picking up any new Parquet files from the Unity Catalog Volume.
2. **`classify`** runs `02_pan_classification`, rebuilding the `pan_classified` table and computing accuracy metrics.

Task 2 depends on Task 1, so classification only runs after a successful ingest. Failure notifications are sent to the configured email address.

### Performance mode trade-off

The workflow is deployed in **Standard** performance mode on serverless compute. On a 1,000-record batch this means:

| Mode | End-to-end | Notes |
|------|------------|-------|
| Performance-Optimized | ~1m 27s | Default; faster cold start |
| Standard | ~3m 42s | Lower cost; slower cold start |

The classification itself takes about 24s. Serverless cold start dominates the total time. For a daily batch job, the two-minute difference doesn't matter and the lower cost does, so Standard mode is the better fit.

## Getting Started

### Prerequisites

- Python 3.11 or newer
- A Databricks Free Edition workspace
- Databricks CLI installed and authenticated (`databricks auth login`)

### Setup

```bash
# Clone and enter the project
git clone https://github.com/terrence0909/pan-classification.git
cd pan-classification

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Databricks host, HTTP path, catalog, and OAuth profile name
```

### Run the Pipeline

```bash
# 1. Generate 1,000 synthetic PAN records locally
python -m src.generation.build_batch 1000 1

# 2. Upload the batch to a Unity Catalog Volume
python -m src.ingestion.upload_to_databricks

# 3. Import the notebooks into Databricks
databricks workspace import \
  "/Workspace/Users/<you>/pan-classification/01_autoloader_ingest" \
  --file databricks/notebooks/01_autoloader_ingest.py \
  --language PYTHON --format SOURCE --overwrite

databricks workspace import \
  "/Workspace/Users/<you>/pan-classification/02_pan_classification" \
  --file databricks/notebooks/02_pan_classification.sql \
  --language SQL --format SOURCE --overwrite

# 4. Or deploy the full workflow at once
databricks jobs create --json @databricks/workflows/pan_classification_job.json
```

### Run Tests

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml                        # GitHub Actions CI
├── databricks/
│   ├── notebooks/
│   │   ├── 01_autoloader_ingest.py       # Auto Loader: Volume -> Delta
│   │   └── 02_pan_classification.sql     # Classification + accuracy check
│   └── workflows/
│       ├── pan_classification_job.json   # Databricks Job definition
│       └── README.md                     # Workflow deployment guide
├── docs/
│   ├── architecture.md                   # Deeper design notes
│   └── architecture.svg                  # Diagram
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
    ├── test_constants.py                 # Structural tests
    ├── test_generate_pan.py              # Generator tests
    └── test_luhn.py                      # Luhn validation tests
```

## Lessons Learned

### Rule order in SQL is a business rule

The first version of the classification logic scored 79.10%, with 209 records misclassified. Because masked and truncated PANs both contain asterisks, the first matching `CASE` branch claimed every truncated record as masked. Putting the truncation check first fixed it (details in [Key Design Decisions](#1-rule-ordering-in-the-classification-logic)).

The takeaway: when patterns overlap, the order of the checks should follow the domain meaning, not just what is easiest to write.

### Why OAuth over Personal Access Tokens

Databricks Free Edition restricts PAT usage for external SDK access, so the project uses OAuth U2M through the Databricks CLI. No tokens appear in the code, `.env`, or Git history. It is also a safer habit for working against governed workspaces.

### Cost discipline

The workflow runs in Standard performance mode instead of the default Performance-Optimized. For a daily batch of 1,000 records, the slower start is negligible and the saving is worthwhile. Serverless compute is used throughout with `trigger(availableNow=True)`, so compute shuts down as soon as each task finishes.

## What I'd Do Next

- **dbt:** refactor the transformation into dbt models with tests and lineage
- **Streaming:** replace batch generation with a Kafka producer for real-time classification
- **Anomaly detection:** flag PANs whose BIN doesn't match the expected issuer bank
- **Sensitive data governance:** apply Unity Catalog row filters and column masks to the full PAN column in production
- **Ingestion tests:** mock the Databricks SDK to test `upload_to_databricks.py`
- **Trend monitoring:** track classification accuracy over time in a dashboard

## Author

**Tshepo Tau**: data engineering portfolio project focused on South African financial services.

- GitHub: [@terrence0909](https://github.com/terrence0909)
- Repo: [pan-classification](https://github.com/terrence0909/pan-classification)

## License

MIT