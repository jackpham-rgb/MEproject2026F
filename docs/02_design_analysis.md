# Design Analysis: Concept A (Claw + Wrist Flip + Turntable)

Numbers come from `sim/concept_a.py`, which reads the servo angles and move times straight out of
`firmware/concept_a/concept_a.ino`. Output: `sim/out/concept_a.txt`, `concept_a_clearance.png`,
`concept_a_sequence.png`. Values marked **EST** get replaced with CAD mass properties and
bench measurements.

## 1. How it meets the requirement

- **Robot location = the turntable axis**, at the vertex of the assignment's Figure 2. START is
  5 in along +Y and TARGET is 5 in along +X.
- **90° relocation:** the turntable turns the whole arm 90°. The can stays 5.0 in from the axis the
  whole time. This is the plain reading of "90° from the initial location, relative to the robot,
  at ~5 in". The robot visibly turns 90°, so no one has to take the geometry on trust.
- **Inversion:** the wrist rolls the gripper 180° about the radial line (robot → can) through the
  can's centre.
- **Free-standing at the target:** the flip is about the can's own centre, so after lowering the
  can occupies the same heights it started at. It is set down, not dropped.

## 2. Why it needs a lift (`concept_a_clearance.png`)

The can is gripped at mid-height, 2.35 in above the table. Its bottom corner is
√(1.2² + 2.35²) = **2.64 in** from the grip point, so it swings **0.29 in into the table** during the
flip. The worst point is 27° into the roll, and again at 153°.

| Lift | Lowest point of the can during the flip |
|---|---|
| 0 | −0.29 in (hits the table) |
| 0.3 in | +0.01 in (too close) |
| **0.6 in (design)** | **+0.31 in** |

## 3. Motion profile (`concept_a_sequence.png`)

The robot does one move at a time: grip → lift → flip → turn → lower → release, **6.4 s** in all.
Every move follows a minimum-jerk (slow–fast–slow) curve, so speed and acceleration are zero at
both ends.

| Move | Angle | Time | Peak speed | Load on the can |
|---|---|---|---|---|
| Turntable | 90° | 1.5 s | 112°/s (can at 249 mm/s) | 0.51 m/s² tangential, 0.49 m/s² centripetal |
| Wrist | 180° | 1.5 s | 225°/s | ≈ 0: the can's centre is on the roll axis |
| Lift | 0.6 in | 1.0 s each way | | small |

## 4. Grip

- **Worst load on the pads:** g plus the turn acceleration = 10.5 m/s². During the turn the can
  hangs upside down in the arms.
- **Minimum squeeze per arm:** SF·m·a / (2μ) = 3 × 0.015 × 10.5 / (2 × 0.6) = **0.39 N**.
- **Dent onset:** about 8 N per arm (**EST**).
- **Setting:** `GRIP_CLOSED` is set just past pad contact, so the soft pads squeeze about 1–2 N.
  That's well inside the 0.4–8 N window.
- **Why a fixed angle:** a hobby servo can't report when it has stopped, so the code goes to a
  fixed angle. The FSR option (`USE_FSR 1`) stops early at a measured force instead.

## 5. Servo sizing (torques in kg·cm; stall ratings at 5 V)

| Joint | Load | Needed | Servo (rating) | Margin |
|---|---|---|---|---|
| Turntable | inertia 8.2 kg·cm², α = 4.0 rad/s² | 0.03 | MG996R (9.4) | large. The lazy-susan carries the weight, and the big servo is there for stiffness, not torque |
| Lift, LM6UU bushings | 112 g moving, CG 2.9 in out from the column | 0.10 | MG90S (1.8) | ~18× |
| Wrist | gripper + can ≈ 47 g, CG ~0.25 in off the axis (**EST**) | 0.03 | micro servo (1.8) | large |
| Gripper | pad squeeze 1–2 N | — | SG90 (1.6) | fine |

### Lift carriage: the jamming check (the drawer effect)

- The arm sticks out 2.9 in from the column. That tilts the carriage on its guide rods and presses
  the bushings against them, the same way a drawer sticks when you pull it by one corner.
- The carriage slides freely only if **2·μ·e / L < 1**. Here e = 2.9 in (CG offset) and
  L = 1.6 in (bushing spacing).
  - Printed PLA slide, μ ≈ 0.3: ratio **1.10, so it jams**.
  - LM6UU linear bearings, μ ≈ 0.01: ratio **0.04, fine**.
- **Design rule: use LM6UU bushings on 6 mm steel rods**, spaced ≥ 1.6 in apart vertically.
  For a printed slide, the spacing would have to exceed 2μe = 1.8 in, with no margin.

## 6. Error budget

| Error | Effect | Tolerance |
|---|---|---|
| Turntable 1° / 2° / 3° off | Can lands 0.09 / 0.17 / 0.26 in from the target | Spec says "approximately", so ±2° is fine. Calibrate `TURN_TARGET` |
| Wrist short of 180° by d° | Can tilted d° at release | Tip-over at 24°, so a few degrees is harmless. **Check the servo really reaches 180°**, or use a 270° servo (`WRIST_RANGE 270`) |
| `LIFT_DOWN` too high by h | Can drops h | Calibrate on a real can |
| `LIFT_DOWN` too low | Pads slide on the can as it's pushed down | Calibrate on a real can |
| Can placed off-centre at START | V-arms re-centre it sideways; a radial error carries straight over to TARGET | Place within ~0.25 in |

## 7. Base and power

- **Keep-out:** the base must stay **within 3.55 in** of the axis toward START and TARGET (can
  footprint + 0.25 in). It can extend behind the corner freely.
- **Tip-over:** the outboard moment is only 0.019 N·m. Add washers and rubber feet anyway, so the
  reaction from the turntable doesn't slide the base.
- **Servo current:**
  - Stall: MG996R 2.5 A, MG90S 0.7 A, micro 0.7 A, SG90 0.65 A. If all four stall at once
    that's up to 4.6 A.
  - The moves run one at a time, so normal draw is < 1.5 A.
- **Supply:** 5–6 V, **≥ 5 A**, with a 1000 µF capacitor, separate from the Uno's 5 V. The grounds
  are joined.

## 8. Firmware (`firmware/concept_a/concept_a.ino`)

- **Built for simple tools:** it's a single file that uses only the built-in Servo library, so it
  pastes into the Arduino IDE, Tinkercad or Wokwi unchanged.
- **Sequence as data:** the run is a table of steps. Each row holds the target pose for all 4
  servos plus a move time, and the code blends from the current pose to the next.
- **Tunable angles:** all servo angles are named constants at the top of the file (`TURN_START`,
  `LIFT_UP`, `GRIP_CLOSED`…). Calibration never touches the logic.
- **Optional sensors:** the IR can check (`USE_IR_SENSOR`) and the FSR grip / slip check
  (`USE_FSR`). On a slip it **freezes instead of opening**, so the can isn't dropped in mid-air.
- **Homing only after the can is removed:** after release, the open arms are still on both sides
  of the can. Turning back would knock it over.
- **Tested:** it compiles for the Uno at 6.3 KB (19 % flash). On an emulated ATmega328P it runs
  the full sequence and the logged angles ease in and out (`tools/emulate_concept_a.sh`).

## 9. Known weaknesses and next steps

1. **Most failure points of the shortlisted concepts:** 4 servos in series. Each one is calibrated
   separately.
2. **Lift binding:** solved by LM6UU bushings (§ 5). Check for binding on the first build.
3. **Wrist range:** many micro servos stop around 170°. Test before designing the wrist mount.
4. **The robot can't back away with the can still there.** Option: arms that pivot open ≥ 80°
   (a wide claw), so the turntable can turn back without touching the can.
5. **Future option, mechanical coupling:** a fixed 40-tooth bevel ring on the base and a 20-tooth
   pinion on the wrist shaft flip the wrist 180° as the turntable turns 90°. That removes the wrist
   servo. Mount the ring at the lifted height, so the pinion only meshes while the arm is up.
   A spring detent holds 0° and 180° when disengaged. It's a stretch goal only after the servo
   version works.
