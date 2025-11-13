SELECT
 project.name,
 service.description,
 TO_JSON_STRING(project.labels) as project_labels,
 sum(cost) as total_cost,
 SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)) as total_credits
FROM `testing-bigquery-220511.billing_export.gcp_billing_export_v1_014CCF_84D5DF_A43BC0`
WHERE invoice.month = "202102"
GROUP BY 1, 2, 3
ORDER BY 1
