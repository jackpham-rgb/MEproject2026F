# Requirements Verification Traceability Matrix: Concept A (draft)

Method: **A** = analysis, **I** = inspection, **D** = demonstration, **T** = test (measured).
Update the Status column as evidence comes in. It feeds Part C item 4a.

## Assignment requirements

| ID | Requirement | Design feature | Method | Evidence | Status |
|---|---|---|---|---|---|
| R1 | Complete the test objective (TO1–TO3) | Turntable + lift + wrist flip + gripper, one move at a time | D, T | Part B demo; `tools/emulate_concept_a.sh` | Emulated ✔, hardware pending |
| R2 | Arduino Uno or similar | Arduino Uno R3 | I | BOM #1; 6.3 KB (19 %) flash | ✔ (build) |
| R3 | Operated by the microcontroller | The Uno runs the whole sequence from `concept_a.ino`. No laptop needed | I, D | Firmware | Design ✔ |
| R4 | Sized for a classroom tabletop | Base 6 × 6 in; reach 6.2 in; column 4.3 in; up to ~5.3 in with the can lifted | I | `cad/out/concept_a/` | Concept CAD ✔ |
| R5 | No direct human intervention | One start press; the rest is automatic. Faults freeze safely | D | Firmware | Emulated ✔ |

## Test objective

| ID | Requirement | Design feature | Method | Evidence | Status |
|---|---|---|---|---|---|
| TO1 | Start: can upright, free-standing, at the initial location | Gripper closes at START; optional IR check | D | Firmware (`USE_IR_SENSOR`) | Design ✔ |
| TO2a | Turn the can upside down | Wrist rolls 180° about the radial line through the can's centre | A, T | `sim/concept_a.py` § 1 | Analysis ✔ |
| TO2b | Move ~90° about the robot at ~5 in | Turntable 90°, can held at r = 5.0 in | A, T | Error budget: 2° → 0.17 in | Analysis ✔ |
| TO3 | Ends free-standing, inverted, at the target | Lowered back the same 0.6 in, so it's set down, not dropped | A, T | `02_design_analysis.md` § 1, § 6 | Analysis ✔, bench pending |

## Derived design requirements

| ID | Requirement | Rationale | Method | Evidence | Status |
|---|---|---|---|---|---|
| DR1 | Lift ≥ 0.6 in before the flip | The can corner dips 0.29 in below the table mid-flip | A | Clearance +0.31 in at 0.6 in lift | ✔ |
| DR2 | Wrist reaches 180° ± 3° | Tilt at release; tip-over at 24° | T | Servo range test | Pending |
| DR3 | Turntable 90° ± 2° | Landing within 0.17 in | T | Calibrate `TURN_TARGET` | Pending |
| DR4 | Grip ≥ 0.39 N per arm, below the dent force | Slip vs dent | A, T | `sim/concept_a.py` § 3; crush test | Analysis ✔, test pending |
| DR5 | Lift carriage slides without jamming (2μe/L < 1) | Drawer effect | A, T | LM6UU: 0.04; printed: 1.10 (rejected) | Analysis ✔ |
| DR6 | Servo supply ≥ 5 A, separate from the Uno 5 V | Stall current up to 4.6 A | A, I | `04_wiring_and_bom.md` | Design ✔ |
| DR7 | Moves eased (zero speed and accel at both ends) | Don't shake the 15 g can loose | A, T | `concept_a_sequence.png`; emulator log | ✔ |
| DR8 | Home only after the can is removed | The open arms straddle the can | D | Firmware DONE → button → HOMING | Design ✔ |
