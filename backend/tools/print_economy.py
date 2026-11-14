"""Economy printing: each part gets only the quality it needs (draft / standard / detail).

    python3.13 backend/tools/print_economy.py
      -> cad/print/plates_eco/*.3mf           (same plates, per-part economy settings inside: open and slice)
      -> cad/print/plates_eco/economy.csv      (per part: profile, time and filament, before vs after)
      -> docs/16_print_economy.md              (the guide; the assembly manual's PART P page uses the same data)

Every time and gram is a real PrusaSlicer slice of the part's STL with cad/print/settings/
concept_a_PETG_prusaslicer.ini (the "before") and with the economy overrides (the "after").
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import plates as PL  # noqa: E402

BEFORE = dict(PL.PER_PART)          # the current plates' per-part settings = the "before"

INI = os.path.join(ROOT, "cad", "print", "settings", "concept_a_PETG_prusaslicer.ini")
STL = os.path.join(ROOT, "cad", "print", "stl")
OUT = os.path.join(ROOT, "cad", "print", "plates_eco")
DOC = os.path.join(ROOT, "docs", "16_print_economy.md")
DENSITY = 1.27                    # PETG g/cm3
AREA = np.pi * 1.75 ** 2 / 4      # mm2 of 1.75 mm filament

# Whole-print speed limits for every profile (the CR-6 SE's stock Bowden hotend melts PETG at ~8 mm3/s)
GLOBAL = {"max_volumetric_speed": "8", "solid_infill_speed": "40", "top_solid_infill_speed": "30", "gap_fill_speed": "30"}

# Profiles = per-object PrusaSlicer settings
PROFILES = {
    "DRAFT": dict(label="Draft (fast, coarse)", layer_height="0.28", perimeters="2", top_solid_layers="3", bottom_solid_layers="3",
                  fill_density="10%", fill_pattern="grid", perimeter_speed="60", external_perimeter_speed="45", infill_speed="90"),
    "STANDARD": dict(label="Standard", layer_height="0.2", perimeters="3", top_solid_layers="4", bottom_solid_layers="4",
                     fill_density="20%", fill_pattern="gyroid", perimeter_speed="50", external_perimeter_speed="35", infill_speed="70"),
    "DETAIL": dict(label="Detail (slow outer walls)", layer_height="0.2", perimeters="4", top_solid_layers="5", bottom_solid_layers="5",
                   fill_density="100%", fill_pattern="rectilinear", perimeter_speed="35", external_perimeter_speed="25", infill_speed="50",
                   small_perimeter_speed="15"),
}
SUPPORT = {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1"}

# part -> (profile, overrides, what must be accurate, what can be rough, fix-up after printing)
PARTS = {
    "CA-101": ("DRAFT", {"perimeters": "3", **SUPPORT},
               "6807 bearing pocket (47.1 mm), MG996R screw holes",
               "everything else: it is a box. Layer lines, rough sides, small sag in the pockets",
               "Bearing tight: sand the pocket wall (120 grit on a finger) until it presses in with thumbs. "
               "Loose: one layer of tape. Clear support bits out of the servo pocket with pliers"),
    "CA-102": ("DRAFT", {},
               "nothing critical: board pegs and 2 screw tabs",
               "everything",
               "Pegs too fat for the Uno / buck holes: twist the board on, or shave a peg with a knife. "
               "Snapped peg: a dab of hot glue holds the board"),
    "CA-201": ("STANDARD", dict(SUPPORT),
               "hub into the bearing bore (34.95 mm), 2 rod holes (6.0 mm), horn screw holes",
               "the plate's top face and edges",
               "Hub tight in the bearing: sand the hub evenly, turning it. Rod holes tight: drill 6 mm (or a 15/64 in bit) by hand"),
    "CA-202": ("DRAFT", {"perimeters": "3", "fill_density": "15%"},
               "lift-servo screw holes, 2 screw holes at each end",
               "faces and edges",
               "Servo screws: run each screw in once and back out before final assembly"),
    "CA-203": ("DRAFT", {"fill_density": "15%"},
               "2 blind rod holes (6.0 mm)",
               "everything else",
               "Rod won't go in: drill 6 mm, 8 mm deep (tape flag on the bit)"),
    "CA-301": ("STANDARD", dict(SUPPORT),
               "4 LM6UU pockets (12.15 mm) in line, wrist-servo screws, link pivot hole",
               "arm faces",
               "Pockets print on their side, so their top droops: ream with 12 mm drill or sandpaper on a 12 mm dowel / marker until "
               "the LM6UU presses in; check the carriage slides down both rods by its own weight"),
    "CA-302": ("STANDARD", {"fill_density": "100%", "fill_pattern": "rectilinear", "brim_width": "5"},
               "the 2 holes",
               "-",
               "Tiny part: peel the brim, open the pivot hole with a 5/32 in (4 mm) drill if the screw binds"),
    "CA-401": ("STANDARD", {"fill_density": "30%", "external_perimeter_speed": "25", "perimeters": "4"},
               "gear axle hole and servo position: they set the gear mesh",
               "flange faces",
               "Don't open the axle hole more than needed: the gears must mesh without play"),
    "CA-402": ("DETAIL", dict(SUPPORT),
               "gear teeth, axle bore 3.9 mm",
               "pad back face (it gets the silicone sheet)",
               "Remove supports, then file only the pad area; never the teeth. Bore tight: twist a 5/32 in drill through by hand"),
    "CA-403": ("DETAIL", dict(SUPPORT),
               "gear teeth, servo-spline socket",
               "pad back face",
               "Spline socket tight: scrape lightly inside with the knife tip, test the SG90 spline after every pass. Never file the teeth"),
    "CA-900": ("STANDARD", {},
               "it is the test of the fits: print it with the STANDARD profile",
               "-",
               "Coarse (draft) layers can make holes come out slightly tight: expect a bit more sanding / drilling on draft parts"),
}
WHY = {
    "DRAFT": "big, hidden, lightly loaded: coarse layers, 2–3 walls, 10–15 % infill, faster speeds",
    "STANDARD": "has press fits or carries a load: 0.2 mm, 3 walls, 20 % infill",
    "DETAIL": "gear teeth: slow outer walls for an accurate tooth shape, solid",
}


def slice_time(paths, extra=None, cwd=None):
    """Slice with the project ini (+ extra overrides). Returns (hours, grams, ok)."""
    with tempfile.TemporaryDirectory() as d:
        cmd = ["prusa-slicer", "--export-gcode", "--load", INI]
        if extra:
            ini = os.path.join(d, "extra.ini")
            with open(ini, "w") as f:
                f.write("".join(f"{k} = {v}\n" for k, v in extra.items()))
            cmd += ["--load", ini]
        out = os.path.join(d, "o.gcode")
        cmd += ["-o", out] + paths
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0 or not os.path.exists(out):
            return None, None, (r.stdout + r.stderr)[-400:]
        txt = open(out, errors="ignore").read()
    m = re.search(r"estimated printing time \(normal mode\) = (.+)", txt)
    secs = 0
    for v, u in re.findall(r"(\d+)([dhms])", m.group(1)):
        secs += int(v) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[u]
    mm = float(re.search(r"filament used \[mm\] = ([\d.]+)", txt).group(1))
    return secs / 3600, mm * AREA / 1000 * DENSITY, True


def part_settings(pn):
    prof, over, *_ = PARTS[pn]
    s = {k: v for k, v in PROFILES[prof].items() if k != "label"}
    s.update(over)
    return s


def stl_of(pn):
    return os.path.join(STL, next(f for f in os.listdir(STL) if f.startswith(pn)))


def build_plates():
    """Same plates as backend/cad/plates.py, economy per-part settings inside."""
    os.makedirs(OUT, exist_ok=True)
    rows = {r["part_no"]: r for r in csv.DictReader(open(os.path.join(PL.PR, "print_table.csv")))}
    PL.PER_PART = {pn: part_settings(pn) for pn in PARTS}
    res = []
    for stem, title, pns, when in PL.PLATES:
        tris, sizes = {}, {}
        for pn in pns:
            t = PL.read_stl(os.path.join(ROOT, rows[pn]["file"]))
            lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
            tris[pn], sizes[pn] = t - lo, (hi[0] - lo[0], hi[1] - lo[1])
        place = PL.pack(sizes)
        objs = []
        for pn in pns:
            x, y, rot = place[pn]
            t = tris[pn].copy()
            if rot:
                t = np.stack([-t[..., 1], t[..., 0], t[..., 2]], axis=-1)
                t[..., 0] += sizes[pn][1]
            t[..., 0] += x
            t[..., 1] += y
            objs.append((f"{pn} {rows[pn]['part']}", t))
        path = os.path.join(OUT, stem + "_eco.3mf")
        PL.write_3mf(path, objs)
        h, g, ok = slice_time([path], GLOBAL)
        h0 = sum(float(rows[pn]["est_time_h"]) for pn in pns)
        res.append((stem, title, pns, h, g, ok))
        print(f"{stem + '_eco':22s} " + (f"{h:5.1f} h {g:5.0f} g" if h else f"SLICE FAILED: {ok}"))
    return res


def fmt_h(h):
    return f"{int(h)} h {round((h % 1) * 60):02d}" if h >= 1 else f"{round(h * 60)} min"


def main():
    names = {r["part_no"]: r["part"] for r in csv.DictReader(open(os.path.join(PL.PR, "print_table.csv")))}
    rows = []
    for pn in PARTS:
        before = dict(BEFORE.get(pn, {}))
        if before.get("fill_density") == "100%":
            before["fill_pattern"] = "rectilinear"                  # gyroid can't do 100 %
        h0, g0, _ = slice_time([stl_of(pn)], before or None)
        h1, g1, ok = slice_time([stl_of(pn)], {**GLOBAL, **part_settings(pn)})
        if h1 is None:
            raise SystemExit(f"{pn}: slice failed: {ok}")
        rows.append(dict(pn=pn, name=names[pn], profile=PARTS[pn][0], h0=h0, g0=g0, h1=h1, g1=g1))
        print(f"{pn} {PARTS[pn][0]:8s} {h0:5.2f} h {g0:5.1f} g  ->  {h1:5.2f} h {g1:5.1f} g")
    plates = build_plates()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "economy.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["part_no", "part", "profile", "settings", "before_h", "before_g", "after_h", "after_g", "accurate", "rough_ok", "fix"])
        for r in rows:
            p = PARTS[r["pn"]]
            w.writerow([r["pn"], r["name"], r["profile"], json.dumps(part_settings(r["pn"])), f"{r['h0']:.2f}", f"{r['g0']:.1f}",
                        f"{r['h1']:.2f}", f"{r['g1']:.1f}", p[2], p[3], p[4]])
    write_doc(rows, plates)
    print("wrote cad/print/plates_eco/ + docs/16_print_economy.md")


def write_doc(rows, plates):
    T0, G0 = sum(r["h0"] for r in rows), sum(r["g0"] for r in rows)
    T1, G1 = sum(r["h1"] for r in rows), sum(r["g1"] for r in rows)
    L = []
    a = L.append
    a("# Economy printing: only the quality each part needs\n")
    a("Not every part needs the same settings. The base is a big hidden box: coarse layers and 10 % infill are fine. "
      "The finger gears must mesh: they get slow, accurate outer walls. We accept small flaws on the rough parts and fix "
      "the few fits that matter with sandpaper, a drill or a knife (the fix-up table below).\n")
    a(f"**Result (sliced in PrusaSlicer, every part): {fmt_h(T0)} → {fmt_h(T1)} of printing "
      f"(−{100 * (1 - T1 / T0):.0f} %), {G0:.0f} g → {G1:.0f} g of PETG (−{100 * (1 - G1 / G0):.0f} %).** "
      "Less heating time = less energy.\n")
    a("## The three profiles\n")
    a("| Profile | Layer | Walls | Top / bottom | Infill | Speeds (outer / inner / infill, mm/s) | For |")
    a("|---|---|---|---|---|---|---|")
    for k, p in PROFILES.items():
        a(f"| **{k}** | {p['layer_height']} mm | {p['perimeters']} | {p['top_solid_layers']} / {p['bottom_solid_layers']} | "
          f"{p['fill_density']} {p['fill_pattern']} | {p['external_perimeter_speed']} / {p['perimeter_speed']} / {p['infill_speed']} | {WHY[k]} |")
    a("\nEverything else stays as in `concept_a_PETG_prusaslicer.ini` (235 °C, bed 80 °C, glue stick, retraction 5 mm). "
      "Solid infill 40, top 30 mm/s, and a cap of 8 mm³/s (the most PETG the CR-6 SE's stock hotend melts): above that it under-extrudes.\n")
    a("**Why not a finer layer on the gears?** The fingers print flat, so the tooth shape is drawn by the nozzle in X–Y; "
      "a thinner layer only adds time. What makes the teeth accurate is a slow outer wall, so DETAIL slows that down.\n")
    a("## Per part\n")
    a("| Part | Profile | Changes from the profile | Before | After | Must be accurate | Can be rough |")
    a("|---|---|---|---|---|---|---|")
    for r in rows:
        p = PARTS[r["pn"]]
        ch = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in p[1].items() if not k.startswith("support_material_")) or "—"
        ch = ch.replace("support material 1", "supports (from the bed)")
        a(f"| {r['pn']} {r['name']} | **{p[0]}** | {ch} | {fmt_h(r['h0'])}, {r['g0']:.0f} g | **{fmt_h(r['h1'])}, {r['g1']:.0f} g** | {p[2]} | {p[3]} |")
    a(f"| **Total** | | | **{fmt_h(T0)}, {G0:.0f} g** | **{fmt_h(T1)}, {G1:.0f} g** | | |\n")
    a("Brim: only the lift link (tiny). Skirt: 2 loops on every plate, as before. Supports: only where the part has a real "
      "overhang (base, turret plate, carriage arm, the two fingers), from the bed only.\n")
    a("## Plates (open and slice: the settings are already inside)\n")
    a("`cad/print/plates_eco/`: the same 4 plates (and the 2 Plan P plates), with each part's profile stored in the .3mf "
      "(PrusaSlicer: right-click a part to see it). Import `concept_a_PETG_prusaslicer.ini` first, then open the plate.\n")
    a("| Plate | Parts | Time | PETG |")
    a("|---|---|---|---|")
    for stem, title, pns, h, g, ok in plates:
        a(f"| `{stem}_eco.3mf` | {' '.join(pns)} | {fmt_h(h) if h else 'n/a'} | {g:.0f} g |" if h else f"| `{stem}_eco.3mf` | {' '.join(pns)} | slice failed | |")
    a("\nOn a plate the slicer prints parts with different layer heights together (0.28 and 0.2 mm parts sync every few layers), "
      "so the plate time is a bit more than the sum of its parts. Cura: set each part with Per Model Settings using the table above.\n")
    a("## Fix-up after printing (sandpaper, drill, knife)\n")
    a("Tools: sandpaper 120 + 240 grit, a 6 mm and a 5/32 in (4 mm) drill bit turned by hand, a 12 mm dowel or marker "
      "wrapped in sandpaper, a craft knife, flush cutters / pliers for supports.\n")
    a("| Part | Fix |")
    a("|---|---|")
    for r in rows:
        a(f"| {r['pn']} {r['name']} | {PARTS[r['pn']][4]} |")
    a("\n**Rules:** sand a press fit a little at a time and test after every few strokes (you can't add plastic back; "
      "if it gets loose, one layer of tape or a drop of CA glue). Never sand or file gear teeth. A draft part that "
      "cracks at a screw: the screw was forced: drill the hole one size bigger and use the next screw size or hot glue.\n")
    a("## Print order\n")
    a("1. Coupon (`plate0_coupon_eco`, STANDARD): check the fits as in the build guide, section 2.\n"
      "2. The claw first if you want the most important parts early (`planP_1_claw_eco`, `planP_2_finger_eco`), "
      "otherwise plates 1 → 3.\n"
      "3. Fix-up each part as it comes off the bed, and test its fit right away (bearing, LM6UU, rods, servos).\n")
    a("Regenerate: `python3.13 backend/tools/print_economy.py` (re-slices every part and plate).\n")
    with open(DOC, "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
