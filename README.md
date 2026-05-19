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

- Each **monitor** belongs to one tool: name, visibility, optional **description** (HTML allowed; bare domains in links are normalized to `https://`), and an optional **default unit label** for legacy single-value displays.
- **Staff** users can create, edit, and delete monitors from the web UI (`/monitor/create/<tool_id>/`, `/monitor/<id>/edit/`, `/monitor/<id>/delete/`). The same models are available in **Django admin** (duplicate monitor, show/hide bulk actions, inline **data entry fields**).
- **Data entry fields** (`MonitorColumn`) define what is collected per timestamp: name, type (`float`, `integer`, `string`), display order, and optional **per-field unit label** for chart axes. New monitors default to **Value** (float) and **Notes** (string); fields can be added, renamed, reordered, or removed. Removing a field that still has data **unlinks** those rows (column set to null) and shows a warning.

Monitors with **no** data entry fields use the older **single numeric value** model (one `MonitorData` row per timestamp, optional `notes` on the row).

### Data entry and charts

- **Chart**, **Data**, **Alert**, and **Upload** tabs on each monitor (`/monitor_details/<id>/` and `/monitor_details/<id>/<tab>/`).
- **Chart.js** time-series charts with a configurable date range (site customization) and optional auto-refresh. Multi-field monitors plot each numeric field as its own series; string fields appear in the data table but not on the chart.
- **Data tab**: sortable table with inline edit/delete for users with upload permission.
- **Upload tab**: single-point form and CSV upload (file or paste).
- **Quick add** on the per-tool page (AJAX) when the user has upload permission.
- **Upload hub** (`/monitors/upload/`) to jump to any monitor’s upload tab.
- **Export** filtered data as CSV (`/export_monitor_data/<monitor_id>/`).

Each data point stores **measurement time** (`created_date`, editable), **upload time** (`created_on`), **created_by** / **updated_by**, and value(s) per column.

### Alerts

- **Email alerts** (`MonitorAlertEmail`) per monitor: trigger on a boolean **condition** (variable `value`, e.g. `value > 42`), on **no data**, or both.
- Alerts fire and reset on new data (via `post_save` on `MonitorData`); recipients come from site customization plus optional per-alert addresses.
- **Alert log** on the monitor and in Django admin; REST API for logs and alert definitions.

### REST API

Read/write (where applicable) via NEMO’s API router:

| Endpoint | Model |
|----------|--------|
| `monitors/monitors` | `Monitor` |
| `monitors/monitor_data` | `MonitorData` |
| `monitors/monitor_alert_emails` | `MonitorAlertEmail` |
| `monitors/monitor_alert_logs` | `MonitorAlertLog` (read-only; Excel export supported) |

Filters follow the same patterns as other NEMO model APIs.

### Site customization

Under NEMO **Customization → Monitor data** (`monitors`):

- **Monitor alert email(s)** — default recipients for all email alerts.
- **Default date range** — last 24 hours, 72 hours, week, month, or year on chart/data views.
- **Default refresh rate** — optional auto-refresh interval for live charts.

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

## Permissions

| Capability | Who |
|------------|-----|
| View dashboard, charts, data, alert logs | Any authenticated user |
| Add, edit, delete **data points**; CSV upload; upload hub; quick add | Users/groups with **`monitors.upload_monitor_data`** (“Can upload monitor data”) |
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
| Alert log JSON | `/monitor_alert_log/<monitor_id>/` |
| Export CSV | `/export_monitor_data/<monitor_id>/` |
| Add data point | `/monitor/<monitor_id>/data/add/` |
| Upload CSV | `/monitor/<monitor_id>/data/upload_csv/` |
| Edit / delete data point | `/monitor/<monitor_id>/data/<data_id>/edit/`, `.../delete/` |
| Create monitor (staff) | `/monitor/create/<tool_id>/` |
| Edit / delete monitor (staff) | `/monitor/<monitor_id>/edit/`, `/monitor/<monitor_id>/delete/` |

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

CI (GitLab) runs tests on Python 3.10–3.13 and builds packages on the default branch and tags.

## Upgrading from NEMO Tool Monitors

1. Uninstall the old package and remove `NEMO/plugins/NEMO_tool_monitors` if present.
2. Install `NEMO-monitors` and set `INSTALLED_APPS` to `NEMO_monitors.apps.MonitorsConfig`.
3. If your database already has `tool_monitors_*` tables, drop and remigrate in development, or run a Django app-rename migration in production before switching app labels.
4. Re-assign the **`monitors.upload_monitor_data`** permission to users and groups (the codename changes with the app label).
5. Re-enter site customization values under the **`monitors`** key (settings stored under `tool_monitors` are not read automatically).
6. Update bookmarks, integrations, and API clients from `/tool_monitors/` to `/monitors/`.

## License

See [LICENSE](LICENSE).
