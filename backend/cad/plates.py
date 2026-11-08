"""Pack the print-ready STLs onto build plates -> cad/print/plates/

    python3.13 backend/cad/print_prep.py   # oriented STLs + print_table.csv
    python3.13 backend/cad/plates.py       # plates

Each plate is one print job: a .3mf (every part a separate object, so the slicer keeps per-part
supports), the same plate as one .stl, and plates.png (top view of every plate). Parts keep the
orientation print_prep.py chose; they may only turn 90° about Z to fit. Bed 235 x 235 mm (Creality CR-6 SE) with a 7 mm
edge margin (skirt / brim) and 14 mm between parts (supports can reach past a part's edge).

Plates are grouped so one failed print wastes as little as possible and the long ones can run overnight.
"""
import csv
import os
import struct
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PR = os.path.join(ROOT, "cad", "print")
OUT = os.path.join(PR, "plates")
BED = (235.0, 235.0)   # Creality CR-6 SE
EDGE, GAP = 7.0, 14.0   # 14 mm: room for supports that reach past a part's edge

PLATES = [  # (file stem, title, part numbers, when)
    ("plate0_coupon", "Plate 0: tolerance coupon (print first, check fits)", ["CA-900"], "first, ~1 h"),
    ("plate1_base", "Plate 1: base + turret plate + top cap + lift link", ["CA-101", "CA-201", "CA-203", "CA-302"], "overnight"),
    # the two fingers are on different plates: PrusaSlicer 2.7 reports a false "G-code path conflict" and
    # crashes for some groupings with a supported finger (checked by slicing every plate, see the README)
    ("plate2_tray_spine", "Plate 2: electronics tray + spine + right finger", ["CA-102", "CA-202", "CA-402"], "day"),
    ("plate3_arm_claw", "Plate 3: carriage arm + gripper frame + left finger", ["CA-301", "CA-401", "CA-403"], "day"),
]


def read_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        tris = []
        for line in data.decode(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                tris.append([float(v) for v in line.split()[1:4]])
        return np.array(tris).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return arr["v"].reshape(-1, 3, 3).astype(float)


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"Concept A plate".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            nrm = np.cross(t[1] - t[0], t[2] - t[0])
            ln = np.linalg.norm(nrm)
            f.write(struct.pack("<3f", *(nrm / ln if ln > 0 else nrm)))
            f.write(struct.pack("<9f", *t.ravel()))
            f.write(b"\0\0")


# Per-part slicer settings written into the .3mf (PrusaSlicer reads them as per-object settings, so
# opening a plate needs no clicking: supports only where needed, solid fingers, a brim on the tiny link)
PER_PART = {
    "CA-101": {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1"},
    "CA-201": {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1"},
    "CA-301": {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1"},
    "CA-402": {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1", "fill_density": "100%"},
    "CA-403": {"support_material": "1", "support_material_auto": "1", "support_material_buildplate_only": "1", "fill_density": "100%"},
    "CA-302": {"brim_width": "5"},
}


def write_3mf(path, objects):
    """objects: [(name, tris)] already placed in bed coordinates. Name starts with the part number."""
    res, items, cfg = [], [], []
    for i, (name, tris) in enumerate(objects, 1):
        v, idx = np.unique(np.round(tris.reshape(-1, 3), 4), axis=0, return_inverse=True)
        idx = [t for t in idx.reshape(-1, 3) if len(set(t)) == 3]
        vs = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in idx)
        res.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" printable="1"/>')
        meta = "".join(f'<metadata type="object" key="{k}" value="{val}"/>' for k, val in PER_PART.get(name.split()[0], {}).items())
        cfg.append(f'<object id="{i}" instances_count="1"><metadata type="object" key="name" value="{name}"/>{meta}'
                   f'<volume firstid="0" lastid="{len(idx) - 1}"><metadata type="volume" key="name" value="{name}"/></volume></object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>' + "".join(res) +
             "</resources><build>" + "".join(items) + "</build></model>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/Slic3r_PE_model.config", '<?xml version="1.0" encoding="utf-8"?><config>' + "".join(cfg) + "</config>")


def pack(sizes):
    """Shelf packing, biggest first, 90° turns allowed. sizes: {key: (w, d)} -> {key: (x, y, rotated)} or None."""
    W, D = BED[0] - 2 * EDGE, BED[1] - 2 * EDGE
    order = sorted(sizes, key=lambda k: -sizes[k][0] * sizes[k][1])
    shelves, place = [], {}                                     # shelf: [y, height, x_used]
    for k in order:
        w0, d0 = sizes[k]
        best = None
        for rot in (False, True):
            w, d = (d0, w0) if rot else (w0, d0)
            if w > W or d > D:
                continue
            for s in shelves:
                if d <= s[1] and s[2] + w <= W:
                    waste = s[1] - d
                    if best is None or waste < best[0]:
                        best = (waste, s, rot, w, d)
            y_new = (shelves[-1][0] + shelves[-1][1] + GAP) if shelves else 0.0
            if y_new + d <= D and (best is None):
                best = (1e9, None, rot, w, d)
        if best is None:
            return None
        _, s, rot, w, d = best
        if s is None:
            s = [(shelves[-1][0] + shelves[-1][1] + GAP) if shelves else 0.0, d, 0.0]
            shelves.append(s)
        place[k] = (EDGE + s[2], EDGE + s[0], rot)
        s[2] += w + GAP
    # centre the whole layout on the bed
    xs = [place[k][0] + (sizes[k][1] if place[k][2] else sizes[k][0]) for k in place]
    ys = [place[k][1] + (sizes[k][0] if place[k][2] else sizes[k][1]) for k in place]
    dx, dy = (BED[0] - EDGE - max(xs)) / 2, (BED[1] - EDGE - max(ys)) / 2
    return {k: (x + dx, y + dy, r) for k, (x, y, r) in place.items()}


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = {r["part_no"]: r for r in csv.DictReader(open(os.path.join(PR, "print_table.csv")))}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, len(PLATES), figsize=(5 * len(PLATES), 5.6))
    summary = []
    for ax, (stem, title, pns, when) in zip(axs, PLATES):
        tris = {pn: read_stl(os.path.join(ROOT, rows[pn]["file"])) for pn in pns}
        sizes = {}
        for pn, t in tris.items():
            lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
            tris[pn] = t - np.array([lo[0], lo[1], lo[2]])          # corner at the origin, sitting on z = 0
            sizes[pn] = (hi[0] - lo[0], hi[1] - lo[1])
        place = pack(sizes)
        if place is None:
            raise SystemExit(f"{stem}: parts do not fit a {BED[0]:.0f} x {BED[1]:.0f} bed")
        objs, allt = [], []
        for pn in pns:
            x, y, rot = place[pn]
            t = tris[pn].copy()
            if rot:                                               # +90° about Z, then back to the origin
                t = np.stack([-t[..., 1], t[..., 0], t[..., 2]], axis=-1)
                t[..., 0] += sizes[pn][1]
            t[..., 0] += x
            t[..., 1] += y
            objs.append((f"{pn} {rows[pn]['part']}", t))
            allt.append(t)
            poly = t.reshape(-1, 3)
            ax.add_patch(plt.Rectangle((poly[:, 0].min(), poly[:, 1].min()), np.ptp(poly[:, 0]), np.ptp(poly[:, 1]),
                                       fc="#cfe0f7", ec="#2f6fdb", lw=1))
            for tri in t[:: max(1, len(t) // 4000)]:
                ax.fill(tri[:, 0], tri[:, 1], color="#2f6fdb", alpha=0.05, lw=0)
            ax.text(poly[:, 0].mean(), poly[:, 1].mean(), f"{pn}\n{rows[pn]['part']}", ha="center", va="center", fontsize=7.5)
        write_3mf(os.path.join(OUT, stem + ".3mf"), objs)
        write_stl(os.path.join(OUT, stem + ".stl"), np.concatenate(allt))
        hrs = sum(float(rows[pn]["est_time_h"]) for pn in pns)
        g = sum(float(rows[pn]["mass_g"]) for pn in pns)
        sup = [pn for pn in pns if rows[pn]["supports"].startswith("yes")]
        summary.append((stem, title, pns, hrs, g, sup, when))
        ax.add_patch(plt.Rectangle((0, 0), *BED, fill=False, ec="k", lw=1.2))
        ax.add_patch(plt.Rectangle((EDGE, EDGE), BED[0] - 2 * EDGE, BED[1] - 2 * EDGE, fill=False, ec="#999", ls="--", lw=0.6))
        ax.set_xlim(-5, BED[0] + 5); ax.set_ylim(-5, BED[1] + 5); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{title.split(':')[0]}\n≈ {hrs:.1f} h, {g:.0f} g PETG  ({when})", fontsize=9)
    fig.suptitle(f"Build plates, {BED[0]:.0f} × {BED[1]:.0f} mm bed (dashed: 7 mm margin for skirt / brim)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(os.path.join(OUT, "plates.png"), dpi=110)
    plt.close(fig)
    with open(os.path.join(OUT, "plates.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["plate", "title", "parts", "hours_est", "petg_g", "parts_needing_supports", "when"])
        for stem, title, pns, hrs, g, sup, when in summary:
            w.writerow([stem, title, " ".join(pns), f"{hrs:.1f}", f"{g:.0f}", " ".join(sup) or "none", when])
    for s in summary:
        print(f"{s[0]:20s} {s[3]:5.1f} h {s[4]:5.0f} g  parts {' '.join(s[2])}  supports: {' '.join(s[5]) or 'none'}")
    print("wrote cad/print/plates/ (.3mf + .stl per plate, plates.png, plates.csv)")


if __name__ == "__main__":
    main()
