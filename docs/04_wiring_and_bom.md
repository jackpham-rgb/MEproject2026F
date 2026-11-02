# Wiring and Bill of Materials: Concept A

> **Updated by the detail design (`07_detail_design.md`):** the lazy-susan is replaced by a 6807 bearing in a 28 mm tower, the base is cut away in the arm's sweep sector, the release opens only 25°, and all screws come from the #67675 kit (#6-32 / #8-32, no nuts). Where this file disagrees, `07` and `cad/concept_a_detail/model.py` win.

## Power

```
Wall adapter 7–12 V, ≥3 A
 ├── Uno VIN (on-board regulator → Uno logic, IR sensor, FSR divider)
 └── 5–6 V buck converter, ≥5 A ──┬── all 4 servo V+   (NOT from the Uno's 5 V pin)
                                   └── 1000 µF capacitor across V+ / GND
All grounds joined (servo supply GND ↔ Uno GND).
```

Why: the 4 servos can pull up to 4.6 A if they all stall (MG996R alone ~2.5 A). On the Uno's
5 V pin they would reset the board in the middle of a move.

## Pin map (matches `firmware/concept_a/concept_a.ino`)

| Uno pin | Connects to | Notes |
|---|---|---|
| D9 | Turntable servo signal (MG996R) | |
| D10 | Lift servo signal (MG90S) | |
| D6 | Wrist servo signal (180° or 270° micro) | Set `WRIST_RANGE 270` for a 270° servo |
| D5 | Gripper servo signal (SG90 / MG90S) | |
| D4 | Start button → GND | `INPUT_PULLUP`, debounced |
| D13 | Status LED (+220 Ω) | off = idle, slow blink = moving, on = done, fast blink = fault |
| D11 | IR proximity module OUT (optional) | LOW = can present, `USE_IR_SENSOR 1` |
| A0 | FSR divider (optional): 5 V – FSR – A0 – 10 kΩ – GND | `USE_FSR 1` |

The Servo library works on any pin. It disables `analogWrite` on D9/D10, which this design doesn't
need.

Simulations with the same pins: `wokwi/concept_a/diagram.json` and `docs/tinkercad_concept_a.md`.
For the Part C report, draw the final wiring diagram in Fritzing.

## Bill of Materials

| # | Item | Qty | Source | Est. cost | Notes |
|---|---|---:|---|---:|---|
| 1 | Arduino Uno R3 | 1 | ELEGOO kit | — | |
| 2 | MG996R servo (180°) | 1 | Buy | $8–10 | Turntable |
| 3 | MG90S servo | 1 | Buy | $4 | Lift |
| 4 | Micro servo with a full 180° (or a 270° micro servo) | 1 | Buy | $5–8 | Wrist: check the range |
| 5 | SG90 or MG90S servo | 1 | Kit / buy | $0–4 | Gripper |
| 6 | 6807-2RS ball bearing, 35 × 47 × 7 mm | 1 | Buy | $5 | Turntable (replaces the lazy-susan) |
| 7 | 6 mm steel rod, ~3 in | 2 | Buy | $3 | Lift guide |
| 8 | LM6UU linear bearing | 2 | Buy | $3 | Carriage (a printed slide jams) |
| 9 | 5 A buck converter (XL4015), set to 6.0 V | 1 | Buy | $6 | Servo power |
| 10 | Wall adapter 7–12 V, ≥3 A | 1 | Buy / lab | $10 | |
| 11 | 1000 µF capacitor (≥10 V) | 1 | Kit / buy | $1 | Across servo power |
| 12 | Push button + LED + 220 Ω | 1 each | Kit | — | Start / status |
| 13 | IR proximity module (TCRT5000 / KY-032) | 1 | Kit / buy | $1–2 | Optional |
| 14 | FSR 402 + 10 kΩ | 1 | Buy | $7 | Optional |
| 15 | TPU filament or silicone sheet | small | Buy | $2 | Gripper arm pads |
| 16 | Steel washers / bolts + rubber feet | some | Hardware store | $3 | Base weight and grip on the table |
| 17 | Printed parts (PLA): base box, turntable plate, column, carriage, arm, wrist hub, palm, 2 arms | 9 | Designed | filament | Part numbers come with the Part C drawings |
| 18 | Machine screws: HF kit #67675 (#6-32 × ½″ ×8, #8-32 × ½″ ×4) + servo-bag screws; wires, headers | — | Have / kit | — | No nuts needed (screws thread into printed pilots) |
| | **Total to buy beyond the kit** | | | **≈ $50–65** | ≈ $40–55 without the optional parts |
