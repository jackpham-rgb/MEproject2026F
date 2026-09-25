#!/usr/bin/env bash
# Build the firmware for the ATmega328P (Arduino Uno) with plain avr-gcc and run it
# headless in simavr against the software plant (SIM_PLANT=1). No board, no IDE.
#
#   sudo apt install gcc-avr avr-libc simavr     # once
#   tools/emulate_uno.sh [seconds_of_wall_time]  # default 150 (simavr runs ~30x slower than real time)
#
# Also prints flash/RAM use of the real-hardware build (SIM_PLANT=0).
# Output: firmware/host_test/simavr_sim_plant_run.csv (+ state-change lines on stdout).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CACHE=$ROOT/tools/.cache
SK=$ROOT/firmware/can_flipper
WALL=${1:-150}
mkdir -p "$CACHE"
[ -d "$CACHE/ArduinoCore-avr" ] || git clone -q --depth 1 https://github.com/arduino/ArduinoCore-avr.git "$CACHE/ArduinoCore-avr"
[ -d "$CACHE/Servo" ] || git clone -q --depth 1 https://github.com/arduino-libraries/Servo.git "$CACHE/Servo"
CORE=$CACHE/ArduinoCore-avr/cores/arduino
VAR=$CACHE/ArduinoCore-avr/variants/standard
SERVO=$CACHE/Servo/src
FL="-mmcu=atmega328p -DF_CPU=16000000L -DARDUINO=10819 -DARDUINO_AVR_UNO -DARDUINO_ARCH_AVR -Os
    -ffunction-sections -fdata-sections -flto -I$CORE -I$VAR -I$SERVO"
CXXFL="-std=gnu++11 -fno-exceptions -fno-threadsafe-statics"

build() {  # $1 = build dir, rest = extra defines
  local B=$1; shift
  rm -rf "$B"; mkdir -p "$B"
  for f in "$CORE"/*.S; do avr-gcc $FL -x assembler-with-cpp -c "$f" -o "$B/core_$(basename "$f").o"; done
  for f in "$CORE"/*.c; do avr-gcc $FL -c "$f" -o "$B/core_$(basename "$f").o"; done
  for f in "$CORE"/*.cpp "$SERVO"/avr/Servo.cpp; do
    avr-g++ $FL $CXXFL -w -c "$f" -o "$B/core_$(basename "$f").o"
  done
  avr-gcc-ar rcs "$B/core.a" "$B"/core_*.o     # archive, like the IDE: only used objects link
  { echo '#include <Arduino.h>'; echo '#line 1 "can_flipper.ino"'; cat "$SK/can_flipper.ino"; } > "$B/sketch.cpp"
  avr-g++ $FL $CXXFL -Wall -Wextra "$@" -I"$SK" -c "$B/sketch.cpp" -o "$B/sketch.o"
  avr-gcc -mmcu=atmega328p -Os -flto -fuse-linker-plugin -Wl,--gc-sections -o "$B/fw.elf" "$B/sketch.o" "$B/core.a" -lm
}

echo "== hardware build (SIM_PLANT=0)"
build "$CACHE/build_hw" -DSIM_PLANT=0
avr-size -C --mcu=atmega328p "$CACHE/build_hw/fw.elf" | grep -E "Program|Data"
echo "== emulator build (SIM_PLANT=1, autostart)"
build "$CACHE/build_sim" -DSIM_PLANT=1 -DSIM_AUTOSTART
echo "== running simavr for ${WALL}s wall time"
timeout "$WALL" stdbuf -o0 -e0 simavr -m atmega328p -f 16000000 "$CACHE/build_sim/fw.elf" 2>&1 \
  | sed -u 's/\x1b\[[0-9;]*m//g; s/\.\.$//' > "$CACHE/simavr_raw.txt" || true
grep '^# ' "$CACHE/simavr_raw.txt" || true
grep -v '^#' "$CACHE/simavr_raw.txt" | grep ',' > "$ROOT/firmware/host_test/simavr_sim_plant_run.csv" || true
echo "== log: firmware/host_test/simavr_sim_plant_run.csv  (plot: python3 sim/plot_telemetry.py <log>)"
