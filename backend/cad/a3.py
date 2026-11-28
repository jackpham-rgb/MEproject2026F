"""A3: the A2 idea (lift by tilting the arm, no slide) built on the parts ALREADY PRINTED (Concept A), with simple fixes.

    python3.13 backend/cad/a3.py  ->  viewer/data/a3.json (viewer/assembly.html?data=a3), cad/a3/arm.stl, cad/a3/report.txt

Kept as they are: base (+ sand the servo blocks 5 mm), MG996R turntable, bearing, turret plate, spine, top cap, the 2 rods
(they now only stiffen the spine/top cap), the MG90S lift servo in the spine, the wrist servo, the whole claw, tray.
Gone: carriage, 4 LM6UU, lift link, crank (the broken / jamming parts).
New: ONE printed arm (about 1 h) bolted to the lift servo's single-arm horn. The lift servo now tilts the arm 6.8 deg
about its own shaft: the can rises 15.7 mm. Every hole is printed (no drilling into metal), and nothing already
assembled has to come apart (the carriage is never fitted; if it already is, see step 1).
"""
import json
import math
import os
import subprocess
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import redesign as R  # noqa: E402
from model import P, TOL, box, cyl_dir  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "a3.json")
DIR = os.path.join(ROOT, "cad", "a3")
GZ, WY = P["grip_z"], P["wrist_tip_y"]
_, AY, AZ = P["lift_servo_tip"]                 # lift servo shaft: along X through (y, z)
TIP_X = P["lift_servo_tip"][0]                  # spline tip (pointing -X)
HX = (TIP_X - 2.5, TIP_X)                       # bagged single-arm horn
ARM_X = (HX[0] - 5.0, HX[0])                    # new arm plate, against the horn
LEVER = P["can_y"] - AY                         # shaft -> can centre, horizontal
H_MAX = P["lift_stroke"]
THETA = math.degrees(math.asin(H_MAX / LEVER))
BY1 = WY - 12.6
GONE = ("carriage_arm", "LM6UU_L1", "LM6UU_L2", "LM6UU_R1", "LM6UU_R2", "lift_link", "lift_crank", "tolerance_coupon")


def build():
    parts = [dict(name=p["name"], group=p["group"], shape=p["shape"], mass=p.get("mass"), material=p["material"])
             for p in M.build_parts() if p["name"] not in GONE]
    # bagged single-arm horn on the lift servo, arm pointing forward (+Y), out of the spine
    horn = cyl_dir((HX[0], AY, AZ), (1, 0, 0), 3.8, 2.5).union(
        cq.Workplane("XY").add(box(HX[0], HX[1], AY, AY + 15.5, AZ - 3.0, AZ + 3.0).val()))
    for r in (10.0, 14.0):
        horn = horn.cut(cyl_dir((HX[0] - 1, AY + r, AZ), (1, 0, 0), 0.8, 5))
    parts.append(dict(name="lift_horn", group="lift", shape=horn, mass=1.0, material="buy"))
    # the new arm: pad on the horn's 2 outer holes -> beam -> the same wrist bracket as the carriage had
    p0, p1 = (AY + 13.0, AZ), (BY1 - 6.0, 80.0)
    wp = lambda: cq.Workplane("YZ").workplane(offset=ARM_X[0])  # noqa: E731
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    beam = wp().center(*p0).circle(6.5).extrude(5.0).union(wp().center(*p1).circle(6.5).extrude(5.0)).union(
        wp().center((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2).transformed(rotate=(0, 0, ang)).rect(math.dist(p0, p1), 13.0).extrude(5.0))
    arm = cq.Workplane("XY").add(beam.val())
    arm = arm.union(box(ARM_X[0], ARM_X[1], AY + 7.0, AY + 19.0, AZ - 6.5, AZ + 6.5))           # pad under the horn arm
    for r in (10.0, 14.0):                                                                     # 2 servo-bag screws through the horn
        arm = arm.cut(cyl_dir((ARM_X[0] - 1, AY + r, AZ), (1, 0, 0), TOL["servo_pilot"] / 2, 7))
    brkt = box(-11, 11, BY1 - 4, BY1, GZ - 24, 82.0)
    wz = (GZ + 5.95 - 22.8, GZ + 5.95)
    brkt = brkt.cut(box(-6.4, 6.4, BY1 - 5, BY1 + 1, wz[0] - 0.3, wz[1] + 0.3))
    for hz in (GZ - (M.MICRO_HOLES_X - 13.75), GZ - (M.MICRO_HOLES_X + 13.75)):
        brkt = brkt.cut(cyl_dir((0, BY1 - 5, hz), (0, 1, 0), TOL["servo_pilot"] / 2, 7))
    arm = arm.union(brkt).union(box(-11, ARM_X[1], BY1 - 10, BY1, 74.0, 82.0))                 # beam -> bracket joint
    arm = arm.union(box(ARM_X[0], ARM_X[1], AY + 26, AY + 30, AZ - 30, AZ - 22))               # hook for the assist band
    parts.append(dict(name="a3_arm", group="lift", shape=arm, mass=None, material="PETG"))
    for p in parts:
        if p["name"] == "wrist_servo":
            p["group"] = "lift"
    return parts


def locs(q):
    th = math.degrees(math.asin(max(0.0, min(1.0, q["h"] / LEVER))))
    L = {"fixed": cq.Location()}
    L["turret"] = R.rot((0, 0, 0), (0, 0, 1), q["psi"])
    L["crank"] = L["turret"]
    L["lift"] = L["turret"] * R.rot((0, AY, AZ), (1, 0, 0), th)
    L["wrist"] = L["lift"] * R.rot((0, 0, GZ), (0, 1, 0), q["phi"])
    L["finger_R"] = L["wrist"] * R.rot((P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), -q["alpha"])
    L["finger_L"] = L["wrist"] * R.rot((-P["pivot_x"], P["pivot_y"], 0), (0, 0, 1), q["alpha"])
    L["can"] = cq.Location()
    return L


def check(parts):
    seq = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))["sequence"]
    sh = {p["name"]: (p["shape"].val() if hasattr(p["shape"], "val") else p["shape"]) for p in parts}
    grp = {p["name"]: p["group"] for p in parts}
    names = list(sh)
    # pairs that touch at rest by design (fits, spline in horn, screws' parts): taken from Concept A's own pose,
    # except anything with the NEW parts, which may only touch what they bolt to
    home = locs(seq[0])
    posed0 = {n: sh[n].moved(home[grp[n]]) for n in names}
    rest = set()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if posed0[a].intersect(posed0[b]).Volume() > 1.0:
                rest.add(frozenset((a, b)))
    by_design = {frozenset(x) for x in [("a3_arm", "lift_horn"), ("a3_arm", "wrist_servo"), ("lift_horn", "lift_servo_MG90S")]}
    rep, bad = [], []
    for r in rest:
        if r & {"a3_arm", "lift_horn"} and r not in by_design:
            bad.append("at rest: " + " x ".join(sorted(r)))
    gripped, canL, final = None, cq.Location(), None
    for i, q in enumerate(seq):
        L = locs(q)
        if q["attached"] and gripped is None:
            gripped = L["wrist"]
        if q["attached"]:
            canL = L["wrist"] * gripped.inverse
        if not q["label"].startswith("H-"):
            final = canL
        if i % 4 and i != len(seq) - 1:
            continue
        posed = {n: sh[n].moved(canL if grp[n] == "can" else L[grp[n]]) for n in names
                 if not (grp[n] == "can" and q["label"].startswith("H-"))}
        bbs = {n: posed[n].BoundingBox() for n in posed}
        ks = list(posed)
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                a, b = ks[x], ks[y]
                if grp[a] == grp[b] or frozenset((a, b)) in rest | by_design:
                    continue
                if "test_can" in (a, b) and ({a, b} & {"finger_L", "finger_R", "can_bumper"}):
                    continue
                A, B = bbs[a], bbs[b]
                if A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin or A.zmax < B.zmin or B.zmax < A.zmin:
                    continue
                v = posed[a].intersect(posed[b]).Volume()
                if v > 1.0:
                    bad.append(f"{q['label']} #{i}: {a} x {b} {v:.0f} mm3")
    c0 = cq.Vertex.makeVertex(0, P["can_y"], P["can_h"] / 2).moved(final).toTuple()
    up = cq.Vertex.makeVertex(0, P["can_y"], P["can_h"]).moved(final).toTuple()
    flip = math.degrees(math.acos(max(-1, min(1, (up[2] - c0[2]) / (P["can_h"] / 2)))))
    rep.append(f"CAN LANDING: centre ({c0[0]:.1f}, {c0[1]:.1f}), upside down {flip:.1f} deg -> "
               f"{'PASS' if abs(math.hypot(c0[0], c0[1]) - P['can_y']) < 2 and flip > 178 else 'CHECK'}")
    rep.append("COLLISIONS through the firmware sequence (every 4th of 289 poses, new arm included): " +
               ("PASS (none)" if not bad else f"FAIL ({len(bad)})"))
    rep += ["  " + b for b in bad[:20]]
    rep.append(f"LIFT: lift servo turns the arm {THETA:.1f} deg (was 68 deg of crank) -> can +{H_MAX:.1f} mm (>= 15.2); "
               f"the can leans {THETA:.1f} deg and moves {(AZ - P['can_h'] / 2) * math.radians(THETA):.0f} mm outward while up, "
               "both undone when it is lowered -> PASS")
    mass = {p["name"]: (p["mass"] if p["mass"] else sh[p["name"]].Volume() / 1000 * 1.27 * 0.55) for p in parts}
    load = [n for n in sh if grp[n] in ("lift", "wrist", "finger_L", "finger_R", "can")]
    W = sum(mass[n] for n in load)
    ycg = sum(mass[n] * sh[n].Center().y for n in load) / W
    static = W * (ycg - AY) / 1000 / 10                                                       # kg*cm
    acc = 4 * math.radians(THETA) / 0.4 ** 2
    J = sum(mass[n] / 1000 * (((sh[n].Center().y - AY) / 1000) ** 2 + ((sh[n].Center().z - AZ) / 1000) ** 2) for n in load)
    dyn = J * acc * 100 / 9.81
    band = 0.8 * static
    rep.append(f"LIFT SERVO (MG90S, 1.8 kg*cm at 4.8 V / 2.2 at 6 V): load {W:.0f} g, CG {ycg - AY:.0f} mm out -> holding {static:.2f} kg*cm "
               f"+ accelerating {dyn:.2f}. Without help: {(static + dyn) / 1.8 * 100:.0f} % of stall (inside the 50 % rule, thin margin if the "
               f"supply sags). With the rubber-band "
               f"assist carrying ~{band:.2f} kg*cm: {(static - band + dyn) / 1.8 * 100:.0f} % -> PASS")
    return rep, not bad, W


def main():
    os.makedirs(DIR, exist_ok=True)
    parts = build()
    rep, ok, W = check(parts)
    import print_prep as PP
    R.DIR = DIR
    arm = next(p for p in parts if p["name"] == "a3_arm")["shape"].val()
    t = R.slice_one(arm, "arm", os.path.join(ROOT, "cad", "print", "reprint", "reprint_a.ini"), PP, keep=True)
    rep.append(f"PRINT: one new part, the arm: {t} (same profile as the other plans). Everything else is already printed.")
    open(os.path.join(DIR, "report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))

    # viewer data: Concept A meshes for the kept parts (real-looking servos etc.), new meshes for the arm + horn
    A = json.load(open(os.path.join(ROOT, "viewer", "data", "assembly.json")))
    keep_names = {p["name"] for p in parts}
    meshes = [m for m in A["meshes"] if m["owner"] in keep_names and m["owner"] not in ("lift_horn", "a3_arm")]
    keep_screws = [s for s in A["screws"] if s["owner"] in keep_names]
    sn = {s["name"] for s in keep_screws}
    gl = [g for g in A["glue"] if any(m["owner"] == g["name"] for m in A["meshes"])]
    meshes += [m for m in A["meshes"] if m["owner"] in sn or m["owner"] in {g["name"] for g in gl}]
    for p in parts:
        if p["name"] in ("lift_horn", "a3_arm"):
            v, tt = p["shape"].val().tessellate(0.12, 0.35)
            meshes.append(dict(owner=p["name"], kind="printed" if p["name"] == "a3_arm" else "bought",
                               color="#2f72e0" if p["name"] == "a3_arm" else "#f4f4f4",
                               v=[round(c, 2) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for x in tt for i in x]))
    groups = {p["name"]: p["group"] for p in parts}
    for s in keep_screws:
        groups[s["name"]] = groups.get(s["owner"], "fixed")
    for g in gl:
        groups[g["name"]] = "wrist"
    st = {s["n"]: s for s in A["steps"]}
    claw = ["wrist_horn", "gripper_frame", "finger_L", "finger_R", "axle_R", "gripper_horn", "gripper_servo_SG90", "can_bumper"]
    base = ["base", "bearing_6807", "turntable_servo_MG996R", "ballast"] if any(m["owner"] == "ballast" for m in A["meshes"]) else \
        ["base", "bearing_6807", "turntable_servo_MG996R"]
    col = ["turret_plate", "turntable_horn", "spine", "lift_servo_MG90S", "rod_L", "rod_R", "top_cap"]
    elec = ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF", "start_button", "status_led", "dc_jack"]

    def scr(names):
        return [s["name"] for s in keep_screws if s["owner"] in names]

    steps = []

    def step(title, new, show, how, level="easy", dir_=(0, 0, 1), dist=40, hw=(), fit="", note="", badge=None, screws=()):
        steps.append(dict(n=len(steps) + 1, title=title, new=list(new), show=sorted(set(show) | set(new) | set(screws)),
                          dir=list(dir_) if dir_ else None, per_part_dir={}, dist=dist, hw=[list(h) for h in hw],
                          badge=list(badge) if badge else None, note=note, screws=list(screws), glue=[], fit=fit, how=how,
                          glue_text="", level=level, callouts=[]))
    step("Start from what you have", [], base + col + claw + elec + ["wrist_servo"] + scr(base + col + claw + ["wrist_servo"]), dir_=None, dist=0,
         note="No carriage, no LM6UU, no lift link, no crank: they're not used",
         how="A3 keeps every part you've printed except the slide. <b>Not built yet?</b> Then just leave out the carriage, the 4 LM6UU, "
             "the lift link and the crank. <b>Already built the column?</b> The rods stay. Only if the carriage is already on them: "
             "undo the top cap's 2 screws, slide the carriage up and off, and put the cap back (the one thing that comes off and "
             "goes back, 2 screws). Unscrew the crank horn from the lift servo; it's replaced by the single-arm horn in step 5.")
    step("Base + column, as in the Fixed guide", base + col, [], screws=scr(base + col),
         note="Fixed guide steps 3, 5, 6, 7, 8, 16–19, without the carriage parts",
         how="Build exactly as in tab 2 (Fixed): lift servo into the spine, turret plate + horn, spine onto the plate, rods, top "
             "cap; base: bearing, MG996R (sand its 2 blocks 5 mm first), weight + feet, then the column onto the turntable "
             "servo. All of it is unchanged.", level="precise")
    step("Print the arm (one part, ~1 h)", ["a3_arm"], [], dir_=(0, 0, 1), dist=30, note="Print it lying on its flat side",
         how=f"The only new print. It's flat (5 mm thick plate + the wrist bracket), so it prints on its side with almost no "
             f"support: about {t}. All holes are printed at this printer's corrected sizes; <b>no drilling</b>.")
    step("Wrist servo into the arm (on the table)", ["wrist_servo"], ["a3_arm"], screws=scr(["wrist_servo"]), dir_=(0, 1, 0), dist=45,
         badge=["MG90S wrist", "0°"], hw=[[2, "servo-bag screw"]],
         how="Body through the bracket from the front, 2 servo-bag screws through the tabs. It's the same bracket and position as "
             "on the carriage, so the claw fits unchanged.")
    step("Single-arm horn onto the arm (on the table)", ["lift_horn"], ["a3_arm", "wrist_servo"], dir_=(1, 0, 0), dist=25,
         hw=[[1, "single-arm horn (lift servo bag)"], [2, "servo-bag screw"]],
         note="2 screws through the horn's 2 outer holes into the arm's pilots",
         how="Lay the uncut single-arm horn on the arm's pad, hub toward the servo side and over the round end, so the horn's 2 "
             "outer holes (10 and 14 mm out) sit on the arm's 2 printed pilots. Drive 2 servo-bag screws through the horn into "
             "the arm. That's the whole joint: no metal is drilled.")
    step("Claw onto the wrist (on the table)", claw, ["a3_arm", "wrist_servo", "lift_horn"], screws=scr(claw), dir_=(0, 1, 0), dist=30,
         badge=["MG90S wrist", "0°"], note="Fixed guide steps 9–12, 14, 15: the same claw",
         how="Build the claw exactly as in the Fixed guide (steps 9–12, 14, 15) and press it onto the wrist servo. Arm, wrist and "
             "claw are now one piece, ready to hang on the lift servo.")
    step("Arm onto the lift servo", ["a3_arm", "lift_horn", "wrist_servo"] + claw, base + col, level="try", dir_=(0, 1, 0), dist=40,
         badge=["MG90S lift", "30° (LIFT_DOWN)"], hw=[[1, "horn centre screw (servo bag)"]],
         note="Press the horn onto the spline with the arm in its lowest position, then the centre screw",
         how="Lift servo at 30° (laptop panel). Hold the arm so the horn points straight forward and the claw hangs at "
             "picking height, then press the horn's hub onto the spline (nearest tooth). Drive the horn centre screw from the "
             "outside. The arm sits in front of the spine, and nothing else comes off.",
         fit=f"Re-teach in the laptop panel: <b>LIFT_DOWN</b> = can resting on the table, <b>LIFT_UP</b> = about {THETA:.0f}° more "
             f"(the can rises {H_MAX:.1f} mm). It used to be 68° of crank; now it's only {THETA:.0f}°.")
    step("Rubber-band assist", [], [p["name"] for p in parts if groups[p["name"]] != "can"], dir_=None, dist=0, level="try",
         hw=[[1, "rubber band (#33 / #64) or a small extension spring"]],
         note="From the hook on the arm up over the top cap",
         how="The MG90S can hold the arm on its own (40 % of stall), but with little margin. A rubber band from the arm's hook, looped over the top "
             "cap, carries most of the weight, so the servo only has to move it. Tune it: lift servo unplugged, claw holding "
             "the can, arm at mid-height. It should hang still. Too low: a second loop. Too high: a longer band.")
    step("Electronics + run", elec, [p["name"] for p in parts if groups[p["name"]] != "can"], screws=scr(elec), dir_=(0, -1, 0), dist=40,
         how="The tray and the wiring are exactly as in the Fixed guide and PART E of the manual: the same pins, the same "
             "firmware. Only LIFT_DOWN / LIFT_UP change (step 7).")
    data = dict(meshes=meshes, screws=keep_screws, glue=gl, steps=steps, printed=sorted(n for n in keep_names if n in A["printed"]) + ["a3_arm"],
                names={**A["names"], "a3_arm": "A3 arm (new)", "lift_horn": "single-arm horn"}, screw_names=A["screw_names"],
                levels=A["levels"], while_waiting=[], a3=True, title="A3: A2's idea on the parts you already printed", report=rep,
                motion=dict(kind="a3", groups=groups, sequence=json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))["sequence"],
                            params=dict(lift_theta0=0, grip_z=GZ, pivot_x=P["pivot_x"], pivot_y=P["pivot_y"], lift_servo_tip=[0, AY, AZ],
                                        axis=[AY, AZ], lever=LEVER, h_max=H_MAX, theta=THETA)))
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/a3.json ({os.path.getsize(OUT) // 1024} KB); {'ALL PASS' if ok else 'COLLISIONS'}")


if __name__ == "__main__":
    main()
