-- ============================================================
-- Duplicate Check Queries for Cloud Cost Analytics
-- ============================================================
-- Run these queries to verify no duplicates exist in the data
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
FROM aws_costs.cur_export_test_00001;

-- ============================================================

-- GCP Costs: Check for duplicates in first billing export table
-- GCP billing records should be unique by their export_time + invoice details
SELECT
  'GCP Costs' as source,
  'gcp_billing_export_resource_v1_014CCF_84D5DF_A43BC0' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT export_time) as distinct_by_export_time,
  COUNT(*) - COUNT(DISTINCT export_time) as potential_duplicates,
  CASE
    WHEN COUNT(*) = COUNT(DISTINCT export_time)
    THEN '✓ PASS (unique by export_time)'
    ELSE '⚠ Multiple records per export_time (may be expected)'
  END as status
FROM gcp_costs.gcp_billing_export_resource_v1_014CCF_84D5DF_A43BC0
WHERE 1=1; -- Add WHERE clause to handle empty table gracefully

-- ============================================================

-- GCP Costs: Check for duplicates in second billing export table
SELECT
  'GCP Costs' as source,
  'gcp_billing_export_v1_014CCF_84D5DF_A43BC0' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT export_time) as distinct_by_export_time,
  COUNT(*) - COUNT(DISTINCT export_time) as potential_duplicates,
  CASE
    WHEN COUNT(*) = COUNT(DISTINCT export_time)
    THEN '✓ PASS (unique by export_time)'
    ELSE '⚠ Multiple records per export_time (may be expected)'
  END as status
FROM gcp_costs.gcp_billing_export_v1_014CCF_84D5DF_A43BC0
WHERE 1=1;

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
FROM stripe_costs.balance_transaction;

-- ============================================================

-- Check for duplicate loads across all pipelines
-- Shows how many times each pipeline has loaded data
SELECT
  schema_name,
  COUNT(DISTINCT load_id) as number_of_loads,
  MIN(inserted_at) as first_load,
  MAX(inserted_at) as last_load
FROM (
  SELECT schema_name, load_id, inserted_at FROM aws_costs._dlt_loads
  UNION ALL
  SELECT schema_name, load_id, inserted_at FROM gcp_costs._dlt_loads
  UNION ALL
  SELECT schema_name, load_id, inserted_at FROM stripe_costs._dlt_loads
)
GROUP BY schema_name
ORDER BY schema_name;

-- ============================================================

-- Find actual duplicate records in AWS (if any)
-- Run this to see which specific records are duplicated
SELECT
  identity_line_item_id,
  identity_time_interval,
  COUNT(*) as occurrence_count,
  STRING_AGG(_dlt_load_id, ', ') as load_ids
FROM aws_costs.cur_export_test_00001
GROUP BY identity_line_item_id, identity_time_interval
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 10;

-- ============================================================
