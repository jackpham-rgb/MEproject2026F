"""Concept-level solid model of the mirror-flip robot + full-sweep collision check.

One source of truth for part geometry: the interactive 3D viewer draws
out/mechanism.json, and this script checks the same boxes for collisions.

Frame (inches), centred on the axis point F in the arm plane:
  s = along the flip axis (+ away from the motor), t = in the arm plane toward the
  START can at theta = 0, w = up, relative to the axis height.
Moving parts rotate about s:  t' = t cos(th) - w sin(th),  w' = t sin(th) + w cos(th)
(positive theta lifts the can side). World: z = w + AXIS_H, xy = F + s*a + t*u.
"""
import json
import math
import os

import numpy as np

import params as p

IN = p.IN
H = p.AXIS_H / IN              # 2.39
R = p.ARM_R / IN               # 3.536
CAN_R, CAN_HT = p.CAN_D / IN / 2, p.CAN_H / IN
OPEN_GAP = 2.9                 # jaw opening, in
OUT = os.path.join(os.path.dirname(__file__), "out")


def box(name, s, t, w, color, kind="box", note=""):
    return {"name": name, "kind": kind, "s": list(s), "t": list(t), "w": list(w), "color": color, "note": note}


MOVING = [
    box("hub", (-2.2, 0.35), (-0.45, 0.45), (-0.45, 0.45), "#8a8f98", "cyl_s", "printed hub on the gearmotor shaft"),
    box("arm", (-0.3, 0.3), (0.0, 2.1), (-0.125, 0.125), "#3d7be0", note="printed arm, 3.54 in axis to can centre"),
    box("palm", (-1.65, 1.65), (1.9, 2.1), (-0.4, 0.4), "#3d7be0", note="palm face 0.24 in clear of the can"),
    box("servo", (-0.45, 0.45), (1.1, 1.9), (0.125, 0.6), "#2b2f36", note="SG90 / MG90S grip servo"),
    box("ir_sensor", (-0.3, 0.3), (1.75, 1.9), (-0.35, -0.1), "#1b8a5a", note="IR proximity sensor in the palm (can present)"),
    box("jaw_L", (-OPEN_GAP / 2 - 0.2, -OPEN_GAP / 2), (1.9, 4.3), (-0.3, 0.3), "#e0a33d", "jaw", "V-jaw + silicone pad"),
    box("jaw_R", (OPEN_GAP / 2, OPEN_GAP / 2 + 0.2), (1.9, 4.3), (-0.3, 0.3), "#e0a33d", "jaw", "V-jaw + pad, FSR 402 behind it"),
    box("cw_arm", (-0.3, 0.3), (-1.8, 0.0), (-0.125, 0.125), "#3d7be0", note="counterweight arm"),
    box("counterweight", (-1.0, 1.0), (-2.05, -1.55), (-0.375, 0.375), "#6b4f3a",
        note="steel bar 1/2 x 3/4 x 2 in, about 97 g, centre 1.8 in from axis"),
    box("stop_tab", (-2.1, -1.8), (0.0, 1.2), (-0.15, 0.15), "#3d7be0", note="rests on the home post at theta = 0"),
]
STATIC = [
    box("base_plate", (-3.8, 1.6), (-2.1, 2.1), (-H, -H + 0.25), "#c9ccd2", note="printed base, 0.25 in"),
    box("tower", (-2.5, -2.25), (-0.9, 0.9), (-H + 0.25, 0.7), "#9aa0aa", note="motor tower, slotted for axis-height trim"),
    box("gearmotor", (-4.3, -2.5), (-0.5, 0.5), (-0.5, 0.5), "#50555e", "cyl_s", note="12 V JGA25-370 + hall encoder"),
    box("home_post", (-2.1, -1.8), (0.8, 1.2), (-H + 0.25, -0.15), "#d0453b", note="hard stop + microswitch, defines theta = 0"),
]
CAN = {"t": R, "r": CAN_R, "w": (-H, -H + CAN_HT)}


def rotate(pts, th):
    s, t, w = pts[:, 0], pts[:, 1], pts[:, 2]
    c, n = math.cos(th), math.sin(th)
    return np.stack([s, t * c - w * n, t * n + w * c], axis=1)


def solid_points(part, n=9):
    """Sample a part's volume. Cylinders along s are sampled on their true circle."""
    ss = np.linspace(*part["s"], n)
    if part["kind"] == "cyl_s":
        r = (part["t"][1] - part["t"][0]) / 2
        tc, wc = sum(part["t"]) / 2, sum(part["w"]) / 2
        a = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        rr = np.linspace(0, r, 4)
        return np.array([[s, tc + q * math.cos(b), wc + q * math.sin(b)] for s in ss for q in rr for b in a])
    tt, ww = np.linspace(*part["t"], n), np.linspace(*part["w"], n)
    return np.array(np.meshgrid(ss, tt, ww)).reshape(3, -1).T


def can_points(th):
    a = np.linspace(0, 2 * math.pi, 36, endpoint=False)
    pts = [[CAN["r"] * q * math.cos(b), CAN["t"] + CAN["r"] * q * math.sin(b), w]
           for q in (0.0, 0.5, 1.0) for b in a for w in np.linspace(*CAN["w"], 12)]
    return rotate(np.array(pts), th)


def inside(pts, part, margin=0.0):
    lo = np.array([part["s"][0], part["t"][0], part["w"][0]]) - margin
    hi = np.array([part["s"][1], part["t"][1], part["w"][1]]) + margin
    if part["kind"] == "cyl_s":
        r = (part["t"][1] - part["t"][0]) / 2 + margin
        tc, wc = sum(part["t"]) / 2, sum(part["w"]) / 2
        ok_s = (pts[:, 0] > lo[0]) & (pts[:, 0] < hi[0])
        return ok_s & ((pts[:, 1] - tc) ** 2 + (pts[:, 2] - wc) ** 2 < r * r)
    return np.all((pts > lo) & (pts < hi), axis=1)


def check(margin=0.02):
    """Sweep 0..180 deg. Returns list of (moving, static, theta_deg) hits and min table clearance."""
    hits = []
    table_min = {}
    thetas = np.radians(np.arange(0, 180.5, 1.0))
    samples = {m["name"]: solid_points(m) for m in MOVING}
    th_end = math.radians(179.5)
    landed = dict(kind="cyl_can")
    for th in thetas:
        for m in MOVING:
            q = rotate(samples[m["name"]], th)
            table_min[m["name"]] = min(table_min.get(m["name"], 1e9), q[:, 2].min() + H)
            for st in STATIC:
                if m["name"] == "stop_tab" and st["name"] == "home_post" and th < math.radians(3):
                    continue       # intended contact at rest
                if inside(q, st, margin).any():
                    hits.append((m["name"], st["name"], round(math.degrees(th))))
            # return stroke: open gripper vs the can already standing at TARGET
            c = can_points(th_end)
            rel = q.copy()
            d_axis = rel  # the landed can is fixed; test gripper points against its cylinder
            ct, cw = R * math.cos(th_end), R * math.sin(th_end)
            # landed can axis is vertical (inverted) at t = ct; radius CAN_R; w in its rotated span
            w_lo, w_hi = sorted([-(CAN["w"][1]) , -(CAN["w"][0])])
            if m["name"] not in ("stop_tab", "cw_arm", "counterweight", "hub"):
                near = ((d_axis[:, 0]) ** 2 + (d_axis[:, 1] - ct) ** 2 < (CAN_R + margin) ** 2) & \
                       (d_axis[:, 2] > w_lo) & (d_axis[:, 2] < w_hi)
                if near.any():
                    hits.append((m["name"], "landed can (return stroke)", round(math.degrees(th))))
        cz = can_points(th)[:, 2].min() + H
        table_min["can"] = min(table_min.get("can", 1e9), cz) if th > math.radians(1) else table_min.get("can", 1e9)
    for st in STATIC:
        if inside(can_points(0.0), st).any() or any(inside(can_points(t), st).any() for t in thetas[1:]):
            hits.append(("can", st["name"], "sweep"))
    return hits, table_min


def export():
    os.makedirs(OUT, exist_ok=True)
    F = np.array([R * math.sqrt(0.5), R * math.sqrt(0.5)])
    data = {
        "units": "in", "axis_height": H, "arm_radius": R, "axis_point_xy": F.tolist(),
        "axis_dir_xy": [math.sqrt(0.5), math.sqrt(0.5)], "u_dir_xy": [-math.sqrt(0.5), math.sqrt(0.5)],
        "start_xy": [0.0, 5.0], "target_xy": [5.0, 0.0],
        "can": {"r": CAN_R, "h": CAN_HT, "t": R}, "open_gap": OPEN_GAP, "closed_gap": 2 * CAN_R,
        "moving": MOVING, "static": STATIC,
    }
    with open(os.path.join(OUT, "mechanism.json"), "w") as f:
        json.dump(data, f, indent=1)


def main():
    export()
    hits, tmin = check()
    lines = ["Full-sweep collision check (0..180 deg, 1 deg steps, 0.02 in margin):"]
    if hits:
        seen = {}
        for m, s, th in hits:
            seen.setdefault((m, s), []).append(th)
        for (m, s), ths in seen.items():
            lines.append(f"  COLLISION {m} x {s} at theta {ths[0]}..{ths[-1]}")
    else:
        lines.append("  no collisions between moving parts and the base, tower, motor, home post or landed can")
    lines.append("Minimum height above the table during the sweep:")
    for k, v in sorted(tmin.items(), key=lambda kv: kv[1]):
        lines.append(f"  {k:14s} {v:+.3f} in")
    rep = "\n".join(lines)
    print(rep)
    with open(os.path.join(OUT, "mechanism_check.txt"), "w") as f:
        f.write(rep + "\n")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
