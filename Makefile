.DEFAULT_GOAL := run-all

install:
	uv sync

dlt-clear:
	# rm -rf ~/.dlt/
	rm -rf ~/.local/share/dlt/
clear-data:
	rm -r aws_cost.duckdb
	# rm aws_cur_pipeline.duckdb
	
clear: dlt-clear clear-data



run-aws:
	uv run python pipelines/aws_pipeline.py
run-bq:
	uv run python pipelines/google_bq_incremental_pipeline.py
run-stripe:
	uv run python pipelines/stripe_pipeline.py




run-all: run-aws run-bq run-stripe

