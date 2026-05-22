from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("monitors", "0002_monitorcolumn_control_limits"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="monitor",
            name="data_unit_label",
        ),
    ]
