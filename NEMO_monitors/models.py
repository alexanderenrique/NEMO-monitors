from __future__ import annotations

import datetime
import random
from logging import getLogger
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.safestring import mark_safe

from NEMO_monitors.html_utils import normalize_description_links
from NEMO.constants import CHAR_FIELD_MEDIUM_LENGTH
from NEMO.evaluators import evaluate_boolean_expression
from NEMO.fields import MultiEmailField
from NEMO.models import BaseModel, Tool, User
from NEMO.typing import QuerySetType
from NEMO.utilities import EmailCategory, format_datetime, get_email_from_settings, send_mail

models_logger = getLogger(__name__)

# Default data entry fields for new monitors (removable on the monitor configuration form).
DEFAULT_DATA_ENTRY_FIELDS = (
    ("Value", "float"),
    ("Notes", "string"),
)


class Monitor(BaseModel):
    name = models.CharField(max_length=CHAR_FIELD_MEDIUM_LENGTH)
    visible = models.BooleanField(
        default=True, help_text="Specifies whether this monitor is visible in the monitor dashboard"
    )
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name="monitors",
        help_text="The tool that this monitor reports data for.",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of what this monitor tracks. HTML may be used (for example for links); shown at the top of the monitor details page.",
    )
    last_read = models.DateTimeField(null=True, blank=True)
    last_value = models.FloatField(null=True, blank=True)

    def last_value_display(self):
        return display_monitor_value(self, self.last_value)

    @property
    def description_html(self):
        if not self.description:
            return ""
        return mark_safe(normalize_description_links(self.description))

    def alert_triggered(self) -> bool:
        for alert_qs in MonitorAlert.monitor_alert_filter(monitor=self):
            if alert_qs.filter(triggered_on__isnull=False).exists():
                return True
        return False

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["tool__name", "name"]


CONTROL_LIMITS_NONE = ""
CONTROL_LIMITS_STATISTICAL = "statistical"
CONTROL_LIMITS_FIXED = "fixed"

CONTROL_LIMITS_MODE_CHOICES = [
    (CONTROL_LIMITS_NONE, "None"),
    (CONTROL_LIMITS_STATISTICAL, "Statistical"),
    (CONTROL_LIMITS_FIXED, "Fixed"),
]


class MonitorColumn(BaseModel):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(
        max_length=CHAR_FIELD_MEDIUM_LENGTH, help_text="Field name as it appears in forms and CSV headers."
    )
    data_type = models.CharField(
        max_length=20,
        choices=[("float", "Number"), ("string", "Text")],
        default="float",
        help_text="Number or text. Numbers are charted and can be used in alerts; text is stored as entered.",
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order on the chart and table.")
    unit_label = models.CharField(
        max_length=CHAR_FIELD_MEDIUM_LENGTH,
        blank=True,
        default="",
        help_text="Unit label for this field on the chart y-axis (e.g. A/min, %).",
    )
    control_limits_mode = models.CharField(
        max_length=20,
        choices=CONTROL_LIMITS_MODE_CHOICES,
        default=CONTROL_LIMITS_NONE,
        blank=True,
        help_text="Statistical (3σ) or fixed min/max control limits for chart display.",
    )
    fixed_limit_min = models.FloatField(
        null=True,
        blank=True,
        help_text="Fixed lower control limit when control_limits_mode is fixed.",
    )
    fixed_limit_max = models.FloatField(
        null=True,
        blank=True,
        help_text="Fixed upper control limit when control_limits_mode is fixed.",
    )

    def is_plottable(self) -> bool:
        # "integer" is a legacy value; new fields are number ("float") or text ("string").
        return self.data_type in ("float", "integer")

    def clean(self):
        super().clean()
        if not self.is_plottable():
            self.control_limits_mode = CONTROL_LIMITS_NONE
            self.fixed_limit_min = None
            self.fixed_limit_max = None
            return
        if self.control_limits_mode == CONTROL_LIMITS_FIXED:
            if self.fixed_limit_min is None and self.fixed_limit_max is None:
                raise ValidationError(
                    "Fixed control limits require at least a minimum or maximum value."
                )
            if (
                self.fixed_limit_min is not None
                and self.fixed_limit_max is not None
                and self.fixed_limit_min >= self.fixed_limit_max
            ):
                raise ValidationError("Fixed minimum must be less than fixed maximum.")
        elif self.control_limits_mode != CONTROL_LIMITS_FIXED:
            self.fixed_limit_min = None
            self.fixed_limit_max = None

    def save(self, *args, **kwargs):
        if not self.is_plottable():
            self.control_limits_mode = CONTROL_LIMITS_NONE
            self.fixed_limit_min = None
            self.fixed_limit_max = None
        elif self.control_limits_mode != CONTROL_LIMITS_FIXED:
            self.fixed_limit_min = None
            self.fixed_limit_max = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.monitor.name} – {self.name} ({self.get_data_type_display()})"

    class Meta:
        ordering = ["order", "name"]
        unique_together = [["monitor", "name"]]


class MonitorData(BaseModel):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    column = models.ForeignKey(
        MonitorColumn,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="data_points",
        help_text="The column definition this data point belongs to. Null for legacy single-value rows.",
    )
    value = models.FloatField(null=True, blank=True)
    string_value = models.CharField(
        max_length=CHAR_FIELD_MEDIUM_LENGTH,
        blank=True,
        default="",
        help_text="Populated for string-typed columns.",
    )
    created_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="The timestamp the data point represents (e.g. measurement time). Editable.",
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monitor_data_created",
        help_text="The user who originally uploaded this data point.",
    )
    created_on = models.DateTimeField(
        auto_now_add=True, help_text="The server timestamp when this data point was uploaded."
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monitor_data_updated",
        help_text="The user who last edited this data point.",
    )
    updated_on = models.DateTimeField(auto_now=True, help_text="The server timestamp when this data point was last edited.")
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Optional comment about this measurement (not plotted on the chart).",
    )

    def display_value(self):
        if self.column and self.column.data_type == "string":
            return self.string_value
        return display_monitor_value(self.monitor, self.value, self.column)

    class Meta:
        verbose_name_plural = "Monitor data"
        ordering = ["-created_date"]
        permissions = [("upload_monitor_data", "Can upload monitor data")]


@receiver(post_save, sender=MonitorData)
def monitor_data_post_save(sender, instance: MonitorData, created, **kwargs):
    from NEMO_monitors.alerts import process_alerts_for_monitor_data

    monitor = instance.monitor
    latest = MonitorData.objects.filter(monitor=monitor, value__isnull=False).order_by("-created_date").first()
    if latest:
        monitor.last_read = latest.created_date
        monitor.last_value = latest.value
        monitor.save(update_fields=["last_read", "last_value"])
    process_alerts_for_monitor_data(monitor, instance)


class MonitorAlertLog(BaseModel):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    column = models.ForeignKey(
        MonitorColumn,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alert_logs",
    )
    time = models.DateTimeField(auto_now_add=True)
    value = models.FloatField(null=True, blank=True)
    reset = models.BooleanField(default=False)
    condition = models.TextField(null=True, blank=True)
    no_data = models.BooleanField(default=False)

    def description(self):
        column_name = self.column.name if self.column_id else None
        return get_alert_description(
            self.time, self.reset, self.condition, self.no_data, self.value, column_name=column_name
        )

    class Meta:
        ordering = ["-time"]


class MonitorAlert(BaseModel):
    enabled = models.BooleanField(default=True)
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    column = models.ForeignKey(
        MonitorColumn,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
        help_text="Numeric data entry field this alert watches. Leave blank for legacy single-value monitors.",
    )
    trigger_no_data = models.BooleanField(
        default=False, help_text="Check this box to trigger this alert when no data is available"
    )
    trigger_condition = models.TextField(
        null=True,
        blank=True,
        help_text=mark_safe(
            "The trigger condition for this alert. The monitor value is available as a variable named "
            "<b>value</b>. e.g. value == 42 or value > 42."
        ),
    )
    triggered_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def _reset_alert(self, alert_time, value):
        if self.triggered_on:
            self.set_alert_time(time=None)
            self.log_alert(alert_time, reset=True, value=value)
            self.reset_alert(alert_time, value)

    def _trigger_alert(self, alert_time, value):
        if not self.triggered_on:
            self.set_alert_time(time=alert_time)
            self.log_alert(alert_time, reset=False, value=value)
            self.trigger_alert(alert_time, value)

    def clean(self):
        if not self.trigger_condition and not self.trigger_no_data:
            raise ValidationError(
                {
                    "trigger_condition": "Please enter a trigger condition or set this alert to trigger when there is no data"
                }
            )
        if self.monitor_id and self.monitor.columns.exists() and self.trigger_condition and not self.column_id:
            raise ValidationError(
                {"column": "Select a data entry field for this alert when the monitor has multiple fields."}
            )
        if self.column_id:
            if self.column.monitor_id != self.monitor_id:
                raise ValidationError({"column": "The selected field does not belong to this monitor."})
            if not self.column.is_plottable():
                raise ValidationError({"column": "Alerts can only target number fields."})
        if self.trigger_condition:
            value = random.uniform(0, 100)
            try:
                evaluate_boolean_expression(self.trigger_condition, value=value)
            except Exception as e:
                raise ValidationError({"trigger_condition": str(e)})

    def set_alert_time(self, time: Optional[datetime.datetime]):
        self.triggered_on = time
        self.save()

    def log_alert(self, time: datetime.datetime, reset: bool = False, value: float = None):
        MonitorAlertLog.objects.create(
            time=time,
            condition=self.trigger_condition,
            monitor=self.monitor,
            column=self.column,
            value=value,
            reset=reset,
            no_data=self.trigger_no_data,
        )

    def _value_for_processing(self, monitor_data: Optional[MonitorData]) -> Optional[float]:
        if monitor_data is not None:
            return monitor_data.value
        if self.column_id:
            latest = (
                MonitorData.objects.filter(monitor=self.monitor, column=self.column, value__isnull=False)
                .order_by("-created_date")
                .first()
            )
            return latest.value if latest else None
        latest = (
            MonitorData.objects.filter(monitor=self.monitor, value__isnull=False)
            .order_by("-created_date")
            .first()
        )
        return latest.value if latest else None

    def process(self, monitor_data: MonitorData = None):
        if monitor_data is not None and self.column_id and monitor_data.column_id != self.column_id:
            return
        now = timezone.now()
        value: Optional[float] = self._value_for_processing(monitor_data)
        if self.trigger_condition and self.trigger_no_data:
            if value is None or evaluate_boolean_expression(self.trigger_condition, value=value):
                self._trigger_alert(now, value)
            else:
                self._reset_alert(now, value)
        elif self.trigger_condition:
            if value is not None:
                if evaluate_boolean_expression(self.trigger_condition, value=value):
                    self._trigger_alert(now, value)
                else:
                    self._reset_alert(now, value)
        else:
            if value is None:
                self._trigger_alert(now, value)
            else:
                self._reset_alert(now, value)

    def reset_alert(self, alert_time: datetime.datetime, value: float = None):
        pass

    def trigger_alert(self, alert_time: datetime.datetime, value: float = None):
        pass

    @classmethod
    def monitor_alert_filter(cls, enabled=True, monitor=None) -> List[QuerySetType["MonitorAlert"]]:
        monitor_alert_qs = []
        for sub_class in cls.__subclasses__():
            sub_filter = sub_class.objects.all()
            if enabled is not None:
                sub_filter = sub_filter.filter(enabled=enabled)
            if monitor:
                sub_filter = sub_filter.filter(monitor=monitor)
            monitor_alert_qs.append(sub_filter)
        return monitor_alert_qs


class MonitorAlertEmail(MonitorAlert):
    recipient_emails = MultiEmailField(
        null=True,
        blank=True,
        help_text="Email address(es) to notify when this alert is triggered or reset. A comma-separated list can be used.",
    )

    def clean(self):
        super().clean()
        if self.enabled and not self.recipient_emails:
            raise ValidationError(
                {"recipient_emails": "Enter at least one recipient email when this alert is enabled."}
            )

    def _alert_subject_prefix(self) -> str:
        if self.column_id:
            return f"{self.monitor.name} ({self.column.name})"
        return self.monitor.name

    def reset_alert(self, alert_time: datetime.datetime, value: float = None):
        subject = f"Alert reset for {self._alert_subject_prefix()}"
        message = get_alert_description(
            alert_time,
            True,
            self.trigger_condition,
            self.trigger_no_data,
            value,
            column_name=self.column.name if self.column_id else None,
        )
        self.send(subject, message)

    def trigger_alert(self, alert_time: datetime.datetime, value: float = None):
        subject = f"Alert triggered for {self._alert_subject_prefix()}"
        message = get_alert_description(
            alert_time,
            False,
            self.trigger_condition,
            self.trigger_no_data,
            value,
            column_name=self.column.name if self.column_id else None,
        )
        self.send(subject, message)

    def send(self, subject, message):
        recipients = list(self.recipient_emails or [])
        if recipients:
            send_mail(
                subject=subject,
                content=message,
                from_email=get_email_from_settings(),
                to=recipients,
                email_category=EmailCategory.GENERAL,
            )


def get_alert_description(
    time, reset: bool, condition: str, no_data: bool, value: float, column_name: Optional[str] = None
):
    if condition and value is not None:
        if reset:
            trigger_reason = f'the value ({value}) didn\'t meet the alert condition: "{condition}" anymore'
        else:
            trigger_reason = f'the condition: "{condition}" was met with value={value}'
    elif no_data and value is None:
        trigger_reason = "there was no data"
    elif value is not None and reset:
        trigger_reason = f"the monitor sent back value={value}"
    else:
        trigger_reason = None
    field_prefix = f"[{column_name}] " if column_name else ""
    alert_description = f"{field_prefix}This alert was {'reset' if reset else 'triggered'} on {format_datetime(time)}"
    if trigger_reason:
        alert_description += f" because {trigger_reason}."
    return alert_description


def display_monitor_value(monitor: Monitor, value: float, column: Optional["MonitorColumn"] = None) -> str:
    if value is None:
        return ""
    unit = ""
    if column and (column.unit_label or "").strip():
        unit = f" {(column.unit_label or '').strip()}"
    return f"{value}{unit}"


def refresh_monitor_last_value(monitor: Monitor) -> None:
    """Update monitor.last_read / last_value from the latest numeric data point."""
    monitor.refresh_from_db()
    latest = MonitorData.objects.filter(monitor=monitor, value__isnull=False).order_by("-created_date").first()
    if latest:
        monitor.last_read = latest.created_date
        monitor.last_value = latest.value
        monitor.save(update_fields=["last_read", "last_value"])
