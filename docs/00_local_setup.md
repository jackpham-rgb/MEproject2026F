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
| 3D replay + charts + wiring | Double-click `viewer/index.html`. It needs internet, because three.js loads from a CDN |
| Plots | `sim/out/*.png` |
| Design docs | `docs/*.md` (GitHub renders them) |
| Wiring simulation | wokwi.com in the browser: steps in `wokwi/README.md` |

## 2. Arduino IDE (needed for the build anyway)

1. Install **Arduino IDE 2.x** (arduino.cc/en/software). The Servo library is built in.
2. **File → Open** `firmware/can_flipper/can_flipper.ino`. The `.h` files in that folder open as
   tabs. Don't rename the folder: the IDE requires the folder name to match the `.ino`.
3. **Tools → Board → Arduino Uno**, pick the port, then **Verify** (✓). It should report about
   36 % flash.
4. **Test on a bare Uno with no mechanism:** in `config.h` set `#define SIM_PLANT 1` and upload.
   Open the Serial Monitor at **250000 baud** and type `g`. The Uno runs the whole
   HOME → … → DONE sequence against the built-in plant model and prints telemetry. A servo on D9
   will actually open and close. **Set it back to `SIM_PLANT 0` before wiring the real robot.**

Serial commands: `g` start · `r` reset after a fault · `i` open-loop motor step for system ID.

## 3. Python (simulations, plots, CAD export)

Install Python 3.10+ from python.org. On Windows, tick "Add to PATH" and use `py` in place of
`python3`.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r sim/requirements.txt
python3 sim/flip_geometry.py       # clearance + error budget      -> sim/out/
python3 sim/flip_control.py        # motor model, PID, robustness  -> sim/out/
python3 sim/grip_control.py        # grip force loop                -> sim/out/
python3 sim/mechanism.py           # part collision sweep + geometry for CAD/viewer
```

Optional extras:

```bash
pip install cadquery               # ~300 MB; regenerates the STEP/STL files
python3 cad/build_cad.py           # -> cad/out/
python3 tools/build_viewer.py      # rebuild viewer/index.html after changing geometry or firmware
pip install pyserial               # to log real runs from the Uno
```

**After changing a number** in `sim/params.py`, rerun the scripts. If controller gains change,
copy them into `firmware/can_flipper/config.h`.

## 4. Fusion 360 (animate the CAD)

Fusion 360 is free with an education licence (autodesk.com/education). Open
`cad/out/can_flipper_assembly.step`, then follow the 5 steps in `cad/README.md`: ground `fixed`,
add a revolute joint on the hub, run a Motion Study from 0° to 180°. SolidWorks can open the same
STEP.

## 5. Laptop firmware test (optional; C++ compiler + make)

```bash
make -C firmware/host_test         # prints "all checks passed" (11 scenarios)
```

- **macOS:** `xcode-select --install`
- **Windows:** use WSL (`wsl --install`, then `sudo apt install build-essential` inside Ubuntu)
- **Linux:** `sudo apt install build-essential`

Rerun it whenever you change `config.h`, `control.h` or `sequencer.h`.

## 6. AVR emulator (optional; Linux or WSL only)

```bash
sudo apt install gcc-avr avr-libc simavr
tools/emulate_uno.sh               # runs the real Uno binary headless, ~2.5 min
```

Skip this on macOS. Step 2.4 (SIM_PLANT on a real Uno) tests the same thing on real hardware.

## 7. Logging real runs for the Part C report (Phase 2)

Close the IDE Serial Monitor first, because only one program can use the port.

```bash
python3 tools/capture_serial.py --list                              # find the port
python3 tools/capture_serial.py --port COM5 --out runs/run1.csv     # macOS: /dev/cu.usbmodem…
python3 sim/plot_telemetry.py runs/run1.csv                         # plot + tracking/landing/grip metrics
```

The same plotter reads the emulator log, so you can compare simulated and measured runs directly.
