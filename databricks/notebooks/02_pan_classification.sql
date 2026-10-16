-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 02 — PAN Classification
-- MAGIC
-- MAGIC Classifies each record in `pan_raw` into one of five types:
-- MAGIC `FULL_PAN`, `MASKED`, `TRUNCATED`, `NULL`, or `INVALID`.
-- MAGIC
-- MAGIC **Input:**  `pan_classification.default.pan_raw`
-- MAGIC **Output:** `pan_classification.default.pan_classified`
-- MAGIC
-- MAGIC **Rule ordering matters.** Masked and truncated PANs both contain
-- MAGIC `*` characters, so we check truncation first (based on whether the
-- MAGIC BIN prefix is visible) before falling back to the mask check.
-- MAGIC Otherwise every truncated PAN would be misclassified as masked.
-- MAGIC
-- MAGIC **Rule order:**
-- MAGIC 1. `NULL` — empty or missing PAN
-- MAGIC 2. `TRUNCATED` — first 6 characters are all mask chars (no visible BIN)
-- MAGIC 3. `MASKED` — BIN visible but mask chars appear later
-- MAGIC 4. `FULL_PAN` — numeric value passes the Luhn checksum
-- MAGIC 5. `INVALID` — none of the above (malformed)
-- MAGIC
-- MAGIC We also flag whether the extracted BIN exists in the known
-- MAGIC South African issuer range — a real data quality control that
-- MAGIC mirrors SARB oversight requirements.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1. Build the classified table

-- COMMAND ----------

CREATE OR REPLACE TABLE pan_classification.default.pan_classified AS
WITH staged AS (
  SELECT
    *,
    -- Strip mask characters and non-digit chars for Luhn
    REGEXP_REPLACE(pan, '[^0-9]', '')         AS pan_digits,

    -- Classification logic — ORDER MATTERS
    CASE
      WHEN pan IS NULL OR TRIM(pan) = ''                  THEN 'NULL'
      -- Truncated first: first 6 chars are all masks (no visible BIN)
      WHEN SUBSTR(pan, 1, 6) RLIKE '^[xX*]{6}$'            THEN 'TRUNCATED'
      -- Masked: BIN is visible but mask chars appear later
      WHEN pan RLIKE '[xX*]'                                THEN 'MASKED'
      -- Full: passes Luhn
      WHEN luhn_check(REGEXP_REPLACE(pan, '[^0-9]', ''))    THEN 'FULL_PAN'
      ELSE 'INVALID'
    END                                        AS classified_variant
  FROM pan_classification.default.pan_raw
)
SELECT
  *,
  -- Does the classification match the ground-truth label we generated?
  CASE
    WHEN pan_variant = classified_variant THEN true
    ELSE false
  END                                          AS classification_matches_truth,

  -- BIN range validation: is this a known SA issuer?
  CASE
    WHEN classified_variant = 'FULL_PAN' THEN
      bin IN (
        '528497', '528498',  -- Capitec
        '512055', '432557',  -- Standard Bank
        '377090',            -- Nedbank
        '400001', '510001',  -- Absa
        '400002', '510002',  -- FNB
        '491050',            -- RMB
        '528499',            -- TymeBank
        '400003'             -- Discovery
      )
    ELSE null
  END                                          AS bin_is_known_sa_issuer
FROM staged;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2. Classification summary
-- MAGIC Compares our algorithm's output against the ground truth.

-- COMMAND ----------

SELECT
  pan_variant                          AS ground_truth,
  classified_variant                   AS algorithm_output,
  COUNT(*)                             AS records,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM pan_classification.default.pan_classified
GROUP BY pan_variant, classified_variant
ORDER BY ground_truth, algorithm_output;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3. Accuracy check
-- MAGIC How many records did our classifier get right?

-- COMMAND ----------

SELECT
  COUNT(*)                                                              AS total_records,
  SUM(CASE WHEN classification_matches_truth THEN 1 ELSE 0 END)         AS correct,
  SUM(CASE WHEN classification_matches_truth THEN 0 ELSE 1 END)         AS incorrect,
  ROUND(
    100.0 * SUM(CASE WHEN classification_matches_truth THEN 1 ELSE 0 END)
    / COUNT(*), 2
  )                                                                     AS accuracy_pct
FROM pan_classification.default.pan_classified;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4. BIN coverage
-- MAGIC What proportion of FULL_PAN records have a known SA issuer BIN?
-- MAGIC Unknown BINs could indicate foreign cards, test data, or new issuers.

-- COMMAND ----------

SELECT
  bin_is_known_sa_issuer,
  COUNT(*)                                                              AS records,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                    AS pct,
  COUNT(DISTINCT bin)                                                   AS distinct_bins
FROM pan_classification.default.pan_classified
WHERE classified_variant = 'FULL_PAN'
GROUP BY bin_is_known_sa_issuer;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 5. Issuer breakdown (FULL_PAN only)

-- COMMAND ----------

SELECT
  issuer_bank,
  card_scheme,
  COUNT(*)                                                              AS full_pan_count,
  ROUND(SUM(transaction_amount), 2)                                     AS total_value_zar
FROM pan_classification.default.pan_classified
WHERE classified_variant = 'FULL_PAN'
GROUP BY issuer_bank, card_scheme
ORDER BY full_pan_count DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 6. Sample classified records
-- MAGIC Sorted so any mismatches appear at the top for inspection.

-- COMMAND ----------

SELECT
  pan,
  pan_variant          AS ground_truth,
  classified_variant   AS algorithm_output,
  classification_matches_truth,
  bin,
  issuer_bank,
  bin_is_known_sa_issuer
FROM pan_classification.default.pan_classified
ORDER BY classification_matches_truth ASC, pan_variant
LIMIT 30;