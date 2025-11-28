# Deployment Architecture Summary

## Overview

Your cloud cost analytics platform now supports **dual deployment modes** with **zero code duplication**:

1. **Local Development** - Parquet files + Rill local server
2. **Production** - ClickHouse Cloud + GitHub Actions + Rill Cloud

## How It Works

### Single Codebase, Two Destinations

All pipeline files (`aws_pipeline.py`, `google_bq_incremental_pipeline.py`, `stripe_pipeline.py`) use environment variable `DLT_DESTINATION` to switch destinations:

```python
destination = os.getenv("DLT_DESTINATION", "filesystem")  # Default: filesystem

pipeline = dlt.pipeline(
    pipeline_name=pipeline_name,
    destination=destination,  # Dynamic!
    dataset_name=dataset_name,
)

# Conditional loader format
if destination == "filesystem":
    load_info = pipeline.run(resource, loader_file_format="parquet")
else:
    load_info = pipeline.run(resource)
```

### Configuration

**Single config file** (`.dlt/config.toml`) contains settings for both destinations:

```toml
# Filesystem destination (local)
[destination.filesystem]
bucket_url = "viz_rill/data"

# ClickHouse destination (production)
[destination.clickhouse]
database = "dlt"
```

**Single secrets file** (`.dlt/secrets.toml`) with all credentials:
- AWS credentials (for S3 access)
- GCP service account (for BigQuery)
- Stripe API key
- ClickHouse credentials (new)

## Usage

### Local Development (Default)

```bash
# No environment variable needed
make run-etl          # Writes to viz_rill/data/*.parquet
make serve            # View in Rill at localhost:9009
```

### Production (ClickHouse)

```bash
# Set DLT_DESTINATION=clickhouse
make run-etl-clickhouse    # Writes to ClickHouse Cloud
```

### GitHub Actions (Automated)

Workflow runs daily at 2 AM UTC:
- Sets `DLT_DESTINATION=clickhouse` automatically
- Runs all three pipelines
- Data lands directly in ClickHouse Cloud

## Data Flow

### Local Development
```
┌─────────────────┐
│ AWS S3 CUR      │───┐
└─────────────────┘   │
                      │    ┌──────────────────┐    ┌────────────────┐    ┌──────────────┐
┌─────────────────┐   ├───→│ dlt Pipelines    │───→│ Parquet Files  │───→│ Rill Local   │
│ GCP BigQuery    │───┤    │ (filesystem dest)│    │ viz_rill/data/ │    │ localhost    │
└─────────────────┘   │    └──────────────────┘    └────────────────┘    └──────────────┘
                      │
┌─────────────────┐   │
│ Stripe API      │───┘
└─────────────────┘
```

### Production (GitHub Actions)
```
┌─────────────────┐
│ AWS S3 CUR      │───┐
└─────────────────┘   │
                      │    ┌──────────────────┐    ┌───────────────────┐    ┌──────────────┐
┌─────────────────┐   ├───→│ dlt Pipelines    │───→│ ClickHouse Cloud  │───→│ Rill Cloud   │
│ GCP BigQuery    │───┤    │ (clickhouse dest)│    │ dlt.aws_costs__*  │    │ or BI Tools  │
└─────────────────┘   │    └──────────────────┘    │ dlt.gcp_costs__*  │    └──────────────┘
                      │         (GitHub Actions)   │ dlt.stripe__*     │
┌─────────────────┐   │                            └───────────────────┘
│ Stripe API      │───┘
└─────────────────┘
```

## Normalization (aws-normalize, gcp-normalize)

### Local (Current Workflow)
1. Run `make run-etl` → Creates parquet files
2. Run `make aws-normalize gcp-normalize` → Reads parquet, flattens tags/labels, writes `normalized_*.parquet`
3. Run `make serve` → Rill reads both raw and normalized parquet files

### Production (Three Options)

**Option 1: Skip normalization** (simplest)
- Raw data in ClickHouse is sufficient for basic analytics
- Tags/labels stored as MAP columns, queryable directly
- GitHub Actions: Just run ETL pipelines

**Option 2: Normalize in GitHub Actions** (current approach adapted)
- Pipelines write to temporary filesystem
- Normalize scripts read parquet files
- Ingest normalized data to ClickHouse
- GitHub Actions workflow supports this with `include_normalized: true`
- Adds ~5 minutes to workflow

**Option 3: Normalize in ClickHouse** (best for production)
- Raw data ingested to ClickHouse
- Use SQL/materialized views to flatten tags:
  ```sql
  CREATE MATERIALIZED VIEW aws_costs_normalized AS
  SELECT
    *,
    resource_tags['Environment'] AS tag_environment,
    resource_tags['Team'] AS tag_team,
    resource_tags['Application'] AS tag_application
  FROM dlt.aws_costs__cur_export_test_00001
  ```
- No parquet files needed, pure SQL transformation
- Recommended for production

## Key Files Created/Modified

### New Files
- `scripts/init_clickhouse.py` - Initialize ClickHouse database
- `pipelines/ingest_normalized_pipeline.py` - Ingest normalized parquet → ClickHouse
- `.dlt/secrets.toml.example` - Credentials template
- `.github/workflows/etl-pipeline.yml` - GitHub Actions workflow
- `CLICKHOUSE_SETUP.md` - Complete setup guide
- `DEPLOYMENT_SUMMARY.md` - This file

### Modified Files
- `pipelines/aws_pipeline.py` - Added destination switching
- `pipelines/google_bq_incremental_pipeline.py` - Added destination switching
- `pipelines/stripe_pipeline.py` - Added destination switching
- `.dlt/config.toml` - Added ClickHouse destination config
- `Makefile` - Added ClickHouse targets
- `CLAUDE.md` - Updated documentation

## Setup Checklist

### One-Time Setup

- [ ] Create ClickHouse Cloud account
- [ ] Create ClickHouse service (note host, username, password)
- [ ] Add ClickHouse credentials to `.dlt/secrets.toml`
- [ ] Run `make init-clickhouse` to create database
- [ ] Test locally: `make run-etl-clickhouse`
- [ ] Add GitHub Secrets (8 secrets total)
- [ ] Enable GitHub Actions workflow

### GitHub Secrets Required

1. `CLICKHOUSE_HOST` - e.g., `xxxxx.europe-west4.gcp.clickhouse.cloud`
2. `CLICKHOUSE_USERNAME` - e.g., `default`
3. `CLICKHOUSE_PASSWORD` - Your ClickHouse password
4. `AWS_ACCESS_KEY_ID` - AWS credentials
5. `AWS_SECRET_ACCESS_KEY` - AWS credentials
6. `GCP_PROJECT_ID` - GCP project ID
7. `GCP_PRIVATE_KEY` - GCP service account private key
8. `GCP_CLIENT_EMAIL` - GCP service account email
9. `STRIPE_SECRET_KEY` - Stripe API key

## Migration Path

### Phase 1: Local Development (Current)
```bash
make run-etl
make serve
```

### Phase 2: Test ClickHouse Locally
```bash
# Add ClickHouse credentials to .dlt/secrets.toml
make init-clickhouse
make run-etl-clickhouse
```

### Phase 3: Deploy to GitHub Actions
```bash
# Configure GitHub Secrets
# Enable workflow in .github/workflows/etl-pipeline.yml
# Workflow runs daily automatically
```

### Phase 4: Connect Rill Cloud (Optional)
- Point Rill Cloud to ClickHouse instead of parquet files
- Update source definitions to query ClickHouse tables
- Enable collaborative dashboards

## Benefits

### Local Development
- Fast iteration (no network overhead)
- Works offline
- Easy debugging with parquet files
- No cloud costs during development

### Production (ClickHouse)
- Centralized data storage
- Direct ingestion (no intermediate files)
- Real-time analytics
- Scalable (handles large datasets)
- Multiple users can access same data
- Scheduled automated updates
- Incremental loading (only new data)

## Cost Considerations

### ClickHouse Cloud
- Pay per usage (compute + storage)
- Idle services auto-pause (minimal cost)
- Typical cost: $20-100/month for medium datasets
- Free tier available for testing

### GitHub Actions
- 2,000 free minutes/month (public repos)
- 500 free minutes/month (private repos)
- Each run: ~5-10 minutes
- Daily schedule: ~30 runs/month = ~300 minutes/month
- Well within free tier limits

## Next Steps

1. Review `CLICKHOUSE_SETUP.md` for detailed setup instructions
2. Add ClickHouse credentials to `.dlt/secrets.toml`
3. Run `make init-clickhouse` to initialize database
4. Test with `make run-etl-clickhouse`
5. Configure GitHub Secrets
6. Enable GitHub Actions workflow
7. Monitor first automated run
8. Connect Rill Cloud or BI tool to ClickHouse

## Support & Documentation

- **Local setup**: See `CLAUDE.md`
- **ClickHouse setup**: See `CLICKHOUSE_SETUP.md`
- **dlt docs**: https://dlthub.com/docs
- **ClickHouse docs**: https://clickhouse.com/docs
- **GitHub Actions**: https://docs.github.com/actions

## Questions?

Common questions answered in `CLICKHOUSE_SETUP.md`:
- How to handle normalized data in production?
- How to connect Rill Cloud to ClickHouse?
- What if pipelines fail?
- How to optimize costs?
- How to migrate from local to production?
