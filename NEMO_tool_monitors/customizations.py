from django.core.validators import validate_email

from NEMO.decorators import customization
from NEMO.views.customization import CustomizationBase


@customization(key="tool_monitors", title="Tool monitor data")
class MonitorCustomization(CustomizationBase):
    variables = {
        "monitor_default_daterange": "last_year",
        "monitor_default_refresh_rate": "0",
        "monitor_alert_emails": "",
    }

    def validate(self, name, value):
        if name == "monitor_alert_emails":
            recipients = tuple([e for e in value.split(",") if e])
            for email in recipients:
                validate_email(email)
