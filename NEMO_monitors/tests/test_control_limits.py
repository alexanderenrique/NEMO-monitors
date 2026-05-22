from django.test import SimpleTestCase

from NEMO_monitors.control_limits import compute_control_limits
from NEMO_monitors.models import CONTROL_LIMITS_FIXED, CONTROL_LIMITS_STATISTICAL


class ComputeControlLimitsTests(SimpleTestCase):
    def test_statistical_known_values(self):
        values = [10.0, 20.0, 30.0]
        result = compute_control_limits(values, CONTROL_LIMITS_STATISTICAL)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["centerline"], 20.0)
        self.assertAlmostEqual(result["ucl"], 20.0 + 3 * 10.0)
        self.assertAlmostEqual(result["lcl"], 20.0 - 3 * 10.0)

    def test_statistical_single_value_returns_none(self):
        self.assertIsNone(compute_control_limits([5.0], CONTROL_LIMITS_STATISTICAL))

    def test_statistical_empty_returns_none(self):
        self.assertIsNone(compute_control_limits([], CONTROL_LIMITS_STATISTICAL))

    def test_statistical_filters_none(self):
        values = [10.0, None, 30.0]
        result = compute_control_limits(values, CONTROL_LIMITS_STATISTICAL)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["centerline"], 20.0)

    def test_statistical_zero_stdev(self):
        values = [5.0, 5.0, 5.0]
        result = compute_control_limits(values, CONTROL_LIMITS_STATISTICAL)
        self.assertAlmostEqual(result["centerline"], 5.0)
        self.assertAlmostEqual(result["ucl"], 5.0)
        self.assertAlmostEqual(result["lcl"], 5.0)

    def test_fixed_min_only(self):
        result = compute_control_limits([], CONTROL_LIMITS_FIXED, fixed_min=100.0)
        self.assertEqual(result, {"lcl": 100.0})
        self.assertNotIn("ucl", result)
        self.assertNotIn("centerline", result)

    def test_fixed_max_only(self):
        result = compute_control_limits([], CONTROL_LIMITS_FIXED, fixed_max=200.0)
        self.assertEqual(result, {"ucl": 200.0})

    def test_fixed_both(self):
        result = compute_control_limits([], CONTROL_LIMITS_FIXED, fixed_min=100.0, fixed_max=200.0)
        self.assertEqual(result["lcl"], 100.0)
        self.assertEqual(result["ucl"], 200.0)

    def test_fixed_without_bounds_returns_none(self):
        self.assertIsNone(compute_control_limits([], CONTROL_LIMITS_FIXED))

    def test_none_mode_returns_none(self):
        self.assertIsNone(compute_control_limits([1.0, 2.0], ""))
