import os
import json
import ast
import streamlit as st
from analyzer.metrics import analyze_file

st.set_page_config(page_title="AI Code Reviewer", layout="wide")

# ---------------- SESSION STATE ----------------
if "metrics_scanned" not in st.session_state:
      st.session_state.metrics_scanned = False

if "metrics_result" not in st.session_state:
      st.session_state.metrics_result = None

# ---------------- SIDEBAR ----------------
st.sidebar.title("🧠 AI Code Reviewer")

view = st.sidebar.selectbox(
   "Select View",
   [
       "Metrics",
       "Docstring Coverage",
       "Code Structure",
       "Complexity Hotspots",
       "Summary Report"
   ]
)

path_to_scan = st.sidebar.text_input("Path to scan", "examples")
output_path = st.sidebar.text_input("Output JSON path", "storage/review_logs.json")

python_files = []
if os.path.exists(path_to_scan):
   python_files = [f for f in os.listdir(path_to_scan) if f.endswith(".py")]

selected_file = st.sidebar.selectbox("Select File", python_files)

# ---------------- AST HELPERS ----------------
def add_parent_references(tree):
   for node in ast.walk(tree):
       for child in ast.iter_child_nodes(node):
           child.parent = node

def coverage_report(file_path):
   with open(file_path, "r", encoding="utf-8") as f:
       tree = ast.parse(f.read())

   add_parent_references(tree)

   total = 0
   documented = 0
   details = []

   for node in ast.walk(tree):
       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
           total += 1
           has_doc = bool(ast.get_docstring(node))

           if has_doc:
               documented += 1

           details.append({
               "Function Name": node.name,
               "Type": "Method" if isinstance(node.parent, ast.ClassDef) else "Function",
               "Start Line": node.lineno,
               "End Line": node.end_lineno,
               "Has Docstring": has_doc
           })

   coverage = round((documented / total) * 100, 2) if total else 0

   return {
       "total_functions": total,
       "documented_functions": documented,
       "undocumented_functions": total - documented,
       "coverage_percent": coverage,
       "details": details
   }

# ---------------- METRICS VIEW ----------------
if view == "Metrics":
   st.subheader("📊 Code Metrics")

   file_path = os.path.join(path_to_scan, selected_file)

   # ---- Scan Metrics Button ----
   if st.button("Scan"):
       result = analyze_file(file_path)
       st.session_state.metrics_scanned = True
       st.session_state.metrics_result = result
   

       with open(output_path, "w", encoding="utf-8") as f:
           json.dump({"metrics": result}, f, indent=4)

   # ---- Display Metrics ----
   if st.session_state.metrics_scanned:
       result = st.session_state.metrics_result

   
       st.metric("Maintainability Index", result["maintainability_index"])
   

       st.subheader("Function Complexity")
       st.json(result["functions"])

       # ---- Coverage BELOW complexity ----
       st.divider()
       st.subheader("📘 Docstring Coverage")

       if st.button("Generate Coverage Report"):
           report = coverage_report(file_path)

           c1, c2, c3, c4 = st.columns(4)
           c1.metric("Total Functions", report["total_functions"])
           c2.metric("Documented", report["documented_functions"])
           c3.metric("Undocumented", report["undocumented_functions"])
           c4.metric("Coverage (%)", report["coverage_percent"])

           st.subheader("Function-wise Docstring Status")
           st.table(report["details"])

           with open(output_path, "w", encoding="utf-8") as f:
               json.dump(
                   {
                       "metrics": result,
                       "coverage_report": report
                   },
                   f,
                   indent=4
               )

# ---------------- DOCSTRING COVERAGE (STANDALONE) ----------------
elif view == "Docstring Coverage":
   st.subheader("📘 Docstring Coverage")

   file_path = os.path.join(path_to_scan, selected_file)

   if st.button("Generate Coverage Report"):
       report = coverage_report(file_path)
       st.metric("Coverage (%)", report["coverage_percent"])
       st.table(report["details"])

# ---------------- CODE STRUCTURE ----------------
elif view == "Code Structure":
   st.subheader("🧩 Code Structure")

   file_path = os.path.join(path_to_scan, selected_file)

   with open(file_path, "r", encoding="utf-8") as f:
       tree = ast.parse(f.read())

   structure = {"functions": [], "classes": []}

   for node in ast.walk(tree):
       if isinstance(node, ast.FunctionDef):
           structure["functions"].append(node.name)
       elif isinstance(node, ast.ClassDef):
           structure["classes"].append(node.name)

   st.json(structure)

# ---------------- COMPLEXITY HOTSPOTS ----------------
elif view == "Complexity Hotspots":
   st.subheader("🔥 Complexity Hotspots")

   file_path = os.path.join(path_to_scan, selected_file)
   result = analyze_file(file_path)

   hotspots = [
       fn for fn in result["functions"]
       if fn["complexity"] >= 5
   ]

   if hotspots:
       st.warning("High complexity functions detected")
       st.json(hotspots)
   else:
       st.success("No complexity hotspots found")

# ---------------- SUMMARY REPORT ----------------
elif view == "Summary Report":
   st.subheader("📊 Summary Report")

   file_path = os.path.join(path_to_scan, selected_file)
   metrics = analyze_file(file_path)
   coverage = coverage_report(file_path)

   summary = {
       "maintainability_index": metrics["maintainability_index"],
       "docstring_coverage": coverage["coverage_percent"],
       "total_functions": coverage["total_functions"]
   }

   st.json(summary)

   with open(output_path, "w", encoding="utf-8") as f:
       json.dump({"summary_report": summary}, f, indent=4)