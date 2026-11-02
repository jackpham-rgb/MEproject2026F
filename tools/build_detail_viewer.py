"""Build viewer/concept_a_detail.html: animated detail CAD + check results.

    python3.13 cad/concept_a_detail/export.py && python3.13 cad/concept_a_detail/check.py
    python3 tools/build_detail_viewer.py
"""
import csv
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "cad", "concept_a_detail", "out")
mesh = json.load(open(os.path.join(OUT, "viewer_mesh.json")))
report = open(os.path.join(OUT, "check_report.txt")).read()
mass = list(csv.DictReader(open(os.path.join(OUT, "mass_table.csv"))))

page = open(os.path.join(ROOT, "viewer", "concept_a_detail_template.html")).read()
mass_rows = "".join(
    f"<tr><td>{html.escape(r['part'])}</td><td>{html.escape(r['group'])}</td><td>{html.escape(r['material'])}</td>"
    f"<td class='num'>{float(r['mass_g']):.1f}</td></tr>" for r in mass if r["part"] != "test_can")
page = page.replace("__MESH__", json.dumps(mesh, separators=(",", ":")))
page = page.replace("__REPORT__", html.escape(report))
page = page.replace("__MASS_ROWS__", mass_rows)
open(os.path.join(ROOT, "viewer", "concept_a_detail.html"), "w").write(page)
print(f"viewer/concept_a_detail.html: {os.path.getsize(os.path.join(ROOT, 'viewer', 'concept_a_detail.html')) // 1024} KB")
