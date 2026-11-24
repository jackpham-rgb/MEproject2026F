"""Plan B in 3D (docs/20_fallback_buy_or_service.md): a wooden base and the repaired carriage arm, as a step-by-step
guide in the same viewer as the real assembly.

    python3.13 backend/cad/planb.py   ->  viewer/data/planb.json   (open viewer/assembly.html?data=planb)

The wooden base keeps every height of the printed base, so the bearing, the turntable servo and the whole column sit
exactly where the CAD has them:
  top board  1/4" (6.35 mm) plywood, 1-7/8" (47.6 mm) hole: the 6807 (47.0 x 7) drops in, 0.65 mm proud
  bottom board 1/2" (12.7 mm): the pocket floor (= the bearing's underside, z 45); the MG996R comes up through a slot
             and its tabs screw to the underside, with washers (~1.2 mm) as spacers
  4 legs     1-1/2" (38 mm) square blocks, 32.3 mm tall; a sandbag under the bottom board between the front legs
The carriage repair: epoxy in the crack + a 1/2" steel corner brace on top of the arm and up the carriage's front face,
4 x #6 x 1/4" pointed screws (the arm's top is the side in tension, where the brace helps most).
Checked here: no wooden part or the brace overlaps a robot part at home or with the carriage raised 15 mm.
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import visual as V  # noqa: E402

OUT = os.path.join(ROOT, "viewer", "data", "planb.json")
WOOD, STEEL, SAND = "#c8a46a", "#9aa1a9", "#b9a27a"
IN = 25.4


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def templates(outline_wires, hole_d, slots, blocks, sand_xy, path):
    """1:1 cutting templates (US Letter landscape, print at 100 % / "actual size"): page 1 top board, 2 bottom board,
    3 floor board. Each page has a 50 mm check bar: measure it after printing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    W, H = 279.4, 215.9
    def ring(w):
        pts = [w.positionAt(i / 600) for i in range(601)]          # along the wire, in order
        return [p.x for p in pts], [p.y for p in pts]
    pages = [("TOP board: 1/4\" (6 mm) plywood. Drill the hole with a 1-7/8\" (47.6 mm) hole saw", "top"),
             ("BOTTOM board: 1/2\" (12 mm) plywood. Cut the servo slot (drill the corners, saw, file)", "bottom"),
             ("FLOOR board: 1/2\" (12 mm) plywood. Servo slot + 3 spacer blocks (3/4\" wood, 30 x 30) + sandbag", "floor")]
    with PdfPages(path) as pdf:
        for title, kind in pages:
            fig = plt.figure(figsize=(W / IN, H / IN))
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_xlim(-W / 2, W / 2); ax.set_ylim(-H / 2 - 20, H / 2 - 20); ax.axis("off")
            for w in outline_wires:
                xs, ys = ring(w)
                if kind == "floor":
                    ys = [max(y, -66) for y in ys]
                ax.plot(xs, ys, color="k", lw=1.4)
            ax.plot([-6, 6], [0, 0], "k", lw=0.8); ax.plot([0, 0], [-6, 6], "k", lw=0.8)       # hole centre
            if kind == "top":
                t = [i / 90 * 2 * math.pi for i in range(91)]
                ax.plot([hole_d / 2 * math.cos(a) for a in t], [hole_d / 2 * math.sin(a) for a in t], color="#c00000", lw=1.4)
                ax.text(0, -hole_d / 2 - 6, f"hole {hole_d} mm (1-7/8\")", ha="center", va="top", color="#c00000", fontsize=9)
            else:
                c = slots[0 if kind == "bottom" else 1]
                ax.fill([p[0] for p in c], [p[1] for p in c], color="#c00000", alpha=0.25)
                ax.plot([p[0] for p in c] + [c[0][0]], [p[1] for p in c] + [c[0][1]], color="#c00000", lw=1.4)
                ax.text(sum(p[0] for p in c) / 4, sum(p[1] for p in c) / 4, "CUT OUT\n(servo)", ha="center", va="center", color="#c00000", fontsize=8)
                ax.text(0, 8, "+ = bearing centre\n(spline goes here)", ha="center", va="bottom", fontsize=7)
            if kind == "floor":
                for (bx, by) in blocks:
                    ax.plot([bx - 15, bx + 15, bx + 15, bx - 15, bx - 15], [by - 15, by - 15, by + 15, by + 15, by - 15], color="#7a5a20", lw=1)
                    ax.text(bx, by, "block", ha="center", va="center", fontsize=7, color="#7a5a20")
                sx, sy = sand_xy
                ax.plot([sx[0], sx[1], sx[1], sx[0], sx[0]], [sy[0], sy[0], sy[1], sy[1], sy[0]], color="#7a5a20", lw=1, ls="--")
                ax.text(sum(sx) / 2, sum(sy) / 2, "sandbag", ha="center", va="center", fontsize=7, color="#7a5a20")
            ax.text(0, -84, "FRONT (tray side)", ha="center", va="top", fontsize=9, fontweight="bold")
            ax.text(-W / 2 + 8, H / 2 - 28, title, fontsize=10, fontweight="bold", va="top")
            ax.text(-W / 2 + 8, H / 2 - 36, "Print at 100 % (actual size). Check the bar = 50 mm. Tape it on the board, cut along the black line.",
                    fontsize=8, va="top")
            ax.plot([-W / 2 + 10, -W / 2 + 60], [-H / 2 - 10, -H / 2 - 10], "k", lw=3)
            ax.text(-W / 2 + 35, -H / 2 - 7, "50 mm", ha="center", va="bottom", fontsize=8)
            pdf.savefig(fig); plt.close(fig)


def main():
    P = M.P
    parts = {p["name"]: p for p in M.build_parts()}
    meshes, screws, glue, _ = V.build()
    drop_owner = {"base", "ballast"}
    drop = {x["name"] for x in screws if x["owner"] in ("turntable_horn", "wrist_horn") and x["kind"] == "M3"} | \
           {x["name"] for x in screws if x["owner"] == "electronics_tray"}
    screws = [x for x in screws if x["name"] not in drop]
    glue = [g for g in glue if g["owner"] not in drop_owner]
    meshes = [m for m in meshes if m["owner"] not in drop and m["owner"] not in drop_owner and m["owner"] not in {g for g in ()}
              and not (m["kind"] == "glue" and m["owner"] not in {g["name"] for g in glue})]

    # ---- the wooden base (same footprint as the printed one: x +-76, y -76..36)
    x0, x1, y0, y1 = -76, 76, -76, 36
    zb_top = 45.0                                   # bearing underside = pocket floor
    # board outline = the printed base's outline seen from above (it has a cut-out corner the wrist swings through)
    bsol = parts["base"]["shape"].val()
    sl = bsol.intersect(box(-200, 200, -200, 200, 51.0, 51.5).val())
    tops = [f for f in sl.Faces() if f.normalAt().z > 0.9 and abs(f.Center().z - 51.5) < 0.05]
    outline = [cq.Face.makeFromWires(f.outerWire()) for f in tops]
    def slab(z0, z1):
        sol = None
        for f in outline:
            e = cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0)).translate(cq.Vector(0, 0, z0 - 51.5))
            sol = e if sol is None else sol.fuse(e)
        return cq.Workplane("XY").add(sol)
    top = slab(zb_top, zb_top + IN / 4).cut(
        cq.Workplane("XY").circle(47.6 / 2).extrude(20).translate((0, 0, zb_top - 5)))
    zb0 = zb_top - IN / 2                           # bottom board 32.3 .. 45
    srv = parts["turntable_servo_MG996R"]["shape"].val()
    ang = P["servo_ang"]
    # the servo body where it passes the bottom board, measured in the servo's own frame -> slot = that + 1 mm
    loc = srv.rotate((0, 0, 0), (0, 0, 1), -ang)
    sec = loc.intersect(box(-200, 200, -200, 200, zb0 + 0.5, zb_top - 0.5).val()).BoundingBox()
    slot_l = box(sec.xmin - 1, sec.xmax + 1, sec.ymin - 1, sec.ymax + 1, zb0 - 1, zb_top + 1).val()
    slot = slot_l.rotate((0, 0, 0), (0, 0, 1), ang)
    bottom = slab(zb0, zb_top).cut(cq.Workplane("XY").add(slot))
    sc = slot.Center()
    slot_txt = (f"slot {sec.xmax - sec.xmin + 2:.0f} × {sec.ymax - sec.ymin + 2:.0f} mm, at {ang - 180:.0f}° (diagonal); "
                f"its centre {math.hypot(sc.x, sc.y):.0f} mm from the hole centre")
    # floor board (same outline, front edge trimmed so the tray slides under) with a slot for the servo's lower end,
    # 3 spacer blocks (3/4" wood = 19 mm, here 19.6) between floor and bottom board: the footprint stays the printed
    # base's, so the tip-over margin is the same
    zf = IN / 2
    sec2 = loc.intersect(box(-200, 200, -200, 200, 0.2, zf - 0.2).val()).BoundingBox()
    slot2 = box(sec2.xmin - 1, sec2.xmax + 1, sec2.ymin - 1, sec2.ymax + 1, -1, zf + 1).val().rotate((0, 0, 0), (0, 0, 1), ang)
    floor = slab(0, zf).cut(cq.Workplane("XY").add(slot2)).cut(box(-200, 200, -200, -66, -1, zf + 1))
    legs = [floor] + [box(x - 15, x + 15, y - 15, y + 15, zf, zb0) for x, y in ((-58, -48), (42, -50), (-60, 15))]
    sand = box(-20, 20, -64, -40, zf, zf + 18)
    # ---- carriage repair: 1/2" steel corner brace, 1.6 mm thick, on top of the arm + up the carriage's front face
    cz0, cy1, bt = P["car_z0"], P["car_y1"], P["beam_t"]
    by1 = P["wrist_tip_y"] - 28.5 + 15.9
    ztop = cz0 + bt
    brace = box(-IN / 4, IN / 4, cy1, by1 - 0.4, ztop, ztop + 1.6).union(box(-IN / 4, IN / 4, cy1, cy1 + 1.6, ztop, ztop + 38))

    new_parts = {"wood_top": top, "wood_bottom": bottom, "sandbag": sand, "brace": brace}
    for i, l in enumerate(legs):
        new_parts[f"leg_{i + 1}"] = l

    # ---- checks: nothing new overlaps a robot part (home pose; brace also with the carriage up 15 mm)
    robot = {n: p["shape"].val() for n, p in parts.items() if n not in ("base", "test_can") and p["group"] != "coupon"}
    rep = []
    for n, s in new_parts.items():
        sv = s.val()
        for o, os_ in robot.items():
            for dz in ((0, 15) if n == "brace" else (0,)):
                if n == "brace" and parts[o]["group"] in ("lift", "wrist", "finger_L", "finger_R"):
                    if dz:
                        continue                          # moves with the carriage
                    v = sv.intersect(os_).Volume()
                elif n == "brace":
                    v = sv.translate((0, 0, dz)).intersect(os_).Volume()
                else:
                    v = sv.intersect(os_).Volume()
                if v > 1.0 and not (n == "wood_top" and o == "bearing_6807") and not (n == "brace" and o == "carriage_arm"):
                    rep.append(f"{n} overlaps {o} by {v:.0f} mm3 (carriage +{dz} mm)")
    print("PLAN B CHECK:", "PASS" if not rep else "\n  " + "\n  ".join(rep))

    def add(owner, kind, shape, color):
        meshes.append(dict(owner=owner, kind=kind, shape=shape, color=color))
    for n, s in new_parts.items():
        add(n, "bought" if n in ("brace", "sandbag") else "printed", s, STEEL if n == "brace" else SAND if n == "sandbag" else WOOD)
    # brace screws: 2 down into the arm, 2 into the carriage's front face
    bscrews = []
    for i, (head, ax) in enumerate([((0, cy1 + 6, ztop + 1.6), (0, 0, -1)), ((0, by1 - 6, ztop + 1.6), (0, 0, -1)),
                                    ((0, cy1 + 1.6, ztop + 14), (0, -1, 0)), ((0, cy1 + 1.6, ztop + 30), (0, -1, 0))]):
        sh, col = V.screw_local("#6s", 6.35)
        nm = f"bscrew_{i}"
        add(nm, "screw", V.moved(sh, V.trsf_axes(head, V.perp_of(ax), ax)), col)
        bscrews.append(dict(name=nm, owner="brace", kind="#6s", head=list(head), axis=list(ax), length=6.35,
                            hole="#6 × ¼″ pointed · drill 7/64″ pilots through the brace holes", head_r=3.3, head_h=2.4))
    screws += bscrews
    add("glue_crack", "glue", box(-10, 10, by1 - 7, by1 - 4, cz0 + 2, ztop - 2), V.C["glue"])
    glue.append(dict(name="glue_crack", owner="brace", at=[0, by1 - 5.5, cz0 + bt / 2]))

    out_meshes = []
    for m in meshes:
        sh = m["shape"].val() if hasattr(m["shape"], "val") else m["shape"]
        verts, tris = sh.tessellate(0.12, 0.35)
        out_meshes.append(dict(owner=m["owner"], kind=m["kind"], color=m["color"],
                               v=[round(c, 1) for vv in verts for c in (vv.x, vv.y, vv.z)], f=[i for t in tris for i in t]))
    owners = {m["owner"] for m in meshes}
    column = [n for n in owners if n in parts and parts[n]["group"] in ("turret", "crank", "lift", "wrist", "finger_L", "finger_R")
              and n not in ("bearing_6807", "turntable_servo_MG996R")]
    sc_of = lambda own: [x["name"] for x in screws if x["owner"] in own]   # noqa: E731
    column_screws = sc_of(set(column) - {"brace"})
    elec = ["electronics_tray", "arduino_uno", "buck_XL4015", "mini_breadboard", "capacitor_1000uF", "start_button", "status_led", "dc_jack"]
    elec = [e for e in elec if e in owners]
    legsn = [f"leg_{i}" for i in range(1, 5)]          # leg_1 = floor board, leg_2..4 = spacer blocks
    glue_col = [g["name"] for g in glue if g["owner"] in column]

    def step(n, title, new, show, dirn, dist, level, how, fit="", scr=(), gl=(), callouts=(), badge=None, glue_text=""):
        return dict(n=n, title=title, new=new, show=sorted(set(show) | set(new) | set(scr) | set(gl)), dir=dirn, per_part_dir={},
                    dist=dist, hw=[], badge=badge, note="", screws=list(scr), glue=list(gl), fit=fit, how=how, glue_text=glue_text,
                    level=level, callouts=[dict(at=list(a), text=t) for a, t in callouts])
    base_set = ["wood_top", "wood_bottom"]
    trs = sc_of({"turntable_servo_MG996R"})
    for x in screws:
        if x["owner"] == "turntable_servo_MG996R":
            x["hole"] = "#8 × ½″ wood screw (or the #8-32) through the tab + 2 washers → 7/64″ pilot in the bottom board"
    steps = [
        step(1, "Top board: drill the bearing hole", ["wood_top"], [], None, 0, "precise",
             "¼″ (6 mm) plywood or MDF. Print the 1:1 template (docs/planb_templates.pdf, page 1; check its 50 mm bar with a "
             "ruler), tape it on, cut round the outline (it has a cut-away back-right corner: the wrist swings through there) "
             "and mark the hole centre through the paper. Drill it with a <b>1‑7/8″ (47.6 mm) hole saw</b> (or Forstner bit), board clamped on scrap.",
             "<b>The 6807 is 47.0 mm:</b> the hole is 0.6 mm bigger. One wrap of electrical tape round the bearing makes it snug.",
             callouts=[((23.8, 0, 51.35), "Ø47.6 · 1‑7/8″ hole saw, right through")]),
        step(2, "Bottom board: cut the servo slot", ["wood_bottom"], [], None, 0, "try",
             "½″ (12 mm) plywood, same outline (template page 2). Cut the slot for the MG996R's body (drill the 4 corners, saw between, file): "
             "the servo's <b>spline must end up exactly under the hole centre</b>. Hold the servo under the board and mark round it "
             "before cutting; the spline is off-centre on the servo.",
             "Test: the servo body slides up through the slot until its tabs touch the board.",
             callouts=[((sc.x, sc.y, zb_top), slot_txt)]),
        step(3, "Glue the boards: the hole becomes the bearing pocket", ["wood_top"], ["wood_bottom"], [0, 0, 1], 40, "easy",
             "Wood glue (or 4 small screws) between the boards, edges flush. The hole in the top board is now a 6 mm deep pocket "
             "with the bottom board as its floor.", glue_text="Wood glue, clamp or weigh it down ~20 min."),
        step(4, "Bearing into the pocket", ["bearing_6807"], base_set, [0, 0, 1], 40, "precise",
             "Press the 6807 into the pocket, pushing on the OUTER ring only, until it sits on the bottom board.",
             "Loose: one wrap of electrical tape round the bearing. It should sit flat and stand 0.6 mm above the top board."),
        step(5, "Turntable servo up through the slot", ["turntable_servo_MG996R"], base_set + ["bearing_6807"], [0, 0, -1], 60, "try",
             "Servo at 135° first (laptop panel). From underneath, push the MG996R up through the slot, spline up, until the "
             "spline is centred in the bearing. 4 screws through the tabs up into the bottom board, with <b>2 washers (~1.2 mm) "
             "between each tab and the board</b> so the spline tip ends 2 mm under the bearing's top.",
             "Check: the spline is in the middle of the bearing's hole when you look down.", scr=trs, badge=["MG996R", "135°"]),
        step(6, "Floor board, spacers + weight", legsn + ["sandbag"], base_set + ["bearing_6807", "turntable_servo_MG996R"] + trs, [0, 0, -1], 40, "easy",
             "A third ½″ board, same outline (template page 3) but 10 mm shorter at the front so the tray slides under, with a "
             "slot for the bottom of the servo. Glue 3 blocks of ¾″ wood (30 × 30 mm) between it and the bottom board (where "
             "the template marks them), and a small bag of sand (~150 g) on the floor board at the front. The base then stands "
             "on the same footprint as the printed one, so it is just as hard to tip over."),
        step(7, "Repair the carriage arm (if it snapped)", ["brace"],
             ["carriage_arm", "LM6UU_L1", "LM6UU_R1", "LM6UU_L2", "LM6UU_R2"], [0, 0, 1], 25, "try",
             "1) 2-part epoxy (or superglue + baking soda) into the crack, press it shut, let it cure. 2) A <b>½″ steel corner "
             "brace</b> (hardware store): one leg flat on TOP of the arm, the other up the carriage's front face. 3) Drill 7/64″ "
             "pilots through its holes, then 4 × <b>#6 × ¼″ pointed screws</b>. The top of the arm is the side that pulls apart "
             "when the claw hangs on it, so the steel there carries the load.",
             "The brace must not reach the wrist bracket's window or the rods: keep it on the arm's centre line.",
             scr=[x["name"] for x in bscrews], gl=["glue_crack"], glue_text="Epoxy in the crack before the brace."),
        step(8, "Column onto the turntable servo", column, base_set + ["bearing_6807", "turntable_servo_MG996R"] + trs + legsn + ["sandbag"],
             [0, 0, 1], 60, "precise",
             "The column is built exactly as in the main guide (steps 1–15), with the repaired carriage. Lower it straight down: "
             "the turret plate's hub into the bearing's inner ring, the horn (screwed under the plate) onto the spline, rod side "
             "toward the START can.", "Hub into the inner ring: ~Ø34.9 printed; loose → tape, tight → sand.",
             scr=column_screws, gl=glue_col, badge=["MG996R", "135°"]),
        step(9, "Electronics tray in front", elec, base_set + ["bearing_6807", "turntable_servo_MG996R"] + legsn + ["sandbag"] + column + column_screws,
             [0, -1, 0], 40, "easy",
             "The tray sits on the table in front of the wooden base, under its front edge. Tape or screw its 2 tabs to a scrap "
             "block so it can't slide; route the servo leads as in the main guide."),
    ]
    vm = json.load(open(os.path.join(HERE, "build", "viewer_mesh.json")))
    gof = {x["name"]: g for g, lst in vm["groups"].items() for x in lst}
    groups = {m["owner"]: gof.get(m["owner"], "fixed") for m in meshes}
    for x in screws:
        groups.setdefault(x["name"], gof.get(x["owner"], "fixed"))
        groups[x["name"]] = gof.get(x["owner"], "lift" if x["owner"] == "brace" else "fixed")
    groups["brace"] = "lift"
    groups["glue_crack"] = "lift"
    pv = vm["params"]
    notes = json.load(open(os.path.join(ROOT, "backend", "tools", "assembly_notes.json")))
    names = dict(notes["names"], wood_top="Top board (¼″ plywood)", wood_bottom="Bottom board (½″ plywood)", sandbag="Sandbag",
                 brace="Steel corner brace ½″", leg_1="Floor board (½″ plywood)", **{f"leg_{i}": "Spacer block (¾″ wood)" for i in range(2, 5)})
    levels = json.loads(json.dumps(notes["levels"]))
    levels["precise"]["text"] = "A fit that decides whether the robot works: test it with the real part; tape if loose, sand or file if tight."
    levels["easy"]["text"] = "Simple wood work or screws: any careful job works."
    data = dict(meshes=out_meshes, screws=screws, glue=glue, steps=steps,
                printed=sorted({m["owner"] for m in meshes if m["kind"] == "printed"}), names=names,
                screw_names=notes["screw_names"], levels=levels, planb=True,
                title="Plan B: wooden base + carriage repair",
                while_waiting=["Hardware store: ½″ and ¼″ plywood, 1‑7/8″ hole saw, wood glue, 1½″ square wood, epoxy, ½″ steel corner brace, #6 × ¼″ pointed screws, washers",
                               "Mark the hole centre on the top board: 76 mm from the sides, 76 mm from the front"],
                motion=dict(groups=groups, sequence=vm["sequence"],
                            params=dict(lift_theta0=pv["lift_theta0"], grip_z=pv["grip_z"], pivot_x=pv["pivot_x"], pivot_y=pv["pivot_y"],
                                        lift_servo_tip=list(P["lift_servo_tip"]))))
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    def corners(sec_, a_deg):
        r = math.radians(a_deg)
        return [(x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r))
                for x, y in ((sec_.xmin - 1, sec_.ymin - 1), (sec_.xmax + 1, sec_.ymin - 1), (sec_.xmax + 1, sec_.ymax + 1), (sec_.xmin - 1, sec_.ymax + 1))]
    templates([f.outerWire() for f in tops], 47.6, [corners(sec, ang), corners(sec2, ang)],
              [(-58, -48), (42, -50), (-60, 15)], ((-20, 20), (-64, -40)), os.path.join(ROOT, "docs", "planb_templates.pdf"))
    print(f"wrote viewer/data/planb.json: {len(out_meshes)} meshes, {len(steps)} steps, {os.path.getsize(OUT) // 1024} KB; {slot_txt}")


if __name__ == "__main__":
    main()
