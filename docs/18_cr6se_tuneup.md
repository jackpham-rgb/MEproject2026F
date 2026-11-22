# CR-6 SE tune-up: get the used printer to a known-good state (PLA + PETG)

Do it in this order: each stage depends on the one before. A mechanical fault can't be tuned away in the slicer.
Files: `cad/print/calibration/` (profiles, SD-card G-code, test prints for each material). Record every result
in the table at the end and send it: the profiles and the robot's CAD tolerances get updated from it.

## Stage 1: inspect and repair (power off, cold)

| ☐ | Check | Good | Fix |
|---|---|---|---|
| ☐ | Frame screws (gantry uprights to base, top bar) | nothing moves when you push the gantry | tighten; check the gantry is square to the bed |
| ☐ | Wheels: print head, X gantry, bed | each wheel turns with a little drag, no wobble, no flat spots | turn the eccentric nut until the wheel just stops slipping; replace flat-spotted wheels |
| ☐ | X and Y belts | tight, no slack, teeth intact, no fraying | re-tension (the knobs / idlers); a belt with missing teeth: replace (GT2 6 mm) |
| ☐ | Z: 2 lead screws | gantry the same height on both sides (measure with a ruler from the frame) | turn one lead screw by hand to level the gantry; clean the screws, a thin film of grease |
| ☐ | Z couplers | screws tight on both motor shafts | tighten |
| ☐ | **Extruder arm** (plastic, known to crack on the CR-6 SE) | no crack near the pivot; filament gripped firmly | replace with an aluminium extruder (cheap and common) |
| ☐ | Bowden tube + couplers | tube doesn't move in and out when the extruder retracts; tube end cut square and pushed fully against the nozzle | cut 2 mm off square, re-seat; worn couplers: replace |
| ☐ | **Nozzle** | a used printer's nozzle is often worn or partly clogged | fit a new 0.4 mm brass nozzle; tighten it HOT (≈ 240 °C), gently |
| ☐ | Fans | hotend fan always on when hot; part fan spins | clean dust; replace a noisy / slow fan |
| ☐ | Bed sheet | flat on the magnet, no dents; textured PEI clean | dish soap + water, then don't touch it |
| ☐ | Cables | no cracked insulation at the hotend / bed; thermistor reads room temperature when cold | replace damaged cables before printing |

## Stage 2: machine calibration (SD card G-code, `cad/print/calibration/gcode/`)

1. **Level:** screen › Level, with a CLEAN nozzle (it is the probe). Re-level after any nozzle change.
2. **PID tuning** (steady temperatures = consistent sizes): print `PID_HOTEND_PETG.gcode`, then `PID_HOTEND_PLA.gcode`
   (the last one run stays saved: run the one for the material you use most last), then `PID_BED.gcode`.
   Each takes ~5 min and saves with M500.
3. **E-steps** (the extruder pushes exactly what is asked):
   - Mark the filament 120 mm above the extruder inlet, print `ESTEPS_TEST.gcode` (extrudes 100 mm slowly).
   - Measure from the inlet to the mark: should be 20 mm. Send the number (and the `M92 E…` value the printer
     shows): you get a one-line G-code file with the corrected value. Formula: new = old × 100 / (120 − remaining).
4. **Clog check:** if extrusion is weak or uneven, do a cold pull: `COLD_PULL_HEAT.gcode` (200 °C), push PLA through,
   cool to ~90 °C, pull it out firmly.

If the screen says a command isn't supported, the firmware is an old Creality build: tell me the version
(screen › About) and we use the slicer-side fallback.

## Stage 3: test prints, for EACH material

Profiles: `cad/print/calibration/profiles/PLA_cr6se.ini`, `PETG_cr6se.ini` (Ctrl+L). Test prints:
`cad/print/calibration/PLA/` and `.../PETG/` (Ctrl+O, "Yes" to load the settings, slice, print).

| # | File | Time | What to look at / measure |
|---|---|---|---|
| 1 | `01_first_layer.3mf` | 11 min | 5 squares (4 corners + centre). Lines flat and touching, same on all 5. Adjust the Z-offset live (0.02 mm steps). A bad corner = re-level / gantry not level |
| 2 | `02_temp_tower.3mf` | 1 h 10 | PLA 220 → 200 °C, PETG 250 → 230 °C, temperature engraved on each block. Pick the block with the best bridge, overhang and surface, least stringing |
| 3 | `03_flow_single_wall.3mf` | 8 min | Vase mode, one wall. Measure the wall (calipers, 4 sides): should be 0.42 mm. Extrusion multiplier = 0.42 / measured |
| 4 | `04_stringing.3mf` | 21 min | 2 pins: hairs between them = more retraction (+0.5 mm, max 7) or −5 °C; blobs = less |
| 5 | `05_xyz_cube.3mf` | 30 min | 20.00 mm each way. X / Y off by the same %: belts / steps; height off: Z; only the bottom wider = elephant foot |
| 6 | `06_tolerance_gauge.3mf` | 1 h 20 | The project's bearing / claw gauge: measure the holes, test the real parts (see `cad/print/tolerance_test/README.md`) |

Do PETG first (it's the robot's material), then PLA.

## Results to send

| | PLA | PETG |
|---|---|---|
| Firmware version (screen › About) | | |
| E-steps: old value / mm remaining | | |
| Best temperature (tower) | | |
| Single-wall thickness (mm, 4 sides) | | |
| Stringing: OK / hairs / blobs | | |
| XYZ cube X / Y / Z (mm) | | |
| Gauge: rod press / slide hole | | |
| Gauge: LM6UU press hole | | |
| Gauge: axle turns-freely hole | | |
| Gauge: horn hub hole | | |
| Gauge: ring 47.25 / post 34.80 (fits?) + caliper sizes | | |

With these numbers the profiles get the right temperature, flow and retraction for each material, and the robot's
hole sizes (`TOL` in `backend/cad/model.py`) get corrected for this printer.
