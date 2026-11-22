"""Plate A: a QUICK one-piece tolerance gauge for the parts that take bearings and for the claw.

    python3.13 backend/cad/tolerance_gauge.py
      -> cad/print/tolerance_test/tolerance_gauge.3mf   (open in PrusaSlicer: placed + all settings inside)
      -> cad/print/tolerance_test/tolerance_gauge.stl, .png, README.md

One piece, thin, no supports: short, meant to be watched. Every hole has its size engraved next to it (mm).
Read it with calipers and with the real parts: 6 mm rod, LM6UU, #6-32 screw, SG90 horn hub, 6807 bearing.
The holes are vertical, like the press fits in the robot's parts.
"""
import os
import sys
import zipfile

import cadquery as cq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import plates as PL  # noqa: E402
from model import box, cyl  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "tolerance_test")
INI = os.path.join(ROOT, "cad", "print", "settings", "plates", "plate_A.ini")
T = 2.0           # plate
TB = 4.0          # bosses round the rod / LM6UU holes (enough depth to feel the fit)
FONT = 3.2

ROWS = [   # (label, sizes): only what decides the bearings and the claw
    ("ROD", [6.0, 6.15, 6.3, 6.45]),        # 6 mm rod: turret plate + top cap holes
    ("LM6UU", [12.1, 12.25, 12.4, 12.55]),  # LM6UU: carriage pockets
    ("AXLE", [3.9, 4.1, 4.3]),       # #6-32 must TURN: claw axle, link pivot
    ("HORN", [6.8, 7.1, 7.4]),       # SG90 horn hub (arms cut off): left finger socket
]
POCKET = 47.25    # 6807 outer race 47.0 -> base pocket (bearing presses into this ring)
HUB = 34.80       # 6807 bore 35.0 -> turret hub (bearing presses onto this post)


def engrave(shape, text, x, y, z_top, size=FONT, depth=0.5, halign="center"):
    t = cq.Workplane("XY").workplane(offset=z_top - depth).text(text, size, depth + 0.5, halign=halign, valign="center",
                                                                 kind="bold").translate((x, y, 0))
    return shape.cut(t)


def label(d):
    return f"{d:.2f}".rstrip("0").rstrip(".")


def gauge():
    """Skeleton, one piece: a bar per hole row joined by a spine on the left, ribs out to the 6807 ring and post."""
    gap, x0 = 2.5, 14.0
    rows, y = [], 0.0
    for name, ds in ROWS:
        dmax = max(ds)
        xs, x = [], x0
        for d in ds:
            w = max(d + 3.4, 8.0)
            xs.append(x + w / 2)
            x += w + gap
        rh = dmax + 3.4 + FONT + 2.0                     # row bar height: hole + boss + its number
        rows.append((name, ds, xs, y, rh, x + 1.0, dmax))
        y += rh + 1.5                                    # 1.5 mm slot between the bars
    H = y - 1.5
    g = box(0, x0, 0, H, 0, T)                           # spine (row titles)
    for name, ds, xs, y0, rh, xend, dmax in rows:
        g = g.union(box(x0 - 1, xend, y0, y0 + rh, 0, T))
    xr = max(r[5] for r in rows)
    rx, py = xr + POCKET / 2 + 4.5, H / 2              # 6807 pocket ring right of the rows
    hx, hy = rx + POCKET / 2 + 2.4 + HUB / 2 + 4.0, H / 2  # 6807 hub post right of the ring
    g = g.union(cyl(rx, py, POCKET / 2 + 2.0, 0, T + 2.0)).cut(cyl(rx, py, POCKET / 2, -1, T + 4))
    g = g.union(cyl(hx, hy, HUB / 2, 0, T + 2.0)).cut(cyl(hx, hy, HUB / 2 - 1.8, -1, T + 4))
    for yy in (H * 0.2, H * 0.8):                       # 2 ribs rows -> ring
        g = g.union(box(xr - 2, rx - POCKET / 2 + 1, yy - 2.0, yy + 2.0, 0, T))
    g = g.union(box(rx + POCKET / 2 - 1, hx - HUB / 2 + 1, py - 2.5, py + 2.5, 0, T))   # ring -> post
    for name, ds, xs, y0, rh, xend, dmax in rows:
        yc = y0 + rh - (dmax / 2 + 1.7)
        for d, xc in zip(ds, xs):
            if name in ("ROD", "LM6UU"):
                g = g.union(cyl(xc, yc, d / 2 + 1.7, T - 0.1, TB))
            g = g.cut(cyl(xc, yc, d / 2, -1, TB + 1))
            g = engrave(g, label(d), xc, y0 + FONT / 2 + 0.7, T)
        g = engrave(g, name, 1.2, y0 + rh / 2, T, 2.4, halign="left")
    W = hx + HUB / 2
    return g, W, H


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f != "README.md":
            os.remove(os.path.join(OUT, f))
    g, W, H = gauge()
    cq.exporters.export(g, os.path.join(OUT, "tolerance_gauge.stl"), tolerance=0.02, angularTolerance=0.1)
    v, t = g.val().tessellate(0.02, 0.1)
    V = np.array([[q.x, q.y, q.z] for q in v])[np.array(t)]
    V = V - V.reshape(-1, 3).min(0)
    V[..., 0] += (230 - W) / 2
    V[..., 1] += (235 - H) / 2
    PL.PER_PART = {}
    p3 = os.path.join(OUT, "tolerance_gauge.3mf")
    PL.write_3mf(p3, [("tolerance_gauge", V)])
    quick = {"solid_infill_speed": "60", "top_solid_infill_speed": "40", "brim_width": "0", "perimeters": "2", "fill_density": "15%", "top_solid_layers": "3", "bottom_solid_layers": "3",
             "perimeter_speed": "50", "external_perimeter_speed": "35", "infill_speed": "70"}
    cfg = []
    for l in open(INI, encoding="utf-8").read().splitlines():
        if not l.strip() or l.startswith("#"):
            continue
        k = l.split("=")[0].strip()
        cfg.append(f"{k} = {quick[k]}" if k in quick else l)
    with zipfile.ZipFile(p3, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Metadata/Slic3r_PE.config", "; generated by PrusaSlicer 2.7.2\n" + "".join("; " + l + "\n" for l in cfg))
    PL.write_stl(os.path.join(OUT, "tolerance_gauge_on_bed.stl"), V)
    print(f"tolerance gauge {W:.1f} x {H:.1f} mm, one piece; wrote cad/print/tolerance_test/")


if __name__ == "__main__":
    main()
