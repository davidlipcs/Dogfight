"""Builds the F-15EX Eagle II in Blender and exports it (models/f15/f15.glb, web/assets/f15.glb).

Run it inside Blender like build_f16.py:

    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), {"__file__": path, "OPTS": {...}})

OPTS: build, textures, export, save, previews, views (see build_f16.py).

Same conventions as the other jets: +Y forward, +X right, +Z up, metres.  Moving parts sit on their hinges with
the local X axis along the hinge (a positive rotation: trailing edge down, rudder trailing edge right, speed
brake open); gear legs and doors carry `retract` / `door`; `store_N` empties are the weapon stations (wing
pylons and the conformal tanks), `ref_*` empties the points the game needs; `screen_*` objects are the front
cockpit's displays (the big touch screen in two halves and the up front controller).
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
import f15_shape as S  # noqa: E402

importlib.reload(L)
importlib.reload(f16_shape)
importlib.reload(S)
from aircraft_lib import (C_BLACK, C_CHROME, C_COCKPIT, C_DARK, C_GREY, C_LIGHT, C_STEEL, C_WHITE, Part,  # noqa: E402
                          airfoil_patch, box, build_object, empty, gear_door, gear_well, prism, retract_rotation,
                          rot_x, rotate_about, superellipse, tube, unit, wheel)

OPTS = dict(dict(build=True, textures=True, export=True, save=True, previews=None, views=None), **globals().get("OPTS", {}))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f15")
TEX = os.path.join(OUT, "textures")
WEB = os.path.join(ROOT, "web", "assets")
WEB_TEXTURES = {"f15_basecolor.png": 2048, "f15_normal.png": 2048, "f15_orm.png": 1024}
INNER_PYLON, OUTER_PYLON = 2.55, 4.55          # right wing pylons (x)
RAIL_OFF = 0.27                                # the inner pylon carries two missiles, one each side


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
    sign = np.where(x >= 0.0, 1.0, -1.0)
    outer = fin & (nrm[:, 0] * sign > 0.0)
    side = ~(top | bot | outer) & (mode != 4)
    out[top] = np.stack([u[top], (S.V_TOP + np.abs(x[top])) / A], axis=1)
    out[bot] = np.stack([u[bot], (S.V_BOT + np.abs(x[bot])) / A], axis=1)
    out[side] = np.stack([u[side], (S.V_SIDE + z[side]) / A], axis=1)
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


def in_holes(c):
    return (c[2] < -0.4 and in_rect(S.MAIN_WELL, c, True)) or (c[2] < 0.1 and in_rect(S.NOSE_WELL, c))


def build_body():
    part = Part("paint", "auto")
    eps = 0.004
    ys = stations(S.Y_NOSE - 0.02, 9.50, 0.035) + stations(9.50, 8.80, 0.07)[1:] + stations(8.80, S.Y_RADOME, 0.10)[1:]
    for a, b in ((S.Y_RADOME, S.COCKPIT_Y1), (S.COCKPIT_Y1, S.COCKPIT_Y0), (S.COCKPIT_Y0, S.Y_KINK + 0.9),
                 (S.Y_KINK + 0.9, S.WING_TE + eps)):
        ys += stations(a, b, 0.11)[1:]
    front = np.array([body_ring(S.Section(y)) for y in ys])
    nr, nc = front.shape[:2]
    flat = front.reshape(-1, 3)
    faces = []
    for i in range(nr - 1):
        for j in range(nc):
            a, b = i * nc + j, i * nc + (j + 1) % nc
            c = flat[[a, b, b + nc, a + nc]].mean(axis=0)
            if S.COCKPIT_Y0 < c[1] < S.COCKPIT_Y1 and abs(c[0]) < S.cockpit_w(c[1]) and c[2] > 0.9:
                continue                                  # the cockpit opening
            faces.append((a, b, b + nc, a + nc))
    part.add(flat, faces)
    part.fan(front[0], (0.0, S.Y_NOSE, 0.375))

    def behind_wing(y):
        sec = S.Section(min(y, S.WING_TE))
        sec.y = y
        return sec

    def aft_ring(y):
        return body_ring(behind_wing(y)) if y > -5.5 else body_ring(S.Section(y, blade=False))
    aft = np.array([aft_ring(y) for y in stations(S.WING_TE + eps, S.Y_BODY_END, 0.11)])
    part.grid(aft, close=True)
    part.ngon(aft[-1])
    return part.drop(in_holes)


def wing_pos(x, s, side):
    c = float(S.wing_chord(x))
    t = float(S.wing_t(x))
    return np.stack([np.full(len(s), x), S.wing_le(x) - s * c, float(S.wing_z(x)) + side * f16_shape.yt(s, t) * c], axis=1)


def stab_pos(x, s, side):
    c = float(S.stab_le(x) - S.stab_te(x))
    return np.stack([np.full(len(s), x), S.stab_le(x) - s * c, S.stab_z(x) + side * f16_shape.yt(s, 0.045) * c], axis=1)


def flap_f(x):
    return 1.0 - S.flap_chord(x) / S.wing_chord(x)


def ail_f(x):
    return 1.0 - S.ail_chord(x) / S.wing_chord(x)


def build_wing():
    """Right wing: fixed part (no leading edge flaps on an Eagle), flap, aileron."""
    fixed, flap, ail = (Part("paint", "tb") for _ in range(3))
    inner = np.linspace(S.X_ROOT, S.X_FLAP, 9)
    mid = np.linspace(S.X_FLAP, S.X_AIL, 8)
    outer = np.linspace(S.X_AIL, S.X_TIP, 3)
    airfoil_patch(fixed, inner, wing_pos, None, flap_f, nc=16)
    airfoil_patch(fixed, mid, wing_pos, None, ail_f, nc=16, cap0=True)
    airfoil_patch(fixed, outer, wing_pos, None, None, nc=18, cap0=True, cap1=True)
    airfoil_patch(flap, inner, wing_pos, flap_f, None, nc=8, cap0=True, cap1=True)
    airfoil_patch(ail, mid, wing_pos, ail_f, None, nc=8, cap0=True, cap1=True)
    return fixed, flap, ail


def build_booms():
    """The tail booms outboard of the engines: they carry the fins and the stabilators."""
    part = Part("paint", "side")
    for side in (1.0, -1.0):
        ys = np.linspace(S.BOOM_Y0, S.BOOM_Y1, 16)
        r = S.BOOM_R * np.where(ys < -8.5, np.clip((ys - S.BOOM_Y1) / 0.65, 0.25, 1.0), 1.0)
        pts = np.stack([np.full(16, side * S.BOOM_X), ys, np.full(16, S.BOOM_Z)], axis=1)
        tube(part, pts, r, 20, caps=True, squash=0.85)
    return part


def fin_point(sign, s, y, off):
    root = np.array([sign * S.FIN_X, 0.0, S.FIN_ZROOT])
    return root + S.fin_span_dir(sign) * s[..., None] + np.array([0.0, 1.0, 0.0]) * y[..., None] + S.fin_normal(sign) * off[..., None]


def build_fins():
    fixed = Part("paint", "fin")
    rudders = {}
    for sign, name in ((1.0, "R"), (-1.0, "L")):
        def pos(sv, s, side, sign=sign):
            c = float(S.fin_le(sv) - S.fin_te(sv))
            t = 0.05 + (0.035 - 0.05) * (sv - S.FIN_S0) / (S.FIN_S1 - S.FIN_S0)
            return fin_point(sign, np.full(len(s), sv), S.fin_le(sv) - s * c, side * f16_shape.yt(s, t) * c)

        def rud_f(sv):
            return 1.0 - S.rudder_chord(sv) / float(S.fin_le(sv) - S.fin_te(sv))
        airfoil_patch(fixed, np.linspace(S.FIN_S0, S.RUD_S0, 3), pos, nc=20, cap1=True)
        airfoil_patch(fixed, np.linspace(S.RUD_S0, S.RUD_S1, 8), pos, None, rud_f, nc=16)
        airfoil_patch(fixed, np.linspace(S.RUD_S1, S.FIN_S1, 9), pos, nc=20, cap0=True, cap1=True)
        rud = Part("paint", "fin")
        airfoil_patch(rud, np.linspace(S.RUD_S0, S.RUD_S1, 8), pos, rud_f, None, nc=8, cap0=True, cap1=True)
        a, b = (fin_point(sign, np.array(s), np.array(float(S.fin_te(s) + S.rudder_chord(s))), np.array(0.0))
                for s in (S.RUD_S0, S.RUD_S1))
        rudders["rudder_" + name] = (rud, a, b - a)
    return fixed, rudders


def intake_ring(y, scale=1.0, dy=0.0, seg=44, sign=1.0):
    xi, xo, zt, zb = S.intake_section(y)
    cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
    cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
    r = superellipse(y, cz, hw * scale, hh * scale, 9.0, 7.0, seg, cx)
    rake = float(S.smoothstep(S.Y_INTAKE - 1.0, S.Y_INTAKE, y))
    r[:, 1] += (r[:, 2] - cz) * 0.42 * rake + dy          # the face leans back: the top lip sticks out forward
    r[:, 0] *= sign
    return r[::-1] if sign < 0 else r


def build_intakes():
    """The big rectangular side inlets: trunk skin with a sharp lip, the ramp line on top, dark duct."""
    skin, duct = Part("paint", "auto"), Part("matte", None, flip=True)
    y0 = S.Y_INTAKE
    ys = [y0, 4.05, 3.90, 3.60, 3.20, 2.70, 2.20, 1.60, 1.00]
    for sign in (1.0, -1.0):
        skin.grid([intake_ring(y0, 0.92, 0.0, sign=sign), intake_ring(y0, 0.955, 0.02, sign=sign),
                   intake_ring(y0, 0.99, 0.02, sign=sign)] + [intake_ring(y, sign=sign) for y in ys], close=True)
        shades = (0.50, 0.28, 0.11, 0.04)
        deep = [intake_ring(y0, 0.92, sign=sign), intake_ring(y0 - 0.5, 0.88, sign=sign), intake_ring(y0 - 1.4, 0.80, sign=sign),
                intake_ring(y0 - 2.4, 0.70, sign=sign), intake_ring(y0 - 3.2, 0.62, sign=sign)]
        for k in range(len(deep) - 1):
            duct.grid([deep[k], deep[k + 1]], close=True, color=(shades[k],) * 3)
        duct.ngon(deep[-1], (0.01, 0.01, 0.01))
    return skin.drop(in_holes), duct


def nozzle(sign):
    """One F110 convergent-divergent nozzle: flaps over seals, light inner petals, the flame holder."""
    metal, inner = Part("metal", None), Part("metal", None, flip=True)
    cx, cz, y0, y1 = sign * S.X_NOZZLE, S.Z_NOZZLE, S.Y_BODY_END, S.Y_NOZZLE
    prof = [(y0 - 0.03, 0.52), (-8.00, 0.51), (-8.30, 0.48), (y1, 0.445)]

    def circle(y, r, seg):
        t = np.linspace(0.0, 2.0 * math.pi, seg, endpoint=False)
        return np.stack([cx + r * np.cos(t), np.full(seg, y), cz + r * np.sin(t)], axis=1)
    metal.grid([circle(y0 + 0.06, 0.52, 56), circle(y0 + 0.02, 0.535, 56), circle(y0 - 0.05, 0.535, 56),
                circle(y0 - 0.07, 0.52, 56)], close=True, color=(0.40, 0.38, 0.36))
    metal.grid([circle(y, r - 0.012, 56) for y, r in prof], close=True, color=(0.13, 0.12, 0.12))
    n = 14
    rng = np.random.default_rng(15 if sign > 0 else 16)
    for k in range(n):
        a0 = 2.0 * math.pi * (k + 0.5) / n
        half = 0.40 * 2.0 * math.pi / n
        tone = rng.uniform(-0.025, 0.025)
        strips = []
        for y, r in prof:
            t = a0 + half * np.array([-1.0, -1.0, -0.4, 0.4, 1.0, 1.0])
            rr = r + np.array([-0.012, 0.0, 0.004, 0.004, 0.0, -0.012])
            strips.append(np.stack([cx + rr * np.cos(t), np.full(6, y), cz + rr * np.sin(t)], axis=1))
        for i in range(len(strips) - 1):
            heat = i / (len(strips) - 2)
            metal.grid(strips[i:i + 2], color=(0.26 + tone + 0.11 * heat, 0.26 + tone + 0.04 * heat, 0.28 + tone - 0.03 * heat))
    metal.grid([circle(y1, 0.449, 56), circle(y1 - 0.012, 0.436, 56), circle(y1, 0.42, 56)], close=True, color=(0.20, 0.18, 0.17))
    wall = [(y1, 0.42, 0.52), (-8.30, 0.38, 0.45), (-8.05, 0.33, 0.30), (-7.75, 0.39, 0.15), (-7.40, 0.45, 0.06), (-6.80, 0.45, 0.03)]
    for (ya, ra, sa), (yb, rb, _sb) in zip(wall, wall[1:]):
        inner.grid([circle(ya, ra, 40), circle(yb, rb, 40)], close=True, color=(sa, sa * 0.92, sa * 0.84))
    inner.ngon(circle(-6.80, 0.45, 40), (0.02, 0.02, 0.02))
    holder = Part("metal", None, color=(0.10, 0.09, 0.085))
    for r in (0.18, 0.32):
        t = np.linspace(0.0, 2.0 * math.pi, 29)
        tube(holder, np.stack([cx + r * np.cos(t), np.full(29, -7.10), cz + r * np.sin(t)], axis=1), 0.015, 6, caps=False)
    tube(holder, [(cx, -6.95, cz), (cx, -7.20, cz), (cx, -7.50, cz)], [0.16, 0.12, 0.012], 14, (0.13, 0.12, 0.11))
    return [metal, inner, holder]


def build_canopy():
    glass, frame = Part("glass", None), Part("matte", None)

    def arc(y, grow=0.0, a0=-14.0, a1=194.0, seg=32):
        w, zs = S.canopy_sill(y)
        h = float(S.CANOPY_H(y)) + grow
        w += grow
        t = np.radians(np.linspace(a0, a1, seg + 1))
        c, s = np.cos(t), np.sin(t)
        z = np.where(s >= 0, zs + h * np.abs(s) ** (2.0 / 2.25), zs + 0.3 * w * s)
        return np.stack([w * np.sign(c) * np.abs(c) ** (2.0 / 2.25), np.full(len(t), y), z], axis=1)
    ys = np.concatenate([np.linspace(S.CANOPY_Y1, 5.6, 10), np.linspace(5.6, S.CANOPY_Y0, 30)[1:]])
    glass.grid([arc(y) for y in ys])
    col = (0.20, 0.21, 0.22)
    b = S.WINDSCREEN_ARCH
    frame.grid([arc(b + 0.06, 0.004, -4, 184), arc(b + 0.055, 0.016, -4, 184), arc(b - 0.055, 0.016, -4, 184),
                arc(b - 0.06, 0.004, -4, 184)], color=col)
    for side in (1.0, -1.0):
        rails = []
        for y in np.linspace(S.CANOPY_Y0 + 0.12, 6.30, 46):
            w, zs = S.canopy_sill(y)
            t = np.radians(np.array([-6.0, -2.0, 4.0, 9.0]))
            g = np.array([0.004, 0.016, 0.016, 0.004])
            h = float(S.CANOPY_H(y))
            rails.append(np.stack([side * (w + g) * np.cos(t), np.full(4, y),
                                   zs + (h + g) * np.maximum(np.sin(t), 0.0) ** (2.0 / 2.25)
                                   + 0.3 * w * np.minimum(np.sin(t), 0.0)], axis=1))
        frame.grid(rails, color=col)
    return glass, frame


def ejection_seat(part, y_back, z_seat):
    """ACES II seat, reclined 15 degrees (the canopy fit lowers it if needed)."""
    r = rot_x(15.0)
    box(part, (0.0, y_back + 0.24, z_seat), (0.22, 0.24, 0.08))
    box(part, (0.0, y_back + 0.26, z_seat + 0.095), (0.19, 0.20, 0.03), color=(0.22, 0.24, 0.20))
    back = np.array([0.0, y_back, z_seat + 0.02])
    up = r @ np.array([0.0, 0.0, 1.0])
    fwd = r @ np.array([0.0, 1.0, 0.0])
    box(part, back + up * 0.40 - fwd * 0.04, (0.22, 0.06, 0.42), r)
    box(part, back + up * 0.38 + fwd * 0.035, (0.17, 0.03, 0.33), r, (0.22, 0.24, 0.20))
    box(part, back + up * 0.88, (0.14, 0.08, 0.12), r, (0.10, 0.10, 0.11))
    tube(part, [(-0.08, y_back + 0.46, z_seat + 0.09), (-0.08, y_back + 0.50, z_seat + 0.16), (0.08, y_back + 0.50, z_seat + 0.16),
                (0.08, y_back + 0.46, z_seat + 0.09)], 0.012, 8, (0.80, 0.68, 0.10))


def build_cockpit():
    """Both cockpits: tub, sills, two ACES II seats; the front one has the F-15EX's large area display (two
    screen_* halves), up front controller, glareshield, HUD and side consoles; the rear one a simpler panel."""
    tub, room = Part("matte", None, flip=True, color=C_COCKPIT), Part("matte", None, color=C_COCKPIT)
    hudglass = Part("hud", None)
    y0, y1, floor = S.COCKPIT_Y0, S.COCKPIT_Y1, 0.45
    ys = np.linspace(y0, y1, 24)
    wy = lambda y: S.cockpit_w(y) - 0.01                    # noqa: E731
    sill_out = lambda y: min(wy(y) + 0.075, float(S.CANOPY_W(y)) - 0.012)   # noqa: E731
    rim = [(wy(y), y, float(S.body_top(y, wy(y))[0]) + 0.004) for y in ys]
    rim = np.array(rim + [(-x, y, z) for x, y, z in rim[::-1]])
    low = rim.copy()
    low[:, 2] = floor
    tub.grid([rim, low], close=True)
    tub.ngon(low, (0.20, 0.21, 0.22))
    sill = Part("matte", None, color=(0.24, 0.25, 0.26))
    for side in (1.0, -1.0):
        strips = []
        for y in np.linspace(y0 - 0.07, y1 + 0.07, 36):
            xs = np.array([wy(y) - 0.045, wy(y) - 0.045, sill_out(y), sill_out(y)])
            top = S.body_top(y, np.array([wy(y) - 0.045, sill_out(y)])) + 0.012
            strips.append(np.stack([side * xs, np.full(4, y), [top[0] - 0.05, top[0], top[1], top[1] - 0.02]], axis=1))
        sill.grid(strips)
    screens = {}

    def panel(yc, zc, w, tilt_deg, live):
        tilt = rot_x(-tilt_deg)
        c0 = np.array([0.0, yc, zc])
        n = tilt @ np.array([0.0, -1.0, 0.0])
        up = tilt @ np.array([0.0, 0.0, 1.0])
        box(room, c0 - n * 0.03, (w, 0.03, 0.22), tilt, (0.10, 0.105, 0.11))
        # the large area display: one 10 x 19 inch touch screen, drawn as two halves
        box(room, c0 + n * 0.010, (0.265, 0.010, 0.140), tilt, (0.05, 0.05, 0.055))
        for name, cx in (("screen_lad_l", -0.125), ("screen_lad_r", 0.125)):
            scr = Part("screen", None)
            box(scr, c0 + n * 0.022 + np.array([cx, 0.0, 0.0]), (0.118, 0.002, 0.118), tilt)
            if live:
                screens[name] = scr
            else:
                screens.setdefault("_static", []).append(scr)
        # up front controller above the display, keys beside it
        c = c0 + up * 0.185
        box(room, c + n * 0.015, (0.10, 0.015, 0.04), tilt, (0.06, 0.06, 0.065))
        scr = Part("screen", None)
        box(scr, c + n * 0.032, (0.07, 0.002, 0.028), tilt)
        if live:
            screens["screen_ufc"] = scr
        else:
            screens.setdefault("_static", []).append(scr)
        for k in range(10):
            p = c + n * 0.034 + np.array([(-0.09 if k < 5 else 0.09), 0.0, 0.0]) + up * (0.03 - 0.015 * (k % 5))
            box(room, p, (0.008, 0.005, 0.005), tilt, (0.30, 0.31, 0.31))
        return c0, n, up
    panel(5.42, 1.06, 0.36, 18.0, True)                          # front cockpit
    panel(FRONT_PANEL_REAR_Y, 1.07, 0.34, 12.0, False)           # rear cockpit (behind the front seat)
    # glareshield and HUD in front
    hood = []
    hw = min(0.40, float(S.CANOPY_W(5.65)) - 0.08)
    for x in np.linspace(-hw, hw, 11):
        zz = 1.36 + 0.03 * (1.0 - (x / hw) ** 2)
        za, zb = min(zz, S.canopy_z(5.40, x) - 0.05), min(zz - 0.03, S.canopy_z(5.72, x) - 0.05)
        hood.append([(x, 5.40, za - 0.02), (x, 5.40, za), (x, 5.72, zb), (x, 5.72, zb - 0.02)])
    room.grid(hood, color=(0.05, 0.05, 0.055))
    box(room, (0.0, 5.58, 1.385), (0.10, 0.11, 0.035), color=(0.07, 0.07, 0.08))
    r = rot_x(20.0)
    for side in (1.0, -1.0):
        box(room, (side * 0.105, 5.54, 1.50), (0.005, 0.012, 0.09), r, (0.07, 0.07, 0.08))
    box(hudglass, (0.0, 5.54, 1.50), (0.10, 0.002, 0.09), r)
    # side consoles, throttles and centre sticks in both cockpits
    for yb in (S.FRONT_SEAT_Y, S.REAR_SEAT_Y):
        for side in (1.0, -1.0):
            box(room, (side * (S.COCKPIT_W - 0.08), yb + 0.20, 0.75), (0.07, 0.52, 0.17))
            box(room, (side * (S.COCKPIT_W - 0.08), yb + 0.20, 0.925), (0.065, 0.48, 0.006), color=(0.09, 0.09, 0.10))
        for dx in (-0.015, 0.025):
            tube(room, [(-S.COCKPIT_W + 0.08 + dx, yb + 0.40, 0.93), (-S.COCKPIT_W + 0.08 + dx, yb + 0.46, 1.03)], 0.012, 8, (0.08, 0.08, 0.09))
        tube(room, [(0.0, yb + 0.62, 0.62), (0.0, yb + 0.62, 0.90), (0.0, yb + 0.60, 1.00)], [0.016, 0.014, 0.013], 8, (0.08, 0.08, 0.09))
        box(room, (0.0, yb + 0.60, 1.04), (0.022, 0.026, 0.045), color=(0.07, 0.07, 0.08))
    seat = Part("matte", None, color=(0.15, 0.16, 0.17))
    ejection_seat(seat, S.FRONT_SEAT_Y, 0.60)
    ejection_seat(seat, S.REAR_SEAT_Y, 0.66)
    static = screens.pop("_static", [])                    # the rear cockpit's displays: lit, but not live
    box(room, (0.0, S.COCKPIT_Y0 + 0.05, 1.00), (S.COCKPIT_W - 0.02, 0.10, 0.14), color=(0.18, 0.19, 0.20))
    drop = L.fit_under_canopy([seat], S)                  # the head boxes stay under the canopy
    print("seat lowered by %.3f m" % drop)
    return [tub, room, sill, seat] + static + [hudglass], screens


FRONT_PANEL_REAR_Y = S.FRONT_SEAT_Y - 0.42          # the rear cockpit's panel sits behind the front seat


def build_gear():
    zg = S.Z_GROUND
    moving = {}
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    hinge = np.array([0.0, 5.70, -0.25])
    c = np.array([0.0, 5.52, zg + 0.33])
    tube(white, [hinge, (0, 5.64, -0.95), (0, 5.56, c[2] + 0.30)], [0.07, 0.065, 0.06], 12)
    tube(metal, [(0, 5.58, -1.05), (0, 5.53, c[2] + 0.05)], 0.045, 12)
    tube(metal, [c + (-0.15, 0, 0), c + (0.15, 0, 0)], 0.03, 10)
    wheel(tire, white, c, 0.33, 0.18)
    lamps = Part("light_white", None)
    tube(white, [(0.08, 5.62, -0.90), (0.08, 5.69, -0.90)], [0.045, 0.05], 12, C_GREY)
    lamps.ngon([(0.08 + 0.042 * math.cos(a), 5.692, -0.90 + 0.042 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    moving["gear_nose"] = ([tire, white, metal, lamps], hinge, (1.0, 0.0, 0.0), 100.0, "retract")
    x0, x1, y0, y1 = S.NOSE_WELL
    z_nose = lambda x: float(S.body_bottom(0.5 * (y0 + y1), abs(x))[0])   # noqa: E731
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = gear_door(side * x1, side * 0.003, y0, y1, z_nose)
        moving["door_nose_" + name] = ([part], h, axis, ang, "door")
    wells = [gear_well(S.NOSE_WELL, lambda x, y: float(S.body_bottom(y, abs(x))[0]), 0.10)]

    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    c = np.array([1.38, -0.95, zg + 0.40])
    top, axle = np.array([1.05, -1.15, -0.62]), np.array([1.28, -0.95, c[2] + 0.04])
    knee = top + (axle - top) * 0.55
    tube(white, [top, knee], [0.08, 0.072], 12)
    tube(metal, [knee, axle], 0.055, 12)
    tube(metal, [axle + (0.0, 0, -0.02), c + (0.03, 0, 0)], 0.045, 10)
    tube(white, [knee + (0.0, 0.0, 0.05), top + (-0.05, 0.42, 0.04)], 0.035, 10)
    wheel(tire, white, c, 0.40, 0.25, (1.0, 0.0, -0.05))
    main = [tire, white, metal]
    a0 = unit((1.0, 0.0, -0.05))
    d0 = unit(axle - top)
    d1 = unit((-0.25, 0.96, 0.10))
    alpha = math.acos(np.clip(np.dot(d0, a0), -1, 1))
    n = unit(np.array([0, 0, 1.0]) - d1 * d1[2])
    a1 = math.cos(alpha) * d1 + math.sin(alpha) * n
    axis, ang = retract_rotation(top, d0, a0, d1, a1)
    moving["gear_main_R"] = (main, top, axis, ang, "retract")
    m = np.array([-1.0, 1.0, 1.0])
    axis, ang = retract_rotation(top * m, d0 * m, a0 * m, d1 * m, a1 * m)
    moving["gear_main_L"] = ([p.mirrored() for p in main], top * m, axis, ang, "retract")
    x0, x1, y0, y1 = S.MAIN_WELL
    zb = lambda x: float(S.body_bottom(0.5 * (y0 + y1), abs(x))[0])      # noqa: E731
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = gear_door(side * x1, side * x0, y0, y1, zb)
        moving["door_main_" + name] = ([part], h, axis, ang, "door")
    for side in (1.0, -1.0):
        wells.append(gear_well(S.MAIN_WELL, lambda x, y: float(S.body_bottom(y, abs(x))[0]), -0.10, side))
    return dict(moving=moving, wells=wells)


def build_stores():
    """Right side: the inner pylon with two launch rails, the outer pylon (new on the EX), and three AIM-120
    launchers on the conformal tank.  -> (part, {station: point})."""
    part = Part("matte", None, color=C_LIGHT)

    def rail(x, z, y_front, y_back, hw=0.04, hh=0.045):
        ys = [y_front, y_front - 0.10, y_front - 0.35, y_back + 0.25, y_back]
        k = [0.25, 0.75, 1.0, 1.0, 0.55]
        rings = [superellipse(y, z, hw * f, hh * f, 4.0, 4.0, 12, x) for y, f in zip(ys, k)]
        part.grid(rings, close=True)
        part.ngon(rings[0])
        part.ngon(rings[-1])
    points = {}
    for x, rails in ((INNER_PYLON, (11, 10)), (OUTER_PYLON, (12,))):
        le, te = float(S.wing_le(x)), float(S.wing_te(x))
        zw = float(S.wing_z(x)) - float(S.wing_t(x)) * float(S.wing_chord(x)) * 0.25
        depth = 0.36
        prof = [(le - 0.25, 0.0), (le - 0.45, depth), (te + 0.55, depth), (te + 0.35, 0.0)]
        prism(part, (x, 0.0, zw), (0, 1, 0), (0, 0, -1), prof, 0.08)
        yc = 0.5 * (le + te) - 0.1
        if len(rails) == 2:                                # a cross bar with a rail on each side
            box(part, (x, yc, zw - depth - 0.03), (RAIL_OFF + 0.05, 0.25, 0.03))
            for st, dx in zip(rails, (RAIL_OFF, -RAIL_OFF)):
                rail(x + dx, zw - depth - 0.08, yc + 1.1, yc - 1.0)
                points[st] = (x + dx, yc - 0.05, zw - depth - 0.21)
        else:
            rail(x, zw - depth - 0.05, yc + 1.0, yc - 0.9)
            points[rails[0]] = (x, yc - 0.05, zw - depth - 0.18)
    # conformal tank launchers (AIM-120 only), staggered along the lower outer corner
    for st, y in ((9, 1.20), (8, -0.40), (7, -2.00)):
        x = 1.45 if y > -1.0 else 1.40
        z = float(S.body_bottom(y, x)[0]) if y < 0.8 else S.intake_bottom(y, x)
        box(part, (x, y, z - 0.02), (0.035, 0.80, 0.025), color=C_GREY)
        points[st] = (x, y - 0.05, z - 0.14)
    return part, points


def build_details():
    grey, metal = Part("matte", None, color=C_GREY), Part("metal", None, color=C_STEEL)
    blade = [(0.0, 0.0), (0.16, 0.0), (0.13, 0.15), (0.07, 0.15)]
    prism(grey, (0.0, 1.0, float(S.BODY[0](1.0)) - 0.02), (0, -1, 0), (0, 0, 1), np.array(blade) * 1.3, 0.02)
    prism(grey, (0.0, 4.5, float(S.BODY[1](4.5)) + 0.02), (0, -1, 0), (0, 0, -1), np.array(blade) * 1.2, 0.02)
    # pitot / angle of attack probes on the nose sides
    for side in (1.0, -1.0):
        x = float(S.BODY[2](8.6))
        tube(metal, [(side * (x - 0.03), 8.6, 0.38), (side * (x + 0.06), 8.62, 0.38), (side * (x + 0.06), 8.78, 0.38)],
             [0.011, 0.009, 0.005], 8)
    # M61 gun port in the right wing root
    z = float(S.body_top(1.2, 1.35)[0])
    tube(grey, [(1.35, 0.90, z - 0.01), (1.35, 1.45, z + 0.005)], [0.035, 0.025], 10, (0.05, 0.05, 0.05), squash=0.5)
    # arresting hook between the nozzles, static dischargers
    tube(grey, [(0, -5.8, -0.30), (0, -7.6, -0.40)], 0.04, 8, (0.80, 0.80, 0.80))
    for side in (1.0, -1.0):
        for x in (S.X_TIP - 0.25, S.X_TIP - 0.8):
            a = np.array([side * x, float(S.wing_te(x)), float(S.wing_z(x))])
            tube(grey, [a + (0, 0.02, 0), a + (0, -0.15, 0)], 0.004, 5, C_DARK)
    return [grey, metal]


def speed_brake():
    """The big dorsal speed brake behind the canopy, hinged at its front edge."""
    part = Part("paint", "tb")
    y0, y1, w = 1.55, 0.05, 0.50
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
    return part, np.array([0.0, y0, zh])


def build_lights():
    out = {}

    def lamp(part, c, r=0.03, stretch=(1.0, 2.0, 1.0)):
        rings = []
        for lat in np.linspace(-0.5 * math.pi, 0.5 * math.pi, 7)[1:-1]:
            t = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False)
            rings.append(np.asarray(c) + r * np.asarray(stretch) * np.stack(
                [np.cos(lat) * np.cos(t), np.cos(lat) * np.sin(t), np.full(10, math.sin(lat))], axis=1))
        part.grid(rings, close=True)
        part.ngon(rings[0])
        part.ngon(rings[-1])
    x = S.X_TIP - 0.05
    for name, mat, side in (("light_nav_R", "light_green", 1.0), ("light_nav_L", "light_red", -1.0)):
        p = Part(mat, None)
        lamp(p, (side * x, float(S.wing_le(x)) - 0.30, float(S.wing_z(x))), 0.03, (0.8, 2.0, 0.7))
        out[name] = p
    p = Part("light_white", None)
    for side in (1.0, -1.0):
        tip = fin_point(side, np.array(S.FIN_S1 - 0.05), np.array(float(S.fin_te(S.FIN_S1)) + 0.10), np.array(0.0))
        lamp(p, tip, 0.035, (1.0, 1.0, 1.0))
    out["light_tail"] = p
    p = Part("light_strip", None)
    for side in (1.0, -1.0):
        a = fin_point(side, np.array([1.9, 2.6]), np.array([float(S.fin_le(1.9)) - 0.45, float(S.fin_le(2.6)) - 0.45]), np.array([0.035, 0.03]))
        b = a + np.array([0.0, -0.05, 0.0])
        p.ngon([a[0], b[0], b[1], a[1]])
    out["light_formation"] = p
    return out


# ============================================================ assembling
def build():
    L.begin("f15", TEX, uv_coords, "F15", glass=(0.40, 0.36, 0.20), glass_alpha=0.30)
    collection = L.CTX["collection"]
    body = build_body()
    wing, flap, ail = build_wing()
    fins, rudders = build_fins()
    intakes, ducts = build_intakes()
    glass, frame = build_canopy()
    cockpit, screens = build_cockpit()
    stores, points = build_stores()
    gear_parts = build_gear()
    hud = cockpit.pop()
    build_object("fuselage", [body, wing, wing.mirrored(), build_booms(), fins, intakes, ducts, frame, stores, stores.mirrored()]
                 + build_details() + gear_parts["wells"])
    build_object("cockpit", cockpit)
    for name, part in screens.items():
        build_object(name, [part])
    build_object("nozzle", nozzle(1.0) + nozzle(-1.0))
    build_object("canopy", [glass])
    build_object("hud_glass", [hud])

    def te(x):
        return float(S.wing_te(x))
    a, b = [np.array([x, te(x) + float(S.flap_chord(x)), float(S.wing_z(x))]) for x in (S.X_ROOT, S.X_FLAP)]
    build_object("flap_R", [flap], (a, b - a))
    build_object("flap_L", [flap.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    a, b = [np.array([x, te(x) + float(S.ail_chord(x)), float(S.wing_z(x))]) for x in (S.X_FLAP, S.X_AIL)]
    build_object("ail_R", [ail], (a, b - a))
    build_object("ail_L", [ail.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    stab = Part("paint", "tb")
    airfoil_patch(stab, np.linspace(S.STAB_X0, S.STAB_X1, 10), stab_pos, nc=20, cap0=True, cap1=True)
    a, b = [np.array([x, S.STAB_PIVOT, float(S.stab_z(x))]) for x in (S.STAB_X0, S.STAB_X1)]
    build_object("stab_R", [stab], (a, b - a))
    build_object("stab_L", [stab.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    for name, (part, origin, axis) in rudders.items():
        build_object(name, [part], (origin, axis))
    brake, hinge = speed_brake()
    build_object("sb_dorsal", [brake], (hinge, (-1.0, 0.0, 0.0)))

    gear = empty("gear", (0, 0, 0))
    for name, (parts, hinge, axis, angle, kind) in gear_parts["moving"].items():
        obj = build_object(name, parts, (hinge, axis), parent=gear)
        obj[kind] = round(angle, 2)
    for name, part in build_lights().items():
        build_object(name, [part])
    for st, p in points.items():
        empty("store_%d" % st, p)
        empty("store_%d" % (13 - st), (-p[0], p[1], p[2]))
    for side, sfx in ((1.0, "R"), (-1.0, "L")):
        empty("ref_nozzle_" + sfx, (side * S.X_NOZZLE, S.Y_NOZZLE, S.Z_NOZZLE))
        empty("ref_wingtip_" + sfx, (side * (S.X_TIP - 0.05), te(S.X_TIP) + 0.3, float(S.wing_z(S.X_TIP))))
        empty("ref_gear_main_" + sfx, (side * 1.38, -0.95, S.Z_GROUND))
        empty("ref_vapor_" + sfx, (side * 1.55, 2.2, float(S.wing_z(1.55)) + 0.08))
        x = S.X_TIP - 0.05
        empty("ref_nav_" + sfx, (side * x, float(S.wing_le(x)) - 0.30, float(S.wing_z(x))))
        tip = fin_point(side, np.array(S.FIN_S1 + 0.04), np.array(float(S.fin_le(S.FIN_S1)) - 0.45), np.array(0.0))
        empty("ref_strobe_" + sfx, tuple(tip))
    empty("ref_eye", (0.0, S.FRONT_SEAT_Y + 0.30, 1.58))
    empty("ref_gun", (1.35, 1.60, float(S.body_top(1.2, 1.35)[0]) + 0.02))
    empty("ref_gear_nose", (0.0, 5.52, S.Z_GROUND))
    empty("ref_tail", (0.0, -8.70, 0.15))
    for obj in collection.objects:
        obj["part"] = 1
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in collection.objects if o.type == "MESH")
    print("objects: %d, triangles: %d" % (len(collection.objects), tris))
    for st, p in sorted(points.items()):
        print("store %d: %.3f %.3f %.3f" % (st, p[0], p[1], p[2]))


def pose(gear=0.0):
    from mathutils import Matrix
    bpy.context.view_layer.update()
    for o in bpy.data.objects:
        if "part" in o.keys() and ("retract" in o.keys() or "door" in o.keys()):
            rest = o.matrix_local.copy()
            o.matrix_local = rest @ Matrix.Rotation(math.radians(o.get("retract", o.get("door", 0.0)) * gear), 4, "X")


# ================================================================ preview
VIEWS = {
    "front": ((11.5, 18.5, 4.0), (0.0, 0.3, 0.4), 50),
    "rear": ((-10.5, -18.5, 5.0), (0.0, -1.5, 0.5), 50),
    "top": ((0.0, 0.0, 40.0), (0.0, 0.0, 0.0), 50),
    "side": ((40.0, 0.0, 0.6), (0.0, 0.0, 0.8), 50),
    "below": ((8.0, 10.0, -9.0), (0.0, 0.0, -0.4), 50),
    "nose": ((3.6, 12.5, 2.4), (0.0, 6.0, 0.9), 50),
    "cockpit": ((2.2, 7.6, 3.4), (0.0, 4.4, 1.2), 50),
    "inside": ((0.0, 4.75, 1.58), (0.0, 6.2, 1.25), 24),
}


def main():
    L.CTX["prefix"] = "f15"
    if OPTS["textures"] and os.path.exists(os.path.join(HERE, "f15_paint.py")):
        import f15_paint
        importlib.reload(f15_paint)
        f15_paint.paint_all(TEX)
    if OPTS["build"]:
        build()
    if OPTS.get("pose") is not None:
        pose(**OPTS["pose"])
    if OPTS["previews"]:
        L.render_previews(OPTS["previews"], OPTS["views"] or list(VIEWS), VIEWS)
    if OPTS["export"]:
        L.export(OUT, WEB, WEB_TEXTURES)
    if OPTS["save"]:
        os.makedirs(OUT, exist_ok=True)
        L.viewport_like_game()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "f15.blend"))


main()
