"""2D drawings for Part C: one dimensioned sheet per designed part + the assembly.

    python3.13 backend/cad/drawings.py          (needs cadquery + matplotlib)

Every view is a hidden-line projection of the real solid from backend/cad/model.py (OCC HLR), so the
drawings always match the STEP / STL files. Third-angle projection, millimetres.

Each part sheet: front, top, right and isometric views; overall dimensions; a hole table
(diameter, count, axis, depth, and which fit from the PETG tolerance table it is), with the
hole letters marked on the view that looks down that axis; title block.
Assembly sheet: front, top and isometric views at HOME, overall dimensions, the 5 in reach,
balloons and a parts list.

Writes docs/drawings/<part no>_<name>.pdf, docs/drawings/CA-000_assembly.pdf,
docs/drawings/all_drawings.pdf and a PNG preview of every sheet.
"""
import csv
import math
import os
import sys
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepLib import BRepLib
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Line
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.TopAbs import TopAbs_EDGE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model  # noqa: E402

OUT = os.path.join(ROOT, "docs", "drawings")
os.makedirs(OUT, exist_ok=True)
SHEET_W, SHEET_H = 279.4, 215.9          # US letter landscape, mm
DATE = "2026-11-02"

# part numbers / names / quantities, same as the BOM (backend/tools/make_tables.py)
PN = {"base": ("CA-101", "Base", 1), "electronics_tray": ("CA-102", "Electronics tray", 1),
      "turret_plate": ("CA-201", "Turret plate", 1), "spine": ("CA-202", "Spine", 1), "top_cap": ("CA-203", "Top cap", 1),
      "carriage_arm": ("CA-301", "Carriage + arm", 1), "lift_link": ("CA-302", "Lift link", 1),
      "gripper_frame": ("CA-401", "Gripper frame", 1), "finger_R": ("CA-402", "Finger, right", 1),
      "finger_L": ("CA-403", "Finger, left", 1), "can_bumper": ("CA-404", "Can bumper", 1),
      "tolerance_coupon": ("CA-900", "Tolerance coupon", 1)}
MASS = {r["part"]: float(r["mass_g"]) for r in csv.DictReader(open(os.path.join(ROOT, "cad", "check", "mass_table.csv")))}
MASS.setdefault("tolerance_coupon", 10.81 * 1.27 * 0.60)

T = model.TOL
FITS = [(T["n6_clear"], "#6-32 clearance / running"), (T["n6_pilot"], "#6-32 pilot (self-threading)"),
        (T["n6_head"], "#6 pan-head pocket"), (T["n8_clear"], "#8-32 clearance"), (T["n8_pilot"], "#8-32 pilot"),
        (T["servo_pilot"], "servo-bag screw pilot"), (T["rod_press"], "6 mm rod press fit"),
        (T["lm_press"], "LM6UU press fit"), (T["bear_housing"], "6807 outer race press fit"),
        (4.6, "MG996R flange screw clearance"), (2.6, "buck peg hole")]


# features that are not a standard fit, named per part (diameters from backend/cad/model.py)
FEATURES = {("base", 36.0): "bearing seat floor bore", ("base", 21.0): "ballast washer pocket",
            ("base", 14.0): "cable hole from the turret", ("electronics_tray", 12.2): "12 mm START button",
            ("electronics_tray", 8.2): "DC panel jack", ("electronics_tray", 5.2): "5 mm status LED",
            ("turret_plate", 27.0): "recess for the Ø25 MG996R horn", ("gripper_frame", 12.2): "SG90 spline + boss clearance",
            ("finger_L", 6.0): "SG90 spline / horn socket"}


def fit_name(d, part=""):
    if (part, round(d, 1)) in FEATURES:
        return FEATURES[(part, round(d, 1))]
    best = min(FITS, key=lambda f: abs(f[0] - d))
    return best[1] if abs(best[0] - d) < 0.011 else ""


# ------------------------------------------------------------------ hidden-line projection
def project(shape, n, xdir):
    """Return (visible, hidden) lists of 2D polylines for a view looking from direction n."""
    algo = HLRBRep_Algo()
    algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*xdir))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)

    def lines(comp):
        out = []
        if comp is None or comp.IsNull():
            return out
        BRepLib.BuildCurves3d_s(comp)
        ex = TopExp_Explorer(comp, TopAbs_EDGE)
        while ex.More():
            e = TopoDS.Edge_s(ex.Current())
            c = BRepAdaptor_Curve(e)
            if c.GetType() == GeomAbs_Line:
                ps = [c.Value(c.FirstParameter()), c.Value(c.LastParameter())]
            else:
                d = GCPnts_QuasiUniformDeflection(c, 0.02)
                ps = [d.Value(i) for i in range(1, d.NbPoints() + 1)] if d.IsDone() else []
            if len(ps) >= 2:
                out.append([(p.X(), p.Y()) for p in ps])
            ex.Next()
        return out

    vis = lines(h.VCompound()) + lines(h.OutLineVCompound())
    hid = lines(h.HCompound()) + lines(h.OutLineHCompound())
    return vis, hid


VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "top": ((0, 0, 1), (1, 0, 0)), "right": ((1, 0, 0), (0, 1, 0)),
         "iso": ((1, -1, 0.9), (1, 1, 0))}


def to_view(pt3, view):
    """Project a 3D model point into a view's 2D frame (same frame as project())."""
    n, xd = VIEWS[view]
    n = _unit(n); xd = _unit(xd)
    yd = _cross(n, xd)
    return (sum(a * b for a, b in zip(pt3, xd)), sum(a * b for a, b in zip(pt3, yd)))


def _unit(v):
    m = math.sqrt(sum(a * a for a in v))
    return tuple(a / m for a in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def bbox2(polys):
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------------ holes
def holes(shape_wp, part=""):
    """Cylindrical faces whose axis runs through empty space = holes (a peg's axis is inside material).
    A hole's wall is often split into 2 half-faces: they are merged by centre, and a hole counts
    only if its faces cover most of the circle."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_OUT
    solid = shape_wp.val()
    acc = {}
    for f in solid.Faces():
        sf = BRepAdaptor_Surface(f.wrapped)
        if sf.GetType() != GeomAbs_Cylinder:
            continue
        cyl = sf.Cylinder()
        r = cyl.Radius()
        ax = cyl.Axis()
        d = ax.Direction()
        dv = (d.X(), d.Y(), d.Z())
        lab = max(range(3), key=lambda i: abs(dv[i]))
        if abs(dv[lab]) < 0.999:
            continue
        bb = f.BoundingBox()
        lo, hi = (bb.xmin, bb.ymin, bb.zmin)[lab], (bb.xmax, bb.ymax, bb.zmax)[lab]
        o = ax.Location()
        ctr = [o.X(), o.Y(), o.Z()]
        ctr[lab] = (lo + hi) / 2
        # probe just outside the wall (away from the axis): material there = the wall bounds a hole
        um = (sf.FirstUParameter() + sf.LastUParameter()) / 2
        vm = (sf.FirstVParameter() + sf.LastVParameter()) / 2
        pw = sf.Value(um, vm)
        rv = [pw.X() - o.X(), pw.Y() - o.Y(), pw.Z() - o.Z()]
        along = sum(rv[i] * dv[i] for i in range(3))
        rv = [rv[i] - along * dv[i] for i in range(3)]
        m = math.sqrt(sum(c * c for c in rv)) or 1.0
        probe = gp_Pnt(*(c + 0.15 * r_ / m for c, r_ in zip((pw.X(), pw.Y(), pw.Z()), rv)))
        cls = BRepClass3d_SolidClassifier(solid.wrapped, probe, 1e-5)
        if cls.State() == TopAbs_OUT:
            continue                                     # empty space outside the wall: a peg / boss / rim
        key = (round(2 * r, 2), "XYZ"[lab], round(ctr[(lab + 1) % 3], 1), round(ctr[(lab + 2) % 3], 1), round(lo, 1), round(hi, 1))
        span = sf.LastUParameter() - sf.FirstUParameter()
        a = acc.setdefault(key, dict(span=0.0, ctr=tuple(ctr), depth=hi - lo))
        a["span"] += span
    found = defaultdict(list)
    for (dia, axis, *_), a in acc.items():
        if a["span"] >= 1.5 * math.pi:
            found[(dia, axis)].append((a["ctr"], round(a["depth"], 1)))
    rows = []
    for (dia, axis), lst in sorted(found.items(), key=lambda k: (-k[0][0], k[0][1])):
        rows.append(dict(dia=dia, axis=axis, n=len(lst), centers=[c for c, _ in lst],
                         depth=max(dp for _, dp in lst), fit=fit_name(dia, part)))
    return rows


# ------------------------------------------------------------------ drawing helpers
def new_sheet(title_rows, sheet_no, n_sheets):
    fig = plt.figure(figsize=(SHEET_W / 25.4, SHEET_H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SHEET_W); ax.set_ylim(0, SHEET_H); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((6, 6), SHEET_W - 12, SHEET_H - 12, fill=False, lw=1.0))
    # title block (bottom right)
    bx, by, bw = SHEET_W - 6 - 112, 6, 112
    rows = title_rows + [("PROJECTION", "Third angle   ⊕◁"), ("SHEET", f"{sheet_no} of {n_sheets}"),
                         ("DRAWN", f"ME 2331 Project 2 team   {DATE}")]
    rh = 5.2
    ax.add_patch(Rectangle((bx, by), bw, rh * len(rows), fill=False, lw=0.8))
    for i, (k, v) in enumerate(reversed(rows)):
        y = by + i * rh
        ax.plot([bx, bx + bw], [y, y], lw=0.4, color="k")
        ax.text(bx + 1.5, y + 1.6, k, fontsize=5.2, color="#555")
        ax.text(bx + 27, y + 1.5, v, fontsize=6.2, weight="bold" if k in ("PART NO.", "TITLE") else "normal")
    ax.plot([bx + 25, bx + 25], [by, by + rh * len(rows)], lw=0.4, color="k")
    return fig, ax, (bx, by + rh * len(rows))


def draw_view(ax, vis, hid, ox, oy, s, x0, y0):
    for p in hid:
        ax.plot([ox + (x - x0) * s for x, _ in p], [oy + (y - y0) * s for _, y in p], color="#7a7a7a", lw=0.35, ls=(0, (2.2, 1.4)))
    for p in vis:
        ax.plot([ox + (x - x0) * s for x, _ in p], [oy + (y - y0) * s for _, y in p], color="k", lw=0.6)


def dim(ax, a, b, off, text, vertical=False):
    """Linear dimension between paper points a and b, offset by 'off' mm (sign = side)."""
    (x1, y1), (x2, y2) = a, b
    kw = dict(color="#1f4e9a", lw=0.4)
    if not vertical:
        y = y1 + off
        ax.plot([x1, x1], [y1, y + math.copysign(1.2, off)], **kw); ax.plot([x2, x2], [y2, y + math.copysign(1.2, off)], **kw)
        ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<|-|>", color="#1f4e9a", lw=0.4, mutation_scale=5))
        ax.text((x1 + x2) / 2, y + (0.8 if off > 0 else -2.6), text, fontsize=5.6, color="#1f4e9a", ha="center")
    else:
        x = x1 + off
        ax.plot([x1, x + math.copysign(1.2, off)], [y1, y1], **kw); ax.plot([x2, x + math.copysign(1.2, off)], [y2, y2], **kw)
        ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<|-|>", color="#1f4e9a", lw=0.4, mutation_scale=5))
        ax.text(x + (0.9 if off > 0 else -0.9), (y1 + y2) / 2, text, fontsize=5.6, color="#1f4e9a",
                ha="left" if off > 0 else "right", va="center", rotation=90)


STD_SCALES = [5, 4, 3, 2, 1.5, 1, 0.75, 0.5, 0.4, 1 / 3, 0.25, 0.2]


def scale_label(s):
    from fractions import Fraction
    f = Fraction(s).limit_denominator(10)
    return f"{f.numerator}:{f.denominator}"


# ------------------------------------------------------------------ part sheet
def part_sheet(p, sheet_no, n_sheets):
    shape = p["shape"].val()
    bb = shape.BoundingBox()
    # move the part so its bounding box starts at the origin (dimensions read from 0)
    shape = shape.translate(cq.Vector(-bb.xmin, -bb.ymin, -bb.zmin))
    wp = cq.Workplane("XY").add(shape)
    L, W, H = bb.xlen, bb.ylen, bb.zlen
    proj = {v: project(shape.wrapped, *VIEWS[v]) for v in VIEWS}
    ext = {v: bbox2(proj[v][0] + proj[v][1]) for v in VIEWS}

    # layout (third angle): front low left, top above it, right side to its right, iso in the
    # space left over at the upper right. Views stay above the title block (y >= 70) and below the notes.
    gap = 16.0
    fx, fy = 20.0, 78.0
    area_w, area_h = 245.0, 92.0
    s = next(sc for sc in STD_SCALES if (L + W) * sc + gap <= area_w and (H + W) * sc + gap <= area_h)
    pno, title, qty = PN[p["name"]]
    fig, ax, (tbx, tby) = new_sheet([("PART NO.", pno), ("TITLE", title), ("MATERIAL", p["material"] + ("  (cut from sheet)" if p["material"] == "silicone" else "  printed, 0.4 mm nozzle")),
                                     ("MASS", f"{MASS.get(p['name'], 0):.1f} g (CAD, 60 % fill)"), ("QTY", f"{qty} per robot"),
                                     ("SCALE", scale_label(s)), ("UNITS", "mm   ·   general tolerance ±0.2"),
                                     ("SOURCE", "cad/step/parts/" + p["name"] + ".step  (from backend/cad/model.py)")], sheet_no, n_sheets)
    ax.text(12, SHEET_H - 14, f"{pno}  {title}", fontsize=11, weight="bold")
    place = {"front": (fx, fy), "top": (fx, fy + H * s + gap), "right": (fx + L * s + gap, fy)}
    for v, (ox, oy) in place.items():
        x0, y0, x1, y1 = ext[v]
        draw_view(ax, *proj[v], ox, oy, s, x0, y0)
        ax.text(ox, oy - 10.5 if v != "top" else oy + (y1 - y0) * s + 2.5, v.upper() + " VIEW", fontsize=5.5, color="#555")
    # overall dimensions
    xf0, yf0, xf1, yf1 = ext["front"]
    dim(ax, (fx, fy), (fx + (xf1 - xf0) * s, fy), -4.5, f"{L:.1f}")
    dim(ax, (fx, fy), (fx, fy + (yf1 - yf0) * s), -4.5, f"{H:.1f}", vertical=True)
    xr0, yr0, xr1, yr1 = ext["right"]
    rx, ry = place["right"]
    dim(ax, (rx, ry), (rx + (xr1 - xr0) * s, ry), -4.5, f"{W:.1f}")
    # isometric (no hidden lines), upper right
    xi0, yi0, xi1, yi1 = ext["iso"]
    iw, ih = xi1 - xi0, yi1 - yi0
    rx_end = place["right"][0] + W * s
    left = max(rx_end, fx + L * s) + 12
    box_w, box_h = SHEET_W - 12 - left, 196 - (fy + H * s + 8)
    si = min(box_w / iw, box_h / ih, 2.5 * s if s < 1 else 3 * s)
    ix, iy = left + (box_w - iw * si) / 2, fy + H * s + 8 + (box_h - ih * si) / 2
    draw_view(ax, proj["iso"][0], [], ix, iy, si, xi0, yi0)
    ax.text(ix, iy - 4, "ISOMETRIC (not to scale)", fontsize=5.5, color="#555")

    # holes: table + letters on the view that looks down each axis
    rows = holes(wp, p["name"])
    look = {"Z": "top", "Y": "front", "X": "right"}
    ty = 12
    tx = 12
    if rows:
        lines = [("", "Ø (mm)", "×", "axis", "depth", "centres from datum (mm)", "fit / feature")]
        for k, r in enumerate(rows[:12]):
            letter = chr(65 + k)
            pl = {"Z": (0, 1), "Y": (0, 2), "X": (1, 2)}[r["axis"]]
            cnt = defaultdict(int)
            for c in r["centers"]:
                cnt[(round(c[pl[0]], 1), round(c[pl[1]], 1))] += 1
            cs = sorted(cnt.items())
            pos = "; ".join(f"({u:.1f}, {w:.1f})" + (f" ×{k}" if k > 1 else "") for (u, w), k in cs[:2]) + (f"  +{len(cs) - 2}" if len(cs) > 2 else "")
            lines.append((letter, f"{r['dia']:.2f}", str(r["n"]), r["axis"], f"{r['depth']:.1f}", pos, r["fit"]))
            v = look[r["axis"]]
            ox, oy = place[v]
            x0, y0, *_ = ext[v]
            for c in r["centers"]:
                u, w = to_view(c, v)
                px, py = ox + (u - x0) * s, oy + (w - y0) * s
                ax.add_patch(Circle((px, py), 1.6, fill=True, color="white", ec="#c0392b", lw=0.35, zorder=5))
                ax.text(px, py, letter, fontsize=3.6, color="#c0392b", ha="center", va="center", zorder=6)
        colx = [0, 5, 16, 21, 28, 37, 84]
        lines = lines[:1] + lines[1:]
        for i, ln in enumerate(lines):
            yy = ty + (len(lines) - 1 - i) * 3.6
            for j, cell in enumerate(ln):
                ax.text(tx + colx[j], yy, cell, fontsize=4.8, weight="bold" if i == 0 else "normal",
                        color="#c0392b" if j == 0 else "k")
        ax.text(tx, ty + len(lines) * 3.6 + 0.8, "HOLE TABLE  (letters mark hole centres on the view along that axis)", fontsize=5.5, weight="bold")
        ax.add_patch(Circle((place["front"][0], place["front"][1]), 1.0, color="#c0392b"))
        ax.text(place["front"][0] - 1.5, place["front"][1] + 1.5, "datum", fontsize=4.5, color="#c0392b", ha="right")
        if len(rows) > 12:
            ax.text(tx + 70, ty + len(lines) * 3.6 + 0.8, f"(+ {len(rows) - 12} smaller sizes: see the STEP file)", fontsize=5)
    notes = ["NOTES", "1. Hole sizes are the printed sizes from the PETG tolerance table (backend/cad/model.py TOL).",
             "   Print CA-900 first and adjust TOL if a fit is off.",
             "2. Screws thread straight into the printed pilots (HF kit #67675, no nuts).",
             "3. Datum = the part's bounding-box corner (min X, Y, Z), lower left of the front and top views.",
             "   Hole centres: (X, Y) for Z holes, (X, Z) for Y holes, (Y, Z) for X holes. ×k = k holes stacked",
             "   along the axis; +n = n more positions (see the STEP file).",
             "4. Shown in its assembly orientation; the STEP file defines all other geometry."]
    for i, n in enumerate(notes):
        ax.text(12, SHEET_H - 20 - i * 3.0, n, fontsize=5.0, weight="bold" if i == 0 else "normal")
    return fig


# ------------------------------------------------------------------ assembly sheet
def assembly_sheet(parts, sheet_no, n_sheets):
    tr = model.group_transforms(model.joints_from_commands(model.FW["TURN_START"], model.FW["LIFT_DOWN"],
                                                           model.FW["WRIST_UP"], model.FW["GRIP_OPEN"]))
    shapes, centers = [], {}
    for p in parts:
        if p["group"] == "coupon":
            continue
        sh = p["shape"].val()
        t = tr.get(p["group"])
        if t is not None:
            sh = sh.moved(cq.Location(t))
        shapes.append(sh)
        if p["name"] in PN:
            c = sh.BoundingBox().center
            centers[p["name"]] = (c.x, c.y, c.z)
    comp = cq.Compound.makeCompound(shapes)
    bb = comp.BoundingBox()
    proj = {v: project(comp.wrapped, *VIEWS[v]) for v in ("front", "top", "iso")}
    ext = {v: bbox2(proj[v][0] + (proj[v][1] if v != "iso" else [])) for v in proj}
    s = 0.2
    fig, ax, (tbx, tby) = new_sheet([("PART NO.", "CA-000"), ("TITLE", "Concept A assembly (HOME pose)"),
                                     ("MASS", "≈ 571 g robot + 15 g can (CAD)"), ("SCALE", "1:5 (front, top)"),
                                     ("UNITS", "mm"), ("SOURCE", "cad/step/concept_a_assembly.step")], sheet_no, n_sheets)
    ax.text(12, SHEET_H - 14, "CA-000  Concept A assembly, HOME pose (arm at START)", fontsize=11, weight="bold")
    fx, fy = 22.0, 76.0
    xf0, yf0, xf1, yf1 = ext["front"]
    xt0, yt0, xt1, yt1 = ext["top"]
    draw_view(ax, proj["front"][0], [], fx, fy, s, xf0, yf0)
    tyy = fy + (yf1 - yf0) * s + 14
    draw_view(ax, proj["top"][0], [], fx, tyy, s, xt0, yt0)
    ax.text(fx, fy - 12, "FRONT VIEW", fontsize=5.5, color="#555")
    ax.text(fx, tyy + (yt1 - yt0) * s + 2, "TOP VIEW", fontsize=5.5, color="#555")
    dim(ax, (fx, fy), (fx + (xf1 - xf0) * s, fy), -4.5, f"{bb.xlen:.0f} overall")
    dim(ax, (fx, fy), (fx, fy + (yf1 - yf0) * s), -4.5, f"{bb.zlen:.0f}", vertical=True)
    dim(ax, (fx + (xt1 - xt0) * s, tyy), (fx + (xt1 - xt0) * s, tyy + (yt1 - yt0) * s), 4.5, f"{bb.ylen:.0f}", vertical=True)
    # turntable axis to can centre (the 5 in requirement), in the top view
    ax0 = (fx + (0 - xt0) * s, tyy + (0 - yt0) * s)
    cy = model.P["can_r_pos"]
    ax1 = (ax0[0], tyy + (cy - yt0) * s)
    ax.plot(*zip(ax0, ax1), color="#c0392b", lw=0.5, ls="--")
    ax.text(ax0[0] - 2, tyy - 3, f"R {cy:.0f} mm (5.0 in): turntable axis → can centre (dashed)", fontsize=5.2, color="#c0392b", va="top")
    # isometric with balloons
    xi0, yi0, xi1, yi1 = ext["iso"]
    si = min(105 / (xi1 - xi0), 118 / (yi1 - yi0))
    ix, iy = 92 + (105 - (xi1 - xi0) * si) / 2, 62
    draw_view(ax, proj["iso"][0], [], ix, iy, si, xi0, yi0)
    ax.text(ix, iy - 4, "ISOMETRIC (not to scale)", fontsize=5.5, color="#555")
    names = [n for n in PN if n in centers]
    for k, n in enumerate(names):
        u, w = to_view(centers[n], "iso")
        px, py = ix + (u - xi0) * si, iy + (w - yi0) * si
        ang = 2 * math.pi * k / len(names)
        bx, by = px + 22 * math.cos(ang), py + 22 * math.sin(ang)
        ax.plot([px, bx], [py, by], color="#1f4e9a", lw=0.35)
        ax.add_patch(Circle((px, py), 0.6, color="#1f4e9a"))
        ax.add_patch(Circle((bx, by), 3.2, fill=True, color="white", ec="#1f4e9a", lw=0.5, zorder=5))
        ax.text(bx, by, PN[n][0][3:], fontsize=4.6, ha="center", va="center", color="#1f4e9a", zorder=6)
    # parts list (designed + key purchased)
    pl = [(PN[n][0], PN[n][1], "PETG" if n != "can_bumper" else "silicone", PN[n][2]) for n in names] + [
        ("CA-P02", "Servo MG996R (turntable)", "buy", 1), ("CA-P03", "Servo MG90S (lift, wrist)", "buy", 2),
        ("CA-P04", "Servo SG90 (gripper)", "buy", 1), ("CA-P05", "Bearing 6807-2RS", "buy", 1),
        ("CA-P06", "Linear bearing LM6UU", "buy", 4), ("CA-P07", "Steel rod 6 × 112 mm", "buy", 2),
        ("CA-P01", "Arduino Uno R3", "buy", 1), ("CA-P09", "Buck converter XL4015", "buy", 1)]
    px0, py0 = 202, SHEET_H - 22
    ax.text(px0, py0, "PARTS LIST (full BOM: docs/05_bom.md)", fontsize=6, weight="bold")
    for i, (pn, nm, mat, q) in enumerate(pl):
        yy = py0 - 4 - i * 3.3
        ax.text(px0, yy, pn, fontsize=4.8); ax.text(px0 + 14, yy, nm, fontsize=4.8); ax.text(px0 + 52, yy, mat, fontsize=4.8); ax.text(px0 + 66, yy, str(q), fontsize=4.8)
    ax.text(12, 64, "Balloon numbers = part number without the CA- prefix. Fasteners: #6-32 × ½″ ×8, #8-32 × ½″ ×4 (HF kit #67675). "
            "\nMotion ranges: turret 0 → −90°, lift 0 → 15.3 mm, wrist 0 → 180°, fingers 0 → 75°.", fontsize=5.0, va="top")
    return fig


def main():
    parts = model.build_parts()
    designed = [p for p in parts if p["name"] in PN]
    order = sorted(designed, key=lambda p: PN[p["name"]][0])
    n = len(order) + 1
    figs = [("CA-000_assembly", assembly_sheet(parts, 1, n))]
    for i, p in enumerate(order, 2):
        figs.append((f"{PN[p['name']][0]}_{p['name']}", part_sheet(p, i, n)))
        print("drew", PN[p["name"]][0], p["name"])
    with PdfPages(os.path.join(OUT, "all_drawings.pdf")) as allpdf:
        for name, fig in figs:
            fig.savefig(os.path.join(OUT, name + ".pdf"))
            fig.savefig(os.path.join(OUT, name + ".png"), dpi=110)
            allpdf.savefig(fig)
            plt.close(fig)
    print(f"wrote {len(figs)} sheets to docs/drawings/")


if __name__ == "__main__":
    main()
