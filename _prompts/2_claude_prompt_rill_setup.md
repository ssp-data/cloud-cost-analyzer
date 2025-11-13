


OK now that I have built in this project a extraction pipeline for cost, especially from AWS cost and GCP cost via BigQuery that I ingest via dlt-tool to DuckDB in `cloud_cost_analytics.duckdb`, as well as including revenue from Stripe (also with dbt), now the next step is to make sense out of it with Rill.



There are some templates in /home/sspaeti/git/work/cost-report-analyse/aws-cur-wizard project, where the creator exported AWS cost only and used some scripts to generate rill. see scripts and rill_project folder, but also other files (not a big repo).


how would I create a small etl pipeline, or queries firstly, that creates a great data model for analysing cost by cloud provider and product and project and region and day and see the dollar amount? use rills features to build in features such as creating a source, metrics views and dashboards + canvas, also see /home/sspaeti/git/work/cost-report-analyse/aws-cur-wizard/run.sh how he generates it. I prepared an structure of an example cost analytics project by rill in @viz_rill folder. Use that structure but replace with my data and columnd and everything that makes sense for my project.

revenue from Stripe and cost from GCP and AWS (imagine there cuuld be more added in the future such as Azure or Cloudflare etc.), theresore a simple cloud-provider dimension would make sense to see different cost from different provider.

some query and structure you see also in /home/sspaeti/git/work/cost-report-analyse/cloud-cost-analyzer/tests/test_duplicates.sql to test duplicates. unfortunately the gcp_costs data is not there yet, because the export doesn't hold data yet, but you can find the schema here: https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/detailed-usage


how would we savely create a data model that joins the multiple table into a simple star schema with dimensions and facts. start simple, we can always make it more complex. IF there's anything unclear, please prompt me to ask.



Please create a rill data model that is working with `cd viz_rill` and start with `rill start --no-ui` -> you can test if it works or there are still error. Again keep it simple to start -> so it's easier to debug.

PS: for additional information, check @Makefile and it's starting pipelines and what they are doing and what data we are getting.

