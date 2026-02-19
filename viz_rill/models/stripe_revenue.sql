-- Stripe Revenue Model
-- Switches between DuckDB (parquet), MotherDuck, and ClickHouse based on RILL_CONNECTOR env var
-- Selects ALL columns to maintain compatibility with existing dashboards

{{ if eq .env.RILL_CONNECTOR "clickhouse" }}
-- ClickHouse: Query table directly
SELECT
  toDate(FROM_UNIXTIME(created)) AS date,
  *
FROM stripe_costs___balance_transaction
WHERE amount IS NOT NULL

{{ else if eq .env.RILL_CONNECTOR "motherduck" }}
-- MotherDuck: Query table in cloud DuckDB (same SQL syntax as local DuckDB)
SELECT
  CAST(to_timestamp(created) AS DATE) AS date,
  *
FROM stripe_costs.balance_transaction
WHERE amount IS NOT NULL

{{ else }}
-- DuckDB: Read from parquet files (default for local development)
SELECT
  CAST(to_timestamp(created) AS DATE) AS date,
  *
FROM read_parquet('data/stripe_costs/balance_transaction/*.parquet')
WHERE amount IS NOT NULL

{{ end }}
