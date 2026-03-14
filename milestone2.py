"""Streamlit app for scanning Python files and validating PEP 257 docstrings."""

import os
import ast
import re
import json
import subprocess
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="AI Code Reviewer",
    page_icon="🧠",
    layout="wide"
)

# ================= COLORFUL UI =================
st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        background: linear-gradient(135deg, #dbeafe, #fef3c7, #ecfeff);
        color: #0f172a;
        font-family: "Segoe UI", sans-serif;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a, #2563eb);
        color: white;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    h1, h2, h3 {
        color: #1e40af;
        font-weight: 700;
    }
    .card {
        background-color: #818CF8;
        padding: 18px;
        border-radius: 14px;
        border-left: 6px solid #2563eb;
        box-shadow: 0 8px 18px rgba(0,0,0,0.08);
        margin-bottom: 14px;
    }
    .error {
        background-color: #e39a9a;
        border-left: 6px solid #dc2626;
        padding: 14px;
        border-radius: 10px;
        margin-bottom: 10px;
        color: #7f1d1d;
    }
    /* ===== COVERAGE HIGHLIGHT BOX ===== */
    .coverage-highlight {
        background: linear-gradient(#07409C, #7D27F5);
        padding: 28px;
        border-radius: 18px;
        text-align: center;
        color: white;
        font-size: 26px;
        font-weight: 800;
    }
    button {
        background: linear-gradient(90deg,#2FC809, #E7F527) !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    button:hover {
        transform: scale(1.04);
        transition: 0.2s ease-in-out;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================= SIDEBAR =================
st.sidebar.title("🧠 AI Code Reviewer")

view = st.sidebar.selectbox(
    "Navigation",
    ["🏠 Home", "📊 Metrics", "📘 Docstrings", "✅ Validation", "📈 Dashboard"]
)

path_to_scan = st.sidebar.text_input("Path to scan", "examples")
output_path = st.sidebar.text_input("Output JSON", "review_output.json")
scan_clicked = st.sidebar.button("🔍 Scan")

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
        inserts.append((0, '"""Module description."""\n\n'))

    for node in ast.walk(tree):
        name = getattr(node, "name", None)

        if isinstance(node, ast.ClassDef):
            indent = " " * node.col_offset
            if not ast.get_docstring(node) and (fix_all or target_function == name):
                inserts.append((node.lineno, f'{indent}    """Class description."""\n'))

        if isinstance(node, ast.FunctionDef):
            indent = " " * node.col_offset
            parent = getattr(node, "parent", None)
            if not ast.get_docstring(node) and (fix_all or target_function == name):
                if isinstance(parent, ast.ClassDef):
                    inserts.append((node.lineno, f'{indent}    """Method description."""\n'))
                else:
                    inserts.append((node.lineno, f'{indent}    """Function description."""\n'))

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
            replacements = {
                "Returns": "Return",
                "Function": "Compute",
                "Method": "Process",
                "Class": "Represent",
                "Module": "Provide",
            }
            for old, new in replacements.items():
                if lines[0].startswith(old):
                    lines[0] = lines[0].replace(old, new, 1)
                    changed = True
                    break
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


# ================= FILE SELECTION =================
files = [f for f in os.listdir(path_to_scan) if f.endswith(".py")] if os.path.exists(path_to_scan) else []
selected_file = st.sidebar.selectbox("Select File", files)

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

# ================= SCAN =================
if scan_clicked and selected_file:
    selected_path = os.path.join(path_to_scan, selected_file)
    tree = parse_file(selected_path)
    if tree:
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

# ================= HOME =================
if view == "🏠 Home" and st.session_state.functions:
    st.title("🤖 AI Code Reviewer")

    coverage = st.session_state.coverage

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
        {st.session_state.coverage}%
    </div>
    """,
    unsafe_allow_html=True
)
    with c2:
        st.metric("Total Functions", st.session_state.total)
    with c3:
        st.metric("Documented", st.session_state.documented)

    st.markdown(
        f"<div class='status-box {status_class}'>Status: {badge}</div>",
        unsafe_allow_html=True
    )

# ================= METRICS =================
if view == "📊 Metrics" and st.session_state.functions:
    st.title("📊 Code Metrics")

    for fn in st.session_state.functions:
        st.markdown(
            f"<div class='card'><b>{fn['name']}</b><br>"
            f"Lines {fn['start']}–{fn['end']}<br>"
            f"Docstring: {'Yes' if fn['doc'] else 'No'}</div>",
            unsafe_allow_html=True
        )

    st.download_button(
        "⬇️ Download Docstring Coverage Report",
        json.dumps(coverage_report(os.path.join(path_to_scan, selected_file)), indent=4),
        "coverage_report.json",
        "application/json"
    )

# ================= DOCSTRINGS =================
elif view == "📘 Docstrings":
    st.title("📘 Docstrings")
    st.info("This section is intentionally empty.")

# ================= VALIDATION =================
elif view == "✅ Validation" and selected_file:
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
elif view == "📈 Dashboard" and st.session_state.metrics_scanned:
    st.title("📈 Summary Dashboard")
    st.json(st.session_state.metrics_result)
