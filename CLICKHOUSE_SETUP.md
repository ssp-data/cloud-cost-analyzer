# ClickHouse Cloud Setup Guide

This guide explains how to deploy your cloud cost analytics pipelines to ClickHouse Cloud with GitHub Actions.

## Architecture Overview

### Two Deployment Modes

1. **Local Development** (default)
   - Destination: `filesystem`
   - Output: Parquet files in `viz_rill/data/`
   - Visualization: Local Rill server
   - Command: `make run-etl`

2. **Production** (GitHub Actions)
   - Destination: `clickhouse`
   - Output: Direct ingestion to ClickHouse Cloud
   - Visualization: Rill Cloud or BI tool connected to ClickHouse
   - Command: `make run-etl-clickhouse`

### How It Works

The pipelines use the `DLT_DESTINATION` environment variable to switch between destinations:

- `DLT_DESTINATION=filesystem` (default) → Writes parquet files locally
- `DLT_DESTINATION=clickhouse` → Writes directly to ClickHouse Cloud

**No code duplication** - same pipeline files work for both destinations!

## Setup Steps

### 1. Prerequisites

- ClickHouse Cloud account ([sign up here](https://clickhouse.cloud))
- GitHub repository with this codebase
- AWS, GCP, and Stripe credentials (same as local setup)

### 2. Create ClickHouse Service

1. Log in to ClickHouse Cloud
2. Find the `connect` button and choose HTTPS for getting the details below
3. Note your connection details:
   - Host: `xxxxx.region.gcp.clickhouse.cloud`
   - Port: `8443` (HTTPS)
   - Username: `default` (or create dedicated user)
   - Password: (save securely)

### 3. Configure Local ClickHouse Credentials

Add to `.dlt/secrets.toml`:

```toml
[destination.clickhouse.credentials]
host = "xxxxx.europe-west4.gcp.clickhouse.cloud"
port = 8443
username = "default"
password = "your-secure-password"
secure = 1
```

See `.dlt/secrets.toml.example` for full template.

### 4. Initialize ClickHouse Database

Run the initialization script once:

```bash
make init-clickhouse
```

This creates:
- Database: `dlt`
- User: `dlt` (optional, can use default user)
- Required permissions for dlt pipelines

### 5. Test Local ClickHouse Ingestion

Before setting up GitHub Actions, test locally:

```bash
# Run ETL to ClickHouse
make run-etl-clickhouse

# Verify data in ClickHouse
clickhouse-client --host xxxxx.clickhouse.cloud --secure --password 'your-password' \
  --query "SELECT count(*) FROM dlt.aws_costs__cur_export_test_00001"
```

### 6. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

**ClickHouse:**
- `CLICKHOUSE_HOST` - e.g., `xxxxx.europe-west4.gcp.clickhouse.cloud`
- `CLICKHOUSE_USERNAME` - e.g., `default` or `dlt`
- `CLICKHOUSE_PASSWORD` - Your ClickHouse password

**AWS:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**GCP:**
- `GCP_PROJECT_ID`
- `GCP_PRIVATE_KEY` - Full service account private key
- `GCP_CLIENT_EMAIL`

**Stripe:**
- `STRIPE_SECRET_KEY`

### 7. Enable GitHub Actions

The workflow is in `.github/workflows/etl-pipeline.yml`

**Schedule:**
- Runs daily at 2 AM UTC
- Manually triggerable via "Actions" tab → "Run workflow"

**What it does:**
1. Runs AWS, GCP, and Stripe pipelines
2. Ingests raw data directly to ClickHouse
3. (Optional) Normalizes data and ingests to ClickHouse

## Usage

### Local Development

```bash
# Run ETL locally (writes parquet files)
make run-etl

# Normalize data
make aws-normalize gcp-normalize

# View in Rill
make serve
```

### Production (ClickHouse)

```bash
# Run ETL to ClickHouse
make run-etl-clickhouse

# Also ingest normalized data (optional)
make aws-normalize gcp-normalize
make ingest-normalized-clickhouse
```

### GitHub Actions

**Automatic (daily at 2 AM UTC):**
- Runs automatically, ingests to ClickHouse
- Check "Actions" tab for status

**Manual trigger:**
1. Go to "Actions" tab
2. Select "Cloud Cost ETL Pipeline"
3. Click "Run workflow"
4. Choose whether to include normalized data
5. Click "Run workflow" button

## Data Structure in ClickHouse

### Raw Data (from dlt pipelines)

```
dlt.aws_costs__cur_export_test_00001      # AWS CUR raw data
dlt.gcp_costs__bigquery_billing_table     # GCP billing raw data
dlt.stripe_costs__balance_transaction     # Stripe transactions
```

### Normalized Data (optional, from normalize scripts)

```
dlt.cloud_costs_normalized__aws_costs_normalized  # Flattened AWS tags
dlt.cloud_costs_normalized__gcp_costs_normalized  # Flattened GCP labels
```

## Connecting Rill Cloud to ClickHouse

Update your Rill Cloud project to use ClickHouse:

```yaml
# rill.yaml (or similar)
type: clickhouse
host: ${CLICKHOUSE_HOST}
port: 8443
username: ${CLICKHOUSE_USERNAME}
password: ${CLICKHOUSE_PASSWORD}
database: dlt
ssl: true
```

Then update sources to query ClickHouse tables:

```yaml
# sources/aws_costs.yaml
type: sql
sql: SELECT * FROM dlt.aws_costs__cur_export_test_00001
```

## Normalization in GitHub Actions

The normalization scripts require parquet files as input. In GitHub Actions:

1. **Option 1: Skip normalization** (default)
   - Sufficient for basic cost analytics
   - Dashboards use raw data directly

2. **Option 2: Run normalization in GitHub Actions**
   - Enable with workflow input: `include_normalized: true`
   - Pipelines write to filesystem first (temporary)
   - Normalize scripts read parquet files
   - Ingest normalized data to ClickHouse
   - This adds extra time but enables advanced dashboards

3. **Option 3: Normalize in ClickHouse with SQL**
   - Best for production
   - Use ClickHouse materialized views or SQL to flatten tags/labels
   - Example:
   ```sql
   CREATE MATERIALIZED VIEW aws_costs_normalized AS
   SELECT
     *,
     resource_tags['Environment'] AS tag_environment,
     resource_tags['Team'] AS tag_team
   FROM dlt.aws_costs__cur_export_test_00001
   ```

## Troubleshooting

### Pipeline fails with "Authentication failed"

- Check ClickHouse credentials in GitHub Secrets
- Verify host includes full domain: `xxxxx.region.gcp.clickhouse.cloud`
- Ensure `secure = 1` in config

### "Table already exists" errors

- dlt handles this automatically with merge/append
- If issues persist, manually drop tables:
  ```sql
  DROP TABLE IF EXISTS dlt.aws_costs__cur_export_test_00001;
  ```

### GitHub Actions runs too long / times out

- Consider running pipelines in parallel (already configured)
- Reduce data volume with `initial_start_date` in config.toml
- Increase GitHub Actions timeout if needed

### Normalized data not appearing

- Check that `include_normalized: true` was selected
- Verify parquet files exist in viz_rill/data/ during workflow
- Check workflow logs for normalization script errors

## Cost Optimization

### ClickHouse Cloud Costs

- Charges based on compute + storage
- Idle services auto-scale to zero (cheap)
- Production: Use scheduled pipelines (1x daily)
- Dev/test: Use local parquet files

### GitHub Actions Costs

- 2,000 free minutes/month for public repos
- ~5-10 minutes per run = ~300 runs/month free
- Daily schedule = ~30 runs/month (well under limit)

## Migration from Local to ClickHouse

Your local development workflow remains unchanged:

```bash
# Local development (unchanged)
make run-etl
make serve
```

Production deployment is additive:

```bash
# Production (new)
make run-etl-clickhouse
```

Both can run simultaneously - no conflicts!

## Next Steps

1. Set up ClickHouse Cloud account
2. Run `make init-clickhouse` locally
3. Test with `make run-etl-clickhouse`
4. Configure GitHub Secrets
5. Enable GitHub Actions workflow
6. Connect Rill Cloud or BI tool to ClickHouse

## Support

- ClickHouse docs: https://clickhouse.com/docs
- dlt ClickHouse destination: https://dlthub.com/docs/dlt-ecosystem/destinations/clickhouse
- GitHub Actions: https://docs.github.com/actions
