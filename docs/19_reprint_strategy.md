# Reprint strategy: accurate fits, easy supports, less plastic, faster

Only the parts with fits that matter get reprinted, and only after the tolerance gauge has been measured:

1. Print and measure the gauge (`cad/print/tolerance_test/`), send the numbers.
2. `TOL` in `backend/cad/model.py` is corrected, every check re-runs, the STLs are re-exported.
3. `python3.13 backend/tools/make_reprint.py` rebuilds `cad/print/reprint/` with the corrected sizes.
4. Print `reprint_1..3.3mf` (Ctrl+O, "Yes"), check each fit as it comes off the bed.

| Plate | Parts | Why they're reprinted |
|---|---|---|
| `reprint_1` | turret plate, top cap, lift link, carriage arm | 6807 hub Ø34.95, rod holes Ø6.0, LM6UU pockets Ø12.15, pivots |
| `reprint_2` | gripper frame + both fingers (new horn drive) | gear mesh, axle, horn screws |
| `reprint_3` | base | 6807 pocket Ø47.1 |

Not reprinted: spine, tray (screw holes only: a drill bit by hand fixes them).

## Supports: easy to remove, less plastic

| Setting | Value | Why |
|---|---|---|
| Style | **Organic** (Cura: Tree) | Prusa: organic supports are easy to remove, don't scar the surface and are fast and cheap to print [1] |
| Placement | build plate only | nothing grows on the part's own surfaces |
| Top contact Z distance | **0.25 mm** | the default 0.1 is reported as too tight; 0.2–0.25 is the common "breaks away cleanly" value, PETG needs the upper end [2][3] |
| Interface layers | 2 top, 0 bottom | fewer interface layers = easier removal [2] |
| XY separation | 60 % | keeps support off the side walls |
| Overhang threshold | 50° | supports only where really needed |

Plus: a part that needs no support (top cap) has supports switched off for it. If one spot still needs help,
paint it in PrusaSlicer (right-click the part › Add support enforcer / blocker) instead of raising the density.

## Strength: walls first, never 100 %

Tests show more perimeters raise strength more than more infill; 100 % infill is the strongest in absolute terms
but the worst strength per gram and the slowest [4][5]. Typical functional-part advice is 3–5 walls with
moderate infill [5]. So:

| Part type | Walls | Infill |
|---|---|---|
| Thin parts (lift link): walls fill it anyway | 3 | 0 % |
| Precision parts (turret plate, carriage, cap) | 4 | 15 % cubic |
| Gripper frame | 4 | 20 % |
| Fingers (gear teeth = solid wall) | 5 | 30 % gyroid, instead of 100 % |
| Base (big, hidden) | 3 | 12 % cubic |

## Speed

| Change | Effect |
|---|---|
| Perimeters 50, infill 80, solid 50 mm/s (outer wall 35, 25 on the gears) | faster, still under the CR-6 SE stock hotend's ~8 mm³/s for PETG |
| Cubic infill where only stiffness matters | faster than gyroid [6] |
| 0.28 mm layers on the base | ~half the time; the pocket's accuracy is in X-Y (set by TOL), not the layer height |
| Fewer, smarter supports (organic, 0.25 gap) | less support printing, faster cleanup |
| "Combine infill every N layers" | helps only below 0.16 mm layers on a 0.4 mm nozzle (max ~0.32 mm infill) [6], so not used at 0.2 mm |
| Only retract when crossing perimeters, thick bridges | fewer retractions and stronger bridges |

**Real numbers (PrusaSlicer, CR-6 SE profile):** reprint_1 ~7 h 20, reprint_2 ~6 h 40 (51 g instead of 67 g at 100 %
infill), reprint_3 ~7 h 15. The biggest remaining limit is the printer's acceleration: the stock CR-6 SE profile uses
500 mm/s²; 1000 mm/s² would save ~8 % (the base: 7 h 15 → 6 h 40). Try it only after the tune-up (docs/18): send
`M201 X1000 Y1000` + `M500`, print the XYZ cube, and keep it if the cube still measures 20.00 mm with no ringing.

## Bed stability

`cad/print/reprint/STABILITY.md` lists, for every reprint part and every side it could lie on, the contact area,
height, tip ratio (height / √contact) and overhang. The side used is the most stable one that keeps the press-fit
holes vertical. A part with less than 300 mm² on the bed or a tip ratio above 2.5 gets a 5 mm brim
(lift link, both fingers).

## Claw redesign (in this reprint)

The SG90's own round horn, trimmed to Ø12 mm, now sits flat on the left finger's gear, fixed with 2 servo-bag screws into 1.7 mm
pilots 5 mm from the gear centre; the servo's spline goes into the horn hub from above, like the earlier
prototype gripper. The horn carries the torque, so the bare spline no longer has to grip printed plastic.
The top plate has a Ø14 opening for the horn, and the servo sits 4.8 mm higher. (A full Ø20 horn would hit the servo post and reach the can bumper: checked.) Checked: collision sweep,
engineering checks (horn-screw pilot bearing at SG90 stall) and the assembly order (`cad/check/`).

## Sources

1. Prusa Knowledge Base, Support material: https://help.prusa3d.com/article/support-material_1698
2. Prusa forum, "PrusaSlicer hard to remove supports": https://forum.prusa3d.com/forum/prusaslicer/prusaslicer-hard-to-remove-supports/paged/5
3. Prusa forum, "PETG Support Help": https://forum.prusa3d.com/forum/english-forum-general-discussion-announcements-and-releases/petg-support-help
4. 3DPrinting.com, How to get stronger FDM prints (CNC Kitchen tests): https://3dprinting.com/how-to/how-to-get-stronger-fdm-3d-prints/
5. DigiKey Maker.io, How to make 3D prints stronger: https://www.digikey.com/en/maker/blogs/2025/how-to-make-3d-prints-stronger
6. Prusa Knowledge Base, Infill (combine infill, patterns): https://help.prusa3d.com/article/infill_42
