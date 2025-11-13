.DEFAULT_GOAL := run-all

install:
	uv sync

dlt-clear:
	# rm -rf ~/.dlt/
	rm -rf ~/.local/share/dlt/

clear-data:
	mv cloud_cost_analytics.duckdb cloud_cost_analytics.bak_$(shell date +%Y%m%d_%H%M%S).duckdb
	
clear: dlt-clear clear-data



run-aws:
	uv run python pipelines/aws_pipeline.py
	echo "####################################################################"
run-bq:
	uv run python pipelines/google_bq_incremental_pipeline.py
	echo "####################################################################"
run-stripe:
	uv run python pipelines/stripe_pipeline.py
	echo "####################################################################"




run-all: run-aws run-bq run-stripe

test-duplicates:
	@echo "Running duplicate checks on cloud_cost_analytics.duckdb..."
	@duckdb cloud_cost_analytics.duckdb < tests/test_duplicates.sql

