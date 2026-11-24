cd "$(dirname "$0")/../.."
run(){ echo "=== $1"; shift; ( "$@" ) 2>&1 | tail -4; echo "--- exit ${PIPESTATUS[0]}"; }
run manual_steps python3.13 backend/tools/make_manual.py
run export python3.13 backend/cad/export.py
run check python3.13 backend/cad/check.py
run mech python3.13 backend/mech/mech_checks.py
run wiring python3.13 backend/cad/wiring.py
run wiring_motion python3.13 backend/cad/wiring_motion.py
run print_prep python3.13 backend/cad/print_prep.py
run drawings python3.13 backend/cad/drawings.py
run fingers python3.13 backend/cad/finger_variants.py
run inis python3.13 backend/tools/make_plate_inis.py
run plates python3.13 backend/tools/make_plate_files.py
run plate_R python3.13 backend/tools/make_reprint_plate.py
run economy python3.13 backend/tools/print_economy.py
run visual python3.13 backend/cad/visual.py
run tool_access python3.13 backend/tools/tool_access_check.py
run reprint python3.13 backend/tools/make_reprint.py
run manual node backend/tools/render_manual.js

run planb python3.13 backend/cad/planb.py
echo "=== CHAIN DONE"
