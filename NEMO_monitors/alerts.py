from logging import getLogger

from NEMO_monitors.models import Monitor, MonitorAlert, MonitorData

alerts_logger = getLogger(__name__)


def process_alerts_for_monitor_data(monitor: Monitor, monitor_data: MonitorData = None):
    """Run every enabled alert for this monitor, optionally scoped to one data point."""
    try:
        monitor_alerts = []
        for sub_class in MonitorAlert.__subclasses__():
            monitor_alerts.extend(sub_class.objects.filter(enabled=True, monitor=monitor))
        for alert in monitor_alerts:
            if (
                monitor_data is not None
                and alert.column_id
                and monitor_data.column_id != alert.column_id
            ):
                continue
            alert.process(monitor_data)
    except Exception as e:
        alerts_logger.error(e)


def process_alerts_after_bulk_create(monitor: Monitor, created_rows):
    """Process alerts after bulk_create (which does not fire post_save signals)."""
    if not created_rows:
        return
    for row in created_rows:
        process_alerts_for_monitor_data(monitor, row)
