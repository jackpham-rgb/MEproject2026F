// Engineering report (Part C) -> docs/Engineering_Report_ConceptA.docx
//
//   node tools/make_report.js
//
// Tables come straight from the repo (docs/06_rvtm.md, docs/bom.csv, EE/out/ee_report.txt numbers
// quoted below are the values those scripts printed), so re-run this after re-running the checks.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, ImageRun, PageBreak, LevelFormat, Footer, PageNumber, TableOfContents,
  BorderStyle,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const P = (...p) => path.join(ROOT, ...p);
const FONT = "Arial";
const CONTENT_W = 9360; // 6.5 in in DXA

// ------------------------------------------------------------------ helpers
const para = (text, opts = {}) => new Paragraph({
  spacing: { after: 120, line: 276 }, ...opts,
  children: (Array.isArray(text) ? text : [text]).map(t => typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 21 }) : t),
});
const b = (t) => new TextRun({ text: t, bold: true, font: FONT, size: 21 });
const r = (t) => new TextRun({ text: t, font: FONT, size: 21 });
const mono = (t) => new TextRun({ text: t, font: "Consolas", size: 19 });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 }, children: [new TextRun({ text: t, font: FONT })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (parts) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60 },
  children: (Array.isArray(parts) ? parts : [parts]).map(t => typeof t === "string" ? r(t) : t) });
const caption = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [new TextRun({ text: t, italics: true, font: FONT, size: 18, color: "555555" })] });

function pngSize(file) {
  const buf = fs.readFileSync(file);
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20), buf };
}
function image(rel, widthIn = 6.5, cap = null) {
  const { w, h, buf } = pngSize(P(rel));
  const wpx = widthIn * 96;
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: wpx * h / w } })] })];
  if (cap) out.push(caption(cap));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "B8BEC8" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(rows, widths, { header = true, size = 17 } = {}) {
  const total = widths.reduce((a, c) => a + c, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((row, i) => new TableRow({
      tableHeader: header && i === 0,
      children: row.map((cell, j) => new TableCell({
        borders, width: { size: widths[j], type: WidthType.DXA },
        margins: { top: 50, bottom: 50, left: 90, right: 90 },
        shading: header && i === 0 ? { fill: "1F3A57", type: ShadingType.CLEAR, color: "auto" } : (i % 2 === 0 ? { fill: "F3F5F8", type: ShadingType.CLEAR, color: "auto" } : undefined),
        children: [new Paragraph({ children: [new TextRun({ text: String(cell), font: FONT, size, bold: header && i === 0, color: header && i === 0 ? "FFFFFF" : "1A1E24" })] })],
      })),
    })),
  });
}
const spacer = () => new Paragraph({ spacing: { after: 120 }, children: [] });

// markdown table reader (for the RVTM)
function mdTables(file) {
  const lines = fs.readFileSync(P(file), "utf8").split("\n");
  const tabs = []; let cur = null;
  for (const ln of lines) {
    if (ln.startsWith("|")) {
      const cells = ln.split("|").slice(1, -1).map(c => c.trim().replace(/`/g, "").replace(/\*\*/g, ""));
      if (cells.every(c => /^:?-+:?$/.test(c))) continue;
      if (!cur) { cur = []; tabs.push(cur); }
      cur.push(cells);
    } else cur = null;
  }
  return tabs;
}
function csvRows(file) {
  const txt = fs.readFileSync(P(file), "utf8").trim().split("\n");
  const parse = (l) => { const out = []; let cur = "", q = false;
    for (const ch of l) { if (ch === '"') q = !q; else if (ch === "," && !q) { out.push(cur); cur = ""; } else cur += ch; }
    out.push(cur); return out; };
  const head = parse(txt[0]);
  return txt.slice(1).map(l => Object.fromEntries(parse(l).map((v, i) => [head[i], v])));
}

// ------------------------------------------------------------------ content
const C = [];
// title page
C.push(new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "ME 2331/L  Project 2: Design, Build, Test", font: FONT, size: 28, color: "4A5563" })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [new TextRun({ text: "Engineering Report: Can-Flipping Robot", font: FONT, size: 44, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [new TextRun({ text: "Concept A: claw + wrist flip + turntable", font: FONT, size: 28 })] }));
image("docs/report_img/cad_flip.png", 5.0).forEach(x => C.push(x));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 },
  children: [new TextRun({ text: "Team: [names]", font: FONT, size: 24 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "Status: detail design complete and verified by analysis and simulation. Build and test results to be added after the demo.", font: FONT, size: 20, italics: true, color: "555555" })] }));
C.push(new Paragraph({ children: [new PageBreak()] }));
C.push(new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }));
C.push(new Paragraph({ children: [new PageBreak()] }));

// 1 summary
C.push(h1("1. Summary"));
C.push(para("An Arduino Uno robot picks up an empty standard 12 oz Coke can standing upright 5 in from the robot, turns it upside down, and sets it down free-standing 90° around the robot at the same 5 in radius, with one button press and no other human input."));
C.push(para([r("The selected design (Concept A) is a small crane on a turntable. Four hobby servos move one at a time: "), b("grip → lift 0.6 in → wrist flips 180° → turntable turns 90° → lower → release"), r(", in 6.4 s.")]));
C.push(para("Before ordering hardware, the design was verified as far as possible on the laptop:"));
[
  "Detail CAD of every printed and purchased part, with PETG print tolerances and screws from the team's Harbor Freight #67675 kit.",
  "A collision check that runs the real firmware sequence through the CAD in 289 poses: no part touches another or the table, the can lands inverted at (127.0, 0.0) mm with 0.0° tilt, and the robot stays 39 mm inside its tip-over footprint.",
  "Mechanical analysis: lift clearance, grip force, servo torques (5× and 30× margins), lift jam check.",
  "Electrical analysis: servo signals replayed from the firmware, a current budget, and an ngspice/LTspice circuit run comparing two power designs. The Uno holds 5.00 V even with a servo stalled.",
  "The firmware compiles for the Uno (19.6 % flash) and runs the full sequence on an emulated ATmega328P.",
].forEach(t => C.push(bullet(t)));

// 2 requirements
C.push(h1("2. Requirements"));
C.push(para("From the assignment: the robot must complete the test objective (TO1–TO3), use an Arduino Uno or similar, be operated by the microcontroller, fit a classroom tabletop, and need no direct human intervention. The test objective: start with the can upright and free-standing at the initial location (TO1); turn it upside down and move it about 90° around the robot at about 5 in (TO2); end with it free-standing and inverted at the target (TO3). Every requirement is traced to a design feature and its evidence in the RVTM (section 9)."));
C.push(table([["Can (as modelled)", "Value"], ["Type", "Standard 12 oz Coke can, empty"], ["Diameter × height", "66.2 × 122.2 mm (2.61 × 4.81 in)"], ["Mass", "15 g"], ["Start / target", "(0, 127) mm and (127, 0) mm from the turntable axis"]], [3200, 6160]));
C.push(spacer());

// 3 concept selection
C.push(h1("3. Concept selection"));
C.push(para("Four concepts were developed and animated (docs/01_concepts_and_decision_matrix.md):"));
[["Concept A", ": claw + wrist flip + turntable (selected)."], ["Concept B", ": cradle flip in place, then drag the can 90° on its rim."], ["Concept C", ": multi-joint pincer arm with inverse kinematics."], ["Concept D", ": one 180° roll about a 45° axis (mirror flip). The robot never visibly turns."]]
  .forEach(([a, t]) => C.push(bullet([b(a), r(t)])));
C.push(para("Two matrices were used: the team's weighted 1–5 matrix and a binary yes/no matrix in which every score carries the number behind it (docs/decision_matrix_and_bom.xlsx)."));
C.push(table([["Matrix", "A", "B", "C", "D"], ["Weighted team matrix (1–5)", "3.85", "3.30", "2.75", "3.00"], ["Binary matrix (of 10 criteria)", "8", "6", "5", "6"], ["Rank", "1", "2", "4", "3"]], [3760, 1400, 1400, 1400, 1400]));
C.push(spacer());
C.push(para("A wins because the 90° turn is literal and obvious, it uses only hobby servos with no encoder or closed-loop tuning, and every move can be tested on its own. Its cost is four actuators in series and the need for a lift: gripped at mid-height, the can's corner is 2.74 in from the grip point, 0.33 in more than the 2.41 in to the table, so it would dig into the table mid-flip without lifting 0.6 in first."));

// 4 design
C.push(h1("4. Design description"));
image("docs/report_img/cad_home.png", 4.6, "Figure 1. Detail CAD at HOME: arm at the start can (red ring); target is the green ring.").forEach(x => C.push(x));
C.push(table([
  ["Subsystem", "Design", "Why"],
  ["Base (CA-101)", "Printed box with a bearing tower; the 175° sector the arm and can sweep is cut away", "Holds the turntable; footprint keeps the CG ≥ 39 mm inside in every pose"],
  ["Turntable", "MG996R + 6807-2RS bearing (35 × 47 × 7 mm) carrying a D-shaped turret plate (CA-201)", "The bearing takes the weight and tipping load, so the servo only turns it"],
  ["Lift", "Carriage + arm (CA-301) on 4 LM6UU bearings on two 6 mm rods; MG90S crank + link (CA-302)", "15.3 mm (0.6 in) stroke; jam ratio 0.018 (a printed slide would be 0.55)"],
  ["Wrist", "MG90S rolls the gripper 180° about the radial line through the can's centre", "Flipping about the can's own centre means lowering 0.6 in sets it exactly on the table"],
  ["Gripper", "Gripper frame (CA-401) + two geared fingers (CA-402/403) with curved pads; SG90", "One servo closes both arms equally and centres the can; release opens only 25°"],
  ["Electronics", "Uno, 12 V adapter, XL4015 buck at 5.8 V, START button, status LED on a printed tray (CA-102)", "Section 6"],
], [1700, 4260, 3400]));
C.push(spacer());
image("docs/report_img/cad_target.png", 4.6, "Figure 2. At the target after release: can inverted and free-standing, 90° around the robot.").forEach(x => C.push(x));
C.push(h2("4.1 Detail design changes found by the motion check"));
C.push(para("Running the real part shapes through the firmware sequence found problems the block-level PDR model missed. Each fix below closed a collision or margin the check reported:"));
[
  "The original lazy-susan stack was as tall as the grip axis, so the wrist servo hit it: replaced by a 6807 bearing in a 28 mm tower and a D-shaped turret plate.",
  "The square base corner was in the can's path: the base is cut away in the swept sector.",
  "At the target the gripper is upside down, so opening fully swung an arm into the base: release opens only 25°, which still clears the can by 3.6 mm.",
  "Un-flipping with the arms open would sweep them through the table: homing closes the arms first, and runs only after the can is lifted off.",
].forEach(t => C.push(bullet(t)));
C.push(h2("4.2 Print tolerances and fasteners"));
C.push(table([["Fit", "Printed size (mm)", "Used for"], ["#6-32 clearance / pilot", "3.9 / 2.9", "Most joints; screws thread into the plastic (no nuts in the kit)"], ["#8-32 pilot", "3.5", "MG996R flange"], ["Servo-bag screw pilot", "1.7", "Servo tabs and horns"], ["6 mm rod press", "6.00", "Guide rods"], ["LM6UU press", "12.15", "Linear bearings"], ["6807 housing / hub", "47.10 / 34.95", "Turntable bearing"], ["Moving clearance", "≥ 0.5", "Fingers between the gripper plates"]], [3000, 2000, 4360]));
C.push(spacer());
C.push(para("A tolerance coupon (CA-900) with all six hole sizes is printed first; if a fit is off, the TOL table in backend/cad/model.py is changed and every part regenerates. Screws: 8 × #6-32 × ½″ and 4 × #8-32 × ½″ from the HF #67675 kit."));

// 5 mechanical analysis
C.push(h1("5. Mechanical analysis"));
C.push(table([
  ["Check", "Calculation / method", "Result"],
  ["Lift clearance", "Can corner from the grip point √(1.30² + 2.41²) = 2.74 in vs 2.41 in to the table", "Without lift −0.33 in (hits); 0.6 in lift → +0.27 in"],
  ["Grip force", "Minimum squeeze per arm = SF·m·a / (2μ) = 3 × 0.015 × 10.52 / (2 × 0.6)", "0.39 N; set 0.5–1 N (dent ~8 N; SG90 max 1.8 N at the 44 mm lever)"],
  ["Lift servo", "149 g moving incl. can, CG 39 mm in front of the rods", "0.33 kg·cm vs MG90S 1.8 → 5×"],
  ["Wrist servo", "58 g rotating, CG 10.3 mm off the roll axis", "0.06 kg·cm vs 1.8 → 30×"],
  ["Turntable", "J = 7.7 kg·cm², weight on the bearing", "0.032 kg·cm vs MG996R 9.4"],
  ["Lift jam", "Drawer effect 2μe/L with bushings 43 mm apart", "0.018 with LM6UU (printed slide 0.55)"],
  ["Collisions", "Solid booleans, 289 poses, run + homing", "None; tightest moving gaps 0.5 mm (designed)"],
  ["Tip-over", "CG vs convex hull of base + tray", "≥ 39 mm inside in every pose"],
  ["Landing", "Can pose after LOWER", "(127.0, 0.0) mm, inverted, 0.0° tilt, z = 0.00"],
  ["Error budget", "Turntable error → landing offset 5 in × sin(e)", "1° → 0.09 in, 2° → 0.17 in"],
], [1700, 4360, 3300]));
C.push(spacer());
C.push(para("Mass: 571 g robot (301 g printed PETG, 270 g purchased) + 15 g can."));

// 6 electrical
C.push(h1("6. Electrical design"));
image("docs/wiring/wiring_diagram.png", 6.5, "Figure 3. Wiring diagram (breadboard style, as drawn in Fritzing).").forEach(x => C.push(x));
C.push(table([["Uno pin", "Connects to", "Notes"], ["D9", "Turntable servo MG996R signal", "Power on the buck terminals"], ["D10", "Lift servo MG90S", "300 mm extension"], ["D6", "Wrist servo MG90S", "Pulse range widened to 500–2500 µs to reach 180°"], ["D5", "Gripper servo SG90", "300 mm extension"], ["D4", "START button to GND", "INPUT_PULLUP, debounced"], ["D13", "Status LED + 220 Ω", "13.6 mA"], ["VIN / GND", "12 V adapter", "Uno makes its own 5 V"]], [1500, 3600, 4260]));
C.push(spacer());
C.push(h2("6.1 Power: why a buck converter"));
C.push(para("Two power designs were simulated in ngspice with the real servo currents: (A) one 5 V 4 A adapter feeding the servos and the Uno's 5V pin, and (B, selected) a 12 V 2 A adapter feeding the Uno's VIN plus an XL4015 buck at 5.8 V for the servos. Both pass the normal run; only B passes the fault cases."));
C.push(table([["Check (limit)", "A normal", "A stall", "B normal", "B stall"], ["Uno 5 V (≥ 4.5 V)", "4.86", "4.43 ✘", "5.00", "5.00"], ["Servo supply (≥ 4.8 V)", "4.82", "4.25 ✘", "5.72", "5.50"], ["Adapter current", "0.66 / 4 A", "3.16 / 4 A", "0.38 / 2 A", "1.79 / 2 A"], ["USB while powered", "not allowed", "", "allowed", ""]], [2760, 1650, 1650, 1650, 1650]));
C.push(spacer());
C.push(para("The buck also lets USB stay plugged in for calibration (the Uno switches USB power off above 6.6 V on VIN). A 9 V battery was rejected: it supplies about 0.5–1 A, and one servo stall needs 2.5 A. Power decision matrix: 12 V + buck 7/9, 5 V direct 6/9, LiPo 5/9, 9 V battery and AA pack 4/9."));
image("EE/out/power_compare.png", 6.5, "Figure 4. ngspice: both power designs in the normal run, a stall, and power-up away from home.").forEach(x => C.push(x));
C.push(h2("6.2 Current budget"));
C.push(table([["Step", "Peak current"], ["GRIP", "0.26 A"], ["LIFT", "0.56 A"], ["FLIP", "0.60 A"], ["TURN", "0.65 A (largest)"], ["LOWER", "0.56 A"], ["RELEASE", "0.24 A"], ["Homing steps", "≤ 0.34 A"]], [4680, 4680]));
C.push(spacer());
C.push(para("The largest steady load is the gripper holding the can: 0.8 N per arm × 44 mm × 2 arms = 0.72 kg·cm, 45 % of the SG90's stall torque, about 0.29 A for 5 s. Two rules came out of the analysis: the MG996R's power goes straight to the buck terminals (its 2.5 A stall would exceed a breadboard contact's ~1 A), and the firmware attaches the servos 0.3 s apart so a power-up away from home never pulls all four stall currents at once (4.7 A)."));

// 7 code
C.push(h1("7. Code discussion"));
C.push(para([r("The firmware is one Arduino sketch ("), mono("firmware/concept_a/concept_a.ino"), r(") using only the built-in Servo library, so it runs unchanged in the Arduino IDE, Tinkercad and Wokwi.")]));
[
  [b("Sequence as data. "), r("The run is a table of steps; each row holds the target angle of all four servos and a move time. The loop blends from the current pose to the next row, so changing the sequence never touches the logic.")],
  [b("Eased moves. "), r("Every move follows a minimum-jerk curve s³(10 − 15s + 6s²): speed and acceleration are zero at both ends, so the light can isn't shaken loose. The loop updates every 10 ms; the Servo library sends a new pulse every 20 ms.")],
  [b("State machine. "), r("IDLE → (button) → RUNNING → DONE → (can removed, button) → RETURNING → IDLE. Homing only runs after the can is lifted off, because the open arms straddle it.")],
  [b("Calibration. "), r("All angles are named constants at the top (TURN_START, LIFT_UP, GRIP_CLOSED, …); calibration never touches the logic. PRINT_ANGLES streams the angles to the Serial Plotter.")],
  [b("Power-up. "), r("The home pose is written before attach(), and the servos are attached 0.3 s apart.")],
  [b("Status LED. "), r("Off = idle, blinking = moving, on = done.")],
].forEach(p => C.push(bullet(p)));
C.push(table([["Step", "D9 turntable", "D10 lift", "D6 wrist", "D5 gripper", "Time"], ["HOME", "135° / 1936 µs", "30° / 853", "0° / 500", "20° / 750", "—"], ["GRIP", "135°", "30°", "0°", "95° / 1523", "0.8 s"], ["LIFT", "135°", "75° / 1317", "0°", "95°", "1.0 s"], ["FLIP", "135°", "75°", "180° / 2500", "95°", "1.5 s"], ["TURN", "45° / 1008", "75°", "180°", "95°", "1.5 s"], ["LOWER", "45°", "30° / 853", "180°", "95°", "1.0 s"], ["RELEASE", "45°", "30°", "180°", "70° / 1265", "0.6 s"]], [1300, 1760, 1560, 1560, 1700, 1480]));
C.push(caption("Table: servo angle / pulse width at the end of each step (pulse = map(angle, 0, 180, min, max) µs)."));
image("EE/out/signals_sequence.png", 6.3, "Figure 5. Button, servo pulse widths, LED and supply current in firmware order, replayed from the code.").forEach(x => C.push(x));
C.push(para("Verification: the sketch compiles to 6.4 KB (19.6 % flash, 24.5 % RAM) and runs the full GRIP → RELEASE → DONE sequence on an emulated ATmega328P (tools/emulate_concept_a.sh); the Wokwi and Tinkercad circuits run the same sketch."));

// 8 BOM
C.push(h1("8. Bill of materials"));
const bom = csvRows("docs/bom.csv");
const des = bom.filter(x => x.type === "designed");
C.push(para("Designed parts (3D printed in PETG unless noted). Drawings for every part are in the appendix (docs/drawings/all_drawings.pdf)."));
C.push(table([["Part no.", "Part", "Material", "Qty", "Mass (g)"], ...des.map(x => [x.part_no, x.item, x["spec / material"], x.qty, x.mass_g])], [1300, 3460, 2000, 1000, 1600]));
C.push(spacer());
const pur = bom.filter(x => x.type === "purchased");
C.push(para("Purchased parts. Every item in docs/05_bom.md also states why it is needed and which alternative was rejected (for example, a physical START button instead of an IR remote: one wire, nothing to pair, no stray triggers)."));
C.push(table([["Part no.", "Item", "Qty", "Unit $ (EST)", "Used for"], ...pur.map(x => [x.part_no, x.item, x.qty, x.unit_price_usd_est === "0" ? "have" : x.unit_price_usd_est, x["what it does / used for"]])], [1100, 3300, 700, 1200, 3060], { size: 16 }));
C.push(spacer());
const spend = pur.reduce((a, x) => a + Number(x.qty) * Number(x.unit_price_usd_est || 0), 0);
C.push(para([b(`Spend beyond what the team already has: ≈ $${spend.toFixed(0)}`), r(" (typical online prices).")]));

// 9 RVTM
C.push(h1("9. Requirements verification traceability matrix"));
C.push(para("Method: A = analysis, I = inspection, D = demonstration, T = test. Status as of the detail design, before hardware."));
const rv = mdTables("docs/06_rvtm.md");
rv.forEach((t, i) => {
  C.push(h2(["9.1 Assignment requirements", "9.2 Test objective", "9.3 Derived design requirements"][i] || "Table"));
  C.push(table(t, [700, 2000, 2200, 800, 2300, 1360], { size: 15 }));
  C.push(spacer());
});

// 10 test plan
C.push(h1("10. Test plan and results"));
C.push(para("Results are filled in after the build. Pass criteria come from the derived requirements."));
C.push(table([
  ["Test", "Procedure", "Pass criterion", "Result"],
  ["Tolerance coupon (DR11)", "Print CA-900; fit screws, rod, LM6UU", "Screws thread, rod and LM6UU press in by hand", ""],
  ["Buck setting (DR6)", "Meter on OUT before servos", "5.8 ± 0.1 V", ""],
  ["Wrist range (DR2)", "Command 0° and 180°", "180° ± 3°", ""],
  ["Turntable (DR3)", "Calibrate TURN_TARGET", "90° ± 2°; can within 0.17 in", ""],
  ["Grip (DR4, DR13)", "Close on a scrap can; shake", "Holds; no dent; SG90 not hot", ""],
  ["Rail under load (DR6)", "Meter on the rail during a run", "≥ 5.5 V servos, Uno 5 V", ""],
  ["Full run (R1, TO1–TO3)", "10 runs from the start mark", "Can inverted, free-standing at the target in ≥ 9 of 10", ""],
], [2000, 2700, 3160, 1500]));
C.push(spacer());

// 11 conclusion
C.push(h1("11. Conclusion"));
C.push(para("Concept A meets every requirement that can be checked before hardware: the motion runs collision-free through the full firmware sequence, the can lands inverted and level at the target, every servo has at least a 5× torque margin, and the power design keeps the Uno at 5.00 V even with a servo stalled. The remaining risks are the ones only hardware can settle: whether the wrist servo reaches a full 180°, the grip squeeze, and the printed fits. Each has a planned test and a mitigation (wider wrist pulse range, the GRIP_CLOSED constant, and the tolerance coupon)."));

// appendix
C.push(h1("Appendix A. Drawings"));
C.push(para("13 sheets, one per designed part plus the assembly, generated from the CAD (backend/cad/drawings.py): third-angle views, overall dimensions, a hole table with fits and positions, and a title block. Full set: docs/drawings/all_drawings.pdf."));
image("docs/drawings/CA-000_assembly.png", 6.5, "Sheet 1: assembly CA-000.").forEach(x => C.push(x));
C.push(h1("Appendix B. Files"));
C.push(table([["What", "Where"], ["Detail CAD, STEP and STL", "cad/ (model.py, out/)"], ["Collision / mass / load check", "backend/cad/check.py → cad/check/check_report.txt"], ["Drawings", "docs/drawings/"], ["Firmware", "firmware/concept_a/concept_a.ino"], ["Electronics calculations and LTspice", "EE/"], ["BOM and decision matrices", "docs/05_bom.md, docs/decision_matrix_and_bom.xlsx"], ["Wiring", "docs/04_wiring.md, docs/wiring/"]], [4000, 5360]));

// ------------------------------------------------------------------ document
const doc = new Document({
  creator: "ME 2331 Project 2 team", title: "Engineering Report: Can-Flipping Robot (Concept A)",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, font: FONT, color: "1F3A57" }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, font: FONT, color: "2B5D8A" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "ME 2331/L Project 2 · Concept A engineering report · page ", font: FONT, size: 16, color: "777777" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "777777" })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then(buf => {
  const out = P("docs", "Engineering_Report_ConceptA.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", path.relative(ROOT, out), Math.round(buf.length / 1024), "KB");
});
