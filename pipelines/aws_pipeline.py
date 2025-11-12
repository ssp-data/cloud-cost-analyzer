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

    # Configure filesystem resource
    filesystem_resource = filesystem(
        bucket_url=bucket_url,
        file_glob=file_glob,
        incremental=dlt.sources.incremental("modification_date"),
    )

    # Pipe to parquet reader
    filesystem_pipe = filesystem_resource | read_parquet()

    # Create pipeline with appropriate naming
    pipeline = dlt.pipeline(
        pipeline_name="cloud_cost_analytics",
        destination="duckdb",
        dataset_name="aws_costs",
        export_schema_path="data_cost/aws_cost_schema.json",
    )

    # Load the data with merge write disposition for deduplication
    load_info = pipeline.run(
        filesystem_pipe.with_name(table_name),
        write_disposition="merge"
    )

    print("\n" + "="*50)
    print("Load Info:")
    print(load_info)
    print("\nNormalize Info:")
    print(pipeline.last_trace.last_normalize_info)
