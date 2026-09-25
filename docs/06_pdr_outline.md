# PDR Slide Plan (10–15 min, due Oct 29)

A slide-by-slide plan with the figure for each slide. The figures in `sim/out/` are already
generated. Items marked ✋ need your hand sketches or SolidWorks renders.

| # | Slide | Content | Figure | Time |
|---|---|---|---|---|
| 1 | Title | Team, course, project | — | 0:15 |
| 2 | Objective and requirements | R1–R5, test sequence, can dimensions | Assignment Fig. 1–2 | 0:45 |
| 3 | What makes it hard | Empty 15 g can: slips if gripped too lightly, dents if too hard. Must land free-standing inverted. **Error budget: overshoot > +0.9° hits the table** | Error-budget table (`02_design_analysis.md` § 1) | 1:00 |
| 4 | Concept A: claw + wrist + turntable | Includes the lift-axis finding | ✋ sketch | 0:45 |
| 5 | Concept B: cradle + slide | | ✋ sketch | 0:30 |
| 6 | Concept C: multi-DOF arm | | ✋ sketch | 0:30 |
| 7 | Concept D: mirror flip | "One 180° turn about the 45° axis = flip + 90° move" | `flip_path_3d.png` + ✋ sketch | 1:00 |
| 8 | Decision matrix | Weights, scores, sensitivity check | Table from `01_concepts_and_decision_matrix.md` | 1:00 |
| 9 | Selected design: CAD | Assembly at 0°/90°/180°, key dimensions (axis height 2.39 in, arm 3.54 in, counterweight) | ✋ SolidWorks renders | 1:30 |
| 10 | Clearance and kinematics | Full-flip sweep, min clearance, axis-height tolerance | `flip_clearance.png` | 0:45 |
| 11 | Flip axis control | Plant TF, why pole placement (not Z-N), FF + PID, derivative-on-error finding | `flip_tracking.png`, `flip_step.png` | 1:30 |
| 12 | Grip force control | Slip/dent window, servo + FSR outer loop, why no grip encoder | `grip_step.png` | 1:00 |
| 13 | Electronics and firmware | Pin map, power architecture, state machine, fault handling | State diagram + pin table (`04_wiring_and_bom.md`) | 1:15 |
| 14 | Verification so far | Host test 11/11, AVR emulator run (1.49 ms/tick), robustness table | `simavr_sim_plant_run.png` | 0:45 |
| 15 | BOM, schedule, risks | ~$55 purchased. Risks: dent force, FSR drift, axis-height tolerance, motor lead time | BOM table | 1:00 |
| | | | **Total** | **≈ 13:30** |

## Motion clips for slides 4–8

`viewer/concepts.html` animates each concept. Screen-record each tab (macOS: Cmd+Shift+5;
Windows: Win+Alt+R or the Snipping Tool's video mode) and drop the clips onto slides 4–7. For
slide 4, record Concept A twice, with and without "remove the lift axis". The red table and the
"Can hits the table" banner make the lift-axis argument in about 5 seconds.

## Risks to state explicitly

1. **Motor parameters are estimates.** Mitigation: system-ID step (`'i'` serial command) on day 1
   of Phase 2, then rerun `flip_control.py` with the fitted K and τ.
2. **Dent force unknown.** Mitigation: crush test on scrap cans with the printed jaw before
   fixing the setpoint.
3. **FSR drift and hysteresis.** Mitigation: calibrate with known weights; grip settle uses a
   ±0.25 N band, not an exact value.
4. **Axis-height tolerance ±0.04 in.** Mitigation: slotted tower mount, caliper check.
