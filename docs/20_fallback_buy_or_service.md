# Fallback: buy the body (or have it printed) and keep our electronics

If the printer keeps failing, these replace printed parts with things that can be bought or ordered. The electronics
(Uno, buck, servos, wiring, firmware) stay exactly as they are; only the mechanical body changes. Checked 2026-11-24.

**With the deadline 2 days away, only same/next-day options are realistic:** anything on Amazon Prime, a local hardware
store, or a campus makerspace / library printer. Online print services (below) are 3–7 days.

## Part by part

| Our part | What it does | Buy instead | Fits our electronics? |
|---|---|---|---|
| Base + 6807 bearing | turntable on the MG996R | a **lazy-susan bearing** (hardware store, 3–4″) screwed between two pieces of plywood/MDF, MG996R screwed under the bottom board, its round horn screwed to the top board; or a **metal pan/tilt / multi-purpose servo bracket kit for MG995/MG996R** ([X2 Robotics](https://x2robotics.ca/pan-tilt-bracket-kit-for-mg995-and-mg996r-servo), [CRC Cibernetica](https://www.crcibernetica.com/servo-bracket-mount-kit), [Lynxmotion ASB-201](https://www.robotshop.com/products/lynxmotion-large-multi-servo-bracket-asb-201)) | yes: same MG996R and horn |
| Spine + carriage + rods (lift) | moves the claw up 15 mm | no kit does a vertical slide; keep the rods + LM6UU, or swap the lift for a **shoulder joint**: the MG90S in an aluminium U-bracket tilting the arm up | yes, but the firmware's lift angles must be re-tuned |
| Wrist bracket | holds the wrist servo, flips the can | **SG90/MG90S servo bracket** ([ProtoSupplies](https://protosupplies.com/product/sg90-mg90-servo-bracket/)) screwed to the arm | yes |
| Gripper frame + fingers | the claw | **acrylic SG90 claw kit** (servo not included): [Abra RACG-03](https://abra-electronics.com/robotics/robot-claws-grippers/racg-03.html), [robu.in](https://robu.in/?p=835777); geared metal: [Lynxmotion geared gripper](https://RobotShop.com/products/lynxmotion-lss-geared-gripper-kit) | yes: SG90; opening must reach the can's 66 mm |
| The whole arm | everything | **4-DOF acrylic arm kit with MG90S** ([ThinkRobotics](https://thinkrobotics.com/products/4-dof-white-acrylic-robotic-arm-mg90s-kit-online), [Probots, with Uno](https://probots.co.in/4-dof-acrylic-robotic-mechanical-arm-programming-with-ps2-controller-servo-motor-claw-diy-kit.html), [Open-Electronics, ball-bearing base](https://www.open-electronics.org/4-dof-plexiglass-robotic-arm/)); same type is on Amazon as "4DOF acrylic robot arm kit" | partly: base + 2 arm joints + claw, but **no wrist roll**: add our MG90S wrist between the arm and the claw with a servo bracket, or the can can't be flipped |

## Caveats (fact-checked)

- Kits built for SG90 are usually too small for a 66 mm can: check the claw's maximum opening (the ThinkRobotics kit
  lists 90 mm; others ~75 mm).
- SG90 and MG90S share mounting sizes, so SG90 brackets usually take an MG90S, but no kit listing confirms it.
- An acrylic 4-DOF arm moves in arcs (shoulder/elbow), not straight up like our carriage: the pick and drop heights
  must be re-taught in the laptop panel.

## Print services (if there are 3+ days)

- [Xometry PLA/PETG](https://www.xometry.com/capabilities/3d-printing-service/pla-petg/): instant quote, free US shipping.
- [Hubs PETG](https://hubs.com/3d-printing/plastic/petg): quoted price includes shipping.
- [Fictiv](https://fictiv.com/?p=1918): advertises parts in as fast as 24 h (vendor claim).

Upload the STLs from `cad/print/stl/`. **Service printers are calibrated, so print the ORIGINAL hole sizes, not ours:**
our `TOL` adds ~1 mm for this CR-6 SE. Ask before sending; we can export a "nominal holes" set in a few minutes.
A campus makerspace or library printer is the fastest; the same note applies.
