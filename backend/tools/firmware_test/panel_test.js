// End-to-end test: viewer/control_panel.html in Chromium, talking through a fake Web Serial port to
// the real firmware (firmware/concept_a/concept_a.ino) running live on the PC (interactive.cpp).
//   g++ -std=c++17 -pthread -Ifake -o /tmp/concept_a_live interactive.cpp && node panel_test.js
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const ROOT = path.resolve(__dirname, "..", "..", "..");
const BIN = process.env.LIVE_BIN || path.join(process.env.TMPDIR || "/tmp", "concept_a_live");
const SHOT = process.env.SHOT || "";
let fails = 0;
const expect = (ok, what) => { console.log((ok ? "PASS  " : "FAIL  ") + what); if (!ok) fails++; };
(async () => {
  const fw = spawn(BIN, [], { stdio: ["pipe", "pipe", "inherit"] });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 1300 } });
  await p.exposeFunction("__serialWrite", s => fw.stdin.write(s));
  await p.addInitScript(() => {
    let ctl;
    const port = {
      readable: new ReadableStream({ start(c) { ctl = c; } }),
      writable: new WritableStream({ write(chunk) { window.__serialWrite(new TextDecoder().decode(chunk)); } }),
      open: async () => {}, close: async () => {},
    };
    window.__serialPush = s => ctl.enqueue(new TextEncoder().encode(s));
    Object.defineProperty(navigator, "serial", { value: { requestPort: async () => port } });
  });
  await p.goto("file://" + path.join(ROOT, "viewer/control_panel.html"));
  fw.stdout.on("data", d => p.evaluate(s => window.__serialPush(s), d.toString()).catch(() => {}));
  const angle = k => p.textContent("#a-" + k);
  const mode = () => p.textContent("#mode");
  const waitMode = async (m, ms) => { const end = Date.now() + ms; while (Date.now() < end) { if ((await mode()) === m) return true; await p.waitForTimeout(100); } return false; };

  await p.click("#connect");
  await p.waitForTimeout(3200);
  expect((await p.textContent("#conn")) === "connected" && (await mode()) === "IDLE", "connects, reads status (IDLE)");
  expect((await angle("t")) === "135" && (await angle("g")) === "20", "shows the HOME angles");

  await p.click('#card-w button[data-a="180"]');
  await p.waitForTimeout(300);
  expect((await mode()) === "MANUAL", "wrist FLIPPED button: firmware starts moving (MANUAL)");
  expect(await p.isDisabled('#card-l button[data-a="75"]'), "servo buttons disabled while moving");
  expect(await waitMode("IDLE", 4000) && (await angle("w")) === "180", "wrist reaches 180, others unchanged");

  await p.click("#start"); await p.waitForTimeout(400);
  expect((await p.textContent("#log")).includes("Not at HOME"), "START away from HOME is refused (firmware guard)");

  await p.click("#home"); await p.waitForTimeout(300);
  expect(await waitMode("IDLE", 8000) && (await angle("w")) === "0", "HOME brings it back");

  await p.fill("#r-t", "60"); await p.dispatchEvent("#r-t", "input");
  await p.click('#card-t button[data-go]');
  expect(await waitMode("MANUAL", 1000) && await waitMode("IDLE", 4000) && (await angle("t")) === "60", "slider + Go moves the base to 60");
  await p.click("#home"); await waitMode("MANUAL", 1000); await waitMode("IDLE", 8000);

  await p.click("#start");
  expect(await waitMode("RUNNING", 1500), "START runs the sequence");
  if (SHOT) await p.screenshot({ path: SHOT, fullPage: true });
  expect(await waitMode("DONE", 12000) && (await angle("t")) === "45" && (await angle("w")) === "180", "sequence ends DONE at the target, flipped");

  await p.click("#start"); await waitMode("RETURNING", 1500);
  await p.waitForTimeout(1500); await p.click("#stop"); await p.waitForTimeout(300);
  expect((await mode()) === "IDLE" && (await p.textContent("#log")).includes("Stopped"), "STOP mid-move holds and reports");

  // calibration: firmware values shown, capture a new angle, code block, test button
  await p.click("#home"); await waitMode("MANUAL", 1500); await waitMode("IDLE", 8000);
  expect((await p.textContent("#cal-TURN_START td.num")) === "135", "calibration table shows the firmware's values (from 'c')");
  await p.click('#card-t button[data-d="-1"]'); await waitMode("MANUAL", 1000); await waitMode("IDLE", 3000);
  await p.click('#card-t button[data-d="-1"]'); await waitMode("MANUAL", 1000); await waitMode("IDLE", 3000);
  expect((await angle("t")) === "133", "±1° buttons nudge the base (135 → 133)");
  await p.click('button[data-use="TURN_START"]');
  expect((await p.inputValue('#cal-TURN_START input')) === "133" && (await p.textContent("#calcode")).includes("const int TURN_START   = 133;"),
         "Use current angle captures 133 and writes it into the code block");
  await p.click('#card-t button[data-a="45"]'); await waitMode("MANUAL", 1000); await waitMode("IDLE", 5000);
  await p.click('button[data-test="TURN_START"]'); await waitMode("MANUAL", 1000); await waitMode("IDLE", 5000);
  expect((await angle("t")) === "133", "Test sends the saved value (base back to 133)");
  if (process.env.SHOT2) await p.screenshot({ path: process.env.SHOT2, fullPage: true });

  console.log(fails ? `FAIL (${fails})` : "ALL PASS");
  await b.close(); fw.kill(); process.exit(fails ? 1 : 0);
})();
