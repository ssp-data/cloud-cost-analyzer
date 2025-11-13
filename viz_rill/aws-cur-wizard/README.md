# aws-cur-wizard Integration

This directory contains scripts and templates from the [aws-cur-wizard](https://github.com/Twing-Data/aws-cur-wizard) project, used to generate sophisticated AWS cost analysis dashboards.

## Source

**Original Project**: https://github.com/Twing-Data/aws-cur-wizard
**License**: MIT License
**Author**: Rill Data / Twing Data

## What's Included

### Scripts (`scripts/`)

These Python scripts handle data normalization and dynamic dashboard generation:

- **`normalize.py`** - Normalizes AWS CUR parquet files, flattens nested MAP columns
- **`generate_rill_yaml.py`** - CLI wrapper for dashboard generation
- **`rill_project_generator.py`** - Core library for generating Rill YAML files
- **`utils/dimension_chart_selector.py`** - Intelligent algorithm for chart selection

### Templates (`templates/`)

Jinja2 templates used to dynamically generate Rill dashboards:

- **`source_template.yml.j2`** - Source configuration template
- **`metrics_template.yml.j2`** - Metrics view template with conditional measures
- **`overview_canvas_template.yml.j2`** - Advanced overview dashboard template
- **`map_canvas_template.yml.j2`** - Dynamic dimension-specific canvas template
- **`explore_template.yml.j2`** - Explore view template

## Usage

These scripts are invoked via the project Makefile:

```bash
# Normalize AWS CUR data
make aws-normalize

# Generate dynamic dashboards
make aws-generate-dashboards

# Full workflow
make aws-dashboards

# List available cost columns
make aws-list-cost-cols
```

## How It Works

1. **Normalization** (`normalize.py`):
   - Reads all parquet files from `viz_rill/data/aws_costs/cur_export_test_00001/`
   - Uses DuckDB's `UNION_BY_NAME` to handle schema evolution
   - Flattens any nested MAP columns (e.g., resource tags)
   - Outputs `viz_rill/data/normalized_aws.parquet`

2. **Dashboard Generation** (`generate_rill_yaml.py`):
   - Analyzes the normalized parquet schema
   - Uses `dimension_chart_selector.py` to determine best visualizations
   - Renders Jinja2 templates with discovered schema
   - Creates:
     - `sources/aws_cost_source.yaml` - Data source
     - `metrics/aws_cost_metrics.yaml` - Metrics view
     - `canvases/aws_cost_overview_canvas.yml` - Overview dashboard
     - `canvases/aws_cost_*_canvas.yml` - Dimension-specific dashboards
     - `explores/aws_cost_explore.yml` - Interactive explorer

## Key Algorithm: Dimension Chart Selector

From `utils/dimension_chart_selector.py`:

### Algorithm Overview

1. **Candidate Discovery** - Finds columns matching user-specified prefixes
   ```
   Example: --dim-prefixes "product_,line_item_"
   Discovers: product_product_family, product_region_code, line_item_usage_type, etc.
   ```

2. **Qualification** - Only includes dimensions meeting criteria:
   - ≥5% of total spend on non-NULL rows (cost coverage)
   - >2 distinct values (cardinality)

3. **Dominant Slice Peeling** - Identifies values representing ≥70% of spend:
   ```python
   # Example: If "us-east-1" accounts for 85% of spend:
   # → Create KPI for "us-east-1"
   # → Chart the remaining 15% across other regions
   ```

4. **Chart Selection** - Picks optimal chart type by cardinality:
   - ≤10 distinct values → Pie chart
   - 11-40 values → Bar chart
   - >40 values → Leaderboard

5. **Layout Generation** - Creates hybrid layouts:
   - `kpi+pie` - KPI for dominant value + pie chart for others
   - `leaderboard+pie` - Leaderboard for top values + pie for remainder
   - `single` - Just one chart (no dominant slices)
   - `kpi` - KPI only (one value dominates everything)
   - `leaderboard` - Leaderboard only (many dominant values)

## Modifications for This Project

While most code is copied 1:1, we made minor path adjustments:

- **Input paths**: Adapted to read from `viz_rill/data/aws_costs/cur_export_test_00001/`
- **Output paths**: Generate files directly in `viz_rill/` directories
- **ENV configuration**: Use local `.env` file instead of requiring export

All core logic (normalization, chart selection, template rendering) is **unchanged** from the original project.

## Generated vs Static Files

This project uses a **hybrid approach**:

### Generated Files (ignored in git)
Created dynamically by running `make aws-dashboards`:
- `canvases/*` - Dynamic dimension canvases
- `explores/*` - Interactive explorers
- `data/normalized_aws.parquet` - Normalized data

### Static Files (committed to git)
Manually created, inspired by aws-cur-wizard patterns:
- `sources/aws_cost_normalized.yaml` - Our custom source
- `metrics/aws_cost_metrics.yaml` - Our custom metrics (20+ measures)
- `dashboards/aws_overview.yaml` - Our static overview canvas
- `dashboards/aws_explore.yaml` - Our static explorer
- `dashboards/aws_product_insights.yaml` - Our product analysis canvas

**Why both?**
- **Static**: Fast loading, version controlled, customized for our multi-cloud setup
- **Dynamic**: Adapts to schema changes, handles resource tags elegantly

## License

The scripts and templates in this directory are from the aws-cur-wizard project:

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

## Credits

**Original Authors**: Rill Data team
**Repository**: https://github.com/Twing-Data/aws-cur-wizard
**Integrated by**: This project with gratitude and full attribution

Thank you to the Rill team for open-sourcing these excellent AWS cost analysis patterns! 🙏
