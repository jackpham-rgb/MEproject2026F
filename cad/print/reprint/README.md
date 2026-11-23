# Reprint: the parts with fits that matter

**Hole sizes corrected from the measurements of 2026-11-23** (docs/17: holes printed ~1.05 mm small). Print these
with the settings inside the 3MF: the correction is only right for the same layer height, speeds and temperatures.

| File | Parts | When | Time | PETG |
|---|---|---|---|---|
| `reprint_1.3mf` | carriage arm + lift link | **tonight** (short night) | 3 h 47 | ~41 g |
| `reprint_5.3mf` | carriage arm + lift link + turret plate | **tonight** (long night, instead of 1) | 6 h 40 | ~67 g |
| `reprint_2.3mf` | spare claw: gripper frame + both fingers | tomorrow during the shift | 6 h 42 | ~52 g |
| `reprint_3.3mf` | base | **only if** sanding the old pocket 46.0 → 47.0 fails | 7 h 21 | ~125 g |
| `reprint_4.3mf` | turret plate | **only if** sanding the hub / drilling the rod holes fails (not needed after 5) | 2 h 52 | ~27 g |

The top cap is not reprinted: its holes were drilled by hand.

Open in PrusaSlicer (Ctrl+O, "Yes" to load the settings), slice, print. Every plate has its settings inside:

- **Supports:** organic (tree), from the bed only, 0.25 mm gap to the part, 2 interface layers: they snap off.
- **Strength:** walls first, nothing at 100 %: fingers 5 walls + 30 % gyroid, precision parts 4 walls + 15 %, lift link 3 walls + 0 %.
- **Speed:** perimeters 50 / infill 80 mm/s (base 60 / 90 at 0.28 mm layers), within the stock hotend's PETG limit.
- **Bed stability:** `STABILITY.md` lists every side each part could lie on (contact area, height, tip ratio,
  overhang). The side used is the most stable one with the press-fit holes vertical; parts on a small footprint
  (lift link, both fingers) get a 5 mm brim automatically.

Why and sources: `docs/19_reprint_strategy.md`.
