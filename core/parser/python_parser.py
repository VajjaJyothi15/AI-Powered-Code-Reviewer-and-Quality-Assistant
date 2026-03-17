"""Python source parser utilities."""

from __future__ import annotations

import ast
import os
from typing import Any


def _annotation_to_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def parse_file(file_path: str) -> dict[str, Any]:
    """Parse a single Python file and extract function metadata."""
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return {"file_path": file_path, "functions": []}

    functions: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = []
            for arg in node.args.args:
                args.append(
                    {
                        "name": arg.arg,
                        "annotation": _annotation_to_str(arg.annotation),
                    }
                )

            fn_meta = {
                "name": node.name,
                "args": args,
                "has_docstring": ast.get_docstring(node) is not None,
                "returns": _annotation_to_str(node.returns),
            }
            functions.append(fn_meta)

    return {"file_path": file_path, "functions": functions}


def parse_path(path: str) -> list[dict[str, Any]]:
    """Parse a path that can be a file or directory."""
    if os.path.isfile(path):
        if path.endswith(".py"):
            return [parse_file(path)]
        return []

    if not os.path.isdir(path):
        return []

    results: list[dict[str, Any]] = []
    for root, _dirs, files in os.walk(path):
        for name in files:
            if name.endswith(".py"):
                file_path = os.path.join(root, name)
                results.append(parse_file(file_path))
    return results
