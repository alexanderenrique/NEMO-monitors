from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("monitors", "0005_monitoralertlog_acknowledgement"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="monitoralertlog",
            name="acknowledged_by",
        ),
        migrations.RemoveField(
            model_name="monitoralertlog",
            name="acknowledged_at",
        ),
    ]
