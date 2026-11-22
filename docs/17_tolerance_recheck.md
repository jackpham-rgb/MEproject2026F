# Tolerance re-check: measure, then correct the CAD

The first prints (turret plate, top cap, lift link) did not fit even with sanding. Sanding can only fix
a few tenths of a millimetre, so the design sizes in `backend/cad/model.py` (`TOL`) have to be corrected
to how **this printer** prints. Measure once, send the numbers, and every hole and shaft gets resized together.

## What to measure (calipers, 0.01 mm)

Measure each one **twice, 90° apart**, and write down the smaller value for holes and the larger value for shafts.
Holes print oval and slightly small at the top; measure in the middle of the hole's depth if you can.

| # | Part (already printed) | Feature | Design size (mm) | Measured (mm) | Fits? (tight / OK / loose) |
|---|---|---|---:|---:|---|
| 1 | Turret plate | Hub outside diameter (goes into the 6807 bearing) | 34.95 | | |
| 2 | 6807 bearing | Inner ring bore (the real part) | 35.00 | | |
| 3 | Turret plate | Rod hole, each of the 2 | 6.00 | | |
| 4 | Steel rod | Rod diameter (the real part) | 6.00 | | |
| 5 | Top cap | Rod hole, each of the 2 | 6.00 | | |
| 6 | Top cap | Screw clearance hole (#6) | 3.90 | | |
| 7 | Turret plate | Screw pilot hole (#6, spine screws) | 2.90 | | |
| 8 | Turret plate | Small horn-screw holes (4) | 1.70 | | |
| 9 | Lift link | Big hole (carriage pivot, #6) | 3.90 | | |
| 10 | Lift link | Small hole (crank pin) | 1.70 | | |
| 11 | Coupon (plate A), if printed | All 6 holes, left to right | 3.9 / 2.9 / 4.6 / 3.5 / 6.0 / 12.15 | | |
| 12 | Base (when printed) | Bearing pocket diameter | 47.10 | | |
| 13 | 6807 bearing | Outer ring diameter (the real part) | 47.00 | | |
| 14 | LM6UU | Outer diameter (the real part) | 12.00 | | |

Also note: filament (PETG brand / colour), nozzle and bed temperature, and whether the part was printed with the
DRAFT or STANDARD settings (plate pages A–E). Draft layers print holes a little smaller.

## How the correction works

- **Hole printed smaller than designed** by δ = design − measured: the new design size = old size + δ (+ the fit you want).
- **Shaft (hub) printed bigger** by δ = measured − design: the new design size = old size − δ.
- Wanted fits: press fit 0.05–0.10 mm interference (bearing, rods, LM6UU), running fit +0.2–0.3 mm (pivots, axle),
  self-tapping pilot about 80 % of the screw's outside diameter.
- One printer usually shrinks every hole by about the same amount, so 3–4 good measurements correct all of them;
  the coupon is the fastest way to get that number.

After the numbers come back: `TOL` in `model.py` is updated, all checks re-run, and only the parts that are not yet
printed (or that failed) are re-exported. Parts that already fit are not reprinted.

## Until then

- Precise steps (1, 5, 6, 7, 8) wait for the corrected parts; do the EASY steps first (see the fit levels in the manual).
- A part that is only slightly tight: drill by hand with the bit named in the manual's callout boxes.
- Don't force press fits: PETG cracks, and a cracked hub or pocket has to be reprinted anyway.

## Gripper (open)

The SG90's bare spline does not grip the finger's Ø6 socket. Interim fix in step 19: glue the splined hub of a
cut-down SG90 horn into the socket. The earlier prototype (servo in a pocket at the end of the arm, single-arm
horn screwed onto the driving gear, second gear on a screw axle) is the model for the proper fix, to be decided
with the plan B discussion.
