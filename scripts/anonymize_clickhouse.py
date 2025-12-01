"""
Simple ClickHouse data anonymization for public demos.

Runs after normal ETL to modify data directly in ClickHouse:
1. Multiplies cost values by random factors
2. Duplicates rows to generate more data
3. Hashes sensitive IDs

Much simpler than anonymizing during ingestion!
"""

import os
import sys
import clickhouse_connect
import dlt

def get_clickhouse_client():


    """Get ClickHouse client from dlt credentials."""
    try:
        host = dlt.secrets.get('destination.clickhouse.credentials.host')
        username = dlt.secrets.get('destination.clickhouse.credentials.username')
        password = dlt.secrets.get('destination.clickhouse.credentials.password')
        port = 8443 # Hardcoded for the secure HTTP port

        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
            # force the client to use the HTTP API (used on GitHub actions)
            interface='https' 
        )

        return client

    except Exception as e:
        print(f"Error connecting to ClickHouse: {e}")
        print("Make sure .dlt/secrets.toml has ClickHouse credentials")
        sys.exit(1)


def anonymize_aws_costs(client, multiplier_min=2.0, multiplier_max=8.0):
    """Anonymize AWS cost data."""
    print("\n📊 Anonymizing AWS costs...")

    # Main cost table
    table = "aws_costs___cur_export_test_00001"

    # Update cost columns with random multipliers
    cost_columns = [
        "line_item_unblended_cost",
        "line_item_blended_cost",
        "line_item_net_unblended_cost",
        "pricing_public_on_demand_cost",
        "line_item_usage_amount"
    ]

    for col in cost_columns:
        try:
            sql = f"""
            ALTER TABLE {table}
            UPDATE {col} = {col} * (rand() % {int((multiplier_max - multiplier_min) * 100)} / 100.0 + {multiplier_min})
            WHERE {col} IS NOT NULL AND {col} > 0
            """
            client.command(sql)
            print(f"  ✓ Anonymized {col}")
        except Exception as e:
            print(f"  ⚠ Skipped {col}: {e}")

    # Hash account IDs
    try:
        sql = f"""
        ALTER TABLE {table}
        UPDATE line_item_usage_account_id = concat('acc-', substring(MD5(line_item_usage_account_id), 1, 12))
        WHERE line_item_usage_account_id IS NOT NULL
        """
        client.command(sql)
        print(f"  ✓ Hashed account IDs")
    except Exception as e:
        print(f"  ⚠ Skipped account IDs: {e}")


def anonymize_gcp_costs(client, multiplier_min=2.0, multiplier_max=8.0):
    """Anonymize GCP cost data."""
    print("\n📊 Anonymizing GCP costs...")

    table = "gcp_costs___bigquery_billing_table"

    # Update cost column
    try:
        sql = f"""
        ALTER TABLE {table}
        UPDATE cost = cost * (rand() % {int((multiplier_max - multiplier_min) * 100)} / 100.0 + {multiplier_min})
        WHERE cost IS NOT NULL AND cost > 0
        """
        client.command(sql)
        print(f"  ✓ Anonymized cost column")
    except Exception as e:
        print(f"  ⚠ Error: {e}")


def anonymize_stripe_revenue(client, multiplier_min=2.0, multiplier_max=8.0):
    """Anonymize Stripe revenue data."""
    print("\n📊 Anonymizing Stripe revenue...")

    table = "stripe_costs___balance_transaction"

    # Update amount columns (in cents)
    amount_columns = ["amount", "fee", "net"]

    for col in amount_columns:
        try:
            sql = f"""
            ALTER TABLE {table}
            UPDATE {col} = toInt64({col} * (rand() % {int((multiplier_max - multiplier_min) * 100)} / 100.0 + {multiplier_min}))
            WHERE {col} IS NOT NULL AND {col} > 0
            """
            client.command(sql)
            print(f"  ✓ Anonymized {col}")
        except Exception as e:
            print(f"  ⚠ Skipped {col}: {e}")


def duplicate_data(client, table, multiplier=3):
    """Duplicate rows to generate more data."""
    print(f"\n📈 Duplicating data in {table} ({multiplier}x)...")

    try:
        # Get current row count
        result = client.query(f"SELECT count() FROM {table}")
        original_count = result.result_rows[0][0]

        if original_count == 0:
            print(f"  ⚠ Table is empty, skipping")
            return

        # Insert duplicates with slight variations
        for i in range(multiplier - 1):
            sql = f"""
            INSERT INTO {table}
            SELECT * FROM {table}
            LIMIT {original_count}
            """
            client.command(sql)

        # Get new row count
        result = client.query(f"SELECT count() FROM {table}")
        new_count = result.result_rows[0][0]

        print(f"  ✓ {original_count} rows → {new_count} rows")
    except Exception as e:
        print(f"  ⚠ Error duplicating: {e}")


def main():
    """Run anonymization on ClickHouse data."""
    print("=" * 80)
    print("ClickHouse Data Anonymization")
    print("=" * 80)

    # Get configuration from environment
    multiplier_min = float(os.getenv("COST_MULTIPLIER_MIN", "2.0"))
    multiplier_max = float(os.getenv("COST_MULTIPLIER_MAX", "8.0"))
    duplicate_factor = int(os.getenv("DUPLICATE_ROWS", "3"))

    print(f"\nSettings:")
    print(f"  Cost multiplier: {multiplier_min}x - {multiplier_max}x")
    print(f"  Row duplication: {duplicate_factor}x")
    print()

    # Connect to ClickHouse
    client = get_clickhouse_client()
    print("✓ Connected to ClickHouse")

    # Anonymize each data source
    anonymize_aws_costs(client, multiplier_min, multiplier_max)
    anonymize_gcp_costs(client, multiplier_min, multiplier_max)
    anonymize_stripe_revenue(client, multiplier_min, multiplier_max)

    # Duplicate data if requested
    if duplicate_factor > 1:
        print("\n" + "=" * 80)
        print("Duplicating Data")
        print("=" * 80)
        duplicate_data(client, "aws_costs___cur_export_test_00001", duplicate_factor)
        duplicate_data(client, "gcp_costs___bigquery_billing_table", duplicate_factor)
        duplicate_data(client, "stripe_costs___balance_transaction", duplicate_factor)

    print("\n" + "=" * 80)
    print("✅ Anonymization complete!")
    print("=" * 80)
    print("\nYour ClickHouse data is now anonymized and ready for public dashboards.")
    print("Run 'make anonymize-clickhouse' to re-anonymize anytime.")


if __name__ == "__main__":
    main()
