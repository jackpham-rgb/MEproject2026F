# Concept A detail CAD (STEP / STL)

Everything is described in `docs/03_detail_design.md`. Units are **millimetres**. The origin is
the turntable axis on the table, +Y points to START and +X to TARGET. The model is in its home
pose: arm at START, lift down, wrist upright, arms open, Coke can (66.2 × 122.2 mm) at START.

```bash
python3.13 cad/check.py    # firmware-sequence motion + collision + mass + loads -> out/check_report.txt
python3.13 cad/export.py   # STEP assembly, per-part STEP/STL, viewer + Fusion data
```

- **`model.py`:** every part (printed and purchased), its material, and the kinematics.
  Hole sizes come from the `TOL` table (PETG); servo angles from the firmware (`FW`).
- **`out/concept_a_detail_assembly.step`:** for SolidWorks and Fusion. One component per
  moving group (`grp_fixed`, `grp_turret`, `grp_crank`, `grp_lift`, `grp_wrist`,
  `grp_finger_L`, `grp_finger_R`, `grp_can`).
- **`out/parts/*.stl` / `*.step`:** each part, in assembly position. Print orientations come
  with the print files.
- **`out/check_report.txt`, `out/mass_table.csv`:** the last check run.
- **`fusion_animate/`:** a Fusion 360 script that imports the STEP, plays the firmware
  sequence, and runs interference at every move.

## SolidWorks mates (if you mate the STEP by hand)

| Groups | Mate | Range |
|---|---|---|
| turret ↔ fixed | Concentric on the Z axis | 0 → −90° |
| crank ↔ turret | Concentric on the X line y = −6, z = 150 | −22.5 → +22.5° |
| lift ↔ turret | Slide along Z | 0 → 15.3 mm |
| wrist ↔ lift | Concentric on the Y line x = 0, z = 61.1 | 0 → 180° |
| finger_R / finger_L ↔ wrist | Concentric on the Z lines x = ±8.1, y = 83 | 0 → 75° (gear-coupled) |
| can ↔ wrist | Rigid after GRIP | |

Fix `grp_fixed`, then **Motion Study → Motor** on each joint in the firmware order:
grip → lift → flip → turn → lower → release.
