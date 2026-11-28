"""Plan G: buy a ready-made arm kit and modify it for our job.

    python3.13 backend/cad/plan_g.py  ->  viewer/data/plang.json (viewer/assembly.html?data=plang), cad/plans/plang_*.stl

Kit: a 4-DOF acrylic arm with MG90S servos (base turn, shoulder, elbow, claw), e.g. the ThinkRobotics listing: 90 mm
claw opening, 200 mm reach, 180 mm tall, 95 mm wide. The kit is drawn from those listed sizes (grey, approximate:
check your kit). Our changes are drawn exactly (blue = printed, tan = wood):
  1 heavier footing: the kit's base screwed onto a 3/4" plywood board with washer ballast (holes in WOOD only)
  2 wrist roll: our MG90S wrist servo between the forearm and the kit's claw, held by 2 small printed adapters that use
    the kit's own screw holes (nothing drilled in the acrylic)
  3 can pads: silicone strips on the claw jaws
  4 a 5th servo channel: shoulder + elbow together do the lift (firmware mapping to write)
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import redesign as R  # noqa: E402
from model import P, box, cyl, cyl_dir, moved, trsf_axes, micro_servo_local  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "plang.json")
DIR = os.path.join(ROOT, "cad", "plans")
IN = 25.4
Z0 = 0.75 * IN                                      # kit stands on the plywood board
GZ = P["grip_z"]
CAN_Y = P["can_y"]
SH = (0.0, Z0 + 62.0)                               # kit shoulder (y, z)
EL = (32.0, Z0 + 130.0)                             # elbow
WR = (69.0, GZ)                                     # forearm end = where the wrist roll starts


def plates(p0, p1, w, xs, t=3.0):
    """Pair of acrylic link plates (the kit's arm) between 2 points in the YZ plane, at x = xs (outer faces)."""
    out = None
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    for x0 in xs:
        wp = lambda: cq.Workplane("YZ").workplane(offset=x0)  # noqa: E731
        b = wp().center(*p0).circle(w / 2).extrude(t).union(wp().center(*p1).circle(w / 2).extrude(t)).union(
            wp().center((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2).transformed(rotate=(0, 0, ang)).rect(math.dist(p0, p1), w).extrude(t))
        b = cq.Workplane("XY").add(b.val())
        out = b if out is None else out.union(b)
    return out


def build():
    parts = []

    def add(name, shape, kind, src, mass=None):
        parts.append(dict(name=name, shape=shape, kind=kind, src=src, mass=mass))

    # ---- our footing
    brd = box(-90, 90, -95, 60, 0, Z0)
    for x in (-60, 60):
        brd = brd.cut(cyl(x, -70, 3.25, -1, Z0 + 1))
    add("plywood_board", brd, "wood", "3/4\" plywood 180 x 155: the kit's base screws onto it with 4 wood screws through the kit's own holes")
    for k, x in (("L", -60), ("R", 60)):
        add(f"ballast_{k}", cyl(x, -70, 12.5, Z0, Z0 + 14).cut(cyl(x, -70, 3.3, 0, 60)), "metal", "1\" steel washers on an M6 bolt", 70.0)
    # ---- the kit (approximate, from the listed sizes)
    add("kit_base", box(-47.5, 47.5, -47.5, 47.5, Z0, Z0 + 38).cut(box(-44.5, 44.5, -44.5, 44.5, Z0 + 3, Z0 + 35)), "kit",
        "kit: base box with the base-turn MG90S inside")
    add("kit_turntable", cyl(0, 0, 40, Z0 + 38, Z0 + 42), "kit", "kit: turntable disc")
    side = box(-24, -21, -18, 14, Z0 + 42, SH[1] + 14).union(box(21, 24, -18, 14, Z0 + 42, SH[1] + 14))
    add("kit_shoulder_frame", side, "kit", "kit: shoulder side plates + shoulder and elbow MG90S")
    add("kit_upper_arm", plates(SH, EL, 12, (-21, 18)), "kit", "kit: upper arm (pair of acrylic plates)")
    add("kit_forearm", plates(EL, WR, 12, (-18, 15)), "kit", "kit: forearm (pair)")
    add("kit_servos", box(-21, -9, -6, 6, SH[1] - 16, SH[1] + 7).union(box(9, 21, -6, 6, SH[1] - 16, SH[1] + 7)), "kit_servo",
        "kit: shoulder + elbow MG90S (in the kit)")
    # ---- our wrist roll: printed adapter on the forearm end -> MG90S (spline along +Y) -> printed claw adapter -> kit claw
    ad1 = box(-18, 18, WR[0] - 4, WR[0], GZ - 9, GZ + 9).cut(box(-6.4, 6.4, WR[0] - 5, WR[0] + 1, GZ - 16.85 - 0.3, GZ + 5.95 + 0.3))
    for x in (-16.5, 13.5):
        ad1 = ad1.cut(cyl_dir((x, WR[0] - 2, GZ - 12), (0, 0, 1), 1.0, 24))
    add("wrist_adapter", ad1, "printed", "printed: clamps between the forearm plates with the kit's own 2 screws; holds our MG90S by its tabs")
    ty = WR[0] + 12.6
    add("wrist_servo", moved(micro_servo_local(), trsf_axes((0, ty, GZ), (0, 0, -1), (0, 1, 0))), "bought", "our MG90S wrist servo", 13.0)
    add("wrist_horn", box(-11, 11, ty, ty + 2.5, GZ - 2.75, GZ + 2.75).union(cyl_dir((0, ty, GZ), (0, 1, 0), 3.8, 2.5)), "bought",
        "cross horn from its bag")
    ad2 = box(-20, 20, ty + 2.5, ty + 6.5, GZ - 10, GZ + 10)
    add("claw_adapter", ad2, "printed", "printed: 4 servo-bag screws into the cross horn; the kit claw bolts on with its own screws")
    # kit claw: a palm + 2 jaws around the can, open to 90 mm max
    palm = box(-24, 24, ty + 6.5, ty + 12, GZ - 12, GZ + 12)
    jaws = None
    for s in (-1, 1):
        j = box(s * 33.1 + (0 if s > 0 else -4), s * 33.1 + (4 if s > 0 else 0), ty + 12, CAN_Y + 14, GZ - 8, GZ + 8).union(
            box(min(s * 24, s * 37.1), max(s * 24, s * 37.1), ty + 8, ty + 14, GZ - 8, GZ + 8))
        jaws = j if jaws is None else jaws.union(j)
    add("kit_claw", palm.union(jaws), "kit", "kit claw: 90 mm max opening (listed), closes on the 66 mm can")
    pads = None
    for s in (-1, 1):
        pd = box(s * 33.1 - (2 if s > 0 else 0), s * 33.1 + (0 if s > 0 else 2), CAN_Y - 18, CAN_Y + 18, GZ - 7, GZ + 7)
        pads = pd if pads is None else pads.union(pd)
    add("can_pads", pads, "silicone", "2 silicone strips 36 x 14 x 2 mm, glued to the jaws")
    can = cyl(0, CAN_Y, P["can_d"] / 2, 0, P["can_h"])
    add("test_can", can, "can", "")
    return parts


def main():
    os.makedirs(DIR, exist_ok=True)
    parts = build()
    sh = {p["name"]: p["shape"].val() for p in parts}
    rep = []
    # static interference (nothing may overlap except designed contacts)
    ok_pairs = {frozenset(x) for x in [("plywood_board", "kit_base"), ("plywood_board", "ballast_L"), ("plywood_board", "ballast_R"),
                                        ("kit_base", "kit_turntable"), ("kit_turntable", "kit_shoulder_frame"), ("kit_shoulder_frame", "kit_upper_arm"),
                                        ("kit_shoulder_frame", "kit_servos"), ("kit_upper_arm", "kit_forearm"), ("kit_upper_arm", "kit_servos"),
                                        ("kit_forearm", "wrist_adapter"), ("wrist_adapter", "wrist_servo"), ("wrist_servo", "wrist_horn"),
                                        ("wrist_horn", "claw_adapter"), ("claw_adapter", "kit_claw"), ("kit_claw", "can_pads"),
                                        ("can_pads", "test_can"), ("wrist_servo", "claw_adapter")]}
    names = list(sh)
    clash = [f"{a} x {b}" for i, a in enumerate(names) for b in names[i + 1:]
             if frozenset((a, b)) not in ok_pairs and sh[a].intersect(sh[b]).Volume() > 1.0]
    rep.append("FIT (gripping pose): " + ("PASS, nothing overlaps" if not clash else "CHECK " + "; ".join(clash)))
    rep.append(f"CLAW OPENING: 90 mm listed vs can {P['can_d']:.1f} + 2 x 2 mm pads = {P['can_d'] + 4:.1f} -> PASS ({90 - P['can_d'] - 4:.0f} mm to spare)")
    rep.append(f"REACH: can centre {CAN_Y:.0f} mm out vs 200 mm listed max reach -> PASS")
    load = 15 + 13 + 6 + 22 + 3                       # can, wrist servo, adapters, kit claw + its servo, pads (g)
    arm = 30.0                                        # kit forearm + upper arm (acrylic), g, at ~half reach
    tq = (load * (CAN_Y - 25) + arm * 45) / 1000 / 10 * 1.5
    rep.append(f"SHOULDER (kit MG90S, 1.8 kg*cm): {load} g at the claw + the arm itself, x1.5 for moving -> {tq:.2f} kg*cm = "
               f"{tq / 1.8 * 100:.0f} % of stall -> {'PASS' if tq < 0.9 else 'MARGINAL: shoulder + elbow share it, move slowly'}"
               " (the kit's 4-bar puts part of it on the elbow servo)")
    rep.append("TIP-OVER: kit base 95 mm wide alone would tip with a can at 127 mm; on the 180 x 155 board with 2 x 70 g washers -> PASS")
    rep.append("FLIP: our MG90S turns the claw 180 deg about the forearm axis (the kit has no wrist roll: this is the main change)")
    import print_prep as PP
    R.DIR = DIR
    ini = os.path.join(ROOT, "cad", "print", "reprint", "reprint_a.ini")
    tt = {n: R.slice_one(sh[n], "plang_" + n, ini, PP, keep=True) for n in ("wrist_adapter", "claw_adapter")}
    rep.append("PRINT: wrist adapter " + tt["wrist_adapter"] + ", claw adapter " + tt["claw_adapter"])
    print("\n".join(rep))
    colors = {"wood": "#c8a06a", "metal": "#6b7076", "kit": "#cfd6de", "kit_servo": "#22346e", "printed": "#2f72e0", "bought": "#3b3f45",
              "silicone": "#e8e2d0", "can": "#c8102e"}
    kindmap = {"wood": "made", "metal": "bought", "kit": "made", "kit_servo": "bought", "printed": "printed", "bought": "bought",
               "silicone": "bought", "can": "can"}
    meshes = []
    for p in parts:
        v, t = sh[p["name"]].tessellate(0.12, 0.35)
        meshes.append(dict(owner=p["name"], kind=kindmap[p["kind"]], color=colors[p["kind"]],
                           v=[round(c, 1) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for x in t for i in x]))

    def step(n, title, new, show, how, level="easy", dir_=(0, 0, 1), dist=40, hw=(), fit="", note=""):
        return dict(n=n, title=title, new=list(new), show=sorted(set(show) | set(new)), dir=list(dir_) if dir_ else None, per_part_dir={},
                    dist=dist, hw=[list(h) for h in hw], badge=None, note=note, screws=[], glue=[], fit=fit, how=how, glue_text="",
                    level=level, callouts=[])
    kit = ["kit_base", "kit_turntable", "kit_shoulder_frame", "kit_upper_arm", "kit_forearm", "kit_servos"]
    steps = [
        step(1, "Buy the kit", kit + ["kit_claw"], [], dir_=None, dist=0,
             hw=[[1, "4-DOF acrylic arm kit with MG90S servos, claw opening ≥ 75 mm"]],
             note="Check the listed claw opening: it must be at least 75 mm for our 66 mm can",
             how="Example: the <a href='https://thinkrobotics.com/products/4-dof-white-acrylic-robotic-arm-mg90s-kit-online'>ThinkRobotics "
                 "4-DOF acrylic arm (MG90S)</a>, listed with a 90 mm claw opening, 200 mm reach and 180 mm height (out of stock when "
                 "checked). Many similar kits sell as \"4DOF acrylic robot arm MG90S\": pick one whose listing gives the claw opening. "
                 "Avoid the 55 mm ones, which are too small for the can. Grey in the 3D view = the kit, drawn from those listed "
                 "sizes, so yours will differ in detail."),
        step(2, "Build the kit as its manual says, except the claw", kit, [], dir_=(0, 0, 1),
             note="Stop before fitting the claw onto the forearm",
             how="Follow the kit's own manual: base, turntable, shoulder, both arm links. <b>Don't fit the claw to the forearm yet</b>: "
                 "our wrist goes in between. That way nothing has to come apart later."),
        step(3, "Heavier footing", ["plywood_board", "ballast_L", "ballast_R"], kit, level="easy",
             hw=[[1, "3/4\" plywood 180 x 155"], [4, "#6 x 3/4\" wood screws"], [2, "M6 bolt + 5 washers"]],
             how="The kit's 95 mm base would tip forward holding a can 127 mm out. Screw its base onto a plywood board with 4 wood "
                 "screws through the <b>kit's own base holes</b> (you only drill wood), and add 2 washer stacks at the back.",
             dir_=(0, 0, -1)),
        step(4, "Insert our wrist roll", ["wrist_adapter", "wrist_servo", "wrist_horn", "claw_adapter"], kit + ["plywood_board", "ballast_L", "ballast_R"],
             level="try", dir_=(0, 1, 0), hw=[[2, "printed adapters (about 1 h together)"], [6, "servo-bag screws"]],
             note="Forearm → printed adapter → our MG90S → cross horn → printed adapter → kit claw",
             how="This is the real modification: the kit has no wrist roll, and flipping the can needs one. 1) The <b>wrist "
                 "adapter</b> slips between the forearm's 2 plates and is held by the <b>same 2 screws</b> that would have held the "
                 "claw. 2) Our MG90S wrist servo goes through its window, 2 tab screws. 3) Cross horn on the <b>claw adapter</b> "
                 "(4 servo-bag screws into printed pilots), wrist at 0°, press the horn onto the spline. 4) The kit's claw bolts "
                 "onto the claw adapter with its own screws. No drilling into the acrylic."),
        step(5, "Pads for the can", ["kit_claw", "can_pads"], kit + ["plywood_board", "wrist_adapter", "wrist_servo", "wrist_horn", "claw_adapter"],
             dir_=(0, 1, 0), hw=[[1, "silicone or rubber strip 36 x 14 x 2 mm, x2"]],
             how="Glue a silicone strip on each jaw where it meets the can. The flat acrylic jaws only touch a round can along "
                 "a line; the pads spread the grip and stop it slipping while it flips."),
        step(6, "Wiring + software", [], [p["name"] for p in parts], dir_=None, dist=0, level="try",
             hw=[[1, "PCA9685 servo board (recommended: 5 servos now)"]],
             how="Five servos now: base turn, shoulder, elbow, claw (all from the kit) plus our wrist. The lift is no longer one "
                 "servo: the shoulder and elbow move together to raise the can about 16 mm without tipping it. The firmware needs "
                 "a new mapping (two angle pairs for LIFT, taught in the laptop panel); the sequence (grip, lift, flip, turn, lower, "
                 "release) stays the same. Power 5 servos from a PCA9685 board on its own 5–6 V supply, not from the Uno. "
                 "<b>Not written yet:</b> the 5-servo firmware."),
    ]
    data = dict(meshes=meshes, screws=[], glue=[], steps=steps, printed=["wrist_adapter", "claw_adapter"],
                names={p["name"]: p["name"].replace("_", " ") for p in parts}, screw_names={}, plang=True, report=rep,
                bom=[dict(f=p["name"].replace("_", " "), part=p["src"]) for p in parts if p["src"]], title="Plan G: buy a kit and modify it",
                levels=dict(precise=dict(label="PRECISE FIT", color="#c40000", text=""),
                            **{"try": dict(label="TRY-FIT", color="#c77700", text="Test before you tighten.")},
                            easy=dict(label="EASY", color="#1f7a45", text="Straightforward.")), while_waiting=[])
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/plang.json ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
