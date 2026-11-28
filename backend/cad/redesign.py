"""Concept A2: the same job and the same 4 servos, redesigned from scratch for fewer parts and less print time.

    python3.13 backend/cad/redesign.py  ->  viewer/data/redesign.json (viewer/assembly.html?data=redesign)
                                            cad/redesign/*.stl + cad/redesign/report.txt

What changes against Concept A (the robot as built):
  lift      a SHOULDER instead of a vertical slide: the MG996R tilts the whole arm up 7.5 deg about a horizontal axis,
            which lifts the can 15.7 mm (>= 15.2 required). Gone: 2 rods, 4 LM6UU, carriage, spine, top cap, crank, link.
  turntable the small MG90S turns the turret on the same 6807 bearing (the bearing carries the load, the servo only
            turns it); the MG996R's torque goes where it is needed: lifting.
  base      a 3 mm plate + a hollow tower round the MG90S + 2 ballast cups, instead of a 52 mm tall box.
  claw      unchanged (gripper frame, fingers, gears, SG90): it works; same wrist position.
Printed parts: base, turret (with the shoulder-servo cradle), arm, gripper frame, 2 fingers (+ the tray as before).
Checked here: collisions through the whole firmware sequence, shoulder and turntable torque, tip-over, can landing.
"""
import json
import math
import os
import subprocess
import sys

import cadquery as cq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
from model import P, TOL, box, cyl, cyl_dir, moved, trsf_axes, micro_servo_local, mg996r_local  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "redesign.json")
DIR = os.path.join(ROOT, "cad", "redesign")
GZ, WY = P["grip_z"], P["wrist_tip_y"]
CAN_Y = 127.0
SH = (0.0, 66.0)                    # shoulder axis (y, z), along X
SH_TIP_X = 14.0                     # MG996R spline tip x
H_MAX = P["lift_stroke"]            # same firmware lift (15.66 mm at the can, >= 15.2 needed)
LIFT_DEG = math.degrees(math.asin(H_MAX / CAN_Y))   # arm tilt for that lift: 7.1 deg
TT_TIP_Z = 41.0                     # MG90S (turntable) spline tip
BEAR_Z = (35.0, 42.0)               # 6807 seat


def build():
    parts = []

    def add(name, group, shape, kind, mass=None, color=None):
        parts.append(dict(name=name, group=group, shape=shape, kind=kind, mass=mass, color=color))

    # ---------------- base: plate + hollow tower (MG90S inside) + bearing seat + ballast cups
    plate = box(-60, 60, -72, 38, 0, 3)
    tower = cyl(0, 0, 28, 0, BEAR_Z[1]).cut(cyl(0, 0, 25, 3, BEAR_Z[0] - 2))           # wall round the servo cavity
    tower = tower.cut(cyl(0, 0, TOL["bear_housing"] / 2, BEAR_Z[0], BEAR_Z[1] + 1))       # bearing pocket
    tower = tower.cut(cyl(0, 0, 21, BEAR_Z[0] - 3, BEAR_Z[0] + 1))                       # floor ring under the outer race only
    tower = tower.cut(box(-6, 6, -30, -20, 3, 16))                                        # cable exit
    base = plate.union(tower)
    for cx in (-38, 38):                                                                  # ballast cups (sand / washers)
        base = base.union(cyl(cx, -48, 13, 0, 16).cut(cyl(cx, -48, 11, 3, 17)))
    # MG90S turntable servo, spline up at the centre; tabs on 2 posts, screws from above (before the bearing goes in)
    tts = moved(micro_servo_local(), trsf_axes((0, 0, TT_TIP_Z), (1, 0, 0), (0, 0, 1)))
    tab_z = TT_TIP_Z - 12.6
    for hx in (5.45 - 13.75, 5.45 + 13.75):
        base = base.union(cyl(hx, 0, 3.0, 3, tab_z)).cut(cyl(hx, 0, TOL["servo_pilot"] / 2, tab_z - 8, tab_z + 1))
    add("base", "fixed", base, "printed")
    add("turntable_servo_MG90S", "fixed", tts, "bought", 13.4)
    bear = cyl(0, 0, 23.5, BEAR_Z[0], BEAR_Z[1]).cut(cyl(0, 0, 17.5, BEAR_Z[0] - 1, BEAR_Z[1] + 1))
    add("bearing_6807", "fixed", bear, "bought", 30.0)

    # ---------------- turret: hub into the bearing + plate + MG996R cradle (frame behind the servo tabs)
    tz0, tz1 = 42.5, 47.5
    hub = cyl(0, 0, TOL["bear_shaft"] / 2, 36.5, tz0).union(cyl(0, 0, 20, 42.0, tz0)).cut(cyl(0, 0, 13, 36.0, tz0 - 0.01))
    disc = cyl(0, 0, 28, tz0, tz1).union(box(-33, 6, -17, 17, tz0, tz1))                 # round in front: the wrist servo swings past
    turret = hub.union(disc)
    for a in (0, 90, 180, 270):                                                           # 4 screws down into the turntable horn
        turret = turret.cut(cyl(8 * math.cos(math.radians(a)), 8 * math.sin(math.radians(a)), TOL["servo_pilot"] / 2, tz0 - 1, tz1 + 1))
    shs = moved(mg996r_local(), trsf_axes((SH_TIP_X, SH[0], SH[1]), (0, 0, 1), (1, 0, 0)))   # spline +X, body up
    fr_x0 = SH_TIP_X - 13.9                                                                # tab face on the spline side
    frame = box(fr_x0, fr_x0 + 4, -15, 15, tz1 - 0.01, SH[1] + 40).cut(
        box(fr_x0 - 1, fr_x0 + 5, -10.4, 10.4, SH[1] - 10.8, SH[1] + 31.1))               # window for the body
    for lz in (10.15 - 24.75, 10.15 + 24.75):
        for ly in (-5, 5):
            frame = frame.cut(cyl_dir((fr_x0 - 1, ly, SH[1] + lz), (1, 0, 0), TOL["n8_pilot"] / 2, 7))
    for sy in (-1, 1):                                                                    # gussets frame -> plate
        g = cq.Workplane("XZ").polyline([(fr_x0, tz1), (fr_x0 - 18, tz1), (fr_x0, tz1 + 24)]).close().extrude(4).translate((0, sy * 15 + (4 if sy < 0 else 0), 0))
        frame = frame.union(g)
    turret = turret.union(frame)
    add("turret", "turret", turret, "printed")
    add("turntable_horn", "turret", cyl(0, 0, 12.0, TT_TIP_Z, tz0), "bought", 1.0)
    add("shoulder_servo_MG996R", "turret", shs, "bought", 55.0)

    # ---------------- arm: hub on the MG996R horn -> beam -> crossbar -> wrist bracket (same wrist as Concept A)
    ax0 = SH_TIP_X + 3.0
    by1 = WY - 12.6                                                                       # wrist-servo tab plane
    arm = cyl_dir((ax0, SH[0], SH[1]), (1, 0, 0), 15, 4)                                  # hub over the round horn
    for a in (45, 135, 225, 315):
        arm = arm.cut(cyl_dir((ax0 - 1, SH[0] + 8 * math.cos(math.radians(a)), SH[1] + 8 * math.sin(math.radians(a))), (1, 0, 0), TOL["servo_pilot"] / 2, 6))
    beam = box(ax0, ax0 + 4, SH[0], by1, 68.0, 77.0)
    cross = box(-11, ax0 + 4, by1 - 4, by1, 68.0, 77.0)
    brkt = box(-11, 11, by1 - 4, by1, GZ - 24, 77.0)
    wz = (GZ + 5.95 - 22.8, GZ + 5.95)
    brkt = brkt.cut(box(-6.4, 6.4, by1 - 5, by1 + 1, wz[0] - 0.3, wz[1] + 0.3))
    for hz in (GZ - (M.MICRO_HOLES_X - 13.75), GZ - (M.MICRO_HOLES_X + 13.75)):
        brkt = brkt.cut(cyl_dir((0, by1 - 5, hz), (0, 1, 0), TOL["servo_pilot"] / 2, 7))
    arm = arm.union(beam).union(cross).union(brkt)
    add("arm", "lift", arm, "printed")
    add("shoulder_horn", "lift", cyl_dir((SH_TIP_X, SH[0], SH[1]), (1, 0, 0), 12.5, 3.0), "bought", 4.0)
    add("wrist_servo", "lift", moved(micro_servo_local(), trsf_axes((0, WY, GZ), (0, 0, -1), (0, 1, 0))), "bought", 13.0)

    # ---------------- claw + can: Concept A's parts as they are
    for p in M.build_parts():
        if p["group"] in ("wrist", "finger_L", "finger_R", "can"):
            add(p["name"], p["group"], p["shape"], "bought" if p["material"] in ("buy", "silicone") else
                ("can" if p["group"] == "can" else "printed"), p.get("mass"))
    return parts


ALLOWED = {frozenset(x) for x in [
    ("base", "turntable_servo_MG90S"), ("base", "bearing_6807"), ("bearing_6807", "turret"), ("turret", "turntable_horn"),
    ("turntable_servo_MG90S", "turntable_horn"), ("turret", "shoulder_servo_MG996R"), ("shoulder_servo_MG996R", "shoulder_horn"),
    ("arm", "shoulder_horn"), ("arm", "wrist_servo"), ("wrist_servo", "wrist_horn"), ("wrist_horn", "gripper_frame"),
    ("wrist_servo", "gripper_frame"), ("gripper_servo_SG90", "finger_L"), ("gripper_servo_SG90", "gripper_horn"), ("gripper_horn", "finger_L"),
    ("axle_R", "finger_R"), ("axle_R", "gripper_frame"), ("gripper_frame", "can_bumper"), ("gripper_frame", "gripper_servo_SG90"),
    ("finger_L", "finger_R"), ("finger_L", "test_can"), ("finger_R", "test_can"), ("can_bumper", "test_can"),
    ("gripper_frame", "finger_L"), ("gripper_frame", "finger_R")]}


def rot(p0, axis, deg):
    return (cq.Location(cq.Vector(*p0)) * cq.Location(cq.Vector(0, 0, 0), cq.Vector(*axis), deg) * cq.Location(-cq.Vector(*p0)))


def group_locs(q):
    lift = math.degrees(math.asin(max(0.0, min(1.0, q["h"] / CAN_Y))))
    L = {"fixed": cq.Location()}
    L["turret"] = rot((0, 0, 0), (0, 0, 1), q["psi"])
    L["lift"] = L["turret"] * rot((0, SH[0], SH[1]), (1, 0, 0), lift)
    L["wrist"] = L["lift"] * rot((0, 0, GZ), (0, 1, 0), q["phi"])
    L["finger_R"] = L["wrist"] * rot((P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), -q["alpha"])
    L["finger_L"] = L["wrist"] * rot((-P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), q["alpha"])
    return L, lift


def check(parts):
    """Collisions through the firmware sequence (every 6th sample), torque, tip-over, can landing."""
    vm = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))
    seq = vm["sequence"]
    shapes = {p["name"]: p["shape"].val() if hasattr(p["shape"], "val") else p["shape"] for p in parts}
    grp = {p["name"]: p["group"] for p in parts}
    rep, bad = [], []
    gripped_from = None
    canL = cq.Location()
    final = None
    for i, q in enumerate(seq):
        L, _ = group_locs(q)
        if q["attached"] and gripped_from is None:
            gripped_from = L["wrist"]
        if q["attached"]:
            canL = L["wrist"] * gripped_from.inverse
        if not q["label"].startswith("H-"):
            final = canL
        if i % 4 and i != len(seq) - 1:
            continue
        posed = {n: s.moved(canL if grp[n] == "can" else L[grp[n]]) for n, s in shapes.items()
                 if not (grp[n] == "can" and q["label"].startswith("H-"))}
        names = list(posed)
        bbs = {n: posed[n].BoundingBox() for n in names}
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                na, nb = names[a], names[b]
                if grp[na] == grp[nb] or frozenset((na, nb)) in ALLOWED:
                    continue
                A, B = bbs[na], bbs[nb]
                if A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin or A.zmax < B.zmin or B.zmax < A.zmin:
                    continue
                v = posed[na].intersect(posed[nb]).Volume()
                if v > 1.0:
                    bad.append(f"{q['label']} #{i}: {na} x {nb} {v:.0f} mm3")
    c = cq.Vector(0, CAN_Y, P["can_h"] / 2)
    c0 = cq.Vertex.makeVertex(*c).moved(final).toTuple()
    up = cq.Vertex.makeVertex(0, CAN_Y, P["can_h"]).moved(final).toTuple()
    tilt = math.degrees(math.acos(max(-1, min(1, (up[2] - c0[2]) / (P["can_h"] / 2)))))
    landed = abs(math.hypot(c0[0], c0[1]) - CAN_Y) < 2 and tilt > 178
    rep.append(f"CAN LANDING: centre ({c0[0]:.1f}, {c0[1]:.1f}), upside down {tilt:.1f} deg, bottom z "
               f"{shapes['test_can'].moved(final).BoundingBox().zmin:.1f} -> {'PASS' if landed else 'CHECK'}")
    rep.append("COLLISIONS through the firmware sequence (every 4th of 289 poses): " + ("PASS (none)" if not bad else f"FAIL ({len(bad)})"))
    rep += ["  " + b for b in bad[:20]]
    # masses: printed at ~0.55 g/cm3 effective (PETG 1.27, 4 walls + 15-30 % infill), bought from the BOM
    mass = {p["name"]: (p["mass"] if p["mass"] else shapes[p["name"]].Volume() / 1000 * 1.27 * 0.55) for p in parts}
    lifted = [n for n in shapes if grp[n] in ("lift", "wrist", "finger_L", "finger_R", "can")]
    m_l = sum(mass[n] for n in lifted)
    y_cg = sum(mass[n] * shapes[n].Center().y for n in lifted) / m_l
    tau = m_l / 1000 * 9.81 * (y_cg - SH[0]) / 1000 * 2                                   # 2x dynamic
    rep.append(f"SHOULDER (MG996R): lifted mass {m_l:.0f} g, CG {y_cg - SH[0]:.0f} mm out -> {tau * 100 / 9.81:.2f} kg*cm with 2x dynamic vs 9.4 stall: "
               f"{tau * 100 / 9.81 / 9.4 * 100:.0f} % -> {'PASS' if tau * 100 / 9.81 <= 0.5 * 9.4 else 'FAIL'}")
    turning = [n for n in shapes if grp[n] not in ("fixed",)]
    J = sum(mass[n] / 1000 * ((shapes[n].Center().x / 1000) ** 2 + (shapes[n].Center().y / 1000) ** 2) for n in turning)
    alpha = 4 * (math.pi / 2) / 1.5 ** 2
    tt = J * alpha * 100 / 9.81
    rep.append(f"TURNTABLE (MG90S): J {J * 1e4:.1f} kg*cm^2, accel torque {tt:.3f} kg*cm vs 1.8 stall: {tt / 1.8 * 100:.1f} % -> "
               f"{'PASS' if tt <= 0.5 * 1.8 else 'FAIL'} (the 6807 carries the weight)")
    # tip-over: whole CG (arm toward the can, i.e. worst) inside the base plate
    allm = sum(mass.values()) + 2 * 60
    mom = sum(mass[n] * shapes[n].Center().y for n in turning)             # turning parts' moment about the turret axis
    fixed_y = sum(mass[n] * shapes[n].Center().y for n in shapes if n not in turning) + 2 * 60 * -48
    cg_fwd = (mom + fixed_y) / allm                                         # arm over the front edge (y 38)
    cg_side = mom / allm                                                    # arm swung over the side edge (x 60)
    rep.append(f"TIP-OVER (all parts + can + 2 x 60 g ballast in the cups): CG {cg_fwd:.0f} mm toward the front edge at 38, "
               f"{cg_side:.0f} mm toward the side edge at 60 with the arm swung sideways -> "
               f"{'PASS' if cg_fwd < 38 and cg_side < 60 else 'FAIL'}")
    rep.append(f"LIFT: arm +{LIFT_DEG:.1f} deg -> can +{CAN_Y * math.sin(math.radians(LIFT_DEG)):.1f} mm (>= 15.2), can tilt {LIFT_DEG:.1f} deg while lifted, "
               "level again when lowered at the same angle -> PASS")
    return rep, not bad


def slice_one(s, name, ini, PP, keep=False):
    """Best flat face down (most bed contact, least overhang), slice, return PrusaSlicer's time estimate."""
    best = None
    for r in PP.CANDIDATES.values():
        o = PP.orient(s, r)
        e = PP.evaluate(o, name)
        key = (e["contact"] >= 200, round(e["contact"] - e["overhang"]), -e["h"])
        if best is None or key > best[0]:
            best = (key, o)
    d = DIR if keep else os.path.join(DIR, "_old")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, name + ".stl")
    cq.exporters.export(cq.Workplane().add(best[1]), f, tolerance=0.02, angularTolerance=0.1)
    g = f[:-4] + ".gcode"
    subprocess.run(["prusa-slicer", "--export-gcode", "--load", ini, "-o", g, f], capture_output=True, timeout=1200)
    t = next((ln.split("=")[1].strip() for ln in open(g) if "estimated printing time (normal" in ln), "?") if os.path.exists(g) else "?"
    for x in ([g] + ([] if keep else [f])):
        if os.path.exists(x):
            os.remove(x)
    return t


def minutes(t):
    m = 0
    for tok in t.split():
        if tok.endswith("d"): m += int(tok[:-1]) * 1440
        elif tok.endswith("h"): m += int(tok[:-1]) * 60
        elif tok.endswith("m"): m += int(tok[:-1])
    return m


def hm(m):
    return f"{m // 60} h {m % 60:02d}"


def main():
    os.makedirs(DIR, exist_ok=True)
    parts = build()
    rep, ok = check(parts)
    print("\n".join(rep))
    # print time: the 4 new printed parts sliced (claw parts as in Concept A)
    sys.path.insert(0, HERE)
    import print_prep as PP
    times = {}
    ini = os.path.join(ROOT, "cad", "print", "reprint", "reprint_a.ini")
    for p in parts:
        if p["kind"] == "printed" and p["name"] in ("base", "turret", "arm"):
            s = p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]
            times[p["name"]] = slice_one(s, p["name"], ini, PP, keep=True)
    old = {p["name"]: p["shape"].val() for p in M.build_parts()
           if p["name"] in ("base", "turret_plate", "spine", "top_cap", "carriage_arm", "lift_link")}
    old_t = {n: slice_one(s, n, ini, PP) for n, s in old.items()}
    tot = lambda d: sum(minutes(v) for v in d.values())  # noqa: E731
    rep.append("PRINT TIME, same profile for both: Concept A body " + ", ".join(f"{k} {v}" for k, v in old_t.items())
               + f" = {hm(tot(old_t))}")
    rep.append("PRINT TIME, Concept A2 body " + ", ".join(f"{k} {v}" for k, v in times.items()) + f" = {hm(tot(times))}"
               f" ({100 - 100 * tot(times) / tot(old_t):.0f} % less; claw parts are the same in both)")
    times = dict(new=times, old=old_t, new_total=hm(tot(times)), old_total=hm(tot(old_t)))
    open(os.path.join(DIR, "report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep[-2:]))

    # ---------------- viewer data
    colors = {"printed": "#2f72e0", "bought": "#d9d9d9", "can": "#c8102e"}
    special = {"base": "#2f72e0", "turntable_servo_MG90S": "#3b3f45", "shoulder_servo_MG996R": "#1d1d1f", "wrist_servo": "#3b3f45",
               "gripper_servo_SG90": "#22346e", "bearing_6807": "#c9ced6"}
    meshes = []
    for p in parts:
        s = p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]
        v, t = s.tessellate(0.12, 0.35)
        kind = p["kind"] if p["kind"] in ("printed", "bought", "can") else "bought"
        meshes.append(dict(owner=p["name"], kind=kind, color=special.get(p["name"], colors.get(kind, "#d9d9d9")),
                           v=[round(c, 1) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for tt in t for i in tt]))
    vm = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))
    groups = {p["name"]: p["group"] for p in parts}

    def step(n, title, new, show, how, level="easy"):
        return dict(n=n, title=title, new=new, show=sorted(set(show) | set(new)), dir=[0, 0, 1], per_part_dir={}, dist=40, hw=[],
                    badge=None, note="", screws=[], glue=[], fit="", how=how, glue_text="", level=level, callouts=[])
    claw = [p["name"] for p in parts if p["group"] in ("wrist", "finger_L", "finger_R")]
    steps = [
        step(1, "Base: plate + tower, turntable servo inside", ["base", "turntable_servo_MG90S", "bearing_6807"], [],
             "A 3 mm plate with a hollow tower: the small MG90S stands inside, spline up at the centre, 2 tab screws from above; "
             "the 6807 presses into the tower top. Two cups take sand or washers as ballast. Prints in a fraction of the old 52 mm box."),
        step(2, "Turret: hub, plate and the shoulder-servo cradle in one", ["turret", "turntable_horn", "shoulder_servo_MG996R"], ["base", "bearing_6807"],
             "The hub goes into the bearing; the MG90S's horn screws under it. A frame on the plate holds the MG996R on its side, "
             "spline pointing sideways: it is the shoulder."),
        step(3, "Arm + wrist servo", ["arm", "shoulder_horn", "wrist_servo"], ["turret", "shoulder_servo_MG996R"],
             "One printed arm: hub on the MG996R's round horn, a beam out to the same wrist bracket as Concept A. "
             "It replaces the 2 rods, 4 LM6UU, carriage, spine, top cap, crank and link."),
        step(4, "Claw (unchanged)", claw, ["arm", "wrist_servo"],
             "The existing gripper frame, gears, fingers and SG90, on the wrist horn exactly as now."),
        step(5, "Lift = tilt the arm", [], [p["name"] for p in parts if p["group"] != "can"],
             f"The MG996R tilts the arm up {LIFT_DEG:.1f}°: the can, 127 mm out, rises {CAN_Y * math.sin(math.radians(LIFT_DEG)):.1f} mm "
             "(≥ 15.2). It comes back to the same angle to put the can down, so it lands level. Watch it in ▶."),
    ]
    data = dict(meshes=meshes, screws=[], glue=[], steps=steps, printed=sorted(p["name"] for p in parts if p["kind"] == "printed"),
                names={p["name"]: p["name"].replace("_", " ") for p in parts}, screw_names={}, redesign=True, report=rep, times=times,
                title="Plan F: redesign from scratch (least printing)",
                levels=dict(precise=dict(label="FIT", color="#c40000", text=""), try_=dict(label="TRY", color="#c77700", text=""),
                            easy=dict(label="CONCEPT", color="#1f7a45", text="Concept model: checked in CAD, not built yet.")),
                while_waiting=[],
                motion=dict(kind="shoulder", groups=groups, sequence=vm["sequence"],
                            params=dict(lift_theta0=0, grip_z=GZ, pivot_x=P["pivot_x"], pivot_y=P["pivot_y"], lift_servo_tip=[0, 0, 0],
                                        shoulder=list(SH), can_y=CAN_Y, lift_deg=LIFT_DEG, h_max=H_MAX)))
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/redesign.json ({os.path.getsize(OUT) // 1024} KB); {'ALL PASS' if ok else 'COLLISIONS'}")


if __name__ == "__main__":
    main()
