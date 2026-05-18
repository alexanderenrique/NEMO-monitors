from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tool_monitors", "0007_rename_suffix_to_unit_label"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="monitor",
            name="data_prefix",
        ),
    ]
