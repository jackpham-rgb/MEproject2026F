"""One picture per row of the measurement sheet (docs/17_tolerance_recheck.md): which part, which hole / size.

    python3.13 backend/tools/measure_pictures.py   ->  viewer/data/measure/<row>.png  (A1..A9, B1..B18, C1..C15)

Printed parts (B = tolerance gauge, C = parts already printed) are drawn from the CAD solids, looking along the
hole's axis; the hole to measure is found in the solid by its CAD diameter and ringed in red with the caliper arrow.
Bought parts (A) are simple drawings with the arrow on the size to measure.
Used by viewer/assembly.html (step M) and backend/tools/render_manual.js (pages M0a-M0c).
Re-run after a CAD change that moves or resizes a measured feature.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle, FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
OUT = os.path.join(ROOT, "viewer", "data", "measure")
RED, INK, PART = "#d00000", "#14181d", np.array([0.42, 0.58, 0.86])
FIG = (3.4, 2.5)


# ---------------------------------------------------------------- geometry helpers
_CACHE = {}


def cylinders(shape):
    if id(shape) not in _CACHE:
        _CACHE[id(shape)] = _cylinders(shape)
    return _CACHE[id(shape)]


def _cylinders(shape):
    """[(radius, centre(3), axis(3), outward?)] for every cylindrical face of a solid, de-duplicated."""
    out = []
    for f in shape.Faces():
        if f.geomType() != "CYLINDER":
            continue
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        c = BRepAdaptor_Surface(f.wrapped).Cylinder()
        r = c.Radius()
        ax = c.Axis()
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        p = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        mid = np.array(f.positionAt(0.5, 0.5).toTuple())   # a point ON the face (Center() can sit on the axis)
        p = p + d * np.dot(mid - p, d)                    # centre at the face's height
        radial = mid - p - d * np.dot(mid - p, d)
        radial /= max(np.linalg.norm(radial), 1e-9)
        import cadquery as cq
        probe = p + radial * max(r - 0.3, r * 0.5)       # just inside the cylinder: solid = shaft, empty = hole
        outward = shape.isInside(cq.Vector(*probe), 1e-4)
        if not any(abs(r - o[0]) < 1e-3 and np.linalg.norm(np.cross(p - o[1], d)) < 1e-3 for o in out):
            out.append((r, p, d, outward))
    return out


def find(shape, dia, shaft=False, tol=0.02):
    same = [c for c in cylinders(shape) if abs(2 * c[0] - dia) < tol]
    hits = [c for c in same if c[3] == shaft] or same      # hole/shaft test is only a tie-breaker
    if not hits:
        raise SystemExit(f"no {'shaft' if shaft else 'hole'} of {dia} mm found")
    return hits


def basis(w):
    w = np.asarray(w, float) / np.linalg.norm(w)
    if w[2] < -0.5:
        w = -w                                            # vertical holes: always seen from the top (left = left)
    up = np.array([0, 0, 1.0]) if abs(w[2]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(up, w); u /= np.linalg.norm(u)
    return u, np.cross(w, u), w


def draw_solid(ax, shape, w):
    """Painter's projection of the solid looking down -w (nearest faces drawn last)."""
    vs, ts = shape.tessellate(0.15, 0.25)
    V = np.array([v.toTuple() for v in vs]); T = np.array(ts)
    u, v, w = basis(w)
    P = np.c_[V @ u, V @ v]; D = V @ w
    tri = V[T]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nn = np.linalg.norm(n, axis=1); ok = nn > 1e-9
    n[ok] /= nn[ok, None]
    order = np.argsort(D[T].max(axis=1))
    for i in order:
        if not ok[i]:
            continue
        s = 0.45 + 0.55 * abs(n[i] @ w)
        ax.add_patch(Polygon(P[T[i]], closed=True, fc=PART * s + (1 - s) * 0.15, ec=PART * s * 0.8, lw=0.15))
    lo, hi = P.min(axis=0), P.max(axis=0)
    return (u, v, w), lo, hi


def arrow(ax, a, b, col=RED, lw=2.2):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<|-|>", color=col, lw=lw, mutation_scale=11,
                                                     shrinkA=0, shrinkB=0))


def tag(ax, xy, text, off):
    ax.annotate(text, xy=xy, xytext=(xy[0] + off[0], xy[1] + off[1]), fontsize=10, fontweight="bold", color="white",
                ha="center", va="center", bbox=dict(boxstyle="round,pad=0.25", fc=RED, ec="none"),
                arrowprops=dict(arrowstyle="-", color=RED, lw=1.6))


def finish(ax, lo, hi, path, title):
    span = max(hi - lo)
    pad = span * 0.12
    ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=9.5, color=INK, loc="left")
    ax.figure.savefig(path, dpi=170, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.close(ax.figure)


def new():
    fig, ax = plt.subplots(figsize=FIG)
    return ax


# ---------------------------------------------------------------- printed parts
def pic_hole(shape, row, title, dia, shaft=False, pick=None, label=None, win=None):
    """Ring one hole (or shaft) of the given CAD diameter; pick chooses among several (by screen x)."""
    hits = find(shape, dia, shaft)
    ax = new()
    (u, v, w), lo, hi = draw_solid(ax, shape, hits[0][2])
    pts = sorted(((np.array([h[1] @ u, h[1] @ v]), h) for h in hits), key=lambda t: t[0][0])
    c, h = pts[0] if pick in (None, "left") else pts[-1]
    r = h[0]; span = max(hi - lo)
    ax.add_patch(Circle(c, max(r, span * 0.03) + span * 0.012, fill=False, ec=RED, lw=2.4))
    if r > span * 0.04:
        arrow(ax, c - [r, 0], c + [r, 0])
    if win:                                               # zoom on a long part (gauge): the hole + its engraved size
        lo, hi = np.maximum(lo, c - win), np.minimum(hi, c + win); span = max(hi - lo)
    rr = max(r, span * 0.03)
    if (hi - lo)[1] > (hi - lo)[0] * 1.3:                 # tall picture: tag to the side, outside the part
        tag(ax, c + [rr, 0], label or f"⌀ {dia:.2f}", (hi[0] - c[0] + span * 0.25, 0))
        hi = hi + [span * 0.45, 0]
    else:
        up = c[1] < (lo[1] + hi[1]) / 2
        dy = ((hi[1] - c[1]) if up else (lo[1] - c[1])) + math.copysign(span * 0.08, 1 if up else -1)
        tag(ax, c + [0, math.copysign(rr, dy)], label or f"⌀ {dia:.2f}", (0, dy - math.copysign(rr, dy)))
    finish(ax, lo, hi, os.path.join(OUT, row + ".png"), title)


def pic_cc(shape, row, title, dia, text):
    hits = find(shape, dia)
    if len(hits) < 2:
        raise SystemExit(f"{row}: need 2 holes of {dia}")
    ax = new()
    (u, v, w), lo, hi = draw_solid(ax, shape, hits[0][2])
    a, b = (np.array([h[1] @ u, h[1] @ v]) for h in hits[:2])
    for p, h in ((a, hits[0]), (b, hits[1])):
        ax.add_patch(Circle(p, h[0], fill=False, ec=RED, lw=2))
    arrow(ax, a, b)
    tag(ax, (a + b) / 2, text, (0, -max(hi - lo) * 0.18))
    finish(ax, lo, hi, os.path.join(OUT, row + ".png"), title)


def pic_cc2(shape, row, title, d1, d2, text):
    h1, h2 = find(shape, d1)[0], find(shape, d2)[0]
    ax = new()
    (u, v, w), lo, hi = draw_solid(ax, shape, h1[2])
    a, b = np.array([h1[1] @ u, h1[1] @ v]), np.array([h2[1] @ u, h2[1] @ v])
    for p, h in ((a, h1), (b, h2)):
        ax.add_patch(Circle(p, h[0], fill=False, ec=RED, lw=2))
    arrow(ax, a, b)
    tag(ax, (a + b) / 2, text, (hi[0] - (a[0] + b[0]) / 2 + max(hi - lo) * 0.25, 0))
    finish(ax, lo, hi + [max(hi - lo) * 0.45, 0], os.path.join(OUT, row + ".png"), title)


def pic_size(shape, row, title, view, texts, thick=False):
    """Overall size arrows. view = the axis looked along; texts = labels for the horizontal / vertical arrows."""
    ax = new()
    (u, v, w), lo, hi = draw_solid(ax, shape, view)
    span = max(hi - lo); g = span * 0.06
    if texts[0]:
        y = lo[1] - g
        arrow(ax, (lo[0], y), (hi[0], y))
        ax.text((lo[0] + hi[0]) / 2, y - g * 0.4, texts[0], color=RED, fontsize=10, fontweight="bold", ha="center", va="top")
    if texts[1]:
        x = hi[0] + g
        y0, y1 = thick if thick else (lo[1], hi[1])
        arrow(ax, (x, y0), (x, y1))
        ax.text(x + g * 0.4, (y0 + y1) / 2, texts[1], color=RED, fontsize=10, fontweight="bold", ha="left", va="center")
    lo2, hi2 = lo - [0, 2 * g], hi + [span * 0.25 if texts[1] else 0, 0]
    finish(ax, lo2, hi2, os.path.join(OUT, row + ".png"), title)


# ---------------------------------------------------------------- bought parts (drawings)
def bought(row, title, kind):
    ax = new()
    def done(lo, hi):
        finish(ax, np.array(lo, float), np.array(hi, float), os.path.join(OUT, row + ".png"), title)
    steel, dark = "#b8bec6", "#59616b"
    if kind == "rod":
        ax.add_patch(Rectangle((0, -3), 60, 6, fc=steel, ec=INK, lw=1.2))
        ax.add_patch(Circle((70, 0), 3, fc=steel, ec=INK, lw=1.2)); ax.text(70, -6, "end", ha="center", va="top", fontsize=8)
        arrow(ax, (30, -3), (30, 3)); ax.text(30, 5, "⌀ 6.00", color=RED, fontweight="bold", ha="center", va="bottom")
        done((0, -8), (75, 8))
    elif kind == "lm6uu":
        ax.add_patch(Rectangle((0, -6), 19, 12, fc=steel, ec=INK, lw=1.2))
        for x in (2.5, 16.5):
            ax.add_patch(Rectangle((x - 0.5, -6), 1, 12, fc=dark, ec="none"))
        ax.add_patch(Circle((30, 0), 6, fc=steel, ec=INK, lw=1.2)); ax.add_patch(Circle((30, 0), 3, fc="white", ec=INK, lw=1))
        arrow(ax, (9.5, -6), (9.5, 6)); ax.text(9.5, 7, "outside ⌀ 12.00", color=RED, fontweight="bold", ha="center", va="bottom")
        done((-1, -8), (37, 10))
    elif kind in ("b_od", "b_id"):
        ax.add_patch(Circle((0, 0), 23.5, fc=steel, ec=INK, lw=1.2)); ax.add_patch(Circle((0, 0), 21, fc="#8a929c", ec=INK, lw=0.8))
        ax.add_patch(Circle((0, 0), 19.5, fc=steel, ec=INK, lw=0.8)); ax.add_patch(Circle((0, 0), 17.5, fc="white", ec=INK, lw=1.2))
        if kind == "b_od":
            arrow(ax, (-23.5, 0), (23.5, 0)); ax.text(0, 25, "outside ⌀ 47.00", color=RED, fontweight="bold", ha="center", va="bottom")
        else:
            arrow(ax, (-17.5, 0), (17.5, 0)); ax.text(0, 2, "bore ⌀ 35.00", color=RED, fontweight="bold", ha="center", va="bottom")
        done((-25, -25), (25, 30))
    elif kind == "b_w":
        ax.add_patch(Rectangle((-3.5, -23.5), 7, 47, fc=steel, ec=INK, lw=1.2))
        ax.add_patch(Rectangle((-3.5, -17.5), 7, 35, fc="white", ec=INK, lw=0.8, ls="--"))
        arrow(ax, (-3.5, 25), (3.5, 25)); ax.text(6, 25, "width 7.00 (edge on)", color=RED, fontweight="bold", va="center")
        done((-12, -25), (40, 28))
    elif kind.startswith("screw"):
        d, L, label = {"screw6": (3.51, 16, "#6-32"), "screw8": (4.17, 16, "#8-32"), "screwS": (2.2, 8, "servo screw")}[kind]
        ax.add_patch(Rectangle((-d, 0), 2 * d, 2.2, fc=dark, ec=INK, lw=1))
        ax.add_patch(Rectangle((-d / 2, -L), d, L, fc=steel, ec=INK, lw=1))
        for y in np.arange(-L + 0.6, -0.3, 0.8):
            ax.plot([-d / 2, d / 2], [y, y + 0.4], color=INK, lw=0.6)
        arrow(ax, (-d / 2, -L * 0.45), (d / 2, -L * 0.45))
        ax.text(d / 2 + 1, -L * 0.45, f"{label}\nthread ⌀ {'~2.2' if kind == 'screwS' else f'{d:.2f}'}\n(not the head)",
                color=RED, fontweight="bold", va="center", fontsize=9)
        done((-d - 1, -L - 1), (d + 12, 3.5))
    elif kind == "horn":
        ax.add_patch(Circle((0, 0), 10, fc="white", ec=INK, lw=1.2))
        for a in range(0, 360, 45):
            ax.add_patch(Circle((7 * math.cos(math.radians(a)), 7 * math.sin(math.radians(a))), 0.6, fc="white", ec=INK, lw=0.6))
        ax.add_patch(Circle((0, 0), 3.5, fc="#e9edf1", ec=INK, lw=1.4)); ax.add_patch(Circle((0, 0), 1, fc=INK))
        arrow(ax, (-3.5, 0), (3.5, 0)); ax.text(0, 11, "round boss ⌀ ~7 (underside)", color=RED, fontweight="bold", ha="center", va="bottom")
        done((-11, -11), (11, 14))


# ---------------------------------------------------------------- the sheet
def main():
    import model as M
    import tolerance_gauge as G
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for row, title, kind in [("A1", "6 mm steel rod", "rod"), ("A2", "LM6UU linear bearing", "lm6uu"),
                             ("A3", "6807 bearing: outside", "b_od"), ("A4", "6807 bearing: bore", "b_id"),
                             ("A5", "6807 bearing: width", "b_w"), ("A6", "#6-32 screw", "screw6"),
                             ("A7", "#8-32 screw", "screw8"), ("A8", "servo-bag screw (small)", "screwS"),
                             ("A9", "SG90 round horn, hub", "horn")]:
        bought(row, title, kind)

    g = G.gauge()[0].val()
    n = 1
    for name, ds in G.ROWS:
        for d in ds:
            pic_hole(g, f"B{n}", f"Gauge: {name} hole {d:.2f}", d, win=22); n += 1
    pic_hole(g, "B15", "Gauge: ring, inside", G.POCKET)
    pic_hole(g, "B16", "Gauge: post, outside", G.HUB, shaft=True)
    bb = g.BoundingBox()
    pic_size(g, "B17", "Gauge: overall length", (0, 0, 1), (f"{bb.xlen:.1f}", None))
    pic_size(g, "B18", "Gauge: overall width", (0, 0, 1), (None, f"{bb.ylen:.1f}"))

    parts = {p["name"]: p["shape"].val() for p in M.build_parts()}
    tp, cap, link, base = parts["turret_plate"], parts["top_cap"], parts["lift_link"], parts["base"]
    pic_hole(tp, "C1", "Turret plate: hub, on the UNDERSIDE (into the 6807)", 34.95, shaft=True)
    pic_hole(tp, "C2", "Turret plate: rod hole, LEFT", 6.0, pick="left")
    pic_hole(tp, "C3", "Turret plate: rod hole, RIGHT", 6.0, pick="right")
    pic_cc(tp, "C4", "Turret plate: rod holes centre to centre", 6.0, "34.0 c-c")
    pic_size(tp, "C5", "Turret plate: overall width", find(tp, 6.0)[0][2], ("80.0", None))
    import cadquery as cq
    bb = tp.BoundingBox()                                 # edge view along +y: screen x = -model x, screen y = z
    rim = cq.Workplane().add(tp).intersect(cq.Workplane().box(3, bb.ylen + 2, bb.zlen + 2, centered=False)
                                           .translate((bb.xmin - 0.5, bb.ymin - 1, bb.zmin - 1))).val().BoundingBox()
    pic_size(tp, "C6", "Turret plate: plate thickness (at the round edge)", (0, 1, 0), (None, f"{rim.zlen:.1f}"),
             thick=(rim.zmin, rim.zmax))
    pic_hole(cap, "C7", "Top cap: rod hole, LEFT", 6.0, pick="left")
    pic_hole(cap, "C8", "Top cap: rod hole, RIGHT", 6.0, pick="right")
    pic_hole(cap, "C9", "Top cap: #6 screw hole (either)", 3.9)
    pic_size(cap, "C10", "Top cap: length × width", find(cap, 6.0)[0][2], ("54.0", "44.0"))
    holes = sorted([c for c in cylinders(link) if not c[3]], key=lambda c: c[0])
    pic_hole(link, "C11", "Lift link: big hole (carriage pivot)", 2 * holes[-1][0], label="big hole")
    pic_hole(link, "C12", "Lift link: small hole (crank pin)", 2 * holes[0][0], label="small hole")
    pic_cc2(link, "C13", "Lift link: hole centre to centre", 2 * holes[-1][0], 2 * holes[0][0], "c-c")
    pic_hole(base, "C14", "Base: bearing pocket", 47.10)
    pic_size(base, "C15", "Base: length × width", (0, 0, 1), ("152.0", "112.0"))
    print(f"wrote {len(os.listdir(OUT))} pictures to viewer/data/measure/")


if __name__ == "__main__":
    main()
