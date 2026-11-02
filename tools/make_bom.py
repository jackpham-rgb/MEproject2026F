"""Top-level bill of materials for Concept A -> docs/bom.csv and docs/05_bom.md.

    python3 tools/make_bom.py

Designed (printed) part masses come from cad/out/mass_table.csv (written by cad/check.py).
Prices are typical US online prices (EST), not quotes.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mass = {}
with open(os.path.join(ROOT, "cad/out/mass_table.csv")) as f:
    for r in csv.DictReader(f):
        mass[r["part"]] = float(r["mass_g"])
mass.setdefault("tolerance_coupon", 10.81 * 1.27 * 0.60)   # not in the robot mass table: 10.81 cm3 (cad/out/parts)

# part no, name, model part, material, qty, how it is made / held
DESIGNED = [
    ("CA-101", "Base", "base", "PETG", 1, "Bearing tower, MG996R pocket, ballast pockets, sweep sector cut away"),
    ("CA-102", "Electronics tray", "electronics_tray", "PETG", 1, "Uno, buck, breadboard, button/LED/DC-jack panel"),
    ("CA-201", "Turret plate", "turret_plate", "PETG", 1, "D plate + hub pressed into the 6807 bore, rod bosses"),
    ("CA-202", "Spine", "spine", "PETG", 1, "Column back + lift-servo bracket"),
    ("CA-203", "Top cap", "top_cap", "PETG", 1, "Captures the rod tops"),
    ("CA-301", "Carriage + arm", "carriage_arm", "PETG", 1, "4 LM6UU pockets, arm, wrist-servo bracket"),
    ("CA-302", "Lift link", "lift_link", "PETG", 1, "Crank pin to carriage"),
    ("CA-401", "Gripper frame", "gripper_frame", "PETG", 1, "Flange + 2 plates + posts"),
    ("CA-402", "Finger, right", "finger_R", "PETG", 1, "Gear m1 16T + arm + curved pad"),
    ("CA-403", "Finger, left", "finger_L", "PETG", 1, "Mirror; gear has the servo-spline socket"),
    ("CA-404", "Can bumper", "can_bumper", "TPU", 1, "Glued to the gripper frame"),
    ("CA-900", "Tolerance coupon", "tolerance_coupon", "PETG", 1, "Print first; checks all hole fits"),
]

# item, spec, qty, unit, source, unit price $ (EST), used for
PURCHASED = [
    ("Arduino Uno R3", "ATmega328P board + USB cable", 1, "ea", "Kit (have)", 0, "Controller"),
    ("Servo MG996R", "Metal gear, 180°, 9.4 kg·cm", 1, "ea", "Amazon", 9, "Turntable (D9)"),
    ("Servo MG90S", "Metal gear micro, 1.8 kg·cm", 1, "ea", "Amazon", 4, "Lift (D10)"),
    ("Servo, micro full-180° (or 270°)", "MG90S-size, check it reaches 180°", 1, "ea", "Amazon", 6, "Wrist (D6)"),
    ("Servo SG90", "Micro, 1.6 kg·cm", 1, "ea", "Kit (have)", 0, "Gripper (D5)"),
    ("Ball bearing 6807-2RS", "35 × 47 × 7 mm", 1, "ea", "Amazon / VXB", 5, "Turntable"),
    ("Linear bearing LM6UU", "6 mm ID × 12 mm OD × 19 mm", 4, "ea", "Amazon", 1, "Lift carriage"),
    ("Steel rod 6 mm (h6), 300 mm long", "Cut to 2 × 112 mm", 1, "ea", "Amazon", 5, "Lift guide rods"),
    ("Buck converter XL4015", "5 A, set to 6.0 V", 1, "ea", "Amazon", 5, "Servo power"),
    ("Wall adapter", "7.5–12 V DC, ≥ 3 A, 5.5 × 2.1 mm plug", 1, "ea", "Amazon / lab", 9, "Main power"),
    ("DC panel jack", "5.5 × 2.1 mm, panel mount", 1, "ea", "Amazon", 1, "Power input"),
    ("Electrolytic capacitor", "1000 µF, ≥ 10 V", 1, "ea", "Kit (have)", 0, "Servo rail"),
    ("Push button", "12 mm momentary", 1, "ea", "Kit (have)", 0, "START (D4)"),
    ("LED + 220 Ω resistor", "5 mm", 1, "set", "Kit (have)", 0, "Status (D13)"),
    ("Mini breadboard", "170 tie points", 1, "ea", "Kit (have)", 0, "Servo power rails"),
    ("Jumper wires", "M-M / M-F", 20, "ea", "Kit (have)", 0, "Signals, ground"),
    ("Servo extension lead", "300 mm", 3, "ea", "Amazon", 1, "Lift, wrist, gripper"),
    ("Machine screw #6-32 × ½″", "Pan Phillips, HF kit #67675", 8, "ea", "Have", 0, "Tray 2, spine 2, top cap 2, link 1, gear axle 1"),
    ("Machine screw #8-32 × ½″", "Pan Phillips, HF kit #67675", 4, "ea", "Have", 0, "MG996R flange"),
    ("Servo-bag screws", "Come with the servos", 14, "ea", "With servos", 0, "Servo tabs, horns, crank"),
    ("M2 self-tapping screws", "M2 × 6/8 mm pack", 1, "pack", "Amazon", 5, "Spare for servo tabs"),
    ("Pad liner", "TPU filament or 1–2 mm silicone sheet", 1, "small", "Amazon", 2, "Finger pads"),
    ("Steel washers (ballast) + rubber feet", "~100 g", 1, "set", "Hardware store", 3, "Base weight, grip on table"),
    ("PETG filament", "1.75 mm", 0.35, "kg", "Have", 0, "Printed parts (~330 g incl. supports)"),
    ("IR sensor TCRT5000 / KY-032 (optional)", "Digital out", 1, "ea", "Kit / Amazon", 2, "Can present (D11)"),
    ("FSR 402 + 10 kΩ (optional)", "Force sensor", 1, "ea", "Amazon", 7, "Grip force (A0)"),
]

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs/bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["type", "part_no", "item", "spec / material", "qty", "unit", "source", "unit_price_usd_est", "mass_g", "used_for"])
    for pn, name, key, mat, q, note in DESIGNED:
        w.writerow(["designed", pn, name, mat, q, "ea", "3D print", "", f"{mass.get(key, 0):.1f}", note])
    for k, (item, spec, q, unit, src, price, use) in enumerate(PURCHASED, 1):
        w.writerow(["purchased", f"CA-P{k:02d}", item, spec, q, unit, src, price, "", use])

printed = sum(mass.get(k, 0) for _, _, k, m, _, _ in DESIGNED if m == "PETG" and k != "tolerance_coupon")
spend = sum((q if u in ("ea", "set", "pack", "small") else 1) * p for (i, s, q, u, src, p, use) in PURCHASED if "optional" not in i)
spend_opt = sum((q if u in ("ea", "set", "pack", "small") else 1) * p for (i, s, q, u, src, p, use) in PURCHASED if "optional" in i)

L = ["# Bill of Materials: Concept A", "",
     "Generated by `tools/make_bom.py` (also `docs/bom.csv`). Printed masses come from the CAD "
     "(`cad/out/mass_table.csv`, 60 % effective fill). Prices are typical online prices (EST).", "",
     "## Designed parts (3D printed)", "",
     "| Part no. | Part | Material | Qty | Mass (g) | Notes |", "|---|---|---|---:|---:|---|"]
for pn, name, key, mat, q, note in DESIGNED:
    L.append(f"| {pn} | {name} | {mat} | {q} | {mass.get(key, 0):.1f} | {note} |")
L += ["", f"Printed robot parts: **≈ {printed:.0f} g PETG** (+ ~15 % for supports/purge). "
      "STL files: `cad/out/parts/`. Part numbers match the Part C drawings.", "",
      "## Purchased parts", "",
      "| Part no. | Item | Spec | Qty | Source | Unit $ (EST) | Used for |", "|---|---|---|---:|---|---:|---|"]
for k, (item, spec, q, unit, src, price, use) in enumerate(PURCHASED, 1):
    qs = f"{q} {unit}" if unit not in ("ea",) else f"{q}"
    L.append(f"| CA-P{k:02d} | {item} | {spec} | {qs} | {src} | {price if price else '—'} | {use} |")
L += ["", f"**Spend beyond what we already have: ≈ ${spend:.0f}** (≈ ${spend + spend_opt:.0f} with the optional sensors).", ""]
open(os.path.join(ROOT, "docs/05_bom.md"), "w").write("\n".join(L))
print(f"docs/bom.csv, docs/05_bom.md: {len(DESIGNED)} designed, {len(PURCHASED)} purchased; PETG {printed:.0f} g; spend ${spend:.0f}")
