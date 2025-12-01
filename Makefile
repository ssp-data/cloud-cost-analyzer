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
		if [ ! -t 0 ]; then \
			echo "⚠️  Non-interactive mode detected - skipping installation"; \
			echo "Please install Rill manually: curl https://rill.sh | sh"; \
			exit 1; \
		fi; \
		read -p "Install Rill now? (y/N): " answer; \
		if [ "$$answer" = "y" ] || [ "$$answer" = "Y" ]; then \
			curl -fsSL https://rill.sh | sh; \
			echo ""; \
			echo "⚠️  Rill installed. You may need to update your PATH:"; \
			echo "   export PATH=\"\$$HOME/.rill:\$$PATH\""; \
			echo ""; \
		else \
			echo "Skipped. Install later with: curl https://rill.sh | sh"; \
			exit 1; \
		fi; \
	fi

install: install-rill
	mkdir -p viz_rill/data/
	@if [ ! -f viz_rill/.env ]; then \
		echo "📋 Copying viz_rill/.env.example to viz_rill/.env"; \
		cp viz_rill/.env.example viz_rill/.env; \
		echo "✅ Created viz_rill/.env (you can edit it later if needed)"; \
	else \
		echo "✅ viz_rill/.env already exists"; \
	fi
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

clear-clickhouse:
	@echo "Clearing ClickHouse tables (interactive)..."
	uv run python scripts/clear_clickhouse.py

clear-clickhouse-force:
	@echo "⚠️  Force clearing ClickHouse tables (non-interactive)..."
	@echo "yes" | uv run python scripts/clear_clickhouse.py

clear: dlt-clear clear-data clear-rill

clear-all: clear clear-clickhouse


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
run-all: install run-etl aws-dashboards gcp-dashboards serve



## Production / ClickHouse (writes directly to ClickHouse Cloud)
run-aws-clickhouse:
	DLT_DESTINATION=clickhouse uv run python pipelines/aws_pipeline.py
	echo "####################################################################"
run-gcp-clickhouse:
	DLT_DESTINATION=clickhouse uv run python pipelines/google_bq_incremental_pipeline.py
	echo "####################################################################"
run-stripe-clickhouse:
	DLT_DESTINATION=clickhouse uv run python pipelines/stripe_pipeline.py
	echo "####################################################################"

# Run dlt incremental loads (production - clickhouse destination)
run-etl-clickhouse: run-aws-clickhouse run-gcp-clickhouse run-stripe-clickhouse
	@echo "✅ ClickHouse ETL complete (data in ClickHouse Cloud)"

# Initialize ClickHouse database (run once before first use)
init-clickhouse:
	@echo "Initializing ClickHouse database..."
	uv run python scripts/init_clickhouse.py

# Ingest normalized data to ClickHouse
ingest-normalized-clickhouse:
	@echo "Ingesting normalized AWS & GCP data to ClickHouse..."
	DLT_DESTINATION=clickhouse uv run python pipelines/ingest_normalized_pipeline.py

## Cloud Deployment with Anonymization (for public demos)
# Simple approach: Run normal ETL, then anonymize data directly in ClickHouse
anonymize-clickhouse:
	@echo ""
	@echo "================================================================================"
	@echo "Anonymizing ClickHouse Data for Public Demos"
	@echo "================================================================================"
	@echo ""
	uv run python scripts/anonymize_clickhouse.py
	@echo ""

# Complete cloud pipeline with anonymization
# Note: Dynamic dashboard generation (aws-dashboards/gcp-dashboards) requires local parquet files,
# so it's excluded from cloud mode. Static dashboards work with ClickHouse via models.
run-all-cloud: check-secrets run-etl-clickhouse anonymize-clickhouse serve
	@echo ""
	@echo "================================================================================"
	@echo "✅ Cloud deployment complete with anonymized data!"
	@echo "================================================================================"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Set RILL_CONNECTOR=clickhouse in viz_rill/.env"
	@echo "  2. Run 'make serve' to view dashboards with ClickHouse data"
	@echo "  3. Configure Rill Cloud to connect to your ClickHouse instance"
	@echo ""
	@echo "Useful commands:"
	@echo "  make anonymize-clickhouse     # Re-anonymize data"
	@echo "  make clear-clickhouse         # Drop all ClickHouse tables (interactive)"
	@echo "  make clear-clickhouse-force   # Drop all ClickHouse tables (non-interactive)"
	@echo ""
	@echo "Customize anonymization with environment variables:"
	@echo "  COST_MULTIPLIER_MIN=2.0 COST_MULTIPLIER_MAX=8.0 DUPLICATE_ROWS=3"
	@echo ""
	@echo "================================================================================"
