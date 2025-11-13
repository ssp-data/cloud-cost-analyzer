# Rill Cloud Cost Analytics Setup Summary

## Overview
Successfully created a Rill data model for analyzing cloud costs from AWS, GCP (prepared), and Stripe revenue.

## What Was Created

### 1. Data Export (Parquet Files)
- `data/aws_costs.parquet` - AWS cost data from Cost and Usage Report
- `data/stripe_revenue.parquet` - Stripe revenue and fee data

### 2. Data Models (`models/`)
- `aws_costs.sql` - Reads AWS cost data from Parquet
- `stripe_revenue.sql` - Reads Stripe revenue data from Parquet
- `unified_cost_model.sql` - Combines AWS and Stripe data into a unified star schema

### 3. Metrics View (`metrics/`)
- `cloud_cost_metrics.yaml` - Defines dimensions and measures for analysis

**Dimensions:**
- Cloud Provider (AWS, GCP, Stripe)
- Service / Product
- Region
- Transaction Type (cost, revenue, fee)
- Account ID
- Currency

**Measures:**
- Total Cost
- Total Revenue
- Net Margin (Revenue - Cost)
- Gross Margin %
- Total Transactions
- Average Transaction Amount

### 4. Dashboard (`dashboards/`)
- `cloud_cost_explore.yaml` - Interactive dashboard for exploring cost and revenue data

## Data Model Structure

The unified cost model creates a simple star schema:

```sql
unified_cost_model
├── date (daily granularity)
├── cloud_provider (AWS, Stripe, GCP*)
├── service_name (product/service)
├── region (geographic region)
├── description (transaction details)
├── account_id
├── amount (raw transaction amount)
├── transaction_type (cost, revenue, fee)
├── currency
├── revenue_amount (calculated)
└── cost_amount (calculated)
```

*GCP prepared but no data available yet

## How to Use

### Start Rill
```bash
cd viz_rill
rill start --no-ui  # Runs without opening browser
# OR
rill start         # Opens browser automatically
```

### Access Dashboard
Navigate to: http://localhost:9009

### Update Data
When new cost/revenue data is available:

1. Run your pipelines to update DuckDB:
   ```bash
   make run-all
   ```

2. Re-export data to Parquet:
   ```bash
   cd viz_rill
   duckdb ../cloud_cost_analytics.duckdb "
   COPY (SELECT CAST(identity_time_interval AS DATE) AS date,
                line_item_product_code, product_region_code,
                line_item_usage_type, line_item_line_item_description,
                line_item_usage_account_id, line_item_unblended_cost,
                line_item_currency_code
         FROM aws_costs.cur_export_test_00001
         WHERE line_item_unblended_cost IS NOT NULL)
   TO 'data/aws_costs.parquet' (FORMAT PARQUET);

   COPY (SELECT CAST(to_timestamp(created) AS DATE) AS date,
                description, amount, net, reporting_category, type, currency
         FROM stripe_costs.balance_transaction
         WHERE amount IS NOT NULL)
   TO 'data/stripe_revenue.parquet' (FORMAT PARQUET);
   "
   ```

3. Rill will automatically detect changes and reload

## Adding GCP Data

When GCP billing export data is available:

1. Create GCP Parquet export:
   ```bash
   duckdb ../cloud_cost_analytics.duckdb "
   COPY (SELECT ... FROM gcp_costs.gcp_billing_export_...)
   TO 'data/gcp_costs.parquet' (FORMAT PARQUET);"
   ```

2. Create model `models/gcp_costs.sql`:
   ```sql
   SELECT * FROM read_parquet('data/gcp_costs.parquet')
   ```

3. Update `unified_cost_model.sql` to include GCP data in the UNION

## Key Features

- **Multi-cloud Analysis**: Compare costs across AWS, GCP, and revenue from Stripe
- **Time Series**: Daily granularity with time-based comparisons
- **Dimensions**: Drill down by provider, service, region, account
- **Margin Analysis**: Calculate gross margins by combining revenue and costs
- **Simple Updates**: Just re-export Parquet files to refresh data

## Files Created

```
viz_rill/
├── data/
│   ├── aws_costs.parquet
│   └── stripe_revenue.parquet
├── models/
│   ├── aws_costs.sql
│   ├── stripe_revenue.sql
│   └── unified_cost_model.sql
├── metrics/
│   └── cloud_cost_metrics.yaml
├── dashboards/
│   └── cloud_cost_explore.yaml
├── connectors/
│   └── duckdb.yaml
└── rill.yaml (updated)
```

## Next Steps

1. **Customize Dashboard**: Edit `dashboards/cloud_cost_explore.yaml` to add custom views
2. **Add Measures**: Edit `metrics/cloud_cost_metrics.yaml` to add new calculations
3. **Automate Updates**: Create a script to automatically re-export Parquet files
4. **Add GCP**: Once GCP data is available, follow the steps above to include it

## Troubleshooting

- **"Table does not exist" errors**: Re-export Parquet files
- **Stale data**: Rill caches data; restart with `rill start --reset`
- **Performance**: Parquet files are optimized for fast queries; data is small enough for instant analysis

Generated: 2025-11-13
