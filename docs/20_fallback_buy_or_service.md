# Fallback plan: finish on time even if a print fails

Rule: **the electronics, servos, rods, LM6UU and 6807 never change**; only the body around them does. Each printed
part has a plan B from a hardware store (same day) and, last, a bought kit or a print service. Decide by the
triggers below, not by hoping: a failed print costs a whole day window.

## 1. Timeline to the deadline (26 Nov) and the decision points

| When | Do | Trigger → switch |
|---|---|---|
| **24 Nov evening** | Electronics: re-wire the bench test into the robot harness (PART E). Try the old base pocket with the rotary tool if it has arrived (46 → 47 mm). | Rotary tool not here, or the pocket goes oval → base plan B tonight or a base print (below). |
| **25 Nov, before work** | Start `reprint_b` (carriage + gripper frame + right finger, 9 h 20). Watch the first layer 5 min. | First layer lifts / spaghetti → stop, start `reprint_a` alone (5 h 09: the carriage is the part you can't replace). |
| **25 Nov, back home** | Check the parts: carriage pockets take the LM6UU by hand, arm solid. Build the column, steps 1–15 (all on the table). | Carriage failed → carriage plan B. Frame failed → keep the old claw (it works). |
| **25 Nov evening** (only if printing while awake is OK) | `reprint_3` base, 5 h 45. | No window or it fails → base plan B (1–1.5 h of work). |
| **26 Nov** | Steps 16–22 (base, column on the servo, tray), full test run, demo. | Anything still missing → the kit/service rows below are too slow now: use plan B parts. |

## 2. Plan B per part (hardware store, same day)

| Part | What it must do | Plan B | Tools / time |
|---|---|---|---|
| **Base** (5 h 45 print) | hold the 6807 outer ring, the MG996R under it with its spline on the bearing's centre, weight low | **Two-layer wooden base**: ½″ plywood/MDF top board (~150 × 150) with a **1‑7/8″ (47.6 mm) hole** (hole saw or Forstner bit), glued/screwed onto a second board: the hole becomes a 12 mm deep pocket for the 6807 (47.0 mm: one wrap of tape on the bearing for a snug fit). Cut a **41 × 20 mm slot** in the bottom board for the MG996R body, spline exactly under the hole centre (measure: the spline is off-centre on the servo), tabs screwed under the board. Stand it on 4 blocks ~50 mm tall (the servo is 43 mm). Weight: a bag of sand or washers taped inside. | drill, 1‑7/8″ hole saw / Forstner, jigsaw or saw + file for the slot, wood glue / screws; 1–1.5 h |
| **Old base, fix** | same | Rotary tool + sanding drum, low speed, all the way round, 46 → 47 mm; loose → tape (docs: step 16) | 20–30 min |
| **Carriage + arm** (5 h 09 print) | slide on the 2 rods (LM6UU), carry the wrist servo 40 mm in front | **Repair the old one**: glue the break (2-part epoxy, or superglue + baking soda), then bridge it with a **½″ aluminium flat bar** (or a steel mending plate) screwed along the underside of the arm and onto the carriage body with 2 short #6 pointed screws each side. The bearings/rod holes are unchanged. | epoxy or superglue, mending plate / flat bar, drill 7/64″ pilots; 30 min + glue cure |
| **Gripper frame + right finger** (4 h 15) | hold the 2 fingers and the SG90 | **Keep the old claw** (gears mesh well today). If the claw breaks: an **acrylic SG90 claw kit** (Amazon, 1-day; check the opening ≥ 70 mm for the 66 mm can). | — |
| **Spine / top cap** | hold the rod tops and the lift servo | Already printed. If one cracks: epoxy + a metal angle bracket (hardware store "corner brace") screwed across the crack. | 20 min |
| **Lift (carriage won't slide / no carriage)** | raise the can ~15 mm before the flip | **Shoulder instead of slide**: the MG90S in an SG90/MG90 servo bracket at the top of the spine tilts a straight arm (aluminium bar) up/down; the lift angles are re-taught in the laptop panel (`LIFT_DOWN`/`LIFT_UP`). Last resort: changes the motion, the firmware stays. | servo bracket, aluminium bar; 1–2 h + re-tune |

## 3. Buy the body (1–2 days delivery: only if ordered by 24 Nov)

| Kit | Covers | Gaps for our job |
|---|---|---|
| 4-DOF acrylic arm with MG90S ([ThinkRobotics](https://thinkrobotics.com/products/4-dof-white-acrylic-robotic-arm-mg90s-kit-online), [Probots](https://probots.co.in/4-dof-acrylic-robotic-mechanical-arm-programming-with-ps2-controller-servo-motor-claw-diy-kit.html), [Open-Electronics](https://www.open-electronics.org/4-dof-plexiglass-robotic-arm/); same type on Amazon as "4DOF acrylic robot arm kit") | base turn, 2 arm joints, claw | **no wrist roll** (add our MG90S wrist with a bracket), small claw (66 mm can), pick/drop heights re-taught |
| Acrylic SG90 claw ([Abra RACG-03](https://abra-electronics.com/robotics/robot-claws-grippers/racg-03.html), [robu.in](https://robu.in/?p=835777)) | the claw | check the max opening |
| MG996R bracket kits ([X2 Robotics](https://x2robotics.ca/pan-tilt-bracket-kit-for-mg995-and-mg996r-servo), [CRC Cibernetica](https://www.crcibernetica.com/servo-bracket-mount-kit), [Lynxmotion ASB-201](https://www.robotshop.com/products/lynxmotion-large-multi-servo-bracket-asb-201)) | brackets for a shoulder joint | — |
| SG90/MG90 bracket ([ProtoSupplies](https://protosupplies.com/product/sg90-mg90-servo-bracket/)) | wrist / shoulder bracket | — |

## 4. Someone else prints it

- **Fastest: a campus makerspace / library printer** (same day if a machine is free).
- Online services are 3–7 days, too slow now: [Xometry](https://www.xometry.com/capabilities/3d-printing-service/pla-petg/), [Hubs](https://hubs.com/3d-printing/plastic/petg) (price includes shipping), [Fictiv](https://fictiv.com/?p=1918) (claims 24 h).
- **Send `cad/print/nominal/stl/`, not `cad/print/stl/`.** Our STLs have every hole ~1 mm bigger to cancel this
  CR-6 SE's over-extrusion; a calibrated printer would print them loose. The nominal set has the original fits
  (made with `CA_NOMINAL_HOLES=1 python3.13 backend/cad/print_prep.py`).
- Priority if only one part can go out: carriage arm → base → gripper frame + right finger.

## 5. One shopping trip that covers every plan B

½″ plywood or MDF (~300 × 150 mm), 1‑7/8″ hole saw or Forstner bit, wood glue, 4 short wood blocks or 2 × 2,
2-part epoxy, ½″ aluminium flat bar (or 2 steel mending plates + 2 corner braces), #6 × ¼″ and #6 × ½″ pointed
pan-head screws, electrical tape, a small precision Phillips screwdriver (for the servo-bag screws), sandbag or
washers for ballast.
