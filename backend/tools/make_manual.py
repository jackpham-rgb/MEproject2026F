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

# (title, new parts, comes-from direction, travel mm, hardware, servo badge, one-line note, view az/el, on-the-table set)
# Order (2026-11-24, after the screwdriver-access check, backend/tools/tool_access_check.py): the column is built ON THE
# TABLE first, every horn goes on its part before the servo, and every screw goes in while nothing is in the way;
# the base comes last and the finished column drops onto the turntable servo. Last field: the parts already on the
# table for that step (a sub-assembly); "COL" = everything built so far for the column; None = the robot on its base.
LM4 = ["LM6UU_L1", "LM6UU_R1", "LM6UU_L2", "LM6UU_R2"]
S6S = "#6 × ¼″ pointed sheet-metal screw"
COLUMN = ["carriage_arm"] + LM4 + ["lift_link", "spine", "lift_servo_MG90S", "lift_crank", "turret_plate", "turntable_horn",
          "rod_L", "rod_R", "top_cap", "wrist_horn", "gripper_frame", "finger_L", "finger_R", "axle_R", "gripper_horn",
          "gripper_servo_SG90", "wrist_servo", "can_bumper"]
CLAW = {"gripper_frame", "wrist_horn", "finger_L", "finger_R", "axle_R", "gripper_horn", "gripper_servo_SG90"}
STEPS = [
    ("Linear bearings into the carriage", LM4, None, 30, [], None,
     "2 from below, 2 from above, flush with the faces", (-40, 20), ["carriage_arm"]),
    ("Lift link onto the carriage", ["lift_link"], UP, 15, [(1, S6S)], None,
     "Pivot screw into the carriage's small boss: snug, then back off ¼ turn so the link swings", (-150, 15), "COL"),
    ("Lift servo into the spine", ["lift_servo_MG90S"], LEFT, 40, [(2, SB)], None,
     "Spine on its own: servo body through the bracket from the left, 2 tab screws", (-150, 15), ["spine"]),
    ("Crank: horn on the link, then on the lift servo", ["lift_crank"], LEFT, 8, [(1, SB), (1, SB)], ("MG90S lift", "30°"),
     "Screw the link's free end onto the horn's 20 mm hole FIRST, then press the horn onto the servo at 30° + centre screw", (-150, 15), "COL"),
    ("Turret plate + turntable horn (on the table)", ["turret_plate", "turntable_horn"], None, 40, [(4, SB)], None,
     "Horn under the plate, inside the hub; 4 screws down through the plate into the horn", (-60, 35), []),
    ("Spine onto the turret plate", ["spine", "lift_servo_MG90S", "lift_crank", "lift_link", "carriage_arm"] + LM4, UP, 60, [(2, S6)], None,
     "The spine (with servo, crank, link and carriage hanging on it) onto the plate behind the rod holes, 2 screws from above", (-130, 25), "COL"),
    ("Rods down through the carriage into the plate", ["rod_L", "rod_R"], UP, 120, [], None,
     "Hold the carriage level; each rod down through both its bearings into its blind hole in the plate", (-60, 25), "COL"),
    ("Top cap", ["top_cap"], UP, 40, [(2, S6)], None,
     "Over the rod tops onto the spine. Carriage still slides freely?", (-130, 30), "COL"),
    ("Gripper frame onto the wrist horn (on the table)", ["gripper_frame", "wrist_horn"], None, 25, [(4, SB)], None,
     "Horn flat on the frame's flange, 4 screws through the flange into the horn", (-140, 25), []),
    ("Both fingers, gears meshed", ["finger_L", "finger_R"], FRONT, 70, [], None,
     "Slide them in together between the plates, open by the same angle", (-60, 55), ["gripper_frame", "wrist_horn"]),
    ("Right finger axle", ["axle_R"], UP, 25, [(1, S6)], None,
     "From the top through the right finger; it must swing freely", (-60, 55), ["gripper_frame", "wrist_horn", "finger_L", "finger_R"]),
    ("Horn on the left gear, then the gripper servo", ["gripper_horn", "gripper_servo_SG90"], UP, 40, [(2, SB), (2, SB)], ("SG90", "20°"),
     "Horn flat on the left gear, 2 screws; then the servo's spline down into the horn hub", (-60, 55),
     ["gripper_frame", "wrist_horn", "finger_L", "finger_R", "axle_R"]),
    ("Wrist servo into the arm", ["wrist_servo"], FRONT, 45, [(2, SB)], ("MG90S wrist", "0°"),
     "Body through the arm's bracket from the front, 2 tab screws", (-140, 20), "COL"),
    ("Claw onto the wrist servo", ["gripper_frame", "wrist_horn", "finger_L", "finger_R", "axle_R", "gripper_horn", "gripper_servo_SG90"],
     FRONT, 30, [], ("MG90S wrist", "0°"), "Press the wrist horn (with the whole claw on it) onto the servo spline, plates level", (-140, 25), "COL"),
    ("Can bumper", ["can_bumper"], FRONT, 25, [], None,
     "Silicone or rubber, 9 × 13.5 mm, superglue to the frame", (-60, 35), "COL"),
    ("Bearing into the base", ["bearing_6807"], UP, 40, [], None,
     "Press on the outer ring only, evenly (flat block + vise)", (-60, 35), ["base"]),
    ("Turntable servo", ["turntable_servo_MG996R"], DOWN, 60, [(4, S8)], None,
     "From underneath; body points away from the arm side", (-120, -30), None),
    ("Weight + feet", ["base"], None, 0, [], None,
     "~100 g in the 2 back pockets (washers, pennies, rocks, a bag of sand): GLUE or TAPE it in. 4 feet or hot-glue dots",
     (-120, -40), None),
    ("Column onto the turntable servo", list(COLUMN), UP, 60, [], ("MG996R", "135°"),
     "Servo at 135° first. Hub into the bearing, horn onto the spline, rod side toward the START can", (-60, 30), None),
    ("Electronics on the tray", ["arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF"], UP, 40, [], None,
     "Pegs + a dab of hot glue; breadboard is self-adhesive. Buck already set to 5.8 V", (-70, 50), ["electronics_tray"]),
    ("Panel: button, LED, power", ["start_button", "status_led", "dc_jack"], BACK, 30, [], None,
     "Through the panel holes from the front, nuts inside. Power: DC jack, or the LIZVOR terminal-block tip", (-110, 30),
     ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF"]),
    ("Tray onto the base", ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF", "start_button", "status_led", "dc_jack"],
     BACK, 45, [(2, S6)], None, "Tabs slide under the base wall, screws from below", (-120, 35), None),
]
# LM6UU come from below (L1/R1, lower pockets) and above (L2/R2): handled per part
PER_PART_DIR = {"LM6UU_L1": DOWN, "LM6UU_R1": DOWN, "LM6UU_L2": UP, "LM6UU_R2": UP,
                "turntable_horn": DOWN, "wrist_horn": BACK}   # horn up into the plate's hub / horn onto the frame's flange

ALLOWED = {frozenset(p) for p in [
    ("bearing_6807", "base"), ("bearing_6807", "turret_plate"), ("turntable_servo_MG996R", "turntable_horn"),
    ("lift_crank", "lift_servo_MG90S"), ("lift_crank", "lift_link"), ("wrist_servo", "wrist_horn"),
    ("wrist_servo", "gripper_frame"), ("gripper_servo_SG90", "finger_L"), ("gripper_servo_SG90", "gripper_horn"), ("gripper_horn", "finger_L"), ("axle_R", "finger_R"),
    ("axle_R", "gripper_frame"), ("rod_L", "turret_plate"), ("rod_R", "turret_plate"), ("rod_L", "top_cap"),
    ("rod_R", "top_cap"), ("lift_link", "carriage_arm")]}
for n in ("LM6UU_L1", "LM6UU_L2", "LM6UU_R1", "LM6UU_R2"):
    ALLOWED.add(frozenset((n, "carriage_arm")))
VOL_TOL = 1.0


def main():
    parts = {p["name"]: p for p in M.build_parts() if p["group"] not in ("coupon",)}
    shp = {n: p["shape"].val() for n, p in parts.items()}
    bb = {n: s.BoundingBox() for n, s in shp.items()}
    installed, column, out, rep, ok = ["base"], [], [], ["ASSEMBLY CHECK: every part slides to its place along its arrow (backend/tools/make_manual.py)",
                                       f"solid booleans every 3 mm of travel; overlap > {VOL_TOL} mm³ with an assembled part = blocked", ""], True
    for i, (title, new, dirn, dist, hw, badge, note, (az, el), only) in enumerate(STEPS, 1):
        table = list(column) if only == "COL" else (list(only) if only is not None else None)
        moving = list(new)                                           # a sub-assembly moves as one
        blocked = []
        for n in moving:
            d = dirn if dirn is not None else PER_PART_DIR.get(n)
            if d is None:
                continue
            others = [o for o in (table if table is not None else installed) if o not in new]
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
        if table is not None:                                        # built on the table
            for n in table + new:                                    # the claw joins the column only when it goes on it
                if n in COLUMN and n not in column and (only == "COL" or n not in CLAW):
                    column.append(n)
            show = (table + [n for n in new if n not in table])
        else:
            for n in new:
                if n not in installed:
                    installed.append(n)
            show = list(installed)
        out.append(dict(n=i, title=title, new=new, dir=dirn, per_part_dir={n: PER_PART_DIR[n] for n in new if n in PER_PART_DIR and dirn is None},
                        dist=dist, hw=hw, badge=badge, note=note, az=az, el=el, show=show, ok=not blocked))
        print(rep[-1], flush=True)
    rep += ["", "RESULT: " + ("every step can be assembled in this order" if ok else "BLOCKED steps above")]
    open(os.path.join(ROOT, "cad", "check", "assembly_check.txt"), "w").write("\n".join(rep) + "\n")
    json.dump(dict(steps=out), open(os.path.join(ROOT, "backend", "cad", "build", "manual_steps.json"), "w"), indent=1)
    print(rep[-1])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
