"""Claw-only files for a close-up Fusion 360 demo of the gripper.

    python3.13 backend/cad/export_claw.py

cad/claw/claw.step               gripper frame + SG90 + wrist servo/horn (grp_frame), the two geared
                                 arms (grp_finger_L, grp_finger_R) and the can (grp_can), wrist upright
cad/claw/claw_sequence.json      arm angle per frame for close -> hold -> release 25° -> open, plus the
                                 arm pivots (and 4x4 matrices for reference), read by backend/cad/fusion_claw/

Angles are the firmware's (GRIP_OPEN 20°, GRIP_CLOSED 95°, GRIP_RELEASE 70°) and the arm motion is
the same kinematics as model.py, eased slow-fast-slow, slowed down so it is easy to watch.
"""
import json
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402

OUT = os.path.join(ROOT, "cad", "claw")
os.makedirs(OUT, exist_ok=True)

FRAME = ("gripper_frame", "can_bumper", "gripper_servo_SG90", "axle_R", "wrist_horn", "wrist_servo")
COL = {"gripper_frame": "#3d7be0", "finger_L": "#e8b923", "finger_R": "#e8b923", "can_bumper": "#2f2f2f",
       "test_can": "#c0202a", "axle_R": "#b8bcc2", "wrist_horn": "#f2f2f2"}
FW = M.FW
# (label, grip angle at the end of the phase, seconds)  - slowed down ~2x for viewing
PHASES = [("OPEN", FW["GRIP_OPEN"], 0.8), ("GRIP", FW["GRIP_CLOSED"], 1.8), ("HOLD", FW["GRIP_CLOSED"], 0.8),
          ("RELEASE", FW["GRIP_RELEASE"], 1.2), ("HOLD2", FW["GRIP_RELEASE"], 0.6), ("OPEN-FULL", FW["GRIP_OPEN"], 1.4)]
CAPTION = {
    "OPEN": f"Home: arms open ({FW['GRIP_OPEN']}°). The can stands against the silicone bumper.",
    "GRIP": f"GRIP: SG90 turns {FW['GRIP_OPEN']}° → {FW['GRIP_CLOSED']}°. It drives the LEFT arm; the gears turn the RIGHT arm the same amount the other way.",
    "HOLD": "Holding: pads squeeze ~0.5–1 N per arm (holds 15 g; dents at ~8 N).",
    "RELEASE": f"RELEASE: {FW['GRIP_CLOSED']}° → {FW['GRIP_RELEASE']}°, only 25° (upside down at the target, a full opening would hit the base).",
    "HOLD2": "Pads now clear the can by ~13 mm (11.7 mm with the silicone liners).",
    "OPEN-FULL": f"Homing: back to fully open ({FW['GRIP_OPEN']}°).",
}


def ease(s):
    return 0.0 if s <= 0 else 1.0 if s >= 1 else s ** 3 * (10 - 15 * s + 6 * s * s)


def mat(t):
    """gp_Trsf -> 4x4 list (mm)."""
    return [[t.Value(i, j) for j in range(1, 5)] for i in range(1, 4)] + [[0, 0, 0, 1]]


def main():
    parts = {p["name"]: p for p in M.build_parts()}
    asm = cq.Assembly(name="claw")
    for grp, names in (("frame", FRAME), ("finger_L", ("finger_L",)), ("finger_R", ("finger_R",)), ("can", ("test_can",))):
        a = cq.Assembly(name="grp_" + grp)
        for n in names:
            a.add(parts[n]["shape"], name=n, color=cq.Color(COL.get(n, "#1f2329")))
        asm.add(a, name="grp_" + grp)
    asm.export(os.path.join(OUT, "claw.step"))

    dt = 0.04
    samples = []
    grip = FW["GRIP_OPEN"]
    for label, to, secs in PHASES:
        n = max(1, int(secs / dt))
        g0 = grip
        for k in range(1, n + 1):
            g = g0 + (to - g0) * ease(k / n)
            j = M.joints_from_commands(FW["TURN_START"], FW["LIFT_DOWN"], FW["WRIST_UP"], g)
            T = M.group_transforms(j)
            samples.append(dict(label=label, grip=round(g, 2), alpha=j["alpha"],
                                finger_L=mat(T["finger_L"]), finger_R=mat(T["finger_R"])))
        grip = to
    json.dump(dict(frame_dt=dt, pivot_x=M.P["pivot_x"], pivot_y=M.P["pivot_y"], captions=CAPTION, samples=samples), open(os.path.join(OUT, "claw_sequence.json"), "w"))
    render_preview(parts, samples)
    print(f"wrote cad/claw/claw.step, claw_sequence.json ({len(samples)} frames, {len(samples) * dt:.1f} s), claw_open_close.png")


def render_preview(parts, samples):
    """Top view at open / closed / release, plus a close-up of the gear mesh."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from OCP.gp import gp_Trsf
    import drawings as D

    def trsf(m):
        t = gp_Trsf()
        t.SetValues(*[m[i][j] for i in range(3) for j in range(4)])
        return t

    pick = {"OPEN": None, "HOLD": None, "HOLD2": None}
    for s_ in samples:
        if s_["label"] in pick:
            pick[s_["label"]] = s_
    fig, axs = plt.subplots(1, 4, figsize=(19, 5.6), gridspec_kw={"width_ratios": [1, 1, 1, 0.8]})
    for ax, (lab, title) in zip(axs, [("OPEN", f"OPEN ({FW['GRIP_OPEN']}°)"), ("HOLD", f"GRIP: closed on the can ({FW['GRIP_CLOSED']}°)"),
                                      ("HOLD2", f"RELEASE ({FW['GRIP_RELEASE']}°)"), ("HOLD", "gear mesh, close-up (closed)")]):
        s_ = pick[lab]
        shapes = [parts[n]["shape"].val() for n in ("gripper_frame", "can_bumper", "test_can")]
        shapes += [parts[f]["shape"].val().moved(cq.Location(trsf(s_[f]))) for f in ("finger_L", "finger_R")]
        if "close-up" in title:
            shapes = [parts[f]["shape"].val().moved(cq.Location(trsf(s_[f]))) for f in ("finger_L", "finger_R")]
        vis, _ = D.project(cq.Compound.makeCompound(shapes).wrapped, (0, 0, 1), (1, 0, 0))
        for p_ in vis:
            ax.plot([x for x, _ in p_], [y for _, y in p_], "k", lw=0.5)
        if "close-up" in title:
            ax.set_xlim(-20, 20); ax.set_ylim(70, 96)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"{title}\narm angle α = {s_['alpha']:.0f}°", fontsize=10)
    fig.suptitle("Claw from above: the SG90 turns the left arm; the 16-tooth gears turn the right arm the same amount the other way", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "claw_open_close.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
