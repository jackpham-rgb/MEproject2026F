"""Screwdriver access check for the assembly order: can every screw actually be driven when its step comes?

    python3.13 backend/tools/tool_access_check.py   ->  cad/check/tool_access.txt   (exit 1 if a screw is blocked)

For each step (backend/cad/build/manual_steps.json, from make_manual.py) and each screw that goes in at that step
(viewer/data/assembly.json screws, from visual.py), a screwdriver is modelled as a 4 mm shaft running 80 mm back
from the screw head along the screw's axis, plus the screw's own body (3 mm). It must not hit any part that is already
in place at that step (the part the screw passes through is in place too: only the shaft BEHIND the head counts for
it). It also checks that the screw body itself does not run into a part it shouldn't (e.g. a too-long screw).
"""
import json
import math
import os
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import model as M  # noqa: E402

SHAFT_R, SHAFT_L, TOL_MM3 = 2.0, 80.0, 1.5      # a #1 / #2 Phillips screwdriver: ~4 mm shaft
SHAFT_R_BY_KIND = {"sb": 1.5, "M3": 1.5}         # servo-bag screws take a small precision screwdriver (~3 mm shaft)
TILTS = [0.0, 4.0]                               # a screwdriver can lean a few degrees: straight first, then 4 deg x 8 ways
# the screw body is allowed inside the parts it clamps / threads into (by screw owner)
BITES = {"turntable_servo_MG996R": ["base"], "turntable_horn": ["turntable_servo_MG996R"],
         "turret_plate": ["turntable_horn"], "spine": ["turret_plate"], "top_cap": ["spine"],
         "lift_servo_MG90S": ["spine"], "lift_link": ["carriage_arm"], "lift_crank": ["lift_servo_MG90S", "lift_link"],
         "wrist_servo": ["carriage_arm"], "wrist_horn": ["wrist_servo"], "gripper_frame": ["wrist_horn"],
         "gripper_servo_SG90": ["gripper_frame"], "gripper_horn": ["finger_L"], "electronics_tray": ["base"]}


def rod(p0, d, L, r):
    d = cq.Vector(*d).normalized()
    return cq.Solid.makeCylinder(r, L, cq.Vector(*p0), d)


def main():
    parts = {p["name"]: p["shape"].val() for p in M.build_parts()}
    steps = json.load(open(os.path.join(ROOT, "backend", "cad", "build", "manual_steps.json")))["steps"]
    A = json.load(open(os.path.join(ROOT, "viewer", "data", "assembly.json")))
    first = {}
    for s in A["steps"]:
        for n in s["screws"]:
            first[n] = s["n"]
    lines, bad = ["SCREWDRIVER ACCESS: 4 mm shaft (3 mm precision driver for servo-bag screws), 80 mm behind each screw head, against every part already in place", ""], 0
    for s in steps:
        here = [sc for sc in A["screws"] if first.get(sc["name"]) == s["n"]]
        if not here:
            continue
        later = s["new"][1:]                                        # parts that go on after the first one in a step
        placed = [n for n in s["show"] if n in parts and n != "test_can"]
        for sc in here:
            h, ax = sc["head"], sc["axis"]
            back = [-a for a in ax]
            hh = sc.get("head_h", 2.0)
            start = [h[i] + back[i] * (hh + 0.3) for i in range(3)]
            sr = SHAFT_R_BY_KIND.get(sc["kind"], SHAFT_R)
            shafts = [rod(start, back, SHAFT_L, sr)]
            b = cq.Vector(*back); u = b.cross(cq.Vector(1, 0, 0) if abs(back[0]) < 0.9 else cq.Vector(0, 1, 0)).normalized(); w = b.cross(u)
            for k in range(8):
                a = math.radians(45 * k)
                dvec = b + (u * math.cos(a) + w * math.sin(a)) * math.tan(math.radians(TILTS[1]))
                shafts.append(rod(start, (dvec.x, dvec.y, dvec.z), SHAFT_L, sr))
            head = rod([h[i] + back[i] * 0.2 for i in range(3)], back, hh, sc.get("head_r", 2.0))  # the head itself
            body = rod(h, ax, sc["length"], 1.5)
            hits = []
            excl = later[later.index(sc["owner"]):] if sc["owner"] in later else (later if sc["owner"] == s["new"][0] else [])
            others = [n for n in placed if not (n in excl and n != sc["owner"])]
            best = None
            for j, sh in enumerate(shafts):                         # any clear lean is good enough
                hh_ = [(n, sh.intersect(parts[n]).Volume()) for n in others]
                hh_ = [(n, v) for n, v in hh_ if v > TOL_MM3]
                if best is None or len(hh_) < len(best[1]):
                    best = (j, hh_)
                if not hh_:
                    break
            hits += [f"screwdriver hits {n} ({v:.0f} mm3)" for n, v in best[1]]
            lean = " (screwdriver leaned 4°)" if best[0] and not best[1] else ""
            for n in others:
                if n != sc["owner"]:
                    v = head.intersect(parts[n]).Volume()
                    if v > TOL_MM3:
                        hits.append(f"screw head hits {n} ({v:.0f} mm3)")
                if n in BITES.get(sc["owner"], []) or n == sc["owner"]:
                    continue
                v = body.intersect(parts[n]).Volume()
                if v > TOL_MM3:
                    hits.append(f"screw body runs into {n} ({v:.0f} mm3)")
            ok = not hits
            bad += not ok
            lines.append(f"  step {s['n']:>2} {s['title'][:34]:<34} {sc['kind']:>3} into {sc['owner']:<24} {'PASS' + lean if ok else 'FAIL: ' + '; '.join(hits)}")
    lines += ["", f"RESULT: {'every screw can be driven in this order' if not bad else f'{bad} screw(s) blocked'}"]
    open(os.path.join(ROOT, "cad", "check", "tool_access.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
