"""Build viewer/index.html: the interactive 3D replay page.

    python3 sim/mechanism.py && make -C firmware/host_test && python3 tools/build_viewer.py

Embeds sim/out/mechanism.json (geometry) and firmware/host_test/sequence_nominal.csv
(the firmware's simulated run) into viewer/template.html and copies the plots.
Open viewer/index.html in a browser (needs internet for three.js from the CDN).
"""
import csv
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mech = json.load(open(os.path.join(ROOT, "sim/out/mechanism.json")))
rows = []
with open(os.path.join(ROOT, "firmware/host_test/sequence_nominal.csv")) as f:
    for k, r in enumerate(csv.DictReader(f)):
        if k % 2 == 0 or r["state"] in ("DONE", "FAULT"):
            rows.append([round(float(r["t"]), 3), r["state"], round(float(r["theta_ref_deg"]), 2),
                         round(float(r["theta_deg"]), 2), round(float(r["volts"]), 2), round(float(r["force_set"]), 2),
                         round(float(r["force"]), 3), round(float(r["servo_deg"]), 1)])
html = open(os.path.join(ROOT, "viewer/template.html")).read()
html = html.replace("__MECH__", json.dumps(mech, separators=(",", ":")))
html = html.replace("__TRAJ__", json.dumps(rows, separators=(",", ":")))
html = html.replace("__CONCEPTS_URL__", "https://claude.ai/artifact/Y5mf8ChwZyVuCEkr7pjYP1")
open(os.path.join(ROOT, "viewer/index.html"), "w").write(html)
os.makedirs(os.path.join(ROOT, "viewer/plots"), exist_ok=True)
for n in ("flip_path_3d", "flip_clearance", "flip_tracking", "flip_step", "grip_step", "simavr_sim_plant_run"):
    shutil.copy(os.path.join(ROOT, "sim/out", n + ".png"), os.path.join(ROOT, "viewer/plots", n + ".png"))
print(f"viewer/index.html: {len(rows)} samples, {len(html) // 1024} KB")

# Concepts page (all four concepts animated). Links back to the published replay page.
VIEWER_URL = "https://claude.ai/artifact/Sq3iuS55Be8UzQHFSEEF2F"
c = open(os.path.join(ROOT, "viewer/concepts_template.html")).read()
c = c.replace("__MECH__", json.dumps(mech, separators=(",", ":"))).replace("__VIEWER_URL__", VIEWER_URL)
open(os.path.join(ROOT, "viewer/concepts.html"), "w").write(c)
print(f"viewer/concepts.html: {len(c) // 1024} KB")
