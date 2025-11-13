# Cloud Cost Analyzer Project

Multi-cloud cost analytics platform combining AWS Cost and Usage Reports (CUR), GCP billing data, and Stripe revenue metrics. Built with dlt for data ingestion, DuckDB for storage, and Rill for visualization.

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
make
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

Edit the pipeline files to point to your data sources:

**`pipelines/aws_pipeline.py`**: Update S3 bucket path
```python
bucket_url = "s3://your-bucket/cur/CUR-export-test/data"
```

**`pipelines/google_bq_incremental_pipeline.py`**: Update BigQuery table
```python
table_name = "your-project.billing_export.gcp_billing_export_v1_XXXXX"
```

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

### AWS: "No files found"
- Check S3 bucket path in `pipelines/aws_pipeline.py`
- Verify AWS credentials: `aws s3 ls s3://your-bucket/`
- Wait 24 hours after enabling CUR export (first files take time)

### GCP: "Table not found"
- Verify BigQuery table name in `pipelines/google_bq_incremental_pipeline.py`
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


