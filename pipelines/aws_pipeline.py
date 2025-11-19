# bucket: cost-analysis-demo-sspaeti
# url: https://s3.us-west-1.amazonaws.com
# endpoint: us-west-1
# path: /cost-analysis-demo-sspaeti/cur/CUR-export-test/data/BILLING_PERIOD=2025-11/CUR-export-test-00001.snappy.parquet

# From: https://dlthub.com/docs/dlt-ecosystem/verified-sources/filesystem/basic

import dlt
from dlt.sources.filesystem import filesystem, read_parquet

if __name__ == "__main__":
    # Load configuration from config.toml [sources.aws_cur] section
    bucket_url = dlt.config["sources.aws_cur.bucket_url"]
    file_glob = dlt.config["sources.aws_cur.file_glob"]
    table_name = dlt.config["sources.aws_cur.table_name"]

    # Optional config with defaults
    try:
        dataset_name = dlt.config["sources.aws_cur.dataset_name"]
    except KeyError:
        dataset_name = "aws_costs"

    try:
        pipeline_name = dlt.config["pipeline.pipeline_name"]
    except KeyError:
        pipeline_name = "cloud_cost_analytics"

    # Get initial start date from config (optional)
    try:
        from dlt.common import pendulum
        initial_start_date_str = dlt.config["sources.aws_cur.initial_start_date"]
        initial_start_date = pendulum.parse(initial_start_date_str)
    except KeyError:
        initial_start_date = None

    # Configure filesystem resource with optional start date
    filesystem_resource = filesystem(
        bucket_url=bucket_url,
        file_glob=file_glob,
        incremental=dlt.sources.incremental("modification_date", initial_value=initial_start_date),
    )

    # Pipe to parquet reader
    filesystem_pipe = filesystem_resource | read_parquet()

    # Create pipeline with appropriate naming
    # Using filesystem destination to write parquet files for Rill
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination="filesystem",
        dataset_name=dataset_name,
        # export_schema_path="exported_schema/aws_cost_schema.json",
    )

    # Load the data with merge mode and composite primary key for deduplication
    # AWS CUR records are uniquely identified by line_item_id + time_interval
    # Using merge instead of append to enforce primary key constraint
    resource = filesystem_pipe.with_name(table_name)
    resource.apply_hints(
        primary_key=["identity_line_item_id", "identity_time_interval"],
        write_disposition="merge",
        merge_key=["identity_line_item_id", "identity_time_interval"]
    )
    # Use loader_file_format="parquet" in run() to generate parquet files
    load_info = pipeline.run(resource, loader_file_format="parquet")

    # Print concise summary instead of full schema
    print(f"\nPipeline {pipeline.pipeline_name} completed successfully")
    print(f"Loaded to: {pipeline.destination}")
    print(f"Dataset: {pipeline.dataset_name}")
