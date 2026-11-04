"""The wiring through each move of the run: one animation per action, see-through.

    python3.13 backend/cad/wiring.py           # routes (and wiring_mesh.json)
    python3.13 backend/cad/wiring_motion.py    # frames + per-action check  (~3 min)
    node backend/tools/render_wiring_motion.js # viewer/wiring_motion.html + docs/wiring/motion/

Each frame moves the parts with the firmware's joint values (eased like the firmware). The tied
(rigid) runs of every servo lead move with the part they are tied to. The three free loops are
drawn between their two tie points with their real cable length, leaving each tie along the tied
run and sagging downward. That shape is an estimate of how the loop drapes; what is exact is the
distance and wrap angle between the tie points, so the slack check uses those.

Writes backend/cad/build/wiring_motion.json and cad/wiring/wiring_motion_report.txt.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import model as M  # noqa: E402
import wiring as Wm  # noqa: E402

FW = M.FW
START = dict(turn=FW["TURN_START"], lift=FW["LIFT_DOWN"], wrist=FW["WRIST_UP"], grip=FW["GRIP_OPEN"])
# (action, joint, target, frames, servo label, what to look at)
ACTIONS = [
    ("GRIP", "grip", FW["GRIP_CLOSED"], 30, "SG90 gripper (D5)", "The SG90 lead rides on top of the gripper, clear of the swinging arms"),
    ("LIFT", "lift", FW["LIFT_UP"], 30, "MG90S lift (D10)", "Lift loop (3) opens up by 15.3 mm"),
    ("FLIP", "wrist", FW["WRIST_FLIP"], 48, "MG90S wrist (D6)", "Wrist loop (1) wraps half a turn around the wrist servo"),
    ("TURN", "turn", FW["TURN_TARGET"], 48, "MG996R turntable (D9)", "Turn loop (6) swings 90° across the base hole"),
    ("LOWER", "lift", FW["LIFT_DOWN"], 30, "MG90S lift (D10)", "Lift loop (3) closes again"),
    ("RELEASE", "grip", FW["GRIP_RELEASE"], 24, "SG90 gripper (D5)", "Arms open 25°: the lead stays clear of them upside down"),
]
GROUPS = ("fixed", "turret", "crank", "lift", "wrist", "finger_R", "finger_L", "can")


def ease(s):
    return s ** 3 * (10 - 15 * s + 6 * s * s)


def np_t(t):
    return np.array([[t.Value(i, j) for j in range(1, 5)] for i in range(1, 4)] + [[0, 0, 0, 1.0]])


def screw(R, w):
    """Fraction w of the rigid motion R (4x4) as a screw: rotate w*angle about R's axis, slide w*axial."""
    Q, t = R[:3, :3], R[:3, 3]
    ang = math.acos(max(-1.0, min(1.0, (np.trace(Q) - 1) / 2)))
    if ang < 1e-6:
        out = np.eye(4); out[:3, 3] = w * t
        return out
    u = np.array([Q[2, 1] - Q[1, 2], Q[0, 2] - Q[2, 0], Q[1, 0] - Q[0, 1]])
    if np.linalg.norm(u) < 1e-6:                                  # 180 deg: axis from Q + I
        k = int(np.argmax(np.diag(Q)))
        u = (Q + np.eye(3))[:, k]
    u = u / np.linalg.norm(u)
    ax = np.dot(t, u)
    c = np.linalg.lstsq(np.eye(3) - Q, t - ax * u, rcond=None)[0]  # a point on the axis
    a = w * ang
    K = np.array([[0, -u[2], u[1]], [u[2], 0, -u[0]], [-u[1], u[0], 0]])
    Qw = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
    out = np.eye(4); out[:3, :3] = Qw; out[:3, 3] = c - Qw @ c + w * ax * u
    return out


def bez(P0, P1, P2, P3, n):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * P0 + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t ** 2 * P2 + t ** 3 * P3


def drape(a_prev, A, B, b_next, L, n):
    """Loop between tie points A and B with length L: leaves A along the tied run's direction, arrives
    at B along the next run's direction, and sags downward (gravity). Bisection on the handle length."""
    tA = (A - a_prev) / (np.linalg.norm(A - a_prev) + 1e-9)
    tB = (b_next - B) / (np.linalg.norm(b_next - B) + 1e-9)
    down = np.array([0, 0, -1.0])

    def curve(h):
        return bez(A, A + h * (0.75 * tA + 0.45 * down), B - h * (0.75 * tB - 0.45 * down), B, 200)

    lo, hi = 0.0, 4 * L
    for _ in range(50):
        h = (lo + hi) / 2
        cc = curve(h)
        if np.sum(np.linalg.norm(np.diff(cc, axis=0), axis=1)) < L:
            lo = h
        else:
            hi = h
    cc = curve((lo + hi) / 2)
    s_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(cc, axis=0), axis=1))])
    want = np.linspace(0, s_[-1], n + 2)[1:-1]
    return np.array([np.interp(want, s_, cc[:, k]) for k in range(3)]).T


def loops_of(g):
    """[(i0, i1, group_before, group_after)] of each loop run in a wire's per-sample groups."""
    segs, i = [], 0
    while i < len(g):
        if g[i] == "loop":
            k = i
            while k < len(g) and g[k] == "loop":
                k += 1
            segs.append((i - 1, k, g[i - 1], g[k]))
            i = k
        else:
            i += 1
    return segs


_CACHE = {}


def settle(P, scene, r, passes=4):
    """Relax a loop polyline (anchors fixed): push out of parts, smooth, repeat."""
    P = P.copy()
    for it in range(passes):
        for i in range(1, len(P) - 1):
            P[i] = scene.push(P[i], r)
        if it < passes - 1:
            Q = P.copy()
            Q[1:-1] = 0.5 * P[1:-1] + 0.25 * (P[:-2] + P[2:])
            P = Q
    return P


def resample(P, n):
    s_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    want = np.linspace(0, s_[-1], n)
    return np.array([np.interp(want, s_, P[:, k]) for k in range(3)]).T


def pose_wire(c, g, T, scene=None, r=1.3):
    """Wire samples in pose T (dict group -> 4x4); loops draped with their real length, resting on parts."""
    out = np.empty_like(c)
    H = np.c_[c, np.ones(len(c))]
    for i, gi in enumerate(g):
        if gi != "loop":
            out[i] = (T[gi] @ H[i])[:3]
    for i0, i1, ga, gb in loops_of(g):
        L = float(np.sum(np.linalg.norm(np.diff(c[i0:i1 + 1], axis=0), axis=1)))   # the cable that is there
        key = (i0, i1, tuple(np.round(np.r_[out[i0 - 1], out[i0], out[i1], out[i1 + 1]], 2)))
        if key not in _CACHE:
            coarse = np.vstack([out[i0], drape(out[i0 - 1], out[i0], out[i1], out[i1 + 1], L, max(22, int(L / 2.5))), out[i1]])
            if scene is not None:
                coarse = settle(coarse, scene, r)
            fine = resample(coarse, i1 - i0 + 1)
            if scene is not None:                                  # final contact pass on every point
                for _ in range(2):
                    for i in range(1, len(fine) - 1):
                        fine[i] = scene.push(fine[i], r, margin=0.5)
            _CACHE[key] = fine[1:-1]
        out[i0 + 1:i1] = _CACHE[key]
    return out


def main():
    W = Wm.routes()[:3]                                            # the three leads that cross moving joints
    for w in W:
        w["c"], w["g"] = Wm.catmull(w["pts"])
    parts = [p for p in M.build_parts() if p["group"] != "coupon"]
    avail = {}                                                     # loop lengths (the cable that is there)
    for w in W:
        for i0, i1, ga, gb in loops_of(w["g"]):
            avail[(w["key"], ga)] = Wm.length(w["c"][i0:i1 + 1])
    kind = {"wrist": "wrist", "lift": "lift", "turret": "turn"}
    LOOPNAME = {"wrist": "Wrist loop (1)", "lift": "Lift loop (3)", "turn": "Turn loop (6)"}

    S = dict(START)
    can_T = np.eye(4)
    frames, rep, ok = [], ["Wiring through each move (backend/cad/wiring_motion.py)", "=" * 60,
                           "slack used = length the motion needs between the tie points / loop length (<= 80 % passes)",
                           "clearance = tied runs of the 3 column leads to every part that moves against them, every 3rd frame (>= 0.3 mm passes)",
                           "loop shape = drape with the real cable length, resting on parts it meets (contact allowed: >= 0 mm passes)", ""], True
    for ai, (act, joint, target, n, servo, note) in enumerate(ACTIONS):
        start = S[joint]
        worst_slack, worst_gap, worst_loop = {}, (1e9, ""), (1e9, "")
        for k in range(n + 1):
            S[joint] = start + (target - start) * ease(k / n)
            j = M.joints_from_commands(S["turn"], S["lift"], S["wrist"], S["grip"])
            Tg = M.group_transforms(j)
            T = {gname: np_t(t) for gname, t in Tg.items()}
            attached = act not in ("GRIP", "RELEASE") or (act == "GRIP" and k == n)
            if attached:
                can_T = T["wrist"]
            T["can"] = can_T
            slack = {}
            for w in W:
                for i0, i1, ga, gb in loops_of(w["g"]):
                    need = Wm.loop_need(kind[ga], w["c"][i0], w["c"][i1], [j])
                    f = need / avail[(w["key"], ga)]
                    nm = LOOPNAME[kind[ga]]
                    slack[nm] = max(slack.get(nm, 0), f)
            for nm, f in slack.items():
                worst_slack[nm] = max(worst_slack.get(nm, 0), f)
            from OCP.gp import gp_Trsf
            Tocc = {}
            for gname, m in T.items():
                t = gp_Trsf(); t.SetValues(*[float(m[r_][c_]) for r_ in range(3) for c_ in range(4)]); Tocc[gname] = t
            sc = Wm.Scene(parts, Tocc)
            posed = [pose_wire(w["c"], w["g"], T, sc, w["r"]) for w in W]
            gap_txt = None
            if k % 3 == 0 or k == n:
                fmin, lmin = (1e9, ""), (1e9, "")
                for w, pc in zip(W, posed):
                    L = Wm.length(w["c"])
                    sarc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(w["c"], axis=0), axis=1))])
                    for i in range(0, len(pc), 3):
                        if sarc[i] < Wm.END_SKIP or sarc[i] > L - Wm.END_SKIP:
                            continue
                        gi = w["g"][i]
                        # a tied run never moves against the part it is tied to (checked in wiring.py)
                        gap, who = sc.clearance(pc[i], w["r"], skip_group=None if gi == "loop" else gi)
                        if w["g"][i] == "loop":
                            if gap < lmin[0]:
                                lmin = (gap, f"{w['name'].split(' (')[0]} / {who}")
                        elif gap < fmin[0]:
                            fmin = (gap, f"{w['name'].split(' (')[0]} / {who}")
                if fmin[0] < worst_gap[0]:
                    worst_gap = fmin
                if lmin[0] < worst_loop[0]:
                    worst_loop = lmin
                gap_txt = round(fmin[0], 1)
            frames.append(dict(a=ai, k=k, n=n, cmd=round(S[joint], 1), T={g_: [round(v, 4) for v in T[g_][:3].ravel()] for g_ in GROUPS},
                               wires=[[round(v, 1) for v in pc[::2].ravel()] + [round(v, 1) for v in pc[-1]] for pc in posed],
                               slack={nm: round(f, 3) for nm, f in slack.items()}, gap=gap_txt))
        good = all(f <= 0.8 for f in worst_slack.values()) and worst_gap[0] >= Wm.CLEAR_MIN and worst_loop[0] >= -0.05
        ok &= good
        rep.append(f"{ai + 1}. {act:8s} {servo:24s} {start:5.0f}° -> {target:5.0f}°   {'PASS' if good else 'FAIL'}")
        rep.append("     slack used (worst frame): " + ", ".join(f"{nm} {f * 100:.0f} %" for nm, f in worst_slack.items()))
        rep.append(f"     tied runs, closest part: {worst_gap[0]:.1f} mm ({worst_gap[1]})")
        rep.append(f"     loops (draped), closest part: {worst_loop[0]:.1f} mm ({worst_loop[1]})" + ("  = resting on it" if worst_loop[0] < 0.6 else ""))
    rep += ["", "RESULT: " + ("ALL PASS" if ok else "FAIL")]
    open(os.path.join(ROOT, "cad", "wiring", "wiring_motion_report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))
    json.dump(dict(actions=[dict(name=a[0], joint=a[1], start=None, target=a[2], frames=a[3], servo=a[4], note=a[5]) for a in ACTIONS],
                   start=START, wires=[dict(name=w["name"], color=w["color"], r=w["r"]) for w in W], frames=frames),
              open(os.path.join(HERE, "build", "wiring_motion.json"), "w"), separators=(",", ":"))
    print("wrote backend/cad/build/wiring_motion.json, cad/wiring/wiring_motion_report.txt")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
