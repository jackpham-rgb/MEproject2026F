"""Kinematic / clearance check for the mirror-flip concept (Concept D).

Replaces the Gazebo step for a 1-DOF mechanism: sweeps the can, gripper and
counterweight through the full 0..180 deg flip and checks
  * nothing passes below the table surface mid-flip,
  * the can lands at TARGET, inverted, at the intended hover gap,
  * how landing error scales with angle error and axis-height error.
Writes figures to sim/out/.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import params as p

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

A = np.array(p.AXIS_DIR)
PIVOT = np.array([0.0, 0.0, p.AXIS_H])


def rot(theta, axis=A):
    """Rodrigues rotation matrix about unit vector `axis`."""
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(theta) * k + (1 - math.cos(theta)) * k @ k


# Sign convention: positive theta lifts the can straight up off the table
# (can centre moves toward +z first).
_c0 = np.array([*p.START, p.CAN_H / 2])
SIGN = 1.0 if (rot(0.1) @ (_c0 - PIVOT))[2] > 0 else -1.0


def transform(pts, theta, pivot=PIVOT):
    return (rot(SIGN * theta) @ (pts - pivot).T).T + pivot


def can_points(center_xy, n_ang=48, n_h=12):
    ang = np.linspace(0, 2 * math.pi, n_ang, endpoint=False)
    zs = np.linspace(0, p.CAN_H, n_h)
    r = p.CAN_D / 2
    pts = [[center_xy[0] + r * math.cos(a), center_xy[1] + r * math.sin(a), z] for a in ang for z in zs]
    # end caps
    for rr in np.linspace(0, r, 4):
        for a in ang:
            for z in (0.0, p.CAN_H):
                pts.append([center_xy[0] + rr * math.cos(a), center_xy[1] + rr * math.sin(a), z])
    return np.array(pts)


def counterweight_point():
    """CW sits on the arm line, on the far side of the axis from the can."""
    c = np.array([*p.START, p.AXIS_H])            # can centre is at axis height by design
    foot = PIVOT + A * np.dot(c - PIVOT, A)       # perpendicular foot on the axis
    u = (c - foot) / np.linalg.norm(c - foot)
    return foot - u * p.R_CW


def sweep(center_xy=p.START, pivot=PIVOT, n=361):
    pts = can_points(center_xy)
    cw = counterweight_point()
    th = np.linspace(0, math.pi, n)
    can_min_z = np.array([transform(pts, t, pivot)[:, 2].min() for t in th])
    cw_z = np.array([transform(cw[None], t, pivot)[0, 2] for t in th])
    centre = np.array([transform(np.array([[*center_xy, p.CAN_H / 2]]), t, pivot)[0] for t in th])
    return th, can_min_z, cw_z, centre


def landing(theta_end=math.pi, center_xy=p.START, pivot=PIVOT):
    """Return (landing centre xy, lowest point z, tilt deg) at theta_end."""
    pts = can_points(center_xy)
    moved = transform(pts, theta_end, pivot)
    axis_vec = rot(SIGN * theta_end) @ np.array([0, 0, 1.0])
    tilt = math.degrees(math.acos(min(1.0, abs(axis_vec[2]))))
    c = transform(np.array([[*center_xy, p.CAN_H / 2]]), theta_end, pivot)[0]
    return c[:2], moved[:, 2].min(), tilt, axis_vec[2] < 0


def main():
    IN = p.IN
    th, zmin, cwz, centre = sweep()
    interior = (th > math.radians(1)) & (th < math.radians(179))
    xy, lz, tilt, inverted = landing()
    lines = []
    lines.append(f"Axis height            : {p.AXIS_H / IN:.3f} in")
    lines.append(f"Arm radius (axis->can) : {p.ARM_R / IN:.3f} in")
    lines.append(f"Min can z mid-flip     : {zmin[interior].min() / IN:+.3f} in (must be > 0)")
    lines.append(f"Min counterweight z    : {cwz.min() / IN:+.3f} in (must be > 0)")
    lines.append(f"Max can centre height  : {centre[:, 2].max() / IN:.3f} in")
    lines.append(f"Landing centre         : ({xy[0] / IN:.3f}, {xy[1] / IN:.3f}) in, target (5, 0)")
    lines.append(f"Landing hover gap      : {lz / IN:.3f} in, inverted={inverted}, tilt={tilt:.2f} deg")
    # Angle error budget: overshoot pushes the far rim into the table.
    lines.append("")
    lines.append("Final-angle error sensitivity (theta_end = 180 + d):")
    for d in (-3, -2, -1, -0.5, 0, 0.5, 1, 2):
        xy_d, lz_d, tilt_d, _ = landing(math.pi + math.radians(d))
        lines.append(f"  d={d:+5.1f} deg  lowest point z={lz_d / IN:+.3f} in  tilt={tilt_d:4.1f} deg"
                     f"  centre=({xy_d[0] / IN:.2f},{xy_d[1] / IN:.2f})")
    tip = math.degrees(math.atan(p.CAN_RIM_R / (p.CAN_H / 2)))
    lines.append(f"Static tip-over angle of inverted can: {tip:.1f} deg")
    lines.append("")
    lines.append("Axis-height error sensitivity (build tolerance):")
    for e in (-0.06, -0.04, -0.02, 0.0, 0.02, 0.05, 0.10):
        piv = PIVOT + np.array([0, 0, e * IN])
        _, lz_e, _, _ = landing(pivot=piv)
        _, zm, _, _ = sweep(pivot=piv, n=91)
        lines.append(f"  dh={e:+.2f} in  hover gap={lz_e / IN:+.3f} in  min mid-flip z={zm[1:-1].min() / IN:+.3f} in")
    lines.append("")
    lines.append("Can placement error (mirror flip copies it to the target):")
    for dx, dy in ((0.25, 0), (-0.25, 0), (0, 0.25), (0, -0.25)):
        c0 = (p.START[0] + dx * IN, p.START[1] + dy * IN)
        xy_c, _, _, _ = landing(center_xy=c0)
        err = math.hypot(xy_c[0] - p.TARGET[0], xy_c[1] - p.TARGET[1]) / IN
        lines.append(f"  start offset ({dx:+.2f},{dy:+.2f}) in -> landing error {err:.2f} in"
                     " (before V-jaw self-centring)")
    report = "\n".join(lines)
    print(report)
    with open(os.path.join(OUT, "flip_geometry.txt"), "w") as f:
        f.write(report + "\n")

    # --- Figures -----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(np.degrees(th), zmin / IN, label="lowest point of can")
    ax.plot(np.degrees(th), cwz / IN, label="counterweight")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("flip angle θ (deg)")
    ax.set_ylabel("height above table (in)")
    ax.set_title("Mid-flip table clearance")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "flip_clearance.png"), dpi=150)

    fig = plt.figure(figsize=(6.5, 6))
    ax = fig.add_subplot(projection="3d")
    pts = can_points(p.START, n_ang=24, n_h=6)
    for t in np.radians([0, 45, 90, 135, 180]):
        q = transform(pts, t) / IN
        ax.scatter(q[:, 0], q[:, 1], q[:, 2], s=1.5)
    ax.plot(centre[:, 0] / IN, centre[:, 1] / IN, centre[:, 2] / IN, "k--", lw=1, label="can centre path")
    L = np.array([PIVOT - A * 0.5 * IN, PIVOT + A * 6 * IN]) / IN
    ax.plot(L[:, 0], L[:, 1], L[:, 2], "r", lw=2, label="flip axis")
    ax.scatter([0], [0], [0], c="k", marker="x", s=40, label="robot origin")
    ax.set_xlabel("x (in)")
    ax.set_ylabel("y (in)")
    ax.set_zlabel("z (in)")
    ax.set_xlim(-1, 7)
    ax.set_ylim(-1, 7)
    ax.set_zlim(0, 8)
    ax.view_init(elev=24, azim=-70)
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Mirror flip: one 180° turn about the 45° axis")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "flip_path_3d.png"), dpi=150)


if __name__ == "__main__":
    main()
