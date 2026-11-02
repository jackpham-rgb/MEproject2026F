# Requirements Verification Traceability Matrix: Concept A

Method: **A** = analysis, **I** = inspection, **D** = demonstration, **T** = test (measured).
Status as of the detail design (before hardware). Update the Status column as test evidence comes in. It feeds Part C item 4a.

## Assignment requirements

| ID | Requirement | Design feature | Method | Evidence | Status |
|---|---|---|---|---|---|
| R1 | Complete the test objective (TO1–TO3) | Turntable + lift + wrist flip + gripper, one move at a time | D, T | Part B demo; `tools/emulate_concept_a.sh` | Emulated ✔, hardware pending |
| R2 | Arduino Uno or similar | Arduino Uno R3 | I | BOM CA-P01; 6.4 KB (19.6 %) flash, 24.5 % RAM | ✔ (build) |
| R3 | Operated by the microcontroller | The Uno runs the whole sequence from `concept_a.ino`. No laptop needed | I, D | Firmware | Design ✔ |
| R4 | Sized for a classroom tabletop | 167 × 331 mm footprint incl. the electronics tray and the can (6.6 × 13 in), 168 mm (6.6 in) tall, 571 g | I | Drawing CA-000; `cad/out/concept_a_detail_assembly.step` | Detail CAD ✔ |
| R5 | No direct human intervention | One START press; the rest is automatic | D | Firmware; `tools/emulate_concept_a.sh` | Emulated ✔ |

## Test objective

| ID | Requirement | Design feature | Method | Evidence | Status |
|---|---|---|---|---|---|
| TO1 | Start: can upright, free-standing, at the initial location | Can placed against the bumper; gripper closes at START | D | Firmware `GRIP` step, `cad/out/check_report.txt` | Design ✔ |
| TO2a | Turn the can upside down | Wrist rolls 180° about the radial line through the can's centre | A, T | `sim/concept_a.py` § 1 | Analysis ✔ |
| TO2b | Move ~90° about the robot at ~5 in | Turntable 90°, can held at r = 127 mm (5.0 in) | A, T | CAD check: can lands at (127.0, 0.0) mm; error budget 2° → 0.17 in | CAD ✔ |
| TO3 | Ends free-standing, inverted, at the target | Lowered back the same 0.6 in, so it's set down, not dropped | A, T | CAD check: inverted, 0.0° tilt, bottom at z = 0.00 mm; `02_design_analysis.md` § 1, § 6 | CAD ✔, bench pending |

## Derived design requirements

| ID | Requirement | Rationale | Method | Evidence | Status |
|---|---|---|---|---|---|
| DR1 | Lift ≥ 0.6 in before the flip | The can corner dips 0.33 in below the table mid-flip | A | Clearance +0.27 in at 0.6 in lift | ✔ |
| DR2 | Wrist reaches 180° ± 3° | Tilt at release; tip-over at 24° | T | Servo range test | Pending |
| DR3 | Turntable 90° ± 2° | Landing within 0.17 in | T | Calibrate `TURN_TARGET` | Pending |
| DR4 | Grip ≥ 0.39 N per arm, below the dent force | Slip vs dent | A, T | `sim/concept_a.py` § 3; crush test | Analysis ✔, test pending |
| DR5 | Lift carriage slides without jamming (2μe/L < 1) | Drawer effect | A, T | CAD masses: LM6UU 0.018; printed slide 0.55 (rejected) | Analysis ✔ |
| DR6 | Servo supply stays in the 4.8–6.0 V rating, Uno ≥ 4.5 V, in a normal run and a servo stall | Stall 2.5 A; the Uno must not misbehave | A (SPICE), T | `EE/README.md`: servos ≥ 5.50 V, Uno 5.00 V (12 V + buck 5.8 V) | Simulated ✔, bench pending |
| DR7 | Moves eased (zero speed and accel at both ends) | Don't shake the 15 g can loose | A, T | `concept_a_sequence.png`; emulator log | ✔ |
| DR8 | Home only after the can is removed | The open arms straddle the can | D | Firmware DONE → button → HOMING | Design ✔ |
| DR9 | No part collides with another or the table in any pose of the run and homing | 4 joints moving near each other and the can | A | `cad/check.py`: 289 poses, solid booleans → no collisions | CAD ✔ |
| DR10 | Robot doesn't tip over | Arm + can reach 5 in out | A | CG stays ≥ 39 mm inside the footprint in every pose | CAD ✔ |
| DR11 | Printed fits work in PETG (screws, rods, bearings) | No nuts; press fits | T | Tolerance coupon CA-900 | Pending (print first) |
| DR12 | Power-up away from home stays within the adapter rating | All 4 servos jumping = 4.7 A | A (SPICE), D | Servos attached 0.3 s apart → 1.54 A of 2 A | Simulated ✔ |
| DR13 | Gripper holds without stalling the SG90 | Squeeze 0.5–1 N per arm; SG90 max 1.8 N per arm at the 44 mm lever | A, T | `EE/README.md` § 2: 0.72 kg·cm = 45 % of stall | Analysis ✔, bench pending |

## What's left before the demo

Everything marked *pending* needs the hardware: the servo range test (DR2), turntable calibration
(DR3), crush and grip tests (DR4, DR13), the tolerance coupon (DR11), rail voltages measured with
a meter (DR6), and the full run on the table (R1, TO1–TO3).
