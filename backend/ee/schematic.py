"""Concept A circuit as a standard schematic (symbols + net labels, the way SPICE / LTspice schematics look).

    python3.13 backend/ee/schematic.py      -> docs/wiring/schematic.svg (+ .png via the docs renderer)

Same connections as docs/04_wiring.md (Wire list) and firmware/concept_a/concept_a.ino.
Nets with the same name are connected (+12V, +5V8, VIN, D4 ... D13). Every ground symbol is the same GND.
"""
import os

import schemdraw
import schemdraw.elements as elm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "wiring")
DIR = {"right": 0, "up": 90, "left": 180, "down": 270}


def stub_label(d, at, name, side, length=0.8, color="#1a4fa0"):
    """Wire stub from `at` and a net label at its end."""
    ln = d.add(elm.Line().at(at).theta(DIR[side]).length(length))
    loc = {"right": "right", "left": "left", "up": "top", "down": "bottom"}[side]
    d.add(elm.Label().at(ln.end).label(name, loc=loc, color=color, fontsize=12))
    return ln.end


def stub_gnd(d, at, side, length=0.6):
    ln = d.add(elm.Line().at(at).theta(DIR[side]).length(length))
    d.add(elm.Ground().at(ln.end))


def main():
    os.makedirs(OUT, exist_ok=True)
    schemdraw.config(fontsize=12, lw=1.4)
    with schemdraw.Drawing(show=False) as d:
        d.add(elm.Label().at((0, 3.2)).label("ME 2331 Project 2 · Concept A schematic", fontsize=17, halign="left"))
        d.add(elm.Label().at((0, 2.5)).label("Net labels with the same name are connected; every ground symbol is the same GND (servo GND and Uno GND joined).",
                                             fontsize=11, halign="left", color="#555"))

        # ---- block 1: servo power, 12 V adapter -> XL4015 -> +5V8 rail with C1
        d.add(elm.Label().at((0, 1.4)).label("SERVO POWER", fontsize=12, halign="left", color="#888"))
        v1 = d.add(elm.SourceV().at((1, -3)).up().length(3))
        d.add(elm.Label().at((0.4, -1.5)).label("V1\n12 V 2 A\nadapter", halign="right", fontsize=12))
        d.add(elm.Ground().at(v1.start))
        buck = d.add(elm.Ic(pins=[elm.IcPin(name="IN+", side="L", slot="2/2"), elm.IcPin(name="IN−", side="L", slot="1/2"),
                                  elm.IcPin(name="OUT+", side="R", slot="2/2"), elm.IcPin(name="OUT−", side="R", slot="1/2")],
                             size=(3.2, 2.4), pinspacing=1.2, label="U2  XL4015\nbuck, set 5.8 V").theta(0).at((4.5, -2.4)))
        d.add(elm.Line().at(v1.end).to((v1.end[0], buck["IN+"][1])))
        d.add(elm.Line().to(buck["IN+"]))
        stub_label(d, (v1.end[0], buck["IN+"][1]), "+12V", "up", 0.6)
        stub_gnd(d, buck["IN−"], "down", 0.8)
        r = d.add(elm.Line().at(buck["OUT+"]).right(1.6)); d.add(elm.Dot())
        rail = r.end
        stub_label(d, rail, "+5V8", "up", 0.6)
        stub_gnd(d, buck["OUT−"], "down", 0.8)
        c1 = d.add(elm.Capacitor(polar=True).at(rail).down().length(2.2).label("C1  1000 µF ≥10 V\n(− stripe to GND;\noptional while testing)", loc="bottom", ofst=0.2))
        d.add(elm.Ground().at(c1.end))

        # ---- block 2: Uno power, 9 V battery
        d.add(elm.Label().at((0, -6.6)).label("UNO POWER", fontsize=12, halign="left", color="#888"))
        b1 = d.add(elm.BatteryCell().at((1, -11)).up().length(2.4))
        d.add(elm.Label().at((0.4, -9.8)).label("BT1\n9 V battery\n(Uno only)", halign="right", fontsize=12))
        d.add(elm.Ground().at(b1.start))
        stub_label(d, b1.end, "VIN", "up", 0.6)
        d.add(elm.Label().at((0.2, -12.6)).label("clip → barrel plug into the Uno jack\n(or + to VIN, − to GND)", fontsize=10, halign="left", color="#555"))

        # ---- block 3: Arduino Uno with button and LED
        pins = [elm.IcPin(name="VIN", side="L", slot="2/2"), elm.IcPin(name="GND", side="L", slot="1/2")]
        pins += [elm.IcPin(name=f"D{n}", side="R", slot=f"{6 - i}/6") for i, n in enumerate((4, 5, 6, 9, 10, 13))]
        uno = d.add(elm.Ic(pins=pins, size=(3.6, 6.0), pinspacing=1.0, label="U1\nArduino\nUno R3").theta(0).at((8.5, -13.2)))
        stub_label(d, uno["VIN"], "VIN", "left")
        stub_gnd(d, uno["GND"], "left", 0.8)
        for n in (5, 6, 9, 10):
            stub_label(d, uno[f"D{n}"], f"D{n}", "right", 1.0)
        # D4 -> S1 -> GND (INPUT_PULLUP)
        d.add(elm.Line().at(uno["D4"]).right(1.0))
        d.add(elm.Button().right().length(2.0).label("S1 START\n(INPUT_PULLUP)", loc="top"))
        d.add(elm.Line().right(0.4)); d.add(elm.Ground())
        # D13 -> R1 -> LED -> GND
        d.add(elm.Line().at(uno["D13"]).right(1.0))
        d.add(elm.Resistor().right().length(2.0).label("R1 220 Ω", loc="bottom"))
        d.add(elm.LED().right().length(1.8).label("D1 status", loc="bottom"))
        d.add(elm.Line().right(0.4)); d.add(elm.Ground())

        # ---- block 4: servos (3-pin plugs)
        d.add(elm.Label().at((17.2, 1.4)).label("SERVOS (plug: brown −, red +, orange SIG)", fontsize=12, halign="left", color="#888"))
        servos = [("M1", "MG996R\nturntable", "D9", "+5V8*"), ("M2", "MG90S\nlift", "D10", "+5V8"),
                  ("M3", "MG90S\nwrist", "D6", "+5V8"), ("M4", "SG90\ngripper", "D5", "+5V8")]
        for i, (ref, name, sig, pwr) in enumerate(servos):
            s = d.add(elm.Ic(pins=[elm.IcPin(name="+", side="L", slot="3/3"), elm.IcPin(name="SIG", side="L", slot="2/3"),
                                   elm.IcPin(name="−", side="L", slot="1/3")],
                             size=(2.6, 2.4), pinspacing=0.8).theta(0).at((20.5, -2.0 - i * 3.6)))
            d.add(elm.Label().at((s["SIG"][0] + 2.1, s["SIG"][1])).label(f"{ref}\n{name}", fontsize=12))
            stub_label(d, s["+"], pwr, "left", 1.2)
            stub_label(d, s["SIG"], sig, "left", 1.2, color="#c06000")
            stub_gnd(d, s["−"], "down", 0.5)
        d.add(elm.Label().at((17.2, -15.4)).label("* M1 + / − go straight to the buck OUT terminals,\n  not through the breadboard (2.5 A stall).",
                                                  fontsize=10, halign="left", color="#555"))
        d.save(os.path.join(OUT, "schematic.svg"))
    print("wrote docs/wiring/schematic.svg")


if __name__ == "__main__":
    main()
