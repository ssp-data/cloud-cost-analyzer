.DEFAULT_GOAL := run-all

check-secrets:
	@if [ ! -f .dlt/secrets.toml ]; then \
		echo ""; \
		echo "================================================================================"; \
		echo "ERROR: Missing .dlt/secrets.toml"; \
		echo "================================================================================"; \
		echo ""; \
		echo "Please create .dlt/secrets.toml from the example:"; \
		echo "  cp .dlt/secrets.toml.example .dlt/secrets.toml"; \
		echo ""; \
		echo "Then edit .dlt/secrets.toml and add your credentials."; \
		echo ""; \
		echo "================================================================================"; \
		echo ""; \
		exit 1; \
	fi

install-rill:
	@if command -v rill >/dev/null 2>&1; then \
		echo "✅ Rill is already installed (version: $$(rill version 2>/dev/null || echo 'unknown'))"; \
	else \
		echo ""; \
		echo "================================================================================"; \
		echo "Rill is not installed"; \
		echo "================================================================================"; \
		echo ""; \
		echo "Rill is required to run the visualization dashboards."; \
		echo ""; \
		read -p "Would you like to install Rill now? (y/N): " answer; \
		if [ "$$answer" = "y" ] || [ "$$answer" = "Y" ]; then \
			echo "Installing Rill..."; \
			curl -fsSL https://rill.sh | sh; \
			echo "✅ Rill installed successfully"; \
		else \
			echo ""; \
			echo "Skipping Rill installation."; \
			echo "You can install it later by running: make install-rill"; \
			echo "Or manually with: curl https://rill.sh | sh"; \
			echo ""; \
		fi; \
	fi

install: install-rill
	mkdir -p viz_rill/data/
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

clear-rill:
	@echo "Clearing Rill cache and materialized views..."
	rm -rf viz_rill/tmp/
	@echo "✅ Rill cache cleared"

clear: dlt-clear clear-data clear-rill


run-aws: check-secrets
	uv run python pipelines/aws_pipeline.py
	echo "####################################################################"
run-gcp: check-secrets
	uv run python pipelines/google_bq_incremental_pipeline.py
	echo "####################################################################"
run-stripe: check-secrets
	uv run python pipelines/stripe_pipeline.py
	echo "####################################################################"


#run dlt incremental loads
run-etl: check-secrets run-aws run-gcp run-stripe


test-duplicates-duckdb:
	@echo "Running duplicate checks on cloud_cost_analytics.duckdb..."
	@duckdb cloud_cost_analytics.duckdb < tests/test_duplicates.sql

test-duplicates:
	@echo "Running duplicate checks on parquet files in viz_rill/data..."
	@duckdb < tests/test_duplicates_parquet.sql

test: test-duplicates


serve:
	rill start viz_rill

demo: install-rill
	@echo "================================================================================"
	@echo "Running in DEMO mode with sample data"
	@echo "================================================================================"
	@echo ""
	@echo "Clearing existing data directory..."
	@rm -rf viz_rill/data
	@mkdir -p viz_rill/data
	@echo "Copying demo data to viz_rill/data/..."
	@cp -r viz_rill/data_demo/* viz_rill/data/
	@echo "✅ Demo data copied successfully"
	@echo ""
	@echo "Starting Rill dashboards with demo data..."
	@echo "NOTE: Run 'make clear' before running 'make run-all' to use real data"
	@echo ""
	rill start viz_rill

## AWS Advanced Analytics (CUR Wizard integration)
aws-normalize:
	@echo "Normalizing AWS CUR data..."
	cd viz_rill && uv run python cur-wizard/scripts/normalize.py

aws-generate-dashboards:
	@echo "Generating AWS-specific Rill dashboards..."
	cd viz_rill && uv run python cur-wizard/scripts/generate_rill_yaml.py \
		--parquet data/normalized_aws.parquet \
		--output-dir . \
		--cost-col line_item_unblended_cost \
		--dim-prefixes "product_,line_item_" \
		--timeseries-col date

aws-dashboards: aws-normalize aws-generate-dashboards
	@echo "✅ AWS dashboards generated! Run 'make serve' to view them."

## GCP Advanced Analytics (CUR Wizard integration)
gcp-normalize:
	@echo "Normalizing GCP billing data..."
	cd viz_rill && uv run python cur-wizard/scripts/normalize_gcp.py

gcp-generate-dashboards:
	@echo "Generating GCP-specific Rill dashboards..."
	cd viz_rill && uv run python cur-wizard/scripts/generate_gcp_rill_yaml.py \
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
run-all: install run-etl aws-normalize gcp-normalize serve
