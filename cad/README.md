# Concept CAD (STEP / STL)

## Concept A (selected)

Regenerate: `python3 cad/build_cad_concept_a.py` (needs `pip install cadquery`). Units are
**millimetres**. The origin is the turntable axis on the table, +Y points to START and +X to
TARGET. The robot is in its home pose: arm at START, lift down, wrist upright, arms open.

`out/concept_a/concept_a_assembly.step` has one group per moving stage:
- `fixed`: base_box, lazy_susan_ring, turntable_servo_MG996R
- `turret`: turntable_plate, column, guide_rod_L/R, lift_servo_MG90S
- `lift`: carriage, arm, wrist_servo
- `wrist`: wrist_hub, palm, gripper_servo, arm_L, arm_R

Plus `test_can`, standing at START.

### Animate it in Fusion 360

1. **File → Open → Open from my computer →** `concept_a_assembly.step`.
2. Right-click `fixed` → **Ground**.
3. **Assemble → Joint**, and add three joints:
   - **Turntable:** `turret` to `fixed`, **Revolute**. Snap to the turntable plate's circular edge,
     so the axis is the Z axis through the origin. Limits: 0° to −90°.
   - **Lift:** `lift` to `turret`, **Slider** along Z. Limits: 0 to 15.2 mm (0.6 in).
   - **Wrist:** `wrist` to `lift`, **Revolute**. Snap to the wrist hub's circular edge, so the
     axis is the radial line at 59.7 mm height. Limits: 0° to 180°.
4. Drag the can into `wrist` (or give it a Rigid joint to `palm`) so it moves with the gripper.
5. **Assemble → Motion Study**: lift 0 → 15.2 mm, wrist 0 → 180°, turntable 0 → −90°, lift
   back to 0. Press Play.
6. **Inspect → Interference** at wrist 27° and 153°. With the lift up, the can clears the table.
   With the lift down, it doesn't: that's the reason for the lift.

SolidWorks works the same way: fix `fixed`, add Concentric + Coincident mates for each joint,
then **Motion Study → Motor** on each one.

---

## Concept D (alternative)

Regenerate: `python3 sim/mechanism.py && python3 cad/build_cad.py` (needs `pip install cadquery`).
Units are **millimetres**. The origin is the robot corner on the table, +Y points to START and
+X points to TARGET.

`out/can_flipper_assembly.step` has two groups:
- `fixed`: base_plate, tower, gearmotor, home_post
- `flip_arm`: hub, arm, palm, servo, ir_sensor, jaw_L/R, cw_arm, counterweight, stop_tab

Plus `test_can`, standing at START.

These are block-level concept solids: correct envelopes, placement and motion. They are meant
as a layout skeleton for the detail design in SolidWorks or Fusion.

### Animate the flip in Fusion 360 (about 5 minutes)

1. **File → Open → Open from my computer →** `can_flipper_assembly.step`. Fusion turns the
   groups into components.
2. Right-click `fixed` → **Ground**.
3. **Assemble → As-built Joint**. Components: `flip_arm` and `fixed`. Type: **Revolute**.
   Position: pick the circular edge at the hub's end face. The joint axis snaps to the hub centre,
   which is the flip axis: through (0, 0, 60.7 mm), along the 45° diagonal.
4. Right-click the joint → **Edit Joint Limits** → Rotation: min 0°, max 180°.
5. **Assemble → Motion Study**. Add the joint, set 0° at step 0 and 180° at step 60, and press
   Play. The arm swings the gripper up and over to TARGET.
6. To check for collisions: **Inspect → Interference**, or turn on **Contact Sets** and drag
   the joint.

The can is a separate component. To make it ride with the arm in the motion study, drag it into
`flip_arm`, or give it a Rigid joint to `palm`.

SolidWorks works the same way: open the STEP, fix `fixed`, add a Concentric mate on the hub, then
**Motion Study → Motor** (rotary, 180°).
