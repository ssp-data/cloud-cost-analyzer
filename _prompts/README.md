here I keep some claude prompts I used to gerenate for example the Rill dashboard. Important note, see I always prompt based on existing table structure and actual data, I created a Rill Template on purpose, so Claude can learn and see how it works and optimize on top of it. I gave it actual access to the database (duckdb) to verify queries and even tell how to run the BI tool and verify if it's correct.

This is not using MCP or anything, but because everything is local, and code first with a declarative data stack, all configuration, all definition, all code, everything is in this single repo, even the data as it's just a duckdb database.

I try to commit the claude code response in one commit, so you can see what it created, and then I can optimize on top of this.


Also check helper SQLs for @helper_sqls GCP to get product and cost analysis.
also be aware that I copied cloud_cost-analytics.duckdb into `viz_rill` folder, so Rill has access (otherwise one level up it can't) -> i'll fix this logistics later, you can ignore the duplicated duckdb and just use the one insize viz_rill.
