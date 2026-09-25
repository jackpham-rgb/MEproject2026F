# Wokwi simulation

Wokwi has no DC gearmotor/encoder part, so the flip axis and FSR are simulated
inside the firmware (`SIM_PLANT=1`, see `firmware/can_flipper/plant_model.h`).
Wokwi then exercises the real sketch, state machine, Servo output, start button
and serial telemetry on a simulated Uno.

1. New Arduino Uno project on wokwi.com.
2. Replace `diagram.json` with the one in this folder.
3. Add `can_flipper.ino`, `config.h`, `control.h`, `sequencer.h`, `plant_model.h`
   from `firmware/can_flipper/` as project files.
4. In `config.h` set `#define SIM_PLANT 1`.
5. Start, open the serial monitor, press START (or type `g`). The servo closes,
   and the telemetry shows the full HOME→…→DONE sequence.

The HC-SR04 and slide switch are wired to the real pins (D11/D12, D10) so the same
diagram works for a `SIM_PLANT=0` wiring check. In SIM_PLANT builds they are
ignored in favour of the plant model.

Headless alternative that I could run without a browser: `tools/emulate_uno.sh`
(simavr). I haven't run this Wokwi diagram. It was written from Wokwi's part
pin names and should be checked on first load.
