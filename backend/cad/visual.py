"""Realistic look for the assembly viewer and the manual: bought parts as they really look, every screw at
its hole with its insertion path, glue and ballast. Visual only: the collision / mechanics checks keep
using the simple envelopes in model.py (the details below stay inside those envelopes, or are tiny).

    python3.13 backend/cad/visual.py      (after backend/tools/make_manual.py)
      -> viewer/data/assembly.json        meshes (owner part, colour, kind printed/bought/screw/glue) + steps

Printed parts are the exact CAD parts from model.py. Positions are the HOME pose, as in the manual.
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
from model import P, TOL, box, cyl, cyl_dir, moved, trsf_axes, MICRO_HOLES_X  # noqa: E402

NOTES = json.load(open(os.path.join(ROOT, "backend", "tools", "assembly_notes.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "viewer", "data", "assembly.json")

C = dict(steel="#c9ced6", steel2="#9aa1aa", zinc="#d4d8de", black="#222326", sg90="#22346e", white="#f2f2f0",
         brass="#c9a23e", pcb_uno="#11808a", pcb_buck="#2457a8", header="#1a1a1a", red="#d42a2a", ledred="#ff3b3b",
         yellow="#e8c04a", toroid="#d9b23a", glue="#ffe14d", rubber="#2a2a2a", copper="#c87533", green="#2f9e4f",
         cream="#efece3", blue="#2c6fd1", orange_w="#e4892a", brown="#6b3b1f")


# ------------------------------------------------------------------ small builders (local frames)
def rbox(x0, x1, y0, y1, z0, z1, r=0.0):
    b = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
    if r > 0:
        b = b.edges("|Z").fillet(min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01))
    return b.translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def ring(x, y, r_out, r_in, z0, z1):
    return cyl(x, y, r_out, z0, z1).cut(cyl(x, y, r_in, z0 - 1, z1 + 1))


def star(r_out, r_in, n, z0, z1):
    pts = [((r_out if i % 2 == 0 else r_in) * math.cos(math.pi * i / n), (r_out if i % 2 == 0 else r_in) * math.sin(math.pi * i / n))
           for i in range(2 * n)]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def hexagon(r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polygon(6, 2 * r).extrude(z1 - z0)


def place(items, t):
    return [(moved(s, t), c) for s, c in items]


def micro_servo_vis(body_col, spline_col):
    """SG90 / MG90S in model.micro_servo_local's frame (spline tip at the origin, +Z; body along +X)."""
    L, W = 22.8, 12.2
    x0, x1 = -5.95, L - 5.95
    fz = -28.5 + 15.9
    body = rbox(x0, x1, -W / 2, W / 2, -32.7, -5.8, 0.8)
    tabs = rbox(x0 - 4.85, x1 + 4.85, -W / 2, W / 2, fz, fz + 2.5, 0.6)
    cx = (x0 + x1) / 2
    for s in (-1, 1):
        hx = cx + s * 13.75
        tabs = tabs.cut(cyl(hx, 0, 1.0, fz - 1, fz + 4)).cut(box(*sorted((hx + s * 0.5, hx + s * 6)), -0.5, 0.5, fz - 1, fz + 4))   # hole + slot
    top = cyl(0, 0, 5.8, -5.8, -4.0).union(cyl(6.4, 0, 3.2, -5.8, -4.9))                  # output boss + gear hump
    spline = star(2.4, 2.1, 21, -4.0, 0.0).cut(cyl(0, 0, 0.8, -2, 0.1))
    label = box(x0 + 2, x1 - 2, W / 2, W / 2 + 0.15, -24, -10)
    wires = [cyl_dir((x1, (i - 1) * 1.2, -26.5), (1, 0, 0), 0.55, 9) for i in range(3)]
    return ([(body.union(tabs).union(top), body_col), (spline, spline_col), (label, C["white"])]
            + list(zip(wires, (C["brown"], C["red"], C["orange_w"]))))


def mg996r_vis():
    x0, x1 = -10.2, 30.5
    fz = -42.9 + 26.5
    body = rbox(x0, x1, -9.85, 9.85, -42.9, -4.8, 1.2)
    tabs = rbox(x0 - 6.9, x1 + 6.9, -9.85, 9.85, fz, fz + 2.5, 1.0)
    cx = (x0 + x1) / 2
    for s in (-1, 1):
        hx = cx + s * 24.75
        for hy in (-5, 5):
            tabs = tabs.cut(cyl(hx, hy, 2.3, fz - 1, fz + 4))
        tabs = tabs.cut(box(*sorted((hx + s * 2, hx + s * 8)), -1.2, 1.2, fz - 1, fz + 4))
    hump = cyl(0, 0, 7.0, -5.0, -3.2)
    spline = star(3.0, 2.7, 25, -3.2, 0.0).cut(cyl(0, 0, 1.2, -2, 0.1))
    label = box(x0 + 3, x1 - 3, 9.85, 10.0, -40, -10)
    wires = [cyl_dir((x1, (i - 1) * 1.4, -44.5), (1, 0, 0), 0.65, 10) for i in range(3)]
    return ([(body.union(tabs).union(hump), C["black"]), (spline, C["brass"]), (label, C["white"])]
            + list(zip(wires, (C["brown"], C["red"], C["orange_w"]))))


def round_horn(r, t, hole_r, rings):
    """Disc horn: disc 0..t along +Z, hub under it, rings of holes [(radius, count, start_deg)]."""
    d = cyl(0, 0, r, 0, t).union(cyl(0, 0, min(4.5, r * 0.4), -1.5, 0))
    d = d.cut(cyl(0, 0, 1.3, -2, t + 1)).cut(cyl(0, 0, 2.6, t - 0.8, t + 1))
    for rr, n, a0 in rings:
        for k in range(n):
            a = math.radians(a0 + 360 * k / n)
            d = d.cut(cyl(rr * math.cos(a), rr * math.sin(a), hole_r, -1, t + 1))
    return d


SCREW = {"#6": dict(hr=3.3, hh=2.4, sr=1.75, col=C["zinc"]), "#8": dict(hr=4.0, hh=2.8, sr=2.1, col=C["zinc"]),
         "sb": dict(hr=2.0, hh=1.4, sr=1.0, col=C["steel2"]), "M3": dict(hr=2.6, hh=1.6, sr=1.4, col=C["steel2"])}
SCREW["#6s"] = dict(SCREW["#6"])          # #6 x 1/4" pointed sheet-metal screw (any hardware store)


def screw_local(kind, L):
    """Pan-head Phillips screw: underside of the head at z=0, shank along +Z (into the part)."""
    s = SCREW[kind]
    head = cq.Workplane("XY").workplane(offset=-s["hh"]).circle(s["hr"]).extrude(s["hh"])
    try:
        head = head.faces("<Z").edges().fillet(s["hh"] * 0.45)
    except Exception:
        pass
    w = s["hr"] * 0.22
    head = head.cut(box(-s["hr"] * 0.6, s["hr"] * 0.6, -w / 2, w / 2, -s["hh"] - 1, -s["hh"] * 0.45))
    head = head.cut(box(-w / 2, w / 2, -s["hr"] * 0.6, s["hr"] * 0.6, -s["hh"] - 1, -s["hh"] * 0.45))
    shank = cyl(0, 0, s["sr"] * 0.82, 0, L)
    pitch = 1.0 if kind in ("#6", "#6s", "#8") else 0.6
    z = 0.6
    while z < L - 0.6:
        shank = shank.union(cyl(0, 0, s["sr"], z, z + pitch * 0.45))
        z += pitch
    return head.union(shank), s["col"]


def perp_of(d):
    return (1, 0, 0) if abs(d[0]) < 0.9 else (0, 1, 0)


# ------------------------------------------------------------------ the whole robot
def build():
    p = P
    parts = {pp["name"]: pp for pp in M.build_parts()}
    meshes = []          # dict(owner, kind, color, shape)

    def add(owner, kind, shape, color):
        meshes.append(dict(owner=owner, kind=kind, shape=shape, color=color))

    # printed parts: exact CAD
    for n, pp in parts.items():
        if pp["material"] == "PETG" and pp["group"] != "coupon":
            add(n, "printed", pp["shape"], "#2f72e0")
    add("test_can", "can", parts["test_can"]["shape"], "#d33a3a")

    H = p["base_h"]
    tz0, tz1 = p["turret_z0"], p["turret_z1"]
    srv_tip_z = tz0 - 3.0
    half = p["base_w"] / 2
    ty0 = -half - p["tray_len"]
    gz, wy = p["grip_z"], p["wrist_tip_y"]
    ltx, lty, ltz = p["lift_servo_tip"]
    pvx, pvy = p["pivot_x"], p["pivot_y"]
    pt = p["plate_top"]
    rx, ry = p["rod_x"], p["rod_y"]
    tt = p["tray_t"]

    # ---- bearings, rods
    add("bearing_6807", "bought", ring(0, 0, 23.5, 21.6, H - 7, H).union(ring(0, 0, 19.4, 17.5, H - 7, H)), C["steel"])
    add("bearing_6807", "bought", ring(0, 0, 21.6, 19.4, H - 6.6, H - 0.4), C["rubber"])
    cz0, cz1, ll = p["car_z0"], p["car_z1"], p["lm_len"]
    for sx in (-1, 1):
        for i, (z0, z1) in enumerate([(cz0, cz0 + ll), (cz1 - ll, cz1)]):
            nm = f"LM6UU_{'L' if sx < 0 else 'R'}{i + 1}"
            shell = ring(sx * rx, ry, 6.0, 4.4, z0, z1)
            for zz in (z0 + 3.0, z1 - 4.1):
                shell = shell.cut(ring(sx * rx, ry, 6.1, 5.6, zz, zz + 1.1))
            add(nm, "bought", shell, C["steel"])
            add(nm, "bought", ring(sx * rx, ry, 4.4, 3.05, z0, z0 + 0.8).union(ring(sx * rx, ry, 4.4, 3.05, z1 - 0.8, z1)), C["rubber"])
    for sx, nm in ((-1, "rod_L"), (1, "rod_R")):
        r = cq.Workplane("XY").workplane(offset=tz0 + 2).center(sx * rx, ry).circle(2.99).extrude(p["rod_len"]).edges().chamfer(0.5)
        add(nm, "bought", r, C["steel2"])

    # ---- servos
    srv_t = M.mul(M.rot((0, 0, 0), (0, 0, 1), p["servo_ang"]), trsf_axes((0, 0, srv_tip_z), (1, 0, 0), (0, 0, 1)))
    for s, c in place(mg996r_vis(), srv_t):
        add("turntable_servo_MG996R", "bought", s, c)
    for nm, t, bc, sc in (("lift_servo_MG90S", trsf_axes((ltx, lty, ltz), (0, 0, -1), (-1, 0, 0)), C["black"], C["brass"]),
                          ("wrist_servo", trsf_axes((0, wy, gz), (0, 0, -1), (0, 1, 0)), C["black"], C["brass"]),
                          ("gripper_servo_SG90", trsf_axes((-pvx, pvy, p["grip_spline_tip"]), (-1, 0, 0), (0, 0, -1)), C["sg90"], C["white"])):
        for s, c in place(micro_servo_vis(bc, sc), t):
            add(nm, "bought", s, c)

    # ---- horns (holes line up with the screws below)
    add("turntable_horn", "bought", moved(round_horn(12.5, 3.0, 0.9, [(8.0, 4, 45), (10.5, 8, 22.5)]), trsf_axes((0, 0, tz0 - 3), (1, 0, 0), (0, 0, 1))), C["white"])
    add("wrist_horn", "bought", moved(round_horn(10.0, 2.5, 0.7, [(7.0, 4, 45), (4.5, 4, 0)]), trsf_axes((0, wy - 2.5, gz), (1, 0, 0), (0, 1, 0))), C["white"])
    add("lift_crank", "bought", parts["lift_crank"]["shape"], C["white"])
    ghz = p["finger_z"][1] + p["ghorn_gap"]                    # SG90 round horn flat on the left gear, hub up into the servo
    add("gripper_horn", "bought", moved(round_horn(p["ghorn_r"], p["ghorn_disc"], 0.7, [(p["ghorn_screw_r"], 2, 0), (8.0, 4, 45)]),
                                        trsf_axes((-pvx, pvy, ghz + p["ghorn_disc"]), (1, 0, 0), (0, 0, -1))), C["white"])

    # ---- electronics
    uo = (-72.0, ty0 + 8.0)
    zb = tt + 6
    pcb = box(uo[0], uo[0] + 68.6, uo[1], uo[1] + 53.3, zb, zb + 1.6)
    for hx, hy in [(14.0, 2.5), (15.3, 50.7), (66.1, 7.6), (66.1, 35.5)]:
        pcb = pcb.cut(cyl(uo[0] + hx, uo[1] + hy, 1.6, zb - 1, zb + 3))
    add("arduino_uno", "bought", pcb, C["pcb_uno"])
    zt = zb + 1.6
    add("arduino_uno", "bought", box(uo[0] - 6, uo[0] + 10, uo[1] + 32, uo[1] + 44, zt, zt + 11), C["steel"])          # USB-B
    add("arduino_uno", "bought", box(uo[0] + 0.5, uo[0] + 14, uo[1] + 3.3, uo[1] + 12.3, zt, zt + 11), C["black"])      # DC jack
    hdr = (box(uo[0] + 17, uo[0] + 40, uo[1] + 50.3, uo[1] + 52.8, zt, zt + 8.5)
           .union(box(uo[0] + 41.5, uo[0] + 64, uo[1] + 50.3, uo[1] + 52.8, zt, zt + 8.5))
           .union(box(uo[0] + 26, uo[0] + 46, uo[1] + 0.5, uo[1] + 3.0, zt, zt + 8.5))
           .union(box(uo[0] + 48, uo[0] + 64, uo[1] + 0.5, uo[1] + 3.0, zt, zt + 8.5)))
    add("arduino_uno", "bought", hdr, C["header"])
    add("arduino_uno", "bought", box(uo[0] + 28, uo[0] + 63, uo[1] + 17, uo[1] + 25, zt, zt + 3.5), C["black"])          # ATmega328P
    add("arduino_uno", "bought", box(uo[0] + 5, uo[0] + 11, uo[1] + 46, uo[1] + 52, zt, zt + 2.5), C["white"])          # reset
    bo = (8.0, ty0 + 22.0)
    zb2 = tt + 5
    bpcb = box(bo[0], bo[0] + 54, bo[1], bo[1] + 23, zb2, zb2 + 1.6)
    for hx, hy in ((3, 3), (51, 3), (3, 20), (51, 20)):
        bpcb = bpcb.cut(cyl(bo[0] + hx, bo[1] + hy, 1.5, zb2 - 1, zb2 + 3))
    add("buck_XL4015", "bought", bpcb, C["pcb_buck"])
    zt2 = zb2 + 1.6
    for x in (bo[0] + 1, bo[0] + 45):
        add("buck_XL4015", "bought", box(x, x + 8, bo[1] + 6, bo[1] + 17, zt2, zt2 + 10), C["blue"])                  # screw terminals
        for yy in (bo[1] + 8.8, bo[1] + 14.2):
            add("buck_XL4015", "bought", cyl(x + 4, yy, 1.4, zt2 + 10, zt2 + 10.3), C["steel"])
    add("buck_XL4015", "bought", ring(bo[0] + 22, bo[1] + 9, 6.0, 2.5, zt2, zt2 + 7), C["toroid"])                     # inductor
    add("buck_XL4015", "bought", box(bo[0] + 30, bo[0] + 43, bo[1] + 13, bo[1] + 22, zt2, zt2 + 7), C["header"])       # display
    add("buck_XL4015", "bought", box(bo[0] + 31, bo[0] + 42, bo[1] + 14, bo[1] + 21, zt2 + 7, zt2 + 7.2), "#ff3030")
    add("buck_XL4015", "bought", box(bo[0] + 12, bo[0] + 16, bo[1] + 15, bo[1] + 22, zt2, zt2 + 9), C["blue"])         # pot
    add("buck_XL4015", "bought", cyl(bo[0] + 14, bo[1] + 18.5, 1.0, zt2 + 9, zt2 + 10.2), C["brass"])
    for xx in (bo[0] + 33, bo[0] + 39):
        add("buck_XL4015", "bought", cyl(xx, bo[1] + 6, 3.0, zt2, zt2 + 8), C["steel"])                              # caps
    bbz = tt + 8.5
    bb = box(8, 55, ty0 + 49, ty0 + 84, tt, bbz).cut(box(8.5, 54.5, ty0 + 65.6, ty0 + 67.4, bbz - 1.5, bbz + 1))
    add("mini_breadboard", "bought", bb, C["cream"])
    holes = None
    for i in range(17):
        for j in range(10):
            x = 11.3 + i * 2.54
            y = ty0 + 52 + j * 2.54 + (2.2 if j >= 5 else 0)
            h = box(x - 0.45, x + 0.45, y - 0.45, y + 0.45, bbz - 0.3, bbz + 0.05)
            holes = h if holes is None else holes.union(h)
    add("mini_breadboard", "bought", holes, "#555555")
    add("capacitor_1000uF", "bought", cyl(48, ty0 + 66, 5.0, tt + 8.5, tt + 24.5), "#1d2c5a")
    add("capacitor_1000uF", "bought", cyl(48, ty0 + 66, 5.02, tt + 9.5, tt + 23.5).intersect(box(44, 52, ty0 + 66 + 3.4, ty0 + 72, tt, tt + 30)), "#c9ccd2")
    add("capacitor_1000uF", "bought", cyl(48, ty0 + 66, 4.3, tt + 24.5, tt + 24.8), C["steel"])
    # panel parts: front face of the panel at y = ty0, inside at ty0 + 3
    x, z = 15, 15
    add("start_button", "bought", cyl_dir((x, ty0 - 2.5, z), (0, 1, 0), 7.2, 2.5), C["steel"])                          # bezel
    add("start_button", "bought", cyl_dir((x, ty0 - 5.5, z), (0, 1, 0), 4.5, 3.2), C["red"])                            # cap
    add("start_button", "bought", cyl_dir((x, ty0, z), (0, 1, 0), 5.9, 3), C["steel"])                                  # thread
    add("start_button", "bought", moved(hexagon(7.5, 0, 2.5), trsf_axes((x, ty0 + 3, z), (1, 0, 0), (0, 1, 0))), C["steel"])
    add("start_button", "bought", cyl_dir((x, ty0 + 5.5, z), (0, 1, 0), 6.0, 10.5), C["black"])
    for dx in (-2.5, 2.5):
        add("start_button", "bought", box(x + dx - 0.8, x + dx + 0.8, ty0 + 16, ty0 + 20, z - 0.25, z + 0.25), C["brass"])
    x = 40
    add("status_led", "bought", cyl_dir((x, ty0 - 3.0, z), (0, 1, 0), 2.5, 6.0), C["ledred"])
    add("status_led", "bought", cq.Workplane("XY").add(cq.Solid.makeSphere(2.5, cq.Vector(x, ty0 - 3.0, z))), C["ledred"])
    add("status_led", "bought", cyl_dir((x, ty0 + 3.0, z), (0, 1, 0), 2.9, 1.0), C["ledred"])
    for dx in (-1.27, 1.27):
        add("status_led", "bought", cyl_dir((x + dx, ty0 + 4.0, z), (0, 1, 0), 0.25, 7.0), C["steel"])
    add("status_led", "bought", cyl_dir((x + 1.27, ty0 + 11.0, z), (0, 1, 0), 1.0, 6.0), "#d8c49a")                   # 220 ohm
    x = 65
    add("dc_jack", "bought", cyl_dir((x, ty0 - 1.5, z), (0, 1, 0), 5.5, 1.5), C["black"])
    add("dc_jack", "bought", cyl_dir((x, ty0, z), (0, 1, 0), 3.9, 5.0).cut(cyl_dir((x, ty0 - 2, z), (0, 1, 0), 2.8, 5)), C["steel"])
    add("dc_jack", "bought", cyl_dir((x, ty0 - 1.5, z), (0, 1, 0), 0.9, 6), C["steel2"])
    add("dc_jack", "bought", moved(hexagon(6.0, 0, 2.0), trsf_axes((x, ty0 + 3, z), (1, 0, 0), (0, 1, 0))), C["steel"])
    add("dc_jack", "bought", box(x - 4, x + 4, ty0 + 5, ty0 + 16, z - 4, z + 4), C["black"])

    # ---- the can bumper (rubber) and the right axle shown as a screw below
    add("can_bumper", "bought", parts["can_bumper"]["shape"], C["rubber"])

    # ---- screws: (step owner name, kind, head point, axis into the part, length)
    S = []
    for bx in (-14.6, 34.9):                                        # MG996R tabs, #8 up into the base blocks
        for by in (-5, 5):
            a = math.radians(p["servo_ang"])
            S.append(("turntable_servo_MG996R", "#8", (bx * math.cos(a) - by * math.sin(a), bx * math.sin(a) + by * math.cos(a), srv_tip_z - 42.9 + 26.5), (0, 0, 1), 12.7))
    S.append(("turntable_horn", "M3", (0, 0, tz0 - 0.8), (0, 0, -1), 8))
    for a in (45, 135, 225, 315):                                   # turret plate -> horn
        S.append(("turret_plate", "sb", (8 * math.cos(math.radians(a)), 8 * math.sin(math.radians(a)), tz1), (0, 0, -1), 8))
    for x in (-15, 15):
        S.append(("spine", "#6", (x, -16, tz1 + 8), (0, 0, -1), 12.7))
        S.append(("top_cap", "#6", (x, -21, p["rod_top"]), (0, 0, -1), 12.7))
    for hz in (ltz - (MICRO_HOLES_X - 13.75), ltz - (MICRO_HOLES_X + 13.75)):
        S.append(("lift_servo_MG90S", "sb", (7.1, lty, hz), (1, 0, 0), 8))
    S.append(("lift_link", "#6s", (-5.5, 12, cz1 + 2), (-1, 0, 0), 6.35))      # 1/4": a 1/2" one reaches the left rod
    th0 = math.radians(p["lift_theta0"])
    pin = (lty + p["lift_crank"] * math.cos(th0), ltz + p["lift_crank"] * math.sin(th0))
    S.append(("lift_crank", "M3", (ltx - 2.5, lty, ltz), (1, 0, 0), 6))
    S.append(("lift_crank", "sb", (ltx - 5.5, pin[0], pin[1]), (1, 0, 0), 6))      # from outside: through the link (2.4 mm) into the horn
    for hz in (gz - (MICRO_HOLES_X - 13.75), gz - (MICRO_HOLES_X + 13.75)):
        S.append(("wrist_servo", "sb", (0, wy - 28.5 + 15.9 + 2.5, hz), (0, -1, 0), 8))
    S.append(("wrist_horn", "M3", (0, wy - 0.6, gz), (0, -1, 0), 5))
    for a in (45, 135, 225, 315):
        S.append(("gripper_frame", "sb", (7 * math.cos(math.radians(a)), wy + 3, gz + 7 * math.sin(math.radians(a))), (0, -1, 0), 6))
    S.append(("axle_R", "#6", (pvx, pvy, pt[1]), (0, 0, -1), 12.7))
    tab_z = p["grip_spline_tip"] + 10.1
    gs_cx = -pvx - MICRO_HOLES_X
    for hx in (gs_cx - 13.75, gs_cx + 13.75):
        S.append(("gripper_servo_SG90", "sb", (hx, pvy, tab_z + 2.5), (0, 0, -1), 8))
    for sx in (-1, 1):                                          # horn -> left gear
        S.append(("gripper_horn", "sb", (-pvx + sx * p["ghorn_screw_r"], pvy, p["finger_z"][1] + p["ghorn_gap"] + p["ghorn_disc"]), (0, 0, -1), 6))
    for x in (-50, 50):
        S.append(("electronics_tray", "#6", (x, -half + p["base_wall"] + 4, 0.0), (0, 0, 1), 12.7))
    HOLE = {  # what the screw passes through / bites, with the drill bit to use by hand if it is tight
        "turntable_servo_MG996R": "servo tab Ø4.6 → base pilot Ø3.5 · tight: 9/64″ (3.6 mm) bit",
        "turntable_horn": "horn centre screw (servo bag)",
        "turret_plate": "plate Ø1.7 → open to 3/32″ (2.4 mm) · bites the horn",
        "spine": "spine clear Ø3.9 (5/32″) → plate pilot Ø2.9 (7/64″)",
        "top_cap": "cap clear Ø3.9 (5/32″) → spine pilot Ø2.9 (7/64″)",
        "lift_servo_MG90S": "servo tab → bracket pilot Ø1.7 (1/16″)",
        "lift_link": "#6 × ¼″ pointed screw · link must turn (5/32″ bit) → carriage pilot (7/64″)",
        "lift_crank": "link hole → drill 3/32″ (2.4 mm), turns · bites the horn",
        "wrist_servo": "servo tab → bracket pilot Ø1.7 (1/16″)",
        "wrist_horn": "horn centre screw (servo bag)",
        "gripper_frame": "flange Ø1.7 → open to 3/32″ (2.4 mm) · bites the horn",
        "gripper_servo_SG90": "servo tab → post pilot Ø1.7 (1/16″)",
        "gripper_horn": "horn hole → gear pilot Ø1.7 (1/16″), 5 mm from centre",
        "electronics_tray": "tray clear Ø3.9 (5/32″) → base pilot Ø2.9 (7/64″)",
    }
    screws = []
    for i, (owner, kind, head, ax, L) in enumerate(S):
        sh, col = screw_local(kind, L)
        if owner == "axle_R":                                       # the axle IS a screw: it is the step's part itself
            add("axle_R", "screw", moved(sh, trsf_axes(head, perp_of(ax), ax)), col)
            continue
        nm = f"screw_{i:02d}"
        add(nm, "screw", moved(sh, trsf_axes(head, perp_of(ax), ax)), col)
        screws.append(dict(name=nm, owner=owner, kind=kind, head=[round(v, 2) for v in head], axis=list(ax), length=L, hole=HOLE.get(owner, ""),
                           head_r=SCREW[kind]["hr"], head_h=SCREW[kind]["hh"]))

    # ---- glue + ballast
    glue = []
    def glue_blob(owner, x, y, z, r, squash=0.5, axis=(0, 0, 1)):
        nm = f"glue_{len(glue):02d}"
        sph = cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(0, 0, 0), angleDegrees1=0, angleDegrees2=90))
        sph = moved(sph, trsf_axes((x, y, z), perp_of(axis), axis))
        add(nm, "glue", sph, C["glue"])
        glue.append(dict(name=nm, owner=owner, at=[x, y, z]))
    for cx_, cy_ in ((-60, -60), (60, -60)):                       # ~50 g of washers in each back pocket, glued
        for k in range(10):
            add("ballast", "bought", ring(cx_, cy_, 9.5, 2.6, 1.0 + k * 2.2, 2.8 + k * 2.2), C["steel2"])
        glue_blob("ballast", cx_, cy_, 23.0, 6.0)
    for hx, hy in [(14.0, 2.5), (15.3, 50.7), (66.1, 7.6), (66.1, 35.5)]:
        glue_blob("arduino_uno", uo[0] + hx, uo[1] + hy, zt, 2.2)
    for hx, hy in ((3, 3), (51, 3), (3, 20), (51, 20)):
        glue_blob("buck_XL4015", bo[0] + hx, bo[1] + hy, zt2, 2.0)
    py1 = p["plate_y1"]
    add("glue_bumper", "glue", box(-2.5, 2.5, py1 - 0.05, py1 + 0.35, p["plate_bot"][0] + 1, pt[1] - 1), C["glue"])
    glue.append(dict(name="glue_bumper", owner="can_bumper", at=[0, py1, gz]))
    cz1 = p["car_z1"]
    callouts = {
        16: [((23.5, 0, H), "pocket ~Ø47.0 printed · sand the wall to fit")],
        19: [((17.5, 0, H - 4), "hub ~Ø34.9 printed · loose: tape / tight: sand")],
        1: [((-rx - 6, ry, cz0 + 9), "pocket ~Ø12.25 printed · slides in; loose: tape")],
        7: [((-rx, ry, tz1 + 6), "blind hole ~Ø5.95 printed · 15/64″ bit if tight")],
        8: [((rx, ry, p["rod_top"]), "blind hole ~Ø5.95 · 15/64″ bit if tight, 8 mm deep")],
        2: [((-7, 12, cz1 + 2), "#6 × ¼″ pointed · link must swing (5/32″ bit)")],
        4: [((-7, pin[0], pin[1]), "drill to 3/32″ (2.4 mm) · must turn")],
        11: [((pvx, pvy, pt[1]), "Ø3.9 running · 5/32″ bit")],
        12: [((-pvx + p["ghorn_screw_r"], pvy, p["finger_z"][1]), "horn screws → 2 small holes, 5 mm from centre")],
    }
    return meshes, screws, glue, callouts


def main():
    meshes, screws, glue, callouts = build()
    # the 2 horn centre screws can't be reached once the horn is under its part: not used (spline teeth carry the torque)
    drop = {x["name"] for x in screws if x["owner"] in ("turntable_horn", "wrist_horn") and x["kind"] == "M3"}
    screws = [x for x in screws if x["name"] not in drop]
    meshes = [m for m in meshes if m["owner"] not in drop]
    steps = json.load(open(os.path.join(HERE, "build", "manual_steps.json")))["steps"]
    out_meshes = []
    for m in meshes:
        verts, tris = m["shape"].val().tessellate(0.12, 0.35) if hasattr(m["shape"], "val") else m["shape"].tessellate(0.12, 0.35)
        out_meshes.append(dict(owner=m["owner"], kind=m["kind"], color=m["color"],
                               v=[round(c, 1) for vv in verts for c in (vv.x, vv.y, vv.z)], f=[i for t in tris for i in t]))
    # attach screws / glue / ballast to their steps
    first = {}
    for s in steps:
        for n in s["new"]:
            first.setdefault(n, s["n"])
    first["ballast"] = next(s["n"] for s in steps if s["title"].startswith("Weight"))
    st = []
    for s in steps:
        n = s["n"]
        sc = [x for x in screws if first.get(x["owner"]) == n]
        gl = [g for g in glue if first.get(g["owner"]) == n]
        extra = ["ballast"] if n == first["ballast"] else []
        note = NOTES["steps"].get(str(n), {})
        base_show = set(s["show"]) | ({"ballast"} if n >= first["ballast"] and "base" in s["show"] else set())
        show = base_show | {x["name"] for x in screws if x["owner"] in base_show and first.get(x["owner"], 99) <= n}
        show |= {g["name"] for g in glue if g["owner"] in base_show and first.get(g["owner"], 99) <= n}
        st.append(dict(n=n, title=s["title"], new=s["new"] + extra, show=sorted(show),
                       dir=s["dir"], per_part_dir=s["per_part_dir"], dist=s["dist"], hw=s["hw"], badge=s["badge"], note=s["note"],
                       screws=[x["name"] for x in sc], glue=[g["name"] for g in gl], fit=note.get("fit", ""), how=note.get("how", ""),
                       glue_text=note.get("glue", ""), level=note.get("level", "easy"),
                       callouts=[dict(at=[round(v, 2) for v in a], text=t) for a, t in callouts.get(n, [])]))
    # motion: which moving group each owner rides with + the firmware sequence (from export.py), for the "watch it run" step
    vm = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))
    gof = {x["name"]: g for g, lst in vm["groups"].items() for x in lst}
    for sc in screws:
        gof.setdefault(sc["name"], gof.get(sc["owner"], "fixed"))
    for g in glue:
        gof.setdefault(g["name"], gof.get(g["owner"], "fixed"))
    groups = {m["owner"]: gof.get(m["owner"], "fixed") for m in meshes}
    pv = vm["params"]
    motion = dict(groups=groups, sequence=vm["sequence"],
                  params=dict(lift_theta0=pv["lift_theta0"], grip_z=pv["grip_z"], pivot_x=pv["pivot_x"], pivot_y=pv["pivot_y"],
                              lift_servo_tip=list(M.P["lift_servo_tip"])))
    data = dict(meshes=out_meshes, screws=screws, glue=glue, steps=st, motion=motion, printed=sorted({m["owner"] for m in meshes if m["kind"] == "printed"}),
                names=NOTES["names"], screw_names=NOTES["screw_names"], levels=NOTES["levels"], while_waiting=NOTES["while_waiting"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/assembly.json: {len(out_meshes)} meshes, {len(screws)} screws, {len(glue)} glue points, "
          f"{os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
