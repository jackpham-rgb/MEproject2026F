"""Generate concept-level CAD (STEP + STL, millimetres) from sim/out/mechanism.json.

    python3 sim/mechanism.py && python3 cad/build_cad.py

Outputs in cad/out/:
  can_flipper_assembly.step  - whole robot at theta = 0, with the can at START.
                               Two top-level groups: 'fixed' (base, tower, motor,
                               home post) and 'flip_arm' (everything that rotates).
  parts/*.step, parts/*.stl  - one file per part, placed in assembly coordinates.

These are block-level concept solids for the PDR (correct envelope, placement and
motion). They are NOT the detail design: fillets, fastener holes, the V-jaw profile
and the servo linkage still have to be modelled in SolidWorks/Fusion.
"""
import json
import math
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 25.4
M = json.load(open(os.path.join(HERE, "..", "sim", "out", "mechanism.json")))
H, F = M["axis_height"], M["axis_point_xy"]
OUT = os.path.join(HERE, "out")
os.makedirs(os.path.join(OUT, "parts"), exist_ok=True)


def solid(part):
    ds, dt, dw = (part[k][1] - part[k][0] for k in ("s", "t", "w"))
    sc, tc, wc = (sum(part[k]) / 2 for k in ("s", "t", "w"))
    if part["kind"] == "cyl_s":
        body = cq.Workplane("YZ").circle(dt / 2 * MM).extrude(ds * MM).translate((-ds / 2 * MM, 0, 0))
    else:
        body = cq.Workplane("XY").box(ds * MM, dt * MM, dw * MM)
    # local (s, t, w) -> world: s along the 45 deg axis, t along u = 135 deg, w up
    body = body.translate((sc * MM, tc * MM, wc * MM)).rotate((0, 0, 0), (0, 0, 1), 45)
    return body.translate((F[0] * MM, F[1] * MM, H * MM))


def colour(hexstr):
    h = hexstr.lstrip("#")
    return cq.Color(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


fixed, arm = cq.Assembly(name="fixed"), cq.Assembly(name="flip_arm")
for group, parts in ((fixed, M["static"]), (arm, M["moving"])):
    for p in parts:
        s = solid(p)
        group.add(s, name=p["name"], color=colour(p["color"]))
        cq.exporters.export(s, os.path.join(OUT, "parts", p["name"] + ".step"))
        cq.exporters.export(s, os.path.join(OUT, "parts", p["name"] + ".stl"))

can = (cq.Workplane("XY").circle(M["can"]["r"] * MM).extrude(M["can"]["h"] * MM)
       .translate((M["start_xy"][0] * MM, M["start_xy"][1] * MM, 0)))
cq.exporters.export(can, os.path.join(OUT, "parts", "test_can.step"))

top = cq.Assembly(name="can_flipper")
top.add(fixed, name="fixed")
top.add(arm, name="flip_arm")
top.add(can, name="test_can", color=cq.Color(0.75, 0.1, 0.12))
top.save(os.path.join(OUT, "can_flipper_assembly.step"))
print("wrote", len(M["static"]) + len(M["moving"]) + 1, "parts + assembly to", OUT)
