#!/usr/bin/env python3
"""
Generate enhanced demo data for Cloud Cost Analyzer
Creates additional parquet files with realistic costs and revenue for demo purposes
"""

import duckdb
from pathlib import Path
from datetime import datetime, timedelta
import random

# Configuration
DATA_DEMO_DIR = Path("viz_rill/data_demo")
OUTPUT_SUFFIX = "_demo"  # Suffix for demo files

# Demo data parameters
MONTHS_HISTORY = 4  # Generate 4 months of historical data
AWS_MONTHLY_COST_RANGE = (5000, 8000)  # $5K-8K per month
GCP_MONTHLY_COST_RANGE = (2000, 4000)  # $2K-4K per month
STRIPE_MONTHLY_REVENUE_RANGE = (15000, 25000)  # $15K-25K per month

# Date ranges
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=MONTHS_HISTORY * 30)

def generate_aws_demo_data():
    """Generate enhanced AWS cost data"""
    print(f"Generating AWS demo data...")

    con = duckdb.connect()

    # Read existing AWS data to understand schema
    existing_data = con.execute("""
        SELECT * FROM read_parquet('viz_rill/data_demo/aws_costs/cur_export_test_00001/*.parquet')
        WHERE line_item_unblended_cost > 0
        LIMIT 100
    """).fetchdf()

    if existing_data.empty:
        print("No AWS data found to use as template")
        return

    # AWS services to generate (with realistic distribution)
    services = [
        ('AmazonEC2', 0.35),  # 35% of cost
        ('AmazonRDS', 0.25),  # 25% of cost
        ('AmazonS3', 0.15),   # 15% of cost
        ('AWSLambda', 0.10),  # 10% of cost
        ('AmazonCloudWatch', 0.05),  # 5% of cost
        ('AmazonVPC', 0.05),  # 5% of cost
        ('AWSGlue', 0.05),    # 5% of cost
    ]

    regions = ['us-east-1', 'us-west-2', 'eu-central-1', 'ap-southeast-1']

    demo_records = []

    # Generate data for each month
    current_date = START_DATE
    while current_date < END_DATE:
        month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (month_start + timedelta(days=32)).replace(day=1)

        # Random monthly cost within range
        monthly_cost = random.uniform(*AWS_MONTHLY_COST_RANGE)

        time_interval = f"{month_start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{next_month.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        for service, percentage in services:
            service_cost = monthly_cost * percentage

            # Create multiple line items for this service
            num_items = random.randint(10, 30)
            for i in range(num_items):
                # Use existing record as template
                template = existing_data.sample(1).iloc[0].to_dict()

                # Modify key fields
                template['identity_time_interval'] = time_interval
                template['identity_line_item_id'] = f"demo_{month_start.strftime('%Y%m')}{service}_{i}_{random.randint(1000,9999)}"
                template['line_item_product_code'] = service
                template['line_item_unblended_cost'] = service_cost / num_items
                template['line_item_blended_cost'] = service_cost / num_items
                template['product_region_code'] = random.choice(regions)
                template['bill_billing_period_start_date'] = month_start
                template['bill_billing_period_end_date'] = next_month
                template['_dlt_load_id'] = f"demo_{month_start.strftime('%Y%m')}"
                template['_dlt_id'] = f"demo_{i}_{random.randint(10000,99999)}"

                demo_records.append(template)

        current_date = next_month

    # Create DataFrame and save
    import pandas as pd
    df = pd.DataFrame(demo_records)

    # Save directly to the main directory so Rill can find it
    output_dir = DATA_DEMO_DIR / "aws_costs" / "cur_export_test_00001"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"demo_data_{datetime.now().strftime('%Y%m%d')}.parquet"
    df.to_parquet(output_file, index=False)

    print(f"✅ Generated {len(demo_records)} AWS demo records")
    print(f"   Total demo cost: ${df['line_item_unblended_cost'].sum():,.2f}")
    print(f"   Saved to: {output_file}")

    con.close()


def generate_gcp_demo_data():
    """Generate enhanced GCP cost data"""
    print(f"\nGenerating GCP demo data...")

    con = duckdb.connect()

    # Read existing GCP data
    existing_data = con.execute("""
        SELECT * FROM read_parquet('viz_rill/data_demo/gcp_costs/bigquery_billing_table/*.parquet')
        WHERE cost > 0
        LIMIT 100
    """).fetchdf()

    if existing_data.empty:
        print("No GCP data found to use as template")
        return

    # GCP services to generate
    services = [
        ('Compute Engine', 0.40),
        ('Cloud Storage', 0.20),
        ('BigQuery', 0.15),
        ('Cloud SQL', 0.15),
        ('Cloud Functions', 0.10),
    ]

    projects = ['production-main', 'staging-env', 'analytics-pipeline']

    demo_records = []

    # Generate daily data for each month
    current_date = START_DATE
    while current_date < END_DATE:
        month_start = current_date.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)

        monthly_cost = random.uniform(*GCP_MONTHLY_COST_RANGE)
        days_in_month = (next_month - month_start).days
        daily_cost = monthly_cost / days_in_month

        # Generate for each day in the month
        day = month_start
        while day < next_month:
            for service, percentage in services:
                service_daily_cost = daily_cost * percentage

                # Create multiple records per service per day
                num_records = random.randint(5, 15)
                for i in range(num_records):
                    template = existing_data.sample(1).iloc[0].to_dict()

                    template['export_time'] = day + timedelta(hours=random.randint(0, 23))
                    template['service__description'] = service
                    template['cost'] = service_daily_cost / num_records
                    template['project__name'] = random.choice(projects)
                    template['usage__amount'] = random.uniform(100, 10000)
                    template['_dlt_load_id'] = f"demo_{day.strftime('%Y%m%d')}"
                    template['_dlt_id'] = f"demo_gcp_{i}_{random.randint(10000,99999)}"

                    demo_records.append(template)

            day += timedelta(days=1)

        current_date = next_month

    # Save
    import pandas as pd
    df = pd.DataFrame(demo_records)

    # Save directly to the main directory so Rill can find it
    output_dir = DATA_DEMO_DIR / "gcp_costs" / "bigquery_billing_table"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"demo_data_{datetime.now().strftime('%Y%m%d')}.parquet"
    df.to_parquet(output_file, index=False)

    print(f"✅ Generated {len(demo_records)} GCP demo records")
    print(f"   Total demo cost: ${df['cost'].sum():,.2f}")
    print(f"   Saved to: {output_file}")

    con.close()


def generate_stripe_demo_data():
    """Generate enhanced Stripe revenue data"""
    print(f"\nGenerating Stripe demo data...")

    con = duckdb.connect()

    # Read existing Stripe data
    existing_data = con.execute("""
        SELECT * FROM read_parquet('viz_rill/data_demo/stripe_costs/balance_transaction/*.parquet')
        WHERE amount > 0
        LIMIT 100
    """).fetchdf()

    if existing_data.empty:
        print("No Stripe data found to use as template")
        return

    # Transaction types with amounts
    transaction_types = [
        ('Subscription update', 49.99, 95),    # $49.99 (95% of transactions)
        ('One-time payment', 99.99, 3),        # $99.99 (3%)
        ('Annual subscription', 499.99, 2),    # $499.99 (2%)
    ]

    demo_records = []

    # Generate daily transactions for each month
    current_date = START_DATE
    while current_date < END_DATE:
        month_start = current_date.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)

        monthly_revenue = random.uniform(*STRIPE_MONTHLY_REVENUE_RANGE)
        days_in_month = (next_month - month_start).days
        daily_revenue_target = monthly_revenue / days_in_month

        # Generate for each day
        day = month_start
        while day < next_month:
            daily_revenue = 0

            # Generate transactions until we hit daily target
            while daily_revenue < daily_revenue_target:
                # Pick transaction type based on distribution
                rand = random.random() * 100
                cumulative = 0
                for description, base_amount, percentage in transaction_types:
                    cumulative += percentage
                    if rand < cumulative:
                        amount = int(base_amount * 100)  # Convert to cents
                        fee = int(amount * 0.029 + 30)   # Stripe fee: 2.9% + $0.30
                        net = amount - fee

                        template = existing_data.sample(1).iloc[0].to_dict()

                        # Generate timestamp for this day
                        timestamp = int((day + timedelta(
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59)
                        )).timestamp())

                        template['created'] = timestamp
                        template['amount'] = amount
                        template['net'] = net
                        template['fee'] = fee
                        template['description'] = description
                        template['reporting_category'] = 'charge'
                        template['type'] = 'charge'
                        template['_dlt_load_id'] = f"demo_{day.strftime('%Y%m%d')}"
                        template['_dlt_id'] = f"demo_stripe_{random.randint(100000,999999)}"

                        demo_records.append(template)
                        daily_revenue += base_amount
                        break

            day += timedelta(days=1)

        current_date = next_month

    # Save
    import pandas as pd
    df = pd.DataFrame(demo_records)

    # Save directly to the main directory so Rill can find it
    output_dir = DATA_DEMO_DIR / "stripe_costs" / "balance_transaction"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"demo_data_{datetime.now().strftime('%Y%m%d')}.parquet"
    df.to_parquet(output_file, index=False)

    print(f"✅ Generated {len(demo_records)} Stripe demo records")
    print(f"   Total demo revenue: ${df['amount'].sum()/100:,.2f}")
    print(f"   Total demo net: ${df['net'].sum()/100:,.2f}")
    print(f"   Saved to: {output_file}")

    con.close()


def main():
    print("="*80)
    print("Generating Enhanced Demo Data for Cloud Cost Analyzer")
    print("="*80)
    print(f"\nDate range: {START_DATE.date()} to {END_DATE.date()}")
    print(f"Months of history: {MONTHS_HISTORY}")
    print()

    try:
        generate_aws_demo_data()
        generate_gcp_demo_data()
        generate_stripe_demo_data()

        print("\n" + "="*80)
        print("✅ Demo data generation complete!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Run 'make demo' to copy data and start Rill")
        print("  2. Check the dashboards at http://localhost:9009")
        print("\nNote: Demo files are marked with '_demo' suffix to distinguish from real data")

    except Exception as e:
        print(f"\n❌ Error generating demo data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
