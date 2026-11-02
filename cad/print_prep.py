"""Print files: every printed part turned to its best side, ready to slice.

    python3.13 cad/print_prep.py          (needs cadquery + matplotlib)

For each printed part, tries all 6 faces as the bed face and picks, in this order:
  0. a stable footprint (>= 200 mm2 of flat face on the bed, or half the part's footprint),
  1. the most press-fit holes (LM6UU, 6 mm rod, 6807 bearing) with a vertical axis
     (vertical holes print round; horizontal ones print slightly oval and tighter at the top),
  2. the most flat area on the bed minus the flat area hanging in the air (overhang to support),
  3. the lowest height.
Writes print/stl/<part no>_<name>.stl (on the bed, centred), print/print_orientations.png and
print/print_table.csv (used by docs/08_build_guide.md).
"""
import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import model      # noqa: E402
import drawings   # noqa: E402  (hidden-line projection + hole finder)

OUT = os.path.join(ROOT, "print")
os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
BED = (220, 220, 250)            # Ender-3 class bed, mm (EST: check yours)
G_PER_H = 12.0                   # PETG at 0.2 mm layers, ~60 mm/s (EST)

# face that goes on the bed -> (rotation axis, angle) that turns its outward normal to -Z
CANDIDATES = {"-Z (as modelled, bottom down)": None, "+Z (upside down, top face down)": ((1, 0, 0), 180),
              "+X face down": ((0, 1, 0), 90), "-X face down": ((0, 1, 0), -90),
              "+Y face down": ((1, 0, 0), -90), "-Y face down": ((1, 0, 0), 90)}
PRESS = ("LM6UU", "rod press", "6807")


def evaluate(shape, part):
    bb = shape.BoundingBox()
    z0 = bb.zmin
    contact = overhang = 0.0
    for f in shape.Faces():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt()
        if n.z < -0.999:
            if abs(f.Center().z - z0) < 0.05:
                contact += f.Area()
            else:
                overhang += f.Area()
    rows = drawings.holes(cq.Workplane("XY").add(shape), part)
    # precision holes: press fits, plus the gears' running bore and spline socket (they must print round)
    keys = PRESS + (("running", "spline") if part.startswith("finger") else ())
    press_v = sum(r["n"] for r in rows if r["axis"] == "Z" and any(k in r["fit"] for k in keys))
    press_all = sum(r["n"] for r in rows if any(k in r["fit"] for k in keys))
    return dict(contact=contact, overhang=overhang, press_v=press_v, press_all=press_all,
                h=bb.zlen, w=bb.xlen, d=bb.ylen)


def orient(shape, rot):
    s = shape if rot is None else shape.rotate(cq.Vector(0, 0, 0), cq.Vector(*rot[0]), rot[1])
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def main():
    parts = [p for p in model.build_parts() if p["name"] in drawings.PN and p["material"] == "PETG"]
    parts.sort(key=lambda p: drawings.PN[p["name"]][0])
    table, previews = [], []
    for p in parts:
        base = p["shape"].val()
        best = None
        for label, rot in CANDIDATES.items():
            s = orient(base, rot)
            e = evaluate(s, p["name"])
            stable = e["contact"] >= 200 or e["contact"] >= 0.5 * e["w"] * e["d"]
            key = (stable, e["press_v"], round(e["contact"] - e["overhang"], 0), -e["h"])
            if best is None or key > best[0]:
                best = (key, label, s, e)
        _, label, s, e = best
        pn, title, qty = drawings.PN[p["name"]]
        fname = f"{pn}_{p['name']}.stl"
        cq.exporters.export(cq.Workplane("XY").add(s), os.path.join(OUT, "stl", fname), tolerance=0.02, angularTolerance=0.1)
        mass = drawings.MASS.get(p["name"], 0)
        fits = e["w"] <= BED[0] and e["d"] <= BED[1] and e["h"] <= BED[2]
        supports = "none" if e["overhang"] < 60 else ("bridges only, check in the slicer" if e["overhang"] < 400 else "yes: supports on build plate")
        table.append(dict(part_no=pn, part=title, file=f"print/stl/{fname}", qty=qty, bed_face=label,
                          size_mm=f"{e['w']:.0f} × {e['d']:.0f} × {e['h']:.0f}", fits_bed="yes" if fits else "NO",
                          press_fits_vertical=f"{e['press_v']} of {e['press_all']}", contact_mm2=round(e["contact"]),
                          overhang_mm2=round(e["overhang"]), supports=supports, mass_g=round(mass, 1),
                          est_time_h=round(max(0.3, mass * 1.15 / G_PER_H), 1)))
        previews.append((pn, title, s, label))
        print(f"{pn} {p['name']:18s} {label:32s} {table[-1]['size_mm']:16s} press-vertical {e['press_v']}/{e['press_all']}  overhang {e['overhang']:.0f} mm2")
    with open(os.path.join(OUT, "print_table.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    # preview sheet: each part as it sits on the bed (isometric, bed line under it)
    n = len(previews)
    cols = 4
    rows_ = math.ceil(n / cols)
    fig, axs = plt.subplots(rows_, cols, figsize=(14, 3.6 * rows_))
    for ax in axs.flat:
        ax.axis("off")
    for ax, (pn, title, s, label) in zip(axs.flat, previews):
        vis, _ = drawings.project(s.wrapped, (1, -1, 0.7), (1, 1, 0))
        bed = cq.Workplane("XY").rect(s.BoundingBox().xlen + 30, s.BoundingBox().ylen + 30).val()
        bvis, _ = drawings.project(cq.Face.makeFromWires(bed).wrapped, (1, -1, 0.7), (1, 1, 0))
        for poly in bvis:
            ax.plot([x for x, _ in poly], [y for _, y in poly], color="#9bb3d6", lw=0.8)
        for poly in vis:
            ax.plot([x for x, _ in poly], [y for _, y in poly], color="k", lw=0.5)
        ax.set_aspect("equal")
        ax.set_title(f"{pn} {title}\nbed face: {label}", fontsize=8)
    fig.suptitle("Print orientations (blue = bed outline; parts shown as they sit on the bed)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "print_orientations.png"), dpi=110)
    print(f"wrote {len(table)} STL files to print/stl/, print/print_table.csv, print/print_orientations.png")


if __name__ == "__main__":
    main()
