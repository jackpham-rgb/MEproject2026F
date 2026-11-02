# EE: Concept A electronics calculations

Everything electrical lives here. One script makes all of it from the real firmware:

```bash
python3 EE/ee_calcs.py      # numpy + matplotlib; runs the circuit too if ngspice is installed
```

| File | What |
|---|---|
| `out/signals_sequence.png` | Button, the 4 servo signals and the LED, in firmware order, plus the current model |
| `out/pwm_frames.png` | Inside one 20 ms frame: the 4 pulses back to back, at HOME, mid-FLIP and DONE |
| `out/pulse_table.csv` | Every 20 ms frame of the run: angle, pulse start and pulse width for each servo |
| `out/spice_rail.png` | ngspice: rail and Uno voltage, normal run and an MG996R stall |
| `out/ee_report.txt` | All numbers below, as computed |
| `ltspice/concept_a_run.cir`, `concept_a_stall.cir` | **LTspice netlists**: File → Open (file type *Netlists*), then Run |
| `ltspice/concept_a.asc` | The same circuit as an LTspice schematic (`.step param STALL list 0 1`) |
| `ltspice/pwl/*.txt` | Signal and load waveforms the circuit plays (PWL files) |

The script re-runs the firmware loop exactly: same constants and step tables read from
`concept_a.ino`, same min-jerk ease and integer rounding, 10 ms loop. The START press is at
t = 1.0 s, and the homing press is 2 s after DONE (the can has been lifted off). Numbers marked
**EST** are typical datasheet values, not measurements.

The LTspice files were checked by running the same netlist in ngspice (it has no LTspice of its
own). The `.asc` schematic has not been opened in LTspice yet; if a part comes up unconnected,
use the `.cir` netlists, which hold the identical circuit.

## 1. The servo signal (wave) calculation

A hobby servo reads one pulse every 20 ms (50 Hz). The pulse width sets the angle:

**width (µs) = map(angle, 0, 180, min, max)** — the Arduino Servo library's own formula.
- Turntable, lift, gripper: default min/max = 544 / 2400 µs → 10.3 µs per degree.
- Wrist: attached with 500 / 2500 µs → 11.1 µs per degree, so an MG90S reaches a full 180°.
- Duty cycle: 544 / 20 000 = 2.7 % at 0°, 2400 / 20 000 = 12.0 % at 180° (wrist 2.5–12.5 %).

**The exact order on the pins.** On a Uno, the Servo library drives every servo from Timer1
(prescaler 8, 0.5 µs ticks). In each 20 ms frame it sends the pulses **one after another, in
attach order: D9 turntable → D10 lift → D6 wrist → D5 gripper**, then waits out the frame.
The longest possible chain is 2400 + 2400 + 2500 + 2400 µs = 9.7 ms, so all four always fit
in the 20 ms frame (`out/pwm_frames.png`).

![PWM frames](out/pwm_frames.png)

**Pulse widths at the end of each step, in firmware order** (angle / µs):

| Step | Ends at t (s) | D9 turntable | D10 lift | D6 wrist | D5 gripper |
|---|---:|---|---|---|---|
| HOME | — | 135° / 1936 | 30° / 853 | 0° / 500 | 20° / 750 |
| GRIP | 1.80 | 135° / 1936 | 30° / 853 | 0° / 500 | **95° / 1523** |
| LIFT | 2.80 | 135° / 1936 | **75° / 1317** | 0° / 500 | 95° / 1523 |
| FLIP | 4.30 | 135° / 1936 | 75° / 1317 | **180° / 2500** | 95° / 1523 |
| TURN | 5.80 | **45° / 1008** | 75° / 1317 | 180° / 2500 | 95° / 1523 |
| LOWER | 6.80 | 45° / 1008 | **30° / 853** | 180° / 2500 | 95° / 1523 |
| RELEASE | 7.40 | 45° / 1008 | 30° / 853 | 180° / 2500 | **70° / 1265** |
| *can lifted off, button pressed* | | | | | |
| H-LIFT | 10.40 | 45° / 1008 | **75° / 1317** | 180° / 2500 | 70° / 1265 |
| H-CLOSE | 11.20 | 45° / 1008 | 75° / 1317 | 180° / 2500 | **95° / 1523** |
| H-WRIST | 12.70 | 45° / 1008 | 75° / 1317 | **0° / 500** | 95° / 1523 |
| H-TURN | 14.20 | **135° / 1936** | 75° / 1317 | 0° / 500 | 95° / 1523 |
| H-LOWER | 15.20 | 135° / 1936 | **30° / 853** | 0° / 500 | 95° / 1523 |
| H-OPEN | 16.00 | 135° / 1936 | 30° / 853 | 0° / 500 | **20° / 750** |

Bold = the servo that moves in that step. Only one servo moves at a time. Between the step ends
each pulse width follows the slow–fast–slow (minimum-jerk) curve, updated every 20 ms:

![Signals in firmware order](out/signals_sequence.png)

The LED on D13 blinks (400 ms on / off) while moving, stays on at DONE, and is off at home.

## 2. Current budget

Model per servo (**EST**): *idle* + *running current × commanded speed / no-load speed* +
*stall current × holding torque / stall torque*. Holding torques come from the CAD loads.

| Servo | Idle | Running (full speed) | No-load speed | Stall | Holding torque in the run |
|---|---:|---:|---:|---:|---|
| MG996R turntable | 10 mA | 0.30 A | 330 °/s | 2.5 A @ 9.4 kg·cm | ≈ 0 (weight on the 6807 bearing) |
| MG90S lift | 10 mA | 0.15 A | 600 °/s | 0.7 A @ 1.8 kg·cm | 0.33 kg·cm with the can |
| MG90S wrist | 10 mA | 0.15 A | 600 °/s | 0.7 A @ 1.8 kg·cm | 0.06 kg·cm with the can |
| SG90 gripper | 6 mA | 0.15 A | 600 °/s | 0.65 A @ 1.6 kg·cm | 0.72 kg·cm while squeezing (below) |

Plus the Uno board ≈ 45 mA and the LED 13.6 mA.

| Step | Peak total current |
|---|---:|
| GRIP | 0.26 A |
| LIFT | 0.56 A |
| FLIP | 0.60 A |
| **TURN** | **0.65 A** (largest) |
| LOWER | 0.56 A |
| RELEASE | 0.24 A |
| Homing steps | ≤ 0.34 A |

**Peak 0.65 A vs a 4 A adapter: 6× margin.** The biggest steady load is not a moving servo but
the gripper holding the can:

- Squeeze 0.8 N per arm × 44 mm lever (finger pivot y = 83 mm to can centre y = 127 mm) × 2
  arms = 7.0 N·cm = **0.72 kg·cm = 45 % of the SG90 stall torque → ≈ 0.29 A** for the ~5 s it
  holds the can (GRIP end to RELEASE).
- The SG90 can make at most 1.6 kg·cm / (2 × 4.4 cm) = **1.8 N per arm** here. Set
  `GRIP_CLOSED` for **0.5–1 N per arm** (minimum 0.39 N for a 3× slip margin, dents at ~8 N).
  Squeezing harder would leave the SG90 near stall and warm.

Worst cases outside the normal run:
- **One MG996R stall** (arm blocked): +2.5 A → about 3.2 A total, inside 4 A. Simulated below.
- **All 4 servos jumping at power-up:** up to 4.6 A, more than the adapter's 4 A. The code
  writes the home pose before `attach()`, so nothing jumps if the robot is powered up at home.
  If it was moved by hand, set it back to home before plugging in.

## 3. Supply path and rail voltage

| Element (EST) | Resistance |
|---|---:|
| 5 V 4 A adapter (≈ 5 % load regulation) | 0.06 Ω |
| 1.5 m cord, 2 × 20 AWG (33 mΩ/m each way) | 0.10 Ω (+ 1.5 µH) |
| DC jack contact | 0.01 Ω |
| Jumpers + breadboard contacts to the rail | 0.05 Ω |
| Servo leads (MG996R 0.08 Ω; others with 300 mm extensions 0.13 Ω) | per servo |
| **Total, adapter to rail** | **0.22 Ω** |

Hand calc: normal peak 0.65 A × 0.22 Ω = **0.14 V drop → rail ≈ 4.86 V**.
MG996R stall: 3.15 A × 0.22 Ω = **0.69 V drop → rail ≈ 4.31 V**.

ngspice, same circuit with the real waveforms (`out/spice_rail.png`):

| Case | Min rail | Min Uno 5V pin | Min at MG996R | Min at gripper |
|---|---:|---:|---:|---:|
| Normal run | 4.86 V | 4.86 V | 4.85 V | 4.82 V |
| MG996R stalled 0.5 s in TURN | 4.31 V | 4.31 V | 4.10 V | 4.27 V |

![Rail voltage](out/spice_rail.png)

- **Normal run: PASS.** The Uno stays above 4.5 V, the ATmega328P's minimum for 16 MHz.
- **Stall:** the Uno dips to 4.31 V. That's below its 16 MHz spec but far above the 2.7 V
  brown-out reset, so it keeps running. To raise it: a shorter or thicker adapter cord, or wire
  the MG996R's power straight to the jack so its current skips the breadboard.

**The 1000 µF capacitor** covers fast steps the adapter can't follow. A 1 A step for 100 µs
(EST adapter response) droops it by 1 A × 100 µs / 1000 µF = 0.10 V. It matters because the Uno
shares the rail. Rated ≥ 10 V, − leg to GND.

## 4. Small parts

| Part | Calculation | Result |
|---|---|---|
| Status LED on D13 | (5.0 V − 2.0 V Vf) / 220 Ω | **13.6 mA** (pin limit 20 mA recommended, 40 mA absolute) |
| START button on D4 | `INPUT_PULLUP` 20–50 kΩ to 5 V | 0.1–0.25 mA when pressed; debounced 40 ms in code |
| Servo signal pins D9, D10, D6, D5 | Servo signal input ≈ 10 kΩ (EST) | < 1 mA each |
| Total from Uno pins | 13.6 + 4 × 0.5 + 0.25 | ≈ 16 mA (ATmega328P total limit 200 mA) |

## 5. Rules that come out of these numbers

1. **Unplug the 5 V adapter before plugging in USB** to upload. Both feed the Uno's 5 V net.
2. Power up with the robot at home (no 4.6 A jump).
3. Calibrate `GRIP_CLOSED` for a light squeeze (0.5–1 N per arm); the gripper's holding current
   is the largest steady load.
4. Keep the adapter cord short and thick (≤ 1.5 m, 20 AWG or better).

## How the LTspice circuit is built

| Block | In the netlist |
|---|---|
| Adapter, cord, jack | `VADP` 5 V → `RADP` → `RCORD` + `LCORD` → `RJACK` |
| Breadboard rail | `RRAIL` → node `rail`; `CRAIL` 1000 µF + `RESR` 0.08 Ω |
| 4 servos | lead resistor + current source playing `pwl/i_*.txt` (the EST current model) |
| Stall test | `ISTALL` 2.5 A for 0.5 s in the middle of TURN (`STALL` = 1) |
| Uno | `RUNO` jumper → node `uno5v`, 45 mA load |
| Servo signals | `VSIG_D9 / D10 / D6 / D5` play `pwl/sig_D*.txt` (the exact pulse trains) through 25 Ω pins into ~10 kΩ servo inputs |
| LED | `VLED_D13` → 25 Ω → 220 Ω → LED model (Vf ≈ 2.0 V at 13.6 mA) |
| Button | 35 kΩ pull-up to `uno5v`, switch `SBTN` to GND, pressed at 1.0 s and 9.4 s |

Plot in LTspice: `V(rail)`, `V(uno5v)`, `V(d9)` `V(d10)` `V(d6)` `V(d5)` (zoom into any 20 ms to see
the four pulses in order), `V(d13)`, `V(d4)`.
