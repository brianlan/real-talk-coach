from __future__ import annotations

from contextlib import contextmanager
from typing import Any


@contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None):
    span = {"name": name, "attributes": attributes or {}}
    try:
        yield span
    finally:
        return
