# Economy printing: only the quality each part needs (set up by hand)

Not every part needs the same settings. The base is a big hidden box: coarse layers and low infill are fine. The finger gears must mesh: they get slow, accurate outer walls. We accept small flaws on the rough parts and fix the few fits that matter with sandpaper, a drill or a knife (fix-up table at the end).

**No settings file and no changed 3D files:** import the unchanged STLs from `cad/print/stl/` (already turned to their best side: don't rotate them, except flat on the bed) and type the numbers below into your slicer. The parts are grouped so that **each plate uses one setting for the whole plate**: nothing to set per part.

**Result (every plate sliced): 36 h 59 → 23 h 39 of printing (−36 %), 387 g → 347 g of PETG (−10 %).** Less heating time = less energy.

## Same on every plate

| Setting | Value |
|---|---|
| Nozzle temperature | 235 °C (first layer 238 °C, never above 240 °C: PTFE-lined hotend) |
| Bed temperature | 80 °C, thin glue stick on the glass |
| First layer | 0.24 mm high, 20 mm/s |
| Line width | 0.42 mm (0.4 mm nozzle) |
| Cooling fan | 30 %, off for the first 3 layers |
| Retraction | 5 mm at 40 mm/s (Bowden) |
| Solid / top infill speed | 40 / 30 mm/s |
| Travel speed | 150 mm/s |
| Max flow | keep under 8 mm³/s (stock CR-6 SE hotend): the speeds below already do |
| Elephant-foot compensation | 0.15 mm (Cura: initial layer horizontal expansion −0.15) |
| Seam | rear / aligned |
| Skirt | 2 loops (unless the plate says brim) |

## The plates

| Plate | Parts (STL in cad/print/stl) | Layer | Walls | Top / bottom | Infill | Speeds outer / inner / infill (mm/s) | Supports | Adhesion | Time | PETG |
|---|---|---|---|---|---|---|---|---|---|---|
| **A  Coupon + lift link** (STANDARD) | CA-900 Tolerance coupon, CA-302 Lift link | 0.2 mm | 3 | 4 / 4 | 20% gyroid | 35 / 50 / 70 | off | **brim 5 mm** | 54 min | 8 g |
| **B  Base + spine + top cap** (DRAFT) | CA-101 Base, CA-202 Spine, CA-203 Top cap | 0.28 mm | 3 | 3 / 3 | 12% grid | 45 / 60 / 90 | **on**, touching build plate only | skirt | 8 h 11 | 151 g |
| **C  Electronics tray** (DRAFT) | CA-102 Electronics tray | 0.28 mm | 2 | 3 / 3 | 10% grid | 45 / 60 / 90 | off | skirt | 3 h 01 | 50 g |
| **D  Turret plate + carriage arm** (STANDARD) | CA-201 Turret plate, CA-301 Carriage + arm | 0.2 mm | 3 | 4 / 4 | 20% gyroid | 35 / 50 / 70 | **on**, touching build plate only | skirt | 5 h 31 | 70 g |
| **E  Claw: 2 fingers + gripper frame** (DETAIL) | CA-402 Finger, right, CA-403 Finger, left, CA-401 Gripper frame | 0.2 mm | 4 | 5 / 5 | 100% lines | 25 / 35 / 50 | **on**, touching build plate only | skirt | 6 h 02 | 67 g |
| **Total** | | | | | | | | | **23 h 39** | **347 g** |

Print in this order (A first). Every plate fits the 235 × 235 mm bed; leave ~15 mm between parts for the supports.

## Why each plate gets its profile

| Plate | Why |
|---|---|
| A  Coupon + lift link | First: the coupon checks every fit; the tiny link rides along and gets the brim it needs |
| B  Base + spine + top cap | Big, hidden, lightly loaded. 3 walls so the screw holes and the bearing pocket stay strong |
| C  Electronics tray | Nothing precise on it: the fastest settings |
| D  Turret plate + carriage arm | Press fits (bearing hub, rods, LM6UU) and the parts that carry the lift |
| E  Claw: 2 fingers + gripper frame | Gear teeth and the gear spacing: slow outer walls, solid |

**Why not a finer layer on the gears?** The fingers print flat, so the tooth shape is drawn by the nozzle sideways (X–Y); a thinner layer only adds time. What makes the teeth accurate is a slow outer wall, so DETAIL slows that down.

**Slicer names:** walls = Cura "Wall Line Count" / Prusa "Perimeters"; top / bottom = "Top / Bottom Layers" / "Solid layers"; outer wall speed = "Outer Wall Speed" / "External perimeters"; supports touching build plate = "Support Placement: Touching Buildplate" / "Support on build plate only".

## Per part: what must be accurate

| Part | Must be accurate | Can be rough |
|---|---|---|
| CA-900 Tolerance coupon | it tests the fits | - |
| CA-302 Lift link | the 2 holes | - |
| CA-101 Base | 6807 bearing pocket (47.1 mm), MG996R screw holes | everything else: layer lines, rough sides, sag in the pockets |
| CA-202 Spine | lift-servo screw holes, screw holes at the ends | faces and edges |
| CA-203 Top cap | 2 blind rod holes (6.0 mm) | everything else |
| CA-102 Electronics tray | nothing critical: board pegs, 2 screw tabs | everything |
| CA-201 Turret plate | hub into the bearing (34.95 mm), 2 rod holes (6.0 mm), horn screw holes | top face and edges |
| CA-301 Carriage + arm | 4 LM6UU pockets (12.15 mm) in line, wrist-servo screws, link pivot | arm faces |
| CA-402 Finger, right | gear teeth, axle bore 3.9 mm | pad back face (gets the silicone sheet) |
| CA-403 Finger, left | gear teeth, servo-spline socket | pad back face |
| CA-401 Gripper frame | gear axle hole and servo position: they set the gear mesh | flange faces |

## Fix-up after printing (sandpaper, drill, knife)

Tools: sandpaper 120 + 240 grit, a 6 mm and a 5/32 in (4 mm) drill bit turned by hand, a 12 mm dowel or marker wrapped in sandpaper, a craft knife, flush cutters / pliers for supports.

| Part | Fix |
|---|---|
| CA-900 Tolerance coupon | Check each hole as in the build guide, section 2: it tells you how much to sand the real parts |
| CA-302 Lift link | Peel the brim. Pivot screw binds: open the hole with a 5/32 in (4 mm) drill turned by hand |
| CA-101 Base | Bearing tight: sand the pocket wall (120 grit on a finger) until it presses in with thumbs. Loose: one layer of tape. Clear support bits out of the servo pocket with pliers |
| CA-202 Spine | Run each screw in once and back out before final assembly |
| CA-203 Top cap | Rod won't go in: drill 6 mm, 8 mm deep (tape flag on the bit) |
| CA-102 Electronics tray | Peg too fat for a board hole: shave it with a knife. Snapped peg: a dab of hot glue holds the board |
| CA-201 Turret plate | Hub tight: sand it evenly, turning it. Rod holes tight: drill 6 mm (or 15/64 in) by hand |
| CA-301 Carriage + arm | Pockets print on their side, so the top of each droops: ream with a 12 mm drill or sandpaper on a 12 mm dowel / marker until the LM6UU presses in; the carriage must slide down both rods by its own weight |
| CA-402 Finger, right | Remove supports, file only the pad area, never the teeth. Bore tight: twist a 5/32 in drill through by hand |
| CA-403 Finger, left | Spline socket tight: scrape lightly inside with the knife tip, test the SG90 spline after every pass. Never file the teeth |
| CA-401 Gripper frame | Don't open the axle hole more than needed: the gears must mesh without play |

**Rules:** sand a press fit a little at a time and test after every few strokes (you can't add plastic back; if it gets loose, one layer of tape or a drop of CA glue). Never sand or file gear teeth. Coarse draft layers can make holes come out a little tight: expect more sanding / drilling on plates B and C. A part that cracks at a screw: the screw was forced: drill the hole one size bigger, use the next screw size or hot glue.

Regenerate (re-slices every plate): `python3.13 backend/tools/print_economy.py`.
