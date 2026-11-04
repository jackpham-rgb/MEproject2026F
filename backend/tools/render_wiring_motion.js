// Build viewer/wiring_motion.html and render one animation per move.
//   python3.13 backend/cad/wiring.py && python3.13 backend/cad/wiring_motion.py && node backend/tools/render_wiring_motion.js
// Outputs: viewer/wiring_motion.html, docs/wiring/motion/{1_GRIP..6_RELEASE}.gif, docs/wiring/motion/all_moves.mp4
const fs = require("fs"), path = require("path"), os = require("os"), { execFileSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(__dirname, "..", "..");
const rd = f => fs.readFileSync(path.join(ROOT, f), "utf8");
const rep = rd("cad/wiring/wiring_motion_report.txt").replace(/&/g, "&amp;").replace(/</g, "&lt;");
const page = rd("viewer/wiring_motion_template.html").replace("__REPORT__", () => rep)
  .replace("__MESH__", () => rd("backend/cad/build/wiring_mesh.json")).replace("__MOTION__", () => rd("backend/cad/build/wiring_motion.json"));
const html = path.join(ROOT, "viewer/wiring_motion.html");
fs.writeFileSync(html, page);
console.log(`viewer/wiring_motion.html: ${(fs.statSync(html).size / 1024) | 0} KB`);
const OUT = path.join(ROOT, "docs/wiring/motion"); fs.mkdirSync(OUT, { recursive: true });
const FR = fs.mkdtempSync(path.join(os.tmpdir(), "wiremot-"));
const NAMES = JSON.parse(rd("backend/cad/build/wiring_motion.json")).actions.map(a => a.name);
(async () => {
  const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  await p.goto("file://" + html);
  await p.waitForFunction("window.__ready === true", null, { timeout: 60000 });
  await p.evaluate(() => document.body.classList.add("capture"));
  let g = 0;                                                     // global frame counter for the MP4
  const all = path.join(FR, "all"); fs.mkdirSync(all);
  for (let ai = 0; ai < NAMES.length; ai++) {
    const n = await p.evaluate(a => window.__frames(a), ai);
    const dir = path.join(FR, "a" + ai); fs.mkdirSync(dir);
    let f = 0;
    const shot = async () => {
      const file = path.join(dir, `f${String(f++).padStart(3, "0")}.png`);
      await p.screenshot({ path: file }); fs.copyFileSync(file, path.join(all, `f${String(g++).padStart(4, "0")}.png`));
    };
    for (let k = 0; k < n; k++) { await p.evaluate(([a, kk]) => window.__show(a, kk), [ai, k]); await shot(); }
    for (let h = 0; h < 12; h++) await shot();                     // hold the end pose ~1 s
    const name = `${ai + 1}_${NAMES[ai]}`;
    execFileSync("ffmpeg", ["-y", "-framerate", "12", "-i", path.join(dir, "f%03d.png"), "-vf",
      "scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
      path.join(OUT, name + ".gif")], { stdio: "ignore" });
    console.log(`docs/wiring/motion/${name}.gif: ${(fs.statSync(path.join(OUT, name + ".gif")).size / 1024) | 0} KB (${n} frames)`);
    if (ai === 3) await p.screenshot({ path: path.join(OUT, "turn_end.png") });
  }
  await b.close();
  execFileSync("ffmpeg", ["-y", "-framerate", "12", "-i", path.join(all, "f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
    path.join(OUT, "all_moves.mp4")], { stdio: "ignore" });
  console.log(`docs/wiring/motion/all_moves.mp4: ${(fs.statSync(path.join(OUT, "all_moves.mp4")).size / 1024) | 0} KB`);
  fs.rmSync(FR, { recursive: true });
})();
