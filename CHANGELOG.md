# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.5] - 2026-11-09

### Changed

- Data entry field type is **Number** or **Text**. Existing integer fields are stored as numbers. Charting, alerts, and uploads behave as before.
- **`/api/monitors/readings/`** accepts field names as top-level keys (order independent), matching the simple NEMO-sensors style. Responses use the same flat shape. A nested `fields` object is still accepted for older clients. Discover field names from the `fields` list on each monitor (`GET /api/monitors/monitors/<id>/`).

### Removed

- REST endpoint **`/api/monitors/monitor_columns/`** and `?expand=columns` on monitors. Use the `fields` list on `/api/monitors/monitors/` instead.

## [1.0.4] - 2026-11-07

### Fixed

- Readings API sets a `MonitorData` queryset so NEMO's `DjangoModelPermissions` can resolve view and add permissions on `/api/monitors/readings/`.

## [1.0.3] - 2026-11-07

### Added

- **`/api/monitors/readings/`** — post and list monitor samples as a name-to-value `fields` map (order-independent field names; response includes per-field `ids`). Legacy monitors without data entry fields use `value` / `notes` on the same endpoint.
- Read-only **`/api/monitors/monitor_columns/`** and `?expand=columns` on `/api/monitors/monitors/` for field discovery by name.

### Removed

- REST endpoint **`/api/monitors/monitor_data/`** (row-level CRUD). Use `/api/monitors/readings/` for uploads and reads; the web UI still edits individual points via `/monitor/<id>/data/...`.
- NEMO Sensors demo assets under `resources/` (fixture, icon, systemd units for `manage_sensor_data`).
- Unused vendored `chart.js` (templates use `chart.min.js` only).
- Empty `management/` package, GitLab CI config (`.gitlab-ci.yml`), local test database and sample CSV from the repo.
- Unused `process_alerts()` alias and redundant import in `MonitorData` post-save handler.
- `monitor_alerts.html` wrapper template (alert log partial rendered directly).

## [1.0.2] - 2026-05-26

### Removed

- Default refresh rate site customization option (Customization → Monitor data).

## [1.0.1] - 2026-05-22

### Changed

- Consolidated database migrations into a single initial migration for new installs.
- Updated README with correct web UI and REST API paths.

## [1.0.0] - 2026-05-22

First PyPI release of **NEMO-monitors**, replacing the earlier **NEMO Tool Monitors** plugin. Requires NEMO or NEMO-CE ≥ 7.3.0 and Python ≥ 3.10.

### Added

- **Monitors dashboard** at `/monitors/` with tool-category navigation and recent alert log entries.
- **Per-tool monitor pages** with last value, last read time, and quick-add data entry (when permitted).
- **Monitor definitions** per tool: name, visibility, HTML description, and configurable **data entry fields** (`MonitorColumn`: float, integer, string) with optional unit labels; legacy single-value monitors without fields remain supported.
- **Detail tabs** per monitor: Chart.js time-series charts, sortable data table with inline edit/delete, CSV/single-point upload, and staff-configured **email alerts**.
- **Alert rules** per monitor and optional field: threshold expressions, no-data detection, per-rule recipients, trigger/reset on save, and alert log history.
- **Upload hub**, CSV export, and site customization default date range under Customization → Monitor data.
- **REST API** under `/api/monitors/` for monitors, monitor data, alert email rules, and read-only alert logs (including `.xlsx` export).
- **Django admin** support: duplicate monitor, bulk show/hide, inline data entry fields.
- Permission **`monitors.upload_monitor_data`** for data entry; staff manage monitor definitions and alert configuration.
- Local development helper script `scripts/dev_reinstall.sh` and test suite via `run_tests.py`.

### Changed

- Renamed package from **NEMO-tool-monitors** to **NEMO-monitors** (`NEMO_monitors` app label `monitors`).
- Web UI paths moved from `/tool_monitors/` to `/monitors/` (and related `/monitor_*` routes).
- API paths moved from `/api/tool_monitors/...` to `/api/monitors/...`.
- Site customization key changed from `tool_monitors` to `monitors` (re-enter settings after upgrade).

[Unreleased]: https://github.com/alexanderenrique/NEMO-monitors/compare/1.0.5...HEAD
[1.0.5]: https://github.com/alexanderenrique/NEMO-monitors/compare/1.0.4...1.0.5
[1.0.4]: https://github.com/alexanderenrique/NEMO-monitors/compare/1.0.3...1.0.4
[1.0.3]: https://github.com/alexanderenrique/NEMO-monitors/compare/1.0.2...1.0.3
[1.0.2]: https://github.com/alexanderenrique/NEMO-monitors/compare/1.0.1...1.0.2
[1.0.1]: https://github.com/alexanderenrique/NEMO-monitors/releases/tag/1.0.1
[1.0.0]: https://github.com/alexanderenrique/NEMO-monitors/releases/tag/1.0.0
