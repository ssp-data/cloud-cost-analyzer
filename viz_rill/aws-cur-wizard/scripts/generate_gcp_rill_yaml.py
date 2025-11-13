#!/usr/bin/env python
"""
Generate Rill YAML files for GCP billing data.
Mirrors the AWS generator but adapted for GCP schema.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from textwrap import dedent

from dotenv import load_dotenv

from rill_project_generator_gcp import generate_gcp_rill_project

load_dotenv()

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=dedent(
        """
        Generate YAML for a Rill GCP cost-analysis project.
        """
    ),
)
parser.add_argument(
    "--parquet",
    type=pathlib.Path,
    help="Path to normalized GCP parquet (default: $NORMALIZED_DATA_DIR/normalized_gcp.parquet)",
)
parser.add_argument(
    "--output-dir",
    type=pathlib.Path,
    help="Destination Rill project folder (default: $RILL_PROJECT_PATH)",
)
parser.add_argument(
    "--cost-col",
    default="cost",
    help="Column to treat as 'cost' (default: cost)",
)
parser.add_argument(
    "--dim-prefixes",
    default=os.getenv("DIM_PREFIXES_GCP", "labels_,service__,project__"),
    help="Comma-separated dimension prefixes for canvas generation",
)
parser.add_argument(
    "--timeseries-col",
    default="date",
    help="Timestamp column (default: date)",
)

args = parser.parse_args()

if args.parquet is None:
    base_dir = pathlib.Path(os.getenv("NORMALIZED_DATA_DIR", "")).expanduser()
    args.parquet = base_dir / "normalized_gcp.parquet"

if not args.parquet.exists():
    sys.exit(f"❌ Parquet not found: {args.parquet}")

if args.output_dir is None:
    args.output_dir = pathlib.Path(os.getenv("RILL_PROJECT_PATH", "")).expanduser()

if not args.output_dir:
    sys.exit("❌ --output-dir or RILL_PROJECT_PATH is required")

prefixes = [p.strip() for p in args.dim_prefixes.split(",") if p.strip()]

generate_gcp_rill_project(
    parquet_path=args.parquet.resolve(),
    out_dir=args.output_dir.resolve(),
    cost_col=args.cost_col,
    dim_prefixes=prefixes,
    timeseries_col=args.timeseries_col,
)
