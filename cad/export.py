"""Export the Concept A detail model.

    python3.13 cad/export.py

cad/out/
  concept_a_detail_assembly.step   SolidWorks / Fusion 360: one component per moving group
                                   grp_fixed, grp_turret, grp_crank, grp_lift, grp_wrist, grp_finger_L, grp_finger_R, grp_can; home pose, mm
  parts/<name>.step / .stl         every part, in assembly position (print orientation comes with the print files)
  viewer_mesh.json                 tessellated groups for the 3D animation page
  fusion_sequence.json             the joint values of the firmware sequence (read by fusion_animate.py)
"""
import json
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(os.path.join(OUT, "parts"), exist_ok=True)


def colour(h):
    h = h.lstrip("#")
    return cq.Color(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


MAT_COL = {"PETG": "#3d7be0", "TPU": "#2f2f2f", "buy": "#1f2329", "can": "#c0202a"}
NAME_COL = {"finger_L": "#e0a33d", "finger_R": "#e0a33d", "rod_L": "#b8bcc2", "rod_R": "#b8bcc2",
            "bearing_6807": "#b8bcc2", "axle_R": "#b8bcc2", "arduino_uno": "#1d6b4a", "buck_XL4015": "#2b5d8a",
            "mini_breadboard": "#e8e8e8", "base": "#9aa3ad", "electronics_tray": "#9aa3ad",
            "turret_plate": "#5b8def", "spine": "#5b8def", "top_cap": "#5b8def", "lift_link": "#5b8def",
            "lift_crank": "#e8e8e8", "turntable_horn": "#e8e8e8", "wrist_horn": "#e8e8e8"}
for n in ("LM6UU_L1", "LM6UU_L2", "LM6UU_R1", "LM6UU_R2"):
    NAME_COL[n] = "#b8bcc2"


def main():
    parts = M.build_parts()
    groups = {}
    mesh = {"groups": {}, "params": {k: v for k, v in M.P.items() if isinstance(v, (int, float))},
            "fw": M.FW}
    for p in parts:
        sh = p["shape"]
        cq.exporters.export(sh, os.path.join(OUT, "parts", p["name"] + ".step"))
        if p["material"] in ("PETG", "TPU") or p["group"] == "coupon":
            cq.exporters.export(sh, os.path.join(OUT, "parts", p["name"] + ".stl"), tolerance=0.05, angularTolerance=0.1)
        if p["group"] == "coupon":
            continue
        col = NAME_COL.get(p["name"], MAT_COL.get(p["material"], "#888888"))
        groups.setdefault(p["group"], cq.Assembly(name="grp_" + p["group"])).add(sh, name=p["name"], color=colour(col))
        verts, tris = sh.val().tessellate(0.4, 0.3)
        mesh["groups"].setdefault(p["group"], []).append({
            "name": p["name"], "color": col,
            "v": [round(c, 2) for vv in verts for c in (vv.x, vv.y, vv.z)],
            "f": [i for t in tris for i in t]})
    top = cq.Assembly(name="concept_a_detail")
    for g, a in groups.items():
        top.add(a, name="grp_" + g)
    top.export(os.path.join(OUT, "concept_a_detail_assembly.step"))
    # firmware sequence as joint values (degrees / mm) for the Fusion script and the viewer
    seq = []
    for label, cmd, attached in M.sequence(step_samples=24):
        j = M.joints_from_commands(**cmd)
        seq.append(dict(label=label, attached=attached, **{k: round(v, 3) for k, v in j.items()}, **cmd))
    json.dump(dict(pivot_x=M.P["pivot_x"], pivot_y=M.P["pivot_y"], grip_z=M.P["grip_z"],
                   lift_servo_tip=M.P["lift_servo_tip"], lift_theta0=M.P["lift_theta0"], samples=seq),
              open(os.path.join(OUT, "fusion_sequence.json"), "w"), indent=0)
    mesh["sequence"] = seq
    json.dump(mesh, open(os.path.join(OUT, "viewer_mesh.json"), "w"), separators=(",", ":"))
    print(f"exported {len(parts)} parts; groups: {', '.join(groups)}; "
          f"viewer mesh {os.path.getsize(os.path.join(OUT, 'viewer_mesh.json')) // 1024} KB")


if __name__ == "__main__":
    main()
