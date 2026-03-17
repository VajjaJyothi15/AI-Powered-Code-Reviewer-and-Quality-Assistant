"""Compute simple code metrics for Python files."""

from __future__ import annotations

import ast
from typing import Any


def _function_complexity(node: ast.AST) -> int:
    complexity = 1
    decision_nodes = (
        ast.If,
        ast.For,
        ast.While,
        ast.With,
        ast.Try,
        ast.BoolOp,
        ast.IfExp,
        ast.Match,
    )
    for child in ast.walk(node):
        if isinstance(child, decision_nodes):
            complexity += 1
    return complexity


def analyze_file(file_path: str) -> dict[str, Any]:
    """Analyze a Python file and return maintainability + function metrics."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        return {"maintainability_index": 0, "functions": []}

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return {"maintainability_index": 0, "functions": []}

    functions: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = _function_complexity(node)
            line_count = (node.end_lineno or node.lineno) - node.lineno + 1
            arg_count = len(node.args.args) + len(node.args.kwonlyargs)
            arg_count += len(getattr(node.args, "posonlyargs", []))

            functions.append(
                {
                    "name": node.name,
                    "complexity": complexity,
                    "lines": line_count,
                    "args": arg_count,
                }
            )

    total_lines = len(source.splitlines())
    avg_complexity = (
        sum(f["complexity"] for f in functions) / len(functions)
        if functions
        else 0
    )

    penalty = (total_lines * 0.1) + (len(functions) * 2) + (avg_complexity * 2)
    maintainability_index = max(0, round(100 - penalty, 2))

    return {
        "maintainability_index": maintainability_index,
        "functions": functions,
    }
