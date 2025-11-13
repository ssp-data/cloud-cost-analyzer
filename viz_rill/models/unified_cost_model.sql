-- Unified Cloud Cost Model
-- Combines AWS costs, Stripe revenue (and prepared for GCP)
-- @materialize: true

-- AWS Costs
WITH aws_cost_data AS (
  SELECT
    date,
    'AWS' AS cloud_provider,
    COALESCE(line_item_product_code, 'Unknown') AS service_name,
    COALESCE(product_region_code, 'global') AS region,
    COALESCE(line_item_line_item_description, line_item_usage_type) AS description,
    line_item_usage_account_id AS account_id,
    line_item_unblended_cost AS amount,
    'cost' AS transaction_type,
    line_item_currency_code AS currency
  FROM aws_costs
),

-- Stripe Revenue
stripe_revenue_data AS (
  SELECT
    date,
    'Stripe' AS cloud_provider,
    COALESCE(reporting_category, 'revenue') AS service_name,
    'global' AS region,
    COALESCE(description, type) AS description,
    NULL AS account_id,
    -- Convert cents to dollars, positive amounts are revenue, negative are costs/fees
    CASE
      WHEN reporting_category = 'charge' THEN net / 100.0
      WHEN reporting_category = 'fee' THEN amount / 100.0  -- fees are negative
      ELSE net / 100.0
    END AS amount,
    CASE
      WHEN reporting_category = 'charge' THEN 'revenue'
      WHEN reporting_category = 'fee' THEN 'cost'
      ELSE type
    END AS transaction_type,
    UPPER(currency) AS currency
  FROM stripe_revenue
)

-- Union all sources
SELECT
  date,
  cloud_provider,
  service_name,
  region,
  description,
  account_id,
  amount,
  transaction_type,
  currency,
  -- Categorize into cost and revenue for easy analysis
  CASE
    WHEN transaction_type IN ('revenue', 'charge') THEN amount
    ELSE 0
  END AS revenue_amount,
  CASE
    WHEN transaction_type IN ('cost', 'fee') THEN ABS(amount)
    WHEN transaction_type NOT IN ('revenue', 'charge') AND amount > 0 THEN amount
    ELSE 0
  END AS cost_amount
FROM (
  SELECT * FROM aws_cost_data
  UNION ALL
  SELECT * FROM stripe_revenue_data
)
WHERE date IS NOT NULL
ORDER BY date DESC
