#!/usr/bin/env python3
"""
Initialize ClickHouse database for dlt pipelines.

This script creates the necessary database, user, and permissions
for dlt to work with ClickHouse Cloud.

Run once before first pipeline execution:
    python scripts/init_clickhouse.py
"""
import sys
import dlt
import clickhouse_connect

def init_clickhouse():
    """Initialize ClickHouse database with required permissions."""

    # Get ClickHouse connection details from secrets.toml
    try:
        host = dlt.secrets.get("destination.clickhouse.credentials.host")
        username = dlt.secrets.get("destination.clickhouse.credentials.username")
        password = dlt.secrets.get("destination.clickhouse.credentials.password")
        secure = dlt.secrets.get("destination.clickhouse.credentials.secure")
    except Exception as e:
        print(f"❌ Error reading ClickHouse credentials from .dlt/secrets.toml: {e}")
        print("\nMake sure you have configured:")
        print("[destination.clickhouse.credentials]")
        print("host = 'your-host.clickhouse.cloud'")
        print("username = 'default'")
        print("password = 'your-password'")
        print("secure = 1")
        sys.exit(1)

    print(f"Connecting to ClickHouse at {host}...")

    try:
        # Connect as admin user (usually 'default')
        client = clickhouse_connect.get_client(
            host=host,
            username=username,
            password=password,
            secure=bool(secure)
        )

        print("✅ Connected successfully")

        # Create database
        print("\n📦 Creating database 'dlt'...")
        client.command("CREATE DATABASE IF NOT EXISTS dlt")
        print("✅ Database 'dlt' created")

        # Create dlt user (optional - you can use default user)
        print("\n👤 Creating user 'dlt' (optional)...")
        try:
            client.command(
                "CREATE USER IF NOT EXISTS dlt IDENTIFIED WITH sha256_password BY 'Dlt*12345789234567'"
            )
            print("✅ User 'dlt' created")

            # Grant permissions
            print("\n🔐 Granting permissions...")
            client.command(
                "GRANT CREATE, ALTER, SELECT, DELETE, DROP, TRUNCATE, OPTIMIZE, SHOW, INSERT, dictGet ON dlt.* TO dlt"
            )
            client.command(
                "GRANT SELECT ON INFORMATION_SCHEMA.COLUMNS TO dlt"
            )
            client.command(
                "GRANT CREATE TEMPORARY TABLE, S3 ON *.* TO dlt"
            )
            print("✅ Permissions granted to user 'dlt'")

            print("\n" + "="*60)
            print("✅ ClickHouse initialization complete!")
            print("="*60)
            print("\nYou can now run pipelines with:")
            print("  DLT_DESTINATION=clickhouse make run-etl")
            print("\nOr update .dlt/secrets.toml to use the new 'dlt' user:")
            print("  [destination.clickhouse.credentials]")
            print("  username = 'dlt'")
            print("  password = 'Dlt*12345789234567'")

        except Exception as e:
            # User creation might fail on ClickHouse Cloud if not admin
            print(f"⚠️  Could not create user 'dlt': {e}")
            print("You can continue using the default admin user.")
            print("\n" + "="*60)
            print("✅ ClickHouse database 'dlt' is ready!")
            print("="*60)

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease check:")
        print("1. ClickHouse credentials in .dlt/secrets.toml")
        print("2. Network connectivity to ClickHouse Cloud")
        print("3. User has admin permissions")
        sys.exit(1)


if __name__ == "__main__":
    init_clickhouse()
