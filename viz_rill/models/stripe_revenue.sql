-- Stripe Revenue Model
-- Reads from dlt-generated parquet files in data/stripe_costs/
SELECT
  CAST(to_timestamp(created) AS DATE) AS date,
  description,
  amount,
  net,
  reporting_category,
  type,
  currency
FROM read_parquet('data/stripe_costs/balance_transaction/*.parquet')
WHERE amount IS NOT NULL
