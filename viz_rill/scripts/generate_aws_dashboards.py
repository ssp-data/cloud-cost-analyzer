#!/usr/bin/env python
"""
Generate Rill dashboards for AWS CUR data.

This script dynamically generates Rill YAML files based on the normalized AWS CUR data,
including advanced metrics, overview canvas, and dynamic dimension-specific canvases.

Adapted from aws-cur-wizard: https://github.com/rilldata/aws-cur-wizard
"""

import duckdb
import argparse
from pathlib import Path
import logging
import sys
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))
from utils.dimension_chart_selector import select_dimension_charts

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
NORMALIZED_PARQUET = PROJECT_ROOT / "data" / "normalized_aws.parquet"
OUTPUT_DIR = PROJECT_ROOT


def get_schema_info(parquet_path: Path) -> tuple:
    """Extract schema information from normalized parquet."""
    logging.info(f"🔍 Analyzing schema: {parquet_path}")

    conn = duckdb.connect(database=":memory:")

    # Get all columns
    schema = conn.execute(f"""
        SELECT column_name, column_type
        FROM (DESCRIBE SELECT * FROM read_parquet('{parquet_path}'))
        ORDER BY column_name
    """).fetchall()

    columns = [col[0] for col in schema]
    column_types = {col[0]: col[1] for col in schema}

    # Identify dimensions (non-numeric columns, excluding IDs and timestamps)
    dimensions = [
        col for col, typ in column_types.items()
        if typ == 'VARCHAR'
        and not col.startswith('_dlt')
        and not col.endswith('_id')
        and col not in ['identity_line_item_id', 'identity_time_interval', 'date']
    ]

    # Identify fact columns (numeric columns)
    facts = [
        col for col, typ in column_types.items()
        if typ in ('DOUBLE', 'BIGINT', 'INTEGER', 'DECIMAL')
        and not col.startswith('_dlt')
        and 'date' not in col.lower()
    ]

    logging.info(f"✅ Found {len(columns)} total columns")
    logging.info(f"   - {len(dimensions)} dimensions")
    logging.info(f"   - {len(facts)} fact columns")

    conn.close()

    return columns, dimensions, facts, column_types


def generate_source_yaml(output_dir: Path):
    """Generate AWS source YAML."""
    logging.info("📝 Generating AWS source YAML...")

    source_content = """# AWS CUR Source
# Auto-generated from normalized AWS Cost and Usage Report data
# Source: https://github.com/rilldata/aws-cur-wizard

type: source

connector: duckdb
sql: |
  SELECT * FROM read_parquet('data/normalized_aws.parquet')
"""

    source_path = output_dir / "sources" / "aws_cost_source.yaml"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source_content)

    logging.info(f"✅ Created: {source_path}")


def generate_metrics_yaml(
    output_dir: Path,
    columns: List[str],
    dimensions: List[str],
    facts: List[str]
):
    """Generate AWS metrics view YAML using template."""
    logging.info("📝 Generating AWS metrics view YAML...")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("metrics_template.yml.j2")

    rendered = template.render(
        model="aws_cost_source",
        timeseries="date",
        dimensions=dimensions[:50],  # Limit to avoid too many dimensions
        facts=facts[:20],  # Include top fact columns
        columns=columns
    )

    metrics_path = output_dir / "metrics" / "aws_cost_metrics.yaml"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(rendered)

    logging.info(f"✅ Created: {metrics_path}")


def generate_overview_canvas(
    output_dir: Path,
    columns: List[str]
):
    """Generate overview canvas using template."""
    logging.info("📝 Generating AWS overview canvas...")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("overview_canvas_template.yml.j2")

    rendered = template.render(
        metrics_view="aws_cost_metrics",
        timeseries="date",
        columns=columns
    )

    canvas_path = output_dir / "dashboards" / "aws_overview.yaml"
    canvas_path.parent.mkdir(parents=True, exist_ok=True)
    canvas_path.write_text(rendered)

    logging.info(f"✅ Created: {canvas_path}")


def generate_dynamic_canvases(
    output_dir: Path,
    parquet_path: Path,
    prefixes: List[str],
    cost_col: str = "line_item_unblended_cost"
):
    """Generate dynamic dimension canvases."""
    logging.info(f"📝 Generating dynamic canvases for prefixes: {prefixes}")

    # Get chart specifications using the dimension selector algorithm
    chart_specs = select_dimension_charts(
        parquet=parquet_path,
        prefixes=prefixes,
        cost_col=cost_col
    )

    if not chart_specs:
        logging.warning(f"⚠️  No qualifying dimensions found for prefixes: {prefixes}")
        return

    # Determine cost measure name (heuristic from aws-cur-wizard)
    cost_measure = "total_unblended_cost"  # Default based on template

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("map_canvas_template.yml.j2")

    rendered = template.render(
        metrics_view="aws_cost_metrics",
        cost_measure=cost_measure,
        tag_charts=chart_specs
    )

    # Create canvas for each prefix group
    prefix_name = "_".join(p.rstrip("_") for p in prefixes)
    canvas_path = output_dir / "dashboards" / f"aws_insights_{prefix_name}.yaml"
    canvas_path.parent.mkdir(parents=True, exist_ok=True)
    canvas_path.write_text(rendered)

    logging.info(f"✅ Created: {canvas_path} with {len(chart_specs)} dimensions")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Rill dashboards for AWS CUR data"
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=NORMALIZED_PARQUET,
        help="Path to normalized AWS parquet file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for Rill project"
    )
    parser.add_argument(
        "--cost-col",
        default="line_item_unblended_cost",
        help="Cost column to use for charts"
    )
    parser.add_argument(
        "--dim-prefixes",
        default="product_,line_item_",
        help="Comma-separated dimension prefixes for dynamic canvases"
    )
    parser.add_argument(
        "--skip-dynamic",
        action="store_true",
        help="Skip dynamic canvas generation"
    )

    args = parser.parse_args()

    # Check if normalized file exists
    if not args.parquet.exists():
        logging.error(f"❌ Normalized parquet not found: {args.parquet}")
        logging.error("   Run normalize_aws.py first!")
        sys.exit(1)

    # Get schema info
    columns, dimensions, facts, column_types = get_schema_info(args.parquet)

    # Generate Rill files
    generate_source_yaml(args.output_dir)
    generate_metrics_yaml(args.output_dir, columns, dimensions, facts)
    generate_overview_canvas(args.output_dir, columns)

    # Generate dynamic canvases
    if not args.skip_dynamic:
        prefixes = [p.strip() for p in args.dim_prefixes.split(",")]
        generate_dynamic_canvases(
            args.output_dir,
            args.parquet,
            prefixes,
            args.cost_col
        )

    logging.info("🎉 Dashboard generation complete!")
    logging.info(f"📂 Output directory: {args.output_dir}")
    logging.info("🚀 Run: cd viz_rill && rill start")


if __name__ == "__main__":
    main()
