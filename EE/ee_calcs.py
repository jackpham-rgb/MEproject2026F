"""Concept A electronics: servo PWM signals in firmware order, current budget, LTspice circuit.

    python3 EE/ee_calcs.py          (needs numpy + matplotlib; ngspice optional, runs the circuit)

1. Re-runs the firmware loop (firmware/concept_a/concept_a.ino) tick by tick: same constants,
   same step tables, same min-jerk ease and integer rounding, 10 ms loop, button at t = 1.0 s.
2. Turns every 20 ms Servo-library frame into the exact pin pulses. On a Uno the library drives
   all servos from Timer1, one after another in attach order (D9, D10, D6, D5), then waits for
   the rest of the 20 ms frame. Pulse width = map(angle, 0, 180, min_us, max_us).
3. Estimates each servo's supply current from the commanded speed and the holding torque
   (CAD loads), then the total current per step.
4. Writes the LTspice files (EE/ltspice/) and, if ngspice is installed, runs the same netlist:
   normal run + a worst-case MG996R stall, and reports the rail voltages.

Outputs: EE/out/*.png, EE/out/pulse_table.csv, EE/out/ee_report.txt, EE/ltspice/*.
Every servo electrical number marked EST is a typical datasheet value, not a measurement.
"""
import csv
import math
import os
import re
import shutil
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EE = os.path.join(ROOT, "EE")
OUT = os.path.join(EE, "out")
LT = os.path.join(EE, "ltspice")
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(LT, "pwl"), exist_ok=True)

# ---------------------------------------------------------------- firmware
src = open(os.path.join(ROOT, "firmware/concept_a/concept_a.ino")).read()
C = {}
for line in src.splitlines():
    if line.strip().startswith("const"):
        for k, v in re.findall(r"(\w+)\s*=\s*(-?\d+)", line.split("//")[0]):
            C[k] = int(v)


def steps(name):
    body = re.search(name + r"\[\]\s*=\s*\{(.*?)\n\};", src, re.S).group(1)
    out = []
    for m in re.finditer(r'\{"([\w-]+)",\s*\{(\w+),\s*(\w+),\s*(\w+),\s*(\w+)\},\s*(\w+)\}', body):
        out.append((m.group(1), tuple(C[x] for x in m.group(2, 3, 4, 5)), C[m.group(6)]))
    return out


RUN, HOMING = steps("RUN"), steps("HOMING")
SERVOS = ["turn", "lift", "wrist", "grip"]                     # attach order = Timer1 channel order
PINS = {"turn": C["PIN_TURN"], "lift": C["PIN_LIFT"], "wrist": C["PIN_WRIST"], "grip": C["PIN_GRIP"]}
US = {"turn": (544, 2400), "lift": (544, 2400), "wrist": (C["WRIST_MIN_US"], C["WRIST_MAX_US"]), "grip": (544, 2400)}
LABEL = {"turn": "Turntable MG996R", "lift": "Lift MG90S", "wrist": "Wrist MG90S", "grip": "Gripper SG90"}


def ease(s):
    return 0.0 if s <= 0 else 1.0 if s >= 1 else s ** 3 * (10 - 15 * s + 6 * s * s)


def blend(a, b, e):
    return a + int((b - a) * e + (0.5 if b > a else -0.5))     # C cast truncates toward zero, like int()


def amap(x, lo, hi):                                            # Arduino map() on longs
    return int((x - 0) * (hi - lo) / 180) + lo


T_PRESS1, T_GAP = 1000, 2000                                    # ms: START press; can removed + 2nd press 2 s after DONE
now = [C["TURN_START"], C["LIFT_DOWN"], C["WRIST_UP"], C["GRIP_OPEN"]]
mode, seq, idx, frm, t0 = "IDLE", None, 0, None, 0
t, log, events, done_at = 0, [], [], None
while True:
    if mode == "IDLE" and t >= T_PRESS1 and not events:
        mode, seq, idx, frm, t0 = "RUNNING", RUN, 0, list(now), t
        events.append((t, "press"))
        events.append((t, RUN[0][0]))
    elif mode == "DONE" and t >= done_at + T_GAP:
        mode, seq, idx, frm, t0 = "RETURNING", HOMING, 0, list(now), t
        events.append((t, "press"))
        events.append((t, HOMING[0][0]))
    if mode in ("RUNNING", "RETURNING"):
        name, to, ms = seq[idx]
        e = ease((t - t0) / ms)
        now = [blend(frm[k], to[k], e) for k in range(4)]
        if e >= 1:
            frm, now = list(to), list(to)
            idx += 1
            if idx >= len(seq):
                if mode == "RUNNING":
                    mode, done_at = "DONE", t
                    events.append((t, "DONE"))
                else:
                    mode = "HOME"
                    events.append((t, "HOME"))
            else:
                t0 = t
                events.append((t, seq[idx][0]))
    led = 1 if mode == "DONE" else 0 if mode in ("IDLE", "HOME") else (t // 400) % 2
    log.append((t, *now, led, mode))
    if mode == "HOME" and t > events[-1][0] + 500:
        break
    t += 10
T_END = log[-1][0] + 10
tt = np.array([r[0] for r in log]) / 1000.0
ang = {s: np.array([r[1 + k] for r in log], float) for k, s in enumerate(SERVOS)}
led = np.array([r[5] for r in log])
modes = [r[6] for r in log]

# ---------------------------------------------------------------- Servo-library frames (exact pulse order)
frames = []          # (t_frame_ms, {servo: (start_us, width_us, angle)})
ATTACH = {s: i * C["ATTACH_GAP_MS"] for i, s in enumerate(SERVOS)}   # setup() attaches one servo every ATTACH_GAP_MS
for tf in range(0, T_END, 20):
    k = min(tf // 10, len(log) - 1)
    off, row = 0, {}
    for i, s in enumerate(SERVOS):
        a = log[k][1 + i]
        w = amap(a, *US[s]) if tf >= ATTACH[s] else 0
        row[s] = (off, w, a)
        off += w
    frames.append((tf, row))

with open(os.path.join(OUT, "pulse_table.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t_frame_ms"] + [f"{s}_D{PINS[s]}_{x}" for s in SERVOS for x in ("angle_deg", "start_us", "width_us")])
    for tf, row in frames:
        w.writerow([tf] + [v for s in SERVOS for v in (row[s][2], row[s][0], row[s][1])])

# ---------------------------------------------------------------- current model (EST)
# I = I_idle + I_run * |w| / w_noload + I_stall * tau_hold / tau_stall      (capped at I_stall)
SP = {   # idle A, running A at full no-load speed, no-load speed deg/s, stall A, stall kg*cm   (EST, 5 V)
    "turn": (0.010, 0.30, 330.0, 2.50, 9.4),
    "lift": (0.010, 0.15, 600.0, 0.70, 1.8),
    "wrist": (0.010, 0.15, 600.0, 0.70, 1.8),
    "grip": (0.006, 0.15, 600.0, 0.65, 1.6),
}
I_UNO, I_LED = 0.045, (5.0 - 2.0) / 220            # Uno R3 board (EST); yellow LED Vf ~2.0 V
F_SQUEEZE, LEVER_M = 0.8, 0.044                    # N per arm (recommended 0.5-1 N); pad force lever about the finger pivot:
                                                   # can centre y 127 mm - pivot y 83 mm (backend/cad/model.py)
TAU_GRIP = 2 * F_SQUEEZE * LEVER_M / 9.81 * 100    # kg*cm at the gripper servo (both arms through the gears)
TAU_LIFT = (0.33, 0.30)                            # kg*cm with / without the can (cad/check/check_report.txt)
TAU_WRIST = 0.06
can_held = np.zeros(len(log), bool)
ev = dict((n, tm) for tm, n in events if n not in ("press",))
t_grip_end = ev["LIFT"] / 1000
t_release = ev["RELEASE"] / 1000
can_held[(tt >= t_grip_end) & (tt < t_release)] = True
grip_closed = ang["grip"] >= C["GRIP_CLOSED"]

cur = {}
for s in SERVOS:
    idle, run, wnl, ist, tst = SP[s]
    w_ = np.abs(np.gradient(ang[s], tt))
    w_ = np.convolve(w_, np.ones(3) / 3, mode="same")
    hold = np.zeros_like(tt)
    if s == "lift":
        hold = np.where(can_held, TAU_LIFT[0], TAU_LIFT[1])
    elif s == "wrist":
        hold = np.where(can_held, TAU_WRIST, 0.02)
    elif s == "grip":
        hold = np.where(can_held & grip_closed, TAU_GRIP, 0.0)
    cur[s] = np.minimum(idle + run * w_ / wnl + ist * hold / tst, ist)
i_tot = sum(cur.values()) + I_UNO + I_LED * led

# ---------------------------------------------------------------- hand calc: wiring resistances (EST)
R = {"adapter": 0.06,       # 5 V 4 A adapter load regulation ~5 % at 4 A
     "cable": 0.10,         # 1.5 m two-conductor 20 AWG cord, 33 mOhm/m each way
     "jack": 0.01,
     "rail": 0.05,          # jack -> breadboard rail jumpers + contacts
     "lead_turn": 0.08, "lead_lift": 0.13, "lead_wrist": 0.13, "lead_grip": 0.13,   # servo leads (+300 mm extensions)
     "uno": 0.05}           # rail -> Uno 5V/GND jumpers
L_CABLE, C_RAIL, ESR = 1.5e-6, 1000e-6, 0.08
R_SRC = R["adapter"] + R["cable"] + R["jack"]

VBUCK = 5.8          # buck output: under the 6.0 V max of the MG90S / SG90 with room for pot drift
EFF = 0.90           # XL4015 efficiency at ~1 A (EST)


TOP = {"A": "jack", "B": "bk"}     # the MG996R's power leads go straight to the jack / buck terminals, not the breadboard


def power_stage(arch, i_uno):
    """A = 5 V 4 A adapter straight to the rail + Uno 5V pin.  B = 12 V 2 A adapter -> Uno VIN, and -> XL4015 -> rail."""
    if arch == "A":
        return ["* --- design A: 5 V 4 A wall adapter, cord, jack, rail; Uno on its 5V pin ---",
                "VADP adp 0 5.0", f"RADP adp n1 {R['adapter']}", f"RCORD n1 n2 {R['cable']}", f"LCORD n2 n3 {L_CABLE}",
                f"RJACK n3 jack {R['jack']}", "VRAIL jack jr 0", f"RRAIL jr rail {R['rail']}",
                f"CRAIL rail nc {C_RAIL} IC=5.0", f"RESR nc 0 {ESR}",
                f"RUNO rail uno5v {R['uno']}", f"IUNO uno5v 0 {i_uno:.4f}"]
    return ["* --- design B: 12 V 2 A wall adapter, cord, jack ---",
            "VADP adp 0 12.0", "RADP adp n1 0.15", f"RCORD n1 n2 {R['cable']}", f"LCORD n2 n3 {L_CABLE}", f"RJACK n3 vin {R['jack']}",
            f"* --- XL4015 buck, averaged: {VBUCK} V out, 30 mOhm output resistance, input current = Pout / (eff x Vin) ---",
            "CIN vin cinn 220u IC=12", "RCIN cinn 0 0.1",
            f"BBUCK bo 0 V={VBUCK}", "VSENSE bo bo2 0", "RBOUT bo2 bk 0.03",
            f"BBIN vin 0 I={VBUCK}*I(VSENSE)/({EFF}*max(V(vin),1))",
            "VRAIL bk bkr 0", f"RRAIL bkr rail {R['rail']}", f"CRAIL rail nc {C_RAIL} IC={VBUCK}", f"RESR nc 0 {ESR}",
            "* --- Uno on VIN: M7 diode (~1.0 V) + NCP1117 5 V regulator (dropout ~1.1 V) ---",
            f"RVIN vin vinu {R['uno']}", f"IUNO vinu 0 {i_uno:.4f}",
            "BREG uno5v 0 V=min(5.0,V(vinu)-2.1)", "RREGL uno5v 0 1meg"]


# ---------------------------------------------------------------- PWL files + netlists
def pwl_pulses(s):
    pts = []
    for tf, row in frames:
        st, wd, _ = row[s]
        a = tf * 1e-3 + st * 1e-6
        b = a + wd * 1e-6
        pts += [(a, 0.0), (a + 1e-6, 5.0), (b, 5.0), (b + 1e-6, 0.0)]
    return pts


def pwl_logic(times, vals, hi=5.0):
    pts, last = [(0.0, hi * vals[0])], vals[0]
    for tm, v in zip(times, vals):
        if v != last:
            pts += [(tm, hi * last), (tm + 1e-6, hi * v)]
            last = v
    return pts


def pwl_current(arr):
    return [(float(a), round(float(b), 5)) for a, b in zip(tt, arr)]


btn = np.ones(len(log))
for tm, n in events:
    if n == "press":
        btn[(tt >= tm / 1000 - 0.04) & (tt < tm / 1000 + 0.10)] = 0      # pressed for ~140 ms
sources = {f"sig_D{PINS[s]}": pwl_pulses(s) for s in SERVOS}
sources["led_D13"] = pwl_logic(tt, led)
sources["btn_ctrl"] = pwl_logic(tt, 1 - btn, 1.0)
loads = {f"i_{s}": pwl_current(cur[s]) for s in SERVOS}


def pwl_text(pts):
    return "\n".join(f"{a:.7f} {b:.6g}" for a, b in pts)


for n, p in {**sources, **loads}.items():
    open(os.path.join(LT, "pwl", n + ".txt"), "w").write(pwl_text(p) + "\n")


def inline(pts, per=6):
    s = [f"{a:.7f} {b:.6g}" for a, b in pts]
    return "PWL(" + "\n+ ".join(" ".join(s[i:i + per]) for i in range(0, len(s), per)) + ")"


T_STALL0 = (ev["TURN"] + 500) / 1000         # worst case: the arm is blocked for 0.5 s in the middle of TURN
tend = T_END / 1000


def netlist(stall, inline_pwl):
    def P(name):
        return inline(({**sources, **loads})[name]) if inline_pwl else f"PWL file=pwl/{name}.txt"
    L = [f"* Concept A (power design B): servo PWM signals and loads in firmware order (stall test = {stall})",
         "* Generated by EE/ee_calcs.py. LTspice: File > Open (Netlists), then Run; the PWL files are in pwl/.",
         "* EE/ee_calcs.py runs this same circuit in ngspice with the PWL data written inline."]
    L += power_stage("B", I_UNO)
    L += ["* --- servos: lead resistance + supply current (EST model) ---"]
    for s in SERVOS:
        L += [f"RL_{s} {TOP['B'] if s == 'turn' else 'rail'} v_{s} {R['lead_' + s]}", f"I_{s} v_{s} 0 {P('i_' + s)}"]
    L += [f"ISTALL v_turn 0 PULSE(0 {2.5 * stall} {T_STALL0} 1m 1m 0.5 100)",
          "* --- servo signal pins (Timer1 pulses, back to back: D9, D10, D6, D5); pin ~25 ohm, servo input ~10k ---"]
    for s in SERVOS:
        d = PINS[s]
        L += [f"VSIG_D{d} pin_d{d}_src 0 {P('sig_D' + str(d))}", f"RPIN_D{d} pin_d{d}_src d{d} 25", f"RIN_D{d} d{d} 0 10k"]
    L += ["* --- status LED on D13 ---",
          f"VLED_D13 d13src 0 {P('led_D13')}",
          "RPIN13 d13src d13 25",
          "R13 d13 led_a 220",
          "DLED led_a 0 YLED",
          ".model YLED D(IS=4e-19 N=2 RS=2)",
          "* --- START button on D4: INPUT_PULLUP (~35k) to the Uno 5V, button to GND ---",
          "RPU uno5v d4 35k",
          "SBTN d4 0 btnc 0 SWBTN",
          f"VBTN btnc 0 {P('btn_ctrl')}",
          ".model SWBTN SW(Ron=0.1 Roff=1e9 Vt=0.5 Vh=0.1)",
          f".tran 1m {tend:.3f} 0 2m uic"]
    return L


for stall in (0, 1):
    open(os.path.join(LT, f"concept_a_{'stall' if stall else 'run'}.cir"), "w").write("\n".join(netlist(stall, False) + [".end", ""]))

# LTspice schematic: symbols with net labels on their pins (no wires to get wrong)
asc = ["Version 4", "SHEET 1 2600 1400"]


def sym(kind, x, y, name, value, pins):
    asc.extend([f"SYMBOL {kind} {x} {y} R0", f"SYMATTR InstName {name}", f"SYMATTR Value {value}"])
    off = {"voltage": [(0, 16), (0, 96)], "res": [(16, 16), (16, 96)], "cap": [(16, 0), (16, 64)],
           "ind": [(16, 16), (16, 96)], "current": [(0, 0), (0, 80)], "diode": [(16, 0), (16, 64)]}[kind]
    for (dx, dy), net in zip(off, pins):
        asc.append(f"FLAG {x + dx} {y + dy} {net}")


def txt(x, y, s, size=2):
    asc.append(f"TEXT {x} {y} Left {size} {s}")


X = 64
sym("voltage", X, 64, "VADP", "12.0", ["adp", "0"]); X += 128
for n, v, a, b in (("RADP", 0.15, "adp", "n1"), ("RCORD", R["cable"], "n1", "n2")):
    sym("res", X, 48, n, v, [a, b]); X += 96
sym("ind", X, 48, "LCORD", L_CABLE, ["n2", "n3"]); X += 96
sym("res", X, 48, "RJACK", R["jack"], ["n3", "vin"]); X += 96
txt(X - 16, -120, f"!BBUCK bo 0 V={VBUCK}")
txt(X - 16, -88, "!VSENSE bo bo2 0")
txt(X - 16, -56, f"!BBIN vin 0 I={VBUCK}*I(VSENSE)/({EFF}*max(V(vin),1))")
txt(X - 16, -150, f";XL4015 buck (averaged model): {VBUCK} V out, input current = Pout / (eff x Vin)", 1)
txt(X - 16, -24, "!CIN vin cinn 220u IC=12")
txt(X - 16, 8, "!RCIN cinn 0 0.1")
sym("res", X, 48, "RBOUT", 0.03, ["bo2", "bk"]); X += 96
txt(X - 16, 40 - 200, "!VRAIL bk bkr 0")
sym("res", X, 48, "RRAIL", R["rail"], ["bkr", "rail"]); X += 96
sym("cap", X, 64, "CRAIL", "1000u", ["rail", "nc"]); sym("res", X, 112, "RESR", ESR, ["nc", "0"]); X += 128
for s in SERVOS:
    sym("res", X, 48, f"RL_{s}", R["lead_" + s], ["bk" if s == "turn" else "rail", f"v_{s}"])
    sym("current", X + 16, 176, f"I_{s}", f"PWL file=pwl/i_{s}.txt", [f"v_{s}", "0"])
    txt(X - 16, 300, f";{LABEL[s]}", 1)
    X += 144
sym("current", X + 16, 176, "ISTALL", f"PULSE(0 {{2.5*STALL}} {T_STALL0} 1m 1m 0.5 100)", ["v_turn", "0"]); X += 144
sym("res", X, 48, "RVIN", R["uno"], ["vin", "vinu"])
sym("current", X + 16, 176, "IUNO", I_UNO, ["vinu", "0"])
txt(X - 16, -56 + 120, "!BREG uno5v 0 V=min(5.0,V(vinu)-2.1)")
txt(X - 16, -24 + 120, "!RREGL uno5v 0 1meg")
txt(X - 16, 300, ";Uno on VIN: M7 diode + NCP1117 regulator", 1)
X, Y = 64, 480
for s in SERVOS:
    d = PINS[s]
    sym("voltage", X, Y, f"VSIG_D{d}", f"PWL file=pwl/sig_D{d}.txt", [f"pin_d{d}_src", "0"])
    sym("res", X + 96, Y - 16, f"RPIN_D{d}", 25, [f"pin_d{d}_src", f"d{d}"])
    sym("res", X + 192, Y - 16, f"RIN_D{d}", "10k", [f"d{d}", "0"])
    txt(X, Y + 140, f";D{d}: {LABEL[s]}", 1)
    X += 320
sym("voltage", X, Y, "VLED_D13", "PWL file=pwl/led_D13.txt", ["d13src", "0"])
sym("res", X + 96, Y - 16, "RPIN13", 25, ["d13src", "d13"])
sym("res", X + 192, Y - 16, "R13", 220, ["d13", "led_a"])
sym("diode", X + 288, Y, "DLED", "YLED", ["led_a", "0"])
X += 448
sym("res", X, Y - 16, "RPU", "35k", ["uno5v", "d4"])
txt(X + 128, Y + 140, "!SBTN d4 0 btnc 0 SWBTN")
txt(X - 16, Y + 180, ";START button = switch d4 -> GND, closed while V(btnc) > 0.5 V", 1)
sym("voltage", X + 256, Y, "VBTN", "PWL file=pwl/btn_ctrl.txt", ["btnc", "0"])
txt(64, 820, "!.model YLED D(IS=4e-19 N=2 RS=2)")
txt(64, 860, "!.model SWBTN SW(Ron=0.1 Roff=1e9 Vt=0.5 Vh=0.1)")
txt(64, 900, f"!.tran 1m {tend:.3f} 0 2m uic")
txt(64, 940, "!.step param STALL list 0 1")
txt(64, 990, f";Concept A, power design B (12 V adapter, XL4015 buck {VBUCK} V for the servos, Uno on VIN) + servo PWM pulses (D9, D10, D6, D5 back to back each 20 ms) in firmware order. "
             "STALL=1 adds a 0.5 s MG996R stall in the middle of TURN. Generated by EE/ee_calcs.py.", 1)
txt(64, 1020, ";Plot: V(rail), V(uno5v), V(d9), V(d10), V(d6), V(d5), V(d13), V(d4), I(I_turn)+I(I_lift)+I(I_wrist)+I(I_grip)", 1)
open(os.path.join(LT, "concept_a.asc"), "w").write("\n".join(asc) + "\n")

# ---------------------------------------------------------------- ngspice run
spice = {}
if shutil.which("ngspice"):
    for stall in (0, 1):
        deck = netlist(stall, True) + [
            ".control", "set noaskquit", "run",
            f"wrdata {os.path.join(OUT, 'spice_' + str(stall) + '.dat')} v(rail) v(uno5v) v(v_turn) v(v_lift) v(v_wrist) v(v_grip) v(d9) v(d4) v(d13)",
            ".endc", ".end"]
        path = os.path.join(OUT, f"_deck_{stall}.sp")
        open(path, "w").write("\n".join(deck))
        r = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True, timeout=900)
        os.remove(path)
        dat = os.path.join(OUT, f"spice_{stall}.dat")
        if r.returncode != 0 or not os.path.exists(dat):
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit("ngspice failed")
        a = np.loadtxt(dat)
        os.remove(dat)
        spice[stall] = {"t": a[:, 0], "rail": a[:, 1], "uno": a[:, 3], "turn": a[:, 5], "lift": a[:, 7],
                        "wrist": a[:, 9], "grip": a[:, 11], "d9": a[:, 13], "d4": a[:, 15], "d13": a[:, 17]}

# ---------------------------------------------------------------- plots
order = [n for _, n in events if n != "press"]
spans = []
for i, (tm, n) in enumerate([(tm, n) for tm, n in events if n != "press"]):
    nxt = [x for x, m in events if x > tm and m != "press"]
    if n in ("DONE", "HOME"):
        continue
    spans.append((tm / 1000, (nxt[0] if nxt else T_END) / 1000, n))
COL = {"turn": "#2f6fdb", "lift": "#e07b00", "wrist": "#1f9d55", "grip": "#c0392b"}


def shade(ax):
    for k, (a, b, n) in enumerate(spans):
        ax.axvspan(a, b, color="#f1f3f6" if k % 2 else "#e6eaf0", lw=0)


fig, axs = plt.subplots(7, 1, figsize=(13, 13), sharex=True, gridspec_kw={"height_ratios": [0.6, 1, 1, 1, 1, 0.6, 1.3]})
shade(axs[0]); axs[0].step(tt, btn * 5, where="post", color="#1f9d55"); axs[0].set_ylabel("D4\nbutton (V)")
for a, b, n in spans:
    axs[0].text((a + b) / 2, 6.0, n, ha="center", fontsize=8, rotation=0 if b - a > 0.9 else 90)
axs[0].set_ylim(-0.5, 8.5)
for k, s in enumerate(SERVOS):
    ax = axs[1 + k]; shade(ax)
    pw = np.array([row[s][1] for _, row in frames]); tf = np.array([f[0] for f in frames]) / 1000
    ax.step(tf, pw, where="post", color=COL[s], lw=1.8)
    ax.set_ylabel(f"D{PINS[s]} pulse (µs)\n{LABEL[s]}", fontsize=9)
    lo, hi = US[s]
    a2 = ax.secondary_yaxis("right", functions=(lambda u, lo=lo, hi=hi: (u - lo) * 180 / (hi - lo),
                                                 lambda d, lo=lo, hi=hi: lo + d * (hi - lo) / 180))
    a2.set_ylabel("angle (°)", fontsize=9)
ax = axs[5]; shade(ax); ax.step(tt, led * 5, where="post", color="#b8860b"); ax.set_ylabel("D13\nLED (V)")
ax = axs[6]; shade(ax)
for s in SERVOS:
    ax.plot(tt, cur[s], color=COL[s], lw=1.2, label=LABEL[s])
ax.plot(tt, i_tot, color="k", lw=2, label="total (incl. Uno + LED)")
ax.set_ylabel("supply current (A)\nEST model"); ax.legend(fontsize=8, ncol=5, loc="upper right"); ax.set_xlabel("time (s)")
fig.suptitle("Concept A signals in firmware order: button → GRIP → LIFT → FLIP → TURN → LOWER → RELEASE → DONE → (can removed, press) → homing", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(os.path.join(OUT, "signals_sequence.png"), dpi=130)
plt.close(fig)

# zoom: the 4 back-to-back pulses inside single 20 ms frames
snap = [("HOME (all 4 attached, before START)", 960), ("mid-FLIP", (ev["FLIP"] + ev["TURN"]) // 2 // 20 * 20),
        ("DONE (can at target)", (ev["DONE"] + 500) // 20 * 20)]
fig, axs = plt.subplots(len(snap), 1, figsize=(12, 7.5), sharex=True)
for ax, (title, tf) in zip(axs, snap):
    row = dict(frames)[tf]
    for k, s in enumerate(SERVOS):
        st, wd, a = row[s]
        y0 = (3 - k) * 1.4
        xs = [0, st, st, st + wd, st + wd, 20000]
        ax.plot(np.array(xs) / 1000, y0 + np.array([0, 0, 1, 1, 0, 0]), color=COL[s], lw=2)
        ax.text((st + wd / 2) / 1000, y0 + 1.12, f"D{PINS[s]} {wd} µs ({a}°)", ha="center", fontsize=8, color=COL[s])
    end = sum(row[s][1] for s in SERVOS)
    ax.axvline(end / 1000, color="#888", ls=":", lw=1)
    ax.text(end / 1000 + 0.2, 4.6, f"all 4 pulses done at {end / 1000:.2f} ms; idle until 20 ms", fontsize=8, color="#555")
    ax.set_yticks([]); ax.set_title(f"{title}: frame at t = {tf / 1000:.2f} s", fontsize=10, loc="left")
    ax.set_xlim(-0.3, 20.3); ax.set_ylim(-0.3, 5.6)
axs[-1].set_xlabel("time inside one 20 ms Servo-library frame (ms)   ·   0 V / 5 V logic, pulses back to back in attach order")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "pwm_frames.png"), dpi=130)
plt.close(fig)

if spice:
    fig, axs = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for ax, stall in zip(axs, (0, 1)):
        d = spice[stall]; shade(ax)
        ax.plot(d["t"], d["rail"], label=f"servo rail (buck {VBUCK} V)", lw=1.4)
        ax.plot(d["t"], d["uno"], label="Uno 5V pin", lw=1.2)
        ax.plot(d["t"], d["turn"], label="MG996R terminals", lw=1.0)
        ax.axhline(4.5, color="#c0392b", ls="--", lw=1); ax.text(0.1, 4.51, "ATmega328P 16 MHz minimum (4.5 V)", fontsize=8, color="#c0392b")
        ax.set_ylabel("V"); ax.set_ylim(4.2, 6.1); ax.legend(fontsize=8, loc="lower right")
        ax.set_title("ngspice, design B: normal run" if not stall else "ngspice, design B: worst case, MG996R stalled 0.5 s in TURN (arm blocked)", fontsize=10, loc="left")
    axs[-1].set_xlabel("time (s)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "spice_rail.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- buck or no buck: both power designs, 3 cases
# A = 5 V 4 A adapter straight to the rail and the Uno 5V pin (current design)
# B = 12 V adapter -> XL4015 buck at 6.0 V for the servos; Uno on VIN through its own regulator
LIM = {"adp5_A": 4.0, "adp12_A": 2.0, "buck_A": 5.0, "buck_eff": 0.90, "bb_contact_A": 1.0,
       "uno_min_V": 4.5, "bod_V": 2.7, "servo_min_V": 4.8, "servo_max_V": {"turn": 7.2, "lift": 6.0, "wrist": 6.0, "grip": 6.0},
       "led_mA": 20.0, "pins_total_mA": 200.0, "reg_W": 1.0, "vin_min": 7.0, "vin_max": 12.0}
CASES = [("normal", "Normal run"), ("stall", "MG996R stalled 0.5 s in TURN (arm blocked)"),
         ("powerup", "Power-up away from home, servos attached 0.3 s apart (this firmware)"),
         ("powerup_all", "Power-up away from home, all 4 attached at once (old firmware)")]
T_PU = (0.05, 0.30)
I_LOAD_UNO = I_UNO + I_LED


def power_netlist(arch, case, inline_pwl):
    def P(name):
        return inline(loads[name]) if inline_pwl else f"PWL file=pwl/{name}.txt"
    st = 1 if case == "stall" else 0
    pu = case in ("powerup", "powerup_all")
    L = [f"* Concept A power design {arch} ({'5 V adapter direct' if arch == 'A' else f'12 V adapter + XL4015 buck {VBUCK} V'}), case: {case}",
         "* Generated by EE/ee_calcs.py (servo currents = EST model, see EE/README.md)"]
    L += power_stage(arch, I_LOAD_UNO)
    for s in SERVOS:
        L += [f"RL_{s} {TOP[arch] if s == 'turn' else 'rail'} v_{s} {R['lead_' + s]}", f"I_{s} v_{s} 0 {P('i_' + s)}",
              f"IPU_{s} v_{s} 0 PULSE(0 {SP[s][3] * pu} "
              f"{T_PU[0] + (0 if case == 'powerup_all' else ATTACH[s] / 1000)} 1m 1m {T_PU[1] - 0.02} 100)"]
    L += [f"ISTALL v_turn 0 PULSE(0 {2.5 * st} {T_STALL0} 1m 1m 0.5 100)",
          f".tran 1m {tend:.3f} 0 2m uic"]
    return L


pres = {}
for arch in ("A", "B"):
    for case, _ in CASES:
        open(os.path.join(LT, f"power_{arch}_{case}.cir"), "w").write("\n".join(power_netlist(arch, case, False) + [".end", ""]))
        if not shutil.which("ngspice"):
            continue
        dat = os.path.join(OUT, f"_p{arch}{case}.dat")
        deck = power_netlist(arch, case, True) + [".control", "set noaskquit", "run",
               f"wrdata {dat} v(uno5v) v(rail) v(v_turn) v(v_lift) v(v_wrist) v(v_grip) i(vadp) i(vrail)" + (" i(vsense)" if arch == "B" else ""),
               ".endc", ".end"]
        path = os.path.join(OUT, f"_p{arch}{case}.sp")
        open(path, "w").write("\n".join(deck))
        r = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True, timeout=900)
        os.remove(path)
        if r.returncode != 0 or not os.path.exists(dat):
            print(r.stdout[-1500:], r.stderr[-1500:])
            raise SystemExit("ngspice failed (power comparison)")
        a = np.loadtxt(dat)
        os.remove(dat)
        d = {"t": a[:, 0], "uno": a[:, 1], "rail": a[:, 3], "turn": a[:, 5], "lift": a[:, 7], "wrist": a[:, 9],
             "grip": a[:, 11], "i_adp": -a[:, 13], "i_rail": a[:, 15]}
        d["i_servo"] = a[:, 17] if arch == "B" else d["i_adp"] - I_LOAD_UNO
        pres[(arch, case)] = d

checks = []          # (arch, case, item, value, limit, verdict)


def chk(arch, case, item, val, lim, ok, note=""):
    checks.append((arch, case, item, val, lim, "PASS" if ok else ("WARN" if note.startswith("warn") else "FAIL"), note))


if pres:
    for arch in ("A", "B"):
        for case, _ in CASES:
            d = pres[(arch, case)]
            skip = d["t"] > 0.02                       # ignore the t = 0 initial-condition step
            umin = d["uno"][skip].min()
            chk(arch, case, "Uno 5 V (min)", f"{umin:.2f} V", "≥ 4.5 V (16 MHz)", umin >= LIM["uno_min_V"],
                "" if umin >= LIM["uno_min_V"] else ("warn: runs, no reset (> 2.7 V BOD)" if umin > LIM["bod_V"] + 0.5 else "reset"))
            smin = min(d[s][skip].min() for s in SERVOS)
            chk(arch, case, "Servo supply (min)", f"{smin:.2f} V", "≥ 4.8 V rated", smin >= LIM["servo_min_V"],
                "" if smin >= LIM["servo_min_V"] else "warn: servos slower/weaker for that moment")
            smax = max(d[s][skip].max() for s in SERVOS)
            chk(arch, case, "Servo supply (max)", f"{smax:.2f} V", "≤ 6.0 V (MG90S, SG90)", smax <= 6.0)
            ia = d["i_adp"][skip].max()
            lim = LIM["adp5_A"] if arch == "A" else LIM["adp12_A"]
            chk(arch, case, f"{'5 V' if arch == 'A' else '12 V'} adapter current (max)", f"{ia:.2f} A", f"≤ {lim} A rating", ia <= lim,
                "" if ia <= lim else "adapter current-limits: rail collapses" + (", Uno resets" if arch == "A" else "; Uno stays up only if VIN holds"))
            if arch == "B":
                ib = d["i_servo"][skip].max()
                chk(arch, case, "XL4015 output current (max)", f"{ib:.2f} A", "≤ 5 A", ib <= LIM["buck_A"])
            ibb = d["i_rail"][skip].max()
            chk(arch, case, "Breadboard rail current (max)", f"{ibb:.2f} A", "≤ ~1 A per contact", ibb <= LIM["bb_contact_A"],
                "" if ibb <= LIM["bb_contact_A"] else "warn: more than one contact's rating")
    reg_w = (12.0 - 0.15 * 0.1 - 1.0 - 5.0) * I_LOAD_UNO
    chk("B", "all", "Uno regulator heat", f"{reg_w:.2f} W", "≤ ~1 W (SOT-223)", reg_w <= LIM["reg_W"])
    chk("A", "all", "USB plugged in while powered", "two 5 V sources", "not allowed", False, "rule: unplug the adapter before USB (no Serial Monitor while running)")
    chk("B", "all", "USB plugged in while powered", "VIN > 6.6 V", "Uno switches USB power off", True)

    fig, axs = plt.subplots(len(CASES), 2, figsize=(14, 11.5), sharex=True)
    for j, arch in enumerate(("A", "B")):
        for i, (case, title) in enumerate(CASES):
            ax = axs[i][j]
            d = pres[(arch, case)]
            shade(ax)
            ax.plot(d["t"], d["uno"], label="Uno 5 V", lw=1.5, color="#0f7c8c")
            ax.plot(d["t"], d["turn"], label="MG996R supply", lw=1.1, color="#2f6fdb")
            ax.plot(d["t"], d["grip"], label="gripper supply", lw=1.0, color="#c0392b")
            ax.axhline(4.5, color="#0f7c8c", ls="--", lw=0.8)
            ax.axhline(4.8, color="#888", ls=":", lw=0.8)
            ax.axhline(6.0, color="#888", ls=":", lw=0.8)
            ax.set_ylim(3.0, 6.3)
            ax2 = ax.twinx()
            ax2.plot(d["t"], d["i_adp"], color="#e07b00", lw=0.9, alpha=0.8, label="adapter current")
            ax2.axhline(LIM["adp5_A"] if arch == "A" else LIM["adp12_A"], color="#e07b00", ls="--", lw=0.8)
            ax2.set_ylim(0, 6.5)
            ax2.set_ylabel("A", color="#e07b00", fontsize=8)
            ax.set_ylabel("V", fontsize=8)
            ax.set_title(f"{'A: 5 V adapter direct' if arch == 'A' else f'B: 12 V + buck {VBUCK} V'} · {title}", fontsize=9, loc="left")
            if i == 0 and j == 0:
                h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
                ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="lower left", ncol=2)
    fig.supxlabel("time (s)   ·   dashed teal: 4.5 V Uno minimum · dotted: 4.8 / 6.0 V servo range · dashed orange: adapter rating (right axis, A)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "power_compare.png"), dpi=125)
    plt.close(fig)

# ---------------------------------------------------------------- report
L = ["CONCEPT A ELECTRONICS (EE/ee_calcs.py)", ""]
L += ["1. SERVO SIGNAL (PWM) BASICS",
      "   Servo library on a Uno: Timer1, prescaler 8 -> 0.5 us resolution; one 20 ms frame (50 Hz) for all servos.",
      "   In each frame the pulses go out back to back in attach order: D9 turntable, D10 lift, D6 wrist, D5 gripper.",
      "   width_us = map(angle, 0, 180, min_us, max_us); default 544-2400 us, wrist attached with 500-2500 us.",
      "   (The library subtracts a 2 us trim; ISR latency adds ~1-2 us. Both are inside the servos' deadband.)",
      f"   Duty cycle range: {544 / 20000:.1%} (0 deg) to {2400 / 20000:.1%} (180 deg); wrist {500 / 20000:.1%} to {2500 / 20000:.1%}.",
      "   Longest frame use: 4 pulses <= 2400 + 2400 + 2500 + 2400 = 9.7 ms, so all 4 fit in the 20 ms frame.", ""]
L += ["2. PULSE WIDTHS AT THE END OF EACH STEP, IN FIRMWARE ORDER"]
L.append("   %-9s %-7s | " % ("step", "t (s)") + " | ".join(f"D{PINS[s]} {s:5s} deg/us" for s in SERVOS))
first = log[0]
L.append("   %-9s %-7s | " % ("HOME", "0.00") + " | ".join(f"{first[1 + k]:4d} / {amap(first[1 + k], *US[s]):4d}  " for k, s in enumerate(SERVOS)))
for nm, pose, ms in RUN + HOMING:
    tm = [x for x, m in events if m == nm][0]
    L.append("   %-9s %-7s | " % (nm, f"{tm / 1000 + ms / 1000:.2f}") + " | ".join(f"{pose[k]:4d} / {amap(pose[k], *US[s]):4d}  " for k, s in enumerate(SERVOS)))
L += ["   (t = time the step ends; the START press is at 1.00 s and the homing press 2 s after DONE.)", ""]
L += ["3. CURRENT BUDGET (EST model: idle + speed share of running current + holding torque share of stall current)"]
for nm, pose, ms in RUN + HOMING:
    a = [x for x, m in events if m == nm][0] / 1000
    m = (tt >= a) & (tt < a + ms / 1000)
    L.append(f"   {nm:9s} peak {i_tot[m].max():.2f} A   " + "  ".join(f"{s} {cur[s][m].max():.2f}" for s in SERVOS))
L += [f"   Peak of the whole run: {i_tot.max():.2f} A. XL4015 rating 5 A -> {5 / i_tot.max():.1f}x margin; 12 V 2 A adapter -> see section 6.",
      f"   Gripper hold: {F_SQUEEZE} N per arm x {LEVER_M * 1000:.0f} mm lever x 2 arms = {TAU_GRIP:.2f} kg*cm "
      f"= {TAU_GRIP / 1.6:.0%} of the SG90 stall torque -> ~{0.65 * TAU_GRIP / 1.6:.2f} A while it holds the can.",
      f"   The SG90 can make at most {1.6 * 9.81 / 100 / (2 * LEVER_M):.2f} N per arm here; squeeze 0.5-1 N (0.39 N minimum, SF 3).",
      "   Worst cases outside the normal run: one MG996R stall 2.5 A; all 4 servos jumping at power-up 4.6 A (> 4 A:",
      "   power up with the robot at home; the code writes the home pose before attach so nothing jumps).", ""]
L += ["4. OTHER CIRCUIT VALUES",
      f"   Status LED: (5.0 - 2.0 V) / 220 ohm = {I_LED * 1000:.1f} mA  (Uno pin limit 20 mA recommended, 40 mA absolute)",
      "   START button: INPUT_PULLUP 20-50 kOhm -> 0.1-0.25 mA when pressed; debounced 40 ms in code",
      "   Servo signal inputs draw < 1 mA each from D9/D10/D6/D5",
      f"   Servo path (design B): buck {VBUCK} V, 0.03 ohm out + rail {R['rail']} ohm; Uno on its own VIN regulator (EST)",
      f"   Hand calc, rail drop at the run peak: {i_tot.max():.2f} A x {0.03 + R['rail']:.2f} ohm = {i_tot.max() * (0.03 + R['rail']):.2f} V",
      f"   Hand calc, rail drop in an MG996R stall: {2.5 + i_tot.max():.2f} A x {0.03 + R['rail']:.2f} ohm = {(2.5 + i_tot.max()) * (0.03 + R['rail']):.2f} V",
      f"   12 V side at the run peak: {VBUCK} V x {i_tot.max():.2f} A / ({EFF} x 12 V) = {VBUCK * i_tot.max() / (EFF * 12):.2f} A, plus the Uno {I_UNO + I_LED:.3f} A",
      f"   1000 uF capacitor: a 1 A step for 100 us (adapter response, EST) droops it 1 A x 100 us / 1000 uF = 0.10 V", ""]
if spice:
    L += ["5. NGSPICE RESULTS, DESIGN B WITH THE REAL SIGNALS (EE/ltspice/concept_a_run.cir / _stall.cir)"]
    for stall in (0, 1):
        d = spice[stall]
        sk = d["t"] > 0.02
        L.append(f"   {'normal run ' if not stall else 'MG996R stall'}: servo rail {d['rail'][sk].min():.2f}-{d['rail'][sk].max():.2f} V, "
                 f"Uno 5V min {d['uno'][sk].min():.2f} V, MG996R min {d['turn'][sk].min():.2f} V, gripper min {d['grip'][sk].min():.2f} V")
    L.append("")
if pres:
    L += ["6. BUCK OR NO BUCK: both power designs, 3 cases (ngspice; EE/ltspice/power_*.cir)",
          f"   A = 5 V 4 A adapter direct (rail + Uno 5V pin).  B = 12 V 2 A adapter -> XL4015 at {VBUCK} V (servos), Uno on VIN.",
          "   %-4s %-11s %-30s %-16s %-26s %s" % ("des", "case", "check", "value", "limit", "result")]
    for c in checks:
        L.append("   %-4s %-11s %-30s %-16s %-26s %s %s" % c)
    for arch in ("A", "B"):
        d = pres[(arch, "normal")]
        p_in = d["i_adp"].max() * (5.0 if arch == "A" else 12.0)
        L.append(f"   {arch}: peak input power, normal run = {p_in:.1f} W (adapter {'20' if arch == 'A' else '24'} W)")
    L.append("")
open(os.path.join(OUT, "ee_report.txt"), "w").write("\n".join(L))
print("\n".join(L))
