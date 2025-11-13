# Third-Party Attribution

## aws-cur-wizard

**Location**: `viz_rill/cur-wizard/` (formerly aws-cur-wizard)

- **Project**: aws-cur-wizard
- **Repository**: https://github.com/Twing-Data/aws-cur-wizard
- **Author**: Twing Data

### What We Use

Scripts and Jinja2 templates for dynamic AWS dashboard generation:

- **Scripts**: `normalize.py`, `generate_rill_yaml.py`, `rill_project_generator.py`, `utils/dimension_chart_selector.py`
- **Templates**: `source_template.yml.j2`, `metrics_template.yml.j2`, `overview_canvas_template.yml.j2`, `map_canvas_template.yml.j2`, `explore_template.yml.j2`

### Purpose

Automatically generates dimension-specific Rill dashboards by analyzing AWS Cost and Usage Report data. Extended to also support GCP billing exports. Used when running `make aws-dashboards` or `make gcp-dashboards`.

See `viz_rill/README.md` for integration details and `viz_rill/cur-wizard/README.md` for technical documentation.
