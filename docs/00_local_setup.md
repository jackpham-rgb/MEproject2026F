# Running Everything on Your Laptop

Every part is optional and independent. Take them in order of usefulness.

## 0. Get the files

```bash
git clone https://github.com/jackpham-rgb/MEproject2026F.git
cd MEproject2026F
git checkout claude/awesome-brahmagupta-i4dvbh     # the work lives on this branch until it's merged
```

No git? On GitHub, switch to the branch, then **Code → Download ZIP**.

## 1. Look at things (no installs)

| What | How |
|---|---|
| Notes doc to share | `docs/Project_Notes_ConceptA.docx` (Word or Google Docs) |
| All four concepts, animated | Double-click `viewer/concepts.html`. It needs internet, because three.js loads from a CDN |
| GIFs for docs and slides | `viewer/gifs/` |
| Plots | `sim/out/concept_a_*.png` |
| Design docs | `docs/*.md` (GitHub renders them) |
| Breadboard simulation | Tinkercad: `docs/tinkercad_concept_a.md`. Wokwi: `wokwi/concept_a/README.md` |

## 2. Arduino IDE (needed for the build anyway)

1. Install **Arduino IDE 2.x** (arduino.cc/en/software). The Servo library is built in.
2. **File → Open** `firmware/concept_a/concept_a.ino`. Don't rename the folder: the IDE requires the
   folder name to match the `.ino`.
3. **Tools → Board → Arduino Uno**, pick the port, then **Verify** (✓). It should report about
   19 % flash.
4. Wire the servos per `docs/04_wiring_and_bom.md`, upload, open the Serial Monitor at
   **9600 baud**, and press the button. Each step is printed: GRIP, LIFT, FLIP, TURN, LOWER,
   RELEASE, DONE.
5. **Calibrate:** change the angle constants at the top of the file (`TURN_START`, `LIFT_UP`,
   `GRIP_CLOSED`…) until each move is right on the real robot. Set `PRINT_ANGLES 1` to watch the
   curves in the Serial Plotter.

## 3. Python (design calcs, plots, CAD export)

Install Python 3.10+ from python.org. On Windows, tick "Add to PATH" and use `py` in place of
`python3`.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r sim/requirements.txt
python3 sim/concept_a.py           # lift clearance, grip, servo loads, jam check -> sim/out/concept_a*
```

The script reads the angles and times from `concept_a.ino`. Rerun it after you change the code
or put real masses into its `M = {...}` table.

Optional:

```bash
pip install cadquery               # ~300 MB; regenerates the STEP/STL files
python3 cad/build_cad_concept_a.py # -> cad/out/concept_a/
```

## 4. Fusion 360 (animate the CAD)

Fusion 360 is free with an education licence (autodesk.com/education). Open
`cad/out/concept_a/concept_a_assembly.step` and follow `cad/README.md`: ground `fixed`, then add
a revolute joint (turret), a slider (lift) and a revolute joint (wrist). SolidWorks can open the
same STEP.

## 5. AVR emulator (optional; Linux or WSL only)

```bash
sudo apt install gcc-avr avr-libc simavr
tools/emulate_concept_a.sh         # compiles the sketch and runs it on an emulated Uno, ~5 min
```

Skip this on macOS. Tinkercad or Wokwi test the same code in the browser.

## 6. Concept D (alternative) tools

D's closed-loop firmware and sims are still in the repo: `firmware/can_flipper/`,
`make -C firmware/host_test`, `tools/emulate_uno.sh`, `python3 sim/flip_control.py`,
`viewer/index.html`. Their docs are in `docs/concept_d/`.

## 7. Logging real runs (Concept D firmware only)

Close the IDE Serial Monitor first, because only one program can use the port.

```bash
python3 tools/capture_serial.py --list                              # find the port
python3 tools/capture_serial.py --port COM5 --out runs/run1.csv     # macOS: /dev/cu.usbmodem…
python3 sim/plot_telemetry.py runs/run1.csv                         # plot + tracking/landing/grip metrics
```

The same plotter reads the emulator log, so you can compare simulated and measured runs directly.
