# Design Concepts and Decision Matrix (PDR Part A, items 1–2)

**Layout used by every concept (assignment Fig. 2).** The robot origin is the corner. The can starts
upright at 5 in along +Y and must end inverted at 5 in along +X, 90° away.

---

## Concept A: Claw + wrist flip + turntable *(selected)*

A claw on a wrist joint sits on an arm, and the arm sits on a turntable. The sequence is grip,
flip 180° at the wrist, rotate the turntable 90°, then release.

**The hidden "somehow": a lift axis.** A can gripped at mid-height has its corners 2.74 in from
the grip point (√(1.30² + 2.41²), Coke can 2.61 × 4.81 in). That is 0.33 in more than the 2.41 in to the table. So the can
cannot flip in place. Its bottom rim hits the table partway through. Gripping off-centre doesn't
help. The far corner still passes below the table, and the can ends up hovering after the flip,
then drops. So Concept A needs a **fourth actuator: lift ~0.5 in before the flip and lower after**.
It also has to set the can down under control. That makes 4 actuators, and 3 of them are in series.

**Resolved in the selected design:** a 0.6 in lift on LM6UU bushings gives +0.27 in of clearance.
Flipping about the can's own centre means lowering the same 0.6 in sets it down exactly on the
table. Full analysis: `02_design_analysis.md`.

## Concept B: Cradle flip + drag

A tall U-cradle on a turntable arm clamps the can along its full height. It lifts slightly, flips
the can 180° in place, and sets it down inverted at START. Then the turntable **drags** it 90°
along the table to TARGET, sliding on its rim, and releases.

Why not "tip twice": tipping the can 90° about its bottom edge, then 90° about the new bottom
edge, moves it about 4.8 + 2.6 in sideways, past the robot rather than to TARGET. So the flip has
to happen in place, which needs the same lift axis as Concept A.

It needs 4 actuators (clamp, lift, flip, turntable). Dragging an inverted 15 g can on its thin rim
is the least repeatable step of all four concepts: friction varies and the can wobbles. The
cradle also has to open without pulling the can over.

## Concept C: Multi-DOF pincer arm

This is a SCARA or articulated arm: base yaw, shoulder, wrist roll and pincer. It lifts the can,
swings it 90°, rolls it 180° and sets it down.

It is the most general option: 4–5 servos, inverse kinematics, and stacked servo backlash at the
end effector. Servo torques add up quickly at a 5 in reach. It is also the most code for the
least certainty.

## Concept D: Mirror flip, one diagonal axis *(alternative, not selected; its full design is in the git history)*

One horizontal revolute axis runs along the **45° bisector** through the robot origin. It sits at
**can mid-height (2.41 in + 0.04 in)**. A gripper on a 3.54 in arm grips the can. Then **one 180°
rotation about that axis moves the can from START to TARGET and inverts it at the same time**.
A 180° turn about a horizontal line is a mirror across that line in plan view, plus z → 2h − z.
So the 90° relocation and the flip are the same motion. See `sim/out/flip_path_3d.png`.

Properties, all checked in `sim/flip_geometry.py`:

- **2 actuators total**: flip gearmotor + grip servo. No turntable and no lift.
- **The can arrives moving straight down.** At 180° the can centre's velocity is vertical. With a
  minimum-jerk profile it reaches zero speed 2 mm (0.08 in) above the table, and then the jaws open.
- **Landing position is set by geometry, not by tuning.** 90° and 5 in are exact by symmetry. The
  V-jaws re-centre the can in the gripper, so start-placement error along the jaw direction
  doesn't carry over to the target.
- **Nothing hits the table mid-flip.** Minimum can clearance is +0.06 in. The counterweight clears
  as long as its radius stays below the axis height.
- **The closed-loop flip is actually needed here:** the error budget is lopsided. Overshoot past
  +0.9° pushes the rim into the table. Undershoot up to −3° only tilts the can by 3°, and it tips
  at 24°. So the target is 179.5° with no overshoot. An open-loop servo sweep has no way to
  guarantee that under load.

Weaknesses: the whole arm swings, so torque is higher than a wrist flip. It is only 18 mN·m after
counterweighting, but the counterweight adds ~100 g. The can passes over the robot, so the base
has to stay low near the axis. Axis height is a build-critical dimension, ±0.04 in.

---

## Decision matrix (team, final)

Ranking: **A → B → D → C.** Scores are 1 (bad) to 5 (good). Each weight is how much that
criterion matters to the team, and the weights sum to 1.00.

| Criterion | Weight | A | B | D | C |
|---|---:|:-:|:-:|:-:|:-:|
| Clearly meets "90° around the robot" | 0.25 | 5 | 5 | 2 | 4 |
| Lands upright and upside down reliably | 0.20 | 4 | 2 | 4 | 4 |
| Few failure points (fewer motors) | 0.15 | 2 (4 servos) | 2 (4) | 5 (2) | 1 (5) |
| Simple parts and electronics | 0.15 | 4 (servos only) | 4 | 2 (motor + encoder + driver) | 3 |
| Simple movement and code | 0.15 | 4 (one move at a time) | 3 | 3 (closed-loop PID) | 1 |
| Easy to build (tolerances) | 0.10 | 3 | 3 | 2 (±0.04 in axis) | 2 |
| **Total** | **1.00** | **3.85** | **3.30** | **3.00** | **2.75** |

**Calculation:** total = Σ (score × weight). For A: 5×0.25 + 4×0.20 + 2×0.15 + 4×0.15 + 4×0.15
+ 3×0.10 = 1.25 + 0.80 + 0.30 + 0.60 + 0.60 + 0.30 = **3.85**. With all criteria weighted equally
(the plain average), the order stays A 3.67, B 3.17, D 3.00, C 2.50.

**Selected: Concept A.**
- It's the one people expect: the robot visibly turns 90° at 5 in.
- It uses only hobby servos, with no encoder, motor driver or closed-loop tuning.
- Every move is simple and can be tested on its own.
- The price is more failure points (4 servos in series) and a lift that must slide freely. Both
  are handled in `02_design_analysis.md`.

### Binary matrix (yes = 1, no = 0)

Every score is a plain yes/no with the number behind it. Totals and ranks are formulas in
`docs/decision_matrix_and_bom.xlsx` (sheet *Concepts*); also `docs/decision_matrix_concepts.csv`.

| # | Criterion | A | B | C | D |
|---|---|:-:|:-:|:-:|:-:|
| 1 | Robot visibly turns 90° about its own location | 1 | 1 | 1 | 0 |
| 2 | Can is held for the whole move (never slid or dropped) | 1 | 0 | 1 | 1 |
| 3 | Landing spot set by geometry, not fine tuning | 1 | 0 | 0 | 1 |
| 4 | 3 or fewer actuators (fewer failure points) | 0 | 0 | 0 | 1 |
| 5 | Hobby servos only (no encoder, motor driver or PID) | 1 | 1 | 1 | 0 |
| 6 | One move at a time, each testable on its own | 1 | 1 | 0 | 1 |
| 7 | No build-critical dimension tighter than ±1 mm | 1 | 1 | 0 | 0 |
| 8 | Servo torque margin ≥ 3× | 1 | 1 | 0 | 1 |
| 9 | Can path stays clear of the robot body | 1 | 1 | 1 | 0 |
| 10 | No separate lift axis needed | 0 | 0 | 1 | 1 |
| | **Total** | **8** | **6** | **5** | **6** |

B and D tie on 6. The tie goes to B because it meets criterion 1 (the spec's visible 90°
turn), giving **A → B → D → C**, the same order as the weighted team matrix. The reasons for
each score are in the spreadsheet's *Why* columns, e.g. A loses only on actuator count (4) and
on needing a lift (the can digs 0.33 in into the table without it).

### First-pass engineering matrix (superseded)

The first scoring weighted landing reliability and actuator count most, and it favoured D.
It's kept for the record. The team matrix above replaces it, because it adds the criteria that
matter for the demo and presentation: an obviously-met 90° turn and simple servo-only
electronics.

| Criterion | Weight | A | B | C | D |
|---|---:|:-:|:-:|:-:|:-:|
| Reliability of an inverted, free-standing landing | 0.30 | 3 | 2 | 3 | 5 |
| Actuator / part count | 0.15 | 2 | 2 | 1 | 5 |
| Tolerance to can placement error | 0.15 | 4 | 2 | 4 | 4 |
| Control + code complexity | 0.10 | 2 | 3 | 1 | 4 |
| Torque / actuator demand | 0.10 | 4 | 3 | 2 | 3 |
| Build time + cost | 0.10 | 2 | 3 | 2 | 4 |
| Shows the closed-loop control objective | 0.10 | 4 | 2 | 4 | 4 |
| **Weighted total** | | 3.00 | 2.30 | 2.55 | 4.35 |

## What still needs doing by hand

- [ ] Hand-sketch each of the 4 concepts for the slides. Take the geometry above as the brief.
- [ ] Team review of the weights and scores.
