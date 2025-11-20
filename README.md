# Cloud Cost Analyzer Project

Multi-cloud cost analytics platform combining AWS Cost and Usage Reports (CUR), GCP billing data, and Stripe revenue metrics. Built with dlt for data ingestion, DuckDB for storage, and Rill for visualization.

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
    N1[normalize.py<br/>🔧 Flatten MAP columns<br/>(CUR 2.0 is flat already)]
    N2[normalize_gcp.py<br/>🔧 Flatten nested data]

    P1 --> N1
    P2 --> N2
    P3 --> R1
end

subgraph "3: RAW STORAGE (Parquet)"
    R1[data/aws_costs/<br/>cur_export_test_00001/<br/>*.parquet]
    R2[data/gcp_costs/<br/>normalized.parquet]
    R3[data/stripe_costs/<br/>balance_transaction.parquet]

    N1 -.-> R1
    N2 --> R2
    P1 --> R1
end

subgraph "4: MODEL (SQL - Star Schema)"
    M1[aws_costs.sql<br/>🔷 Dimensions + Facts]
    M2[gcp_costs.sql<br/>🔷 Dimensions + Facts]
    M3[stripe_revenue.sql<br/>🔷 Dimensions + Facts]
    M4[unified_cost_model.sql<br/>🌟 UNION ALL + Currency Conversion]

    R1 --> M1
    R2 --> M2
    R3 --> M3

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
style M4 fill:#E74C3C,stroke:#C0392B,color:#fff
style MV3 fill:#27AE60,stroke:#1E8449,color:#fff
style D3 fill:#F39C12,stroke:#D68910,color:#fff

```

### Key Notes on Data Flow:

**AWS CUR 2.0 Format**: Modern AWS Cost and Usage Reports export in Parquet format with already-flattened columns. The `normalize.py` script exists for backward compatibility with older CUR formats that contained nested MAP columns (like resource tags), but for CUR 2.0, it acts as a pass-through operation—no transformation occurs.

**GCP Billing Export**: Google Cloud exports use nested structures (e.g., `service__description`, `location__country`) that require flattening via `normalize_gcp.py` to make them accessible for analytics.

**Stripe**: Revenue data comes pre-normalized from the Stripe API and requires no additional processing.

## Features

- **Multi-Cloud Cost Tracking** - AWS, GCP, and future cloud providers
- **Revenue Integration** - Stripe payment data for margin analysis
- **Incremental Loading** - Efficient append-only data pipeline with dlt
- **Advanced Analytics** - RI/SP utilization, unit economics, effective cost tracking (adapted from [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard))
- **Dynamic Dashboards** - Powered by Rill visualizations

## How it works

Setup secrets and configs, and then run:
```
git clone git@github.com:ssp-data/cloud-cost-analyzer.git
cd cloud-cost-analyzer
make run-all
```

### How to Use: Seperate commands to run
```sh
  # View static dashboards (always available)
  make serve

  # Generate dynamic dashboards (optional)
  make aws-dashboards

  # Complete workflow
  make run-all
```


## Setup

### 1. Install Dependencies

```bash
git clone git@github.com:ssp-data/cloud-cost-analyzer.git
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
If you change the AWS `table_name` from the default `cur_export_test_00001`, you'll also need to update two Rill files:
- `viz_rill/models/aws_costs.sql` - Update the parquet path
- `viz_rill/sources/aws_cost_normalized.yaml` - Update the parquet path
- `viz_rill/.env` - Update `INPUT_DATA_DIR`

Both files have comments showing exactly where to update the table name.

### 4. Run the Pipeline

```bash
make run-etl  # Loads AWS + GCP + Stripe data
make serve    # Opens Rill dashboards
```


## How the Data Pipeline Works

### Incremental Loading

Uses `write_disposition="append"` - cost data is append-only (no updates/merges needed).

### Data Flow

```
Cloud Providers          dlt Pipelines              Storage                 Visualization
AWS S3 (CUR)      →→     aws_pipeline.py      →→    Parquet files    →→    Rill Dashboards
GCP BigQuery      →→     google_bq_*.py       →→    viz_rill/data/   →→    localhost:9009
Stripe API        →→     stripe_pipeline.py   →→                     →→
```

### Output

Data is stored in both formats:
- **DuckDB**: `cloud_cost_analytics.duckdb` (legacy, optional)
- **Parquet**: `viz_rill/data/` (used by Rill dashboards)

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

## Complete Workflow

```bash
# Full workflow: ETL + dashboards
make run-all

# Or step-by-step:
make run-etl         # 1. Load AWS/GCP/Stripe data
make aws-dashboards  # 2. (Optional) Generate dynamic dashboards
make serve           # 3. View in browser
```

## Documentation

- `viz_rill/README.md` - Dashboard structure and how the visualization layer works
- `ATTRIBUTION.md` - Third-party components (aws-cur-wizard) used in this project


