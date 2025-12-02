# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-cloud cost analytics platform combining AWS Cost and Usage Reports (CUR), GCP billing data, and Stripe revenue. Built with dlt for data ingestion, DuckDB/ClickHouse for storage, and Rill for visualization.

## Core Architecture

### Two Deployment Modes

**Local Development** (default):
- Data pipelines write to Parquet files in `viz_rill/data/`
- Rill dashboards query Parquet via DuckDB
- Command: `make run-all`

**Cloud Production**:
- Data pipelines write to ClickHouse Cloud
- Rill dashboards query ClickHouse directly
- Command: `make run-all-cloud`
- Requires: ClickHouse credentials in `.dlt/secrets.toml`

Mode is controlled by `DLT_DESTINATION` environment variable (set in Makefile automatically).

### Data Flow

```
1. EXTRACT (dlt incremental pipelines)
   - pipelines/aws_pipeline.py → S3 CUR Parquet
   - pipelines/google_bq_incremental_pipeline.py → BigQuery billing export
   - pipelines/stripe_pipeline.py → Stripe API

2. LOAD (write_disposition="append" for cost data, "merge" for AWS)
   - Local: → viz_rill/data/*.parquet
   - Cloud: → ClickHouse tables

3. MODEL (Rill SQL models in viz_rill/models/)
   - aws_costs.sql, gcp_costs.sql, stripe_revenue.sql
   - Models use {{ if .env.RILL_CONNECTOR }} to switch between DuckDB/ClickHouse
   - unified_cost_model.sql → UNION ALL with currency conversion

4. VISUALIZE (Rill dashboards in viz_rill/dashboards/)
   - Static dashboards (always work)
   - Optional: Dynamic dashboards via CUR Wizard (local mode only)
```

### Key Design Patterns

**Incremental Loading**: All pipelines use dlt's incremental loading
- AWS: `incremental("modification_date")` for S3 files
- GCP: `incremental("export_time")` for BigQuery rows
- Stripe: Built into stripe_analytics helper
- Primary keys: AWS uses composite key `[identity_line_item_id, identity_time_interval]`

**Connector Switching**: Rill SQL models detect mode via template syntax
```sql
{{ if .env.RILL_CONNECTOR }}
  -- ClickHouse query
{{ else }}
  -- DuckDB/Parquet query
{{ end }}
```

**Configuration Centralization**: `.dlt/config.toml` contains all pipeline settings
- Data source paths, table names, dataset names
- `initial_start_date` controls historical data loading
- Secrets in `.dlt/secrets.toml` (not committed)

## Common Development Commands

### Setup and Installation
```bash
uv sync                    # Install Python dependencies from pyproject.toml
make install              # Install Rill CLI + copy .env files
make install-rill         # Install only Rill CLI
```

### Data Pipeline Operations
```bash
make run-etl              # Run all pipelines (AWS + GCP + Stripe) → local parquet
make run-aws              # Run only AWS pipeline
make run-gcp              # Run only GCP pipeline
make run-stripe           # Run only Stripe pipeline

make run-etl-clickhouse   # Run all pipelines → ClickHouse Cloud
make run-aws-clickhouse   # AWS pipeline → ClickHouse
```

### Visualization
```bash
make serve                # Start Rill dashboards (localhost:9009)
make serve-duckdb         # Force DuckDB mode
make serve-clickhouse     # Force ClickHouse mode
```

### Optional: Dynamic Dashboard Generation (local mode only)
```bash
make aws-dashboards       # Normalize + generate AWS canvases
make gcp-dashboards       # Normalize + generate GCP canvases
```
Note: Dynamic generation only works with local Parquet files, not ClickHouse.

### Data Management
```bash
make dlt-clear           # Clear dlt state (forces full reload)
make clear-data          # Backup and clear local parquet files
make clear-rill          # Clear Rill cache
make clear-clickhouse    # Drop ClickHouse tables (interactive)
make clear               # Clear dlt + data + rill
```

### Testing
```bash
make test                # Run duplicate checks on parquet files
make test-duplicates-duckdb  # Check duplicates in DuckDB
```

### Mode Switching
```bash
make set-connector-duckdb      # Switch to local parquet mode
make set-connector-clickhouse  # Switch to ClickHouse mode
```
This modifies `viz_rill/rill.yaml` and `viz_rill/.env`.

### Complete Workflows
```bash
make run-all              # Full local: ETL + dashboards + serve
make run-all-cloud        # Full cloud: ETL → ClickHouse + anonymize + serve
make demo                 # Run with sample data (no credentials needed)
```

## Configuration Files

### `.dlt/config.toml` - Pipeline Configuration
All data source settings:
- AWS: `[sources.aws_cur]` - S3 bucket, file glob, table name
- GCP: `[sources.gcp_billing]` - BigQuery dataset, table names
- Stripe: `[sources.stripe]` - Initial start date
- Destinations: `[destination.filesystem]`, `[destination.clickhouse]`

**Important**: When changing `table_name` in `[sources.aws_cur]`, update parquet path in `viz_rill/models/aws_costs.sql`.

### `.dlt/secrets.toml` - Credentials (Not Committed)
- AWS: `[sources.filesystem.credentials]` - access key, secret
- GCP: `[source.bigquery.credentials]` - service account JSON fields
- Stripe: `[sources.stripe_analytics]` - API secret key
- ClickHouse: `[destination.clickhouse.credentials]` - host, port, password

### `viz_rill/.env` - Rill Configuration
```bash
RILL_CONNECTOR=""  # or "clickhouse"
CONNECTOR_CLICKHOUSE_DSN="clickhouse://user:pass@host:8443/default?secure=true"
```

### `viz_rill/rill.yaml` - Rill Project Settings
```yaml
olap_connector: duckdb  # or clickhouse
```

## Key Source Files

### Data Pipelines
- `pipelines/aws_pipeline.py` - AWS CUR loader with merge deduplication
- `pipelines/google_bq_incremental_pipeline.py` - GCP BigQuery incremental loader
- `pipelines/stripe_pipeline.py` - Stripe revenue pipeline
- `pipelines/helpers/stripe_analytics/` - Stripe helper modules

### Rill SQL Models
- `viz_rill/models/aws_costs.sql` - AWS cost transformations with date extraction
- `viz_rill/models/gcp_costs.sql` - GCP billing with label flattening
- `viz_rill/models/stripe_revenue.sql` - Stripe revenue model
- `viz_rill/models/unified_cost_model.sql` - Multi-cloud union with currency conversion

### Dashboard Generation (CUR Wizard)
- `viz_rill/cur-wizard/scripts/normalize.py` - Flatten AWS MAP columns
- `viz_rill/cur-wizard/scripts/normalize_gcp.py` - Flatten GCP nested structures
- `viz_rill/cur-wizard/scripts/generate_rill_yaml.py` - Generate AWS dashboards
- `viz_rill/cur-wizard/scripts/generate_gcp_rill_yaml.py` - Generate GCP dashboards

### ClickHouse Utilities
- `scripts/init_clickhouse.py` - Initialize ClickHouse database
- `scripts/clear_clickhouse.py` - Drop all ClickHouse tables
- `scripts/anonymize_clickhouse.py` - Anonymize data for public demos

## Important Implementation Details

### AWS CUR 2.0 Format
Modern AWS CUR exports are already flat. The `normalize.py` script exists for backward compatibility with older formats that had nested MAP columns (resource tags), but acts as pass-through for CUR 2.0.

### GCP Billing Structure
GCP exports use nested field names (`service__description`, `location__country`) that must be accessed with double underscores in SQL. The `normalize_gcp.py` script flattens these for dashboard generation.

### Deduplication Strategy
- AWS: Uses `merge` write disposition with composite primary key for hard deduplication
- GCP/Stripe: Uses `append` write disposition (cost data is append-only)

### Dynamic Dashboard Generation Limitations
The CUR Wizard dashboard generator requires Parquet files to analyze schema. It works in local mode but not ClickHouse mode. Static dashboards work in both modes via SQL models.

### Switching Between Modes
Both `viz_rill/rill.yaml` (olap_connector) and `viz_rill/.env` (RILL_CONNECTOR) must match. Use `make set-connector-*` commands to change both consistently.

## Testing and Verification

### Duplicate Detection
```bash
make test  # Runs tests/test_duplicates_parquet.sql
```
Checks for duplicate records in AWS/GCP/Stripe datasets.

### Data Verification Queries
```bash
# Check AWS data loaded
duckdb -c "SELECT COUNT(*) FROM read_parquet('viz_rill/data/aws_costs/**/*.parquet')"

# Check date ranges
duckdb -c "SELECT MIN(date), MAX(date) FROM read_parquet('viz_rill/data/aws_costs/**/*.parquet')"
```

## Troubleshooting

### "No files found" - AWS
- Verify S3 bucket path in `.dlt/config.toml`
- Check AWS credentials: `aws s3 ls s3://your-bucket/`
- Wait 24 hours after enabling CUR (first export takes time)

### "Table not found" - GCP
- Verify table names in `.dlt/config.toml` match BigQuery
- Check service account has BigQuery Data Viewer + Job User roles
- Confirm billing export is enabled in GCP Console

### Rill shows no data
- Run `make run-etl` first to load data
- Check parquet files exist: `ls viz_rill/data/*/`
- Clear Rill cache: `make clear-rill`

### ClickHouse mode not working
- Verify credentials in `.dlt/secrets.toml`
- Check both `viz_rill/rill.yaml` and `viz_rill/.env` are set to clickhouse
- Run `make init-clickhouse` if tables don't exist

### Initial start date not respected
- Clear dlt state: `make dlt-clear`
- Re-run pipeline to reload from configured date

## Documentation References

- [CLICKHOUSE.md](CLICKHOUSE.md) - Complete ClickHouse Cloud setup and deployment guide
- [ANONYMIZATION.md](ANONYMIZATION.md) - Data anonymization for public dashboards
- [viz_rill/README.md](viz_rill/README.md) - Dashboard structure and CUR Wizard integration
- [ATTRIBUTION.md](ATTRIBUTION.md) - Third-party components (aws-cur-wizard)
- [README.md](README.md) - Main project documentation with setup instructions
