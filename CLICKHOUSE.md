# ClickHouse Cloud Deployment

Complete guide for deploying your cloud cost analytics to ClickHouse Cloud with optional data anonymization for public dashboards.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Switching Between Local and Cloud](#switching-between-local-and-cloud)
5. [Data Anonymization](#data-anonymization)
6. [GitHub Actions Automation](#github-actions-automation)
7. [Troubleshooting](#troubleshooting)

## Overview

### Two Deployment Modes

**Local Development** (default):
- Data: Parquet files in `viz_rill/data/`
- Visualization: Local Rill server
- Command: `make run-all`

**Cloud Production**:
- Data: ClickHouse Cloud database
- Visualization: Rill Cloud or local Rill pointing to ClickHouse
- Command: `make run-all-cloud`

### Architecture

```
Local Mode:
  Cloud APIs → dlt → Parquet files → Rill (DuckDB) → localhost:9009

Cloud Mode:
  Cloud APIs → dlt → ClickHouse Cloud → Rill Cloud → Public dashboard
```

**Key Feature**: Same codebase works for both! Just switch environment variables.

## Quick Start

### Prerequisites

- ✅ Working local setup (`make run-all` works)
- ✅ ClickHouse Cloud account ([sign up free](https://clickhouse.cloud))

### 5-Minute Setup

```bash
# 1. Add ClickHouse credentials to .dlt/secrets.toml
[destination.clickhouse.credentials]
host = "xxxxx.europe-west4.gcp.clickhouse.cloud"
port = 8443
username = "default"
password = "your-password"
secure = 1

# 2. Initialize database
make init-clickhouse

# 3. Load data to ClickHouse
make run-etl-clickhouse

# 4. (Optional) Anonymize for public dashboards
make anonymize-clickhouse

# 5. Configure Rill to use ClickHouse
cd viz_rill
echo 'RILL_CONNECTOR=clickhouse' >> .env
echo 'connector.clickhouse.dsn=clickhouse://user:pass@host:8443/default?secure=true' >> .env

# 6. View dashboards
cd .. && make serve
```

Done! Your dashboards now show ClickHouse data.

## Detailed Setup

### Step 1: Create ClickHouse Service

1. Go to [ClickHouse Cloud Console](https://clickhouse.cloud)
2. Click "Create new service"
3. Choose:
   - **Provider**: GCP, AWS, or Azure
   - **Region**: Choose closest to your data sources
   - **Tier**: Development (free tier) or Production
4. Click "Create service"
5. **Save credentials** (you won't see the password again):
   ```
   Host: xxxxx.region.gcp.clickhouse.cloud
   Port: 8443
   Username: default
   Password: [copy this!]
   ```

### Step 2: Configure Local Credentials

Edit `.dlt/secrets.toml`:

```toml
[destination.clickhouse.credentials]
host = "xxxxx.europe-west4.gcp.clickhouse.cloud"
port = 8443
username = "default"
password = "your-secure-password"
secure = 1
```

See `.dlt/secrets.toml.example` for full template.

### Step 3: Initialize Database

```bash
make init-clickhouse
```

This creates the necessary database and permissions for dlt.

### Step 4: Test Data Ingestion

Start with one pipeline:

```bash
make run-aws-clickhouse
```

Verify data arrived:

```bash
# Using clickhouse-client
clickhouse-client --host xxxxx.clickhouse.cloud --secure \
  --password 'your-password' \
  --query "SELECT count(*) FROM aws_costs___cur_export_test_00001"
```

Or use ClickHouse Cloud SQL console in the web UI.

### Step 5: Run All Pipelines

```bash
make run-etl-clickhouse
```

This runs AWS, GCP, and Stripe pipelines to ClickHouse.

## Switching Between Local and Cloud

### Mode Switching

The project uses environment variables to switch between local and cloud:

**ETL destination** (set automatically by Makefile):
- `DLT_DESTINATION=filesystem` → Parquet files (local)
- `DLT_DESTINATION=clickhouse` → ClickHouse Cloud

**Rill connector** (set in `viz_rill/.env`):
- `RILL_CONNECTOR=""` or not set → DuckDB reads parquet (local)
- `RILL_CONNECTOR=clickhouse` → Rill queries ClickHouse

### Local Mode (Default)

```bash
# ETL to parquet
make run-all

# Rill automatically uses parquet files
make serve
```

**No configuration needed!** This is the default.

### Cloud Mode

**Option A: ETL + View locally**
```bash
# 1. Load to ClickHouse
make run-etl-clickhouse

# 2. Configure Rill
cd viz_rill
cat > .env << 'EOF'
RILL_CONNECTOR=clickhouse
connector.clickhouse.dsn=clickhouse://user:pass@host:8443/default?secure=true
EOF

# 3. View dashboards
cd .. && make serve
```

**Option B: Full Cloud Pipeline (ETL + Anonymize)**
```bash
# Loads data and anonymizes in one command
make run-all-cloud

# Then configure Rill as above
```

### Switching Back to Local

```bash
cd viz_rill
# Remove or comment out RILL_CONNECTOR
echo 'RILL_CONNECTOR=""' > .env
cd .. && make serve
```

Rill now reads parquet files again.

### Data Structure

**ClickHouse tables created:**
```
aws_costs___cur_export_test_00001      # AWS raw data
gcp_costs___bigquery_billing_table     # GCP raw data
stripe_costs___balance_transaction     # Stripe raw data

aws_costs                              # Rill model (materialized)
gcp_costs                              # Rill model (materialized)
stripe_revenue                         # Rill model (materialized)
unified_cost_model                     # Rill model (materialized)
```

## Data Anonymization

For public dashboards, anonymize your cost data:

### What Gets Anonymized

- **Cost values**: Multiplied by random 2-8x factor
- **Row duplication**: 3x more data by default
- **IDs hashed**: Account IDs, project IDs anonymized

### Usage

```bash
# After loading data to ClickHouse
make anonymize-clickhouse

# Customize with environment variables
COST_MULTIPLIER_MIN=5.0 COST_MULTIPLIER_MAX=10.0 DUPLICATE_ROWS=5 make anonymize-clickhouse
```

### Clearing Data

```bash
# Interactive (asks for confirmation)
make clear-clickhouse

# Force mode (for scripts)
make clear-clickhouse-force

# Dry run (see what would be deleted)
uv run python scripts/clear_clickhouse.py --dry-run
```

This drops all dlt tables AND Rill model tables.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COST_MULTIPLIER_MIN` | `2.0` | Minimum cost multiplier |
| `COST_MULTIPLIER_MAX` | `8.0` | Maximum cost multiplier |
| `DUPLICATE_ROWS` | `3` | Row duplication factor |

See [ANONYMIZATION.md](ANONYMIZATION.md) for details.

## GitHub Actions Automation

Automate daily data loads to ClickHouse.

### Setup

1. **Add GitHub Secrets** (Settings → Secrets → Actions):
   - `CLICKHOUSE_HOST` - Your ClickHouse host
   - `CLICKHOUSE_USERNAME` - Usually `default`
   - `CLICKHOUSE_PASSWORD` - Your ClickHouse password
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - `GCP_PROJECT_ID`, `GCP_PRIVATE_KEY`, `GCP_CLIENT_EMAIL`
   - `STRIPE_SECRET_KEY`

2. **Workflow already exists** at `.github/workflows/etl-pipeline.yml`

3. **Test manual trigger**:
   - Go to Actions tab → Cloud Cost ETL Pipeline
   - Click "Run workflow"
   - Monitor progress

### Schedule

- Runs daily at 2 AM UTC automatically
- Loads only new data (incremental)
- ~5-10 minutes per run

### Monitoring

- Check Actions tab for status
- Green checkmark = success
- Logs available in each workflow run

## Troubleshooting

### Connection Issues

**"Cannot connect to ClickHouse"**

Solutions:
- Verify ClickHouse service is running (check cloud console)
- Check host includes full domain: `xxxxx.region.gcp.clickhouse.cloud`
- Ensure `secure = 1` in secrets.toml
- Test connection:
  ```bash
  clickhouse-client --host xxx --secure --password 'xxx' --query "SELECT 1"
  ```

### Authentication Errors

**"Authentication failed"**

Solutions:
- Verify credentials in `.dlt/secrets.toml`
- No trailing spaces in values
- Try regenerating password in ClickHouse console
- Update both local config and GitHub Secrets

### Rill Connection Issues

**"Model execution is disabled" or "read_parquet not found"**

Solutions:
- Check `RILL_CONNECTOR=clickhouse` is set in `viz_rill/.env`
- Verify ClickHouse DSN is correct
- Make sure `rill.yaml` has `olap_connector: clickhouse`
- Restart Rill after changing config

### Data Issues

**"No data in dashboards"**

Solutions:
- Verify data loaded: `SELECT count(*) FROM aws_costs___cur_export_test_00001`
- Check Rill is using correct connector
- Look for errors in Rill startup logs
- Verify models reconciled successfully

**"Dashboards show errors on some visualizations"**

Solutions:
- Some visualizations may need column adjustments
- Check metrics files reference correct columns
- Models select all columns with `SELECT *`, so schema should match

### Performance Issues

**"Queries are slow"**

Solutions:
- Add indexes in ClickHouse for common query patterns
- Use materialized views for aggregations
- Optimize metrics to reduce data scanned
- Consider table partitioning for large datasets

### Clearing and Reloading

**Start fresh:**

```bash
# 1. Clear ClickHouse
make clear-clickhouse-force

# 2. Reload data
make run-etl-clickhouse

# 3. Anonymize if needed
make anonymize-clickhouse
```

## Cost Optimization

### ClickHouse Cloud Costs

- **Free tier**: Development tier available
- **Idle scaling**: Auto-scales to zero when not in use
- **Optimization**: Run ETL once daily (sufficient for most use cases)

### GitHub Actions Costs

- **Free tier**: 2,000 minutes/month for public repos
- **Usage**: ~5-10 minutes per run × 30 days = ~300 minutes/month
- **Well under limit** for daily schedules

## Advanced: Normalization (Optional)

### Are normalization scripts still needed?

**Short answer: No, normalization is optional for both local and cloud modes.**

The normalization scripts (`normalize.py`, `normalize_gcp.py`) are now **optional** because:
- Models use `SELECT *` to get all columns from raw data
- ClickHouse and DuckDB can query nested structures directly
- Current dashboards work perfectly with raw, unnormalized data
- Models add derived columns (like `product_product_name`) where needed

### When to use normalization

**Only use normalization if you need:**
- CUR Wizard dynamic dashboards (canvas generation)
- Pre-flattened tag/label columns for external tools
- Compatibility with tools that can't query nested structures

**Current approach (no normalization):**
1. Pipelines load raw data to parquet/ClickHouse
2. Models query raw data and add derived columns
3. Dashboards use models

### If you still want normalization

**Important:** Dynamic dashboard generation (`make aws-dashboards` / `make gcp-dashboards`) only works in **local mode** because it requires parquet files to analyze. ClickHouse mode doesn't create parquet files.

**For local mode only:**
```bash
# These commands work ONLY with local parquet files
make aws-dashboards   # Requires: viz_rill/data/aws_costs/*.parquet
make gcp-dashboards   # Requires: viz_rill/data/gcp_costs/*.parquet
```

**For ClickHouse (alternative approach):**
```sql
-- Create materialized view instead of Python normalization
CREATE MATERIALIZED VIEW aws_costs_normalized AS
SELECT
  *,
  resource_tags['Environment'] AS tag_environment,
  resource_tags['Team'] AS tag_team
FROM aws_costs___cur_export_test_00001;
```

ClickHouse materialized views are:
- ✅ Faster than Python scripts
- ✅ No intermediate parquet files needed
- ✅ Updated automatically as new data arrives
- ✅ Native ClickHouse performance

## Next Steps

After successful ClickHouse deployment:

1. **Configure Rill Cloud** (optional):
   - Deploy dashboards: `cd viz_rill && rill deploy`
   - Set ClickHouse credentials in Rill Cloud settings
   - Share dashboards with team

2. **Set up monitoring** (optional):
   - Add Slack/email notifications to workflow
   - Monitor data freshness
   - Set up alerts for failed runs

3. **Optimize performance** (optional):
   - Add ClickHouse indexes for common queries
   - Create aggregation tables
   - Adjust workflow frequency based on needs

## Resources

- **ClickHouse docs**: https://clickhouse.com/docs
- **dlt ClickHouse destination**: https://dlthub.com/docs/dlt-ecosystem/destinations/clickhouse
- **Rill docs**: https://docs.rilldata.com

