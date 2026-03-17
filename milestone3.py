"""Streamlit app for scanning Python files and validating PEP 257 docstrings."""
import os
import ast
import re
import json
import difflib
import subprocess
import hashlib
import time
import html
import importlib
import importlib.util
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
if importlib.util.find_spec("plotly.graph_objects") is not None:
    go = importlib.import_module("plotly.graph_objects")
    PLOTLY_AVAILABLE = True
else:
    go = None
    PLOTLY_AVAILABLE = False
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="AI Code Reviewer",
    page_icon="🤖",
    layout="wide"
)

# ================= UI THEME =================
st.markdown(
    """
    <style>
    :root {
        --primary: #3b82f6;
        --secondary: #8b5cf6;
        --accent: #22d3ee;
        --success: #22c55e;
        --warning: #f59e0b;
        --danger: #ef4444;
        --glass: rgba(15, 23, 42, 0.35);
        --glass-border: rgba(148, 163, 184, 0.35);
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 15%, rgba(56, 189, 248, 0.22), transparent 35%),
            radial-gradient(circle at 85% 10%, rgba(139, 92, 246, 0.24), transparent 40%),
            linear-gradient(130deg, #020617 0%, #0f172a 45%, #111827 100%);
        color: #e2e8f0;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.96));
        border-right: 1px solid rgba(148, 163, 184, 0.22);
    }

    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown, .stCaption, .stMetricLabel, .stMetricValue {
        color: #e2e8f0 !important;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.72), rgba(15, 23, 42, 0.65));
        border: 1px solid var(--glass-border);
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 10px 24px rgba(2, 6, 23, 0.35);
        animation: fadeInUp 0.55s ease forwards;
    }

    .glass-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.68), rgba(15, 23, 42, 0.54));
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 12px 26px rgba(2, 6, 23, 0.35);
        backdrop-filter: blur(7px);
        margin-bottom: 12px;
        animation: fadeInUp 0.45s ease forwards;
    }

    .metric-card {
        border-radius: 16px;
        padding: 14px 16px;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.35), rgba(139, 92, 246, 0.25));
        border: 1px solid rgba(148, 163, 184, 0.3);
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.35);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 16px 32px rgba(30, 64, 175, 0.3);
    }

    .doc-card {
        background: linear-gradient(100deg, rgba(37, 99, 235, 0.45), rgba(124, 58, 237, 0.45));
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 14px;
        padding: 12px 14px;
        margin: 10px 0;
        font-weight: 700;
        color: #f8fafc;
    }

    .metric-icon {
        font-size: 22px;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #f8fafc;
        line-height: 1.1;
    }

    .metric-label {
        font-size: 13px;
        color: #cbd5e1;
        letter-spacing: 0.2px;
    }

    .severity-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.2px;
    }

    .severity-high { background: rgba(239, 68, 68, 0.2); color: #fecaca; border: 1px solid rgba(239, 68, 68, 0.45); }
    .severity-medium { background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.45); }
    .severity-low { background: rgba(34, 197, 94, 0.2); color: #bbf7d0; border: 1px solid rgba(34, 197, 94, 0.45); }

    .status-pill {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin-top: 8px;
    }

    .status-success { background: rgba(34, 197, 94, 0.2); color: #bbf7d0; border: 1px solid rgba(34, 197, 94, 0.4); }
    .status-warning { background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.4); }
    .status-error { background: rgba(239, 68, 68, 0.2); color: #fecaca; border: 1px solid rgba(239, 68, 68, 0.4); }

    .rule-pill {
        border: 1px dashed rgba(56, 189, 248, 0.55);
        color: #7dd3fc;
        border-radius: 999px;
        padding: 2px 8px;
        font-size: 12px;
        cursor: help;
    }

    .loader {
        width: 100%;
        height: 6px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.2);
        overflow: hidden;
        margin: 8px 0 14px;
    }

    .loader::before {
        content: "";
        display: block;
        height: 100%;
        width: 35%;
        background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent));
        animation: loading 1.3s ease-in-out infinite;
        border-radius: inherit;
    }

    .fade-in { animation: fadeInUp 0.55s ease forwards; }

    .coverage-highlight {
        background: linear-gradient(130deg, rgba(37, 99, 235, 0.75), rgba(124, 58, 237, 0.75));
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        color: #f8fafc;
        font-size: 24px;
        font-weight: 800;
        box-shadow: 0 12px 26px rgba(2, 6, 23, 0.35);
    }

    .status-box {
        margin-top: 12px;
        border-radius: 999px;
        padding: 8px 14px;
        display: inline-block;
        font-weight: 700;
        border: 1px solid transparent;
    }

    .status-poor {
        background: rgba(239, 68, 68, 0.2);
        color: #fecaca;
        border-color: rgba(239, 68, 68, 0.45);
    }

    .status-average {
        background: rgba(245, 158, 11, 0.2);
        color: #fde68a;
        border-color: rgba(245, 158, 11, 0.45);
    }

    .status-good {
        background: rgba(34, 197, 94, 0.2);
        color: #bbf7d0;
        border-color: rgba(34, 197, 94, 0.45);
    }

    .diff-box {
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 8px;
        background: rgba(15, 23, 42, 0.25);
        padding: 6px 8px;
        font-family: Consolas, "Courier New", monospace;
        font-size: 0.85rem;
        line-height: 1.35;
        overflow-x: auto;
        white-space: pre;
    }

    .diff-meta { color: #93c5fd; }
    .diff-hunk { color: #fcd34d; }
    .diff-add {
        color: #bbf7d0;
        background: rgba(34, 197, 94, 0.18);
        display: block;
    }
    .diff-del {
        color: #fecaca;
        background: rgba(239, 68, 68, 0.18);
        display: block;
    }
    .diff-ctx { color: #cbd5e1; }

    div[data-testid="stButton"] > button {
        border: 0 !important;
        color: #f8fafc !important;
        font-weight: 700 !important;
        border-radius: 11px !important;
        background: linear-gradient(90deg, #16a34a, #22c55e) !important;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.35);
        transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
    }

    div[data-testid="stButton"] > button:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 14px 24px rgba(22, 163, 74, 0.35);
        filter: brightness(1.05);
    }

    div[data-testid="stFileUploader"] section {
        border-radius: 14px !important;
        border: 1px dashed rgba(148, 163, 184, 0.45) !important;
        background: rgba(30, 41, 59, 0.35) !important;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes loading {
        0% { transform: translateX(-120%); }
        100% { transform: translateX(330%); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================= SAFE PARSER =================
def parse_file(file_path):
    """Parse a Python file into an AST, returning ``None`` on parse failure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return ast.parse(f.read())
    except Exception as e:
        st.error(str(e))
        return None

# ================= CORE =================
def extract_functions(tree):
    """Extract function metadata and docstring presence from an AST."""
    return [
        {
            "name": node.name,
            "start": node.lineno,
            "end": node.end_lineno,
            "doc": bool(ast.get_docstring(node))
        }
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]

def docstring_coverage(functions):
    """Compute total, documented count, and percentage of documented functions."""
    total = len(functions)
    documented = sum(1 for f in functions if f["doc"])
    coverage = round((documented / total) * 100, 2) if total else 0
    return total, documented, coverage

def coverage_report(file_path):
    """Build a docstring coverage report dictionary for a Python file."""
    tree = parse_file(file_path)
    if not tree:
        return {}
    functions = extract_functions(tree)
    total, documented, coverage = docstring_coverage(functions)
    return {
        "total_functions": total,
        "documented_functions": documented,
        "undocumented_functions": total - documented,
        "coverage_percent": coverage,
        "details": functions
    }
def calculate_metrics(functions):
    """Return simple maintainability metrics for collected function data."""
    return {
        "maintainability_index": round(100 - len(functions) * 2, 2),
        "functions": functions
    }

def _function_nesting_depth(func_node):
    """Return the maximum nesting depth of control-flow blocks in a function."""
    control_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match)
    max_depth = 0

    def walk(node, depth):
        nonlocal max_depth
        next_depth = depth + 1 if isinstance(node, control_nodes) else depth
        if next_depth > max_depth:
            max_depth = next_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child is not func_node:
                continue
            walk(child, next_depth)

    walk(func_node, 0)
    return max_depth

def analyze_code_quality(tree, source):
    """Analyze non-docstring code quality signals and build a quality report."""
    hotspots = []
    issue_counts = {
        "long_functions": 0,
        "many_args": 0,
        "deep_nesting": 0,
        "print_calls": 0,
        "bare_except": 0,
        "todo_comments": 0,
    }

    issue_counts["todo_comments"] = len(re.findall(r"#\s*(TODO|FIXME|HACK)\b", source, re.IGNORECASE))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            issue_counts["print_calls"] += 1

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issue_counts["bare_except"] += 1

        if isinstance(node, ast.FunctionDef):
            line_count = (node.end_lineno or node.lineno) - node.lineno + 1
            arg_count = (
                len(node.args.args)
                + len(node.args.kwonlyargs)
                + len(getattr(node.args, "posonlyargs", []))
            )
            nesting = _function_nesting_depth(node)

            risk = 0
            if line_count > 40:
                issue_counts["long_functions"] += 1
                risk += 35
            if arg_count > 5:
                issue_counts["many_args"] += 1
                risk += (arg_count - 5) * 8
            if nesting > 3:
                issue_counts["deep_nesting"] += 1
                risk += (nesting - 3) * 12

            if risk > 0:
                hotspots.append(
                    {
                        "function": node.name,
                        "lines": line_count,
                        "args": arg_count,
                        "nesting": nesting,
                        "risk": min(risk, 100),
                    }
                )

    penalty = (
        issue_counts["long_functions"] * 12
        + issue_counts["many_args"] * 8
        + issue_counts["deep_nesting"] * 10
        + issue_counts["print_calls"] * 2
        + issue_counts["bare_except"] * 10
        + issue_counts["todo_comments"] * 3
    )
    quality_score = max(0, 100 - penalty)

    hotspots.sort(key=lambda item: item["risk"], reverse=True)
    return {
        "quality_score": quality_score,
        "issue_counts": issue_counts,
        "hotspots": hotspots[:10],
    }

# ================= PEP 257 ENGINE =================
def attach_parents(tree):
    """Attach ``parent`` references to AST nodes for context-aware checks."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

def check_format_rules(docstring):
    """Validate selected PEP 257 formatting rules for a docstring."""
    violations = []

    if not docstring:
        return violations

    lines = docstring.strip().splitlines()

    # D200
    if len(lines) == 1 and len(lines[0]) > 72:
        violations.append("D200: One-line docstring too long")

    # D205
    if len(lines) > 1 and lines[1].strip() != "":
        violations.append("D205: Blank line required after summary")

    # D401
    first_line = lines[0]
    if first_line.startswith("Returns"):
        violations.append("D401: Use imperative mood (Return, not Returns)")

    return violations

def _extract_item_from_context(context):
    """Extract a display item name from pydocstyle context text."""
    if not context:
        return "Module"
    if "module level" in context:
        return "Module"
    match = re.search(r"`([^`]+)`", context)
    if match:
        return match.group(1)
    return context.strip()

def parse_pydocstyle_violations(lines):
    """Parse pydocstyle output lines into ``(item_name, rule)`` tuples."""
    violations = []
    inline_pattern = re.compile(
        r"^(?P<path>.+?):(?P<line>\d+)(?:\s+(?P<context>.*?))?:\s*(?P<code>D\d{3}):\s*(?P<msg>.+)$"
    )
    context_pattern = re.compile(r"^(?P<path>.+?):(?P<line>\d+)\s+(?P<context>.*):$")
    rule_pattern = re.compile(r"^(?P<code>D\d{3}):\s*(?P<msg>.+)$")

    current_context = ""
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            continue

        inline = inline_pattern.match(line.strip())
        if inline:
            item_name = _extract_item_from_context(inline.group("context") or "")
            rule = f"{inline.group('code')}: {inline.group('msg')}"
            violations.append((item_name, rule))
            continue

        context = context_pattern.match(line.strip())
        if context:
            current_context = context.group("context") or ""
            continue

        rule_match = rule_pattern.match(line.strip())
        if rule_match:
            item_name = _extract_item_from_context(current_context)
            rule = f"{rule_match.group('code')}: {rule_match.group('msg')}"
            violations.append((item_name, rule))

    return violations

def _has_blank_line_after_docstring(lines, doc_expr):
    """Return True if there's a blank line immediately after the docstring."""
    if not doc_expr or not hasattr(doc_expr, "end_lineno"):
        return False
    idx = doc_expr.end_lineno
    if idx is None or idx >= len(lines):
        return False
    return lines[idx].strip() == ""

def get_ast_pep257_violations(tree, source_lines=None):
    """Collect AST-based PEP 257 violations for module, classes, and functions."""
    violations = []

    # Module
    module_doc = ast.get_docstring(tree)
    if not module_doc:
        violations.append(("Module", "D100: Missing module docstring"))
    else:
        for rule in check_format_rules(module_doc):
            violations.append(("Module", rule))

    for node in ast.walk(tree):

        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            if not doc:
                violations.append((node.name, "D101: Missing class docstring"))
            else:
                for rule in check_format_rules(doc):
                    violations.append((node.name, rule))
                if source_lines:
                    doc_expr = _get_docstring_expr(node)
                    if _has_blank_line_after_docstring(source_lines, doc_expr):
                        violations.append((node.name, "D202: No blank lines allowed after docstring"))

        if isinstance(node, ast.FunctionDef):
            parent = getattr(node, "parent", None)
            doc = ast.get_docstring(node)

            if isinstance(parent, ast.ClassDef):
                if not doc:
                    violations.append((node.name, "D102: Missing method docstring"))
                else:
                    for rule in check_format_rules(doc):
                        violations.append((node.name, rule))
                    if source_lines:
                        doc_expr = _get_docstring_expr(node)
                        if _has_blank_line_after_docstring(source_lines, doc_expr):
                            violations.append((node.name, "D202: No blank lines allowed after docstring"))
            else:
                if not doc:
                    violations.append((node.name, "D103: Missing function docstring"))
                else:
                    for rule in check_format_rules(doc):
                        violations.append((node.name, rule))
                    if source_lines:
                        doc_expr = _get_docstring_expr(node)
                        if _has_blank_line_after_docstring(source_lines, doc_expr):
                            violations.append((node.name, "D202: No blank lines allowed after docstring"))

    return violations

def get_pep257_violations(tree, file_path=None):
    """Collect PEP 257 violations using AST checks plus pydocstyle when available."""
    source_lines = None
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_lines = f.read().splitlines(keepends=True)
        except FileNotFoundError:
            source_lines = None

    ast_violations = get_ast_pep257_violations(tree, source_lines=source_lines)
    if not file_path:
        return ast_violations

    pydocstyle_lines = run_pydocstyle(file_path)
    pydocstyle_violations = []
    for item_name, rule in parse_pydocstyle_violations(pydocstyle_lines):
        rule_code = rule.split(":", 1)[0].strip()
        if rule_code == "D204":
            continue
        pydocstyle_violations.append((item_name, rule))
    if not pydocstyle_violations:
        return ast_violations

    merged = []
    seen = set()
    for item_name, rule in pydocstyle_violations + ast_violations:
        key = (item_name, rule)
        if key in seen:
            continue
        seen.add(key)
        merged.append((item_name, rule))
    return merged

# ================= AUTO FIX =================
def auto_fix_docstrings(file_path, target_function=None, fix_all=False):
    """
    Insert placeholder docstrings for missing items.

    - if `fix_all` is True all undocumented module/class/functions are fixed.
    - if `target_function` is given only that name is modified.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    attach_parents(tree)
    lines = source.splitlines(keepends=True)

    inserts = []

    # module docstring
    if not ast.get_docstring(tree) and (fix_all or target_function is None):
        inserts.append(
            (
                0,
                '"""Summary:\n'
                '    Describe the module purpose.\n\n'
                'Args:\n'
                '    None.\n\n'
                'Returns:\n'
                '    None.\n\n'
                'Raises:\n'
                '    None.\n'
                '"""\n\n',
            )
        )

    for node in ast.walk(tree):
        name = getattr(node, "name", None)

        if isinstance(node, ast.ClassDef):
            indent = " " * node.col_offset
            if not ast.get_docstring(node) and (fix_all or target_function == name):
                inserts.append(
                    (
                        node.lineno,
                        f'{indent}    """Summary:\n'
                        f'{indent}        Describe the class purpose.\n\n'
                        f'{indent}    Args:\n'
                        f'{indent}        None.\n\n'
                        f'{indent}    Returns:\n'
                        f'{indent}        None.\n\n'
                        f'{indent}    Raises:\n'
                        f'{indent}        None.\n'
                        f'{indent}    """\n',
                    )
                )

        if isinstance(node, ast.FunctionDef):
            indent = " " * node.col_offset
            parent = getattr(node, "parent", None)
            if not ast.get_docstring(node) and (fix_all or target_function == name):
                if isinstance(parent, ast.ClassDef):
                    inserts.append(
                        (
                            node.lineno,
                            f'{indent}    """Summary:\n'
                            f'{indent}        Describe what the method does.\n\n'
                            f'{indent}    Args:\n'
                            f'{indent}        Describe method parameters.\n\n'
                            f'{indent}    Returns:\n'
                            f'{indent}        Describe returned value.\n\n'
                            f'{indent}    Raises:\n'
                            f'{indent}        Describe possible exceptions.\n'
                            f'{indent}    """\n',
                        )
                    )
                else:
                    inserts.append(
                        (
                            node.lineno,
                            f'{indent}    """Summary:\n'
                            f'{indent}        Describe what the function does.\n\n'
                            f'{indent}    Args:\n'
                            f'{indent}        Describe function parameters.\n\n'
                            f'{indent}    Returns:\n'
                            f'{indent}        Describe returned value.\n\n'
                            f'{indent}    Raises:\n'
                            f'{indent}        Describe possible exceptions.\n'
                            f'{indent}    """\n',
                        )
                    )

    for ln, text in sorted(inserts, reverse=True):
        lines.insert(ln, text)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def _get_docstring_expr(node):
    """Return the AST expression node containing a docstring, if present."""
    if not hasattr(node, "body") or not node.body:
        return None
    first_stmt = node.body[0]
    if not isinstance(first_stmt, ast.Expr):
        return None
    value = first_stmt.value
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return first_stmt
    return None

def _replace_docstring_text(file_path, node, new_docstring):
    """Replace a node docstring text with a normalized triple-quoted form."""
    doc_expr = _get_docstring_expr(node)
    if not doc_expr:
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)

    indent = " " * doc_expr.col_offset
    doc_lines = new_docstring.strip().splitlines()
    if not doc_lines:
        doc_lines = ["Description."]

    replacement = []
    if len(doc_lines) == 1:
        replacement.append(f'{indent}"""{doc_lines[0]}"""\n')
    else:
        replacement.append(f'{indent}"""{doc_lines[0]}\n')
        for line in doc_lines[1:]:
            replacement.append(f"{indent}{line}\n")
        replacement.append(f'{indent}"""\n')

    start = doc_expr.lineno - 1
    end = doc_expr.end_lineno
    lines[start:end] = replacement

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True

def _replace_docstring_text_with_second_line_summary(file_path, node, new_docstring):
    """Replace a node docstring using D213 style summary on the second line."""
    doc_expr = _get_docstring_expr(node)
    if not doc_expr:
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)

    indent = " " * doc_expr.col_offset
    doc_lines = new_docstring.strip().splitlines()
    if not doc_lines:
        doc_lines = ["Description."]

    replacement = [f'{indent}"""\n']
    for line in doc_lines:
        replacement.append(f"{indent}{line}\n")
    replacement.append(f'{indent}"""\n')

    start = doc_expr.lineno - 1
    end = doc_expr.end_lineno
    lines[start:end] = replacement

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True

def _fix_blank_lines_around_docstring(file_path, node, rule_code):
    """Fix blank-line placement rules around a node docstring."""
    doc_expr = _get_docstring_expr(node)
    if not doc_expr:
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)

    changed = False

    if rule_code in {"D201", "D211"}:
        start = node.lineno
        end = doc_expr.lineno - 1
        if end > start:
            for idx in range(end - 1, start - 1, -1):
                if lines[idx].strip() == "":
                    del lines[idx]
                    changed = True

    elif rule_code == "D202":
        idx = doc_expr.end_lineno
        while idx < len(lines) and lines[idx].strip() == "":
            del lines[idx]
            changed = True

    elif rule_code == "D204":
        idx = doc_expr.end_lineno
        if idx < len(lines) and lines[idx].strip() != "":
            indent = " " * (node.col_offset + 4)
            lines.insert(idx, f"{indent}\n")
            changed = True

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    return changed

def _apply_text_rule(lines, rule_code, node_name):
    """Apply a single text-level docstring rule transformation."""
    changed = False

    if rule_code == "D200":
        if len(lines) == 1 and len(lines[0]) > 72:
            lines[0] = f"{lines[0][:69].rstrip()}..."
            changed = True
    elif rule_code == "D205":
        if len(lines) > 1 and lines[1].strip() != "":
            lines.insert(1, "")
            changed = True
    elif rule_code == "D210":
        new_lines = [line.strip() for line in lines]
        if new_lines != lines:
            lines[:] = new_lines
            changed = True
    elif rule_code == "D400":
        if lines and not lines[0].rstrip().endswith("."):
            lines[0] = lines[0].rstrip(".!? ") + "."
            changed = True
    elif rule_code == "D401":
        if lines:
            summary = lines[0].strip()
            if summary:
                parts = summary.split(maxsplit=1)
                first = parts[0]
                rest = parts[1] if len(parts) > 1 else ""
                lower_first = first.lower()

                replacements = {
                    "returns": "Return",
                    "gets": "Get",
                    "fetches": "Fetch",
                    "reads": "Read",
                    "loads": "Load",
                    "retrieves": "Retrieve",
                    "sets": "Set",
                    "updates": "Update",
                    "calculates": "Calculate",
                    "computes": "Compute",
                    "finds": "Find",
                    "searches": "Search",
                    "locates": "Locate",
                    "processes": "Process",
                    "handles": "Handle",
                    "creates": "Create",
                    "builds": "Build",
                    "makes": "Make",
                    "parses": "Parse",
                    "validates": "Validate",
                    "converts": "Convert",
                    "checks": "Check",
                    "determines": "Determine",
                    "generates": "Generate",
                    "adds": "Add",
                    "removes": "Remove",
                    "does": "Do",
                    "has": "Have",
                }

                new_first = replacements.get(lower_first)
                if not new_first and re.match(r"^[A-Za-z]+s$", first):
                    if lower_first not in {"is", "was"}:
                        new_first = first[:-1].capitalize()

                if lower_first in {"is", "can", "should"}:
                    rewritten = f"Return whether {summary[0].lower() + summary[1:]}".rstrip()
                    lines[0] = rewritten
                    changed = True
                elif new_first and new_first != first:
                    lines[0] = f"{new_first} {rest}".rstrip()
                    changed = True
    elif rule_code == "D403":
        if lines and lines[0]:
            first = lines[0][0]
            upper = first.upper()
            if first != upper:
                lines[0] = upper + lines[0][1:]
                changed = True
    elif rule_code == "D404":
        if lines and lines[0].startswith("This "):
            lines[0] = "Describe " + lines[0][5:]
            changed = True
    elif rule_code == "D415":
        if lines and lines[0] and lines[0][-1] not in ".!?":
            lines[0] = f"{lines[0].rstrip()}."
            changed = True
    elif rule_code == "D402":
        signature_prefix = f"{node_name}("
        if lines and lines[0].lstrip().startswith(signature_prefix):
            lines[0] = f"Describe {node_name}."
            changed = True

    return changed

def _split_name_words(name):
    """Split snake_case or CamelCase names into readable lowercase words."""
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [part for part in snake.replace("__", "_").split("_") if part]

def _title_from_name(name):
    """Build a title fragment from an identifier name."""
    words = _split_name_words(name)
    return " ".join(words) if words else name

def _suggest_docstring_for_node(node, parent=None):
    """Generate a concise, meaningful docstring summary for a node."""
    if isinstance(node, ast.ClassDef):
        return f"Represent {_title_from_name(node.name)}."

    if not isinstance(node, ast.FunctionDef):
        return "Describe this object."

    title = _title_from_name(node.name)
    prefixes = _split_name_words(node.name)
    first = prefixes[0].lower() if prefixes else node.name.lower()

    if first in {"get", "fetch", "read", "load", "retrieve"}:
        return f"Return {title.replace(first, '', 1).strip() or 'the requested value'}."
    if first in {"is", "has", "can", "should"}:
        return f"Return whether {title}."
    if first in {"set", "update"}:
        return f"Set {title.replace(first, '', 1).strip() or 'the target value'}."
    if first in {"calculate", "compute"}:
        return f"Compute {title.replace(first, '', 1).strip() or 'the requested value'}."
    if first in {"find", "search", "locate"}:
        return f"Find {title.replace(first, '', 1).strip() or 'the matching value'}."
    if first in {"process", "handle"}:
        return f"Process {title.replace(first, '', 1).strip() or 'the input data'}."
    if first in {"add", "create", "build", "make"}:
        return f"Create {title.replace(first, '', 1).strip() or 'the target object'}."

    if isinstance(parent, ast.ClassDef):
        return f"Handle {title}."
    return f"Perform {title}."

def _is_generic_docstring(doc):
    """Return True when a docstring is generic placeholder text."""
    if not doc:
        return False
    normalized = " ".join(doc.strip().lower().split())
    generic_patterns = {
        "auto-generated docstring.",
        "module description.",
        "class description.",
        "method description.",
        "function description.",
        "todo.",
        "tbd.",
    }
    if normalized in generic_patterns:
        return True
    if normalized.startswith("this function"):
        return True
    return False

def collect_generic_docstrings(file_path):
    """Collect nodes that still use generic placeholder docstrings."""
    tree = parse_file(file_path)
    if not tree:
        return []
    attach_parents(tree)

    generic_items = []
    module_doc = ast.get_docstring(tree, clean=True)
    if _is_generic_docstring(module_doc):
        generic_items.append(("Module", module_doc))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            continue
        doc = ast.get_docstring(node, clean=True)
        if _is_generic_docstring(doc):
            generic_items.append((node.name, doc))
    return generic_items

def improve_generic_docstrings(file_path):
    """Replace generic placeholder docstrings with generated meaningful summaries."""
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    attach_parents(tree)

    changed = False

    module_doc = ast.get_docstring(tree, clean=True)
    if _is_generic_docstring(module_doc):
        changed = _replace_docstring_text(file_path, tree, "Provide module-level utilities.") or changed

    # Process deepest nodes first to avoid line-offset drift while rewriting.
    sortable_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            doc = ast.get_docstring(node, clean=True)
            if _is_generic_docstring(doc):
                sortable_nodes.append(node)
    sortable_nodes.sort(key=lambda n: getattr(n, "lineno", 0), reverse=True)

    for node in sortable_nodes:
        parent = getattr(node, "parent", None)
        suggestion = _suggest_docstring_for_node(node, parent=parent)
        if _replace_docstring_text(file_path, node, suggestion):
            changed = True

    return changed

def _find_target_node(tree, item_name, rule_code):
    """Find the AST node that corresponds to the given violation item."""
    if item_name == "Module":
        return tree

    node_rules = {
        "D101",
        "D102",
        "D103",
        "D105",
        "D106",
        "D107",
        "D200",
        "D201",
        "D202",
        "D204",
        "D205",
        "D210",
        "D211",
        "D212",
        "D213",
        "D300",
        "D400",
        "D401",
        "D402",
        "D403",
        "D404",
        "D415",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == item_name:
            if rule_code in node_rules:
                return node

        if isinstance(node, ast.FunctionDef) and node.name == item_name:
            parent = getattr(node, "parent", None)
            if rule_code in {"D102", "D105", "D107"} and isinstance(parent, ast.ClassDef):
                return node
            if rule_code == "D103" and not isinstance(parent, ast.ClassDef):
                return node
            if rule_code in node_rules:
                return node

    return None

def _normalize_llm_docstring(raw_text):
    """Normalize LLM output to plain docstring content without quote wrappers."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:python)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    if text.startswith('"""') and text.endswith('"""') and len(text) >= 6:
        text = text[3:-3].strip()
    return text

def collect_function_docstrings(file_path):
    """Collect function metadata and current docstrings from a Python file."""
    tree = parse_file(file_path)
    if not tree:
        return []

    with open(file_path, "r", encoding="utf-8") as source_file:
        source = source_file.read()

    attach_parents(tree)
    functions = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        parent = getattr(node, "parent", None)
        if isinstance(parent, ast.ClassDef):
            qualified_name = f"{parent.name}.{node.name}"
        else:
            qualified_name = node.name

        current_doc = ast.get_docstring(node, clean=True) or ""
        function_code = ast.get_source_segment(source, node) or ""
        functions.append(
            {
                "qualified_name": qualified_name,
                "name": node.name,
                "lineno": node.lineno,
                "docstring": current_doc,
                "source": function_code,
                "params": [arg.arg for arg in node.args.args],
            }
        )

    functions.sort(key=lambda item: item["lineno"])
    return functions

def _find_function_node_by_qualified_name(tree, qualified_name):
    """Find a function AST node by its qualified display name."""
    attach_parents(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        parent = getattr(node, "parent", None)
        node_name = f"{parent.name}.{node.name}" if isinstance(parent, ast.ClassDef) else node.name
        if node_name == qualified_name:
            return node
    return None

def generate_docstring_with_llm(api_key, model_name, selected_style, function_name, function_code, variation_hint=""):
    """Generate a docstring via LLM in the selected style."""
    llm = ChatGroq(model=model_name, temperature=0.2, api_key=api_key)
    prompt = f"""
You are an expert Python documentation generator.

Your task is to generate a professional, production-ready Python docstring.

STRICT RULES:
- Output ONLY the docstring.
- Do NOT add explanations outside triple quotes.
- Wrap the entire response inside triple quotes (\\"\\"\\" ).
- Follow the selected style EXACTLY.
- Maintain clean indentation and formatting.
- Include summary, parameters, returns, and raises sections.
- Keep it clean and IDE-ready.

Selected Style: {selected_style}
(Valid values: GOOGLE, NUMPY, REST)

Function Name: {function_name}

Function Code:
{function_code}

{f"Regeneration Hint: {variation_hint}. Keep meaning and style correct, but use different wording/structure from prior attempt." if variation_hint else ""}
""".strip()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content if hasattr(response, "content") else str(response)

def apply_docstring_to_function(file_path, qualified_name, generated_docstring):
    """Apply a generated docstring to the chosen function in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    node = _find_function_node_by_qualified_name(tree, qualified_name)
    if not node:
        return False
    clean_doc = _normalize_llm_docstring(generated_docstring)
    if not clean_doc:
        return False
    return _replace_docstring_text(file_path, node, clean_doc)

def evaluate_docstring_quality(docstring_text, style, param_names):
    """Return a lightweight quality report for a generated docstring."""
    text = _normalize_llm_docstring(docstring_text)
    lower = text.lower()
    has_summary = bool(text.strip())
    if style == "GOOGLE":
        has_params_section = "args:" in lower
    elif style == "NUMPY":
        has_params_section = "parameters" in lower
    elif style == "REST":
        has_params_section = ":param " in lower
    else:
        has_params_section = False

    has_returns = ("returns:" in lower) or ("returns" in lower) or (":returns:" in lower)
    has_raises = ("raises:" in lower) or ("raises" in lower) or (":raises" in lower)

    missing_params = []
    for param in param_names:
        if param and param not in {"self", "cls"} and re.search(rf"\b{re.escape(param)}\b", text) is None:
            missing_params.append(param)

    score = 0
    score += 25 if has_summary else 0
    score += 25 if has_params_section else 0
    score += 25 if has_returns else 0
    score += 25 if has_raises else 0
    if missing_params:
        score = max(0, score - min(len(missing_params) * 5, 20))

    return {
        "score": score,
        "has_summary": has_summary,
        "has_params_section": has_params_section,
        "has_returns": has_returns,
        "has_raises": has_raises,
        "missing_params": missing_params,
        "fingerprint": hashlib.sha1(text.encode("utf-8")).hexdigest()[:10] if text else "",
    }

def is_docstring_style_compliant(docstring_text, style, param_names, function_source):
    """Return whether a docstring matches the selected style form."""
    quality = evaluate_docstring_quality(docstring_text, style, param_names)
    requires_raises = bool(re.search(r"\braise\b", function_source or ""))

    is_ok = (
        quality["has_summary"]
        and quality["has_params_section"]
        and quality["has_returns"]
        and (quality["has_raises"] if requires_raises else True)
        and not quality["missing_params"]
    )
    return is_ok, quality, requires_raises

def fix_pep257_violation(file_path, item_name, rule):
    """Fix a single PEP 257 violation and return True when a change is made."""
    rule_code = rule.split(":", 1)[0].strip()

    if rule_code in {"D100", "D104"}:
        auto_fix_docstrings(file_path)
        return True
    if rule_code in {"D101", "D102", "D103", "D105", "D106", "D107"}:
        auto_fix_docstrings(file_path, target_function=item_name)
        return True

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    attach_parents(tree)

    node = _find_target_node(tree, item_name, rule_code)
    if not node:
        return False

    current_doc = ast.get_docstring(node, clean=True)
    if not current_doc:
        return False

    lines = current_doc.strip().splitlines()
    if not lines:
        return False

    if rule_code in {"D201", "D202", "D204", "D211"}:
        return _fix_blank_lines_around_docstring(file_path, node, rule_code)

    if rule_code == "D213":
        return _replace_docstring_text_with_second_line_summary(file_path, node, "\n".join(lines))

    if rule_code in {"D212", "D300"}:
        return _replace_docstring_text(file_path, node, "\n".join(lines))

    changed = _apply_text_rule(lines, rule_code, getattr(node, "name", item_name))
    if not changed:
        return False

    return _replace_docstring_text(file_path, node, "\n".join(lines))

def fix_all_pep257_violations(file_path, max_passes=5):
    """Fix all currently detected PEP 257 violations."""
    for _ in range(max_passes):
        tree = parse_file(file_path)
        if not tree:
            return
        attach_parents(tree)
        violations = get_pep257_violations(tree, file_path=file_path)
        if not violations:
            return

        changed = False
        for item_name, rule in violations:
            if fix_pep257_violation(file_path, item_name, rule):
                changed = True
        if not changed:
            return

def can_auto_fix_violation(item_name, rule):
    """Return True when the rule is currently supported by auto-fix."""
    rule_code = rule.split(":", 1)[0].strip()
    if rule_code in {"D100", "D104"}:
        return True
    if rule_code in {"D101", "D102", "D103", "D105", "D106", "D107"}:
        return bool(item_name and item_name != "Module")
    if rule_code in {
        "D200",
        "D201",
        "D202",
        "D204",
        "D205",
        "D210",
        "D211",
        "D212",
        "D213",
        "D300",
        "D400",
        "D401",
        "D402",
        "D403",
        "D404",
        "D415",
    }:
        return bool(item_name)
    return False

# ================= PYDOCSTYLE =================
def run_pydocstyle(file_path):
    """Run pydocstyle for a file and return output lines."""
    try:
        result = subprocess.run(
            ["pydocstyle", file_path],
            capture_output=True,
            text=True
        )
    except FileNotFoundError:
        return []

    output = []
    if result.stdout:
        output.extend(result.stdout.splitlines())
    if result.stderr:
        output.extend(result.stderr.splitlines())
    return output

# ================= SIDEBAR + UI HELPERS =================
RULE_HINTS = {
    "D100": "Module should include a top-level docstring.",
    "D101": "Public classes should have a docstring.",
    "D102": "Public methods should have a docstring.",
    "D103": "Public functions should have a docstring.",
    "D200": "One-line docstring should fit on one line.",
    "D205": "Keep a blank line between summary and details.",
    "D400": "Summary line should end with a period.",
    "D401": "Summary should use imperative mood.",
    "D415": "Summary should end with punctuation.",
}

st.sidebar.title("AI Code Reviewer")
view_choice = st.sidebar.selectbox(
    "Navigation",
    ["🏠 Home", "📊 Metrics", "📘 Docstrings", "✅ Validation", "📈 Dashboard"]
)
view = view_choice.split(" ", 1)[1]
path_to_scan = st.sidebar.text_input("Path to scan", "examples")
output_path = st.sidebar.text_input("Output JSON", "review_output.json")
scan_clicked = st.sidebar.button("🔍 Scan", use_container_width=True)

def _rule_hint(rule):
    """Return a short tooltip description for a PEP 257 rule."""
    code = (rule or "").split(":", 1)[0].strip()
    return RULE_HINTS.get(code, "PEP 257 docstring style guidance.")

def _severity_from_rule(rule):
    """Map docstring rule into severity bands for UI badges."""
    code = (rule or "").split(":", 1)[0].strip()
    if code in {"D100", "D101", "D102", "D103", "D104", "D105", "D106", "D107"}:
        return "high"
    if code in {"D400", "D401", "D415"}:
        return "medium"
    return "low"

def _status_markup(coverage):
    """Build status pill markup from coverage percentage."""
    if coverage >= 80:
        return "<span class='status-pill status-success'>Success</span>"
    if coverage >= 50:
        return "<span class='status-pill status-warning'>Warning</span>"
    return "<span class='status-pill status-error'>Error</span>"

def _show_summary_cards(total_files, total_functions, missing_docstrings, fixed_issues):
    """Render four top summary cards."""
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("📂", "Total Files", total_files),
        ("🔧", "Total Functions", total_functions),
        ("⚠️", "Missing Docstrings", missing_docstrings),
        ("✅", "Fixed Issues", fixed_issues),
    ]
    for col, (icon, label, value) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card fade-in">
                    <div class="metric-icon">{icon}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

def _code_snippet(file_path, lineno, radius=3):
    """Return a short code snippet centered around a line number."""
    if not lineno or not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = max(0, lineno - radius - 1)
    end = min(len(lines), lineno + radius)
    return "".join(lines[start:end])

def _render_colored_diff(old_text, new_text, from_label="Current", to_label="Generated"):
    """Render a red/green unified diff using HTML spans."""
    diff_lines = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=from_label,
            tofile=to_label,
            lineterm="",
        )
    )
    if not diff_lines:
        st.info("No difference between current and generated docstring.")
        return

    colored_lines = []
    for line in diff_lines:
        escaped = html.escape(line)
        if line.startswith("+++") or line.startswith("---"):
            colored_lines.append(f"<span class='diff-meta'>{escaped}</span>")
        elif line.startswith("@@"):
            colored_lines.append(f"<span class='diff-hunk'>{escaped}</span>")
        elif line.startswith("+"):
            colored_lines.append(f"<span class='diff-add'>{escaped}</span>")
        elif line.startswith("-"):
            colored_lines.append(f"<span class='diff-del'>{escaped}</span>")
        else:
            colored_lines.append(f"<span class='diff-ctx'>{escaped}</span>")

    st.markdown(f"<div class='diff-box'>{''.join(colored_lines)}</div>", unsafe_allow_html=True)

def refresh_selected_file_state(path_to_scan, selected_file):
    """Refresh session metrics and analysis for the currently selected file."""
    if not selected_file:
        return False

    selected_path = os.path.join(path_to_scan, selected_file)
    if not os.path.isfile(selected_path):
        return False

    tree = parse_file(selected_path)
    if not tree:
        return False

    attach_parents(tree)
    with open(selected_path, "r", encoding="utf-8") as scanned_file:
        source_text = scanned_file.read()

    funcs = extract_functions(tree)
    st.session_state.functions = funcs
    st.session_state.pep257_violations = get_pep257_violations(tree, file_path=selected_path)
    st.session_state.quality_report = analyze_code_quality(tree, source_text)
    st.session_state.total, st.session_state.documented, st.session_state.coverage = docstring_coverage(funcs)
    st.session_state.metrics_result = calculate_metrics(funcs)
    st.session_state.metrics_scanned = True
    st.session_state.last_scan_file = selected_file
    return True


# ================= FILE SELECTION =================
uploaded_files = st.sidebar.file_uploader(
    "Upload Python Files",
    type=["py"],
    accept_multiple_files=True,
    help="Uploaded files are saved into the scan path and become selectable.",
)
if uploaded_files:
    os.makedirs(path_to_scan, exist_ok=True)
    for uploaded in uploaded_files:
        destination = os.path.join(path_to_scan, uploaded.name)
        with open(destination, "wb") as out:
            out.write(uploaded.getbuffer())
    st.sidebar.success(f"Uploaded {len(uploaded_files)} file(s) into '{path_to_scan}'.")

files = sorted([f for f in os.listdir(path_to_scan) if f.endswith(".py")]) if os.path.exists(path_to_scan) else []
if files:
    selected_file = st.sidebar.selectbox("Select File", files)
else:
    selected_file = ""
    st.sidebar.info("No Python files found in the selected path.")

# ================= SESSION STATE INIT =================
if "functions" not in st.session_state:
    st.session_state.functions = []
    st.session_state.pep257_violations = []
    st.session_state.quality_report = {}
    st.session_state.metrics_scanned = False
    st.session_state.metrics_result = {}
    st.session_state.total = 0
    st.session_state.documented = 0
    st.session_state.coverage = 0
if "fixed_issues" not in st.session_state:
    st.session_state.fixed_issues = 0
if "last_scan_file" not in st.session_state:
    st.session_state.last_scan_file = ""

# ================= SCAN =================
if scan_clicked:
    if not selected_file:
        st.sidebar.warning("Select a Python file before scanning.")
    else:
        selected_path = os.path.join(path_to_scan, selected_file)
        if not os.path.isfile(selected_path):
            st.sidebar.error("Selected file is not available. Refresh selection.")
            st.stop()
        scan_loader = st.sidebar.empty()
        scan_loader.markdown("<div class='loader'></div>", unsafe_allow_html=True)
        scan_progress = st.sidebar.progress(0, text="Preparing scan...")

        for pct in range(5, 60, 11):
            scan_progress.progress(pct, text=f"Analyzing AST... {pct}%")
            time.sleep(0.03)

        if refresh_selected_file_state(path_to_scan, selected_file):

            for pct in range(60, 101, 10):
                scan_progress.progress(pct, text=f"Finishing scan... {pct}%")
                time.sleep(0.02)
            st.sidebar.success(f"Scan complete: {selected_file}")
        else:
            st.sidebar.error("Scan failed: file could not be parsed.")

        scan_loader.empty()

# Keep requested pages synced with the selected file, similar to milestone2 behavior.
if view in {"Home", "Metrics", "Validation", "Dashboard"} and selected_file:
    if st.session_state.last_scan_file != selected_file or not st.session_state.metrics_scanned:
        refresh_selected_file_state(path_to_scan, selected_file)

# ================= HOME =================
if view == "Home":
    st.title("🤖 AI Code Reviewer")

    home_functions = list(st.session_state.functions)
    home_total = st.session_state.total
    home_documented = st.session_state.documented
    home_coverage = st.session_state.coverage

    if selected_file:
        selected_path = os.path.join(path_to_scan, selected_file)
        if os.path.isfile(selected_path):
            selected_tree = parse_file(selected_path)
            if selected_tree:
                attach_parents(selected_tree)
                home_functions = extract_functions(selected_tree)
                home_total, home_documented, home_coverage = docstring_coverage(home_functions)

    coverage = home_coverage
    if coverage < 50:
        badge = "🟥 Poor"
        status_class = "status-poor"
    elif coverage < 80:
        badge = "🟨 Average"
        status_class = "status-average"
    else:
        badge = "🟩 Good"
        status_class = "status-good"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="coverage-highlight">
                📊 Coverage<br>
                {coverage}%
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.metric("Total Functions", home_total)
    with c3:
        st.metric("Documented", home_documented)

    st.markdown(
        f"<div class='status-box {status_class}'>Status: {badge}</div>",
        unsafe_allow_html=True
    )

# ================= FILE UPLOAD =================
if view == "📂 File Upload":
    st.title("File Upload")
    st.markdown("<div class='glass-card'>Use the sidebar uploader to add `.py` files. They are saved into the configured scan path.</div>", unsafe_allow_html=True)
    st.write(f"Current scan path: `{path_to_scan}`")
    if files:
        for fname in files:
            with st.expander(f"📄 {fname}"):
                fpath = os.path.join(path_to_scan, fname)
                fn_items = collect_function_docstrings(fpath)
                st.caption(f"Functions: {len(fn_items)}")
                if fn_items:
                    st.dataframe(
                        pd.DataFrame(
                            [{"Function": item["qualified_name"], "Line": item["lineno"]} for item in fn_items]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
    else:
        st.info("No Python files found in the current scan path.")

# ================= METRICS =================
if view == "Metrics":
    if not selected_file:
        st.warning("Select a Python file and run scan first.")
        st.stop()
    if not st.session_state.functions:
        st.warning("Run a scan to view metrics.")
        st.stop()

    st.title("📊 Code Metrics")

    for fn in st.session_state.functions:
        status = "✅ Documented" if fn["doc"] else "⚠️ Missing Docstring"
        with st.expander(f"🔹 {fn['name']} ({fn['start']}-{fn['end']})", expanded=False):
            st.markdown(
                f"""
                <div class="glass-card">
                    <b>Function:</b> {fn['name']}<br>
                    <b>Lines:</b> {fn['start']} - {fn['end']}<br>
                    <b>Status:</b> {status}
                </div>
                """,
                unsafe_allow_html=True,
            )
           

    st.download_button(
        "⬇️ Download Docstring Coverage Report",
        json.dumps(coverage_report(os.path.join(path_to_scan, selected_file)), indent=4),
        os.path.basename(output_path) if output_path.strip() else "coverage_report.json",
        "application/json"
    )

# ================= DOCSTRINGS =================
elif view == "Docstrings":
    st.title("📘 Docstrings")
    bulk_result = st.session_state.pop("bulk_docstring_apply_result", None)
    if bulk_result:
        updated = bulk_result.get("updated", 0)
        total = bulk_result.get("total", 0)
        failed = bulk_result.get("failed", [])
        if failed:
            st.warning(f"Bulk apply completed: {updated}/{total} functions updated.")
            st.dataframe(pd.DataFrame(failed), use_container_width=True, hide_index=True)
        else:
            st.success(f"Bulk apply completed: {updated}/{total} functions updated.")

    if not selected_file:
        st.warning("Select a Python file from the sidebar first.")
    else:
        current_file = os.path.join(path_to_scan, selected_file)
        function_items = collect_function_docstrings(current_file)

        if not function_items:
            st.info("No functions found in the selected file.")
        else:
            st.markdown("<div class='doc-card'><b>Configuration</b></div>", unsafe_allow_html=True)
            selected_style_label = st.radio(
                "Docstring Style",
                ["Google Style", "NumPy Style", "ReSt Style"],
                horizontal=True,
            )
            style_map = {
                "Google Style": "GOOGLE",
                "NumPy Style": "NUMPY",
                "ReSt Style": "REST",
            }
            selected_style = style_map[selected_style_label]
            model_options = [
                "openai/gpt-oss-120b",
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
                "qwen/qwen3-32b",
                "qwen/qwen3-14b",
                "custom",
            ]
            selected_model_option = st.selectbox("LLM Model", model_options)
            if selected_model_option == "custom":
                model_name = st.text_input("Custom LLM Model", value="llama-3.1-8b-instant").strip()
                if not model_name:
                    model_name = "llama-3.1-8b-instant"
            else:
                model_name = selected_model_option

            st.markdown("<div class='doc-card'><b>Current File Overview</b></div>", unsafe_allow_html=True)
            non_compliant_rows = []
            compliant_count = 0
            for item in function_items:
                ok, quality, requires_raises = is_docstring_style_compliant(
                    docstring_text=item.get("docstring", ""),
                    style=selected_style,
                    param_names=item.get("params", []),
                    function_source=item.get("source", ""),
                )
                if ok:
                    compliant_count += 1
                else:
                    reasons = []
                    if not quality["has_summary"]:
                        reasons.append("missing summary")
                    if not quality["has_params_section"]:
                        reasons.append("missing parameters section")
                    if not quality["has_returns"]:
                        reasons.append("missing returns section")
                    if requires_raises and not quality["has_raises"]:
                        reasons.append("missing raises section")
                    if quality["missing_params"]:
                        reasons.append("params not documented: " + ", ".join(quality["missing_params"]))

                    non_compliant_rows.append(
                        {
                            "Function": item["qualified_name"],
                            "Has Docstring": "Yes" if bool(item.get("docstring", "").strip()) else "No",
                            "Raises Required": "Yes" if requires_raises else "No",
                            "Why Not In Style": "; ".join(reasons) if reasons else "format mismatch",
                        }
                    )

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total Functions", len(function_items))
            with m2:
                st.metric(f"Not in {selected_style_label}", len(non_compliant_rows))
            with m3:
                st.metric(f"In {selected_style_label}", compliant_count)

            if non_compliant_rows:
                with st.expander(f"Functions not in {selected_style_label}", expanded=False):
                    st.dataframe(pd.DataFrame(non_compliant_rows), use_container_width=True, hide_index=True)
            else:
                st.success(f"All functions are in {selected_style_label}.")

            st.markdown("<div class='doc-card'><b>File Name Badges</b></div>", unsafe_allow_html=True)
            file_badge_rows = []
            for fname in files:
                file_path = os.path.join(path_to_scan, fname)
                file_functions = collect_function_docstrings(file_path)
                total_in_file = len(file_functions)

                if total_in_file == 0:
                    badge = "⚪ No Functions"
                    compliant_in_file = 0
                else:
                    compliant_in_file = 0
                    for f_item in file_functions:
                        ok, _, _ = is_docstring_style_compliant(
                            docstring_text=f_item.get("docstring", ""),
                            style=selected_style,
                            param_names=f_item.get("params", []),
                            function_source=f_item.get("source", ""),
                        )
                        if ok:
                            compliant_in_file += 1

                    ratio = (compliant_in_file / total_in_file) * 100
                    if ratio == 100:
                        badge = "🟢 In Style"
                    elif ratio >= 70:
                        badge = "🟡 Partial"
                    else:
                        badge = "🔴 Needs Fix"

                file_badge_rows.append(
                    {
                        "File": fname,
                        "Badge": badge,
                        "In Style": compliant_in_file,
                        "Total": total_in_file,
                    }
                )
            st.dataframe(pd.DataFrame(file_badge_rows), use_container_width=True, hide_index=True)

            st.markdown("<div class='doc-card'><b>Filter And Sort</b></div>", unsafe_allow_html=True)
            filter_mode = st.radio(
                "Filter",
                ["All", "Missing Docstring", "Not In Style", "In Style"],
                horizontal=True,
            )
            sort_mode = st.selectbox(
                "Sort",
                ["Name (A-Z)", "Name (Z-A)", "Non-Compliant First", "Missing Docstring First"],
            )

            non_compliant_names = {row["Function"] for row in non_compliant_rows}
            filtered_items = []
            for item in function_items:
                name = item["qualified_name"]
                has_doc = bool(item.get("docstring", "").strip())
                is_non_compliant = name in non_compliant_names

                if filter_mode == "Missing Docstring" and has_doc:
                    continue
                if filter_mode == "Not In Style" and not is_non_compliant:
                    continue
                if filter_mode == "In Style" and is_non_compliant:
                    continue
                filtered_items.append(item)

            if sort_mode == "Name (A-Z)":
                filtered_items.sort(key=lambda item: item["qualified_name"].lower())
            elif sort_mode == "Name (Z-A)":
                filtered_items.sort(key=lambda item: item["qualified_name"].lower(), reverse=True)
            elif sort_mode == "Non-Compliant First":
                filtered_items.sort(
                    key=lambda item: (item["qualified_name"] not in non_compliant_names, item["qualified_name"].lower())
                )
            elif sort_mode == "Missing Docstring First":
                filtered_items.sort(
                    key=lambda item: (bool(item.get("docstring", "").strip()), item["qualified_name"].lower())
                )

            function_names = [item["qualified_name"] for item in filtered_items] or [item["qualified_name"] for item in function_items]
            selected_function = st.selectbox("Choose Function", function_names)

            live1, live2 = st.columns(2)
            with live1:
                st.metric("Filtered Functions", len(filtered_items))
            with live2:
                st.metric("Selected Style", selected_style_label)

            active_item = next(
                (item for item in function_items if item["qualified_name"] == selected_function),
                None,
            )

            selected_ok, selected_quality, selected_requires_raises = is_docstring_style_compliant(
                docstring_text=active_item.get("docstring", "") if active_item else "",
                style=selected_style,
                param_names=active_item.get("params", []) if active_item else [],
                function_source=active_item.get("source", "") if active_item else "",
            )

        
            if selected_ok:
                st.success(f"`{selected_function}` already matches {selected_style_label}.")
            else:
                reasons = []
                if not selected_quality["has_summary"]:
                    reasons.append("missing summary")
                if not selected_quality["has_params_section"]:
                    reasons.append("missing parameters section")
                if not selected_quality["has_returns"]:
                    reasons.append("missing returns section")
                if selected_requires_raises and not selected_quality["has_raises"]:
                    reasons.append("missing raises section")
                if selected_quality["missing_params"]:
                    reasons.append("params not documented: " + ", ".join(selected_quality["missing_params"]))
                st.info(
                    f"`{selected_function}` is not in {selected_style_label}: "
                    + ("; ".join(reasons) if reasons else "format mismatch")
                )

            current_doc = (active_item.get("docstring", "") if active_item else "").strip()
            current_doc_block = f'"""\n{current_doc}\n"""' if current_doc else '"""No docstring found."""'

            preview_key = f"generated_docstring::{selected_file}::{selected_function}::{selected_style}"
            if preview_key not in st.session_state:
                st.session_state[preview_key] = ""
            regen_counter_key = f"regen_counter::{preview_key}"
            if regen_counter_key not in st.session_state:
                st.session_state[regen_counter_key] = 0

            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("<div class='doc-card'><b>Current Docstring</b></div>", unsafe_allow_html=True)
                st.code(current_doc_block, language="python")

            with c_right:
                st.markdown("<div class='doc-card'><b>Generated Docstring</b></div>", unsafe_allow_html=True)
                style_params = [p for p in (active_item.get("params", []) if active_item else []) if p not in {"self", "cls"}]
                if selected_style == "GOOGLE":
                    params_block = "\n".join([f"    {p} (Any): Description." for p in style_params]) or "    None."
                    style_sample = (
                        '"""\n'
                        f"Describe {selected_function}.\n\n"
                        "Args:\n"
                        f"{params_block}\n\n"
                        "Returns:\n"
                        "    Any: Description.\n\n"
                        "Raises:\n"
                        "    Exception: Description.\n"
                        '"""'
                    )
                elif selected_style == "NUMPY":
                    params_block = "\n".join([f"{p} : Any\n    Description." for p in style_params]) or "None\n    No parameters."
                    style_sample = (
                        '"""\n'
                        f"Describe {selected_function}.\n\n"
                        "Parameters\n"
                        "----------\n"
                        f"{params_block}\n\n"
                        "Returns\n"
                        "-------\n"
                        "Any\n"
                        "    Description.\n\n"
                        "Raises\n"
                        "------\n"
                        "Exception\n"
                        "    Description.\n"
                        '"""'
                    )
                else:
                    params_block = "\n".join([f":param {p}: Description.\n:type {p}: Any" for p in style_params]) or ":param None: No parameters.\n:type None: None"
                    style_sample = (
                        '"""\n'
                        f"Describe {selected_function}.\n\n"
                        f"{params_block}\n"
                        ":returns: Description.\n"
                        ":rtype: Any\n"
                        ":raises Exception: Description.\n"
                        '"""'
                    )
                generated_preview = st.session_state.get(preview_key, "")
                normalized_generated = _normalize_llm_docstring(generated_preview).strip() if generated_preview else ""
                generated_doc_block = (
                    f'"""\n{normalized_generated}\n"""' if normalized_generated else '"""No docstring generated."""'
                )
                display_docstring = generated_doc_block if generated_preview else style_sample
                st.code(display_docstring, language="python")
                if generated_preview:
                    st.caption("Showing generated docstring.")
                else:
                    st.caption("Showing style sample template (generate to replace).")
                accept_col, reject_col = st.columns(2)
                with accept_col:
                    if st.button("✅ Accept", key=f"accept::{preview_key}", use_container_width=True):
                        if not generated_preview:
                            st.warning("Generate a docstring first.")
                        elif apply_docstring_to_function(current_file, selected_function, generated_preview):
                            st.success("Accepted and applied to function.")
                            st.session_state[preview_key] = ""
                            st.session_state[regen_counter_key] = 0
                            st.rerun()
                        else:
                            st.error("Could not apply generated docstring.")
                with reject_col:
                    if st.button("🔁 Reject", key=f"reject::{preview_key}", use_container_width=True):
                        api_key = os.getenv("GROQ_API_KEY")
                        if not api_key:
                            st.error("GROQ_API_KEY not found. Set it in your .env file.")
                        elif not active_item or not active_item.get("source", "").strip():
                            st.error("Unable to read the selected function source.")
                        else:
                            st.session_state[regen_counter_key] += 1
                            attempt = st.session_state[regen_counter_key]
                            with st.spinner("Regenerating docstring..."):
                                refreshed_output = generate_docstring_with_llm(
                                    api_key=api_key,
                                    model_name=model_name,
                                    selected_style=selected_style,
                                    function_name=selected_function,
                                    function_code=active_item["source"],
                                    variation_hint=f"Reject attempt {attempt} at {time.time()}. Use clearly different wording and structure.",
                                )
                            st.session_state[preview_key] = refreshed_output
                            st.success(f"Generated docstring updated (attempt {attempt}).")
                            st.rerun()

            st.markdown("<div class='doc-card'><b>Docstring Difference</b></div>", unsafe_allow_html=True)
            diff_lines = list(
                difflib.unified_diff(
                    current_doc_block.splitlines(),
                    display_docstring.splitlines(),
                    fromfile="Current",
                    tofile="Generated",
                    lineterm="",
                )
            )
            if diff_lines:
                _render_colored_diff(
                    current_doc_block,
                    display_docstring,
                    from_label="Current",
                    to_label="Generated",
                )
            else:
                st.info("No difference between current and generated docstring.")

            action_left, action_right = st.columns([1, 1])

            with action_left:
                if st.button("✨ Generate with LLM"):
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        st.error("GROQ_API_KEY not found. Set it in your .env file.")
                    elif not active_item or not active_item.get("source", "").strip():
                        st.error("Unable to read the selected function source.")
                    else:
                        with st.spinner("Generating docstring with LLM..."):
                            raw_output = generate_docstring_with_llm(
                                api_key=api_key,
                                model_name=model_name,
                                selected_style=selected_style,
                                function_name=selected_function,
                                function_code=active_item["source"],
                            )

                        st.session_state[preview_key] = raw_output
                        st.session_state[regen_counter_key] = 0
                        st.success("Docstring generated. Use Accept/Reject below.")
                        st.rerun()

            with action_right:
                _, right_btn_col = st.columns([1, 1])
                with right_btn_col:
                    if st.button("⚙️ Generate and Apply Style to ALL Functions", use_container_width=True):
                        api_key = os.getenv("GROQ_API_KEY")
                        if not api_key:
                            st.error("GROQ_API_KEY not found. Set it in your .env file.")
                        else:
                            progress = st.progress(0)
                            status = st.empty()
                            total = len(function_items)
                            updated = 0
                            failed = []
                            for idx, item in enumerate(function_items, start=1):
                                status.text(f"Processing {item['qualified_name']} ({idx}/{total})")
                                if not item.get("source", "").strip():
                                    failed.append(
                                        {
                                            "Function": item["qualified_name"],
                                            "Reason": "source not available",
                                        }
                                    )
                                    progress.progress(idx / total)
                                    continue

                                try:
                                    raw_output = generate_docstring_with_llm(
                                        api_key=api_key,
                                        model_name=model_name,
                                        selected_style=selected_style,
                                        function_name=item["qualified_name"],
                                        function_code=item["source"],
                                    )
                                    if apply_docstring_to_function(current_file, item["qualified_name"], raw_output):
                                        updated += 1
                                    else:
                                        failed.append(
                                            {
                                                "Function": item["qualified_name"],
                                                "Reason": "could not apply generated docstring",
                                            }
                                        )
                                except Exception as exc:
                                    failed.append(
                                        {
                                            "Function": item["qualified_name"],
                                            "Reason": str(exc),
                                        }
                                    )

                                progress.progress(idx / total)

                            status.empty()
                            st.session_state["bulk_docstring_apply_result"] = {
                                "updated": updated,
                                "total": total,
                                "failed": failed,
                            }
                            st.rerun()
                            
# ================= VALIDATION =================
elif view == "Validation" and selected_file:
    st.title("✅ Validation & Auto Fix")
    current_file = os.path.join(path_to_scan, selected_file)
    current_tree = parse_file(current_file)
    if current_tree:
        attach_parents(current_tree)
        st.session_state.functions = extract_functions(current_tree)
        st.session_state.pep257_violations = get_pep257_violations(current_tree, file_path=current_file)
        st.session_state.total, st.session_state.documented, st.session_state.coverage = docstring_coverage(
            st.session_state.functions
        )

    pep257_violations = st.session_state.pep257_violations

    total_functions = len(st.session_state.functions)
    violations = len(pep257_violations)
    compliant = max(total_functions - violations, 0)

    df = pd.DataFrame({
        "Status": ["Violations", "Compliant"],
        "Count": [violations, compliant]
})
    st.caption(f"Total Functions in File: {total_functions}")
    st.caption(f"PEP 257 Violations: {violations}")

    c_bar, c_pie = st.columns(2)
    with c_bar:
        st.bar_chart(df.set_index("Status"))
    with c_pie:
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(
            [violations, compliant],
            labels=["Violations", "Compliant"],
            autopct="%1.1f%%",
            startangle=90,
            colors=["#ef4444", "#22c55e"]
        )
        ax.axis("equal")
        st.pyplot(fig)

    if not pep257_violations:
        st.success("No PEP 257 violations found.")

    for idx, (item_name, item_rule) in enumerate(pep257_violations):
        c1, c2 = st.columns([5, 1])
        can_fix = can_auto_fix_violation(item_name, item_rule)
        with c1:
            st.markdown(
                f"<div class='error'>{item_name}: {item_rule}</div>",
                unsafe_allow_html=True
            )
        with c2:
            if st.button("Fix", key=f"fix_violation_{idx}", disabled=not can_fix):
                if fix_pep257_violation(current_file, item_name, item_rule):
                    st.rerun()

    if st.button("🚀 Fix ALL"):
        fix_all_pep257_violations(current_file)
        st.rerun()
        
# ================= DASHBOARD =================
elif view == "Dashboard" and st.session_state.metrics_scanned:
    st.title("📈 Summary Dashboard")
    st.json(st.session_state.metrics_result)
