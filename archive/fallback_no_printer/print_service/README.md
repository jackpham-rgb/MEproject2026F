# Order sheet: printing the parts somewhere else

Use this if our CR-6 SE can't print the parts. Places to try, fastest first:
1. **Campus makerspace / engineering shop / library.** Often free or charged by the gram. Bring the zip on a USB stick.
2. **A classmate's or a friend's printer.**
3. **An online print service.** Upload the STLs and get a quote. Delivery takes a few days, so order early.

## Files

| Zip | Contents | When |
|---|---|---|
| `concept_a_all_parts_stl.zip` | all 11 parts (CA-101 … CA-900) | the whole robot |
| `concept_a_claw_only_stl.zip` | gripper frame + 2 fingers | Plan P (the body is cardboard) |

The STLs are in millimetres and already turned to their best side for printing.

## Tell the printer person / the service

| Setting | Value |
|---|---|
| Material | **PETG** (PLA / PLA+ is fine for a prototype) |
| Layer / nozzle | 0.2 mm layers, 0.4 mm nozzle |
| Walls | 3 perimeters (1.2 mm), 4 top / 4 bottom layers |
| Infill | 30 % (gyroid if they can); **fingers CA-402 / CA-403: 100 %** |
| Orientation | **as in the file, don't rotate** (press-fit holes are vertical on purpose) |
| Supports | only CA-101 base, CA-201 turret plate, CA-301 carriage arm, CA-402 / CA-403 fingers (from the build plate only) |
| Brim | CA-302 lift link (tiny part) |
| Print first, if possible | CA-900 tolerance coupon (~1 h): we test the bearing / LM6UU / servo fits before the big parts |

## Parts

| Part | Name | Qty | Size (mm) | Supports | Est. mass | Est. time on our printer |
|---|---|---:|---|---|---:|---:|
| CA-101 | Base | 1 | 152 × 112 × 52 | yes | 102 g | 9.8 h |
| CA-102 | Electronics tray | 1 | 152 × 104 × 28 | no | 57 g | 5.5 h |
| CA-201 | Turret plate | 1 | 80 × 62 × 19 | yes | 24 g | 2.3 h |
| CA-202 | Spine | 1 | 50 × 99 × 24 | no | 22 g | 2.1 h |
| CA-203 | Top cap | 1 | 54 × 44 × 6 | no | 11 g | 1.0 h |
| CA-301 | Carriage + arm | 1 | 52 × 100 × 44 | yes | 46 g | 4.4 h |
| CA-302 | Lift link | 1 | 16 × 7 × 3 | no (brim) | 0.2 g | 0.3 h |
| CA-401 | Gripper frame | 1 | 62 × 39 × 33 | no | 12 g | 1.1 h |
| CA-402 | Finger, right | 1 | 42 × 79 × 40 | yes | 10 g | 0.9 h |
| CA-403 | Finger, left | 1 | 42 × 78 × 40 | yes | 10 g | 0.9 h |
| CA-900 | Tolerance coupon | 1 | 70 × 22 × 8 | no | 8 g | 0.8 h |
| | **Total** | | | | **≈ 300 g** | **≈ 29 h of print time** |

Everything fits a 220 × 220 mm bed.

**Checks when the parts arrive:**
- **LM6UU:** press it into the carriage pockets.
- **6807 bearing:** fit it into the base pocket.
- **Servos:** each servo must drop into its pocket.
- **If a fit is too tight:** sand or ream it a little. Don't force it, PETG cracks.
- **If it's loose:** add a drop of CA glue or a layer of tape.
