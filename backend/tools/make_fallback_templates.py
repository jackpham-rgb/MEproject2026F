"""Fallback kit (no 3D printer): 1:1 cut templates for the cardboard / foam-board robot + print-shop zips.

    python3.13 backend/tools/make_fallback_templates.py
      -> fallback_no_printer/cut_templates.pdf          (US Letter, print at 100 % / "Actual size")
      -> fallback_no_printer/templates_preview.png
      -> fallback_no_printer/print_service/*.zip        (STL files for a makerspace / online print service)

Every dimension comes from backend/cad/model.py (same numbers as the printed robot and Plan P), so the
cardboard robot puts the can in exactly the same place.
"""
import math
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "cad"))
import model as M  # noqa: E402

P = M.P
OUT = os.path.join(ROOT, "fallback_no_printer")
W, H = 215.9, 279.4                       # US Letter, mm
LINK_HOLES = 11.4                          # lift link hole-to-hole (Plan P)
SPINE_W = 40.0                             # spine width (foam board)
RED, BLUE, GREY = "#c0392b", "#1a4fa0", "#777"


def t(x, y, s, size=3.2, anchor="start", color="#111", weight="normal"):
    lines = s.split("\n")
    out = []
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x:.2f}" y="{y + i * size * 1.25:.2f}" font-size="{size}" text-anchor="{anchor}" '
                   f'fill="{color}" font-weight="{weight}" font-family="Helvetica, Arial, sans-serif">{ln}</text>')
    return "".join(out)


def rect(x, y, w, h, stroke="#111", fill="none", sw=0.35, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" stroke="{stroke}" fill="{fill}" stroke-width="{sw}"{d}/>'


def circ(x, y, r, stroke="#111", fill="none", sw=0.35, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" stroke="{stroke}" fill="{fill}" stroke-width="{sw}"{d}/>'


def line(x0, y0, x1, y1, stroke="#111", sw=0.35, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def cross(x, y, r=3, color=RED):
    return line(x - r, y, x + r, y, color, 0.25) + line(x, y - r, x, y + r, color, 0.25)


def header(n, title, sub):
    return (t(10, 13, f"Concept A fallback kit · page {n} · {title}", 5, weight="bold")
            + t(10, 19, sub, 3, color="#444")
            + t(W - 10, H - 6, "PRINT AT 100 % (\"Actual size\", not \"Fit\"). Check the 50 mm square on page 1 with a ruler.",
                2.6, "end", GREY))


def page1():
    s = header(1, "scale check + turret + rod plates", "Solid line = cut. Red cross = hole centre. Dashed = glue / position mark. Foam board 5 mm.")
    # scale check
    s += rect(10, 26, 50, 50, sw=0.5) + t(35, 50, "50 mm\nsquare", 4, "middle", weight="bold")
    s += t(35, 82, "Measure it. Not 50 mm?\nPrinter scaled the page:\nreprint at 100 %.", 2.8, "middle", RED)
    s += line(10, 95, 60.8, 95, sw=0.6) + line(10, 93, 10, 97) + line(60.8, 93, 60.8, 97) + t(35, 100, "2 in = 50.8 mm", 2.8, "middle")

    # turret disc, top view, Y (toward the can) = up on the page
    cx, cy, r = 140, 78, P["turret_r"]
    s += circ(cx, cy, r, sw=0.5) + cross(cx, cy, 4)
    s += t(cx, cy - r - 4, "TURRET DISC  r 40 mm (cut 2, glue together)", 3.4, "middle", weight="bold")
    s += t(cx + 5, cy + 4, "MG996R horn centre:\nscrew the horn here", 2.6, color=RED)
    for sx in (-1, 1):                                             # rod positions
        x, y = cx + sx * P["rod_x"], cy - P["rod_y"]
        s += circ(x, y, P["rod_d"] / 2, BLUE, dash="1,0.8") + cross(x, y, 2, BLUE)
    s += t(cx, cy - P["rod_y"] + 9, "rods (marks only)", 2.5, "middle", BLUE)
    s += rect(cx - SPINE_W / 2, cy + 18, SPINE_W, 6, BLUE, dash="1.5,1") + t(cx, cy + 29, "spine glued here", 2.5, "middle", BLUE)
    s += t(cx, cy - 22, "▲ toward the can", 2.6, "middle", RED)

    # rod plates: x -26..26, y -24..20 (top view), holes at (+-17, 12)
    for i, (label, holes) in enumerate((("ROD PLATE, BOTTOM (cut 2, glue)", True), ("ROD PLATE, TOP (cut 2, glue)", True))):
        ox, oy = 40 + i * 90, 150
        s += rect(ox - 26, oy - 20, 52, 44, sw=0.5)
        s += t(ox, oy - 24, label, 3, "middle", weight="bold")
        for sx in (-1, 1):
            x, y = ox + sx * P["rod_x"], oy - P["rod_y"] + 12 - 12
            y = oy - P["rod_y"]
            s += circ(x, y, 3.0, sw=0.5) + cross(x, y, 2)
            s += t(x, y + 7, "Ø6", 2.5, "middle")
        s += rect(ox - SPINE_W / 2, oy + 18, SPINE_W, 6, BLUE, dash="1.5,1")
        s += t(ox, oy + 30, "spine edge here · rods 34 mm apart", 2.5, "middle", BLUE)
        s += cross(ox, oy, 2, GREY) + t(ox + 3, oy + 1, "axis", 2.2, color=GREY)
    s += t(10, 190, "Rods: push through the bottom plate, hot-glue, plates 112 mm apart (outer faces). Bottom plate glued onto the\n"
                    "turret disc with its axis cross on the disc's cross. Holes snug: start Ø5, open with the rod itself.", 2.8)

    # carriage block top/bottom: x -26..26, y 2..22, LM6UU bores 12 mm at (+-17, 12)
    ox, oy = 40, 215
    s += rect(ox - 26, oy, 52, 20, sw=0.5)
    for sx in (-1, 1):
        x, y = ox + sx * P["rod_x"], oy + 10
        s += circ(x, y, P["lm_od"] / 2, sw=0.5) + cross(x, y, 2)
    s += t(ox, oy - 4, "CARRIAGE ENDS (cut 2)", 3, "middle", weight="bold")
    s += t(ox - 26, oy + 26, "Ø12 holes for the LM6UU. Join the 2 ends\nwith foam-board sides 62 mm tall. LM6UU\nhot-glued in, + a zip tie each.", 2.6)

    # lift link + crank gauge
    lx, ly = 125, 208
    s += rect(lx, ly, LINK_HOLES + 8, 7, sw=0.5)
    s += cross(lx + 4, ly + 3.5, 2) + cross(lx + 4 + LINK_HOLES, ly + 3.5, 2)
    s += t(lx, ly - 4, f"LIFT LINK: holes {LINK_HOLES} mm apart", 3, weight="bold")
    s += t(lx, ly + 13, "popsicle stick, drill Ø3.5 (#6 screw pivot)", 2.6)
    gx, gy = 120, 248
    s += line(gx, gy, gx + P["lift_crank"], gy, sw=0.5) + cross(gx, gy, 2.5) + cross(gx + P["lift_crank"], gy, 2.5)
    s += t(gx - 2, gy - 5, "CRANK: horn centre → link hole = 20 mm", 3, weight="bold")
    s += t(gx - 2, gy + 6, "lay the lift servo's long horn on this,\nmark, drill Ø1.5 for a servo screw", 2.6)
    return s


def page2():
    s = header(2, "gauges + spine", "Cut out the strips and use them while gluing. Heights are measured from the TABLE.")
    # height gauge, vertical strip: z=0 at bottom
    x0, ybase = 20, 255
    zmax = P["rod_top"] + 5
    s += rect(x0, ybase - zmax, 16, zmax, sw=0.5)
    marks = [(P["base_h"], "base top 52"), (P["turret_z1"] - 1.8, "turret top 59 (line just above)"),
             (P["grip_z"], "WRIST AXIS 61.1 = can centre"), (P["car_z0"], "carriage bottom 69 (lift DOWN)"),
             (P["car_z0"] + P["lift_stroke"], "carriage bottom 84 (lift UP)"), (P["turret_z1"] + 2 + P["rod_len"] - 2, "rod top ~171"),
             (P["can_h"], "can top 122")]
    for z, lab in marks:
        y = ybase - z
        hot = "WRIST" in lab
        s += line(x0, y, x0 + 22, y, RED if hot else "#111", 0.6 if hot else 0.35)
        s += t(x0 + 24, y + 1, lab, 3 if hot else 2.6, color=RED if hot else "#111", weight="bold" if hot else "normal")
    for z in range(0, int(zmax), 10):
        s += line(x0, ybase - z, x0 + 4, ybase - z, sw=0.25) + t(x0 + 5, ybase - z + 1, str(z), 2, color=GREY)
    s += t(x0, ybase + 6, "HEIGHT GAUGE (stand it on the table)", 3, weight="bold")

    # reach gauge: 127 mm
    rx, ry = 68, 40
    s += rect(rx, ry, P["can_r_pos"] + 8, 10, sw=0.5)
    s += cross(rx + 4, ry + 5, 3) + cross(rx + 4 + P["can_r_pos"], ry + 5, 3)
    s += t(rx, ry - 4, "REACH GAUGE: turntable axis → can centre = 127 mm (5 in)", 3, weight="bold")
    s += t(rx, ry + 15, "Pin the left cross on the turntable axis; the right cross must land on the\ncan's centre when the claw holds it.", 2.6)

    # spine: SPINE_W wide x (rod_top - turret_z1) tall, lift servo pocket mark
    sh = P["rod_top"] - P["turret_z1"]
    sx, sy = 120, 255 - sh
    s += rect(sx, sy, SPINE_W, sh, sw=0.5)
    s += t(sx, sy - 4, f"SPINE (cut 2, glue)  {SPINE_W:.0f} × {sh:.0f} mm", 3, weight="bold")
    tip = P["lift_servo_tip"][2] - P["turret_z1"]                  # servo shaft height above the turret top
    s += cross(sx + SPINE_W / 2 - 3, 255 - tip, 3)
    s += rect(sx + SPINE_W / 2 - 9, 255 - tip - 6, 12, 23, BLUE, dash="1.5,1")
    s += t(sx + SPINE_W + 2, 255 - tip + 1, "lift servo shaft\n(MG90S body = blue,\nshaft at the top end)", 2.6, color=BLUE)
    s += t(sx + SPINE_W + 2, 252, "bottom edge glues on\nthe turret disc's\nspine mark", 2.6, color=BLUE)

    # arm stick length
    ay = 80
    arm = P["wrist_tip_y"] - P["car_y1"]
    s += line(90, ay, 90 + arm, ay, sw=0.8) + cross(90, ay, 2.5) + cross(90 + arm, ay, 2.5)
    s += t(90, ay - 4, f"ARM: carriage front → wrist servo face = {arm:.1f} mm", 3, weight="bold")
    s += t(90, ay + 6, "2 popsicle sticks glued as a sandwich, wrist servo hot-glued at the right end,\n"
                       "its shaft pointing at the can, shaft centre at the 61.1 mark when the lift is DOWN.", 2.6)
    return s


def page3():
    """Floor mat, rotated so the arc fits a portrait page: 'toward the can' points to the right."""
    s = header(3, "floor mat (turntable axis, START and TARGET circles)", "Tape this to the table. Robot axis on the cross; base box behind the line.")
    ax, ay = 40, 147                                       # axis on the page
    R, rc = P["can_r_pos"], P["can_d"] / 2
    g = ""
    # local frame: u = toward the can (page +x), v = sideways (page y)
    for a, lab in ((45, "CAN CIRCLE A"), (-45, "CAN CIRCLE B")):
        u, v = R * math.cos(math.radians(a)), R * math.sin(math.radians(a))
        g += circ(ax + u, ay - v, rc, sw=0.6) + cross(ax + u, ay - v, 4)
        g += t(ax + u, ay - v - 2, lab, 3.2, "middle", weight="bold") + t(ax + u, ay - v + 4, "Ø66 Coke can", 2.6, "middle")
    # 127 mm arc from -60 to +60
    pts = [(ax + R * math.cos(math.radians(a)), ay - R * math.sin(math.radians(a))) for a in range(-60, 61, 3)]
    g += '<polyline points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + f'" fill="none" stroke="{BLUE}" stroke-width="0.35" stroke-dasharray="2,1.2"/>'
    g += t(ax + R * 0.97 + 4, ay + 2, "r 127 mm (5 in)", 2.8, color=BLUE)
    g += cross(ax, ay, 6) + circ(ax, ay, 2, RED) + t(ax + 3, ay + 9, "TURNTABLE AXIS", 3, color=RED, weight="bold")
    # base front edge: 20 mm in front of the axis (toward the can)
    g += line(ax + 20, ay - 76, ax + 20, ay + 76, sw=0.6, dash="3,1.5")
    g += t(ax + 18, ay - 70, "base box front edge", 2.6, "end") + t(ax + 18, ay - 66, "(box behind = left)", 2.6, "end")
    g += line(ax, ay - 2, ax + 20, ay - 2, GREY, 0.25)
    s += g
    s += t(170, 162, "A and B are 90° apart.\nWhich one is START\ndepends on how the\nMG996R sits in the\nbox. With the panel:\nt 135 → tape START\non the circle the\nclaw points at;\nt 45 = TARGET.\n\nSame mat for Plan P\nand the printed robot.", 2.8)
    return s


def page4():
    """No-print claw, top view, 1:1. The wrist axis (Y) points up the page, through the can's centre."""
    s = header(4, "no-print claw (only if nothing can be printed)", "Top view, 1:1. One moving finger (SG90 horn + stick), one fixed finger. Pads: rubber band / inner tube, ~2 mm.")
    ox, oy = W / 2, 215                                    # wrist horn centre on the bar's back face
    rc = P["can_d"] / 2
    pad = 2.0
    can_y = oy - 60                                        # can centre 60 mm in front of the bar (= along the wrist axis)
    # cross bar (2 popsicle sticks / foam strip): x -55..55, 12 deep
    s += rect(ox - 62, oy - 12, 124, 12, sw=0.5) + t(ox, oy + 7, "CROSS BAR: foam board 124 × 12 (or 2 popsicle sticks)", 3, "middle", weight="bold")
    s += cross(ox, oy - 6, 4) + t(ox + 5, oy - 2, "wrist horn here (glue + 2 servo screws)", 2.5, color=RED)
    # can
    s += circ(ox, can_y, rc, RED, dash="2,1.2") + cross(ox, can_y, 4) + t(ox, can_y + 3, "can (Ø66)", 2.8, "middle", RED)
    s += line(ox, oy - 6, ox, can_y - rc - 8, RED, 0.25, "3,1.5") + t(ox + 2, can_y - rc - 4, "wrist axis = can centre line", 2.5, color=RED)
    # fixed finger (right): inner face at x = rc + pad
    fx = ox + rc + pad
    s += rect(fx, can_y - 45, 10, (oy - 12) - (can_y - 45), sw=0.5)
    s += rect(fx - pad, can_y - 25, pad, 50, BLUE, "#dbe6f7", 0.3)
    s += t(fx + 12, can_y - 10, "FIXED FINGER\n2 popsicle sticks,\nglued to the bar.\nPad (blue) on\nthe inside.", 2.6)
    # moving finger (left): SG90 shaft at the bar, stick swings about it
    shx, shy = ox - rc - pad - 6, oy - 18
    s += rect(shx - 17, shy - 6.1, 23, 12.2, BLUE, dash="1.5,1") + t(shx - 18, shy + 13, "SG90 body (glued on\ntop of the bar, shaft up)", 2.4, color=BLUE)
    s += cross(shx, shy, 3)
    closed_len = 85
    s += rect(shx - 5, shy - closed_len, 10, closed_len, sw=0.5)          # closed: along -page-y
    s += rect(shx + 5, can_y - 25, pad, 50, BLUE, "#dbe6f7", 0.3)
    s += t(shx - 7, can_y - 30, "MOVING FINGER\n(closed)\nstick glued\nto the SG90\nhorn", 2.6, "end")
    # open position, 75 deg away from the can
    a = math.radians(75)
    ex, ey = shx - 45 * math.sin(a), shy - 45 * math.cos(a)
    s += line(shx, shy, ex, ey, GREY, 0.6, "2,1.5") + t(ex - 2, ey - 2, "open (~75°)", 2.6, "end", GREY)
    s += t(10, 248, "The can sits between the pads, its centre on the wrist axis (red line). Closed: pads squeeze the can ~1 mm\n"
                    "each side. The SG90 angles will differ from the printed claw: set GRIP OPEN / CLOSED / RELEASE in the\n"
                    "control panel's calibration table, then Copy code into concept_a.ino.", 2.8)
    return s


def svg_page(body):
    return (f'<div class="pg"><svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            f'<rect width="{W}" height="{H}" fill="white"/>{body}</svg></div>')


def build_pdf(pages):
    html = ("<!doctype html><html><head><meta charset='utf-8'><style>@page{size:215.9mm 279.4mm;margin:0}"
            "body{margin:0}.pg{width:215.9mm;height:279.4mm;page-break-after:always;overflow:hidden}"
            ".pg:last-child{page-break-after:auto}svg{display:block}</style></head><body>" + "".join(svg_page(p) for p in pages)
            + "</body></html>")
    hpath = os.path.join(OUT, "_templates.html")
    with open(hpath, "w") as f:
        f.write(html)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium") if os.path.exists("/opt/pw-browsers/chromium") else pw.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + hpath)
        pg.pdf(path=os.path.join(OUT, "cut_templates.pdf"), width="215.9mm", height="279.4mm", print_background=True,
               margin=dict(top="0", bottom="0", left="0", right="0"), prefer_css_page_size=True)
        # preview: the 4 pages side by side
        prev = ("<!doctype html><html><body style='margin:0;background:#ddd;display:flex;gap:12px;padding:12px'>"
                + "".join(f"<div style='width:400px;background:white'>{svg_page(p).replace(f'width=\"{W}mm\" height=\"{H}mm\"', 'width=\"400\" height=\"518\"')}</div>"
                          for p in pages) + "</body></html>")
        pg.set_viewport_size({"width": 4 * 400 + 5 * 12, "height": 518 + 24})
        pg.set_content(prev)
        pg.screenshot(path=os.path.join(OUT, "templates_preview.png"))
        b.close()
    os.remove(hpath)


def build_zips():
    d = os.path.join(OUT, "print_service")
    os.makedirs(d, exist_ok=True)
    stl = os.path.join(ROOT, "cad", "print", "stl")
    sets = {"concept_a_all_parts_stl.zip": sorted(f for f in os.listdir(stl) if f.endswith(".stl")),
            "concept_a_claw_only_stl.zip": ["CA-401_gripper_frame.stl", "CA-402_finger_R.stl", "CA-403_finger_L.stl"]}
    for name, files in sets.items():
        with zipfile.ZipFile(os.path.join(d, name), "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                info = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0))      # fixed date: same zip every run
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(os.path.join(stl, f), "rb") as fh:
                    z.writestr(info, fh.read())
        print(f"wrote fallback_no_printer/print_service/{name} ({len(files)} STL)")


def main():
    os.makedirs(OUT, exist_ok=True)
    build_pdf([page1(), page2(), page3(), page4()])
    print("wrote fallback_no_printer/cut_templates.pdf + templates_preview.png")
    build_zips()


if __name__ == "__main__":
    main()
