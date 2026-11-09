from django.db import migrations, models


def convert_integer_columns_to_number(apps, schema_editor):
    MonitorColumn = apps.get_model("monitors", "MonitorColumn")
    MonitorColumn.objects.filter(data_type="integer").update(data_type="float")


class Migration(migrations.Migration):

    dependencies = [
        ("monitors", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(convert_integer_columns_to_number, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="monitorcolumn",
            name="data_type",
            field=models.CharField(
                choices=[("float", "Number"), ("string", "Text")],
                default="float",
                help_text="Number or text. Numbers are charted and can be used in alerts; text is stored as entered.",
                max_length=20,
            ),
        ),
    ]
