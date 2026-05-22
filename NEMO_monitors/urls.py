from django.urls import path, re_path

from NEMO.urls import router, sort_urls

from NEMO_monitors import api, views

router.register(r"monitors/monitors", api.MonitorViewSet)
router.register(r"monitors/monitor_data", api.MonitorDataViewSet)
router.register(r"monitors/monitor_alert_emails", api.MonitorAlertEmailViewSet)
router.register(r"monitors/monitor_alert_logs", api.MonitorAlertLogViewSet)
router.registry.sort(key=sort_urls)


urlpatterns = [
    path("monitors/", views.monitors_dashboard, name="monitors"),
    path(
        "monitors/category/<path:category_path>/",
        views.monitors_dashboard,
        name="monitors_category",
    ),
    path("monitors/upload/", views.monitors_upload_hub, name="monitors_upload"),
    path("monitors/tool/<int:tool_id>/", views.monitors_for_tool, name="monitors_for_tool"),
    path("monitor_details/<int:monitor_id>/", views.monitor_details, name="monitor_details"),
    re_path(
        r"monitor_details/(?P<monitor_id>\d+)/(?P<tab>chart|data|alert|upload)/$",
        views.monitor_details,
        name="monitor_details",
    ),
    path("monitor_chart_data/<int:monitor_id>/", views.monitor_chart_data, name="monitor_chart_data"),
    path("monitor_alert_log/<int:monitor_id>/", views.monitor_alert_log, name="monitor_alert_log"),
    path(
        "monitor/<int:monitor_id>/alert/save/",
        views.save_monitor_alert,
        name="save_monitor_alert",
    ),
    path(
        "monitor/<int:monitor_id>/alert/<int:alert_id>/save/",
        views.save_monitor_alert,
        name="edit_monitor_alert",
    ),
    path(
        "monitor/<int:monitor_id>/alert/<int:alert_id>/delete/",
        views.delete_monitor_alert,
        name="delete_monitor_alert",
    ),
    path("export_monitor_data/<int:monitor_id>/", views.export_monitor_data, name="export_monitor_data"),
    path(
        "monitor/<int:monitor_id>/data/add/",
        views.add_monitor_data,
        name="add_monitor_data",
    ),
    path(
        "monitor/<int:monitor_id>/data/upload_csv/",
        views.upload_monitor_data_csv,
        name="upload_monitor_data_csv",
    ),
    path(
        "monitor/<int:monitor_id>/data/<int:data_id>/edit/",
        views.edit_monitor_data,
        name="edit_monitor_data",
    ),
    path(
        "monitor/<int:monitor_id>/data/<int:data_id>/delete/",
        views.delete_monitor_data,
        name="delete_monitor_data",
    ),
    path("monitor/create/<int:tool_id>/", views.create_monitor, name="create_monitor"),
    path("monitor/<int:monitor_id>/edit/", views.edit_monitor, name="edit_monitor"),
    path("monitor/<int:monitor_id>/delete/", views.delete_monitor, name="delete_monitor"),
]
