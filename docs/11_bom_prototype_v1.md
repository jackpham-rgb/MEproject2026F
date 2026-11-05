# Bill of materials: prototype v1

What it takes to build the **first prototype**, split three ways: what we already have, what must be
bought, and what can come from home. Prices for the must-buy items are from the actual Amazon cart
(Nov 2026). Links are Amazon searches for that exact listing. Home items cost **$0 if found**; each has
a buy option if not.

**Plan:** buy the cart, build v1 this weekend, then return what the household swaps make unnecessary
(keep the boxes, don't cut the rod until the LM6UU slides on it, check each listing says returnable
within 30 days). Prototype v2 then optimizes material and salvages more from home.

## 1. Already have: $0

| Item | Qty | Use | Note |
|---|---:|---|---|
| Arduino Uno R3 + USB cable | 1 | Controller | Kit |
| SG90 servo | 1 | Gripper (D5) | Kit |
| Electrolytic capacitor 1000 µF, ≥ 10 V | 1 | Servo rail | Kit |
| Push button 12 mm | 1 | START (D4) | Kit |
| LED 5 mm + 220 Ω resistor | 1 | Status (D13) | Kit |
| Mini breadboard (170 holes) | 1 | Servo rail | Kit |
| Jumper wires M-M / M-F | ~20 | Signals, ground | Kit |
| #6-32 × ½″ screws / #8-32 × ½″ screws | 8 / 4 | Frame / MG996R | Harbor Freight kit |
| Servo-bag screws | ~14 | Servo tabs, horns | Come with the servos |
| PETG filament 1.75 mm | ~0.35 kg | All printed parts | |
| **LIZVOR adjustable adapter, 3.5–24 V 2 A** | 1 | **Replaces the 12 V adapter** | Set to **12.0 V** before connecting, tape the knob, use the plain 5.5 × 2.1 mm tip (centre +), **not** the polarity-reversing cable |
| **LIZVOR "DC terminal block" tip** | 1 | **Replaces the DC panel jack** | Screw the + / − wires to the buck input and Uno VIN; hot-glue it inside the tray by the panel hole |

## 2. Must buy: $52.57

| Item | Listing in the cart | Qty | Price | Link | Why it can't come from home |
|---|---|---:|---:|---|---|
| MG996R servo (turntable, D9) | Adeept 996R metal gear, 2-pack | 1 pack | $12.99 | [Amazon](https://www.amazon.com/s?k=Adeept+996R+metal+gear+servo+2+pack) | Torque for the turntable. Check it's the **180°** version. The 2nd is a spare (a single ≈ $9 if you'd rather) |
| MG90S servo (lift D10, wrist D6) | Miuzei MG90S metal gear, 2-pack | 1 pack | $8.88 | [Amazon](https://www.amazon.com/s?k=Miuzei+MG90S+metal+gear+micro+servo+2+pack) | Metal gears for the lift and the 180° flip |
| 6807-2RS bearing (turntable) | uxcell 6807-2RS, 35 × 47 × 7 mm | 1 | $5.93 | [Amazon](https://www.amazon.com/s?k=uxcell+6807-2RS+bearing+35x47x7mm) | A skateboard / fidget-spinner bearing (608) is too small for the 47 mm pocket |
| LM6UU linear bearing (lift) | Skweawert LM6UU, 4 pcs | 1 pack | $6.79 | [Amazon](https://www.amazon.com/s?k=Skweawert+LM6UU+linear+ball+bearing+4pcs) | Carriage slides without jamming (jam check done with these) |
| 6 mm steel rod (lift guides) | ReliaBot 6 mm × 300 mm h8, 2 pcs | 1 pack | $9.99 | [Amazon](https://www.amazon.com/s?k=ReliaBot+6mm+x+300mm+linear+rod+shaft) | Hard, exactly 6 mm for the LM6UU. 1 rod cut to 2 × 112 mm; the 2nd is a spare. **Weekend test:** see the note below |
| XL4015 buck converter (servo power) | HiLetgo XL4015 5 A with LED voltmeter | 1 | $7.99 | [Amazon](https://www.amazon.com/s?k=HiLetgo+XL4015+5A+step+down+LED+voltmeter) | 5.8 V for the servos; a phone charger can't take the MG996R stall current. The display makes setting 5.8 V easy |
| | | | **$52.57** | | |

## 3. Find at home: $0 if found

| Item | Look for at home | What to check | If not found |
|---|---|---|---|
| Servo extension leads (4) | Chains of the kit's M-F jumper wires | Joints only in tied runs, never in a loop; tape each joint. The gripper needs ~270 mm added | Already in the cart: 20 pcs, **$8.99**, [Amazon](https://www.amazon.com/s?k=servo+extension+cable+20+pcs+female+to+male). **Return it** if the jumpers hold during the weekend dry run |
| Wire ties (~8) | Bread twist ties, small ties from packaging, electrical / masking tape, hot glue | Tie only at the tie points; the 3 loops hang free | ≈ $6 EST, [Amazon](https://www.amazon.com/s?k=small+zip+ties+adhesive+mounts+kit) |
| Grip pads + can bumper | Bike inner tube, wide rubber band over each pad, non-slip shelf liner, old silicone phone case | 1–2 mm thick; re-check the closed angle with `servo_setup` | ≈ $8 EST, silicone sheet 1/16 in, [Amazon](https://www.amazon.com/s?k=silicone+rubber+sheet+1%2F16+inch) |
| Base weight (~100 g) | Rocks, pennies (fit the 21 mm pockets, quarters don't), nuts / bolts, fishing weights | **Glue or tape it in**: the pockets are open underneath. Never on the base top | ≈ $3 EST, washers, hardware store |
| Feet (4) | Hot-glue dots, mouse-pad or shelf-liner pieces | Optional: the robot uses only 1–2 % of bare-plastic friction | ≈ $2 EST, adhesive rubber feet |
| Lubricant | Silicone / dielectric grease or white lithium grease from the garage | **No brake fluid** (attacks plastic). LM6UU come greased: a drop of light oil at most | — |

## Totals

| | Cost |
|---|---:|
| Must buy (cart without the extension leads) | **$52.57** |
| + extension leads, if the jumper chains don't hold | + $8.99 |
| + everything in section 3 bought new instead of found | + ≈ $19 EST |
| Single MG996R instead of the 2-pack | − ≈ $4 |

## Decided by the weekend test (prototype v1)

| Question | Test | If yes | If no |
|---|---|---|---|
| Jumper chains good enough? | Move the arm by hand through the flip and the turn with jumpers in place | Return the extension leads (−$8.99) | Use them |
| Do we keep the LM6UU + rod for v2? | v1 runs with them; optionally try printed LM6UU-sized bushings with silicone grease on the steel rod (same pockets) | Printed bushings: return or keep LM6UU as spares | Keep LM6UU |
| Adapter steady at 12 V? | Multimeter on the LIZVOR output, then with the buck connected | Keep using it | Buy a fixed 12 V 2 A adapter (≈ $8) |
| Household pads grip? | Grip, lift and flip the can 10 times | Keep | Buy the silicone sheet |

**Prototype v2** (after the weekend): optimize material (lighter printed parts, less PETG), and salvage
more from home (a 6 mm rod from a dead printer or scanner, a jack from old electronics).
