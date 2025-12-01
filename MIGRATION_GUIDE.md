# Migration Guide: Local → ClickHouse Cloud

This guide walks you through migrating from local development (parquet files + Rill local) to production deployment (ClickHouse Cloud + GitHub Actions).

## Prerequisites

- [ ] Working local setup with `make run-etl` and `make serve`
- [ ] ClickHouse Cloud account ([sign up](https://clickhouse.cloud))
- [ ] GitHub repository with this codebase

## Phase 1: Set Up ClickHouse Cloud (15 minutes)

### Step 1.1: Create ClickHouse Service

1. Log in to ClickHouse Cloud console
2. Click "Create new service"
3. Choose configuration:
   - **Provider**: GCP, AWS, or Azure (choose same as your data sources for lower latency)
   - **Region**: `europe-west4`, `us-east-1`, etc. (choose closest to you)
   - **Tier**: Development (for testing) or Production
4. Click "Create service"
5. Wait 2-3 minutes for service to be ready

### Step 1.2: Save Connection Details

Once service is ready, note these values:

```
Host: xxxxx.europe-west4.gcp.clickhouse.cloud
Port: 8443 (HTTPS)
Native Port: 9440 (not needed for dlt)
Username: default
Password: [generated password - copy this!]
```

**IMPORTANT**: Save the password securely. You won't be able to see it again.

### Step 1.3: Configure Local Credentials

Edit `.dlt/secrets.toml` and add:

```toml
[destination.clickhouse.credentials]
host = "xxxxx.europe-west4.gcp.clickhouse.cloud"  # Your host from above
port = 8443
username = "default"
password = "your-password-from-above"
secure = 1
```

## Phase 2: Initialize & Test Locally (10 minutes)

### Step 2.1: Install ClickHouse Client (Optional)

For easier testing:

```bash
# macOS
brew install clickhouse

# Linux
curl https://clickhouse.com/ | sh

# Or skip if you'll use SQL clients
```

### Step 2.2: Initialize Database

Run the initialization script:

```bash
make init-clickhouse
```

Expected output:
```
Connecting to ClickHouse at xxxxx.clickhouse.cloud:8443...
✅ Connected successfully
📦 Creating database 'dlt'...
✅ Database 'dlt' created
...
✅ ClickHouse initialization complete!
```

If you see errors, check:
- Credentials in `.dlt/secrets.toml` are correct
- Host includes full domain (not just hostname)
- No extra spaces in credentials
- ClickHouse service is running (check cloud console)

### Step 2.3: Test Single Pipeline

Start small - test AWS pipeline first:

```bash
make run-aws-clickhouse
```

Expected output:
```
Destination: clickhouse
Load Info:
...
```

### Step 2.4: Verify Data in ClickHouse

Check that data arrived:

```bash
# Using clickhouse-client
clickhouse-client --host xxxxx.clickhouse.cloud \
  --secure \
  --password 'your-password' \
  --query "SELECT count(*) FROM dlt.aws_costs__cur_export_test_00001"

# Expected output: some number > 0
```

Or use ClickHouse Cloud SQL console in the web UI.

### Step 2.5: Test All Pipelines

If AWS worked, run all pipelines:

```bash
make run-etl-clickhouse
```

This runs:
1. AWS pipeline
2. GCP pipeline
3. Stripe pipeline

Check each table:
```sql
SHOW TABLES FROM dlt;

SELECT count(*) FROM dlt.aws_costs__cur_export_test_00001;
SELECT count(*) FROM dlt.gcp_costs__bigquery_billing_table;
SELECT count(*) FROM dlt.stripe_costs__balance_transaction;
```

## Phase 3: Deploy to GitHub Actions (15 minutes)

### Step 3.1: Configure GitHub Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each of these secrets:

**ClickHouse** (3 secrets):
```
Name: CLICKHOUSE_HOST
Value: xxxxx.europe-west4.gcp.clickhouse.cloud

Name: CLICKHOUSE_USERNAME
Value: default

Name: CLICKHOUSE_PASSWORD
Value: your-clickhouse-password
```

**AWS** (2 secrets):
```
Name: AWS_ACCESS_KEY_ID
Value: your-aws-access-key

Name: AWS_SECRET_ACCESS_KEY
Value: your-aws-secret-key
```

**GCP** (3 secrets):
```
Name: GCP_PROJECT_ID
Value: your-gcp-project-id

Name: GCP_PRIVATE_KEY
Value: -----BEGIN PRIVATE KEY-----
...full key here...
-----END PRIVATE KEY-----

Name: GCP_CLIENT_EMAIL
Value: service-account@project.iam.gserviceaccount.com
```

**Stripe** (1 secret):
```
Name: STRIPE_SECRET_KEY
Value: sk_live_...
```

**Total: 9 secrets**

### Step 3.2: Commit and Push Workflow

The workflow file already exists at `.github/workflows/etl-pipeline.yml`.

Commit and push if you haven't already:

```bash
git add .github/workflows/etl-pipeline.yml
git commit -m "Add ClickHouse ETL workflow"
git push origin main
```

### Step 3.3: Test Manual Trigger

Before waiting for the scheduled run:

1. Go to **Actions** tab in GitHub
2. Click **Cloud Cost ETL Pipeline** in left sidebar
3. Click **Run workflow** button (top right)
4. Leave options as defaults (include_normalized: false)
5. Click green **Run workflow** button

### Step 3.4: Monitor First Run

Watch the workflow execute:

1. Click on the workflow run (appears after few seconds)
2. Click **run-etl** job
3. Expand each step to see logs
4. Wait for completion (~5-10 minutes)

Expected result: ✅ Green checkmark

### Step 3.5: Verify Automated Data

Check ClickHouse has new data:

```sql
-- Check latest data timestamp
SELECT MAX(identity_time_interval) as latest_date
FROM dlt.aws_costs__cur_export_test_00001;

-- Should be very recent (within last day)
```

## Phase 4: Normalization (Optional)

### Option A: Skip Normalization

For basic cost analytics, raw data is sufficient. ClickHouse can query MAP columns directly:

```sql
-- Query AWS tags directly
SELECT
  resource_tags['Environment'] as environment,
  SUM(line_item_unblended_cost) as cost
FROM dlt.aws_costs__cur_export_test_00001
GROUP BY environment;
```

**Recommendation**: Start here. Add normalization only if you need:
- Pre-computed tag/label columns
- Faster queries on tags
- Compatibility with tools that can't query MAP columns

### Option B: Normalize in ClickHouse (Recommended for Production)

Create materialized views to flatten tags:

```sql
-- AWS normalized view
CREATE MATERIALIZED VIEW dlt.aws_costs_normalized
ENGINE = MergeTree()
ORDER BY (identity_time_interval, identity_line_item_id)
AS SELECT
  *,
  resource_tags['Environment'] AS tag_environment,
  resource_tags['Team'] AS tag_team,
  resource_tags['Application'] AS tag_application,
  resource_tags['CostCenter'] AS tag_cost_center
FROM dlt.aws_costs__cur_export_test_00001;

-- GCP normalized view
CREATE MATERIALIZED VIEW dlt.gcp_costs_normalized
ENGINE = MergeTree()
ORDER BY (usage_start_time)
AS SELECT
  b.*,
  labels.key,
  labels.value
FROM dlt.gcp_costs__bigquery_billing_table b
LEFT JOIN dlt.gcp_costs__bigquery_billing_table__labels labels
  ON b._dlt_id = labels._dlt_parent_id;
```

**Benefits**:
- No Python scripts needed
- Updates automatically with new data
- Leverages ClickHouse performance
- No intermediate parquet files

### Option C: Normalize in GitHub Actions

If you prefer the Python normalization scripts:

1. Manual trigger workflow with `include_normalized: true`
2. Or modify workflow schedule to always include normalization

**Trade-offs**:
- Adds ~5 minutes to workflow
- Requires temporary parquet file generation
- More complex workflow
- Useful if normalization logic is complex

## Phase 5: Connect Rill Cloud (Optional)

If using Rill Cloud for visualization:

### Step 5.1: Update Rill Project

In your Rill Cloud project settings:

```yaml
# rill.yaml
connector: clickhouse
clickhouse:
  host: xxxxx.europe-west4.gcp.clickhouse.cloud
  port: 8443
  username: default
  password: ${CLICKHOUSE_PASSWORD}  # Store in Rill Cloud secrets
  database: dlt
  ssl: true
```

### Step 5.2: Update Source Definitions

Instead of reading parquet files, query ClickHouse:

```yaml
# sources/aws_costs.yaml
type: sql
sql: SELECT * FROM dlt.aws_costs__cur_export_test_00001

# sources/gcp_costs.yaml
type: sql
sql: SELECT * FROM dlt.gcp_costs__bigquery_billing_table
```

### Step 5.3: Deploy to Rill Cloud

```bash
rill deploy \                                         ✘ INT
--org demo \
--path viz_rill \
--public \
--prod-branch main \
```

Your dashboards now query ClickHouse Cloud in real-time!

## Rollback Plan

If anything goes wrong, local development still works:

```bash
# Continue using local setup
make run-etl
make serve
```

Your local environment is **completely independent** from ClickHouse deployment.

## Maintenance

### Daily Operations

**Everything is automated!** 🎉

- ETL runs daily at 2 AM UTC
- Data incrementally loaded (only new records)
- Failures send logs to GitHub artifacts

**You don't need to do anything.**

### Monthly Checks

- Review GitHub Actions usage (should be well under free tier)
- Check ClickHouse costs in cloud console
- Verify data freshness: latest records should be < 24h old
- Review failed workflow runs (if any)

### When to Intervene

**Never (probably)**, but watch for:
- Multiple failed workflow runs → Check credentials haven't expired
- ClickHouse costs spike → Review data volume or optimize queries
- Dashboards show stale data → Check workflow schedule

## Troubleshooting

### "Cannot connect to ClickHouse"

**Symptoms**: Pipeline fails with connection errors

**Solutions**:
1. Check ClickHouse service is running (cloud console)
2. Verify host is full domain: `xxxxx.region.gcp.clickhouse.cloud`
3. Ensure `secure = 1` in config
4. Test connection manually:
   ```bash
   clickhouse-client --host xxx --secure --password 'xxx' --query "SELECT 1"
   ```

### "Authentication failed"

**Symptoms**: Pipeline fails with auth errors

**Solutions**:
1. Verify username/password in secrets
2. No trailing spaces in secret values
3. Try regenerating ClickHouse password in cloud console
4. Update both local `.dlt/secrets.toml` and GitHub Secrets

### "Table already exists"

**Symptoms**: Pipeline fails with "table exists" error

**Solutions**:
1. dlt handles this automatically - likely a bug
2. Manually drop table:
   ```sql
   DROP TABLE IF EXISTS dlt.aws_costs__cur_export_test_00001;
   ```
3. Re-run pipeline

### GitHub Actions doesn't trigger

**Symptoms**: No automatic runs

**Solutions**:
1. Verify workflow file is in `main` branch
2. Check GitHub Actions is enabled for repo
3. Wait - first scheduled run happens at next 2 AM UTC
4. Manually trigger to test

### Data appears duplicated

**Symptoms**: Row counts keep growing

**Solutions**:
1. Check write disposition: AWS should use `merge`, GCP/Stripe use `append`
2. Review pipeline code for `write_disposition` parameter
3. Run duplicate tests:
   ```bash
   make test-duplicates
   ```

## Success Criteria

You've successfully migrated when:

- ✅ Local development still works: `make run-etl && make serve`
- ✅ ClickHouse contains all three data sources (AWS, GCP, Stripe)
- ✅ GitHub Actions runs automatically and succeeds
- ✅ Data freshness < 24 hours
- ✅ No manual intervention needed
- ✅ (Optional) Rill Cloud or BI tool connected to ClickHouse

## Support

- **Stuck?** Review `CLICKHOUSE_SETUP.md` for detailed instructions
- **Errors?** Check `.github/workflows/README.md` for troubleshooting
- **Architecture questions?** See `DEPLOYMENT_SUMMARY.md`
- **dlt issues?** https://dlthub.com/docs
- **ClickHouse issues?** https://clickhouse.com/docs

## What's Next?

After migration:

1. **Remove local parquet files** (optional):
   ```bash
   make clear-data
   ```
   You can regenerate anytime with `make run-etl`

2. **Set up monitoring** (optional):
   - Add Slack/email notifications to workflow
   - Set up ClickHouse alerts for data freshness
   - Monitor GitHub Actions usage

3. **Optimize costs** (optional):
   - Review ClickHouse query patterns
   - Add aggregation tables for common queries
   - Schedule more/less frequent runs based on needs

4. **Share with team**:
   - Others can query ClickHouse directly
   - Share Rill Cloud dashboards
   - No local setup needed for analysts

Congratulations! 🎉 You now have a production-grade, automated multi-cloud cost analytics platform.
