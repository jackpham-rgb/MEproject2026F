# Measurement sheet: CAD file vs real part

Fill in the **Measured** column and send it back. Every CAD value comes from `backend/cad/model.py`
(the `TOL` table and the part dimensions). From the differences, every hole and shaft in the robot gets
corrected in one go, and only the parts that need it are reprinted (`cad/print/reprint/`).

## How to measure (digital calipers)

- **Hole:** the small top jaws inside the hole; measure, turn the calipers 90°, measure again: write **both**.
  Measure in the middle of the hole's depth, not at the bed side (the first layer bulges out: "elephant foot").
- **Shaft / outside (hub, post):** the big jaws; two readings 90° apart, write **both**.
- **Length / width:** big jaws across the whole part, ~1 mm above the bed face.
- Don't squeeze: close the jaws until they just touch. Zero the calipers first.
- **Fit:** try the real part in it: **press** (needs force, stays), **snug** (slides in by hand, no play),
  **loose** (wobbles), **no** (won't go in).

## A. Bought parts (the real sizes everything is checked against)

| # | Part | Measure | Nominal | Measured | Measured (90°) |
|---|---|---|---:|---:|---:|
| A1 | 6 mm steel rod | outside diameter | 6.00 | | |
| A2 | LM6UU | outside diameter | 12.00 | | |
| A3 | 6807 bearing | outside diameter | 47.00 | | |
| A4 | 6807 bearing | inside (bore) diameter | 35.00 | | |
| A5 | 6807 bearing | width | 7.00 | | — |
| A6 | #6-32 screw | thread outside diameter | 3.51 | | — |
| A7 | #8-32 screw | thread outside diameter | 4.17 | | — |
| A8 | Servo-bag screw (small) | thread outside diameter | ~2.2 | | — |
| A9 | SG90 round horn | hub outside diameter (the round boss) | ~7 | | |

## B. Tolerance gauge (`cad/print/tolerance_test/`)

| # | Feature | CAD | Measured | Measured (90°) | Fit with the real part |
|---|---|---:|---:|---:|---|
| B1 | ROD hole 1 | 6.00 | | | rod: |
| B2 | ROD hole 2 | 6.15 | | | rod: |
| B3 | ROD hole 3 | 6.30 | | | rod: |
| B4 | ROD hole 4 | 6.45 | | | rod: |
| B5 | LM6UU hole 1 | 12.10 | | | LM6UU: |
| B6 | LM6UU hole 2 | 12.25 | | | LM6UU: |
| B7 | LM6UU hole 3 | 12.40 | | | LM6UU: |
| B8 | LM6UU hole 4 | 12.55 | | | LM6UU: |
| B9 | AXLE hole 1 | 3.90 | | | #6 screw turns freely? |
| B10 | AXLE hole 2 | 4.10 | | | |
| B11 | AXLE hole 3 | 4.30 | | | |
| B12 | HORN hole 1 | 6.80 | | | horn hub: |
| B13 | HORN hole 2 | 7.10 | | | horn hub: |
| B14 | HORN hole 3 | 7.40 | | | horn hub: |
| B15 | Ring, inside | 47.25 | | | 6807: |
| B16 | Post, outside | 34.80 | | | 6807: |
| B17 | Overall length | 180.9 | | — | |
| B18 | Overall width | 69.6 | | — | |

## C. Parts already printed (original plate 1)

| # | Part | Feature | CAD | Measured | Measured (90°) | Fit with the real part |
|---|---|---|---:|---:|---:|---|
| C1 | Turret plate | hub outside diameter (goes into the 6807) | 34.95 | | | 6807: |
| C2 | Turret plate | rod hole, left | 6.00 | | | rod: |
| C3 | Turret plate | rod hole, right | 6.00 | | | rod: |
| C4 | Turret plate | rod holes, centre to centre (inside-to-inside + one Ø) | 34.0 | | — | |
| C5 | Turret plate | overall width (round edge to round edge) | 80.0 | | — | |
| C6 | Turret plate | plate thickness | 6.0 | | — | |
| C7 | Top cap | rod hole, left | 6.00 | | | rod: |
| C8 | Top cap | rod hole, right | 6.00 | | | rod: |
| C9 | Top cap | screw hole (#6 clearance), one of the 2 | 3.90 | | | #6 passes? |
| C10 | Top cap | overall length × width | 54.0 × 44.0 | | — | |
| C11 | Lift link | big hole (carriage pivot) | 3.90 | | | #6 turns? |
| C12 | Lift link | small hole (old print: crank pin) | 1.70 | | | |
| C13 | Lift link | hole centre to centre | 9.36 | | — | |
| C14 | Base (only if printed) | bearing pocket inside diameter | 47.10 | | | 6807: |
| C15 | Base (only if printed) | overall length × width | 152.0 × 112.0 | | — | |

**Also note:** filament (brand, PETG), nozzle / bed temperature used, and which settings the part was printed with
(the original plate 1 used the old single-setting profile; the gauge used its own settings).

## What happens with the numbers

- A tells the real reference sizes (bearings and rods vary by maker).
- B and C give how much this printer shrinks holes and grows shafts at each size. One printer usually has a nearly
  constant offset, so 4–6 good readings correct everything.
- Then: `TOL` updated → checks re-run → `cad/print/reprint/` regenerated → print the reprint plates.
