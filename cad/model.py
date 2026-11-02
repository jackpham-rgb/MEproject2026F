"""Concept A detail model: every part, its group, material, and the robot's kinematics.

Units: millimetres. World frame at the HOME pose: origin = turntable axis on the table
(the robot's location, Figure 2 vertex), +Y -> START can (0, 127), +X -> TARGET can (127, 0), +Z up.

Groups (one rigid body each, so they map 1:1 to Fusion/SolidWorks components and joints):
  fixed    base (with bearing tower), 6807 bearing, electronics tray, MG996R, Arduino, buck, breadboard
  turret   turret plate + hub, horn, rods, spine, top cap, lift servo + bracket
  crank    lift crank (rotates about the lift-servo shaft, an X-axis line)
  lift     carriage, 4x LM6UU, beam, wrist bracket, wrist servo, link
  wrist    wrist horn, flange, gripper plates, posts, bumper, gripper servo, axles
  finger_L / finger_R   gear + arm + pad (each rotates about its axle, a Z line in the wrist frame)
  can      the test can

Purchased-part envelopes use typical datasheet dimensions (marked VERIFY): measure your
actual parts with calipers before printing and edit the numbers in P below.
"""
import math

import cadquery as cq
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec

IN = 25.4

# --------------------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------------------
P = dict(
    # standard empty 12 oz Coca-Cola can (355 ml): 66.2 mm body, 122.2 mm tall, tapered neck and base
    can_d=66.2, can_h=122.2, can_r_pos=5.0 * IN,
    grip_z=122.2 / 2,                       # wrist roll axis height = can mid-height (61.1)
    base_w=152.0, base_h=52.0, base_wall=3.0, base_top=4.0,
    sweep_a0=-30.0, sweep_a1=145.0, tower_r=28.0,       # base is cut away in this sector (arm, open arms, can)
    servo_ang=225.0,                                     # MG996R body points away from the sweep
    bear_id=35.0, bear_od=47.0, bear_w=7.0,              # 6807-2RS deep-groove bearing
    tray_len=95.0, tray_t=4.0, tray_wall_h=28.0,
    turret_r=40.0, turret_t=6.0, turret_front=22.0,
    rod_x=17.0, rod_y=12.0, rod_d=6.0, rod_top=168.0, rod_len=112.0,
    lm_od=12.0, lm_len=19.0,
    car_x=26.0, car_y0=2.0, car_y1=22.0, car_z0=69.0, car_h=62.0,
    beam_w=20.0, beam_t=10.0,
    lift_crank=20.0, lift_theta0=-22.5, lift_span=45.0,             # crank +-22.5 deg -> 15.3 mm
    lift_servo_tip=(-3.0, -6.0, 150.0),
    wrist_tip_y=58.5,
    plate_x=31.0, plate_y1=91.0, plate_bot=(68.5, 72.5), plate_top=(79.5, 82.0),
    pivot_x=8.1, pivot_y=83.0, gear_r=8.0, finger_z=(73.0, 79.0), pad_z=(46.0, 86.0),        # 40 mm pads centred near can mid-height (59.7)
    pad_t=5.5, pad_half_angle=28.0, grip_open_angle=75.0,
    print_density=1.27, print_fill=0.60,                             # PETG, ~3 walls + 30 % infill
)
P["can_y"] = P["can_r_pos"]
P["base_top_z"] = P["base_h"]
P["turret_z0"] = 53.0                                                 # servo tip 50 + 3 mm horn
P["turret_z1"] = P["turret_z0"] + P["turret_t"]                       # 59
P["car_z1"] = P["car_z0"] + P["car_h"]                                # 129
P["lift_stroke"] = P["lift_crank"] * (math.sin(math.radians(P["lift_theta0"] + P["lift_span"]))
                                      - math.sin(math.radians(P["lift_theta0"])))

# 3D-print tolerances (PETG, 0.4 mm nozzle). Every hole below is sized from this table.
# Print tolerance_coupon.stl first and adjust if your printer runs tight or loose.
# Fasteners: Harbor Freight 57-pc stainless machine-screw kit #67675 (pan-head Phillips, NO nuts):
#   12x #6-32x1/2, 10x #8-32x1/2, 10x #8-32x3/4, 10x #10-24x3/4, 10x 1/4-20x3/4, 5x 1/4-20x1.
# No nuts -> screws self-thread into printed pilot holes (fine in PETG for these loads).
TOL = dict(
    n6_clear=3.9,      # #6-32 (3.51 mm major) passes freely
    n6_pilot=2.9,      # #6-32 cuts its own thread
    n6_head=7.2,       # pan-head pocket (head 6.6 mm)
    n8_clear=4.6,      # #8-32 (4.17 mm major)
    n8_pilot=3.5,
    servo_pilot=1.7,   # self-tapping screws from the servo bags
    rod_press=6.0,     # 6 mm rod: nominal hole prints ~0.1 mm under -> light press fit
    lm_press=12.15,    # LM6UU 12 mm OD: +0.15 -> snug press fit
    run_bore=3.9,      # gear on a #6 screw axle: running clearance
    peg=2.8,           # printed peg for 3.2 mm board holes (Uno); the buck uses 2.6 mm pegs for its 3.0 mm holes
    bear_shaft=34.95,  # printed hub into the 35 mm bearing bore (prints ~+0.05)
    bear_housing=47.1, # bearing outer race into the printed tower
    gap_moving=0.5,    # minimum gap between parts that move relative to each other
    gear_backlash=0.2, # added to the gear centre distance
)

# Firmware angles (kept equal to firmware/concept_a/concept_a.ino)
FW = dict(TURN_START=135, TURN_TARGET=45, LIFT_DOWN=30, LIFT_UP=75, WRIST_UP=0, WRIST_FLIP=180,
          GRIP_OPEN=20, GRIP_CLOSED=95, GRIP_RELEASE=70)   # release opens only 25 deg (gripper is upside down there)

COLORS = dict(print="#3d7be0", print2="#e0a33d", tpu="#2f2f2f", servo="#1f2329", steel="#b8bcc2",
              pcb="#1d6b4a", alu="#c0202a", brass="#c9a24a")


# --------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def cyl(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def hole_z(wp, pts, d, z0, z1):
    for x, y in pts:
        wp = wp.cut(cyl(x, y, d / 2, z0, z1))
    return wp


def trsf_axes(origin, xdir, zdir):
    """Transform mapping local (x along xdir, z along zdir) to world, local origin -> origin."""
    xd = [c / math.sqrt(sum(v * v for v in xdir)) for c in xdir]
    zd = [c / math.sqrt(sum(v * v for v in zdir)) for c in zdir]
    yd = [zd[1] * xd[2] - zd[2] * xd[1], zd[2] * xd[0] - zd[0] * xd[2], zd[0] * xd[1] - zd[1] * xd[0]]
    t = gp_Trsf()
    t.SetValues(xd[0], yd[0], zd[0], origin[0], xd[1], yd[1], zd[1], origin[1], xd[2], yd[2], zd[2], origin[2])
    return t


def moved(wp, t):
    return cq.Workplane("XY").add(wp.val().moved(cq.Location(t)))


def rot(point, direction, deg):
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(gp_Pnt(*point), gp_Dir(*direction)), math.radians(deg))
    return t


def trans(dx, dy, dz):
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(dx, dy, dz))
    return t


def mul(*ts):
    """mul(a, b, c) = a*b*c (c applied first)."""
    r = gp_Trsf()
    for t in ts:
        r = r.Multiplied(t)
    return r


def cyl_dir(a, d, r, L):
    """Cylinder of radius r starting at point a, running L along direction d (any axis)."""
    perp = (1, 0, 0) if abs(d[0]) < 0.9 else (0, 1, 0)
    return moved(cyl(0, 0, r, 0, L), trsf_axes(a, perp, d))


def bar(p1, p2, w, z0, z1):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    b = cq.Workplane("XY").box(L + w, w, z1 - z0).translate(((x1 + x2) / 2, (y1 + y2) / 2, (z0 + z1) / 2))
    return b.rotate(((x1 + x2) / 2, (y1 + y2) / 2, 0), ((x1 + x2) / 2, (y1 + y2) / 2, 1),
                    math.degrees(math.atan2(y2 - y1, x2 - x1)))


# --------------------------------------------------------------------------------------
# Purchased-part envelopes (typical dims, VERIFY with calipers)
# --------------------------------------------------------------------------------------
def micro_servo_local(mounting_holes=True):
    """SG90 / MG90S class. Local frame: spline tip at origin, spline along +Z,
    body along +X from the shaft (shaft 5.95 from the body end)."""
    L, W, Hb = 22.8, 12.2, 22.7
    x0, x1 = -5.95, L - 5.95
    body = box(x0, x1, -W / 2, W / 2, -28.5, -5.8)
    flange_z = -28.5 + 15.9
    tabs = box(x0 - 4.85, x1 + 4.85, -W / 2, W / 2, flange_z, flange_z + 2.5)
    if mounting_holes:
        cx = (x0 + x1) / 2
        for hx in (cx - 13.75, cx + 13.75):
            tabs = tabs.cut(cyl(hx, 0, 1.0, flange_z - 1, flange_z + 4))
    boss = cyl(0, 0, 5.8, -5.8, -4.0)
    spline = cyl(0, 0, 2.4, -4.0, 0.0)
    return body.union(tabs).union(boss).union(spline)


def mg996r_local():
    """MG996R. Local: spline tip at origin along +Z, body along +X (shaft 10.2 from the end)."""
    x0, x1 = -10.2, 30.5
    body = box(x0, x1, -9.85, 9.85, -47.9, -5.0)
    fz = -47.9 + 26.5
    tabs = box(x0 - 6.9, x1 + 6.9, -9.85, 9.85, fz, fz + 2.5)
    cx = (x0 + x1) / 2
    for hx in (cx - 24.75, cx + 24.75):
        for hy in (-5, 5):
            tabs = tabs.cut(cyl(hx, hy, 2.3, fz - 1, fz + 4))
    spline = cyl(0, 0, 3.0, -5.0, 0.0)
    return body.union(tabs).union(spline)


MICRO_HOLES_X = (-5.95 + 22.8 - 5.95) / 2   # body centre x in the micro-servo local frame (5.45)


# --------------------------------------------------------------------------------------
# Part definitions
# --------------------------------------------------------------------------------------
def build_parts():
    p = P
    parts = []

    def add(name, group, shape, material, mass=None, collide=None, note=""):
        parts.append(dict(name=name, group=group, shape=shape, material=material, mass=mass,
                          collide=collide if collide is not None else shape, note=note))

    gz = p["grip_z"]

    # ---------------- fixed: base ----------------
    W, H, wall, top = p["base_w"], p["base_h"], p["base_wall"], p["base_top"]
    half = W / 2
    rt = p["tower_r"]

    def sector(r_in, a0, a1, z0, z1):
        angs = [math.radians(a0 + (a1 - a0) * i / 24) for i in range(25)]
        pts = [(r_in * math.cos(a), r_in * math.sin(a)) for a in angs] + [(400 * math.cos(a), 400 * math.sin(a)) for a in reversed(angs)]
        return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)

    def servo_frame(wp):                                  # MG996R-local -> world (body points along servo_ang)
        return wp.rotate((0, 0, 0), (0, 0, 1), p["servo_ang"])

    srv_tip_z = p["turret_z0"] - 3.0                      # 50: horn sits 3 mm under the turret plate
    flange_top = srv_tip_z - 47.9 + 26.5 + 2.5            # 31.1
    base = box(-half, half, -half, half, 0, H).cut(sector(rt, p["sweep_a0"], p["sweep_a1"], -1, H + 1))
    cavity = box(-half + wall, half - wall, -half + wall, half - wall, 0, H - top).cut(
        sector(rt - wall, p["sweep_a0"] - 3, p["sweep_a1"] + 3, -1, H + 1))
    base = base.cut(cavity)
    # bearing seat in the tower top: floor ring + pocket for the 6807 outer race
    base = base.union(cyl(0, 0, rt, H - top - 7, H - top).cut(cyl(0, 0, 18, H - top - 8, H)))
    base = base.cut(cyl(0, 0, TOL["bear_housing"] / 2, H - p["bear_w"], H + 1)).cut(cyl(0, 0, 18, H - top - 9, H + 1))
    base = base.cut(servo_frame(box(-10.7, 31.0, -10.4, 10.4, 0, srv_tip_z - 5 + 0.5)))      # MG996R body clearance
    for bx, (x0, x1), ztop in ((-14.6, (-19.6, -10.6), H - p["bear_w"] - 1),                  # stays 1 mm under the hub
                               (34.9, (30.7, 39.6), H - top)):                                  # MG996R flange blocks
        blk = box(x0, x1, -10, 10, flange_top, ztop)
        blk = hole_z(blk, [(bx, -5), (bx, 5)], TOL["n8_pilot"], flange_top - 1, flange_top + 11)   # #8-32x1/2 from below
        base = base.union(servo_frame(blk))
    for cx, cy in ((-60, -60), (60, -60)):                                                     # ballast pockets (outside the sweep)
        base = base.union(cyl(cx, cy, 12.5, 0, H - top).cut(cyl(cx, cy, 10.5, 0, H - top - 2)))
    base = base.cut(cyl(-34, -34, 7.0, H - top - 1, H + 1))                                    # cable hole from the turret
    base = base.cut(box(-15, 15, -half - 1, -half + wall + 1, 8, 22))                          # cable exit to the tray
    for x in (-50, 50):
        base = base.union(box(x - 6, x + 6, -half + wall, -half + wall + 8, 5, 14)).cut(
            cyl(x, -half + wall + 4, TOL["n6_pilot"] / 2, 0, 15))                               # tray screw #6-32x1/2 from below
    add("base", "fixed", base, "PETG", note="Print top-down (top face on the bed). The arm/can sweep sector is cut away, "
        "leaving a 28 mm tower that holds the 6807 bearing (47.1 mm press pocket). MG996R: 4x #8-32x1/2 up into "
        "pilot holes. Corner pockets take steel washers as ballast.")

    # ---------------- fixed: electronics tray ----------------
    ty0, ty1 = -half - p["tray_len"], -half
    tray = box(-half, half, ty0, ty1, 0, p["tray_t"])
    tray = tray.union(box(-half, half, ty0, ty0 + 3, 0, p["tray_wall_h"]))              # front panel
    tray = tray.union(box(-half, -half + 3, ty0, ty1, 0, 12)).union(box(half - 3, half, ty0, ty1, 0, 12))
    for x in (-50, 50):                                                                  # tabs that slide under the base wall
        tray = tray.union(box(x - 6, x + 6, ty1, ty1 + 9, 0, 5))
        tray = tray.cut(cyl(x, -half + wall + 4, TOL["n6_clear"] / 2, -1, 6)).cut(cyl(x, -half + wall + 4, TOL["n6_head"] / 2, -1, 2.6))
    # panel: start button (12 mm), LED (5 mm), DC jack (8 mm)
    for (x, d) in ((15, 12.2), (40, 5.2), (65, 8.2)):
        tray = tray.cut(cyl_dir((x, ty0 - 1, 15), (0, 1, 0), d / 2, 5))
    # Arduino Uno standoffs (board origin at (-72, ty0 + 8)), hole pattern from the Uno R3 drawing
    uno_o = (-72.0, ty0 + 8.0)
    uno_holes = [(14.0, 2.5), (15.3, 50.7), (66.1, 7.6), (66.1, 35.5)]
    for hx, hy in uno_holes:                                                             # standoff + 3 mm peg (no #4 screws in the kit)
        x, y = uno_o[0] + hx, uno_o[1] + hy
        tray = tray.union(cyl(x, y, 3.0, p["tray_t"], p["tray_t"] + 6)).union(cyl(x, y, TOL["peg"] / 2, p["tray_t"] + 6, p["tray_t"] + 9))
    # buck converter standoffs (XL4015 5 A module, 54 x 23, holes ~48 x 17  VERIFY)
    bk_o = (8.0, ty0 + 10.0)
    for hx, hy in ((3, 3), (51, 3), (3, 20), (51, 20)):
        x, y = bk_o[0] + hx, bk_o[1] + hy
        tray = tray.union(cyl(x, y, 3.0, p["tray_t"], p["tray_t"] + 5)).union(cyl(x, y, 1.3, p["tray_t"] + 5, p["tray_t"] + 8))
    add("electronics_tray", "fixed", tray, "PETG", note="2x #6-32x1/2 up through the tabs into the base. "
        "The Uno and the buck sit on printed pegs (dab of hot glue); mini breadboard is self-adhesive.")

    # ---------------- fixed: purchased ----------------
    bear = cyl(0, 0, p["bear_od"] / 2, H - p["bear_w"], H).cut(cyl(0, 0, p["bear_id"] / 2, H - p["bear_w"] - 1, H + 1))
    add("bearing_6807", "fixed", bear, "buy", mass=30.0, note="6807-2RS, 35 x 47 x 7 mm: carries the turret")
    srv = servo_frame(moved(mg996r_local(), trsf_axes((0, 0, srv_tip_z), (1, 0, 0), (0, 0, 1))))
    add("turntable_servo_MG996R", "fixed", srv, "buy", mass=55.0)
    uno = box(uno_o[0], uno_o[0] + 68.6, uno_o[1], uno_o[1] + 53.3, p["tray_t"] + 6, p["tray_t"] + 7.6)
    uno = uno.union(box(uno_o[0] - 6, uno_o[0] + 10, uno_o[1] + 32, uno_o[1] + 44, p["tray_t"] + 7.6, p["tray_t"] + 18.6))
    add("arduino_uno", "fixed", uno, "buy", mass=25.0)
    add("buck_XL4015", "fixed", box(bk_o[0], bk_o[0] + 54, bk_o[1], bk_o[1] + 23, p["tray_t"] + 5, p["tray_t"] + 19),
        "buy", mass=25.0, note="XL4015 5 A buck set to 5.8 V for the servos; MG996R power on its OUT terminals  VERIFY footprint")
    add("mini_breadboard", "fixed", box(8, 55, ty0 + 45, ty0 + 80, p["tray_t"], p["tray_t"] + 8.5), "buy", mass=10.0,
        note="5.8 V servo rail from the buck + 1000 uF capacitor")

    # ---------------- turret ----------------
    tz0, tz1 = p["turret_z0"], p["turret_z1"]
    tp = cyl(0, 0, p["turret_r"], tz0, tz1).intersect(box(-60, 60, -60, p["turret_front"], tz0 - 1, tz1 + 1))   # "D" plate
    tp = tp.union(cyl(0, 0, TOL["bear_shaft"] / 2, H - p["bear_w"] + 0.6, tz0))                # hub in the bearing bore (0.6 mm over the servo)
    tp = tp.union(cyl(0, 0, 19.5, H, tz0))                                                      # shoulder on the inner race
    tp = tp.cut(cyl(0, 0, 13.5, H - p["bear_w"] - 1, tz0))                                      # room for the horn
    tp = tp.cut(box(-6, 6, -41, -33, tz0 - 1, tz1 + 1))                                         # cable notch at the back
    for a in (45, 135, 225, 315):                                                        # horn: servo-bag screws
        tp = tp.cut(cyl(8 * math.cos(math.radians(a)), 8 * math.sin(math.radians(a)), TOL["servo_pilot"] / 2, tz0 - 1, tz1 + 1))
    rx, ry = p["rod_x"], p["rod_y"]
    for sx in (-1, 1):                                                                   # rod bosses
        tp = tp.union(cyl(sx * rx, ry, 7.0, tz1, tz1 + 6))
        tp = tp.cut(cyl(sx * rx, ry, TOL["rod_press"] / 2, tz0 + 2, tz1 + 7))             # blind: rod sits on the bottom
    tp = tp.union(box(-25, 25, -24, -8, tz1, tz1 + 4))                                  # spine foot
    tp = tp.cut(cyl(-15, -16, TOL["n6_pilot"] / 2, tz0 + 1, tz1 + 5)).cut(cyl(15, -16, TOL["n6_pilot"] / 2, tz0 + 1, tz1 + 5))
    add("turret_plate", "turret", tp, "PETG", note="D-shaped plate + hub. The hub presses into the 6807 bore (34.95 mm) and "
        "the shoulder rests on the inner race. Horn: 4 servo-bag screws. Rods press into blind 6.0 mm holes. "
        "Spine: 2x #6-32x1/2 from above.")
    add("turntable_horn", "turret", cyl(0, 0, 12.5, tz0 - 3, tz0), "buy", mass=4.0, note="MG996R round horn (25T)")
    for sx, nm in ((-1, "rod_L"), (1, "rod_R")):
        add(nm, "turret", cyl(sx * rx, ry, 2.99, tz0 + 2, tz0 + 2 + p["rod_len"]), "buy",
            mass=math.pi * 0.3 ** 2 * p["rod_len"] / 10 * 7.85, note="6 mm steel rod, cut to 112 mm, captured in blind holes")
    spine = box(-25, 25, -24, -18, tz1 + 4, p["rod_top"] - 6)
    spine = spine.union(box(-25, 25, -24, -12, tz1, tz1 + 4)).cut(cyl(-15, -16, TOL["n6_clear"] / 2, tz1 - 1, tz1 + 6)).cut(cyl(15, -16, TOL["n6_clear"] / 2, tz1 - 1, tz1 + 6))
    spine = spine.cut(cyl(-15, -21, TOL["n6_pilot"] / 2, p["rod_top"] - 18, p["rod_top"])).cut(cyl(15, -21, TOL["n6_pilot"] / 2, p["rod_top"] - 18, p["rod_top"]))
    spine = spine.cut(box(-8, 8, -25, -17, tz1 + 12, tz1 + 50))                          # cable window
    # lift-servo bracket: frame behind the servo tabs (servo body x 2.8..25.5, tabs at x 7.1..9.6)
    ltx, lty, ltz = p["lift_servo_tip"]
    brk = box(9.6, 13.6, -18, 0.1, ltz - 22, ltz + 11).cut(box(9, 14, -12.4, 0.4, ltz - 16.85 - 0.3, ltz + 5.95 + 0.3))
    for hz in (ltz - (MICRO_HOLES_X - 13.75), ltz - (MICRO_HOLES_X + 13.75)):      # servo tab screws (M2)
        brk = brk.cut(cyl_dir((9, -6, hz), (1, 0, 0), 0.85, 6))
    spine = spine.union(brk)
    add("spine", "turret", spine, "PETG", note="Back spine of the column + lift-servo bracket. 2x #6-32x1/2 into the "
        "turret plate, top cap screws thread into its top. Lift servo: 2 servo-bag screws.")
    cap = box(-27, 27, -24, 20, p["rod_top"] - 6, p["rod_top"])
    for sx in (-1, 1):
        cap = cap.cut(cyl(sx * rx, ry, TOL["rod_press"] / 2, p["rod_top"] - 7, p["rod_top"] - 1))      # blind
        cap = cap.cut(cyl(sx * 15, -21, TOL["n6_clear"] / 2, p["rod_top"] - 7, p["rod_top"] + 1))
    add("top_cap", "turret", cap, "PETG", note="Captures the rod tops (blind 6.0 mm holes); 2x #6-32x1/2 into the spine.")
    # lift servo: tip at (ltx, lty, ltz), shaft pointing -X, body along -Z
    lsrv = moved(micro_servo_local(), trsf_axes((ltx, lty, ltz), (0, 0, -1), (-1, 0, 0)))
    add("lift_servo_MG90S", "turret", lsrv, "buy", mass=13.4)

    # ---------------- crank (about the lift-servo shaft) ----------------
    R = p["lift_crank"]
    th0 = math.radians(p["lift_theta0"])
    pin = (lty + R * math.cos(th0), ltz + R * math.sin(th0))
    crank2d = cq.Workplane("XY").polyline(
        [(lty, ltz - 3.5), (pin[0], pin[1] - 3.5), (pin[0], pin[1] + 3.5), (lty, ltz + 3.5)]).close().extrude(2.5)
    crank2d = crank2d.union(cq.Workplane("XY").center(lty, ltz).circle(5).extrude(2.5))
    crank = moved(crank2d, trsf_axes((ltx - 2.5, 0, 0), (0, 1, 0), (1, 0, 0)))
    add("lift_crank", "crank", crank, "buy", mass=1.0, note="MG90S single-arm horn, trimmed to a 20 mm pin radius")

    # ---------------- lift ----------------
    cx_, cy0, cy1, cz0, cz1 = p["car_x"], p["car_y0"], p["car_y1"], p["car_z0"], p["car_z1"]
    car = box(-cx_, cx_, cy0, cy1, cz0, cz1)
    lm_z = [(cz0, cz0 + p["lm_len"]), (cz1 - p["lm_len"], cz1)]
    for sx in (-1, 1):
        car = car.cut(cyl(sx * rx, ry, 3.6, cz0 - 1, cz1 + 1))                           # rod clearance
        for z0, z1 in lm_z:
            car = car.cut(cyl(sx * rx, ry, TOL["lm_press"] / 2, z0, z1))                  # LM6UU press pockets
    car = car.union(box(-11.5, -8.5, 8, 16, cz1 - 4, cz1 + 6)).cut(
        cyl_dir((-12.5, 12, cz1 + 2), (1, 0, 0), TOL["n6_pilot"] / 2, 5))                 # link pivot: #6-32x1/2 threads in
    # arm beam + wrist bracket (wrist servo body passes through the bracket window)
    by1 = p["wrist_tip_y"] - 28.5 + 15.9                                                   # tab plane y (45.9)
    beam = box(-p["beam_w"] / 2, p["beam_w"] / 2, cy1 - 1, by1, cz0, cz0 + p["beam_t"])
    brkt = box(-11, 11, by1 - 4, by1, gz - 24, cz0 + p["beam_t"])
    w_body_z = (gz + 5.95 - 22.8, gz + 5.95)
    brkt = brkt.cut(box(-6.4, 6.4, by1 - 5, by1 + 1, w_body_z[0] - 0.3, w_body_z[1] + 0.3))
    for hz in (gz - (MICRO_HOLES_X - 13.75), gz - (MICRO_HOLES_X + 13.75)):           # wrist-servo tab screws (M2)
        brkt = brkt.cut(cyl_dir((0, by1 - 5, hz), (0, 1, 0), 0.85, 7))
    car = car.union(beam).union(brkt)
    add("carriage_arm", "lift", car, "PETG", note="Carriage + arm + wrist bracket in one print. 4x LM6UU press-fit "
        "(12.15 mm pockets, 43 mm apart on each rod). Wrist servo: 2 servo-bag screws. Link pivot: #6-32x1/2.")
    for sx in (-1, 1):
        for i, (z0, z1) in enumerate(lm_z):
            lm = cyl(sx * rx, ry, p["lm_od"] / 2, z0, z1).cut(cyl(sx * rx, ry, 3.0, z0 - 1, z1 + 1))
            add(f"LM6UU_{'L' if sx < 0 else 'R'}{i + 1}", "lift", lm, "buy", mass=8.0)
    link = box(-8.5, -5.5, pin[0] - 3.5, pin[0] + 3.5, cz1 + 2 - 3.5, pin[1] + 3.5)
    link = link.cut(cyl_dir((-9, 12, cz1 + 2), (1, 0, 0), TOL["n6_clear"] / 2, 4)).cut(cyl_dir((-9, pin[0], pin[1]), (1, 0, 0), TOL["servo_pilot"] / 2, 4))
    add("lift_link", "lift", link, "PETG", note="Link crank -> carriage. Carriage end: #6-32x1/2 pivot (3.9 mm running hole). "
        "Crank end: servo-bag screw through the horn into the link.")
    wsrv = moved(micro_servo_local(), trsf_axes((0, p["wrist_tip_y"], gz), (0, 0, -1), (0, 1, 0)))
    add("wrist_servo", "lift", wsrv, "buy", mass=13.0, note="micro servo that reaches 180 deg (or 270 deg type)")

    # ---------------- wrist (rotates about the Y line x=0, z=grip_z) ----------------
    wy = p["wrist_tip_y"]
    horn = cyl_dir((0, wy - 2.5, gz), (0, 1, 0), 10, 2.5)
    add("wrist_horn", "wrist", horn, "buy", mass=1.0, note="micro-servo round horn")
    px, py1 = p["plate_x"], p["plate_y1"]
    pb, pt = p["plate_bot"], p["plate_top"]
    gr = box(-14, 14, wy, wy + 3, gz - 13, pb[1])                                         # flange on the horn
    for a in (45, 135, 225, 315):
        gr = gr.cut(cyl_dir((7 * math.cos(math.radians(a)), wy - 1, gz + 7 * math.sin(math.radians(a))), (0, 1, 0), 0.85, 6))
    gr = gr.union(box(-px, px, wy, py1, pb[0], pb[1]))                                    # bottom plate (4 mm: axle thread)
    gr = gr.union(box(-px, px, wy, py1, pt[0], pt[1]))                                    # top plate
    for x in (-15, 0, 15):                                                                # back posts (inside the finger swing)
        gr = gr.union(box(x - 3, x + 3, wy, wy + 6, pb[1], pt[0]))
    pvx, pvy = p["pivot_x"], p["pivot_y"]
    gr = gr.cut(cyl(pvx, pvy, TOL["n6_clear"] / 2, pt[0] - 1, pt[1] + 1))                 # right axle: clear in the top plate
    gr = gr.cut(cyl(pvx, pvy, TOL["n6_pilot"] / 2, pb[0] - 1, pb[1] + 1))                 # ... threads into the bottom plate
    gr = gr.cut(cyl(-pvx, pvy, 6.1, pt[0] - 1, pt[1] + 1))                                # servo spline + boss through top plate
    # gripper servo posts (servo tabs at z = pt1 + 0.5 + 6.8)
    gs_face = pt[1] + 0.5
    tab_z = gs_face - 5.8 + 10.1                                                          # underside of the servo tabs
    gs_cx = -pvx - MICRO_HOLES_X
    for hx in (gs_cx - 13.75, gs_cx + 13.75):
        gr = gr.union(box(hx - 3, hx + 3, pvy - 3, pvy + 3, pt[1], tab_z)).cut(cyl(hx, pvy, 0.85, tab_z - 6, tab_z + 1))
    add("gripper_frame", "wrist", gr, "PETG", note="Flange + 2 plates + posts in one print. Wrist horn: 4 servo-bag "
        "screws. Right gear axle: #6-32x1/2 from the top. Left gear rides on the gripper-servo horn. Servo: 2 servo-bag screws.")
    add("can_bumper", "wrist", box(-4.5, 4.5, py1, py1 + 2.4, pb[0], pt[1]), "silicone", note="can stop, cut from the 3/32 in silicone sheet: place the can against it")
    gsrv = moved(micro_servo_local(), trsf_axes((-pvx, pvy, gs_face - 5.8), (-1, 0, 0), (0, 0, -1)))
    add("gripper_servo_SG90", "wrist", gsrv, "buy", mass=9.0)
    add("axle_R", "wrist", cyl(pvx, pvy, 1.75, pt[1] - 12.7, pt[1]), "buy", mass=1.6, note="#6-32x1/2 (kit), right-gear axle")

    # ---------------- fingers (right built, left mirrored) ----------------
    fz0, fz1 = p["finger_z"]
    cy = p["can_y"]
    rc = p["can_d"] / 2
    pts = [(pvx, pvy), (pvx + 9, pvy + 3), (rc + 4.5, 100.0), (rc + 4.5, 150.0)]
    arm = cyl(pvx, pvy, 5.0, fz0, fz1)
    for a, b in zip(pts[:-1], pts[1:]):
        arm = arm.union(bar(a, b, 5.0, fz0, fz1))
    pz0, pz1 = p["pad_z"]
    ha = math.radians(p["pad_half_angle"])
    ring = cyl(0, cy, rc + p["pad_t"], pz0, pz1).cut(cyl(0, cy, rc, pz0 - 1, pz1 + 1))
    wedge = cq.Workplane("XY").workplane(offset=pz0 - 1).polyline(
        [(0, cy), (200 * math.cos(ha), cy - 200 * math.sin(ha)), (200 * math.cos(ha), cy + 200 * math.sin(ha))]).close().extrude(pz1 - pz0 + 2)
    pad = ring.intersect(wedge)
    pad = pad.union(box(rc + 2, rc + 7, cy - 13, cy + 13, pz0, pz1))
    pad = pad.cut(cyl(0, cy, rc, pz0 - 1, pz1 + 1))
    gear_disc = cyl(pvx, pvy, p["gear_r"], fz0, fz1)
    fR = arm.union(pad).union(gear_disc).cut(cyl(pvx, pvy, TOL["run_bore"] / 2, fz0 - 1, fz1 + 1))
    fL = arm.union(pad).union(gear_disc).mirror("YZ").cut(cyl(-pvx, pvy, 3.0, fz0 + 2, fz1 + 1))   # spline / horn socket
    add("finger_R", "finger_R", fR, "PETG", note="Gear (m1, 16T, pitch r 8 mm, +0.2 backlash) + arm + can pad. Print "
        "flat. Runs on a #6-32 axle (3.9 mm bore). Line the pad with the 3/32 in silicone sheet.")
    add("finger_L", "finger_L", fL, "PETG", note="Mirror of finger_R; its gear has the servo-spline socket.")

    # ---------------- tolerance test coupon (print first; not part of the assembly) ----------------
    cp = box(0, 70, 0, 22, 0, 8)
    for i, (d, lbl) in enumerate([(TOL["n6_clear"], "6c"), (TOL["n6_pilot"], "6p"), (TOL["n8_clear"], "8c"),
                                  (TOL["n8_pilot"], "8p"), (TOL["rod_press"], "rod"), (TOL["lm_press"], "lm")]):
        cp = cp.cut(cyl(6 + i * 11.3, 11, d / 2, -1, 9))
    add("tolerance_coupon", "coupon", cp.translate((-35, -260, 0)), "PETG",
        note="Holes left to right: #6 clear 3.9, #6 pilot 2.9, #8 clear 4.6, #8 pilot 3.5, rod 6.0, LM6UU 12.15. "
             "Check each fit, then edit TOL in model.py.")

    # ---------------- can ----------------
    # Coke can: standing ring 50.8 mm -> body 66.2 mm (z 9..110) -> neck -> 54/55 mm top seam
    def cone(r1, r2, z0, z1):
        return cq.Workplane("XY").add(cq.Solid.makeCone(r1, r2, z1 - z0, cq.Vector(0, cy, z0), cq.Vector(0, 0, 1)))
    can = cone(25.4, 31.0, 0, 4).union(cone(31.0, rc, 4, 9)).union(cyl(0, cy, rc, 9, 110))
    can = can.union(cone(rc, 28.6, 110, 118)).union(cone(28.6, 27.6, 118, p["can_h"]))
    add("test_can", "can", can, "can", mass=15.0, note="standard empty 12 oz Coke can, ~15 g")
    return parts


# --------------------------------------------------------------------------------------
# Kinematics: servo commands -> group transforms
# --------------------------------------------------------------------------------------
def joints_from_commands(turn, lift, wrist, grip, wrist_range=180):
    psi = -(FW["TURN_START"] - turn)                          # deg about +Z (0 at START, -90 at TARGET)
    th = P["lift_theta0"] + (lift - FW["LIFT_DOWN"]) * P["lift_span"] / (FW["LIFT_UP"] - FW["LIFT_DOWN"])
    h = P["lift_crank"] * (math.sin(math.radians(th)) - math.sin(math.radians(P["lift_theta0"])))
    phi = wrist * 180.0 / wrist_range * (wrist_range / 180.0)
    alpha = max(0.0, (FW["GRIP_CLOSED"] - grip) / (FW["GRIP_CLOSED"] - FW["GRIP_OPEN"]) * P["grip_open_angle"])
    return dict(psi=psi, theta=th, h=h, phi=phi, alpha=alpha)


def group_transforms(j):
    gz = P["grip_z"]
    _, lty, ltz = P["lift_servo_tip"]
    T_turret = rot((0, 0, 0), (0, 0, 1), j["psi"])
    T_crank = mul(T_turret, rot((0, lty, ltz), (1, 0, 0), j["theta"] - P["lift_theta0"]))
    T_lift = mul(T_turret, trans(0, 0, j["h"]))
    T_wrist = mul(T_lift, rot((0, 0, gz), (0, 1, 0), j["phi"]))
    T_fR = mul(T_wrist, rot((P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), -j["alpha"]))
    T_fL = mul(T_wrist, rot((-P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), j["alpha"]))
    I = gp_Trsf()
    return dict(fixed=I, turret=T_turret, crank=T_crank, lift=T_lift, wrist=T_wrist, finger_R=T_fR, finger_L=T_fL)


def sequence(step_samples=10):
    """The firmware run, then the return home (after the operator removes the can), as
    (label, commands, can_attached) samples. Steps named H-* run with the can removed."""
    S = dict(turn=FW["TURN_START"], lift=FW["LIFT_DOWN"], wrist=FW["WRIST_UP"], grip=FW["GRIP_OPEN"])
    steps = [("GRIP", "grip", FW["GRIP_CLOSED"], True), ("LIFT", "lift", FW["LIFT_UP"], True),
             ("FLIP", "wrist", FW["WRIST_FLIP"], True), ("TURN", "turn", FW["TURN_TARGET"], True),
             ("LOWER", "lift", FW["LIFT_DOWN"], True), ("RELEASE", "grip", FW["GRIP_RELEASE"], False),
             ("H-LIFT", "lift", FW["LIFT_UP"], False), ("H-CLOSE", "grip", FW["GRIP_CLOSED"], False),
             ("H-WRIST", "wrist", FW["WRIST_UP"], False), ("H-TURN", "turn", FW["TURN_START"], False),
             ("H-LOWER", "lift", FW["LIFT_DOWN"], False), ("H-OPEN", "grip", FW["GRIP_OPEN"], False)]
    ease = lambda s: s ** 3 * (10 - 15 * s + 6 * s * s)
    out = [("HOME", dict(S), False)]
    for label, joint, target, attached in steps:
        start = S[joint]
        for i in range(1, step_samples + 1):
            S[joint] = start + (target - start) * ease(i / step_samples)
            out.append((label, dict(S), attached if label != "GRIP" else i == step_samples))
    return out
