# flake8: noqa
import humanize
from typing import Any
import os

import dlt
from dlt.common import pendulum

from google.cloud import bigquery
from google.oauth2 import service_account

def bigquery_billing_table(
    table_name: str,
    dataset: str = None,
    project_id: str = None,
    initial_start_date: str = None,
):
    """
    Load a BigQuery billing table incrementally using export_time as cursor
    """
    # Set up incremental loading with initial start date from config
    if initial_start_date:
        initial_value = pendulum.parse(initial_start_date)
    else:
        initial_value = pendulum.parse("2000-01-01T00:00:00Z")

    # Create the dlt resource with incremental loading decorator
    @dlt.resource(write_disposition="append")
    def _load_table(
        incremental: dlt.sources.incremental[str] = dlt.sources.incremental("export_time", initial_value=initial_value)
    ):
        # Get service account credentials from .dlt/secrets.toml
        service_account_info = {
            "project_id": dlt.secrets.get('source.bigquery.credentials.project_id'),
            "private_key": dlt.secrets.get('source.bigquery.credentials.private_key'),
            "client_email": dlt.secrets.get('source.bigquery.credentials.client_email'),
            "token_uri": dlt.secrets.get('source.bigquery.credentials.token_uri'),
        }
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        client = bigquery.Client(credentials=credentials, project=project_id)

        # Get the last loaded value for incremental loading
        last_value = incremental.last_value

        query = f"""
            SELECT * FROM `{project_id}.{dataset}.{table_name}`
            WHERE export_time > @last_value
            ORDER BY export_time
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("last_value", "TIMESTAMP", last_value)
            ]
        )

        print(f'Loading {table_name} (incremental from {last_value})...')
        for row in client.query(query, job_config=job_config):
            yield {key: value for key, value in row.items()}

    # Set the resource name to 'bigquery_billing_table' to maintain consistent output directory
    return _load_table.with_name("bigquery_billing_table")


def load_standalone_table_resource() -> None:
    """Load BigQuery billing export tables into DuckDB"""

    # Load configuration from config.toml
    try:
        pipeline_name = dlt.config["pipeline.pipeline_name"]
    except KeyError:
        pipeline_name = "cloud_cost_analytics"

    try:
        dataset_name = dlt.config["sources.gcp_billing.dataset_name"]
    except KeyError:
        dataset_name = "gcp_costs"

    # Get initial start date from config (optional)
    try:
        initial_start_date = dlt.config["sources.gcp_billing.initial_start_date"]
    except KeyError:
        initial_start_date = None

    project_id = dlt.secrets.get('source.bigquery.credentials.project_id')
    dataset = dlt.config["sources.gcp_billing.dataset"]
    table_names = dlt.config["sources.gcp_billing.table_names"]

    # Create pipeline to write parquet files for Rill
    # Using filesystem destination to write parquet files
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination="filesystem",
        dataset_name=dataset_name,
        # export_schema_path="exported_schema/google_cost_schema.json"
    )

    # Create resources for each table with initial start date
    resources = [bigquery_billing_table(table_name, dataset=dataset, project_id=project_id, initial_start_date=initial_start_date) for table_name in table_names]

    # Run the pipeline with incremental (append) write disposition
    # This will only load new records based on export_time
    # Use loader_file_format="parquet" in run() to generate parquet files
    info = pipeline.run(resources, loader_file_format="parquet")
    print(info)
    print(f"\nSuccessfully loaded {len(table_names)} tables to DuckDB (incremental)")
    print(pipeline.default_schema.to_pretty_yaml())



if __name__ == "__main__":
    # Load selected tables with different settings
    # load_select_tables_from_database()

    # load_entire_database()
    # select_with_end_value_and_row_order()

    # Load tables with the standalone table resource
    load_standalone_table_resource()

    # Load all tables from the database.
    # Warning: The sample database is very large
    # load_entire_database()
