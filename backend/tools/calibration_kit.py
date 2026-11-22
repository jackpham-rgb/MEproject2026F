"""CR-6 SE tune-up kit, PLA + PETG: printer profiles, machine G-code (PID, e-steps) and test prints in order.

    python3.13 backend/tools/calibration_kit.py
      -> cad/print/calibration/profiles/{PLA,PETG}_cr6se.ini        full PrusaSlicer configs (Ctrl+L)
      -> cad/print/calibration/gcode/*.gcode                         put on the SD card and "print" them
      -> cad/print/calibration/{PLA,PETG}/NN_<test>.3mf               open (Ctrl+O, "Yes"), slice, print
      -> cad/print/calibration/{PLA,PETG}/tolerance_gauge.3mf         the project's tolerance gauge in that material
Guide: docs/18_cr6se_tuneup.md. Every 3MF is test-sliced here (temperature changes checked in the G-code).
"""
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import cadquery as cq
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import plates as PL  # noqa: E402
from model import box, cyl  # noqa: E402

OUT = os.path.join(ROOT, "cad", "print", "calibration")
BASE_INI = os.path.join(ROOT, "cad", "print", "settings", "plates", "plate_A.ini")    # CR-6 SE vendor printer + PETG STANDARD
BED = (230.0, 235.0)

MAT = {   # filament + the few print settings that differ per material (textured PEI, no glue)
    "PLA": dict(filament_type="PLA", temperature="210", first_layer_temperature="215", bed_temperature="60",
                first_layer_bed_temperature="60", min_fan_speed="100", max_fan_speed="100", bridge_fan_speed="100",
                disable_fan_first_layers="1", retract_length="5", retract_speed="45", max_volumetric_speed="11",
                filament_max_volumetric_speed="11", fill_density="20%"),
    "PETG": dict(filament_type="PETG", temperature="235", first_layer_temperature="238", bed_temperature="80",
                 first_layer_bed_temperature="80", min_fan_speed="30", max_fan_speed="50", bridge_fan_speed="100",
                 disable_fan_first_layers="3", retract_length="5", retract_speed="40", max_volumetric_speed="8",
                 filament_max_volumetric_speed="8", fill_density="20%"),
}
TOWER = {"PLA": [220, 215, 210, 205, 200], "PETG": [250, 245, 240, 235, 230]}   # bottom -> top


def read_ini(path):
    d = {}
    for line in open(path, encoding="utf-8"):
        if "=" in line and not line.lstrip().startswith(("#", ";")):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def write_ini(path, d, head):
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "".join(f"{k} = {v}\n" for k, v in d.items()))


def engrave(shape, text, x, y, z, size, depth=0.6, plane="XY"):
    if plane == "XY":
        t = cq.Workplane("XY").workplane(offset=z - depth).text(text, size, depth + 0.4, kind="bold").translate((x, y, 0))
    else:   # front face (normal -Y) at y
        t = cq.Workplane("XZ").workplane(offset=-(y + depth)).text(text, size, depth + 0.4, kind="bold").translate((x, 0, z))
    return shape.cut(t)


# ------------------------------------------------------------------ test models (mm, sitting on z = 0)
def temp_tower(temps):
    """5 slim blocks of 7 mm, temperature engraved on each front, a 10 mm bridge and a 45° overhang per block."""
    s = box(0, 32, 0, 8, 0, 1.0)
    for i, t in enumerate(temps):
        z0 = 1.0 + i * 7
        blk = box(0, 32, 0, 8, z0, z0 + 7).cut(box(13, 23, -1, 9, z0, z0 + 4.5))                # bridge window 10 mm
        wedge = cq.Workplane("XZ").polyline([(25, z0), (32, z0), (32, z0 + 6.5), (31.5, z0 + 6.5)]).close().extrude(-8)
        blk = blk.cut(box(25, 33, -1, 9, z0, z0 + 6.5)).union(wedge)                             # 45° overhang
        blk = engrave(blk, str(t), 1.2, 0, z0 + 1.5, 3.6, depth=0.5, plane="XZ")
        s = s.union(blk)
    return s


def flow_cube():
    return box(0, 20, 0, 20, 0, 12)               # printed in vase mode: one wall, measure its thickness


def first_layer():
    s = None
    for x, y in ((25, 25), (175, 25), (100, 105), (25, 185), (175, 185)):   # 4 corners + centre of the bed
        p = box(x - 15, x + 15, y - 15, y + 15, 0, 0.24)
        s = p if s is None else s.union(p)
    return s


def xyz_cube():
    s = box(0, 20, 0, 20, 0, 20)
    s = engrave(s, "Z", 7, 7, 20, 7)
    s = engrave(s, "X", 7, 0, 7, 7, plane="XZ")
    return s


def stringing():
    s = box(0, 50, 0, 8, 0, 0.8)
    for x in (4, 46):
        s = s.union(cyl(x, 4, 2.5, 0.7, 22))
    return s


# ------------------------------------------------------------------ 3MF with config (+ per-height G-code)
def make_3mf(path, shape, cfg, z_gcode=()):
    v, t = shape.val().tessellate(0.02, 0.1)
    V = np.array([[q.x, q.y, q.z] for q in v])[np.array(t)]
    lo, hi = V.reshape(-1, 3).min(0), V.reshape(-1, 3).max(0)
    if hi[0] - lo[0] > 150 or hi[1] - lo[1] > 150:        # bed-sized objects (first layer test) keep their placement
        V = V - [0, 0, lo[2]]
        V[..., 0] += (BED[0] - 200) / 2
    else:
        V = V - lo
        V[..., 0] += (BED[0] - (hi[0] - lo[0])) / 2
        V[..., 1] += (BED[1] - (hi[1] - lo[1])) / 2
    PL.PER_PART = {}
    name = os.path.splitext(os.path.basename(path))[0]
    PL.write_3mf(path, [(name, V)])
    with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Metadata/Slic3r_PE.config", "; generated by PrusaSlicer 2.7.2\n" + "".join(f"; {k} = {v}\n" for k, v in cfg.items()))
        if z_gcode:
            xml = '<?xml version="1.0" encoding="utf-8"?>\n<custom_gcodes_per_print_z>\n'
            for zz, g in z_gcode:
                xml += f'<code print_z="{zz:.2f}" type="4" extruder="1" color="" extra="{g}" gcode="{g}"/>\n'
            xml += '<mode value="SingleExtruder"/>\n</custom_gcodes_per_print_z>\n'
            z.writestr("Metadata/Prusa_Slicer_custom_gcode_per_print_z.xml", xml)


def slice_check(path):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.gcode")
        subprocess.run(["prusa-slicer", "--export-gcode", "--dont-arrange", "-o", out, path], capture_output=True, timeout=900)
        if not os.path.exists(out):
            return None, []
        txt = open(out, errors="ignore").read()
    m = re.search(r"estimated printing time \(normal mode\) = (.+)", txt)
    return (m.group(1) if m else "?"), re.findall(r"^M104 S(\d+)", txt, re.M)


# ------------------------------------------------------------------ machine G-code (SD card)
def gcode_files():
    d = os.path.join(OUT, "gcode")
    os.makedirs(d, exist_ok=True)
    files = {
        "PID_HOTEND_PLA.gcode": "; PID-tune the hotend at 210 C, fan on (as when printing), save\nM106 S255\nM303 E0 S210 C8 U1\nM500\nM107\nM117 PID saved\n",
        "PID_HOTEND_PETG.gcode": "; PID-tune the hotend at 235 C, part fan 40 %, save\nM106 S100\nM303 E0 S235 C8 U1\nM500\nM107\nM117 PID saved\n",
        "PID_BED.gcode": "; PID-tune the bed at 70 C (between PLA 60 and PETG 80), save\nM303 E-1 S70 C8 U1\nM500\nM117 Bed PID saved\n",
        "ESTEPS_TEST.gcode": ("; E-steps check. Mark the filament 120 mm above the extruder inlet first.\n"
                              "; Heats to 220 C, extrudes 100 mm slowly. Then measure the mark: 20 mm left = correct.\n"
                              "M104 S220\nM109 S220\nM503\nM83\nG1 E100 F100\nM400\nM104 S0\nM117 Measure the mark now\n"),
        "COLD_PULL_HEAT.gcode": "; Heat for a cold pull / nozzle clean (PLA 200 C)\nM104 S200\nM109 S200\nM117 Push filament, then cool to 90 C and pull\n",
    }
    for n, txt in files.items():
        open(os.path.join(d, n), "w").write(txt)
    return list(files)


def main():
    os.makedirs(os.path.join(OUT, "profiles"), exist_ok=True)
    base = read_ini(BASE_INI)
    for k in ("brim_width",):
        base[k] = "0"
    print("gcode:", ", ".join(gcode_files()))
    tests = [("01_first_layer", first_layer(), {}, None),
             ("02_temp_tower", None, {}, "tower"),
             ("03_flow_single_wall", flow_cube(), {"spiral_vase": "1", "perimeters": "1", "top_solid_layers": "0", "fill_density": "0%"}, None),
             ("04_stringing", stringing(), {}, None),
             ("05_xyz_cube", xyz_cube(), {}, None)]
    rows = []
    for mat, m in MAT.items():
        cfg = {**base, **m}
        write_ini(os.path.join(OUT, "profiles", f"{mat}_cr6se.ini"), cfg,
                  f"# Concept A: Creality CR-6 SE, 0.4 mm nozzle, textured PEI (no glue), {mat}. PrusaSlicer: File > Import > Import Config (Ctrl+L).\n")
        d = os.path.join(OUT, mat)
        os.makedirs(d, exist_ok=True)
        for name, shape, over, special in tests:
            zg = ()
            if special == "tower":
                temps = TOWER[mat]
                shape = temp_tower(temps)
                zg = [(1.0 + i * 7 + 0.2, f"M104 S{t}") for i, t in enumerate(temps)]
                over = {"first_layer_temperature": str(temps[0]), "temperature": str(temps[0])}
            p3 = os.path.join(d, f"{name}.3mf")
            make_3mf(p3, shape, {**cfg, **over}, zg)
            t, temps_seen = slice_check(p3)
            rows.append((mat, name, t, temps_seen))
            print(f"{mat:4s} {name:22s} {t}" + (f"  M104: {' '.join(dict.fromkeys(temps_seen))}" if special == "tower" else ""))
        # the project's tolerance gauge in this material
        src = os.path.join(ROOT, "cad", "print", "tolerance_test", "tolerance_gauge.stl")
        if os.path.exists(src):
            V = PL.read_stl(src)
            V = V - V.reshape(-1, 3).min(0)
            V[..., 0] += (BED[0] - np.ptp(V[..., 0])) / 2
            V[..., 1] += (BED[1] - np.ptp(V[..., 1])) / 2
            p3 = os.path.join(d, "06_tolerance_gauge.3mf")
            PL.write_3mf(p3, [("tolerance_gauge", V)])
            quick = {"perimeters": "2", "fill_density": "15%", "top_solid_layers": "3", "bottom_solid_layers": "3"}
            with zipfile.ZipFile(p3, "a", zipfile.ZIP_DEFLATED) as z:
                z.writestr("Metadata/Slic3r_PE.config", "; generated by PrusaSlicer 2.7.2\n" + "".join(f"; {k} = {v}\n" for k, v in {**cfg, **quick}.items()))
            t, _ = slice_check(p3)
            print(f"{mat:4s} 06_tolerance_gauge      {t}")


if __name__ == "__main__":
    main()
