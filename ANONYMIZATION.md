# Data Anonymization for Public Demos

Simple anonymization for protecting sensitive cost data in public dashboards.

## How It Works

**Super simple two-step process:**

1. **Run normal ETL** → Load real data to ClickHouse
2. **Anonymize in database** → Modify data directly in ClickHouse

No complex pipeline changes needed!

## Quick Start

### Full Pipeline (ETL + Anonymization)
```bash
make run-all-cloud
```

This runs:
1. Normal ETL to ClickHouse (`make run-etl-clickhouse`)
2. Anonymization script (`make anonymize-clickhouse`)

### Anonymize Existing Data
```bash
make anonymize-clickhouse
```

Re-anonymize anytime without re-running ETL!

### Clear ClickHouse Data
```bash
# Interactive (asks for confirmation)
make clear-clickhouse

# Force (non-interactive, useful for scripts)
make clear-clickhouse-force
```

This drops:
- All dlt tables: `aws_costs___*`, `gcp_costs___*`, `stripe_costs___*`, `aws_costs_staging___*`
- All Rill model tables: `aws_costs`, `gcp_costs`, `stripe_revenue`, `unified_cost_model`

## What Gets Anonymized?

The script modifies data directly in ClickHouse:

### ✅ AWS Costs
- **Multiplies costs** by random 2-8x factor:
  - `line_item_unblended_cost`
  - `line_item_blended_cost`
  - `line_item_net_unblended_cost`
  - `pricing_public_on_demand_cost`
  - `line_item_usage_amount`
- **Hashes account IDs**: `123456789012` → `acc-a1b2c3d4e5f6`

### ✅ GCP Costs
- **Multiplies costs** by random 2-8x factor
- **Hashes project IDs**: `my-project` → `proj-a1b2c3d4e5f6`

### ✅ Stripe Revenue
- **Multiplies amounts** by random 2-8x factor:
  - `amount`, `fee`, `net`
- **Hashes customer IDs**: `cus_ABC123` → `cus_a1b2c3d4e5f6`

### ✅ Data Volume
- **Duplicates all rows** 3x by default (customizable)
- Creates more interesting dashboards

## Customization

Control anonymization with environment variables:

```bash
# Higher cost multipliers (5-10x instead of 2-8x)
COST_MULTIPLIER_MIN=5.0 COST_MULTIPLIER_MAX=10.0 make anonymize-clickhouse

# More data duplication (5x instead of 3x)
DUPLICATE_ROWS=5 make anonymize-clickhouse

# Combine both
COST_MULTIPLIER_MIN=3.0 COST_MULTIPLIER_MAX=7.0 DUPLICATE_ROWS=4 make anonymize-clickhouse
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COST_MULTIPLIER_MIN` | `2.0` | Minimum random multiplier for costs |
| `COST_MULTIPLIER_MAX` | `8.0` | Maximum random multiplier for costs |
| `DUPLICATE_ROWS` | `3` | How many copies of each row (1 = no duplication) |

## Example: Before & After

**Before:**
```
AWS: 100 rows, $1,234 total, account 123456789012
GCP: 50 rows, €456 total, project my-production-app
Stripe: 20 rows, $890 revenue
```

**After (default settings):**
```
AWS: 300 rows, $6,789 total, account acc-e3b0c44298fc
GCP: 150 rows, €2,345 total, project proj-7f83b1657ff1
Stripe: 60 rows, $4,567 revenue
```

## GitHub Actions

Add to your workflow:

```yaml
- name: Deploy to ClickHouse with anonymization
  run: |
    make run-etl-clickhouse
    make anonymize-clickhouse
  env:
    COST_MULTIPLIER_MIN: 3.0
    COST_MULTIPLIER_MAX: 7.0
    DUPLICATE_ROWS: 5
```

## How the Script Works

The script (`scripts/anonymize_clickhouse.py`) is very simple:

1. **Connects to ClickHouse** using credentials from `.dlt/secrets.toml`
2. **Runs SQL UPDATE statements** to multiply cost columns
3. **Hashes IDs** using MD5
4. **Duplicates rows** with INSERT INTO SELECT

All done with standard SQL - no complex data pipeline changes!

## When to Use

✅ **Use anonymization:**
- Public Rill Cloud dashboards
- Demo environments
- Screenshots/presentations
- Sharing with external stakeholders

❌ **Don't use anonymization:**
- Internal cost analysis
- Finance reports
- Actual cost optimization
- Local development (use `make run-all` instead)

## Troubleshooting

**Error: Can't connect to ClickHouse**
- Check `.dlt/secrets.toml` has `[destination.clickhouse.credentials]`
- Run `make init-clickhouse` first

**Data doesn't look different**
- Check the script output for errors
- Run with `uv run python scripts/anonymize_clickhouse.py` to see details

**Want to reset to original data**
- Re-run `make run-etl-clickhouse` (will reload from sources)
- Then optionally `make anonymize-clickhouse` again

**Tables not found**
- Make sure you ran `make run-etl-clickhouse` first
- Script expects tables: `aws_costs___cur_export_test_00001`, etc.

## Technical Details

The anonymization uses:
- **ClickHouse ALTER TABLE UPDATE** for in-place modifications
- **rand()** function for random multipliers
- **MD5()** for hashing identifiers
- **INSERT INTO SELECT** for row duplication

This is much simpler than anonymizing during ETL!

## Why This Approach?

**Advantages:**
- ✅ Simple - just one Python script with SQL
- ✅ Fast - runs in seconds
- ✅ Flexible - re-anonymize anytime with different settings
- ✅ No pipeline changes - original ETL stays clean
- ✅ Easy to understand - standard SQL operations

**vs. Complex Approach (anonymizing during ETL):**
- ❌ Requires modifying all pipelines
- ❌ Harder to debug
- ❌ Can't easily re-anonymize
- ❌ More code to maintain
