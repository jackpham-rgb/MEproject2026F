# Economy printing: only the quality each part needs

Not every part needs the same settings. The base is a big hidden box: coarse layers and 10 % infill are fine. The finger gears must mesh: they get slow, accurate outer walls. We accept small flaws on the rough parts and fix the few fits that matter with sandpaper, a drill or a knife (the fix-up table below).

**Result (sliced in PrusaSlicer, every part): 36 h 59 → 23 h 12 of printing (−37 %), 387 g → 345 g of PETG (−11 %).** Less heating time = less energy.

## The three profiles

| Profile | Layer | Walls | Top / bottom | Infill | Speeds (outer / inner / infill, mm/s) | For |
|---|---|---|---|---|---|---|
| **DRAFT** | 0.28 mm | 2 | 3 / 3 | 10% grid | 45 / 60 / 90 | big, hidden, lightly loaded: coarse layers, 2–3 walls, 10–15 % infill, faster speeds |
| **STANDARD** | 0.2 mm | 3 | 4 / 4 | 20% gyroid | 35 / 50 / 70 | has press fits or carries a load: 0.2 mm, 3 walls, 20 % infill |
| **DETAIL** | 0.2 mm | 4 | 5 / 5 | 100% rectilinear | 25 / 35 / 50 | gear teeth: slow outer walls for an accurate tooth shape, solid |

Everything else stays as in `concept_a_PETG_prusaslicer.ini` (235 °C, bed 80 °C, glue stick, retraction 5 mm). Solid infill 40, top 30 mm/s, and a cap of 8 mm³/s (the most PETG the CR-6 SE's stock hotend melts): above that it under-extrudes.

**Why not a finer layer on the gears?** The fingers print flat, so the tooth shape is drawn by the nozzle in X–Y; a thinner layer only adds time. What makes the teeth accurate is a slow outer wall, so DETAIL slows that down.

## Per part

| Part | Profile | Changes from the profile | Before | After | Must be accurate | Can be rough |
|---|---|---|---|---|---|---|
| CA-101 Base | **DRAFT** | perimeters 3, supports (from the bed) | 12 h 47, 139 g | **6 h 33, 124 g** | 6807 bearing pocket (47.1 mm), MG996R screw holes | everything else: it is a box. Layer lines, rough sides, small sag in the pockets |
| CA-102 Electronics tray | **DRAFT** | — | 7 h 08, 66 g | **3 h 01, 50 g** | nothing critical: board pegs and 2 screw tabs | everything |
| CA-201 Turret plate | **STANDARD** | supports (from the bed) | 3 h 08, 31 g | **2 h 23, 28 g** | hub into the bearing bore (34.95 mm), 2 rod holes (6.0 mm), horn screw holes | the plate's top face and edges |
| CA-202 Spine | **DRAFT** | perimeters 3, fill density 15% | 2 h 25, 22 g | **1 h 05, 18 g** | lift-servo screw holes, 2 screw holes at each end | faces and edges |
| CA-203 Top cap | **DRAFT** | fill density 15% | 1 h 09, 10 g | **29 min, 8 g** | 2 blind rod holes (6.0 mm) | everything else |
| CA-301 Carriage + arm | **STANDARD** | supports (from the bed) | 4 h 14, 47 g | **3 h 08, 42 g** | 4 LM6UU pockets (12.15 mm) in line, wrist-servo screws, link pivot hole | arm faces |
| CA-302 Lift link | **STANDARD** | fill density 100%, fill pattern rectilinear, brim width 5 | 5 min, 1 g | **5 min, 1 g** | the 2 holes | - |
| CA-401 Gripper frame | **STANDARD** | fill density 30%, external perimeter speed 25, perimeters 4 | 1 h 39, 17 g | **1 h 47, 19 g** | gear axle hole and servo position: they set the gear mesh | flange faces |
| CA-402 Finger, right | **DETAIL** | supports (from the bed) | 1 h 41, 23 g | **1 h 55, 23 g** | gear teeth, axle bore 3.9 mm | pad back face (it gets the silicone sheet) |
| CA-403 Finger, left | **DETAIL** | supports (from the bed) | 1 h 42, 23 g | **1 h 57, 24 g** | gear teeth, servo-spline socket | pad back face |
| CA-900 Tolerance coupon | **STANDARD** | — | 1 h 02, 8 g | **48 min, 8 g** | it is the test of the fits: print it with the STANDARD profile | - |
| **Total** | | | **36 h 59, 387 g** | **23 h 12, 345 g** | | |

Brim: only the lift link (tiny). Skirt: 2 loops on every plate, as before. Supports: only where the part has a real overhang (base, turret plate, carriage arm, the two fingers), from the bed only.

## Plates (open and slice: the settings are already inside)

`cad/print/plates_eco/`: the same 4 plates (and the 2 Plan P plates), with each part's profile stored in the .3mf (PrusaSlicer: right-click a part to see it). Import `concept_a_PETG_prusaslicer.ini` first, then open the plate.

| Plate | Parts | Time | PETG |
|---|---|---|---|
| `plate0_coupon_eco.3mf` | CA-900 | 48 min | 8 g |
| `plate1_base_eco.3mf` | CA-101 CA-201 CA-203 CA-302 | 9 h 30 | 161 g |
| `plate2_tray_spine_eco.3mf` | CA-102 CA-202 CA-402 | 6 h 03 | 92 g |
| `plate3_arm_claw_eco.3mf` | CA-301 CA-401 CA-403 | 6 h 55 | 84 g |
| `planP_1_claw_eco.3mf` | CA-401 CA-402 | 3 h 43 | 42 g |
| `planP_2_finger_eco.3mf` | CA-403 CA-900 | 2 h 45 | 31 g |

On a plate the slicer prints parts with different layer heights together (0.28 and 0.2 mm parts sync every few layers), so the plate time is a bit more than the sum of its parts. Cura: set each part with Per Model Settings using the table above.

## Fix-up after printing (sandpaper, drill, knife)

Tools: sandpaper 120 + 240 grit, a 6 mm and a 5/32 in (4 mm) drill bit turned by hand, a 12 mm dowel or marker wrapped in sandpaper, a craft knife, flush cutters / pliers for supports.

| Part | Fix |
|---|---|
| CA-101 Base | Bearing tight: sand the pocket wall (120 grit on a finger) until it presses in with thumbs. Loose: one layer of tape. Clear support bits out of the servo pocket with pliers |
| CA-102 Electronics tray | Pegs too fat for the Uno / buck holes: twist the board on, or shave a peg with a knife. Snapped peg: a dab of hot glue holds the board |
| CA-201 Turret plate | Hub tight in the bearing: sand the hub evenly, turning it. Rod holes tight: drill 6 mm (or a 15/64 in bit) by hand |
| CA-202 Spine | Servo screws: run each screw in once and back out before final assembly |
| CA-203 Top cap | Rod won't go in: drill 6 mm, 8 mm deep (tape flag on the bit) |
| CA-301 Carriage + arm | Pockets print on their side, so their top droops: ream with 12 mm drill or sandpaper on a 12 mm dowel / marker until the LM6UU presses in; check the carriage slides down both rods by its own weight |
| CA-302 Lift link | Tiny part: peel the brim, open the pivot hole with a 5/32 in (4 mm) drill if the screw binds |
| CA-401 Gripper frame | Don't open the axle hole more than needed: the gears must mesh without play |
| CA-402 Finger, right | Remove supports, then file only the pad area; never the teeth. Bore tight: twist a 5/32 in drill through by hand |
| CA-403 Finger, left | Spline socket tight: scrape lightly inside with the knife tip, test the SG90 spline after every pass. Never file the teeth |
| CA-900 Tolerance coupon | Coarse (draft) layers can make holes come out slightly tight: expect a bit more sanding / drilling on draft parts |

**Rules:** sand a press fit a little at a time and test after every few strokes (you can't add plastic back; if it gets loose, one layer of tape or a drop of CA glue). Never sand or file gear teeth. A draft part that cracks at a screw: the screw was forced: drill the hole one size bigger and use the next screw size or hot glue.

## Print order

1. Coupon (`plate0_coupon_eco`, STANDARD): check the fits as in the build guide, section 2.
2. The claw first if you want the most important parts early (`planP_1_claw_eco`, `planP_2_finger_eco`), otherwise plates 1 → 3.
3. Fix-up each part as it comes off the bed, and test its fit right away (bearing, LM6UU, rods, servos).

Regenerate: `python3.13 backend/tools/print_economy.py` (re-slices every part and plate).
