"""Docstring validation and complexity utilities."""

from __future__ import annotations

import ast
from typing import Any


def validate_docstrings(file_path: str) -> list[Any]:
    """Validate docstrings for functions in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        return ["missing file: docstring validation skipped"]

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return ["syntax error: docstring validation skipped"]

    errors: list[Any] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is None:
                errors.append(
                    {
                        "function": node.name,
                        "message": f"missing docstring for function {node.name}",
                    }
                )
    return errors


def compute_complexity(source: str) -> list[dict[str, Any]]:
    """Compute a simple cyclomatic complexity per function."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1
            for child in ast.walk(node):
                if isinstance(
                    child,
                    (
                        ast.If,
                        ast.For,
                        ast.While,
                        ast.With,
                        ast.Try,
                        ast.BoolOp,
                        ast.IfExp,
                    ),
                ):
                    complexity += 1
            results.append({"name": node.name, "complexity": complexity})
    return results
