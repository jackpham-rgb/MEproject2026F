"""Run the firmware sequence through the detail model and check it.

    python3.13 backend/cad/check.py          (needs cadquery)

1. Collision sweep: every pair of parts in different groups, at every sample of every move
   (grip, lift, flip, turn, lower, release, then the automatic return), using solid
   booleans (not bounding boxes). Also checks every moving part and the can against the table.
2. Mass, centre of gravity and tip-over for the whole robot.
3. Servo loads recomputed from the CAD masses (lift jam ratio, lift / wrist / turntable torque).
Writes cad/check/check_report.txt and cad/check/mass_table.csv.
"""
import math
import os
import sys
import time

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Trsf, gp_Pnt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "cad", "check")
os.makedirs(OUT, exist_ok=True)
G = 9.81

# Pairs that touch by design (a spline in its horn, a pin in its link, meshing pitch discs, a can in the pads).
ALLOWED = {
    frozenset(("turntable_servo_MG996R", "turntable_horn")),
    frozenset(("bearing_6807", "turret_plate")),
    frozenset(("lift_crank", "lift_link")),
    frozenset(("lift_crank", "lift_servo_MG90S")),
    frozenset(("wrist_servo", "wrist_horn")),
    frozenset(("wrist_servo", "gripper_frame")),        # spline tip touches the flange face
    frozenset(("gripper_servo_SG90", "finger_L")),
    # finger_L / finger_R: real involute gears now; they must NOT overlap (checked like any other pair)
    frozenset(("axle_R", "finger_R")),
}
VOL_TOL = 1.0      # mm^3: anything bigger is a real overlap
NEAR = 4.0         # mm: report pairs that come closer than this


def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def hull(points):
    pts = sorted(set(points))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def inside_margin(poly, pt):
    """Signed distance from pt to the nearest hull edge (positive = inside)."""
    best = 1e9
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(x2 - x1, y2 - y1)
        best = min(best, ((x2 - x1) * (pt[1] - y1) - (y2 - y1) * (pt[0] - x1)) / L)
    return best


def moved_shape(part, t):
    return part["collide"].val().moved(cq.Location(t))


def main():
    t0 = time.time()
    parts = [p for p in M.build_parts() if p["group"] != "coupon"]
    by_name = {p["name"]: p for p in parts}
    seq = M.sequence(step_samples=24)
    lines = []
    hits = {}
    table = {}
    can_pose = None          # gp_Trsf of the can (world) while attached
    T_can = gp_Trsf()
    attached_prev = False
    grip_wrist = None
    can = by_name["test_can"]
    near = {}
    pad_gap = {}
    footprint = None
    tip_worst = (1e9, None)
    masses = {}
    for p in parts:
        if p["material"] in ("PETG", "TPU", "silicone"):
            masses[p["name"]] = p["shape"].val().Volume() / 1000.0 * (1.27 if p["material"] == "PETG" else 1.21) * M.P["print_fill"]
        else:
            masses[p["name"]] = p["mass"] or 0.0
    centers = {p["name"]: p["shape"].val().Center() for p in parts}
    # support footprint = convex hull of the base + tray bottom faces
    pts = []
    for nm in ("base", "electronics_tray"):
        for v in by_name[nm]["shape"].faces("<Z").vertices().vals():
            pts.append((round(v.X, 2), round(v.Y, 2)))
    footprint = hull(pts)
    for k, (label, cmd, attached) in enumerate(seq):
        j = M.joints_from_commands(**cmd)
        T = M.group_transforms(j)
        if attached and not attached_prev:
            grip_wrist = T["wrist"]                             # can rides with the wrist from here
        if attached:
            T_can = T["wrist"].Multiplied(grip_wrist.Inverted())
        attached_prev = attached
        T["can"] = T_can
        can_removed = label.startswith("H-")              # operator lifts the can off before homing
        shapes = {p["name"]: (p, moved_shape(p, T[p["group"]])) for p in parts
                  if not (can_removed and p["name"] == "test_can")}
        bbs = {n: s.BoundingBox() for n, (_, s) in shapes.items()}
        names = list(shapes)
        for a in range(len(names)):
            na = names[a]
            pa, sa = shapes[na]
            # table check for anything that moves
            if pa["group"] not in ("fixed",):
                zmin = bbs[na].zmin
                table[na] = min(table.get(na, 1e9), zmin)
            for b in range(a + 1, len(names)):
                nb = names[b]
                pb, sb = shapes[nb]
                if pa["group"] == pb["group"]:
                    continue
                if frozenset((na, nb)) in ALLOWED:
                    continue
                if "test_can" in (na, nb) and attached:
                    other = nb if na == "test_can" else na
                    if other.startswith("finger_") or other == "can_bumper":
                        continue
                A, B = bbs[na], bbs[nb]
                if A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin or A.zmax < B.zmin or B.zmax < A.zmin:
                    continue
                v = sa.intersect(sb).Volume()
                if v > VOL_TOL:
                    key = (na, nb)
                    hits.setdefault(key, []).append((label, round(v, 1)))
                elif k % 4 == 0 and A.xmin - NEAR < B.xmax and B.xmin - NEAR < A.xmax:
                    dd = dist(sa, sb)
                    if dd < NEAR:
                        key = tuple(sorted((na, nb)))
                        if dd < near.get(key, (1e9, ""))[0]:
                            near[key] = (dd, label)
            # bounding boxes miss gaps up to NEAR: also test pairs whose boxes are within NEAR
        for na in (names if k % 4 == 0 else []):
            for nb in names:
                if na >= nb or shapes[na][0]["group"] == shapes[nb][0]["group"] or frozenset((na, nb)) in ALLOWED:
                    continue
                A, B = bbs[na], bbs[nb]
                overlap = not (A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin or A.zmax < B.zmin or B.zmax < A.zmin)
                close = not (A.xmax + NEAR < B.xmin or B.xmax + NEAR < A.xmin or A.ymax + NEAR < B.ymin or
                             B.ymax + NEAR < A.ymin or A.zmax + NEAR < B.zmin or B.zmax + NEAR < A.zmin)
                if close and not overlap:
                    if "test_can" in (na, nb) and attached:
                        continue
                    dd = dist(shapes[na][1], shapes[nb][1])
                    key = tuple(sorted((na, nb)))
                    if dd < NEAR and dd < near.get(key, (1e9, ""))[0]:
                        near[key] = (dd, label)
        step_end = k + 1 == len(seq) or seq[k + 1][0] != label
        if not can_removed and step_end and label in ("GRIP", "RELEASE"):
            for fn, sx in (("finger_L", -1), ("finger_R", 1)):
                # pads only: leave out the gear (within 11 mm of the pivot), whose teeth sit behind the can
                pad_only = by_name[fn]["shape"].val().cut(
                    M.cyl(sx * M.P["pivot_x"], M.P["pivot_y"], 11.0, -1, 200).val()).moved(cq.Location(T[by_name[fn]["group"]]))
                pad_gap.setdefault(label, []).append(dist(pad_only, shapes["test_can"][1]))
        # whole-robot CG (incl. can if present) vs the support footprint
        tm = tx = ty = 0.0
        for nm, (pp, shp) in shapes.items():
            c = centers[nm]
            q = gp_Pnt(c.x, c.y, c.z).Transformed(T[pp["group"]])
            tm += masses[nm]; tx += masses[nm] * q.X(); ty += masses[nm] * q.Y()
        mg = inside_margin(footprint, (tx / tm, ty / tm))
        if mg < tip_worst[0]:
            tip_worst = (mg, label)
        if label == "LOWER":
            final_can = T_can
    lines.append(f"COLLISION SWEEP: {len(seq)} poses x {len(parts)} parts, solid booleans, tolerance {VOL_TOL} mm^3")
    lines.append(f"  sequence: {' > '.join(dict.fromkeys(s[0] for s in seq))}")
    if hits:
        for (a, b), lst in hits.items():
            lines.append(f"  FAIL  {a} x {b}: {len(lst)} poses, first at {lst[0][0]} ({lst[0][1]} mm^3), max {max(v for _, v in lst)} mm^3")
    else:
        lines.append("  PASS  no part-to-part collisions in any pose")
    lines.append(f"  tightest gaps between parts that move relative to each other (< {NEAR} mm):")
    for (a, b), (dd, lbl) in sorted(near.items(), key=lambda kv: kv[1][0])[:10]:
        lines.append(f"    {dd:5.2f} mm  {a} x {b}  (at {lbl})")
    # can placement result
    c0 = gp_Pnt(0, M.P["can_y"], M.P["can_h"] / 2).Transformed(final_can)
    up = gp_Pnt(0, M.P["can_y"], M.P["can_h"]).Transformed(final_can)
    axis_z = (up.Z() - c0.Z()) / (M.P["can_h"] / 2)
    tilt = math.degrees(math.acos(max(-1, min(1, abs(axis_z)))))
    zmin_can = can["shape"].val().moved(cq.Location(final_can)).BoundingBox().zmin
    lines.append(f"  can after LOWER: centre ({c0.X():.1f}, {c0.Y():.1f}) mm (target (127.0, 0.0)), "
                 f"{'INVERTED' if axis_z < 0 else 'UPRIGHT'}, tilt {tilt:.1f} deg, bottom at z = {zmin_can:+.2f} mm "
                 f"-> {'PASS' if axis_z < 0 and abs(zmin_can) < 0.5 and math.hypot(c0.X() - 127, c0.Y()) < 6 else 'FAIL'}")
    gl = pad_gap.get("GRIP", [])
    lines.append(f"  gap measurement: every 4th pose ({len(seq) // 4}); collision booleans: every pose")
    lines.append(f"  pads at GRIP end: {min(gl[-2:]):.2f} mm from the can (0 = touching; the servo then squeezes past contact); "
                 f"at RELEASE end: {min(pad_gap['RELEASE'][-2:]):.1f} mm clear")
    lines.append(f"  tip-over: robot CG stays {tip_worst[0]:.0f} mm inside the support footprint (worst at {tip_worst[1]}) -> "
                 f"{'PASS' if tip_worst[0] > 10 else 'FAIL'}")
    lows = sorted(table.items(), key=lambda kv: kv[1])
    bad = [(n, z) for n, z in lows if z < -0.05]
    lines.append(f"  {'FAIL' if bad else 'PASS'}  table clearance (lowest moving parts): " +
                 ", ".join(f"{n} {z:+.1f} mm" for n, z in lows[:5]))

    # ---------------- mass ----------------
    lines.append("")
    lines.append("MASS (printed: volume x 1.27 g/cc x 0.60 fill factor, EST; purchased: typical datasheet mass)")
    rows = []
    tot = 0.0
    mx = my = mz = 0.0
    group_mass = {}
    group_mom = {}
    for p in parts:
        sh = p["shape"].val()
        vol = sh.Volume() / 1000.0                                 # cm^3
        c = sh.Center()
        if p["material"] in ("PETG", "TPU", "silicone"):
            m = vol * (1.27 if p["material"] == "PETG" else 1.21) * M.P["print_fill"]
        else:
            m = p["mass"] or 0.0
        rows.append((p["name"], p["group"], p["material"], vol, m, c.x, c.y, c.z))
        if p["name"] != "test_can":
            tot += m
            mx += m * c.x; my += m * c.y; mz += m * c.z
        group_mass[p["group"]] = group_mass.get(p["group"], 0) + m
        gm = group_mom.setdefault(p["group"], [0, 0, 0])
        gm[0] += m * c.x; gm[1] += m * c.y; gm[2] += m * c.z
    with open(os.path.join(OUT, "mass_table.csv"), "w") as f:
        f.write("part,group,material,volume_cm3,mass_g,cg_x_mm,cg_y_mm,cg_z_mm\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]:.1f},{r[4]:.1f},{r[5]:.1f},{r[6]:.1f},{r[7]:.1f}\n")
    printed = sum(r[4] for r in rows if r[2] in ("PETG", "TPU", "silicone"))
    filament = sum(r[3] for r in rows if r[2] == "PETG") * 1.27 * M.P["print_fill"]
    lines.append(f"  robot total {tot:.0f} g (printed {printed:.0f} g, purchased {tot - printed:.0f} g), can 15 g")
    lines.append(f"  PETG filament ~{filament:.0f} g (+ supports / purge ~15 %)")
    cg = (mx / tot, my / tot, mz / tot)
    lines.append(f"  CG at home: ({cg[0]:.1f}, {cg[1]:.1f}, {cg[2]:.1f}) mm")
    for g in ("turret", "crank", "lift", "wrist", "finger_L", "finger_R"):
        lines.append(f"    {g:9s} {group_mass.get(g, 0):6.1f} g")

    # ---------------- servo loads from CAD ----------------
    lines.append("")
    lines.append("SERVO LOADS FROM CAD MASSES (stall ratings at 5 V: MG996R 9.4, MG90S 1.8, SG90 1.6 kg*cm)")
    lift_set = ["lift", "wrist", "finger_L", "finger_R"]
    m_lift = sum(group_mass[g] for g in lift_set) + 15.0
    y_cg = (sum(group_mom[g][1] for g in lift_set) + 15.0 * M.P["can_y"]) / m_lift
    e = y_cg - M.P["rod_y"]
    L = (M.P["car_z1"] - M.P["lm_len"] / 2) - (M.P["car_z0"] + M.P["lm_len"] / 2)
    mu = 0.01
    jam = 2 * mu * e / L
    F = m_lift / 1000 * G * (1 + jam)
    th = math.radians(abs(M.P["lift_theta0"]))
    tau = F * M.P["lift_crank"] / 1000 / math.cos(th) / G * 100
    lines.append(f"  lift: {m_lift:.0f} g moving (incl. can), CG {e:.0f} mm in front of the rods, bushing span {L:.0f} mm")
    lines.append(f"        jam ratio 2*mu*e/L = {jam:.3f} with LM6UU (printed slide mu 0.3 would be {2 * 0.3 * e / L:.2f}) -> "
                 f"{'PASS' if jam < 1 else 'FAIL'}; crank torque {tau:.2f} kg*cm vs MG90S 1.8 -> {1.8 / tau:.0f}x margin")
    wset = ["wrist", "finger_L", "finger_R"]
    m_w = sum(group_mass[g] for g in wset) + 15.0
    xw = (sum(group_mom[g][0] for g in wset) + 0) / m_w
    zw = (sum(group_mom[g][2] for g in wset) + 15.0 * M.P["can_h"] / 2) / m_w - M.P["grip_z"]
    off = math.hypot(xw, zw)
    tau_w = m_w / 1000 * off / 10
    lines.append(f"  wrist: {m_w:.0f} g rotating (incl. can), CG {off:.1f} mm off the roll axis -> {tau_w:.2f} kg*cm "
                 f"vs micro servo 1.8 -> {1.8 / max(tau_w, 1e-6):.0f}x margin")
    J = 0.0
    for p in parts:
        if p["group"] in ("fixed", "can"):
            continue
        r = next(rr for rr in rows if rr[0] == p["name"])
        J += r[4] / 1000 * ((r[5] / 1000) ** 2 + (r[6] / 1000) ** 2)
    J += 0.015 * (M.P["can_y"] / 1000) ** 2
    alpha = 10 / math.sqrt(3) * math.radians(90) / 1.5 ** 2
    lines.append(f"  turntable: J = {J * 1e4:.1f} kg*cm^2, accel torque {J * alpha / G * 100:.3f} kg*cm vs MG996R 9.4 (weight on the 6807 bearing)")
    lines.append("")
    lines.append(f"(run time {time.time() - t0:.0f} s)")
    rep = "\n".join(lines)
    print(rep)
    open(os.path.join(OUT, "check_report.txt"), "w").write(rep + "\n")
    return 1 if (hits or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
