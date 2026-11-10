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
| 5 | **9 V battery** → Uno barrel jack (snap clip with a 5.5 × 2.1 mm plug). Meter on the battery first | Unplug USB, plug the battery | Battery ≥ 8.5 V (fresh ~9.3 V); LED blinks 3× again (running on the battery) |
| 5b | Uno **GND** → rail **−** (common ground: required) | Meter between Uno GND and the buck OUT− | 0 Ω / beeps |
| 6 | START button: D4 ↔ GND. LED: D13 → 220 Ω → LED → GND | Press START | LED lights while pressed |

**Never** connect the rail (5.8 V) to the Uno's 5V pin. The Uno gets its power only from the 9 V battery
(jack or VIN); the 12 V adapter feeds only the buck. The 1000 µF capacitor is optional while testing:
skip row 3 if you don't have one yet, and fit it before the final runs.

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

## 2b. Laptop control panel (the whole program, from the laptop)

1. Upload `firmware/concept_a/concept_a.ino` with the Arduino IDE, then **close the IDE's Serial Monitor**
   (only one program can use the USB port).
2. Open `viewer/control_panel.html` in **Chrome or Edge** (or the project site link). Click
   **Connect to Arduino** and pick the Uno's port. The Uno restarts; after ~2 s the angles appear.
3. Each servo has a slider, ±5° buttons and its working angles (base START 135° / TARGET 45°, lift DOWN / UP,
   wrist UPRIGHT / FLIPPED, grip OPEN / RELEASE / CLOSED). Every move is smooth and stays inside safe limits.
4. **HOME** brings the robot home one servo at a time. **START** runs the whole sequence (same as the
   physical button, which keeps working). START only runs from HOME. **STOP** (or Esc) holds where it is.

| Check | Expected |
|---|---|
| Each servo button | Only that servo moves, to that angle, smoothly |
| HOME | Lift up → wrist → base → grip → lift down |
| START at HOME | GRIP → LIFT → FLIP → TURN → LOWER → RELEASE, ends DONE |
| START again after DONE (can removed) | Goes home |
| STOP during a move | Holds; HOME before the next START |

Tested without hardware: the firmware's commands on a simulated Uno (`backend/tools/firmware_test/run.sh`,
15 checks) and the page driving the live firmware through a fake USB port (`panel_test.js`, 11 checks).

## 3. If something is wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Uno resets (blinks 3×) when a servo moves | 9 V battery flat, or the servo supply wired to the Uno by mistake | Battery < 7.5 V: replace it. Check nothing from the rail goes to the Uno's 5V or VIN |
| Servos twitch or don't respond at all | No common ground | Uno GND ↔ rail − (row 5b) |
| Servo buzzes / jitters | Signal without ground, loose jumper | Re-seat; shorter jumpers; ground first |
| Servo doesn't move at all | Signal on the wrong pin, dead servo | Swap the plug to a known-good test; try the spare |
| One servo works sometimes, then stops responding | Cable / dupont joint (most often), power at its plug, or the servo | **Swap test** (unmounted, horn off): plug that servo into a good servo's cable, and a good servo into its cable. Problem follows the servo → servo; stays with the cable / pin → wiring; both fine → it was a loose joint. Same code drives all four, so code alone is unlikely |
| Wrist stops short of 180° | That MG90S's range | `servo_setup`: try `WRIST_MIN_US` / `WRIST_MAX_US` 450 / 2550; else swap MG90S (buy a spare) |
| Rail below 5.5 V in test 5 | Weak adapter / long thin wires / no capacitor | Shorter rail wires; check the adapter is at 12.0 V under load; fit the 1000 µF |
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
