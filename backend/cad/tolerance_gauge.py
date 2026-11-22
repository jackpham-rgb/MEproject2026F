"""Plate A: a tolerance gauge made for THIS robot's real parts, + the lift link (crank hole opened to 2.4 mm).

    python3.13 backend/cad/tolerance_gauge.py
      -> cad/print/tolerance_test/plate_A_gauge.3mf   (open in PrusaSlicer: parts placed + all settings inside)
      -> cad/print/tolerance_test/*.stl  + README.md

Every hole / ring / disc has its size engraved next to it (mm). Read it with calipers OR with the real
parts: the 6 mm rod, an LM6UU, the 6807 bearing, the #6 / #8 screws and the servo screws. The numbers of the
best-fitting holes are what the CAD gets corrected to. All holes are vertical, like the press fits in the parts.
"""
import math
import os
import sys
import zipfile

import cadquery as cq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import plates as PL  # noqa: E402
import print_prep as PP  # noqa: E402
from model import box, cyl, cyl_dir  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "tolerance_test")
INI = os.path.join(ROOT, "cad", "print", "settings", "plates", "plate_A.ini")
T = 2.6                                    # plate thickness (screw rows); rod / LM6UU holes sit in 7 mm tall bosses
TB = 7.0
FONT = 3.4

# rows: (title, what to test with, hole sizes)
ROWS = [   # only what decides the bearings and the claw
    ("ROD", "6 mm steel rod (turret plate + top cap holes)", [5.9, 6.0, 6.1, 6.2, 6.3]),
    ("LM6UU", "LM6UU bearing (carriage pockets)", [11.9, 12.0, 12.1, 12.2, 12.3]),
    ("AXLE", "#6-32 screw must TURN freely (claw axle, link pivot)", [3.7, 3.9, 4.1, 4.3]),
    ("HORN", "SG90 horn hub, arms cut off (left finger socket)", [6.5, 6.8, 7.1, 7.4, 7.7]),
]
GEAR_THIN = [0.00, 0.10, 0.18, 0.25]       # finger gear variants (0.10 = the standard fingers)
RINGS = [46.9, 47.1, 47.3]                 # 6807 outer race (47.0): pocket sizes
HUBS = [34.75, 34.90, 35.05]               # 6807 bore (35.0): hub sizes


def engrave(shape, text, x, y, z_top, size=FONT, depth=0.6, halign="center"):
    t = cq.Workplane("XY").workplane(offset=z_top - depth).text(text, size, depth + 0.5, halign=halign, valign="center",
                                                                 kind="bold").translate((x, y, 0))
    return shape.cut(t)


def gauge():
    pad, gap = 5.0, 3.2
    rows_geo, y = [], pad
    width = 0
    for title, _, ds in ROWS:
        dmax = max(ds)
        xs, x = [], 17.0                    # room for the row title on the left
        for d in ds:
            xs.append(x + d / 2)
            x += d + gap + max(0, 7.5 - d)  # numbers need ~7.5 mm of width
        width = max(width, x + pad - gap)
        rows_geo.append((title, ds, xs, y + dmax / 2, dmax))
        y += dmax + FONT + 5.5
    height = y + pad - 3
    g = box(0, width, 0, height, 0, T).edges("|Z").fillet(3)
    for title, ds, xs, yc, dmax in rows_geo:
        if title in ("ROD", "LM6UU"):                 # tall bosses: the rod / bearing sits straight in 7 mm of hole
            for d, xc in zip(ds, xs):
                g = g.union(cyl(xc, yc, d / 2 + 1.7, T - 0.1, TB))
        for d, xc in zip(ds, xs):
            g = g.cut(cyl(xc, yc, d / 2, -1, TB + 1))
            g = engrave(g, f"{d:.1f}".rstrip("0").rstrip(".") if d != int(d) else f"{d:.0f}", xc, yc - dmax / 2 - FONT / 2 - 1.3, T, FONT)
        g = engrave(g, title, 3.0, yc, T, 3.6, halign="left")
    g = engrave(g, f"X {width:.1f}", width - 18, height - 3.5, T, 2.6)        # outside size: XY scale check
    return g, width, height


def ring(d_in, wall=2.6, h=2.0):
    r = cyl(0, 0, d_in / 2 + wall + 3.5, 0, h).cut(cyl(0, 0, d_in / 2, -1, h + 1))
    return engrave(r, f"{d_in:.1f}", 0, -(d_in / 2 + wall / 2 + 1.75), h, 2.6, depth=0.5)


def hub(d_out, h=2.4):
    s = cyl(0, 0, d_out / 2, 0, h).cut(cyl(0, 0, d_out / 2 - 5.5, -1, h + 1))
    return engrave(s, f"{d_out:.2f}", 0, -(d_out / 2 - 2.75), h, 2.4, depth=0.5)


def gear_test(thin):
    """One gear pair of the finger gears (16T m1, same centre distance as the gripper) on 2 pegs, + its 2 gears.
    Put both gears on the pegs and turn one: the variant that turns smoothly with a little play is the finger pair to print."""
    p = dict(M.P); p["gear_thin"] = thin
    cd = 2 * p["pivot_x"]                                   # centre distance used in the gripper
    base = box(-13, cd + 13, -12, 12, 0, 2).edges("|Z").fillet(2)
    for x in (0, cd):
        base = base.union(cyl(x, 0, 3.7 / 2, 1.9, 2 + 3.6))  # pegs: Ø3.7 (gear bores are 3.9, like the #6 axle)
    base = engrave(base, f"{thin:.2f}", cd / 2, -8.5, 2, 3.6, depth=0.5)
    g1, _ = M.involute_gear(0, 0, 0, 3, 180.0, p)
    g2, _ = M.involute_gear(0, 0, 0, 3, 360.0 / p["gear_z"] / 2, p)
    g1 = g1.cut(cyl(0, 0, 3.9 / 2, -1, 5)); g2 = g2.cut(cyl(0, 0, 3.9 / 2, -1, 5))
    lab = f"{int(round(thin * 100)):02d}"                   # variant engraved on each gear (00 / 10 / 18 / 25)
    g1 = engrave(g1, lab, 0, -4.3, 3, 2.4, depth=0.4); g2 = engrave(g2, lab, 0, -4.3, 3, 2.4, depth=0.4)
    return base, g1, g2


def lift_link_24():
    """The lift link as in model.py, its crank (small) hole opened from 1.7 to 2.4 mm: the link turns on the screw."""
    p = M.P
    parts = {pp["name"]: pp for pp in M.build_parts()}
    lty, ltz = p["lift_servo_tip"][1], p["lift_servo_tip"][2]
    th0 = math.radians(p["lift_theta0"])
    pin = (lty + p["lift_crank"] * math.cos(th0), ltz + p["lift_crank"] * math.sin(th0))
    link = parts["lift_link"]["shape"].cut(cyl_dir((-10, pin[0], pin[1]), (1, 0, 0), 1.2, 6))
    return PP.orient(link.val(), PP.CANDIDATES["+X face down"])


def tris_of(shape):
    v, t = (shape.val() if hasattr(shape, "val") else shape).tessellate(0.02, 0.1)
    V = np.array([[q.x, q.y, q.z] for q in v])
    return V[np.array(t)]


def main():
    os.makedirs(OUT, exist_ok=True)
    g, w, h = gauge()
    objs = {"gauge": g}
    for th in GEAR_THIN:
        b, g1, g2 = gear_test(th)
        objs[f"gears_{th:.2f}_base"] = b; objs[f"gears_{th:.2f}_a"] = g1; objs[f"gears_{th:.2f}_b"] = g2
    for d in RINGS:
        objs[f"ring_{d:.1f}"] = ring(d)
    for d in HUBS:
        objs[f"hub_{d:.2f}"] = hub(d)
    objs["CA-302_lift_link_2.4"] = cq.Workplane("XY").add(lift_link_24())
    tris = {}
    for n, s in objs.items():
        cq.exporters.export(s if hasattr(s, "val") else cq.Workplane("XY").add(s), os.path.join(OUT, f"{n}.stl"), tolerance=0.02, angularTolerance=0.1)
        t = tris_of(s)
        lo = t.reshape(-1, 3).min(0)
        tris[n] = t - lo
    sizes = {n: tuple(np.ptp(t.reshape(-1, 3), 0)[:2]) for n, t in tris.items()}
    PL.GAP, PL.EDGE = 6.0, 6.0                 # no supports on this plate: parts can sit closer
    place = PL.pack(sizes)
    if place is None:
        raise SystemExit("plate A does not fit the bed")
    out = []
    for n, t in tris.items():
        x, y, rot = place[n]
        t = t.copy()
        if rot:
            t = np.stack([-t[..., 1], t[..., 0], t[..., 2]], axis=-1)
            t[..., 0] += sizes[n][1]
        t[..., 0] += x
        t[..., 1] += y
        out.append((n, t))
    PL.PER_PART = {"CA-302_lift_link_2.4": {"brim_width": "5", "fill_density": "100%", "fill_pattern": "rectilinear"}}
    p3 = os.path.join(OUT, "plate_A_gauge.3mf")
    PL.write_3mf(p3, out)
    cfg = [l for l in open(INI, encoding="utf-8").read().splitlines() if l.strip() and not l.startswith("#")]
    cfg = ["brim_width = 0" if l.startswith("brim_width") else l for l in cfg]          # brim only on the tiny link (per part)
    with zipfile.ZipFile(p3, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Metadata/Slic3r_PE.config", "; generated by PrusaSlicer 2.7.2\n" + "".join("; " + l + "\n" for l in cfg))
    PL.write_stl(os.path.join(OUT, "plate_A_gauge.stl"), np.concatenate([t for _, t in out]))
    print(f"gauge {w:.1f} x {h:.1f} x {T} mm; wrote cad/print/tolerance_test/")


if __name__ == "__main__":
    main()
