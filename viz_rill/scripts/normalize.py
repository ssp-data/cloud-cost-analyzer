#!/usr/bin/env python
import os
import pathlib
import sys

import duckdb
from dotenv import load_dotenv

load_dotenv()

NORMALIZED_DATA_DIR = pathlib.Path(os.getenv("NORMALIZED_DATA_DIR") or "").resolve()
if not NORMALIZED_DATA_DIR.exists() or not NORMALIZED_DATA_DIR.is_dir():
    sys.exit(f"NORMALIZED_DATA_DIR ({NORMALIZED_DATA_DIR}) does not exist or is not a directory")
output_path = NORMALIZED_DATA_DIR / "normalized.parquet"

INPUT_DATA_DIR = pathlib.Path(os.getenv("INPUT_DATA_DIR") or "").resolve()
if not INPUT_DATA_DIR.exists() or not INPUT_DATA_DIR.is_dir():
    sys.exit(f"INPUT_DATA_DIR ({INPUT_DATA_DIR}) does not exist or is not a directory")
full_input_path = f"{INPUT_DATA_DIR}/*.parquet"

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
