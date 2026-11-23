# Reprint: the parts with fits that matter

**Hole sizes corrected from the measurements of 2026-11-23** (docs/17: holes printed ~1.05 mm small). Print these
with the settings inside the 3MF: the correction is only right for the same layer height, speeds and temperatures.

| File | Parts | When | Time | PETG |
|---|---|---|---|---|
| `reprint_1.3mf` | carriage arm + lift link | **tonight** (short night) | 3 h 52 | ~39 g |
| `reprint_5.3mf` | carriage arm + lift link + turret plate | **tonight** (long night, instead of 1) | 6 h 51 | ~65 g |
| `reprint_7.3mf` | carriage arm + lift link + **left finger + gripper frame** (turret plate fixed by hand) | tomorrow, instead of 5 | 8 h 32 | ~74 g |
| `reprint_6.3mf` | left finger + gripper frame only | any free daytime slot | 4 h 39 | ~35 g |
| `reprint_2.3mf` | spare claw: gripper frame + both fingers | tomorrow during the shift | 6 h 49 | ~50 g |
| `reprint_3.3mf` | base | **only if** sanding the old pocket 46.0 → 47.0 fails | 7 h 22 | ~125 g |
| `reprint_4.3mf` | turret plate | **only if** sanding the hub / drilling the rod holes fails (not needed after 5) | 2 h 56 | ~26 g |

The top cap is not reprinted: its holes were drilled by hand. The new left finger (horn screwed onto the gear) only works
with the new gripper frame (servo 4.8 mm higher, 14 mm horn opening), so they always print together. The old right finger
still meshes with it (same gear).

Open in PrusaSlicer (Ctrl+O, "Yes" to load the settings), slice, print. Every plate has its settings inside:

- **Supports (easy to remove):** organic (tree), from the bed only, **support lines 0.25 mm wide** (about half the normal
  0.45 mm line, so they crush and peel; 0.34 on the 0.28 mm base, where PrusaSlicer refuses thinner), 0.25 mm top gap,
  0.2 mm bottom gap, 3 top interface layers spaced 0.7 mm apart (not solid), 2 bottom interface layers. **Let the part
  cool completely before pulling the supports.**
- **Brim** only where a part could tip (lift link, fingers): 3 mm, outer only, 0.3 mm gap to the part, so it peels off.
- **Strength:** walls first, nothing at 100 %: fingers 5 walls + 30 % gyroid, precision parts 4 walls + 15 %, lift link 3 walls + 0 %.
- **Speed:** perimeters 50 / infill 80 mm/s (base 60 / 90 at 0.28 mm layers), within the stock hotend's PETG limit.
- **Bed stability:** `STABILITY.md` lists every side each part could lie on (contact area, height, tip ratio,
  overhang). The side used is the most stable one with the press-fit holes vertical; parts on a small footprint
  (lift link, both fingers) get the 3 mm brim automatically.

Why and sources: `docs/19_reprint_strategy.md`.
