import NEMO.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("monitors", "0003_remove_monitor_data_unit_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitoralertlog",
            name="column",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alert_logs",
                to="monitors.monitorcolumn",
            ),
        ),
        migrations.AddField(
            model_name="monitoralertemail",
            name="column",
            field=models.ForeignKey(
                blank=True,
                help_text="Numeric data entry field this alert watches. Leave blank for legacy single-value monitors.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alerts",
                to="monitors.monitorcolumn",
            ),
        ),
        migrations.RenameField(
            model_name="monitoralertemail",
            old_name="additional_emails",
            new_name="recipient_emails",
        ),
        migrations.AlterField(
            model_name="monitoralertemail",
            name="recipient_emails",
            field=NEMO.fields.MultiEmailField(
                blank=True,
                help_text="Email address(es) to notify when this alert is triggered or reset. A comma-separated list can be used.",
                max_length=2000,
                null=True,
            ),
        ),
    ]
