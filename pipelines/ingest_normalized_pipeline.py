#!/usr/bin/env python3
"""
Ingest normalized parquet files into ClickHouse.

This pipeline loads the normalized AWS and GCP data (created by normalize.py scripts)
into ClickHouse for production analytics.

Usage:
    # Make sure normalized files exist first:
    make aws-normalize gcp-normalize

    # Then ingest to ClickHouse:
    DLT_DESTINATION=clickhouse python pipelines/ingest_normalized_pipeline.py
"""
import os
import sys
from pathlib import Path

import dlt
from dlt.sources.filesystem import filesystem, read_parquet


def ingest_normalized_data():
    """Ingest normalized AWS and GCP parquet files to ClickHouse."""

    # Get destination from environment (should be 'clickhouse' for this pipeline)
    destination = os.getenv("DLT_DESTINATION", "clickhouse")

    if destination != "clickhouse":
        print("⚠️  Warning: This pipeline is designed for ClickHouse destination")
        print(f"   Current destination: {destination}")
        print("   Set DLT_DESTINATION=clickhouse to ingest to ClickHouse")

    # Pipeline configuration
    try:
        pipeline_name = dlt.config["pipeline.pipeline_name"]
    except KeyError:
        pipeline_name = "cloud_cost_analytics"

    # Check if normalized files exist
    normalized_dir = Path("viz_rill/data")
    aws_normalized = normalized_dir / "normalized_aws.parquet"
    gcp_normalized = normalized_dir / "normalized_gcp.parquet"

    resources = []

    # AWS Normalized Data
    if aws_normalized.exists():
        print(f"📊 Found AWS normalized data: {aws_normalized}")

        # Create filesystem resource for AWS normalized data
        aws_fs = filesystem(
            bucket_url=str(normalized_dir),
            file_glob="normalized_aws.parquet"
        )
        aws_pipe = aws_fs | read_parquet()
        aws_resource = aws_pipe.with_name("aws_costs_normalized")
        aws_resource.apply_hints(
            write_disposition="replace"  # Replace normalized data each time
        )
        resources.append(aws_resource)
    else:
        print(f"⚠️  AWS normalized data not found: {aws_normalized}")
        print("   Run 'make aws-normalize' first")

    # GCP Normalized Data
    if gcp_normalized.exists():
        print(f"📊 Found GCP normalized data: {gcp_normalized}")

        # Create filesystem resource for GCP normalized data
        gcp_fs = filesystem(
            bucket_url=str(normalized_dir),
            file_glob="normalized_gcp.parquet"
        )
        gcp_pipe = gcp_fs | read_parquet()
        gcp_resource = gcp_pipe.with_name("gcp_costs_normalized")
        gcp_resource.apply_hints(
            write_disposition="replace"  # Replace normalized data each time
        )
        resources.append(gcp_resource)
    else:
        print(f"⚠️  GCP normalized data not found: {gcp_normalized}")
        print("   Run 'make gcp-normalize' first")

    if not resources:
        print("\n❌ No normalized data found to ingest")
        print("   Run 'make aws-normalize gcp-normalize' first")
        sys.exit(1)

    # Create pipeline for normalized data
    pipeline = dlt.pipeline(
        pipeline_name=f"{pipeline_name}_normalized",
        destination=destination,
        dataset_name="cloud_costs_normalized",
    )

    # Load the normalized data
    print(f"\n🚀 Loading normalized data to {destination}...")
    load_info = pipeline.run(resources)

    print("\n" + "="*50)
    print(f"Destination: {destination}")
    print("Load Info:")
    print(load_info)

    if load_info.has_failed_jobs:
        print("\n❌ Some jobs failed:")
        for job in load_info.load_packages[0].jobs["failed_jobs"]:
            print(f"  - {job}")
        sys.exit(1)
    else:
        print("\n✅ Normalized data ingestion complete!")


if __name__ == "__main__":
    ingest_normalized_data()
