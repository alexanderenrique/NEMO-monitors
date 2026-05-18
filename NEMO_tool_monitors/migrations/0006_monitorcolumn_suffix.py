from django.db import migrations, models

from NEMO.constants import CHAR_FIELD_MEDIUM_LENGTH


class Migration(migrations.Migration):

    dependencies = [
        ("tool_monitors", "0005_alter_monitor_description_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitorcolumn",
            name="suffix",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Unit label for this field on the chart y-axis (e.g. A/min, %).",
                max_length=CHAR_FIELD_MEDIUM_LENGTH,
            ),
        ),
    ]
