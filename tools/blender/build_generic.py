"""Builds one of the table driven jets (jets.py) in Blender and exports it (models/<id>/<id>.glb, web/assets/<id>.glb).

Run it inside Blender like the other builders, with OPTS["jet"] naming the aircraft:

    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), {"__file__": path, "OPTS": {"jet": "su35"}})

Same conventions as the hand built jets (build_f15.py): +Y forward, +X right, +Z up, metres; moving parts on their
hinges with the local X axis along the hinge (positive: trailing edge down, rudder trailing edge right, brake
open); gear legs and doors carry `retract` / `door`; `store_N` empties are the weapon stations (numbered like
specs.js std(): 1 left tip .. 4 left fuselage, 5 right fuselage .. 8 right tip); `ref_*` empties the points the
game needs; `screen_*` objects the front cockpit's displays in the Super Hornet layout (two DDIs, the AMPCD and
the UFCD), so the game's live displays show on them.

Every cockpit part is kept under the canopy glass (or under the skin where there is no glass): nothing in the
cockpit pokes through the canopy, from inside or outside.
"""

import importlib
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import aircraft_lib as L  # noqa: E402
import f16_shape  # noqa: E402
import generic_shape as S  # noqa: E402
import jets  # noqa: E402

importlib.reload(L)
importlib.reload(f16_shape)
importlib.reload(S)
importlib.reload(jets)
from aircraft_lib import (C_BLACK, C_CHROME, C_DARK, C_GREY, C_LIGHT, C_STEEL, C_WHITE, Part,  # noqa: E402
                          airfoil_patch, box, build_object, empty, gear_door, gear_well, prism, retract_rotation,
                          rot_x, rotate_about, superellipse, tube, unit, wheel)

OPTS = dict(dict(jet="su35", build=True, textures=True, export=True, save=False, previews=None, views=None), **globals().get("OPTS", {}))
CFG = jets.JETS[OPTS["jet"]]
S.configure(CFG)
ID = CFG["name"]
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", ID)
TEX = os.path.join(OUT, "textures")
WEB = os.path.join(ROOT, "web", "assets")
WEB_TEXTURES = {ID + "_basecolor.png": 2048, ID + "_normal.png": 1024, ID + "_orm.png": 1024}
CK = CFG["cockpit"]


# ================================================================ texture atlas
def uv_coords(pos, nrm, mode, cent=None):
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    A = S.ATLAS
    u = (y - S.YA0) / A
    out = np.zeros((len(pos), 2))
    auto = mode == 0
    top = (auto & (nrm[:, 2] >= 0.55)) | ((mode == 1) & (nrm[:, 2] >= 0.0))
    bot = (auto & (nrm[:, 2] <= -0.35)) | ((mode == 1) & (nrm[:, 2] < 0.0))
    fin = mode == 2
    sign = np.where((cent[:, 0] if cent is not None else x) >= 0.0, 1.0, -1.0)
    outer = fin & (nrm[:, 0] * sign > 0.0)
    side = ~(top | bot | outer) & (mode != 4)
    out[top] = np.stack([u[top], (S.V_TOP + np.abs(x[top])) / A], axis=1)
    out[bot] = np.stack([u[bot], (S.V_BOT + np.abs(x[bot])) / A], axis=1)
    out[side] = np.stack([u[side], (S.V_SIDE + np.clip(z[side], -S.V_SIDE + 2 * S.HALF + 0.1, S.ZMAX_SIDE)) / A], axis=1)
    if S.FIN is not None:
        s = S.fin_s(x, z)
        for sg in (1.0, -1.0):
            m = outer & (sign == sg)
            fu, fv = S.fin_island(y[m], s[m], sg)
            out[m] = np.stack([fu / A, fv / A], axis=1)
    return out


# ================================================================ airframe
NH_UP, NH_CUT, NH_LO = 48, 2, 44


def body_ring(sec):
    h = sec.half_ring(NH_UP, NH_CUT, NH_LO)
    right = np.stack([h[:, 0], np.full(len(h), sec.y), h[:, 1]], axis=1)
    left = right[-2:0:-1] * np.array([-1.0, 1.0, 1.0])
    return np.vstack([right, left])


def stations(y1, y0, step):
    n = max(1, int(round((y1 - y0) / step)))
    return list(np.linspace(y1, y0, n + 1))


def in_rect(rect, c, mirror=False):
    x0, x1, y0, y1 = rect
    x = abs(c[0]) if mirror else c[0]
    return x0 < x < x1 and y0 < c[1] < y1


GEAR = {}          # filled by plan_gear(): wells (cut in the body skin) and painted wells


def in_holes(c):
    for rect, mirror in GEAR.get("cut", []):
        if c[2] < S.body_hw(c[1]) * 0 + float(S.BODY[5](c[1])) and in_rect(rect, c, mirror):
            return True
    return False


def build_body():
    part = Part("paint", "auto")
    eps = 0.004
    yn = S.Y_NOSE
    ys = stations(yn - 0.02, yn - 0.40, 0.035) + stations(yn - 0.40, yn - 1.10, 0.07)[1:] + stations(yn - 1.10, S.Y_RADOME, 0.10)[1:]
    marks = sorted({S.Y_RADOME, S.CANOPY_Y1, S.COCKPIT_Y1, S.COCKPIT_Y0, S.CANOPY_Y0, min(S.Y_CHINE0, S.Y_RADOME - 0.05),
                    S.Y_KINK + 0.9, S.Y_KINK, S.WING_TE + eps}, reverse=True)
    marks = [m for m in marks if S.WING_TE + eps <= m <= S.Y_RADOME]
    for a, b in zip(marks, marks[1:]):
        if a - b > 0.02:
            ys += stations(a, b, 0.11)[1:]
    front = np.array([body_ring(S.Section(y)) for y in ys])
    nr, nc = front.shape[:2]
    flat = front.reshape(-1, 3)
    faces = []
    for i in range(nr - 1):
        for j in range(nc):
            a, b = i * nc + j, i * nc + (j + 1) % nc
            c = flat[[a, b, b + nc, a + nc]].mean(axis=0)
            if S.COCKPIT_Y0 < c[1] < S.COCKPIT_Y1 and abs(c[0]) < S.cockpit_w(c[1]) and c[2] > float(S.BODY[5](c[1])) + 0.05:
                continue                                  # the cockpit opening
            faces.append((a, b, b + nc, a + nc))
    part.add(flat, faces)
    part.fan(front[0], (0.0, S.Y_NOSE, float(S.BODY[5](S.Y_NOSE))))
    aft = np.array([body_ring(S.Section(y)) for y in stations(S.WING_TE + eps, S.Y_BODY_END, 0.11)])
    part.grid(aft, close=True)
    part.fan(aft[-1], aft[-1].mean(axis=0) + np.array([0.0, -0.01, 0.0]))
    return part.drop(in_holes)


def wing_pos(x, s, side):
    c = float(S.wing_chord(x))
    t = float(S.wing_t(x))
    return np.stack([np.full(len(s), x), S.wing_le(x) - s * c, float(S.wing_z(x)) + side * f16_shape.yt(s, t) * c], axis=1)


def flap_f(x):
    return 1.0 - S.flap_chord(x) / S.wing_chord(x)


def ail_f(x):
    return 1.0 - S.ail_chord(x) / S.wing_chord(x)


def span_pts(a, b, n, extra=()):
    pts = set(np.linspace(a, b, n).round(5))
    for k in list(S.WING_KINKS) + list(extra):
        if a < k < b:
            pts.add(round(k, 5))
    return np.array(sorted(pts))


def build_wing():
    """Right wing: fixed part, flap (inboard trailing edge), aileron (outboard), optional leading edge flap."""
    fixed, flap, ail, lef = (Part("paint", "tb") for _ in range(4))
    f0, f1 = S.FLAP[0], S.FLAP[1]
    a0, a1 = S.AIL[0], S.AIL[1]
    lf = S.LEF
    cuts = [S.X_ROOT, f0, f1, a0, a1, S.X_TIP] + ([lf[0], lf[1]] if lf else [])
    cuts = sorted(set(round(c, 5) for c in cuts if S.X_ROOT <= c <= S.X_TIP))
    for x0, x1 in zip(cuts, cuts[1:]):
        if x1 - x0 < 1e-3:
            continue
        span = span_pts(x0, x1, max(3, int((x1 - x0) / 0.35) + 2))
        in_flap = f0 <= x0 and x1 <= f1
        in_ail = a0 <= x0 and x1 <= a1
        in_lef = lf is not None and lf[0] <= x0 and x1 <= lf[1]
        b_fn = flap_f if in_flap else ail_f if in_ail else None
        a_fn = (lambda x: lf[2]) if in_lef else None
        airfoil_patch(fixed, span, wing_pos, a_fn, b_fn, nc=18, cap0=x0 > S.X_ROOT + 1e-4, cap1=x1 >= S.X_TIP - 1e-4)
        if in_flap:
            airfoil_patch(flap, span, wing_pos, flap_f, None, nc=8, cap0=True, cap1=True)
        if in_ail:
            airfoil_patch(ail, span, wing_pos, ail_f, None, nc=8, cap0=True, cap1=True)
        if in_lef:
            airfoil_patch(lef, span, wing_pos, None, lambda x: lf[2], nc=8, cap0=True, cap1=True)
    return fixed, flap, ail, (lef if lf else None)


def surface_pos(srf):
    def pos(x, s, side):
        c = float(srf.le(x) - srf.te(x))
        return np.stack([np.full(len(s), x), srf.le(x) - s * c, srf.z(x) + side * f16_shape.yt(s, srf.t) * c], axis=1)
    return pos


def build_booms():
    part = Part("paint", "side")
    for b in S.BOOMS:
        for side in (1.0, -1.0):
            ys = np.linspace(b["y0"], b["y1"], 18)
            taper = b.get("taper", 0.65)
            r = b["r"] * np.where(ys < b["y1"] + taper, np.clip((ys - b["y1"]) / taper, 0.2, 1.0) ** 0.5, 1.0)
            pts = np.stack([np.full(18, side * b["x"]), ys, np.full(18, b["z"])], axis=1)
            tube(part, pts, r, 20, caps=True, squash=b.get("squash", 0.85))
    for p in S.SHELVES:
        for side in (1.0, -1.0):
            cx, hw = 0.5 * (p["x0"] + p["x1"]), 0.5 * (p["x1"] - p["x0"])
            rings = []
            for y in np.linspace(p["y0"], p["y1"], 12):
                k = 1.0 if y > p["y1"] + 0.6 else max(0.15, (y - p["y1"]) / 0.6)
                rings.append(superellipse(y, p["z"], hw, 0.5 * p["t"] * k, 3.0, 3.0, 16, side * cx))
            part.grid(rings, close=True)
            part.ngon(rings[0])
            part.ngon(rings[-1])
    return part


def fin_parts(f, sign, uv="fin"):
    """One fin: (fixed part, moving part or None, hinge origin, hinge axis)."""
    def pos(sv, s, side):
        c = float(f.le(sv) - f.te(sv))
        t = f.t0 + (f.t1 - f.t0) * (sv - f.s0) / (f.s1 - f.s0)
        return f.point(sign, np.full(len(s), sv), f.le(sv) - s * c, side * f16_shape.yt(s, t) * c)
    fixed = Part("paint", uv)
    if f.moving:
        mov = Part("paint", uv)
        airfoil_patch(mov, np.linspace(f.s0, f.s1, 12), pos, nc=20, cap0=True, cap1=True)
        piv = f.pivot
        a = f.point(sign, np.array(f.s0), np.array(piv), np.array(0.0))
        b = f.point(sign, np.array(f.s1), np.array(piv), np.array(0.0))
        stub = Part("paint", uv)
        return stub, mov, a, b - a
    if not f.rudder:
        airfoil_patch(fixed, np.linspace(f.s0, f.s1, 12), pos, nc=20, cap0=True, cap1=True)
        return fixed, None, None, None
    r0, r1 = f.rudder[0], f.rudder[1]

    def rud_f(sv):
        return 1.0 - float(f.rudder_chord(sv)) / float(f.le(sv) - f.te(sv))
    if r0 > f.s0 + 1e-3:
        airfoil_patch(fixed, np.linspace(f.s0, r0, 3), pos, nc=20, cap0=True, cap1=True)
    airfoil_patch(fixed, np.linspace(r0, r1, 8), pos, None, rud_f, nc=16, cap0=r0 <= f.s0 + 1e-3)
    if r1 < f.s1 - 1e-3:
        airfoil_patch(fixed, np.linspace(r1, f.s1, 5), pos, nc=20, cap0=True, cap1=True)
    else:
        pass
    rud = Part("paint", uv)
    airfoil_patch(rud, np.linspace(r0, r1, 8), pos, rud_f, None, nc=8, cap0=True, cap1=True)
    a, b = (f.point(sign, np.array(s), np.array(float(f.te(s) + f.rudder_chord(s))), np.array(0.0)) for s in (r0, r1))
    return fixed, rud, a, b - a


def build_fins():
    fixed, moving = [], {}
    for f in S.FINS:
        for sign, sfx in (((1.0, "R"), (-1.0, "L")) if f.twin else ((1.0, ""),)):
            fx, mv, a, d = fin_parts(f, sign)
            fixed.append(fx)
            if mv is not None:
                name = "rudder_" + sfx if sfx else "rudder"
                if sign < 0 and f.moving:
                    a, d = a, d
                moving[name] = (mv, a, d)
    for f in S.VENTRALS:
        for sign in (1.0, -1.0):
            fx, _mv, _a, _d = fin_parts(f, sign, uv="side")
            fixed.append(fx)
    return fixed, moving


def duct_ring(d, y, scale=1.0, dy=0.0, seg=48, sign=1.0, face=False):
    xi, xo, zt, zb, nu, nl = d.section(y)
    if d.mirror:
        cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
    else:
        cx, hw = 0.0, xo
    cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
    r = superellipse(y, cz, hw * scale, hh * scale, nu, nl, seg, cx)
    rake = float(S.smoothstep(d.y0 - 1.0, d.y0, y))
    r[:, 1] += (r[:, 2] - cz) * d.rake * rake + (np.abs(r[:, 0]) - abs(cx)) * d.side_rake * rake * (1.0 if d.mirror else 0.0) \
        - np.abs(r[:, 0]) * d.side_rake * rake * (0.0 if d.mirror else 1.0) + dy
    r[:, 0] *= sign
    return r[::-1] if sign < 0 else r


def build_ducts():
    """Inlet trunks / engine nacelles: the skin with a sharp lip at the face, the dark duct inside."""
    skin, duct = Part("paint", "auto"), Part("matte", None, flip=True)
    for d in S.DUCTS:
        y0 = d.y0
        ys = [y for y in np.linspace(y0, d.y1, max(8, int((y0 - d.y1) / 0.25)))][1:]
        signs = (1.0, -1.0) if d.mirror else (1.0,)
        for sign in signs:
            skin.grid([duct_ring(d, y0, 0.90, 0.0, sign=sign), duct_ring(d, y0, 0.945, 0.025, sign=sign),
                       duct_ring(d, y0, 0.985, 0.022, sign=sign)] + [duct_ring(d, y, sign=sign) for y in ys], close=True)
            shades = (0.50, 0.28, 0.11, 0.04)
            dep = d.depth
            deep = [duct_ring(d, y0, 0.90, sign=sign), duct_ring(d, y0, 0.86, -0.15 * dep, sign=sign),
                    duct_ring(d, y0, 0.78, -0.45 * dep, sign=sign), duct_ring(d, y0, 0.68, -0.8 * dep, sign=sign),
                    duct_ring(d, y0, 0.60, -dep, sign=sign)]
            for k in range(len(deep) - 1):
                duct.grid([deep[k], deep[k + 1]], close=True, color=(shades[k],) * 3)
            duct.ngon(deep[-1], (0.01, 0.01, 0.01))
            # the compressor face far down the duct
            c = deep[-1].mean(axis=0)
            fan = Part("metal", None, color=(0.16, 0.16, 0.17))
            duct.extend(fan)
    return skin, duct


def nozzle(n):
    """A convergent-divergent nozzle: flaps over seals, light inner petals, the flame holder deep inside."""
    metal, inner = Part("metal", None), Part("metal", None, flip=True)
    cx, cz, y0, ln, r0, r1 = n["x"], n["z"], n["y0"], n["len"], n["r0"], n["r1"]
    y1 = y0 - ln
    prof = [(y0 - 0.03, r0), (y0 - 0.40 * ln, r0 * 0.985), (y0 - 0.72 * ln, 0.5 * (r0 + r1) * 0.97 + 0.03 * r0), (y1, r1)]
    seg = n.get("seg", 56)

    def circle(y, r, sg=seg):
        t = np.linspace(0.0, 2.0 * math.pi, sg, endpoint=False)
        return np.stack([cx + r * np.cos(t), np.full(sg, y), cz + r * np.sin(t)], axis=1)
    tone = n.get("tone", (0.40, 0.38, 0.36))
    metal.grid([circle(y0 + 0.06, r0, seg), circle(y0 + 0.02, r0 + 0.015, seg), circle(y0 - 0.05, r0 + 0.015, seg),
                circle(y0 - 0.07, r0, seg)], close=True, color=tone)
    metal.grid([circle(y, r - 0.012) for y, r in prof], close=True, color=(0.13, 0.12, 0.12))
    k = n.get("petals", 14)
    rng = np.random.default_rng(int(abs(cx) * 100) + 7)
    hue = n.get("hue", (0.11, 0.04, -0.03))
    for i in range(k):
        a0 = 2.0 * math.pi * (i + 0.5) / k
        half = 0.40 * 2.0 * math.pi / k
        tn = rng.uniform(-0.025, 0.025)
        strips = []
        for y, r in prof:
            t = a0 + half * np.array([-1.0, -1.0, -0.4, 0.4, 1.0, 1.0])
            rr = r + np.array([-0.012, 0.0, 0.004, 0.004, 0.0, -0.012])
            strips.append(np.stack([cx + rr * np.cos(t), np.full(6, y), cz + rr * np.sin(t)], axis=1))
        for j in range(len(strips) - 1):
            heat = j / (len(strips) - 2)
            base = n.get("base", 0.26)
            metal.grid(strips[j:j + 2], color=(base + tn + hue[0] * heat, base + tn + hue[1] * heat, base + 0.02 + tn + hue[2] * heat))
    metal.grid([circle(y1, r1 + 0.004), circle(y1 - 0.012, r1 - 0.009), circle(y1, r1 - 0.025)], close=True, color=(0.20, 0.18, 0.17))
    ri = r1 - 0.025
    wall = [(y1, ri, 0.52), (y1 + 0.3 * ln, ri * 0.9, 0.45), (y1 + 0.55 * ln, ri * 0.78, 0.30), (y0 - 0.05, ri * 0.92, 0.15),
            (y0 + 0.30, ri * 1.0, 0.06), (y0 + 0.9, ri * 1.0, 0.03)]
    for (ya, ra, sa), (yb, rb, _sb) in zip(wall, wall[1:]):
        inner.grid([circle(ya, ra, 40), circle(yb, rb, 40)], close=True, color=(sa, sa * 0.92, sa * 0.84))
    inner.ngon(circle(y0 + 0.9, ri, 40), (0.02, 0.02, 0.02))
    holder = Part("metal", None, color=(0.10, 0.09, 0.085))
    yh = y0 + 0.35
    for rr in (0.35 * ri, 0.68 * ri):
        t = np.linspace(0.0, 2.0 * math.pi, 29)
        tube(holder, np.stack([cx + rr * np.cos(t), np.full(29, yh), cz + rr * np.sin(t)], axis=1), 0.015, 6, caps=False)
    tube(holder, [(cx, yh + 0.15, cz), (cx, yh - 0.10, cz), (cx, yh - 0.40, cz)], [0.34 * ri, 0.26 * ri, 0.012], 14, (0.13, 0.12, 0.11))
    return [metal, inner, holder]


def build_canopy():
    """The glass and its frames: closed box sections, so they are solid from inside the cockpit too."""
    glass, frame = Part("glass", None), Part("matte", None)
    expo = CFG["canopy"].get("expo", 2.25)

    def arc(y, grow=0.0, a0=-14.0, a1=194.0, seg=36):
        w, zs = S.canopy_sill(y)
        h = float(S.CANOPY_H(y)) + grow
        w += grow
        t = np.radians(np.linspace(a0, a1, seg + 1))
        c, s = np.cos(t), np.sin(t)
        z = np.where(s >= 0, zs + h * np.abs(s) ** (2.0 / expo), zs + 0.3 * w * s)
        return np.stack([w * np.sign(c) * np.abs(c) ** (2.0 / expo), np.full(len(t), y), z], axis=1)
    y0, y1 = S.CANOPY_Y0, S.CANOPY_Y1
    ys = np.concatenate([np.linspace(y1, y1 - 0.3, 8), np.linspace(y1 - 0.3, y0, 44)[1:]])
    glass.grid([arc(y) for y in ys])
    col = CFG["canopy"].get("frame", (0.20, 0.21, 0.22))
    fw = CFG["canopy"].get("frame_w", 0.055)
    for b in S.ARCHES:
        rings = [arc(b + fw, 0.004, -4, 184), arc(b + fw, 0.020, -4, 184), arc(b - fw, 0.020, -4, 184), arc(b - fw, 0.004, -4, 184)]
        frame.grid(np.array(rings + [rings[0]]), color=col)
    for side in (1.0, -1.0):
        rails = []
        for y in np.linspace(y0 + 0.12, y1 - 0.40, 46):
            w, zs = S.canopy_sill(y)
            t = np.radians(np.array([-6.0, -2.0, 4.0, 9.0]))
            g = np.array([0.004, 0.018, 0.018, 0.004])
            h = float(S.CANOPY_H(y))
            p = np.stack([side * (w + g) * np.cos(t), np.full(4, y),
                          zs + (h + g) * np.maximum(np.sin(t), 0.0) ** (2.0 / expo) + 0.3 * w * np.minimum(np.sin(t), 0.0)], axis=1)
            rails.append(np.vstack([p, p[:1]]))
        frame.grid(np.array(rails).transpose(1, 0, 2).transpose(1, 0, 2), color=col)
    return glass, frame


# ================================================================ cockpit
def clamp_under_canopy(parts, margin=0.015):
    """Every vertex at least ``margin`` under the glass / skin: the last guard against parts poking out."""
    moved = 0
    for p in parts:
        nv = []
        for v in p.verts:
            v = v.copy()
            for i in range(len(v)):
                lim = S.skin_limit(v[i, 0], v[i, 1]) - margin
                if v[i, 2] > lim:
                    v[i, 2] = lim
                    moved += 1
            nv.append(v)
        p.verts = nv
        p.uvverts = [v.copy() for v in nv]
    return moved


def ejection_seat(part, y_back, z_seat, style, recline=17.0):
    """ACES II / K-36D / Martin-Baker style seat, reclined (the canopy fit lowers it if needed)."""
    r = rot_x(recline)
    cush = style.get("cushion", (0.22, 0.24, 0.20))
    frame_c = style.get("frame", (0.15, 0.16, 0.17))
    head_c = style.get("head", (0.10, 0.10, 0.11))
    box(part, (0.0, y_back + 0.24, z_seat), (0.22, 0.24, 0.08), color=frame_c)
    box(part, (0.0, y_back + 0.26, z_seat + 0.095), (0.19, 0.20, 0.03), color=cush)
    back = np.array([0.0, y_back, z_seat + 0.02])
    up = r @ np.array([0.0, 0.0, 1.0])
    fwd = r @ np.array([0.0, 1.0, 0.0])
    box(part, back + up * 0.40 - fwd * 0.04, (0.22, 0.06, 0.42), r, frame_c)
    box(part, back + up * 0.38 + fwd * 0.035, (0.17, 0.03, 0.33), r, cush)
    if style.get("kind") == "k36":                       # K-36D: the tall head box with the side wings
        box(part, back + up * 0.90, (0.16, 0.09, 0.14), r, head_c)
        for s in (1.0, -1.0):
            box(part, back + up * 0.86 + fwd * 0.05 + np.array([s * 0.15, 0, 0]), (0.025, 0.06, 0.10), r, head_c)
        box(part, back + up * 0.72 - fwd * 0.10, (0.12, 0.05, 0.20), r, (0.30, 0.31, 0.30))
    else:
        box(part, back + up * 0.88, (0.14, 0.08, 0.12), r, head_c)
    for s in (1.0, -1.0):                                 # side rails and the arm rests
        box(part, back + up * 0.45 - fwd * 0.03 + np.array([s * 0.235, 0, 0]), (0.012, 0.075, 0.50), r, (0.30, 0.31, 0.32))
        box(part, (s * 0.235, y_back + 0.24, z_seat + 0.06), (0.012, 0.25, 0.10), color=(0.30, 0.31, 0.32))
    # the yellow and black firing handle between the knees
    tube(part, [(-0.08, y_back + 0.46, z_seat + 0.09), (-0.08, y_back + 0.50, z_seat + 0.16), (0.08, y_back + 0.50, z_seat + 0.16),
                (0.08, y_back + 0.46, z_seat + 0.09)], 0.012, 8, (0.80, 0.68, 0.10))
    # harness straps over the cushion
    for s in (1.0, -1.0):
        box(part, back + up * 0.40 + fwd * 0.07 + np.array([s * 0.08, 0, 0]), (0.025, 0.006, 0.30), r, (0.28, 0.30, 0.22))


def osb_bezel(room, c0, n, up, right, half, tilt, col, keys=5):
    """A display bezel with the push buttons around it (the "OSBs" of an MFD)."""
    box(room, c0 + n * 0.012, (half + 0.022, 0.012, half + 0.022), tilt, col)
    for k in range(keys):
        f = (k - (keys - 1) / 2) / ((keys - 1) / 2) * (half - 0.012)
        for a, b in ((right, up), (-right, up), (up, right), (-up, right)):
            p = c0 + n * 0.026 + a * (half + 0.012) + b * f
            box(room, p, (0.006, 0.004, 0.006), tilt, (0.32, 0.33, 0.33))


def instrument_panel(room, screens, statics, y_panel, z_c, w, live, style):
    """The front panel: displays in the Super Hornet arrangement (live) or a simpler set (rear cockpit)."""
    tilt_deg = style.get("tilt", 16.0)
    tilt = rot_x(-tilt_deg)
    c0 = np.array([0.0, y_panel, z_c])
    n = tilt @ np.array([0.0, -1.0, 0.0])
    up = tilt @ np.array([0.0, 0.0, 1.0])
    right = np.array([1.0, 0.0, 0.0])
    pc = style.get("panel", (0.10, 0.105, 0.11))
    bz = style.get("bezel", (0.06, 0.06, 0.065))
    box(room, c0 - n * 0.04, (w, 0.04, 0.20), tilt, pc)
    # the lower panel down to the floor (knee panel)
    box(room, c0 - n * 0.06 - up * 0.30, (w * 0.82, 0.05, 0.14), rot_x(-tilt_deg * 0.4), pc)
    layout = style.get("layout", "hornet")
    big = layout == "twin"                                 # two large displays side by side (Su-35 / Typhoon / Rafale)
    if big:
        dd = [("screen_ddi_l", -0.125, 0.025, 0.098), ("screen_ddi_r", 0.125, 0.025, 0.098),
              ("screen_ampcd", 0.0, -0.145, 0.062)]
    else:
        dd = [("screen_ddi_l", -0.165, 0.035, 0.074), ("screen_ddi_r", 0.165, 0.035, 0.074),
              ("screen_ampcd", 0.0, -0.105, 0.078)]
    for name, cx, cz, half in dd:
        ctr = c0 + right * cx + up * cz
        osb_bezel(room, ctr, n, up, right, half, tilt, bz)
        scr = Part("screen", None)
        box(scr, ctr + n * 0.026, (half, 0.002, half), tilt)
        (screens.__setitem__(name, scr) if live else statics.append(scr))
    # up front controller / data entry display at the top centre, keys on both sides
    c = c0 + up * (0.125 if not big else 0.135)
    box(room, c + n * 0.018, (0.085, 0.018, 0.048), tilt, bz)
    scr = Part("screen", None)
    box(scr, c + n * 0.037, (0.060, 0.002, 0.036), tilt)
    (screens.__setitem__("screen_ufcd", scr) if live else statics.append(scr))
    for k in range(10):
        p = c + n * 0.038 + right * (-0.072 if k < 5 else 0.072) + up * (0.030 - 0.015 * (k % 5))
        box(room, p, (0.006, 0.004, 0.005), tilt, (0.32, 0.33, 0.33))
    # standby gauges, warning lights, switches
    rng = np.random.default_rng(abs(int(y_panel * 100)) + 7)
    gauges = style.get("gauges", [(-0.27, -0.07), (-0.27, -0.16), (0.27, -0.07), (0.27, -0.16)])
    for gx, gz in gauges:
        if abs(gx) > w - 0.04:
            continue
        p = c0 + right * gx + up * gz
        tube(room, [p - n * 0.01, p + n * 0.022], 0.034, 16, (0.05, 0.05, 0.055))
        g = Part("matte", None, color=(0.86, 0.86, 0.80))
        tube(room, [p + n * 0.022, p + n * 0.024], 0.026, 16, style.get("dial", (0.07, 0.07, 0.07)))
        box(room, p + n * 0.026 + up * 0.008, (0.002, 0.001, 0.016), tilt, (0.85, 0.85, 0.80))
        room.extend(g)
    for _ in range(22):
        x, z = rng.uniform(-w + 0.04, w - 0.04), rng.uniform(-0.19, 0.19)
        if any(abs(x - cx) < half + 0.05 and abs(z - cz) < half + 0.05 for _n, cx, cz, half in dd) or (abs(x) < 0.11 and z > 0.08):
            continue
        p = c0 + right * x + up * z
        col = (0.30, 0.31, 0.32) if rng.random() < 0.7 else ((0.75, 0.55, 0.10) if rng.random() < 0.5 else (0.55, 0.12, 0.08))
        box(room, p + n * 0.006, (0.012, 0.006, 0.010), tilt, col)
    return c0, n, up


def build_cockpit():
    """Tub, sills, seats, instrument panels, glareshields, HUD, side consoles, stick and throttle, pedals: an F-16
    class cockpit for each seat, every part kept under the glass."""
    style = CK.get("style", {})
    tubc = style.get("tub", (0.27, 0.29, 0.30))
    tub, room = Part("matte", None, flip=True, color=tubc), Part("matte", None, color=tubc)
    hudglass = Part("hud", None)
    y0, y1 = S.COCKPIT_Y0, S.COCKPIT_Y1
    seats = sorted(S.SEATS, reverse=True)                   # front seat first
    eyes = []
    for sy in seats:
        ey = sy + 0.30
        eyes.append((ey, S.canopy_z(ey, 0.0) - CK.get("head_clear", 0.27)))
    floor = min(ez for _y, ez in eyes) - 1.10
    ys = np.linspace(y0, y1, 30)
    wy = lambda y: S.cockpit_w(y) - 0.01                    # noqa: E731
    sill_out = lambda y: min(wy(y) + 0.075, float(S.CANOPY_W(y)) - 0.012)   # noqa: E731
    rim = [(wy(y), y, float(S.body_top(y, wy(y))[0]) + 0.004) for y in ys]
    rim = np.array(rim + [(-x, y, z) for x, y, z in rim[::-1]])
    low = rim.copy()
    low[:, 2] = floor
    tub.grid([rim, low], close=True)
    tub.ngon(low, (0.20, 0.21, 0.22))
    sill = Part("matte", None, color=style.get("sill", (0.24, 0.25, 0.26)))
    for side in (1.0, -1.0):
        strips = []
        for y in np.linspace(y0 - 0.07, y1 + 0.07, 40):
            xs = np.array([wy(y) - 0.045, wy(y) - 0.045, sill_out(y), sill_out(y)])
            top = S.body_top(y, np.array([wy(y) - 0.045, sill_out(y)])) + 0.012
            strips.append(np.stack([side * xs, np.full(4, y), [top[0] - 0.05, top[0], top[1], top[1] - 0.02]], axis=1))
        sill.grid(strips)
    for ya, yb in ((y0 - 0.07, y0 + 0.05), (y1 - 0.05, y1 + 0.07)):
        strips = []
        for x in np.linspace(-1.0, 1.0, 14) * min(sill_out(ya), sill_out(yb)):
            za, zb = float(S.body_top(ya, abs(x))[0]) + 0.012, float(S.body_top(yb, abs(x))[0]) + 0.012
            strips.append([(x, ya, za - 0.03), (x, ya, za), (x, yb, zb), (x, yb, zb - 0.05)])
        sill.grid(strips)
    screens, statics = {}, []
    seat = Part("matte", None)
    sstyle = style.get("seat", {})
    REFS["panels"] = []
    for k, (sy, (ey, ez)) in enumerate(zip(seats, eyes)):
        live = k == 0
        z_seat = ez - 0.93
        ejection_seat(seat, sy, z_seat, sstyle, style.get("recline", 17.0))
        # instrument panel ahead of the seat: in front of the next seat's head box in a tandem cockpit
        yp = sy + CK.get("panel_dist", 0.90)
        if k == 0:
            yp = min(yp, y1 - 0.10)
            if yp - ey < 0.55:
                print("WARNING: the front panel is only %.2f m ahead of the eye" % (yp - ey))
        else:
            yp = min(yp, seats[k - 1] - 0.16)
        wp = min(S.cockpit_w(yp) - 0.02, 0.34)
        zc = ez - CK.get("panel_drop", 0.50)
        c0, n, up = instrument_panel(room, screens, statics, yp, zc, wp, live, style)
        REFS["panels"].append(c0)
        # glareshield hood over the panel, under the glass
        hood = []
        hw = min(wp + 0.03, float(S.CANOPY_W(yp + 0.15)) - 0.07)
        ztop = zc + 0.25
        for x in np.linspace(-hw, hw, 11):
            zz = ztop + 0.03 * (1.0 - (x / hw) ** 2)
            ya, yb = yp - 0.03, yp + 0.30
            za, zb = min(zz, S.skin_limit(x, ya) - 0.05), min(zz - 0.04, S.skin_limit(x, yb) - 0.05)
            hood.append([(x, ya, za - 0.025), (x, ya, za), (x, yb, zb), (x, yb, zb - 0.025)])
        room.grid(hood, color=(0.05, 0.05, 0.055))
        if live and CK.get("hud", True):
            # HUD: the projector under the glareshield, the combiner glass in a frame on top of it
            yh = yp + 0.13
            zb = ztop + 0.01
            box(room, (0.0, yh, zb - 0.02), (0.075, 0.09, 0.035), color=(0.07, 0.07, 0.08))
            top = min(ez + 0.03, S.skin_limit(0.0, yh - 0.04) - 0.06, S.skin_limit(0.07, yh) - 0.06)
            hh = max(0.04, 0.5 * (top - zb))
            r = rot_x(20.0)
            for side in (1.0, -1.0):
                box(room, (side * 0.074, yh - 0.03, zb + hh), (0.004, 0.012, hh), r, (0.07, 0.07, 0.08))
            box(room, (0.0, yh - 0.03, zb + 2 * hh), (0.078, 0.012, 0.004), r, (0.07, 0.07, 0.08))
            box(hudglass, (0.0, yh - 0.03, zb + hh), (0.070, 0.002, hh - 0.005), r)
        # side consoles beside the seat, with panels and knobs
        cw = S.cockpit_w(sy + 0.2) - 0.075
        for side in (1.0, -1.0):
            zt = ez - 0.62
            box(room, (side * cw, sy + 0.22, (zt + floor) / 2), (0.065, 0.48, (zt - floor) / 2))
            box(room, (side * cw, sy + 0.22, zt + 0.004), (0.060, 0.46, 0.006), color=(0.09, 0.09, 0.10))
            rng = np.random.default_rng(abs(int(sy * 77 + side * 5)) + 11)
            for _ in range(9):
                p = (side * cw + rng.uniform(-0.04, 0.04), sy + rng.uniform(-0.15, 0.6), zt + 0.012)
                tube(room, [p, (p[0], p[1], p[2] + 0.018)], 0.008, 8, (0.30, 0.31, 0.32) if rng.random() < 0.8 else (0.70, 0.55, 0.12))
        # throttle on the left console, stick in the middle (or on the right console)
        zt = ez - 0.62
        for dx in ((-0.015, 0.025) if CFG.get("engines", 2) > 1 else (0.0,)):
            tube(room, [(-cw + 0.01 + dx, sy + 0.40, zt + 0.01), (-cw + 0.01 + dx, sy + 0.47, zt + 0.11)], 0.012, 8, (0.08, 0.08, 0.09))
            box(room, (-cw + 0.01 + dx, sy + 0.48, zt + 0.13), (0.018, 0.03, 0.025), color=(0.07, 0.07, 0.08))
        if CK.get("stick", "centre") == "side":
            tube(room, [(cw - 0.01, sy + 0.42, zt + 0.01), (cw - 0.01, sy + 0.43, zt + 0.14)], [0.014, 0.020], 8, (0.07, 0.07, 0.08))
        else:
            sb = (0.0, sy + 0.62, z_seat + 0.02)
            tube(room, [sb, (0.0, sy + 0.62, z_seat + 0.30), (0.0, sy + 0.60, z_seat + 0.40)], [0.016, 0.014, 0.013], 8, (0.08, 0.08, 0.09))
            box(room, (0.0, sy + 0.60, z_seat + 0.44), (0.022, 0.026, 0.045), color=(0.07, 0.07, 0.08))
            tube(room, [(0.0, sy + 0.62, z_seat - 0.02), (0.0, sy + 0.62, z_seat + 0.05)], 0.05, 12, (0.12, 0.12, 0.13))
        # rudder pedals
        for side in (1.0, -1.0):
            box(room, (side * 0.13, yp - 0.12, floor + 0.14), (0.05, 0.02, 0.08), rot_x(20.0), (0.20, 0.21, 0.22))
    # bulkhead behind the last seat
    yb = y0 + 0.05
    box(room, (0.0, yb, floor + 0.35), (S.cockpit_w(yb) - 0.02, 0.05, 0.35), color=(0.18, 0.19, 0.20))
    # mirrors on the canopy bow
    if S.ARCHES:
        b = S.ARCHES[0] - 0.09
        for x in (-0.20, 0.0, 0.20):
            z = S.canopy_z(b, x) - 0.06
            box(room, (x, b, z), (0.07 if x == 0 else 0.05, 0.006, 0.022), color=(0.12, 0.12, 0.13))
    drop = L.fit_under_canopy([seat], S, margin=0.07)
    moved = clamp_under_canopy([room, sill, seat, hudglass] + statics + list(screens.values()))
    print("cockpit: seat lowered by %.3f m, %d vertices pulled under the glass" % (drop, moved))
    REFS["eye"] = (0.0, eyes[0][0], eyes[0][1])
    REFS["floor"] = floor
    return [tub, room, sill, seat] + statics, hudglass, screens


REFS = {}


# ================================================================ landing gear
def rot_between(a, b):
    a, b = unit(a), unit(b)
    ax = np.cross(a, b)
    s = np.linalg.norm(ax)
    if s < 1e-9:
        return np.array([1.0, 0.0, 0.0]), 0.0
    return ax / s, math.atan2(s, float(np.dot(a, b)))


def plan_gear():
    """Where the legs hinge, how they fold, the wells they fold into (computed from the wheel positions)."""
    gc = CFG["gear"]
    zg = S.Z_GROUND
    plan = {}
    cut, painted = [], []
    n = gc["nose"]
    r = n["r"]
    yh = n["y"] + n.get("trail", 0.08)
    zl = S.lower_z(0.0, yh)
    fold = n.get("fold", "aft")
    zh = zl + r + 0.08 if not n.get("twin") else zl + r + 0.08
    leg = zh - (zg + r)
    sgn = -1.0 if fold == "aft" else 1.0
    yw0, yw1 = sorted([yh, yh + sgn * (leg + r + 0.06)])
    hw = (n["w"] * (2.2 if n.get("twin") else 1.0)) / 2 + 0.07
    rect = (-hw, hw, yw0 - 0.04, yw1 + 0.04)
    plan["nose"] = dict(hinge=np.array([0.0, yh, zh]), wheel=np.array([0.0, n["y"], zg + r]), fold=np.array([0.0, sgn, 0.0]),
                        rect=rect, r=r, w=n["w"], twin=n.get("twin", False))
    cut.append((rect, False))
    m = gc["main"]
    r, x, y = m["r"], m["x"], m["y"]
    fold = m.get("fold", "in")
    xh = m.get("hinge_x", x - 0.12 if fold != "out" else x + 0.1)
    yh = m.get("hinge_y", y + 0.15 if fold != "fwd" else y - 0.25)
    zl = S.lower_z(xh, yh, strict=True)
    if zl > 5.0:                       # under the wing
        zl = float(S.wing_z(xh)) - float(S.wing_t(xh)) * float(S.wing_chord(xh)) * 0.4
    zh = zl + m.get("hinge_up", 0.12)
    d0 = unit(np.array([x, y, zg + r]) - np.array([xh, yh, zh]))
    leg = float(np.linalg.norm(np.array([x, y, zg + r]) - np.array([xh, yh, zh])))
    d1 = {"in": np.array([-1.0, 0.0, 0.08]), "out": np.array([1.0, 0.0, 0.08]), "fwd": np.array([0.0, 1.0, 0.06]),
          "aft": np.array([0.0, -1.0, 0.06])}[fold]
    d1 = unit(d1)
    wheel_c = np.array([x + m.get("offset", 0.0), y, zg + r])
    hinge = np.array([xh, yh, zh])
    folded = hinge + d1 * (leg + r * 0.3)
    pts = np.array([hinge, folded + np.array([r, r, 0]), folded - np.array([r, r, 0])])
    rect = (min(pts[:, 0]) - 0.05, max(pts[:, 0]) + 0.05, min(pts[:, 1]) - 0.05, max(pts[:, 1]) + 0.05)
    plan["main"] = dict(hinge=hinge, wheel=wheel_c, d0=d0, d1=d1, rect=rect, r=r, w=m["w"], fold=fold, leg=leg,
                        twin=m.get("twin", False))
    painted.append(rect)
    GEAR.update(cut=cut, painted=painted, plan=plan)
    return plan


def leg_door(rect, hinge, axis, angle, sign=1.0):
    """A door fixed to the leg: modelled flush with the skin over the well (UVs from there), then swung down with
    the leg.  -> part (in the leg's rest pose)"""
    x0, x1, y0, y1 = rect
    xs, ys = np.linspace(x0, x1, 6), np.linspace(y0, y1, 6)
    flush = []
    for yy in ys:
        row = []
        for xx in xs:
            zz = S.lower_z(sign * xx, yy, strict=True)
            if zz > 5.0:
                zz = float(S.wing_z(xx)) - f16_shape.yt(np.clip((S.wing_le(xx) - yy) / S.wing_chord(xx), 0, 1), S.wing_t(xx)) * S.wing_chord(xx)
            row.append((sign * xx, yy, float(zz) - 0.004))
        flush.append(row)
    flush = np.array(flush)
    thick = flush + np.array([0.0, 0.0, 0.02])
    closed = np.concatenate([flush.reshape(-1, 3), thick.reshape(-1, 3)])
    opened = rotate_about(closed, hinge, axis, -math.radians(angle))
    part = Part("paint", "tb")
    nx = len(xs)
    faces = []
    for i in range(len(ys) - 1):
        for j in range(nx - 1):
            a = i * nx + j
            faces.append((a, a + 1, a + nx + 1, a + nx))
            o = len(xs) * len(ys)
            faces.append((o + a, o + a + nx, o + a + nx + 1, o + a + 1))
    part.add(opened, faces, uv_verts=closed)
    return part


def gear_leg(hinge, wheel_c, r, w, twin, sc=1.0, door=None):
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    axle = wheel_c + np.array([-(0.5 * w + 0.06) if not twin else 0.0, 0.0, 0.04 * sc]) * (1.0 if wheel_c[0] >= 0 else -1.0)
    if twin:
        axle = wheel_c.copy()
    knee = hinge + (axle - hinge) * 0.55
    tube(white, [hinge, knee], [0.075 * sc, 0.068 * sc], 12)
    tube(metal, [knee, axle + np.array([0, 0, 0.06])], 0.050 * sc, 12)
    tube(white, [knee + np.array([0, 0.0, 0.05]), hinge + np.array([0.0, 0.35 * sc, 0.0])], 0.03 * sc, 10)
    if twin:
        for s in (1.0, -1.0):
            c = wheel_c + np.array([s * (0.5 * w + 0.03), 0.0, 0.0])
            wheel(tire, white, c, r, w)
        tube(metal, [wheel_c - np.array([w + 0.05, 0, 0]), wheel_c + np.array([w + 0.05, 0, 0])], 0.03 * sc, 10)
    else:
        tube(metal, [axle, wheel_c], 0.04 * sc, 10)
        wheel(tire, white, wheel_c, r, w)
    parts = [tire, white, metal]
    return parts


def build_gear():
    plan = GEAR["plan"]
    zg = S.Z_GROUND
    moving = {}
    n = plan["nose"]
    hinge, wc = n["hinge"], n["wheel"]
    parts = gear_leg(hinge, wc, n["r"], n["w"], n["twin"], 0.8)
    lamps = Part("light_white", None)
    lp = hinge + (wc - hinge) * 0.35 + np.array([0.07, 0.06, 0.0])
    tube(parts[1], [lp - np.array([0, 0.03, 0]), lp + np.array([0, 0.04, 0])], [0.04, 0.045], 12, C_GREY)
    lamps.ngon([(lp[0] + 0.038 * math.cos(a), lp[1] + 0.042, lp[2] + 0.038 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    d0 = unit(wc - hinge)
    axis, ang = retract_rotation(hinge, d0, (1, 0, 0), n["fold"], (1, 0, 0))
    moving["gear_nose"] = (parts + [lamps], hinge, axis, ang, "retract")
    x0, x1, y0, y1 = n["rect"]
    ym = 0.5 * (y0 + y1)
    z_nose = lambda x: S.lower_z(abs(x), ym)              # noqa: E731
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, ax, a = gear_door(side * x1, side * 0.003, y0, y1, z_nose)
        moving["door_nose_" + name] = ([part], h, ax, a, "door")
    wells = [gear_well(n["rect"], lambda x, y: S.lower_z(x, y), n["hinge"][2] + n["r"] + 0.05)]

    m = plan["main"]
    hinge, wc = m["hinge"], m["wheel"]
    parts = gear_leg(hinge, wc, m["r"], m["w"], m["twin"], 1.0)
    d0, d1 = m["d0"], m["d1"]
    a0 = np.array([1.0, 0.0, 0.0])
    ax, an = rot_between(d0, d1)
    a1 = rotate_about(a0[None, :], np.zeros(3), ax, an)[0]
    if m["fold"] in ("fwd", "aft"):
        a1 = unit(np.array([0.0, 0.0, 1.0]) - d1 * d1[2])          # the wheel turns to lie flat
    axis, ang = retract_rotation(hinge, d0, a0, d1, a1)
    door = leg_door(m["rect"], hinge, axis, ang)
    moving["gear_main_R"] = (parts + [door], hinge, axis, ang, "retract")
    mm = np.array([-1.0, 1.0, 1.0])
    axis_l, ang_l = retract_rotation(hinge * mm, d0 * mm, a0 * mm, d1 * mm, a1 * mm)
    moving["gear_main_L"] = ([p.mirrored() for p in parts + [door]], hinge * mm, axis_l, ang_l, "retract")
    REFS["gear_main"] = wc
    REFS["gear_nose"] = n["wheel"]
    return dict(moving=moving, wells=wells)


# ================================================================ weapons, details, lights
def build_stores():
    """Wing tip rails, two pylons under each wing, launchers under the fuselage.  -> (part, {station: point})"""
    st = CFG.get("stores")
    part = Part("matte", None, color=C_LIGHT)
    points = {}
    if not st:
        return part, points

    def rail(x, z, y_front, y_back, hw=0.04, hh=0.045):
        ys = [y_front, y_front - 0.10, y_front - 0.35, y_back + 0.25, y_back]
        k = [0.25, 0.75, 1.0, 1.0, 0.55]
        rings = [superellipse(y, z, hw * f, hh * f, 4.0, 4.0, 12, x) for y, f in zip(ys, k)]
        part.grid(rings, close=True)
        part.ngon(rings[0])
        part.ngon(rings[-1])
    if st.get("tip", True):
        x = S.X_TIP
        le, te = float(S.wing_le(x)), float(S.wing_te(x))
        z = float(S.wing_z(x))
        rail(x + 0.03, z - 0.01, le + 0.35, te - 0.25, 0.035, 0.05)
        points[8] = (x + 0.03, 0.5 * (le + te) - 0.05, z - 0.15)
    pylons = [(7, st["mid"]), (6, st["inner"])]
    if not st.get("tip", True):
        pylons.insert(0, (8, st["outer"]))
    for stn, x in pylons:
        le, te = float(S.wing_le(x)), float(S.wing_te(x))
        if S.FLAP[0] <= x <= S.AIL[1]:
            te += float(S.flap_chord(x)) if x < S.FLAP[1] else float(S.ail_chord(x))
        zw = float(S.wing_z(x)) - float(S.wing_t(x)) * float(S.wing_chord(x)) * 0.25
        depth = st.get("depth", 0.34)
        length = min(le - te - 0.3, 2.6)
        yc = 0.5 * (le + te) + 0.1
        prof = [(yc + 0.5 * length, 0.0), (yc + 0.5 * length - 0.25, depth), (yc - 0.5 * length + 0.3, depth), (yc - 0.5 * length, 0.0)]
        prism(part, (x, 0.0, zw + 0.03), (0, 1, 0), (0, 0, -1), prof, 0.08)
        rail(x, zw - depth - 0.03, yc + 1.0, yc - 0.9)
        points[stn] = (x, yc - 0.05, zw - depth - 0.17)
    fx, fy = st["fus"]
    z = S.lower_z(fx, fy)
    box(part, (fx, fy, z - 0.02), (0.035, 0.85, 0.025), color=C_GREY)
    points[5] = (fx, fy - 0.05, z - 0.15)
    return part, points


def build_details():
    grey, metal = Part("matte", None, color=C_GREY), Part("metal", None, color=C_STEEL)
    dk = Part("matte", None, color=(0.05, 0.05, 0.055))
    det = CFG.get("details", {})
    blade = [(0.0, 0.0), (0.16, 0.0), (0.13, 0.15), (0.07, 0.15)]
    for y, up in det.get("blades", [(S.CANOPY_Y0 - 0.6, True), (1.0, False)]):
        z = float(S.body_top(y, 0.0)[0]) - 0.02 if up else S.lower_z(0.0, y) + 0.02
        prism(grey, (0.0, y, z), (0, -1, 0), (0, 0, 1 if up else -1), np.array(blade) * 1.2, 0.02)
    for y, x, z in det.get("probes", []):
        for side in (1.0, -1.0):
            tube(metal, [(side * (x - 0.03), y, z), (side * (x + 0.06), y + 0.02, z), (side * (x + 0.06), y + 0.18, z)],
                 [0.011, 0.009, 0.005], 8)
    if det.get("pitot"):
        ln = det["pitot"]
        zc = float(S.BODY[5](S.Y_NOSE))
        tube(metal, [(0, S.Y_NOSE - 0.05, zc), (0, S.Y_NOSE + 0.3 * ln, zc), (0, S.Y_NOSE + ln, zc)], [0.03, 0.018, 0.008], 10)
    if det.get("irst"):
        x, y, r = det["irst"]
        z = float(S.body_top(y, abs(x))[0])
        rings = []
        for lat in np.linspace(-0.2, 0.5 * math.pi, 7):
            t = np.linspace(0.0, 2.0 * math.pi, 18, endpoint=False)
            rings.append(np.stack([x + r * math.cos(lat) * np.cos(t), y + r * math.cos(lat) * np.sin(t), np.full(18, z + r * math.sin(lat))], axis=1))
        g = Part("glass", None)
        g.grid(rings, close=True)
        g.ngon(rings[-1])
        tube(dk, [(x, y, z - 0.08), (x, y, z + 0.02)], r * 1.05, 18)
        DET_EXTRA.append(g)
    if det.get("gun"):
        x, y = det["gun"][:2]
        low = len(det["gun"]) > 2 and det["gun"][2] == "low"
        z = S.lower_z(x, y) if low else float(S.body_top(y, abs(x))[0])
        tube(dk, [(x, y - 0.35, z + (0.01 if low else -0.01)), (x, y + 0.05, z - (0.005 if low else -0.005))], [0.04, 0.03], 10, squash=0.6)
        REFS["gun"] = (x, y + 0.08, z + (-0.02 if low else 0.02))
    if det.get("refuel"):
        pts = det["refuel"]
        tube(metal, pts, [0.045] * (len(pts) - 1) + [0.03], 12, (0.55, 0.56, 0.58))
    for (x, y, z, ln) in det.get("stacks", []):
        for side in (1.0, -1.0):
            tube(dk, [(side * x, y, z), (side * (x + 0.10), y - 0.12, z), (side * (x + 0.16), y - ln, z - 0.02)], [0.07, 0.07, 0.075], 14)
    if det.get("hook"):
        y0, y1 = det["hook"]
        z0 = S.lower_z(0.0, y0) + 0.03
        tube(grey, [(0, y0, z0), (0, y1, z0 - 0.12)], 0.04, 8, (0.80, 0.80, 0.80))
        box(grey, (0, y1 - 0.03, z0 - 0.15), (0.05, 0.06, 0.04), color=(0.15, 0.15, 0.15))
    for side in (1.0, -1.0):                             # static dischargers on the wing tips
        for x in (S.X_TIP - 0.25, S.X_TIP - 0.8):
            a = np.array([side * x, float(S.wing_te(x)), float(S.wing_z(x))])
            tube(grey, [a + (0, 0.02, 0), a + (0, -0.15, 0)], 0.004, 5, C_DARK)
    return [grey, metal, dk]


DET_EXTRA = []


def speed_brakes():
    """Dorsal speed brake (hinged at its front edge) if the jet has one.  -> {name: (part, hinge, axis)}"""
    out = {}
    sb = CFG.get("speed_brake")
    if not sb:
        return out
    part = Part("paint", "tb")
    y0, y1, w = sb["y0"], sb["y1"], sb["w"]
    rings = []
    for y in np.linspace(y0, y1, 8):
        xs = np.linspace(-w, w, 9)
        zs = S.body_top(y, np.abs(xs)) + 0.004
        rings.append(np.stack([xs, np.full(9, y), zs], axis=1))
    rings = np.array(rings)
    part.grid(rings)
    thick = rings - np.array([0.0, 0.0, 0.03])
    part.grid(thick[:, ::-1])
    for i in (0, -1):
        part.grid([rings[i], thick[i]])
    part.grid([rings[:, 0], thick[:, 0]])
    part.grid([thick[:, -1], rings[:, -1]])
    zh = float(S.body_top(y0, 0.0)[0])
    out["sb_dorsal"] = (part, np.array([0.0, y0, zh]), (-1.0, 0.0, 0.0))
    return out


def lamp(part, c, r=0.03, stretch=(1.0, 2.0, 1.0)):
    rings = []
    for lat in np.linspace(-0.5 * math.pi, 0.5 * math.pi, 7)[1:-1]:
        t = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False)
        rings.append(np.asarray(c) + r * np.asarray(stretch) * np.stack(
            [np.cos(lat) * np.cos(t), np.cos(lat) * np.sin(t), np.full(10, math.sin(lat))], axis=1))
    part.grid(rings, close=True)
    part.ngon(rings[0])
    part.ngon(rings[-1])


def build_lights():
    out = {}
    x = S.X_TIP - 0.05
    for name, mat, side in (("light_nav_R", "light_green", 1.0), ("light_nav_L", "light_red", -1.0)):
        p = Part(mat, None)
        c = (side * x, float(S.wing_le(x)) - 0.30, float(S.wing_z(x)))
        lamp(p, c, 0.03, (0.8, 2.0, 0.7))
        out[name] = p
        REFS["nav_" + ("R" if side > 0 else "L")] = c
    p = Part("light_white", None)
    tails = []
    if S.FIN is not None:
        f = S.FIN
        for sign in ((1.0, -1.0) if f.twin else (1.0,)):
            tip = f.point(sign, np.array(f.s1 - 0.05), np.array(float(f.te(f.s1)) + 0.10), np.array(0.0))
            lamp(p, tip, 0.035, (1.0, 1.0, 1.0))
            tails.append(tip)
    out["light_tail"] = p
    REFS["tail_lights"] = tails
    return out


# ============================================================ assembling
def build():
    L.begin(ID, TEX, uv_coords, ID.upper(), glass=S.CANOPY_TINT, glass_alpha=CFG["canopy"].get("alpha", 0.30))
    collection = L.CTX["collection"]
    plan_gear()
    body = build_body()
    wing, flap, ail, lef = build_wing()
    fins, rudders = build_fins()
    ducts, dark = build_ducts()
    glass, frame = build_canopy()
    cockpit, hud, screens = build_cockpit()
    stores, points = build_stores()
    gear_parts = build_gear()
    fus = [body, wing, wing.mirrored(), build_booms(), ducts, dark, frame] + fins + gear_parts["wells"] + build_details()
    if points:
        fus += [stores, stores.mirrored()]
    build_object("fuselage", fus)
    build_object("cockpit", cockpit)
    for name, part in screens.items():
        build_object(name, [part])
    noz = []
    for nz in S.NOZZLES:
        noz += nozzle(nz)
        if nz["x"] > 0.01:
            noz += nozzle(dict(nz, x=-nz["x"]))
    if noz:
        build_object("nozzle", noz)
    build_object("canopy", [glass] + DET_EXTRA)
    build_object("hud_glass", [hud])

    def te(x):
        return float(S.wing_te(x))
    for nm, (x0, x1, _c0, _c1), chord in (("flap", S.FLAP, S.flap_chord), ("ail", S.AIL, S.ail_chord)):
        part = flap if nm == "flap" else ail
        if not part.faces:
            continue
        a, b = [np.array([x, te(x) + float(chord(x)), float(S.wing_z(x))]) for x in (x0, x1)]
        build_object(nm + "_R", [part], (a, b - a))
        build_object(nm + "_L", [part.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    if lef is not None and lef.faces:
        x0, x1, f = S.LEF
        a, b = [np.array([x, float(S.wing_le(x)) - f * float(S.wing_chord(x)), float(S.wing_z(x))]) for x in (x0, x1)]
        build_object("lef_R", [lef], (a, b - a))
        build_object("lef_L", [lef.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    for srf in S.SURFACES:
        part = Part("paint", "tb")
        airfoil_patch(part, np.linspace(srf.x0, srf.x1, 10), surface_pos(srf), nc=20, cap0=True, cap1=True)
        a, b = [np.array([x, srf.pivot, float(srf.z(x))]) for x in (srf.x0, srf.x1)]
        name = "stab"
        if srf.canard and S.STAB is not None:
            name = "canard"                                   # (not animated when there is a stabilator too)
        d = b - a
        if srf.canard:
            d = -d                                            # canards: leading edge up for nose up
        build_object(name + "_R", [part], (a, d))
        ml = part.mirrored()
        al, bl = a * (-1, 1, 1), b * (-1, 1, 1)
        build_object(name + "_L", [ml], (bl, (al - bl)) if not srf.canard else (bl, -(al - bl)))
    for name, (part, origin, axis) in rudders.items():
        build_object(name, [part], (origin, axis))
    for name, (part, hinge, axis) in speed_brakes().items():
        build_object(name, [part], (hinge, axis))
    if CFG.get("prop"):
        build_prop()

    gear = empty("gear", (0, 0, 0))
    for name, (parts, hinge, axis, angle, kind) in gear_parts["moving"].items():
        obj = build_object(name, parts, (hinge, axis), parent=gear)
        obj[kind] = round(angle, 2)
    for name, part in build_lights().items():
        build_object(name, [part])
    for stn, p in points.items():
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))
    refs()
    for obj in collection.objects:
        obj["part"] = 1
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in collection.objects if o.type == "MESH")
    print("objects: %d, triangles: %d" % (len(collection.objects), tris))
    for stn, p in sorted(points.items()):
        print("store %d: %.3f %.3f %.3f" % (stn, p[0], p[1], p[2]))


def build_prop():
    """Turboprop: spinner and four blades, one object turning about its local X axis (= the flight direction)."""
    pr = CFG["prop"]
    y, z, r, spin = pr["y"], pr["z"], pr["r"], pr.get("spinner", 0.22)
    hub = Part("matte", None, color=pr.get("spinner_colour", (0.10, 0.10, 0.11)))
    prof = [(y - 0.05, spin), (y + 0.10, spin * 0.98), (y + 0.30, spin * 0.80), (y + 0.48, spin * 0.45), (y + 0.58, 0.02)]
    tube(hub, [(0, a, z) for a, _ in prof], [b for _, b in prof], 24)
    blades = Part("matte", None, color=(0.06, 0.06, 0.065))
    tips = Part("matte", None, color=(0.85, 0.75, 0.10))
    for k in range(pr.get("blades", 4)):
        a = 2.0 * math.pi * k / pr.get("blades", 4) + 0.3
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        t = np.array([-math.sin(a), 0.0, math.cos(a)])
        for (s0, s1, part) in ((spin * 0.8, r - 0.12, blades), (r - 0.12, r, tips)):
            ss = np.linspace(s0, s1, 6)
            rows = []
            for s in ss:
                ch = 0.22 * (1.0 - 0.45 * (s / r) ** 2)
                tw = math.radians(45.0 - 30.0 * s / r)
                c = np.array([0.0, y + 0.12, z]) + d * s
                lead = c + t * math.cos(tw) * ch * 0.5 + np.array([0, 1, 0]) * math.sin(tw) * ch * 0.5
                trail = c - t * math.cos(tw) * ch * 0.5 - np.array([0, 1, 0]) * math.sin(tw) * ch * 0.5
                rows.append([lead, c + np.array([0, 0.02, 0]), trail, c - np.array([0, 0.01, 0])])
            rows = np.array(rows)
            part.grid(np.concatenate([rows, rows[:, :1]], axis=1))
            part.ngon(rows[-1])
    obj = build_object("prop", [hub, blades, tips], (np.array([0.0, y, z]), (0.0, 1.0, 0.0)))
    obj["prop"] = 1


def refs():
    for nz in S.NOZZLES:
        y = nz["y0"] - nz["len"]
        if nz["x"] > 0.01:
            empty("ref_nozzle_R", (nz["x"], y, nz["z"]))
            empty("ref_nozzle_L", (-nz["x"], y, nz["z"]))
        else:
            empty("ref_nozzle_C", (0.0, y, nz["z"]))
    for nm, p in CFG.get("exhausts", {}).items():
        empty("ref_nozzle_" + nm, p)
    te = lambda x: float(S.wing_te(x))                    # noqa: E731
    for side, sfx in ((1.0, "R"), (-1.0, "L")):
        empty("ref_wingtip_" + sfx, (side * (S.X_TIP - 0.05), te(S.X_TIP) + 0.3, float(S.wing_z(S.X_TIP))))
        g = REFS["gear_main"]
        empty("ref_gear_main_" + sfx, (side * abs(g[0]), g[1], S.Z_GROUND))
        xv = S.X_ROOT + 0.35
        empty("ref_vapor_" + sfx, (side * xv, float(S.wing_le(xv)) - 0.6, float(S.wing_z(xv)) + 0.08))
        empty("ref_nav_" + sfx, REFS["nav_" + sfx])
    for k, tip in enumerate(REFS["tail_lights"]):
        sfx = "R" if tip[0] > 0.01 else "L" if tip[0] < -0.01 else "C"
        empty("ref_strobe_" + sfx, tuple(np.asarray(tip) + np.array([0.0, -0.05, 0.05])))
    empty("ref_eye", REFS["eye"])
    empty("ref_panel", tuple(REFS["panels"][0]))
    empty("ref_gun", REFS.get("gun", (0.0, S.Y_NOSE - 1.5, float(S.BODY[5](S.Y_NOSE - 1.5)))))
    empty("ref_gear_nose", (0.0, REFS["gear_nose"][1], S.Z_GROUND))
    ytail = min([S.Y_BODY_END] + [n["y0"] - n["len"] for n in S.NOZZLES])
    empty("ref_tail", (0.0, ytail - 0.1, float(S.BODY[5](S.Y_BODY_END))))


# ================================================================ preview
VIEWS = {
    "front": ((11.5, 18.5, 4.0), (0.0, 0.3, 0.4), 50),
    "side": ((40.0, 0.0, 0.6), (0.0, 0.0, 0.8), 50),
}


def main():
    L.CTX["prefix"] = ID
    print(S.summary())
    if OPTS["textures"]:
        import generic_paint
        importlib.reload(generic_paint)
        generic_paint.paint_all(TEX, CFG, GEAR_PLAN_FOR_PAINT())
    if OPTS["build"]:
        build()
    if OPTS["export"]:
        L.export(OUT, WEB, WEB_TEXTURES)
    if OPTS["save"]:
        os.makedirs(OUT, exist_ok=True)
        L.viewport_like_game()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, ID + ".blend"))


def GEAR_PLAN_FOR_PAINT():
    if not GEAR:
        plan_gear()
    return GEAR


main()
