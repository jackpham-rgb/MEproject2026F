# Reprint: the parts with fits that matter

**Hole sizes corrected from the measurements of 2026-11-23** (docs/17: holes printed ~1.05 mm small). Print these
with the settings inside the 3MF: the correction is only right for the same layer height, speeds and temperatures.

| File | Parts | Time | PETG | When |
|---|---|---|---|---|
| `reprint_3.3mf` | **base**, time-optimised: 0.32 mm layers, lightning infill, 3 walls | 5 h 45 | ~113 g | (was 7 h 40) |
| `reprint_a.3mf` | **carriage arm, on its side** (stronger arm, side gussets, teardrop pockets: no support inside; the link's pivot boss notched so the upper bearing goes in) | 5 h 09 | ~52 g | the old one snapped at the arm |
| `reprint_8.3mf` | **gripper frame + right finger** (frame: 16 mm horn opening, unused plate wings cut off: −27 % plastic) | 4 h 05 | ~30 g | goes with the new left finger you printed |
| `reprint_b.3mf` | a + 8 on one plate | 9 h 20 | ~81 g | only if a 10 h window; PrusaSlicer's command line crashed AFTER slicing it once: if your slicer crashes, print a and 8 separately |
| `reprint_c.3mf` | **base + carriage arm** on one plate (base keeps 0.32 mm layers, carriage 0.2 mm) | 10 h 50 | ~164 g | only with an 11 h window: same time as 3 + a apart |
| **`reprint_g.3mf`** | **carriage arm + lift link + 5 mm horn spacer: the Fixed build from your original parts.** Only what can't be fixed by hand: the snapped carriage, the new lift link (14 mm crank horn), the spacer (old base: no sanding). Reused: base, turret plate, spine, top cap, gripper frame (open its horn hole to 16 mm by hand, loose on the table), both fingers | **5 h 27** | ~55 g | **recommended, 1 run** |
| `reprint_h.3mf` | g + a new gripper frame (if the old claw is already built: no hole to open, no taking it apart) | 7 h 13 | ~68 g | 1 run, if you'd rather not touch the old frame |
| `reprint_f.3mf` | **carriage arm + gripper frame + lift link: everything that must be reprinted** (base reused: add the 5 mm horn spacer, `cad/print/fix/horn_spacer_5mm.stl`, 23 min; no sanding) | 6 h 52 | ~65 g | superseded by h (same parts + the horn spacer) |
| `reprint_d.3mf` | **base + carriage arm + gripper frame + new lift link** (14 mm crank) on one plate (old right finger reused) | **12 h 46** | ~179 g | **the one-go plate (≤ 13 h)** |
| `reprint_e.3mf` | d + a new right finger | 14 h 49 | ~194 g | over 13 h: print the finger separately if needed (`reprint_8` has frame + finger) |
| `reprint_2.3mf` | whole claw (frame + both fingers) | 6 h 27 | ~45 g | only if the left finger is reprinted too |

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


**2026-11-25:** the lift crank now uses the single-arm horn from the servo bag (its last hole, 14 mm), so a new, longer lift link
(11.2 mm between holes) is on the carriage plates (a, b, c, d, e). Firmware LIFT_UP 75 -> 98 (68 deg swing, 15.7 mm lift).

**2026-11-25 (servo datasheets):** MG996R modelled at its real 42.9 mm overall height (the spline was 5 mm too high): the base's 2 servo blocks are 5 mm shorter. **A base printed before this: sand 5 mm off the 2 blocks' bottom faces.** MG90S/SG90 bodies modelled at 32.7 mm: the wrist servo sits 3.5 mm further out on the arm (it reached the base tower), so the carriage arm is 3.5 mm longer and the gripper frame 3.5 mm shorter (both on plate d).

**Reuse, don't reprint:** base (print the 5 mm horn spacer, `cad/print/fix/`, instead of sanding the blocks), turret plate, spine (file 2 screw-head notches), top cap, both fingers. The carriage now has a lightening window between its bearing pockets (−8 % plastic); the gripper frame is already trimmed (−27 %).
