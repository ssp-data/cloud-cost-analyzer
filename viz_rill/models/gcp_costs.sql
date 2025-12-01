-- GCP Costs Model
-- Switches between DuckDB (parquet) and ClickHouse based on RILL_CONNECTOR env var
-- Selects ALL columns + derived columns to maintain compatibility with existing dashboards

{{ if .env.RILL_CONNECTOR }}
-- ClickHouse: Query table directly
SELECT
  toDate(usage_start_time) AS date,
  service__description AS service_name,
  sku__description AS sku_description,
  location__location AS region,
  location__country AS country,
  project__id AS project_id,
  
  project__name AS project_name,
  *
FROM gcp_costs___bigquery_billing_table
WHERE cost IS NOT NULL

{{ else }}
-- DuckDB: Read from parquet files (default for local development)
SELECT
  CAST(usage_start_time AS DATE) AS date,
  service__description AS service_name,
  sku__description AS sku_description,
  location__location AS region,
  location__country AS country,
  project__id AS project_id,
  project__name AS project_name,
  *
FROM read_parquet('data/gcp_costs/bigquery_billing_table/*.parquet')
WHERE cost IS NOT NULL

{{ end }}
