from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tool_monitors", "0006_monitorcolumn_suffix"),
    ]

    operations = [
        migrations.RenameField(
            model_name="monitor",
            old_name="data_suffix",
            new_name="data_unit_label",
        ),
        migrations.RenameField(
            model_name="monitorcolumn",
            old_name="suffix",
            new_name="unit_label",
        ),
    ]
