#!/usr/bin/env bash
# Build firmware/concept_a/concept_a.ino for the Uno with avr-gcc and run it headless in simavr.
# The test build presses START after 1 s (AUTO_START) and prints the 4 servo angles every tick.
#
#   sudo apt install gcc-avr avr-libc simavr      # once (Linux / WSL)
#   backend/tools/emulate_concept_a.sh [wall_seconds]     # default 330 (simavr is ~30x slower than real time)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
C=$ROOT/backend/.cache
WALL=${1:-330}
mkdir -p "$C"
[ -d "$C/ArduinoCore-avr" ] || git clone -q --depth 1 https://github.com/arduino/ArduinoCore-avr.git "$C/ArduinoCore-avr"
[ -d "$C/Servo" ] || git clone -q --depth 1 https://github.com/arduino-libraries/Servo.git "$C/Servo"
CORE=$C/ArduinoCore-avr/cores/arduino VAR=$C/ArduinoCore-avr/variants/standard SERVO=$C/Servo/src
FL="-mmcu=atmega328p -DF_CPU=16000000L -DARDUINO=10819 -DARDUINO_AVR_UNO -DARDUINO_ARCH_AVR -Os
    -ffunction-sections -fdata-sections -flto -I$CORE -I$VAR -I$SERVO"
XF="-std=gnu++11 -fno-exceptions -fno-threadsafe-statics"
B=$C/build_concept_a; rm -rf "$B"; mkdir -p "$B"
for f in "$CORE"/*.S; do avr-gcc $FL -x assembler-with-cpp -c "$f" -o "$B/core_$(basename "$f").o"; done
for f in "$CORE"/*.c; do avr-gcc $FL -c "$f" -o "$B/core_$(basename "$f").o"; done
for f in "$CORE"/*.cpp "$SERVO"/avr/Servo.cpp; do avr-g++ $FL $XF -w -c "$f" -o "$B/core_$(basename "$f").o"; done
avr-gcc-ar rcs "$B/core.a" "$B"/core_*.o
sketch() { { echo '#include <Arduino.h>'; echo '#line 1 "concept_a.ino"'; cat "$ROOT/firmware/concept_a/concept_a.ino"; } > "$B/$1.cpp"; }
sketch hw
avr-g++ $FL $XF -Wall -Wextra -c "$B/hw.cpp" -o "$B/hw.o"
avr-gcc -mmcu=atmega328p -Os -flto -fuse-linker-plugin -Wl,--gc-sections -o "$B/hw.elf" "$B/hw.o" "$B/core.a" -lm
echo "== real build"; avr-size -C --mcu=atmega328p "$B/hw.elf" | grep -E "Program|Data"
sketch test; sed -i 's/#define PRINT_ANGLES  0/#define PRINT_ANGLES  1/' "$B/test.cpp"
avr-g++ $FL $XF -DAUTO_START -c "$B/test.cpp" -o "$B/test.o"
avr-gcc -mmcu=atmega328p -Os -flto -fuse-linker-plugin -Wl,--gc-sections -o "$B/test.elf" "$B/test.o" "$B/core.a" -lm
echo "== running for ${WALL}s wall time (turn lift wrist grip)"
timeout "$WALL" stdbuf -o0 simavr -m atmega328p -f 16000000 "$B/test.elf" 2>&1 \
  | sed -u 's/\x1b\[[0-9;]*m//g; s/\.\.$//' > "$B/run.txt" || true
grep -v '^[0-9]' "$B/run.txt" | grep -v '^Loaded' || true
echo "angle samples: $(grep -c '^[0-9]' "$B/run.txt" || true)   full log: $B/run.txt"
