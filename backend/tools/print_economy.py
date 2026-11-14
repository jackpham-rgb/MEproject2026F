"""Economy printing, set up BY HAND in any slicer (Cura, Creality Print, PrusaSlicer, Orca): no .ini, no edited 3D files.

    python3.13 backend/tools/print_economy.py
      -> docs/16_print_economy.md                 (the guide; the assembly manual's PART P pages use it)
      -> cad/print/settings/economy_plates.csv     (plate, parts, settings, time, grams)

The parts are grouped so that every plate uses ONE profile for the whole plate (layer height, walls,
infill, speeds, supports): you type one set of numbers per plate, nothing per part. The STLs are the
unchanged files in cad/print/stl/ (already turned to their best side).

Times and grams are real PrusaSlicer slices of each plate (the project's printer profile is only used
here to estimate; you don't need it), compared with the old one-setting-for-everything plates.
"""
import csv
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import plates as PL  # noqa: E402

INI = os.path.join(ROOT, "cad", "print", "settings", "concept_a_PETG_prusaslicer.ini")
STL = os.path.join(ROOT, "cad", "print", "stl")
DOC = os.path.join(ROOT, "docs", "16_print_economy.md")
CSV = os.path.join(ROOT, "cad", "print", "settings", "economy_plates.csv")
DENSITY, AREA = 1.27, np.pi * 1.75 ** 2 / 4          # PETG g/cm3, mm2 of 1.75 mm filament

# Same on every plate (type these once in your slicer's PETG profile)
COMMON = [
    ("Nozzle temperature", "235 °C (first layer 238 °C, never above 240 °C: PTFE-lined hotend)"),
    ("Bed temperature", "80 °C, thin glue stick on the glass"),
    ("First layer", "0.24 mm high, 20 mm/s"),
    ("Line width", "0.42 mm (0.4 mm nozzle)"),
    ("Cooling fan", "30 %, off for the first 3 layers"),
    ("Retraction", "5 mm at 40 mm/s (Bowden)"),
    ("Solid / top infill speed", "40 / 30 mm/s"),
    ("Travel speed", "150 mm/s"),
    ("Max flow", "keep under 8 mm³/s (stock CR-6 SE hotend): the speeds below already do"),
    ("Elephant-foot compensation", "0.15 mm (Cura: initial layer horizontal expansion −0.15)"),
    ("Seam", "rear / aligned"),
    ("Skirt", "2 loops (unless the plate says brim)"),
]

PROFILES = {
    "DRAFT": dict(layer_height="0.28", perimeters="2", top_solid_layers="3", bottom_solid_layers="3", fill_density="10%",
                  fill_pattern="grid", external_perimeter_speed="45", perimeter_speed="60", infill_speed="90"),
    "STANDARD": dict(layer_height="0.2", perimeters="3", top_solid_layers="4", bottom_solid_layers="4", fill_density="20%",
                     fill_pattern="gyroid", external_perimeter_speed="35", perimeter_speed="50", infill_speed="70"),
    "DETAIL": dict(layer_height="0.2", perimeters="4", top_solid_layers="5", bottom_solid_layers="5", fill_density="100%",
                   fill_pattern="rectilinear", external_perimeter_speed="25", perimeter_speed="35", infill_speed="50",
                   small_perimeter_speed="15"),
}
SPEED_GLOBAL = {"solid_infill_speed": "40", "top_solid_infill_speed": "30", "gap_fill_speed": "30", "max_volumetric_speed": "8"}
SUP = {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1"}

# Hand plates: one profile per plate. (name, profile, plate overrides, parts, why)
PLATES = [
    ("A  Coupon + lift link", "STANDARD", {"brim_width": "5"}, ["CA-900", "CA-302"],
     "First: the coupon checks every fit; the tiny link rides along and gets the brim it needs"),
    ("B  Base + spine + top cap", "DRAFT", {"perimeters": "3", "fill_density": "12%", **SUP}, ["CA-101", "CA-202", "CA-203"],
     "Big, hidden, lightly loaded. 3 walls so the screw holes and the bearing pocket stay strong"),
    ("C  Electronics tray", "DRAFT", {}, ["CA-102"],
     "Nothing precise on it: the fastest settings"),
    ("D  Turret plate + carriage arm", "STANDARD", dict(SUP), ["CA-201", "CA-301"],
     "Press fits (bearing hub, rods, LM6UU) and the parts that carry the lift"),
    ("E  Claw: 2 fingers + gripper frame", "DETAIL", dict(SUP), ["CA-402", "CA-403", "CA-401"],
     "Gear teeth and the gear spacing: slow outer walls, solid"),
]

# part: (must be accurate, can be rough, fix-up after printing)
PARTS = {
    "CA-900": ("it tests the fits", "-", "Check each hole as in the build guide, section 2: it tells you how much to sand the real parts"),
    "CA-302": ("the 2 holes", "-", "Peel the brim. Pivot screw binds: open the hole with a 5/32 in (4 mm) drill turned by hand"),
    "CA-101": ("6807 bearing pocket (47.1 mm), MG996R screw holes", "everything else: layer lines, rough sides, sag in the pockets",
               "Bearing tight: sand the pocket wall (120 grit on a finger) until it presses in with thumbs. Loose: one layer of tape. "
               "Clear support bits out of the servo pocket with pliers"),
    "CA-202": ("lift-servo screw holes, screw holes at the ends", "faces and edges",
               "Run each screw in once and back out before final assembly"),
    "CA-203": ("2 blind rod holes (6.0 mm)", "everything else", "Rod won't go in: drill 6 mm, 8 mm deep (tape flag on the bit)"),
    "CA-102": ("nothing critical: board pegs, 2 screw tabs", "everything",
               "Peg too fat for a board hole: shave it with a knife. Snapped peg: a dab of hot glue holds the board"),
    "CA-201": ("hub into the bearing (34.95 mm), 2 rod holes (6.0 mm), horn screw holes", "top face and edges",
               "Hub tight: sand it evenly, turning it. Rod holes tight: drill 6 mm (or 15/64 in) by hand"),
    "CA-301": ("4 LM6UU pockets (12.15 mm) in line, wrist-servo screws, link pivot", "arm faces",
               "Pockets print on their side, so the top of each droops: ream with a 12 mm drill or sandpaper on a 12 mm dowel / marker "
               "until the LM6UU presses in; the carriage must slide down both rods by its own weight"),
    "CA-402": ("gear teeth, axle bore 3.9 mm", "pad back face (gets the silicone sheet)",
               "Remove supports, file only the pad area, never the teeth. Bore tight: twist a 5/32 in drill through by hand"),
    "CA-403": ("gear teeth, servo-spline socket", "pad back face",
               "Spline socket tight: scrape lightly inside with the knife tip, test the SG90 spline after every pass. Never file the teeth"),
    "CA-401": ("gear axle hole and servo position: they set the gear mesh", "flange faces",
               "Don't open the axle hole more than needed: the gears must mesh without play"),
}


def slice_plate(paths, extra):
    """Slice the given STLs together (auto-arranged on the bed). Returns (hours, grams)."""
    with tempfile.TemporaryDirectory() as d:
        ini = os.path.join(d, "x.ini")
        with open(ini, "w") as f:
            f.write("".join(f"{k} = {v}\n" for k, v in extra.items()))
        out = os.path.join(d, "o.gcode")
        r = subprocess.run(["prusa-slicer", "--export-gcode", "--load", INI, "--load", ini, "-o", out] + (["--merge"] if len(paths) > 1 else []) + paths,
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.exists(out):
            raise SystemExit(f"slice failed for {paths}: {(r.stdout + r.stderr)[-400:]}")
        txt = open(out, errors="ignore").read()
    m = re.search(r"estimated printing time \(normal mode\) = (.+)", txt)
    secs = sum(int(v) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[u] for v, u in re.findall(r"(\d+)([dhms])", m.group(1)))
    mm = float(re.search(r"filament used \[mm\] = ([\d.]+)", txt).group(1))
    return secs / 3600, mm * AREA / 1000 * DENSITY


def stl_of(pn):
    return os.path.join(STL, next(f for f in os.listdir(STL) if f.startswith(pn)))


def fits(pns):
    sizes = {}
    for pn in pns:
        t = PL.read_stl(stl_of(pn)).reshape(-1, 3)
        sizes[pn] = tuple(np.ptp(t, 0)[:2])
    return PL.pack(sizes) is not None


def fmt_h(h):
    return f"{int(h)} h {round((h % 1) * 60):02d}" if h >= 1 else f"{round(h * 60)} min"


def main():
    names = {r["part_no"]: r["part"] for r in csv.DictReader(open(os.path.join(PL.PR, "print_table.csv")))}
    # before: the old plates' settings (one setting for everything + per-part supports / solid fingers / brim from plates.py)
    before_h = before_g = 0.0
    for stem, title, pns, when in PL.PLATES[:4]:
        for pn in pns:
            o = dict(PL.PER_PART.get(pn, {}))
            if o.get("fill_density") == "100%":
                o["fill_pattern"] = "rectilinear"
            h, g = slice_plate([stl_of(pn)], o)
            before_h, before_g = before_h + h, before_g + g
    rows = []
    for name, prof, over, pns, why in PLATES:
        if not fits(pns):
            raise SystemExit(f"plate {name}: parts don't fit the 235 x 235 bed")
        s = {**PROFILES[prof], **SPEED_GLOBAL, **over}
        if s["fill_density"] == "100%":
            s["fill_pattern"] = "rectilinear"
        h, g = slice_plate([stl_of(pn) for pn in pns], s)
        rows.append(dict(name=name, prof=prof, pns=pns, why=why, s=s, h=h, g=g))
        print(f"{name:36s} {prof:8s} {h:5.2f} h {g:5.0f} g")
    T1, G1 = sum(r["h"] for r in rows), sum(r["g"] for r in rows)
    print(f"before {before_h:.1f} h {before_g:.0f} g -> after {T1:.1f} h {G1:.0f} g")
    with open(CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["plate", "profile", "parts", "layer_mm", "walls", "infill", "supports", "brim_mm", "hours", "grams"])
        for r in rows:
            s = r["s"]
            w.writerow([r["name"], r["prof"], " ".join(r["pns"]), s["layer_height"], s["perimeters"], s["fill_density"],
                        "yes" if s.get("support_material") == "1" else "no", s.get("brim_width", "0"), f"{r['h']:.2f}", f"{r['g']:.0f}"])
    write_doc(rows, names, before_h, before_g)
    print("wrote docs/16_print_economy.md + cad/print/settings/economy_plates.csv")


def write_doc(rows, names, T0, G0):
    T1, G1 = sum(r["h"] for r in rows), sum(r["g"] for r in rows)
    L = []
    a = L.append
    a("# Economy printing: only the quality each part needs (set up by hand)\n")
    a("Not every part needs the same settings. The base is a big hidden box: coarse layers and low infill are fine. "
      "The finger gears must mesh: they get slow, accurate outer walls. We accept small flaws on the rough parts and fix "
      "the few fits that matter with sandpaper, a drill or a knife (fix-up table at the end).\n")
    a("**No settings file and no changed 3D files:** import the unchanged STLs from `cad/print/stl/` (already turned to "
      "their best side: don't rotate them, except flat on the bed) and type the numbers below into your slicer. "
      "The parts are grouped so that **each plate uses one setting for the whole plate**: nothing to set per part.\n")
    a(f"**Result (every plate sliced): {fmt_h(T0)} → {fmt_h(T1)} of printing (−{100 * (1 - T1 / T0):.0f} %), "
      f"{G0:.0f} g → {G1:.0f} g of PETG (−{100 * (1 - G1 / G0):.0f} %).** Less heating time = less energy.\n")
    a("## Same on every plate\n")
    a("| Setting | Value |")
    a("|---|---|")
    for k, v in COMMON:
        a(f"| {k} | {v} |")
    a("")
    a("## The plates\n")
    a("| Plate | Parts (STL in cad/print/stl) | Layer | Walls | Top / bottom | Infill | Speeds outer / inner / infill (mm/s) | Supports | Adhesion | Time | PETG |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        s = r["s"]
        parts = ", ".join(f"{pn} {names[pn]}" for pn in r["pns"])
        sup = "**on**, touching build plate only" if s.get("support_material") == "1" else "off"
        adh = f"**brim {s['brim_width']} mm**" if s.get("brim_width") else "skirt"
        pat = {"grid": "grid", "gyroid": "gyroid", "rectilinear": "lines"}[s["fill_pattern"]]
        a(f"| **{r['name']}** ({r['prof']}) | {parts} | {s['layer_height']} mm | {s['perimeters']} | {s['top_solid_layers']} / "
          f"{s['bottom_solid_layers']} | {s['fill_density']} {pat} | {s['external_perimeter_speed']} / {s['perimeter_speed']} / "
          f"{s['infill_speed']} | {sup} | {adh} | {fmt_h(r['h'])} | {r['g']:.0f} g |")
    a(f"| **Total** | | | | | | | | | **{fmt_h(T1)}** | **{G1:.0f} g** |\n")
    a("Print in this order (A first). Every plate fits the 235 × 235 mm bed; leave ~15 mm between parts for the supports.\n")
    a("## Why each plate gets its profile\n")
    a("| Plate | Why |")
    a("|---|---|")
    for r in rows:
        a(f"| {r['name']} | {r['why']} |")
    a("")
    a("**Why not a finer layer on the gears?** The fingers print flat, so the tooth shape is drawn by the nozzle sideways "
      "(X–Y); a thinner layer only adds time. What makes the teeth accurate is a slow outer wall, so DETAIL slows that down.\n")
    a("**Slicer names:** walls = Cura \"Wall Line Count\" / Prusa \"Perimeters\"; top / bottom = \"Top / Bottom Layers\" / "
      "\"Solid layers\"; outer wall speed = \"Outer Wall Speed\" / \"External perimeters\"; supports touching build plate = "
      "\"Support Placement: Touching Buildplate\" / \"Support on build plate only\".\n")
    a("## Per part: what must be accurate\n")
    a("| Part | Must be accurate | Can be rough |")
    a("|---|---|---|")
    for r in rows:
        for pn in r["pns"]:
            a(f"| {pn} {names[pn]} | {PARTS[pn][0]} | {PARTS[pn][1]} |")
    a("")
    a("## Fix-up after printing (sandpaper, drill, knife)\n")
    a("Tools: sandpaper 120 + 240 grit, a 6 mm and a 5/32 in (4 mm) drill bit turned by hand, a 12 mm dowel or marker "
      "wrapped in sandpaper, a craft knife, flush cutters / pliers for supports.\n")
    a("| Part | Fix |")
    a("|---|---|")
    for r in rows:
        for pn in r["pns"]:
            a(f"| {pn} {names[pn]} | {PARTS[pn][2]} |")
    a("\n**Rules:** sand a press fit a little at a time and test after every few strokes (you can't add plastic back; "
      "if it gets loose, one layer of tape or a drop of CA glue). Never sand or file gear teeth. Coarse draft layers can make "
      "holes come out a little tight: expect more sanding / drilling on plates B and C. A part that cracks at a screw: the "
      "screw was forced: drill the hole one size bigger, use the next screw size or hot glue.\n")
    a("Regenerate (re-slices every plate): `python3.13 backend/tools/print_economy.py`.\n")
    with open(DOC, "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
