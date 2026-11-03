"""Fusion 360 script: import the Concept A assembly, play the firmware sequence, and run
Fusion's own interference check at the end of every move.

How to run (Fusion 360 -> UTILITIES -> ADD-INS -> Scripts and Add-Ins):
  1. Click "+" next to My Scripts, pick the folder backend/cad/fusion_animate, select
     "fusion_animate", and press Run.
  2. When asked, choose cad/step/concept_a_assembly.step. fusion_sequence.json must be in
     the same cad/step/ folder (it is, after running backend/cad/export.py).
  3. Choose Yes for the guided tour (a box explains each motor before its move, slow playback)
     or No for the full run with Fusion's interference check (log: cad/step/fusion_interference_log.txt).
  4. At the end it asks "Play again?" (no re-import needed).

The script opens a NEW design (Direct modeling, so occurrences can be moved freely) and leaves
your other documents alone. Kinematics are identical to model.py / check.py.

NOT YET RUN IN FUSION: this script was written without access to Fusion 360. If an API call
fails, the message box shows which one; the STEP itself opens normally in Fusion and
SolidWorks either way (see cad/README.md for setting up the joints by hand).
"""
import json
import math
import os
import time
import traceback

import adsk.core
import adsk.fusion

ALLOWED = [("turntable_servo_MG996R", "turntable_horn"), ("bearing_6807", "turret_plate"),
           ("lift_crank", "lift_link"), ("lift_crank", "lift_servo_MG90S"), ("wrist_servo", "wrist_horn"),
           ("wrist_servo", "gripper_frame"), ("gripper_servo_SG90", "finger_L"), ("finger_L", "finger_R"),
           ("axle_R", "finger_R")]
GROUPS = ["fixed", "turret", "crank", "lift", "wrist", "finger_L", "finger_R", "can"]


# ---------------- 4x4 matrix helpers (mm) ----------------
def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def ident():
    return [[1 if i == j else 0 for j in range(4)] for i in range(4)]


def trans(x, y, z):
    m = ident()
    m[0][3], m[1][3], m[2][3] = x, y, z
    return m


def rot(point, axis, deg):
    """Rotation by deg about the line through point along unit axis (Rodrigues)."""
    ux, uy, uz = axis
    n = math.sqrt(ux * ux + uy * uy + uz * uz)
    ux, uy, uz = ux / n, uy / n, uz / n
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    C = 1 - c
    R = [[c + ux * ux * C, ux * uy * C - uz * s, ux * uz * C + uy * s, 0],
         [uy * ux * C + uz * s, c + uy * uy * C, uy * uz * C - ux * s, 0],
         [uz * ux * C - uy * s, uz * uy * C + ux * s, c + uz * uz * C, 0],
         [0, 0, 0, 1]]
    px, py, pz = point
    return mat_mul(trans(px, py, pz), mat_mul(R, trans(-px, -py, -pz)))


def inverse_rigid(m):
    r = [[m[j][i] for j in range(3)] for i in range(3)]
    t = [-sum(r[i][k] * m[k][3] for k in range(3)) for i in range(3)]
    return [r[0] + [t[0]], r[1] + [t[1]], r[2] + [t[2]], [0, 0, 0, 1]]


def group_mats(s, cfg):
    gz = cfg["grip_z"]
    _, lty, ltz = cfg["lift_servo_tip"]
    T_turret = rot((0, 0, 0), (0, 0, 1), s["psi"])
    T_crank = mat_mul(T_turret, rot((0, lty, ltz), (1, 0, 0), s["theta"] - cfg["lift_theta0"]))
    T_lift = mat_mul(T_turret, trans(0, 0, s["h"]))
    T_wrist = mat_mul(T_lift, rot((0, 0, gz), (0, 1, 0), s["phi"]))
    T_fR = mat_mul(T_wrist, rot((cfg["pivot_x"], cfg["pivot_y"], 0), (0, 0, 1), -s["alpha"]))
    T_fL = mat_mul(T_wrist, rot((-cfg["pivot_x"], cfg["pivot_y"], 0), (0, 0, 1), s["alpha"]))
    return dict(fixed=ident(), turret=T_turret, crank=T_crank, lift=T_lift, wrist=T_wrist,
                finger_R=T_fR, finger_L=T_fL)


def to_fusion(m):
    """mm 4x4 -> adsk Matrix3D (Fusion's internal unit is cm)."""
    arr = []
    for i in range(4):
        for j in range(4):
            v = m[i][j]
            if j == 3 and i < 3:
                v = v / 10.0
            arr.append(v)
    mx = adsk.core.Matrix3D.create()
    mx.setWithArray(arr)
    return mx


# Guided tour: what each motor does, shown before its move (keys = step labels from fusion_sequence.json)
TOUR = {
    "GRIP": ("MOTOR 4 of 4: GRIPPER  (SG90 servo, pin D5)   20° -> 95°",
             "The SG90 turns the LEFT finger directly: the finger's gear sits on the servo's spline.\n"
             "The left finger's 16-tooth gear meshes with the RIGHT finger's gear, so the right finger turns the\n"
             "same amount the other way. Both arms close together and centre the can.\n\n"
             "The can is pushed against the silicone bumper, so it sits at the same depth every time.\n"
             "The silicone pads squeeze about 0.5–1 N per arm: enough to hold 15 g, far below the ~8 N that dents it."),
    "LIFT": ("MOTOR 2 of 4: LIFT  (MG90S servo, pin D10)   30° -> 75°",
             "The lift servo on the column turns a 20 mm crank. A link pushes the carriage straight up the two\n"
             "6 mm steel rods, sliding on 4 LM6UU linear bearings: 45° of crank = 15.3 mm (0.6 in) of lift.\n\n"
             "Why lift first: gripped at mid-height, the can's corner is 2.74 in from the grip point but only\n"
             "2.41 in above the table. Flipping in place would dig 0.33 in into the table. Lifted 0.6 in, it clears by 0.27 in."),
    "FLIP": ("MOTOR 3 of 4: WRIST  (MG90S servo, pin D6)   0° -> 180°",
             "The wrist servo rolls the whole gripper half a turn about the arm's line. That line passes through\n"
             "the can's centre, so the can turns upside down in place, without moving sideways.\n\n"
             "The code widens this servo's pulse range (500–2500 µs) so an MG90S reaches the full 180°."),
    "TURN": ("MOTOR 1 of 4: TURNTABLE  (MG996R servo, pin D9)   135° -> 45°",
             "The big servo under the base turns the turret 90°. The turret rides on a 6807 ball bearing, which\n"
             "carries the weight and the tipping load, so the servo only has to turn it.\n\n"
             "The can travels on a 5 in (127 mm) circle from START to TARGET: the robot visibly turns 90°."),
    "LOWER": ("MOTOR 2 again: LIFT  75° -> 30°",
              "The carriage comes back down the same 15.3 mm. Because the can was flipped about its own centre,\n"
              "lowering the same distance sets the upside-down can exactly on the table: placed, not dropped."),
    "RELEASE": ("MOTOR 4 again: GRIPPER  95° -> 70°",
                "The arms open only 25°. The gripper is upside down here, so opening fully would swing an arm into\n"
                "the base. 25° is enough: the pads clear the can by about 13 mm. The can stands free, inverted, at TARGET.\n\n"
                "On the real robot the LED now stays on. Homing starts only after you lift the can off and press START."),
    "H-LIFT": ("HOMING 1: lift up (MG90S, D10)", "Raise the arm so the gripper can turn over without touching the table."),
    "H-CLOSE": ("HOMING 2: close the arms (SG90, D5)", "Open arms would sweep through the table while un-flipping, so close them first."),
    "H-WRIST": ("HOMING 3: wrist back to 0° (MG90S, D6)", "The gripper rolls back upright."),
    "H-TURN": ("HOMING 4: turntable back to START (MG996R, D9)", "The turret turns back 90°."),
    "H-LOWER": ("HOMING 5: lower (MG90S, D10)", "Back down to can height."),
    "H-OPEN": ("HOMING 6: open the arms (SG90, D5)", "Ready for the next can."),
}
INTRO = ("HOW IT MOVES: 4 servos, one at a time\n\n"
         "1  Turntable   MG996R  pin D9    turns the whole arm 90°\n"
         "2  Lift        MG90S   pin D10   raises the arm 0.6 in (crank + link on 2 rods)\n"
         "3  Wrist       MG90S   pin D6    rolls the gripper 180°\n"
         "4  Gripper     SG90    pin D5    closes 2 geared arms on the can\n\n"
         "Sequence: GRIP -> LIFT -> FLIP -> TURN -> LOWER -> RELEASE (6.4 s on the real robot).\n"
         "Every move eases in and out (slow - fast - slow) so the light can isn't shaken loose.\n\n"
         "Before each move a box explains which motor moves and why. Press OK to play it.")


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        dlg = ui.createFileDialog()
        dlg.title = "Choose cad/step/concept_a_assembly.step"
        dlg.filter = "STEP (*.step;*.stp)"
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return
        step_path = dlg.filename
        folder = os.path.dirname(step_path)
        cfg = json.load(open(os.path.join(folder, "fusion_sequence.json")))

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent
        im = app.importManager
        im.importToTarget(im.createSTEPImportOptions(step_path), root)
        adsk.doEvents()

        # group occurrences ("grp_turret:1" ...) and the part -> group map
        occ_of = {}
        leaf_group = {}
        for occ in root.allOccurrences:
            nm = occ.name.split(":")[0]
            if nm.startswith("grp_"):
                occ_of[nm[4:]] = occ
        for g, occ in occ_of.items():
            for child in occ.childOccurrences:
                leaf_group[child.entityToken] = (g, child.name.split(":")[0])
        missing = [g for g in GROUPS if g not in occ_of]
        if missing:
            ui.messageBox("Could not find groups: " + ", ".join(missing))
            return

        Y = adsk.core.DialogResults.DialogYes
        YN = adsk.core.MessageBoxButtonTypes.YesNoButtonType
        guided = ui.messageBox("Guided tour?\n\nYes: explain each motor before its move, play slowly.\n"
                               "No: play the full sequence and run Fusion's interference check.",
                               "Concept A", YN) == Y
        if guided:
            ui.messageBox(INTRO, "Concept A: how it moves")
        while True:
            n_hits = play(app, ui, design, cfg, occ_of, leaf_group, folder, guided)
            if not guided:
                ui.messageBox(("PASS: no interference between moving groups at the end of any move.\n"
                               if n_hits == 0 else f"{n_hits} interference(s) found.\n") +
                              "Log: " + os.path.join(folder, "fusion_interference_log.txt"))
            if ui.messageBox("Play again?", "Concept A", YN) != Y:
                break
    except Exception:
        ui.messageBox("Failed:\n" + traceback.format_exc())


def play(app, ui, design, cfg, occ_of, leaf_group, folder, guided):
    """One pass through the sequence. Guided: explain each step first, slower, no interference check."""
    if True:
        log = []
        grip_wrist = None
        T_can = ident()
        prev_label = None
        n_hits = 0
        samples = cfg["samples"]
        for k, s in enumerate(samples):
            if guided and s["label"] != prev_label and s["label"] in TOUR:
                title, text = TOUR[s["label"]]
                ui.messageBox(text, title)
            prev_label = s["label"]
            M = group_mats(s, cfg)
            if s["attached"] and grip_wrist is None:
                grip_wrist = M["wrist"]
            if s["attached"]:
                T_can = mat_mul(M["wrist"], inverse_rigid(grip_wrist))
            M["can"] = T_can
            for g, occ in occ_of.items():
                occ.transform = to_fusion(M[g])
            app.activeViewport.refresh()
            adsk.doEvents()
            time.sleep(0.09 if guided else 0.03)

            last_of_step = (k + 1 == len(samples)) or samples[k + 1]["label"] != s["label"]
            if last_of_step and not guided:
                ents = adsk.core.ObjectCollection.create()
                for g, occ in occ_of.items():
                    if g == "can" and s["label"].startswith("H-"):
                        continue
                    for child in occ.childOccurrences:
                        ents.add(child)
                try:
                    res = design.analyzeInterference(design.createInterferenceInput(ents))
                    for r in res:
                        a = leaf_group.get(r.entityOne.entityToken, ("?", r.entityOne.name))
                        b = leaf_group.get(r.entityTwo.entityToken, ("?", r.entityTwo.name))
                        if a[0] == b[0]:
                            continue                      # same rigid group: bolted / pressed together
                        pair = (a[1], b[1])
                        if pair in ALLOWED or pair[::-1] in ALLOWED:
                            continue
                        if "test_can" in pair and s["attached"] and any(x.startswith("finger_") for x in pair):
                            continue
                        vol = r.interferenceBody.volume * 1000 if r.interferenceBody else 0.0   # cm^3 -> mm^3
                        if vol > 1.0:
                            n_hits += 1
                            log.append(f"{s['label']}: {pair[0]} x {pair[1]} {vol:.1f} mm^3")
                except Exception:
                    log.append(f"{s['label']}: interference API failed: {traceback.format_exc().splitlines()[-1]}")
                log.append(f"end of {s['label']}: checked")
        if not guided:
            with open(os.path.join(folder, "fusion_interference_log.txt"), "w") as f:
                f.write("\n".join(log) + "\n")
        return n_hits
