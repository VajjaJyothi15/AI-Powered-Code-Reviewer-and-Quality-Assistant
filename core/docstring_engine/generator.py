"""Docstring generation utilities."""

from __future__ import annotations


def _format_args(args: list[dict]) -> list[tuple[str, str]]:
    formatted = []
    for arg in args:
        name = arg.get("name", "")
        annotation = arg.get("annotation") or ""
        formatted.append((name, annotation))
    return formatted


def generate_docstring(fn: dict, style: str = "google") -> str:
    """Generate a docstring for a function based on style."""
    name = fn.get("name", "function")
    args = _format_args(fn.get("args", []))
    returns = fn.get("returns")
    returns_str = str(returns) if returns is not None else "None"

    if style == "google":
        lines = [f"{name} summary.", ""]
        if args:
            lines.append("Args:")
            for arg_name, annotation in args:
                type_part = f" ({annotation})" if annotation else ""
                lines.append(f"    {arg_name}{type_part}: Description.")
        lines.append("")
        lines.append("Returns:")
        lines.append(f"    {returns_str}: Description.")
        return "\n".join(lines)

    if style == "numpy":
        lines = [f"{name} summary.", ""]
        if args:
            lines.append("Parameters")
            lines.append("----------")
            for arg_name, annotation in args:
                type_part = f" : {annotation}" if annotation else ""
                lines.append(f"{arg_name}{type_part}")
                lines.append("    Description.")
        lines.append("")
        lines.append("Returns")
        lines.append("-------")
        lines.append(f"{returns_str}")
        lines.append("    Description.")
        return "\n".join(lines)

    if style == "rest":
        lines = [f"{name} summary.", ""]
        for arg_name, annotation in args:
            type_part = f" ({annotation})" if annotation else ""
            lines.append(f":param {arg_name}: Description.{type_part}")
        lines.append(f":return: {returns_str}")
        return "\n".join(lines)

    raise ValueError(f"Unknown style: {style}")
