"""Concept A (claw + wrist flip + turntable + lift) design calculations.

Reads the servo angles and move times straight from firmware/concept_a/concept_a.ino,
so the numbers here always match the code. Writes sim/out/concept_a.txt and plots.

    python3 sim/concept_a.py

Values tagged EST are estimates to replace with CAD mass properties / bench tests.
"""
import math
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
IN, G = 0.0254, 9.81

# ---------- test article and layout ----------
CAN_R, CAN_H, CAN_M = 66.2 / 2 / 25.4, 122.2 / 25.4, 0.015   # standard 12 oz Coke can: 66.2 x 122.2 mm, 15 g empty
R_CAN = 5.0                                    # turntable axis -> can centre, in
GRIP_Z = CAN_H / 2                             # grip at mid-height
LIFT = 0.6                                     # lift stroke, in
TIP_ANGLE = math.degrees(math.atan(1.09 / (CAN_H / 2)))   # inverted can on its top rim (rim r 27.6 mm = 1.09 in)

# ---------- moving masses (EST) ----------
M = {  # name: (kg, radius from turntable axis in inches, moves with lift?)
    "can": (0.015, 5.0, True),
    "gripper arms + palm + pads": (0.020, 4.9, True),
    "gripper servo (SG90/MG90S)": (0.012, 3.6, True),
    "wrist servo (micro 180/270)": (0.015, 3.0, True),
    "arm": (0.020, 2.2, True),
    "lift carriage + bushings": (0.030, 0.8, True),
    "column + rods + lift servo": (0.080, 0.2, False),
}
MU_PAD, SF = 0.6, 3.0
MU_SLIDE_PRINTED, MU_SLIDE_LM6UU = 0.30, 0.01
BUSHING_SPACING = 1.6       # in, vertical distance between the two carriage bushings
LIFT_CRANK = 0.35           # in, lift servo horn radius (stroke = 2 r sin 60 = 0.61 in over +-60 deg)

SERVOS = {  # stall torque kg*cm at 5 V (datasheet, typical)
    "MG996R (turntable)": 9.4, "MG90S (lift)": 1.8, "micro 180/270 (wrist)": 1.8, "SG90 (gripper)": 1.6,
}


def read_firmware():
    src = open(os.path.join(HERE, "..", "firmware", "concept_a", "concept_a.ino")).read()
    ints = {k: int(v) for k, v in re.findall(r"const int (\w+)\s*=\s*(-?\d+);", src)}
    times = {k: int(v) for k, v in re.findall(r"(T_\w+) = (\d+)", src)}
    return ints, times


def lowest_point(roll_deg, lift):
    """Lowest point of the can (in) when rolled about a horizontal axis through its centre."""
    p = math.radians(roll_deg)
    return GRIP_Z + lift - (CAN_R * abs(math.sin(p)) + CAN_H / 2 * abs(math.cos(p)))


def ease_peaks(angle_rad, T):
    """Peak speed and acceleration of the minimum-jerk profile used in the firmware."""
    return 15 / 8 * angle_rad / T, 10 / math.sqrt(3) * angle_rad / T ** 2


def main():
    ints, times = read_firmware()
    L = []
    L.append("CONCEPT A - design calculations (angles/times read from firmware/concept_a/concept_a.ino)")
    L.append("")

    # 1. Why the lift: clearance during the wrist flip
    rolls = np.linspace(0, 180, 361)
    need = max(-lowest_point(r, 0) for r in rolls)
    worst = rolls[int(np.argmax([-lowest_point(r, 0) for r in rolls]))]
    L.append("1. Flip clearance")
    L.append(f"   corner distance from grip point = sqrt(R^2 + (H/2)^2) = {math.hypot(CAN_R, CAN_H / 2):.3f} in")
    L.append(f"   no lift: can digs {need:.3f} in into the table, worst at roll {worst:.0f} deg (and {180 - worst:.0f})")
    for lift in (0.3, LIFT):
        L.append(f"   lift {lift:.1f} in: lowest point during flip = {min(lowest_point(r, lift) for r in rolls):+.3f} in")
    L.append(f"   after the flip the can spans the same heights, so lowering {LIFT} in puts it exactly on the table")
    L.append("")

    # 2. Motion profile (from the firmware)
    turn = abs(ints["TURN_START"] - ints["TURN_TARGET"])
    w, a = ease_peaks(math.radians(turn), times["T_TURN"] / 1000)
    wf, af = ease_peaks(math.radians(abs(ints["WRIST_FLIP"] - ints["WRIST_UP"])), times["T_FLIP"] / 1000)
    r = R_CAN * IN
    L.append("2. Motion (eased slow-fast-slow moves)")
    L.append(f"   turntable {turn} deg in {times['T_TURN'] / 1000:.1f} s: peak {math.degrees(w):.0f} deg/s, "
             f"can speed {w * r * 1000:.0f} mm/s, tangential accel {a * r:.2f} m/s^2, centripetal {w * w * r:.2f} m/s^2")
    L.append(f"   wrist 180 deg in {times['T_FLIP'] / 1000:.1f} s: peak {math.degrees(wf):.0f} deg/s "
             "(can centre is on the roll axis, so almost no extra load)")
    seq = ["T_GRIP", "T_LIFT", "T_FLIP", "T_TURN", "T_LIFT", "T_RELEASE"]
    L.append(f"   full run: {sum(times[k] for k in seq) / 1000:.1f} s")
    L.append("")

    # 3. Grip force
    a_max = G + math.hypot(a * r, w * w * r)
    f_min = SF * CAN_M * a_max / (2 * MU_PAD)
    L.append("3. Grip")
    L.append(f"   worst load on the pads: g + turn accel = {a_max:.2f} m/s^2 (the can hangs upside down in the arms)")
    L.append(f"   minimum squeeze per arm = SF*m*a/(2*mu) = {SF}*{CAN_M}*{a_max:.2f}/(2*{MU_PAD}) = {f_min:.2f} N")
    L.append("   dent onset ~8 N per arm (EST): set GRIP_CLOSED so the pads squeeze ~0.5-1 N per arm (SG90 max ~1.8 N, see EE/README.md)")
    L.append("")

    # 4. Servo torques
    lifted = sum(m for m, _, lifts in M.values() if lifts)
    moment = sum(m * rr * IN for m, rr, lifts in M.values() if lifts)       # kg*m about the column
    e = moment / lifted / IN                                                 # in, CG offset from column
    J = sum(m * (rr * IN) ** 2 for m, rr, _ in M.values())
    L.append("4. Servo loads (torques in kg*cm, stall ratings at 5 V)")
    tau_turn = (J * a) / G * 100                                             # N*m -> kg*cm
    L.append(f"   turntable: inertia {J * 1e4:.1f} kg*cm^2, accel torque {tau_turn:.3f} kg*cm "
             f"vs MG996R {SERVOS['MG996R (turntable)']} (the 6807 bearing carries the weight)")
    for mu, name in ((MU_SLIDE_PRINTED, "printed slide"), (MU_SLIDE_LM6UU, "LM6UU bushings")):
        jam = 2 * mu * e / BUSHING_SPACING
        drag = lifted * G * jam                                              # N, friction from the tilting moment
        tau = (lifted * G + drag) * LIFT_CRANK * IN / G * 100
        L.append(f"   lift ({name}, mu {mu}): moving mass {lifted * 1000:.0f} g, CG {e:.1f} in out, "
                 f"jam ratio 2*mu*e/L = {jam:.2f} {'(JAMS - must be < 1)' if jam >= 1 else '(ok, < 1)'}, "
                 f"torque {tau:.2f} kg*cm vs MG90S {SERVOS['MG90S (lift)']}")
    grip_off = 0.25 * IN        # EST: gripper CG offset from the roll axis
    tau_w = (CAN_M + 0.032) * G * grip_off / G * 100
    L.append(f"   wrist: gripper + can ~{(CAN_M + 0.032) * 1000:.0f} g, CG ~0.25 in off the roll axis (EST) -> "
             f"{tau_w:.2f} kg*cm vs {SERVOS['micro 180/270 (wrist)']}")
    L.append("")

    # 5. Error budget
    L.append("5. Error budget")
    for d in (1, 2, 3):
        L.append(f"   turntable off by {d} deg -> can lands {R_CAN * math.radians(d):.2f} in from the target")
    L.append(f"   wrist short of 180 by d deg -> can tilted d deg at release; it only tips past {TIP_ANGLE:.0f} deg")
    L.append("   LIFT_DOWN set too high by h -> can drops h; too low -> pads slide on the can. Calibrate on a real can.")
    L.append("")

    # 6. Base
    base_half = 5.0 - CAN_R - 0.25
    L.append("6. Base")
    L.append(f"   base must stay within {base_half:.2f} in of the turntable axis toward START and TARGET "
             "(can footprint + 0.25 in); it can extend behind the corner freely")
    over = sum(m * (rr - 3.0) for m, rr, _ in M.values() if rr > 3.0) * G * IN
    L.append(f"   tip-over about a 3 in base edge: outboard moment {over:.3f} N*m -> base needs >"
             f" {over / (G * 3.0 * IN) * 1000:.0f} g at the axis (easy; add washers anyway so it doesn't slide)")
    L.append("")

    # 7. Power
    L.append("7. Servo power")
    L.append("   stall currents ~ MG996R 2.5 A, MG90S 0.7 A, micro 0.7 A, SG90 0.65 A -> up to 4.6 A if all stall")
    L.append("   moves are one at a time, so normal draw < 1.5 A; use a 5-6 V supply rated 5 A + 1000 uF capacitor")
    rep = "\n".join(L)
    print(rep)
    open(os.path.join(OUT, "concept_a.txt"), "w").write(rep + "\n")

    # ---------- plots ----------
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for lift, ls in ((0, "-"), (0.3, "--"), (LIFT, "-")):
        ax.plot(rolls, [lowest_point(r, lift) for r in rolls], ls, label=f"lift {lift:.1f} in")
    ax.axhline(0, color="k", lw=0.8)
    ax.fill_between(rolls, -0.5, 0, color="tab:red", alpha=0.08)
    ax.set_xlabel("wrist roll (deg)")
    ax.set_ylabel("lowest point of can (in)")
    ax.set_title("Concept A: why the lift is needed")
    ax.set_ylim(-0.4, 0.8)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "concept_a_clearance.png"), dpi=150)

    # servo angle timeline from the firmware sequence
    steps = [("GRIP", "grip", "GRIP_CLOSED", "T_GRIP"), ("LIFT", "lift", "LIFT_UP", "T_LIFT"),
             ("FLIP", "wrist", "WRIST_FLIP", "T_FLIP"), ("TURN", "turn", "TURN_TARGET", "T_TURN"),
             ("LOWER", "lift", "LIFT_DOWN", "T_LIFT"), ("RELEASE", "grip", "GRIP_OPEN", "T_RELEASE")]
    pose = {"turn": ints["TURN_START"], "lift": ints["LIFT_DOWN"], "wrist": ints["WRIST_UP"], "grip": ints["GRIP_OPEN"]}
    tl = {k: [] for k in pose}
    labels = []
    ts = []
    t0 = 0.0
    ease = lambda s: s ** 3 * (10 - 15 * s + 6 * s * s)
    for name, joint, target, tkey in steps:
        T = times[tkey] / 1000
        start = pose[joint]
        for s in np.linspace(0, 1, 40):
            pose[joint] = start + (ints[target] - start) * ease(s)
            ts.append(t0 + s * T)
            for k in tl:
                tl[k].append(pose[k])
        labels.append((t0 + T / 2, name))
        t0 += T
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for k, lbl in (("turn", "turntable"), ("lift", "lift"), ("wrist", "wrist"), ("grip", "gripper")):
        ax.plot(ts, tl[k], label=lbl)
    for tc, name in labels:
        ax.text(tc, 188, name, ha="center", fontsize=8)
    ax.set_ylim(0, 200)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("servo command (deg)")
    ax.set_title("Concept A: one eased move at a time (from the firmware)")
    ax.legend(loc="center right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "concept_a_sequence.png"), dpi=150)


if __name__ == "__main__":
    main()
