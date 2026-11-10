"""Compile every sketch the way the Arduino IDE does, so IDE-only errors show up here too.

    python3 backend/tools/arduino_build_check.py

The IDE adds `#include <Arduino.h>` and writes a prototype for every top-level function, inserted just
above the FIRST function definition in the file. A function whose header uses a type (struct / enum)
declared further down then fails in the IDE ("'Mode' was not declared in this scope") even though a
plain compiler build passes. This reproduces that step, then compiles with avr-g++ for the Uno
(core + Servo from backend/.cache, see backend/tools/emulate_concept_a.sh).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
C = os.path.join(ROOT, "backend", ".cache")
CORE = os.path.join(C, "ArduinoCore-avr", "cores", "arduino")
VAR = os.path.join(C, "ArduinoCore-avr", "variants", "standard")
SERVO = os.path.join(C, "Servo", "src")
CORE_A = os.path.join(C, "build_bench", "core.a")
SKETCHES = ["firmware/concept_a/concept_a.ino", "firmware/servo_setup/servo_setup.ino", "firmware/bench_test/bench_test.ino"]
FUNC = re.compile(r"^(?!\s)(?!(?:if|for|while|switch|else|return|struct|enum|class|typedef)\b)"
                  r"([A-Za-z_][\w\s\*&:<>,]*?[\s\*&]+)([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\{")


def preprocess(src):
    lines = src.split("\n")
    protos, first = [], None
    for i, ln in enumerate(lines):
        m = FUNC.match(ln)
        if m and m.group(2) not in ("setup", "loop"):
            protos.append(f"{m.group(1).strip()} {m.group(2)}({m.group(3)});")
            first = i if first is None else first
        elif m and first is None:
            first = i
    if first is None:
        return "#include <Arduino.h>\n" + src
    head = "\n".join(lines[:first])
    body = "\n".join(lines[first:])
    return ("#include <Arduino.h>\n" + head + "\n" + "\n".join(protos) + f"\n#line {first + 1}\n" + body)


def main():
    fl = ["-mmcu=atmega328p", "-DF_CPU=16000000L", "-DARDUINO=10819", "-DARDUINO_AVR_UNO", "-DARDUINO_ARCH_AVR", "-Os",
          "-ffunction-sections", "-fdata-sections", "-flto", "-I" + CORE, "-I" + VAR, "-I" + SERVO,
          "-std=gnu++11", "-fno-exceptions", "-fno-threadsafe-statics", "-Wall", "-Wextra"]
    if not os.path.exists(CORE_A):
        sys.exit("build the Arduino core first (backend/tools/emulate_concept_a.sh or the bench-test build)")
    ok = True
    out = os.path.join(C, "ide_check"); os.makedirs(out, exist_ok=True)
    for sk in SKETCHES:
        name = os.path.splitext(os.path.basename(sk))[0]
        cpp = os.path.join(out, name + ".cpp")
        open(cpp, "w").write(preprocess(open(os.path.join(ROOT, sk)).read()))
        r = subprocess.run(["avr-g++", *fl, "-c", cpp, "-o", cpp + ".o"], capture_output=True, text=True)
        if r.returncode == 0:
            r = subprocess.run(["avr-gcc", "-mmcu=atmega328p", "-Os", "-flto", "-fuse-linker-plugin", "-Wl,--gc-sections",
                                "-o", cpp + ".elf", cpp + ".o", CORE_A, "-lm"], capture_output=True, text=True)
        size = ""
        if r.returncode == 0:
            sz = subprocess.run(["avr-size", "-C", "--mcu=atmega328p", cpp + ".elf"], capture_output=True, text=True).stdout
            size = re.search(r"Program:\s+(\d+ bytes \([\d.]+% Full\))", sz).group(1)
        print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  {sk:42s} {size}")
        if r.returncode != 0:
            ok = False
            print((r.stderr or r.stdout)[-2000:])
        elif r.stderr.strip():
            print("   warnings:\n" + r.stderr[-1500:])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
