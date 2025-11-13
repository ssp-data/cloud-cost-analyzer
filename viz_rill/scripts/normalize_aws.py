#!/usr/bin/env python
"""
Normalize AWS CUR data from dlt parquet files.

This script reads AWS CUR data exported by dlt and flattens it into a normalized
structure compatible with Rill dashboards. It handles nested product lists and
prepares the data for advanced analytics.

Adapted from aws-cur-wizard: https://github.com/rilldata/aws-cur-wizard
"""

import duckdb
from pathlib import Path
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "aws_costs"
NORMALIZED_OUTPUT = PROJECT_ROOT / "data" / "normalized_aws.parquet"


def normalize_aws_cur():
    """
    Normalize AWS CUR data from dlt parquet exports.

    This function:
    1. Reads all AWS CUR parquet files
    2. Extracts date from identity_time_interval
    3. Handles product list expansion (if needed)
    4. Writes normalized output
    """
    logging.info("🔄 Starting AWS CUR normalization...")

    conn = duckdb.connect(database=":memory:")

    # Find the main CUR data file pattern
    cur_pattern = str(DATA_DIR / "cur_export_test_00001" / "*.parquet")

    logging.info(f"📂 Reading AWS CUR data from: {cur_pattern}")

    # Create normalized view with date extraction
    query = f"""
    CREATE OR REPLACE VIEW normalized_aws AS
    SELECT
        -- Extract date from identity_time_interval (format: "2025-11-01T00:00:00Z/2025-12-01T00:00:00Z")
        CAST(SPLIT_PART(identity_time_interval, 'T', 1) AS DATE) AS date,

        -- Bill information
        bill_bill_type,
        bill_billing_entity,
        bill_billing_period_end_date,
        bill_billing_period_start_date,
        bill_invoicing_entity,
        bill_payer_account_id,
        bill_payer_account_name,

        -- Line item details
        line_item_blended_cost,
        line_item_unblended_cost,
        line_item_net_unblended_cost,
        line_item_currency_code,
        line_item_line_item_description,
        line_item_line_item_type,
        line_item_product_code,
        line_item_usage_account_id,
        line_item_usage_account_name,
        line_item_usage_amount,
        line_item_usage_type,
        line_item_operation,
        line_item_blended_rate,
        line_item_unblended_rate,
        line_item_normalization_factor,
        line_item_normalized_usage_amount,
        line_item_tax_type,
        line_item_legal_entity,

        -- Product information
        product_location,
        product_location_type,
        product_product_family,
        product_region_code,
        product_servicecode,
        product_sku,
        product_usagetype,
        product_operation,
        product_from_location,
        product_from_location_type,
        product_from_region_code,
        product_to_location,
        product_to_location_type,
        product_to_region_code,
        product_fee_code,
        product_fee_description,

        -- Pricing
        pricing_currency,
        pricing_public_on_demand_cost,
        pricing_public_on_demand_rate,
        pricing_rate_code,
        pricing_rate_id,
        pricing_term,
        pricing_unit,

        -- Reservations
        reservation_amortized_upfront_cost_for_usage,
        reservation_amortized_upfront_fee_for_billing_period,
        reservation_effective_cost,
        reservation_normalized_units_per_reservation,
        reservation_number_of_reservations,
        reservation_recurring_fee_for_usage,
        reservation_total_reserved_normalized_units,
        reservation_total_reserved_units,
        reservation_units_per_reservation,
        reservation_unused_amortized_upfront_fee_for_billing_period,
        reservation_unused_normalized_unit_quantity,
        reservation_unused_quantity,
        reservation_unused_recurring_fee,
        reservation_upfront_value,
        reservation_subscription_id,

        -- Savings Plans
        savings_plan_amortized_upfront_commitment_for_billing_period,
        savings_plan_recurring_commitment_for_billing_period,
        savings_plan_savings_plan_effective_cost,
        savings_plan_savings_plan_rate,
        savings_plan_total_commitment_to_date,
        savings_plan_used_commitment,

        -- Identity
        identity_line_item_id,
        identity_time_interval

    FROM read_parquet('{cur_pattern}', union_by_name=true)
    WHERE identity_time_interval IS NOT NULL
    """

    conn.execute(query)
    logging.info("✅ Created normalized view")

    # Check for any MAP columns that need flattening (like resource tags)
    schema_check = conn.execute("""
        SELECT column_name, column_type
        FROM (DESCRIBE SELECT * FROM normalized_aws)
        WHERE column_type LIKE '%MAP%' OR column_type LIKE '%STRUCT%'
    """).fetchall()

    if schema_check:
        logging.info(f"⚠️  Found {len(schema_check)} nested columns that may need flattening:")
        for col_name, col_type in schema_check:
            logging.info(f"   - {col_name}: {col_type}")

    # Write to parquet
    NORMALIZED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f"💾 Writing normalized data to: {NORMALIZED_OUTPUT}")
    conn.execute(f"""
        COPY normalized_aws TO '{NORMALIZED_OUTPUT}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    # Get row count
    row_count = conn.execute("SELECT COUNT(*) FROM normalized_aws").fetchone()[0]
    logging.info(f"✅ Normalized {row_count:,} rows")

    # Get column count
    col_count = conn.execute("SELECT COUNT(*) FROM (DESCRIBE SELECT * FROM normalized_aws)").fetchone()[0]
    logging.info(f"✅ Total columns: {col_count}")

    # Show sample date range
    date_range = conn.execute("""
        SELECT MIN(date), MAX(date)
        FROM normalized_aws
    """).fetchone()
    if date_range[0] and date_range[1]:
        logging.info(f"📅 Date range: {date_range[0]} to {date_range[1]}")

    conn.close()
    logging.info("🎉 AWS normalization complete!")

    return NORMALIZED_OUTPUT


if __name__ == "__main__":
    normalize_aws_cur()
