"""Grip-force loop: SG90/MG90S position servo + FSR, outer force controller.

The servo is a position actuator with its own internal loop, so the force loop
is an outer PI that trims the servo command:
    psi_cmd += (Ki*(F_set - F) + Kp*dF_err/dt) * dt     (velocity-form PI)
Contact model: each finger pad is a spring (PAD_K) once the jaw passes the
contact angle. The FSR is read through a 10k divider with a 10-bit ADC.

Also sizes the force setpoint from the slip / dent window.
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
G = 9.81
A_PEAK = 11.65      # m/s^2 along the grip, from flip_control.py

F_MIN = p.SAFETY_FACTOR * p.CAN_M * A_PEAK / (2 * p.MU_PAD)   # per finger
F_SET = 1.5          # N per finger
F_TOL = 0.25         # N, "grip settled" band
F_CONTACT = 0.15     # N, switch from fast close to force loop

KI_F = 25.0          # deg/(N s)
KP_F = 1.5           # deg/N (applied to error change)
CLOSE_RATE = 90.0    # deg/s approach speed before contact
PSI_CONTACT = 40.0   # deg, servo angle where pads touch a 2.4 in can (from CAD)


def fsr_adc(force, rng):
    """FSR 402-ish: R ~ 10k/F(N) above the ~0.1 N turn-on; 10k pull-down, 5 V, 10-bit."""
    if force < 0.1:
        v = 0.0
    else:
        r = 10e3 / force
        v = 5.0 * 10e3 / (10e3 + r)
    return int(min(1023, max(0, round(v / 5.0 * 1023 + rng.normal(0, 1.5)))))


def adc_to_force(adc):
    """Inverse of the nominal curve - replace with a bench calibration fit."""
    if adc <= 2:
        return 0.0
    ratio = adc / 1023.0
    return ratio / max(1e-3, 1 - ratio)     # F/(F+1) = ratio  ->  F = ratio/(1-ratio)


def simulate(t_end=1.2, k_scale=1.0, seed=0, dt=1 / p.CONTROL_HZ, sub=20):
    rng = np.random.default_rng(seed)
    psi = 0.0          # actual servo angle, deg (0 = fully open)
    psi_cmd = 0.0
    mode = "approach"
    prev_err = None
    servo_rate = math.degrees(p.SERVO_RATE) * 0.6   # loaded, 5 V
    lever = p.JAW_LEVER
    log = {k: [] for k in ("t", "F", "Fm", "psi", "cmd")}
    for i in range(int(t_end / dt)):
        t = i * dt
        force = max(0.0, math.radians(psi - PSI_CONTACT) * lever) * p.PAD_K * k_scale
        fm = adc_to_force(fsr_adc(force, rng))
        if mode == "approach":
            psi_cmd += CLOSE_RATE * dt
            if fm > F_CONTACT:
                mode = "force"
        else:
            err = F_SET - fm
            derr = 0.0 if prev_err is None else err - prev_err
            prev_err = err
            psi_cmd += KI_F * err * dt + KP_F * derr
        psi_cmd = min(max(psi_cmd, 0.0), 120.0)
        psi_cmd_q = round(psi_cmd / 0.18) * 0.18           # writeMicroseconds: ~0.18 deg/us
        for _ in range(sub):                               # servo internal loop: rate limit + lag
            h = dt / sub
            step = (psi_cmd_q - psi) * min(1.0, h / 0.02)
            psi += max(-servo_rate * h, min(servo_rate * h, step))
        log["t"].append(t); log["F"].append(force); log["Fm"].append(fm)
        log["psi"].append(psi); log["cmd"].append(psi_cmd)
    return {k: np.array(v) for k, v in log.items()}


def metrics(lg):
    t, f = lg["t"], lg["F"]
    i0 = np.argmax(f > F_CONTACT)
    t0 = t[i0]
    tr = t[np.argmax(f >= 0.9 * F_SET)] - t[np.argmax(f >= 0.1 * F_SET)]
    os_pct = max(0.0, (f.max() - F_SET) / F_SET * 100)
    out = np.where(np.abs(f - F_SET) > F_TOL)[0]
    ts = t[out[-1] + 1] - t0 if len(out) and out[-1] + 1 < len(t) else float("nan")
    return tr, os_pct, ts, F_SET - f[-40:].mean(), f.max()


def main():
    lines = [
        f"Slip limit: F >= SF*m*a/(2 mu) = {F_MIN:.3f} N per finger (SF={p.SAFETY_FACTOR}, mu={p.MU_PAD}, a={A_PEAK} m/s^2)",
        f"Dent limit (ESTIMATE, verify on scrap cans): {p.F_DENT} N per finger",
        f"Setpoint {F_SET} N -> {F_SET / F_MIN:.1f}x above slip limit, {p.F_DENT / F_SET:.1f}x below dent limit",
        f"Window is ~{p.F_DENT / F_MIN:.0f}x wide, so an open-loop servo with compliant pads would likely also work;",
        "the force loop earns its place by (a) confirming the can is actually gripped before the",
        "flip starts and (b) keeping force independent of can diameter/placement error.",
        "",
        "  pad stiffness   rise 10-90   overshoot   settle(+-0.25N)   SS err    peak F",
    ]
    logs = {}
    for ks in (0.5, 1.0, 2.0):
        lg = simulate(k_scale=ks)
        logs[ks] = lg
        tr, os_pct, ts, sse, fpk = metrics(lg)
        lines.append(f"  {ks:4.1f} x nominal   {tr * 1000:6.0f} ms   {os_pct:7.1f} %   {ts * 1000:10.0f} ms"
                     f"      {sse:+.3f} N  {fpk:.2f} N")
    report = "\n".join(lines)
    print(report)
    with open(os.path.join(OUT, "grip_control.txt"), "w") as f:
        f.write(report + "\n")

    fig, ax = plt.subplots(figsize=(7, 3.6))
    for ks, lg in logs.items():
        ax.plot(lg["t"], lg["F"], label=f"pad stiffness x{ks}")
    ax.axhline(F_SET, color="k", ls="--", lw=0.8, label="setpoint")
    ax.axhline(F_MIN, color="tab:red", ls=":", lw=0.8, label="slip limit")
    ax.set_xlabel("t (s)")
    ax.set_ylabel("finger force (N)")
    ax.set_title("Grip force loop (simulated)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "grip_step.png"), dpi=150)


if __name__ == "__main__":
    main()
