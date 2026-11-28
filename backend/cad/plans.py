"""Plan C (before 3D printers: shop-built) and Plan E (online designs + engineering advice, DUM-E style) in 3D.

    python3.13 backend/cad/plans.py  ->  viewer/data/planc.json, viewer/data/plane.json, viewer/data/fixes_summary.json
                                          cad/plans/report_c.txt, cad/plans/report_e.txt

Both use the hybrid's checked kinematics (MG90S turntable on the 6807, MG996R shoulder driving an equal-link
parallelogram, the same wrist and claw position) so the firmware sequence and the collision check carry over.
  Plan C: nothing printed. Plywood base (Forstner pocket for the bearing), 1/8" aluminium plate + angle for the turret,
          cradle and coupler, a PVC-pipe hub, a hex standoff as the idle pivot, tapped holes instead of inserts; the claw
          outline cut from acrylic (laser or scroll saw) with bought brass gears.
  Plan E: the hybrid + what the engineers' rule books and the online arms say: counterbalance the arm (weight on a tail
          behind the shoulder: the servo only accelerates it), a heavy round base, servo power on its own supply
          (PCA9685), soft motion, cable strain relief, a can-present sensor. The look borrows the DUM-E idea from the
          Iron Man films: one sturdy arm on a heavy round base with a simple claw (inspiration only, no copied design).
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import hybrid as H  # noqa: E402
from model import P, box, cyl, cyl_dir, moved, trsf_axes, micro_servo_local  # noqa: E402

DIR = os.path.join(ROOT, "cad", "plans")
IN = 25.4
T8 = IN / 8                                    # 1/8" aluminium plate / angle
AL = 0.0027                                    # g/mm3 aluminium
WOOD = 0.0006                                  # g/mm3 plywood
GZ, WY = P["grip_z"], P["wrist_tip_y"]
BY1 = WY - 12.6                                # wrist-servo tab plane


def angle_piece(x0, x1, y0, y1, z0, z1, legs):
    """1" x 1" x 1/8" aluminium angle cut to length; legs = list of boxes (already positioned)."""
    s = None
    for b in legs:
        s = b if s is None else s.union(b)
    return s


def claw_parts(hparts, material_note):
    out = []
    for p in hparts:
        if p["group"] in ("wrist", "finger_L", "finger_R", "can"):
            q = dict(p)
            if p["name"] in material_note:
                q["kind"], q["src"] = "metal" if "brass" in material_note[p["name"]] else q["kind"], material_note[p["name"]]
            out.append(q)
    return out


# ------------------------------------------------------------------ Plan C
def build_c():
    hp = {p["name"]: p for p in H.build()}
    parts = []

    def add(name, group, shape, kind, mass=None, src="", color=None):
        parts.append(dict(name=name, group=group, shape=shape, kind=kind, mass=mass, src=src, color=color))

    # base: 3/4" plywood + 3/8" riser + 1/2" bearing board (Forstner pocket), servo tabs on the riser
    z1, z2, z3 = 0.75 * IN, 0.75 * IN + 0.375 * IN, 0.75 * IN + 0.375 * IN + 0.5 * IN
    tip = z2 + 12.6                                                                       # spline tip: tab underside on the riser
    slot = box(-6.4, 17.3, -6.6, 6.6, -1, z3 + 1)                                         # MG90S body (x -5.95..16.85)
    base = box(-60, 60, -72, 38, 0, z1).cut(slot)
    for x in (-45, 45):
        base = base.cut(cyl(x, -58, 3.25, -1, z1 + 1))
    riser = box(-40, 40, -40, 38, z1, z2).cut(slot)
    for hx in (5.45 - 13.75, 5.45 + 13.75):
        riser = riser.cut(cyl(hx, 0, 1.0, z2 - 8, z2 + 1))                                # pilots for the tab screws
    brd = box(-40, 40, -40, 38, z2, z3).cut(cyl(0, 0, 1.875 * IN / 2, z3 - 7, z3 + 1))     # 1-7/8" Forstner, 7 deep
    brd = brd.cut(box(-11.5, 22.4, -6.8, 6.8, z2 - 1, z3))                                # through-slot over the servo tabs
    brd = brd.cut(cyl(0, 0, 1.5 * IN / 2, z2 - 1, z3))                                    # 1-1/2" through: horn + hub clearance
    add("base_board", "fixed", base, "wood", WOOD * 120 * 110 * z1, "3/4\" plywood 120 x 110")
    add("riser_board", "fixed", riser, "wood", WOOD * 80 * 78 * (z2 - z1), "3/8\" plywood 80 x 78, servo slot")
    add("bearing_board", "fixed", brd, "wood", WOOD * 80 * 78 * (z3 - z2), "1/2\" plywood 80 x 78, 1-7/8\" Forstner pocket 7 mm deep")
    for k, x in (("L", -45), ("R", 45)):
        add(f"ballast_{k}", "fixed", cyl(x, -58, 12.5, z1, z1 + 14).cut(cyl(x, -58, 3.3, 0, 40)), "metal", 70.0, "1\" steel washers on an M6 bolt")
    add("turntable_servo_MG90S", "fixed", moved(micro_servo_local(), trsf_axes((0, 0, tip), (1, 0, 0), (0, 0, 1))), "bought", 13.4)
    add("bearing_6807", "fixed", cyl(0, 0, 23.5, z3 - 7, z3).cut(cyl(0, 0, 17.5, 0, 60)), "bought", 30.0)

    # turret: 1/8" aluminium plate + 1" PVC pipe stub hub (33.4 OD + tape = 35) + cradle plate + 2 angle brackets
    tz0, tz1 = 42.5, 42.5 + T8
    plate = cyl(0, 0, 28, tz0, tz1).union(box(-33, 6, -25, 25, tz0, tz1))
    for a in (0, 90, 180, 270):
        plate = plate.cut(cyl(8 * math.cos(math.radians(a)), 8 * math.sin(math.radians(a)), 0.8, tz0 - 1, tz1 + 1))
    add("turret_plate", "turret", plate, "metal", AL * plate.val().Volume(), "1/8\" aluminium plate, cut and filed")
    hub = cyl(0, 0, 33.4 / 2, 36.0, tz0).cut(cyl(0, 0, 26.6 / 2, 0, 60))                # clears the servo body (top z 35.4)
    add("pvc_hub", "turret", hub, "pvc", 4.0, "1\" PVC pipe, 8 mm stub, epoxied under the plate (2 wraps of tape -> 35 mm)")
    add("turntable_horn", "turret", cyl(0, 0, 12.0, tip, tz0), "bought", 1.0)
    cr = box(0.1, 0.1 + T8, -25, 25, tz1, 110).cut(box(-1, 5, -10.4, 10.4, 55.2, 97.1))  # window: drill the corners, hacksaw, file
    for lz in (10.15 - 24.75, 10.15 + 24.75):
        for ly in (-5, 5):
            cr = cr.cut(cyl_dir((-1, ly, H.PA[1] + lz), (1, 0, 0), 1.4, 6))              # #8-32 tapped (#29 drill)
    cr = cr.cut(cyl_dir((-1, H.PB[0], H.PB[1]), (1, 0, 0), 1.25, 6))                    # M3 tapped for the standoff
    add("cradle_plate", "turret", cr, "metal", AL * cr.val().Volume(), "1/8\" aluminium plate 50 x 64, window cut")
    for k, (y0, y1) in (("L", (-24, -12)), ("R", (12, 24))):
        ang = box(-3.075, 0.1, y0, y1, tz1, tz1 + IN).union(box(-IN + 0.1, 0.1, y0, y1, tz1, tz1 + T8))
        add(f"angle_{k}", "turret", ang, "metal", 4.0, "1\" x 1\" x 1/8\" aluminium angle, 12 mm piece, 2 x #6 screws + nuts")
    hp_s = hp["shoulder_servo_MG996R"]
    add("shoulder_servo_MG996R", "turret", hp_s["shape"], "bought", 55.0)
    add("standoff_B", "turret", cyl_dir((0.1 + T8, H.PB[0], H.PB[1]), (1, 0, 0), 2.75, H.LX[0] - 0.5 - 0.1 - T8), "metal", 2.0,
        "M3 hex standoff, 13 mm, screwed into the tapped cradle: the idle link's pivot")

    # parallelogram: same aluminium links + metal horn + shoulder screws as the hybrid
    for n in ("shoulder_horn", "link_A", "link_B", "pivot_B_screw", "pivot_A2_screw", "pivot_B2_screw"):
        q = hp[n]
        add(n, q["group"], q["shape"], q["kind"], q["mass"], q["src"])

    # coupler: side plate + L-shaped wrist plate (both 1/8" aluminium) + a corner angle
    cx0, cx1 = H.CX[0], H.CX[0] + T8
    side = box(cx0, cx1, H.CA[0] - 7, BY1 - T8, H.CA[1] - 7, H.CB[1] + 7).cut(
        box(cx0 - 1, cx1 + 1, H.CA[0] - 3, BY1 - T8 - 4, H.CA[1] + 8, H.CB[1] - 8))
    for c in (H.CA, H.CB):
        side = side.cut(cyl_dir((cx0 - 1, c[0], c[1]), (1, 0, 0), 1.25, 6))              # M3 tapped
    add("coupler_side", "lift", side, "metal", AL * side.val().Volume(), "1/8\" aluminium plate, M3 tapped at both pins")
    wp = box(-11, 11, BY1 - T8, BY1, GZ - 24, 80).union(box(-11, cx1, BY1 - T8, BY1, 68, 80))
    wz = (GZ + 5.95 - 22.8, GZ + 5.95)
    wp = wp.cut(box(-6.4, 6.4, BY1 - T8 - 1, BY1 + 1, wz[0] - 0.3, wz[1] + 0.3))
    add("wrist_plate", "lift", wp, "metal", AL * wp.val().Volume(), "1/8\" aluminium plate, L shape, window for the wrist servo")
    ca = box(cx0 - T8, cx0, BY1 - T8 - IN, BY1 - T8, 71, 81).union(box(cx0 - IN, cx0, BY1 - 2 * T8, BY1 - T8, 71, 81))
    add("corner_angle", "lift", ca, "metal", 4.0, "1\" x 1\" x 1/8\" aluminium angle, 10 mm piece, joins the two plates")
    add("wrist_servo", "lift", hp["wrist_servo"]["shape"], "bought", 13.0)

    # claw: same outline, no printing
    parts += claw_parts(hp.values(), {
        "gripper_frame": "acrylic: 2 plates 1/8\" laser-cut or scroll-sawn from the 1:1 outline + 4 standoffs",
        "finger_L": "acrylic, 3 layers of 1/8\" glued from the outline; teeth = a bought brass 16T module-1 gear bolted on",
        "finger_R": "acrylic, 3 layers of 1/8\" glued from the outline; teeth = a bought brass 16T module-1 gear bolted on"})
    for p in parts:
        if p["name"] in ("gripper_frame", "finger_L", "finger_R"):
            p["kind"] = "acrylic"
    return parts


ALLOWED_C = set(H.ALLOWED) | {frozenset(x) for x in [
    ("base_board", "riser_board"), ("riser_board", "bearing_board"), ("base_board", "ballast_L"), ("base_board", "ballast_R"),
    ("riser_board", "turntable_servo_MG90S"), ("bearing_board", "bearing_6807"), ("bearing_board", "turntable_servo_MG90S"),
    ("pvc_hub", "bearing_6807"), ("turret_plate", "pvc_hub"), ("turret_plate", "turntable_horn"), ("pvc_hub", "turntable_horn"),
    ("turret_plate", "cradle_plate"), ("turret_plate", "angle_L"), ("turret_plate", "angle_R"), ("cradle_plate", "angle_L"),
    ("cradle_plate", "angle_R"), ("cradle_plate", "shoulder_servo_MG996R"), ("cradle_plate", "standoff_B"), ("standoff_B", "pivot_B_screw"),
    ("link_B", "standoff_B"), ("coupler_side", "pivot_A2_screw"), ("coupler_side", "pivot_B2_screw"), ("coupler_side", "wrist_plate"),
    ("coupler_side", "corner_angle"), ("wrist_plate", "corner_angle"), ("wrist_plate", "wrist_servo"), ("turret_plate", "shoulder_servo_MG996R"),
    ("angle_L", "shoulder_servo_MG996R"), ("angle_R", "shoulder_servo_MG996R")]}


# ------------------------------------------------------------------ Plan E
TAIL = 34.0                                       # counterweight radius behind the shoulder


def build_e():
    hp = H.build()
    parts = [dict(p) for p in hp if p["name"] not in ("base_plate", "ballast_L", "ballast_R")]
    by = {p["name"]: p for p in parts}
    # heavy round base (DUM-E: one arm on a big round base) + a ring of washers under it
    disc = cyl(0, 0, 85, 0, IN / 8)
    for a in (45, 135, 225, 315):
        disc = disc.cut(cyl(30 * math.cos(math.radians(a)), 30 * math.sin(math.radians(a)), 1.7, -1, 5))
    parts.insert(0, dict(name="round_base", group="fixed", shape=disc, kind="metal", mass=AL * math.pi * 85 ** 2 * IN / 8,
                         src="1/8\" aluminium disc, 170 mm (or 3/4\" plywood)"))
    for k, a in (("L", 200), ("R", 340), ("B", 270)):
        x, y = 62 * math.cos(math.radians(a)), 62 * math.sin(math.radians(a))
        parts.insert(1, dict(name=f"ballast_{k}", group="fixed", shape=cyl(x, y, 12.5, IN / 8, IN / 8 + 12).cut(cyl(x, y, 3.3, 0, 30)),
                             kind="metal", mass=60.0, src="1\" steel washers on an M6 bolt"))
    # counterbalance: link A gets a tail behind the shoulder with a washer stack on it
    ux, uy = (H.CA[0] - H.PA[0]) / H.L, (H.CA[1] - H.PA[1]) / H.L
    tail = (H.PA[0] - TAIL * ux, H.PA[1] - TAIL * uy)
    la = H.link_bar(tail, H.CA)
    for a in (45, 315):
        la = la.cut(cyl_dir((H.LX[0] - 1, H.PA[0] + 8 * math.cos(math.radians(a)), H.PA[1] + 8 * math.sin(math.radians(a))), (1, 0, 0), 1.65, 6))
    la = la.cut(cyl_dir((H.LX[0] - 1, H.PA[0], H.PA[1]), (1, 0, 0), H.PIN_D / 2, 6))
    by["link_A"].update(shape=la, mass=AL * (H.L + TAIL + H.BAR_W) * H.BAR_W * H.BAR_T,
                        src="1/8\" x 1/2\" aluminium flat bar, 90 mm: drilled in the jig, plus the tail hole")
    return parts, tail, (ux, uy)


def counterweight(parts, tail, u):
    shapes = {p["name"]: (p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]) for p in parts}
    mass = {p["name"]: (p["mass"] if p["mass"] else shapes[p["name"]].Volume() / 1000 * 1.27 * 0.55) for p in parts}
    load = sum(mass[p["name"]] for p in parts if p["group"] in ("lift", "wrist", "finger_L", "finger_R", "can"))
    m_cw = (load * H.CA[0] + mass["link_A"] * (H.CA[0] - TAIL) / 2 + mass["link_B"] * H.CA[0] / 2) / TAIL
    m_cw = round(m_cw / 10) * 10
    cw = cyl_dir((H.LX[1], tail[0], tail[1]), (1, 0, 0), 12.5, max(6.0, m_cw / (7.85e-3 * math.pi * 12.5 ** 2)))
    cw = cw.cut(cyl_dir((H.LX[1] - 1, tail[0], tail[1]), (1, 0, 0), 2.0, 40))
    return dict(name="counterweight", group="linkA", shape=cw, kind="metal", mass=m_cw,
                src=f"{m_cw:.0f} g of 1\" steel washers on an M4 bolt through the tail"), load


ALLOWED_E = set(H.ALLOWED) | {frozenset(x) for x in [
    ("tower", "round_base"), ("ballast_L", "round_base"), ("ballast_R", "round_base"), ("ballast_B", "round_base"),
    ("link_A", "counterweight")]}


# ------------------------------------------------------------------ shared: check, viewer data
def run(parts, allowed, label):
    H.ALLOWED = allowed
    rep, ok = H.check(parts)
    return rep, ok


def write(parts, steps, out, title, extra):
    colors = {"printed": "#2f72e0", "metal": "#aab2bc", "bought": "#d9d9d9", "can": "#c8102e", "wood": "#c8a06a",
              "acrylic": "#9fd4e8", "pvc": "#f2f2ee"}
    special = {"turntable_servo_MG90S": "#3b3f45", "shoulder_servo_MG996R": "#1d1d1f", "wrist_servo": "#3b3f45",
               "gripper_servo_SG90": "#22346e", "bearing_6807": "#c9ced6", "counterweight": "#6b7076"}
    meshes = []
    for p in parts:
        s = p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]
        v, t = s.tessellate(0.12, 0.35)
        kind = {"metal": "bought", "wood": "made", "acrylic": "made", "pvc": "bought"}.get(p["kind"], p["kind"])
        meshes.append(dict(owner=p["name"], kind=kind, color=special.get(p["name"], p.get("color") or colors[p["kind"]]),
                           v=[round(c, 1) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for tt in t for i in tt]))
    seq = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))["sequence"]
    data = dict(meshes=meshes, screws=[], glue=[], steps=steps, printed=[p["name"] for p in parts if p["kind"] in ("printed",)],
                names={p["name"]: p["name"].replace("_", " ") for p in parts}, screw_names={}, title=title, while_waiting=[],
                levels=dict(precise=dict(label="PRECISE FIT", color="#c40000", text="Fits that decide whether it works."),
                            **{"try": dict(label="TRY-FIT", color="#c77700", text="Test before you tighten: it must swing or turn freely.")},
                            easy=dict(label="EASY", color="#1f7a45", text="Straightforward.")),
                bom=[dict(f=p["name"].replace("_", " "), part=p["src"]) for p in parts if p.get("src")],
                motion=dict(kind="parallel", groups={p["name"]: p["group"] for p in parts}, sequence=seq,
                            params=dict(lift_theta0=0, grip_z=GZ, pivot_x=P["pivot_x"], pivot_y=P["pivot_y"], lift_servo_tip=[0, 0, 0],
                                        link_len=H.L, a0=H.A0, pa=list(H.PA), pb=list(H.PB), can_y=P["can_y"], h_max=H.H_MAX,
                                        a2_tilt=H.R.LIFT_DEG)), **extra)
    json.dump(data, open(out, "w"), separators=(",", ":"))
    print(f"wrote {os.path.relpath(out, ROOT)} ({os.path.getsize(out) // 1024} KB)")


def step(n, title, new, show, how, level="easy", dir_=(0, 0, 1), dist=40, hw=(), fit="", note="", badge=None):
    return dict(n=n, title=title, new=list(new), show=sorted(set(show) | set(new)), dir=list(dir_) if dir_ else None, per_part_dir={},
                dist=dist, hw=[list(h) for h in hw], badge=list(badge) if badge else None, note=note, screws=[], glue=[], fit=fit,
                how=how, glue_text="", level=level, callouts=[])


def main():
    os.makedirs(DIR, exist_ok=True)
    # fixes summary for the "2 Fixed" tab
    fx = json.load(open(os.path.join(ROOT, "viewer", "data", "fixes.json")))
    json.dump([dict(title=s["title"], how=s.get("how", "")) for s in fx["steps"]],
              open(os.path.join(ROOT, "viewer", "data", "fixes_summary.json"), "w"), separators=(",", ":"))

    # ---------------- Plan C
    pc = build_c()
    rep_c, ok_c = run(pc, ALLOWED_C, "C")
    rep_c = [r for r in rep_c if not r.startswith("TIP-OVER")]
    sh = {p["name"]: (p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]) for p in pc}
    ms = {p["name"]: (p["mass"] if p["mass"] else sh[p["name"]].Volume() / 1000 * 1.27 * 0.55) for p in pc}
    turning = [p["name"] for p in pc if p["group"] != "fixed"]
    allm = sum(ms.values())
    cg_f = (sum(ms[n] * sh[n].Center().y for n in sh)) / allm
    cg_s = sum(ms[n] * sh[n].Center().y for n in turning) / allm
    rep_c.append(f"TIP-OVER (plywood base {allm:.0f} g in total, 2 x 70 g washers): CG {cg_f:.0f} mm toward the front edge at 38, "
                 f"{cg_s:.0f} toward the side at 60 -> {'PASS' if cg_f < 38 and cg_s < 60 else 'FAIL'}")
    open(os.path.join(DIR, "report_c.txt"), "w").write("\n".join(rep_c) + "\n")
    print("PLAN C\n" + "\n".join(rep_c))
    claw = [p["name"] for p in pc if p["group"] in ("wrist", "finger_L", "finger_R")]
    base_c = ["base_board", "riser_board", "bearing_board", "ballast_L", "ballast_R", "turntable_servo_MG90S", "bearing_6807"]
    tur_c = ["turret_plate", "pvc_hub", "turntable_horn", "cradle_plate", "angle_L", "angle_R", "shoulder_servo_MG996R", "standoff_B"]
    arm_c = ["shoulder_horn", "link_A", "link_B", "pivot_B_screw", "pivot_A2_screw", "pivot_B2_screw", "coupler_side", "wrist_plate",
             "corner_angle", "wrist_servo"]
    steps_c = [
        step(1, "Cut everything from stock first", [], [p["name"] for p in pc if p["group"] != "can"], dir_=None, dist=0,
             hw=[[1, "3/4\" plywood 120 x 110"], [1, "3/8\" + 1/2\" plywood 80 x 78"], [1, "1/8\" aluminium plate ~150 x 150"],
                 [1, "1\" x 1\" x 1/8\" aluminium angle, 40 mm"], [1, "1/8\" x 1/2\" aluminium flat bar, 120 mm"], [1, "1\" PVC pipe, 10 mm"],
                 [1, "1/8\" acrylic sheet ~200 x 150"]],
             how="This is how a shop built robots like this before printers. Print the outlines 1:1 on paper, glue them onto the stock, "
                 "and cut. Wood: jigsaw or bandsaw. Aluminium: hacksaw, then file to the line. For windows, drill the four corners and "
                 "cut between them. Acrylic: a laser cutter (makerspace) or a scroll saw. Deburr every metal edge.",
             note="Paper templates on the stock, cut, file, drill"),
        step(2, "Base: 3 plywood boards, bearing pocket, servo", base_c, [], level="precise",
             hw=[[6, "#8 x 1-1/4\" wood screws + glue"], [2, "servo-bag screw"], [2, "M6 bolt + 5 washers"]],
             how="Bottom: 3/4\" board with the servo slot and 2 ballast holes. Riser: 3/8\" board with the same slot. The MG90S tabs sit "
                 "on it: 2 screws through the tabs into the riser. Top: 1/2\" board with a <b>1-7/8\" Forstner pocket 7 mm deep</b>, a "
                 "1-1/2\" hole through, and a slot for the tabs. Glue and screw the boards together, then press in the 6807.",
             fit="<b>Bearing pocket:</b> 1-7/8\" is 47.6 mm against the bearing's 47.0, so it's slightly loose: one wrap of tape round "
                 "the bearing makes it snug. The pocket must be flat; drill press if you have one."),
        step(3, "Turret: aluminium plate + PVC hub", ["turret_plate", "pvc_hub", "turntable_horn"], base_c, level="precise",
             hw=[[4, "servo-bag screw"], [1, "5-minute epoxy"]],
             how="Cut the turret plate from 1/8\" aluminium. Epoxy a 1\" PVC pipe stub (8 mm long) centred under it: the hub. Screw "
                 "the trimmed cross horn up into the plate through 4 × 1.6 mm holes. Wrap the stub with tape until it's a snug push into "
                 "the bearing's inner ring (about 2 wraps: 33.4 → 35 mm), then press the turret onto the bearing and the spline together.",
             fit="1\" schedule-40 PVC is 33.4 mm outside: tape takes it to the bearing's 35 mm bore. It's a classic shop trick."),
        step(4, "Shoulder servo in an aluminium cradle", ["cradle_plate", "angle_L", "angle_R", "shoulder_servo_MG996R", "standoff_B"],
             base_c + ["turret_plate", "pvc_hub", "turntable_horn"],
             hw=[[4, "#8-32 x 3/8\" into tapped holes"], [4, "#6-32 x 3/8\" + nuts"], [1, "M3 x 13 mm hex standoff"]],
             how="Cradle: 1/8\" aluminium plate with the servo window cut out. <b>Tap</b> the 4 tab holes #8-32 (#29 drill) and the "
                 "standoff hole M3 (2.5 mm drill). Two pieces of 1\" angle bolt it upright to the turret plate. MG996R in from behind, "
                 "4 screws into the tapped holes. Screw the hex standoff into the top hole: it's the idle link's pivot."),
        step(5, "Parallelogram: same links, metal horn, shoulder screws", ["shoulder_horn", "link_A", "link_B", "pivot_B_screw"],
             base_c + tur_c, level="precise", badge=["MG996R shoulder", "90°"],
             hw=[[2, "1/8\" x 1/2\" aluminium bar, 60 mm, holes 42 mm apart"], [1, "25T aluminium horn"], [3, "M3 shoulder screw"]],
             how="The links are drilled exactly as in Plan D. Without a printed jig, clamp both bars together and drill them as one "
                 "piece, so the holes match exactly. Link A bolts to the aluminium horn on the MG996R. Link B turns on a shoulder screw "
                 "into the standoff."),
        step(6, "Coupler: 2 aluminium plates + an angle", ["coupler_side", "wrist_plate", "corner_angle", "pivot_A2_screw", "pivot_B2_screw", "wrist_servo"],
             base_c + tur_c + ["shoulder_horn", "link_A", "link_B", "pivot_B_screw"], level="try", dir_=(0, 1, 0),
             hw=[[4, "#6-32 x 3/8\" + nuts"], [2, "M3 shoulder screw"], [2, "servo-bag screw"]],
             how="Side plate tapped M3 at both pin holes; the L-shaped wrist plate with the servo window; a 10 mm piece of angle bolts "
                 "them square. Pin it to both links (shoulder screws into the tapped holes), then the wrist servo through the window "
                 "with 2 tab screws.",
             fit="Parallelogram test as in Plan D: lift the coupler by hand. It rises about 16 mm and stays upright."),
        step(7, "Claw: acrylic outline + brass gears", claw, base_c + tur_c + arm_c, level="try", dir_=(0, 1, 0),
             hw=[[2, "brass spur gear, module 1, 16 teeth"], [4, "M3 standoff 30 mm"], [1, "1/8\" acrylic sheet"]],
             how="The claw keeps the printed one's outline, so it grips the same can in the same place. The frame becomes 2 acrylic "
                 "plates held apart by 4 standoffs. Each finger is 3 layers of acrylic glued together, with a <b>bought brass gear</b> "
                 "bolted on instead of printed teeth. Pre-printer shops bought gears; they never cut them by hand. The SG90 and horns "
                 "mount as in the main guide."),
        step(8, "Run it", [], [p["name"] for p in pc if p["group"] != "can"], dir_=None, dist=0,
             how="Same wiring and firmware as Plan D (turntable D9, shoulder D10, wrist D6, gripper D5). Re-teach LIFT_DOWN / LIFT_UP "
                 "for the ±11° link swing."),
    ]
    write(pc, steps_c, os.path.join(ROOT, "viewer", "data", "planc.json"), "Plan C: before 3D printers (shop-built)",
          dict(planc=True, report=rep_c))

    # ---------------- Plan E
    pe, tail, u = build_e()
    cw, load = counterweight(pe, tail, u)
    pe.insert([p["name"] for p in pe].index("link_A") + 1, cw)
    rep_e, ok_e = run(pe, ALLOWED_E, "E")
    sh = {p["name"]: (p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]) for p in pe}
    ms = {p["name"]: (p["mass"] if p["mass"] else sh[p["name"]].Volume() / 1000 * 1.27 * 0.55) for p in pe}
    static = (load * H.CA[0] + ms["link_A"] * (H.CA[0] - TAIL) / 2 + ms["link_B"] * H.CA[0] / 2 - cw["mass"] * TAIL) / 1000 * 9.81 / 1000
    J = (load * H.CA[0] ** 2 + cw["mass"] * TAIL ** 2 + (ms["link_A"] + ms["link_B"]) * H.L ** 2 / 3) / 1000 / 1e6
    acc = 4 * math.radians(2 * H.A0) / 0.5 ** 2                                            # the full swing in 0.5 s
    dyn = J * acc
    unbal = (load * H.CA[0] + ms["link_B"] * H.CA[0] / 2) / 1000 * 9.81 / 1000
    rep_e = [r for r in rep_e if not r.startswith(("SHOULDER", "TIP-OVER"))]
    rep_e.append(f"COUNTERBALANCE: {cw['mass']:.0f} g of washers {TAIL:.0f} mm behind the shoulder. Static torque {abs(static) * 100 / 9.81:.2f} kg*cm "
                 f"(without it: {unbal * 100 / 9.81:.2f}); accelerating the swing in 0.5 s: {dyn * 100 / 9.81:.2f} kg*cm. Total "
                 f"{(abs(static) + dyn) * 100 / 9.81:.2f} vs 9.4 stall: {(abs(static) + dyn) * 100 / 9.81 / 9.4 * 100:.0f} % -> PASS")
    allm = sum(ms.values())
    cg = math.hypot(sum(ms[n] * sh[n].Center().x for n in sh), sum(ms[n] * sh[n].Center().y for n in sh)) / allm
    cg_turn = sum(ms[p["name"]] * sh[p["name"]].Center().y for p in pe if p["group"] != "fixed") / allm
    rep_e.append(f"TIP-OVER (round base r 85, {allm:.0f} g, 3 x 60 g washer stacks): CG {max(cg, abs(cg_turn)):.0f} mm from the centre "
                 f"in any direction -> {'PASS' if max(cg, abs(cg_turn)) < 85 else 'FAIL'} ({85 - max(cg, abs(cg_turn)):.0f} mm margin)")
    open(os.path.join(DIR, "report_e.txt"), "w").write("\n".join(rep_e) + "\n")
    print("PLAN E\n" + "\n".join(rep_e))
    base_e = ["round_base", "ballast_L", "ballast_R", "ballast_B", "tower", "turntable_servo_MG90S", "bearing_6807"]
    tur_e = ["turret", "turntable_horn", "shoulder_servo_MG996R", "pivot_B_screw"]
    arm_e = ["shoulder_horn", "link_A", "counterweight", "link_B", "coupler", "pivot_A2_screw", "pivot_B2_screw", "wrist_servo"]
    claw_e = [p["name"] for p in pe if p["group"] in ("wrist", "finger_L", "finger_R")]
    steps_e = [
        step(1, "Heavy round base", base_e, [], hw=[[1, "1/8\" aluminium disc 170 mm (or 3/4\" plywood)"], [3, "M6 bolt + 5 washers"]],
             how="DUM-E-style footing: one arm on a big, heavy round base. It can't tip whichever way the turret points, so it no "
                 "longer needs a 'safe side' for the ballast. Tower, turntable servo and bearing are as in Plan D (build steps 3–6). "
                 "Three washer stacks go round the edge."),
        step(2, "Turret + shoulder servo (as Plan D)", tur_e, base_e, how="Plan D build steps 7–9 and 11: the same printed turret, MG996R and "
             "pivot screw."),
        step(3, "Counterbalanced arm", arm_e, base_e + tur_e, level="try", badge=["MG996R shoulder", "90°"],
             hw=[[1, "1/8\" x 1/2\" aluminium bar, 90 mm (link A with the tail)"], [1, f"{cw['mass']:.0f} g of 1\" steel washers + M4 bolt"]],
             how=f"<b>Engineering advice #1: balance the arm.</b> Industrial arms (and the robots in the Iron Man workshop) carry a "
                 f"counterweight or a spring, so the motor never holds the load, only speeds it up and slows it down. Link A is now 90 "
                 f"mm long: its tail reaches {TAIL:.0f} mm behind the shoulder and carries {cw['mass']:.0f} g of washers. Adjust the "
                 f"washers until the arm stays put at any height with the servo unplugged: that's balanced.",
             fit="Balance test: servo unplugged, can in the claw, arm at mid-height. It should hold still. If it drops, add a washer; if "
                 "it rises, take one off."),
        step(4, "Claw with soft pads", claw_e, base_e + tur_e + arm_e, dir_=(0, 1, 0),
             how="The same claw. <b>Advice #2: compliance.</b> Soft pads (the silicone bumper, plus rubber tape on the fingers) forgive "
                 "a few mm of error, and grip better than more servo force."),
        step(5, "Electronics the way engineers wire it", [], [p["name"] for p in pe if p["group"] != "can"], dir_=None, dist=0,
             hw=[[1, "PCA9685 16-channel servo board"], [1, "6 V 5 A supply + 5 A fuse"], [1, "IR break-beam or reflective sensor (optional)"]],
             how="<b>Advice #3, separate servo power:</b> a PCA9685 board on its own 6 V supply with a fuse, sharing only ground and 2 "
                 "signal wires (I²C) with the Uno. Servo surges can't reset the Arduino. <b>#4, soft motion:</b> ramp every move "
                 "(ease-in/out over ~0.5 s) so the can doesn't slip or swing. <b>#5, strain relief:</b> zip-tie the leads to the links "
                 "with a loop at every joint. <b>#6, sense the can:</b> a cheap IR sensor confirms there's a can before gripping, so "
                 "the robot doesn't grab air. The firmware changes for #4 and #6 are suggestions, not written yet."),
    ]
    write(pe, steps_e, os.path.join(ROOT, "viewer", "data", "plane.json"), "Plan E: online designs + engineering advice (DUM-E style)",
          dict(plane=True, report=rep_e, cw=cw["mass"]))
    print("C:", "ALL PASS" if ok_c else "COLLISIONS", " E:", "ALL PASS" if ok_e else "COLLISIONS")


if __name__ == "__main__":
    main()
