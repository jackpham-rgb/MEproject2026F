# Reprint: the parts with fits that matter

**Wait:** these files are regenerated after the tolerance gauge is measured (`TOL` in `backend/cad/model.py` corrected,
then `python3.13 backend/tools/make_reprint.py`). Printing them before that reprints the old hole sizes.

| File | Parts | Time | PETG |
|---|---|---|---|
| `reprint_1.3mf` | turret plate, top cap, lift link (crank hole 2.4 mm), carriage arm | ~7 h 20 | ~75 g |
| `reprint_2.3mf` | gripper frame + both fingers (new horn drive) | ~6 h 40 | ~51 g |
| `reprint_3.3mf` | base | ~7 h 15 | ~121 g |

Open in PrusaSlicer (Ctrl+O, "Yes" to load the settings), slice, print. Every plate has its settings inside:

- **Supports:** organic (tree), from the bed only, 0.25 mm gap to the part, 2 interface layers: they snap off.
- **Strength:** walls first, nothing at 100 %: fingers 5 walls + 30 % gyroid, precision parts 4 walls + 15 %, lift link 3 walls + 0 %.
- **Speed:** perimeters 50 / infill 80 mm/s (base 60 / 90 at 0.28 mm layers), within the stock hotend's PETG limit.
- **Bed stability:** `STABILITY.md` lists every side each part could lie on (contact area, height, tip ratio,
  overhang). The side used is the most stable one with the press-fit holes vertical; parts on a small footprint
  (lift link, both fingers) get a 5 mm brim automatically.

Why and sources: `docs/19_reprint_strategy.md`.
