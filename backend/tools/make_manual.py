"""Assembly manual, step 1 of 2: the steps + a check that every part can really get to its place.

    python3.13 backend/tools/make_manual.py      # steps + insertion check  (~5 min)
    node backend/tools/render_manual.js          # pictures + docs/12_assembly_manual.pdf

For every step the new parts slide in along their arrow from `dist` mm away to their final place, in
3 mm steps, and at each position they are intersected (solid booleans) with every part already
assembled. Pairs that touch on purpose (press fits, a spline in its horn, a screw in its pilot) are
allowed. Writes backend/cad/build/manual_steps.json and cad/check/assembly_check.txt.
"""
import json
import os
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import model as M  # noqa: E402

S6, S8, SB = "#6-32 × ½″ screw", "#8-32 × ½″ screw", "servo-bag screw"
UP, DOWN, FRONT, BACK, LEFT = (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0), (-1, 0, 0)

# (title, new parts, comes-from direction, travel mm, hardware, servo badge, one-line note, view az/el, only-these parts)
STEPS = [
    ("Bearing into the base", ["bearing_6807"], UP, 40, [], None,
     "Press on the outer ring only, evenly (flat block + vise)", (-60, 35), ["base"]),
    ("Turntable servo", ["turntable_servo_MG996R"], DOWN, 60, [(4, S8)], None,
     "From underneath; body points away from the arm side", (-120, -30), None),
    ("Weight + feet", ["base"], None, 0, [], None,
     "~100 g in the 2 back pockets (washers, pennies, rocks): GLUE or TAPE it in. 4 feet or hot-glue dots", (-120, -40), None),
    ("Servo horn", ["turntable_horn"], UP, 40, [(1, SB)], ("MG996R", "135°"),
     "Set the servo to 135° first (servo_setup: t 135)", (-60, 40), None),
    ("Turret plate", ["turret_plate"], UP, 60, [(4, SB)], None,
     "Hub into the bearing; rod bosses point at the START can. Turns 90° freely", (-60, 35), None),
    ("Linear bearings into the carriage", ["LM6UU_L1", "LM6UU_R1", "LM6UU_L2", "LM6UU_R2"], None, 30, [], None,
     "2 from below, 2 from above, flush with the faces", (-40, 20), ["carriage_arm"]),
    ("Rods", ["rod_L", "rod_R"], UP, 120, [], None,
     "Press into the blind holes of the turret plate", (-60, 25), None),
    ("Carriage onto the rods", ["carriage_arm", "LM6UU_L1", "LM6UU_R1", "LM6UU_L2", "LM6UU_R2"], UP, 110, [], None,
     "It must slide down under its own weight", (-60, 20), None),
    ("Spine", ["spine"], UP, 80, [(2, S6)], None,
     "Onto the turret plate behind the rods, screws from above", (-130, 25), None),
    ("Top cap", ["top_cap"], UP, 40, [(2, S6)], None,
     "Over the rod tops onto the spine. Carriage still slides freely?", (-130, 30), None),
    ("Lift servo", ["lift_servo_MG90S"], LEFT, 40, [(2, SB)], ("MG90S lift", "30°"),
     "Body through the spine bracket from the left", (-150, 15), None),
    ("Lift link", ["lift_link"], UP, 15, [(1, S6)], None,
     "Carriage end: #6-32 as the pivot, don't over-tighten: it must turn", (-150, 15), None),
    ("Crank", ["lift_crank"], LEFT, 8, [(1, SB), (1, SB)], ("MG90S lift", "30°"),
     "Single-arm horn trimmed to 20 mm, on the spline at 30°; pin screw into the link", (-150, 15), None),
    ("Wrist servo", ["wrist_servo"], FRONT, 45, [(2, SB)], ("MG90S wrist", "0°"),
     "Body through the bracket from the front", (-140, 20), None),
    ("Wrist horn", ["wrist_horn"], FRONT, 25, [(1, SB)], ("MG90S wrist", "0°"), "", (-140, 20), None),
    ("Gripper frame", ["gripper_frame"], FRONT, 45, [(4, SB)], None,
     "Upright: plates level, opening facing out", (-140, 25), None),
    ("Both fingers, gears meshed", ["finger_L", "finger_R"], FRONT, 70, [], None,
     "Slide them in together between the plates, open by the same angle", (-60, 55), None),
    ("Right finger axle", ["axle_R"], UP, 25, [(1, S6)], None,
     "From the top through the right finger; it must swing freely", (-60, 55), None),
    ("Gripper servo", ["gripper_servo_SG90"], UP, 40, [(2, SB), (1, SB)], ("SG90", "20°"),
     "Spline down into the left finger's socket (it is the horn)", (-60, 55), None),
    ("Can bumper", ["can_bumper"], FRONT, 25, [], None,
     "Silicone or rubber, 9 × 13.5 mm, superglue to the frame", (-60, 35), None),
    ("Electronics on the tray", ["arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF"], UP, 40, [], None,
     "Pegs + a dab of hot glue; breadboard is self-adhesive. Buck already set to 5.8 V", (-70, 50), ["electronics_tray"]),
    ("Panel: button, LED, power", ["start_button", "status_led", "dc_jack"], BACK, 30, [], None,
     "Through the panel holes from the front, nuts inside. Power: DC jack, or the LIZVOR terminal-block tip", (-110, 30), ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF"]),
    ("Tray onto the base", ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF", "start_button", "status_led", "dc_jack"],
     BACK, 45, [(2, S6)], None, "Tabs slide under the base wall, screws from below", (-120, 35), None),
]
# LM6UU come from below (L1/R1, lower pockets) and above (L2/R2): handled per part
PER_PART_DIR = {"LM6UU_L1": DOWN, "LM6UU_R1": DOWN, "LM6UU_L2": UP, "LM6UU_R2": UP}

ALLOWED = {frozenset(p) for p in [
    ("bearing_6807", "base"), ("bearing_6807", "turret_plate"), ("turntable_servo_MG996R", "turntable_horn"),
    ("lift_crank", "lift_servo_MG90S"), ("lift_crank", "lift_link"), ("wrist_servo", "wrist_horn"),
    ("wrist_servo", "gripper_frame"), ("gripper_servo_SG90", "finger_L"), ("axle_R", "finger_R"),
    ("axle_R", "gripper_frame"), ("rod_L", "turret_plate"), ("rod_R", "turret_plate"), ("rod_L", "top_cap"),
    ("rod_R", "top_cap"), ("lift_link", "carriage_arm")]}
for n in ("LM6UU_L1", "LM6UU_L2", "LM6UU_R1", "LM6UU_R2"):
    ALLOWED.add(frozenset((n, "carriage_arm")))
VOL_TOL = 1.0


def main():
    parts = {p["name"]: p for p in M.build_parts() if p["group"] not in ("coupon",)}
    shp = {n: p["shape"].val() for n, p in parts.items()}
    bb = {n: s.BoundingBox() for n, s in shp.items()}
    installed, out, rep, ok = ["base"], [], ["ASSEMBLY CHECK: every part slides to its place along its arrow (backend/tools/make_manual.py)",
                                       f"solid booleans every 3 mm of travel; overlap > {VOL_TOL} mm³ with an assembled part = blocked", ""], True
    for i, (title, new, dirn, dist, hw, badge, note, (az, el), only) in enumerate(STEPS, 1):
        moving = [n for n in new if n not in installed]
        blocked = []
        for n in moving:
            d = PER_PART_DIR.get(n, dirn) if dirn is not None or n in PER_PART_DIR else None
            if d is None:
                continue
            others = [o for o in (only if only else installed) if o not in new]
            for k in range(int(dist / 3), 0, -1):
                off = cq.Vector(*d) * (3 * k)
                s = shp[n].translate(off)
                b = s.BoundingBox()
                for o in others:
                    if frozenset((n, o)) in ALLOWED:
                        continue
                    B = bb[o]
                    if b.xmax < B.xmin or B.xmax < b.xmin or b.ymax < B.ymin or B.ymax < b.ymin or b.zmax < B.zmin or B.zmax < b.zmin:
                        continue
                    v = s.intersect(shp[o]).Volume()
                    if v > VOL_TOL:
                        blocked.append(f"{n} hits {o} at {3 * k} mm out ({v:.0f} mm³)")
                        break
                if blocked and blocked[-1].startswith(n):
                    break
        status = "PASS" if not blocked else "BLOCKED"
        ok &= not blocked
        rep.append(f"{i:2d}. {title:36s} {status}" + ("" if not blocked else "\n      " + "\n      ".join(blocked)))
        for n in new:
            if n not in installed:
                installed.append(n)
        out.append(dict(n=i, title=title, new=new, dir=dirn, per_part_dir={n: PER_PART_DIR[n] for n in new if n in PER_PART_DIR},
                        dist=dist, hw=hw, badge=badge, note=note, az=az, el=el,
                        show=(only + new) if only else list(installed), ok=not blocked))
        print(rep[-1], flush=True)
    rep += ["", "RESULT: " + ("every step can be assembled in this order" if ok else "BLOCKED steps above")]
    open(os.path.join(ROOT, "cad", "check", "assembly_check.txt"), "w").write("\n".join(rep) + "\n")
    json.dump(dict(steps=out), open(os.path.join(ROOT, "backend", "cad", "build", "manual_steps.json"), "w"), indent=1)
    print(rep[-1])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
