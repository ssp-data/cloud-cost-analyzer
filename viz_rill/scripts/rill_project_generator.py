#!/usr/bin/env python
"""
Library for turning a *normalised* CUR parquet into a ready-to-run
**Rill** project.

Call :func:`generate_rill_project` from Python, tests, or a thin CLI
wrapper.  All heavy IO happens inside this function; it is therefore
side-effect free *until* it starts writing the YAML artefacts to
*out_dir*.

The helper relies on:
    • duckdb
    • Jinja2
    • python-dotenv (only if the caller wishes to pre-load .env)
"""

from __future__ import annotations

import pathlib
from typing import Sequence, Mapping, Any

import duckdb
from jinja2 import Environment, FileSystemLoader

from utils.dimension_chart_selector import select_dimension_charts


_TEMPLATE_DIR = pathlib.Path(__file__).parent.parent / "templates"


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=False)


def _render(tmpl: str, **kws) -> str:
    """Render a Jinja template *tmpl* with keyword arguments *kws*."""
    return _env().get_template(tmpl).render(**kws)


def create_measures_list(all_cols: list[str], cost_col: str) -> list[str]:
    """
    Build the list of fact columns (measures).  The chosen cost column
    goes first so downstream GUIs pick a sensible default.
    """
    COMMON = [
        "line_item_usage_amount",
        "line_item_unblended_cost",
        "line_item_blended_cost",
        "line_item_net_unblended_cost",
        "savings_plan_effective_cost",
        "reservation_effective_cost",
    ]
    ordered = [cost_col] + [c for c in COMMON if c != cost_col]
    return [c for c in ordered if c in all_cols]


def generate_rill_project(
    *,
    parquet_path: pathlib.Path,
    out_dir: pathlib.Path,
    cost_col: str,
    dim_prefixes: Sequence[str] = ("resource_tags_",),
    timeseries_col: str = "line_item_usage_start_date",
    list_cost_columns: bool = False,
    conn: duckdb.DuckDBPyConnection | None = None,
    extra_context: Mapping[str, Any] | None = None,
) -> None:
    """
    Build a full Rill project (sources/metrics/explores/canvases).

    Parameters
    ----------
    parquet_path : Path
        *Normalised* parquet file.
    out_dir : Path
        Directory to create or update – will contain ``metrics/``,
        ``sources/``, ``explores/`` and ``canvases/`` sub-folders.
    cost_col : str
        Column to treat as "spend".
    dim_prefixes : list[str]
        Each prefix produces a *canvas* covering all matching dimensions.
    timeseries_col : str
        Timestamp column in the model.
    list_cost_columns : bool
        If *True*, only print detected cost-like columns and return.
    conn : duckdb connection, optional
        Inject an existing DuckDB connection (handy for tests).  If *None*
        a transient in-memory DB is created.
    extra_context : dict, optional
        Extra key/values injected into Jinja templates (advanced).

    Ideas for future knobs:
    • dominant_threshold : float
        ≥ fraction of remaining spend for a value to be "peeled".
    • min_spend_share : float
        Minimum fraction of total spend a dimension must cover to qualify.
    """
    if not cost_col:
        cost_col = "line_item_unblended_cost"
    out_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("metrics", "sources", "explores", "canvases"):
        (out_dir / sub).mkdir(exist_ok=True)

    script_owns_conn = conn is None
    if conn is None:
        conn = duckdb.connect(database=":memory:")

    conn.execute(f"CREATE VIEW _tmp AS SELECT * FROM read_parquet('{parquet_path}') LIMIT 0")
    all_cols = [r[0] for r in conn.execute("DESCRIBE SELECT * FROM _tmp").fetchall()]

    # Diagnostics
    if list_cost_columns:
        cost_columns = [c for c in all_cols if "cost" in c.lower() or "amount" in c.lower()]
        print("Cost-like columns detected:")
        for c in sorted(cost_columns)[:40]:
            print(f"  • {c}")
        return

    measures = create_measures_list(all_cols, cost_col)
    if timeseries_col not in all_cols:
        timeseries_col = "line_item_usage_start_date"

    dimensions = sorted(set(all_cols) - set(measures) - {timeseries_col})

    shared = dict(
        measures=measures,
        dimensions=dimensions,
        timeseries=timeseries_col,
        model="aws_cost_source",
        columns=all_cols,
        **(extra_context or {}),
    )

    (out_dir / "metrics" / "aws_cost_metrics.yml").write_text(
        _render("metrics_template.yml.j2", **shared)
    )
    (out_dir / "sources" / "aws_cost_source.yml").write_text(
        _render(
            "source_template.yml.j2",
            parquet_path=str(parquet_path),
            env={"DATA_DIR": str(parquet_path.parent)},
        )
    )
    (out_dir / "explores" / "aws_cost_explore.yml").write_text(
        _render("explore_template.yml.j2", metrics_view="aws_cost_metrics")
    )

    overview_canvas_yaml = _render(
        "overview_canvas_template.yml.j2",
        metrics_view="aws_cost_metrics",
        **shared,
    )
    (out_dir / "canvases" / "aws_cost_overview_canvas.yml").write_text(overview_canvas_yaml)
    print("✓ canvas written → canvases/aws_cost_overview_canvas.yml")

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

        # TODO: this is a hack to get the measure name that the metrics view will have created
        if cost_col in (
            "line_item_unblended_cost",
            "line_item_blended_cost",
        ):
            measure_name = f"total_{cost_col.split('_', 2)[-1]}"
        else:
            measure_name = f"sum_{cost_col}"

        canvas_yaml = _render(
            "map_canvas_template.yml.j2",
            metrics_view="aws_cost_metrics",
            timeseries=timeseries_col,
            tag_charts=charts,
            cost_measure=measure_name,
        )
        fname = f"aws_cost_{prefix.rstrip('_')}_canvas.yml"
        (out_dir / "canvases" / fname).write_text(canvas_yaml)
        print(f"✓ canvas written → canvases/{fname}")

    if script_owns_conn:
        conn.close()

    print("✅  Rill project ready at", out_dir)
