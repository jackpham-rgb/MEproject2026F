# Project notes for Claude

ME 2331/L Project 2, Concept A can-flipping robot. Push only to the session's `claude/...` branch.

## Standing rules from the team

- **The assembly manual (`docs/12_assembly_manual.pdf`) must contain everything needed to build and
  wire the robot**, not only the mechanical steps: the circuit connections (PART E, E1: wire list +
  diagram) and the full electronics bench test (E2–E5), before the mechanical steps (PART M).
  PART E is generated from `docs/04_wiring.md` ("Wire list") and `docs/13_electronics_bench_test.md`.
  Whenever wiring, power, pins or the bench test change, update those docs and re-run
  `node backend/tools/render_manual.js` so the manual stays complete.
- Any CAD change: re-run the checks (`backend/cad/check.py`, `backend/mech/mech_checks.py`,
  `backend/tools/make_manual.py` assembly check, `backend/cad/wiring.py`) and regenerate the print
  plates (`print_prep.py`, `plates.py`), drawings and manual.
- When the user asks to "just answer in chat", don't edit files.
