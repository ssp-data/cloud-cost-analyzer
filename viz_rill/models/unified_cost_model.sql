-- Unified Cloud Cost Model
-- Combines AWS costs, GCP costs, and Stripe revenue
-- All amounts converted to USD for consistent reporting
-- @materialize: true

-- Currency conversion rates (update as needed)
-- CHF to USD: 1.13 (as of 2025-11-13)
WITH currency_rates AS (
  SELECT 1.26 AS chf_to_usd
),

-- AWS Costs (already in USD)
aws_cost_data AS (
  SELECT
    date,
    'AWS' AS cloud_provider,
    COALESCE(line_item_product_code, 'Unknown') AS service_name,
    COALESCE(product_region_code, 'global') AS region,
    COALESCE(line_item_line_item_description, line_item_usage_type) AS description,
    line_item_usage_account_id AS account_id,
    line_item_unblended_cost AS amount,
    'cost' AS transaction_type,
    line_item_currency_code AS original_currency,
    line_item_unblended_cost AS amount_usd  -- Already in USD
  FROM {{ ref "aws_costs" }}
),

-- GCP Costs (convert CHF to USD)
gcp_cost_data AS (
  SELECT
    date,
    'GCP' AS cloud_provider,
    COALESCE(service_name, 'Unknown') AS service_name,
    COALESCE(region, 'global') AS region,
    COALESCE(sku_description, service_name) AS description,
    project_id AS account_id,
    cost AS amount,
    COALESCE(transaction_type, 'cost') AS transaction_type,
    currency AS original_currency,
    -- Convert CHF to USD
    CASE
      WHEN UPPER(currency) = 'CHF' THEN cost * (SELECT chf_to_usd FROM currency_rates)
      WHEN UPPER(currency) = 'USD' THEN cost
      ELSE cost  -- Fallback: use original amount
    END AS amount_usd
  FROM {{ ref "gcp_costs" }}
),

-- Stripe Revenue (convert CHF to USD)
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
    UPPER(currency) AS original_currency,
    -- Convert CHF to USD
    CASE
      WHEN UPPER(currency) = 'CHF' THEN
        CASE
          WHEN reporting_category = 'charge' THEN (net / 100.0) * (SELECT chf_to_usd FROM currency_rates)
          WHEN reporting_category = 'fee' THEN (amount / 100.0) * (SELECT chf_to_usd FROM currency_rates)
          ELSE (net / 100.0) * (SELECT chf_to_usd FROM currency_rates)
        END
      WHEN UPPER(currency) = 'USD' THEN
        CASE
          WHEN reporting_category = 'charge' THEN net / 100.0
          WHEN reporting_category = 'fee' THEN amount / 100.0
          ELSE net / 100.0
        END
      ELSE  -- Fallback
        CASE
          WHEN reporting_category = 'charge' THEN net / 100.0
          WHEN reporting_category = 'fee' THEN amount / 100.0
          ELSE net / 100.0
        END
    END AS amount_usd
  FROM {{ ref "stripe_revenue" }}
)

-- Union all sources
SELECT
  date,
  cloud_provider,
  service_name,
  region,
  description,
  account_id,
  amount AS original_amount,
  original_currency,
  amount_usd,
  transaction_type,
  'USD' AS currency,  -- All amounts normalized to USD
  -- Categorize into cost and revenue for easy analysis (using USD amounts)
  CASE
    WHEN transaction_type IN ('revenue', 'charge') THEN amount_usd
    ELSE 0
  END AS revenue_amount,
  CASE
    WHEN transaction_type IN ('cost', 'fee') THEN ABS(amount_usd)
    WHEN transaction_type NOT IN ('revenue', 'charge') AND amount_usd > 0 THEN amount_usd
    ELSE 0
  END AS cost_amount
FROM (
  SELECT date, cloud_provider, service_name, region, description, account_id,
         amount, transaction_type, original_currency, amount_usd
  FROM aws_cost_data
  UNION ALL
  SELECT date, cloud_provider, service_name, region, description, account_id,
         amount, transaction_type, original_currency, amount_usd
  FROM gcp_cost_data
  UNION ALL
  SELECT date, cloud_provider, service_name, region, description, account_id,
         amount, transaction_type, original_currency, amount_usd
  FROM stripe_revenue_data
)
WHERE date IS NOT NULL
ORDER BY date DESC
