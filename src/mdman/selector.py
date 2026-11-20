from __future__ import annotations

from collections.abc import Mapping
from enum import Enum


class Missing(Enum):
    MISSING = "missing"


MISSING = Missing.MISSING


def select(record: Mapping[str, object], key: str) -> object:
    """Return the top-level value for key, or MISSING if absent."""
    return record.get(key, MISSING)
