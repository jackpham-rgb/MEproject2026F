# Preliminary CAD Brief: Concept A (SolidWorks / Fusion 360)

The concept solids are already generated: `cad/out/concept_a/concept_a_assembly.step` (mm), with
one STEP/STL per part (`python3 cad/build_cad_concept_a.py`). Use it as the layout skeleton,
then detail each part.

## Frame

- **Origin:** the turntable axis on the table, which is the robot's location (the vertex of
  Figure 2). **+Y** → START, can at (0, 5) in. **+X** → TARGET, can at (5, 0) in. **+Z** up.
- **Home pose:** arm pointing at START, lift down, wrist upright, arms open.
- **Joints:**
  - Turntable: revolute about Z, 0 → −90°.
  - Lift: slider along Z, 0 → 0.6 in.
  - Wrist: revolute about the radial Y line at z = 2.35 in (+0.6 when lifted), 0 → 180°.

## Parts

| Group | Part | Critical dimensions (in) | Notes |
|---|---|---|---|
| fixed | Base box | ±3.0 × ±3.0, 1.0 tall | Must stay **within 3.55 in** of the axis toward both cans. May extend behind the corner. Holds the turntable servo. Add washer pockets and rubber feet |
| fixed | Lazy-susan bearing | Ø 3.5 ring, top at z = 1.15 | Carries the turret's weight and tipping load, so the servo only turns it |
| fixed | Turntable servo (MG996R) | Inside the base, output shaft on the Z axis | Couple it to the turret with a spline horn. It must not carry side load |
| turret | Turntable plate | Ø 3.6, z 1.15–1.35 | |
| turret | Column | 0.9 × 0.9, to z = 4.3 | |
| turret | Guide rods | 2 × Ø 6 mm steel, 0.7 apart, 0.6 in front of the axis | **LM6UU bushings**, a printed slide jams (see `02_design_analysis.md` § 5) |
| turret | Lift servo (MG90S) | On the back of the column | Horn radius **0.35 in**, swings ±60° to give a 0.61 in stroke through a link to the carriage |
| lift | Carriage | 1.2 × 0.65 × **1.6 tall** | The 2 LM6UU bushings are ≥ 1.6 in apart vertically. Travel z 1.55–3.15 (down) to 2.15–3.75 (up) |
| lift | Arm | From the carriage to r = 2.65, at the grip height 2.35 | |
| lift | Wrist servo | r = 2.65–3.35, output shaft pointing radially (+Y) | **Must reach a full 180°.** Use a 270° micro servo if not |
| wrist | Wrist hub + palm | Palm face at **r = 3.7** (0.1 in clear of the can at 3.8), ±1.6 wide | The wrist axis passes through the can's centre: r = 5, z = 2.35 |
| wrist | Gripper servo | On top of the palm | Link to both arms so they move symmetrically |
| wrist | 2 gripper arms | V-shaped, **open gap 2.9**, closed on the can at 2.4, reach r = 3.5–5.9 | Contact at can mid-height. TPU or silicone pads. The FSR goes under one pad (optional) |

## Checks to do in CAD

1. **Interference at wrist roll 0°, 27°, 90°, 153° and 180°** with the lift up. The can must clear
   the table by ≥ 0.3 in (the calc says +0.31 in).
2. **Turntable sweep 0 → −90°** with the lift up: nothing on the turret hits the base or the can
   footprints.
3. **Carriage travel:** 0.6 in without binding. Check the bushing spacing (≥ 1.6 in).
4. **Mass properties:** put the moving masses back into `sim/concept_a.py` (the `M = {…}` table)
   and rerun it for the servo loads and the jam ratio.
5. **Optional wide-opening claw:** if the arms pivot open ≥ 80°, check they clear the can so the
   turntable can turn back without the can being removed first.
