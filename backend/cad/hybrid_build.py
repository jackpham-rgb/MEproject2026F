"""Step-by-step build guide for Concept A3 (hybrid), in the same format as the main guide.

    python3.13 backend/cad/hybrid_build.py  ->  viewer/data/hybrid_build.json  (viewer/assembly.html?data=hybrid_build)

Parts come from hybrid.build(); every screw is placed at its real hole (head point = under the head, axis = the way it
drives). The claw is identical to Concept A, so its steps, screws and glue are taken from viewer/data/assembly.json.
Checks: every screw's body must reach the part it threads into and stay out of anything else (cad/hybrid/screws.txt).
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import hybrid as H  # noqa: E402
from model import P, cyl_dir  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "hybrid_build.json")
MAIN = json.load(open(os.path.join(ROOT, "viewer", "data", "assembly.json")))
SCREW_NAMES = dict(MAIN["screw_names"], **{
    "M3x6": "M3 × 6 mm pan / button head", "sh": "M3 shoulder screw, 4 mm shoulder × 4 mm long",
    "M6": "M6 × 30 bolt + nut (ballast)", "M3x8": "M3 × 8 mm pan / button head"})
SHAFT_R = {"#8": 2.1, "#6": 1.75, "#6s": 1.7, "sb": 1.0, "M3": 1.5, "M3x6": 1.5, "M3x8": 1.5, "sh": 2.0, "M6": 3.0}
HEAD = {"#8": (4.0, 2.8), "#6": (3.5, 2.4), "sb": (2.2, 1.2), "M3": (2.75, 2.0), "M3x6": (2.75, 1.7), "M3x8": (2.75, 1.7),
        "sh": (3.5, 3.0), "M6": (5.0, 4.0)}


def main():
    parts = H.build()
    shapes = {p["name"]: (p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]) for p in parts}
    group = {p["name"]: p["group"] for p in parts}
    screws, n = [], [0]

    def sc(owner, kind, head, axis, length, hole, into):
        n[0] += 1
        hr, hh = HEAD[kind]
        s = dict(name=f"hs_{n[0]:02d}", owner=owner, kind=kind, head=[round(v, 2) for v in head], axis=list(axis), length=length,
                 hole=hole, head_r=hr, head_h=hh, into=into)
        screws.append(s)
        return s["name"]

    # ---- screws (new ones; claw screws come from the main guide below)
    s_tower = [sc("tower", "M3x6", (30 * math.cos(math.radians(a)), 30 * math.sin(math.radians(a)), 0.0), (0, 0, 1), 6,
                  "plate Ø3.4 drilled (9/64″ bit) → brass insert in the tower flange", "tower") for a in (45, 135, 225, 315)]
    s_ball = [sc(f"ballast_{k}", "M6", (x, -48, 0.0), (0, 0, 1), 30, "plate Ø6.5 drilled (1/4″ bit) · washers · nut on top", f"ballast_{k}")
              for k, x in (("L", -38), ("R", 38))]
    tab_top = H.R.TT_TIP_Z - 12.6 + 2.5
    s_tt = [sc("turntable_servo_MG90S", "sb", (hx, 0, tab_top), (0, 0, -1), 8, "servo tab → post pilot in the tower", "tower")
            for hx in (5.45 - 13.75, 5.45 + 13.75)]
    s_horn = [sc("turntable_horn", "sb", (8 * math.cos(math.radians(a)), 8 * math.sin(math.radians(a)), H.R.TT_TIP_Z), (0, 0, 1), 6,
                 "horn arm hole → turret pilot (from under the turret)", "turret") for a in (0, 90, 180, 270)]
    s_mg = [sc("shoulder_servo_MG996R", "#8", (-2.4, ly, H.PA[1] + lz), (1, 0, 0), 12.7,
               "MG996R tab → cradle pilot Ø4.5 (prints ~3.5) · 9/64″ bit if tight", "turret")
            for lz in (10.15 - 24.75, 10.15 + 24.75) for ly in (-5, 5)]
    s_la = [sc("link_A", "M3x6", (H.LX[1], 8 * math.cos(math.radians(a)), H.PA[1] + 8 * math.sin(math.radians(a))), (-1, 0, 0), 6,
               "link Ø3.3 (drill through the horn's holes) → horn's M3 thread", "shoulder_horn") for a in (45, 315)]
    s_hc = sc("shoulder_horn", "M3", (H.LX[1], H.PA[0], H.PA[1]), (-1, 0, 0), 8, "horn centre screw through the link's pivot hole", "shoulder_servo_MG996R")
    s_lb = sc("pivot_B_screw", "sh", (H.LX[1] + 0.1, H.PB[0], H.PB[1]), (-1, 0, 0), 10, "link Ø4.0 (5/32″) turns on the shoulder → ear insert", "turret")
    s_cp = [sc(nm, "sh", (H.LX[0] - 0.1, c[0], c[1]), (1, 0, 0), 8, "link Ø4.0 turns on the shoulder → coupler insert", "coupler")
            for nm, c in (("pivot_A2_screw", H.CA), ("pivot_B2_screw", H.CB))]

    # ---- screw check: material all round the screw in the part it threads into (it sits in that part's hole),
    #      and its body (thinner than any hole) runs into nothing else (except what it passes through by design)
    passes = {"tower": ["base_plate"], "turret": ["turntable_horn", "shoulder_servo_MG996R", "link_B"], "coupler": ["link_A", "link_B"],
              "shoulder_horn": ["link_A"], "shoulder_servo_MG996R": ["shoulder_horn", "link_A"]}
    lines, bad = [], 0
    for s in screws:
        body = cyl_dir(tuple(s["head"]), tuple(s["axis"]), SHAFT_R[s["kind"]] * 0.8, s["length"]).val()
        ring = cyl_dir(tuple(s["head"]), tuple(s["axis"]), SHAFT_R[s["kind"]] + 1.2, s["length"]).val()   # wall round the hole
        bite = ring.intersect(shapes[s["into"]]).Volume() if s["into"] in shapes else 0
        hits = [m for m, sh in shapes.items() if m not in (s["owner"], s["into"], *passes.get(s["into"], []), *[x for x in shapes if x.startswith("pivot")])
                and group[m] != "can" and body.intersect(sh).Volume() > 1.0]
        ok = (bite > 1.0 or s["kind"] == "M6") and not hits
        bad += not ok
        lines.append(f"  {s['name']} {s['kind']:>4} {s['owner']:<24} into {s['into']:<22} bite {bite:5.1f} mm3  "
                     f"{'PASS' if ok else 'FAIL ' + ', '.join(hits)}")
    lines.append(f"RESULT: {'every screw reaches its part and hits nothing else' if not bad else f'{bad} screw(s) wrong'}")
    open(os.path.join(ROOT, "cad", "hybrid", "screws.txt"), "w").write("SCREWS (hybrid build)\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))

    # ---- meshes: hybrid parts + new screws + the claw's screws and glue from the main guide
    colors = {"printed": "#2f72e0", "metal": "#aab2bc", "bought": "#d9d9d9", "can": "#c8102e"}
    special = {"turntable_servo_MG90S": "#3b3f45", "shoulder_servo_MG996R": "#1d1d1f", "wrist_servo": "#3b3f45",
               "gripper_servo_SG90": "#22346e", "bearing_6807": "#c9ced6", "ballast_L": "#6b7076", "ballast_R": "#6b7076"}
    meshes = []

    def mesh(owner, shape, kind, color):
        v, t = shape.tessellate(0.12, 0.35)
        meshes.append(dict(owner=owner, kind=kind, color=color, v=[round(c, 2) for vv in v for c in (vv.x, vv.y, vv.z)],
                           f=[i for tt in t for i in tt]))
    for p in parts:
        mesh(p["name"], shapes[p["name"]], "bought" if p["kind"] == "metal" else p["kind"], special.get(p["name"], colors[p["kind"]]))
    for s in screws:
        back = tuple(-a for a in s["axis"])
        shp = cyl_dir(tuple(s["head"]), tuple(s["axis"]), SHAFT_R[s["kind"]] * 0.85, s["length"]).union(
            cyl_dir(tuple(h + b * 0.05 for h, b in zip(s["head"], back)), back, s["head_r"], s["head_h"])).val()
        mesh(s["name"], shp, "screw", "#d4d8de")
    claw_steps = [MAIN["steps"][i - 1] for i in (9, 10, 11, 12, 13, 14, 15)]
    claw_screws = sorted({x for st in claw_steps for x in st["screws"]})
    claw_glue = sorted({x for st in claw_steps for x in st["glue"]})
    meshes += [m for m in MAIN["meshes"] if m["owner"] in claw_screws or m["owner"] in claw_glue]
    screws += [dict(s) for s in MAIN["screws"] if s["name"] in claw_screws]
    glue = [g for g in MAIN["glue"] if g["name"] in claw_glue]
    for s in screws:
        group[s["name"]] = group.get(s["owner"], "fixed")
    for g in claw_glue:
        group[g] = "wrist"

    # ---- steps
    steps, placed = [], set()
    CLAW = {"wrist_horn", "gripper_frame", "finger_L", "finger_R", "axle_R", "gripper_horn", "gripper_servo_SG90", "can_bumper"}

    def step(title, new, screws_, how, level="easy", dir_=(0, 0, 1), dist=40, hw=(), badge=None, fit="", note="", table=None,
             callouts=(), per_part_dir=None, glue_=(), glue_text=""):
        if table is None:
            placed.update(new, screws_, glue_)
            show = sorted(placed)
        else:
            show = sorted(set(table) | set(new) | set(screws_) | set(glue_))
        steps.append(dict(n=len(steps) + 1, title=title, new=list(new), show=show, dir=list(dir_) if dir_ else None,
                          per_part_dir=per_part_dir or {}, dist=dist, hw=[list(h) for h in hw], badge=list(badge) if badge else None,
                          note=note, screws=list(screws_), glue=list(glue_), fit=fit, how=how, glue_text=glue_text, level=level,
                          callouts=list(callouts)))

    L, A0 = H.L, H.A0
    step("Cut and drill the 2 links (printed jig)", ["link_A", "link_B"], [], table=[], level="precise", dir_=(0, 0, 1), dist=30,
         hw=[[2, "1/8″ × 1/2″ aluminium flat bar, 60 mm long"]],
         note="Both links must come out identical: the jig makes sure of it",
         how=f"1) Cut two 60 mm pieces of 1/8″ × 1/2″ aluminium flat bar (hacksaw), file the ends. 2) Lay one in the printed "
             f"<b>link jig</b>'s slot, its end against the stop, and clamp jig + bar to a piece of wood. 3) Drill <b>4.0 mm (5/32″)</b> "
             f"through both guide holes: they are exactly {L:.0f} mm apart. 4) Same for the second bar. 5) Round the ends with a file and "
             f"deburr the holes. Check: put two 5/32″ drill bits through both links stacked together. If the bits slide in, the links match.",
         fit="<b>A parallelogram only stays level if both links are the same length.</b> Never drill them by eye; always use the jig.")
    step("Plate: cut, drill, ballast and feet", ["base_plate", "ballast_L", "ballast_R"], s_ball, dir_=(0, 0, 1), dist=40,
         hw=[[1, "1/8″ aluminium sheet, 120 × 110 mm"], [2, "M6 × 30 bolt + nut"], [10, "1″ steel washers (≈ 60 g per stack)"],
             [4, "rubber feet"]],
         note="Use the printed tower as the drilling template",
         how="1) Cut the sheet to 120 × 110 mm (hacksaw or a jigsaw with a metal blade) and file the edges. 2) Set the printed tower on "
             "it, centred 72 mm from the back edge, and mark through its 4 flange holes. 3) Drill those <b>3.4 mm (9/64″)</b>. Drill 2 × "
             "<b>6.5 mm (1/4″)</b> for the ballast bolts and 4 corner holes for the feet (or use stick-on feet). 4) Each ballast is an "
             "M6 bolt up from below through 5 washers, with a nut on top. It's about 60 g each and keeps the robot from tipping toward the "
             "arm. Deburr everything: aluminium edges are sharp.")
    ins = [{"at": [30 * math.cos(math.radians(a)), 30 * math.sin(math.radians(a)), 3.2], "text": "M3 insert from below"} for a in (45, 225)]
    ins += [{"at": [16.5, H.PB[0], H.PB[1]], "text": "M3 insert in the ear (from the link side)"},
            {"at": [H.CX[0], H.CA[0], H.CA[1]], "text": "M3 insert (from the link side)"},
            {"at": [H.CX[0], H.CB[0], H.CB[1]], "text": "M3 insert (from the link side)"}]
    step("Melt in the 7 brass inserts", [], [], table=["tower", "turret", "coupler"], level="try", dir_=None, dist=0, callouts=ins,
         hw=[[7, "M3 brass heat-set insert, 4 mm long"]],
         note="Soldering iron at about 230 °C; push straight, stop flush",
         how="Inserts give the printed parts real metal threads, so you can take the robot apart and rebuild it without stripping. "
             "Where they go: 4 in the tower flange (from below), 1 in the ear on the turret (from the link side), 2 in the coupler (from "
             "the link side). For each one: put the insert on the hole, rest the iron tip in it, let it sink under light pressure (about "
             "5 s), stop when it's flush, then press it flat with something metal while it cools. Test each with an M3 screw.",
         fit="Holes are 5.0 mm in the CAD, which prints at about 4.0 on this printer: the size inserts need. An insert that "
             "drops in loose wasn't melted in; one that won't start needs the hole opened with a 4 mm bit by hand.")
    step("Tower onto the plate", ["tower"], s_tower, dir_=(0, 0, 1), dist=40, hw=[[4, "M3 × 6 mm"]],
         note="4 M3 screws up through the plate into the inserts",
         how="Tower on the plate with the cable slot toward the back (the ballast side). 4 × M3 × 6 up through the plate into the "
             "flange inserts. Snug, not hard: the inserts are in plastic.")
    step("Turntable servo (MG90S) into the tower", ["turntable_servo_MG90S"], s_tt, dir_=(0, 0, 1), dist=60, hw=[[2, "servo-bag screw"]],
         badge=["MG90S turntable", "135° (HOME)"], note="Lead out through the slot first, then the servo down onto the 2 posts",
         how="Feed the servo lead out through the slot at the bottom of the tower first. Lower the servo in, spline up and centred, "
             "tabs on the 2 posts. 2 servo-bag screws through the tabs into the posts, from above.")
    step("Bearing into the tower", ["bearing_6807"], [], level="precise", dir_=(0, 0, 1), dist=40,
         note="Press the 6807 into the top of the tower, flat and fully down",
         how="Press the bearing in evenly with a flat block (a piece of wood across it) until it sits on the ledge. Push on the outer "
             "ring only.",
         fit="<b>Press fit, outer ring.</b> The pocket is drawn 48.0 mm so it prints about 47.0, the bearing's size (same correction "
             "as the main base). Loose: one wrap of tape round the bearing. Too tight: sand the pocket wall evenly, never one side.")
    step("Turntable horn under the turret (on the table)", ["turret", "turntable_horn"], s_horn, table=[], dir_=(0, 0, -1), dist=30,
         hw=[[4, "servo-bag screw"]], note="Turret upside down; horn screwed onto its underside",
         how="Take the <b>cross horn</b> from the MG90S bag and cut its arms to 12 mm from the centre so it fits inside the hub. Turn "
             "the turret upside down and lay the horn in the hub recess, hub sticking out (toward the servo). Drive 4 servo-bag "
             "screws through the horn's holes 8 mm out into the turret's pilots. Drill 1/16″ through the horn hole first if a hole "
             "doesn't line up.")
    placed.update(["turret", "turntable_horn", *s_horn])
    step("Turret onto the bearing and the spline", ["turret", "turntable_horn"], [], level="precise", dir_=(0, 0, 1), dist=50,
         note="Hub into the bearing's inner ring AND horn onto the spline together",
         how="Servo still at 135°. Hold the turret with the cradle at the back and the round front pointing at the can position "
             "(+Y, toward the work area). Lower it so the hub enters the bearing's inner ring as the horn meets the spline, then press "
             "down evenly until it bottoms.",
         fit="<b>Press fit, inner ring:</b> the hub is drawn 34.3 mm and prints at about 35.0. This fit keeps the turret down on "
             "the spline, so there is <b>no horn centre screw</b> here (it can't be reached under the cradle). Loose: one wrap of "
             "tape on the hub.")
    step("Shoulder servo (MG996R) into the cradle", ["shoulder_servo_MG996R"], s_mg, dir_=(-1, 0, 0), dist=60, hw=[[4, "#8-32 × ½″"]],
         note="Spline first through the window from behind; tabs against the cradle's back face",
         how="Slide the MG996R in from the back (the side away from the links), spline first through the window, until its tabs sit "
             "flat on the cradle. Spline to the link side, lead toward the turret plate. 4 × #8 through the tabs into the cradle's "
             "pilots. Drive them from behind; the top 2 continue into the ear for extra grip.")
    step("Link A on the metal horn, horn on the shoulder", ["link_A", "shoulder_horn"], s_la + [s_hc], level="try", dir_=(1, 0, 0), dist=40,
         hw=[[1, "25T aluminium disc horn (MG996R)"], [2, "M3 × 6 mm"], [1, "horn centre screw (servo bag)"]],
         badge=["MG996R shoulder", "90°"], note="Bolt link A to the horn on the table, then press the horn on at the right angle",
         how=f"1) On the table: lay link A on the aluminium horn with its pivot hole on the horn's centre. Mark two of the horn's "
             f"threaded holes through the link (8 mm out, both on the same side), drill them 3.3 mm, and bolt the link on with 2 × M3 × 6. "
             f"2) Shoulder servo at 90°. Press the horn onto the spline so link A points forward and about <b>{A0:.0f}° below "
             f"horizontal</b> (the nearest spline tooth; 25 teeth = 14.4° per tooth, the rest is fine-tuned in software). 3) Horn "
             f"centre screw through the link's pivot hole into the spline.",
         fit="Re-teach <b>LIFT_DOWN</b> (link at −11°) and <b>LIFT_UP</b> (+11°) in the laptop panel in step 20. The swing is about "
             f"{2 * A0:.0f}° of the servo.")
    step("Link B on the ear", ["link_B", "pivot_B_screw"], [s_lb], level="try", dir_=(1, 0, 0), dist=30,
         hw=[[1, "M3 shoulder screw, 4 mm shoulder × 4 mm"], [1, "M3 nylon washer"]],
         note="Shoulder screw through link B into the ear's insert; the link must swing freely",
         how="Nylon washer between link B and the ear. Shoulder screw through link B into the ear insert, tightened fully: the "
             "smooth shoulder is the bearing surface, so the link turns on it while the screw stays tight.",
         fit="<b>Running fit:</b> link B must swing under its own weight. If it drags, the shoulder is shorter than the bar (3.2 mm) "
             "plus the washer: use a 4 mm shoulder.")
    step("Coupler onto both links", ["coupler", "pivot_A2_screw", "pivot_B2_screw"], s_cp, level="try", dir_=(0, 1, 0), dist=40,
         hw=[[2, "M3 shoulder screw, 4 mm shoulder × 4 mm"]],
         note="2 shoulder screws from the servo side, through the links into the coupler's inserts",
         how="Hold the coupler against the outside of both links' front ends. A shoulder screw goes from the servo side through "
             "each link into the coupler's inserts, lower one first. Do this <b>before</b> the wrist servo: once it's in, its body "
             "blocks the screwdriver.",
         fit=f"<b>The parallelogram test:</b> lift the coupler by hand. It should rise about 16 mm and stay upright (vertical) the whole "
             f"way, with no binding. If it tilts, the links aren't equal: re-drill one with the jig.")
    main13 = claw_steps[4]
    step("Wrist servo into the coupler", ["wrist_servo"], main13["screws"], dir_=(0, 1, 0), dist=45, hw=main13["hw"], badge=main13["badge"],
         note="Body through the coupler's bracket from the front, 2 tab screws",
         how="Body through the coupler's bracket from the front (the claw side), lead toward the links, 2 servo-bag screws "
             "through the tabs. It's the same bracket and position as on the carriage arm, so the claw fits unchanged.")
    claw_show = []
    for st in claw_steps[:4]:                                                                 # main 9-12: claw on the table
        claw_show = sorted(set(claw_show) | set(st["new"]) | set(st["screws"]))
        step(st["title"].replace(" (on the table)", "") + " (on the table)", st["new"], st["screws"], st["how"], level=st["level"],
             dir_=st["dir"], dist=st["dist"], hw=st["hw"], badge=st["badge"], fit=st["fit"], note=st["note"], table=claw_show,
             callouts=st["callouts"], per_part_dir=st["per_part_dir"], glue_=st["glue"], glue_text=st["glue_text"])
    placed.update(claw_show)
    for st in claw_steps[5:]:                                                                 # main 14-15: claw on, bumper
        step(st["title"], st["new"], st["screws"], st["how"], level=st["level"], dir_=st["dir"], dist=st["dist"], hw=st["hw"],
             badge=st["badge"], fit=st["fit"], note=st["note"], callouts=st["callouts"], per_part_dir=st["per_part_dir"],
             glue_=st["glue"], glue_text=st["glue_text"])
    step("Wire it and re-teach the lift", [], [], dir_=None, dist=0,
         note="Same harness and pins as PART E; only the lift angles change",
         how="<b>Wiring:</b> same pins as PART E of the manual: turntable on <b>D9</b> (now the MG90S), lift on <b>D10</b> (now the "
             "MG996R shoulder), wrist D6, gripper D5, same buck supply. The turntable now pulls less current and the lift more, and "
             "the total stays within the supply. <b>Recommended upgrade:</b> a PCA9685 16-channel servo board on its own 6 V supply, "
             "controlled by the Uno over I²C (SDA/SCL, 2 wires). Servo power then never goes near the Uno. <b>Re-teach</b> in the "
             f"laptop panel: LIFT_DOWN = link A at −{A0:.0f}°, LIFT_UP = +{A0:.0f}° (the can rises {H.H_MAX:.1f} mm, level). The "
             "turntable and wrist angles stay as they are.")

    # ---- screwdriver access (as backend/tools/tool_access_check.py): 80 mm shaft behind each head, straight or leaned 4 deg,
    #      against every part already in place at that step
    allshapes = dict(shapes)
    lines.append("SCREWDRIVER ACCESS (80 mm shaft behind each head, vs the parts in place at that step)")
    byname = {x["name"]: x for x in screws}
    for st in steps:
        for nm in st["screws"]:
            x = byname[nm]
            back = cq.Vector(*[-a for a in x["axis"]])
            start = cq.Vector(*x["head"]) + back * (x["head_h"] + 0.3)
            r = 1.5 if x["kind"] in ("sb", "M3", "M3x6", "M3x8") else 2.0
            u = back.cross(cq.Vector(1, 0, 0) if abs(back.x) < 0.9 else cq.Vector(0, 1, 0)).normalized()
            w = back.cross(u)
            dirs = [back] + [back + (u * math.cos(math.radians(45 * k)) + w * math.sin(math.radians(45 * k))) * math.tan(math.radians(4))
                             for k in range(8)]
            later = st["new"][1:]                     # parts fitted after the step's first one (same rule as the main check)
            excl = later[later.index(x["owner"]) + 1:] if x["owner"] in later else (later if st["new"] and x["owner"] == st["new"][0] else [])
            others = [m for m in st["show"] if m in allshapes and m != x["owner"] and m not in excl and group.get(m) != "can"]
            best = None
            for d in dirs:
                sh = cq.Solid.makeCylinder(r, 80, start, d.normalized())
                hits = [m for m in others if sh.intersect(allshapes[m]).Volume() > 1.5]
                if best is None or len(hits) < len(best):
                    best = hits
                if not hits:
                    break
            bad += bool(best)
            lines.append(f"  step {st['n']:>2} {nm} {x['kind']:>4} {x['owner']:<22} {'PASS' if not best else 'BLOCKED by ' + ', '.join(best)}")
    open(os.path.join(ROOT, "cad", "hybrid", "screws.txt"), "w").write("SCREWS (hybrid build)\n" + "\n".join(lines) + "\n")
    print("\n".join(lines[-len([1 for st in steps for _ in st['screws']]) - 1:]))

    groups = {**group}
    for n_ in [p["name"] for p in parts]:
        groups[n_] = group[n_]
    levels = dict(precise=dict(label="PRECISE FIT", color="#c40000",
                               text="Fits that decide whether it works: identical links, bearing press fits. Check each with the real part."),
                  **{"try": dict(label="TRY-FIT", color="#c77700",
                                 text="Test before you tighten: pivots must swing freely, and inserts must sit flush and take a screw.")},
                  easy=dict(label="EASY", color="#1f7a45", text="Straightforward: screw it on."))
    tools = ["Drill + 3.3 mm, 3.4 mm (9/64″), 4.0 mm (5/32″), 6.5 mm (1/4″) bits; hacksaw; file",
             "Soldering iron (for the brass inserts)", "#1 Phillips + small precision screwdriver; 2.5 mm hex key for the shoulder screws",
             "Print first: tower, turret, coupler, link jig (about 8 h in total); the claw parts you already have"]
    data = dict(meshes=meshes, screws=screws, glue=glue, steps=steps,
                printed=sorted(p["name"] for p in parts if p["kind"] == "printed") + ["gripper_frame", "finger_L", "finger_R"],
                names={**{p["name"]: p["name"].replace("_", " ") for p in parts}, **MAIN["names"]}, screw_names=SCREW_NAMES,
                levels=levels, while_waiting=tools, hybrid_build=True, title="Plan D: hybrid build guide",
                motion=dict(kind="parallel", groups=groups, sequence=json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))["sequence"],
                            params=dict(lift_theta0=0, grip_z=P["grip_z"], pivot_x=P["pivot_x"], pivot_y=P["pivot_y"], lift_servo_tip=[0, 0, 0],
                                        link_len=L, a0=A0, pa=list(H.PA), pb=list(H.PB), can_y=P["can_y"], h_max=H.H_MAX, a2_tilt=H.R.LIFT_DEG)))
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/hybrid_build.json ({os.path.getsize(OUT) // 1024} KB), {len(steps)} steps, {len(screws)} screws")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
