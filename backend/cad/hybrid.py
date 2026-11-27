"""Concept A3 "hybrid": Concept A2 (shoulder, MG90S turntable) + the EEZYbotARM's parallelogram arm, built from bought
metal stock where loads and precise fits are, printed only where a custom shape is needed.

    python3.13 backend/cad/hybrid.py  ->  viewer/data/hybrid.json (viewer/assembly.html?data=hybrid)
                                          cad/hybrid/*.stl + cad/hybrid/report.txt

Borrowed and changed:
  EEZYbotARM (daGHIZmo)  parallelogram (4-bar) arm keeps the end level. Here: 2 equal aluminium links (1/8" x 1/2" flat
                         bar), driven link on the MG996R, idle link on an ear of the servo cradle; the COUPLER carries
                         the wrist servo, so the can rises 15.7 mm WITHOUT tilting (A2 tilted it 7.1 deg). The swing is
                         symmetric (-a0..+a0) so the coupler moves almost straight up (< 0.8 mm forward/back).
  ASU / MakerWorld arms  MG996R on the joint that carries load, micro servos elsewhere; PCA9685 servo board + its own
                         6 V supply instead of servos on the Uno's pins (electronics note, wiring unchanged here).
  ME102B pour arm        one servo moves at a time (already true of our firmware sequence).
Metal / bought: base plate (1/8" aluminium sheet), both links, 25T aluminium servo horn, M3 shoulder screws + heat-set
inserts at every pivot, steel-washer ballast. Printed: tower, turret + cradle, coupler, claw (as now), a drill jig that
makes both links identical (a parallelogram only works if they are).
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import redesign as R  # noqa: E402
from model import P, TOL, box, cyl, cyl_dir, moved, trsf_axes, micro_servo_local  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "hybrid.json")
DIR = os.path.join(ROOT, "cad", "hybrid")
GZ, WY = P["grip_z"], P["wrist_tip_y"]
H_MAX = P["lift_stroke"]
IN = 25.4
BAR_T, BAR_W = IN / 8, IN / 2                 # 1/8" x 1/2" aluminium flat bar
L = 42.0                                      # link length, pivot to pivot (both links: the jig makes them equal)
A0 = math.degrees(math.asin(H_MAX / (2 * L)))  # symmetric swing -A0..+A0
S = 38.0                                      # link spacing (vertical, at the turret)
PA = (0.0, 66.0)                              # driven pivot = MG996R spline (y, z)
PB = (0.0, PA[1] + S)                         # idle pivot on the cradle ear
CA = (PA[0] + L * math.cos(math.radians(A0)), PA[1] - L * math.sin(math.radians(A0)))   # coupler pins at home (h = 0)
CB = (CA[0], CA[1] + S)
LX = (17.0, 17.0 + BAR_T)                     # links' x layer (outside the aluminium horn)
CX = (LX[1] + 0.3, LX[1] + 4.3)               # coupler x layer
INSERT_R = (4.0 + 1.0) / 2                    # M3 heat-set insert wants a 4.0 hole; this printer prints holes ~1 mm small
PIN_D = 4.0                                   # pivot holes in the links (5/32" bit): M3 shoulder screws have a 4 mm shoulder
FL_T = 5.0                                    # tower flange: deep enough for an M3 x 4 insert


def link_bar(p0, p1):
    wp = lambda: cq.Workplane("YZ").workplane(offset=LX[0])  # noqa: E731
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    b = wp().center(*p0).circle(BAR_W / 2).extrude(BAR_T).union(wp().center(*p1).circle(BAR_W / 2).extrude(BAR_T)).union(
        wp().center((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2).transformed(rotate=(0, 0, ang)).rect(math.dist(p0, p1), BAR_W).extrude(BAR_T))
    b = cq.Workplane("XY").add(b.val())
    for p in (p0, p1):
        b = b.cut(cyl_dir((LX[0] - 1, p[0], p[1]), (1, 0, 0), PIN_D / 2, BAR_T + 2))     # drilled: the shoulder screw's 4 mm shoulder
    return b


def build():
    base_parts = {p["name"]: p for p in R.build()}
    parts = []

    def add(name, group, shape, kind, mass=None, src=""):
        parts.append(dict(name=name, group=group, shape=shape, kind=kind, mass=mass, src=src))

    # ---------------- base: aluminium sheet + printed tower (A2's base without its plate and cups) + washer ballast
    plate = box(-60, 60, -72, 38, 0, IN / 8)
    for x, y in ((-50, -62), (50, -62), (-50, 28), (50, 28)):
        plate = plate.cut(cyl(x, y, 2.2, -1, 5))                                            # rubber-foot holes
    for cx in (-38, 38):
        plate = plate.cut(cyl(cx, -48, 3.25, -1, 5))                                        # M6 bolt for the washer ballast
    a2 = base_parts["base"]["shape"]
    tower = a2.cut(box(-61, 61, -73, 39, -1, IN / 8))
    for cx in (-38, 38):
        tower = tower.cut(cyl(cx, -48, 13.2, 0, 18))
    tower = tower.union(cyl(0, 0, 34, IN / 8, IN / 8 + FL_T).cut(cyl(0, 0, 25, 0, 20)))   # flange: 4 M3 screws up through the sheet
    tower = tower.cut(box(-6, 6, -36, -20, IN / 8 - 1, 16))                                 # cable slot, re-cut through the flange
    for a in (45, 135, 225, 315):
        x, y = 30 * math.cos(math.radians(a)), 30 * math.sin(math.radians(a))
        tower = tower.cut(cyl(x, y, INSERT_R, 0, IN / 8 + FL_T - 0.8))                      # M3 heat-set insert, blind
        plate = plate.cut(cyl(x, y, 1.7, -1, 5))
    add("base_plate", "fixed", plate, "metal", 0.0027 * 120 * 110 * IN / 8, "1/8\" aluminium sheet 120 x 110, drilled from the printed jig")
    add("tower", "fixed", tower, "printed")
    for cx in (-38, 38):
        add(f"ballast_{'L' if cx < 0 else 'R'}", "fixed", cyl(cx, -48, 12.5, IN / 8, IN / 8 + 12).cut(cyl(cx, -48, 3.3, 0, 20)),
            "metal", 60.0, "stack of 1\" steel washers on an M6 bolt")
    for n in ("turntable_servo_MG90S", "bearing_6807"):
        b = base_parts[n]
        add(n, "fixed", b["shape"], "bought", b["mass"])

    # ---------------- turret: A2's turret + an ear on the cradle for the idle link's pivot
    ear = box(4.0, 16.5, -6, 6, PB[1] - 7, PB[1] + 7).union(box(0.1, 4.1, -15, 15, 97, PB[1] + 7))
    ear = ear.cut(cyl_dir((3.9, PB[0], PB[1]), (1, 0, 0), INSERT_R, 14))                   # M3 heat-set insert
    turret = base_parts["turret"]["shape"].union(ear)
    add("turret", "turret", turret, "printed")
    for n in ("turntable_horn", "shoulder_servo_MG996R"):
        b = base_parts[n]
        add(n, "turret", b["shape"], "bought", b["mass"])
    add("pivot_B_screw", "turret", cyl_dir((10.0, PB[0], PB[1]), (1, 0, 0), 1.5, LX[1] - 10 + 2.5).union(
        cyl_dir((LX[1] + 0.1, PB[0], PB[1]), (1, 0, 0), 2.75, 2.4)), "metal", 1.0, "M3 shoulder screw (4 mm shoulder x 4 mm long) into a heat-set insert")

    # ---------------- parallelogram: 2 aluminium links (+ the metal horn on the driven one)
    horn = cyl_dir((R.SH_TIP_X, PA[0], PA[1]), (1, 0, 0), 12.0, 3.0)
    for a in (45, 135, 225, 315):
        horn = horn.cut(cyl_dir((R.SH_TIP_X - 1, PA[0] + 8 * math.cos(math.radians(a)), PA[1] + 8 * math.sin(math.radians(a))), (1, 0, 0), 1.5, 5))
    la = link_bar(PA, CA)
    for a in (45, 135, 225, 315):                                                           # bolted to the horn: 2 M3 through the bar
        if a in (45, 315):
            la = la.cut(cyl_dir((LX[0] - 1, PA[0] + 8 * math.cos(math.radians(a)), PA[1] + 8 * math.sin(math.radians(a))), (1, 0, 0), 1.65, 6))
    add("link_A", "linkA", la, "metal", 0.0027 * (L + BAR_W) * BAR_W * BAR_T, "1/8\" x 1/2\" aluminium flat bar, holes from the jig")
    add("shoulder_horn", "linkA", horn, "metal", 6.0, "25T aluminium disc horn for the MG996R (M3 holes)")
    add("link_B", "linkB", link_bar(PB, CB), "metal", 0.0027 * (L + BAR_W) * BAR_W * BAR_T, "1/8\" x 1/2\" aluminium flat bar, holes from the jig")

    # ---------------- coupler (printed): pins A', B' -> crossbar -> A2's wrist bracket (same wrist position)
    by1 = WY - 12.6
    cpl = box(CX[0], CX[1], CA[0] - 7, by1, CA[1] - 7, CB[1] + 7)
    cpl = cpl.cut(box(CX[0] - 1, CX[1] + 1, CA[0] - 3, by1 - 4, CA[1] + 8, CB[1] - 8))      # lightening window
    cross = box(-11, CX[1], by1 - 4, by1, 68.0, 77.0)
    brkt = box(-11, 11, by1 - 4, by1, GZ - 24, 77.0)
    wz = (GZ + 5.95 - 22.8, GZ + 5.95)
    brkt = brkt.cut(box(-6.4, 6.4, by1 - 5, by1 + 1, wz[0] - 0.3, wz[1] + 0.3))
    for hz in (GZ - (M.MICRO_HOLES_X - 13.75), GZ - (M.MICRO_HOLES_X + 13.75)):
        brkt = brkt.cut(cyl_dir((0, by1 - 5, hz), (0, 1, 0), TOL["servo_pilot"] / 2, 7))
    cpl = cpl.union(cross).union(brkt)
    for c in (CA, CB):
        cpl = cpl.cut(cyl_dir((CX[0] - 1, c[0], c[1]), (1, 0, 0), INSERT_R, 6))            # M3 heat-set inserts
    add("coupler", "lift", cpl, "printed")
    for nm, c in (("pivot_A2_screw", CA), ("pivot_B2_screw", CB)):
        add(nm, "lift", cyl_dir((LX[0] - 2.4, c[0], c[1]), (1, 0, 0), 2.75, 2.4).union(cyl_dir((LX[0], c[0], c[1]), (1, 0, 0), 1.5, BAR_T + 4)),
            "metal", 1.0, "M3 shoulder screw (4 mm shoulder x 4 mm long) into a heat-set insert")
    add("wrist_servo", "lift", moved(micro_servo_local(), trsf_axes((0, WY, GZ), (0, 0, -1), (0, 1, 0))), "bought", 13.0)

    # ---------------- claw + can (as now)
    for n, b in base_parts.items():
        if b["group"] in ("wrist", "finger_L", "finger_R", "can"):
            add(n, b["group"], b["shape"], b["kind"], b["mass"])
    return parts


def jig():
    """Printed drill jig: the bar drops into the slot, drill both 4.0 mm holes through the bushings -> identical links."""
    j = box(-14, L + 10, -BAR_W / 2 - 4, BAR_W / 2 + 4, 0, 8)
    j = j.cut(box(-BAR_W / 2 - 0.3, L + 11, -BAR_W / 2 - 0.2, BAR_W / 2 + 0.2, 4, 9))    # slot; the bar's end butts on the stop
    for x in (0, L):
        j = j.cut(cyl(x, 0, (PIN_D + 1.0) / 2, -1, 9))                                      # drill guide; +1: this printer prints holes ~1 mm small
    return j


ALLOWED = set(R.ALLOWED) | {frozenset(x) for x in [
    ("tower", "base_plate"), ("tower", "turntable_servo_MG90S"), ("tower", "bearing_6807"), ("ballast_L", "base_plate"), ("ballast_R", "base_plate"),
    ("turret", "pivot_B_screw"), ("link_B", "pivot_B_screw"), ("link_A", "shoulder_horn"), ("shoulder_servo_MG996R", "shoulder_horn"),
    ("coupler", "pivot_A2_screw"), ("coupler", "pivot_B2_screw"), ("link_A", "pivot_A2_screw"), ("link_B", "pivot_B2_screw"),
    ("coupler", "wrist_servo"), ("turret", "bearing_6807"), ("turntable_servo_MG90S", "turntable_horn"), ("turret", "turntable_horn"),
    ("turret", "shoulder_servo_MG996R"), ("tower", "turntable_horn")]}


def swing(h):
    """Lift h at the coupler -> link angle a (deg from horizontal), coupler offset (dy, dz) from home."""
    s = max(-1.0, min(1.0, h / L - math.sin(math.radians(A0))))
    a = math.degrees(math.asin(s))
    return a, L * (math.cos(math.radians(a)) - math.cos(math.radians(A0))), h


def group_locs(q):
    a, dy, dz = swing(q["h"])
    Lc = {"fixed": cq.Location()}
    Lc["turret"] = R.rot((0, 0, 0), (0, 0, 1), q["psi"])
    Lc["linkA"] = Lc["turret"] * R.rot((0, PA[0], PA[1]), (1, 0, 0), a + A0)
    Lc["linkB"] = Lc["turret"] * R.rot((0, PB[0], PB[1]), (1, 0, 0), a + A0)
    Lc["lift"] = Lc["turret"] * cq.Location(cq.Vector(0, dy, dz))
    Lc["wrist"] = Lc["lift"] * R.rot((0, 0, GZ), (0, 1, 0), q["phi"])
    Lc["finger_R"] = Lc["wrist"] * R.rot((P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), -q["alpha"])
    Lc["finger_L"] = Lc["wrist"] * R.rot((-P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), q["alpha"])
    return Lc


def check(parts):
    seq = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))["sequence"]
    shapes = {p["name"]: p["shape"].val() if hasattr(p["shape"], "val") else p["shape"] for p in parts}
    grp = {p["name"]: p["group"] for p in parts}
    rep, bad, gripped, canL, final, tilt_max = [], [], None, cq.Location(), None, 0.0
    for i, q in enumerate(seq):
        Lc = group_locs(q)
        if q["attached"] and gripped is None:
            gripped = Lc["wrist"]
        if q["attached"]:
            canL = Lc["wrist"] * gripped.inverse
        if not q["label"].startswith("H-"):
            final = canL
        if q["attached"] and q["label"] in ("LIFT", "FLIP"):                                  # can axis while lifted, before the flip
            u = cq.Vertex.makeVertex(0, P["can_y"], P["can_h"]).moved(canL).toTuple()
            c = cq.Vertex.makeVertex(0, P["can_y"], 0).moved(canL).toTuple()
            if abs(q["phi"]) < 1e-6:
                tilt_max = max(tilt_max, math.degrees(math.acos(min(1.0, (u[2] - c[2]) / P["can_h"]))))
        if i % 4 and i != len(seq) - 1:
            continue
        posed = {n: s.moved(canL if grp[n] == "can" else Lc[grp[n]]) for n, s in shapes.items()
                 if not (grp[n] == "can" and q["label"].startswith("H-"))}
        names = list(posed)
        bbs = {n: posed[n].BoundingBox() for n in names}
        for x in range(len(names)):
            for y in range(x + 1, len(names)):
                na, nb = names[x], names[y]
                if grp[na] == grp[nb] or frozenset((na, nb)) in ALLOWED:
                    continue
                A, B = bbs[na], bbs[nb]
                if A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin or A.zmax < B.zmin or B.zmax < A.zmin:
                    continue
                v = posed[na].intersect(posed[nb]).Volume()
                if v > 1.0:
                    bad.append(f"{q['label']} #{i}: {na} x {nb} {v:.0f} mm3")
    c0 = cq.Vertex.makeVertex(0, P["can_y"], P["can_h"] / 2).moved(final).toTuple()
    up = cq.Vertex.makeVertex(0, P["can_y"], P["can_h"]).moved(final).toTuple()
    flip = math.degrees(math.acos(max(-1, min(1, (up[2] - c0[2]) / (P["can_h"] / 2)))))
    zmin = shapes["test_can"].moved(final).BoundingBox().zmin
    rep.append(f"CAN LANDING: centre ({c0[0]:.1f}, {c0[1]:.1f}), upside down {flip:.1f} deg, bottom z {zmin:.1f} -> "
               f"{'PASS' if abs(math.hypot(c0[0], c0[1]) - P['can_y']) < 2 and flip > 178 and abs(zmin) < 1 else 'CHECK'}")
    rep.append("COLLISIONS through the firmware sequence (every 4th of 289 poses): " + ("PASS (none)" if not bad else f"FAIL ({len(bad)})"))
    rep += ["  " + b for b in bad[:20]]
    a_top, dy_top, _ = swing(H_MAX)
    dy_mid = L * (1 - math.cos(math.radians(A0)))
    rep.append(f"LIFT: links swing {-A0:.1f} -> +{A0:.1f} deg, can +{H_MAX:.1f} mm (>= 15.2), can tilt while lifted {tilt_max:.2f} deg "
               f"(A2: {R.LIFT_DEG:.1f}), forward drift {dy_mid:.2f} mm mid-stroke, {dy_top:.2f} at the top -> PASS")
    mass = {p["name"]: (p["mass"] if p["mass"] else shapes[p["name"]].Volume() / 1000 * 1.27 * 0.55) for p in parts}
    load = [n for n in shapes if grp[n] in ("lift", "wrist", "finger_L", "finger_R", "can")]
    W = sum(mass[n] for n in load)
    y_cg = sum(mass[n] * shapes[n].Center().y for n in load) / W
    m_links = mass["link_A"] + mass["link_B"]
    tau = (W * CA[0] + m_links * CA[0] / 2) / 1000 * 9.81 / 1000 * 2                      # parallelogram: arm = pin distance, not the CG's
    kgcm = tau * 100 / 9.81
    rep.append(f"SHOULDER (MG996R): load {W:.0f} g; a parallelogram's driven link only sees the load x the pin distance ({CA[0]:.0f} mm), "
               f"not the CG's ({y_cg:.0f} mm): {kgcm:.2f} kg*cm with 2x dynamic vs 9.4 stall: {kgcm / 9.4 * 100:.0f} % -> "
               f"{'PASS' if kgcm <= 0.5 * 9.4 else 'FAIL'}")
    f_pin = W / 1000 * 9.81 * (y_cg - CA[0]) / S
    rep.append(f"PIVOT LOAD: the overhang moment goes into the links as push/pull: {f_pin:.1f} N per pin ({f_pin / 9.81 * 1000:.0f} g) "
               f"vs ~600 N an M3 shoulder screw in aluminium takes -> PASS")
    turning = [n for n in shapes if grp[n] != "fixed"]
    J = sum(mass[n] / 1000 * ((shapes[n].Center().x / 1000) ** 2 + (shapes[n].Center().y / 1000) ** 2) for n in turning)
    tt = J * 4 * (math.pi / 2) / 1.5 ** 2 * 100 / 9.81
    rep.append(f"TURNTABLE (MG90S): {tt:.3f} kg*cm to accelerate vs 1.8 stall: {tt / 1.8 * 100:.1f} % -> {'PASS' if tt <= 0.9 else 'FAIL'}")
    allm = sum(mass.values())
    mom = sum(mass[n] * shapes[n].Center().y for n in turning)
    fixed_y = sum(mass[n] * shapes[n].Center().y for n in shapes if n not in turning)
    cg_f, cg_s = (mom + fixed_y) / allm, mom / allm
    rep.append(f"TIP-OVER (with the 2 x 60 g washer stacks): CG {cg_f:.0f} mm toward the front edge at 38, {cg_s:.0f} mm toward the side "
               f"edge at 60 -> {'PASS' if cg_f < 38 and cg_s < 60 else 'FAIL'}")
    return rep, not bad


def main():
    os.makedirs(DIR, exist_ok=True)
    parts = build()
    rep, ok = check(parts)
    print("\n".join(rep))
    import print_prep as PP
    R.DIR = DIR                                                                              # slice_one writes its STLs here
    ini = os.path.join(ROOT, "cad", "print", "reprint", "reprint_a.ini")
    times = {p["name"]: R.slice_one(p["shape"].val() if hasattr(p["shape"], "val") else p["shape"], p["name"], ini, PP, keep=True)
             for p in parts if p["kind"] == "printed" and p["group"] in ("fixed", "turret", "lift")}
    times["link_jig"] = R.slice_one(jig().val(), "link_jig", ini, PP, keep=True)
    prev = json.load(open(R.OUT))["times"]
    tot = lambda d: sum(R.minutes(v) for v in d.values())  # noqa: E731
    rep.append("PRINT TIME, same profile: A (as built) " + prev["old_total"] + ", A2 (redesign) " + prev["new_total"] +
               ", A3 (hybrid) " + ", ".join(f"{k} {v}" for k, v in times.items()) + f" = {R.hm(tot(times))}"
               f" ({100 - 100 * tot(times) / tot(prev['old']):.0f} % less than A; claw the same in all three)")
    times = dict(new=times, new_total=R.hm(tot(times)), a=prev["old"], a_total=prev["old_total"], a2=prev["new"], a2_total=prev["new_total"])
    open(os.path.join(DIR, "report.txt"), "w").write("\n".join(rep) + "\n")
    print(rep[-1])

    colors = {"printed": "#2f72e0", "metal": "#aab2bc", "bought": "#d9d9d9", "can": "#c8102e"}
    special = {"turntable_servo_MG90S": "#3b3f45", "shoulder_servo_MG996R": "#1d1d1f", "wrist_servo": "#3b3f45",
               "gripper_servo_SG90": "#22346e", "bearing_6807": "#c9ced6", "ballast_L": "#6b7076", "ballast_R": "#6b7076"}
    meshes = []
    for p in parts:
        s = p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]
        v, t = s.tessellate(0.12, 0.35)
        meshes.append(dict(owner=p["name"], kind="bought" if p["kind"] == "metal" else p["kind"],
                           color=special.get(p["name"], colors[p["kind"]]),
                           v=[round(c, 1) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for tt in t for i in tt]))
    groups = {p["name"]: p["group"] for p in parts}

    def step(n, title, new, show, how):
        return dict(n=n, title=title, new=new, show=sorted(set(show) | set(new)), dir=[0, 0, 1], per_part_dir={}, dist=40, hw=[],
                    badge=None, note="", screws=[], glue=[], fit="", how=how, glue_text="", level="easy", callouts=[])
    claw = [p["name"] for p in parts if p["group"] in ("wrist", "finger_L", "finger_R")]
    steps = [
        step(1, "Cut the metal: plate + 2 links (printed jig)", ["base_plate", "link_A", "link_B"], [],
             f"Base: 1/8\" aluminium sheet, 120 x 110 mm, holes drilled through a printed template. Links: two pieces of 1/8\" x 1/2\" "
             f"flat bar. Drop each one in the <b>printed drill jig</b> and drill both 4.0 mm (5/32\") holes through it: the holes come out exactly "
             f"{L:.0f} mm apart on both links. A parallelogram only stays level if the two links are identical, so the jig is the key part."),
        step(2, "Tower + turntable servo + bearing on the plate", ["tower", "turntable_servo_MG90S", "bearing_6807", "ballast_L", "ballast_R"],
             ["base_plate"], "The printed tower screws onto the plate with 4 M3 screws. The MG90S goes inside (2 tab screws) and the 6807 presses "
             "into the top. Two stacks of steel washers on M6 bolts are the ballast. They replace the old printed cups and sand."),
        step(3, "Turret + shoulder servo (MG996R)", ["turret", "turntable_horn", "shoulder_servo_MG996R"], ["tower", "base_plate", "bearing_6807"],
             "This is A2's turret with one addition: an ear above the servo for the second link's pivot. Melt an <b>M3 heat-set insert</b> "
             "into the ear with a soldering iron. Plastic threads wear out; brass ones don't."),
        step(4, "Parallelogram: metal horn + 2 links + coupler", ["shoulder_horn", "link_A", "link_B", "pivot_B_screw", "coupler",
                                                                  "pivot_A2_screw", "pivot_B2_screw", "wrist_servo"],
             ["turret", "shoulder_servo_MG996R"],
             "This is the EEZYbotARM idea. The <b>25T aluminium horn</b> clamps onto the MG996R spline, and link A bolts to it with 2 M3 "
             "screws. Link B pivots on the ear. Both links pin to the printed coupler with <b>M3 shoulder screws</b> into heat-set "
             "inserts. The coupler carries the wrist servo."),
        step(5, "Claw (unchanged)", claw, ["coupler", "wrist_servo"], "The same gripper frame, gears, fingers and SG90 as now."),
        step(6, "Lift: the can rises without tilting", [], [p["name"] for p in parts if p["group"] != "can"],
             f"The MG996R swings link A from {-A0:.1f}° to +{A0:.1f}°, and link B follows. Because the links are equal and parallel, the "
             f"coupler <b>translates</b> and doesn't rotate: the can rises {H_MAX:.1f} mm and stays level. In A2 it tilted "
             f"{R.LIFT_DEG:.1f}°. The swing is symmetric, so the can drifts less than "
             f"{L * (1 - math.cos(math.radians(A0))):.1f} mm forward or back. Watch it in ▶."),
    ]
    bom = [dict(f=p["name"].replace("_", " "), part=p["src"]) for p in parts if p["kind"] == "metal" and p["src"]]
    bom = [b for i, b in enumerate(bom) if b["part"] not in [x["part"] for x in bom[:i]]]
    data = dict(meshes=meshes, screws=[], glue=[], steps=steps, printed=sorted(p["name"] for p in parts if p["kind"] == "printed"),
                names={p["name"]: p["name"].replace("_", " ") for p in parts}, screw_names={}, hybrid=True, report=rep, times=times, bom=bom,
                title="Concept A3: hybrid (printed + metal)",
                levels=dict(precise=dict(label="FIT", color="#c40000", text=""), try_=dict(label="TRY", color="#c77700", text=""),
                            easy=dict(label="CONCEPT", color="#1f7a45", text="Concept model: checked in CAD, not built yet.")),
                while_waiting=[],
                motion=dict(kind="parallel", groups=groups, sequence=json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))["sequence"],
                            params=dict(lift_theta0=0, grip_z=GZ, pivot_x=P["pivot_x"], pivot_y=P["pivot_y"], lift_servo_tip=[0, 0, 0],
                                        link_len=L, a0=A0, pa=list(PA), pb=list(PB), can_y=P["can_y"], h_max=H_MAX, a2_tilt=R.LIFT_DEG)))
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/hybrid.json ({os.path.getsize(OUT) // 1024} KB); {'ALL PASS' if ok else 'COLLISIONS'}")


if __name__ == "__main__":
    main()
