"""Engineering checks for Concept A: physics, strength, stability and power of every mechanism.

    python3.13 backend/mech/mech_checks.py        (needs cadquery, numpy, matplotlib; ~1 min)

Uses the real CAD solids (mass, centre of gravity, inertia tensor of every part) and the firmware's
real move times and eased (minimum-jerk) profiles. Every result is compared with a stated limit
and marked PASS / FAIL. Writes cad/check/mech_report.txt and cad/check/mech_*.png.

Material / component values marked EST are typical datasheet values, not measurements.
"""
import csv
import math
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt, gp_Trsf, gp_Ax1, gp_Dir

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import model as M  # noqa: E402
import check as C  # noqa: E402  (support-footprint hull helpers)

OUT = os.path.join(ROOT, "cad", "check")
G = 9.81
P = M.P
FW = M.FW

# ------------------------------------------------------------------ material and component data (EST)
PETG = dict(E=2.0e3, sigma_allow=20.0, tau_allow=10.0, sigma_uts=50.0)   # MPa: printed PETG, allowable = UTS/2.5
STEEL = dict(E=200e3, sigma_allow=200.0)
MU_PAD = 0.5          # silicone pad on the aluminium can (EST, conservative; 0.6-1.0 typical)
MU_FEET = 0.5         # rubber feet on a table (EST)
MU_LM = 0.005         # LM6UU rolling friction coefficient (EST)
SERVO = {             # stall torque N*m and no-load speed deg/s at 4.8 V (conservative: they run at 5.8 V)
    "turn": dict(name="MG996R", stall=9.4 * 0.0981, speed=60 / 0.17),
    "lift": dict(name="MG90S", stall=1.8 * 0.0981, speed=60 / 0.10),
    "wrist": dict(name="MG90S", stall=1.8 * 0.0981, speed=60 / 0.10),
    "grip": dict(name="SG90", stall=1.6 * 0.0981, speed=60 / 0.10),
}
LIMIT_TORQUE = 0.5    # PASS if demand <= 50 % of the torque available at that speed (2x margin)
LIMIT_SPEED = 0.7     # PASS if peak speed <= 70 % of no-load speed

results = []          # (area, item, value, limit, pass)
lines = []


def check(area, item, value, limit, ok):
    results.append((area, item, value, limit, "PASS" if ok else "FAIL"))


def out(s=""):
    lines.append(s)


# ------------------------------------------------------------------ firmware timing
src = open(os.path.join(ROOT, "firmware", "concept_a", "concept_a.ino")).read()
tl = src.split("const unsigned long T_GRIP")[1].split(";")[0]
T = {"T_GRIP": float(re.search(r"= (\d+)", tl).group(1)) / 1000}
for k, v in re.findall(r"(T_\w+) = (\d+)", tl):
    T[k] = int(v) / 1000
STEPS = [  # (label, servo, from, to, seconds, can attached)
    ("GRIP", "grip", FW["GRIP_OPEN"], FW["GRIP_CLOSED"], T["T_GRIP"], False),
    ("LIFT", "lift", FW["LIFT_DOWN"], FW["LIFT_UP"], T["T_LIFT"], True),
    ("FLIP", "wrist", FW["WRIST_UP"], FW["WRIST_FLIP"], T["T_FLIP"], True),
    ("TURN", "turn", FW["TURN_START"], FW["TURN_TARGET"], T["T_TURN"], True),
    ("LOWER", "lift", FW["LIFT_UP"], FW["LIFT_DOWN"], T["T_LIFT"], True),
    ("RELEASE", "grip", FW["GRIP_CLOSED"], FW["GRIP_RELEASE"], T["T_RELEASE"], False),
    ("H-LIFT", "lift", FW["LIFT_DOWN"], FW["LIFT_UP"], T["T_LIFT"], False),
    ("H-CLOSE", "grip", FW["GRIP_RELEASE"], FW["GRIP_CLOSED"], T["T_GRIP"], False),
    ("H-WRIST", "wrist", FW["WRIST_FLIP"], FW["WRIST_UP"], T["T_FLIP"], False),
    ("H-TURN", "turn", FW["TURN_TARGET"], FW["TURN_START"], T["T_TURN"], False),
    ("H-LOWER", "lift", FW["LIFT_UP"], FW["LIFT_DOWN"], T["T_LIFT"], False),
    ("H-OPEN", "grip", FW["GRIP_CLOSED"], FW["GRIP_OPEN"], T["T_GRIP"], False),
]


def mj(s):      # minimum-jerk position, velocity, acceleration (normalised)
    s = np.clip(s, 0, 1)
    return s ** 3 * (10 - 15 * s + 6 * s * s), 30 * s * s * (1 - s) ** 2, 60 * s * (1 - s) * (1 - 2 * s)


# ------------------------------------------------------------------ exact lift slider-crank
lty, ltz = P["lift_servo_tip"][1], P["lift_servo_tip"][2]
Rc = P["lift_crank"]
piv = (12.0, P["car_z1"] + 2.0)                         # link pivot on the carriage (y, z at home)


def pin(th_deg):
    t = math.radians(th_deg)
    return lty + Rc * math.cos(t), ltz + Rc * math.sin(t)


L_LINK = math.dist(pin(P["lift_theta0"]), piv)


def h_exact(th_deg):
    py_, pz_ = pin(th_deg)
    z = pz_ - math.sqrt(L_LINK ** 2 - (py_ - piv[0]) ** 2)
    py0, pz0 = pin(P["lift_theta0"])
    return z - (pz0 - math.sqrt(L_LINK ** 2 - (py0 - piv[0]) ** 2))


def link_tilt(th_deg):
    py_, _ = pin(th_deg)
    return math.degrees(math.asin((py_ - piv[0]) / L_LINK))


def lift_theta(cmd):
    return P["lift_theta0"] + (cmd - FW["LIFT_DOWN"]) * P["lift_span"] / (FW["LIFT_UP"] - FW["LIFT_DOWN"])


def joints(turn, lift, wrist, grip):
    j = M.joints_from_commands(turn, lift, wrist, grip)
    j["h"] = h_exact(j["theta"])                         # exact slider-crank instead of the model's approximation
    return j


# ------------------------------------------------------------------ parts: mass, CG, inertia
parts = [p for p in M.build_parts() if p["group"] != "coupon"]
mass, vol, cg_local, Icg = {}, {}, {}, {}
for p in parts:
    sh = p["shape"].val()
    gp = GProp_GProps()
    BRepGProp.VolumeProperties_s(sh.wrapped, gp)
    v = gp.Mass()                                         # mm^3
    if p["material"] in ("PETG", "silicone"):
        m = v / 1000 * (1.27 if p["material"] == "PETG" else 1.21) * P["print_fill"]
    else:
        m = p["mass"] or 0.0
    mass[p["name"]] = m / 1000.0                          # kg
    vol[p["name"]] = v
    c = gp.CentreOfMass()
    cg_local[p["name"]] = np.array([c.X(), c.Y(), c.Z()]) / 1000.0   # m
    I = gp.MatrixOfInertia()                              # about the CG, unit density, mm^5
    rho = mass[p["name"]] / v if v > 0 else 0.0           # kg / mm^3
    Icg[p["name"]] = np.array([[I.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]) * rho * 1e-6   # kg m^2
group_of = {p["name"]: p["group"] for p in parts}


def trsf_np(t):
    R = np.array([[t.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    tr = np.array([t.Value(i, 4) for i in (1, 2, 3)]) / 1000.0
    return R, tr


def pose_mats(j, can_attached):
    Tg = M.group_transforms(j)
    mats = {g: trsf_np(t) for g, t in Tg.items()}
    mats["can"] = mats["wrist"] if can_attached else (np.eye(3), np.zeros(3))   # can gripped at the HOME wrist pose
    return mats


def world_cg(name, mats):
    R, tr = mats[group_of[name]]
    return R @ cg_local[name] + tr


def inertia_about(names, mats, point, axis):
    """Moment of inertia (kg m^2) of the named parts about the line through point (m) along axis."""
    u = np.array(axis, float) / np.linalg.norm(axis)
    J = 0.0
    for n in names:
        R, _ = mats[group_of[n]]
        Iw = R @ Icg[n] @ R.T
        c = world_cg(n, mats)
        d = c - point
        d_perp = d - u * (d @ u)
        J += u @ Iw @ u + mass[n] * (d_perp @ d_perp)
    return J


TURRET_SET = [n for n, g in group_of.items() if g in ("turret", "crank", "lift", "wrist", "finger_L", "finger_R")]
LIFT_SET = [n for n, g in group_of.items() if g in ("lift", "wrist", "finger_L", "finger_R")]
WRIST_SET = [n for n, g in group_of.items() if g in ("wrist", "finger_L", "finger_R")]
CAN = "test_can"

# ------------------------------------------------------------------ 1. servo duty (inverse dynamics along the run)
out("1. SERVO DUTY: inverse dynamics along the firmware's eased moves (ratings at 4.8 V: conservative)")
N = 300
duty = {k: dict(t=[], tau=[], w=[], avail=[]) for k in SERVO}
t_run = 0.0
can_state = {"attached": False}
step_peaks = []
squeeze_hold = 2 * 0.8 * 0.044                            # N*m at the gripper servo, 0.8 N per arm design squeeze
for label, sv, a0, a1, secs, attached in STEPS:
    s = np.linspace(0, 1, N)
    pos, vel, acc = mj(s)
    th = a0 + (a1 - a0) * pos                              # servo angle, deg
    w = (a1 - a0) * vel / secs                             # deg/s
    al = math.radians(a1 - a0) * acc / secs ** 2           # rad/s^2
    cmd = dict(turn=FW["TURN_START"], lift=FW["LIFT_DOWN"], wrist=FW["WRIST_UP"], grip=FW["GRIP_OPEN"])
    # pose context of each step (what the other joints are doing)
    ctx = {"GRIP": {}, "LIFT": dict(grip=95), "FLIP": dict(grip=95, lift=75), "TURN": dict(grip=95, lift=75, wrist=180),
           "LOWER": dict(grip=95, wrist=180, turn=45), "RELEASE": dict(wrist=180, turn=45),
           "H-LIFT": dict(grip=70, wrist=180, turn=45), "H-CLOSE": dict(lift=75, wrist=180, turn=45),
           "H-WRIST": dict(grip=95, lift=75, turn=45), "H-TURN": dict(grip=95, lift=75), "H-LOWER": dict(grip=95),
           "H-OPEN": {}}[label]
    cmd.update(ctx)
    tau = np.zeros(N)
    if sv == "turn":
        names = TURRET_SET + ([CAN] if attached else [])
        cmd["turn"] = (a0 + a1) / 2
        mats = pose_mats(joints(**cmd), attached)
        J = inertia_about(names, mats, np.zeros(3), (0, 0, 1))
        w_axial = sum(mass[n] for n in names) * G
        fric = 0.0015 * w_axial * 0.0205 + 0.002          # bearing rolling (mu 0.0015 at r 20.5 mm) + 2RS seal drag (EST)
        tau = J * al + np.sign(w + 1e-12) * fric
        extra = f"J = {J * 1e4:.2f} kg·cm²"
    elif sv == "lift":
        names = LIFT_SET + ([CAN] if attached else [])
        m = sum(mass[n] for n in names)
        thc = lift_theta(th)
        h = np.array([h_exact(x) for x in thc]) / 1000
        dh = np.gradient(h, np.radians(thc)) if abs(a1 - a0) > 0 else np.zeros(N)   # m per rad of crank
        hdd = np.gradient(np.gradient(h, s * secs), s * secs)
        mats = pose_mats(joints(**cmd), attached)
        cgy = sum(mass[n] * world_cg(n, mats)[1] for n in names) / m
        e = cgy - P["rod_y"] / 1000                       # CG offset in front of the rods (m)
        span = (P["car_h"] - P["lm_len"]) / 1000          # bushing pair spacing
        f_fric = MU_LM * 2 * (m * G * e / span)
        F = m * (G + hdd) + np.sign(w + 1e-12) * f_fric
        tau = F * dh
        extra = f"moving mass {m * 1000:.0f} g, CG {e * 1000:.0f} mm in front of the rods"
    elif sv == "wrist":
        names = WRIST_SET + ([CAN] if attached else [])
        cmd["wrist"] = 0
        mats0 = pose_mats(joints(**cmd), attached)
        axis_pt = np.array([0, 0, (P["grip_z"] + h_exact(lift_theta(cmd["lift"])))]) / 1000
        J = inertia_about(names, mats0, axis_pt, (0, 1, 0))
        m = sum(mass[n] for n in names)
        cgw = sum(mass[n] * world_cg(n, mats0) for n in names) / m - axis_pt
        phi = np.radians(th)
        tg = m * G * (cgw[0] * np.cos(phi) + cgw[2] * np.sin(phi))
        tau = J * al + tg
        extra = f"J = {J * 1e4:.3f} kg·cm², CG {math.hypot(cgw[0], cgw[2]) * 1000:.1f} mm off the roll axis"
    else:  # grip
        mats0 = pose_mats(joints(**cmd), False)
        J = sum(inertia_about([f], mats0, np.array([sx * P["pivot_x"], P["pivot_y"], 0]) / 1000, (0, 0, 1))
                for f, sx in (("finger_L", -1), ("finger_R", 1)))
        tau = J * al
        if label == "GRIP":                               # pads reach the can at the end of GRIP and start to squeeze
            tau = tau.copy()
            tau[-N // 6:] += squeeze_hold * np.linspace(0, 1, N // 6 if N // 6 else 1)[:len(tau[-N // 6:])]
        extra = f"J (both arms, 1:1 gears) = {J * 1e7:.2f} kg·mm²"
    sd = SERVO[sv]
    avail = sd["stall"] * np.clip(1 - np.abs(w) / sd["speed"], 0, 1)
    ratio = np.max(np.abs(tau) / np.maximum(avail, 1e-9))
    duty[sv]["t"] += list(t_run + s * secs)
    duty[sv]["tau"] += list(np.abs(tau))
    duty[sv]["w"] += list(np.abs(w))
    duty[sv]["avail"] += list(avail)
    for k in SERVO:
        if k != sv:
            duty[k]["t"] += [t_run, t_run + secs]
            hold = squeeze_hold if (k == "grip" and attached) else 0.0
            duty[k]["tau"] += [hold, hold]
            duty[k]["w"] += [0, 0]
            duty[k]["avail"] += [SERVO[k]["stall"]] * 2
    t_run += secs
    pk_tau, pk_w = np.max(np.abs(tau)), np.max(np.abs(w))
    step_peaks.append((label, sd["name"], pk_tau, pk_w, ratio))
    out(f"   {label:8s} {sd['name']:6s} peak torque {pk_tau * 1000:7.2f} N·mm ({pk_tau / sd['stall']:5.1%} of stall), "
        f"peak speed {pk_w:6.1f} °/s ({pk_w / sd['speed']:5.1%}), worst torque/available {ratio:5.1%}   [{extra}]")
by_servo = {}
for (label, sv, *_), pk in zip(STEPS, step_peaks):
    by_servo.setdefault(sv, []).append(pk)
worst_ratio = {}
for sv, lst in by_servo.items():
    worst = max(x[4] for x in lst)
    worst_ratio[sv] = worst
    wmax = max(x[3] for x in lst)
    check("Servos", f"{SERVO[sv]['name']} ({sv}): torque demand / torque available", f"{worst:.1%}", f"≤ {LIMIT_TORQUE:.0%}", worst <= LIMIT_TORQUE)
    check("Servos", f"{SERVO[sv]['name']} ({sv}): peak speed / no-load speed", f"{wmax / SERVO[sv]['speed']:.1%}", f"≤ {LIMIT_SPEED:.0%}", wmax / SERVO[sv]["speed"] <= LIMIT_SPEED)
grip_hold_frac = squeeze_hold / SERVO["grip"]["stall"]
check("Servos", "SG90 holding torque at 0.8 N/arm squeeze", f"{grip_hold_frac:.0%} of stall", "≤ 60 %", grip_hold_frac <= 0.6)
out(f"   gripper hold: 2 × 0.8 N × 44 mm = {squeeze_hold * 1000:.1f} N·mm = {grip_hold_frac:.0%} of SG90 stall")
out("")

# ------------------------------------------------------------------ 2. lift mechanism
out("2. LIFT MECHANISM: crank + link (exact slider-crank)")
ths = np.linspace(P["lift_theta0"], P["lift_theta0"] + P["lift_span"], 91)
hx = np.array([h_exact(x) for x in ths])
hm = np.array([P["lift_crank"] * (math.sin(math.radians(x)) - math.sin(math.radians(P["lift_theta0"]))) for x in ths])
tilt = np.array([link_tilt(x) for x in ths])
out(f"   link length {L_LINK:.2f} mm; stroke exact {hx[-1]:.2f} mm (model {hm[-1]:.2f}); max difference mid-stroke {np.max(np.abs(hx - hm)):.2f} mm")
out(f"   link tilt from vertical: {tilt.min():.1f}° … {tilt.max():.1f}°  (force transmission cos = {math.cos(math.radians(np.max(np.abs(tilt)))):.3f})")
check("Lift", "stroke (exact slider-crank)", f"{hx[-1]:.2f} mm", "≥ 15.2 mm (0.6 in)", hx[-1] >= 15.2)
check("Lift", "link angle (transmission; toggle at 90°)", f"{np.max(np.abs(tilt)):.1f}°", "≤ 30°", np.max(np.abs(tilt)) <= 30)
check("Lift", "model vs exact lift height", f"{np.max(np.abs(hx - hm)):.2f} mm", "≤ 0.5 mm", np.max(np.abs(hx - hm)) <= 0.5)
# link clearance in its real (tilted) pose against the spine, top cap, lift servo and carriage (except its pivot)
by_name = {p["name"]: p for p in parts}
link_local = by_name["lift_link"]["shape"].val()
neighbours = ["spine", "top_cap", "lift_servo_MG90S", "rod_L", "rod_R"]
min_clear = 1e9
for x in np.linspace(P["lift_theta0"], P["lift_theta0"] + P["lift_span"], 13):
    hh = h_exact(x)
    t1 = gp_Trsf(); t1.SetTranslation(cq.Vector(0, 0, hh).wrapped)               # carriage moves up hh
    t2 = gp_Trsf(); t2.SetRotation(gp_Ax1(gp_Pnt(0, piv[0], piv[1] + hh), gp_Dir(1, 0, 0)), -math.radians(link_tilt(x) - link_tilt(P["lift_theta0"])))
    lk = link_local.moved(cq.Location(t1)).moved(cq.Location(t2))
    for n in neighbours:
        d = BRepExtrema_DistShapeShape(lk.wrapped, by_name[n]["shape"].val().wrapped)
        d.Perform()
        min_clear = min(min_clear, d.Value())
out(f"   link in its real tilted pose: min clearance to spine / top cap / lift servo / rods = {min_clear:.2f} mm")
check("Lift", "link clearance in its real tilted pose", f"{min_clear:.2f} mm", "≥ 0.5 mm", min_clear >= 0.5)
out("")

# ------------------------------------------------------------------ 3. gears
out("3. CLAW GEARS: 16T, module 1, 20°, profile shift +0.1 each, 0.2 mm backlash")
z, m_, pa, xs, thin = P["gear_z"], P["gear_m"], math.radians(P["gear_pa"]), P["gear_x"], P["gear_thin"]
r = m_ * z / 2
rb = r * math.cos(pa)
ra = r + m_ * (1 + xs)
rf = r - m_ * (1.25 - xs)
inv = lambda a: math.tan(a) - a
inv_w = 2 * (2 * xs) * math.tan(pa) / (2 * z) + inv(pa)
aw = pa
for _ in range(50):                                        # solve inv(aw) = inv_w
    aw -= (inv(aw) - inv_w) / (math.tan(aw) ** 2)
a_work = 2 * r * math.cos(pa) / math.cos(aw)
cd = 2 * P["pivot_x"]
eps = (2 * math.sqrt(ra ** 2 - rb ** 2) - cd * math.sin(aw)) / (math.pi * m_ * math.cos(pa))
x_min = (17 - z) / 17
_, ginfo = M.involute_gear(0, 0, 0, 1, 0)
tip_s = ginfo["tip_thickness"]
clearance_root = cd - ra - rf
out(f"   pitch r {r}, base r {rb:.3f}, tip r {ra:.2f}, root r {rf:.2f} mm; working pressure angle {math.degrees(aw):.2f}°")
out(f"   centre distance for zero backlash {a_work:.3f} mm vs pivots {cd:.3f} mm; contact ratio {eps:.2f}; tip thickness {tip_s:.2f} mm")
check("Gears", "contact ratio (smooth, continuous mesh)", f"{eps:.2f}", "≥ 1.2", eps >= 1.2)
check("Gears", "profile shift vs undercut limit (17-z)/17", f"x = {xs} vs {x_min:.3f}", "x ≥ limit", xs >= x_min)
check("Gears", "centre distance matches shifted gears", f"{cd - a_work:+.3f} mm", "|Δ| ≤ 0.05 mm", abs(cd - a_work) <= 0.05)
check("Gears", "tip thickness (printable, not pointed)", f"{tip_s:.2f} mm", "≥ 0.4 mm (nozzle)", tip_s >= 0.4)
check("Gears", "root clearance", f"{clearance_root:.2f} mm", "≥ 0.2 mm", clearance_root >= 0.2)
fL, fR = by_name["finger_L"]["shape"].val(), by_name["finger_R"]["shape"].val()
ov, gaps = 0.0, []
for k in range(0, 31):
    al_ = 75 * k / 30
    Tg = M.group_transforms(M.joints_from_commands(135, 30, 0, 95 - al_))
    Lg, Rg = fL.moved(cq.Location(Tg["finger_L"])), fR.moved(cq.Location(Tg["finger_R"]))
    ov = max(ov, Lg.intersect(Rg).Volume())
    d = BRepExtrema_DistShapeShape(Lg.wrapped, Rg.wrapped); d.Perform(); gaps.append(d.Value())
out(f"   CAD mesh over 0–75° (31 poses): max overlap {ov:.4f} mm³; flank gap {min(gaps):.3f}–{max(gaps):.3f} mm (constant = true involute)")
check("Gears", "teeth never overlap over the full 75° travel (CAD)", f"{ov:.4f} mm³", "0", ov < 1e-3)
check("Gears", "running clearance between flanks (CAD)", f"{min(gaps):.3f} mm", "0.05–0.3 mm", 0.05 <= min(gaps) <= 0.3)
# Lewis bending: worst case = the SG90's full stall torque goes through the mesh
Y_lewis = 0.296 + 0.6 * xs * 0.1                          # 16T Lewis form factor (20°), slightly raised by +x (EST)
Ft = SERVO["grip"]["stall"] / (r / 1000)                   # N at the pitch circle
b = P["finger_z"][1] - P["finger_z"][0]
sig_t = Ft / (b * m_ * Y_lewis)
out(f"   Lewis: worst case full SG90 stall through the mesh, Ft = {Ft:.1f} N → σ = {sig_t:.1f} MPa (face {b} mm, Y {Y_lewis:.3f})")
check("Strength", "gear tooth bending at SG90 stall (Lewis)", f"{sig_t:.1f} MPa", f"≤ {PETG['sigma_allow']} MPa", sig_t <= PETG["sigma_allow"])
out("")

# ------------------------------------------------------------------ 4. the can: grip, landing, standing
out("4. THE CAN: friction needed through every acceleration, landing, standing inverted")
m_can = mass[CAN]
cg_can_local = cg_local[CAN]
dt = 0.002
f_need = []
times = []
t0 = 0.0
for label, sv, a0, a1, secs, attached in STEPS[1:5]:     # LIFT, FLIP, TURN, LOWER: can held
    ctx = {"LIFT": dict(grip=95), "FLIP": dict(grip=95, lift=75), "TURN": dict(grip=95, lift=75, wrist=180),
           "LOWER": dict(grip=95, wrist=180, turn=45)}[label]
    ts = np.arange(-2 * dt, secs + 3 * dt, dt)
    P_w, R_w = [], []
    for t in ts:
        p_, _, _ = mj(np.array([t / secs]))
        c = dict(turn=FW["TURN_START"], lift=FW["LIFT_DOWN"], wrist=FW["WRIST_UP"], grip=FW["GRIP_OPEN"])
        c.update(ctx)
        c[{"turn": "turn", "lift": "lift", "wrist": "wrist"}[sv]] = a0 + (a1 - a0) * float(p_[0])
        mats = pose_mats(joints(**c), True)
        R, tr = mats["can"]
        P_w.append(R @ cg_can_local + tr)
        R_w.append(R)
    P_w = np.array(P_w)
    acc = np.gradient(np.gradient(P_w, dt, axis=0), dt, axis=0)
    for k in range(2, len(ts) - 3):
        f = acc[k] + np.array([0, 0, G])                  # specific force the pads must supply (m/s^2)
        fl = R_w[k].T @ f                                  # in the gripper frame (pad normal = local X)
        inplane = math.hypot(fl[1], fl[2])
        f_need.append(m_can * inplane / (2 * MU_PAD))
        times.append(t0 + ts[k])
    t0 += secs
N_min = max(f_need)
out(f"   max friction demand: squeeze ≥ {N_min:.3f} N per arm (μ = {MU_PAD}, includes gravity, lift, flip and turn accelerations)")
check("Can", "design squeeze 0.8 N/arm vs needed (slip)", f"{0.8 / N_min:.1f}× the minimum", "≥ 2×", 0.8 / N_min >= 2)
check("Can", "design squeeze vs dent force (~8 N/arm)", f"{8 / 0.8:.0f}× below", "≥ 3×", 8 / 0.8 >= 3)
sg90_max_N = SERVO["grip"]["stall"] / (2 * 0.044)
check("Can", "SG90 can't crush the can even at stall", f"{sg90_max_N:.2f} N/arm max", "< 8 N", sg90_max_N < 8)
# landing: min-jerk ends with zero speed and acceleration; CAD check puts the bottom at z = 0.00
rep = open(os.path.join(OUT, "check_report.txt")).read() if os.path.exists(os.path.join(OUT, "check_report.txt")) else ""
mz = re.search(r"bottom at z = (-?[\d.]+)", rep)
z_land = float(mz.group(1)) if mz else float("nan")
check("Can", "set down, not dropped (bottom height after LOWER, CAD)", f"{z_land:+.2f} mm, 0 mm/s", "|z| ≤ 0.5 mm", abs(z_land) <= 0.5)
r_rim_top = 27.6
h_cg = P["can_h"] / 2
tip_ang = math.degrees(math.atan(r_rim_top / h_cg))
check("Can", "inverted can tips only past", f"{tip_ang:.1f}°", "≥ 3 × wrist tolerance (3°)", tip_ang >= 9)
out(f"   inverted on its top rim (r {r_rim_top} mm), CG {h_cg:.1f} mm up: tips at {tip_ang:.1f}°; wrist error budget ±3°")
out("")

# ------------------------------------------------------------------ 5. robot stability (dynamic)
out("5. ROBOT STABILITY: zero-moment point (dynamic tip-over), sliding, turning reaction")
pts = []
for nm in ("base", "electronics_tray"):
    for v in by_name[nm]["shape"].faces("<Z").vertices().vals():
        pts.append((round(v.X, 2), round(v.Y, 2)))
foot = C.hull(pts)
zmp_margin, slide_ratio, yaw_ratio = 1e9, 0.0, 0.0
m_all = sum(mass.values())
for label, sv, a0, a1, secs, attached in STEPS:
    ctx = {"GRIP": {}, "LIFT": dict(grip=95), "FLIP": dict(grip=95, lift=75), "TURN": dict(grip=95, lift=75, wrist=180),
           "LOWER": dict(grip=95, wrist=180, turn=45), "RELEASE": dict(wrist=180, turn=45),
           "H-LIFT": dict(grip=70, wrist=180, turn=45), "H-CLOSE": dict(lift=75, wrist=180, turn=45),
           "H-WRIST": dict(grip=95, lift=75, turn=45), "H-TURN": dict(grip=95, lift=75), "H-LOWER": dict(grip=95),
           "H-OPEN": {}}[label]
    ts = np.arange(-2 * dt, secs + 3 * dt, 4 * dt)
    names = [n for n in mass if not (n == CAN and label.startswith("H-"))]
    traj = {n: [] for n in names}
    for t in ts:
        p_, _, _ = mj(np.array([t / secs]))
        c = dict(turn=FW["TURN_START"], lift=FW["LIFT_DOWN"], wrist=FW["WRIST_UP"], grip=FW["GRIP_OPEN"])
        c.update(ctx)
        c[sv] = a0 + (a1 - a0) * float(p_[0])
        mats = pose_mats(joints(**c), attached)
        if not attached and label in ("RELEASE",):
            mats["can"] = pose_mats(joints(**dict(c, grip=95)), True)["can"]
        for n in names:
            traj[n].append(world_cg(n, mats))
    hh = 4 * dt
    for k in range(2, len(ts) - 2):
        num_x = num_y = den = 0.0
        Fx = Fy = 0.0
        for n in names:
            pth = np.array(traj[n])
            a = (pth[k + 1] - 2 * pth[k] + pth[k - 1]) / hh ** 2
            x_, y_, z_ = pth[k]
            mm = mass[n]
            num_x += mm * ((a[2] + G) * x_ - a[0] * z_)
            num_y += mm * ((a[2] + G) * y_ - a[1] * z_)
            den += mm * (a[2] + G)
            Fx += mm * a[0]; Fy += mm * a[1]
        zmp = (num_x / den, num_y / den)
        zmp_margin = min(zmp_margin, C.inside_margin(foot, (zmp[0] * 1000, zmp[1] * 1000)))
        slide_ratio = max(slide_ratio, math.hypot(Fx, Fy) / (MU_FEET * m_all * G))
    if sv == "turn":
        names_t = TURRET_SET + ([CAN] if attached else [])
        mid = joints((a0 + a1) / 2, ctx.get("lift", 30), ctx.get("wrist", 0), ctx.get("grip", 20))
        J = inertia_about(names_t, pose_mats(mid, attached), np.zeros(3), (0, 0, 1))
        alpha_pk = math.radians(abs(a1 - a0)) * 5.7735 / secs ** 2
        yaw_ratio = max(yaw_ratio, J * alpha_pk / (MU_FEET * m_all * G * 0.05))
out(f"   dynamic ZMP stays ≥ {zmp_margin:.1f} mm inside the support footprint in every pose of the run and homing")
check("Stability", "tip-over (dynamic ZMP margin, all moves)", f"{zmp_margin:.1f} mm", "≥ 20 mm", zmp_margin >= 20)
check("Stability", "base sliding: inertial force / foot friction", f"{slide_ratio:.2%}", "≤ 20 %", slide_ratio <= 0.2)
check("Stability", "turntable reaction torque / foot friction torque", f"{yaw_ratio:.2%}", "≤ 20 %", yaw_ratio <= 0.2)
out("")

# ------------------------------------------------------------------ 6. strength and stiffness
out("6. STRENGTH AND STIFFNESS (worst-case loads; PETG allowable 20 MPa = UTS 50 / 2.5)")
# finger arm: bar 5 mm (in the bending plane) x 6 mm, worst case SG90 stall force on the pad
F_pad = sg90_max_N
L_arm = math.dist((P["pivot_x"], P["pivot_y"]), (P["can_d"] / 2 + 4.5, P["can_y"]))
bw, bh = 5.0, P["finger_z"][1] - P["finger_z"][0]
I_f = bh * bw ** 3 / 12
sig_f = F_pad * L_arm * (bw / 2) / I_f
d_f = F_pad * L_arm ** 3 / (3 * PETG["E"] * I_f)
out(f"   finger arm: {F_pad:.2f} N at {L_arm:.0f} mm → σ {sig_f:.1f} MPa, deflection {d_f:.2f} mm")
check("Strength", "finger arm bending at SG90 stall", f"{sig_f:.1f} MPa", "≤ 20 MPa", sig_f <= PETG["sigma_allow"])
check("Strength", "finger arm deflection at SG90 stall", f"{d_f:.2f} mm", "≤ 1.5 mm", d_f <= 1.5)
# carriage arm beam: cantilever carrying the wrist set + can, with a 2x dynamic factor
W_tip = (sum(mass[n] for n in WRIST_SET) + mass["wrist_servo"] + m_can) * G * 2
L_beam = (P["wrist_tip_y"] - 28.5 + 15.9) - P["car_y1"]
I_b = P["beam_w"] * P["beam_t"] ** 3 / 12
sig_b = W_tip * L_beam * (P["beam_t"] / 2) / I_b
d_b = W_tip * L_beam ** 3 / (3 * PETG["E"] * I_b)
check("Strength", "carriage arm (2× dynamic load)", f"{sig_b:.2f} MPa, {d_b * 1000:.1f} µm", "≤ 20 MPa", sig_b <= PETG["sigma_allow"])
# rods: lift-set moment taken as a couple by the bushing pairs; fixed-fixed rods
m_lift = sum(mass[n] for n in LIFT_SET) + m_can
mats_h = pose_mats(joints(FW["TURN_START"], FW["LIFT_UP"], 0, 95), True)
e_l = (sum(mass[n] * world_cg(n, mats_h)[1] for n in LIFT_SET + [CAN]) / m_lift) * 1000 - P["rod_y"]
span = P["car_h"] - P["lm_len"]
F_b = m_lift * G * 2 * e_l / span / 2                     # per rod, 2x dynamic
I_r = math.pi * P["rod_d"] ** 4 / 64
L_r = P["rod_len"]
d_r = F_b * L_r ** 3 / (192 * STEEL["E"] * I_r)
sig_r = F_b * L_r / 8 * (P["rod_d"] / 2) / I_r
check("Strength", "6 mm rods (bending, fixed-fixed)", f"{sig_r:.2f} MPa, {d_r * 1000:.2f} µm", "≤ 200 MPa", sig_r <= STEEL["sigma_allow"])
check("Strength", "LM6UU load vs static rating 206 N (EST)", f"{F_b:.2f} N", "≤ 50 N", F_b <= 50)
# turret plate: column moment into the plate at the hub
m_turret_side = sum(mass[n] for n in TURRET_SET) + m_can
mats_t = pose_mats(joints(FW["TURN_START"], FW["LIFT_UP"], 180, 95), True)
cg_t = sum(mass[n] * world_cg(n, mats_t) for n in TURRET_SET + [CAN]) / m_turret_side
M_t = m_turret_side * G * 2 * math.hypot(cg_t[0], cg_t[1])        # N*m, 2x dynamic
I_tp = 60 * P["turret_t"] ** 3 / 12
sig_tp = M_t * 1000 * (P["turret_t"] / 2) / I_tp
check("Strength", "turret plate at the hub (2× dynamic)", f"{sig_tp:.2f} MPa", "≤ 20 MPa", sig_tp <= PETG["sigma_allow"])
C0_6807 = 3500.0                                           # N static radial rating (EST)
check("Strength", "6807 bearing: load vs static rating (EST 3.5 kN)", f"{m_turret_side * G * 2:.1f} N + {M_t * 1000:.0f} N·mm", "≤ 10 % of rating", m_turret_side * G * 2 + M_t / 0.0205 <= 0.1 * C0_6807)
# lift link: axial load and Euler buckling (3 x 7 section, pinned-pinned)
F_link = max(abs(np.array(duty["lift"]["tau"]))) / (Rc / 1000) * 2
I_l = 7 * 3 ** 3 / 12
P_cr = math.pi ** 2 * PETG["E"] * I_l / L_LINK ** 2
check("Strength", "lift link: buckling load / max link force", f"{P_cr / F_link:.0f}×", "≥ 10×", P_cr / F_link >= 10)
# servo spline socket in the left finger: torque at stall, shear on the socket wall
tau_sock = SERVO["grip"]["stall"] * 1000 / (2 * math.pi * 3.0 ** 2 * (P["finger_z"][1] - P["finger_z"][0] - 2))
check("Strength", "SG90 spline socket shear at stall", f"{tau_sock:.2f} MPa", "≤ 10 MPa", tau_sock <= PETG["tau_allow"])
# screws in PETG pilots: #6-32 pull-out (2.9 mm pilot, 6 mm engagement, 15 MPa shear, 75 % thread fill)
F_pull = math.pi * 2.9 * 6 * 15 * 0.75
F_screw_max = 9.4 * 0.0981 / 0.0495 / 2 * 2                  # MG996R stall reacted by its flange screws (worst screw load)
check("Strength", "#6/#8 screws in PETG: pull-out / worst load", f"{F_pull:.0f} N vs {F_screw_max:.0f} N", "≥ 10×", F_pull / F_screw_max >= 10)
out("")

# ------------------------------------------------------------------ 7. power and heat
out("7. POWER AND HEAT")
ee = open(os.path.join(ROOT, "EE", "out", "ee_report.txt")).read() if os.path.exists(os.path.join(ROOT, "EE", "out", "ee_report.txt")) else ""
pk_I = re.search(r"Peak of the whole run: ([\d.]+) A", ee)
pk_I = float(pk_I.group(1)) if pk_I else float("nan")
mech_pk = {}
for sv in SERVO:
    tau_a, w_a = np.array(duty[sv]["tau"]), np.radians(np.array(duty[sv]["w"]))
    mech_pk[sv] = float(np.max(tau_a * w_a))
out("   peak mechanical power: " + ", ".join(f"{SERVO[k]['name']} ({k}) {v:.3f} W" for k, v in mech_pk.items()))
P_elec = pk_I * 5.8
out(f"   peak electrical (servo rail, ngspice model): {pk_I:.2f} A × 5.8 V = {P_elec:.2f} W; buck loss (10 %) {0.1 * P_elec / 0.9:.2f} W")
check("Power", "peak servo current vs XL4015 rating 5 A", f"{pk_I:.2f} A", "≤ 2.5 A (50 %)", pk_I <= 2.5)
check("Power", "buck dissipation (no heatsink ≤ 1 W)", f"{0.1 * P_elec / 0.9:.2f} W", "≤ 1 W", 0.1 * P_elec / 0.9 <= 1.0)
hold_I = 0.65 * grip_hold_frac
check("Power", "SG90 holding heat (5 s per run)", f"{hold_I * 5.8:.2f} W for 5 s", "≤ 2 W", hold_I * 5.8 <= 2.0)
check("Power", "Uno regulator (own 9 V battery, 59 mA)", f"{(9.3 - 1.0 - 5) * 0.059:.2f} W", "≤ 1 W (SOT-223)", (9.3 - 1.0 - 5) * 0.059 <= 1.0)
check("Power", "9 V battery life (Uno + LED, 59 mA, ~550 mAh)", f"{0.55 / 0.059:.0f} h", "≥ 4 h (a day of testing)", 0.55 / 0.059 >= 4)
E_run = 0.0
for sv in SERVO:
    t_ = np.array(duty[sv]["t"]); o = np.argsort(t_, kind="stable")
    E_run += float(np.trapezoid((np.array(duty[sv]["tau"]) * np.radians(np.array(duty[sv]["w"])))[o], t_[o]))
out(f"   mechanical energy per run (all servos, run + homing): {E_run:.3f} J")
out("")

# ------------------------------------------------------------------ 8. prototype v1 (the parts actually bought + household swaps)
out("8. PROTOTYPE v1: the purchased parts and the household swaps (docs/11_bom_prototype_v1.md)")
# servos: what each one must at least deliver for the 2x torque margin to hold
for sv, listed in (("turn", None), ("lift", 2.0), ("wrist", 2.0)):
    need_kgcm = SERVO[sv]["stall"] / 0.0981 * worst_ratio[sv] / LIMIT_TORQUE
    if listed is None:
        check("Proto v1", f"Adeept 996R: stall needed for 2× margin (VERIFY ≥ this)", f"≥ {need_kgcm:.1f} kg·cm", "MG996R class 9.4", need_kgcm <= 9.4)
    else:
        check("Proto v1", f"Miuzei MG90S ({sv}): listed 2.0 kg·cm vs needed", f"{need_kgcm:.2f} kg·cm needed", "≤ 2.0 listed", need_kgcm <= listed)
# pads: household rubber, worst friction
MU_HOME = 0.35          # rubber band / shelf liner on aluminium, worst case (EST)
check("Proto v1", f"household pad rubber (μ {MU_HOME}): squeeze margin", f"{0.8 / (N_min * MU_PAD / MU_HOME):.1f}× the minimum", "≥ 2×", 0.8 / (N_min * MU_PAD / MU_HOME) >= 2)
for t_ in (1.0, 2.0):
    d_alpha = math.degrees((t_ - 1.6) / 44.0)
    out(f"   pad rubber {t_:.1f} mm instead of 1.6: closed angle shifts {d_alpha:+.1f}° (re-set GRIP_CLOSED with servo_setup), release gap {13.3 - (t_ - 1.6) - 1.6:.1f} mm")
check("Proto v1", "pad rubber 2.0 mm: release gap to the can", f"{13.3 - 2.0:.1f} mm", "≥ 5 mm", 13.3 - 2.0 >= 5)
# ballast: not in the mass model, so every stability result above already holds without it
check("Proto v1", "tip-over with NO ballast (ballast is not in the model)", f"{zmp_margin:.1f} mm", "≥ 20 mm", zmp_margin >= 20)
# LIZVOR adjustable adapter set to 12 V, 2 A
eta, v_in = 0.88, 12.0
I_in_run = pk_I * 5.8 / (eta * v_in)                  # the Uno is on its own 9 V battery now
I_in_stall = (2.5 + 0.3) * 5.8 / (eta * v_in)            # MG996R stalled (2.5 A EST) + the rest idle
check("Proto v1", "LIZVOR 2 A adapter: current in a normal run", f"{I_in_run:.2f} A", "≤ 1.0 A (50 %)", I_in_run <= 1.0)
check("Proto v1", "LIZVOR 2 A adapter: MG996R stalled (worst case)", f"{I_in_stall:.2f} A", "≤ 2.0 A", I_in_stall <= 2.0)
out("   the knob: the adapter feeds only the buck now (the Uno has its own 9 V battery); the servos stay at 5.8 V whatever comes in. Tape it at 12.0 V")
# jumper chains instead of servo extensions (gripper: ~270 mm added, 2 jumpers per wire)
R_wire = 0.213 * 0.40 * 2          # 28 AWG ohm/m x 0.4 m, + and - wires
R_joint = 0.03 * 4                 # 4 dupont joints in the loop
I_sg90 = 0.65                      # SG90 stall current (EST)
dV = I_sg90 * (R_wire + R_joint)
check("Proto v1", "jumper chain on the gripper lead: voltage drop at SG90 stall", f"{dV:.2f} V", "≤ 0.3 V (5 %)", dV <= 0.3)
# h8 rod instead of h6 in the LM6UU
play = 0.022 + 0.008               # extra rod undersize (h8) + LM6UU clearance (EST), mm
wobble = 2 * play / 43.0 * 110.0   # bearing pair 43 mm apart, pads ~110 mm in front of the rods
check("Proto v1", "h8 rod: extra wobble at the pads", f"{wobble:.2f} mm", "≤ 0.5 mm", wobble <= 0.5)
out("")

# ------------------------------------------------------------------ plots
fig, axs = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
for ax, sv in zip(axs, SERVO):
    t = np.array(duty[sv]["t"]); o = np.argsort(t, kind="stable")
    ax.plot(t[o], 1000 * np.array(duty[sv]["tau"])[o], label="torque needed", color="#c0392b")
    ax.plot(t[o], 1000 * np.array(duty[sv]["avail"])[o], label="torque available at that speed", color="#2f6fdb", lw=0.8)
    ax.plot(t[o], 1000 * LIMIT_TORQUE * np.array(duty[sv]["avail"])[o], ls="--", color="#2f6fdb", lw=0.6, label="50 % (design limit)")
    ax.set_ylabel(f"{SERVO[sv]['name']} {sv}\nN·mm", fontsize=9)
    ax.set_yscale("log"); ax.legend(fontsize=7, loc="lower right")
t_acc = 0
for label, *_x, secs, _a in STEPS:
    for ax in axs:
        ax.axvline(t_acc, color="#ccc", lw=0.5)
    axs[0].text(t_acc + secs / 2, axs[0].get_ylim()[1] * 0.6, label, ha="center", fontsize=7)
    t_acc += secs
axs[-1].set_xlabel("time in the sequence (s): run, then homing (moves only)")
fig.suptitle("Servo torque needed vs available (inverse dynamics from CAD masses and inertias)", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "mech_servo_duty.png"), dpi=120)
plt.close(fig)

# ------------------------------------------------------------------ report
n_fail = sum(1 for r_ in results if r_[4] == "FAIL")
head = [f"ENGINEERING CHECKS: {len(results)} checks, {len(results) - n_fail} PASS, {n_fail} FAIL",
        "(backend/mech/mech_checks.py; CAD masses/inertias, firmware timing; EST = datasheet value)", "",
        f"   {'area':10s} {'check':58s} {'value':30s} {'limit':24s} result"]
for a, i, v, l, res in results:
    head.append(f"   {a:10s} {i:58s} {v:30s} {l:24s} {res}")
head.append("")
open(os.path.join(OUT, "mech_report.txt"), "w").write("\n".join(head + ["DETAILS", ""] + lines) + "\n")
print("\n".join(head))
print(f"wrote cad/check/mech_report.txt, cad/check/mech_servo_duty.png")
sys.exit(1 if n_fail else 0)
