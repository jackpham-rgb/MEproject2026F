# Design Concepts and Decision Matrix (PDR Part A, items 1–2)

**Layout used by every concept (assignment Fig. 2).** The robot origin is the corner. The can starts
upright at 5 in along +Y and must end inverted at 5 in along +X, 90° away.

---

## Concept A: Claw + wrist flip + turntable *(original "selected direction")*

A claw on a wrist joint sits on an arm, and the arm sits on a turntable. The sequence is grip,
flip 180° at the wrist, rotate the turntable 90°, then release.

**The hidden "somehow": a lift axis.** A can gripped at mid-height has its corners 2.64 in from
the grip point (√(1.2² + 2.35²)). That is 0.29 in more than the 2.35 in to the table. So the can
cannot flip in place. Its bottom rim hits the table partway through. Gripping off-centre doesn't
help. The far corner still passes below the table, and the can ends up hovering after the flip,
then drops. So Concept A needs a **fourth actuator: lift ~0.5 in before the flip and lower after**.
It also has to set the can down under control. That makes 4 actuators, and 3 of them are in series.

## Concept B: Cradle flip + drag

A tall U-cradle on a turntable arm clamps the can along its full height. It lifts slightly, flips
the can 180° in place, and sets it down inverted at START. Then the turntable **drags** it 90°
along the table to TARGET, sliding on its rim, and releases.

Why not "tip twice": tipping the can 90° about its bottom edge, then 90° about the new bottom
edge, moves it about 4.7 + 2.4 in sideways, past the robot rather than to TARGET. So the flip has
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

## Concept D: Mirror flip, one diagonal axis *(recommended)*

One horizontal revolute axis runs along the **45° bisector** through the robot origin. It sits at
**can mid-height (2.35 in + 0.04 in)**. A gripper on a 3.54 in arm grips the can. Then **one 180°
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

## Decision matrix

Scores are 1 (poor) to 5 (best) and weights sum to 1.0. The scores are engineering judgement
backed by the analyses referenced. **Revise them as a team before the PDR** — the matrix should be yours.

| Criterion | Weight | A: Claw+wrist+turntable | B: Cradle+slide | C: Pincer arm | D: Mirror flip |
|---|---:|:-:|:-:|:-:|:-:|
| Reliability of an inverted, free-standing landing | 0.30 | 3 | 2 | 3 | **5** |
| Actuator / part count (fewer = better) | 0.15 | 2 (4 act.) | 2 (4 act.) | 1 (5 act.) | **5** (2 act.) |
| Tolerance to can placement error | 0.15 | 4 | 2 | 4 | 4 |
| Control + code complexity (lower = better) | 0.10 | 2 | 3 | 1 | **4** |
| Torque / actuator demand (lower = better) | 0.10 | **4** | 3 | 2 | 3 |
| Build time + cost | 0.10 | 2 | 3 | 2 | **4** |
| Shows the closed-loop control objective | 0.10 | 4 | 2 | 4 | 4 |
| **Weighted total** | **1.00** | **3.00** | **2.30** | **2.55** | **4.35** |

**Sensitivity check.** With all seven criteria weighted equally, the totals are A 3.00, B 2.43,
C 2.43, D 4.14. With landing reliability cut from 0.30 to 0.15 and the difference spread evenly
over the others, the totals are A 3.00, B 2.38, C 2.45, D 4.20, and D still leads by 1.2. So the ranking holds across reasonable weightings.

**Selected: Concept D.** It keeps both closed-loop axes from the original plan (grip force, flip
angle), where they matter most. It drops the turntable. The ~90° move needed no closed loop anyway,
and here it comes free from the geometry.

## What still needs doing by hand

- [ ] Hand-sketch each of the 4 concepts for the slides. Take the geometry above as the brief.
- [ ] Team review of the weights and scores.
