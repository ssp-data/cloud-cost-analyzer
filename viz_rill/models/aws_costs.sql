-- AWS Costs Model
-- Switches between DuckDB (parquet) and ClickHouse based on RILL_CONNECTOR env var
-- Selects ALL columns + derived columns to maintain compatibility with existing dashboards

{{ if .env.RILL_CONNECTOR }}
-- ClickHouse: Query table directly
SELECT
  toDate(splitByChar('T', identity_time_interval)[1]) AS date,
  COALESCE(product_servicecode, line_item_product_code, 'Unknown') AS product_product_name,
  product_servicecode AS product_servicename,
  *
FROM aws_costs___cur_export_test_00001
WHERE identity_time_interval IS NOT NULL

{{ else }}
-- DuckDB: Read from parquet files (default for local development)
SELECT
  
  CAST(SPLIT_PART(identity_time_interval, 'T', 1) AS DATE) AS date,
  COALESCE(product_servicecode, line_item_product_code, 'Unknown') AS product_product_name,
  product_servicecode AS product_servicename,
  *
FROM read_parquet('data/aws_costs/cur_export_test_00001/*.parquet')
WHERE identity_time_interval IS NOT NULL

{{ end }}
