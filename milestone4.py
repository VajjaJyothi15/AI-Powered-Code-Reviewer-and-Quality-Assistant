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
        --bg-color: #0f172a;
        --text-color: #e2e8f0;
        --secondary-bg: rgba(30, 41, 59, 0.7);
        --panel-bg: rgba(15, 23, 42, 0.55);
        --panel-border: rgba(148, 163, 184, 0.35);
        --panel-shadow: 0 12px 26px rgba(2, 6, 23, 0.35);
        --accent-color: #38bdf8;
        --muted-text: #cbd5e1;
        --help-header-bg: linear-gradient(135deg, rgba(16, 185, 129, 0.35), rgba(34, 197, 94, 0.18));
        --help-header-border: rgba(34, 197, 94, 0.35);
        --help-header-text: #f8fafc;
        --help-card-bg: rgba(15, 23, 42, 0.55);
        --help-card-border: rgba(148, 163, 184, 0.35);
        --help-card-shadow: 0 10px 22px rgba(2, 6, 23, 0.35);
        --help-card-hover: 0 16px 28px rgba(2, 6, 23, 0.45);
        --help-card-title: #bbf7d0;
        --help-card-text: #e2e8f0;
        --help-panel-bg: rgba(15, 23, 42, 0.45);
        --help-panel-border: rgba(148, 163, 184, 0.35);
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 15%, rgba(56, 189, 248, 0.22), transparent 35%),
            radial-gradient(circle at 85% 10%, rgba(139, 92, 246, 0.24), transparent 40%),
            linear-gradient(130deg, #020617 0%, #0f172a 45%, #111827 100%);
        color: var(--text-color);
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
        background: var(--panel-bg);
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: var(--panel-shadow);
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

        .glass-card:hover,
        .help-card:hover,
        .help-panel:hover,
        .tool-display:hover {
            transform: translateY(-2px);
            box-shadow: 0 14px 26px rgba(2, 6, 23, 0.18);
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

    /* Dashboard Colorful Tool Buttons */
    button[key="dashboard_filter_btn"] {
        background: linear-gradient(90deg, #16a34a, #22c55e) !important;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.35) !important;
    }
    button[key="dashboard_filter_btn"]:hover {
        box-shadow: 0 14px 24px rgba(37, 99, 235, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    button[key="dashboard_search_btn"] {
        background: linear-gradient(90deg, #16a34a, #22c55e) !important;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.35) !important;
    }
    button[key="dashboard_search_btn"]:hover {
        box-shadow: 0 14px 24px rgba(124, 58, 237, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    button[key="dashboard_tests_btn"] {
        background: linear-gradient(90deg, #16a34a, #22c55e) !important;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.35) !important;
    }
    button[key="dashboard_tests_btn"]:hover {
        box-shadow: 0 14px 24px rgba(34, 197, 94, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    button[key="dashboard_export_btn"] {
        background: linear-gradient(90deg, #16a34a, #22c55e) !important;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.35) !important;
    }
    button[key="dashboard_export_btn"]:hover {
        box-shadow: 0 14px 24px rgba(245, 158, 11, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    button[key="dashboard_help_btn"] {
        background: linear-gradient(90deg, #16a34a, #22c55e) !important;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.35) !important;
    }
    button[key="dashboard_help_btn"]:hover {
        box-shadow: 0 14px 24px rgba(6, 182, 212, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    /* Tool Display Styling */
    .tool-display {
        background: var(--panel-bg) !important;
        border: 1px solid var(--panel-border) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin: 16px 0 !important;
        box-shadow: var(--panel-shadow) !important;
        animation: slideInDown 0.4s ease !important;
    }
    .tool-display h2,
    .tool-display span {
        color: var(--text-color) !important;
    }

    .help-header-card {
        background: var(--help-header-bg);
        border: 1px solid var(--help-header-border);
        border-radius: 16px;
        padding: 16px 18px;
        color: var(--help-header-text);
    }
    .help-card-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(180px, 1fr));
        gap: 14px;
        margin: 16px 0;
    }
    .help-card {
        background: var(--help-card-bg);
        border: 1px solid var(--help-card-border);
        border-radius: 14px;
        padding: 14px;
        box-shadow: var(--help-card-shadow);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .help-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--help-card-hover);
    }
    .help-card.variant-scan {
        background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        border-color: rgba(59, 130, 246, 0.35);
    }
    .help-card.variant-coverage {
        background: linear-gradient(135deg, #ede9fe, #ddd6fe);
        border-color: rgba(124, 58, 237, 0.35);
    }
    .help-card.variant-docs {
        background: linear-gradient(135deg, #ffe4e6, #fecdd3);
        border-color: rgba(244, 63, 94, 0.35);
    }
    .help-card.variant-validation {
        background: linear-gradient(135deg, #ccfbf1, #99f6e4);
        border-color: rgba(20, 184, 166, 0.35);
    }
    .help-card-title {
        font-weight: 800;
        color: var(--help-card-title);
    }
    .help-card-text {
        color: var(--help-card-text);
        font-size: 0.9rem;
        margin-top: 6px;
    }
    .help-panel {
        background: var(--help-panel-bg);
        border: 1px solid var(--help-panel-border);
        border-radius: 12px;
        padding: 14px 16px;
    }
    .help-panel.variant-coverage {
        background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        border-color: rgba(59, 130, 246, 0.35);
    }
    .help-panel.variant-tests {
        background: linear-gradient(135deg, #ffe4e6, #fecdd3);
        border-color: rgba(244, 63, 94, 0.35);
    }
    .help-panel.variant-status {
        background: linear-gradient(135deg, #ede9fe, #ddd6fe);
        border-color: rgba(124, 58, 237, 0.35);
    }
    .help-panel.variant-styles {
        background: linear-gradient(135deg, #ccfbf1, #99f6e4);
        border-color: rgba(20, 184, 166, 0.35);
    }
    .help-panel div,
    .help-panel summary {
        color: var(--help-card-title) !important;
    }
    .help-panel ul,
    .help-panel ol {
        color: var(--help-card-text) !important;
    }
    .help-panel-title {
        font-weight: 800;
        color: var(--help-card-title);
        margin-bottom: 6px;
    }
    .help-panel-list {
        color: var(--help-card-text);
        margin: 0 0 0 18px;
    }
    .help-panel-summary {
        font-weight: 800;
        color: var(--help-card-title);
    }
    .help-panel-ol {
        color: var(--help-card-text);
        margin: 10px 0 0 18px;
    }

    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
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

def get_ast_pep257_violations(tree):
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

        if isinstance(node, ast.FunctionDef):
            parent = getattr(node, "parent", None)
            doc = ast.get_docstring(node)

            if isinstance(parent, ast.ClassDef):
                if not doc:
                    violations.append((node.name, "D102: Missing method docstring"))
                else:
                    for rule in check_format_rules(doc):
                        violations.append((node.name, rule))
            else:
                if not doc:
                    violations.append((node.name, "D103: Missing function docstring"))
                else:
                    for rule in check_format_rules(doc):
                        violations.append((node.name, rule))

    return violations

def get_pep257_violations(tree, file_path=None):
    """Collect PEP 257 violations using AST checks plus pydocstyle when available."""
    ast_violations = get_ast_pep257_violations(tree)
    if not file_path:
        return ast_violations

    pydocstyle_lines = run_pydocstyle(file_path)
    pydocstyle_violations = parse_pydocstyle_violations(pydocstyle_lines)
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

if "nav_view" not in st.session_state:
    st.session_state.nav_view = "🏠 Home"
if st.session_state.get("force_home"):
    st.session_state.nav_view = "🏠 Home"
    st.session_state.force_home = False

st.sidebar.title("AI Code Reviewer")
view_choice = st.sidebar.selectbox(
    "Navigation",
    ["🏠 Home", "📊 Metrics", "📘 Docstrings", "✅ Validation", "📈 Dashboard"],
    key="nav_view",
)
view = view_choice.split(" ", 1)[1]
path_to_scan = st.sidebar.text_input("Path to scan", "examples")
output_path = st.sidebar.text_input("Output JSON", "review_output.json")
scan_clicked = st.sidebar.button("🔍 Scan", use_container_width=True)
theme = st.sidebar.selectbox("Theme", ["Dark", "Light"], index=0)

if view != "Dashboard":
    st.session_state.show_filter = False
    st.session_state.show_search = False
    st.session_state.show_tests = False
    st.session_state.show_export = False
    st.session_state.show_help = False

if theme == "Light":
    st.markdown(
        """
        <style>
        :root {
            --bg-color: #f8fafc;
            --text-color: #0f172a;
            --secondary-bg: #f1f5f9;
            --panel-bg: #ffffff;
            --panel-border: rgba(148, 163, 184, 0.4);
            --panel-shadow: 0 10px 24px rgba(148, 163, 184, 0.2);
            --accent-color: #7c3aed;
            --muted-text: #475569;
            --help-header-bg: linear-gradient(135deg, #f8fafc, #ede9fe);
            --help-header-border: rgba(124, 58, 237, 0.35);
            --help-header-text: #1e1b4b;
            --help-card-bg: #ffffff;
            --help-card-border: rgba(148, 163, 184, 0.45);
            --help-card-shadow: 0 8px 18px rgba(148, 163, 184, 0.22);
            --help-card-hover: 0 14px 24px rgba(148, 163, 184, 0.28);
            --help-card-title: #0f172a;
            --help-card-text: #334155;
            --help-panel-bg: #ffffff;
            --help-panel-border: rgba(148, 163, 184, 0.45);
        }
        .stApp {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9, #ffffff) !important;
            color: #0f172a !important;
        }
        section[data-testid="stSidebar"] {
            background: #f1f5f9 !important;
            border-right: 1px solid rgba(148, 163, 184, 0.35) !important;
            box-shadow: 4px 0 18px rgba(148, 163, 184, 0.18);
        }
        section[data-testid="stSidebar"] * {
            color: #0f172a !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(59, 130, 246, 0.28) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px) scale(1.01);
            box-shadow: 0 12px 22px rgba(59, 130, 246, 0.32) !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div,
        section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
            background: #ffffff !important;
            border: 1px dashed rgba(148, 163, 184, 0.55) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
            background: linear-gradient(90deg, #fb7185, #fb923c) !important;
            color: #0f172a !important;
            border: 1px solid rgba(249, 115, 22, 0.5) !important;
            box-shadow: 0 8px 16px rgba(249, 115, 22, 0.22) !important;
        }
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown, .stCaption, .stMetricLabel, .stMetricValue {
            color: #0f172a !important;
        }
        [data-testid="stMetric"] {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
            box-shadow: 0 10px 22px rgba(148, 163, 184, 0.2) !important;
        }
        .glass-card, .metric-card {
            background: var(--panel-bg) !important;
            border: 1px solid var(--panel-border) !important;
            box-shadow: var(--panel-shadow) !important;
        }
        .tool-display {
            background: var(--panel-bg) !important;
            border: 1px solid var(--panel-border) !important;
            box-shadow: var(--panel-shadow) !important;
        }
        .tool-display,
        .tool-display * {
            color: #0f172a !important;
        }
        button[key="dashboard_filter_btn"] {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
            box-shadow: 0 8px 18px rgba(124, 58, 237, 0.28) !important;
        }
        button[key="dashboard_search_btn"] {
            background: linear-gradient(135deg, #fb7185, #fb923c) !important;
            box-shadow: 0 8px 18px rgba(251, 146, 60, 0.28) !important;
        }
        button[key="dashboard_tests_btn"] {
            background: linear-gradient(135deg, #14b8a6, #0d9488) !important;
            box-shadow: 0 8px 18px rgba(13, 148, 136, 0.28) !important;
        }
        button[key="dashboard_export_btn"] {
            background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28) !important;
        }
        button[key="dashboard_help_btn"] {
            background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
            box-shadow: 0 8px 18px rgba(109, 40, 217, 0.28) !important;
        }
        .metric-value {
            color: #0f172a !important;
        }
        .metric-label {
            color: #334155 !important;
        }
        .doc-card {
            background: linear-gradient(100deg, #7c3aed, #3b82f6) !important;
            color: #ffffff !important;
            border: 1px solid rgba(124, 58, 237, 0.45) !important;
        }
        .coverage-highlight {
            background: linear-gradient(130deg, #14b8a6, #0d9488) !important;
            color: #ffffff !important;
            border: 1px solid rgba(20, 184, 166, 0.45) !important;
        }
        .status-poor, .status-average, .status-good {
            color: #0f172a !important;
        }
        .status-success {
            background: rgba(34, 197, 94, 0.18) !important;
            color: #166534 !important;
            border: 1px solid rgba(34, 197, 94, 0.35) !important;
        }
        .status-warning {
            background: rgba(245, 158, 11, 0.2) !important;
            color: #92400e !important;
            border: 1px solid rgba(245, 158, 11, 0.35) !important;
        }
        .status-error {
            background: rgba(239, 68, 68, 0.18) !important;
            color: #991b1b !important;
            border: 1px solid rgba(239, 68, 68, 0.35) !important;
        }
        .severity-high {
            background: rgba(239, 68, 68, 0.12) !important;
            color: #991b1b !important;
            border: 1px solid rgba(239, 68, 68, 0.32) !important;
        }
        .severity-medium {
            background: rgba(245, 158, 11, 0.14) !important;
            color: #92400e !important;
            border: 1px solid rgba(245, 158, 11, 0.32) !important;
        }
        .severity-low {
            background: rgba(34, 197, 94, 0.12) !important;
            color: #166534 !important;
            border: 1px solid rgba(34, 197, 94, 0.32) !important;
        }
        .rule-pill {
            color: #1d4ed8 !important;
            border: 1px dashed rgba(37, 99, 235, 0.45) !important;
        }
        .error {
            background: rgba(254, 226, 226, 0.95) !important;
            color: #991b1b !important;
            border: 1px solid rgba(239, 68, 68, 0.35) !important;
            border-left: 4px solid #ef4444 !important;
            border-radius: 10px !important;
            padding: 10px 12px !important;
        }
        .diff-box {
            background: #f8fafc !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
        }
        .diff-meta, .diff-hunk, .diff-ctx {
            color: #334155 !important;
        }
        div[data-testid="stButton"] > button {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(251, 146, 60, 0.28) !important;
        }
        div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px) scale(1.01);
            box-shadow: 0 12px 22px rgba(251, 146, 60, 0.32) !important;
        }
        div[data-testid="stDownloadButton"] > button {
            background: linear-gradient(90deg, #7c3aed, #5b21b6) !important;
            color: #ffffff !important;
            border: 0 !important;
            box-shadow: 0 8px 18px rgba(91, 33, 182, 0.24) !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            filter: brightness(1.06);
            transform: translateY(-1px);
        }
        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
        }
        [data-baseweb="select"] > div {
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
        }
        [data-baseweb="popover"],
        [data-baseweb="popover"] * {
            color: #0f172a !important;
        }
        [role="listbox"] {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
        }
        [role="option"] {
            background: #ffffff !important;
            color: #0f172a !important;
        }
        [role="option"][aria-selected="true"] {
            background: #ede9fe !important;
            color: #4c1d95 !important;
            box-shadow: inset 4px 0 0 #7c3aed;
        }
        [role="option"]:hover {
            background: #f1f5f9 !important;
        }
        [data-testid="stCodeBlock"],
        [data-testid="stCode"] {
            background: #f8fafc !important;
            color: #0f172a !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
        }
        [data-testid="stCodeBlock"] pre,
        [data-testid="stCode"] pre {
            background: #f8fafc !important;
            color: #0f172a !important;
        }
        [data-testid="stCodeBlock"] code,
        [data-testid="stCode"] code,
        [data-testid="stCodeBlock"] code span,
        [data-testid="stCode"] code span {
            color: #0f172a !important;
        }
        div[data-testid="stExpander"] details {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
            border-radius: 10px !important;
        }
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary * {
            color: #0f172a !important;
        }
        div[data-testid="stJson"] {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
            border-radius: 10px !important;
            padding: 8px !important;
        }
        div[data-testid="stJson"] * {
            color: #0f172a !important;
        }
        div[data-testid="stJson"] pre,
        div[data-testid="stJson"] code,
        div[data-testid="stJson"] span {
            color: #0f172a !important;
            background: transparent !important;
        }
        div[data-testid="stDataFrame"] * {
            color: #0f172a !important;
        }
        .stAlert, .stInfo, .stWarning, .stSuccess, .stError {
            color: #0f172a !important;
        }
        [data-testid="stAlertContainer"] * {
            color: #0f172a !important;
        }
        div[data-baseweb="select"] * {
            color: #0f172a !important;
        }
        /* Final fallback overrides for any remaining unreadable controls */
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] * {
            color: #0f172a;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stSidebar"] [data-testid="stText"] {
            color: #0f172a !important;
        }
        [data-testid="stSelectbox"] label,
        [data-testid="stTextInput"] label,
        [data-testid="stTextArea"] label,
        [data-testid="stFileUploader"] label {
            color: #0f172a !important;
        }
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] * {
            color: #0f172a !important;
        }
        [data-testid="stCodeBlock"] pre,
        [data-testid="stCode"] pre,
        code {
            color: #0f172a !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: rgba(148, 163, 184, 0.65) !important;
        }
        [data-testid="stFileUploaderDropzone"] * {
            color: #0f172a !important;
        }
        [data-testid="stTooltipIcon"] svg {
            fill: #0f172a !important;
        }
        [role="tooltip"],
        [role="tooltip"] * {
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: rgba(148, 163, 184, 0.55) !important;
        }
        [data-testid="stDownloadButton"] * {
            color: #ffffff !important;
        }
        [data-baseweb="menu"] {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
        }
        [data-baseweb="menu"] li,
        [data-baseweb="menu"] div {
            color: #0f172a !important;
        }
        [data-baseweb="menu"] li:hover,
        [data-baseweb="menu"] li[aria-selected="true"] {
            background: #dbeafe !important;
            color: #1e3a8a !important;
        }
        [data-testid="stDataFrame"] table,
        [data-testid="stDataFrame"] th,
        [data-testid="stDataFrame"] td {
            color: #0f172a !important;
            background-color: #ffffff !important;
        }
        [data-testid="stDataFrame"] th {
            background-color: #f1f5f9 !important;
        }
        [data-testid="stDataFrame"] tbody tr:nth-child(even) td {
            background-color: #f8fafc !important;
        }
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary * {
            color: #0f172a !important;
        }
        /* Strong Light Theme Overrides */
        section[data-testid="stSidebar"] button,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            background: linear-gradient(90deg, #60a5fa, #7c3aed) !important;
            color: #ffffff !important;
            border: 0 !important;
            box-shadow: 0 8px 16px rgba(124, 58, 237, 0.24) !important;
        }
        .glass-card, .metric-card, .tool-display, .help-card, .help-panel {
            background: linear-gradient(135deg, #ffffff, #fed7aa) !important;
            border: 1px solid rgba(249, 115, 22, 0.45) !important;
            box-shadow: 0 10px 22px rgba(249, 115, 22, 0.18) !important;
        }
        .help-card-title, .help-panel div, .help-panel summary {
            color: #0f172a !important;
        }
        .help-card-text, .help-panel ul, .help-panel ol {
            color: #334155 !important;
        }
        div[data-testid="stButton"] > button {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(251, 146, 60, 0.28) !important;
        }
        div[data-testid="stDownloadButton"] > button {
            background: linear-gradient(90deg, #7c3aed, #5b21b6) !important;
            color: #ffffff !important;
            border: 0 !important;
            box-shadow: 0 8px 18px rgba(91, 33, 182, 0.24) !important;
        }
        button[key="dashboard_filter_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
        }
        button[key="dashboard_search_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
        }
        button[key="dashboard_tests_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
        }
        button[key="dashboard_export_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
        }
        button[key="dashboard_help_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
        }
        :root {
            --help-header-bg: linear-gradient(135deg, #dcfce7, #bbf7d0);
            --help-header-border: rgba(34, 197, 94, 0.35);
            --help-header-text: #065f46;
            --help-card-bg: #ffffff;
            --help-card-border: rgba(148, 163, 184, 0.45);
            --help-card-shadow: 0 8px 18px rgba(148, 163, 184, 0.22);
            --help-card-hover: 0 14px 24px rgba(148, 163, 184, 0.28);
            --help-card-title: #0f172a;
            --help-card-text: #334155;
            --help-panel-bg: #ffffff;
            --help-panel-border: rgba(148, 163, 184, 0.45);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary * {
            color: #e2e8f0 !important;
        }
        .help-card {
            background: rgba(30, 41, 59, 0.85) !important;
            border: 1px solid rgba(148, 163, 184, 0.35) !important;
            box-shadow: 0 12px 26px rgba(2, 6, 23, 0.35) !important;
        }
        .help-card-title {
            color: #f8fafc !important;
        }
        .help-card-text {
            color: #e2e8f0 !important;
        }
        .help-panel {
            background: rgba(15, 23, 42, 0.65) !important;
            border: 1px solid rgba(148, 163, 184, 0.35) !important;
        }
        .help-panel * {
            color: #e2e8f0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Final Light Theme overrides (ensures visibility after all other CSS)
if theme == "Light":
    st.markdown(
        """
        <style>
        .glass-card, .metric-card, .tool-display, .help-panel {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
            box-shadow: 0 10px 22px rgba(148, 163, 184, 0.22) !important;
        }
        .help-card.variant-scan {
            background: linear-gradient(135deg, #dbeafe, #bfdbfe) !important;
        }
        .help-card.variant-coverage {
            background: linear-gradient(135deg, #ede9fe, #ddd6fe) !important;
        }
        .help-card.variant-docs {
            background: linear-gradient(135deg, #ffe4e6, #fecdd3) !important;
        }
        .help-card.variant-validation {
            background: linear-gradient(135deg, #ccfbf1, #99f6e4) !important;
        }
        .help-card-title, .help-card-text, .help-panel * {
            color: #0f172a !important;
        }
        [data-testid="stCodeBlock"],
        [data-testid="stCode"] {
            background: #ffffff !important;
            border: 1px solid rgba(148, 163, 184, 0.55) !important;
        }
        [data-testid="stCodeBlock"] pre,
        [data-testid="stCode"] pre,
        [data-testid="stCodeBlock"] code,
        [data-testid="stCode"] code {
            color: #0f172a !important;
            background: transparent !important;
        }
        div[data-testid="stJson"],
        div[data-testid="stJson"] * {
            color: #0f172a !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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


def _count_test_functions_in_file(file_path):
    """Return the number of top-level pytest-style test functions in a file."""
    tree = parse_file(file_path)
    if not tree:
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def _load_pytest_json_report(report_path="storage/reports/pytest_results.json"):
    """Load pytest JSON report as a dict when available."""
    if not os.path.isfile(report_path):
        return None
    try:
        with open(report_path, "r", encoding="utf-8") as report_file:
            return json.load(report_file)
    except Exception:
        return None


def _run_pytest_command(tests_root="tests", report_path="storage/reports/pytest_results.json"):
    """Run pytest with JSON report output and return results."""
    try:
        import subprocess
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        cmd = [
            "pytest",
            tests_root,
            "--json-report",
            f"--json-report-file={report_path}",
            "-v",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }


def _extract_pass_counts_from_report(report_data):
    """Extract per-test-file passed/total counts from pytest JSON report."""
    counts = {}
    if not isinstance(report_data, dict):
        return counts

    for test_entry in report_data.get("tests", []) or []:
        if not isinstance(test_entry, dict):
            continue
        nodeid = str(test_entry.get("nodeid", ""))
        if not nodeid:
            continue
        file_key = nodeid.split("::", 1)[0].replace("\\", "/")
        outcome = str(test_entry.get("outcome", "")).lower()

        current = counts.setdefault(file_key, {"passed": 0, "total": 0})
        current["total"] += 1
        if outcome == "passed":
            current["passed"] += 1

    return counts


def _collect_dashboard_test_stats(tests_root="tests"):
    """Build ordered test stats for dashboard cards/chart from the tests folder."""
    report_data = _load_pytest_json_report()
    report_counts = _extract_pass_counts_from_report(report_data)
    test_files = []
    if os.path.isdir(tests_root):
        test_files = sorted(
            [
                name
                for name in os.listdir(tests_root)
                if name.startswith("test_") and name.endswith(".py")
            ]
        )

    stats = []
    for filename in test_files:
        label = filename.replace(".py", "").replace("_", " ").title()
        file_path = os.path.join(tests_root, filename)
        total = _count_test_functions_in_file(file_path) if os.path.isfile(file_path) else 0
        rel_key = file_path.replace("\\", "/")
        report_item = report_counts.get(rel_key)
        if report_item:
            passed = report_item["passed"]
            total_from_report = report_item["total"]
            pending = 0
        else:
            passed = 0
            total_from_report = total
            pending = total

        stats.append(
            {
                "label": label,
                "file": file_path,
                "passed": passed,
                "total": total_from_report,
                "pending": pending,
            }
        )
    return stats


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
            st.session_state.force_home = True
            st.rerun()
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

    if not st.session_state.metrics_scanned:
        st.markdown(
            """
            <div class="glass-card">
                <h3 style="margin-top:0;">Project Overview</h3>
                <p>This app scans Python files, checks docstring coverage, validates PEP 257 rules, and highlights quality hotspots.</p>
                <ul>
                    <li>Scan a folder to build coverage and metrics.</li>
                    <li>Generate or improve docstrings with AI assistance.</li>
                    <li>Validate compliance and export reports for audits.</li>
                </ul>
            </div>
            <div class="glass-card">
                <h3 style="margin-top:0;">Get Started</h3>
                <ol>
                    <li>Choose your scan path in the sidebar.</li>
                    <li>Select a Python file.</li>
                    <li>Click Scan to load coverage and metrics.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

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
    metrics_summary_text = "#0f172a" if theme == "Light" else "#e2e8f0"
    metrics_summary_bg = "rgba(148, 163, 184, 0.15)" if theme == "Light" else "rgba(148, 163, 184, 0.22)"
    metrics_css = """
        <style>
        @keyframes metricsCardIn {
            0% { opacity: 0; transform: translateY(10px) scale(0.99); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .metrics-card {
            animation: metricsCardIn 0.38s ease-out both;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metrics-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 14px 24px rgba(2, 6, 23, 0.18);
        }
        div[data-testid="stExpander"] details > summary {
            color: __METRICS_SUMMARY_TEXT__ !important;
            transition: background-color 0.2s ease, color 0.2s ease;
        }
        div[data-testid="stExpander"] details > summary *,
        div[data-testid="stExpander"] details > summary:hover,
        div[data-testid="stExpander"] details > summary:hover *,
        div[data-testid="stExpander"] details > summary:focus,
        div[data-testid="stExpander"] details > summary:focus *,
        div[data-testid="stExpander"] details > summary[aria-expanded="true"],
        div[data-testid="stExpander"] details > summary[aria-expanded="true"] * {
            color: __METRICS_SUMMARY_TEXT__ !important;
        }
        div[data-testid="stExpander"] details > summary:hover,
        div[data-testid="stExpander"] details > summary:focus,
        div[data-testid="stExpander"] details > summary[aria-expanded="true"] {
            background-color: __METRICS_SUMMARY_BG__ !important;
        }
        </style>
        """
    st.markdown(
        metrics_css
        .replace("__METRICS_SUMMARY_TEXT__", metrics_summary_text)
        .replace("__METRICS_SUMMARY_BG__", metrics_summary_bg),
        unsafe_allow_html=True,
    )

    for idx, fn in enumerate(st.session_state.functions):
        status = "✅ Documented" if fn["doc"] else "⚠️ Missing Docstring"
        with st.expander(f"🔹 {fn['name']} ({fn['start']}-{fn['end']})", expanded=False):
            st.markdown(
                f"""
                <div class="glass-card metrics-card" style="animation-delay:{idx * 0.04:.2f}s;">
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
elif view == "Dashboard":
    dashboard_all_functions = []
    for fname in files:
        file_path = os.path.join(path_to_scan, fname)
        if not os.path.exists(file_path):
            continue
        tree = parse_file(file_path)
        if not tree:
            continue
        for fn in extract_functions(tree):
            fn_with_file = dict(fn)
            fn_with_file["file"] = fname
            dashboard_all_functions.append(fn_with_file)

    dashboard_functions = dashboard_all_functions
    dashboard_total = len(dashboard_functions)
    dashboard_documented = sum(1 for fn in dashboard_functions if fn.get("doc"))
    dashboard_coverage = (dashboard_documented / dashboard_total * 100) if dashboard_total else 0.0

    dashboard_violations = []
    if selected_file:
        selected_path = os.path.join(path_to_scan, selected_file)
        if os.path.exists(selected_path):
            selected_source = open(selected_path, "r", encoding="utf-8").read()
            selected_tree = parse_file(selected_path)
            if selected_tree:
                dashboard_violations = get_pep257_violations(selected_tree, selected_source)

    dashboard_theme_css = """
        .dash-shell {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 20px;
            padding: 18px;
            margin-bottom: 16px;
        }
        .dash-header {
            background: linear-gradient(135deg, #c4b5fd, #94a3b8);
            border-radius: 18px;
            padding: 22px;
            color: #0f172a;
            margin-bottom: 14px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.25);
        }
        .dash-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 2.0rem;
            font-weight: 800;
            margin: 0;
        }
        .dash-subtitle {
            margin-top: 8px;
            font-size: 1rem;
            color: #1f2937;
        }
        .dash-heading {
            color: #facc15;
            font-size: 1.2rem;
            font-weight: 700;
            margin: 8px 0 8px 0;
        }
        .dash-text {
            color: #e2e8f0;
            margin-bottom: 10px;
        }
        .dash-list {
            color: #e2e8f0;
            line-height: 1.7;
            margin-left: 18px;
        }
        div[data-baseweb="tab-list"] {
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        button[data-baseweb="tab"] {
            background: #111827 !important;
            color: #ffffff !important;
            border: 1px solid #334155 !important;
            border-radius: 14px !important;
            min-width: 220px !important;
            min-height: 70px !important;
            font-weight: 700 !important;
            box-shadow: 0 0 0 rgba(0,0,0,0) !important;
            transition: all 0.2s ease-in-out !important;
        }
        button[data-baseweb="tab"]:hover {
            border-color: #60a5fa !important;
            box-shadow: 0 0 16px rgba(96, 165, 250, 0.35) !important;
            transform: translateY(-2px);
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.35) !important;
        }
    """
    if theme == "Light":
        dashboard_theme_css = """
            .dash-shell {
                background: linear-gradient(135deg, #ddd6fe, #fed7aa, #bfdbfe);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 20px;
                padding: 18px;
                margin-bottom: 16px;
            }
            .dash-header {
                background: linear-gradient(135deg, #c4b5fd, #fdba74);
                border-radius: 18px;
                padding: 22px;
                color: #0f172a;
                margin-bottom: 14px;
                box-shadow: 0 10px 24px rgba(124, 58, 237, 0.22);
            }
            .dash-title {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 2.0rem;
                font-weight: 800;
                margin: 0;
                color: #0f172a;
            }
            .dash-subtitle {
                margin-top: 8px;
                font-size: 1rem;
                color: #1e293b;
            }
            .dash-heading {
                color: #7c3aed;
                font-size: 1.2rem;
                font-weight: 700;
                margin: 8px 0 8px 0;
            }
            .dash-text {
                color: #334155;
                margin-bottom: 10px;
            }
            .dash-list {
                color: #334155;
                line-height: 1.7;
                margin-left: 18px;
            }
            div[data-baseweb="tab-list"] {
                gap: 12px;
                flex-wrap: wrap;
                margin-bottom: 10px;
            }
            button[data-baseweb="tab"] {
                background: linear-gradient(135deg, #ffffff, #fed7aa) !important;
                color: #0f172a !important;
                border: 1px solid rgba(249, 115, 22, 0.45) !important;
                border-radius: 14px !important;
                min-width: 220px !important;
                min-height: 70px !important;
                font-weight: 700 !important;
                box-shadow: 0 0 0 rgba(0,0,0,0) !important;
                transition: all 0.2s ease-in-out !important;
            }
            button[data-baseweb="tab"]:hover {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 14px rgba(59, 130, 246, 0.24) !important;
                transform: translateY(-2px);
            }
            button[data-baseweb="tab"][aria-selected="true"] {
                border-color: #7c3aed !important;
                box-shadow: 0 0 18px rgba(124, 58, 237, 0.28) !important;
            }
        """

    st.markdown(f"<style>{dashboard_theme_css}</style>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='dash-header'>
            <h1 class='dash-title'>📊 Dashboard</h1>
            <div class='dash-subtitle'>Advanced tools for code analysis and management</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ================= TOOLS MENU - COLORFUL BUTTONS =================
    st.markdown(
        """
        <div style='margin: 20px 0; text-align: center;'>
            <h3 style='color: #facc15; margin-bottom: 16px;'>⚡ Quick Tools & Options</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tool_col1, tool_col2, tool_col3, tool_col4, tool_col5 = st.columns(5)

    with tool_col1:
        if st.button("🔍 Filter", use_container_width=True, key="dashboard_filter_btn"):
            st.session_state.show_filter = True
            st.session_state.show_search = False
            st.session_state.show_tests = False
            st.session_state.show_export = False
            st.session_state.show_help = False
            pass

    with tool_col2:
        if st.button("🔎 Search", use_container_width=True, key="dashboard_search_btn"):
            st.session_state.show_search = True
            st.session_state.show_filter = False
            st.session_state.show_tests = False
            st.session_state.show_export = False
            st.session_state.show_help = False
            pass

    with tool_col3:
        if st.button("✅ Tests", use_container_width=True, key="dashboard_tests_btn"):
            st.session_state.show_tests = True
            st.session_state.show_filter = False
            st.session_state.show_search = False
            st.session_state.show_export = False
            st.session_state.show_help = False
            pass

    with tool_col4:
        if st.button("💾 Export", use_container_width=True, key="dashboard_export_btn"):
            st.session_state.show_export = True
            st.session_state.show_filter = False
            st.session_state.show_search = False
            st.session_state.show_tests = False
            st.session_state.show_help = False
            pass

    with tool_col5:
        if st.button("❓ Help", use_container_width=True, key="dashboard_help_btn"):
            st.session_state.show_help = True
            st.session_state.show_filter = False
            st.session_state.show_search = False
            st.session_state.show_tests = False
            st.session_state.show_export = False
            pass


    st.markdown("</div>", unsafe_allow_html=True)


# ================= TOOL DISPLAYS =================
# Display modals/sections for tool buttons when activated

if st.session_state.get("show_filter"):

    st.markdown(
        """
        <div class="glass-card">
            <h2 style="color: #38bdf8; display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.8rem;">🔍</span> Filter Functions
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_type = st.selectbox(
            "Filter By",
            ["Docstring Status", "File", "Line Count"],
            key="filter_type",
        )
    with filter_col2:
        if filter_type == "Docstring Status":
            filter_value = st.selectbox("Status", ["All", "Documented", "Missing"], key="filter_docstring")
            filtered_results = [
                fn for fn in dashboard_functions
                if filter_value == "All" or 
                   (filter_value == "Documented" and fn.get("doc")) or
                   (filter_value == "Missing" and not fn.get("doc"))
            ]
        elif filter_type == "File":
            selected_filters = st.multiselect("Select Files", files, key="filter_files")
            filtered_results = [fn for fn in dashboard_functions if fn.get("file") in selected_filters] if selected_filters else dashboard_functions
        else:
            # Calculate available line counts from functions
            line_counts = sorted(set(fn.get("end", 0) - fn.get("start", 0) for fn in dashboard_functions if fn.get("end", 0)))
            line_count_options = ["All"] + [str(lc) for lc in line_counts]
            selected_lines = st.selectbox("Select Line Count", line_count_options, key="filter_line_count")
            
            if selected_lines == "All":
                filtered_results = dashboard_functions
            else:
                selected_line_count = int(selected_lines)
                filtered_results = [fn for fn in dashboard_functions if (fn.get("end", 0) - fn.get("start", 0)) == selected_line_count]
    
    st.metric("Filtered Results", len(filtered_results))
    if filtered_results:
        st.dataframe(
            pd.DataFrame(filtered_results)[["file", "name", "start", "end", "doc"]],
            use_container_width=True,
            hide_index=True,
        )


if st.session_state.get("show_search"):
   
    st.markdown(
        """
        <div class="glass-card">
            <h2 style="color: #a78bfa; display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.8rem;">🔎</span> Search Functions
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    search_query = st.text_input("Enter function name or pattern:", key="search_query")
    if search_query:
        import re
        pattern = search_query.lower()
        search_results = [fn for fn in dashboard_functions if pattern in fn["name"].lower()]
        st.success(f"Found {len(search_results)} matching function(s)")
        if search_results:
            st.dataframe(
                pd.DataFrame(search_results)[["file", "name", "start", "end", "doc"]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Enter a search term to find functions")


if st.session_state.get("show_tests"):
   
    st.markdown(
        """
        <div class="glass-card">
            <h2 style="color: #22c55e; display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.8rem;">✅</span> Tests Module
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    report_path = "storage/reports/pytest_results.json"

    # Button to run pytest
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("🚀 Run Pytest (JSON Report)", use_container_width=True, key="run_pytest_btn"):
            with st.spinner("Running pytest... This may take a moment"):
                test_result = _run_pytest_command("tests", report_path)
            
            if test_result["success"]:
                st.success("✅ All tests passed!")
            else:
                st.warning(f"⚠️ Some tests failed (Exit code: {test_result['returncode']})")
            
            if test_result["stdout"]:
                with st.expander("📋 Test Output"):
                    st.code(test_result["stdout"], language="bash")
            
            if test_result["stderr"]:
                with st.expander("❌ Error Output"):
                    st.code(test_result["stderr"], language="bash")

    report_data = _load_pytest_json_report(report_path)
    if report_data:
        summary = report_data.get("summary", {}) if isinstance(report_data, dict) else {}
        report_total = summary.get("total", 0)
        report_passed = summary.get("passed", 0)
        report_failed = summary.get("failed", 0) + summary.get("errors", 0)
        duration = summary.get("duration", 0)
    else:
        st.info("Run pytest to generate the JSON report and populate pass/fail results.")
    
    st.divider()
    
    # Load and display test statistics
    test_stats = _collect_dashboard_test_stats("tests")
    test_df = pd.DataFrame(test_stats)
    
    col1, col2, col3 = st.columns(3)
    total_tests = sum(stat["total"] for stat in test_stats)
    total_passed = sum(stat["passed"] for stat in test_stats)
    total_pending = sum(stat.get("pending", 0) for stat in test_stats)
    total_failed = max(total_tests - total_passed - total_pending, 0)
    
    with col1:
        st.metric("Total Tests", total_tests)
    with col2:
        st.metric("Passed", total_passed)
    with col3:
        st.metric("Failed", total_failed)
    
    st.divider()
    
    # Bar graph for test results
    if test_stats and total_tests > 0:
        test_chart_data = pd.DataFrame({
            "Test File": [stat["label"] for stat in test_stats],
            "Passed": [stat["passed"] for stat in test_stats],
            "Failed": [max(stat["total"] - stat["passed"] - stat.get("pending", 0), 0) for stat in test_stats],
            "Pending": [stat.get("pending", 0) for stat in test_stats],
        })
        
        st.write("**Test Results by File:**")
        
        if PLOTLY_AVAILABLE:
            fig = go.Figure(data=[
                go.Bar(
                    x=test_chart_data["Test File"],
                    y=test_chart_data["Passed"],
                    name="Passed",
                    marker=dict(color="#22c55e"),
                ),
                go.Bar(
                    x=test_chart_data["Test File"],
                    y=test_chart_data["Failed"],
                    name="Failed",
                    marker=dict(color="#ef4444"),
                ),
                go.Bar(
                    x=test_chart_data["Test File"],
                    y=test_chart_data["Pending"],
                    name="Pending",
                    marker=dict(color="#f59e0b"),
                ),
            ])
            fig.update_layout(
                barmode="stack",
                title="Test Results by File",
                xaxis_title="Test File",
                yaxis_title="Test Count",
                height=400,
                hovermode="x unified",
                template="plotly_white" if theme == "Light" else "plotly_dark",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(test_chart_data.set_index("Test File"))
    
    st.divider()
    
    st.write("**Test Statistics:**")
    st.dataframe(test_df[["label", "passed", "pending", "total"]], use_container_width=True, hide_index=True)


if st.session_state.get("show_export"):
    
    st.markdown(
        """
        <div class="glass-card">
            <h2 style="color: #f59e0b; display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.8rem;">💾</span> Export Data
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    project_metrics = calculate_metrics(dashboard_functions)
    project_total = len(dashboard_functions)
    project_documented = sum(1 for fn in dashboard_functions if fn.get("doc"))
    project_coverage = round((project_documented / project_total) * 100, 2) if project_total else 0
    metrics_snapshot = {
        "maintainability_index": project_metrics.get("maintainability_index", 0),
        "docstring_coverage": project_coverage,
        "total_functions": project_total,
        "documented_functions": project_documented,
        "undocumented_functions": max(project_total - project_documented, 0),
    }
    files_summary = {
        "scan_path": path_to_scan,
        "python_files": len(files),
        "file_list": files,
        "selected_file": selected_file,
    }
    
    st.markdown(
        """
        <div class="glass-card tool-display">
            <h4 style="margin:0 0 8px 0;">Summary Metrics</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Files", files_summary["python_files"])
    with c2:
        st.metric("Functions", metrics_snapshot["total_functions"])
    with c3:
        st.metric("Documented", metrics_snapshot["documented_functions"])
    with c4:
        st.metric("Coverage %", metrics_snapshot["docstring_coverage"])

    st.markdown(
        """
        <div class="glass-card tool-display">
            <h4 style="margin:0 0 8px 0;">Files & Functions (Short)</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )
    per_file_counts = {}
    for item in dashboard_functions:
        key = item.get("file", "unknown")
        entry = per_file_counts.setdefault(key, {"total": 0, "documented": 0})
        entry["total"] += 1
        if item.get("doc"):
            entry["documented"] += 1
    preview_names = []
    for item in dashboard_functions:
        label = f"{item.get('file')}::{item.get('name')}"
        preview_names.append(label)
    compact_payload = {
        "files": {
            "scan_path": files_summary["scan_path"],
            "python_files": files_summary["python_files"],
            "selected_file": files_summary["selected_file"],
            "all_files": files_summary["file_list"],
        },
        "functions_summary": {
            "total_functions": len(dashboard_functions),
            "per_file_counts": per_file_counts,
            "all_functions": preview_names,
        },
    }
    st.code(json.dumps(compact_payload, indent=2), language="json")
    
    export_format = st.radio(
        "Export Format",
        ["JSON Summary", "CSV Functions", "JSON Report", "JSON Functions Details"],
        horizontal=True,
    )
    
    if export_format == "JSON Summary":
        summary_data = {
            "total_functions": dashboard_total,
            "documented": dashboard_documented,
            "coverage": round(dashboard_coverage, 2),
            "pep257_violations": len(dashboard_violations),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        st.download_button("Download JSON", json.dumps(summary_data, indent=2), "summary.json", "application/json")
    elif export_format == "CSV Functions":
        if dashboard_functions:
            csv_data = pd.DataFrame(dashboard_functions).to_csv(index=False)
            st.download_button("Download CSV", csv_data, "functions.csv", "text/csv")
    elif export_format == "JSON Report":
        report_data = {
            "metadata": {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "files": len(files)},
            "summary": {"total_functions": dashboard_total, "documented": dashboard_documented, "coverage": dashboard_coverage},
            "violations": [{"item": item[0], "rule": item[1]} for item in dashboard_violations],
        }
        st.download_button("Download Report", json.dumps(report_data, indent=2), "report.json", "application/json")
    else:
        functions_payload = {
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "files": len(files),
                "function_count": dashboard_total,
            },
            "functions": dashboard_functions,
        }
        st.download_button(
            "Download Functions JSON",
            json.dumps(functions_payload, indent=2),
            "dashboard_functions.json",
            "application/json",
        )


if st.session_state.get("show_help"):

    st.markdown(
        """
        <div class="help-header-card">
            <div style="display:flex; align-items:center; gap:10px; font-size:1.2rem; font-weight:800;">
                <span style="font-size:1.5rem;">&#8505;</span>
                <div>
                    <div>Help & Tips</div>
                    <div style="font-size:0.9rem; font-weight:600;">Quick guide</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="help-card-grid">
            <div class="help-card variant-scan">
                <div class="help-card-title">&#128269; Scan</div>
                <div class="help-card-text">Analyze files in seconds.</div>
            </div>
            <div class="help-card variant-coverage">
                <div class="help-card-title">&#128202; Coverage</div>
                <div class="help-card-text">Track docstring health.</div>
            </div>
            <div class="help-card variant-docs">
                <div class="help-card-title">&#128196; Docstrings</div>
                <div class="help-card-text">Generate and refine fast.</div>
            </div>
            <div class="help-card variant-validation">
                <div class="help-card-title">&#9989; Validation</div>
                <div class="help-card-text">PEP 257 compliance checks.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Metrics Section")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(
            """
            <div class="glass-card help-panel variant-coverage" style="border-radius:12px; background: linear-gradient(135deg, #dbeafe, #bfdbfe); border-color: rgba(59, 130, 246, 0.35);">
                <div style="font-weight:800; color:#f8fafc; margin-bottom:6px;">&#128200; Coverage Metrics</div>
                <ul style="color:#e2e8f0; margin:0 0 0 18px;">
                    <li>Coverage % = (Documented / Total) x 100</li>
                    <li>Green badge (&gt;80% coverage)</li>
                    <li>Yellow badge (50-79% coverage)</li>
                    <li>Red badge (&lt;50% coverage)</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="glass-card help-panel variant-tests" style="border-radius:12px; margin-top:12px; background: linear-gradient(135deg, #ffe4e6, #fecdd3); border-color: rgba(244, 63, 94, 0.35);">
                <div style="font-weight:800; color:#f8fafc; margin-bottom:6px;">&#129514; Test Results</div>
                <ul style="color:#e2e8f0; margin:0 0 0 18px;">
                    <li>Real time test execution monitoring</li>
                    <li>Pass/fail ratio visualization</li>
                    <li>Per-file test breakdown</li>
                    <li>Integration with pytest reports</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_right:
        st.markdown(
            """
            <div class="glass-card help-panel variant-status" style="border-radius:12px; background: linear-gradient(135deg, #ede9fe, #ddd6fe); border-color: rgba(124, 58, 237, 0.35);">
                <div style="font-weight:800; color:#f8fafc; margin-bottom:6px;">&#128994; Function Status</div>
                <ul style="color:#e2e8f0; margin:0 0 0 18px;">
                    <li>Green: Complete docstring present</li>
                    <li>Red: Missing or incomplete docstrings</li>
                    <li>Auto detection of docstring styles</li>
                    <li>Style specific validation</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="glass-card help-panel variant-styles" style="border-radius:12px; margin-top:12px; background: linear-gradient(135deg, #ccfbf1, #99f6e4); border-color: rgba(20, 184, 166, 0.35);">
                <div style="font-weight:800; color:#f8fafc; margin-bottom:6px;">&#128196; Docstring Styles</div>
                <ul style="color:#e2e8f0; margin:0 0 0 18px;">
                    <li>Google: Args, Returns, Raises</li>
                    <li>NumPy: Parameters/Returns with dashes</li>
                    <li>reST: :param, :type directives</li>
                    <li>Auto style detection and validation</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Getting Started")
    st.markdown(
        """
        <div class="glass-card help-panel" style="border-radius:12px;">
            <details>
                <summary style="font-weight:800; color:#f8fafc;">Open step-by-step guide</summary>
                <ol style="color:#e2e8f0; margin:10px 0 0 18px;">
                    <li>Scan your project - Enter the path and click scan</li>
                    <li>Review coverage - Check the home page statistics</li>
                    <li>Generate docstrings - Navigate to docstrings tab</li>
                    <li>Validate - Ensure PEP-257 compliance</li>
                    <li>Export - Download reports</li>
                </ol>
            </details>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Pro Tips")
    st.markdown(
        """
        <div class="glass-card help-panel" style="border-radius:12px;">
            <ul style="color:#e2e8f0; margin:0 0 0 18px;">
                <li>Use filters to focus on undocumented functions</li>
                <li>Preview before applying changes</li>
                <li>Export reports for CI/CD integration</li>
                <li>Check metrics regularly</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Global final override (runs regardless of which panel is open)
if theme == "Light":
    st.markdown(
        """
        <style>
        button[key="dashboard_filter_btn"],
        button[key="dashboard_search_btn"],
        button[key="dashboard_tests_btn"],
        button[key="dashboard_export_btn"],
        button[key="dashboard_help_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
            color: #ffffff !important;
            border: 0 !important;
            box-shadow: 0 8px 18px rgba(251, 146, 60, 0.28) !important;
        }
        button[key="dashboard_filter_btn"]:hover,
        button[key="dashboard_search_btn"]:hover,
        button[key="dashboard_tests_btn"]:hover,
        button[key="dashboard_export_btn"]:hover,
        button[key="dashboard_help_btn"]:hover {
            filter: brightness(1.05);
            transform: translateY(-1px) scale(1.01);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Final CSS override to enforce scan-button color on dashboard buttons
if theme == "Light":
    st.markdown(
        """
        <style>
        button[key="dashboard_filter_btn"],
        button[key="dashboard_search_btn"],
        button[key="dashboard_tests_btn"],
        button[key="dashboard_export_btn"],
        button[key="dashboard_help_btn"] {
            background: linear-gradient(90deg, #fdba74, #fb923c) !important;
            box-shadow: 0 8px 18px rgba(251, 146, 60, 0.28) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
