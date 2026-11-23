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
# wide-spaced interface): organic tree from the bed, 0.25 top gap / 0.2 bottom gap
EASY_SUP = {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1",
            "support_material_style": "organic", "support_material_contact_distance": "0.25",
            "support_material_bottom_contact_distance": "0.2", "support_material_interface_layers": "3",
            "support_material_bottom_interface_layers": "2", "support_material_interface_spacing": "0.7",
            "support_material_spacing": "2.5", "support_material_extrusion_width": "0.25",
            "support_material_xy_spacing": "60%", "support_material_threshold": "50"}
BRIM = {"brim_width": "3", "brim_separation": "0.3", "brim_type": "outer_only"}   # outer only, 0.3 gap: peels off
FAST = {"perimeter_speed": "50", "external_perimeter_speed": "35", "infill_speed": "80", "solid_infill_speed": "60",
        "top_solid_infill_speed": "40", "support_material_speed": "60", "gap_fill_speed": "35", "travel_speed": "150",
        "only_retract_when_crossing_perimeters": "1", "thick_bridges": "1"}
FAST_DRAFT = {**FAST, "perimeter_speed": "60", "external_perimeter_speed": "45", "infill_speed": "90"}   # 0.28 mm: keep the draft speeds

# (name, profile, plate settings, parts, why). The leading digit names the file (reprint_N).
PLATES = [
    ("1  Tonight: carriage arm + lift link (LM6UU pockets, pivots)", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-301", "CA-302"],
     "LM6UU pockets 13.0 in CAD (print ~12.0), pivots: 0.2 mm, 4 walls; same speeds/temps as the measured gauge"),
    ("5  Tonight, LONG version (6-7 h of sleep): carriage arm + lift link + turret plate", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-301", "CA-302", "CA-201"],
     "plate 1 + the turret plate in one go: no hand-fixing of the hub / rod holes"),
    ("2  Claw spare: gripper frame + 2 fingers", "DETAIL",
     {**FAST, **EASY_SUP, "perimeters": "5", "top_solid_layers": "5", "bottom_solid_layers": "5", "fill_density": "30%",
      "fill_pattern": "gyroid", "external_perimeter_speed": "25", "perimeter_speed": "35"},
     ["CA-402", "CA-403", "CA-401"],
     "Gear teeth: slow outer wall, 5 walls (teeth are solid wall), 30 % gyroid inside instead of 100 %"),
    ("3  Base: ONLY if sanding the old pocket fails", "DRAFT",
     {**FAST_DRAFT, **EASY_SUP, "perimeters": "3", "fill_density": "12%", "fill_pattern": "cubic",
      "support_material_extrusion_width": "0.34"},   # PrusaSlicer refuses 0.25 at 0.28 mm layers (too thin to print)
     ["CA-101"],
     "6807 pocket 48.0 in CAD (print ~47.05); coarse 0.28 mm layers, 3 walls round the pocket"),
    ("4  Turret plate: ONLY if sanding the hub / drilling the rod holes fails", "STANDARD",
     {**FAST, **EASY_SUP, "perimeters": "4", "fill_density": "15%", "fill_pattern": "cubic"},
     ["CA-201"],
     "hub 34.3 in CAD (print ~34.9), rod holes 7.05 (print ~5.95)"),
]
PER_PART = {"CA-302_lift_link": {"perimeters": "3", "fill_density": "0%", **BRIM},       # tiny: walls fill it
            "CA-401_gripper_frame": {"perimeters": "4", "fill_density": "20%"}}


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
