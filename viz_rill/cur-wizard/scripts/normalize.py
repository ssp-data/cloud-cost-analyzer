#!/usr/bin/env python
import os
import pathlib
import sys

import dlt
import duckdb
from dotenv import load_dotenv

load_dotenv()

# Read configuration from dlt config
try:
    normalized_data_dir_str = dlt.config["sources.aws_cur.normalized_data_dir"]
except KeyError:
    # Fall back to environment variables if not in config
    normalized_data_dir_str = os.getenv("NORMALIZED_DATA_DIR")

try:
    input_data_dir_str = dlt.config["sources.aws_cur.input_data_dir"]
except KeyError:
    # Fall back to environment variables if not in config
    input_data_dir_str = os.getenv("INPUT_DATA_DIR")

if not normalized_data_dir_str:
    sys.exit("ERROR: normalized_data_dir not configured. Add to .dlt/config.toml under [sources.aws_cur]")
if not input_data_dir_str:
    sys.exit("ERROR: input_data_dir not configured. Add to .dlt/config.toml under [sources.aws_cur]")

NORMALIZED_DATA_DIR = pathlib.Path(normalized_data_dir_str).resolve()
INPUT_DATA_DIR = pathlib.Path(input_data_dir_str).resolve()

# Create directories if they don't exist
NORMALIZED_DATA_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)

output_path = NORMALIZED_DATA_DIR / "normalized_aws.parquet"
full_input_path = f"{INPUT_DATA_DIR}/*.parquet"

# Check if any parquet files exist
parquet_files = list(INPUT_DATA_DIR.glob("*.parquet"))
if not parquet_files:
    print(f"ℹ️  No parquet files found in {INPUT_DATA_DIR}")
    print(f"   This is normal for incremental loading when no new data is available.")
    print(f"   Skipping AWS normalization.")
    sys.exit(0)

con = duckdb.connect(database=":memory:")

con.execute(
    f"""
    CREATE VIEW raw AS
      SELECT *
      FROM read_parquet('{full_input_path}', UNION_BY_NAME => TRUE)
    """
)

schema_rows = con.execute("DESCRIBE SELECT * FROM raw").fetchall()
all_columns = {row[0] for row in schema_rows}
map_cols = [row[0] for row in schema_rows if row[1].startswith("MAP")]
print("MAP columns found:", map_cols)


select_clauses = ["*"]

for col in map_cols:
    keys = [
        k[0]
        for k in con.execute(
            f"""
            SELECT DISTINCT
              key.unnest AS key_str
            FROM (
              SELECT map_keys({col}) AS k
              FROM raw
              WHERE {col} IS NOT NULL
            ) t
            CROSS JOIN UNNEST(k) AS key
            """
        ).fetchall()
    ]

    for key_str in keys:
        exploded = f"{col} ->> '{key_str}'"
        flat = f"{col}_{key_str}"
        if flat in all_columns:
            clause = f"COALESCE({flat}, {exploded}) AS {flat}"
        else:
            clause = f"{exploded} AS {flat}"
        select_clauses.append(clause)

if len(select_clauses) > 1:
    print("Generated SELECT clauses:\n", "\n".join(select_clauses))
else:
    print("No MAP columns found. No normalization needed.")

select_sql = "SELECT " + ",\n       ".join(select_clauses) + "\n  FROM raw"

copy_sql = "COPY (\n" + select_sql + f"\n) TO '{output_path}' (FORMAT PARQUET);"
con.execute(copy_sql)
print(f"✅ Normalized parquet written to {output_path}")
