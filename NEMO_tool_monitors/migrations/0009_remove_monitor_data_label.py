from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tool_monitors", "0008_remove_monitor_data_prefix"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="monitor",
            name="data_label",
        ),
    ]
