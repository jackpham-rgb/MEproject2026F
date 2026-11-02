# CAD: Concept A

Only CAD files live here. The code that makes them is in `backend/cad/`.

| Folder | What | Open with |
|---|---|---|
| `step/concept_a_assembly.step` | **The whole robot**, one component per moving group (`grp_fixed`, `grp_turret`, `grp_crank`, `grp_lift`, `grp_wrist`, `grp_finger_L`, `grp_finger_R`, `grp_can`) | SolidWorks, Fusion 360, Onshape, FreeCAD |
| `step/parts/*.step` | Every part on its own (printed and purchased), in assembly position | same |
| `step/fusion_sequence.json` | Joint values of the firmware sequence, read by the Fusion 360 animation script | — |
| `print/stl/*.stl` | **Print-ready parts**, each turned to its best side and placed on the bed | any slicer (Cura, PrusaSlicer, Bambu Studio) |
| `print/print_orientations.png`, `print/print_table.csv` | How each part sits on the bed, supports, time, mass | — |
| `check/check_report.txt` | Motion check: collisions in 289 poses, landing, tip-over, servo loads | text |
| `check/mass_table.csv` | Mass and centre of gravity of every part | Excel |

Units are **millimetres**. The origin is the turntable axis on the table, +Y points to START and
+X to TARGET. The assembly is in its HOME pose: arm at START, lift down, wrist upright, arms open,
Coke can (66.2 × 122.2 mm) at START. 2D drawings: `docs/drawings/`.

## Opening it in SolidWorks

1. **File → Open**, set the file type to **STEP AP203/214/242 (\*.step; \*.stp)**, pick
   `cad/step/concept_a_assembly.step`.
2. When asked, let SolidWorks import it **as an assembly** (each `grp_*` becomes a sub-assembly).
3. **File → Save As** `.SLDASM`. SolidWorks saves every part as its own `.SLDPRT` next to it. Those
   are normal SolidWorks files you can edit.
4. Imported parts have no feature tree (they're solid bodies). To edit one, open its `.SLDPRT` and
   either use **Insert → Features → FeatureWorks → Recognize Features** to rebuild features, or add
   new features on top of the body. A single part can also be opened from `step/parts/`.

Fusion 360 opens the same STEP (**File → Open → Open from my computer**). The script in
`backend/cad/fusion_animate/` plays the firmware sequence on it with an interference check at every
move (written without access to Fusion, so not yet run there).

## SolidWorks mates (to animate it by hand)

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

## Regenerating

The CAD is parametric Python (CadQuery). After changing `backend/cad/model.py`:

```bash
python3.13 backend/cad/export.py       # cad/step/
python3.13 backend/cad/check.py        # cad/check/ (~5 min)
python3.13 backend/cad/print_prep.py   # cad/print/
python3.13 backend/cad/drawings.py     # docs/drawings/
```
