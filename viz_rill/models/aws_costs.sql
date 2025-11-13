-- AWS Costs Model
-- Reads from dlt-generated parquet files in data/aws_costs/
SELECT
  CAST(identity_time_interval AS DATE) AS date,
  line_item_product_code,
  product_region_code,
  line_item_usage_type,
  line_item_line_item_description,
  line_item_usage_account_id,
  line_item_unblended_cost,
  line_item_currency_code
FROM read_parquet('data/aws_costs/cur_export_test_00001/*.parquet')
WHERE line_item_unblended_cost IS NOT NULL
