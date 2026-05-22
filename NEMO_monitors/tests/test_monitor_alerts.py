from unittest.mock import MagicMock, Mock, PropertyMock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from NEMO_monitors.alerts import process_alerts_for_monitor_data
from NEMO_monitors.models import Monitor, MonitorAlert, MonitorAlertEmail, MonitorColumn


class MonitorAlertValidationTests(SimpleTestCase):
    def _unsaved_monitor(self):
        monitor = Monitor(name="Test monitor")
        monitor.pk = 1
        return monitor

    @patch.object(Monitor, "columns", new_callable=PropertyMock)
    def test_requires_column_when_monitor_has_fields_and_condition(self, mock_columns):
        mock_columns.return_value.exists.return_value = True
        monitor = self._unsaved_monitor()
        alert = MonitorAlertEmail(
            monitor=monitor,
            trigger_condition="value > 1",
            recipient_emails=["a@example.org"],
            enabled=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            alert.clean()
        self.assertIn("column", ctx.exception.error_dict)

    def test_requires_recipients_when_enabled(self):
        alert = MonitorAlertEmail(
            trigger_no_data=True,
            recipient_emails=[],
            enabled=True,
        )
        with patch.object(MonitorAlert, "clean", return_value=None):
            with self.assertRaises(ValidationError) as ctx:
                alert.clean()
        self.assertIn("recipient_emails", ctx.exception.error_dict)


class MonitorAlertProcessTests(SimpleTestCase):
    def test_process_returns_early_for_non_matching_column(self):
        alert = MonitorAlertEmail()
        alert.column_id = 1
        alert.trigger_condition = "value > 10"
        alert.trigger_no_data = False
        pressure_data = Mock(column_id=2, value=50.0)
        with patch.object(alert, "_trigger_alert") as mock_trigger:
            alert.process(pressure_data)
            mock_trigger.assert_not_called()

    def test_process_evaluates_matching_column(self):
        alert = MonitorAlertEmail()
        alert.column_id = 1
        alert.trigger_condition = "value > 10"
        alert.trigger_no_data = False
        alert.triggered_on = None
        temp_data = Mock(column_id=1, value=50.0)
        with patch.object(alert, "_trigger_alert") as mock_trigger:
            alert.process(temp_data)
            mock_trigger.assert_called_once()

    @patch("NEMO_monitors.models.send_mail")
    def test_send_uses_only_recipient_emails(self, mock_send_mail):
        alert = MonitorAlertEmail()
        alert.monitor = Monitor(name="Test")
        alert.recipient_emails = ["only@example.org"]
        alert.send("subject", "body")
        mock_send_mail.assert_called_once()
        self.assertEqual(mock_send_mail.call_args.kwargs["to"], ["only@example.org"])


class ProcessAlertsForMonitorDataTests(SimpleTestCase):
    @patch.object(MonitorAlertEmail, "objects")
    def test_skips_alerts_for_other_columns(self, mock_objects):
        monitor = Mock(pk=1)
        pressure_data = Mock(column_id=2)
        temp_alert = Mock(column_id=1, enabled=True)
        pressure_alert = Mock(column_id=2, enabled=True)
        mock_objects.filter.return_value = [temp_alert, pressure_alert]

        process_alerts_for_monitor_data(monitor, pressure_data)

        temp_alert.process.assert_not_called()
        pressure_alert.process.assert_called_once_with(pressure_data)
