"""Match monitor field labels (CSV headers, API field names) to MonitorColumn records."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional

from NEMO_monitors.models import MonitorColumn

# Top-level keys that are never treated as data entry field names on a reading.
RESERVED_READING_KEYS = frozenset({"monitor", "created_date", "id", "ids", "fields"})


def normalize_monitor_field_label(raw: str) -> str:
    """Normalize a monitor/CSV field label for comparison (unicode, spaces, case)."""
    s = unicodedata.normalize("NFKC", (raw or "").strip())
    s = re.sub(r"[\u00a0\u2000-\u200b\ufeff]", " ", s)
    return " ".join(s.split()).lower()


def _csv_header_inner_looks_like_unit(inner: str) -> bool:
    """True if parenthetical at end of a header is likely a unit, e.g. (%) or (A/min), not (RIE)."""
    s = inner.strip().lower()
    if not s:
        return False
    if "%" in s:
        return True
    if "/" in s:
        return True
    if re.fullmatch(r"[\d\.]+\s*[a-zµμ°/]*|[a-zµμ]\s*\d+", s):
        return True
    return False


def _strip_trailing_unit_parenthetical(label_norm: str) -> Optional[str]:
    """If label_norm ends with ' (unit)', return the part before it when unit is recognized."""
    m = re.search(r"\s+\(([^)]*)\)$", label_norm)
    if not m:
        return None
    inner = m.group(1).strip()
    if not _csv_header_inner_looks_like_unit(inner):
        return None
    return label_norm[: m.start()].strip()


def match_field_name_to_monitor_column(
    header: str, by_normalized_name: Dict[str, MonitorColumn]
) -> Optional[MonitorColumn]:
    """
    Match a field label to a MonitorColumn.

    Handles minor export/format differences vs. defined names: NFC/NFKC unicode, whitespace,
    and optional trailing '(unit)' segments such as '(%)' or '(A/min)' on the label side or on
    the defined field name.
    """
    norm = normalize_monitor_field_label(header)
    if not norm:
        return None
    if norm in by_normalized_name:
        return by_normalized_name[norm]
    stripped = _strip_trailing_unit_parenthetical(norm)
    if stripped and stripped in by_normalized_name:
        return by_normalized_name[stripped]
    for _key, col in by_normalized_name.items():
        key_stripped = _strip_trailing_unit_parenthetical(_key)
        if not key_stripped:
            continue
        if norm == key_stripped or (stripped and stripped == key_stripped):
            return col
    return None


def columns_by_normalized_name(columns) -> Dict[str, MonitorColumn]:
    """Build a lookup map from an iterable of MonitorColumn instances."""
    return {normalize_monitor_field_label(col.name): col for col in columns}
