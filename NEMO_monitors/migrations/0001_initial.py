import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import NEMO.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("NEMO", "0001_version_1_0_0"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Monitor",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                (
                    "visible",
                    models.BooleanField(
                        default=True, help_text="Specifies whether this monitor is visible in the monitor dashboard"
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional description of what this monitor tracks. HTML may be used (for example for links); shown at the top of the monitor details page.",
                        null=True,
                    ),
                ),
                ("last_read", models.DateTimeField(blank=True, null=True)),
                ("last_value", models.FloatField(blank=True, null=True)),
                (
                    "tool",
                    models.ForeignKey(
                        help_text="The tool that this monitor reports data for.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="monitors",
                        to="NEMO.tool",
                    ),
                ),
            ],
            options={
                "ordering": ["tool__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="MonitorColumn",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(help_text="Field name as it appears in forms and CSV headers.", max_length=255),
                ),
                (
                    "data_type",
                    models.CharField(
                        choices=[("float", "Float"), ("integer", "Integer"), ("string", "String")],
                        default="float",
                        help_text="Expected data type for this column.",
                        max_length=20,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0, help_text="Display order on the chart and table.")),
                (
                    "unit_label",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Unit label for this field on the chart y-axis (e.g. A/min, %).",
                        max_length=255,
                    ),
                ),
                (
                    "control_limits_mode",
                    models.CharField(
                        blank=True,
                        choices=[("", "None"), ("statistical", "Statistical"), ("fixed", "Fixed")],
                        default="",
                        help_text="Statistical (3σ) or fixed min/max control limits for chart display.",
                        max_length=20,
                    ),
                ),
                (
                    "fixed_limit_min",
                    models.FloatField(
                        blank=True,
                        help_text="Fixed lower control limit when control_limits_mode is fixed.",
                        null=True,
                    ),
                ),
                (
                    "fixed_limit_max",
                    models.FloatField(
                        blank=True,
                        help_text="Fixed upper control limit when control_limits_mode is fixed.",
                        null=True,
                    ),
                ),
                (
                    "monitor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="columns", to="monitors.monitor"
                    ),
                ),
            ],
            options={
                "ordering": ["order", "name"],
                "unique_together": {("monitor", "name")},
            },
        ),
        migrations.CreateModel(
            name="MonitorData",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.FloatField(blank=True, null=True)),
                (
                    "string_value",
                    models.CharField(
                        blank=True, default="", help_text="Populated for string-typed columns.", max_length=255
                    ),
                ),
                (
                    "created_date",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                        help_text="The timestamp the data point represents (e.g. measurement time). Editable.",
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(
                        auto_now_add=True, help_text="The server timestamp when this data point was uploaded."
                    ),
                ),
                (
                    "updated_on",
                    models.DateTimeField(
                        auto_now=True, help_text="The server timestamp when this data point was last edited."
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Optional comment about this measurement (not plotted on the chart).",
                    ),
                ),
                (
                    "column",
                    models.ForeignKey(
                        blank=True,
                        help_text="The column definition this data point belongs to. Null for legacy single-value rows.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_points",
                        to="monitors.monitorcolumn",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="The user who originally uploaded this data point.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="monitor_data_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="monitors.monitor")),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="The user who last edited this data point.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="monitor_data_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Monitor data",
                "ordering": ["-created_date"],
                "permissions": [("upload_monitor_data", "Can upload monitor data")],
            },
        ),
        migrations.CreateModel(
            name="MonitorAlertLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time", models.DateTimeField(auto_now_add=True)),
                ("value", models.FloatField(blank=True, null=True)),
                ("reset", models.BooleanField(default=False)),
                ("condition", models.TextField(blank=True, null=True)),
                ("no_data", models.BooleanField(default=False)),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="monitors.monitor")),
                (
                    "column",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="alert_logs",
                        to="monitors.monitorcolumn",
                    ),
                ),
            ],
            options={
                "ordering": ["-time"],
            },
        ),
        migrations.CreateModel(
            name="MonitorAlertEmail",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                (
                    "trigger_no_data",
                    models.BooleanField(
                        default=False, help_text="Check this box to trigger this alert when no data is available"
                    ),
                ),
                (
                    "trigger_condition",
                    models.TextField(
                        blank=True,
                        help_text="The trigger condition for this alert. The monitor value is available as a variable named <b>value</b>. e.g. value == 42 or value > 42.",
                        null=True,
                    ),
                ),
                ("triggered_on", models.DateTimeField(blank=True, null=True)),
                (
                    "recipient_emails",
                    NEMO.fields.MultiEmailField(
                        blank=True,
                        help_text="Email address(es) to notify when this alert is triggered or reset. A comma-separated list can be used.",
                        max_length=2000,
                        null=True,
                    ),
                ),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="monitors.monitor")),
                (
                    "column",
                    models.ForeignKey(
                        blank=True,
                        help_text="Numeric data entry field this alert watches. Leave blank for legacy single-value monitors.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="alerts",
                        to="monitors.monitorcolumn",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
