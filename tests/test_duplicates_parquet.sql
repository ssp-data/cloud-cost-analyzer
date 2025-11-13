-- ============================================================
-- Duplicate Check Queries for Cloud Cost Analytics (Parquet Files)
-- ============================================================
-- Run these queries to verify no duplicates exist in the parquet data
-- Expected: duplicate_count should be 0 for all queries
-- ============================================================

-- AWS Costs: Check for duplicates using composite primary key
-- Expected: duplicate_count = 0
SELECT
  'AWS Costs' as source,
  'cur_export_test_00001' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT (identity_line_item_id, identity_time_interval)) as distinct_records,
  COUNT(*) - COUNT(DISTINCT (identity_line_item_id, identity_time_interval)) as duplicate_count,
  CASE
    WHEN COUNT(*) - COUNT(DISTINCT (identity_line_item_id, identity_time_interval)) = 0
    THEN '✓ PASS'
    ELSE '✗ FAIL - Duplicates found!'
  END as status
FROM read_parquet('viz_rill/data/aws_costs/cur_export_test_00001/*.parquet');

-- ============================================================

-- GCP Costs: Check for duplicates in bigquery_billing_table
-- Expected: duplicate_count = 0 (_dlt_id is unique per record)
SELECT
  'GCP Costs' as source,
  'bigquery_billing_table' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT _dlt_id) as distinct_ids,
  COUNT(*) - COUNT(DISTINCT _dlt_id) as duplicate_count,
  CASE
    WHEN COUNT(*) - COUNT(DISTINCT _dlt_id) = 0
    THEN '✓ PASS'
    ELSE '✗ FAIL - Duplicates found!'
  END as status
FROM read_parquet('viz_rill/data/gcp_costs/bigquery_billing_table/*.parquet');

-- ============================================================

-- GCP Costs: Check for duplicates in labels table
-- Expected: duplicate_count = 0 (_dlt_id is unique per label record)
SELECT
  'GCP Costs' as source,
  'bigquery_billing_table__labels' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT _dlt_id) as distinct_ids,
  COUNT(*) - COUNT(DISTINCT _dlt_id) as duplicate_count,
  CASE
    WHEN COUNT(*) - COUNT(DISTINCT _dlt_id) = 0
    THEN '✓ PASS'
    ELSE '✗ FAIL - Duplicates found!'
  END as status
FROM read_parquet('viz_rill/data/gcp_costs/bigquery_billing_table__labels/*.parquet');

-- ============================================================

-- GCP Costs: Check for duplicates in project ancestors table
-- Expected: duplicate_count = 0 (_dlt_id is unique per ancestor record)
SELECT
  'GCP Costs' as source,
  'bigquery_billing_table__project__ancestors' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT _dlt_id) as distinct_ids,
  COUNT(*) - COUNT(DISTINCT _dlt_id) as duplicate_count,
  CASE
    WHEN COUNT(*) - COUNT(DISTINCT _dlt_id) = 0
    THEN '✓ PASS'
    ELSE '✗ FAIL - Duplicates found!'
  END as status
FROM read_parquet('viz_rill/data/gcp_costs/bigquery_billing_table__project__ancestors/*.parquet');

-- ============================================================

-- Stripe Costs: Check for duplicates in balance_transaction table
-- Expected: duplicate_count = 0 (transactions have unique IDs)
SELECT
  'Stripe Costs' as source,
  'balance_transaction' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT id) as distinct_ids,
  COUNT(*) - COUNT(DISTINCT id) as duplicate_count,
  CASE
    WHEN COUNT(*) - COUNT(DISTINCT id) = 0
    THEN '✓ PASS'
    ELSE '✗ FAIL - Duplicates found!'
  END as status
FROM read_parquet('viz_rill/data/stripe_costs/balance_transaction/*.parquet');

-- ============================================================

-- Check for duplicate loads across all pipelines (from dlt metadata - JSONL files)
-- Shows how many times each pipeline has loaded data
-- Note: dlt stores metadata in JSONL format, not parquet
SELECT
  'Load Metadata' as source,
  'dlt_loads' as table_name,
  (SELECT COUNT(*) FROM read_json_auto('viz_rill/data/aws_costs/_dlt_loads/*.jsonl')) +
  (SELECT COUNT(*) FROM read_json_auto('viz_rill/data/gcp_costs/_dlt_loads/*.jsonl')) +
  (SELECT COUNT(*) FROM read_json_auto('viz_rill/data/stripe_costs/_dlt_loads/*.jsonl')) as total_loads,
  'ℹ Info - Number of pipeline runs' as status;

-- ============================================================

-- Find actual duplicate records in AWS (if any)
-- Run this to see which specific records are duplicated
SELECT
  identity_line_item_id,
  identity_time_interval,
  COUNT(*) as occurrence_count,
  STRING_AGG(_dlt_load_id, ', ') as load_ids
FROM read_parquet('viz_rill/data/aws_costs/cur_export_test_00001/*.parquet')
GROUP BY identity_line_item_id, identity_time_interval
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 10;

-- ============================================================

-- File size and row count summary across all parquet files
-- Useful to understand data distribution
SELECT
  'Summary' as check_type,
  'File Statistics' as description,
  (SELECT COUNT(*) FROM read_parquet('viz_rill/data/aws_costs/cur_export_test_00001/*.parquet')) as aws_rows,
  (SELECT COUNT(*) FROM read_parquet('viz_rill/data/gcp_costs/bigquery_billing_table/*.parquet')) as gcp_billing_rows,
  (SELECT COUNT(*) FROM read_parquet('viz_rill/data/gcp_costs/bigquery_billing_table__labels/*.parquet')) as gcp_labels_rows,
  (SELECT COUNT(*) FROM read_parquet('viz_rill/data/gcp_costs/bigquery_billing_table__project__ancestors/*.parquet')) as gcp_ancestors_rows,
  (SELECT COUNT(*) FROM read_parquet('viz_rill/data/stripe_costs/balance_transaction/*.parquet')) as stripe_rows,
  '✓ Data available' as status;

-- ============================================================
