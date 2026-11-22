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
import json
import os
import re
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import plates as PL  # noqa: E402

INI = os.path.join(ROOT, "cad", "print", "settings", "concept_a_PETG_prusaslicer.ini")
STL = os.path.join(ROOT, "cad", "print", "stl")
DOC = os.path.join(ROOT, "docs", "16_print_economy.md")
CSV = os.path.join(ROOT, "cad", "print", "settings", "economy_plates.csv")
JSN = os.path.join(ROOT, "cad", "print", "settings", "economy_plates.json")   # read by render_manual.js
IMG = os.path.join(ROOT, "docs", "print_plates")                             # plate + part pictures
DENSITY, AREA = 1.27, np.pi * 1.75 ** 2 / 4          # PETG g/cm3, mm2 of 1.75 mm filament

# Same on every plate (type these once in your slicer's PETG profile)
COMMON = [
    ("Nozzle temperature", "235 °C (first layer 238 °C, never above 240 °C: PTFE-lined hotend)"),
    ("Bed", "Textured PEI sheet, 80 °C. **No glue.** Clean it with dish soap + water (or isopropyl) and don't touch the print area"),
    ("Z-offset", "a little higher than for PLA: PETG must not be squished into PEI (it can stick too hard)"),
    ("Removing parts", "let the bed cool to room temperature, take the sheet off and flex it: parts pop off"),
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
SUP = {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1",
       "support_material_threshold": "50", "support_material_contact_distance": "0.25", "support_material_xy_spacing": "0.8",
       "support_material_interface_layers": "2"}
# Normal supports, lines, 15 %: cheapest for the flat ledges of the base and turret plate (organic was +35 min on plate D).
SUP_NORMAL = {**SUP, "support_material_style": "grid", "support_material_pattern": "rectilinear", "support_material_spacing": "2.5"}
# Tree / organic: only touches the curved pads, peels off cleanly away from the gear teeth, 4 g less per finger, same time.
SUP_TREE = {**SUP, "support_material_style": "organic"}
SUP_TEXT = {  # what to type (Cura name / PrusaSlicer name)
    "grid": [("Support type", "**Normal** (Cura) / **Grid** style (PrusaSlicer)"), ("Support pattern", "**Lines** (Prusa: Rectilinear)"),
             ("Support density", "**15 %** (Prusa: pattern spacing 2.5 mm)")],
    "organic": [("Support type", "**Tree** (Cura) / **Organic** (PrusaSlicer)"), ("Support pattern / density", "automatic (leave default)")],
}
SUP_COMMON = [("Placement", "**touching build plate only** (no supports on the part)"), ("Overhang angle", "50°"),
              ("Top Z distance", "0.25 mm (PETG: easier to peel)"), ("XY distance", "0.8 mm"), ("Support interface / roof", "on, 2 layers")]

# Hand plates: one profile per plate. (name, profile, plate overrides, parts, why)
PLATES = [
    ("A  Coupon + lift link", "STANDARD", {"brim_width": "5"}, ["CA-900", "CA-302"],
     "First: the coupon checks every fit; the tiny link rides along and gets the brim it needs"),
    ("B  Base + spine + top cap", "DRAFT", {"perimeters": "3", "fill_density": "12%", **SUP_NORMAL}, ["CA-101", "CA-202", "CA-203"],
     "Big, hidden, lightly loaded. 3 walls so the screw holes and the bearing pocket stay strong"),
    ("C  Electronics tray", "DRAFT", {}, ["CA-102"],
     "Nothing precise on it: the fastest settings"),
    ("D  Turret plate + carriage arm", "STANDARD", dict(SUP_NORMAL), ["CA-201", "CA-301"],
     "Press fits (bearing hub, rods, LM6UU) and the parts that carry the lift"),
    ("E  Claw: 2 fingers + gripper frame", "DETAIL", dict(SUP_TREE), ["CA-402", "CA-403", "CA-401"],
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


# PrusaSlicer 2.7 quick map: where each setting lives (Expert mode). (setting, where)
PRUSA_STEPS = [
    "**Fastest:** File › Open Project (Ctrl+O) › `cad/print/plates/plate_X.3mf`. The parts are already on the bed AND every "
    "setting on the plate's page is inside (printer CR-6 SE, PETG, layers, infill, supports): answer **Yes** to load its settings, then slice. "
    "Part already printed? Right-click it in the object list › Delete.",
    "Top right: switch the mode to **Expert** (red). Otherwise half of these fields are hidden.",
    "Printer (once): Configuration › Configuration Wizard › Creality › **CR-6 SE**. Filament: Generic PETG.",
    "Lost? **Ctrl+F** searches every setting by name (type \"support\", \"brim\", \"infill\"…) and jumps to it.",
    "Make 3 print presets once: set DRAFT (plates B, C), STANDARD (A, D), DETAIL (E), click the **save icon** next to the "
    "preset name and call them \"PETG Draft / Standard / Detail\". Then each plate = pick the preset in the right panel + the plate's few changes.",
    "Changed fields turn **orange** with an unlocked padlock; click the orange arrow to undo a change.",
]
PRUSA_KEYS = [("Ctrl+I", "import STL (or drag the files in)"), ("A", "arrange the parts on the bed"), ("F", "place on face: click the flat face that goes down"),
              ("R / M / S", "rotate / move / scale tool"), ("Del", "delete selected part"), ("Ctrl+1 / 2 / 3 / 4", "Plater / Print / Filament / Printer settings tabs"),
              ("Ctrl+R", "slice"), ("Tab", "switch 3D view ↔ Preview (layers, supports, estimated time bottom right)"),
              ("Ctrl+G", "export G-code: short name, no spaces (e.g. PLATEB.gcode), to the SD card")]
PRUSA_MAP = [
    ("Layer height, first layer height", "Print Settings › **Layers and perimeters** › Layer height"),
    ("Walls", "Print Settings › Layers and perimeters › Vertical shells › **Perimeters**"),
    ("Top / bottom layers", "Print Settings › Layers and perimeters › Horizontal shells › **Solid layers** Top / Bottom"),
    ("Seam", "Print Settings › Layers and perimeters › Advanced › Seam position: **Rear** / Aligned"),
    ("Infill density + pattern", "Print Settings › **Infill** › Fill density, Fill pattern (Grid, Gyroid, Rectilinear = lines)"),
    ("Skirt / brim", "Print Settings › **Skirt and brim** › Loops (minimum) = 2; Brim type Outer only, Brim width 5 mm (plate A)"),
    ("Supports on / off", "Print Settings › **Support material** › Generate support material ✓, Auto generated supports ✓"),
    ("Support style", "Support material › Style: **Grid** (B, D) or **Organic** (E)"),
    ("Placement, overhang angle", "Support material › **On build plate only** ✓, Overhang threshold 50°"),
    ("Z / XY distance, interface", "Support material › Top contact Z distance 0.25, XY separation 0.8 mm, Top interface layers 2"),
    ("Support pattern, density", "Support material › Options for support material › Pattern **Rectilinear**, Pattern spacing **2.5 mm** (≈15 %)"),
    ("Speeds", "Print Settings › **Speed** › Perimeters, Small perimeters, External perimeters, Infill, Solid / Top solid infill, Travel, First layer speed"),
    ("Line width, elephant foot", "Print Settings › **Advanced** › Extrusion width 0.42; Elephant foot compensation 0.15 mm"),
    ("Nozzle / bed temperature", "Filament Settings › **Filament** › Temperature: First layer 238 / 80, Other layers 235 / 80"),
    ("Cooling fan", "Filament Settings › **Cooling** › Min / max fan speed 30 %, Disable fan for the first 3 layers"),
    ("Max flow", "Filament Settings › **Advanced** › Max volumetric speed 8 mm³/s"),
    ("Retraction", "Printer Settings › **Extruder 1** › Retraction length 5 mm, speed 40 mm/s"),
]

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


def render(objs, path, bed=None, size=(7, 5.4), elev=40, azim=-60):
    """Orthographic picture, painter's algorithm (back to front). objs: [(tris, colour)] in bed coordinates."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])          # towards the camera
    right = np.array([-np.sin(a), np.cos(a), 0.0])
    up = np.cross(view, right)
    light = np.array([-0.3, -0.5, 0.95]); light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    for tris, c in objs:
        n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        vis = n @ view > 0                                                               # back faces away
        t = tris[vis]
        k = 0.42 + 0.58 * np.clip(n[vis] @ light, 0, 1)
        rgb = np.array(matplotlib.colors.to_rgb(c))
        polys.append(np.stack([t @ right, t @ up], axis=-1))
        cols.append(np.clip(rgb[None] * k[:, None] + 0.06, 0, 1))
        depth.append(t.mean(1) @ view)
    P, C, D = np.concatenate(polys), np.concatenate(cols), np.concatenate(depth)
    order = np.argsort(D)
    fig, ax = plt.subplots(figsize=size, dpi=140)
    if bed:
        corners = np.array([[0, 0, 0], [bed[0], 0, 0], [bed[0], bed[1], 0], [0, bed[1], 0]], float)
        ax.add_patch(plt.Polygon(np.stack([corners @ right, corners @ up], -1), fc="#ece6d6", ec="#9c937c", lw=1, zorder=0))
        for g in np.arange(0, bed[0] + 1, 47):
            for p0, p1 in (([g, 0, 0], [g, bed[1], 0]), ([0, g, 0], [bed[0], g, 0])):
                q = np.array([p0, p1], float)
                ax.plot(q @ right, q @ up, color="#d8d0bb", lw=0.6, zorder=1)
        allp = np.concatenate([P.reshape(-1, 2), np.stack([corners @ right, corners @ up], -1)])
    else:
        allp = P.reshape(-1, 2)
    ax.add_collection(PolyCollection(P[order], facecolors=C[order], edgecolors=C[order], linewidths=0.2, zorder=3))
    lo, hi = allp.min(0), allp.max(0)
    pad = 0.04 * (hi - lo).max()
    ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal"); ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(path, facecolor="white")
    plt.close(fig)


COLOURS = ["#2f6fdb", "#e07b22", "#2a9d5b", "#b84fc4", "#c43a3a"]


def plate_layout(pns):
    tris, sizes = {}, {}
    for pn in pns:
        t = PL.read_stl(stl_of(pn))
        lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
        tris[pn], sizes[pn] = t - lo, (hi[0] - lo[0], hi[1] - lo[1])
    place = PL.pack(sizes)
    out = []
    for pn in pns:
        x, y, rot = place[pn]
        t = tris[pn].copy()
        if rot:
            t = np.stack([-t[..., 1], t[..., 0], t[..., 2]], axis=-1)
            t[..., 0] += sizes[pn][1]
        t[..., 0] += x
        t[..., 1] += y
        out.append(t)
    return out


def images(rows):
    os.makedirs(IMG, exist_ok=True)
    for r in rows:
        lay = plate_layout(r["pns"])
        r["img"] = f"docs/print_plates/plate_{r['name'][0]}.png"
        render([(t, COLOURS[i % len(COLOURS)]) for i, t in enumerate(lay)], os.path.join(ROOT, r["img"]), bed=PL.BED)
        r["part_imgs"] = []
        for i, pn in enumerate(r["pns"]):
            pi = f"docs/print_plates/part_{pn}.png"
            render([(lay[i], COLOURS[i % len(COLOURS)])], os.path.join(ROOT, pi), size=(3.2, 2.6))
            r["part_imgs"].append(pi)


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
        try:
            h, g = slice_plate([stl_of(pn) for pn in pns], s)
        except SystemExit:          # PrusaSlicer 2.7 bug (false "gcode path conflict" with organic supports): sum the parts
            h, g = map(sum, zip(*[slice_plate([stl_of(pn)], s) for pn in pns]))
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
    images(rows)
    with open(JSN, "w") as f:
        json.dump(dict(prusa_steps=PRUSA_STEPS, prusa_keys=PRUSA_KEYS, prusa_map=PRUSA_MAP, common=COMMON, before=[before_h, before_g], after=[T1, G1], plates=[dict(
            letter=r["name"][0], img=r["img"], ini=f"cad/print/settings/plates/plate_{r['name'][0]}.ini", time=fmt_h(r["h"]), grams=round(r["g"]), profile=r["prof"],
            layer=r["s"]["layer_height"], walls=r["s"]["perimeters"], topbot=f"{r['s']['top_solid_layers']} / {r['s']['bottom_solid_layers']}",
            infill=r["s"]["fill_density"] + " " + {"grid": "grid", "gyroid": "gyroid", "rectilinear": "lines"}[r["s"]["fill_pattern"]],
            speeds=f"{r['s']['external_perimeter_speed']} / {r['s']['perimeter_speed']} / {r['s']['infill_speed']}",
            supports="ON" if r["s"].get("support_material") == "1" else "OFF (no overhangs)",
            support_rows=(SUP_TEXT[r["s"]["support_material_style"]] + SUP_COMMON) if r["s"].get("support_material") == "1" else [],
            adhesion=f"BRIM {r['s']['brim_width']} mm" if r["s"].get("brim_width") else "skirt",
            parts=[dict(img=pi, file=os.path.basename(stl_of(pn)), accurate=PARTS[pn][0], fix=PARTS[pn][2]) for pn, pi in zip(r["pns"], r["part_imgs"])])
            for r in rows]), f, indent=1, ensure_ascii=False)
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
    a("The pictures show each plate as it sits on the bed: put the parts on the bed the same way.\n")
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
        sup = ("**on**, " + ("Normal, lines 15 %" if s.get("support_material_style") == "grid" else "Tree / organic")) if s.get("support_material") == "1" else "off"
        adh = f"**brim {s['brim_width']} mm**" if s.get("brim_width") else "skirt"
        pat = {"grid": "grid", "gyroid": "gyroid", "rectilinear": "lines"}[s["fill_pattern"]]
        a(f"| **{r['name']}** ({r['prof']}) | {parts} | {s['layer_height']} mm | {s['perimeters']} | {s['top_solid_layers']} / "
          f"{s['bottom_solid_layers']} | {s['fill_density']} {pat} | {s['external_perimeter_speed']} / {s['perimeter_speed']} / "
          f"{s['infill_speed']} | {sup} | {adh} | {fmt_h(r['h'])} | {r['g']:.0f} g |")
    a(f"| **Total** | | | | | | | | | **{fmt_h(T1)}** | **{G1:.0f} g** |\n")
    for r in rows:
        a(f"**Plate {r['name'][0]}**\n\n![Plate {r['name'][0]}](print_plates/plate_{r['name'][0]}.png)\n")
    a("Print in this order (A first). Every plate fits the 235 × 235 mm bed; leave ~15 mm between parts for the supports.\n")
    a("## PrusaSlicer: where to find everything\n")
    for i, t in enumerate(PRUSA_STEPS, 1):
        a(f"{i}. {t}")
    a("\n| Key | Does |")
    a("|---|---|")
    for k, v in PRUSA_KEYS:
        a(f"| **{k}** | {v} |")
    a("\n| Setting | Where (PrusaSlicer 2.7, Expert mode) |")
    a("|---|---|")
    for k, v in PRUSA_MAP:
        a(f"| {k} | {v} |")
    a("")
    a("## Supports (plates B, D, E)\n")
    a("| Setting | Plates B and D | Plate E (claw) |")
    a("|---|---|---|")
    for (k, v1), (_, v2) in zip(SUP_TEXT["grid"][:2], SUP_TEXT["organic"][:2]):
        a(f"| {k} | {v1} | {v2} |")
    a(f"| Support density | {SUP_TEXT['grid'][2][1]} | automatic |")
    for k, v in SUP_COMMON:
        a(f"| {k} | {v} | {v} |")
    a("\nInfill pattern is in the plate table (grid / gyroid / lines). Plates A and C need no supports at all.\n")
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
