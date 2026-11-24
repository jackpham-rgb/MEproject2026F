# Reprint: the parts with fits that matter

**Hole sizes corrected from the measurements of 2026-11-23** (docs/17: holes printed ~1.05 mm small). Print these
with the settings inside the 3MF: the correction is only right for the same layer height, speeds and temperatures.

| File | Parts | Time | PETG | When |
|---|---|---|---|---|
| `reprint_3.3mf` | **base** | 7 h 40 | ~131 g | priority 1 |
| `reprint_a.3mf` | **carriage arm, on its side** (stronger arm, side gussets, teardrop pockets: no support inside) | 5 h 09 | ~52 g | the old one snapped at the arm |
| `reprint_8.3mf` | **gripper frame + right finger** (frame with a 16 mm horn opening) | 4 h 40 | ~35 g | goes with the new left finger you printed |
| `reprint_b.3mf` | a + 8 on one plate | 9 h 44 | ~87 g | only if a 10 h window; PrusaSlicer's command line crashed AFTER slicing it once: if your slicer crashes, print a and 8 separately |
| `reprint_2.3mf` | whole claw (frame + both fingers) | 6 h 52 | ~51 g | only if the left finger is reprinted too |

Round 1 plates (1, 4, 5, 6, 7, 9; 5 was printed): `archive/reprint_2026-11-23/`.

The top cap is not reprinted: its holes were drilled by hand. The new left finger (horn screwed onto the gear) only works
with the new gripper frame (servo 4.8 mm higher, 14 mm horn opening), so they always print together. The old right finger
still meshes with it (same gear).

Open in PrusaSlicer (Ctrl+O, "Yes" to load the settings), slice, print. Every plate has its settings inside:

- **Supports (easy to remove, round 2):** organic (tree), from the bed only, support lines 0.3 mm (0.34 on the 0.28 mm
  base), 0.2 mm top and bottom gap, 3 top interface layers 0.35 mm apart, 2 bottom ones. Round 1 (lines 0.25, interface
  0.7 mm apart, 0.25 gap, from the shared guide) came off easily but left a saggy, stringy underside on reprint_5: the
  sparse interface lets the first layer droop between the lines. **Let the part cool completely before pulling them.**
- **Brim** only where a part could tip (lift link, fingers): 3 mm, outer only, 0.3 mm gap to the part, so it peels off.
- **Strength:** walls first, nothing at 100 %: fingers 5 walls + 30 % gyroid, precision parts 4 walls + 15 %, lift link 3 walls + 0 %.
- **Speed:** perimeters 50 / infill 80 mm/s (base 60 / 90 at 0.28 mm layers), within the stock hotend's PETG limit.
- **Bed stability:** `STABILITY.md` lists every side each part could lie on (contact area, height, tip ratio,
  overhang). The side used is the most stable one with the press-fit holes vertical; parts on a small footprint
  (lift link, both fingers) get the 3 mm brim automatically.

Why and sources: `docs/19_reprint_strategy.md`.
