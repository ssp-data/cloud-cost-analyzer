#!/usr/bin/env python
"""
Generate chart specifications for Rill canvases by analysing a *normalised
CUR* parquet file.

Algorithm overview
------------------
1. **Candidate discovery** – any column whose name starts with one of the
   user-supplied *prefixes* (e.g. ``resource_tags_``, ``product_``).

2. **Minimal qualification** – a column is only considered if

       • ≥ 5 % of total spend is on rows where the column is **NOT NULL**
       • the column has **> 2** distinct values

3. **Dominant-slice peeling** – one or more values that together own
   ≥ 70 % of the *remaining* spend are "peeled off" **recursively**.
   These dominant values will be presented in a KPI (single value) or
   leaderboard (several values).  The rest (the *remainder*) is what the
   main pie/bar/leaderboard visualises.

4. **Non-zero remainder guard (NEW)** – after peeling, the spend of the
   remainder is calculated.  If that remainder is **0 $** *or* only one
   value remains, the chart is suppressed and we fall back to a pure
   KPI/leaderboard layout – preventing Rill from rendering empty widgets.

5. **Chart selection** for the remainder (when it exists):

       ``distinct_count ≤ 10`` → ``pie_chart``
       ``11 ≤ distinct_count ≤ 40`` → ``bar_chart``
       ``distinct_count > 40`` → ``leaderboard``

6. **Layout codes** produced (consumed by the Jinja template):

       ``single``            – only the chart (no dominant slices)
       ``kpi+pie``           – KPI for one dominant value + chart
       ``leaderboard+pie``   – leaderboard for several dominant values + chart
       ``kpi``               – KPI only (nothing left to chart)
       ``leaderboard``       – leaderboard only (nothing left to chart)

Return structure
----------------
``select_dimension_charts`` returns a list of dictionaries, one per
qualified dimension, pre-sorted by skew (``top_cost_share``):

    {
        "dimension": "resource_tags_user_name",
        "layout":    "kpi+pie",
        "chart":     "pie_chart",      # bar_chart / leaderboard / None
        "filter_in": ["alice"],        # peeled dominant values
    }

Tunable constants (thresholds) are defined at the top of this file.

Example:

    >>> charts = select_dimension_charts(
            Path("normalized.parquet"),
            prefixes=["resource_tags_", "product_"],
            cost_col="line_item_unblended_cost",
        )
"""

from pathlib import Path
from typing import List, Dict

import duckdb
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

COST_COVERAGE_THR = 0.05
MIN_DISTINCT = 2
DOMINANT_SLICE_THR = 0.70


def _per_tag_stats(conn, table_sql, dim, cost) -> Dict[str, float]:
    nn, dc, top_share = conn.execute(
        f"""
        WITH x AS (
          SELECT "{dim}" AS k, "{cost}" AS c
          FROM {table_sql}
          WHERE "{dim}" IS NOT NULL
        ),
        g AS (
          SELECT k, SUM(c) AS c FROM x GROUP BY k
        )
        SELECT
          COUNT(k),                     -- non-null rows
          COUNT(DISTINCT k),            -- cardinality
          MAX(c) / NULLIF(SUM(c), 0.0)  -- share of top value
        FROM g
        """
    ).fetchone()
    return dict(
        dimension=dim,
        non_null_count=int(nn),
        distinct_count=int(dc),
        top_cost_share=float(top_share or 0.0),
    )


def _cost_coverage(conn, table_sql, dim, cost) -> float:
    """Spend occurring on non-null rows, as a share of total."""
    return (
        conn.execute(
            f"""
            SELECT SUM(CASE WHEN "{dim}" IS NOT NULL THEN "{cost}" END)
                   / NULLIF(SUM("{cost}"),0)
            FROM {table_sql}
            """
        ).fetchone()[0]
        or 0.0
    )


def _dominant_filters(conn, table_sql, dim, cost) -> List[str]:
    """
    Peel values that own ≥ DOMINANT_SLICE_THR of *remaining* spend.
    """
    rows = conn.execute(
        f"""
        SELECT "{dim}" AS k, SUM("{cost}") AS c
        FROM   {table_sql}
        WHERE  "{dim}" IS NOT NULL
        GROUP  BY k
        ORDER  BY c DESC
        """
    ).fetchall()

    remainder = sum(c for _k, c in rows) or 1
    keep = []

    for k, c in rows:
        if c / remainder < DOMINANT_SLICE_THR:
            break
        keep.append(k)
        remainder -= c
        if remainder <= 0:
            break
    return keep


def _remaining_spend(conn, table_sql, dim, cost, excluded_vals) -> float:
    """
    Spend of rows **not** in excluded_vals (i.e. what would be charted).
    """
    if not excluded_vals:  # nothing peeled
        return conn.execute(f'SELECT SUM("{cost}") FROM {table_sql}').fetchone()[0] or 0.0

    placeholders = ",".join(["?"] * len(excluded_vals))
    return (
        conn.execute(
            f"""
            SELECT SUM("{cost}")
            FROM   {table_sql}
            WHERE  "{dim}" IS NOT NULL
              AND  "{dim}" NOT IN ({placeholders})
            """,
            excluded_vals,
        ).fetchone()[0]
        or 0.0
    )


def _chart_by_cardinality(dc: int) -> str:
    if dc <= 10:
        return "pie_chart"
    if dc <= 40:
        return "bar_chart"
    return "leaderboard"


def select_dimension_charts(
    parquet: Path,
    prefixes: List[str],
    cost_col: str = "line_item_unblended_cost",
    conn: duckdb.DuckDBPyConnection | None = None,
) -> List[Dict]:
    owns_conn = conn is None
    if owns_conn:
        conn = duckdb.connect(database=":memory:")

    table_sql = f"read_parquet('{parquet.as_posix()}')"
    logging.info("🔍  analysing parquet   %s", parquet)

    dims = [
        col
        for col, *_ in conn.execute(f"DESCRIBE SELECT * FROM {table_sql}").fetchall()
        if any(col.startswith(p) for p in prefixes)
    ]
    logging.info("🔍  %d candidate dimensions: %s", len(dims), dims[:20])

    selected: List[Dict] = []

    for dim in dims:
        stats = _per_tag_stats(conn, table_sql, dim, cost_col)
        cov = _cost_coverage(conn, table_sql, dim, cost_col)

        if cov < COST_COVERAGE_THR or stats["distinct_count"] <= MIN_DISTINCT:
            logging.info(
                "  – skip %-45s (%.1f %%, distinct=%d)", dim, 100 * cov, stats["distinct_count"]
            )
            continue

        filter_in = _dominant_filters(conn, table_sql, dim, cost_col)
        remaining_distinct = stats["distinct_count"] - len(filter_in)
        remaining_spend = _remaining_spend(conn, table_sql, dim, cost_col, filter_in)

        if remaining_spend == 0 or remaining_distinct <= 1:
            # Nothing left to plot after peeling
            layout = "kpi" if len(filter_in) == 1 else "leaderboard"
            chart = None
        else:
            chart = _chart_by_cardinality(remaining_distinct)
            layout = (
                "single"
                if not filter_in
                else "kpi+pie"
                if len(filter_in) == 1
                else "leaderboard+pie"
            )

        selected.append(
            dict(
                dimension=dim,
                layout=layout,
                chart=chart,
                filter_in=filter_in,
                top_cost_share=stats["top_cost_share"],
            )
        )
        logging.info("  ✔ %-45s → %s", dim, layout)

    # ranking by skew
    selected.sort(key=lambda d: d["top_cost_share"], reverse=True)
    for d in selected:
        d.pop("top_cost_share", None)

    if owns_conn:
        conn.close()
    logging.info("✓ prepared %d chart specs", len(selected))
    return selected


if __name__ == "__main__":
    import pathlib
    import argparse, pprint
    from dotenv import load_dotenv
    import os

    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", nargs="+", default=["resource_tags_"])
    ap.add_argument("--cost-col", default="line_item_unblended_cost")
    args = ap.parse_args()
    NORMALIZED_DATA_DIR = pathlib.Path(os.getenv("NORMALIZED_DATA_DIR", ""))
    PARQUET = NORMALIZED_DATA_DIR / "normalized.parquet"

    out = select_dimension_charts(PARQUET, args.prefix, cost_col=args.cost_col)
    pprint.pp(out)
