// Build viewer/wiring_360.html and render the 360 wiring views.
//   python3.13 backend/cad/wiring.py && node backend/tools/render_wiring_360.js
// Outputs: viewer/wiring_360.html, docs/wiring/wiring_360{,_clean}.gif + .mp4 (_clean = no legend / tags),
//          docs/wiring/wiring_3d_{iso,back,column,tray}.png and *_clean.png
// THREE_LOCAL=<dir with three.min.js and OrbitControls.js> serves three.js locally when the CDN is blocked.
const fs = require("fs"), path = require("path"), { execFileSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(__dirname, "..", "..");
const mesh = fs.readFileSync(path.join(ROOT, "backend/cad/build/wiring_mesh.json"), "utf8");
const rep = fs.readFileSync(path.join(ROOT, "cad/wiring/wiring_report.txt"), "utf8").replace(/&/g, "&amp;").replace(/</g, "&lt;");
let page = fs.readFileSync(path.join(ROOT, "viewer/wiring_360_template.html"), "utf8");
page = page.replace("__REPORT__", () => rep).replace("__MESH__", () => mesh);
const html = path.join(ROOT, "viewer/wiring_360.html");
fs.writeFileSync(html, page);
console.log(`viewer/wiring_360.html: ${(fs.statSync(html).size / 1024) | 0} KB`);

const OUT = path.join(ROOT, "docs/wiring"), FR = fs.mkdtempSync(path.join(require("os").tmpdir(), "wire360-"));
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const L = process.env.THREE_LOCAL;
  if (L) {
    await p.route("**/three.min.js", r => r.fulfill({ path: path.join(L, "three.min.js"), contentType: "text/javascript" }));
    await p.route("**/OrbitControls.js", r => r.fulfill({ path: path.join(L, "OrbitControls.js"), contentType: "text/javascript" }));
  }
  await p.goto("file://" + html);
  await p.waitForFunction("window.__ready === true", null, { timeout: 60000 });
  await p.evaluate(() => document.body.classList.add("capture"));
  await p.waitForTimeout(300);
  for (const v of ["iso", "back", "column", "tray"]) {
    await p.evaluate(v => window.__frame(v), v); await p.waitForTimeout(150);
    await p.screenshot({ path: path.join(OUT, `wiring_3d_${v}.png`) });
  }
  const N = 72;
  const runs = [["", false], ["_clean", true]];          // with legend + number tags, and without
  for (const [suf, clean] of runs) {
    await p.evaluate(c => document.body.classList.toggle("nolegend", c), clean);
    await p.waitForTimeout(200);
    const dir = path.join(FR, "run" + suf); fs.mkdirSync(dir);
    for (let i = 0; i < N; i++) {
      await p.evaluate(a => window.__frame("iso", a), -125 + i * 360 / N);
      await p.screenshot({ path: path.join(dir, `f${String(i).padStart(3, "0")}.png`) });
    }
    if (clean) for (const v of ["iso", "column", "tray"]) {
      await p.evaluate(v => window.__frame(v), v); await p.waitForTimeout(150);
      await p.screenshot({ path: path.join(OUT, `wiring_3d_${v}_clean.png`) });
    }
  }
  await b.close();
  for (const suf of ["", "_clean"]) {
    const inp = ["-y", "-framerate", "12", "-i", path.join(FR, "run" + suf, "f%03d.png")];
    execFileSync("ffmpeg", [...inp, "-vf", "scale=1280:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", path.join(OUT, `wiring_360${suf}.mp4`)], { stdio: "ignore" });
    execFileSync("ffmpeg", [...inp, "-vf", "scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4", path.join(OUT, `wiring_360${suf}.gif`)], { stdio: "ignore" });
  }
  fs.rmSync(FR, { recursive: true });
  for (const f of fs.readdirSync(OUT).filter(f => /wiring_(360|3d)/.test(f))) console.log(`docs/wiring/${f}: ${(fs.statSync(path.join(OUT, f)).size / 1024) | 0} KB`);
})();
