# Cloud Cost Analyzer Project

Multi-cloud cost analytics platform combining AWS Cost and Usage Reports (CUR), GCP billing data, and Stripe revenue metrics. Built with dlt for data ingestion, DuckDB for storage, and Rill for visualization.

## Features

- **Multi-Cloud Cost Tracking** - AWS, GCP, and future cloud providers
- **Revenue Integration** - Stripe payment data for margin analysis
- **Incremental Loading** - Efficient append-only data pipeline with dlt
- **Advanced Analytics** - RI/SP utilization, unit economics, effective cost tracking (by [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard)
- **Dynamic Dashboards** - Powered by Rill visualizations

## How it works

Setup secrets and configs, and then run:
```
git clone git@github.com:ssp-data/cloud-cost-analyzer.git
cd cloud-cost-analyzer
make
```

### How to Use: Seperate commands to run
```sh
  # View static dashboards (always available)
  make serve

  # Generate dynamic dashboards (optional)
  make aws-dashboards

  # List available cost columns
  make aws-list-cost-cols

  # Complete workflow
  make run-all
```

and it will export all data to `cloud_cost_analytics.duckdb`. The tables look something like this:
```
D select table_catalog, table_schema, table_name from information_schema.tables;
┌──────────────────────┬───────────────────┬─────────────────────────────────────────────────────────┐
│    table_catalog     │   table_schema    │                       table_name                        │
│       varchar        │      varchar      │                         varchar                         │
├──────────────────────┼───────────────────┼─────────────────────────────────────────────────────────┤
│ cloud_cost_analytics │ aws_costs         │ cur_export_test_00001                                   │
│ cloud_cost_analytics │ aws_costs         │ cur_export_test_00001__product                          │
│ cloud_cost_analytics │ aws_costs         │ cur_export_test_00001__product__list                    │
│ cloud_cost_analytics │ aws_costs         │ _dlt_loads                                              │
│ cloud_cost_analytics │ aws_costs         │ _dlt_pipeline_state                                     │
│ cloud_cost_analytics │ aws_costs         │ _dlt_version                                            │
│ cloud_cost_analytics │ aws_costs_staging │ cur_export_test_00001                                   │
│ cloud_cost_analytics │ aws_costs_staging │ cur_export_test_00001__product                          │
│ cloud_cost_analytics │ aws_costs_staging │ cur_export_test_00001__product__list                    │
│ cloud_cost_analytics │ aws_costs_staging │ _dlt_version                                            │
│ cloud_cost_analytics │ gcp_costs         │ _dlt_loads                                              │
│ cloud_cost_analytics │ gcp_costs         │ _dlt_pipeline_state                                     │
│ cloud_cost_analytics │ gcp_costs         │ _dlt_version                                            │
│ cloud_cost_analytics │ stripe_costs      │ balance_transaction                                     │
│ cloud_cost_analytics │ stripe_costs      │ balance_transaction__fee_details                        │
│ cloud_cost_analytics │ stripe_costs      │ event                                                   │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__available                          │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__card__networks__available          │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__features__subscription_cancel__c…  │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__items__data                        │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__last_payment_error__payment_meth…  │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__lines__data                        │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__next_action__use_stripe_sdk__dir…  │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__payment_method_types               │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__pending                            │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__refund_and_dispute_prefunding__a…  │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__refund_and_dispute_prefunding__p…  │
│ cloud_cost_analytics │ stripe_costs      │ event__data__object__saved_payment_method_options__al…  │
│ cloud_cost_analytics │ stripe_costs      │ event__data__previous_attributes__items__data           │
│ cloud_cost_analytics │ stripe_costs      │ _dlt_loads                                              │
│ cloud_cost_analytics │ stripe_costs      │ _dlt_pipeline_state                                     │
│ cloud_cost_analytics │ stripe_costs      │ _dlt_version                                            │
├──────────────────────┴───────────────────┴─────────────────────────────────────────────────────────┤
│ 32 rows                                                                                  3 columns │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Setup

General setup you can just run `uv sync` and it will install all required packages. You can see the once being installed and used in  `pyproject.toml` under dependencies.



## For AWS Pipeline

set local ENV variables:
```sh
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
```

Note: You can also set them in [secrets.toml][.dlt/secrets.toml] directly - I have set above and in [.env](.env) it will source them automatically with dlt feature of `SOURCES__FILESYSTEM__CREDENTIALS__AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"` as example.


## Incremental Loads with dlt

We use `write_disposition="append"` to load incrementally, but not merging, as cost data are usually append only.

## Visualization with Rill

The `viz_rill/` directory contains Rill dashboards for cost analysis:

- **Static Dashboards** (always available):
  - `dashboards/cloud_cost_explore.yaml` - Multi-cloud overview
  - `dashboards/aws_overview.yaml` - AWS cost analytics with RI/SP tracking
  - `dashboards/aws_explore.yaml` - Interactive AWS explorer
  - `dashboards/aws_product_insights.yaml` - Product dimension analysis

- **Dynamic Dashboards** (generated on-demand):
  - Run `make aws-dashboards` to generate dimension-specific canvases
  - Uses [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard) scripts

### View Dashboards

```bash
make serve
# Opens Rill at http://localhost:9009
```

### Generate Dynamic AWS Dashboards

```bash
make aws-dashboards
# Normalizes data and generates custom dimension canvases
```

## aws-cur-wizard Integration

This project integrates the sophisticated AWS cost analysis capabilities from [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard) (MIT License).

**What we use from aws-cur-wizard:**
- Normalization scripts for flattening AWS CUR data
- Dynamic dashboard generation with intelligent chart selection
- Jinja2 templates for metrics views and canvases
- Dimension analysis algorithm for optimal visualizations

**Location**: `viz_rill/aws-cur-wizard/`

**Attribution**: Full credit to the Rill Data team for these excellent patterns. See `viz_rill/aws-cur-wizard/README.md` for complete details and license.

### Static vs Dynamic Approach

We use a **hybrid approach**:

| Type | Location | When Generated | In Git? |
|------|----------|----------------|---------|
| **Static** | `viz_rill/dashboards/` | Manually created | ✅ Yes |
| **Dynamic** | `viz_rill/canvases/`, `viz_rill/explores/` | `make aws-dashboards` | ❌ No (gitignored) |

**Why both?**
- **Static**: Fast loading, version controlled, multi-cloud support, customized
- **Dynamic**: Adapts to schema changes, handles resource tags, follows AWS best practices

## Complete Workflow

```bash
# 1. Load data from all sources
make run-etl

# 2. (Optional) Generate dynamic AWS dashboards
make aws-dashboards

# 3. Start Rill dashboards
make serve
```

Or run everything at once:
```bash
make run-all
```


