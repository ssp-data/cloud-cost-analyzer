
what steps would I need to take to run this project on github actions and use ClickHouse Cloud as my fast real-time database ingesting Parquet files into Clickhouse directly with append.

1. use github actions as our cron job to run etl part (see Makefile, `run-etl aws-normalize gcp-normalize`) there.
2. can we use dlt destination ClickHouse to ingest directcly over the network? Or (my guess), better to run above commands on GH instances and generate parquet files locally (as append shouldn't get too big) and then ingest it into Clickhouse with a seperate job? or can we ingest data with dlt directly (would make logic easier potentially)  - Check docs on dlt : https://dlthub.com/docs/dlt-ecosystem/destinations/clickhouse and for clickhouse/dlt: https://clickhouse.com/docs/integrations/data-ingestion/etl-tools/dlt-and-clickhouse
3. Clickhouse has ClickPipes with these sources:

Search data sources

Cloud object stores
Amazon S3
Google Cloud Storage
DigitalOcean Spaces
Azure Blob Storage

Databases, data lakehouses
Postgres CDC
MySQL CDC
Beta
MariaDB CDC
Beta
MongoDB CDC
Beta

Event streams
Amazon MSK
Amazon Kinesis
Apache Kafka
Confluent Cloud
Azure Event Hubs
Redpanda
WarpStream
DigitalOcean Kafka


3.1 what's the best option to ingest into clickhouse from GitHub Actions?
3.2 there is also "Connect to My first service" 

Get started by creating a high-powered serverless ClickHouse database in minutes.
default

Username
•••••••••••••
Password

Connect with:

HTTPS -> which also has python or native and others. is that a way to use dlt?
Run the following command from your terminal:

curl --user 'default:•••••••••••••' \
  --data-binary 'SELECT 1' \
  https://xxxxx.europe-west4.gcp.clickhouse.cloud:8443
Visit the documentation to learn how to use the HTTP Interface

for native it says:
Installation
Run the following command in your terminal to install it on Linux, macOS, or FreeBSD.
Or check out all the installation options


curl https://clickhouse.com/ | sh
Connection

clickhouse client --host vvfohxqvoa.europe-west4.gcp.clickhouse.cloud --secure --password '•••••••••••••'

or with python:
Installation

pip install clickhouse-connect
Usage

import clickhouse_connect

if __name__ == '__main__':
    client = clickhouse_connect.get_client(
        host='XXXX.europe-west4.gcp.clickhouse.cloud',
        user='default',
        password='•••••••••••••',
        secure=True
    )
    print("Result:", client.query("SELECT 1").result_set[0][0])

3.3 based on the documentations, which one should i use?
4. also we use rill cloud to run Rill at the end, it can run from a github repo, so hopefully that should be straight forward.
