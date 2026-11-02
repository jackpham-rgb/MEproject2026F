# Backend: the code behind every file in this repo

Nothing here needs to be opened to use the design: the outputs are already committed in `cad/`,
`docs/`, `EE/`, `sim/` and `viewer/`. Run these only after changing something.

```bash
pip install -r backend/requirements.txt cadquery      # CadQuery needs Python ≥ 3.10
```

| Script | Makes | Run after changing |
|---|---|---|
| `cad/model.py` | (the parametric CAD: every part, tolerances `TOL`, kinematics) | — this is what you edit |
| `cad/export.py` | `cad/step/` (assembly + parts STEP, Fusion sequence), `cad/build/viewer_mesh.json` | the model |
| `cad/check.py` | `cad/check/` (collisions in 289 poses, landing, tip-over, masses, servo loads), ~5 min | the model |
| `cad/print_prep.py` | `cad/print/` (STLs turned to their best bed face, preview, print table) | the model |
| `cad/drawings.py` | `docs/drawings/` (13 dimensioned sheets) | the model |
| `cad/export_claw.py` | `cad/claw/` (claw-only STEP + arm motion file) | the model |
| `cad/fusion_claw/` | Fusion 360 script: close-up claw animation from `cad/claw/claw.step` | — run inside Fusion |
| `cad/fusion_animate/` | Fusion 360 script: plays the firmware sequence on `cad/step/concept_a_assembly.step` | — run inside Fusion |
| `ee/ee_calcs.py` | `EE/out/`, `EE/ltspice/` (signals, current, ngspice runs if installed) | the firmware or the power design |
| `sim/concept_a.py` | `sim/` (lift clearance, grip, loads, plots) | the firmware angles or times |
| `tools/make_tables.py` | `docs/05_bom.md`, `docs/bom.csv`, decision matrices (CSV + xlsx) | the check (masses) |
| `tools/make_build_guide.py` | `docs/08_build_guide.md`, `cad/print/README.md` | the tables, print prep |
| `tools/make_wiring_diagram.py` | `docs/wiring/wiring_diagram.svg` | the wiring |
| `tools/build_detail_viewer.py` | `viewer/concept_a_detail.html` | export + check |
| `tools/build_concepts_viewer.py` | `viewer/concepts.html` | — |
| `tools/make_report.js` | `docs/Engineering_Report_ConceptA.docx` (`node`, uses the `docx` package) | anything in the report |
| `tools/emulate_concept_a.sh` | compiles the firmware and runs it on an emulated Uno (`apt install gcc-avr avr-libc simavr`) | the firmware |

Full rebuild after a CAD change:

```bash
python3 backend/cad/export.py && python3 backend/cad/check.py && python3 backend/cad/print_prep.py && python3 backend/cad/drawings.py
python3 backend/tools/make_tables.py && python3 backend/tools/make_build_guide.py
python3 backend/tools/build_detail_viewer.py && node backend/tools/make_report.js
```
