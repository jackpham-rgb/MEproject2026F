# Creality CR-6 SE: finding and fixing print problems (PETG)

For our settings (`cad/print/settings/printer_settings.txt`): PETG, 235 °C nozzle, 80 °C bed, 0.2 mm
layers, Bowden extruder, carborundum glass bed, auto-levelling with the nozzle as the probe.

**Rule for an unreliable printer:** print small first (the tolerance coupon, then the Plan P claw),
**watch the whole first layer**, and check again after 30 minutes. Most failures show up in the first
layer or the first half hour.

## Before every print (2 minutes)

- ☐ Nozzle tip **clean** (no plastic blob): the CR-6 SE measures the bed **with the nozzle**, so a blob = a bad level
- ☐ Glass clean (dish soap + water or isopropyl), thin **glue stick** layer for PETG
- ☐ Filament dry (no popping or crackling on the last print), spool turns freely, no tangles
- ☐ Bed at 80 °C for 5 min before starting (the glass needs to heat through)
- ☐ Auto-level (Level on the screen) after moving the printer or changing the nozzle
- ☐ Watch the first layer: lines slightly squished and touching each other, not round, not see-through

## Symptom → cause → fix

### First layer and sticking

| What you see | Likely cause | Fix |
|---|---|---|
| First layer lines **round, not stuck**, get dragged around | Nozzle too high (Z-offset) | Live-adjust Z-offset down in 0.02 mm steps during the first layer until the lines are slightly flat |
| First layer **see-through / rough / ridged**, nozzle scrapes | Nozzle too low | Z-offset up 0.02–0.05 mm |
| Good on one side, bad on the other | Bed not level, or the **two Z screws out of sync** (CR-6 SE has 2 Z motors) | Power off, turn one Z screw by hand until the gantry is the same height both sides (measure with a ruler), then re-level |
| Auto-level fails / gives odd numbers | Plastic on the nozzle, or the nozzle-probe (strain gauge) disturbed | Heat to 235 °C, wipe the tip with a brass brush or cloth, let it cool to < 60 °C, level again. Don't touch the hotend during levelling |
| **Corners lift / warp** (base, tray) | PETG shrinks as it cools; draft; bed too cool at the edges | Glue stick, bed 80 °C (try 85), no fan for the first 3 layers, keep the room draft-free (box or blanket around the printer), add a 5 mm **brim** to that part |
| Part **won't come off**, pulls a chip of glass | PETG bonds to glass when too hot or squished | Always glue stick (release layer), Z-offset a little higher, let the bed cool to room temperature before removing |
| **Elephant foot**: bottom edge wider, holes on the bed side tight | First layer squished | Already set: 0.15 mm compensation. If still there, Z-offset up 0.02 mm |

### During the print

| What you see | Likely cause | Fix |
|---|---|---|
| **Spaghetti / noodles**: a nest of loose plastic, print gone | Part came off the bed, or support fell over | Stop the print. Fix sticking (above), add a brim, check supports are on; for tall thin parts add a brim |
| **Blobs and zits** on the surface | Ooze at the seam / retraction start | Seam position "rear", retraction 5 mm (try 6), enable "wipe while retracting", lower temp 5 °C (min 230) |
| **Stringing** (hairs between parts) | PETG oozes; wet filament; too hot | Retraction 6 mm at 40 mm/s, travel 150 mm/s, temp −5 °C, **dry the filament** (65 °C for 4 h, or a food dehydrator) |
| **Popping, crackling, bubbles**, rough foamy surface | Wet filament | Dry it (65 °C, 4–6 h), store it in a bag with silica gel |
| **Gaps, thin walls, missing lines** (under-extrusion) | Partial clog, extruder slipping, filament tangled | Check the spool turns freely; listen for **clicking** at the extruder (see clogs); check the extruder arm (below) |
| **Clicking** from the extruder, little or no plastic | Clog, often a **gap between the PTFE tube and the nozzle** (common on the CR-6 SE) or too low a nozzle on the first layer | Cold pull (heat to 235, push filament, cool to 120, pull hard). If it comes back: heat, re-seat the PTFE tube tight against the nozzle, cut its end square. Never run above 240 °C (the PTFE tube breaks down) |
| **Extruder slips or clicks** although nothing is clogged | The **plastic extruder arm cracked** (very common on the CR-6 SE, near the pivot) | Look for a hairline crack on the arm; replace with a metal extruder (a few dollars) |
| **Layer shift** (the print steps sideways) | Nozzle hit a curled-up edge; a belt loose; too fast | Fix warping/curling, tighten X / Y belts (twang like a low guitar string), keep travel 150 mm/s |
| **Nozzle knocks into the print** | Curled overhangs (PETG curls if too hot or too little cooling) | Fan 50 % for overhangs, temp −5 °C, check "avoid crossing perimeters" |
| **Ribs / waves up the side** (Z banding) | Z screws binding or out of sync | Clean + lightly oil the Z screws, re-sync both sides |
| **Supports fused to the part**, hard to remove | Z gap too small for PETG | Support Z distance 0.2 mm (already set), try 0.25; peel with pliers while still slightly warm |

### After printing

| What you see | Likely cause | Fix |
|---|---|---|
| Holes too small, screws / rods / LM6UU won't fit | Normal for printed holes | That's what the coupon (plate 0) is for: change `TOL` in `backend/cad/model.py`, re-export (I can do it: tell me which hole) |
| Holes too big, parts loose | Over-compensation | Same: adjust `TOL` |
| Part cracks along a layer when screwed | Layers didn't bond (too cold, too much fan) | Temp +5 °C (max 240), fan 30 %, run screws in slowly by hand |
| Gear teeth soft / break | Fingers not at 100 % infill | Check the per-part setting (it's in the .3mf); never print them at 30 % |

## Quick calibration prints (if the problems keep coming)

1. **Our tolerance coupon** (`plate0_coupon`, 1 h): fit check of every hole.
2. **First-layer test**: a single-layer 100 × 100 mm square in the middle of the bed: tune the Z-offset until it's smooth and even.
3. **Temperature tower** (230–240 °C) for your PETG: pick the temperature with the least stringing that still bonds well.
4. **Retraction test** (two towers): 4, 5, 6, 7 mm: take the lowest with no strings.

## When a print fails mid-way

Stop it (don't let spaghetti wrap the nozzle), let the bed cool, remove the plastic, clean the nozzle,
check the cause in the table, and restart. A failed 1 h print is cheap: that's why we print the coupon and
the Plan P claw before the 17 h base plate.
