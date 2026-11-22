"""Reprint of the parts that need accurate fits, with easier supports, walls-over-infill and faster speeds.

    python3.13 backend/tools/make_reprint.py
      -> cad/print/reprint/reprint_1..3.3mf (+ .ini, .stl, .png)  open in PrusaSlicer (Ctrl+O, "Yes"), slice, print

RUN IT AGAIN AFTER `TOL` IN backend/cad/model.py IS CORRECTED FROM THE TOLERANCE GAUGE (and after print_prep.py):
the STLs come from cad/print/stl/, which carry the hole sizes.

Rules (docs/19_reprint_strategy.md, with sources):
  supports  organic ("tree"), from the build plate only, top contact Z distance 0.25 mm, 2 interface layers
  strength  more walls, less infill; nothing at 100 %: the fingers get 5 walls + 30 % gyroid (the teeth are all wall)
  speed     faster perimeters / infill within the stock hotend's PETG flow (8 mm3/s), cubic infill (faster than gyroid)
            where only stiffness matters, 0.28 mm layers on the big base (its pocket accuracy is in X-Y, set by TOL)
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "tools"))
import make_plate_files as F  # noqa: E402
import make_plate_inis as I  # noqa: E402
import print_economy as E  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "reprint")
EASY_SUP = {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1",
            "support_material_style": "organic", "support_material_contact_distance": "0.25",
            "support_material_bottom_contact_distance": "0.25", "support_material_interface_layers": "2",
            "support_material_bottom_interface_layers": "0", "support_material_xy_spacing": "60%",
            "support_material_threshold": "50"}
FAST = {"perimeter_speed": "50", "external_perimeter_speed": "35", "infill_speed": "80", "solid_infill_speed": "50",
        "top_solid_infill_speed": "35", "support_material_speed": "60", "gap_fill_speed": "35", "travel_speed": "150",
        "only_retract_when_crossing_perimeters": "1", "thick_bridges": "1"}

# (name, profile, plate settings, parts, why). The leading digit names the file (reprint_N).
PLATES = [
    ("1  Precision fits: turret plate + top cap + lift link + carriage arm", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-201", "CA-203", "CA-302", "CA-301"],
     "6807 hub, rod holes, LM6UU pockets, pivots: 0.2 mm, 4 walls carry the fits and the screws"),
    ("2  Claw: gripper frame + 2 fingers", "DETAIL",
     {**FAST, **EASY_SUP, "perimeters": "5", "top_solid_layers": "5", "bottom_solid_layers": "5", "fill_density": "30%",
      "fill_pattern": "gyroid", "external_perimeter_speed": "25", "perimeter_speed": "35"},
     ["CA-402", "CA-403", "CA-401"],
     "Gear teeth: slow outer wall, 5 walls (teeth are solid wall), 30 % gyroid inside instead of 100 %"),
    ("3  Base", "DRAFT",
     {**FAST, **EASY_SUP, "perimeters": "3", "fill_density": "12%", "fill_pattern": "cubic"},
     ["CA-101"],
     "6807 pocket: its size is set in X-Y by TOL, so coarse 0.28 mm layers are fine; 3 walls round the pocket"),
]
PER_PART = {"CA-302_lift_link": {"perimeters": "3", "fill_density": "0%", "brim_width": "5"},       # tiny: walls fill it
            "CA-401_gripper_frame": {"perimeters": "4", "fill_density": "20%"},
            "CA-203_top_cap": {"support_material": "0"}}


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f != "README.md":
            os.remove(os.path.join(OUT, f))
    I.main(PLATES, OUT)
    F.main((), OUT, PLATES, OUT, PER_PART)
    for name, prof, over, pns, why in PLATES:
        n = name[0]
        for ext in ("3mf", "ini", "stl"):
            src = os.path.join(OUT, f"plate_{n}.{ext}")
            if os.path.exists(src):
                shutil.move(src, os.path.join(OUT, f"reprint_{n}.{ext}"))
        E.render([(t, E.COLOURS[i % len(E.COLOURS)]) for i, t in enumerate(E.plate_layout(pns))],
                 os.path.join(OUT, f"reprint_{n}.png"), bed=E.PL.BED)
    print("wrote cad/print/reprint/")


if __name__ == "__main__":
    main()
