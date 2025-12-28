# Cloud Cost Analyzer Project

Multi-cloud cost analytics platform combining AWS Cost and Usage Reports (CUR), GCP billing data, and Stripe revenue metrics. Built with dlt for data ingestion, DuckDB/ClickHouse for storage, and Rill for visualization.

> **NEW: Cloud-Ready Version**
>
> This version now supports **both local and cloud deployment**:
> - **Local Mode**: Parquet files + DuckDB + local Rill (perfect for development)
> - **Cloud Mode**: ClickHouse Cloud + Rill Cloud + GitHub Actions automation (production-ready)
>
> Switch between modes with a single command. The same codebase works everywhere! Looking for the original local-only version? Check out [branch `v1`](https://github.com/ssp-data/cloud-cost-analyzer/tree/v1)

>
> **Note**: The live cloud demo is currently offline to save costs. You can recreate the full cloud setup with your own [ClickHouse Cloud](https://clickhouse.cloud) and [Rill Cloud](https://www.rilldata.com/try-free) instances following the [blog article](https://www.ssp.sh/blog/finops-dlt-clickhouse-rill/).

![](img/tech-stack.png)


## Features

- **Multi-Cloud Cost Tracking** - AWS, GCP, and future cloud providers
- **Revenue Integration** - Stripe payment data for margin analysis
- **Dual Deployment Modes** - Run locally with Parquet/DuckDB or in the cloud with ClickHouse/Rill Cloud
- **Incremental Loading** - Efficient append-only data pipeline with dlt
- **Advanced Analytics** - RI/SP utilization, unit economics, effective cost tracking (adapted from [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard))
- **GitHub Actions Automation** - [Daily data updates](.github/workflows/etl-pipeline.yml) with automated ETL pipelines
- **Data Anonymization** - Built-in anonymization for public dashboards (see [ANONYMIZATION.md](ANONYMIZATION.md))
- **Dynamic Dashboards** - Powered by Rill visualizations

## Quick Start with Demo Data

Try without any credentials:
```bash
git clone https://github.com/ssp-data/cloud-cost-analyzer.git
cd cloud-cost-analyzer
make demo
```

Opens at http://localhost:9009 with sample data.

- **Note 1**: Rill tries to be installed during that process. But best to have it install first with: `curl https://rill.sh | sh`
- **Note 2**: Run `make clear` before `make run-all` to switch to real data.

## How it works

### Two Deployment Modes

This project supports both local development and cloud production:

**Local Mode** (default):
```sh
make run-all        # ETL → Parquet files → Local Rill dashboard
make serve          # View dashboards at localhost:9009
```
Perfect for: Development, testing, small datasets

**Cloud Mode** (production-ready):
```sh
make run-all-cloud  # ETL → ClickHouse Cloud → Anonymize → Rill Cloud/Local
```
Perfect for: Production, team collaboration, large datasets, public dashboards

> **Note**: The ClickHouse cluster is currently offline to save costs. The cloud setup is fully documented and functional—you'll just need your own ClickHouse Cloud instance.

**Additional commands:**
```sh
make aws-dashboards  # Generate dynamic AWS dashboards (local mode only)
make serve-clickhouse  # View dashboards connected to ClickHouse
```

### Deployment Guides

- **[CLICKHOUSE.md](CLICKHOUSE.md)** - Complete ClickHouse Cloud setup, deployment, mode switching, and GitHub Actions automation
- **[ANONYMIZATION.md](ANONYMIZATION.md)** - Data anonymization for public dashboards
- **[CLAUDE.md](CLAUDE.md)** - Architecture details and development guide


## Setup
We need to get the Cost reports and the credentials properly setup.

First we clone the project, isntall dependencies, then we setup the cost reports for each cloud provider and at the end, we need to set `.dlt/secrets.toml` and `.dlt/config.toml` to match your data. 

Below step by step how to create a cost report and extract the keys. Also check related blog posts: [local first](http://www.ssp.sh/blog/cost-analyzer-aws-gcp/) and [cloud-ready](https://www.ssp.sh/blog/finops-dlt-clickhouse-rill/) for more details.


### 1. Install Dependencies

```bash
git clone https://github.com/ssp-data/cloud-cost-analyzer.git
cd cloud-cost-analyzer
uv sync  # Installs all packages from pyproject.toml
```


### 2. Configure Data Sources

You need to set up cost/revenue exports from each cloud provider:

#### AWS Cost and Usage Report (CUR)

**One-time setup in AWS Console**:

1. Go to [AWS Billing Console](https://us-east-1.console.aws.amazon.com/billing/home?region=us-east-1#/bills) → **Cost & Usage Reports**
2. Click **"Create report"**
3. Configure:
   - Report name: `CUR-export-test` (or your choice)
   - Time granularity: **Hourly** or **Daily**
   - Enable: **Include resource IDs**
   - Report data integration: Select **Amazon Athena** (enables Parquet format)
   - S3 bucket: Choose or create a bucket (e.g., `s3://your-bucket/cur`)
   - Enable: **Overwrite existing report**

AWS will automatically generate and upload CUR files to your S3 bucket daily.

**Set AWS credentials**:

```bash
# Option 1: Environment variables (recommended)
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Option 2: Edit .dlt/secrets.toml
[sources.filesystem.credentials]
aws_access_key_id = "your-key"
aws_secret_access_key = "your-secret"
```

The `.env` file automatically sources these for dlt.

#### Google Cloud Platform (BigQuery Export)

**One-time setup in GCP Console**:

1. Go to [GCP Billing Console](https://console.cloud.google.com/billing)
2. Navigate to: **Billing → Billing export**
3. Click **"Edit settings"** for **Detailed usage cost**
4. Choose:
   - BigQuery dataset: Create or select dataset (e.g., `billing_export`)
5. Click **"Save"**

GCP will automatically export billing data to BigQuery daily (usually completes by end of next day).

**More**: [GCP Billing Export Guide](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)

**Create Service Account & Get Credentials**:

1. Go to [IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **"+ CREATE SERVICE ACCOUNT"**
3. Grant roles:
   - **BigQuery Data Viewer**
   - **BigQuery Job User**
4. Create JSON key: **Keys → ADD KEY → Create new key → JSON**
5. Download the JSON file

**Configure credentials in `.dlt/secrets.toml`**:

```toml
[source.bigquery.credentials]
project_id = "your-project-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
token_uri = "https://oauth2.googleapis.com/token"
```

**Note**: Extract these values from your downloaded JSON key file.

#### Stripe Revenue Data

**Get API Key**:

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Navigate to: **Developers → API keys**
3. Copy your **Secret key** (starts with `sk_live_` or `sk_test_`)

**Configure in `.dlt/secrets.toml`**:

```toml
[sources.stripe_analytics]
stripe_secret_key = "sk_live_your_key_here"
```

### 3. Update Pipeline Configuration

All pipeline configuration is centralized in `.dlt/config.toml`. Edit this file to point to your data sources:

**Edit `.dlt/config.toml`**:

```toml
# Pipeline configuration
[pipeline]
pipeline_name = "cloud_cost_analytics"  # Change if needed

# AWS CUR configuration
[sources.aws_cur]
bucket_url = "s3://your-bucket-name"  # Your S3 bucket
file_glob = "cur/your-report-name/data/**/*.parquet"  # Path to your CUR files
table_name = "your_table_name"  # Name for the output table
dataset_name = "aws_costs"  # Dataset name (default: aws_costs)
initial_start_date = "2025-09-01"  # Only load data from this date onwards (filters by file modification date)

# GCP BigQuery billing export configuration
[sources.gcp_billing]
# project_id is automatically read from secrets.toml
# (uses source.bigquery.credentials.project_id)
# Uncomment below only if you want to override:
# project_id = "your-gcp-project-id"
dataset = "billing_export"  # BigQuery dataset name
dataset_name = "gcp_costs"  # Output dataset name (default: gcp_costs)
initial_start_date = "2025-09-01T00:00:00Z"  # Only load data from this date onwards (filters by export_time)
# Update these table names to match your GCP billing export tables
# Find them in BigQuery Console under your billing_export dataset
table_names = [
    "gcp_billing_export_resource_v1_XXXXXX_XXXXXX_XXXXXX",
    "gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX"
]

# Stripe configuration
[sources.stripe]
dataset_name = "stripe_costs"  # Dataset name (default: stripe_costs)
initial_start_date = "2025-09-01"  # Only load data from this date onwards (filters by created timestamp)
```

**Understanding `initial_start_date` Configuration:**

The `initial_start_date` parameter controls how far back to load historical data when running the pipeline for the first time. This is especially important when copying this project to avoid loading 10+ years of historical data:

- **AWS**: Filters files by modification date. Format: `"YYYY-MM-DD"` (e.g., `"2025-09-01"`)
- **GCP**: Filters records by `export_time` field. Format: `"YYYY-MM-DDTHH:MM:SSZ"` (e.g., `"2025-09-01T00:00:00Z"`)
- **Stripe**: Filters transactions by created timestamp. Format: `"YYYY-MM-DD"` (e.g., `"2025-09-01"`)

**Important Notes:**
- Once data is loaded, subsequent runs only load new data (incremental loading)
- To reset and reload from a different start date, run `make dlt-clear` to clear the dlt state
- If omitted, AWS/Stripe will load all available data, and GCP will default to loading from 2000-01-01
- Recommended: Set to a recent date (e.g., 3-6 months ago) to keep initial data load manageable

**How to find your GCP billing table names:**
1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. Find your billing export dataset (usually `billing_export`)
3. Look for tables starting with `gcp_billing_export_v1_` or `gcp_billing_export_resource_v1_`
4. Copy the full table names into the config above

**Note about AWS table_name and Rill dashboards:**
If you change the AWS `table_name` from the default `cur_export_test_00001`, you'll also need to update the parquet path in `viz_rill/models/aws_costs.sql` (file has comments showing where).

#### Cloud Deployment with ClickHouse & Rill Cloud

**New in this version**: Deploy to production with ClickHouse Cloud and automate with GitHub Actions!

**Quick Cloud Setup:**

1. **Create ClickHouse Cloud service** ([sign up free](https://clickhouse.cloud))

2. **Add credentials to `.dlt/secrets.toml`:**
   ```toml
   [destination.clickhouse.credentials]
   host = "xxxxx.europe-west4.gcp.clickhouse.cloud"
   port = 8443
   username = "default"
   password = "your-password"
   secure = 1
   ```

3. **Configure Rill for ClickHouse** in `viz_rill/.env`:
   ```bash
   RILL_CONNECTOR="clickhouse"
   CONNECTOR_CLICKHOUSE_DSN="clickhouse://default:password@host:8443/default?secure=true"
   ```

4. **Run cloud pipeline:**
   ```bash
   make init-clickhouse      # Initialize database (one-time)
   make run-all-cloud        # ETL + anonymize + serve
   ```

**What you get:**
- Data stored in ClickHouse Cloud (scalable, fast)
- [Automated daily updates via GitHub Actions](.github/workflows/etl-pipeline.yml) (runs at 2 AM UTC)
- Optional data anonymization for public dashboards
- Works with both Rill Cloud and local Rill

**Complete guide**: See [CLICKHOUSE.md](CLICKHOUSE.md) for detailed setup, GitHub Actions configuration, mode switching, and troubleshooting. 

### 4. Run the Pipeline

```bash
make run-etl  # Loads AWS + GCP + Stripe data
make serve    # Opens Rill dashboards
```


## How the Data Pipeline Works

This pipeline supports both **local mode** (Parquet + DuckDB) and **cloud mode** (ClickHouse Cloud). The architecture remains the same, only the storage layer changes.

## The Data Flow
```mermaid
graph TB

subgraph "1: EXTRACT (dlt)"
    A1[AWS S3<br/>CUR Parquet]
    A2[GCP BigQuery<br/>Billing Export]
    A3[Stripe API<br/>Revenue]

    P1[aws_pipeline.py<br/>📥 Incremental]
    P2[google_bq_pipeline.py<br/>📥 Incremental]
    P3[stripe_pipeline.py<br/>📥 Incremental]

    A1 --> P1
    A2 --> P2
    A3 --> P3
end

subgraph "2: NORMALIZE (Python + DuckDB)"
    N1["normalize.py<br/>🔧 Flatten MAP columns<br/>(CUR 2.0 is flat already)"]
    N2[normalize_gcp.py<br/>🔧 Flatten nested data]

    P1 --> N1
    P2 --> N2
    P3 --> R1
end

subgraph "3: STORAGE (Dual Mode)"
    R1[LOCAL: Parquet files<br/>or<br/>CLOUD: ClickHouse tables]
    R2[Switch with DLT_DESTINATION env var]

    N1 -.-> R1
    N2 --> R1
    P1 --> R1
end

subgraph "4: MODEL (SQL - Star Schema)"
    M1[aws_costs.sql<br/>🔷 Dimensions + Facts]
    M2[gcp_costs.sql<br/>🔷 Dimensions + Facts]
    M3[stripe_revenue.sql<br/>🔷 Dimensions + Facts]
    M4[unified_cost_model.sql<br/>🌟 UNION ALL + Currency Conversion]

    R1 --> M1
    R1 --> M2
    R1 --> M3

    M1 --> M4
    M2 --> M4
    M3 --> M4
end

subgraph "5: METRICS & DASHBOARDS (Rill)"
    MV1[aws_cost_metrics.yaml<br/>📊 KPIs & Measures]
    MV2[gcp_cost_metrics.yaml<br/>📊 KPIs & Measures]
    MV3[cloud_cost_metrics.yaml<br/>📊 Unified Metrics]

    D1[🎨 AWS Dashboard]
    D2[🎨 GCP Dashboard]
    D3[🎨 Cloud Cost Explorer<br/>Multi-Cloud + Revenue]

    M4 --> MV1
    M4 --> MV2
    M4 --> MV3

    MV1 --> D1
    MV2 --> D2
    MV3 --> D3
end

style P1 fill:#4A90E2,stroke:#2E5C8A,color:#fff
style P2 fill:#4A90E2,stroke:#2E5C8A,color:#fff
style P3 fill:#4A90E2,stroke:#2E5C8A,color:#fff
style N1 fill:#9B59B6,stroke:#7D3C98,color:#fff
style N2 fill:#9B59B6,stroke:#7D3C98,color:#fff
style R1 fill:#FF6B6B,stroke:#C92A2A,color:#fff
style R2 fill:#FF6B6B,stroke:#C92A2A,color:#fff
style M4 fill:#E74C3C,stroke:#C0392B,color:#fff
style MV3 fill:#27AE60,stroke:#1E8449,color:#fff
style D3 fill:#F39C12,stroke:#D68910,color:#fff

```

### Key Notes on Data Flow

**AWS CUR 2.0 Format**: Modern AWS Cost and Usage Reports export in Parquet format with already-flattened columns. The `normalize.py` script exists for backward compatibility with older CUR formats that contained nested MAP columns (like resource tags), but for CUR 2.0, it acts as a pass-through operation—no transformation occurs.

**GCP Billing Export**: Google Cloud exports use nested structures (e.g., `service__description`, `location__country`) that require flattening via `normalize_gcp.py` to make them accessible for analytics.

**Stripe**: Revenue data comes pre-normalized from the Stripe API and requires no additional processing.

### Incremental Loading

Uses `write_disposition="append"` - cost data is append-only (no updates/merges needed). AWS uses `merge` for hard deduplication.

### Data Flow by Mode

**Local Mode:**
```
Cloud Providers    dlt Pipelines          Storage              Visualization
AWS S3 (CUR)   →   aws_pipeline.py   →   Parquet files    →   Rill (DuckDB)
GCP BigQuery   →   google_bq_*.py    →   viz_rill/data/   →   localhost:9009
Stripe API     →   stripe_pipeline.py →                   →
```

**Cloud Mode:**
```
Cloud Providers    dlt Pipelines          Storage               Visualization
AWS S3 (CUR)   →   aws_pipeline.py   →   ClickHouse Cloud  →   Rill Cloud/Local
GCP BigQuery   →   google_bq_*.py    →   (via dlt)         →   (connects to CH)
Stripe API     →   stripe_pipeline.py →                    →
                        ↓
                  GitHub Actions (automated daily at 2 AM UTC)
```
See [workflow configuration](.github/workflows/etl-pipeline.yml) for details.

### Output

**Local Mode:**
- **Parquet files**: `viz_rill/data/` (primary storage, used by Rill via DuckDB)
- **DuckDB**: `cloud_cost_analytics.duckdb` (legacy, optional)

**Cloud Mode:**
- **ClickHouse tables**: Scalable cloud database
- **Automated updates**: Via [GitHub Actions](.github/workflows/etl-pipeline.yml) (daily at 2 AM UTC)

## Troubleshooting

### Configuration Issues
- All configuration is in `.dlt/config.toml` - check this file first
- Verify your table names, project IDs, and bucket paths match your cloud provider setup
- The test runner will use your config values automatically

### AWS: "No files found"
- Check S3 bucket path in `.dlt/config.toml` under `[sources.aws_cur]`
- Verify AWS credentials: `aws s3 ls s3://your-bucket/`
- Wait 24 hours after enabling CUR export (first files take time)

### GCP: "Table not found"
- Verify BigQuery table names in `.dlt/config.toml` under `[sources.gcp_billing]`
- Check service account permissions (BigQuery Data Viewer + Job User)
- Confirm billing export is enabled and dataset exists

### Stripe: "Invalid API key"
- Verify secret key in `.dlt/secrets.toml` starts with `sk_live_` or `sk_test_`
- Check key has read permissions in Stripe Dashboard

### Rill: "No data in dashboards"
- Run `make run-etl` first to load data
- Check parquet files exist: `ls viz_rill/data/*/`
- Verify data loaded: `duckdb cloud_cost_analytics.duckdb -c "SELECT COUNT(*) FROM aws_costs.cur_export_test_00001;"`

## Visualization with Rill

The `viz_rill/` directory contains Rill dashboards for multi-cloud cost analysis.

```bash
make serve  # Opens Rill at http://localhost:9009
```

**Features**:
- AWS cost analytics with RI/SP utilization tracking
- Multi-cloud overview (AWS + GCP + Stripe)
- Interactive explorers and product dimension analysis
- Optional: Dynamic dashboard generation using [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard)

See `viz_rill/README.md` for dashboard details and integration information.

## Data Normalization (Optional)

**TL;DR: Normalization is optional and only needed for dynamic dashboard generation.**

### What Normalization Does

The normalization scripts (`normalize.py`, `normalize_gcp.py`) flatten nested data structures (AWS resource_tags, GCP labels) and feed them to the dashboard generator from [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard).

### Do You Need It?

It works without also. The core dashboards work without normalization:
- Static dashboards (`viz_rill/dashboards/*.yaml`) query raw data via models
- Models use `SELECT *` to read all columns from raw parquet/ClickHouse
- Everything works for both local and cloud deployment

But it provides useful dashboards (alredy pre commited in this repo), but if you have different data, i'd suggest to run it. Normalization provides:
- Auto-generated dimension-specific canvases (e.g., per-tag breakdowns)
- Dynamic explorers based on discovered labels/tags
- CUR Wizard's intelligent chart type selection

### How to Generate Dynamic Dashboards

**Important:** This only works in **local mode** (parquet files). ClickHouse mode doesn't create parquet files, so dynamic dashboard generation is unavailable.

```bash
# Local mode only - Generate AWS canvases (optional)
make aws-dashboards  # Normalizes + generates canvases/explores/

# Local mode only - Generate GCP canvases (optional)
make gcp-dashboards  # Normalizes + generates canvases/explores/

# View all dashboards (static + generated)
make serve
```

**Generated files** (in `.gitignore` but can be committed):
- `viz_rill/canvases/*.yaml` - Dimension-specific breakdowns
- `viz_rill/explores/*.yaml` - Auto-generated explorers
- `viz_rill/data/normalized_aws.parquet` - Flattened AWS data
- `viz_rill/data/normalized_gcp.parquet` - Flattened GCP data

### Feature Comparison: Local vs Cloud Mode

| Feature | Local Mode (Parquet) | Cloud Mode (ClickHouse) |
|---------|---------------------|------------------------|
| Static dashboards | ✅ Always work | ✅ Always work |
| Dynamic dashboard generation | ✅ `make aws-dashboards` | ❌ Not available* |
| Data storage | Parquet files | ClickHouse Cloud |
| Normalization | Optional | Not needed |
| Best for | Development, dynamic canvases | Production, GitHub Actions |

*ClickHouse doesn't create parquet files, so the dashboard generator can't analyze data. Static dashboards provide full functionality.

See [CLICKHOUSE.md](CLICKHOUSE.md#advanced-normalization-optional) for more details.

## Complete Workflow

### Local Development Workflow

```bash
# Full local workflow: ETL + dashboards
make run-all

# Or step-by-step:
make run-etl         # 1. Load AWS/GCP/Stripe data → Parquet files
make aws-dashboards  # 2. (Optional) Generate dynamic dashboards
make serve           # 3. View in browser at localhost:9009
```

### Cloud Production Workflow

```bash
# Full cloud workflow: ETL + anonymize + serve
make run-all-cloud

# Or step-by-step:
make init-clickhouse      # 1. Initialize ClickHouse (one-time)
make run-etl-clickhouse   # 2. Load data → ClickHouse Cloud
make anonymize-clickhouse # 3. (Optional) Anonymize for public dashboards
make serve-clickhouse     # 4. View dashboards (local Rill → ClickHouse)
```

**Switching modes:**
```bash
make set-connector-duckdb      # Switch to local Parquet/DuckDB
make set-connector-clickhouse  # Switch to ClickHouse Cloud
```

## Documentation

### Cloud Deployment
- **[CLICKHOUSE.md](CLICKHOUSE.md)** - ClickHouse Cloud setup, GitHub Actions automation, mode switching, and troubleshooting
- **[ANONYMIZATION.md](ANONYMIZATION.md)** - Data anonymization for public dashboards
- **GitHub Actions Workflows**:
  - [Daily ETL Pipeline](.github/workflows/etl-pipeline.yml) - Automated data ingestion (runs at 2 AM UTC)
  - [Clear ClickHouse Data](.github/workflows/clear-clickhouse.yml) - Manual workflow to drop all tables

### Development & Architecture
- **[CLAUDE.md](CLAUDE.md)** - Architecture details, key design patterns, and development guide
- **[viz_rill/README.md](viz_rill/README.md)** - Dashboard structure and visualization layer
- **[ATTRIBUTION.md](ATTRIBUTION.md)** - Third-party components (aws-cur-wizard)

### Related Resources
- **Blog Post**: [Multi-Cloud Cost Analytics: From Cost-Export to Parquet to Rill](https://www.ssp.sh/blog/cost-analyzer-aws-gcp/) - Detailed write-up of this project
- **Blog Post Part 2**: [Multi-Cloud Cost Analytics with dlt, ClickHouse & Rill](https://www.ssp.sh/blog/finops-dlt-clickhouse-rill/) - Detailed write-up of this project
- **Original Local Version**: [Branch `v1`](https://github.com/ssp-data/cloud-cost-analyzer/tree/v1) - Pre-ClickHouse version


