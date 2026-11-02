# Concept A in Tinkercad Circuits

Free at **tinkercad.com**. Sign in, then go to **Circuits → Create new Circuit**.

## 1. Drag in the parts (search box, top right)

| Part in Tinkercad | Qty | Stands for |
|---|---|---|
| Arduino Uno R3 | 1 | Arduino Uno |
| Breadboard Small | 1 | breadboard |
| Micro Servo | 4 | turntable (MG996R), lift, wrist, gripper servos |
| Pushbutton | 1 | start button |
| LED (any colour) + Resistor (set to 220 Ω) | 1 + 1 | status light |

## 2. Power rails on the breadboard

- Uno **5V** → breadboard **+ rail** (red wire)
- Uno **GND** → breadboard **– rail** (black wire)

## 3. Wires

Tinkercad's micro servo has 3 pins: **Ground** (brown), **Power** (red), **Signal** (orange).

| From | To | Wire colour |
|---|---|---|
| Turntable servo Signal | Uno **D9** | orange |
| Lift servo Signal | Uno **D10** | orange |
| Wrist servo Signal | Uno **D6** | orange |
| Gripper servo Signal | Uno **D5** | orange |
| All 4 servos Power | + rail | red |
| All 4 servos Ground | – rail | black |
| Pushbutton, one leg | Uno **D4** | green |
| Pushbutton, diagonal leg | – rail | black |
| LED long leg (anode) | Uno **D13** | yellow |
| LED short leg → 220 Ω resistor → | – rail | black |

Tip: put the pushbutton across the middle gap of the breadboard, and use legs on opposite
corners so the press actually connects them.

## 4. Code

1. Click **Code** (top right) → change **Blocks** to **Text** → confirm.
2. Delete everything and paste `firmware/concept_a/concept_a.ino`.
3. Click **Start Simulation**, then click the pushbutton.
4. Open **Serial Monitor** (bottom of the code panel) to see each step: GRIP, LIFT, FLIP, TURN, LOWER, RELEASE, DONE.


## 5. Good to know

- Tinkercad only has a small micro servo, so all 4 look the same. That's fine for testing the
  code and wiring. The real turntable uses a stronger MG996R.
- Tinkercad powers the servos from the Uno's 5V pin. The real robot does the opposite: one
  **5 V, 4 A wall adapter** feeds the servo rail, and the rail feeds the Uno's 5V pin. The Uno's
  own 5 V regulator could never supply 4 servos. To show it in Tinkercad, add a **Power Supply**
  part set to 5 V on the + / – rails.
- The simulation shows the servo angles, not the can. For the motion, use the GIFs.
