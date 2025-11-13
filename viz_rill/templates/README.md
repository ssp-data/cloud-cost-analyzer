# Templates Directory

This directory is **empty** because all Jinja2 templates have been moved to:

**`../aws-cur-wizard/templates/`**

## Original Source

All templates in `../aws-cur-wizard/templates/` are from:

**Project**: https://github.com/Twing-Data/aws-cur-wizard
**License**: MIT License
**Files**:
- `source_template.yml.j2`
- `metrics_template.yml.j2`
- `overview_canvas_template.yml.j2`
- `map_canvas_template.yml.j2`
- `explore_template.yml.j2`

## Usage

These templates are used by the aws-cur-wizard scripts to dynamically generate Rill dashboards:

```bash
make aws-dashboards  # Renders templates → generates YAML files
```

## Attribution

Full credit to the Rill Data team for these excellent templates!

See `../aws-cur-wizard/README.md` for complete attribution and license details.
