# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Auto Loader Ingestion: PAN Raw
# MAGIC
# MAGIC Incrementally ingests Parquet batches from the Unity Catalog volume
# MAGIC into a Delta table using Databricks Auto Loader (`cloudFiles`).
# MAGIC
# MAGIC **Source:** `/Volumes/pan_classification/default/pan_data/raw/`
# MAGIC **Target:** `pan_classification.default.pan_raw`
# MAGIC
# MAGIC **Design notes:**
# MAGIC - `trigger(availableNow=True)` processes all pending files then stops,
# MAGIC   making this safe to schedule without leaving a cluster running.
# MAGIC - Schema inference is used on first run; subsequent files must match
# MAGIC   or be added via schema evolution (`mergeSchema`).
# MAGIC - The checkpoint location persists processed-file state, so re-runs
# MAGIC   only ingest *new* files.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configuration

# COMMAND ----------

CATALOG = "pan_classification"
SCHEMA = "default"
TABLE = "pan_raw"

SOURCE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/pan_data/raw/"
CHECKPOINT_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/pan_data/_checkpoints/pan_raw/"
SCHEMA_LOCATION = f"/Volumes/{CATALOG}/{SCHEMA}/pan_data/_schemas/pan_raw/"

TARGET_TABLE = f"{CATALOG}.{SCHEMA}.{TABLE}"

print(f"Source:     {SOURCE_PATH}")
print(f"Target:     {TARGET_TABLE}")
print(f"Checkpoint: {CHECKPOINT_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Read as a stream with Auto Loader

# COMMAND ----------

from pyspark.sql import functions as F

raw_stream = (
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("cloudFiles.schemaLocation", SCHEMA_LOCATION)
        # Add ingestion metadata so we can trace lineage
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .load(SOURCE_PATH)
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Write the stream to a Delta table
# MAGIC
# MAGIC `availableNow=True` makes this a one-shot microbatch that processes
# MAGIC every pending file and then terminates — ideal for scheduled ingestion.

# COMMAND ----------

(
    raw_stream.writeStream
        .format("delta")
        .option("checkpointLocation", CHECKPOINT_PATH)
        .option("mergeSchema", "true")
        .trigger(availableNow=True)
        .toTable(TARGET_TABLE)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Verify

# COMMAND ----------

row_count = spark.sql(f"SELECT COUNT(*) AS n FROM {TARGET_TABLE}").collect()[0]["n"]
print(f"Rows in {TARGET_TABLE}: {row_count:,}")

# COMMAND ----------

display(
    spark.sql(f"""
        SELECT pan_variant, COUNT(*) AS records
        FROM {TARGET_TABLE}
        GROUP BY pan_variant
        ORDER BY records DESC
    """)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Sample rows

# COMMAND ----------

display(
    spark.sql(f"""
        SELECT pan, pan_variant, bin, issuer_bank, card_scheme,
               transaction_amount, _ingested_at
        FROM {TARGET_TABLE}
        LIMIT 20
    """)
)