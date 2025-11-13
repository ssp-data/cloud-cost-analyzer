.DEFAULT_GOAL := run-all

install:
	uv sync

dlt-clear:
	# rm -rf ~/.dlt/
	rm -rf ~/.local/share/dlt/

clear-data:
	@if [ -f cloud_cost_analytics.duckdb ]; then \
		mv cloud_cost_analytics.duckdb cloud_cost_analytics.bak_$(shell date +%Y%m%d_%H%M%S).duckdb; \
	fi
	rm -rf viz_rill/data
	mkdir -p viz_rill/data

clear: dlt-clear clear-data



run-aws:
	uv run python pipelines/aws_pipeline.py
	echo "####################################################################"
run-gcp:
	uv run python pipelines/google_bq_incremental_pipeline.py
	echo "####################################################################"
run-stripe:
	uv run python pipelines/stripe_pipeline.py
	echo "####################################################################"


#run dlt incremental loads
run-etl: run-aws run-gcp run-stripe


test-duplicates-duckdb:
	@echo "Running duplicate checks on cloud_cost_analytics.duckdb..."
	@duckdb cloud_cost_analytics.duckdb < tests/test_duplicates.sql

test-duplicates:
	@echo "Running duplicate checks on parquet files in viz_rill/data..."
	@duckdb < tests/test_duplicates_parquet.sql

test: test-duplicates


serve:
	rill start viz_rill

## AWS-Specific Advanced Analytics (aws-cur-wizard integration)
aws-normalize:
	@echo "Normalizing AWS CUR data..."
	cd viz_rill && uv run python aws-cur-wizard/scripts/normalize.py

aws-generate-dashboards:
	@echo "Generating AWS-specific Rill dashboards..."
	cd viz_rill && uv run python aws-cur-wizard/scripts/generate_rill_yaml.py \
		--parquet data/normalized_aws.parquet \
		--output-dir . \
		--cost-col line_item_unblended_cost \
		--dim-prefixes "product_,line_item_" \
		--timeseries-col date

aws-dashboards: aws-normalize aws-generate-dashboards
	@echo "✅ AWS dashboards generated! Run 'make serve' to view them."

## GCP-Specific Advanced Analytics
gcp-normalize:
	@echo "Normalizing GCP billing data..."
	cd viz_rill && uv run python aws-cur-wizard/scripts/normalize_gcp.py

gcp-generate-dashboards:
	@echo "Generating GCP-specific Rill dashboards..."
	cd viz_rill && uv run python aws-cur-wizard/scripts/generate_gcp_rill_yaml.py \
		--parquet data/normalized_gcp.parquet \
		--output-dir . \
		--cost-col cost \
		--dim-prefixes "labels_,service__,project__" \
		--timeseries-col date

gcp-dashboards: gcp-normalize gcp-generate-dashboards
	@echo "✅ GCP dashboards generated! Run 'make serve' to view them."

#what this does:
# 1. load data incrementally
# 2. normalizes AWS & GCP cost reports and generates Rill dashboards
# 3. starts Rill BI and opens in browser
run-all: run-etl aws-normalize gcp-normalize serve
