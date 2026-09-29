# PDR Slide Plan: Concept A (10–15 min, due Oct 29)

✋ = needs your sketches or SolidWorks renders. GIFs are in `viewer/gifs/`, plots in `sim/out/`.

| # | Slide | Content | Visual | Time |
|---|---|---|---|---|
| 1 | Title | Team, course, project | — | 0:15 |
| 2 | Objective and requirements | R1–R5, test sequence, can dimensions | Assignment Fig. 1–2 | 0:45 |
| 3 | What makes it hard | 15 g empty can: slips or dents; must land free-standing inverted | Photo of a can | 0:30 |
| 4 | **Concept A introduced** | Claw + wrist flip + turntable; the robot visibly turns 90° at 5 in | `conceptA_claw_turntable.gif` | 1:00 |
| 5 | Why A needs a lift | The corner dips 0.29 in into the table; lift 0.6 in gives +0.31 in | `conceptA_claw_turntable_no_lift_hits_table.gif` + `concept_a_clearance.png` | 1:00 |
| 6 | Concept B | Cradle flip + drag: movement more complicated, drag on the rim | `conceptB_cradle_drag.gif` | 0:30 |
| 7 | Concept D | Mirror flip: 2 motors, meets the spec technically, but the robot never turns 90° (the "lazy" option) | `conceptD_mirror_flip.gif` | 0:45 |
| 8 | Concept C | Pincer arm: most beautiful, hardest (5–6 servos, stacked backlash) | `conceptC_pincer_arm.gif` | 0:30 |
| 9 | **Concept A compared** | Decision matrix + how it's calculated (A 3.85, B 3.30, D 3.00, C 2.75); honest downside: 4 servos = more failure points | Matrix table | 1:30 |
| 10 | Selected design: CAD | Base, lazy-susan, column, lift carriage, arm, wrist, gripper | ✋ renders (start from `cad/out/concept_a/`) | 1:30 |
| 11 | Motion sequence | Grip → lift → flip → turn → lower → release, 6.4 s, eased moves | `concept_a_sequence.png` | 1:00 |
| 12 | Engineering checks | Grip 0.39 N minimum; servo loads with big margins; lift jam check (printed 1.10 → LM6UU 0.04) | Numbers from `sim/out/concept_a.txt` | 1:30 |
| 13 | Electronics and code | Pin map, separate 5 A servo supply, one-file sketch, Tinkercad / Wokwi sims | Wiring table + Tinkercad screenshot ✋ | 1:00 |
| 14 | BOM, schedule, risks | ≈ $50–65; risks: wrist 180° range, lift binding, calibration, can can't be left mid-return | BOM | 1:00 |
| | | | **Total** | **≈ 13:15** |

## Risks to state

1. **Wrist servo range.** Many micro servos stop around 170°. Mitigation: test on arrival; 270°
   servo as backup (`WRIST_RANGE 270`).
2. **Lift binding.** Mitigation: LM6UU bushings, ≥ 1.6 in spacing (jam ratio 0.04).
3. **4 servos in series.** Mitigation: each move is tested on its own; angles are constants at the
   top of the code.
4. **Return with the can present.** Mitigation: home only after removal, or a wide-opening claw.
5. **Stretch goal:** a 2:1 bevel gear couples the flip to the turntable (one servo fewer).
