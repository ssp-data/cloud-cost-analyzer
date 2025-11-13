SELECT
 project.name,
 service.description,
 TO_JSON_STRING(project.labels) as project_labels,
 sum(cost) as total_cost,
 SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)) as total_credits
FROM `ctg-storage.bigquery_billing_export.gcp_billing_export_v1_01150A_B8F62B_47D999`
WHERE invoice.month = "202102"
GROUP BY 1, 2, 3
ORDER BY 1
