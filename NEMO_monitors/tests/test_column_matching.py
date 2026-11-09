from django.test import SimpleTestCase

from NEMO_monitors.column_matching import (
    RESERVED_READING_KEYS,
    columns_by_normalized_name,
    match_field_name_to_monitor_column,
    normalize_monitor_field_label,
)
from NEMO_monitors.models import MonitorColumn


class ReservedReadingKeysTests(SimpleTestCase):
    def test_reserved_keys_for_flat_readings_api(self):
        self.assertEqual(
            RESERVED_READING_KEYS,
            frozenset({"monitor", "created_date", "id", "ids", "fields"}),
        )


class NormalizeMonitorFieldLabelTests(SimpleTestCase):
    def test_lowercases_and_collapses_whitespace(self):
        self.assertEqual(normalize_monitor_field_label("  Cylinder   ID  "), "cylinder id")

    def test_empty(self):
        self.assertEqual(normalize_monitor_field_label(""), "")
        self.assertEqual(normalize_monitor_field_label(None), "")


class MatchFieldNameToMonitorColumnTests(SimpleTestCase):
    def setUp(self):
        self.weight = MonitorColumn(pk=1, name="Weight Remaining", data_type="float")
        self.cylinder = MonitorColumn(pk=2, name="Cylinder ID", data_type="string")
        self.notes = MonitorColumn(pk=3, name="Notes", data_type="string")
        self.pressure = MonitorColumn(pk=4, name="Pressure (%)", data_type="float")
        self.by_name = columns_by_normalized_name(
            [self.weight, self.cylinder, self.notes, self.pressure]
        )

    def test_exact_and_case_insensitive(self):
        self.assertEqual(
            match_field_name_to_monitor_column("weight remaining", self.by_name),
            self.weight,
        )
        self.assertEqual(
            match_field_name_to_monitor_column("CYLINDER ID", self.by_name),
            self.cylinder,
        )

    def test_order_independent_lookup(self):
        # Matching does not depend on insertion order of the map keys.
        self.assertIs(
            match_field_name_to_monitor_column("Notes", self.by_name),
            self.notes,
        )
        self.assertIs(
            match_field_name_to_monitor_column("Weight Remaining", self.by_name),
            self.weight,
        )

    def test_trailing_unit_parenthetical_on_request(self):
        col = MonitorColumn(pk=5, name="Pressure", data_type="float")
        by_name = columns_by_normalized_name([col])
        self.assertEqual(
            match_field_name_to_monitor_column("Pressure (%)", by_name),
            col,
        )

    def test_trailing_unit_parenthetical_on_defined_name(self):
        self.assertEqual(
            match_field_name_to_monitor_column("Pressure", self.by_name),
            self.pressure,
        )

    def test_unknown_returns_none(self):
        self.assertIsNone(match_field_name_to_monitor_column("Temperature", self.by_name))
