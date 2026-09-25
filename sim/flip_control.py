"""Flip-axis plant model, PID design by pole placement, and closed-loop sim.

Plant (output side of the gearbox, electrical lag neglected: L/R ~1 ms << 5 ms loop):
    J*theta'' = Kt*V - b*theta' - Tc*sign(theta') - g*m_r*cos(theta)
with Kt = T_stall/V_supply and b = T_stall/w_noload, i.e.
    theta(s)/V(s) = K / (s (tau s + 1)),   K = Kt/b,  tau = J/b.

Controller (what firmware/can_flipper runs, same discretisation):
    V = feedforward(ref) + PID(theta_ref - theta),  derivative on measurement,
    clamped integrator, output saturation, 8-bit PWM + 1496 CPR quantisation.

Ziegler-Nichols is not used: the continuous plant is type-1 second order, its
phase never reaches -180 deg, so there is no ultimate gain to measure. Gains
come from placing a triple closed-loop pole at -wn instead.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import params as p

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
G = 9.81

KT = p.MOTOR_STALL_T / p.V_SUPPLY          # N*m/V
B = p.MOTOR_STALL_T / p.MOTOR_NOLOAD_W     # N*m*s/rad
J = p.load_inertia()
TAU = J / B
K = KT / B
WN = 30.0          # rad/s closed-loop triple pole; ~6x below the 200 Hz Nyquist, above tau^-1
FLIP_T = 1.6       # s, quintic flip duration
THETA_END = math.radians(179.5)
NO_CW_SCALE = (p.gravity_unbalance() + p.M_CW * p.R_CW) / p.gravity_unbalance()   # aim 0.5 deg short: overshoot > +0.9 deg drives the rim into the table


def pole_placement(wn=WN, k=K, tau=TAU):
    kd = (3 * wn * tau - 1) / k
    kp = 3 * wn**2 * tau / k
    ki = wn**3 * tau / k
    return kp, ki, kd


def quintic(t, T, th0, th1):
    """Minimum-jerk profile: zero vel/acc at both ends -> can arrives with ~0 speed."""
    s = min(max(t / T, 0.0), 1.0)
    d = th1 - th0
    pos = th0 + d * (10 * s**3 - 15 * s**4 + 6 * s**5)
    vel = d * (30 * s**2 - 60 * s**3 + 30 * s**4) / T
    acc = d * (60 * s - 180 * s**2 + 120 * s**3) / T**2
    return pos, vel, acc


class PID:
    def __init__(self, kp, ki, kd, dt, i_lim, out_lim):
        self.kp, self.ki, self.kd, self.dt = kp, ki, kd, dt
        self.i_lim, self.out_lim = i_lim, out_lim
        self.i = 0.0
        self.prev_meas = None

    def update(self, ref, meas, ff=0.0, ref_rate=0.0):
        """Derivative acts on the error rate (ref_rate - measured rate). ref_rate comes
        from the analytic trajectory, so there is no derivative kick; with ref_rate = 0
        it reduces to derivative-on-measurement for plain steps. Plain
        derivative-on-measurement during a moving trajectory would brake the arm by
        Kd*omega (~6 V at peak speed) and cost ~2 deg of tracking error."""
        e = ref - meas
        d_meas = 0.0 if self.prev_meas is None else (meas - self.prev_meas) / self.dt
        self.prev_meas = meas
        u_unsat = ff + self.kp * e + self.i + self.kd * (ref_rate - d_meas)
        # conditional integration anti-windup: freeze I while saturated in the same direction
        if abs(u_unsat) < self.out_lim or (u_unsat > 0) != (e > 0):
            self.i = min(max(self.i + self.ki * e * self.dt, -self.i_lim), self.i_lim)
        return min(max(u_unsat, -self.out_lim), self.out_lim)


def simulate(ref_fn, t_end, gains=None, j_scale=1.0, fric_scale=1.0, grav_scale=1.0,
             use_ff=True, can_attached=True, dt_ctrl=1 / p.CONTROL_HZ, dt_sim=1e-4):
    kp, ki, kd = gains or pole_placement()
    ctrl = PID(kp, ki, kd, dt_ctrl, i_lim=3.0, out_lim=p.V_SUPPLY)
    mr = p.gravity_unbalance() - (0 if can_attached else p.CAN_M * p.ARM_R)
    j_true = J * j_scale
    tc_true = p.FRICTION_T * fric_scale
    th = w = 0.0
    v = 0.0
    n_ctrl = int(round(dt_ctrl / dt_sim))
    log = {k: [] for k in ("t", "ref", "theta", "meas", "v", "w")}
    steps = int(t_end / dt_sim)
    for i in range(steps):
        t = i * dt_sim
        if i % n_ctrl == 0:
            ref, wref, aref = ref_fn(t)
            meas = math.floor(th / (2 * math.pi) * p.ENC_CPR) * 2 * math.pi / p.ENC_CPR
            ff = 0.0
            if use_ff:  # nominal model only - the plant uses the scaled "true" values
                tau_ff = J * aref + B * wref + G * p.gravity_unbalance() * math.cos(ref)
                if abs(wref) > 1e-3:
                    tau_ff += p.FRICTION_T * math.copysign(1, wref)
                ff = tau_ff / KT
            v = ctrl.update(ref, meas, ff, wref)
            v = round(v / p.V_SUPPLY * p.PWM_MAX) * p.V_SUPPLY / p.PWM_MAX  # 8-bit PWM
            log["t"].append(t); log["ref"].append(ref); log["theta"].append(th)
            log["meas"].append(meas); log["v"].append(v); log["w"].append(w)
        tau_m = KT * v - B * w
        tau_g = -G * mr * grav_scale * math.cos(th)
        tau_net = tau_m + tau_g
        if abs(w) < 1e-4 and abs(tau_net) <= tc_true:   # stiction
            w = 0.0
            continue
        tau_net -= tc_true * (math.copysign(1, w) if abs(w) >= 1e-4 else math.copysign(1, tau_net))
        w += tau_net / j_true * dt_sim
        th += w * dt_sim
    return {k: np.array(v_) for k, v_ in log.items()}


def step_metrics(log, target, t0=0.0):
    t, y = log["t"] - t0, log["theta"]
    r10, r90 = 0.1 * target, 0.9 * target
    tr = t[np.argmax(y >= r90)] - t[np.argmax(y >= r10)]
    os_pct = max(0.0, (y.max() - target) / target * 100)
    band = 0.02 * abs(target)
    outside = np.where(np.abs(y - target) > band)[0]
    ts = t[outside[-1] + 1] if len(outside) and outside[-1] + 1 < len(t) else float("nan")
    sse = target - y[-1]
    return tr, os_pct, ts, sse


def main():
    kp, ki, kd = pole_placement()
    lines = [
        f"J (incl. reflected rotor) = {J:.3e} kg m^2",
        f"Kt = {KT:.4f} N m/V   b = {B:.4f} N m s/rad",
        f"Plant: K/(s(tau s+1)), K = {K:.3f} rad/s/V, tau = {TAU * 1000:.1f} ms",
        f"Pole placement wn = {WN} rad/s -> Kp = {kp:.2f} V/rad, Ki = {ki:.1f} V/(rad s), Kd = {kd:.3f} V s/rad",
        f"Gravity unbalance torque (with CW) = {G * p.gravity_unbalance() * 1000:.1f} mN m",
        "",
    ]

    # 1) Small-step response - the test to repeat on the bench for Part C.
    step = math.radians(30)
    log = simulate(lambda t: (step, 0.0, 0.0), 1.0, use_ff=False)
    tr, os_pct, ts, sse = step_metrics(log, step)
    lines.append("30 deg step (PID only, no feedforward) - bench comparison baseline:")
    lines.append(f"  rise 10-90 = {tr * 1000:.0f} ms, overshoot = {os_pct:.1f} %, "
                 f"2% settling = {ts * 1000:.0f} ms, steady-state error = {math.degrees(sse):+.2f} deg")

    # 2) Full flip on the quintic trajectory, nominal + robustness cases.
    ref = lambda t: quintic(t, FLIP_T, 0.0, THETA_END)
    cases = [
        ("nominal, FF + PID", dict()),
        ("nominal, PID only", dict(use_ff=False)),
        ("J +30 %", dict(j_scale=1.3)),
        ("J -30 %", dict(j_scale=0.7)),
        ("friction x2", dict(fric_scale=2.0)),
        ("counterweight missing", dict(grav_scale=NO_CW_SCALE)),
    ]
    lines.append("")
    lines.append(f"Full flip, quintic 0 -> {math.degrees(THETA_END):.1f} deg in {FLIP_T} s:")
    lines.append("  case                              max track err  final err   peak angle   peak |V|   landing ok")
    logs = {}
    for name, kw in cases:
        lg = simulate(ref, FLIP_T + 0.8, **kw)
        logs[name] = lg
        err = np.degrees(lg["ref"] - lg["theta"])
        peak = math.degrees(lg["theta"].max())
        ok = peak <= 180.9
        lines.append(f"  {name:32s}  {np.abs(err).max():8.2f} deg  {err[-1]:+7.2f} deg  "
                     f"{peak:8.2f} deg  {np.abs(lg['v']).max():6.1f} V   {'yes' if ok else 'NO'}")
    w_peak = 15 / 8 * THETA_END / FLIP_T
    a_peak = 10 / math.sqrt(3) * THETA_END / FLIP_T**2
    lines.append("")
    lines.append(f"Quintic peaks: omega = {w_peak:.2f} rad/s, alpha = {a_peak:.2f} rad/s^2")
    lines.append(f"  -> peak can accel along grip = g + w^2 r + a r = "
                 f"{G + w_peak**2 * p.ARM_R + a_peak * p.ARM_R:.2f} m/s^2 (used by grip_control.py)")
    report = "\n".join(lines)
    print(report)
    with open(os.path.join(OUT, "flip_control.txt"), "w") as f:
        f.write(report + "\n")

    fig, axs = plt.subplots(2, 1, figsize=(7, 5.5), sharex=True)
    lg = logs["nominal, FF + PID"]
    axs[0].plot(lg["t"], np.degrees(lg["ref"]), "k--", lw=1, label="reference (quintic)")
    for name in ("nominal, FF + PID", "nominal, PID only", "counterweight missing"):
        axs[0].plot(logs[name]["t"], np.degrees(logs[name]["theta"]), label=name)
    axs[0].axhline(180.9, color="r", lw=0.8, ls=":", label="table-contact limit")
    axs[0].set_ylabel("θ (deg)")
    axs[0].legend(fontsize=8)
    axs[0].grid(alpha=0.3)
    for name in ("nominal, FF + PID", "nominal, PID only"):
        axs[1].plot(logs[name]["t"], np.degrees(logs[name]["ref"] - logs[name]["theta"]), label=name)
    axs[1].set_ylabel("tracking error (deg)")
    axs[1].set_xlabel("t (s)")
    axs[1].legend(fontsize=8)
    axs[1].grid(alpha=0.3)
    fig.suptitle("Flip axis: simulated trajectory tracking")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "flip_tracking.png"), dpi=150)

    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.plot(log["t"] * 1000, np.degrees(log["theta"]), label="θ")
    ax.axhline(30, color="k", ls="--", lw=0.8)
    ax.set_xlabel("t (ms)")
    ax.set_ylabel("θ (deg)")
    ax.set_title(f"Flip axis 30° step, PID only (tr={tr * 1000:.0f} ms, OS={os_pct:.1f}%, ts={ts * 1000:.0f} ms)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "flip_step.png"), dpi=150)
    return 0


if __name__ == "__main__":
    sys.exit(main())
