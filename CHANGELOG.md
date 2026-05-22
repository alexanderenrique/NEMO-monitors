# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- NEMO Sensors demo assets under `resources/` (fixture, icon, systemd units for `manage_sensor_data`).
- Unused vendored `chart.js` (templates use `chart.min.js` only).
- Empty `management/` package, GitLab CI config (`.gitlab-ci.yml`), local test database and sample CSV from the repo.
- Unused `process_alerts()` alias and redundant import in `MonitorData` post-save handler.
- `monitor_alerts.html` wrapper template (alert log partial rendered directly).

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
- **Upload hub**, CSV export, and site customization defaults (date range and chart refresh) under Customization → Monitor data.
- **REST API** under `/api/monitors/` for monitors, monitor data, alert email rules, and read-only alert logs (including `.xlsx` export).
- **Django admin** support: duplicate monitor, bulk show/hide, inline data entry fields.
- Permission **`monitors.upload_monitor_data`** for data entry; staff manage monitor definitions and alert configuration.
- Local development helper script `scripts/dev_reinstall.sh` and test suite via `run_tests.py`.

### Changed

- Renamed package from **NEMO-tool-monitors** to **NEMO-monitors** (`NEMO_monitors` app label `monitors`).
- Web UI paths moved from `/tool_monitors/` to `/monitors/` (and related `/monitor_*` routes).
- API paths moved from `/api/tool_monitors/...` to `/api/monitors/...`.
- Site customization key changed from `tool_monitors` to `monitors` (re-enter settings after upgrade).

[Unreleased]: https://github.com/alexanderenrique/NEMO-monitors/compare/1.0.1...HEAD
[1.0.1]: https://github.com/alexanderenrique/NEMO-monitors/releases/tag/1.0.1
[1.0.0]: https://github.com/alexanderenrique/NEMO-monitors/releases/tag/1.0.0
