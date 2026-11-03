"""Fusion 360 script: close-up animation of the Concept A claw (gripper) only.

How to run (Fusion 360 -> Shift+S, or UTILITIES -> ADD-INS -> Scripts and Add-Ins):
  1. Click "+" and pick this folder (it must be named fusion_claw), select "fusion_claw", Run.
  2. When asked, choose claw.step. claw_sequence.json must be in the same folder
     (both come from cad/claw/).
  3. An explanation box appears first. Press OK and the claw plays: open -> close on the can ->
     hold -> release 25° -> open fully. The step name and servo angle show in the progress bar.
  4. "Play again?" at the end replays without re-importing.

The arm positions are precomputed in claw_sequence.json (same kinematics and firmware angles as
the robot), so this script only applies them.
NOT YET RUN IN FUSION: written without access to Fusion 360; if an API call fails, the message box
says which one.
"""
import json
import math
import os
import time
import traceback

import adsk.core
import adsk.fusion

INTRO = ("THE CLAW: one SG90 servo (pin D5), two geared arms\n\n"
         "1. The SG90 turns the LEFT arm directly: the arm's gear sits on the servo's spline.\n"
         "2. The left gear (16 teeth) meshes with the RIGHT arm's gear, which turns freely on a screw axle.\n"
         "   Meshed gears turn opposite ways by the same angle, so both arms close together and\n"
         "   centre the can.\n"
         "3. The can stands against a silicone bumper, so it sits at the same depth every time.\n"
         "4. Silicone-lined pads squeeze about 0.5–1 N per arm: enough to hold the 15 g can,\n"
         "   far below the ~8 N that dents it.\n"
         "5. Release opens only 25°: on the robot the claw is upside down there, and opening fully\n"
         "   would swing an arm into the base. 25° still swings the pads ~13 mm clear of the can.\n\n"
         "Servo angles: open 20°, closed 95°, release 70°.\n"
         "Tip: orbit to look down on the gears before pressing OK.")


def rot_z(px, py, deg):
    """4x4 (mm) rotation by deg about the vertical line through (px, py), at full precision."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, -s, 0.0, px - c * px + s * py],
            [s, c, 0.0, py - s * px - c * py],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def set_transform(occ, mx):
    """Move an occurrence; fall back to transform2 (root-relative) if Fusion rejects transform."""
    try:
        occ.transform = mx
    except Exception:
        occ.transform2 = mx


def to_fusion(m):
    """mm 4x4 (list of rows) -> adsk Matrix3D (Fusion's internal unit is cm)."""
    arr = []
    for i in range(4):
        for j in range(4):
            v = m[i][j]
            if j == 3 and i < 3:
                v = v / 10.0
            arr.append(v)
    mx = adsk.core.Matrix3D.create()
    if not mx.setWithArray(arr):
        raise RuntimeError("Matrix3D.setWithArray rejected the matrix")
    return mx


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        dlg = ui.createFileDialog()
        dlg.title = "Choose claw.step (cad/claw/)"
        dlg.filter = "STEP (*.step;*.stp)"
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return
        step_path = dlg.filename
        cfg = json.load(open(os.path.join(os.path.dirname(step_path), "claw_sequence.json")))

        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent
        im = app.importManager
        im.importToTarget(im.createSTEPImportOptions(step_path), root)
        adsk.doEvents()

        occ = {}
        for o in root.allOccurrences:
            nm = o.name.split(":")[0]
            if nm.startswith("grp_"):
                occ[nm[4:]] = o
        if "finger_L" not in occ or "finger_R" not in occ:
            ui.messageBox("Could not find grp_finger_L / grp_finger_R in the STEP. Found: " + ", ".join(occ))
            return
        try:
            app.activeViewport.fit()
        except Exception:
            pass
        ui.messageBox(INTRO, "Concept A: how the claw works")

        Y = adsk.core.DialogResults.DialogYes
        YN = adsk.core.MessageBoxButtonTypes.YesNoButtonType
        samples = cfg["samples"]
        dt = cfg.get("frame_dt", 0.04)
        px, py = cfg["pivot_x"], cfg["pivot_y"]
        while True:
            bar = None
            try:
                bar = ui.progressBar
                bar.show("Claw", 0, len(samples), False)
            except Exception:
                bar = None
            for k, s in enumerate(samples):
                a = s["alpha"]                       # arm opening angle (0 = closed on the can)
                set_transform(occ["finger_L"], to_fusion(rot_z(-px, py, a)))
                set_transform(occ["finger_R"], to_fusion(rot_z(px, py, -a)))
                if bar is not None:
                    try:
                        bar.message = f"{s['label']}: servo {s['grip']:.0f}°   ({cfg['captions'].get(s['label'], '')})"
                        bar.progressValue = k + 1
                    except Exception:
                        bar = None
                app.activeViewport.refresh()
                adsk.doEvents()
                time.sleep(dt)
            if bar is not None:
                try:
                    bar.hide()
                except Exception:
                    pass
            if ui.messageBox("Play the claw again?", "Concept A claw", YN) != Y:
                break
    except Exception:
        ui.messageBox("Failed:\n" + traceback.format_exc())
