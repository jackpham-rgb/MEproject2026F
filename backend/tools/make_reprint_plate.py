"""Plate R: the parts already printed from the original plate 1 (turret plate, top cap, lift link), as a check
picture and a ready reprint file if one is lost or broken.

    python3.13 backend/tools/make_reprint_plate.py   -> cad/print/plates/plate_R.3mf (+ .stl, .ini, plate_R.png)

STANDARD profile (0.2 mm, 3 walls, 20 %), normal supports from the bed (the turret plate needs them), and a
5 mm brim + solid infill on the tiny lift link only (per-part setting inside the .3mf).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "tools"))
import make_plate_files as F  # noqa: E402
import make_plate_inis as I  # noqa: E402
import print_economy as E  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "plates")
PLATE = [("R  Reprint: turret plate + top cap + lift link", "STANDARD", dict(E.SUP_NORMAL), ["CA-201", "CA-203", "CA-302"], "")]

if __name__ == "__main__":
    I.main(PLATE, OUT)
    F.main((), OUT, PLATE, OUT, {"CA-302_lift_link": {"brim_width": "5", "fill_density": "100%", "fill_pattern": "rectilinear"}})
    lay = E.plate_layout(PLATE[0][3])
    E.render([(t, E.COLOURS[i]) for i, t in enumerate(lay)], os.path.join(OUT, "plate_R.png"), bed=E.PL.BED)
    print("wrote cad/print/plates/plate_R.*")
