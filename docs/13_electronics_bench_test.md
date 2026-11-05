# Electronics bench test: before anything is screwed together

Wire everything flat on the table, servos loose (no horns, nothing printed needed), and prove the
power and every servo work. Do this **while the parts print** (the prints take ~29 h). If something is
wrong here, it is a 5-minute fix; inside the robot it is an hour.

Sketch: `firmware/bench_test/bench_test.ino` (button + LED driven, Serial Monitor optional at 9600).
Diagram: `docs/wiring/wiring_diagram.png`. Have the multimeter ready.

## 1. Power, no servos yet

| # | Do | Check | Expected |
|---|---|---|---|
| 1 | LIZVOR adapter, nothing connected, plain 5.5 × 2.1 mm tip | Display + meter on the tip (centre = +) | **12.0 V**, centre positive. Tape the knob |
| 2 | Adapter → terminal-block tip → buck **IN+ / IN−** | Buck display / meter on **OUT+ / OUT−** | Turn the buck pot (many turns) to **5.8 V**. Dot of nail polish on the pot |
| 3 | Buck OUT → breadboard **+ / −** rails. 1000 µF capacitor across the rails | Stripe on the capacitor = **−** rail | Rail reads 5.8 V |
| 4 | Unplug. Uno on **USB only**, upload `bench_test` | Uno LED | Blinks 3× |
| 5 | Adapter **+ → Uno VIN**, **− → Uno GND**. Uno GND → rail **−** (common ground) | Unplug USB, plug the adapter | LED blinks 3× again (running on 12 V) |
| 6 | START button: D4 ↔ GND. LED: D13 → 220 Ω → LED → GND | Press START | LED lights while pressed |

**Never** connect the rail (5.8 V) to the Uno's 5V pin. The Uno gets 12 V on VIN only.

## 2. One servo at a time

Plug only the servo for the next test. Brown = GND (rail −), red = + (rail +), orange = signal (pin).
The MG996R's + / − go to the **buck OUT terminals** (cut extension), its signal to D9.

| Test | Servo | Plug signal to | Press START, expect |
|---|---|---|---|
| 1 | SG90 gripper | D5 | Goes to 20°, wiggles ±10°, back |
| 2 | MG90S wrist | D6 | 0°, wiggle to 20°, then **a full half-turn 0 → 180 → 0**: mark the horn and check it really reaches 180° |
| 3 | MG90S lift | D10 | 30°, wiggles ±10° |
| 4 | MG996R turntable | D9 (+/− on the buck) | 135°, wiggles ±10° |
| 5 | All four plugged in | — | All at HOME for 5 s. **Meter on the rail: stays above 5.5 V** |

Each test: smooth, no buzzing, the Uno doesn't reset (no 3× blink in the middle).

## 3. If something is wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Uno resets (blinks 3×) when a servo moves | Rail sags or no common ground | Check Uno GND ↔ rail −, the 1000 µF capacitor, the MG996R on the buck terminals (not the breadboard) |
| Servo buzzes / jitters | Signal without ground, loose jumper | Re-seat; shorter jumpers; ground first |
| Servo doesn't move at all | Signal on the wrong pin, dead servo | Swap the plug to a known-good test; try the spare |
| Wrist stops short of 180° | That MG90S's range | `servo_setup`: try `WRIST_MIN_US` / `WRIST_MAX_US` 450 / 2550; else swap MG90S (buy a spare) |
| Rail below 5.5 V in test 5 | Weak adapter / long thin wires | Shorter rail wires; check the adapter is at 12.0 V under load |
| Buck gets hot | Pot set too high, short | Unplug, re-check OUT = 5.8 V with nothing connected |

## 4. Then the wiring dry run (decides what to return)

With the servos still loose, build the **jumper chains** (prototype v1 BOM): 2 jumpers per wire for
the gripper, 1 for the wrist and lift, tape every joint. Re-run tests 1–5 through the chains.
- All pass, joints stay put when you tug and bend them → **return the extension leads**.
- A joint drops out or a servo resets → keep the extension leads.

Record the results (angles that looked right, rail voltage in test 5) in the build log: they go in
the report's test section.

## Electronics first, or mechanics first?

**Electronics first**, in parallel with the prints. When the parts are done you assemble with
`servo_setup` (every horn fitted at its HOME angle), then load `concept_a` and calibrate. The full
order: bench test (this page) → print (plates 0–3) → assembly manual (`12_assembly_manual.pdf`) →
calibration (build guide section 6) → test runs.
