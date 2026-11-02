"""Concept A tables: BOM + decision matrices.

    python3 tools/make_tables.py

Writes
  docs/05_bom.md, docs/bom.csv                         top-level BOM with "why we need it" / "alternative, why not"
  docs/decision_matrix_concepts.csv                    binary matrix: concepts A-D
  docs/decision_matrix_power.csv                       binary matrix: power source options
  docs/decision_matrix_and_bom.xlsx                    all three as sheets (totals and ranks are Excel formulas)

Scoring: 1 = yes / good, 0 = no / bad. Every score carries the number or fact behind it.
Printed masses come from cad/out/mass_table.csv (written by cad/check.py). Prices are typical
online prices (EST), not quotes.
"""
import csv
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

mass = {}
with open(os.path.join(ROOT, "cad/out/mass_table.csv")) as f:
    for r in csv.DictReader(f):
        mass[r["part"]] = float(r["mass_g"])
mass.setdefault("tolerance_coupon", 10.81 * 1.27 * 0.60)   # not in the robot mass table: 10.81 cm3 (cad/out/parts)

# ------------------------------------------------------------------ concepts
CONCEPTS = ["A: claw + wrist flip + turntable", "B: cradle flip + drag", "C: multi-DOF pincer arm", "D: mirror flip (diagonal axis)"]
# (criterion, [(score, why) for A, B, C, D])
CONCEPT_ROWS = [
    ("Robot visibly turns 90° about its own location", [
        (1, "Turntable at the corner turns 90°; can stays 5 in (127 mm) out"),
        (1, "Same turntable, 90°"),
        (1, "Base yaw joint turns 90°"),
        (0, "One 180° roll about a 45° axis; the robot never rotates, the 90° only shows in plan view")]),
    ("Can is held for the whole move (never slid or dropped)", [
        (1, "Held GRIP → RELEASE; lowered to z = 0.00 mm before opening (CAD check)"),
        (0, "Dragged 7.9 in (5 in × π/2) on its thin rim"),
        (1, "Held until set down"),
        (1, "Held; released 2 mm (0.08 in) above the table")]),
    ("Landing spot set by geometry, not fine tuning", [
        (1, "Flip about the can centre: lowering 0.6 in = lift 0.6 in; ±2° turn = ±0.17 in"),
        (0, "Rim friction on the table decides where it stops"),
        (0, "3-joint inverse kinematics; ~1° backlash per servo stacks to ~0.3 in"),
        (1, "Exact by symmetry of the 180° roll")]),
    ("3 or fewer actuators (fewer failure points)", [
        (0, "4 servos"), (0, "4 actuators"), (0, "5 servos"), (1, "2: gearmotor + grip servo")]),
    ("Hobby servos only (no encoder, motor driver or PID)", [
        (1, "4 servos, open loop"), (1, "Servos"), (1, "Servos"),
        (0, "Gearmotor + encoder + driver; closed loop needed (overshoot > 0.9° hits the table)")]),
    ("One move at a time, each testable on its own", [
        (1, "6 steps: grip, lift, flip, turn, lower, release"), (1, "Clamp, lift, flip, drag, release"),
        (0, "Joints must move together for a straight path"), (1, "One flip move")]),
    ("No build-critical dimension tighter than ±1 mm", [
        (1, "Lift gives +0.27 in (6.9 mm) table clearance; slots and pilots from the tolerance coupon"),
        (1, "Cradle fits loosely around the can"),
        (0, "Link lengths feed the IK; errors add up at the 5 in reach"),
        (0, "Axis height ±0.04 in (±1 mm) or the rim hits the table")]),
    ("Servo torque margin ≥ 3×", [
        (1, "CAD loads: lift 5×, wrist 30×, turntable > 100× (weight on the bearing)"),
        (1, "Similar servos and loads to A"),
        (0, "Shoulder holds arm + can at 5 in: ~1.5 kg·cm vs 1.8 for an MG90S (1.2×)"),
        (1, "18 mN·m (0.18 kg·cm) after the counterweight")]),
    ("Can path stays clear of the robot body", [
        (1, "No collisions in 289 poses (CAD solid check)"), (1, "Can stays outside the base"),
        (1, "Can stays outside the base"), (0, "Can passes over the robot; base must stay low")]),
    ("No separate lift axis needed", [
        (0, "Needs a 0.6 in lift: without it the can digs 0.33 in into the table"),
        (0, "Same in-place flip, same lift"),
        (1, "Shoulder lifts the can"),
        (1, "Can arrives moving straight down; +0.06 in clearance mid-flip")]),
]

# ------------------------------------------------------------------ power
POWERS = ["9 V battery (PP3) + buck", "4×AA NiMH (servos) + 9 V (Uno)", "2S LiPo 7.4 V + buck",
          "12 V wall adapter + XL4015 buck 5.8 V (selected)", "5 V 4 A wall adapter, direct"]
# Rows 1, 5, 6 and 7 come from the ngspice runs in EE/ee_calcs.py (EE/out/ee_report.txt, section 6).
POWER_ROWS = [
    ("Covers a 2.5 A MG996R stall without current-limiting", [
        (0, "A PP3 gives ~0.5–1 A; under 2.5 A it collapses"),
        (1, "NiMH AA cells handle 2–3 A"), (1, "LiPo handles > 10 A"),
        (1, "ngspice: 12 V side 1.79 A of 2 A; buck 3.1 A of 5 A"), (1, "ngspice: 3.16 A of 4 A")]),
    ("No batteries to charge, replace or monitor", [
        (0, "~500 mAh, voltage drops as it drains"), (0, "Two packs to keep charged"), (0, "Needs balance charging"),
        (1, "Wall power"), (1, "Wall power")]),
    ("One power source for the whole robot", [
        (1, "One battery"), (0, "Two packs (servos and Uno)"), (1, "One pack"), (1, "One plug"), (1, "One plug")]),
    ("No extra power board to set up", [
        (0, "Buck must be set with a meter"), (1, "4.8 V pack, nothing to set"), (0, "Buck must be set"),
        (0, "Buck set to 5.8 V once with a meter"), (1, "Fixed 5 V")]),
    ("Servos stay ≥ 4.8 V (rated) in a stall", [
        (0, "Battery sags below the buck's input need"), (0, "4.8 V nominal pack sags under 2.5 A"), (1, "Buck holds its output"),
        (1, "ngspice: min 5.50 V"), (0, "ngspice: min 4.25 V (cord + adapter drop)")]),
    ("Uno stays ≥ 4.5 V (16 MHz minimum) in a stall", [
        (0, "Same sagging battery feeds VIN"), (1, "Uno on its own 9 V"), (1, "7.4 V on VIN → 5 V"),
        (1, "ngspice: 5.00 V, Uno on its own regulator"), (0, "ngspice: min 4.43 V, shares the servo rail")]),
    ("USB can stay plugged in for calibration (Serial Monitor)", [
        (1, "Uno on VIN: switches USB power off"), (1, "Uno on VIN"), (1, "Uno on VIN"),
        (1, "Uno on VIN above 6.6 V: switches USB power off"), (0, "Adapter on the 5V pin: two 5 V sources fight")]),
    ("No special charger, no fire-risk cell", [
        (1, "Alkaline, disposable"), (0, "Needs a NiMH charger"), (0, "LiPo charger + fire-safe bag"), (1, "None"), (1, "None")]),
    ("Power parts cost ≤ $12", [
        (1, "~$3 battery + $5 buck"), (0, "~$12 cells + $2 holder + $15 charger"), (0, "~$15 pack + $20 charger + $5 buck"),
        (0, "~$8 adapter + $5 buck = $13"), (1, "~$9 adapter")]),
]

# ------------------------------------------------------------------ BOM
# part no, name, model key, material, qty, what it does, why we need it, alternative considered -> why not
DESIGNED = [
    ("CA-101", "Base", "base", "PETG", 1, "Bearing tower, MG996R pocket, ballast pockets; sweep sector cut away",
     "Holds the turntable and gives the robot its footprint (CG stays ≥ 39 mm inside it in every pose)",
     "Flat plywood/acrylic plate → the tower, servo pocket and sweep cut-out would be several glued pieces"),
    ("CA-102", "Electronics tray", "electronics_tray", "PETG", 1, "Uno, buck, servo rail, button / LED / DC-jack panel",
     "Keeps the electronics and wires out of the arm's 175° sweep",
     "Loose on the table → wires can snag the turning arm and the button moves around"),
    ("CA-201", "Turret plate", "turret_plate", "PETG", 1, "D plate + hub pressed into the 6807 bore, rod bosses",
     "Puts the column's weight and tipping load on the bearing, so the servo only turns it",
     "Column screwed to the servo horn → the servo spline carries all the bending load"),
    ("CA-202", "Spine", "spine", "PETG", 1, "Column back + lift-servo bracket",
     "Ties the rods to the turret and holds the lift servo",
     "Aluminium extrusion → extra cost and brackets for no gain at this load"),
    ("CA-203", "Top cap", "top_cap", "PETG", 1, "Captures the rod tops",
     "Keeps the 2 rods parallel so the 4 LM6UU slide without binding",
     "Rods held only at the bottom → they splay and the carriage jams"),
    ("CA-301", "Carriage + arm", "carriage_arm", "PETG", 1, "4 LM6UU pockets, arm, wrist-servo bracket",
     "One print: the arm can't work loose; bearings 43 mm apart keep the jam ratio at 0.018",
     "Separate arm screwed on → the joint sags under the can's 2.6 in offset"),
    ("CA-302", "Lift link", "lift_link", "PETG", 1, "Crank pin to carriage",
     "Turns the lift servo's 45° swing into a 15.3 mm (0.6 in) straight lift",
     "Printed rack and pinion → more teeth to print, more backlash"),
    ("CA-401", "Gripper frame", "gripper_frame", "PETG", 1, "Flange + 2 plates + posts",
     "Holds the gripper servo and both finger axles on the wrist horn",
     "Servo bracket from a kit → doesn't hold geared fingers at the right centre distance (16.2 mm)"),
    ("CA-402", "Finger, right", "finger_R", "PETG", 1, "Gear m1 16T + arm + curved pad",
     "Geared to the left finger so one servo closes both arms equally and centres the can",
     "One fixed + one moving arm → pushes the can off-centre"),
    ("CA-403", "Finger, left", "finger_L", "PETG", 1, "Mirror; gear has the servo-spline socket", "As CA-402", "As CA-402"),
    ("CA-404", "Can bumper", "can_bumper", "Silicone sheet", 1, "Cut from the pad sheet, glued to the gripper frame",
     "Sets how deep the can sits in the gripper, so every grip and landing is the same",
     "No stop → grip depth varies with how the can is placed"),
    ("CA-900", "Tolerance coupon", "tolerance_coupon", "PETG", 1, "6 test holes",
     "Checks screw, rod and bearing fits on our printer before ~300 g of parts",
     "Print the parts first → one wrong fit wastes hours of printing"),
]

# part no, item, spec, qty, source, unit $ (EST), used for, why we need it, alternative -> why not
PURCHASED = [
    ("Arduino Uno R3", "ATmega328P board + USB cable", 1, "Kit (have)", 0, "Controller",
     "Required by the assignment; runs the 4 servos and the button", "Nano / ESP32 → no benefit, the Uno is in the kit"),
    ("Servo MG996R", "Metal gear, 180°, 9.4 kg·cm", 1, "Amazon", 9, "Turntable (D9)",
     "Metal gears keep the swinging arm from wobbling at the 5 in reach", "SG90 → plastic gears, backlash shows up as ±0.1 in at the can"),
    ("Servo MG90S", "Metal gear micro, 1.8 kg·cm", 2, "Amazon", 4, "Lift (D10) + wrist (D6)",
     "Lift margin 5×, wrist 30×; metal gears so the wrist lands at 180° (500–2500 µs pulse in code)",
     "Stepper motors → need drivers and homing switches; 270° servo → a 2nd servo type for no gain"),
    ("Servo SG90", "Micro, 1.6 kg·cm", 1, "Kit (have)", 0, "Gripper (D5)",
     "A light squeeze is what we want: 0.4 N holds the can, it dents at ~8 N per arm",
     "MG90S → stronger than needed, more risk of crushing the can"),
    ("Ball bearing 6807-2RS", "35 × 47 × 7 mm", 1, "Amazon / VXB", 5, "Turntable",
     "Carries the arm's weight and tipping moment so the servo only turns it",
     "4 in lazy-susan → too tall, it collided with the wrist in the CAD check; servo alone → side load on the spline"),
    ("Linear bearing LM6UU", "6 mm ID × 12 mm OD × 19 mm", 4, "Amazon", 1, "Lift carriage",
     "Jam ratio 0.018, the lift can't stick", "Printed slide → jam ratio 0.55, it can bind"),
    ("Steel rod 6 mm (h6), 300 mm long", "Cut to 2 × 112 mm", 1, "Amazon", 5, "Lift guide rods",
     "Straight, hard track for the LM6UU", "Printed rails → too rough and soft for the bearings"),
    ("Wall adapter 12 V, 2 A", "Regulated, 5.5 × 2.1 mm plug", 1, "Amazon", 8, "Uno VIN + buck input",
     "Power matrix 7/9: wall power, one plug, and the Uno keeps its own regulator (5.00 V even in a servo stall)",
     "5 V 4 A adapter direct → simpler (6/9) but Uno dips to 4.43 V in a stall and USB can't stay plugged in; 9 V battery → can't supply 2.5 A (4/9)"),
    ("Buck converter XL4015", "5 A, set to 5.8 V", 1, "Amazon", 5, "Servo rail",
     "Holds the servos at 5.8 V (≥ 5.5 V in a stall, ngspice) and keeps their current off the Uno's supply",
     "No buck (5 V adapter direct) → servos sag to 4.25 V and the Uno to 4.43 V in a stall"),
    ("DC panel jack", "5.5 × 2.1 mm, panel mount", 1, "Amazon", 1, "Power input",
     "Adapter plugs into the robot; no loose wires to pull out", "Screw terminal → wires pull out when bumped"),
    ("Electrolytic capacitor", "1000 µF, ≥ 10 V", 1, "Kit (have)", 0, "Servo rail",
     "Covers fast current steps at the servo rail (1 A for 100 µs → 0.10 V droop)", "None → larger dips each time a servo starts"),
    ("Push button", "12 mm momentary", 1, "Kit (have)", 0, "START (D4)",
     "Spec: one start, then no human input. A button is one wire, one pin, nothing to pair or lose",
     "IR remote → receiver + library + batteries, stray IR can trigger it; timer → can't choose when it starts"),
    ("LED + 220 Ω resistor", "5 mm", 1, "Kit (have)", 0, "Status (D13)",
     "Blinking = moving, on = done: tells you when to lift the can off before homing",
     "Serial Monitor only → needs a laptop at the demo"),
    ("Mini breadboard", "170 tie points", 1, "Kit (have)", 0, "Servo rail",
     "Splits the buck's 5.8 V to the 3 micro servos (each < 1 A, inside a contact's rating)", "Soldered perfboard → harder to change while calibrating"),
    ("Jumper wires", "M-M / M-F", 20, "Kit (have)", 0, "Signals, ground",
     "Connects the servo signals, button and LED", "Soldered wires → harder to fix"),
    ("Servo extension lead", "300 mm", 4, "Amazon", 1, "Lift, wrist, gripper; 1 cut for the MG996R",
     "Column servos need 300 mm with a loop for the 90° turn; one is cut so the MG996R's + / − go to the buck terminals",
     "None → leads pull tight at the end of the turn; MG996R stall current would run through breadboard contacts (~1 A)"),
    ("Machine screw #6-32 × ½″", "Pan Phillips, HF kit #67675", 8, "Have", 0, "Tray 2, spine 2, top cap 2, link 1, gear axle 1",
     "Threads into printed pilots, no nuts needed", "Glue → can't take apart to fix or adjust"),
    ("Machine screw #8-32 × ½″", "Pan Phillips, HF kit #67675", 4, "Have", 0, "MG996R flange",
     "The MG996R's 4.6 mm flange holes fit #8", "#6 → loose in the flange"),
    ("Servo-bag screws", "Come with the servos", 14, "With servos", 0, "Servo tabs, horns, crank",
     "Sized for the servo tabs and horns", "Kit screws → too big for the micro-servo tabs"),
    ("Silicone rubber sheet", "3/32 in (2.4 mm), ~6 × 6 in", 1, "Amazon", 6, "Finger pads + can bumper",
     "Grippy pads (μ ≈ 0.6) keep the squeeze needed low (0.4 N), so the can isn't dented",
     "Bare PETG pads → slippery, needs a harder squeeze; TPU → a second filament for 1 g of parts"),
    ("Steel washers + rubber feet", "~100 g of washers, 4 feet", 1, "Hardware store", 3, "Base",
     "Weight and friction so the turning reaction doesn't slide the base", "Clamp to the table → the demo table may not allow it"),
    ("PETG filament", "1.75 mm, ~0.35 kg", 1, "Have", 0, "Printed parts",
     "Tougher than PLA and creeps less under the press fits (bearing, LM6UU, rods)", "PLA → press fits loosen over time"),
]


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ------------------------------------------------------------------ CSV + markdown
def matrix_csv(path, options, rows):
    header = ["#", "criterion (1 = yes / good, 0 = no / bad)"]
    for o in options:
        header += [o, f"{o}: why"]
    out = []
    for i, (crit, cells) in enumerate(rows, 1):
        line = [i, crit]
        for sc, why in cells:
            line += [sc, why]
        out.append(line)
    tot = ["", "TOTAL"]
    for k in range(len(options)):
        tot += [sum(c[k][0] for _, c in rows), ""]
    out.append(tot)
    write_csv(path, header, out)
    return [sum(c[k][0] for _, c in rows) for k in range(len(options))]


ct = matrix_csv(os.path.join(DOCS, "decision_matrix_concepts.csv"), CONCEPTS, CONCEPT_ROWS)
pt = matrix_csv(os.path.join(DOCS, "decision_matrix_power.csv"), POWERS, POWER_ROWS)

bom_rows = []
for pn, name, key, mat, q, what, why, alt in DESIGNED:
    bom_rows.append(["designed", pn, name, mat, q, "3D print" if mat == "PETG" else "Cut", "", f"{mass.get(key, 0):.1f}", what, why, alt])
for k, (item, spec, q, src, price, use, why, alt) in enumerate(PURCHASED, 1):
    bom_rows.append(["purchased", f"CA-P{k:02d}", item, spec, q, src, price, "", use, why, alt])
BOM_HEADER = ["type", "part_no", "item", "spec / material", "qty", "source", "unit_price_usd_est", "mass_g",
              "what it does / used for", "why we need it", "alternative considered → why not"]
write_csv(os.path.join(DOCS, "bom.csv"), BOM_HEADER, bom_rows)

printed = sum(mass.get(k, 0) for _, _, k, m, _, _, _, _ in DESIGNED if m == "PETG" and k != "tolerance_coupon")
spend = sum(q * p for (_, _, q, _, p, _, _, _) in PURCHASED)

L = ["# Bill of Materials: Concept A", "",
     "Generated by `tools/make_tables.py`. Also in `docs/bom.csv` and, with the decision matrices, in "
     "`docs/decision_matrix_and_bom.xlsx`. Printed masses come from the CAD (`cad/out/mass_table.csv`, "
     "60 % effective fill). Prices are typical online prices (EST). There are no optional parts: everything "
     "listed is on the robot.", "",
     "Each row says **why we need it** and **what else we considered**, so the list answers \"do we "
     "really need this, or would something else do?\"", "",
     "## Designed parts (3D printed / cut)", "",
     "| Part no. | Part | Material | Qty | Mass (g) | What it does | Why we need it | Alternative → why not |",
     "|---|---|---|---:|---:|---|---|---|"]
for pn, name, key, mat, q, what, why, alt in DESIGNED:
    L.append(f"| {pn} | {name} | {mat} | {q} | {mass.get(key, 0):.1f} | {what} | {why} | {alt} |")
L += ["", f"Printed robot parts: **≈ {printed:.0f} g PETG** (+ ~15 % for supports/purge). "
      "STL files: `cad/out/parts/`. Part numbers match the Part C drawings.", "",
      "## Purchased parts", "",
      "| Part no. | Item | Spec | Qty | Source | Unit $ (EST) | Used for | Why we need it | Alternative → why not |",
      "|---|---|---|---:|---|---:|---|---|---|"]
for k, (item, spec, q, src, price, use, why, alt) in enumerate(PURCHASED, 1):
    L.append(f"| CA-P{k:02d} | {item} | {spec} | {q} | {src} | {price if price else '—'} | {use} | {why} | {alt} |")
L += ["", f"**Spend beyond what we already have: ≈ ${spend:.0f}.**", ""]
open(os.path.join(DOCS, "05_bom.md"), "w").write("\n".join(L))

# ------------------------------------------------------------------ Excel
ARIAL = "Arial"
HDR = PatternFill("solid", fgColor="1F3A57")
SUB = PatternFill("solid", fgColor="E9EDF2")
YES = PatternFill("solid", fgColor="D9F2E1")
NO = PatternFill("solid", fgColor="FBE0DE")
WIN = PatternFill("solid", fgColor="FFF2B3")
thin = Side(style="thin", color="C9CED6")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
CEN = Alignment(horizontal="center", vertical="top")


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=ARIAL, bold=True, color="FFFFFF", size=10)
        cell.fill = HDR
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = BOX


def matrix_sheet(wb, title, heading, note, options, rows, tiebreak_row=None, winner=None):
    ws = wb.create_sheet(title)
    ws["A1"] = heading
    ws["A1"].font = Font(name=ARIAL, bold=True, size=14)
    ws["A2"] = note
    ws["A2"].font = Font(name=ARIAL, italic=True, size=10, color="4A5563")
    hr = 4
    ws.cell(row=hr, column=1, value="#")
    ws.cell(row=hr, column=2, value="Criterion (1 = yes / good, 0 = no / bad)")
    for k, o in enumerate(options):
        ws.cell(row=hr, column=3 + 2 * k, value=o)
        ws.cell(row=hr, column=4 + 2 * k, value="Why (the number behind the score)")
    style_header(ws, hr, 2 + 2 * len(options))
    r0 = hr + 1
    for i, (crit, cells) in enumerate(rows):
        r = r0 + i
        ws.cell(row=r, column=1, value=i + 1).alignment = CEN
        ws.cell(row=r, column=2, value=crit).alignment = WRAP
        for k, (sc, why) in enumerate(cells):
            c = ws.cell(row=r, column=3 + 2 * k, value=sc)
            c.font = Font(name=ARIAL, color="0000FF", bold=True)
            c.alignment = CEN
            c.fill = YES if sc else NO
            ws.cell(row=r, column=4 + 2 * k, value=why).alignment = WRAP
        for col in range(1, 3 + 2 * len(options)):
            ws.cell(row=r, column=col).border = BOX
            if ws.cell(row=r, column=col).font.color is None or col % 2 == 0 or col <= 2:
                ws.cell(row=r, column=col).font = Font(name=ARIAL, size=10)
    r1 = r0 + len(rows) - 1
    rt, rp, rk = r1 + 1, r1 + 2, r1 + 3
    ws.cell(row=rt, column=2, value="TOTAL (number of 1s)")
    ws.cell(row=rp, column=2, value="Share of criteria met")
    ws.cell(row=rk, column=2, value="Rank" + (" (ties broken by criterion %d)" % tiebreak_row if tiebreak_row else ""))
    cols = [get_column_letter(3 + 2 * k) for k in range(len(options))]
    for k, cl in enumerate(cols):
        ws[f"{cl}{rt}"] = f"=SUM({cl}{r0}:{cl}{r1})"
        ws[f"{cl}{rp}"] = f"={cl}{rt}/COUNT({cl}{r0}:{cl}{r1})"
        ws[f"{cl}{rp}"].number_format = "0%"
        key = (lambda c: f"({c}{rt}+0.1*{c}{r0 + tiebreak_row - 1})") if tiebreak_row else (lambda c: f"{c}{rt}")
        ws[f"{cl}{rk}"] = "=1" + "".join(f"+IF({key(o)}>{key(cl)},1,0)" for o in cols if o != cl)
    for r in (rt, rp, rk):
        for col in range(1, 3 + 2 * len(options)):
            cell = ws.cell(row=r, column=col)
            cell.font = Font(name=ARIAL, bold=True, size=10)
            cell.fill = SUB
            cell.border = BOX
            if col >= 3:
                cell.alignment = CEN
    if winner is not None:
        for r in range(hr, rk + 1):
            c = ws.cell(row=r, column=3 + 2 * winner)
            if r >= rt:
                c.fill = WIN
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 38
    for k in range(len(options)):
        ws.column_dimensions[get_column_letter(3 + 2 * k)].width = 14
        ws.column_dimensions[get_column_letter(4 + 2 * k)].width = 34
    ws.row_dimensions[hr].height = 42
    ws.freeze_panes = ws.cell(row=hr + 1, column=3)
    return ws, rt


wb = Workbook()
wb.remove(wb.active)
matrix_sheet(wb, "Concepts", "Concept decision matrix (binary)",
             "1 = yes / good, 0 = no / bad. Totals and ranks are formulas: change a blue score and they update. "
             "B and D tie on points; the tie goes to the concept that meets criterion 1 (the spec's 90° turn), "
             "which matches the team's weighted matrix (A 3.85, B 3.30, D 3.00, C 2.75).",
             CONCEPTS, CONCEPT_ROWS, tiebreak_row=1, winner=0)
matrix_sheet(wb, "Power source", "Power source decision matrix (binary)",
             "Stall currents: MG996R 2.5 A, MG90S 0.7 A, SG90 0.65 A. Normal run peak 0.65 A. Rows 1 and 5-7 are "
             "ngspice results (EE/ee_calcs.py): the 12 V + buck design keeps the Uno at 5.00 V and the servos at >= 5.5 V "
             "in a stall; the 5 V direct design is simpler but dips below both limits.",
             POWERS, POWER_ROWS, winner=3)

ws = wb.create_sheet("BOM")
ws["A1"] = "Bill of materials: Concept A"
ws["A1"].font = Font(name=ARIAL, bold=True, size=14)
ws["A2"] = "Prices are typical online prices (EST). Printed masses from the CAD (cad/out/mass_table.csv)."
ws["A2"].font = Font(name=ARIAL, italic=True, size=10, color="4A5563")
hdr = ["Type", "Part no.", "Item", "Spec / material", "Qty", "Source", "Unit $ (EST)", "Line $", "Mass (g)",
       "What it does / used for", "Why we need it", "Alternative considered → why not"]
for c, h in enumerate(hdr, 1):
    ws.cell(row=4, column=c, value=h)
style_header(ws, 4, len(hdr))
r = 5
for row in bom_rows:
    typ, pn, item, spec, q, src, price, m, use, why, alt = row
    vals = [typ, pn, item, spec, q, src, price if price != "" else None, None, float(m) if m else None, use, why, alt]
    for c, v in enumerate(vals, 1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = Font(name=ARIAL, size=10, color="0000FF" if c in (5, 7) else None)
        cell.alignment = WRAP
        cell.border = BOX
    ws.cell(row=r, column=8, value=f'=IF(G{r}="","",E{r}*G{r})')
    ws.cell(row=r, column=7).number_format = '$#,##0;($#,##0);-'
    ws.cell(row=r, column=8).number_format = '$#,##0;($#,##0);-'
    ws.cell(row=r, column=9).number_format = '0.0'
    r += 1
last = r - 1
ws.cell(row=r, column=3, value="Total spend beyond what we have")
ws.cell(row=r, column=8, value=f"=SUM(H5:H{last})").number_format = '$#,##0'
ws.cell(row=r + 1, column=3, value="Printed PETG (robot parts, excl. coupon)")
ws.cell(row=r + 1, column=9, value=f'=SUMIFS(I5:I{last},D5:D{last},"PETG",B5:B{last},"<>CA-900")').number_format = '0'
for rr in (r, r + 1):
    for c in range(1, len(hdr) + 1):
        cell = ws.cell(row=rr, column=c)
        cell.font = Font(name=ARIAL, bold=True, size=10)
        cell.fill = SUB
        cell.border = BOX
for col, w in zip("ABCDEFGHIJKL", (10, 9, 26, 24, 6, 14, 10, 9, 9, 30, 44, 48)):
    ws.column_dimensions[col].width = w
ws.freeze_panes = "D5"

xlsx = os.path.join(DOCS, "decision_matrix_and_bom.xlsx")
wb.save(xlsx)
print(f"concept totals {dict(zip('ABCD', ct))}; power totals {pt}; "
      f"BOM {len(DESIGNED)} designed + {len(PURCHASED)} purchased, PETG {printed:.0f} g, spend ${spend:.0f}")
print("wrote docs/05_bom.md, docs/bom.csv, docs/decision_matrix_concepts.csv, docs/decision_matrix_power.csv,", os.path.relpath(xlsx, ROOT))
