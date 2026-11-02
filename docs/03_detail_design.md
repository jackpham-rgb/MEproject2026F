# Detail Design: Concept A (printable-level CAD + motion check)

Source: `cad/`. Wiring: `04_wiring.md`. BOM: `05_bom.md`. One Python model (`model.py`) holds every part, its material and
the robot's kinematics. The collision check, the STEP/STL exports, the Fusion 360 script and the
3D page (`viewer/concept_a_detail.html`) all use that same model.

```bash
python3.13 cad/check.py    # motion + collision + mass + loads -> out/check_report.txt
python3.13 cad/export.py   # STEP assembly, per-part STEP/STL, viewer + Fusion data
python3 tools/build_detail_viewer.py        # rebuild the 3D page
```
(`pip install cadquery`; CadQuery needs Python ≥ 3.10.)

## What changed from the PDR concept, and why

Running the real part shapes through the firmware sequence found problems that the block model
missed. Each fix below closes a problem the check found.

| Problem found | Fix |
|---|---|
| The turntable stack (servo + bearing + plate, ~59 mm) is as tall as the grip axis (59.7 mm), so the wrist servo hanging below the arm drove into the turret plate and the lazy-susan | Replaced the 4 in lazy-susan with a **6807-2RS bearing (35 × 47 × 7 mm)** in a **28 mm tower**. The turret plate is now a **"D"** that stops 22 mm in front of the axis |
| The square base corner reached the can's path, so the inverted can and the flipped gripper hit the base during the 90° turn | The base is **cut away in the 175° sector the arm, the open arms and the can sweep** (−30° … 145°). Only the bearing tower stays there |
| The MG996R body sat under the arm's path | The servo now points **away from the sweep** (225°) |
| The open gripper arms hit the gripper-frame posts | Posts moved inside the arms' swing (x = ±15 mm) |
| At the target the gripper is upside down, so opening fully (75°) swung an arm down into the base | **Release opens only 25°** (`GRIP_RELEASE = 70`). That's enough: the pads clear the can by 3.6 mm |
| Turning back with the can at the target sweeps the gripper through it | Homing only after the can is lifted off (the button press), as before |
| Un-flipping with the arms open sweeps them through the table | Homing order: **lift → close → un-flip → turn → lower → open** (firmware updated) |
| The turret hub sat at 0.0 mm on the MG996R body (rubbing) | Hub raised 0.6 mm |
| Pads touched the can 6–26 mm above its middle (the voted design grips the middle) | Pads made 40 mm tall (z 46–86 mm), so they cover the middle of the can |
| The can is a standard Coke can (66.2 × 122.2 mm, tapered top and bottom), not a generic 2.4 × 4.7 in cylinder | Grip axis raised to 61.1 mm (mid-height); finger pivots moved to y = 83 mm and the plates trimmed; carriage and lift servo up 2 mm; can bumper narrowed so it stays ≥ 0.5 mm from the closed fingers |
| One MG996R mounting block rose into the turret hub | Block shortened to stop 1 mm under the hub |
| Power: a 12 V adapter + XL4015 buck needed setting with a meter and added a board | One **5 V 4 A wall adapter** feeds the servos and the Uno directly; the buck and its tray standoffs are gone (power matrix in `decision_matrix_and_bom.xlsx`, rail check in `EE/README.md`) |

## Final check (`out/check_report.txt`)

| Check | Result |
|---|---|
| Part-to-part collisions, 289 poses (every 7°/0.6 mm), solid booleans | **PASS**: none |
| Anything moving below the table | **PASS**: lowest is the gripper servo, 17 mm up |
| Can at the end | **PASS**: centre (127.0, 0.0) mm, inverted, 0.0° tilt, set down at z = 0 |
| Pads | Touching the can at the end of GRIP (the servo then squeezes past contact); 3.6 mm clear after release |
| Tightest running gaps | 0.5 mm finger ↔ gripper plates (designed); 0.5 mm can ↔ bumper and bumper ↔ closed fingers (designed). LM6UU on rods is a sliding fit |
| Tip-over | **PASS**: the robot CG stays ≥ 36 mm inside the base + tray footprint in every pose |
| Lift slides freely | **PASS**: jam ratio 0.018 with LM6UU; a printed slide would be 0.55 |
| Servo margins (CAD masses) | Lift 5×, wrist 30×, turntable ≫ (weight on the bearing) |
| Mass | ≈ 545 g robot (≈ 300 g PETG printed, 245 g purchased) |

## 3D-print tolerances (PETG, 0.4 mm nozzle)

All holes are generated from the `TOL` table in `model.py`. **Print `tolerance_coupon.stl`
first** (6 holes, labelled in the part note) and adjust `TOL` if a fit is off.

| Fit | Size (mm) | Where |
|---|---|---|
| #6-32 clearance / pilot | 3.9 / 2.9 | Most joints. Screws cut their own thread (no nuts in the kit) |
| #8-32 pilot | 3.5 | MG996R flange into the base |
| Servo-bag screw pilot | 1.7 | Servo tabs and horns |
| 6 mm rod press | 6.00 | Blind holes in the turret plate and top cap capture the rods |
| LM6UU press | 12.15 | 4 pockets in the carriage, 43 mm apart per rod |
| 6807 housing / hub | 47.10 / 34.95 | Outer race in the tower; printed hub in the bore |
| Running clearance | ≥ 0.5 | Finger arms between the gripper plates |
| Gear backlash | +0.2 | m1 16T gears, centre distance 16.2 mm |

## Fasteners: Harbor Freight 57-pc machine-screw kit #67675

The kit has pan-head Phillips screws only, with **no nuts**, so every screw threads into a
printed pilot hole.

| Screw | Used | Where |
|---|---|---|
| #6-32 × ½″ (12 in kit) | 8 | Tray → base 2, spine → turret 2, top cap → spine 2, link pivot 1, right gear axle 1 |
| #8-32 × ½″ (10 in kit) | 4 | MG996R flange → base |
| Servo-bag screws | ~14 | Servo tabs 2 × 3, horn → turret 4, horn → gripper flange 4, crank → link 1. A small M2 self-tapping pack covers any shortfall |
| None (press fit) | — | 2 rods, 4 LM6UU, 6807 bearing, turret hub |
| Glue | — | Silicone pad liners and can bumper. The Uno sits on printed pegs (the Uno's 3.2 mm holes are too small for #6) |

## Parts (printed in PETG unless noted)

`base` (bearing tower, servo pocket, ballast pockets) · `electronics_tray` (Uno,
breadboard, button/LED/DC-jack panel) · `turret_plate` (D plate + hub + rod bosses) · `spine`
(column back + lift-servo bracket) · `top_cap` · `carriage_arm` (carriage + arm + wrist bracket,
one print) · `lift_link` · `gripper_frame` (flange + 2 plates + posts) · `finger_L`, `finger_R`
(gear + arm + pad) · `can_bumper` (silicone sheet) · `tolerance_coupon`.

## Simulating it in Fusion 360 and SolidWorks

- **STEP:** `cad/out/concept_a_detail_assembly.step` opens in both. It has one
  component per moving group: `grp_fixed`, `grp_turret`, `grp_crank`, `grp_lift`, `grp_wrist`,
  `grp_finger_L`, `grp_finger_R`, `grp_can`.
- **Fusion 360:** run the script `cad/fusion_animate/`. It imports the STEP,
  plays the firmware sequence, and runs Fusion's own interference check at the end of every
  move. Its transforms match the model to 1e-14. It **has not been run inside Fusion yet**; if
  an API call fails, it reports which one.
- **SolidWorks:** open the STEP and mate the groups. The joints are listed in `cad/README.md`.

## Verify before printing

Purchased-part dimensions are typical datasheet values: **measure your parts** and edit `P` in
`model.py`, then rerun `check.py`.
- MG996R body and flange
- Micro servo body and tabs
- 6807 bearing
- The can: modelled as a standard 12 oz Coke can (66.2 mm × 122.2 mm, 15 g empty)
