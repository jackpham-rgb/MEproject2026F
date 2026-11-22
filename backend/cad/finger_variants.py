"""Finger pairs with thinner / thicker gear teeth, for when the printed gears mesh too tight or too loose.

    python3.13 backend/cad/finger_variants.py   -> cad/print/stl/finger_variants/*.stl (+ README.md)

gear_thin (model.py P) = how much thinner each tooth is than a perfect involute tooth, at the pitch circle
(mm). The design uses 0.10. Printers usually make teeth a little fat, so the looser pairs are the usual fix.
Same orientation as the main STLs (flat, as modelled). Print BOTH fingers of the same variant.
"""
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import print_prep as PP  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "stl", "finger_variants")
# tip thickness at the tooth tip (involute math, m1 z16 x0.1): 0.00 -> 0.62, 0.10 -> 0.51, 0.18 -> 0.42, 0.25 -> 0.34 mm.
# Beyond ~0.25 the tips get thinner than the 0.4 mm nozzle line and print rounded / missing: don't go further.
VARIANTS = [(0.00, "tighter", "gears rattle / have visible play with the standard pair"),
            (0.18, "looser", "standard pair binds or needs force to turn"),
            (0.25, "loosest", "the looser pair still binds (tips print a bit rounded: fine)")]


def main():
    os.makedirs(OUT, exist_ok=True)
    std = M.P["gear_thin"]
    rows = []
    for thin, tag, when in VARIANTS:
        M.P["gear_thin"] = thin
        parts = {p["name"]: p for p in M.build_parts()}
        for nm, pn in (("finger_R", "CA-402"), ("finger_L", "CA-403")):
            s = PP.orient(parts[nm]["shape"].val(), None)
            f = f"{pn}_{nm}_{tag}_thin{thin:.2f}.stl"
            cq.exporters.export(cq.Workplane("XY").add(s), os.path.join(OUT, f), tolerance=0.02, angularTolerance=0.1)
            rows.append((tag, thin, f, when))
            print("wrote", f)
    M.P["gear_thin"] = std
    with open(os.path.join(OUT, "README.md"), "w") as fh:
        fh.write("# Finger gear variants\n\nThe gears on the two fingers must mesh with a little play over the whole swing. "
                 "3D printers rarely print teeth exactly, so instead of sanding the teeth (never do that), print the pair that fits.\n\n"
                 f"Standard pair (in `../`): gear_thin = {std:.2f} mm. **Print both fingers of the same variant.**\n\n"
                 "| Variant | gear_thin (mm) | Files | Print it when |\n|---|---|---|---|\n")
        for tag in dict.fromkeys(r[0] for r in rows):
            rs = [r for r in rows if r[0] == tag]
            fh.write(f"| {tag} | {rs[0][1]:.2f} | `{rs[0][2]}`, `{rs[1][2]}` | {rs[0][3]} |\n")
        fh.write("\nTest: hold the frame, turn the left finger by hand. Both fingers should swing together smoothly, with a small click of play "
                 "when you reverse, and no tight spot anywhere in the 75° swing.\n\n"
                 "Edit it yourself: `gear_thin` in `backend/cad/model.py` (P), then `python3.13 backend/cad/finger_variants.py` "
                 "or the full print_prep. +0.05 mm = a little looser. Don't go above 0.25: the tooth tips get thinner than the nozzle line.\n")


if __name__ == "__main__":
    main()
