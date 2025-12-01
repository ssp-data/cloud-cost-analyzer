#!/usr/bin/env python
"""
GCP Rill Project Generator - mirrors AWS version but for GCP billing.
"""

from __future__ import annotations

import pathlib
from typing import Sequence

import duckdb
from jinja2 import Environment, FileSystemLoader

from utils.dimension_chart_selector import select_dimension_charts

_TEMPLATE_DIR = pathlib.Path(__file__).parent.parent / "templates"


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=False)


def _render(tmpl: str, **kws) -> str:
    return _env().get_template(tmpl).render(**kws)


def create_gcp_measures_list(all_cols: list[str]) -> list[str]:
    """Build GCP-specific measures list."""
    COMMON = [
        "cost",
        "cost_at_list",
        "usage__amount",
        "price__effective_price",
    ]
    return [c for c in COMMON if c in all_cols]


def generate_gcp_rill_project(
    *,
    parquet_path: pathlib.Path,
    out_dir: pathlib.Path,
    cost_col: str = "cost",
    dim_prefixes: Sequence[str] = ("labels_",),
    timeseries_col: str = "date",
    conn: duckdb.DuckDBPyConnection | None = None,
) -> None:
    """
    Generate Rill metrics/sources/explores/canvases for GCP billing.

    Parameters
    ----------
    parquet_path : Path
        Normalized GCP parquet file
    out_dir : Path
        Output directory for Rill YAML files
    cost_col : str
        Cost column name (default: 'cost')
    dim_prefixes : list[str]
        Dimension prefixes for canvas generation
    timeseries_col : str
        Timestamp column (default: 'date')
    conn : DuckDB connection, optional
        Existing connection to reuse
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("metrics", "sources", "explores", "dashboards"):
        (out_dir / sub).mkdir(exist_ok=True)

    script_owns_conn = conn is None
    if conn is None:
        conn = duckdb.connect(database=":memory:")

    conn.execute(f"CREATE VIEW _tmp AS SELECT * FROM read_parquet('{parquet_path}') LIMIT 0")
    all_cols = [r[0] for r in conn.execute("DESCRIBE SELECT * FROM _tmp").fetchall()]

    measures = create_gcp_measures_list(all_cols)
    dimensions = sorted(set(all_cols) - set(measures) - {timeseries_col, "_dlt_id"})

    shared = dict(
        measures=measures,
        dimensions=dimensions,
        timeseries=timeseries_col,
        model="gcp_cost_source",
        columns=all_cols,
        provider="GCP",
    )

    # NOTE: Metrics, sources, dashboards are hand-crafted static files that work with both
    # local (parquet) and cloud (ClickHouse) modes. We skip generating them to avoid overwrites.
    # Only generate dimension-specific canvases below.

    # # Generate metrics (DISABLED - use static file)
    # (out_dir / "metrics" / "gcp_cost_metrics.yaml").write_text(
    #     _render("metrics_template_gcp.yaml.j2", **shared)
    # )
    # print("✓ metrics written → metrics/gcp_cost_metrics.yaml")

    # # Generate source (DISABLED - use static models)
    # (out_dir / "sources" / "gcp_cost_source.yaml").write_text(
    #     _render(
    #             "source_template_gcp.yaml.j2",
    #         parquet_path=str(parquet_path),
    #     )
    # )
    # print("✓ source written → sources/gcp_cost_source.yaml")

    # # Generate explore (DISABLED - use static file)
    # (out_dir / "explores" / "gcp_cost_explore.yaml").write_text(
    #     _render("explore_template_gcp.yaml.j2", metrics_view="gcp_cost_metrics")
    # )
    # print("✓ explore written → explores/gcp_cost_explore.yaml")

    # # Generate overview dashboard (DISABLED - use static file)
    # overview_yaml = _render(
    #     "overview_dashboard_template_gcp.yaml.j2",
    #     metrics_view="gcp_cost_metrics",
    #     **shared,
    # )
    # (out_dir / "dashboards" / "gcp_overview.yaml").write_text(overview_yaml)
    # print("✓ dashboard written → dashboards/gcp_overview.yaml")

    # # Generate product insights dashboard (DISABLED - use static file)
    # product_insights_yaml = _render(
    #     "product_insights_gcp.yaml.j2",
    #     metrics_view="gcp_cost_metrics",
    # )
    # (out_dir / "dashboards" / "gcp_product_insights.yaml").write_text(product_insights_yaml)
    # print("✓ dashboard written → dashboards/gcp_product_insights.yaml")

    print("ℹ️  Skipping metrics/sources/dashboards generation (using static files)")
    print("   Only generating dimension-specific canvases below...")

    # Generate label-specific canvases
    for prefix in dim_prefixes:
        charts = select_dimension_charts(
            parquet_path,
            prefixes=[prefix],
            cost_col=cost_col,
            conn=conn,
        )
        if not charts:
            print(f"⚠️  no qualifying columns for prefix '{prefix}' – canvas skipped.")
            continue

        canvas_yaml = _render(
            "label_canvas_template_gcp.yaml.j2",
            metrics_view="gcp_cost_metrics",
            timeseries=timeseries_col,
            label_charts=charts,
            cost_measure="total_cost",
        )
        fname = f"gcp_{prefix.rstrip('_')}_canvas.yaml"
        (out_dir / "dashboards" / fname).write_text(canvas_yaml)
        print(f"✓ canvas written → dashboards/{fname}")

    if script_owns_conn:
        conn.close()

    print("✅ GCP Rill project ready at", out_dir)
