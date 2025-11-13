#!/usr/bin/env python
"""
GCP Billing Data Normalization Script

Flattens GCP billing labels into columns (similar to AWS resource_tags).
This enables dynamic dashboard generation based on discovered labels.
"""
import os
import pathlib
import sys

import duckdb
from dotenv import load_dotenv

load_dotenv()

NORMALIZED_DATA_DIR = pathlib.Path(os.getenv("NORMALIZED_DATA_DIR") or "").resolve()
if not NORMALIZED_DATA_DIR.exists() or not NORMALIZED_DATA_DIR.is_dir():
    sys.exit(f"NORMALIZED_DATA_DIR ({NORMALIZED_DATA_DIR}) does not exist or is not a directory")
output_path = NORMALIZED_DATA_DIR / "normalized_gcp.parquet"

INPUT_DATA_DIR_GCP = pathlib.Path(os.getenv("INPUT_DATA_DIR_GCP") or "data/gcp_costs").resolve()
if not INPUT_DATA_DIR_GCP.exists() or not INPUT_DATA_DIR_GCP.is_dir():
    sys.exit(f"INPUT_DATA_DIR_GCP ({INPUT_DATA_DIR_GCP}) does not exist or is not a directory")

billing_path = f"{INPUT_DATA_DIR_GCP}/bigquery_billing_table/*.parquet"
labels_path = f"{INPUT_DATA_DIR_GCP}/bigquery_billing_table__labels/*.parquet"

con = duckdb.connect(database=":memory:")

# Create billing view
con.execute(f"CREATE VIEW billing AS SELECT * FROM read_parquet('{billing_path}')")

# Check if labels exist
labels_exist = (INPUT_DATA_DIR_GCP / "bigquery_billing_table__labels").exists()

if labels_exist:
    con.execute(f"CREATE VIEW labels AS SELECT * FROM read_parquet('{labels_path}')")

    # Get all unique label keys
    label_keys = [
        row[0] for row in con.execute(
            "SELECT DISTINCT key FROM labels WHERE key IS NOT NULL ORDER BY key"
        ).fetchall()
    ]
    print(f"Found {len(label_keys)} unique labels:", label_keys)

    # Build pivot columns for labels
    label_columns = []
    for key in label_keys:
        # Sanitize key for column name
        safe_key = key.replace("-", "_").replace(":", "_").replace("/", "_").replace(".", "_")
        label_columns.append(
            f"MAX(CASE WHEN l.key = '{key}' THEN l.value END) AS labels_{safe_key}"
        )

    label_select = ",\n       ".join(label_columns)

    # Join and flatten
    normalize_sql = f"""
    WITH labels_pivot AS (
      SELECT
        _dlt_parent_id,
        {label_select}
      FROM labels l
      GROUP BY _dlt_parent_id
    )
    SELECT
      CAST(b.usage_start_time AS DATE) AS date,
      b.billing_account_id,
      b.service__id,
      b.service__description,
      b.sku__id,
      b.sku__description,
      b.project__id,
      b.project__number,
      b.project__name,
      b.location__location,
      b.location__country,
      b.resource__name,
      b.resource__global_name,
      b.cost,
      b.currency,
      b.cost_type,
      b.usage__amount,
      b.usage__unit,
      b.price__effective_price,
      b.transaction_type,
      b._dlt_id,
      lp.*
    FROM billing b
    LEFT JOIN labels_pivot lp ON b._dlt_id = lp._dlt_parent_id
    """
else:
    print("No labels found, proceeding without labels...")
    normalize_sql = """
    SELECT
      CAST(usage_start_time AS DATE) AS date,
      billing_account_id,
      service__id,
      service__description,
      sku__id,
      sku__description,
      project__id,
      project__number,
      project__name,
      location__location,
      location__country,
      resource__name,
      resource__global_name,
      cost,
      currency,
      cost_type,
      usage__amount,
      usage__unit,
      price__effective_price,
      transaction_type,
      _dlt_id
    FROM billing
    """

con.execute(f"COPY ({normalize_sql}) TO '{output_path}' (FORMAT PARQUET);")
print(f"✅ Normalized GCP parquet written to {output_path}")
