from typing import Optional, Tuple

import dlt
from pendulum import DateTime
from helpers.stripe_analytics import (
    incremental_stripe_source,
    stripe_source,
)
from helpers.stripe_analytics.settings import (
    ENDPOINTS,
    INCREMENTAL_ENDPOINTS,
)


def load_data(
    endpoints: Tuple[str, ...] = ("Product", "Price"), #use `ENDPOINTS + INCREMENTAL_ENDPOINTS,` for all data
    start_date: Optional[DateTime] = None,
    end_date: Optional[DateTime] = None,
) -> None:
    """
    Load Stripe reference data (non-incremental, replace mode).

    IMPORTANT: Only loads Product and Price to avoid PII. These endpoints contain:
    - Product catalog information (names, descriptions, features)
    - Pricing information (amounts, currencies, billing intervals)

    Args:
        endpoints: A tuple of endpoint names to retrieve data from.
                   Defaults to Product and Price (no PII).
        start_date: An optional start date to limit the data retrieved. Defaults to None.
        end_date: An optional end date to limit the data retrieved. Defaults to None.
    """
    # Load configuration from config.toml
    try:
        pipeline_name = dlt.config["pipeline.pipeline_name"]
    except KeyError:
        pipeline_name = "cloud_cost_analytics"

    try:
        dataset_name = dlt.config["sources.stripe.dataset_name"]
    except KeyError:
        dataset_name = "stripe_costs"

    # Using filesystem destination to write parquet files for Rill
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination="filesystem",
        dataset_name=dataset_name,
        # export_schema_path="exported_schema/stripe_cost_schema.json",
    )
    source = stripe_source(
        endpoints=endpoints, start_date=start_date, end_date=end_date
    )
    # Use loader_file_format="parquet" in run() to generate parquet files
    load_info = pipeline.run(source, loader_file_format="parquet")
    print(load_info)


def load_incremental_endpoints(
    endpoints: Tuple[str, ...] = ("BalanceTransaction",), # use `INCREMENTAL_ENDPOINTS,` to load all data

    initial_start_date: Optional[DateTime] = None,
    end_date: Optional[DateTime] = None,
) -> None:
    """
    Load Stripe cost data using incremental loading (append mode).

    IMPORTANT: Only loads BalanceTransaction to avoid storing PII (customer emails, names, etc).
    BalanceTransaction contains all necessary financial data for cost analysis:
    - Transaction amounts, fees, net revenue
    - Currency and exchange rates
    - Transaction types and categories
    - Fee details (Stripe fees, application fees, taxes)

    This approach enables us to load all the data for the first time and only retrieve
    the newest data later, without duplicating and downloading a massive amount of data.

    Args:
        endpoints: A tuple of incremental endpoint names to retrieve data from.
                   Defaults to only BalanceTransaction (no PII).
        initial_start_date: An optional parameter that specifies the initial value for dlt.sources.incremental.
                            If parameter is not None, then load only data that were created after initial_start_date on the first run.
                            Defaults to None. Format: datetime(YYYY, MM, DD).
        end_date: An optional end date to limit the data retrieved.
                  Defaults to None. Format: datetime(YYYY, MM, DD).
    """
    # Load configuration from config.toml
    try:
        pipeline_name = dlt.config["pipeline.pipeline_name"]
    except KeyError:
        pipeline_name = "cloud_cost_analytics"

    try:
        dataset_name = dlt.config["sources.stripe.dataset_name"]
    except KeyError:
        dataset_name = "stripe_costs"

    # Using filesystem destination to write parquet files for Rill
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination="filesystem",
        dataset_name=dataset_name,
        # export_schema_path="exported_schema/stripe_cost_schema.json",
    )
    # load all data on the first run that created before end_date
    source = incremental_stripe_source(
        endpoints=endpoints,
        initial_start_date=initial_start_date,
        end_date=end_date,
    )
    # Use loader_file_format="parquet" in run() to generate parquet files
    load_info = pipeline.run(source, loader_file_format="parquet")
    print(load_info)

    # # load nothing, because incremental loading and end date limit
    # source = incremental_stripe_source(
    #     endpoints=endpoints,
    #     initial_start_date=initial_start_date,
    #     end_date=end_date,
    # )
    # load_info = pipeline.run(source)
    # print(load_info)
    #
    # # load only the new data that created after end_date
    # source = incremental_stripe_source(
    #     endpoints=endpoints,
    #     initial_start_date=initial_start_date,
    # )
    # load_info = pipeline.run(source)
    # print(load_info)


if __name__ == "__main__":
    # Use incremental loading for cost data to avoid duplicates
    load_incremental_endpoints()
    # # load only data that was created during the period between the Jan 1, 2024 (incl.), and the Feb 1, 2024 (not incl.).
    # from pendulum import datetime
    # load_data(start_date=datetime(2024, 1, 1), end_date=datetime(2024, 2, 1))
    # # load only data that was created during the period between the May 3, 2023 (incl.), and the March 1, 2024 (not incl.).
    # load_incremental_endpoints(
    #     endpoints=("Event",),
    #     initial_start_date=datetime(2023, 5, 3),
    #     end_date=datetime(2024, 3, 1),
    # )
