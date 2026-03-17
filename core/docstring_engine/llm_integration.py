"""LLM integration stub for docstring content generation."""

from __future__ import annotations


def generate_docstring_content(fn: dict) -> dict:
    """Generate structured docstring content without external calls."""
    args = {a.get("name", "arg"): "Description" for a in fn.get("args", [])}
    returns = fn.get("returns")
    return {
        "summary": f"Auto-generated summary for {fn.get('name', 'function')}.",
        "args": args,
        "returns": "None" if returns is None else str(returns),
        "raises": {},
    }
