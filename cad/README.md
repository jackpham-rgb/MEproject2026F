# Concept CAD (STEP / STL)

Regenerate: `python3 sim/mechanism.py && python3 cad/build_cad.py` (needs `pip install cadquery`).
Units are **millimetres**. The origin is the robot corner on the table, +Y points to START and
+X points to TARGET.

`out/can_flipper_assembly.step` has two groups:
- `fixed`: base_plate, tower, gearmotor, home_post
- `flip_arm`: hub, arm, palm, servo, ir_sensor, jaw_L/R, cw_arm, counterweight, stop_tab

Plus `test_can`, standing at START.

These are block-level concept solids: correct envelopes, placement and motion. They are meant
as a layout skeleton for the detail design in SolidWorks or Fusion.

## Animate the flip in Fusion 360 (about 5 minutes)

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
