from __future__ import annotations

import statistics
from typing import List, Optional

from NEMO_monitors.models import CONTROL_LIMITS_FIXED, CONTROL_LIMITS_STATISTICAL


def _numeric_values(values: List[Optional[float]]) -> List[float]:
    result: List[float] = []
    for value in values:
        if value is None:
            continue
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            continue
    return result


def compute_control_limits(
    values: List[Optional[float]],
    mode: str,
    fixed_min: Optional[float] = None,
    fixed_max: Optional[float] = None,
) -> Optional[dict]:
    """
    Compute control limit lines for chart display.

    Statistical mode: centerline (mean), UCL/LCL at mean ± 3σ (sample stdev, n >= 2).
    Fixed mode: LCL from fixed_min, UCL from fixed_max; no centerline.
    Returns None when limits cannot be computed.
    """
    if mode == CONTROL_LIMITS_STATISTICAL:
        numeric = _numeric_values(values)
        if len(numeric) < 2:
            return None
        centerline = statistics.mean(numeric)
        sigma = statistics.stdev(numeric)
        return {
            "centerline": centerline,
            "ucl": centerline + 3 * sigma,
            "lcl": centerline - 3 * sigma,
        }

    if mode == CONTROL_LIMITS_FIXED:
        if fixed_min is None and fixed_max is None:
            return None
        result = {}
        if fixed_min is not None:
            result["lcl"] = float(fixed_min)
        if fixed_max is not None:
            result["ucl"] = float(fixed_max)
        return result or None

    return None
