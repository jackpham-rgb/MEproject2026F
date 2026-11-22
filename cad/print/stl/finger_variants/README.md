# Finger gear variants

The gears on the two fingers must mesh with a little play over the whole swing. 3D printers rarely print teeth exactly, so instead of sanding the teeth (never do that), print the pair that fits.

Standard pair (in `../`): gear_thin = 0.10 mm. **Print both fingers of the same variant.**

| Variant | gear_thin (mm) | Files | Print it when |
|---|---|---|---|
| tighter | 0.00 | `CA-402_finger_R_tighter_thin0.00.stl`, `CA-403_finger_L_tighter_thin0.00.stl` | gears rattle / have visible play with the standard pair |
| looser | 0.18 | `CA-402_finger_R_looser_thin0.18.stl`, `CA-403_finger_L_looser_thin0.18.stl` | standard pair binds or needs force to turn |
| loosest | 0.25 | `CA-402_finger_R_loosest_thin0.25.stl`, `CA-403_finger_L_loosest_thin0.25.stl` | the looser pair still binds (tips print a bit rounded: fine) |

Test: hold the frame, turn the left finger by hand. Both fingers should swing together smoothly, with a small click of play when you reverse, and no tight spot anywhere in the 75° swing.

Edit it yourself: `gear_thin` in `backend/cad/model.py` (P), then `python3.13 backend/cad/finger_variants.py` or the full print_prep. +0.05 mm = a little looser. Don't go above 0.25: the tooth tips get thinner than the nozzle line.
