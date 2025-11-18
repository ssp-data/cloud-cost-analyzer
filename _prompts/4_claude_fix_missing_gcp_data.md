
> I'm missing data from GCP e.g. category cloud sql or compute engine. i have clear data, or restarted the run (see make in @Makefile ). Is thta because the gcp-normalize python scripts do not hold all categories, or is the data missing? check the downloaded data in viz_rill/data/gcp_cost folder, you can directly
  query them with duckdb to check

  if i run @helper_sqls/gcp_breakdown_project_product.sql on bigquery, i get actual data:
  Row    name    description    project_labels    total_cost    total_credits
  1    real-estate    Cloud Storage    []    0.002028    0.0
  2    real-estate    BigQuery    []    0.0    0.0
  3    real-estate    Cloud Logging    []    0.0    0.0
  4    siroop    Cloud Storage    []    2.5e-05    0.0
  5    testing BigQuery    reCAPTCHA Enterprise    []    0.0    0.0
  6    testing BigQuery    Cloud Logging    []    0.0    0.0
  7    testing BigQuery    BigQuery    []    0.58233899999999994    0.0
  8    testing BigQuery    Cloud Storage    []    0.264324    0.0
  9    testing BigQuery    Vertex AI    []    0.008181    0.0
  10    testing BigQuery    Networking    []    0.011948    -0.011948
  11    testing BigQuery    BigQuery Reservation API    []    0.406612    0.0
  12    testing BigQuery    Compute Engine    []    11.040309999999998    0.0
  13    testing BigQuery    Deep Learning VM    []    0.0    0.0
  14    testing BigQuery    Cloud SQL    []    21.680359000000021


When I go into the dashboard @viz_rill/dashboards/gcp_overview.yaml or @viz_rill/dashboards/gcp_product_insights.yaml or also in @viz_rill/dashboards/cloud_cost_explore.yaml i don't see the GCP cost recently added. e.g. in prouct_insight i only see bigquery and cloudlogger, why is this?

note, that i have created these dashboards when there was no data yet. so there might a missing category or filter somewhere. 

Can you search where the missing piece between the parquet files are and the not showing up in the dashboard?
