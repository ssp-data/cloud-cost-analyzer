# Attribution & Third-Party Components

This project incorporates open-source components from other projects. This document provides full attribution and license information.

## aws-cur-wizard Integration

**Location**: `viz_rill/aws-cur-wizard/`

### Source Information

- **Project**: aws-cur-wizard
- **Repository**: https://github.com/Twing-Data/aws-cur-wizard
- **Author**: Rill Data / Twing Data
- **License**: MIT License

### Components Used

We have integrated the following components from aws-cur-wizard:

#### Scripts (`viz_rill/aws-cur-wizard/scripts/`)

1. **`normalize.py`** - Normalizes and flattens AWS CUR parquet files
2. **`generate_rill_yaml.py`** - CLI wrapper for dashboard generation
3. **`rill_project_generator.py`** - Core library for generating Rill project files
4. **`utils/dimension_chart_selector.py`** - Algorithm for intelligent chart selection based on data characteristics

#### Templates (`viz_rill/aws-cur-wizard/templates/`)

1. **`source_template.yml.j2`** - Jinja2 template for Rill source configuration
2. **`metrics_template.yml.j2`** - Template for metrics views with conditional measures
3. **`overview_canvas_template.yml.j2`** - Template for overview dashboard
4. **`map_canvas_template.yml.j2`** - Template for dimension-specific canvases
5. **`explore_template.yml.j2`** - Template for explore views

### Modifications

All scripts and templates are used **as-is** from the original project with only minor path adjustments:
- Input/output paths adapted to match our project structure
- ENV variable handling adjusted for local `.env` file

**No modifications** were made to:
- Core normalization logic
- Chart selection algorithm
- Template rendering logic
- Business logic or analytics patterns

### License Text

```
MIT License

Copyright (c) Twing Data / Rill Data

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### What We Built On Top

While we use aws-cur-wizard's scripts and templates directly, we created:

1. **Static AWS Dashboards** (`viz_rill/dashboards/`) - Inspired by aws-cur-wizard patterns but customized:
   - `aws_overview.yaml` - Advanced cost analytics canvas
   - `aws_explore.yaml` - Interactive explorer
   - `aws_product_insights.yaml` - Product dimension analysis

2. **Multi-Cloud Integration** - Extended beyond AWS to include:
   - GCP billing data support
   - Stripe revenue integration
   - Unified cost model across providers

3. **Custom Data Pipeline** - Built with dlt:
   - `pipelines/aws_pipeline.py` - AWS CUR data ingestion
   - `pipelines/google_bq_incremental_pipeline.py` - GCP billing ingestion
   - `pipelines/stripe_pipeline.py` - Stripe revenue ingestion

## Other Dependencies

This project also uses:

- **dlt (data load tool)** - Data ingestion framework (Apache 2.0 License)
- **DuckDB** - In-memory analytical database (MIT License)
- **Rill** - Data visualization platform (Apache 2.0 License)
- **Python packages** - See `pyproject.toml` for complete list

## Acknowledgements

Special thanks to:

- **Rill Data team** for creating aws-cur-wizard and open-sourcing their AWS cost analysis patterns
- **dlt team** for the excellent data ingestion framework
- **DuckDB team** for the fast analytical database

## Questions?

For questions about:
- **aws-cur-wizard components**: See their [GitHub repository](https://github.com/Twing-Data/aws-cur-wizard)
- **This project**: Open an issue in this repository

---

Last updated: 2025-11-13
