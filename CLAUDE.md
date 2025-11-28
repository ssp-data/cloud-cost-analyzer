# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Multi-cloud cost analytics platform combining AWS Cost and Usage Reports (CUR), GCP BigQuery billing exports, and Stripe revenue data. Built with dlt for data ingestion, DuckDB for storage, and Rill for visualization.

## Essential Commands

### Development Workflow

**Local Development (Parquet Files):**
```bash
# Install dependencies
uv sync

# Run complete ETL + visualization pipeline
make run-all

# Run individual pipelines (writes parquet to viz_rill/data/)
make run-aws      # AWS CUR from S3
make run-gcp      # GCP billing from BigQuery
make run-stripe   # Stripe revenue data

# Run all ETL pipelines (local)
make run-etl

# Start Rill dashboards (port 9009)
make serve
```

**Production (ClickHouse Cloud):**
```bash
# Initialize ClickHouse (run once)
make init-clickhouse

# Run all ETL pipelines to ClickHouse
make run-etl-clickhouse

# Run individual pipelines to ClickHouse
make run-aws-clickhouse
make run-gcp-clickhouse
make run-stripe-clickhouse

# Ingest normalized data to ClickHouse (optional)
make ingest-normalized-clickhouse
```

**Normalization & Dashboard Generation:**
```bash
# Generate dynamic AWS dashboards (optional)
make aws-dashboards      # Normalize + generate AWS canvases
make aws-normalize       # Just normalize AWS data
make aws-generate-dashboards  # Just generate dashboards

# Generate dynamic GCP dashboards (optional)
make gcp-dashboards
make gcp-normalize
make gcp-generate-dashboards

# Testing
make test            # Run duplicate checks on parquet files
make test-duplicates # Same as above
make test-duplicates-duckdb  # Check DuckDB database (legacy)

# Data management
make clear          # Clear dlt cache and parquet data (backs up DuckDB)
make clear-data     # Clear only parquet data
make dlt-clear      # Clear only dlt cache
```

### Running Single Tests
To test a specific pipeline without running all ETL:
```bash
uv run python pipelines/aws_pipeline.py
uv run python pipelines/google_bq_incremental_pipeline.py
uv run python pipelines/stripe_pipeline.py
```

## Architecture

### Data Flow

**Local Development:**
```
Cloud Providers → dlt Pipelines (filesystem) → Parquet Files → Rill Local
                                              ↓
                                          viz_rill/data/
                                            ├── aws_costs/
                                            ├── gcp_costs/
                                            └── stripe_costs/
```

**Production (GitHub Actions):**
```
Cloud Providers → dlt Pipelines (clickhouse) → ClickHouse Cloud → Rill Cloud / BI Tools
                                              ↓
                                          dlt.aws_costs__*
                                          dlt.gcp_costs__*
                                          dlt.stripe_costs__*
```

**Environment Variable Controls Destination:**
- `DLT_DESTINATION=filesystem` (default) → Local parquet files
- `DLT_DESTINATION=clickhouse` → ClickHouse Cloud

### Pipeline System (dlt-based)

**Key Architecture Pattern**: All pipelines support dual destinations via `DLT_DESTINATION` environment variable:
- **Local**: `destination="filesystem"` with `loader_file_format="parquet"` writes to `viz_rill/data/`
- **Production**: `destination="clickhouse"` writes directly to ClickHouse Cloud

**Three Independent Pipelines**:

1. **AWS Pipeline** (`pipelines/aws_pipeline.py`)
   - Reads parquet files from S3 bucket (configured in `.dlt/config.toml`)
   - Uses incremental loading based on `modification_date`
   - Deduplicates using composite primary key: `identity_line_item_id` + `identity_time_interval`
   - Write disposition: `merge` (enforces primary key constraint)
   - Output: `viz_rill/data/aws_costs/cur_export_test_00001/*.parquet`

2. **GCP Pipeline** (`pipelines/google_bq_incremental_pipeline.py`)
   - Queries BigQuery billing export tables using service account credentials
   - Uses incremental loading based on `export_time` cursor (initial: 2000-01-01)
   - Loads two tables: resource-level and standard billing exports
   - Write disposition: `append` (cost data is append-only)
   - Credentials from `.dlt/secrets.toml` under `[source.bigquery.credentials]`
   - Output: `viz_rill/data/gcp_costs/*.parquet`

3. **Stripe Pipeline** (`pipelines/stripe_pipeline.py`)
   - Uses Stripe API via custom `stripe_analytics` dlt source
   - Loads events and balance transactions
   - Credentials: `stripe_secret_key` in `.dlt/secrets.toml`
   - Output: `viz_rill/data/stripe_costs/*.parquet`

**dlt Configuration**:
- `.dlt/config.toml`: Pipeline settings, S3 paths, table names
- `.dlt/secrets.toml`: Credentials (AWS, GCP service account, Stripe API key)
- `.env`: Exports AWS credentials from environment variables for dlt

### Visualization Layer (Rill)

Located in `viz_rill/` - contains both static and dynamically generated dashboards.

**Static Dashboards** (always in git):
- `dashboards/aws_overview.yaml` - Effective cost, RI/SP utilization, regional breakdown
- `dashboards/aws_explore.yaml` - Interactive AWS cost explorer
- `dashboards/aws_product_insights.yaml` - Product dimension analysis
- `dashboards/gcp_overview.yaml` - GCP cost overview
- `dashboards/gcp_product_insights.yaml` - GCP product analysis
- `dashboards/cloud_cost_explore.yaml` - Multi-cloud overview
- `sources/aws_cost_normalized.yaml` - Queries parquet files directly
- `metrics/aws_cost_metrics.yaml` - 20+ AWS-specific measures (effective cost, RI utilization, etc.)
- `metrics/cloud_cost_metrics.yaml` - Multi-cloud metrics

**Dynamic Generation** (gitignored, optional):
- `canvases/` - Auto-generated dimension-specific dashboards
- `explores/` - Auto-generated explorers
- Generated by cur-wizard scripts when running `make aws-dashboards` or `make gcp-dashboards`

**cur-wizard Integration**:
- `viz_rill/cur-wizard/` contains scripts adapted from [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard)
- Normalizes AWS/GCP data and generates Rill YAML using Jinja2 templates
- Scripts: `normalize.py`, `generate_rill_yaml.py`, `normalize_gcp.py`, `generate_gcp_rill_yaml.py`
- Algorithm intelligently selects chart types based on cardinality

### Key Concepts

**Incremental Loading**:
- AWS: Tracks `modification_date` of S3 files
- GCP: Tracks `export_time` with initial value of 2000-01-01
- Stripe: Uses dlt source's built-in incremental handling
- State managed by dlt in `~/.local/share/dlt/`

**Deduplication Strategy**:
- AWS: Uses `merge` disposition with composite primary key (prevents duplicates)
- GCP: Uses `append` disposition (relies on unique export_time + invoice details)
- Stripe: Uses `append` disposition (events/transactions have unique IDs)
- Tests auto-generate SQL from config using `tests/run_duplicate_tests.py`

**Data Storage**:
- Primary: Parquet files in `viz_rill/data/` (used by Rill dashboards)
- Legacy: `cloud_cost_analytics.duckdb` (optional, for SQL queries)
- Rill queries parquet files directly via DuckDB under the hood

## Configuration Files

**All configuration is now centralized in `.dlt/config.toml` and `.dlt/secrets.toml`** - no need to edit pipeline files!

### Dual Destination Support

The pipelines automatically switch destinations based on the `DLT_DESTINATION` environment variable:
- Not set or `filesystem` → Local development (parquet files)
- `clickhouse` → Production (ClickHouse Cloud)

### Configuration Files

1. `.dlt/config.toml` - Update these values:
   ```toml
   # Pipeline configuration (shared across all pipelines)
   [pipeline]
   pipeline_name = "cloud_cost_analytics"

   # AWS CUR configuration
   [sources.aws_cur]
   bucket_url = "s3://your-bucket"
   file_glob = "cur/your-report/data/**/*.parquet"
   table_name = "your_table_name"
   dataset_name = "aws_costs"

   # GCP BigQuery billing export configuration
   [sources.gcp_billing]
   project_id = "your-project-id"
   dataset = "billing_export"
   dataset_name = "gcp_costs"
   table_names = [
       "gcp_billing_export_resource_v1_XXXXXX_XXXXXX_XXXXXX",
       "gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX"
   ]

   # Stripe configuration
   [sources.stripe]
   dataset_name = "stripe_costs"
   ```

2. `.dlt/secrets.toml` - Add credentials:
   ```toml
   [sources.filesystem.credentials]
   aws_access_key_id = "your-key"
   aws_secret_access_key = "your-secret"

   [source.bigquery.credentials]
   project_id = "your-project"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n"
   client_email = "service-account@project.iam.gserviceaccount.com"
   token_uri = "https://oauth2.googleapis.com/token"

   [sources.stripe_analytics]
   stripe_secret_key = "sk_live_..."

   # ClickHouse credentials (for production deployment)
   [destination.clickhouse.credentials]
   host = "xxxxx.europe-west4.gcp.clickhouse.cloud"
   port = 8443
   username = "default"
   password = "your-password"
   secure = 1
   ```

See `.dlt/secrets.toml.example` for template.

## Project Structure

```
cloud-cost-analyzer/
├── pipelines/              # dlt ETL pipelines
│   ├── aws_pipeline.py                      # AWS CUR (dual destination)
│   ├── google_bq_incremental_pipeline.py    # GCP BigQuery (dual destination)
│   ├── stripe_pipeline.py                   # Stripe revenue (dual destination)
│   ├── ingest_normalized_pipeline.py        # Normalized data → ClickHouse
│   └── helpers/                             # Stripe analytics helper modules
├── scripts/                # Utility scripts
│   └── init_clickhouse.py           # Initialize ClickHouse database
├── viz_rill/               # Rill visualization project
│   ├── dashboards/                  # Static dashboards (version controlled)
│   ├── sources/                     # Data source definitions
│   ├── metrics/                     # Metric definitions
│   ├── models/                      # SQL transformations
│   ├── data/                        # Parquet files (gitignored)
│   ├── cur-wizard/                  # Dashboard generator scripts
│   │   ├── scripts/                 # Python generators
│   │   └── templates/               # Jinja2 templates
│   ├── canvases/                    # Generated dashboards (gitignored)
│   └── explores/                    # Generated explorers (gitignored)
├── tests/                  # Test SQL scripts
│   ├── test_duplicates.sql          # DuckDB duplicate checks
│   └── test_duplicates_parquet.sql  # Parquet duplicate checks
├── .dlt/                   # dlt configuration
│   ├── config.toml                  # Pipeline configuration (both destinations)
│   ├── secrets.toml                 # Credentials (not in git)
│   └── secrets.toml.example         # Credentials template
├── .github/workflows/      # GitHub Actions
│   └── etl-pipeline.yml             # Production ETL workflow
├── Makefile               # All workflow commands
├── pyproject.toml         # Python dependencies (managed by uv)
├── CLAUDE.md              # This file
└── CLICKHOUSE_SETUP.md    # ClickHouse deployment guide
```

## Important Implementation Notes

**When Modifying Pipelines**:
- Use environment variable to control destination: `destination = os.getenv("DLT_DESTINATION", "filesystem")`
- For filesystem destination: Use `loader_file_format="parquet"` in `pipeline.run()`
- For ClickHouse destination: Omit `loader_file_format` parameter (auto-handled)
- For AWS: Use `write_disposition="merge"` with primary keys to prevent duplicates
- For GCP/Stripe: Use `write_disposition="append"` as data is naturally append-only
- **All configuration values must be read from `dlt.config`** - never hardcode!
- Test for duplicates after changes: `make test` (auto-generates SQL from config)

**When Adding New Cloud Providers**:
1. Create pipeline in `pipelines/new_provider_pipeline.py`
   - Read all config from `dlt.config["sources.newprovider.*"]`
   - Use `dlt.config.get()` with defaults for optional values
2. Add credentials section to `.dlt/secrets.toml`
3. Add configuration section to `.dlt/config.toml` under `[sources.newprovider]`
4. Add Makefile target (e.g., `make run-newprovider`)
5. Update `make run-etl` to include new pipeline
6. Update `tests/run_duplicate_tests.py` to include new provider tests
7. Create Rill source in `viz_rill/sources/`
8. Add dashboard in `viz_rill/dashboards/`

**When Working with Rill Dashboards**:
- Static dashboards in `viz_rill/dashboards/` should be edited directly
- Don't manually edit files in `canvases/` or `explores/` (they're regenerated)
- Run `make serve` to see changes (Rill auto-reloads)
- Rill uses DuckDB to query parquet files directly (no separate database needed)

**Troubleshooting Tips**:
- If pipelines fail: Check credentials in `.dlt/secrets.toml` and config in `.dlt/config.toml`
- If no data in dashboards: Verify parquet files exist in `viz_rill/data/`
- If duplicates appear: Run `make test-duplicates` and check pipeline write_disposition
- If Rill errors: Check `viz_rill/data/` for valid parquet files
- If config values aren't being read: Ensure `.dlt/config.toml` syntax is correct (use TOML linter)
- If AWS table name changed: Update paths in `viz_rill/models/aws_costs.sql` and `viz_rill/sources/aws_cost_normalized.yaml`
- Clear dlt state: `make dlt-clear` (forces full reload next run)

## Currency Handling

The project includes CHF to USD conversion for GCP costs. Check `viz_rill/cur-wizard/scripts/normalize_gcp.py` for conversion logic.

## ClickHouse Cloud Deployment

For production deployment to ClickHouse Cloud with GitHub Actions, see **CLICKHOUSE_SETUP.md** for:
- Setting up ClickHouse Cloud account
- Configuring GitHub Secrets
- Running pipelines to ClickHouse
- Connecting Rill Cloud or BI tools
- Migration strategy from local to production

**Quick Start:**
```bash
# 1. Add ClickHouse credentials to .dlt/secrets.toml
# 2. Initialize database
make init-clickhouse

# 3. Test locally
make run-etl-clickhouse

# 4. Configure GitHub Secrets and enable workflow
```
