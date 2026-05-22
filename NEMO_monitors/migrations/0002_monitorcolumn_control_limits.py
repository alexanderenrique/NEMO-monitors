from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitors", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitorcolumn",
            name="control_limits_mode",
            field=models.CharField(
                blank=True,
                choices=[("", "None"), ("statistical", "Statistical"), ("fixed", "Fixed")],
                default="",
                help_text="Statistical (3σ) or fixed min/max control limits for chart display.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="monitorcolumn",
            name="fixed_limit_min",
            field=models.FloatField(
                blank=True,
                help_text="Fixed lower control limit when control_limits_mode is fixed.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="monitorcolumn",
            name="fixed_limit_max",
            field=models.FloatField(
                blank=True,
                help_text="Fixed upper control limit when control_limits_mode is fixed.",
                null=True,
            ),
        ),
    ]
