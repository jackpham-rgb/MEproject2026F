// Assembly manual, step 2 of 2: line drawings for every step + the printable manual.
//   python3.13 backend/cad/export.py && python3.13 backend/tools/make_manual.py && node backend/tools/render_manual.js
// Reads backend/cad/build/viewer_mesh.json (parts in place) and manual_steps.json (steps).
// Writes docs/manual/step_NN.png, cover.png, parts.png and docs/12_assembly_manual.pdf (+ .html).
// PART E (circuit + electronics bench test) is pulled from docs/04_wiring.md (Wire list) and
// docs/13_electronics_bench_test.md, so edit those docs, not this file, and re-run.
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "docs/manual"); fs.mkdirSync(OUT, { recursive: true });
const mesh = JSON.parse(fs.readFileSync(path.join(ROOT, "backend/cad/build/viewer_mesh.json"), "utf8"));
const steps = JSON.parse(fs.readFileSync(path.join(ROOT, "backend/cad/build/manual_steps.json"), "utf8")).steps;
// realistic meshes per owner (backend/cad/visual.py): printed parts = the CAD, bought parts as they look, screws, glue
const ASM = JSON.parse(fs.readFileSync(path.join(ROOT, "viewer/data/assembly.json"), "utf8"));
const parts = {}; for (const m of ASM.meshes) (parts[m.owner] = parts[m.owner] || []).push(m);
const ASTEP = Object.fromEntries(ASM.steps.map(s => [s.n, s]));
const SCREW = Object.fromEntries(ASM.screws.map(s => [s.name, s]));
const LIB = path.join(ROOT, "viewer/lib");
// printed (blue in every drawing) vs bought (orange)
const PRINTED_PARTS = ["base", "electronics_tray", "turret_plate", "spine", "top_cap", "carriage_arm", "lift_link", "gripper_frame", "finger_R", "finger_L"];
const BOUGHT_NAME = { bearing_6807: "6807 ball bearing", turntable_servo_MG996R: "MG996R servo", turntable_horn: "servo horn (round)",
  LM6UU_L1: "LM6UU linear bearing", LM6UU_L2: "LM6UU linear bearing", LM6UU_R1: "LM6UU linear bearing", LM6UU_R2: "LM6UU linear bearing",
  rod_L: "6 mm steel rod, 112 mm", rod_R: "6 mm steel rod, 112 mm", lift_servo_MG90S: "MG90S servo", lift_crank: "servo horn, cut to 20 mm",
  wrist_servo: "MG90S servo", wrist_horn: "servo horn", gripper_servo_SG90: "SG90 servo", axle_R: "#6-32 screw (axle)",
  can_bumper: "rubber pad, cut 9 × 13.5 mm", arduino_uno: "Arduino Uno", buck_XL4015: "XL4015 buck converter", mini_breadboard: "mini breadboard",
  capacitor_1000uF: "1000 µF capacitor", start_button: "push button", status_led: "LED + 220 Ω", dc_jack: "DC jack / terminal tip" };
// steps where a fit needs care (tolerance): what, the size, how to test / fix
const BOUGHT_SHOW = ["bearing_6807", "LM6UU_L1", "rod_L", "turntable_servo_MG996R", "lift_servo_MG90S", "gripper_servo_SG90", "turntable_horn",
  "axle_R", "can_bumper", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF", "start_button", "status_led"];
const NOTES = JSON.parse(fs.readFileSync(path.join(ROOT, "backend/tools/assembly_notes.json"), "utf8"));
const FIT = Object.fromEntries(Object.entries(NOTES.steps).filter(([, v]) => v.fit).map(([k, v]) => [k, v.fit]));
const LEVEL = Object.fromEntries(Object.entries(NOTES.steps).map(([k, v]) => [k, v.level || "easy"]));

const DRAW = `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}</style></head><body>
<script src="file://${LIB}/three.min.js"></script><script>
const PARTS = ${JSON.stringify(parts)};
const PRINTED = ${JSON.stringify(PRINTED_PARTS)};
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(2); document.body.appendChild(renderer.domElement);
let W = 1200, H = 860; renderer.setSize(W, H);
renderer.setClearColor(0xffffff, 1);
const geoCache = {};
function geo(n){ if (geoCache[n]) return geoCache[n];
  return geoCache[n] = PARTS[n].map(p => { let g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(p.v, 3)); g.setIndex(p.f); g = g.toNonIndexed(); g.computeVertexNormals();
    return [g, new THREE.EdgesGeometry(g, p.kind === "printed" || p.kind === "can" ? 24 : 35), p.color, p.kind]; }); }
// draw(shown, fresh, offsets{name:[dx,dy,dz]}, arrows[[from,to]], az, el, size)
window.draw = (shown, fresh, offs, arrows, az, el, w, h, focus, paths) => {
  W = w || 1200; H = h || 860; renderer.setSize(W, H);
  const scene = new THREE.Scene(); const root = new THREE.Group(); root.rotation.x = -Math.PI/2; scene.add(root);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xb0b0b0, 0.95)); const d = new THREE.DirectionalLight(0xffffff, 0.35); d.position.set(200, 400, 300); scene.add(d);
  const box = new THREE.Box3();
  for (const n of shown) { if (!PARTS[n]) continue;
   const isNew = fresh.includes(n);
   for (const [g, e, hex, kind] of geo(n)) {
    let c = new THREE.Color(hex);
    if (kind === "printed") c = new THREE.Color(isNew ? 0x2f72e0 : 0xcadcf6);
    else if (kind === "can") c = new THREE.Color(isNew ? 0xe04040 : 0xf3c4c4);
    else if (!isNew && kind !== "glue") c.lerp(new THREE.Color(0xffffff), 0.6);
    const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({color: c, polygonOffset:true, polygonOffsetFactor:1, polygonOffsetUnits:1}));
    const ecol = kind === "printed" || kind === "can" ? (isNew ? 0x000000 : 0x3a3a3a) : kind === "bought" ? (isNew ? 0xff6a00 : 0xb0b0b0) : kind === "screw" ? (isNew ? 0x202020 : 0xaaaaaa) : 0x9a7a00;
    const l = new THREE.LineSegments(e, new THREE.LineBasicMaterial({color: ecol}));
    const o = offs[n] || [0,0,0]; m.position.set(...o); l.position.set(...o); root.add(m); root.add(l);
    g.computeBoundingBox(); const b = g.boundingBox.clone(); b.translate(new THREE.Vector3(...o)); box.union(b);
   }
  }
  for (const [a, b] of (paths || [])) {                       // screw paths: red dashed line through the hole
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), dir = B.clone().sub(A), L = dir.length(); dir.normalize();
    const mat = new THREE.MeshBasicMaterial({ color: 0xe00000, depthTest: false });
    for (let t = 0; t < L; t += 4.2) {                         // thick red dashes (WebGL lines are 1 px)
      const seg = Math.min(2.6, L - t), cy = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, seg, 8), mat);
      cy.position.copy(A.clone().addScaledVector(dir, t + seg / 2)); cy.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      cy.renderOrder = 5; root.add(cy);
    }
    box.expandByPoint(A);
  }
  for (const [a, b] of arrows) {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), dir = B.clone().sub(A), L = dir.length();
    if (L < 3) continue;
    const arr = new THREE.ArrowHelper(dir.normalize(), A, L, 0x000000, Math.min(9, L * 0.35), Math.min(6, L * 0.25)); root.add(arr);
    box.expandByPoint(A); box.expandByPoint(B);
  }
  // orthographic camera fitted to the drawing (or to the new parts + their arrows, when zoomed)
  if (focus && focus.length) {
    const fb = new THREE.Box3();
    for (const n of focus) { if (!PARTS[n]) continue; for (const [g] of geo(n)) { g.computeBoundingBox(); const b = g.boundingBox.clone(); b.translate(new THREE.Vector3(...(offs[n] || [0,0,0]))); fb.union(b); } }
    for (const [a, b] of arrows) { fb.expandByPoint(new THREE.Vector3(...a)); fb.expandByPoint(new THREE.Vector3(...b)); }
    const c = fb.getCenter(new THREE.Vector3()), sz = fb.getSize(new THREE.Vector3());
    const half = Math.max(45, Math.max(sz.x, sz.y, sz.z) * 0.9);
    box.makeEmpty(); box.expandByPoint(c.clone().addScalar(-half)); box.expandByPoint(c.clone().addScalar(half));
  }
  root.updateMatrixWorld();
  const ctr = box.getCenter(new THREE.Vector3()).applyMatrix4(root.matrixWorld);
  const a = az * Math.PI/180, e2 = el * Math.PI/180;
  const v = new THREE.Vector3(Math.cos(e2)*Math.cos(a), Math.cos(e2)*Math.sin(a), Math.sin(e2));  // model frame
  const vw = new THREE.Vector3(v.x, v.z, -v.y);                                                    // world (root rotated)
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, -5000, 5000);
  cam.position.copy(ctr.clone().addScaledVector(vw, 1000)); cam.up.set(0, 1, 0); cam.lookAt(ctr); cam.updateMatrixWorld();
  const pts = []; for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z])
    pts.push(new THREE.Vector3(x, y, z).applyMatrix4(root.matrixWorld).applyMatrix4(cam.matrixWorldInverse));
  let x0 = Math.min(...pts.map(p => p.x)), x1 = Math.max(...pts.map(p => p.x)), y0 = Math.min(...pts.map(p => p.y)), y1 = Math.max(...pts.map(p => p.y));
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2; let hw = (x1 - x0) / 2 * 1.12, hh = (y1 - y0) / 2 * 1.12;
  if (hw / hh > W / H) hh = hw * H / W; else hw = hh * W / H;
  cam.left = cx - hw; cam.right = cx + hw; cam.top = cy + hh; cam.bottom = cy - hh; cam.updateProjectionMatrix();
  renderer.render(scene, cam);
};
window.ready = true;
</script></body></html>`;

const ALL = Object.keys(parts).filter(n => n !== "test_can" && !n.startsWith("glue"));
function bbCenter(n) { let lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
  for (const m of parts[n]) { const v = m.v; for (let i = 0; i < v.length; i += 3) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], v[i + k]); hi[k] = Math.max(hi[k], v[i + k]); } }
  return lo.map((l, k) => (l + hi[k]) / 2); }

(async () => {
  const tmp = path.join(OUT, "_draw.html"); fs.writeFileSync(tmp, DRAW);
  const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--allow-file-access-from-files"] });
  const p = await b.newPage({ viewport: { width: 1200, height: 860 } });
  await p.goto("file://" + tmp); await p.waitForFunction("window.ready === true");
  const shot = async (file, w, h) => { const c = await p.$("canvas"); await c.screenshot({ path: path.join(OUT, file) }); };
  // cover: the whole robot with the can
  await p.evaluate(([s]) => window.draw(s, s, {}, [], -125, 22), [[...ALL, "test_can"]]); await shot("cover.png");
  // every step
  for (const s of steps) {
    const offs = {}, arrows = [];
    const ex = Math.min(s.dist, 45);
    for (const n of s.new) {
      const d = s.per_part_dir[n] || s.dir; if (!d) continue;
      const e = (s.per_part_dir[n] ? Math.min(ex, 22) : ex);
      offs[n] = d.map(c => c * e);
      const c = bbCenter(n);
      if (!s.new.slice(0, s.new.indexOf(n)).some(m => (s.per_part_dir[m] || s.dir) === d && s.new.length > 3)) {
        arrows.push([c.map((v, k) => v + d[k] * (e + 8)), c.map((v, k) => v + d[k] * 6)]);
      }
    }
    // one arrow per group of parts moving together (the carriage, the tray, the meshed fingers)
    const arr = s.new.length > 3 && !Object.keys(s.per_part_dir).length ? arrows.slice(0, 1) : arrows;
    const ZOOM = { 11: [-150, 15], 12: [-150, 20], 13: [-160, 15], 14: [-140, 20], 15: [-140, 20], 16: [-130, 25],
                   17: [-115, 50], 18: [-115, 50], 19: [-115, 45], 20: [-60, 30] };
    const [az, el] = ZOOM[s.n] || [s.az, s.el];
    const A = ASTEP[s.n], paths = [];
    for (const nm of A.screws) { const sc = SCREW[nm]; offs[nm] = sc.axis.map(c => -c * 18);
      paths.push([sc.head.map((v, k) => v - sc.axis[k] * 34), sc.head.map((v, k) => v + sc.axis[k] * sc.length)]); }
    const fresh = [...s.new, ...A.screws, ...A.glue, ...(s.n === 3 ? ["ballast"] : [])];
    await p.evaluate(([sh, nw, o, a, az, el, f, pa]) => window.draw(sh, nw, o, a, az, el, 1200, 860, f, pa), [A.show, fresh, offs, arr, az, el, ZOOM[s.n] ? [...s.new, ...A.screws] : null, paths]);
    await shot(`step_${String(s.n).padStart(2, "0")}.png`);
  }
  // parts page: every printed part on its own
  const printed = ["base", "electronics_tray", "turret_plate", "spine", "top_cap", "carriage_arm", "lift_link", "gripper_frame", "finger_R", "finger_L"];
  for (const n of printed) { await p.evaluate(([n]) => window.draw([n], [n], {}, [], -60, 30, 400, 300), [n]); await shot(`part_${n}.png`); }
  for (const n of BOUGHT_SHOW) { await p.evaluate(([n]) => window.draw([n], [n], {}, [], -60, 30, 400, 300), [n]); await shot(`bought_${n}.png`); }
  await b.close(); fs.unlinkSync(tmp);

  // ---------------- the manual (A4 landscape, IKEA style: pictures first, few words)
  const PN = { base: "CA-101", electronics_tray: "CA-102", turret_plate: "CA-201", spine: "CA-202", top_cap: "CA-203", carriage_arm: "CA-301",
    lift_link: "CA-302", gripper_frame: "CA-401", finger_R: "CA-402", finger_L: "CA-403" };
  const NAME = { base: "Base", electronics_tray: "Tray", turret_plate: "Turret plate", spine: "Spine", top_cap: "Top cap", carriage_arm: "Carriage arm",
    lift_link: "Lift link", gripper_frame: "Gripper frame", finger_R: "Finger R", finger_L: "Finger L" };
  const screw = (lbl) => `<svg viewBox="0 0 60 16" width="60" height="16"><rect x="0" y="2" width="9" height="12" rx="2" fill="#fff" stroke="#000" stroke-width="1.6"/>
    <rect x="9" y="5" width="${lbl.includes("#8") ? 40 : lbl.includes("#6") ? 34 : 22}" height="6" fill="#fff" stroke="#000" stroke-width="1.4"/>
    ${Array.from({ length: 8 }, (_, i) => `<line x1="${12 + i * 4}" y1="5" x2="${14 + i * 4}" y2="11" stroke="#000" stroke-width="0.8"/>`).join("")}</svg>`;
  const css = `@page{size:A4 landscape;margin:0}*{box-sizing:border-box}body{margin:0;font:17px/1.35 Helvetica,Arial,sans-serif;color:#000}
  .pg{width:297mm;height:210mm;position:relative;page-break-after:always;overflow:hidden;padding:12mm 14mm}
  .num{position:absolute;left:14mm;top:8mm;font:700 72px/1 Helvetica,Arial,sans-serif}
  .ttl{position:absolute;left:46mm;top:11mm;font-size:24px;font-weight:700;color:#000}
  .chips{position:absolute;left:46mm;right:14mm;top:22mm;display:flex;flex-wrap:wrap;gap:2mm}
  .chip{font-size:15px;font-weight:700;padding:1mm 3mm;border-radius:2mm;border:2px solid #000}
  .chip small{font-weight:400;font-size:13px}
  .chip.pr{background:#2f72e0;color:#fff;border-color:#1a4fa8}.chip.bo{background:#f29a2e;color:#000;border-color:#a85f00}
  .img{position:absolute;left:62mm;right:12mm;top:34mm;bottom:28mm;display:flex;align-items:center;justify-content:center}
  .img img{max-width:100%;max-height:100%}
  .box{position:absolute;left:14mm;top:36mm;width:45mm;border:2.4px solid #000;border-radius:3mm;padding:3mm;display:grid;gap:3mm;background:#fff}
  .hw{display:flex;align-items:center;gap:2mm;font-weight:700;font-size:18px}.hw small{font-weight:700;display:block;font-size:14px}
  .servo{position:absolute;left:14mm;bottom:30mm;width:45mm;border:2.4px solid #000;border-radius:50%;aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
  .servo b{font-size:36px}.servo span{font-size:14px;font-weight:700}
  .foot{position:absolute;left:62mm;right:14mm;bottom:8mm;display:grid;gap:2mm}
  .fit{display:flex;gap:3mm;align-items:flex-start;background:#ffe3e3;border:3px solid #c40000;border-radius:2.5mm;padding:2mm 3mm;font-size:16px;line-height:1.3}
  .fitb{background:#c40000;color:#fff;font-weight:700;font-size:18px;padding:.5mm 2.5mm;border-radius:1.5mm;flex:none}
  .side{position:absolute;right:14mm;top:36mm;width:94mm;bottom:9mm;display:flex;flex-direction:column;gap:2.5mm;font-size:15px;line-height:1.3}
  .lv{color:#fff;font-weight:800;font-size:20px;padding:1.5mm 3mm;border-radius:2mm;letter-spacing:.03em}
  .sbox{border:2px solid #000;border-radius:2mm;padding:2mm 2.5mm}
  .gluebox{border:3px solid #c9a400;background:#fff3b0;border-radius:2mm;padding:2mm 2.5mm}
  .note,.note2{font-size:17px;border-top:2px solid #000;padding-top:2mm;font-weight:600}
  .note{position:absolute;left:62mm;right:14mm;bottom:9mm}
  .warn::before{content:"!";display:inline-block;width:7mm;height:7mm;border:2.4px solid #000;border-radius:50%;text-align:center;font-weight:700;margin-right:2mm;line-height:6.4mm}
  .legend{display:flex;gap:4mm;flex-wrap:wrap;font-size:16px}
  .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:4mm;margin-top:5mm}.cell{border:2px solid #000;border-radius:2mm;padding:2mm;text-align:center;font-size:15px}
  .cell img{width:100%}h1{font-size:40px;margin:0}h2{font-size:24px;margin:0 0 3mm}.two{display:grid;grid-template-columns:1fr 1fr;gap:8mm}
  table{border-collapse:collapse;font-size:15px}
  .ebody{position:absolute;left:14mm;right:14mm;top:30mm;bottom:9mm;font-size:16px}.ebody.withimg{display:grid;grid-template-columns:1.15fr 1fr;gap:6mm}
  .eimg{width:100%;align-self:start}.md{width:100%;margin-bottom:3mm}.md td,.md th{font-size:15.5px;padding:1mm 1.6mm;vertical-align:top}.ck{width:6mm;text-align:center;font-size:15px}
  .ebody p{margin:0 0 2mm}.li{margin:0 0 1.5mm}.sec{position:absolute;right:14mm;top:10mm;font:700 16px Helvetica,Arial,sans-serif;border:2.4px solid #000;border-radius:2mm;padding:1mm 3mm}
  td,th{border:1.4px solid #000;padding:1.2mm 2mm;text-align:left}th{background:#e8e8e8}`;
  const img = f => `data:image/png;base64,${fs.readFileSync(path.join(OUT, f)).toString("base64")}`;
  const imgAny = f => `data:image/png;base64,${fs.readFileSync(path.join(ROOT, f)).toString("base64")}`;

  // ---- markdown (tables, paragraphs, lists) from the source docs, so the manual never drifts from them
  const inline = t => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
  const mdSection = (file, heading, tablesOnly) => {
    const lines = fs.readFileSync(path.join(ROOT, file), "utf8").split("\n");
    const i0 = lines.findIndex(l => l.startsWith("## ") && l.includes(heading));
    if (i0 < 0) throw new Error(`${file}: no section "${heading}"`);
    let i = i0 + 1, out = "", tbl = [];
    const flush = () => { if (!tbl.length) return;
      const rows = tbl.filter(r => !/^\|[\s:-]+\|/.test(r.replace(/[^|:\s-]/g, "x").replace(/x+/g, "x")) || /[A-Za-z0-9]/.test(r))
        .filter(r => !/^\|(\s*:?-+:?\s*\|)+\s*$/.test(r)).map(r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim())));
      out += `<table class="md"><tr><th class="ck"></th>${rows[0].map(c => `<th>${c}</th>`).join("")}</tr>` +
        rows.slice(1).map(r => `<tr><td class="ck">☐</td>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("") + "</table>"; tbl = []; };
    let para = "", kind = "";
    const endPara = () => { if (para && !tablesOnly) out += kind === "li" ? `<div class="li">• ${inline(para)}</div>` : `<p>${inline(para)}</p>`; para = ""; };
    for (; i < lines.length && !lines[i].startsWith("## "); i++) {
      const l = lines[i];
      if (l.startsWith("|")) { endPara(); tbl.push(l); continue; }
      flush();
      if (!l.trim()) { endPara(); continue; }
      if (l.startsWith("- ")) { endPara(); para = l.slice(2); kind = "li"; }
      else if (para) para += " " + l.trim();
      else { para = l.trim(); kind = "p"; }
    }
    endPara(); flush(); return out;
  };
  const ePage = (n, title, body, imgSrc) => `<div class="pg"><div class="num">${n}</div><div class="ttl" style="left:${n.length > 2 ? 68 : 50}mm">${title}</div>
    <div class="ebody ${imgSrc ? "withimg" : ""}">${imgSrc ? `<img class="eimg" src="${imgSrc}">` : ""}<div>${body}</div></div></div>`;
  let H = `<!doctype html><html><head><meta charset="utf-8"><title>Concept A Assembly Manual</title><style>${css}</style></head><body>`;
  H += `<div class="pg"><h1>CONCEPT A</h1><div style="font-size:20px;margin-top:2mm;font-weight:700">Can-flipping robot · assembly manual · ME 2331/L</div>
    <div class="img" style="left:14mm;right:106mm;top:36mm;bottom:26mm"><img src="${img("cover.png")}"></div>
    <div style="position:absolute;right:14mm;top:14mm;width:88mm;display:grid;gap:3mm">
      <span class="chip pr" style="font-size:18px">BLUE = PRINTED part</span><span class="chip bo" style="font-size:18px">ORANGE = BOUGHT part</span>
      <span class="fit" style="font-size:16px"><span class="fitb">FIT</span><span>= this step needs a careful fit: measure, test, sand or drill</span></span>
      <span style="font-size:15px">In each step the <b>new</b> parts are strong colour with black edges; parts already in place are pale.</span></div>
    <div class="note">1 person · ~3 h after printing · read each page, then build. <b>Servo angles:</b> the laptop control panel (or <code>firmware/servo_setup</code>) moves the servo to the angle in the round badge before you fit the horn.</div></div>`;
  H += `<div class="pg"><h2>You need</h2><div class="two"><div><table><tr><th>Tool</th></tr>
    ${["Phillips screwdrivers #1 and #2", "Multimeter", "Hot-glue gun", "Superglue", "Wire stripper", "Small flat screwdriver (buck pot)", "Hacksaw (6 mm rod) + file", "Vise or clamp (bearing press)", "12 mm drill bit, turned by hand", "Sandpaper 120 + 240, craft knife, flush cutters"].map(t => `<tr><td>${t}</td></tr>`).join("")}</table></div>
    <div><table><tr><th>Hardware</th><th>Qty</th></tr>
    <tr><td>${screw("#6")} #6-32 × ½″</td><td>8</td></tr><tr><td>${screw("#8")} #8-32 × ½″</td><td>4</td></tr><tr><td>${screw("s")} servo-bag screws</td><td>~14</td></tr>
    <tr><td>6807-2RS bearing</td><td>1</td></tr><tr><td>LM6UU linear bearing</td><td>4</td></tr><tr><td>6 mm rod, cut 2 × 112 mm</td><td>2</td></tr>
    <tr><td>Servos: MG996R / MG90S / SG90</td><td>1 / 2 / 1</td></tr></table>
    <p style="font-size:16px;margin-top:4mm"><span class="warn"></span>Before building: bench-test the electronics (docs/13_electronics_bench_test.md) and set the buck to <b>5.8 V</b>.</p></div></div></div>`;
  H += `<div class="pg"><h2><span class="chip pr" style="font-size:22px">PRINTED parts</span> &nbsp;blue in every drawing · 10 parts</h2><div class="grid">${printed.map(n => `<div class="cell" style="border-color:#1a4fa8"><img src="${img(`part_${n}.png`)}"><b>${PN[n]}</b><br>${NAME[n]}</div>`).join("")}</div></div>`;
  H += `<div class="pg"><h2><span class="chip bo" style="font-size:22px">BOUGHT parts</span> &nbsp;orange in every drawing · not printed</h2><div class="grid">${BOUGHT_SHOW.map(n => `<div class="cell" style="border-color:#a85f00"><img src="${img(`bought_${n}.png`)}"><b>${BOUGHT_NAME[n]}</b>${{ LM6UU_L1: " ×4", rod_L: " ×2", lift_servo_MG90S: " ×2" }[n] || ""}</div>`).join("")}</div></div>`;
  H += `<div class="pg"><h2>Fit level of every step: start with the easy ones while the precise parts print</h2>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5mm;margin-top:3mm">
    ${["precise", "try", "easy"].map(k => { const v = NOTES.levels[k]; const ns = steps.filter(x => LEVEL[x.n] === k);
      return `<div style="border:3px solid ${v.color};border-radius:3mm;padding:3mm"><div class="lv" style="background:${v.color}">${k === "precise" ? "⚠ " : ""}${v.label}</div>
        <p style="font-size:14.5px;margin:2mm 0">${v.text}</p>
        <table style="width:100%;font-size:14.5px">${ns.map(x => `<tr><td style="width:12mm;font-weight:700;font-size:18px;text-align:center">${x.n}</td><td>${x.title}${FIT[x.n] ? `<br><small>${FIT[x.n].replace(/<[^>]+>/g, "").split(/\.\s/)[0]}</small>` : ""}</td></tr>`).join("")}</table></div>`; }).join("")}
    </div>
    <div style="margin-top:4mm;font-size:15px"><b>Do while waiting:</b> ${NOTES.while_waiting.join(" · ")}.</div></div>`;

  // ---------------- PART E: electronics first (circuit + bench test), before any mechanical step
  H += `<div class="pg"><h1>PART E</h1><div style="font-size:18px;margin-top:3mm">Electronics first: wire it flat on the table and test it while the parts print</div>
    <div class="img" style="left:14mm;top:34mm"><img src="${imgAny("docs/wiring/wiring_diagram.png")}"></div></div>`;
  H += ePage("E1", "Circuit: every connection", mdSection("docs/04_wiring.md", "Wire list", true) +
    `<p><b>Never</b> connect the 5.8 V rail to the Uno's 5V pin: the Uno gets its power only from the 9 V battery. Servo plug: brown = GND, red = +, orange = signal. Diagram: page "PART E".</p>`);
  H += `<div class="pg"><div class="num">E1b</div><div class="ttl" style="left:62mm">Schematic: same circuit, same net name = connected</div>
    <div class="img" style="left:14mm;top:26mm;bottom:20mm"><img src="${imgAny("docs/wiring/schematic.png")}"></div>
    <div class="note">Uno on its own 9 V battery; the 12 V adapter feeds only the buck (servos). Uno GND and servo GND must be joined.</div></div>`;
  H += ePage("E2", "Bench test 1: power, no servos yet", mdSection("docs/13_electronics_bench_test.md", "1. Power"));
  H += ePage("E3", "Bench test 2: one servo at a time (firmware/bench_test)", mdSection("docs/13_electronics_bench_test.md", "2. One servo"));
  H += ePage("E3b", "Laptop control panel (viewer/control_panel.html)", mdSection("docs/13_electronics_bench_test.md", "2b. Laptop control panel"));
  H += ePage("E4", "If something is wrong", mdSection("docs/13_electronics_bench_test.md", "3. If something"));
  H += ePage("E5", "Wiring dry run (decides what to return)", mdSection("docs/13_electronics_bench_test.md", "4. Then the wiring dry run") +
    `<h2 style="margin-top:6mm">Then: PART P, printing, and PART M, the mechanics</h2><p>Print plates A–E with the settings on the next page, fix up the fits, then follow steps 1–${steps.length}. Keep the bench-test wiring: it moves into the tray in step ${steps.length - 2}.</p>`);
  // ---------------- PART P: economy printing (only the quality each part needs) + fix-up
  {
    const E = JSON.parse(fs.readFileSync(path.join(ROOT, "cad/print/settings/economy_plates.json"), "utf8"));
    const md = t => inline(t);
    H += ePage("P0", "PrusaSlicer: where to find everything (quick map)",
      `<div style="display:grid;grid-template-columns:0.9fr 1.25fr;gap:6mm">
        <div>${E.prusa_steps.map((t, i) => `<div class="li" style="font-size:15px"><b>${i + 1}.</b> ${md(t)}</div>`).join("")}</div>
        <table class="md" style="align-self:start">${E.prusa_keys.map(([k, v]) => `<tr><td style="width:34mm;font-size:15px"><b>${k}</b></td><td style="font-size:15px">${md(v)}</td></tr>`).join("")}</table>
      </div>`);
    H += ePage("P0b", "PrusaSlicer: where each setting lives",
      `<table class="md"><tr><th>Setting</th><th>Where (Expert mode)</th></tr>${E.prusa_map.map(([k, v]) => `<tr><td style="width:62mm;font-size:14px">${md(k)}</td><td style="font-size:14px">${md(v)}</td></tr>`).join("")}</table>`);
    H += ePage("P1", "Printing: set these once (same for every plate)",
      `<table class="md">${E.common.map(([k, v]) => `<tr><td class="ck">☐</td><td style="width:55mm"><b>${md(k)}</b></td><td>${md(v)}</td></tr>`).join("")}</table>
      <p style="font-size:16px">Then print plates <b>A → E</b> (next pages). Each page shows what goes on the bed and the settings for that whole plate.
      Total about <b>${Math.round(E.after[0])} h</b> and <b>${Math.round(E.after[1])} g</b> of PETG.</p>`);
    for (const P of E.plates) {
      const rows = [["Layer height", P.layer + " mm"], ["Walls", P.walls], ["Top / bottom layers", P.topbot], ["Infill density", P.infill.split(" ")[0]], ["Infill pattern", P.infill.split(" ")[1]],
        ["Speed: outer wall / inner wall / infill", P.speeds + " mm/s"], ["Supports", P.supports], ...P.support_rows.map(([k, v]) => ["&nbsp;&nbsp;" + k, md(v)]), ["Bed adhesion", P.adhesion]];
      H += `<div class="pg"><div class="num">${P.letter}</div><div class="ttl" style="left:34mm">Plate ${P.letter}: put these parts on the bed like this</div>
        <div style="position:absolute;left:12mm;top:26mm;width:165mm;height:118mm;display:flex;align-items:center;justify-content:center">
          <img src="${imgAny(P.img)}" style="max-width:100%;max-height:100%"></div>
        <div style="position:absolute;left:14mm;width:160mm;top:146mm;font-size:12px"><b>Files to add (Ctrl+I), from <code>cad/print/stl/</code>:</b>
          <div style="display:grid;grid-template-columns:repeat(3,48mm);gap:4mm;margin-top:1.5mm">${P.parts.map(c => `<div style="text-align:center;font-size:11px"><img src="${imgAny(c.img)}" style="height:30mm;max-width:100%;border:1px solid #ccc"><br><code>${c.file}</code></div>`).join("")}</div></div>
        <div style="position:absolute;left:182mm;right:12mm;top:30mm">
          <table class="md">${rows.map(([k, v]) => `<tr><td class="ck" style="padding:.5mm">☐</td><td style="font-size:13.5px;padding:.5mm 1.5mm">${k}</td><td style="padding:.5mm 1.5mm;font-size:${String(v).length > 30 ? 13 : 16}px"><b>${v}</b></td></tr>`).join("")}</table>
          <div style="margin-top:5mm;font-size:16px">≈ <b>${P.time}</b> · <b>${P.grams} g</b></div>
          <div style="margin-top:3mm;font-size:13px">PrusaSlicer: open <b><code>cad/print/plates_AE/plate_${P.letter}.3mf</code></b>: parts placed + all these settings inside. Other slicers: <code>plate_${P.letter}.stl</code> + type the settings.</div>
          <div style="margin-top:2mm;font-size:12px;color:#333">Same picture in your slicer: ${P.parts.length} part${P.parts.length > 1 ? "s" : ""}, flat side down as shown, don't rotate them up.</div>
        </div></div>`;
    }
    const cards = E.plates.flatMap(P => P.parts.map(c => ({ ...c, letter: P.letter })));
    for (let k = 0; k < cards.length; k += 6) {
      H += `<div class="pg"><div class="num">P2</div><div class="ttl" style="left:44mm">After printing: make the fits fit (sandpaper, drill, knife)${k ? " (continued)" : ""}</div>
        <div style="position:absolute;left:14mm;right:14mm;top:30mm;bottom:10mm;display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:1fr;gap:4mm">
        ${cards.slice(k, k + 6).map(c => `<div style="border:1px solid #000;border-radius:2mm;padding:2mm;display:grid;grid-template-columns:38mm 1fr;gap:3mm;font-size:12.5px;line-height:1.3;overflow:hidden">
          <div><img src="${imgAny(c.img)}" style="width:100%"><div style="font-size:11px;color:#555">plate ${c.letter}</div></div>
          <div><div><b>Must fit:</b> ${md(c.accurate)}</div><div style="margin-top:1.5mm">☐ ${md(c.fix)}</div></div></div>`).join("")}
        </div></div>`;
    }
    H += ePage("P3", "Fix-up rules", `<p style="font-size:14px">Tools: sandpaper 120 + 240 grit, 6 mm and 5/32 in (4 mm) drill bits turned by hand, a 12 mm dowel or marker wrapped in sandpaper, craft knife, flush cutters.</p>
      <div class="li" style="font-size:14px">• Sand a press fit a little at a time, test after every few strokes. Too loose: one layer of tape or a drop of superglue.</div>
      <div class="li" style="font-size:14px">• <b>Never sand or file gear teeth.</b></div>
      <div class="li" style="font-size:14px">• Plates B and C (coarse layers): holes can come out a little tight: drill or sand them.</div>
      <div class="li" style="font-size:14px">• A part cracks at a screw: the screw was forced: drill one size bigger, use the next screw or hot glue.</div>`);
  }
  const seen = new Set();
  for (const s of steps) {
    const first = s.new.filter(n => !seen.has(n)); s.new.forEach(n => seen.add(n));
    const hw = {}; for (const [q, n] of s.hw) hw[n] = (hw[n] || 0) + q;
    const box = Object.keys(hw).length ? `<div class="box">${Object.entries(hw).map(([n, q]) => `<div class="hw">${q}×&nbsp;${screw(n)}<small>${n.replace(" screw", "")}</small></div>`).join("")}</div>` : "";
    const cmd = s.badge ? { "135°": "t 135", "30°": "l 30", "0°": "w 0", "20°": "g 20" }[s.badge[1]] : "";
    const badge = s.badge ? `<div class="servo"><span>${s.badge[0]}</span><b>${s.badge[1]}</b><span><code>${cmd}</code></span></div>` : "";
    const pr = first.filter(n => PRINTED_PARTS.includes(n)), bo = {};
    for (const n of first.filter(n => !PRINTED_PARTS.includes(n) && n !== "test_can")) { const k = BOUGHT_NAME[n] || n; bo[k] = (bo[k] || 0) + 1; }
    const chips = `<div class="chips">${pr.map(n => `<span class="chip pr">PRINTED · ${NAME[n]} <small>${PN[n]}</small></span>`).join("")}${Object.entries(bo).map(([k, q]) => `<span class="chip bo">BOUGHT · ${q > 1 ? q + "× " : ""}${k}</span>`).join("")}</div>`;
    const N = NOTES.steps[String(s.n)] || {}, lv = NOTES.levels[LEVEL[s.n]];
    const A = ASTEP[s.n], sk = {}; for (const nm of A.screws) { const k = SCREW[nm].kind; sk[k] = (sk[k] || 0) + 1; }
    const side = `<div class="side">
      <div class="lv" style="background:${lv.color}">${LEVEL[s.n] === "precise" ? "⚠ " : ""}${lv.label}</div>
      ${s.badge ? `<div class="sbox" style="border-width:3px"><b>Servo angle first:</b> ${s.badge[0]} → <b style="font-size:20px">${s.badge[1]}</b> (laptop panel, or <code>${cmd}</code>)</div>` : ""}
      ${Object.keys(sk).length ? `<div class="sbox"><b>Screws</b> (red dashed line = path): ${Object.entries(sk).map(([k, q]) => `${q}× ${NOTES.screw_names[k]}`).join(", ")}</div>` : ""}
      ${N.how ? `<div class="sbox">${N.how}</div>` : (s.note ? `<div class="sbox">${s.note}</div>` : "")}
      ${N.fit ? `<div class="fit"><span class="fitb">FIT</span><div>${N.fit}</div></div>` : ""}
      ${N.glue ? `<div class="gluebox"><b>GLUE</b> ${N.glue}</div>` : ""}
      <div style="font-size:13px;color:#333">Rotate / zoom this step in 3D: <b>viewer/assembly.html#${s.n}</b></div></div>`;
    H += `<div class="pg"><div class="num">${s.n}</div><div class="ttl">${s.title}</div>${s.n === 1 ? '<div class="sec">PART M</div>' : ""}${chips}
      <div class="img" style="left:14mm;right:112mm;bottom:8mm;${pr.length + Object.keys(bo).length > 3 ? "top:44mm" : ""}"><img src="${img(`step_${String(s.n).padStart(2, "0")}.png`)}"></div>${side}</div>`;
  }
  H += `<div class="pg"><div class="num">${steps.length + 1}</div><div class="ttl">Wiring</div>
    <div class="img" style="left:14mm;right:110mm;top:28mm"><img src="${imgAny("docs/wiring/wiring_3d_column_clean.png")}"></div>
    <div style="position:absolute;right:14mm;top:28mm;width:92mm"><table><tr><th>Servo lead</th><th>Pin</th></tr>
    <tr><td>MG996R turntable</td><td>D9 (+/− on the buck)</td></tr><tr><td>MG90S lift</td><td>D10</td></tr><tr><td>MG90S wrist</td><td>D6</td></tr><tr><td>SG90 gripper</td><td>D5</td></tr>
    <tr><td>START button</td><td>D4 + GND</td></tr><tr><td>LED + 220 Ω</td><td>D13 + GND</td></tr></table>
    <p style="font-size:12.5px">Route: claw → wrist loop → along the arm → lift loop → spine window → down the back → turret notch → turn loop → base hole → tray. <b>Tie at the tie points, leave the 3 loops free.</b> Wrist loop ≥ 70 mm of cable.</p>
    <p style="font-size:12.5px">3D view: viewer/wiring_360.html · moves: viewer/wiring_motion.html</p></div>
    <div class="note warn">Power off while wiring. Servo plugs: brown = GND, red = +5.8 V, orange = signal.</div></div>`;
  H += `<div class="pg"><div class="num">${steps.length + 2}</div><div class="ttl">Test</div>
    <div class="img"><img src="${img("cover.png")}"></div>
    <div class="box" style="font-weight:400;font-size:12.5px">1. Upload <code>firmware/concept_a</code><br>2. Can on START, 5 in out<br>3. Press START<br>4. Can lands upside down at TARGET</div>
    <div class="note">If a move is off: re-set its angle with servo_setup, then edit the constant at the top of concept_a.ino.</div></div>`;
  H += `</body></html>`;
  const html = path.join(ROOT, "docs/12_assembly_manual.html"); fs.writeFileSync(html, H);
  const b2 = await chromium.launch(); const p2 = await b2.newPage();
  await p2.goto("file://" + html); await p2.pdf({ path: path.join(ROOT, "docs/12_assembly_manual.pdf"), format: "A4", landscape: true, printBackground: true });
  await b2.close();
  const nPages = (H.match(/class="pg"/g) || []).length;
  console.log(`docs/12_assembly_manual.pdf: ${nPages} pages, ${(fs.statSync(path.join(ROOT, "docs/12_assembly_manual.pdf")).size / 1024) | 0} KB`);
})();
