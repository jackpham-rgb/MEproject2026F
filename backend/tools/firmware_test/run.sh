#!/usr/bin/env bash
# Compile and run the firmware's host test (fake Arduino on the PC). Needs g++.
set -euo pipefail
cd "$(dirname "$0")"
BIN="${TMPDIR:-/tmp}/concept_a_host_test"
g++ -std=c++17 -Wall -Wno-unused-parameter -Ifake -o "$BIN" host_test.cpp && "$BIN"
