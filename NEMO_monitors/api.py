from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_excel.mixins import XLSXFileMixin
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.serializers import DateTimeField, DictField, IntegerField, Serializer
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet

from NEMO.serializers import ModelSerializer
from NEMO.views.api import ModelViewSet, boolean_filters, datetime_filters, key_filters, number_filters, string_filters

from NEMO_monitors.alerts import process_alerts_after_bulk_create
from NEMO_monitors.column_matching import (
    RESERVED_READING_KEYS,
    columns_by_normalized_name,
    match_field_name_to_monitor_column,
)
from NEMO_monitors.models import (
    Monitor,
    MonitorAlertEmail,
    MonitorAlertLog,
    MonitorColumn,
    MonitorData,
    refresh_monitor_last_value,
)


def api_field_type(data_type: str) -> str:
    """Map stored column data_type to the public API word."""
    return "text" if data_type == "string" else "number"


def monitor_fields_payload(monitor: Monitor) -> List[Dict[str, str]]:
    """Short field list for monitor discovery (name, type, unit)."""
    return [
        {
            "name": col.name,
            "type": api_field_type(col.data_type),
            "unit": col.unit_label or "",
        }
        for col in monitor.columns.order_by("order", "name")
    ]


class MonitorSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    class Meta:
        model = Monitor
        fields = "__all__"
        expandable_fields = {
            "tool": "NEMO.serializers.ToolSerializer",
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["fields"] = monitor_fields_payload(instance)
        return data


class MonitorAlertEmailSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    class Meta:
        model = MonitorAlertEmail
        fields = "__all__"
        expandable_fields = {
            "monitor": "NEMO_monitors.api.MonitorSerializer",
        }


class MonitorAlertLogSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    class Meta:
        model = MonitorAlertLog
        fields = "__all__"
        expandable_fields = {
            "monitor": "NEMO_monitors.api.MonitorSerializer",
        }


class MonitorReadingSerializer(Serializer):
    """
    Name-keyed sample for one monitor at one timestamp.

    Preferred shape: monitor + field names as top-level keys (order independent).
    Nested ``fields`` object is still accepted for compatibility with 1.0.3 clients.
    """

    monitor = IntegerField()
    created_date = DateTimeField(required=False, allow_null=True)
    ids = DictField(child=IntegerField(), read_only=True)
    id = IntegerField(read_only=True, required=False)

    def validate(self, attrs):
        monitor_id = attrs["monitor"]
        try:
            monitor = Monitor.objects.prefetch_related("columns").get(pk=monitor_id)
        except Monitor.DoesNotExist:
            raise ValidationError({"monitor": f"Monitor {monitor_id} does not exist."})
        attrs["_monitor"] = monitor

        initial = self.initial_data
        if not isinstance(initial, dict):
            raise ValidationError("Expected an object.")

        nested = initial.get("fields", None)
        used_nested = nested is not None
        if used_nested:
            if not isinstance(nested, dict):
                raise ValidationError({"fields": "Expected an object of field name to value."})
            field_values: Dict[str, Any] = dict(nested)
        else:
            field_values = {k: v for k, v in initial.items() if k not in RESERVED_READING_KEYS}

        has_columns = monitor.columns.exists()
        if has_columns:
            attrs["_field_values"] = field_values
        else:
            if used_nested:
                raise ValidationError(
                    {
                        "fields": "This monitor has no data entry fields. Send 'value' (and optional 'notes') instead."
                    }
                )
            if "value" not in field_values or field_values.get("value") is None:
                raise ValidationError({"value": "This field is required for monitors without data entry fields."})
            extra = set(field_values) - {"value", "notes"}
            if extra:
                unknown = sorted(extra)[0]
                raise ValidationError({unknown: f"Unknown key '{unknown}' for a monitor without data entry fields."})
            try:
                attrs["value"] = float(field_values["value"])
            except (TypeError, ValueError, OverflowError):
                raise ValidationError({"value": f"Expected a number, got {field_values['value']!r}."})
            notes_raw = field_values.get("notes", "")
            attrs["notes"] = "" if notes_raw is None else str(notes_raw)

        created_date = attrs.get("created_date")
        if created_date is None:
            attrs["created_date"] = timezone.now()
        elif timezone.is_naive(created_date):
            attrs["created_date"] = timezone.make_aware(created_date, timezone.get_current_timezone())

        return attrs


def _coerce_field_value(column: MonitorColumn, raw: Any) -> Tuple[Optional[float], str]:
    """Return (numeric_value, string_value) for a column from a raw API value."""
    if raw is None:
        return None, ""
    if isinstance(raw, str) and not raw.strip():
        return None, ""

    if column.data_type == "string":
        return None, str(raw)

    if isinstance(raw, bool):
        raise ValidationError(
            {column.name: f"Expected {'integer' if column.data_type == 'integer' else 'number'}, got boolean."}
        )

    try:
        if column.data_type == "integer":
            return float(int(float(raw))), ""
        return float(raw), ""
    except (TypeError, ValueError, OverflowError):
        raise ValidationError(
            {
                column.name: (
                    f"Expected {'integer' if column.data_type == 'integer' else 'number'}, got {raw!r}."
                )
            }
        )


def _build_multi_column_rows(
    monitor: Monitor, fields: Dict[str, Any], created_date: datetime, user
) -> Tuple[List[MonitorData], Dict[str, Any], Dict[str, str]]:
    """Validate fields and build unsaved MonitorData rows. Returns (rows, display_fields, name_by_col_pk)."""
    by_normalized = columns_by_normalized_name(monitor.columns.all())
    data_points: List[MonitorData] = []
    display_fields: Dict[str, Any] = OrderedDict()
    name_by_col_pk: Dict[str, str] = {}

    for key, raw in fields.items():
        col = match_field_name_to_monitor_column(str(key), by_normalized)
        if col is None:
            raise ValidationError({str(key): f"Unknown field '{key}' for monitor '{monitor.name}'."})
        if isinstance(raw, str) and not raw.strip():
            continue
        if raw is None:
            continue
        value, string_value = _coerce_field_value(col, raw)
        if col.data_type == "string":
            if string_value == "":
                continue
            display_fields[col.name] = string_value
            data_points.append(
                MonitorData(
                    monitor=monitor,
                    column=col,
                    value=None,
                    string_value=string_value,
                    created_date=created_date,
                    created_by=user,
                    updated_by=user,
                )
            )
        else:
            if value is None:
                continue
            display_fields[col.name] = int(value) if col.data_type == "integer" else value
            data_points.append(
                MonitorData(
                    monitor=monitor,
                    column=col,
                    value=value,
                    string_value="",
                    created_date=created_date,
                    created_by=user,
                    updated_by=user,
                )
            )
        name_by_col_pk[str(col.pk)] = col.name

    if not data_points:
        raise ValidationError({"non_field_errors": "Please enter at least one data entry field value."})

    return data_points, display_fields, name_by_col_pk


def _flat_reading_response(
    monitor_id: int,
    created_date: datetime,
    display_fields: Dict[str, Any],
    ids: Dict[str, int],
) -> dict:
    """Build the public reading dict: monitor, created_date, field names as keys, plus ids."""
    result: Dict[str, Any] = {
        "monitor": monitor_id,
        "created_date": created_date,
    }
    result.update(display_fields)
    result["ids"] = ids
    return result


def _create_reading(validated: dict, user) -> dict:
    monitor: Monitor = validated["_monitor"]
    created_date: datetime = validated["created_date"]

    if monitor.columns.exists():
        data_points, display_fields, name_by_col_pk = _build_multi_column_rows(
            monitor, validated["_field_values"], created_date, user
        )
        with transaction.atomic():
            created = MonitorData.objects.bulk_create(data_points)
            refresh_monitor_last_value(monitor)
            process_alerts_after_bulk_create(monitor, created)

        ids = {}
        for row in created:
            field_name = name_by_col_pk.get(str(row.column_id)) or (row.column.name if row.column_id else "")
            if field_name:
                ids[field_name] = row.id
                if field_name not in display_fields:
                    if row.column and row.column.data_type == "string":
                        display_fields[field_name] = row.string_value
                    else:
                        display_fields[field_name] = row.value

        return _flat_reading_response(monitor.pk, created_date, display_fields, ids)

    notes = (validated.get("notes") or "").strip()
    data_point = MonitorData.objects.create(
        monitor=monitor,
        value=validated["value"],
        created_date=created_date,
        notes=notes,
        created_by=user,
        updated_by=user,
    )
    return {
        "monitor": monitor.pk,
        "created_date": data_point.created_date,
        "value": data_point.value,
        "notes": data_point.notes or "",
        "id": data_point.id,
    }


def _display_value_for_point(point: MonitorData) -> Any:
    if point.column and point.column.data_type == "string":
        return point.string_value
    if point.column and point.column.data_type == "integer" and point.value is not None:
        return int(point.value)
    if point.value is not None:
        return point.value
    if point.notes:
        return point.notes
    return None


def _group_monitor_data_into_readings(points: List[MonitorData]) -> List[dict]:
    """Pivot MonitorData rows sharing (monitor_id, created_date) into flat reading dicts."""
    groups: OrderedDict[Tuple[int, datetime], dict] = OrderedDict()
    for point in points:
        key = (point.monitor_id, point.created_date)
        if key not in groups:
            groups[key] = {
                "monitor": point.monitor_id,
                "created_date": point.created_date,
                "display_fields": OrderedDict(),
                "ids": OrderedDict(),
                "_has_columns": False,
                "_legacy_value": None,
                "_legacy_notes": "",
                "_legacy_id": None,
            }
        entry = groups[key]
        if point.column_id:
            entry["_has_columns"] = True
            name = point.column.name
            entry["display_fields"][name] = _display_value_for_point(point)
            entry["ids"][name] = point.id
        else:
            entry["_legacy_value"] = point.value
            entry["_legacy_notes"] = point.notes or ""
            entry["_legacy_id"] = point.id

    readings = []
    for entry in groups.values():
        if entry["_has_columns"]:
            readings.append(
                _flat_reading_response(
                    entry["monitor"],
                    entry["created_date"],
                    dict(entry["display_fields"]),
                    dict(entry["ids"]),
                )
            )
        else:
            readings.append(
                {
                    "monitor": entry["monitor"],
                    "created_date": entry["created_date"],
                    "value": entry["_legacy_value"],
                    "notes": entry["_legacy_notes"],
                    "id": entry["_legacy_id"],
                }
            )
    return readings


class MonitorReadingViewSet(ViewSet):
    """
    Name-keyed monitor samples.

    POST one object or a list of objects with monitor plus field names as keys
    (or a nested fields object). Legacy monitors without data entry fields use value/notes.
    GET requires ?monitor=<id> and returns samples grouped by created_date.
    """

    # NEMO's DjangoModelPermissions resolves view/add/change/delete from this model.
    queryset = MonitorData.objects.all()

    def list(self, request):
        monitor_param = request.query_params.get("monitor")
        if not monitor_param:
            raise ValidationError({"monitor": "This query parameter is required."})
        try:
            monitor_id = int(monitor_param)
        except (TypeError, ValueError):
            raise ValidationError({"monitor": "Must be an integer monitor id."})

        qs = (
            MonitorData.objects.filter(monitor_id=monitor_id)
            .select_related("column")
            .order_by("-created_date", "-id")
        )

        created_date_exact = request.query_params.get("created_date")
        created_date_gte = request.query_params.get("created_date__gte")
        created_date_lte = request.query_params.get("created_date__lte")
        created_date_gt = request.query_params.get("created_date__gt")
        created_date_lt = request.query_params.get("created_date__lt")

        def _parse_filter_dt(raw: str, label: str) -> datetime:
            parsed = parse_datetime(raw)
            if parsed is None:
                raise ValidationError({label: f"Could not parse datetime '{raw}'."})
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            return parsed

        if created_date_exact:
            qs = qs.filter(created_date=_parse_filter_dt(created_date_exact, "created_date"))
        if created_date_gte:
            qs = qs.filter(created_date__gte=_parse_filter_dt(created_date_gte, "created_date__gte"))
        if created_date_lte:
            qs = qs.filter(created_date__lte=_parse_filter_dt(created_date_lte, "created_date__lte"))
        if created_date_gt:
            qs = qs.filter(created_date__gt=_parse_filter_dt(created_date_gt, "created_date__gt"))
        if created_date_lt:
            qs = qs.filter(created_date__lt=_parse_filter_dt(created_date_lt, "created_date__lt"))

        return Response(_group_monitor_data_into_readings(list(qs)))

    @transaction.atomic
    def create(self, request):
        many = isinstance(request.data, list)
        serializer = MonitorReadingSerializer(data=request.data, many=many)
        serializer.is_valid(raise_exception=True)
        user = request.user if getattr(request.user, "is_authenticated", False) else None

        if many:
            results = [_create_reading(item, user) for item in serializer.validated_data]
            return Response(results, status=status.HTTP_201_CREATED)

        result = _create_reading(serializer.validated_data, user)
        return Response(result, status=status.HTTP_201_CREATED)


class MonitorViewSet(ModelViewSet):
    filename = "monitors"
    queryset = Monitor.objects.prefetch_related("columns").all()
    serializer_class = MonitorSerializer
    filterset_fields = {
        "id": key_filters,
        "name": string_filters,
        "visible": boolean_filters,
        "tool": key_filters,
        "last_read": datetime_filters,
        "last_value": number_filters,
    }


class MonitorAlertEmailViewSet(ModelViewSet):
    filename = "monitor_alert_emails"
    queryset = MonitorAlertEmail.objects.all()
    serializer_class = MonitorAlertEmailSerializer
    filterset_fields = {
        "id": key_filters,
        "enabled": boolean_filters,
        "monitor": key_filters,
        "trigger_no_data": boolean_filters,
        "trigger_condition": string_filters,
        "triggered_on": datetime_filters,
        "column": key_filters,
        "recipient_emails": string_filters,
    }


class MonitorAlertLogViewSet(XLSXFileMixin, ReadOnlyModelViewSet):
    filename = "monitor_alert_logs"
    queryset = MonitorAlertLog.objects.all()
    serializer_class = MonitorAlertLogSerializer
    filterset_fields = {
        "id": key_filters,
        "monitor": key_filters,
        "time": datetime_filters,
        "value": number_filters,
        "reset": boolean_filters,
        "condition": string_filters,
        "no_data": boolean_filters,
    }
