#!/usr/bin/env python
"""
Thin command-line façade around rill_project_generator.generate_rill_project
to keep business logic & argument parsing cleanly separated.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from textwrap import dedent

from dotenv import load_dotenv

from rill_project_generator import generate_rill_project

load_dotenv()


parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=dedent(
        """
        Generate YAML for a Rill cost-analysis project.

        Flags override env-vars; if both are absent reasonable defaults
        kick in (including an interactive prompt for the *cost* column
        when executed in a TTY).
        """
    ),
)
parser.add_argument(
    "--parquet",
    type=pathlib.Path,
    help="Path to *normalised* parquet (default: $NORMALIZED_DATA_DIR/normalized.parquet)",
)
parser.add_argument(
    "--output-dir",
    type=pathlib.Path,
    help="Destination Rill project folder; will be created if absent. (default: $RILL_PROJECT_PATH)",
)
parser.add_argument(
    "--cost-col",
    help=(
        "Column to be treated as 'cost'. Overrides the interactive picker "
        "and the COST_COL env-var. (default: interactively chosen or $COST_COL)"
    ),
)
parser.add_argument(
    "--dim-prefixes",
    default=os.getenv("DIM_PREFIXES", "resource_tags_"),
    help=(
        "Comma-separated list of dimension prefixes. "
        "Each prefix spawns its own canvas (default comes from "
        "DIM_PREFIXES env-var, falling back to 'resource_tags_')."
    ),
)
parser.add_argument(
    "--timeseries-col",
    default=os.getenv("TIMESERIES_COL", "line_item_usage_start_date"),
    help="Timestamp column",
)
parser.add_argument(
    "--list-cost-columns",
    action="store_true",
    help="List all cost-like numeric columns found in the parquet and exit. "
    "Useful to discover the exact column names you may want to feed "
    "into --cost-col.",
)
args = parser.parse_args()

if args.parquet is None:
    base_dir = pathlib.Path(os.getenv("NORMALIZED_DATA_DIR", "")).expanduser()
    args.parquet = base_dir / "normalized.parquet"
if not args.parquet.exists():
    sys.exit(f"❌ Parquet not found: {args.parquet}")

if args.output_dir is None:
    args.output_dir = pathlib.Path(os.getenv("RILL_PROJECT_PATH", "")).expanduser()
if not args.output_dir:
    sys.exit("❌ --output-dir or RILL_PROJECT_PATH is required")

prefixes = [p.strip() for p in args.dim_prefixes.split(",") if p.strip()]


generate_rill_project(
    parquet_path=args.parquet.resolve(),
    out_dir=args.output_dir.resolve(),
    cost_col=args.cost_col or "",
    dim_prefixes=prefixes,
    timeseries_col=args.timeseries_col,
    list_cost_columns=args.list_cost_columns,
)
