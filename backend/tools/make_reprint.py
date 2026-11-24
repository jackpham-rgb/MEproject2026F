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
import math
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "tools"))
import make_plate_files as F  # noqa: E402
import make_plate_inis as I  # noqa: E402
import print_economy as E  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "reprint")
# easy-to-remove supports (docs/19; plus the "thin + hollow" guide: support lines ~half the normal width, sparse base,
# spaced interface): organic tree from the bed, 0.2 top / 0.2 bottom gap. Round 2 (after reprint_5's stringy, saggy
# underside): interface 0.7 -> 0.35 mm apart and top gap 0.25 -> 0.2 (flatter underside), support lines 0.25 -> 0.3
EASY_SUP = {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1",
            "support_material_style": "organic", "support_material_contact_distance": "0.2",
            "support_material_bottom_contact_distance": "0.2", "support_material_interface_layers": "3",
            "support_material_bottom_interface_layers": "2", "support_material_interface_spacing": "0.35",
            "support_material_spacing": "2.5", "support_material_extrusion_width": "0.3",
            "support_material_xy_spacing": "60%", "support_material_threshold": "50"}
BRIM = {"brim_width": "3", "brim_separation": "0.3", "brim_type": "outer_only"}   # outer only, 0.3 gap: peels off
FAST = {"perimeter_speed": "50", "external_perimeter_speed": "35", "infill_speed": "80", "solid_infill_speed": "60",
        "top_solid_infill_speed": "40", "support_material_speed": "60", "gap_fill_speed": "35", "travel_speed": "150",
        "only_retract_when_crossing_perimeters": "1", "thick_bridges": "1"}
FAST_DRAFT = {**FAST, "perimeter_speed": "60", "external_perimeter_speed": "45", "infill_speed": "90"}   # 0.28 mm: keep the draft speeds

# (name, profile, plate settings, parts, why). The leading digit names the file (reprint_N).
# base, time-optimised (sliced 2026-11-24): 0.28 mm + 12 % cubic 7 h 22 -> 0.32 mm + lightning 10 % 5 h 45.
# 3 walls kept: at 2 the middle of the 3 mm walls would be left hollow by lightning infill (4 h 33 but weak walls).
# 0.32 mm = 80 % of the 0.4 nozzle (the max); the 8 mm3/s volumetric cap of the stock hotend is in the profile.
BASE_FAST = {"layer_height": "0.32", "support_material_extrusion_width": "0.38", "perimeters": "3",
             "fill_pattern": "lightning", "fill_density": "10%", "top_solid_layers": "3", "bottom_solid_layers": "3"}
PLATES = [   # round 2 (2026-11-24). Round 1 plates 1, 4, 5, 6, 7, 9: archive/reprint_2026-11-23/
    ("3  Base", "DRAFT",
     {**FAST_DRAFT, **EASY_SUP, **BASE_FAST},
     ["CA-101"],
     "time-optimised: 0.32 mm layers, lightning infill (only under top faces), 3 walls = the 3 mm walls print solid"),
    ("8  Gripper frame + right finger", "DETAIL",
     {**FAST, **EASY_SUP, "perimeters": "5", "top_solid_layers": "5", "bottom_solid_layers": "5", "fill_density": "30%",
      "fill_pattern": "gyroid", "external_perimeter_speed": "25", "perimeter_speed": "35"},
     ["CA-402", "CA-401"], "frame with the 16 mm horn opening (screwdriver reaches the horn screws) + right finger"),
    ("a  Carriage arm, on its side (stronger arm)", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-301"], "on its +X side: the arm's layers run along it; teardrop pockets (no support inside), side gussets"),
    ("b  Carriage arm + gripper frame + right finger, one go", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-301", "CA-402", "CA-401"], "a + 8 on one plate, all 0.2 mm; the claw parts keep their settings per part"),
    ("c  Base + carriage arm, one go (base at its own 0.32 mm layers)", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-101", "CA-301"], "3 + a on one plate: the carriage at 0.2 mm (its holes), the base keeps its fast settings per part"),
    ("2  Whole claw: gripper frame + both fingers", "DETAIL",
     {**FAST, **EASY_SUP, "perimeters": "5", "top_solid_layers": "5", "bottom_solid_layers": "5", "fill_density": "30%",
      "fill_pattern": "gyroid", "external_perimeter_speed": "25", "perimeter_speed": "35"},
     ["CA-402", "CA-403", "CA-401"], "only if the left finger is printed again too"),
]
PER_PART = {"CA-301_carriage_arm": {"perimeters": "5", "fill_density": "30%", "fill_pattern": "gyroid"},   # the arm snapped: more walls
            "CA-302_lift_link": {"perimeters": "3", "fill_density": "0%", **BRIM},       # tiny: walls fill it
            "CA-101_base": {**BASE_FAST, "external_perimeter_speed": "45", "perimeter_speed": "60", "infill_speed": "90"},
            "CA-402_finger_R": {"perimeters": "5", "top_solid_layers": "5", "bottom_solid_layers": "5", "fill_density": "30%",
                                "fill_pattern": "gyroid", "external_perimeter_speed": "25", "perimeter_speed": "35"},
            "CA-401_gripper_frame": {"perimeters": "4", "fill_density": "20%", "external_perimeter_speed": "25", "perimeter_speed": "35"},
            "CA-403_finger_L": {"perimeters": "5", "top_solid_layers": "5", "bottom_solid_layers": "5", "fill_density": "30%",
                                "fill_pattern": "gyroid", "external_perimeter_speed": "25", "perimeter_speed": "35"}}


def stability():
    """Every reprint part, every way it can lie on the bed: contact area, height, tip ratio. The orientation used is
    print_prep's choice (stable footprint first, then press fits vertical, then least overhang). Parts that sit on a
    small area or stand tall for their footprint get a 5 mm brim. Writes cad/print/reprint/STABILITY.md."""
    sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
    import drawings as D
    import model as M
    import print_prep as PP
    import csv
    chosen = {r["part_no"]: r["bed_face"] for r in csv.DictReader(open(os.path.join(ROOT, "cad", "print", "print_table.csv")))}
    parts = {p["name"]: p for p in M.build_parts()}
    pn_of = {v[0]: k for k, v in D.PN.items()}
    lines = ["# Bed stability of the reprint parts", "",
             "Contact = flat area touching the bed. Tip ratio = height / √contact (above ~2.5 a part can rock or get knocked",
             "over by the nozzle). Overhang = flat area printed in the air (needs support). The chosen side is the one in the STL.", ""]
    brims = {}
    for _, _, _, pns, _ in PLATES:
        for pn in pns:
            nm = pn_of[pn]
            lines += [f"## {pn} {D.PN[nm][1]}", "", "| Side on the bed | Contact (mm²) | Height (mm) | Tip ratio | Overhang (mm²) | Press fits vertical | |",
                      "|---|---:|---:|---:|---:|---|---|"]
            for label, rot in PP.CANDIDATES.items():
                e = PP.evaluate(PP.orient(parts[nm]["shape"].val(), rot), nm)
                tip = e["h"] / math.sqrt(max(e["contact"], 1))
                use = label == chosen.get(pn)
                lines.append(f"| {label} | {e['contact']:.0f} | {e['h']:.0f} | {tip:.1f} | {e['overhang']:.0f} | {e['press_v']} of {e['press_all']} | {'**used**' if use else ''} |")
                if use and (e["contact"] < 300 or tip > 2.5):
                    brims[f"{pn}_{nm}"] = f"contact {e['contact']:.0f} mm², tip {tip:.1f}"
            lines.append("")
    lines += ["## Brims added", ""] + ([f"- {k}: {v} → 3 mm brim (0.3 mm gap)" for k, v in brims.items()] or ["- none needed"]) + [""]
    open(os.path.join(OUT, "STABILITY.md"), "w").write("\n".join(lines))
    return brims


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f != "README.md":
            os.remove(os.path.join(OUT, f))
    brims = stability()
    per_part = {k: dict(v) for k, v in PER_PART.items()}
    for k in brims:
        per_part.setdefault(k, {}).update(BRIM)
    I.main(PLATES, OUT)
    F.main((), OUT, PLATES, OUT, per_part)
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
