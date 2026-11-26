"""'Proposed fixes' tab of the 3D guide: every change since the parts printed on 23 Nov (reprint_5), the new part in
its normal colour and the old one as a red ghost.

    python3.13 backend/cad/fixes_view.py   ->  viewer/data/fixes.json   (viewer/assembly.html?data=fixes)

The old parts come from backend/cad/build/old_parts.json: the CAD at commit da6e43b (what reprint_5 was made from),
tessellated once with that commit's model.py. Regenerate it only if the baseline should change.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import visual as V  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "fixes.json")
OLD = json.load(open(os.path.join(HERE, "build", "old_parts.json")))
RED = "#e0352b"


def main():
    P = M.P
    meshes, screws, glue, _ = V.build()
    drop = {x["name"] for x in screws if x["owner"] in ("turntable_horn", "wrist_horn") and x["kind"] == "M3"}
    screws = [x for x in screws if x["name"] not in drop]
    meshes = [m for m in meshes if m["owner"] not in drop and m["kind"] != "screw" and m["kind"] != "glue"]
    screws, glue = [], []
    out = []
    for m in meshes:
        sh = m["shape"].val() if hasattr(m["shape"], "val") else m["shape"]
        v, t = sh.tessellate(0.12, 0.35)
        out.append(dict(owner=m["owner"], kind=m["kind"], color=m["color"],
                        v=[round(c, 1) for vv in v for c in (vv.x, vv.y, vv.z)], f=[i for tt in t for i in tt]))
    for n, g in OLD.items():
        out.append(dict(owner="old_" + n, kind="old", color=RED, v=g["v"], f=g["f"]))
    owners = {m["owner"] for m in out}
    column = [n for n in owners if not n.startswith("old_")]
    LM = ["LM6UU_L1", "LM6UU_R1", "LM6UU_L2", "LM6UU_R2"]
    base_set = ["base", "bearing_6807", "turntable_servo_MG996R", "turntable_horn", "turret_plate"]
    tc = P["turret_z0"] - 3.0
    fz_new = tc - 42.9 + 26.5 + 2.5

    def step(n, title, new, show, how, fit="", level="try", callouts=()):
        return dict(n=n, title=title, new=new, show=sorted(set(show) | set(new)), dir=None, per_part_dir={}, dist=0, hw=[],
                    badge=None, note="", screws=[], glue=[], fit=fit, how=how, glue_text="", level=level,
                    callouts=[dict(at=list(a), text=t) for a, t in callouts])
    steps = [
        step(1, "Base: MG996R at its real height (blocks 5 mm shorter)", ["base", "turntable_servo_MG996R"],
             base_set + ["old_base", "old_turntable_servo_MG996R"],
             "The MG996R is <b>42.9 mm overall</b> (case 38.1 + spline), not 47.9: in the old CAD its spline was 5 mm too high, so on the "
             "real servo it stops short of the horn under the turret plate. The 2 blocks its tabs screw into are now 5 mm shorter, "
             "so the servo sits 5 mm higher and the spline reaches the horn.",
             "<b>Base already printed:</b> sand <b>5 mm off the bottom face of both blocks</b>, equally (rotary tool, low speed), "
             "then #8 × ⅜″ screws (or ½″ + a washer).", "precise",
             callouts=[((0, -30, fz_new), "servo blocks: −5 mm on their bottom face")]),
        step(2, "Wrist servo 3.5 mm further out", ["carriage_arm", "wrist_servo", "gripper_frame"],
             base_set + ["old_carriage_arm", "old_wrist_servo", "old_gripper_frame"] + LM,
             "The real MG90S body is 32.7 mm long (the CAD had 28.5): its end reached the base's bearing tower whenever the carriage "
             "was low. The wrist servo now sits 3.5 mm further out: the arm beam is 3.5 mm longer, the gripper frame 3.5 mm shorter. "
             "Fingers, gears and the can position are unchanged.", "Both parts are on reprint_d.", "easy"),
        step(3, "Carriage: printed on its side, gussets, pockets", ["carriage_arm"] + LM, ["old_carriage_arm"],
             "The old carriage snapped where the arm meets the wrist bracket (printed standing, the layers ran across the arm). "
             "Now: printed on its side (layers along the arm), 2 side gussets at that corner, 5 walls + 30 % infill, LM6UU pockets "
             "with a pointed top (no support inside) and ~12.25 mm as printed, and the link's pivot block notched so the upper "
             "bearing goes in.", "", "precise"),
        step(4, "Lift: the bagged horn's last hole + a new link", ["lift_crank", "lift_link"],
             ["spine", "lift_servo_MG90S", "top_cap", "carriage_arm", "rod_L", "rod_R", "old_lift_crank", "old_lift_link"],
             "No horn in the servo bag reaches 20 mm, so the crank now uses the single-arm horn's <b>last hole (14 mm)</b>. A new, "
             "longer link (11.2 mm between holes) and a bigger swing (−34° … +34°, firmware LIFT_UP 98) keep the lift at 15.7 mm "
             "(≥ 15.2 required); the crank top stays 0.7 mm under the top cap.", "The new link is on reprint_d (a few minutes).", "try"),
        step(5, "Gripper frame: bigger horn opening, wings cut off", ["gripper_frame"],
             ["finger_L", "finger_R", "axle_R", "gripper_servo_SG90", "gripper_horn", "old_gripper_frame"],
             "Horn opening Ø16 (was 14) so a screwdriver reaches the horn screws; the plate wings that nothing touches are cut "
             "off (−27 % plastic). Old right finger and the new left finger both fit.", "", "easy"),
        step(6, "Horns from the servo bags", ["lift_crank", "wrist_horn", "gripper_horn"],
             ["gripper_frame", "finger_L", "finger_R", "wrist_servo", "carriage_arm", "spine", "lift_servo_MG90S", "lift_link"],
             "<b>Lift:</b> single-arm horn, link on its last hole. <b>Wrist:</b> cross horn, drill 1/16″ through 4 of its holes "
             "into the frame flange. <b>Gripper:</b> double-arm horn with the arms cut to 7 mm, drill 1/16″ through its 2 holes into "
             "the left gear. The horn is its own drill guide, so the holes always line up.", "", "easy"),
        step(7, "Spine: room for the screw heads", ["spine"], ["turret_plate", "old_spine"],
             "The #6 pan heads (Ø6.6) hit the spine wall 2 mm from the holes: a half-round notch beside each hole.",
             "<b>Spine already printed:</b> file or Dremel a 1.5 mm half-round notch next to each of the 2 holes.", "easy"),
    ]
    vm = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))
    gof = {x["name"]: g for g, lst in vm["groups"].items() for x in lst}
    groups = {o: gof.get(o, "fixed") for o in owners}
    pv = vm["params"]
    notes = json.load(open(os.path.join(ROOT, "backend", "tools", "assembly_notes.json")))
    levels = json.loads(json.dumps(notes["levels"]))
    levels["precise"]["text"] = "Decides whether it fits: do this one carefully."
    levels["try"]["text"] = "Check it moves freely after."
    levels["easy"]["text"] = "Simple."
    names = dict(notes["names"], **{"old_" + k: "OLD " + notes["names"].get(k, k) for k in OLD})
    data = dict(meshes=out, screws=[], glue=[], steps=steps, printed=sorted({m["owner"] for m in out if m["kind"] == "printed"}),
                names=names, screw_names=notes["screw_names"], levels=levels, fixes=True, title="Proposed fixes (new vs old)",
                while_waiting=[],
                motion=dict(groups=groups, sequence=vm["sequence"],
                            params=dict(lift_theta0=pv["lift_theta0"], grip_z=pv["grip_z"], pivot_x=pv["pivot_x"], pivot_y=pv["pivot_y"],
                                        lift_servo_tip=list(P["lift_servo_tip"]))))
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"wrote viewer/data/fixes.json: {len(out)} meshes, {len(steps)} fixes, {os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
