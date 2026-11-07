# NEMO Monitors

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Plugin for [NEMO](https://github.com/usnistgov/NEMO) (and NEMO-CE) that lets facilities attach **monitor data** to tools: time-series readings, optional notes, charts, exports, and email alerts. The UI follows the same patterns as the NEMO **Sensors** plugin (category dashboard, tool listing, detail tabs).

Requires **NEMO or NEMO-CE ≥ 7.3.0** and **Python ≥ 3.10**.

## Features

### Dashboard and navigation

- **Monitors dashboard** at `/monitors/` lists tools that have visible monitors, grouped by NEMO **tool category** (browse subcategories at `/monitors/category/<path>/`).
- Recent **alert log** entries appear on the dashboard and per-tool pages; categories and tools can show when an alert is active.
- **Per-tool page** (`/monitors/tool/<tool_id>/`) lists that tool’s monitors with last value and last read time.

### Monitor definitions

- Each **monitor** belongs to one tool: name, visibility, and optional **description** (HTML allowed; bare domains in links are normalized to `https://`).
- **Staff** users can create, edit, and delete monitors from the web UI (`/monitor/create/<tool_id>/`, `/monitor/<id>/edit/`, `/monitor/<id>/delete/`). The same models are available in **Django admin** (duplicate monitor, show/hide bulk actions, inline **data entry fields**).
- **Data entry fields** (`MonitorColumn`) define what is collected per timestamp: name, type (`float`, `integer`, `string`), display order, and optional **per-field unit label** for chart axes. New monitors default to **Value** (float) and **Notes** (string); fields can be added, renamed, reordered, or removed. Removing a field that still has data **unlinks** those rows (column set to null) and shows a warning.

Monitors with **no** data entry fields use the older **single numeric value** model (one `MonitorData` row per timestamp, optional `notes` on the row).

### Data entry and charts

- **Chart**, **Data**, **Alert**, and **Upload** tabs on each monitor (`/monitor_details/<id>/` and `/monitor_details/<id>/<tab>/`).
- **Chart.js** time-series charts with a configurable date range (site customization). Multi-field monitors plot each numeric field as its own series; string fields appear in the data table but not on the chart.
- **Data tab**: sortable table with inline edit/delete for users with upload permission.
- **Upload tab**: single-point form and CSV upload (file or paste).
- **Quick add** on the per-tool page (AJAX) when the user has upload permission.
- **Upload hub** (`/monitors/upload/`) to jump to any monitor’s upload tab.
- **Export** filtered data as CSV (`/export_monitor_data/<monitor_id>/`).

Each data point stores **measurement time** (`created_date`, editable), **upload time** (`created_on`), **created_by** / **updated_by**, and value(s) per column.

### Control limits (chart display)

On monitors with **data entry fields**, staff can enable optional control-limit lines per **numeric** field (float or integer) when creating or editing the monitor. Limits are drawn on the chart only; they do **not** trigger email alerts, change alarm state, or appear in the alert log. Alerting uses separate **email alert** rules on the Alerts tab.

| Mode | Behavior |
|------|----------|
| **None** (default) | No limit lines. |
| **3σ (statistical)** | **Centerline** = mean of numeric points in the chart’s current date range. **UCL** and **LCL** = mean ± 3× sample standard deviation (`statistics.stdev`). Requires at least **two** numeric points in that range; otherwise no lines are shown. If all values are identical, UCL, centerline, and LCL coincide. |
| **Fixed** | Horizontal **LCL** and/or **UCL** from staff-defined minimum and/or maximum values (at least one required). No centerline. These values do not change when the date range changes. |

**Date range:** Statistical limits are recomputed from whatever data is loaded for the chart—i.e. the same **start/end** filter as the series (site default range or the range the user selects). Changing the range can move or hide statistical lines. Fixed limits are constant regardless of range.

**Chart appearance:** Limit lines are dashed (centerline gray, UCL orange, LCL blue) and follow the visibility of their data series. String fields cannot have control limits.

Legacy monitors (single numeric value, no data entry fields) do not support per-field control limits.

### Alerts

- **Email alerts** (`MonitorAlertEmail`) per monitor and optional **data entry field**: trigger on a boolean **condition** (variable `value`, e.g. `value > 42`), on **no data** for that field, or both. **Staff** configure rules on each monitor’s **Alerts** tab (also Django admin and REST API `/api/monitors/monitor_alert_emails/`).
- Recipients are set **per alert** (comma-separated emails on each rule).
- Alerts fire and reset when matching data is saved (`post_save` on `MonitorData`, including after multi-field `bulk_create`).
- **Alert log** on each monitor’s **Alerts** tab; Django admin and REST API for logs. Category dashboard tiles do not aggregate alert history.
- Live alarm state (`triggered_on`, red monitor rows) clears only when new data satisfies the alert rule or relevant data is removed—not via the log UI.

### REST API

When `NEMO_monitors` is in `INSTALLED_APPS`, `NEMO_monitors/urls.py` registers these view sets on NEMO’s shared DRF router (same mechanism as `tools`, `reservations`, etc.). They are served under the site’s **`/api/`** prefix (trailing slash required), not under the web UI `/monitors/` paths.

| Path | Model / resource | Access |
|------|------------------|--------|
| `/api/monitors/monitors/` | `Monitor` | read/write; expand columns with `?expand=columns` |
| `/api/monitors/monitor_columns/` | `MonitorColumn` | read-only (field definitions: name, type, order, unit) |
| `/api/monitors/readings/` | Name-keyed sample | read/write (see below) |
| `/api/monitors/monitor_alert_emails/` | `MonitorAlertEmail` | read/write |
| `/api/monitors/monitor_alert_logs/` | `MonitorAlertLog` | read-only; list export as `.xlsx` via `?format=xlsx` (same as other NEMO APIs) |

Filters and authentication follow the same patterns as other NEMO model APIs.

#### Readings (`/api/monitors/readings/`)

Post one logical sample as a map of **field name → value**. Key order does not matter; names are matched case-insensitively (optional trailing unit in parentheses, same as CSV upload). Each non-blank field creates one `MonitorData` row.

```json
POST /api/monitors/readings/
{
  "monitor": 11,
  "created_date": "2026-11-07T18:15:00",
  "fields": {
    "Notes": "swapped cylinder",
    "Cylinder ID": "HF-204",
    "Weight Remaining": 12.4
  }
}
```

`created_date` is optional (defaults to now). The response echoes `fields` and an `ids` map of field name → created `MonitorData` primary key. A JSON list of the same objects is accepted for bulk create.

`GET /api/monitors/readings/?monitor=11` returns samples grouped by `created_date` (newest first). The `monitor` query parameter is required. Optional `created_date`, `created_date__gte`, `created_date__lte`, `created_date__gt`, and `created_date__lt` filters are supported.

Monitors with **no** data entry fields use legacy shape on the same endpoint: `{"monitor": 11, "value": 42.5, "notes": "optional"}` (response includes a single `id`).

### Site customization

Under NEMO **Customization → Monitor data** (`monitors`):

- **Default date range** — last 24 hours, 72 hours, week, month, or year on chart/data views.

## Installation

```bash
pip install NEMO-monitors
```

In `settings.py`, add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "...",
    "NEMO_monitors.apps.MonitorsConfig",
    "...",
]
```

Run migrations (app label `monitors`):

```bash
python manage.py migrate monitors
```

Optional extras when installing from source:

```bash
pip install ".[NEMO]"      # or ".[NEMO-CE]"
```

### Docker (official NEMO image)

Production Docker installs mount your runtime directory (including `settings.py`) at `/nemo/`. On each container start, NEMO runs [`start_NEMO_in_Docker.sh`](https://github.com/usnistgov/NEMO/blob/master/start_NEMO_in_Docker.sh), which can `pip install` extra packages before `collectstatic`, `migrate`, and gunicorn.

**1. Enable the app in `settings.py`**

Edit the `settings.py` you mount into the container (for example `./nemo/settings.py` on the host) and add the app config to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "...",
    "NEMO_monitors.apps.MonitorsConfig",
    "...",
]
```

**2. Install the package at container start**

Set the `NEMO_EXTRA_PIP_PACKAGES` environment variable so `start_NEMO_in_Docker.sh` installs this plugin when the container starts. The PyPI package name is `NEMO-monitors` (hyphen).

`docker run` example:

```bash
docker run --detach \
  --publish 8000:8000 \
  --volume /path/to/nemo:/nemo \
  -e NEMO_EXTRA_PIP_PACKAGES="NEMO-monitors" \
  nanofab/nemo:7.4.1
```

`docker-compose.yml` example:

```yaml
services:
  nemo:
    image: nanofab/nemo:7.4.1
    volumes:
      - ./nemo:/nemo
    environment:
      NEMO_EXTRA_PIP_PACKAGES: "NEMO-monitors"
```

Pin a version if you want reproducible installs, for example `NEMO-monitors==1.0.2`. To install from a local wheel or VCS URL instead of PyPI, put that spec in `NEMO_EXTRA_PIP_PACKAGES` the same way you would for any other pip requirement.

You do not need to edit `start_NEMO_in_Docker.sh` in the image for a normal install; `NEMO_EXTRA_PIP_PACKAGES` is the supported hook. If your site maintains a custom startup script (sometimes named `START_NEMO.sh` or a fork of `start_NEMO_in_Docker.sh`), you can instead add `python3 -m pip install NEMO-monitors` before `collectstatic` / `migrate`, but prefer the env var when using the stock NEMO image. After the container starts, `django-admin migrate` in that script applies the `monitors` migrations automatically. Restart the container after changing `settings.py` or the pip-install configuration.

See also the [NEMO Docker installation wiki](https://github.com/usnistgov/NEMO/wiki/Installation-with-Docker).

## Permissions

| Capability | Who |
|------------|-----|
| View dashboard, charts, data, alert logs | Any authenticated user |
| Add, edit, delete **data points**; CSV upload; upload hub; quick add | Users/groups with **`monitors.upload_monitor_data`** (“Can upload monitor data”) |
| Configure **email alerts** on a monitor | **Staff** (`is_staff`) on the monitor **Alerts** tab |
| Create, edit, delete **monitor definitions** and data entry fields | **Staff** (`is_staff`) via web UI or Django admin |

Assign `upload_monitor_data` in Django admin under Auth → Users / Groups → Permissions.

## URLs

Paths are relative to your NEMO site root.

| Purpose | Path |
|--------|------|
| Monitors dashboard | `/monitors/` |
| Dashboard by tool category | `/monitors/category/<category_path>/` |
| Monitors for one tool | `/monitors/tool/<tool_id>/` |
| Upload hub | `/monitors/upload/` |
| Monitor detail (default: chart) | `/monitor_details/<monitor_id>/` |
| Chart / data / alert / upload tab | `/monitor_details/<monitor_id>/chart/`, `.../data/`, `.../alert/`, `.../upload/` |
| Chart/table JSON | `/monitor_chart_data/<monitor_id>/` |
| Alert log (partial HTML) | `/monitor_alert_log/<monitor_id>/` |
| Save email alert (staff) | `/monitor/<monitor_id>/alert/save/`, `/monitor/<monitor_id>/alert/<alert_id>/save/` |
| Delete email alert (staff) | `/monitor/<monitor_id>/alert/<alert_id>/delete/` |
| Export CSV | `/export_monitor_data/<monitor_id>/` |
| Add data point | `/monitor/<monitor_id>/data/add/` |
| Upload CSV | `/monitor/<monitor_id>/data/upload_csv/` |
| Edit / delete data point | `/monitor/<monitor_id>/data/<data_id>/edit/`, `.../delete/` |
| Create monitor (staff) | `/monitor/create/<tool_id>/` |
| Edit / delete monitor (staff) | `/monitor/<monitor_id>/edit/`, `/monitor/<monitor_id>/delete/` |
| REST: monitors | `/api/monitors/monitors/` |
| REST: monitor columns (read-only) | `/api/monitors/monitor_columns/` |
| REST: readings (name-keyed samples) | `/api/monitors/readings/` |
| REST: alert email rules | `/api/monitors/monitor_alert_emails/` |
| REST: alert log (read-only) | `/api/monitors/monitor_alert_logs/` |

## CSV upload formats

### Legacy monitors (no data entry fields)

Two or three columns per row, optional header skipped if it does not look like data:

```text
timestamp,value
2024-01-15 10:00:00,42.5
2024-01-15 11:00:00,43.0,optional notes column
```

Timestamps are parsed flexibly (ISO-like strings and common US formats).

### Monitors with data entry fields

First row is a **header**. First column is the timestamp; remaining columns map to defined fields by name (case-insensitive). Headers may include a unit in parentheses, e.g. `Pressure (PSI)`, which is matched to the field name.

```text
Date,Value,Notes
2024-01-15 10:00:00,42.5,startup
2024-01-15 11:00:00,43.0,
```

Unrecognized columns are skipped with a warning; defined fields missing from the header are reported. Each non-empty cell creates one `MonitorData` row for that field and timestamp.

## Data model (summary)

| Model | Role |
|-------|------|
| `Monitor` | Definition for one tool; `last_read` / `last_value` updated from latest numeric point |
| `MonitorColumn` | Named data entry field (type, order, unit label) |
| `MonitorData` | One measurement: timestamp, column (optional), numeric or string value, notes (legacy monitors only when no Notes field) |
| `MonitorAlertEmail` | Email alert configuration |
| `MonitorAlertLog` | History of alert trigger/reset events |

## Local development

A helper script builds a wheel and installs it into a local NEMO checkout (default: `/Users/adenton/Desktop/nemo-ce-alex`):

```bash
./scripts/dev_reinstall.sh                 # build, copy to NEMO/plugins, pip install, migrate
./scripts/dev_reinstall.sh --restart       # also restart the Django dev server
./scripts/dev_reinstall.sh --nemo-path /path/to/nemo-ce
```

The script installs into the NEMO project **venv** when present. It also patches that checkout’s `manage.py` once so `NEMO/plugins` is on `sys.path`, so the copied package loads even when you run a different Python (e.g. conda) without a matching `pip install`.

Use `--skip-pip` to only copy the package and apply the path hook.

See [scripts/dev_reinstall.sh](scripts/dev_reinstall.sh) for all options.

## Tests

```bash
python run_tests.py
```

This creates or updates `test_nemo.db` in the project root (gitignored). Tests use [NEMO_monitors/tests/test_settings.py](NEMO_monitors/tests/test_settings.py) with a minimal NEMO install.

## Upgrading from NEMO Tool Monitors

1. Uninstall the old package and remove `NEMO/plugins/NEMO_tool_monitors` if present.
2. Install `NEMO-monitors` and set `INSTALLED_APPS` to `NEMO_monitors.apps.MonitorsConfig`.
3. If your database already has `tool_monitors_*` tables, drop and remigrate in development, or run a Django app-rename migration in production before switching app labels.
4. Re-assign the **`monitors.upload_monitor_data`** permission to users and groups (the codename changes with the app label).
5. Re-enter site customization values under the **`monitors`** key (settings stored under `tool_monitors` are not read automatically).
6. Update bookmarks and integrations: web UI from `/tool_monitors/` to `/monitors/` (and related `/monitor_*` paths above). API clients from `/api/tool_monitors/...` to `/api/monitors/...` (see REST API table). Prefer `/api/monitors/readings/` for uploading samples; `/api/monitors/monitor_data/` has been removed.

## License

See [LICENSE](LICENSE).
