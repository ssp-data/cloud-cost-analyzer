# Cloud Cost Analytics with Rill

Multi-cloud cost analytics dashboard combining AWS Cost and Usage Reports (CUR), GCP billing data, and Stripe revenue metrics into a unified analytics platform.

## Quick Start

```bash
cd viz_rill
rill start
```

Rill will build your project from data sources to dashboards and launch in your browser.

## Overview

This project provides comprehensive cost analytics across multiple cloud providers and revenue sources:

- **AWS Costs**: Full AWS Cost and Usage Report (CUR) analysis with RI/SP tracking
- **GCP Costs**: Google Cloud Platform billing data (via BigQuery export)
- **Stripe Revenue**: Payment processing fees and revenue tracking

The dashboards are designed for engineering, finance, and operations teams to:
- Track multi-cloud spending trends
- Optimize Reserved Instance (RI) and Savings Plan (SP) utilization
- Analyze gross margins (revenue vs. cloud costs)
- Identify cost anomalies and optimization opportunities

## Data Model

### Unified Cost Model
Combines all cost and revenue sources into a star schema:

**Dimensions:**
- Cloud Provider (AWS, GCP, Stripe)
- Service/Product Name
- Region
- Account ID
- Transaction Type (cost, revenue, fee)

**Metrics:**
- Total Cost & Revenue
- Net Margin & Gross Margin %
- Cost per Unit (efficiency tracking)

### AWS-Specific Model
Direct access to AWS CUR data with full fidelity:

**Key Dimensions:**
- Product Family, Service Name, Product Code
- Region, Availability Zone
- Usage Account, Payer Account
- Usage Type, Operation
- Pricing Term (On-Demand, Reserved, Spot)

**Key Metrics:**
- Unblended Cost (list price)
- Blended Cost (averaged across accounts)
- **Effective Cost** (RI/SP amortized)
- On-Demand Cost (for comparison)
- RI/SP Savings & Utilization
- Unit Economics (cost per usage unit)
- Marketplace Spend

## Dashboards

### 1. Cloud Cost Analytics (`cloud_cost_explore.yaml`)
Overall multi-cloud cost and revenue analysis with margin tracking.

### 2. AWS Cost Analytics (`aws_overview.yaml`)
**Advanced AWS-specific dashboard** featuring:
- Effective Cost vs. Unblended Cost comparison
- RI/SP savings tracking
- Regional cost distribution
- Multi-account breakdown
- Unit economics trends
- RI utilization monitoring
- Marketplace spend isolation

Inspired by best practices from [aws-cur-wizard](https://github.com/rilldata/aws-cur-wizard).

### 3. AWS Cost Explorer (`aws_explore.yaml`)
Interactive drill-down interface for ad-hoc AWS cost analysis.

### 4. AWS Product Deep Dive (`aws_product_insights.yaml`)
Detailed product, service, and usage type analysis with leaderboards.

## Data Pipeline

Data is ingested using [dlt (data load tool)](https://dlthub.com/):

```bash
# Run pipelines (from project root)
make run-aws      # AWS CUR → Parquet
make run-gcp      # GCP BigQuery → Parquet
make run-stripe   # Stripe → Parquet
```

Parquet files are written to `viz_rill/data/`:
- `aws_costs/` - AWS CUR data
- `gcp_costs/` - GCP billing data
- `stripe_costs/` - Stripe transaction data

## Advanced AWS Analytics

This project incorporates sophisticated AWS cost analysis techniques from [aws-cur-wizard](https://github.com/rilldata/aws-cur-wizard), including:

### Effective Cost Calculation
AWS billing has multiple cost types:
- **Unblended Cost**: List price (what you'd pay without commitments)
- **Blended Cost**: Averaged across accounts in an organization
- **Effective Cost**: True cost after RI/SP amortization

The dashboards show **Effective Cost** to give you the real financial picture.

### RI/SP Utilization Tracking
Monitor Reserved Instance and Savings Plan efficiency:
- Recurring fees (used capacity)
- Unused fees (wasted spend)
- Utilization percentage
- Savings vs. on-demand pricing

### Unit Economics
Track cost efficiency over time:
```
Cost per Unit = Total Cost / Total Usage Amount
```
Helps identify whether cost increases are due to inefficiency or business growth.

### Marketplace Spend
Isolate 3rd-party AWS Marketplace charges that often hide in blended totals.

## Project Structure

```
viz_rill/
├── sources/
│   ├── aws_cost_normalized.yaml    # AWS CUR source with date extraction
│   └── (unified source - TBD)
├── metrics/
│   ├── aws_cost_metrics.yaml       # AWS-specific metrics with RI/SP tracking
│   └── cloud_cost_metrics.yaml     # Multi-cloud metrics
├── dashboards/
│   ├── aws_overview.yaml           # Advanced AWS analytics canvas
│   ├── aws_explore.yaml            # Interactive AWS explorer
│   ├── aws_product_insights.yaml   # Product dimension deep dive
│   └── cloud_cost_explore.yaml     # Multi-cloud overview
├── models/
│   ├── aws_costs.sql               # AWS cost model
│   ├── stripe_revenue.sql          # Stripe revenue model
│   └── unified_cost_model.sql      # Combined star schema
├── scripts/
│   ├── normalize_aws.py            # AWS data normalization
│   ├── generate_aws_dashboards.py  # Dynamic dashboard generation
│   └── utils/
│       └── dimension_chart_selector.py  # Chart selection algorithm
├── templates/                      # Jinja2 templates for dynamic generation
└── data/                           # Parquet files (gitignored)
```

## Acknowledgements

AWS cost analytics capabilities inspired by and adapted from:
- **[aws-cur-wizard](https://github.com/rilldata/aws-cur-wizard)** by [Rill Data](https://github.com/rilldata)
- Special thanks to the Rill team for demonstrating best practices in CUR analysis

The dimension chart selector algorithm, Jinja2 templates, and effective cost calculation patterns are based on their work.

## License

This project builds upon techniques from aws-cur-wizard (Apache 2.0 License).
See individual file headers for attribution details.

## Future Enhancements

- [ ] GCP-specific dashboards with committed use discount tracking
- [ ] Dynamic canvas generation for resource tags (when tags are added to AWS export)
- [ ] Budget tracking and forecasting
- [ ] Anomaly detection alerts
- [ ] Multi-cloud cost comparison canvas
