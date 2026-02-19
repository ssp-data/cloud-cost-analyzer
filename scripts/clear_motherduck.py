"""
Clear MotherDuck schemas for cloud cost analytics.

Drops all schemas created by dlt pipelines:
- aws_costs
- gcp_costs
- stripe_costs
- aws_costs_staging

This is safe to run - only drops schemas created by our ETL pipelines.
"""

import sys

import dlt
import duckdb


def get_motherduck_connection():
    """Get MotherDuck connection from dlt credentials."""
    try:
        token = dlt.secrets.get("destination.motherduck.credentials.password")
        database = dlt.config.get("destination.motherduck.database", str) or "cloud_cost_analytics"
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        return conn
    except Exception as e:
        print(f"Error connecting to MotherDuck: {e}")
        print("Make sure .dlt/secrets.toml has MotherDuck credentials")
        sys.exit(1)


def get_dlt_schemas(conn):
    """Get list of all dlt-created schemas."""
    target_schemas = [
        "aws_costs",
        "gcp_costs",
        "stripe_costs",
        "aws_costs_staging",
    ]
    result = conn.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
    existing = [row[0] for row in result]
    return [s for s in target_schemas if s in existing]


def drop_schemas(conn, schemas, dry_run=False):
    """Drop schemas from MotherDuck."""
    if not schemas:
        print("No dlt schemas found to drop")
        return

    print(f"\n{'DRY RUN: ' if dry_run else ''}Found {len(schemas)} dlt schemas:")
    for schema in schemas:
        print(f"  - {schema}")

    if dry_run:
        print("\nThis is a dry run. No schemas were dropped.")
        print("Run without --dry-run to actually drop schemas.")
        return

    print(f"\nAbout to DROP {len(schemas)} schemas (CASCADE)!")
    response = input("Are you sure? Type 'yes' to confirm: ")

    if response.lower() != "yes":
        print("Aborted. No schemas were dropped.")
        sys.exit(0)

    print("\nDropping schemas...")
    dropped = 0
    errors = 0

    for schema in schemas:
        try:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            print(f"  Dropped {schema}")
            dropped += 1
        except Exception as e:
            print(f"  Failed to drop {schema}: {e}")
            errors += 1

    print(f"\nDropped {dropped} schemas")
    if errors > 0:
        print(f"{errors} errors occurred")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Clear MotherDuck schemas")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("MotherDuck Schema Cleanup")
    print("=" * 80)

    conn = get_motherduck_connection()
    print("Connected to MotherDuck")

    schemas = get_dlt_schemas(conn)
    drop_schemas(conn, schemas, dry_run=args.dry_run)

    if not args.dry_run and schemas:
        print("\nTip: Run 'make run-etl-motherduck' to reload data")

    conn.close()
    print("=" * 80)


if __name__ == "__main__":
    main()
