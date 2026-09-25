# Preliminary CAD Brief (SolidWorks)

Modelling brief for the PDR-level CAD of Concept D. The dimensions come from `sim/params.py` and
`sim/flip_geometry.py`. If you change one, change it there and rerun the scripts.

## Global frame (make this the assembly origin)

- **Origin:** robot corner on the table surface. **+Y** points to START (can at (0, 5) in),
  **+X** points to TARGET (can at (5, 0) in), and **+Z** is up.
- **Flip axis:** a construction line through (0, 0, 2.39) in with direction (1, 1, 0)/√2.
- **Arm plane:** perpendicular to the axis, passing through the axis point (2.5, 2.5, 2.39) in,
  which is 3.536 in along the axis from the origin.
- Add two 2.4 in × 4.7 in reference cylinders, one at START upright and one at TARGET inverted.
  Add a mate or a configuration that rotates the arm sub-assembly 0 → 180° about the axis. Then use
  *Interference Detection* at 0°, 45°, 90°, 135° and 180°, or a *Motion Study* sweep.

## Parts

| Part | Critical dimensions | Notes |
|---|---|---|
| **Base plate** | Keep-outs: Ø 2.9 in circles at START and TARGET (can + 0.25 in). Under the arm plane, a half-disk of radius 2.3 in below the axis (counterweight sweep) must be clear | Low profile. Nothing within 0.3 in of the table plane along the can path near START or TARGET |
| **Motor tower** | Shaft centreline at **z = 2.39 +0.05/−0.02 in** on the 45° line. Tower faces at axial position **≤ 1.9 in** from the origin | Can's axial extent is 2.34–4.74 in, so leave 0.4 in margin. Slot the mount holes vertically so the axis height can be trimmed |
| **Shaft / hub** | Hub reaches from the tower to the arm plane, ~1.6 in. Hub radius < 1.0 in near the arm plane | Can passes no closer than 2.34 in radially. Use a D-shaft set-screw hub or a 6 mm shaft + 2 × 626 bearings, so the gearbox takes no bending load |
| **Arm** | Axis → gripper palm face **2.336 in** (3.536 − 1.2). Axis → can centre 3.536 in. Opposite side: counterweight pocket with its centre at **1.8 in** | Counterweight: steel bar **½ × ¾ × 2 in** (≈ 97 g), long edge parallel to the axis, ½ in dimension radial |
| **Gripper** | Two jaws closing **parallel to the flip axis**, contact at can mid-height. Open width ≥ 2.9 in, closed on the can at 2.4 in | **V-jaws** (90–120° included angle) to self-centre the can. Silicone or TPU pads (~2 mm). FSR 402 under one pad, with a small puck so the load goes through the sensing area |
| **Grip servo mount** | SG90/MG90S on the arm, horn → finger lever **~30 mm** | Use a rack or a linkage so both jaws move symmetrically |
| **Home stop** | Stop post under the **can-side** arm at ~1.0 in radius, top surface where the arm is exactly horizontal (θ = 0) | Gravity holds the arm on it. Put the microswitch lever in the stop face |
| **Sensor bracket** | HC-SR04 at the axis foot, under the arm (z ≈ 0.7 in), aimed along −X+Y at START | The can face is ~2.34 in (5.9 cm) away. Check the beam isn't blocked by the jaws at θ = 0 |

## Mass properties

Once modelled, assign materials (PLA 1.24 g/cc at your infill, steel for the counterweight). Then
read the arm sub-assembly's **mass, centre of mass and moment of inertia about the flip axis**.
Put them into `sim/params.py` (`M_GRIPPER`, `M_ARM`, `R_CW`/`M_CW`, or override `load_inertia()`)
and rerun `flip_control.py`. The counterweight mass is chosen to cancel 90 % of the *empty* arm's
first moment. Adjust it with washers after the build.
