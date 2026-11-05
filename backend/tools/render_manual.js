// Assembly manual, step 2 of 2: line drawings for every step + the printable manual.
//   python3.13 backend/cad/export.py && python3.13 backend/tools/make_manual.py && node backend/tools/render_manual.js
// Reads backend/cad/build/viewer_mesh.json (parts in place) and manual_steps.json (steps).
// Writes docs/manual/step_NN.png, cover.png, parts.png and docs/12_assembly_manual.pdf (+ .html).
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "docs/manual"); fs.mkdirSync(OUT, { recursive: true });
const mesh = JSON.parse(fs.readFileSync(path.join(ROOT, "backend/cad/build/viewer_mesh.json"), "utf8"));
const steps = JSON.parse(fs.readFileSync(path.join(ROOT, "backend/cad/build/manual_steps.json"), "utf8")).steps;
const parts = {}; for (const g of Object.values(mesh.groups)) for (const p of g) parts[p.name] = p;
const LIB = path.join(ROOT, "viewer/lib");

const DRAW = `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}</style></head><body>
<script src="file://${LIB}/three.min.js"></script><script>
const PARTS = ${JSON.stringify(parts)};
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(2); document.body.appendChild(renderer.domElement);
let W = 1200, H = 860; renderer.setSize(W, H);
renderer.setClearColor(0xffffff, 1);
const geoCache = {};
function geo(n){ if (geoCache[n]) return geoCache[n]; const p = PARTS[n]; let g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(p.v, 3)); g.setIndex(p.f); g = g.toNonIndexed(); g.computeVertexNormals();
  const e = new THREE.EdgesGeometry(g, 24); return geoCache[n] = [g, e]; }
// draw(shown, fresh, offsets{name:[dx,dy,dz]}, arrows[[from,to]], az, el, size)
window.draw = (shown, fresh, offs, arrows, az, el, w, h, focus) => {
  W = w || 1200; H = h || 860; renderer.setSize(W, H);
  const scene = new THREE.Scene(); const root = new THREE.Group(); root.rotation.x = -Math.PI/2; scene.add(root);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xb0b0b0, 0.95)); const d = new THREE.DirectionalLight(0xffffff, 0.35); d.position.set(200, 400, 300); scene.add(d);
  const box = new THREE.Box3();
  for (const n of shown) {
    const [g, e] = geo(n); const isNew = fresh.includes(n);
    const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({color: isNew ? 0xd6e4f5 : 0xffffff, polygonOffset:true, polygonOffsetFactor:1, polygonOffsetUnits:1}));
    const l = new THREE.LineSegments(e, new THREE.LineBasicMaterial({color: isNew ? 0x000000 : 0x5a5a5a}));
    const o = offs[n] || [0,0,0]; m.position.set(...o); l.position.set(...o); root.add(m); root.add(l);
    g.computeBoundingBox(); const b = g.boundingBox.clone(); b.translate(new THREE.Vector3(...o)); box.union(b);
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
    for (const n of focus) { const [g] = geo(n); g.computeBoundingBox(); const b = g.boundingBox.clone(); b.translate(new THREE.Vector3(...(offs[n] || [0,0,0]))); fb.union(b); }
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

const ALL = Object.keys(parts).filter(n => n !== "test_can");
function bbCenter(n) { const v = parts[n].v; let lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
  for (let i = 0; i < v.length; i += 3) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], v[i + k]); hi[k] = Math.max(hi[k], v[i + k]); }
  return lo.map((l, k) => (l + hi[k]) / 2); }

(async () => {
  const tmp = path.join(OUT, "_draw.html"); fs.writeFileSync(tmp, DRAW);
  const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--allow-file-access-from-files"] });
  const p = await b.newPage({ viewport: { width: 1200, height: 860 } });
  await p.goto("file://" + tmp); await p.waitForFunction("window.ready === true");
  const shot = async (file, w, h) => { const c = await p.$("canvas"); await c.screenshot({ path: path.join(OUT, file) }); };
  // cover: the whole robot with the can
  await p.evaluate(([s]) => window.draw(s, [], {}, [], -125, 22), [[...ALL, "test_can"]]); await shot("cover.png");
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
    await p.evaluate(([sh, nw, o, a, az, el, f]) => window.draw(sh, nw, o, a, az, el, 1200, 860, f), [s.show, s.new, offs, arr, az, el, ZOOM[s.n] ? s.new : null]);
    await shot(`step_${String(s.n).padStart(2, "0")}.png`);
  }
  // parts page: every printed part on its own
  const printed = ["base", "electronics_tray", "turret_plate", "spine", "top_cap", "carriage_arm", "lift_link", "gripper_frame", "finger_R", "finger_L"];
  for (const n of printed) { await p.evaluate(([n]) => window.draw([n], [n], {}, [], -60, 30, 400, 300), [n]); await shot(`part_${n}.png`); }
  await b.close(); fs.unlinkSync(tmp);

  // ---------------- the manual (A4 landscape, IKEA style: pictures first, few words)
  const PN = { base: "CA-101", electronics_tray: "CA-102", turret_plate: "CA-201", spine: "CA-202", top_cap: "CA-203", carriage_arm: "CA-301",
    lift_link: "CA-302", gripper_frame: "CA-401", finger_R: "CA-402", finger_L: "CA-403" };
  const NAME = { base: "Base", electronics_tray: "Tray", turret_plate: "Turret plate", spine: "Spine", top_cap: "Top cap", carriage_arm: "Carriage arm",
    lift_link: "Lift link", gripper_frame: "Gripper frame", finger_R: "Finger R", finger_L: "Finger L" };
  const screw = (lbl) => `<svg viewBox="0 0 60 16" width="60" height="16"><rect x="0" y="2" width="9" height="12" rx="2" fill="#fff" stroke="#000" stroke-width="1.6"/>
    <rect x="9" y="5" width="${lbl.includes("#8") ? 40 : lbl.includes("#6") ? 34 : 22}" height="6" fill="#fff" stroke="#000" stroke-width="1.4"/>
    ${Array.from({ length: 8 }, (_, i) => `<line x1="${12 + i * 4}" y1="5" x2="${14 + i * 4}" y2="11" stroke="#000" stroke-width="0.8"/>`).join("")}</svg>`;
  const css = `@page{size:A4 landscape;margin:0}*{box-sizing:border-box}body{margin:0;font:14px/1.35 Helvetica,Arial,sans-serif;color:#000}
  .pg{width:297mm;height:210mm;position:relative;page-break-after:always;overflow:hidden;padding:12mm 14mm}
  .num{position:absolute;left:14mm;top:9mm;font:700 64px/1 Helvetica,Arial,sans-serif}
  .ttl{position:absolute;left:44mm;top:14mm;font-size:15px;color:#333}
  .img{position:absolute;left:60mm;right:12mm;top:16mm;bottom:22mm;display:flex;align-items:center;justify-content:center}
  .img img{max-width:100%;max-height:100%}
  .box{position:absolute;left:14mm;top:34mm;width:42mm;border:1.6px solid #000;border-radius:3mm;padding:3mm;display:grid;gap:2.5mm}
  .hw{display:flex;align-items:center;gap:2mm;font-weight:700}.hw small{font-weight:400;display:block;font-size:10.5px}
  .servo{position:absolute;left:14mm;bottom:30mm;width:42mm;border:1.6px solid #000;border-radius:50%;aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
  .servo b{font-size:30px}.servo span{font-size:11px}
  .note{position:absolute;left:60mm;right:14mm;bottom:9mm;font-size:13px;border-top:1px solid #000;padding-top:2mm}
  .warn::before{content:"!";display:inline-block;width:6mm;height:6mm;border:1.6px solid #000;border-radius:50%;text-align:center;font-weight:700;margin-right:2mm;line-height:5.4mm}
  .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:4mm;margin-top:6mm}.cell{border:1px solid #000;border-radius:2mm;padding:2mm;text-align:center;font-size:12px}
  .cell img{width:100%}h1{font-size:34px;margin:0}h2{font-size:20px;margin:0 0 3mm}.two{display:grid;grid-template-columns:1fr 1fr;gap:8mm}
  table{border-collapse:collapse;font-size:12.5px}td,th{border:1px solid #000;padding:1.2mm 2mm;text-align:left}`;
  const img = f => `data:image/png;base64,${fs.readFileSync(path.join(OUT, f)).toString("base64")}`;
  const imgAny = f => `data:image/png;base64,${fs.readFileSync(path.join(ROOT, f)).toString("base64")}`;
  let H = `<!doctype html><html><head><meta charset="utf-8"><title>Concept A Assembly Manual</title><style>${css}</style></head><body>`;
  H += `<div class="pg"><h1>CONCEPT A</h1><div style="font-size:16px;margin-top:2mm">Can-flipping robot · assembly manual · ME 2331/L</div>
    <div class="img" style="left:14mm;top:30mm"><img src="${img("cover.png")}"></div>
    <div class="note">1 person · ~3 h after printing · read each page, then build. <b>Servo angles:</b> load <code>firmware/servo_setup</code> and type the command in the round badge (Serial Monitor, 9600).</div></div>`;
  H += `<div class="pg"><h2>You need</h2><div class="two"><div><table><tr><th>Tool</th></tr>
    ${["Phillips screwdrivers #1 and #2", "Multimeter", "Hot-glue gun", "Superglue", "Wire stripper", "Small flat screwdriver (buck pot)", "Hacksaw (6 mm rod) + file", "Vise or clamp (bearing press)", "12 mm drill bit, turned by hand"].map(t => `<tr><td>${t}</td></tr>`).join("")}</table></div>
    <div><table><tr><th>Hardware</th><th>Qty</th></tr>
    <tr><td>${screw("#6")} #6-32 × ½″</td><td>8</td></tr><tr><td>${screw("#8")} #8-32 × ½″</td><td>4</td></tr><tr><td>${screw("s")} servo-bag screws</td><td>~14</td></tr>
    <tr><td>6807-2RS bearing</td><td>1</td></tr><tr><td>LM6UU linear bearing</td><td>4</td></tr><tr><td>6 mm rod, cut 2 × 112 mm</td><td>2</td></tr>
    <tr><td>Servos: MG996R / MG90S / SG90</td><td>1 / 2 / 1</td></tr></table>
    <p style="font-size:12.5px;margin-top:4mm"><span class="warn"></span>Before building: bench-test the electronics (docs/13_electronics_bench_test.md) and set the buck to <b>5.8 V</b>.</p></div></div></div>`;
  H += `<div class="pg"><h2>Printed parts</h2><div class="grid">${printed.map(n => `<div class="cell"><img src="${img(`part_${n}.png`)}"><b>${PN[n]}</b><br>${NAME[n]}</div>`).join("")}</div></div>`;
  for (const s of steps) {
    const hw = {}; for (const [q, n] of s.hw) hw[n] = (hw[n] || 0) + q;
    const box = Object.keys(hw).length ? `<div class="box">${Object.entries(hw).map(([n, q]) => `<div class="hw">${q}×&nbsp;${screw(n)}<small>${n.replace(" screw", "")}</small></div>`).join("")}</div>` : "";
    const cmd = s.badge ? { "135°": "t 135", "30°": "l 30", "0°": "w 0", "20°": "g 20" }[s.badge[1]] : "";
    const badge = s.badge ? `<div class="servo"><span>${s.badge[0]}</span><b>${s.badge[1]}</b><span><code>${cmd}</code></span></div>` : "";
    H += `<div class="pg"><div class="num">${s.n}</div><div class="ttl">${s.title}</div>${box}${badge}
      <div class="img"><img src="${img(`step_${String(s.n).padStart(2, "0")}.png`)}"></div>
      ${s.note ? `<div class="note ${/GLUE|must|first|don't|5.8/.test(s.note) ? "warn" : ""}">${s.note}</div>` : ""}</div>`;
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
  console.log(`docs/12_assembly_manual.pdf: ${steps.length + 5} pages, ${(fs.statSync(path.join(ROOT, "docs/12_assembly_manual.pdf")).size / 1024) | 0} KB`);
})();
