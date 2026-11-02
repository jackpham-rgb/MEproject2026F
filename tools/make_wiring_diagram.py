"""Draw the Concept A wiring diagram (breadboard style, like Fritzing) -> docs/wiring/wiring_diagram.svg

    python3 tools/make_wiring_diagram.py

Pins match firmware/concept_a/concept_a.ino. Wire colours follow hobby convention:
red = + power, black = ground, orange = servo signal, other colours = logic signals.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "wiring")
os.makedirs(OUT, exist_ok=True)

W, H = 1500, 960
el = []


def rect(x, y, w, h, fill, stroke="#333", rx=6, sw=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=14, fill="#1a1e24", anchor="start", weight="400", family="Helvetica, Arial, sans-serif"):
    el.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def wire(pts, color, w=4, dash=None):
    d = " ".join(f"{x},{y}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    el.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{da}/>')


def dot(x, y, color="#333", r=5):
    el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')


def pin(x, y, label, below=True):
    rect(x - 7, y - 7, 14, 14, "#2b2b2b", "#111", rx=2, sw=1)
    text(x, y + (24 if below else -14), label, 12, "#ffffff", "middle", "600")


RED, BLK, ORG, GRN, BLU, YEL, PUR, CYN = "#d7261e", "#1b1b1b", "#f08a00", "#1f9d55", "#2f6fdb", "#e2b100", "#8e44ad", "#16a6b6"

# ---------------- title ----------------
text(30, 42, "ME 2331 Project 2 · Concept A wiring", 26, weight="700")
text(30, 68, "Arduino Uno + 4 servos on one 5 V, 4 A wall adapter. The adapter feeds the servo rail; the rail feeds the Uno 5V pin. All grounds are joined.", 15, "#4a5563")

# ---------------- DC jack (5 V adapter, no regulator needed) ----------------
rect(40, 120, 190, 90, "#e9edf2")
text(135, 150, "DC jack", 16, anchor="middle", weight="700")
text(135, 172, "5 V, 4 A regulated", 13, "#4a5563", "middle")
text(135, 192, "wall adapter", 13, "#4a5563", "middle")
jack_p, jack_n = (230, 140), (230, 190)
dot(*jack_p, RED); dot(*jack_n, BLK)
text(60, 300, "No buck converter: the adapter", 12, "#4a5563")
text(60, 316, "already gives the 5 V that the", 12, "#4a5563")
text(60, 332, "servos and the Uno need.", 12, "#4a5563")

# ---------------- servo power rails (mini breadboard) ----------------
rx0, rx1 = 520, 1440
rect(rx0, 250, rx1 - rx0, 70, "#f4f1e8", "#c9c3b3", rx=8)
wire([(rx0 + 15, 268), (rx1 - 15, 268)], RED, 3)
wire([(rx0 + 15, 302), (rx1 - 15, 302)], BLU, 3)
text(rx0 + 18, 262, "+5 V rail", 12, RED, weight="600")
text(rx0 + 18, 318, "GND rail", 12, BLU, weight="600")
for x in range(rx0 + 30, rx1 - 20, 20):
    dot(x, 268, "#9b9583", 2.5); dot(x, 302, "#9b9583", 2.5)
wire([jack_p, (490, 140), (490, 268), (rx0 + 30, 268)], RED)
wire([jack_n, (480, 190), (480, 302), (rx0 + 30, 302)], BLK)
# capacitor
rect(600, 272, 34, 26, "#2a3f6e", "#111", rx=4, sw=1)
text(617, 289, "C", 12, "#fff", "middle", "700")
text(270, 254, "C = 1000 µF ≥10 V on the servo rail", 12, "#4a5563")
text(270, 270, "(− leg to GND)", 12, "#4a5563")
wire([(610, 268), (610, 272)], RED, 3); wire([(624, 298), (624, 302)], BLK, 3)

# ---------------- servos ----------------
servos = [("Lift", "MG90S", 10, 760), ("Turntable", "MG996R", 9, 960), ("Wrist", "MG90S", 6, 1160), ("Gripper", "SG90", 5, 1340)]
uno_x, uno_y, uno_w, uno_h = 300, 520, 560, 300
# Uno header: digital pins along the top edge, D13 left ... D0 right (as on the board)
dpin = {n: (uno_x + 70 + (13 - n) * 34, uno_y + 34) for n in range(14)}
for name, model, d, x in servos:
    rect(x - 70, 110, 140, 90, "#1f2329", "#000")
    text(x, 140, name, 16, "#ffffff", "middle", "700")
    text(x, 160, model, 12, "#c9d1da", "middle")
    text(x, 180, f"signal → D{d}", 12, "#f6b26b", "middle")
    sx_b, sx_r, sx_o = x - 30, x, x + 30
    for xx, c in ((sx_b, "#6b3b16"), (sx_r, RED), (sx_o, ORG)):
        wire([(xx, 200), (xx, 236)], c, 4)
    wire([(sx_b, 236), (sx_b, 302)], BLK, 4); dot(sx_b, 302, BLK, 4)
    wire([(sx_r, 236), (sx_r, 268)], RED, 4); dot(sx_r, 268, RED, 4)
    lane = 360 + servos.index((name, model, d, x)) * 22
    px, py = dpin[d]
    wire([(sx_o, 236), (sx_o + 12, 236), (sx_o + 12, lane), (px, lane), (px, py)], ORG, 4)
text(690, 96, "servo plug: brown = GND · red = + · orange = signal · 300 mm extension leads for lift, wrist, gripper", 12, "#4a5563")

# ---------------- Arduino Uno ----------------
rect(uno_x, uno_y, uno_w, uno_h, "#0f7c8c", "#0a5560", rx=14)
text(uno_x + uno_w / 2, uno_y + 150, "Arduino Uno R3", 26, "#ffffff", "middle", "700")
text(uno_x + uno_w / 2, uno_y + 178, "firmware/concept_a/concept_a.ino", 14, "#d4f1f4", "middle", family="Menlo, monospace")
for n, (x, y) in dpin.items():
    pin(x, y, f"D{n}")
apins = {"VIN": (uno_x + 110, uno_y + uno_h - 34), "GND": (uno_x + 160, uno_y + uno_h - 34),
         "5V": (uno_x + 210, uno_y + uno_h - 34), "A0": (uno_x + 330, uno_y + uno_h - 34)}
for lbl, (x, y) in apins.items():
    pin(x, y, lbl, below=False)
rect(uno_x - 26, uno_y + 60, 40, 46, "#b8bcc2", "#555", rx=3, sw=1)
text(uno_x + 22, uno_y + 88, "USB", 11, "#d4f1f4")

# Uno power from the jack (VIN) and the common ground
wire([jack_p, (250, 140), (250, 100), (20, 100), (20, 905), (apins["5V"][0], 905), apins["5V"]], RED)
wire([jack_n, (258, 190), (258, 230), (32, 230), (32, 920), (apins["GND"][0], 920), apins["GND"]], BLK)
wire([(rx1 - 15, 302), (rx1 - 15, 470), (uno_x + uno_w + 40, 470), (uno_x + uno_w + 40, 930),
      (apins["GND"][0] + 8, 930), (apins["GND"][0] + 8, apins["GND"][1])], BLK, 3)
text(uno_x + uno_w + 48, 560, "common GND", 12, "#1b1b1b")
text(apins["GND"][0] - 14, 898, "Uno 5V ← adapter +", 12, RED, "end", "600")

# ---------------- start button, LED ----------------
bx, by = 1010, 600
rect(bx, by, 120, 70, "#e9edf2")
el.append(f'<circle cx="{bx + 60}" cy="{by + 35}" r="18" fill="#2f2f2f"/>')
text(bx + 60, by + 92, "START button (12 mm)", 13, anchor="middle", weight="600")
px, py = dpin[4]
wire([(px, py), (px, 470), (bx + 30, 470), (bx + 30, by)], GRN)
wire([(bx + 118, by + 50), (bx + 140, by + 50), (bx + 140, 930), (uno_x + uno_w + 40, 930)], BLK, 3)
text(bx + 60, by + 110, "D4 → button → GND", 12, "#4a5563", "middle")
text(bx + 60, by + 126, "(INPUT_PULLUP)", 12, "#4a5563", "middle")

lx, ly = 1300, 600
el.append(f'<circle cx="{lx + 30}" cy="{ly + 20}" r="14" fill="#f2c94c" stroke="#333" stroke-width="2"/>')
text(lx + 52, ly + 25, "status LED (D13)", 13, weight="600")
rect(lx + 18, ly + 70, 24, 50, "#d9c7a4", "#555", rx=4, sw=1)
text(lx + 50, ly + 100, "220 Ω", 12, "#4a5563")
px, py = dpin[13]
wire([(px, py), (px, 490), (lx + 30, 490), (lx + 30, ly + 6)], YEL)
wire([(lx + 30, ly + 34), (lx + 30, ly + 70)], "#333", 3)
wire([(lx + 30, ly + 120), (lx + 30, 930), (bx + 140, 930)], BLK, 3)

# ---------------- upload rule ----------------
rect(50, 640, 210, 120, "#fff7e0", "#e2b100", sw=2)
text(155, 666, "Uploading code", 14, "#7a5b00", "middle", "700")
text(155, 690, "Unplug the 5 V adapter", 12, "#4a5563", "middle")
text(155, 708, "before plugging in USB:", 12, "#4a5563", "middle")
text(155, 726, "both feed the Uno's 5 V.", 12, "#4a5563", "middle")
text(155, 748, "Run on the adapter only.", 12, "#4a5563", "middle", "600")

# legend
lg = [(RED, "+ power"), (BLK, "ground"), (ORG, "servo signal"), (GRN, "button"), (YEL, "LED")]
for i, (c, s) in enumerate(lg):
    x = 960 + (i % 4) * 130
    y = 30 + (i // 4) * 24
    wire([(x, y), (x + 30, y)], c, 4)
    text(x + 38, y + 5, s, 13)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + "".join(el) + "</svg>")
open(os.path.join(OUT, "wiring_diagram.svg"), "w").write(svg)
print("wrote docs/wiring/wiring_diagram.svg")
