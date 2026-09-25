# Requirements Verification Traceability Matrix (draft)

Method: **A** = analysis, **I** = inspection, **D** = demonstration, **T** = test (measured).
The Status column is updated as evidence comes in. It feeds Part C item 4a.

## Assignment requirements

| ID | Requirement | Design feature | Method | Evidence | Status |
|---|---|---|---|---|---|
| R1 | Complete the test objective (TO1–TO3) | Mirror-flip mechanism + closed-loop flip and grip | D, T | Part B demo; `firmware/host_test`; `tools/emulate_uno.sh` | Simulated ✔, hardware pending |
| R2 | Arduino Uno or similar | Arduino Uno R3 (ATmega328P) | I | BOM #1; 36.6 % flash / 21.4 % RAM | ✔ (build) |
| R3 | Operated by the microcontroller | Uno runs the state machine and both control loops standalone. The laptop only logs | I, D | `firmware/can_flipper/sequencer.h` | Design ✔ |
| R4 | Sized for a classroom tabletop | Robot + swept envelope ~7 × 7 in in plan; max swept height 7.7 in (farthest can point is 5.29 in from the axis) | I | CAD envelope | Pending CAD |
| R5 | No direct human intervention | One start press. DETECT → DONE runs with no further input; FAULT stops safely | D | State machine; fault tests | Simulated ✔ |

## Test objective

| ID | Requirement | Design feature | Method | Evidence | Status |
|---|---|---|---|---|---|
| TO1 | Start: can upright, free-standing, at the initial location | Ultrasonic DETECT (5 consecutive hits) before any motion | T | Fault test "no can" → F_NO_CAN | Simulated ✔ |
| TO2a | Turn the can upside down | 180° rotation about a horizontal axis | A | `sim/flip_geometry.py`: inverted = True | ✔ (analysis) |
| TO2b | Move ~90° about the robot at ~5 in radius | Axis on the 45° bisector, so the mirror image of START is TARGET | A | Landing centre (5.000, 0.000) in | ✔ (analysis) |
| TO3 | Ends free-standing, inverted, at the target | θ_end = 179.5° with no overshoot, 2 mm hover, jaws open symmetrically | A, T | Error budget § 1; sim peak ≤ 179.8° | Simulated ✔ |

## Derived design requirements

| ID | Requirement | Rationale | Method | Evidence | Status |
|---|---|---|---|---|---|
| DR1 | Final flip angle 179.5° (−2.5 / +1.4°), overshoot never past 180.9° | Rim hits the table at +1°. Tip-over at 24° | A, T | `flip_control.py`; host test checks it | Sim ✔, bench pending |
| DR2 | Grip force 1.5 ± 0.25 N per finger, never > 4 N | Slip at 0.44 N, dent ~8 N **EST** | A, T | `grip_control.py`; can crush test | Sim ✔, dent test pending |
| DR3 | Flip axis height 2.39 +0.05/−0.02 in | Hover gap ≥ 0 and drop ≤ 0.2 in | A, I | Geometry sensitivity table; caliper check | Pending build |
| DR4 | No part of the robot below the can path mid-flip | Collision | A | Clearance +0.06 in (can), +0.34 in (counterweight body) | ✔ (analysis) |
| DR5 | Control loop 200 Hz with no missed ticks | Discrete design assumes a fixed dt | T | simavr: 1.49 ms worst case, 0 overruns | ✔ (emulated) |
| DR6 | Any fault leaves the motor off and the jaws open | Safety; the can isn't crushed | T | Host fault-injection tests | Sim ✔ |
| DR7 | Encoder zero re-established every cycle | Incremental encoder drift | D | Home stop + switch, HOME/SEAT states | Design ✔ |
