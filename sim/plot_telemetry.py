"""Plot and score a telemetry log captured from the Uno's serial port.

Usage:  python3 plot_telemetry.py LOG.csv [--out out/run.png]
Capture on the bench with e.g.  arduino-cli monitor -p /dev/ttyACM0 -c baudrate=250000 > run.csv
('#' event lines are skipped). Reports flip tracking error, landing angle and
grip-force settling - the validation numbers for the Part C report. Compare
against sim/out/*.txt (the Phase 1 predictions).
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLS = ["t_ms", "state", "theta_ref_mdeg", "theta_mdeg", "mV", "fset_mN", "f_mN", "servo_cdeg", "fault"]


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.reader(line for line in f if line.strip() and not line.startswith("#")):
            if len(r) >= len(COLS) and r[0].strip().isdigit():
                rows.append(r)
    d = {c: [r[i] for r in rows] for i, c in enumerate(COLS)}
    out = {"state": np.array(d["state"])}
    for c in COLS:
        if c != "state":
            out[c] = np.array(d[c], dtype=float)
    out["t"] = (out["t_ms"] - out["t_ms"][0]) / 1000
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = load(a.log)
    th, ref = d["theta_mdeg"] / 1000, d["theta_ref_mdeg"] / 1000
    flip = d["state"] == "FLIP"
    grip = d["state"] == "GRIP"
    print(f"samples: {len(th)}   states seen: {', '.join(dict.fromkeys(d['state']))}")
    if flip.any():
        e = ref[flip] - th[flip]
        print(f"FLIP: max |tracking error| = {np.abs(e).max():.2f} deg, RMS = {np.sqrt(np.mean(e**2)):.2f} deg, "
              f"peak angle = {th.max():.2f} deg (limit 180.9), angle at release = {th[flip][-1]:.2f} deg, "
              f"peak |V| = {np.abs(d['mV'][flip]).max() / 1000:.1f} V")
    if grip.any():
        f = d["f_mN"] / 1000
        fs = d["fset_mN"][grip][0] / 1000
        t = d["t"][grip]
        inside = np.abs(f[grip] - fs) < 0.25
        t_first = t[np.argmax(inside)] - t[0] if inside.any() else float("nan")
        print(f"GRIP: setpoint {fs:.2f} N, time to +-0.25 N band = {t_first * 1000:.0f} ms, "
              f"peak force = {f.max():.2f} N, force at flip start = {f[grip][-1]:.2f} N")

    fig, axs = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    axs[0].plot(d["t"], ref, "k--", lw=1, label="θ ref")
    axs[0].plot(d["t"], th, label="θ measured")
    axs[0].set_ylabel("deg")
    axs[0].legend(fontsize=8)
    axs[1].plot(d["t"], d["mV"] / 1000, color="tab:orange")
    axs[1].set_ylabel("motor V")
    axs[2].plot(d["t"], d["fset_mN"] / 1000, "k--", lw=1, label="F set")
    axs[2].plot(d["t"], d["f_mN"] / 1000, color="tab:green", label="F measured")
    axs[2].set_ylabel("grip N")
    axs[2].set_xlabel("t (s)")
    axs[2].legend(fontsize=8)
    # shade states
    edges = np.flatnonzero(d["state"][1:] != d["state"][:-1]) + 1
    for ax in axs:
        ax.grid(alpha=0.3)
        for i in edges:
            ax.axvline(d["t"][i], color="0.8", lw=0.8)
    for i in np.r_[0, edges]:
        axs[0].text(d["t"][i], axs[0].get_ylim()[1], d["state"][i], fontsize=7, va="bottom", rotation=30)
    fig.tight_layout()
    out = a.out or os.path.splitext(a.log)[0] + ".png"
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
