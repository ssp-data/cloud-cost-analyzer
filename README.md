# Cloud Cost Analyzer Project

Using dlt to load AWS Cost report and Google, combine with Stripe income and load into ClickHouse (DuckDB locally) and present with Rill.

## How it works

Setup secrets and configs, and then run:
```
make
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
