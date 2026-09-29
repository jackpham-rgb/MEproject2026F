"""Concept-level CAD for Concept A (claw + wrist flip + turntable + lift), STEP + STL in mm.

    python3 cad/build_cad_concept_a.py     # needs: pip install cadquery

Frame (inches in this file, exported in mm): origin = turntable axis on the table (the robot's
location, the vertex in the assignment's Figure 2). +Y points to START, +X to TARGET, +Z up.
Robot shown in its home pose: arm pointing at START, lift down, wrist upright, arms open.

Groups in cad/out/concept_a/concept_a_assembly.step, one per moving stage, so Fusion 360 /
SolidWorks joints are easy (see cad/README.md):
  fixed    - base box, lazy-susan outer ring, turntable servo
  turret   - turntable plate, column, guide rods, lift servo           (revolute about Z)
  lift     - carriage, arm, wrist servo                                 (slider along Z, 0.6 in)
  wrist    - wrist hub, palm, gripper servo, arm_L, arm_R               (revolute about the radial Y line at z = 2.35)
  test_can - the can at START

Block-level solids only: correct envelopes and placement. Detail design (V-arm profile,
pivots, linkage, screw holes, fillets) is still to do in SolidWorks.
"""
import os

import cadquery as cq

MM = 25.4
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "concept_a")
os.makedirs(os.path.join(OUT, "parts"), exist_ok=True)

GRIP_Z = 2.35          # can mid-height
CAN_Y = 5.0            # can centre radius
OPEN_GAP = 2.9         # arms open


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box((x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM).translate(
        ((x0 + x1) / 2 * MM, (y0 + y1) / 2 * MM, (z0 + z1) / 2 * MM))


def cyl_z(x, y, r, z0, z1, r_in=0.0):
    w = cq.Workplane("XY").workplane(offset=z0 * MM).center(x * MM, y * MM).circle(r * MM)
    if r_in:
        w = w.circle(r_in * MM)
    return w.extrude((z1 - z0) * MM)


def cyl_y(x, z, r, y0, y1):
    return cq.Workplane("XZ").workplane(offset=-y0 * MM).center(x * MM, z * MM).circle(r * MM).extrude(-(y1 - y0) * MM)


PARTS = {
    "fixed": {
        "base_box": (box(-3.0, 3.0, -3.0, 3.0, 0.0, 1.0), "#c9ccd2"),       # stays 3.55 in from both cans
        "lazy_susan_ring": (cyl_z(0, 0, 1.75, 1.0, 1.15, r_in=1.2), "#8a8f98"),
        "turntable_servo_MG996R": (box(-0.8, 0.8, -0.4, 0.4, 0.1, 0.95), "#2b2f36"),
    },
    "turret": {
        "turntable_plate": (cyl_z(0, 0, 1.8, 1.15, 1.35), "#9aa0aa"),
        "column": (box(-0.45, 0.45, -0.45, 0.45, 1.35, 4.3), "#9aa0aa"),
        "guide_rod_L": (cyl_z(-0.35, 0.6, 0.118, 1.35, 4.2), "#b8bcc2"),      # 6 mm steel rods
        "guide_rod_R": (cyl_z(0.35, 0.6, 0.118, 1.35, 4.2), "#b8bcc2"),
        "lift_servo_MG90S": (box(-0.25, 0.25, -0.95, -0.45, 3.3, 4.2), "#2b2f36"),
    },
    "lift": {
        "carriage": (box(-0.6, 0.6, 0.45, 1.1, GRIP_Z - 0.8, GRIP_Z + 0.8), "#3d7be0"),   # LM6UU pair inside, 1.6 in apart
        "arm": (box(-0.25, 0.25, 1.1, 2.65, GRIP_Z - 0.175, GRIP_Z + 0.175), "#3d7be0"),
        "wrist_servo": (box(-0.25, 0.25, 2.65, 3.35, GRIP_Z - 0.45, GRIP_Z + 0.45), "#2b2f36"),
    },
    "wrist": {
        "wrist_hub": (cyl_y(0, GRIP_Z, 0.3, 3.35, 3.5), "#50555e"),
        "palm": (box(-1.6, 1.6, 3.5, 3.7, GRIP_Z - 0.4, GRIP_Z + 0.4), "#3d7be0"),   # 0.1 in clear of the can
        "gripper_servo": (box(-0.45, 0.45, 3.5, 3.7, GRIP_Z + 0.4, GRIP_Z + 1.0), "#2b2f36"),
        "arm_L": (box(-OPEN_GAP / 2 - 0.2, -OPEN_GAP / 2, 3.5, 5.9, GRIP_Z - 0.3, GRIP_Z + 0.3), "#e0a33d"),
        "arm_R": (box(OPEN_GAP / 2, OPEN_GAP / 2 + 0.2, 3.5, 5.9, GRIP_Z - 0.3, GRIP_Z + 0.3), "#e0a33d"),
    },
}


def colour(h):
    h = h.lstrip("#")
    return cq.Color(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


top = cq.Assembly(name="concept_a")
count = 0
for group, parts in PARTS.items():
    g = cq.Assembly(name=group)
    for name, (solid, col) in parts.items():
        g.add(solid, name=name, color=colour(col))
        cq.exporters.export(solid, os.path.join(OUT, "parts", name + ".step"))
        cq.exporters.export(solid, os.path.join(OUT, "parts", name + ".stl"))
        count += 1
    top.add(g, name=group)
can = cyl_z(0, CAN_Y, 1.2, 0, 4.7)
top.add(can, name="test_can", color=cq.Color(0.75, 0.1, 0.12))
cq.exporters.export(can, os.path.join(OUT, "parts", "test_can.step"))
top.save(os.path.join(OUT, "concept_a_assembly.step"))
print(f"wrote {count} parts + can + assembly to {OUT}")
