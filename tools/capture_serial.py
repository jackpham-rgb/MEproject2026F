"""Save the Uno's serial telemetry to a CSV file (then plot it with sim/plot_telemetry.py).

    pip install pyserial
    python3 tools/capture_serial.py --port COM5 --out runs/run1.csv          # Windows
    python3 tools/capture_serial.py --port /dev/cu.usbmodem14101 --out runs/run1.csv   # macOS
    python3 tools/capture_serial.py --list                                     # show ports

Sends 'g' to start the sequence (add --no-start to press the button yourself) and
stops at DONE or FAULT, or after --seconds. Close the Arduino IDE Serial Monitor
first: only one program can hold the port.
"""
import argparse
import os
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is missing: pip install pyserial")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=250000)
    ap.add_argument("--out", default="runs/run.csv")
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--no-start", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.port:
        for p in list_ports.comports():
            print(f"{p.device:24s} {p.description}")
        if not a.port:
            print("\npass --port <one of the above>")
        return
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with serial.Serial(a.port, a.baud, timeout=0.2) as s, open(a.out, "w") as f:
        time.sleep(2.0)                     # opening the port resets the Uno; wait for boot + homing
        s.reset_input_buffer()
        if not a.no_start:
            s.write(b"g")
        t0 = time.time()
        while time.time() - t0 < a.seconds:
            line = s.readline().decode(errors="replace").strip()
            if not line:
                continue
            f.write(line + "\n")
            if line.startswith("#"):
                print(line)
                if "-> DONE" in line or "-> FAULT" in line:
                    break
    print(f"saved {a.out}  ->  python3 sim/plot_telemetry.py {a.out}")


if __name__ == "__main__":
    main()
