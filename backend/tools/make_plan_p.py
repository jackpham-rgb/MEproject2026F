"""Plan P (quick prototype) picture: side + top view of the cardboard / foam-board version, real dimensions.

    python3.13 backend/tools/make_plan_p.py      -> docs/plan_p/plan_p.png

Every dimension comes from backend/cad/model.py, so the cardboard robot moves the can exactly like the
printed one: grip height, 5 in radius, wrist axis through the can's centre, crank and link lengths.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import model as M  # noqa: E402

P = M.P
OUT = os.path.join(ROOT, "docs", "plan_p")
os.makedirs(OUT, exist_ok=True)
C = dict(card="#c9a273", foam="#f4f4f0", printed="#3d7be0", steel="#9aa3ad", servo="#2b2b2b", can="#d33a3a", glue="#e8b923")


def box(ax, y0, y1, z0, z1, kind, label=None, lc="#333", fs=7.5, ta="center"):
    ax.add_patch(Rectangle((y0, z0), y1 - y0, z1 - z0, fc=C[kind], ec=lc, lw=1.0, zorder=3 if kind != "card" else 2))
    if label:
        ax.text((y0 + y1) / 2 if ta == "center" else y1 + 2, (z0 + z1) / 2, label, ha=ta, va="center", fontsize=fs,
                color="white" if kind in ("servo", "printed", "can") else "#111", zorder=6)


def dim(ax, p0, p1, text, off=(0, 0), fs=8):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<->", mutation_scale=9, lw=0.9, color="#c0392b", zorder=7))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], text, fontsize=fs, color="#c0392b", ha="center", va="center",
            zorder=7, bbox=dict(fc="white", ec="none", pad=0.6))


def main():
    gz, cy, rc, ch = P["grip_z"], P["can_y"], P["can_d"] / 2, P["can_h"]
    H, tz0, tz1 = P["base_h"], P["turret_z0"], P["turret_z1"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 8.2), gridspec_kw=dict(width_ratios=[1.35, 1]))

    # ---------------- side view (looking along -X: Y to the right, Z up)
    a1.axhline(0, color="#555", lw=1.2)
    box(a1, -76, 20, 0, H, "card", "BASE: cardboard\nbox, 52 mm tall\nMG996R glued\ninside, horn\nout the top", fs=7)
    a1.text(24, 12, "← base ends 20 mm in front of the axis:\n    the wrist servo swings below here", fontsize=6.5, color="#c0392b")
    box(a1, -11, 11, H - 2, tz0, "servo")
    box(a1, -40, 22, tz0, tz1, "foam", "turret: foam board\nscrewed to the horn", fs=6.5)
    box(a1, -24, -18, tz1, P["rod_top"], "foam")
    a1.text(-27, 120, "SPINE\nfoam board\n2 layers", ha="right", fontsize=7.5)
    ry = P["rod_y"]
    box(a1, ry - 3, ry + 3, tz0 + 2, P["rod_top"], "steel")
    a1.text(ry + 4, 160, "6 mm rods\n(hot-glued into\nfoam board top + bottom)", fontsize=7, va="top")
    box(a1, -24, 20, P["rod_top"] - 6, P["rod_top"], "foam")
    box(a1, P["car_y0"], P["car_y1"], P["car_z0"], P["car_z1"], "foam", "CARRIAGE\nfoam board\nblock\n+ 4 LM6UU\n(zip-tied)", fs=6.5)
    box(a1, -12, 0, 128, 161, "servo", "MG90S\nlift", fs=6.5)
    a1.plot([-6, -6 + 20 * 0.92], [150, 150 - 20 * 0.38], color=C["glue"], lw=3, zorder=6)
    a1.plot([14, 12], [142, 133], color=C["card"], lw=4, zorder=6)
    a1.text(-6, 172, "crank = servo horn, pin at 20 mm\nlink = popsicle stick, 11.4 mm hole-to-hole", fontsize=7, ha="center")
    wy = P["wrist_tip_y"]
    box(a1, P["car_y1"], 46, P["car_z0"], P["car_z0"] + 10, "card", "arm: 2 popsicle sticks", fs=6)
    box(a1, 30, wy, 39, 72, "servo", "MG90S\nwrist", fs=6.5)
    box(a1, wy, 91, 48, 87, "printed", "PRINTED\ngripper\nframe", fs=6.5)
    a1.add_patch(Rectangle((74, 46), 78, 40, fc=C["printed"], ec="#333", alpha=0.45, zorder=3))
    a1.text(118, 89, "PRINTED fingers (gears)", fontsize=7, ha="center", color=C["printed"])
    a1.add_patch(Rectangle((cy - rc, 0), 2 * rc, ch, fc=C["can"], ec="#333", alpha=0.35, zorder=1))
    a1.text(cy, 108, "Coke can", ha="center", fontsize=8, color="#8b1a1a")
    a1.plot([wy - 40, cy + 60], [gz, gz], ls="-.", color="#c0392b", lw=0.8)
    a1.text(cy + 62, gz, "wrist axis = can centre line", fontsize=7, va="center", color="#c0392b")
    dim(a1, (cy + 45, 0), (cy + 45, gz), f"{gz:.1f} mm\n(MUST match)", off=(14, 0))
    dim(a1, (0, -14), (cy, -14), f"{cy:.0f} mm = 5 in (turntable axis → can centre)", off=(0, -7))
    dim(a1, (-40, P["car_z0"]), (-40, P["car_z0"] + 15.3), "lift 15.3", off=(-12, 0), fs=7)
    a1.axvline(0, color="#888", lw=0.7, ls=":")
    a1.text(1, -30, "turntable axis", fontsize=7, color="#666")
    a1.set_xlim(-95, 230); a1.set_ylim(-42, 185); a1.set_aspect("equal"); a1.axis("off")
    a1.set_title("Side view (mm). Shapes don't matter, these 3 numbers do: 61.1 mm, 5 in, wrist axis through the can", fontsize=10)

    # ---------------- top view
    import math
    from matplotlib.patches import Polygon, Wedge
    a2.add_patch(Wedge((0, 0), 175, -30, 145, fc="#fde2e0", ec="none", zorder=0))
    a2.text(118, 40, "KEEP CLEAR:\narm + can sweep\n(-30° … 145°)", fontsize=7.5, color="#c0392b")
    base = [(-76, -76), (20, -76), (20, 4), (4, 20), (-76, 20)]          # corner cut: stays < 25 mm from the axis
    a2.add_patch(Polygon(base, fc=C["card"], ec="#333", zorder=2))
    a2.text(-45, -60, "BASE box (behind + left of the axis,\ncorner cut 25 mm from it)", ha="center", fontsize=7.5, zorder=6)
    a2.add_patch(Circle((0, 0), 40, fc=C["foam"], ec="#333", zorder=3, alpha=0.9))
    a2.add_patch(Rectangle((-10, 10), 20, 50, fc=C["card"], ec="#333", zorder=4))
    a2.add_patch(Rectangle((-31, 58), 62, 33, fc=C["printed"], ec="#333", zorder=4))
    for sx in (-1, 1):
        a2.add_patch(Rectangle((sx * (rc + 1.5) - (4.5 if sx > 0 else 0), 83), 4.5, 69, fc=C["printed"], ec="#333", zorder=4, alpha=0.8))
    for (x, y, lab, col) in ((0, cy, "START", "#1f8a5b"), (cy, 0, "TARGET", "#c0392b")):
        a2.add_patch(Circle((x, y), rc, fc="none", ec=col, lw=2, zorder=5))
        a2.text(x, y, lab, ha="center", va="center", fontsize=8, color=col, zorder=6)
    a2.add_patch(Circle((0, cy), rc, fc=C["can"], alpha=0.3, zorder=2))
    a2.add_patch(Arc((0, 0), 2 * cy, 2 * cy, theta1=0, theta2=90, color="#555", ls="--", lw=1))
    a2.add_patch(Rectangle((-76, -171), 152, 95, fc=C["foam"], ec="#333"))
    a2.text(0, -123, "ELECTRONICS on cardboard\n(the bench-test layout,\nunchanged)", ha="center", fontsize=8)
    a2.set_xlim(-90, 180); a2.set_ylim(-180, 180); a2.set_aspect("equal"); a2.axis("off")
    a2.set_title("Top view: tape START and TARGET on the table; nothing may stand in the pink area", fontsize=10)

    handles = [Rectangle((0, 0), 1, 1, fc=C[k], ec="#333") for k in ("card", "foam", "printed", "steel", "servo")]
    fig.legend(handles, ["cardboard / popsicle sticks", "foam board", "3D-printed (only these, ~4 h)", "bought steel", "servo"],
               loc="lower center", ncol=5, fontsize=9, frameon=False)
    fig.suptitle("Plan P: the quick prototype (cardboard + foam board + hot glue, only the claw printed)", fontsize=13)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(OUT, "plan_p.png"), dpi=120)
    print("wrote docs/plan_p/plan_p.png")


if __name__ == "__main__":
    main()
