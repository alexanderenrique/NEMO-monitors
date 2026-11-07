from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from NEMO.models import Tool, User
from NEMO.permissions import DjangoModelPermissions

from NEMO_monitors.api import (
    MonitorReadingSerializer,
    MonitorReadingViewSet,
    _create_reading,
    _group_monitor_data_into_readings,
)
from NEMO_monitors.models import Monitor, MonitorColumn, MonitorData


def _grant_billing_api(user: User) -> None:
    perm = Permission.objects.get(codename="use_billing_api")
    user.user_permissions.add(perm)


class ReadingsApiHelpersTests(TestCase):
    def setUp(self):
        self.tool = Tool.objects.create(name="Fiji 1 readings test")
        self.user = User.objects.create(
            username="readings_api_user",
            first_name="Read",
            last_name="Ings",
            email="readings@example.org",
        )
        self.monitor = Monitor.objects.create(name="Hf precursor", tool=self.tool)
        self.cylinder = MonitorColumn.objects.create(
            monitor=self.monitor, name="Cylinder ID", data_type="string", order=0
        )
        self.weight = MonitorColumn.objects.create(
            monitor=self.monitor, name="Weight Remaining", data_type="float", order=1
        )
        self.notes = MonitorColumn.objects.create(
            monitor=self.monitor, name="Notes", data_type="string", order=2
        )

    def test_create_reading_order_independent_field_names(self):
        serializer = MonitorReadingSerializer(
            data={
                "monitor": self.monitor.pk,
                "created_date": "2026-11-07T18:15:00",
                "fields": {
                    "Notes": "swapped cylinder",
                    "Cylinder ID": "HF-204",
                    "Weight Remaining": 12.4,
                },
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = _create_reading(serializer.validated_data, self.user)

        self.assertEqual(result["monitor"], self.monitor.pk)
        self.assertEqual(result["fields"]["Cylinder ID"], "HF-204")
        self.assertEqual(result["fields"]["Weight Remaining"], 12.4)
        self.assertEqual(result["fields"]["Notes"], "swapped cylinder")
        self.assertEqual(set(result["ids"]), {"Cylinder ID", "Weight Remaining", "Notes"})
        self.assertEqual(MonitorData.objects.filter(monitor=self.monitor).count(), 3)

    def test_case_insensitive_field_names(self):
        serializer = MonitorReadingSerializer(
            data={
                "monitor": self.monitor.pk,
                "fields": {"cylinder id": "A-1", "WEIGHT REMAINING": 1},
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = _create_reading(serializer.validated_data, self.user)
        self.assertEqual(result["fields"]["Cylinder ID"], "A-1")
        self.assertEqual(result["fields"]["Weight Remaining"], 1.0)

    def test_unknown_field_returns_validation_error(self):
        serializer = MonitorReadingSerializer(
            data={"monitor": self.monitor.pk, "fields": {"Temperature": 22}}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError) as ctx:
            _create_reading(serializer.validated_data, self.user)
        self.assertIn("fields", ctx.exception.detail)

    def test_bad_number_returns_validation_error(self):
        serializer = MonitorReadingSerializer(
            data={"monitor": self.monitor.pk, "fields": {"Weight Remaining": "not-a-number"}}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError) as ctx:
            _create_reading(serializer.validated_data, self.user)
        self.assertIn("Weight Remaining", ctx.exception.detail)

    def test_blank_fields_only_returns_error(self):
        serializer = MonitorReadingSerializer(
            data={"monitor": self.monitor.pk, "fields": {"Notes": "  ", "Weight Remaining": ""}}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError):
            _create_reading(serializer.validated_data, self.user)

    def test_legacy_value_notes_create(self):
        legacy = Monitor.objects.create(name="Legacy single value", tool=self.tool)
        serializer = MonitorReadingSerializer(
            data={"monitor": legacy.pk, "value": 42.5, "notes": "startup"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = _create_reading(serializer.validated_data, self.user)
        self.assertEqual(result["value"], 42.5)
        self.assertEqual(result["notes"], "startup")
        self.assertIn("id", result)
        self.assertEqual(MonitorData.objects.filter(monitor=legacy).count(), 1)

    def test_fields_rejected_on_legacy_monitor(self):
        legacy = Monitor.objects.create(name="Legacy no columns", tool=self.tool)
        serializer = MonitorReadingSerializer(
            data={"monitor": legacy.pk, "fields": {"Value": 1}}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("fields", serializer.errors)

    def test_value_rejected_on_column_monitor(self):
        serializer = MonitorReadingSerializer(
            data={"monitor": self.monitor.pk, "value": 1.0}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("fields", serializer.errors)

    def test_group_readings_by_created_date(self):
        ts = timezone.now()
        rows = [
            MonitorData.objects.create(
                monitor=self.monitor,
                column=self.cylinder,
                string_value="HF-1",
                created_date=ts,
                created_by=self.user,
                updated_by=self.user,
            ),
            MonitorData.objects.create(
                monitor=self.monitor,
                column=self.weight,
                value=9.5,
                created_date=ts,
                created_by=self.user,
                updated_by=self.user,
            ),
        ]
        grouped = _group_monitor_data_into_readings(list(reversed(rows)))
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["fields"]["Cylinder ID"], "HF-1")
        self.assertEqual(grouped[0]["fields"]["Weight Remaining"], 9.5)
        self.assertEqual(grouped[0]["ids"]["Cylinder ID"], rows[0].id)
        self.assertEqual(grouped[0]["ids"]["Weight Remaining"], rows[1].id)


class ReadingsViewSetTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tool = Tool.objects.create(name="Fiji viewset readings")
        self.user = User.objects.create(
            username="readings_view_user",
            first_name="View",
            last_name="User",
            email="view@example.org",
        )
        _grant_billing_api(self.user)
        self.monitor = Monitor.objects.create(name="View monitor", tool=self.tool)
        MonitorColumn.objects.create(monitor=self.monitor, name="Cylinder ID", data_type="string", order=0)
        MonitorColumn.objects.create(monitor=self.monitor, name="Weight Remaining", data_type="float", order=1)
        MonitorColumn.objects.create(monitor=self.monitor, name="Notes", data_type="string", order=2)
        self.view = MonitorReadingViewSet.as_view({"post": "create", "get": "list"})

    def test_post_and_get_round_trip(self):
        post_request = self.factory.post(
            "/api/monitors/readings/",
            {
                "monitor": self.monitor.pk,
                "created_date": "2026-11-07T18:15:00-08:00",
                "fields": {
                    "Notes": "ok",
                    "Weight Remaining": 3.2,
                    "Cylinder ID": "C-9",
                },
            },
            format="json",
        )
        force_authenticate(post_request, user=self.user)
        post_response = self.view(post_request)
        self.assertEqual(post_response.status_code, 201, post_response.data)
        self.assertEqual(post_response.data["fields"]["Cylinder ID"], "C-9")
        self.assertEqual(len(post_response.data["ids"]), 3)

        get_request = self.factory.get(
            f"/api/monitors/readings/?monitor={self.monitor.pk}"
        )
        force_authenticate(get_request, user=self.user)
        get_response = self.view(get_request)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(len(get_response.data), 1)
        self.assertEqual(get_response.data[0]["fields"]["Weight Remaining"], 3.2)

    def test_list_requires_monitor(self):
        get_request = self.factory.get("/api/monitors/readings/")
        force_authenticate(get_request, user=self.user)
        response = self.view(get_request)
        self.assertEqual(response.status_code, 400)

    def test_django_model_permissions_resolve_monitor_data(self):
        """Production uses DjangoModelPermissions, which requires a queryset on the view."""
        permission = DjangoModelPermissions()
        view = MonitorReadingViewSet()
        get_request = self.factory.get(f"/api/monitors/readings/?monitor={self.monitor.pk}")
        get_request.user = self.user
        self.assertFalse(permission.has_permission(get_request, view))

        view_perm = Permission.objects.get(codename="view_monitordata")
        add_perm = Permission.objects.get(codename="add_monitordata")
        self.user.user_permissions.add(view_perm, add_perm)
        self.user = User.objects.get(pk=self.user.pk)

        get_request.user = self.user
        self.assertTrue(permission.has_permission(get_request, view))

        post_request = self.factory.post("/api/monitors/readings/", {}, format="json")
        post_request.user = self.user
        self.assertTrue(permission.has_permission(post_request, view))
