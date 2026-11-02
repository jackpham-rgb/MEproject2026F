"""Build viewer/concepts.html: the four concepts animated side by side.

    python3 backend/tools/build_concepts_viewer.py

Embeds viewer/data/mechanism.json (Concept D geometry) into viewer/concepts_template.html.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
mech = json.load(open(os.path.join(ROOT, "viewer/data/mechanism.json")))
c = open(os.path.join(ROOT, "viewer/concepts_template.html")).read()
c = c.replace("__MECH__", json.dumps(mech, separators=(",", ":")))
open(os.path.join(ROOT, "viewer/concepts.html"), "w").write(c)
print(f"viewer/concepts.html: {len(c) // 1024} KB")
