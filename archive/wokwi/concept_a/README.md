# Concept A in Wokwi

1. Go to wokwi.com → **New Project → Arduino Uno**.
2. In the `diagram.json` tab, replace everything with this folder's `diagram.json`.
3. In the `sketch.ino` tab, paste `firmware/concept_a/concept_a.ino`. The Servo library is built in.
4. Press ▶. Click the green **START** button. The 4 servos move one at a time:
   gripper closes → lift up → wrist flips 180° → turntable turns 90° → lift down → gripper opens.
5. Optional: set `#define PRINT_ANGLES 1`, run again, and open the **Serial Plotter**
   to watch the smooth slow–fast–slow curve of each move.

The yellow LED on D13 is the status light: blinking while moving, on when done.

In Wokwi the servos run from the Uno's 5 V pin. That's fine in a simulation, but on the real
robot a 12 V adapter feeds the Uno's VIN and an XL4015 buck at 5.8 V feeds the servos. See `docs/04_wiring.md`.

I checked the code on an emulated Uno (it runs the full sequence), but I haven't loaded this
diagram in Wokwi itself. If a wire shows up unconnected, check the pin names on first load.
