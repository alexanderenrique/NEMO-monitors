from NEMO.decorators import customization
from NEMO.views.customization import CustomizationBase


@customization(key="monitors", title="Monitor data")
class MonitorCustomization(CustomizationBase):
    variables = {
        "monitor_default_daterange": "last_year",
    }
