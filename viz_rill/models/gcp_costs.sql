-- GCP Costs Model
-- Reads from dlt-generated parquet files in data/gcp_costs/
SELECT
  CAST(usage_start_time AS DATE) AS date,
  service__description AS service_name,
  sku__description AS sku_description,
  location__location AS region,
  location__country AS country,
  project__id AS project_id,
  project__name AS project_name,
  billing_account_id,
  cost,
  currency,
  cost_type,
  usage__amount AS usage_amount,
  usage__unit AS usage_unit,
  transaction_type
FROM read_parquet('data/gcp_costs/bigquery_billing_table/*.parquet')
WHERE cost IS NOT NULL
