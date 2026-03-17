"""Docstring coverage reporter."""

from __future__ import annotations

from typing import Any


def compute_coverage(parsed: list[dict[str, Any]], threshold: int = 80) -> dict[str, Any]:
    """Compute aggregate docstring coverage from parsed metadata."""
    total_functions = 0
    documented = 0

    for file_meta in parsed:
        functions = file_meta.get("functions", [])
        total_functions += len(functions)
        documented += sum(1 for fn in functions if fn.get("has_docstring"))

    coverage_percent = 0
    if total_functions:
        coverage_percent = round((documented / total_functions) * 100)

    aggregate = {
        "total_functions": total_functions,
        "documented": documented,
        "coverage_percent": coverage_percent,
        "meets_threshold": coverage_percent >= threshold if total_functions else False,
    }
    return {"aggregate": aggregate}
