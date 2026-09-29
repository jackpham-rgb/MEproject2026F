# Wiring (draft) and Bill of Materials (draft)

> **Concept D (mirror flip): alternative, not selected.** The team picked Concept A. The current design docs are in `docs/` (`02_design_analysis.md` … `06_pdr_outline.md`). Paths in this file that point to `docs/0x_…` mean the copies in `docs/concept_d/`.

## Power architecture

```
12 V DC (≥2 A wall adapter or 3S LiPo)
 ├── Motor driver VM (TB6612FNG recommended; L298N/L293D work but drop ~1.5–2 V)
 ├── Uno VIN (on-board regulator → 5 V logic, encoder, FSR, IR sensor)
 └── 5 V buck (≥2 A, e.g. mini-360/LM2596) → servo V+ ONLY
         SG90 stall ≈ 0.65 A; on the Uno's 5 V pin it browns out the board mid-grip
All grounds common (star at the driver).
```

## Pin map (matches `firmware/can_flipper/config.h`)

| Uno pin | Connects to | Notes |
|---|---|---|
| D2 (INT0) | Encoder A | Both edges, 4× decode |
| D3 (INT1) | Encoder B | Both edges |
| D4 | Start button → GND | `INPUT_PULLUP`, 50 ms debounce |
| D5 | Driver PWMA / ENA | Timer0 PWM (Timer1 = Servo, Timer2 = control tick) |
| D7, D8 | Driver AIN1/AIN2 or IN1/IN2 | Direction |
| D9 | Grip servo signal | Servo lib (Timer1) |
| D10 | Home microswitch → GND | `INPUT_PULLUP`, closed = on stop |
| D11 | IR proximity module OUT (in the palm) | `INPUT_PULLUP`, LOW = can present |
| D12 | spare | |
| D13 | Status LED (on-board) | Blinking = running, solid = DONE, fast = FAULT |
| A0 | FSR divider: 5 V — FSR — A0 — 10 kΩ — GND | |
| 5 V / GND | Encoder VCC, IR module, FSR divider | |

Do not use `tone()`: it needs Timer2, which the control tick uses.

The Part C wiring diagram: draw this in Fritzing or KiCad once the parts are in hand. The Wokwi
diagram in `wokwi/concept_d/diagram.json` covers the logic side.

## Draft BOM

| # | Item | Qty | Source | Est. cost | Notes |
|---|---|---:|---|---:|---|
| 1 | Arduino Uno R3 | 1 | ELEGOO kit | — | |
| 2 | 12 V gearmotor with hall encoder, ~1:34, ~200 rpm (JGA25-370 class) | 1 | Purchase | $12–15 | The main purchase. Check stall torque ≥ 0.3 N·m |
| 3 | TB6612FNG driver breakout | 1 | Purchase | $5 | Or the kit's L293D |
| 4 | SG90 or MG90S servo | 1 | Kit / purchase | $3–6 | MG90S (metal gears) preferred for holding force |
| 5 | FSR 402 (Interlink) | 1 | Purchase | $7 | + 10 kΩ resistor |
| 6 | Microswitch with lever | 1 | Purchase | $1 | Home stop |
| 7 | IR proximity module (TCRT5000 or KY-032) | 1 | Kit / purchase | $1–2 | In the palm; replaces the HC-SR04 |
| 8 | Push button | 1 | Kit | — | Start |
| 9 | 5 V ≥2 A buck converter | 1 | Purchase | $3 | Servo supply |
| 10 | 12 V ≥2 A supply | 1 | Purchase / lab | $8 | |
| 11 | 626ZZ bearing + 6 mm shaft (optional) | 2 + 1 | Purchase | $5 | Takes the bending load off the gearbox shaft |
| 12 | Steel bar ½ × ¾ × 2 in (counterweight) | 1 | Hardware store / shop | $2 | ≈ 97 g; or a washer stack |
| 13 | Silicone/TPU pad material | — | Purchase / print in TPU | $2 | |
| 14 | Printed parts: base, tower, hub (with stop tab), arm, palm, 2 jaws, home post | 8 | Designed (PLA) | filament | Part numbers come with the Part C drawings |
| 15 | M3 fasteners, standoffs, wire, headers | — | Kit / purchase | $5 | |

Estimated purchased cost beyond the kit: **~$50–60**.
