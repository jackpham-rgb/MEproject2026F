"""Concept A wire routing in 3D: every lead and jumper as a tube, checked against the CAD.

    python3.13 backend/cad/wiring.py          # routes + checks + mesh  (~1 min)
    node backend/tools/render_wiring_360.js   # 360 GIF / MP4 / stills from the mesh

Writes
  cad/wiring/wiring_harness.step   the wires as solids (open with concept_a_assembly.step)
  cad/wiring/wiring_report.txt     clearances in every motion pose, service-loop slack, lead lengths
  backend/cad/build/wiring_mesh.json   parts + wires for the 360 page (viewer/wiring_360.html)

How the wires are tucked in (home pose, numbers = labels in the 360 view)
  1  wrist loop      SG90 lead leaves the gripper behind the frame and hangs in a loop left of the wrist
                     servo: enough slack to wrap 180 deg around the roll axis when the claw flips
  2  arm clip        SG90 + wrist leads tied along the left side of the arm beam and carriage
  3  lift loop       a U-loop in the gap between carriage and spine takes the 15.3 mm lift
  4  spine window    the three column leads pass through the window in the spine's back wall ...
  5  turret notch    ... run down the back of the spine and leave the turret through the notch
  6  turn loop       a loop on the base top, outside the turret (r > 41 mm) and outside the 175 deg sweep,
                     takes the 90 deg turn: the base hole sits half-way (225 deg) between START and TARGET
  7  base hole       down into the base, along the floor (MG996R lead joins) ...
  8  base exit       ... out through the back wall into the tray
  9  servo headers   3-pin headers on the breadboard (servo rail: buck 5.8 V + 1000 uF)
 10  Uno             signal jumpers to D5 D6 D9 D10, button D4, LED D13, GND, VIN
 11  buck            12 V in, 5.8 V out to the rail and to the MG996R
 12  panel           START button, LED, 12 V jack
"""
import json
import math
import os
import sys

import numpy as np
import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402

OUT = os.path.join(ROOT, "cad", "wiring")
BUILD = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)
os.makedirs(BUILD, exist_ok=True)
P, FW = M.P, M.FW

LEAD_R = 1.3        # servo lead (3-wire ribbon ~3.6 x 1.2 mm) drawn as a 2.6 mm round cable
JUMP_R = 0.8        # dupont jumper
PWR_R = 1.1         # 20 AWG power wire
GAP = 2.8           # spacing of parallel leads in a bundle
END_SKIP = 4.0      # mm at each plug end that may touch the part it plugs into
CLEAR_MIN = 0.3     # wire surface must stay this far from any part

# colours: one per servo lead, then by function
C = dict(grip="#e8b923", wrist="#9b59d0", lift="#2a9df4", turn="#e2552d", sig="#ff8c1a", pos="#d42020",
         neg="#202020", btn="#18a058", led="#00b5b5")

# ---------- geometry the routes are built from (all from model.py) ----------
ty0 = -P["base_w"] / 2 - P["tray_len"]                       # tray front (-171)
TF = P["tray_t"]                                             # tray floor top (4)
UNO = (-72.0, ty0 + 8.0)                                     # Uno board origin
UNO_TOP = TF + 7.6                                           # board top
HDR = UNO_TOP + 8.5                                          # female header top


def uno_pin(name):
    """Header pin position (Uno R3 drawing, board origin at the corner near the power jack)."""
    dig = {f"D{i}": 63.5 - 2.54 * i for i in range(8)}
    dig.update({f"D{i}": 41.6 - 2.54 * (i - 8) for i in range(8, 14)})
    dig["GND"] = 41.6 - 2.54 * 6
    if name in dig:
        return (UNO[0] + dig[name], UNO[1] + 50.8, HDR)
    pwr = {"5V": 27.9 + 4 * 2.54, "GND2": 27.9 + 5 * 2.54, "VIN": 27.9 + 7 * 2.54}
    return (UNO[0] + pwr[name], UNO[1] + 2.5, HDR)


BB_Y0 = ty0 + 49                                            # breadboard (y -122 .. -87)
BB_TOP = TF + 8.5
HDR_X = dict(grip=14.0, wrist=20.0, lift=26.0)              # 3-pin servo headers (pins along y)
HDR_Y = BB_Y0 + 30                                          # -92
SIG_Y = BB_Y0 + 21                                          # signal row jumper hole
RAIL_P, RAIL_N = BB_Y0 + 3.5, BB_Y0 + 1.0                   # + / - rail
BK = (8.0, ty0 + 22.0)                                      # buck origin (54 x 23)
BK_TOP = TF + 19
BK_IN_P, BK_IN_N = (BK[0] + 3, BK[1] + 16, BK_TOP), (BK[0] + 3, BK[1] + 7, BK_TOP)
BK_OUT_P, BK_OUT_N = (BK[0] + 51, BK[1] + 16, BK_TOP), (BK[0] + 51, BK[1] + 7, BK_TOP)
PANEL_IN = ty0 + 3


def micro_exit(origin, xdir, zdir):
    """Lead exit of an SG90/MG90S: far end face (local x = 16.85), near the bottom (local z = -25)."""
    t = M.trsf_axes(origin, xdir, zdir)
    p = gp_Pnt(16.85, 0, -25).Transformed(t)
    return (p.X(), p.Y(), p.Z())


lt = P["lift_servo_tip"]
EX_LIFT = micro_exit(lt, (0, 0, -1), (-1, 0, 0))
EX_WRIST = micro_exit((0, P["wrist_tip_y"], P["grip_z"]), (0, 0, -1), (0, 1, 0))
gs_face = P["plate_top"][1] + 0.5
EX_GRIP = micro_exit((-P["pivot_x"], P["pivot_y"], gs_face - 5.8), (-1, 0, 0), (0, 0, -1))
a = math.radians(P["servo_ang"])                             # MG996R: far end face, 8 mm off the table
EX_TURN = (30.5 * math.cos(a), 30.5 * math.sin(a), 50.0 - 42.0)


def k_off(trunk, k):
    """Trunk points offset by k * GAP along each point's offset direction (k = -1, 0, 1, 2)."""
    out = []
    for (x, y, z, g, d) in trunk:
        n = math.sqrt(sum(c * c for c in d)) or 1
        out.append((x + k * GAP * d[0] / n, y + k * GAP * d[1] / n, z + k * GAP * d[2] / n, g))
    return out


# Column trunk: carriage side -> lift loop -> spine window -> back of spine -> notch -> turn loop ->
# base hole -> floor -> base exit. (x, y, z, group, offset direction)
TRUNK = [
    (-28.5, 16.0, 77.0, "lift", (0, 0, -1)),
    (-28.5, 4.0, 77.0, "lift", (0, 0, -1)),
    (-24.0, -6.0, 70.0, "loop", (0.6, 0, -0.8)),             # 3 lift loop (sags, then climbs to the window)
    (-15.0, -13.0, 70.0, "loop", (0.3, 0, -1)),
    (-6.0, -15.5, 84.0, "loop", (1, 0, 0)),
    (-1.0, -15.5, 94.0, "turret", (1, 0, 0)),                # 4 spine window (x -8..8, z 71..109)
    (-1.0, -21.0, 94.0, "turret", (1, 0, 0)),
    (-1.0, -27.0, 90.0, "turret", (1, 0, 0)),
    (-1.0, -27.0, 70.0, "turret", (1, 0, 0)),                # down the back of the spine
    (-1.0, -31.0, 63.0, "turret", (1, 0, 0)),
    (-1.0, -35.5, 61.5, "turret", (1, 0, 0)),
    (-1.0, -37.5, 57.0, "turret", (1, 0, 0)),                # 5 turret notch (x -6..6, y -41..-33)
    (-1.0, -43.0, 55.0, "turret", (1, 0, 0)),
    (-7.0, -51.0, 56.0, "loop", (0.15, -1, 0)),             # 6 turn loop on the base top
    (-22.0, -64.0, 57.0, "loop", (-0.3, -1, 0)),
    (-40.0, -60.0, 57.0, "loop", (-1, -0.6, 0)),
    (-42.0, -45.0, 57.0, "loop", (-1, 0.3, 0)),
    (-35.5, -37.5, 54.5, "fixed", (-1, 1, 0)),               # 7 base hole (-34, -34) r 7
    (-34.5, -35.0, 47.0, "fixed", (-1, 1, 0)),
    (-36.0, -38.0, 30.0, "fixed", (-1, 1, 0)),
    (-34.0, -46.0, 8.0, "fixed", (-1, 0.4, 0)),
    (-24.0, -58.0, 2.0, "fixed", (-0.8, 1, 0)),             # on the table inside the base
    (-10.0, -66.0, 4.0, "fixed", (-1, 0.3, 0)),
    (-4.0, -73.0, 11.0, "fixed", (1, 0, 0)),                 # 8 base exit (x -15..15, z 8..22)
    (-4.0, -80.0, 9.0, "fixed", (1, 0, 0)),
]
I_WINDOW = 5      # the lift lead joins the trunk here
I_FLOOR = 21      # the MG996R lead joins the trunk here


def servo_tail(k, x_hdr, z_hdr=BB_TOP + 2.5):
    """From the trunk end across the tray floor to a 3-pin header on the breadboard."""
    x0 = -4.0 + k * GAP
    zf = TF + LEAD_R + 2.2
    return [(x0, -83.0, zf, "fixed"), (x_hdr - 4, -82.0, zf, "fixed"), (x_hdr, -84.0, BB_TOP + 6, "fixed"),
            (x_hdr, -89.0, z_hdr + 4, "fixed"), (x_hdr, HDR_Y + 1.5, z_hdr, "fixed")]


def arc(p0, p1, lift, groups="fixed", mid_frac=(0.25, 0.75)):
    """Jumper from p0 to p1 bowed up by `lift` mm (the way a loose dupont wire lies)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    up = np.array([0, 0, lift])
    pts = [p0, p0 + np.array([0, 0, min(lift, 6)])]
    for f in mid_frac:
        pts.append(p0 + (p1 - p0) * f + up)
    pts += [p1 + np.array([0, 0, min(lift, 6)]), p1]
    return [(*p, groups) for p in pts]


def routes():
    W = []
    k_g, k_w, k_l, k_t = -1, 0, 1, 2
    # SG90 (gripper) lead: over the servo, behind the gripper frame, 1 wrist loop, 2 along the arm
    g_own = [(*EX_GRIP, "wrist"), (EX_GRIP[0] - 3.5, EX_GRIP[1] - 1, EX_GRIP[2] - 0.5, "wrist"),
             (-29.0, 74.0, 98.0, "wrist"), (-26.0, 63.0, 95.0, "wrist"), (-24.0, 56.5, 90.0, "wrist"),
             (-21.0, 56.0, 72.0, "wrist"), (-17.5, 57.8, 63.5, "wrist"), (-15.9, 60.5, 61.0, "wrist"),   # tied to the flange side
             (-21.0, 57.0, 50.0, "loop"), (-26.0, 51.0, 36.0, "loop"), (-19.0, 45.5, 29.0, "loop"),   # 1 wrist loop
             (-14.6, 43.5, 44.0, "loop"),
             (-13.2, 43.0, 55.0, "lift"), (-13.2, 39.0, 66.0, "lift"), (-12.5, 33.0, 72.0, "lift"),   # tied to the bracket side
             (-12.5, 26.0, 75.0, "lift"), (-21.0, 25.5, 77.0 - k_g * GAP, "lift"), (-28.5, 24.5, 77.0 - k_g * GAP, "lift")]
    W.append(dict(name="SG90 gripper lead (D5)", key="grip", color=C["grip"], r=LEAD_R, servo="grip",
                  pts=g_own + k_off(TRUNK, k_g) + servo_tail(k_g, HDR_X["grip"])))
    # wrist lead: from the bottom of the wrist servo, up the left of the bracket, joins along the arm
    w_own = [(*EX_WRIST, "lift"), (EX_WRIST[0], EX_WRIST[1] - 1.5, EX_WRIST[2] - 3, "lift"),
             (-7.0, 31.0, 41.0, "lift"), (-14.0, 30.0, 50.0, "lift"), (-15.3, 28.0, 66.0, "lift"),
             (-15.3, 26.5, 74.0, "lift"), (-21.0, 25.5, 77.0, "lift"), (-28.5, 24.5, 77.0, "lift")]
    W.append(dict(name="Wrist servo lead (D6)", key="wrist", color=C["wrist"], r=LEAD_R, servo="wrist",
                  pts=w_own + k_off(TRUNK, k_w) + servo_tail(k_w, HDR_X["wrist"])))
    # lift lead: from the bottom of the MG90S down the front of the spine into the window
    l_own = [(*EX_LIFT, "turret"), (EX_LIFT[0], EX_LIFT[1] - 1.5, EX_LIFT[2] - 3, "turret"),
             (20.0, -13.0, 118.0, "turret"), (9.0, -15.5, 103.0, "turret")]
    W.append(dict(name="MG90S lift lead (D10)", key="lift", color=C["lift"], r=LEAD_R, servo="lift",
                  pts=l_own + k_off(TRUNK, k_l)[I_WINDOW:] + servo_tail(k_l, HDR_X["lift"])))
    # MG996R lead: out of the turntable servo's end, joins the bundle on the floor; in the tray it is the
    # cut extension: +/- to the buck OUT terminals, signal straight to D9
    ang = math.radians(P["servo_ang"])
    t_own = [(*EX_TURN, "fixed"), (EX_TURN[0] + 5 * math.cos(ang), EX_TURN[1] + 5 * math.sin(ang), 4.0, "fixed"),
             (-31.0, -38.0, 2.0, "fixed")]
    split = (66.0, -128.0, TF + LEAD_R + 2.2)
    zf = TF + LEAD_R + 2.2
    t_tail = [(-4.0 + k_t * GAP, -83.0, zf, "fixed"), (40.0, -82.0, zf, "fixed"),
              (64.0, -86.0, zf, "fixed"), (66.0, -100.0, zf, "fixed"), (66.0, -118.0, zf, "fixed"), (*split, "fixed")]
    W.append(dict(name="MG996R turntable lead (D9, power on the buck)", key="turn", color=C["turn"], r=LEAD_R, servo="turn",
                  pts=t_own + k_off(TRUNK, k_t)[I_FLOOR:] + t_tail))
    # MG996R +/- from the split to the buck OUT terminals, signal to D9
    W.append(dict(name="MG996R + to buck OUT+", key="pos", color=C["pos"], r=PWR_R,
                  pts=[(*split, "fixed"), (66.0, BK_OUT_P[1] + 3, BK_TOP + 6, "fixed"), (BK_OUT_P[0] + 1, BK_OUT_P[1], BK_TOP + 4, "fixed"), (*BK_OUT_P, "fixed")]))
    W.append(dict(name="MG996R - to buck OUT-", key="neg", color=C["neg"], r=PWR_R,
                  pts=[(split[0] + 1.5, split[1], split[2], "fixed"), (67.5, BK_OUT_N[1] + 2, BK_TOP + 7, "fixed"), (BK_OUT_N[0] + 2, BK_OUT_N[1], BK_TOP + 4, "fixed"), (*BK_OUT_N, "fixed")]))
    W.append(dict(name="MG996R signal to D9", key="sig", color=C["sig"], r=JUMP_R,
                  pts=[(split[0] - 1.5, split[1] + 1, split[2], "fixed"), (64.0, -110.0, 30.0, "fixed"), (20.0, -106.0, 30.0, "fixed"),
                       (uno_pin("D9")[0] + 3, -108.0, 28.0, "fixed"), (uno_pin("D9")[0], uno_pin("D9")[1], HDR + 6, "fixed"), (*uno_pin("D9"), "fixed")]))
    # signal jumpers from each servo header's signal row to the Uno
    for key, pin in (("grip", "D5"), ("wrist", "D6"), ("lift", "D10")):
        x = HDR_X[key] + 1.0
        W.append(dict(name=f"{key} signal jumper to {pin}", key="sig", color=C["sig"], r=JUMP_R,
                      pts=arc((x, SIG_Y, BB_TOP), uno_pin(pin), 14 + (x - 14) * 0.6)))
    # buck OUT -> breadboard rail, 1000 uF on the rail (part in model.py)
    W.append(dict(name="buck OUT+ to servo rail", key="pos", color=C["pos"], r=PWR_R,
                  pts=arc(BK_OUT_P, (52.0, RAIL_P, BB_TOP), 8, mid_frac=(0.3, 0.7))))
    W.append(dict(name="buck OUT- to rail -", key="neg", color=C["neg"], r=PWR_R,
                  pts=arc(BK_OUT_N, (49.0, RAIL_N, BB_TOP), 12, mid_frac=(0.3, 0.7))))
    # Uno GND to the rail (common ground)
    W.append(dict(name="Uno GND to rail -", key="neg", color=C["neg"], r=JUMP_R,
                  pts=arc(uno_pin("GND"), (11.0, RAIL_N, BB_TOP), 16)))
    # 12 V jack -> buck IN and Uno VIN: leave the lugs straight up (the buck is 3 mm behind), then over the buck
    jx, yb = 65.0, PANEL_IN + 17.5
    zt = BK_TOP + 7
    W.append(dict(name="12 V jack + to buck IN+", key="pos", color=C["pos"], r=PWR_R,
                  pts=[(jx - 1.0, PANEL_IN + 16, 15, "fixed"), (jx - 0.5, yb + 1, 17, "fixed"), (jx - 0.5, -146.0, zt - 1, "fixed"),
                       (40.0, -146.0, zt, "fixed"), (BK_IN_P[0] + 3, BK_IN_P[1], zt - 1, "fixed"), (BK_IN_P[0], BK_IN_P[1], BK_TOP + 4, "fixed"), (*BK_IN_P, "fixed")]))
    W.append(dict(name="12 V jack - to buck IN-", key="neg", color=C["neg"], r=PWR_R,
                  pts=[(jx + 1.5, PANEL_IN + 16, 15, "fixed"), (jx + 2.0, yb + 1, 17, "fixed"), (jx + 2.0, -147.0, zt + 2, "fixed"),
                       (40.0, -147.5, zt + 3, "fixed"), (BK_IN_N[0] + 3, BK_IN_N[1], zt + 2, "fixed"), (BK_IN_N[0], BK_IN_N[1], BK_TOP + 4, "fixed"), (*BK_IN_N, "fixed")]))
    vin = uno_pin("VIN")
    W.append(dict(name="12 V jack + to Uno VIN", key="pos", color=C["pos"], r=JUMP_R,
                  pts=[(jx + 3.0, PANEL_IN + 16, 16, "fixed"), (jx + 4.5, yb + 1, 18, "fixed"), (jx + 4.5, -147.0, zt + 6, "fixed"), (30.0, -150.0, zt + 7, "fixed"),
                       (vin[0] + 6, vin[1] + 1, HDR + 9, "fixed"), (vin[0], vin[1], HDR + 5, "fixed"), (*vin, "fixed")]))
    # START button (D4 + GND) and status LED (D13 via 220 ohm, + GND rail)
    for nm, x0, pin, col in (("START button", 15.0, "D4", C["btn"]), ("status LED", 40.0, "D13", C["led"])):
        depth = 16 if nm.startswith("START") else 10
        yb_ = PANEL_IN + depth + 1.5
        p0 = (x0 - 1.5, PANEL_IN + depth, 15.5)
        W.append(dict(name=f"{nm} to {pin}", key=col, color=col, r=JUMP_R,
                      pts=[(*p0, "fixed"), (x0 - 1.5, yb_, 20.0, "fixed"), (x0 - 1.5, yb_, 30.0, "fixed"), (x0 - 6, -130.0, 34.0, "fixed"),
                           (uno_pin(pin)[0] + 4, -110.0, 30.0, "fixed"), (uno_pin(pin)[0], uno_pin(pin)[1], HDR + 6, "fixed"), (*uno_pin(pin), "fixed")]))
        xr = 11.0 if x0 < 30 else 30.0
        W.append(dict(name=f"{nm} to GND rail", key="neg", color=C["neg"], r=JUMP_R,
                      pts=[(x0 + 1.5, PANEL_IN + depth, 14.5, "fixed"), (x0 + 1.5, yb_, 20.0, "fixed"), (x0 + 1.5, yb_, 28.0, "fixed"),
                           (xr, -127.0, 26.0, "fixed"), (xr, RAIL_N - 1, BB_TOP + 5, "fixed"), (xr, RAIL_N, BB_TOP, "fixed")]))
    return W


# ---------- curves ----------
def catmull(pts, step=1.0):
    """Centripetal Catmull-Rom through the waypoints, resampled every ~step mm; group per sample."""
    P_ = np.array([p[:3] for p in pts], float)
    G_ = [p[3] for p in pts]
    ext = np.vstack([2 * P_[0] - P_[1], P_, 2 * P_[-1] - P_[-2]])
    out, grp = [], []
    for i in range(len(P_) - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        g = G_[i] if G_[i] == G_[i + 1] else "loop"
        for t in np.linspace(t1, t2, n, endpoint=False):
            A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
            B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
            out.append((t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2)
            grp.append(g)
    out.append(P_[-1]); grp.append(G_[-1])
    return np.array(out), grp


def length(c):
    return float(np.sum(np.linalg.norm(np.diff(c, axis=0), axis=1)))


def tube(c, r, sides=10):
    """Triangle mesh of a tube along the polyline c (parallel-transport frames), capped."""
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    n = np.cross(T[0], [0, 0, 1.0])
    if np.linalg.norm(n) < 1e-3:
        n = np.cross(T[0], [1.0, 0, 0])
    n /= np.linalg.norm(n)
    V, F = [], []
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    for i, (p, t) in enumerate(zip(c, T)):
        n = n - t * np.dot(n, t)
        n /= np.linalg.norm(n) + 1e-12
        b = np.cross(t, n)
        for a_ in ang:
            V.append(p + r * (math.cos(a_) * n + math.sin(a_) * b))
    m = len(c)
    for i in range(m - 1):
        for j in range(sides):
            a0, a1 = i * sides + j, i * sides + (j + 1) % sides
            b0, b1 = a0 + sides, a1 + sides
            F += [a0, b0, a1, a1, b0, b1]
    for i, sgn in ((0, 1), (m - 1, -1)):                                   # caps
        ci = len(V); V.append(c[i])
        for j in range(sides):
            a0, a1 = i * sides + j, i * sides + (j + 1) % sides
            F += [ci, a1, a0] if sgn > 0 else [ci, a0, a1]
    return np.array(V), F


# ---------- checks ----------
def trsf_pt(t, p):
    q = gp_Pnt(*map(float, p)).Transformed(t)
    return (q.X(), q.Y(), q.Z())


class Scene:
    def __init__(self, parts, T):
        self.items = []
        for p in parts:
            sh = p["shape"].val().moved(cq.Location(T[p["group"]]))
            self.items.append((p["name"], p["group"], sh.wrapped, sh.BoundingBox()))
        self._faces = {}

    def push(self, pt, r, margin=0.4):
        """Move a loop sample out of any part it is in (or too close to), to the part surface + r + margin:
        a cable resting on a surface instead of passing through it."""
        p = np.array(pt, float)
        for name, grp, sh, bb in self.items:
            m = r + margin + 1.0
            if p[0] < bb.xmin - m or p[0] > bb.xmax + m or p[1] < bb.ymin - m or p[1] > bb.ymax + m or p[2] < bb.zmin - m or p[2] > bb.zmax + m:
                continue
            if name not in self._faces:
                self._faces[name] = cq.Compound.makeCompound(cq.Shape.cast(sh).Faces()).wrapped
            v = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, p))).Vertex()
            d = BRepExtrema_DistShapeShape(v, self._faces[name])
            if not d.IsDone() or d.NbSolution() == 0:
                continue
            q = d.PointOnShape2(1); q = np.array([q.X(), q.Y(), q.Z()])
            dist = d.Value()
            inside = BRepClass3d_SolidClassifier(sh, gp_Pnt(*map(float, p)), 1e-6).State() == TopAbs_IN
            if inside and dist > 1e-6:
                p = q + (q - p) / dist * (r + margin)
            elif not inside and dist < r + margin and dist > 1e-6:
                p = q + (p - q) / dist * (r + margin)
        return p

    def clearance(self, pt, r, skip=(), skip_group=None):
        """(min surface gap, part name) of a wire sample of radius r; <0 means it cuts into a part."""
        best, who = 1e9, None
        v = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, pt))).Vertex()
        for name, grp, sh, bb in self.items:
            if name in skip or grp == skip_group:
                continue
            m = r + 3.0
            if pt[0] < bb.xmin - m or pt[0] > bb.xmax + m or pt[1] < bb.ymin - m or pt[1] > bb.ymax + m or pt[2] < bb.zmin - m or pt[2] > bb.zmax + m:
                continue
            cls = BRepClass3d_SolidClassifier(sh, gp_Pnt(*map(float, pt)), 1e-6)
            if cls.State() == TopAbs_IN:
                return -r, name
            d = BRepExtrema_DistShapeShape(v, sh)
            gap = d.Value() - r
            if gap < best:
                best, who = gap, name
        return best, who


POSES = [  # (label, turn, lift, wrist, grip, can removed?)
    ("GRIP (as modelled)", FW["TURN_START"], FW["LIFT_DOWN"], FW["WRIST_UP"], FW["GRIP_CLOSED"], False),
    ("HOME, arms open", FW["TURN_START"], FW["LIFT_DOWN"], FW["WRIST_UP"], FW["GRIP_OPEN"], False),
    ("LIFT up", FW["TURN_START"], FW["LIFT_UP"], FW["WRIST_UP"], FW["GRIP_CLOSED"], False),
    ("FLIP done", FW["TURN_START"], FW["LIFT_UP"], FW["WRIST_FLIP"], FW["GRIP_CLOSED"], False),
    ("TURN done", FW["TURN_TARGET"], FW["LIFT_UP"], FW["WRIST_FLIP"], FW["GRIP_CLOSED"], False),
    ("RELEASE at target", FW["TURN_TARGET"], FW["LIFT_DOWN"], FW["WRIST_FLIP"], FW["GRIP_RELEASE"], True),
]


def loop_need(kind, A, B, j_list):
    """Shortest length the loop between rigid anchors A (moving side, home) and B must reach over the motion."""
    need = 0.0
    for j in j_list:
        T = M.group_transforms(j)
        if kind == "wrist":       # A on the wrist, B on the lift: wraps around the roll axis (x=0, z=grip_z), lift frame
            a_ = np.array(trsf_pt(T["lift"].Inverted(), trsf_pt(T["wrist"], A))); b_ = np.array(B)
            gz = P["grip_z"]
            ra, ta = math.hypot(a_[0], a_[2] - gz), math.atan2(a_[2] - gz, a_[0])
            rb, tb = math.hypot(b_[0], b_[2] - gz), math.atan2(b_[2] - gz, b_[0])
            dth = abs((ta - tb + math.pi) % (2 * math.pi) - math.pi)
            # the wrist servo body sits between the anchors: wrap at the larger radius
            need = max(need, math.hypot(dth * max(ra, rb), a_[1] - b_[1]) + abs(ra - rb))
        elif kind == "lift":      # A on the lift, B on the turret
            a_ = np.array(trsf_pt(T["lift"], A)); b_ = np.array(trsf_pt(T["turret"], B))
            need = max(need, float(np.linalg.norm(a_ - b_)))
        else:                     # turn: A on the turret, B fixed; stays outside the turret (r 41)
            a_ = np.array(trsf_pt(T["turret"], A)); b_ = np.array(B)
            ra, rb = math.hypot(*a_[:2]), math.hypot(*b_[:2])
            dth = abs((math.atan2(a_[1], a_[0]) - math.atan2(b_[1], b_[0]) + math.pi) % (2 * math.pi) - math.pi)
            need = max(need, math.hypot(dth * min(ra, rb), a_[2] - b_[2]) + abs(ra - rb))
    return need


def sweep_wire(c, r):
    """Solid tube(s) along the sampled curve; long or tightly bent wires are swept in pieces."""
    def one(seg):
        idx = list(range(0, len(seg) - 1, 5)) + [len(seg) - 1]
        path = cq.Wire.assembleEdges([cq.Edge.makeSpline([cq.Vector(*seg[i]) for i in idx])])
        prof = cq.Wire.makeCircle(r, cq.Vector(*seg[0]), cq.Vector(*(seg[1] - seg[0])).normalized())
        sol = cq.Solid.sweep(prof, [], path, makeSolid=True, isFrenet=True)
        if not sol.isValid():
            raise ValueError("invalid sweep")
        return sol
    for n in (len(c), 120, 60, 30):
        try:
            return [one(c[i:i + n + 1]) for i in range(0, len(c) - 1, n)]
        except Exception:  # noqa: BLE001
            continue
    raise ValueError("could not sweep")


def main():
    parts = [p for p in M.build_parts() if p["group"] != "coupon"]
    by = {p["name"]: p for p in parts}
    W = routes()
    for w in W:
        w["c"], w["g"] = catmull(w["pts"])
    rep = ["Concept A wire routing check (backend/cad/wiring.py)", "=" * 60,
           f"wires: {len(W)}   lead r {LEAD_R} mm, jumper r {JUMP_R} mm, power r {PWR_R} mm; "
           f"required gap to any part >= {CLEAR_MIN} mm (first/last {END_SKIP:.0f} mm of a wire may touch what it plugs into)", ""]
    ok = True

    # 0. tray parts must not overlap each other (same group, so check.py does not look)
    rep.append("Tray / panel parts (fixed group, not in the motion check):")
    tray = ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF", "start_button", "status_led", "dc_jack"]
    for i, a_ in enumerate(tray):
        for b_ in tray[i + 1:]:
            if a_ == "electronics_tray":
                continue
            v = by[a_]["shape"].val().intersect(by[b_]["shape"].val()).Volume()
            d = BRepExtrema_DistShapeShape(by[a_]["shape"].val().wrapped, by[b_]["shape"].val().wrapped).Value()
            if v > 0.5:
                ok = False
                rep.append(f"  FAIL {a_} / {b_}: overlap {v:.1f} mm^3, gap {d:.1f} mm")
    for nm in ("start_button", "dc_jack", "status_led"):
        d = BRepExtrema_DistShapeShape(by[nm]["shape"].val().wrapped, by["buck_XL4015"]["shape"].val().wrapped).Value()
        rep.append(f"  {nm} body (incl. lugs) to the buck: {d:.1f} mm")
    rep.append("  PASS no overlaps" if ok else "")
    rep.append("")

    # 1. every wire sample vs every part, in each pose (loop samples only in the modelled pose)
    rep.append("Clearance in each motion pose (min gap from the wire surface to any part):")
    worst_all = {}
    for pi_, (lab, tu, li, wr, gr, no_can) in enumerate(POSES):
        j = M.joints_from_commands(tu, li, wr, gr)
        T = M.group_transforms(j)
        T["can"] = T["wrist"]                      # gripped can rides with the wrist (identity while it stands at START)
        sc = Scene([p for p in parts if not (no_can and p["name"] == "test_can")], T)
        line = []
        for w in W:
            c, g, r = w["c"], w["g"], w["r"]
            s_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
            Ltot = s_[-1]
            worst = (1e9, None, None)
            for i in range(0, len(c), 2):
                if s_[i] < END_SKIP or s_[i] > Ltot - END_SKIP:
                    continue
                if g[i] == "loop" and pi_ != 0:
                    continue
                pt = trsf_pt(T[g[i]] if g[i] != "loop" else T["fixed"], c[i])
                gap, who = sc.clearance(pt, r)
                if gap < worst[0]:
                    worst = (gap, who, tuple(round(v, 1) for v in pt))
            worst_all.setdefault(w["name"], []).append(worst[0])
            if worst[0] < CLEAR_MIN:
                ok = False
                line.append(f"    FAIL {w['name']}: {worst[0]:.2f} mm to {worst[1]} at {worst[2]}")
        rep.append(f"  {lab:20s} " + ("PASS" if not line else "FAIL"))
        rep += line
    rep.append("")
    rep.append("  closest approach over all poses:")
    for w in W:
        rep.append(f"    {w['name']:46s} {min(worst_all[w['name']]):6.2f} mm")
    rep.append("")

    # 2. service loops: modelled loop length vs the length the motion needs
    rep.append("Service loops (loop length between the last rigid points on each side):")
    j_all = [M.joints_from_commands(*ps[1:5]) for ps in POSES]
    for w in W[:3]:
        c, g = w["c"], w["g"]
        segs, i = [], 0
        while i < len(g):
            if g[i] == "loop":
                k = i
                while k < len(g) and g[k] == "loop":
                    k += 1
                segs.append((i - 1, k, g[i - 1], g[k] if k < len(g) else g[-1]))
                i = k
            else:
                i += 1
        for i0, i1, ga, gb in segs:
            kind = {"wrist": "wrist", "lift": "lift", "turret": "turn"}[ga]
            L_loop = length(c[i0:i1 + 1])
            need = loop_need(kind, c[i0], c[i1], j_all + [M.joints_from_commands(FW["TURN_START"] - d, FW["LIFT_UP"], FW["WRIST_FLIP"], FW["GRIP_CLOSED"]) for d in (30, 45, 60)])
            f = L_loop / need
            good = f >= 1.25
            ok &= good
            what = {"wrist": "wrist roll 180°", "lift": "lift 15.3 mm", "turn": "turn 90°"}[kind]
            rep.append(f"  {w['name']:24s} {what:16s} loop {L_loop:5.0f} mm, motion needs {need:5.0f} mm "
                       f"-> {f:4.2f}x {'PASS' if good else 'FAIL'} (>= 1.25x so it never pulls tight)")
    rep.append("")

    # 3. lead lengths vs what you buy
    rep.append("Lead length (servo exit -> breadboard header, along the route):")
    stock = dict(grip=("SG90", 250, 500), wrist=("MG90S", 250, 300), lift=("MG90S", 250, 300), turn=("MG996R", 300, 300))
    for w in W[:4]:
        L_ = length(w["c"])
        nm, s0, ext = stock[w["servo"]]
        have = s0 + ext - 15                       # + one extension, minus the plug overlap
        rep.append(f"  {w['name']:46s} {L_:5.0f} mm; {nm} lead {s0} + {ext} mm extension = {have} mm "
                   f"-> {'PASS' if have >= L_ * 1.1 else 'FAIL'} ({have - L_:.0f} mm spare, tuck the spare in the tray)")
        ok &= have >= L_ * 1.1
    rep.append("")
    rep.append("  (stock lead lengths are the usual 250 / 300 mm  VERIFY on the servos you get)")
    rep.append("")
    rep.append("Tie points: small zip ties on adhesive mounts (or a dab of hot glue) at the arm beam, carriage side,")
    rep.append("back of the spine, base floor and tray floor. The loops (wrist, lift, turn) are left free.")
    rep.append("")
    rep.append("RESULT: " + ("ALL PASS" if ok else "FAIL"))
    open(os.path.join(OUT, "wiring_report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))

    # mesh for the 360 page (home pose as modelled: GRIP)
    mesh = dict(parts=[], wires=[], labels=LABELS)
    col = {"fixed": "#b9c2cc", "turret": "#7f9cc0", "crank": "#7f9cc0", "lift": "#7aa7d6", "wrist": "#3d7be0",
           "finger_L": "#e8b923", "finger_R": "#e8b923", "can": "#c0202a"}
    elec = {"arduino_uno": "#1b6fae", "buck_XL4015": "#2e3a87", "mini_breadboard": "#f4f4f0", "capacitor_1000uF": "#2b2b6e",
            "start_button": "#d03030", "status_led": "#30c030", "dc_jack": "#222222", "turntable_servo_MG996R": "#2a2a2a",
            "lift_servo_MG90S": "#2a2a2a", "wrist_servo": "#2a2a2a", "gripper_servo_SG90": "#2a5fd0"}
    for p in parts:
        v, f = p["shape"].val().tessellate(0.15, 0.3)
        mesh["parts"].append(dict(name=p["name"], group=p["group"], color=elec.get(p["name"], col.get(p["group"], "#999999")),
                                  solid=p["name"] in elec, v=[round(c, 2) for q in v for c in (q.x, q.y, q.z)],
                                  f=[i for t in f for i in t]))
    for w in W:
        v, f = tube(w["c"], w["r"])
        mesh["wires"].append(dict(name=w["name"], color=w["color"], v=[round(c, 2) for c in v.ravel()], f=[int(i) for i in f]))
    json.dump(mesh, open(os.path.join(BUILD, "wiring_mesh.json"), "w"), separators=(",", ":"))

    # STEP of the harness (one swept solid per wire)
    asm = cq.Assembly(name="wiring")
    nbad = 0
    for i, w in enumerate(W):
        try:
            pieces = sweep_wire(w["c"], w["r"])
            nm = f"w{i:02d}_" + "".join(ch if ch.isalnum() else "_" for ch in w["name"])[:40]
            asm.add(cq.Workplane("XY").add(cq.Compound.makeCompound(pieces)), name=nm, color=cq.Color(w["color"]))
        except Exception as e:  # noqa: BLE001
            nbad += 1
            print("sweep failed:", w["name"], e)
    asm.export(os.path.join(OUT, "wiring_harness.step"))
    print(f"wrote cad/wiring/wiring_harness.step ({len(W) - nbad} wires), wiring_report.txt, backend/cad/build/wiring_mesh.json")
    sys.exit(0 if ok else 1)


LABELS = [
    [1, "Wrist loop: lets the claw flip 180°", [-27.5, 47.0, 60.0]],
    [2, "Tied along the arm and carriage", [-28.5, 10.0, 77.0]],
    [3, "Lift loop: takes the 15 mm lift", [-15.0, -13.0, 70.0]],
    [4, "Through the spine's cable window", [-1.0, -21.0, 94.0]],
    [5, "Down the back, out the turret notch", [-1.0, -36.5, 56.5]],
    [6, "Turn loop: takes the 90° turn", [-20.0, -53.0, 57.0]],
    [7, "Into the base through the cable hole", [-34.5, -35.0, 50.0]],
    [8, "Out the back wall into the tray", [-4.0, -76.0, 11.0]],
    [9, "Servo headers on the breadboard (5.8 V rail)", [20.0, -92.0, 15.0]],
    [10, "Uno: D4 D5 D6 D9 D10 D13, GND, VIN", [-30.0, -112.0, 21.0]],
    [11, "Buck: 12 V in, 5.8 V out", [35.0, -138.0, 24.0]],
    [12, "Panel: START, LED, 12 V jack", [40.0, -171.0, 28.0]],
]

if __name__ == "__main__":
    main()
