"""Tab "1 · Original": the 23 Nov guide (git da6e43b) + fixes a person can actually do on the parts already printed.

    python3.13 backend/tools/original_fixes.py  ->  viewer/data/original.json, cad/print/fix/horn_spacer_5mm.stl

Rule for every fix: no working inside an assembled part, no sanding hidden faces, no drilling into metal.
The worst one was "sand 5 mm off the 2 servo blocks inside the base" (the old CAD had the MG996R 5 mm too tall, so
the real spline stops 5 mm short of the horn). Instead the base is left alone: the horn goes on the spline where the
spline really is (5 mm lower) and a printed 5 mm spacer fills the gap under the turret plate (longer screws).
"""
import json
import os
import subprocess
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import model as M  # noqa: E402
import redesign as R  # noqa: E402
from model import cyl  # noqa: E402

DROP = 5.0
HORN_R = 10.4                                   # trim the round horn to 21 mm: the old base's servo blocks start 10.7 mm out


def old_base_check(horn, spacer, tips):
    """Clearances against the base AS PRINTED (model at git da6e43b, built in a temp folder)."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    subprocess.run(f"git archive da6e43b backend/cad | tar -x -C {tmp}", shell=True, cwd=ROOT, check=True)
    code = (f"import sys, json; sys.path.insert(0, {os.path.join(tmp, 'backend', 'cad')!r}); import model as M\n"
            "from model import cyl\n"
            "b = next(p['shape'] for p in M.build_parts() if p['name'] == 'base')\n"
            "import cadquery as cq\n"
            "sh = {k: cq.importers.importStep(v) for k, v in json.loads(sys.argv[1]).items()}\n"
            "out = {k: round(v.intersect(b).val().Volume(), 2) for k, v in sh.items()}\n"
            "near = cyl(0, 0, 16, 20, 45).intersect(b).val().BoundingBox().zmax\n"
            "rin = next(r / 10 for r in range(100, 160) if cyl(0, 0, r / 10, 20, 45).intersect(b).val().Volume() > 0.01)\n"
            "print(json.dumps(dict(out=out, block_top=round(near, 1), block_r=round(rin, 1))))\n")
    files = {}
    for k, v in (("horn", horn), ("spacer", spacer), ("tips", tips)):
        files[k] = os.path.join(tmp, k + ".step")
        cq.exporters.export(cq.Workplane().add(v), files[k])
    r = subprocess.run([sys.executable, "-c", code, json.dumps(files)], capture_output=True, text=True, cwd=tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    return json.loads(r.stdout.strip().splitlines()[-1])
OUT = os.path.join(ROOT, "viewer", "data", "original.json")
FIX = os.path.join(ROOT, "cad", "print", "fix")


def mesh(owner, shape, kind, color):
    v, t = shape.tessellate(0.12, 0.35)
    return dict(owner=owner, kind=kind, color=color, v=[round(c, 2) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for x in t for i in x])


def main():
    os.makedirs(FIX, exist_ok=True)
    d = json.loads(subprocess.run(["git", "show", "da6e43b:viewer/data/assembly.json"], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    cur = json.load(open(os.path.join(ROOT, "viewer", "data", "assembly.json")))

    # ---- the spacer: fits inside the turret plate's hub (inner r ~13) between the horn (now z 45-48) and the plate (z 53)
    sp = cyl(0, 0, 12.4, 53 - DROP, 53).cut(cyl(0, 0, 3.5, 40, 60))                       # centre clear of the horn hub + screw
    for x, y in ((5.66, 5.66), (-5.66, 5.66), (-5.66, -5.66), (5.66, -5.66)):
        sp = sp.cut(cyl(x, y, 1.6, 40, 60))                                                # through: the plate screws pass
    tp = next(p["shape"] for p in M.build_parts() if p["name"] == "turret_plate")
    horn_s = cyl(0, 0, HORN_R, 45.0, 48.0).union(cyl(0, 0, 5.0, 42.0, 45.0)).val()
    tips_s = cyl(0, 0, 8.9, 43.0, 48.0).cut(cyl(0, 0, 7.1, 42, 49)).val()                  # where the screw tips sweep as it turns
    chk = old_base_check(horn_s, sp.val(), tips_s)
    print("vs the base as printed:", chk)
    clash = sp.intersect(tp).val().Volume()
    cq.exporters.export(sp, os.path.join(FIX, "horn_spacer_5mm.stl"), tolerance=0.02, angularTolerance=0.1)
    import print_prep as PP
    R.DIR = FIX
    t = R.slice_one(sp.val(), "horn_spacer_5mm", os.path.join(ROOT, "cad", "print", "reprint", "reprint_a.ini"), PP, keep=True)
    print(f"spacer vs turret plate overlap {clash:.1f} mm3; print {t}")

    # ---- 3D: real-height MG996R (tabs where they are, spline 5 mm lower), horn 5 mm lower, the spacer, longer screws
    servo = next(m for m in cur["meshes"] if m["owner"] == "turntable_servo_MG996R")
    servo = dict(servo, v=[round(c - DROP if i % 3 == 2 else c, 2) for i, c in enumerate(servo["v"])])  # current model has it 5 mm higher (shorter blocks)
    hm = cyl(0, 0, HORN_R, 45.0, 48.0).union(cyl(0, 0, 5.0, 42.0, 45.0)).cut(cyl(0, 0, 1.6, 40, 50))
    for x, y in ((5.66, 5.66), (-5.66, 5.66), (-5.66, -5.66), (5.66, -5.66)):
        hm = hm.cut(cyl(x, y, 0.8, 40, 50))
    horn = [mesh("turntable_horn", hm.val(), "bought", "#f4f4f4")]
    long = []
    for s in d["screws"]:
        if s["owner"] == "turret_plate":
            s.update(kind="#2", length=15.9, hole="#2 × 5/8″ through the plate + spacer into the horn (servo-bag screws are too short now)")
            ax = cq.Vector(*s["axis"])
            body = cq.Solid.makeCylinder(0.9, s["length"], cq.Vector(*s["head"]), ax)
            head = cq.Solid.makeCylinder(s.get("head_r", 2.2), s.get("head_h", 1.2), cq.Vector(*s["head"]), -ax)
            long.append(mesh(s["name"], body.fuse(head), "screw", "#d4d8de"))
        if s["owner"] == "turntable_horn":
            s["head"] = [s["head"][0], s["head"][1], round(s["head"][2] - DROP, 2)]
    longn = {m["owner"] for m in long}
    d["meshes"] = [m for m in d["meshes"] if m["owner"] not in ("turntable_servo_MG996R", "turntable_horn") and m["owner"] not in longn]
    d["meshes"] += [servo] + horn + long + [mesh("horn_spacer", sp.val(), "printed", "#2f72e0")]
    for m in d["meshes"]:
        if m["owner"] == "screw_04":
            m["v"] = [round(c - DROP if i % 3 == 2 else c, 2) for i, c in enumerate(m["v"])]
    d["names"]["horn_spacer"] = "Horn spacer 5 mm (new, 23 min print)"
    d["printed"] = sorted(set(d["printed"]) | {"horn_spacer"})

    for s in d["steps"]:
        if s["title"] == "Servo horn":
            s["how"] = ("<b>First, on the table: trim the round horn to Ø21 mm</b> (flush cutters round the rim, then sand smooth; "
                        "the 4 holes 8 mm out keep ~1.6 mm of plastic round them). Lowered 5 mm, the horn passes just 1 mm over "
                        "the tops of the base's 2 servo blocks, which start 10.7 mm from the centre; a full-size horn overlaps "
                        "them and could scrape. At Ø21 it clears them sideways too. <b>Test before the turret goes on:</b> turn "
                        "the horn by hand 180° each way. It must not touch anything. "
                        "Turn the servo to 135° first (laptop panel). Press the round horn onto the spline with its 4 inner holes on "
                        "the diagonals, then the centre screw. <b>The horn now sits about 5 mm lower than the 3D model of 23 Nov "
                        "showed</b>, inside the bearing's bore: the real MG996R is 5 mm shorter. That's fine; the spacer in the next "
                        "step makes up the gap. Leave the base's servo blocks as they are.")
        if s["title"] == "Turret plate":
            s["new"] = ["horn_spacer", "turret_plate"]
            s["show"] = sorted(set(s["show"]) | {"horn_spacer"})
            s["hw"] = [[1, "printed horn spacer (5 mm)"], [4, "#2 × 5/8″ pan-head sheet-metal screws"]]
            s["how"] = ("1) Drop the printed <b>5 mm horn spacer</b> onto the horn, its 4 holes over the horn's 4 diagonal holes. "
                        "2) The turret plate's hub goes into the bearing's inner ring, covering the spacer. 3) Line up the holes and "
                        "drive 4 × <b>#2 × 5/8″</b> screws down through the plate and the spacer into the horn. The servo-bag "
                        "screws are now 5 mm too short.")
            s["fit"] = ("<b>Why the spacer:</b> the old CAD had the MG996R 5 mm too tall, so the real spline stops 5 mm short of the "
                        "plate. Sanding the 2 blocks inside the base would fix it, but they're hard to reach and must come out exactly "
                        "level. The spacer is a 23-minute print and leaves the base untouched (checked in CAD: it fits inside the "
                        "plate's hub). File: cad/print/fix/horn_spacer_5mm.stl.")
    d["known_issues"] = [
        ["MG996R spline stops 5 mm short of the turret horn", "<b>Don't sand the blocks inside the base.</b> Trim the round horn to "
         "Ø21 mm on the table (so it clears the servo blocks as it turns), put it on the spline where it is, drop a printed <b>5 mm horn spacer</b> on it (23 min print) and use 4 × #2 × 5/8″ screws through the plate. "
         "Shown in steps 4–5. <i>Easy · 15 min.</i>"],
        ["Wrist servo hits the base tower when the carriage is low", "No cutting: set <b>LIFT_DOWN</b> a few degrees higher in the laptop "
         "panel, so the carriage stops about 4 mm higher. The claw then grips the can 4 mm higher, which makes no difference. "
         "<i>Easy · 2 min, software only.</i>"],
        ["Carriage arm snapped where it meets the wrist bracket", "Best: <b>switch to A3</b> (tab 4). It doesn't use a carriage at all, "
         "only one new 56-minute arm, and keeps everything else. Quick patch: epoxy + a steel mending plate with 2 short #6 screws "
         "each side, on the loose part on the table. <i>A3: easy · 1 h print + 30 min.</i>"],
        ["No horn in the bag reaches the crank's 20 mm hole", "A3 removes the crank too. Staying with the slide: the single-arm horn's "
         "last hole (14 mm) + the new 11.2 mm lift link (5-minute print) + LIFT_UP 98. <i>Easy.</i>"],
        ["Gripper frame: horn opening too small for the screwdriver", "With the frame <b>loose on the table</b> (before the claw is "
         "built), open the hole to Ø16 with a 5/8″ bit turned <b>by hand</b> (PETG cuts easily) or a step drill. Already built? Use "
         "the reprinted frame instead of taking the claw apart. <i>Easy · 5 min, plastic only.</i>"],
        ["Spine: #6 pan heads hit the wall next to the holes", "With the spine loose on the table, before anything is mounted on it: "
         "a few strokes of a round needle file make a half-round notch beside each hole. <i>Easy · 5 min.</i>"],
        ["Holes about 1 mm small", "Twist the drill bit named in the step's callout <b>by hand</b> (or in a drill at the slowest speed) "
         "through the loose part before assembling. Never force a press fit. <i>Easy.</i>"],
    ]
    d["fix_files"] = [dict(name="horn_spacer_5mm.stl", time=t)]
    d["fix_check"] = (f"Checked against the base as printed (git da6e43b): horn (trimmed Ø{2 * HORN_R:.0f}) overlap {chk['out']['horn']} mm3, "
                      f"spacer {chk['out']['spacer']} mm3, screw tips {chk['out']['tips']} mm3. Servo blocks start {chk['block_r']} mm "
                      f"out, tops at z {chk['block_top']}: the horn clears them by {chk['block_r'] - HORN_R:.1f} mm sideways and "
                      f"{45.0 - chk['block_top']:.1f} mm above.")
    d["screw_names"]["#2"] = "#2 × 5/8″ pan-head sheet-metal screw"
    d["title"] = "1 · Original parts (as printed 23 Nov)"
    d["original"] = True
    json.dump(d, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/original.json ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
