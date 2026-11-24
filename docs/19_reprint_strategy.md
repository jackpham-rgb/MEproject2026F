# Reprint strategy: accurate fits, easy supports, less plastic, faster

Only the parts with fits that matter get reprinted, and only after the tolerance gauge has been measured:

1. Print and measure the gauge (`cad/print/tolerance_test/`), send the numbers.
2. `TOL` in `backend/cad/model.py` is corrected, every check re-runs, the STLs are re-exported.
3. `python3.13 backend/tools/make_reprint.py` rebuilds `cad/print/reprint/` with the corrected sizes.
4. Print `reprint_1..3.3mf` (Ctrl+O, "Yes"), check each fit as it comes off the bed.

| Plate | Parts | When | Time |
|---|---|---|---|
| `reprint_5` | carriage arm + lift link + turret plate | night 1 | 6 h 51 |
| `reprint_1` | carriage arm + lift link (short-night version of 5) | night 1, instead of 5 | 3 h 52 |
| `reprint_2` | spare claw: gripper frame + both fingers (horn drive) | day 2, during the shift | 6 h 49 |
| `reprint_3` | base | only if sanding the old pocket 46.0 → 47.0 fails (instead of 2) | 7 h 22 |
| `reprint_4` | turret plate | only after `reprint_1`, if hand-fixing the old one fails | 2 h 56 |

Hole sizes corrected from the measurements (docs/17, round 1): holes printed ~1.05 mm small, so `TOL` adds that back.
Not reprinted: top cap (drilled by hand), spine, tray (screw holes only: a drill bit by hand fixes them).

## Supports: easy to remove, less plastic

| Setting | Value | Why |
|---|---|---|
| Style | **Organic** (Cura: Tree) | Prusa: organic supports are easy to remove, don't scar the surface and are fast and cheap to print [1] |
| Placement | build plate only | nothing grows on the part's own surfaces |
| Support line width | **0.3 mm** (round 1: 0.25; 0.34 on the 0.28 mm base) | about half the 0.45 mm part line: thin lines bond weakly and crush off [7]. PrusaSlicer refuses a line thinner than the layer height, hence 0.34 at 0.28 mm |
| Top contact Z distance | **0.2 mm** (round 1: 0.25) | the default 0.1 is reported as too tight; 0.2–0.25 is the common "breaks away cleanly" value, PETG needs the upper end [2][3][7] |
| Bottom contact Z distance | 0.2 mm | [7] |
| Interface layers | 3 top, spaced **0.35 mm** (round 1: 0.7, from the guide); 2 bottom | a sparse interface still gives a flat underside but doesn't fuse into one sheet [7] |
| Base spacing | 2.5 mm | sparse body [7]; Bambu's "hollow" base pattern has no PrusaSlicer equivalent: organic branches are already hollow |
| XY separation | 60 % | keeps support off the side walls |
| Overhang threshold | 50° | supports only where really needed |
| Brim (only parts that could tip) | 3 mm, outer only, 0.3 mm gap | stable on a small footprint, peels off [7] |

Checked by slicing (PrusaSlicer 2.7): the thin supports use ~4 % less filament and add 1–11 min per plate (more,
thinner lines). The guide [7] was written for PLA+ on a Bambu printer; for PETG the same idea holds (PETG sticks to
itself more, so the wide gaps matter even more), but it is a user report, not a test: check the first plate.
Let the part cool completely before removing supports.

**Round 2 (after reprint_5):** the round-1 values came off easily but the supported underside sagged and strung: with
the interface lines 0.7 mm apart the first layer over them droops into the gaps (more so with this printer's
over-extrusion and PETG's oozing). Interface 0.35 mm apart and a 0.2 mm gap give a flatter underside for a little more
effort to remove. Strings over supports also come from wet PETG and over-extrusion: drying the spool and the flow /
retraction calibration (docs/18) fix those at the source, after the arm is done.

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

**Real numbers (PrusaSlicer, CR-6 SE profile):** see the table above (the claw: ~50 g instead of 67 g at 100 % infill). The biggest remaining limit is the printer's acceleration: the stock CR-6 SE profile uses
500 mm/s²; 1000 mm/s² would save ~8 % (the base: 7 h 15 → 6 h 40). Try it only after the tune-up (docs/18): send
`M201 X1000 Y1000` + `M500`, print the XYZ cube, and keep it if the cube still measures 20.00 mm with no ringing.

## Bed stability

`cad/print/reprint/STABILITY.md` lists, for every reprint part and every side it could lie on, the contact area,
height, tip ratio (height / √contact) and overhang. The side used is the most stable one that keeps the press-fit
holes vertical. A part with less than 300 mm² on the bed or a tip ratio above 2.5 gets a brim
(lift link, both fingers): 3 mm, outer only, 0.3 mm gap.

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
7. r/BambuLab user guide "How to produce easy to remove supports every time" (PLA+, Bambu Studio), shared by the team
