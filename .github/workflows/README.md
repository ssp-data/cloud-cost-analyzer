# GitHub Actions Workflows

## ETL Pipeline Workflow

**File**: `etl-pipeline.yml`

### Purpose
Automated daily ETL pipeline that loads AWS, GCP, and Stripe cost data into ClickHouse Cloud.

### Schedule
- **Automatic**: Runs daily at 2:00 AM UTC
- **Manual**: Can be triggered from GitHub Actions tab

### Required GitHub Secrets

Configure these in your repository: Settings → Secrets and variables → Actions

#### ClickHouse Credentials
- `CLICKHOUSE_HOST` - ClickHouse Cloud host (e.g., `xxxxx.europe-west4.gcp.clickhouse.cloud`)
- `CLICKHOUSE_USERNAME` - Username (usually `default`)
- `CLICKHOUSE_PASSWORD` - Password

#### AWS Credentials
- `AWS_ACCESS_KEY_ID` - AWS access key for S3 CUR access
- `AWS_SECRET_ACCESS_KEY` - AWS secret key

#### GCP Credentials
- `GCP_PROJECT_ID` - GCP project ID
- `GCP_PRIVATE_KEY` - Service account private key (full key with `-----BEGIN PRIVATE KEY-----`)
- `GCP_CLIENT_EMAIL` - Service account email

#### Stripe Credentials
- `STRIPE_SECRET_KEY` - Stripe API secret key (starts with `sk_live_` or `sk_test_`)

### Workflow Steps

1. **Checkout code** - Clones repository
2. **Set up Python** - Installs Python 3.11
3. **Install dependencies** - Uses `uv` to install packages
4. **Create dlt secrets** - Generates `.dlt/secrets.toml` from GitHub Secrets
5. **Run AWS pipeline** - Loads AWS CUR data to ClickHouse
6. **Run GCP pipeline** - Loads GCP billing data to ClickHouse
7. **Run Stripe pipeline** - Loads Stripe revenue data to ClickHouse
8. **Normalize data** (optional) - Flattens AWS tags and GCP labels
9. **Ingest normalized** (optional) - Loads normalized data to ClickHouse
10. **Upload logs** (on failure) - Saves logs as artifacts for debugging

### Manual Trigger Options

When manually triggering the workflow:

- **include_normalized** (boolean, default: false)
  - `true` - Also run normalization and ingest normalized data
  - `false` - Only ingest raw data (faster, recommended for most cases)

### Monitoring

**View workflow runs**:
1. Go to "Actions" tab in GitHub
2. Select "Cloud Cost ETL Pipeline"
3. View recent runs and logs

**Check ClickHouse data**:
```bash
clickhouse-client --host xxxxx.clickhouse.cloud --secure --password 'your-password' \
  --query "SELECT count(*) FROM dlt.aws_costs__cur_export_test_00001"
```

### Troubleshooting

**Pipeline fails with authentication error**:
- Verify all GitHub Secrets are set correctly
- Check ClickHouse host includes full domain
- Ensure no trailing spaces in secret values

**Pipeline fails on specific cloud provider**:
- Check individual step logs in GitHub Actions
- Verify cloud provider credentials
- Test locally first: `DLT_DESTINATION=clickhouse make run-aws-clickhouse`

**Workflow doesn't trigger automatically**:
- Verify workflow file is in `main` branch
- Check cron syntax: `0 2 * * *` = 2 AM UTC daily
- GitHub Actions must be enabled for repository

**Logs needed for debugging**:
- Failed runs automatically upload logs as artifacts
- Download from workflow run page → "Artifacts" section
- Logs retained for 7 days

### Performance

**Typical run time**:
- Raw data only: ~5-10 minutes
- With normalization: ~10-15 minutes
- Depends on data volume and API response times

**Optimization tips**:
- Use `initial_start_date` in config to limit data
- Run normalization separately if needed
- Consider splitting large providers into separate workflows

### Cost

**GitHub Actions**:
- Public repos: 2,000 free minutes/month
- Private repos: 500 free minutes/month
- Daily run: ~10 minutes × 30 days = 300 minutes/month
- Well within free tier

**ClickHouse Cloud**:
- Charges per compute + storage usage
- Idle services auto-pause
- Typical cost: $20-100/month depending on data volume

### Local Testing

Test the workflow logic locally before enabling:

```bash
# Test raw data ingestion
DLT_DESTINATION=clickhouse make run-etl-clickhouse

# Test with normalization
make aws-normalize gcp-normalize
DLT_DESTINATION=clickhouse make ingest-normalized-clickhouse
```

### Customization

**Change schedule**:
Edit cron expression in `etl-pipeline.yml`:
```yaml
schedule:
  - cron: '0 2 * * *'  # Change to your preferred time
```

**Add notifications**:
Add notification step at end of workflow:
```yaml
- name: Notify on completion
  uses: some-notification-action
  with:
    status: ${{ job.status }}
```

**Split by provider**:
Create separate workflows for each cloud provider if needed:
- `aws-pipeline.yml`
- `gcp-pipeline.yml`
- `stripe-pipeline.yml`

### Security Notes

- Secrets are encrypted at rest
- Secrets are not visible in logs
- Use least-privilege IAM roles for cloud providers
- Rotate credentials periodically
- Use dedicated service accounts (not personal credentials)

### See Also

- **Setup guide**: `../CLICKHOUSE_SETUP.md`
- **Project docs**: `../CLAUDE.md`
- **Deployment summary**: `../DEPLOYMENT_SUMMARY.md`
