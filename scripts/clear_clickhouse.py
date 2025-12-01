"""
Clear ClickHouse tables for cloud cost analytics.

Drops all tables in the default schema that belong to dlt datasets and Rill models:

dlt tables (from ETL pipelines):
- aws_costs___*
- gcp_costs___*
- stripe_costs___*
- aws_costs_staging___*

Rill model tables (materialized views):
- aws_costs
- gcp_costs
- stripe_revenue
- unified_cost_model

This is safe to run - only drops tables created by our ETL pipelines and Rill.
"""

import sys
import clickhouse_connect
import dlt

def get_clickhouse_client():
    """Get ClickHouse client from dlt credentials."""
    try:
        host = dlt.secrets.get('destination.clickhouse.credentials.host')
        username = dlt.secrets.get('destination.clickhouse.credentials.username')
        password = dlt.secrets.get('destination.clickhouse.credentials.password')
        port = 8443  # Hardcoded for the secure HTTP port

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
        print(f"❌ Error connecting to ClickHouse: {e}")
        print("Make sure .dlt/secrets.toml has ClickHouse credentials")
        sys.exit(1)


def get_dlt_tables(client):
    """Get list of all dlt-created tables and Rill model tables."""
    query = """
    SELECT name
    FROM system.tables
    WHERE database = 'default'
    AND (
        name LIKE 'aws_costs___%'
        OR name LIKE 'gcp_costs___%'
        OR name LIKE 'stripe_costs___%'
        OR name LIKE 'aws_costs_staging___%'
        OR name IN ('aws_costs', 'gcp_costs', 'stripe_revenue', 'unified_cost_model')
    )
    ORDER BY name
    """

    result = client.query(query)
    return [row[0] for row in result.result_rows]


def drop_tables(client, tables, dry_run=False):
    """Drop tables from ClickHouse."""
    if not tables:
        print("ℹ️  No dlt tables found to drop")
        return

    print(f"\n{'DRY RUN: ' if dry_run else ''}Found {len(tables)} dlt tables:")
    for table in tables:
        print(f"  • {table}")

    if dry_run:
        print("\n⚠️  This is a dry run. No tables were dropped.")
        print("Run without --dry-run to actually drop tables.")
        return

    print(f"\n⚠️  About to DROP {len(tables)} tables!")
    response = input("Are you sure? Type 'yes' to confirm: ")

    if response.lower() != 'yes':
        print("❌ Aborted. No tables were dropped.")
        sys.exit(0)

    print("\n🗑️  Dropping tables...")
    dropped = 0
    errors = 0

    for table in tables:
        try:
            client.command(f"DROP TABLE IF EXISTS {table}")
            print(f"  ✓ Dropped {table}")
            dropped += 1
        except Exception as e:
            print(f"  ✗ Failed to drop {table}: {e}")
            errors += 1

    print(f"\n✅ Dropped {dropped} tables")
    if errors > 0:
        print(f"⚠️  {errors} errors occurred")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Clear ClickHouse tables')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    args = parser.parse_args()

    print("=" * 80)
    print("ClickHouse Table Cleanup")
    print("=" * 80)

    # Connect
    client = get_clickhouse_client()
    print("✓ Connected to ClickHouse")

    # Get tables
    tables = get_dlt_tables(client)

    # Drop tables
    drop_tables(client, tables, dry_run=args.dry_run)

    if not args.dry_run and tables:
        print("\n💡 Tip: Run 'make run-etl-clickhouse' to reload data")

    print("=" * 80)


if __name__ == "__main__":
    main()
