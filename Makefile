.DEFAULT_GOAL := run-all

install:
	uv sync

dlt-clear:
	# rm -rf ~/.dlt/
	rm -rf ~/.local/share/dlt/
	# rm aws_cur_pipeline.duckdb

clear-data:
	rm -r data_cost/aws_cost.duckdb

clear: dlt-clear clear-data
run-aws:
	uv run python pipelines/aws_pipeline.py

run-all:
	uv run python pipelines/aws_pipeline.py
