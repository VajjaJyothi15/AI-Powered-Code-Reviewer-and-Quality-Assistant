"""Minimal dashboard utilities used by tests."""

from __future__ import annotations

import json
import os
from typing import Any


def load_pytest_results() -> dict[str, Any] | None:
    """Load pytest results if present."""
    candidates = [
        "pytest_report.json",
        "pytest_results.json",
        "pytest_output.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
    return None


def filter_functions(
    functions: list[dict[str, Any]],
    search: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Filter functions by search text and docstring status."""
    filtered = functions
    if search:
        search_lower = search.lower()
        filtered = [
            fn
            for fn in filtered
            if search_lower in str(fn.get("name", "")).lower()
        ]

    if status == "OK":
        filtered = [fn for fn in filtered if fn.get("has_docstring") is True]
    elif status == "Fix":
        filtered = [fn for fn in filtered if fn.get("has_docstring") is False]

    return filtered
