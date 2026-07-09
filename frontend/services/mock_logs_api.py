from __future__ import annotations

from copy import deepcopy
from typing import Any


_LOG_STORE: list[dict[str, Any]] = [
    {
        "timestamp": "2026-07-09T09:00:00",
        "event": "boot",
        "status": "ready",
        "summary": "Frontend mock service is ready.",
    }
]


def append_log_entry(entry: dict[str, Any]) -> None:
    _LOG_STORE.append(deepcopy(entry))


def get_recent_logs() -> list[dict[str, Any]]:
    return deepcopy(_LOG_STORE[-50:])