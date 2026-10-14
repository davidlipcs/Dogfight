"""Builds the F/A-18E Super Hornet in Blender and exports it (models/fa18/fa18.glb, web/assets/fa18.glb).

Run it inside Blender like build_f16.py:

    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), {"__file__": path, "OPTS": {...}})

OPTS: build, textures, export, save, previews, views (see build_f16.py).

Same conventions as the F-16: +Y forward, +X right, +Z up, metres.  Moving parts sit on their hinges with the
local X axis along the hinge (a positive rotation: trailing edge down, leading edge down, rudder trailing edge
right, spoiler open); gear legs and doors carry `retract` / `door` (degrees about local X that fold them away);
`store_N` empties are the weapon stations, `ref_*` empties the points the game needs; `screen_*` objects are
the cockpit displays the game draws on.
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
import fa18_shape as S  # noqa: E402

importlib.reload(L)
importlib.reload(f16_shape)
importlib.reload(S)
from aircraft_lib import (C_BLACK, C_CHROME, C_COCKPIT, C_DARK, C_GREY, C_LIGHT, C_STEEL, C_WHITE, Part,  # noqa: E402
                          airfoil_patch, box, build_object, empty, gear_door, gear_well, prism, retract_rotation,
                          rot_x, rotate_about, superellipse, tube, unit, wheel)

OPTS = dict(dict(build=True, textures=True, export=True, save=True, previews=None, views=None), **globals().get("OPTS", {}))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "fa18")
TEX = os.path.join(OUT, "textures")
WEB = os.path.join(ROOT, "web", "assets")
WEB_TEXTURES = {"fa18_basecolor.png": 2048, "fa18_normal.png": 2048, "fa18_orm.png": 1024}
RAIL_X, RAIL_HW = S.X_TIP + 0.06, 0.055
PYLONS = {10: 4.75, 9: 3.60, 8: 2.45}            # right wing stations (x); the left ones are 2, 3, 4


# ================================================================ texture atlas
def uv_coords(pos, nrm, mode, cent=None):
    """Strips of planar views (see fa18_shape: ATLAS, V_TOP / V_BOT / V_SIDE) plus one island per fin."""
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
    if cent is not None:                                  # left side decals (see fa18_shape.DECALS)
        for y0, y1, z0, z1, u0, v0 in S.DECALS:
            m = side & (cent[:, 0] < -0.05) & (cent[:, 1] > y0) & (cent[:, 1] < y1) & (cent[:, 2] > z0) & (cent[:, 2] < z1)
            out[m] = np.stack([(u0 + (y1 - y[m])) / A, (v0 + (z[m] - z0)) / A], axis=1)
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


def in_main_well(c):
    return c[2] < -0.5 and in_rect(S.MAIN_WELL, c, True)


def in_nose_well(c):
    return c[2] < -0.2 and in_rect(S.NOSE_WELL, c)


def build_body():
    part = Part("paint", "auto")
    eps = 0.004
    ys = stations(S.Y_NOSE - 0.02, 9.35, 0.035) + stations(9.35, 8.70, 0.065)[1:] + stations(8.70, S.Y_RADOME, 0.10)[1:]
    for a, b in ((S.Y_RADOME, S.Y_STRAKE0), (S.Y_STRAKE0, S.COCKPIT_Y1), (S.COCKPIT_Y1, S.COCKPIT_Y0),
                 (S.COCKPIT_Y0, S.Y_KINK), (S.Y_KINK, S.WING_TE + eps)):
        ys += stations(a, b, 0.11)[1:]
    front = np.array([body_ring(S.Section(y)) for y in ys])
    nr, nc = front.shape[:2]
    flat = front.reshape(-1, 3)
    faces = []
    for i in range(nr - 1):
        for j in range(nc):
            a, b = i * nc + j, i * nc + (j + 1) % nc
            c = flat[[a, b, b + nc, a + nc]].mean(axis=0)
            if S.COCKPIT_Y0 < c[1] < S.COCKPIT_Y1 and abs(c[0]) < S.cockpit_w(c[1]) and c[2] > 0.6:
                continue                                  # the cockpit opening
            faces.append((a, b, b + nc, a + nc))
    part.add(flat, faces)
    part.fan(front[0], (0.0, S.Y_NOSE, 0.25))

    def behind_wing(y):
        sec = S.Section(min(y, S.WING_TE))
        sec.y = y
        return sec
    aft = np.array([body_ring(behind_wing(y)) for y in stations(S.WING_TE + eps, S.Y_BODY_END, 0.11)])
    part.grid(aft, close=True)
    part.ngon(aft[-1])                                    # the engine bulkhead (hidden by the nozzles)
    return part.drop(lambda c: in_main_well(c) or in_nose_well(c))


def wing_pos(x, s, side):
    c = float(S.wing_chord(x))
    t = float(S.wing_t(x))
    return np.stack([np.full(len(s), x), S.wing_le(x) - s * c, float(S.wing_z(x)) + side * f16_shape.yt(s, t) * c], axis=1)


def stab_pos(x, s, side):
    c = float(S.stab_le(x) - S.stab_te(x))
    return np.stack([np.full(len(s), x), S.stab_le(x) - s * c, S.stab_z(x) + side * f16_shape.yt(s, 0.045) * c], axis=1)


def lef_f(x):
    return S.lef_chord(x) / S.wing_chord(x)


def flap_f(x):
    return 1.0 - S.flap_chord(x) / S.wing_chord(x)


def ail_f(x):
    return 1.0 - S.ail_chord(x) / S.wing_chord(x)


def build_wing():
    """Right wing: fixed part, leading edge flap, trailing edge flap, aileron."""
    fixed, lef, flap, ail = (Part("paint", "tb") for _ in range(4))
    inner = np.linspace(S.X_ROOT, S.X_FLAP, 10)
    mid = np.linspace(S.X_FLAP, S.X_AIL, 8)
    outer = np.linspace(S.X_AIL, S.X_TIP, 3)
    airfoil_patch(fixed, inner, wing_pos, lef_f, flap_f, nc=12)
    airfoil_patch(fixed, mid, wing_pos, lef_f, ail_f, nc=12, cap0=True)
    airfoil_patch(fixed, outer, wing_pos, lef_f, None, nc=14, cap0=True, cap1=True)
    airfoil_patch(lef, np.linspace(S.X_ROOT, S.X_TIP, 18), wing_pos, None, lef_f, nc=10, cap0=True, cap1=True)
    airfoil_patch(flap, inner, wing_pos, flap_f, None, nc=8, cap0=True, cap1=True)
    airfoil_patch(ail, mid, wing_pos, ail_f, None, nc=8, cap0=True, cap1=True)
    return fixed, lef, flap, ail


def fin_point(sign, s, y, off):
    """A point of the canted fin: s up the span, y along the chord, `off` across (outwards +)."""
    root = np.array([sign * S.FIN_X, 0.0, S.FIN_ZROOT])
    return root + S.fin_span_dir(sign) * s[..., None] + np.array([0.0, 1.0, 0.0]) * y[..., None] + S.fin_normal(sign) * off[..., None]


def build_fins():
    """(fixed fins, {rudder_R, rudder_L}) of the twin canted tails."""
    fixed = Part("paint", "fin")
    rudders = {}
    for sign, name in ((1.0, "R"), (-1.0, "L")):
        def pos(sv, s, side, sign=sign):
            c = float(S.fin_le(sv) - S.fin_te(sv))
            t = 0.055 + (0.035 - 0.055) * (sv - S.FIN_S0) / (S.FIN_S1 - S.FIN_S0)
            sv_arr = np.full(len(s), sv)
            return fin_point(sign, sv_arr, S.fin_le(sv) - s * c, side * f16_shape.yt(s, t) * c)

        def rud_f(sv):
            return 1.0 - S.rudder_chord(sv) / float(S.fin_le(sv) - S.fin_te(sv))
        airfoil_patch(fixed, np.linspace(S.FIN_S0, S.RUD_S0, 3), pos, nc=20, cap1=True)
        airfoil_patch(fixed, np.linspace(S.RUD_S0, S.RUD_S1, 8), pos, None, rud_f, nc=16)
        airfoil_patch(fixed, np.linspace(S.RUD_S1, S.FIN_S1, 7), pos, nc=20, cap0=True, cap1=True)
        rud = Part("paint", "fin")
        airfoil_patch(rud, np.linspace(S.RUD_S0, S.RUD_S1, 8), pos, rud_f, None, nc=8, cap0=True, cap1=True)
        a, b = (fin_point(sign, np.array(s), np.array(float(S.fin_te(s) + S.rudder_chord(s))), np.array(0.0))
                for s in (S.RUD_S0, S.RUD_S1))
        rudders["rudder_" + name] = (rud, a, b - a)
    return fixed, rudders


def build_intakes():
    """Caret inlets under the LEX (both sides): trunk skin, lip, dark duct."""
    skin, duct = Part("paint", "auto"), Part("matte", None, flip=True)

    def ring(y, scale=1.0, dy=0.0, seg=40, sign=1.0):
        xi, xo, zt, zb = S.intake_section(y)
        cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
        cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
        r = superellipse(y, cz, hw * scale, hh * scale, 9.0, 6.0, seg, cx)
        r[:, 0] += (r[:, 2] - cz) * 0.16                    # parallelogram: the top edge sits further out
        rake = float(S.smoothstep(S.Y_INTAKE - 0.9, S.Y_INTAKE, y))
        r[:, 1] += ((r[:, 2] - cz) * 0.42 + (r[:, 0] - cx) * 0.45) * rake + dy
        r[:, 0] *= sign
        return r[::-1] if sign < 0 else r
    y0 = S.Y_INTAKE
    ys = [y0, 2.84, 2.70, 2.40, 2.00, 1.50, 1.00, 0.50, 0.00, -0.20]
    for sign in (1.0, -1.0):
        skin.grid([ring(y0, 0.90, 0.0, sign=sign), ring(y0, 0.94, 0.025, sign=sign), ring(y0, 0.985, 0.025, sign=sign)]
                  + [ring(y, sign=sign) for y in ys], close=True)
        shades = (0.52, 0.30, 0.12, 0.04)
        deep = [ring(y0, 0.90, sign=sign), ring(y0 - 0.5, 0.86, sign=sign), ring(y0 - 1.4, 0.78, sign=sign),
                ring(y0 - 2.4, 0.68, sign=sign), ring(y0 - 3.2, 0.60, sign=sign)]
        for k in range(len(deep) - 1):
            duct.grid([deep[k], deep[k + 1]], close=True, color=(shades[k],) * 3)
        duct.ngon(deep[-1], (0.01, 0.01, 0.01))
    return skin.drop(lambda c: in_main_well(c)), duct


def nozzle(sign):
    """One F414 convergent-divergent nozzle (cf. the F-16's F110): flaps over seals, light inner petals."""
    metal, inner = Part("metal", None), Part("metal", None, flip=True)
    cx, cz, y0, y1 = sign * S.X_NOZZLE, S.Z_NOZZLE, S.Y_BODY_END, S.Y_NOZZLE
    prof = [(y0 - 0.03, 0.478), (-7.90, 0.468), (-8.25, 0.440), (y1, 0.405)]

    def circle(y, r, seg):
        t = np.linspace(0.0, 2.0 * math.pi, seg, endpoint=False)
        return np.stack([cx + r * np.cos(t), np.full(seg, y), cz + r * np.sin(t)], axis=1)
    metal.grid([circle(y0 + 0.06, 0.478, 56), circle(y0 + 0.02, 0.490, 56), circle(y0 - 0.05, 0.490, 56),
                circle(y0 - 0.07, 0.479, 56)], close=True, color=(0.40, 0.38, 0.36))
    metal.grid([circle(y, r - 0.012, 56) for y, r in prof], close=True, color=(0.13, 0.12, 0.12))
    n = 12
    rng = np.random.default_rng(7 if sign > 0 else 8)
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
    metal.grid([circle(y1, 0.409, 56), circle(y1 - 0.012, 0.396, 56), circle(y1, 0.380, 56)], close=True, color=(0.20, 0.18, 0.17))
    wall = [(y1, 0.380, 0.52), (-8.30, 0.340, 0.45), (-8.05, 0.300, 0.30), (-7.75, 0.360, 0.15), (-7.40, 0.42, 0.06),
            (-6.80, 0.42, 0.03)]
    for (ya, ra, sa), (yb, rb, _sb) in zip(wall, wall[1:]):
        inner.grid([circle(ya, ra, 40), circle(yb, rb, 40)], close=True, color=(sa, sa * 0.92, sa * 0.84))
    inner.ngon(circle(-6.80, 0.42, 40), (0.02, 0.02, 0.02))
    holder = Part("metal", None, color=(0.10, 0.09, 0.085))
    for r in (0.17, 0.30):
        t = np.linspace(0.0, 2.0 * math.pi, 29)
        tube(holder, np.stack([cx + r * np.cos(t), np.full(29, -7.10), cz + r * np.sin(t)], axis=1), 0.015, 6, caps=False)
    tube(holder, [(cx, -6.95, cz), (cx, -7.20, cz), (cx, -7.50, cz)], [0.15, 0.11, 0.012], 14, (0.13, 0.12, 0.11))
    return [metal, inner, holder]


def build_canopy():
    glass, frame = Part("glass", None), Part("matte", None)

    def arc(y, grow=0.0, a0=-14.0, a1=194.0, seg=30):
        w, zs = S.canopy_sill(y)
        h = float(S.CANOPY_H(y)) + grow
        w += grow
        t = np.radians(np.linspace(a0, a1, seg + 1))
        c, s = np.cos(t), np.sin(t)
        z = np.where(s >= 0, zs + h * np.abs(s) ** (2.0 / 2.25), zs + 0.3 * w * s)
        return np.stack([w * np.sign(c) * np.abs(c) ** (2.0 / 2.25), np.full(len(t), y), z], axis=1)
    ys = np.concatenate([np.linspace(S.CANOPY_Y1, 5.5, 10), np.linspace(5.5, S.CANOPY_Y0, 22)[1:]])
    glass.grid([arc(y) for y in ys])
    col = (0.24, 0.26, 0.28)
    b = S.WINDSCREEN_ARCH                               # the windscreen frame (the Hornet has a framed windscreen)
    frame.grid([arc(b + 0.06, 0.004, -4, 184), arc(b + 0.055, 0.016, -4, 184), arc(b - 0.055, 0.016, -4, 184),
                arc(b - 0.06, 0.004, -4, 184)], color=col)
    for side in (1.0, -1.0):
        rails = []
        for y in np.linspace(S.CANOPY_Y0 + 0.12, 6.05, 40):
            w, zs = S.canopy_sill(y)
            t = np.radians(np.array([-6.0, -2.0, 4.0, 9.0]))
            g = np.array([0.004, 0.016, 0.016, 0.004])
            h = float(S.CANOPY_H(y))
            rails.append(np.stack([side * (w + g) * np.cos(t), np.full(4, y),
                                   zs + (h + g) * np.maximum(np.sin(t), 0.0) ** (2.0 / 2.25)
                                   + 0.3 * w * np.minimum(np.sin(t), 0.0)], axis=1))
        frame.grid(rails, color=col)
    return glass, frame


def build_cockpit():
    """Tub, sill, NACES seat, front panel with the four displays (screen_* objects), glareshield, HUD, centre
    stick and throttles.  Returns (static parts, {screen name: part})."""
    tub, room = Part("matte", None, flip=True, color=C_COCKPIT), Part("matte", None, color=C_COCKPIT)
    glass = Part("hud", None)                             # the HUD combiner
    y0, y1, floor = S.COCKPIT_Y0, S.COCKPIT_Y1, 0.35
    ys = np.linspace(y0, y1, 18)
    wy = lambda y: S.cockpit_w(y) - 0.01                    # noqa: E731
    sill_out = lambda y: min(wy(y) + 0.075, float(S.CANOPY_W(y)) - 0.012)   # noqa: E731
    rim = [(wy(y), y, float(S.body_top(y, wy(y))[0]) + 0.004) for y in ys]
    rim = np.array(rim + [(-x, y, z) for x, y, z in rim[::-1]])
    low = rim.copy()
    low[:, 2] = floor
    tub.grid([rim, low], close=True)
    tub.ngon(low, (0.20, 0.21, 0.22))
    sill = Part("matte", None, color=(0.26, 0.28, 0.30))
    for side in (1.0, -1.0):
        strips = []
        for y in np.linspace(y0 - 0.07, y1 + 0.07, 30):
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

    # ---- front panel: tilted back 14 degrees, its face at y ~ 5.36
    w = 0.38
    tilt = rot_x(-14.0)
    pan_c = np.array([0.0, 5.37, 1.04])
    pan_n = tilt @ np.array([0.0, -1.0, 0.0])               # faces the pilot
    pan_up = tilt @ np.array([0.0, 0.0, 1.0])
    box(room, pan_c - pan_n * 0.03, (w, 0.03, 0.26), tilt, (0.12, 0.125, 0.13))
    box(room, (0.0, 5.30, 0.55), (0.16, 0.12, 0.12), color=(0.13, 0.135, 0.14))          # the knee well column
    screens = {}

    def display(name, cx, cz, half):
        """Square display: bezel (with buttons) and the glowing screen in front of it."""
        c = pan_c + np.array([cx, 0.0, 0.0]) + pan_up * cz
        box(room, c + pan_n * 0.012, (half + 0.032, 0.012, half + 0.032), tilt, (0.07, 0.07, 0.075))
        for k in range(5):                                  # pushbuttons on all four sides
            t = (k - 2) / 2.6 * half
            for off in ((t, half + 0.020), (t, -half - 0.020), (half + 0.020, t), (-half - 0.020, t)):
                p = c + pan_n * 0.026 + np.array([off[0], 0.0, 0.0]) + pan_up * off[1]
                box(room, p, (0.008, 0.005, 0.006), tilt, (0.32, 0.33, 0.33))
        scr = Part("screen", None)
        box(scr, c + pan_n * 0.024, (half, 0.002, half), tilt)
        screens[name] = scr
    display("screen_ddi_l", -0.215, 0.06, 0.080)            # left and right DDI
    display("screen_ddi_r", 0.215, 0.06, 0.080)
    display("screen_ampcd", 0.0, -0.16, 0.095)               # the big centre display under the UFCD
    # up front control display under the glareshield, between the DDIs and above the AMPCD; keypad beside it
    c = pan_c + pan_up * 0.115
    box(room, c + pan_n * 0.02, (0.100, 0.02, 0.088), tilt, (0.07, 0.07, 0.075))
    scr = Part("screen", None)
    box(scr, c + pan_n * 0.040, (0.085, 0.002, 0.070), tilt)
    screens["screen_ufcd"] = scr
    for k in range(12):                                     # option select buttons above and below the screen
        p = c + pan_n * 0.042 + np.array([-0.075 + 0.030 * (k % 6), 0.0, 0.0]) + pan_up * (0.080 if k < 6 else -0.080)
        box(room, p, (0.010, 0.006, 0.006), tilt, (0.30, 0.31, 0.31))
    # standby instruments, caution lights, landing gear handle
    for i, (cx, cz) in enumerate(((0.30, -0.10), (0.30, -0.20), (-0.30, -0.12))):
        p = pan_c + pan_n * 0.012 + np.array([cx, 0.0, 0.0]) + pan_up * cz
        tube(room, [p, p + pan_n * 0.02], 0.035, 14, (0.04, 0.04, 0.045))
    for k in range(8):
        p = pan_c + pan_n * 0.012 + np.array([-0.33 + 0.024 * (k % 4), 0.0, 0.0]) + pan_up * (0.20 - 0.02 * (k // 4))
        box(room, p, (0.009, 0.005, 0.007), tilt, (0.75, 0.55, 0.10) if k % 3 else (0.70, 0.12, 0.08))
    tube(room, [pan_c + np.array([-0.32, 0, 0]) + pan_up * 0.02, pan_c + np.array([-0.32, 0, 0]) + pan_up * 0.02 + pan_n * 0.08],
         0.010, 8, (0.85, 0.85, 0.80))
    # glareshield and HUD
    hood = []
    hw = min(w + 0.02, float(S.CANOPY_W(5.50)) - 0.08)
    for x in np.linspace(-hw, hw, 11):
        zz = 1.32 + 0.03 * (1.0 - (x / hw) ** 2)
        za, zb = min(zz, S.canopy_z(5.22, x) - 0.05), min(zz - 0.03, S.canopy_z(5.52, x) - 0.05)
        hood.append([(x, 5.22, za - 0.02), (x, 5.22, za), (x, 5.52, zb), (x, 5.52, zb - 0.02)])
    room.grid(hood, color=(0.06, 0.06, 0.065))
    box(room, (0.0, 5.42, 1.355), (0.10, 0.11, 0.04), color=(0.08, 0.08, 0.09))
    r = rot_x(18.0)
    for side in (1.0, -1.0):
        box(room, (side * 0.102, 5.36, 1.47), (0.005, 0.014, 0.11), r, (0.08, 0.08, 0.09))
    box(glass, (0.0, 5.36, 1.47), (0.098, 0.002, 0.105), r)
    # side consoles (switch panels), throttles on the left, centre stick
    for side in (1.0, -1.0):
        box(room, (side * (S.COCKPIT_W - 0.08), 4.55, 0.68), (0.07, 0.60, 0.18))
        box(room, (side * (S.COCKPIT_W - 0.08), 4.55, 0.865), (0.065, 0.56, 0.006), color=(0.10, 0.10, 0.11))
        rng = np.random.default_rng(3 if side > 0 else 4)
        for _ in range(14):
            p = (side * (S.COCKPIT_W - 0.08) + rng.uniform(-0.045, 0.045), rng.uniform(4.05, 5.05), 0.874)
            box(room, p, (0.008, 0.008, 0.006), color=(0.30, 0.31, 0.32))
    for dx in (-0.015, 0.025):
        tube(room, [(-S.COCKPIT_W + 0.08 + dx, 4.80, 0.87), (-S.COCKPIT_W + 0.08 + dx, 4.86, 0.98)], 0.012, 8, (0.08, 0.08, 0.09))
        box(room, (-S.COCKPIT_W + 0.08 + dx, 4.87, 1.00), (0.018, 0.035, 0.02), color=(0.07, 0.07, 0.08))
    tube(room, [(0.0, 5.02, 0.55), (0.0, 5.02, 0.84), (0.0, 4.99, 0.95)], [0.016, 0.014, 0.013], 8, (0.08, 0.08, 0.09))
    box(room, (0.0, 4.99, 0.99), (0.022, 0.026, 0.045), color=(0.07, 0.07, 0.08))
    # NACES ejection seat, reclined 18 degrees, with the head box and the yellow / black firing handle
    seat = Part("matte", None, color=(0.17, 0.18, 0.19))
    r = rot_x(18.0)
    box(seat, (0.0, 4.66, 0.50), (0.23, 0.25, 0.08))
    box(seat, (0.0, 4.68, 0.595), (0.20, 0.21, 0.03), color=(0.26, 0.28, 0.23))
    back = np.array([0.0, 4.42, 0.53])
    up = r @ np.array([0.0, 0.0, 1.0])
    fwd = r @ np.array([0.0, 1.0, 0.0])
    box(seat, back + up * 0.40 - fwd * 0.04, (0.23, 0.06, 0.42), r)
    box(seat, back + up * 0.38 + fwd * 0.035, (0.18, 0.03, 0.33), r, (0.26, 0.28, 0.23))
    box(seat, back + up * 0.92 + fwd * 0.00, (0.15, 0.09, 0.13), r, (0.11, 0.11, 0.12))
    tube(seat, [back + up * 0.99 + fwd * 0.09 + np.array([-0.07, 0, 0]), back + up * 1.07 + fwd * 0.12 + np.array([-0.07, 0, 0]),
          back + up * 1.07 + fwd * 0.12 + np.array([0.07, 0, 0]), back + up * 0.99 + fwd * 0.09 + np.array([0.07, 0, 0])],
         0.012, 8, (0.80, 0.68, 0.10))
    for side in (1.0, -1.0):
        box(seat, back + up * 0.50 - fwd * 0.04 + np.array([side * 0.245, 0, 0]), (0.014, 0.08, 0.52), r, (0.32, 0.33, 0.34))
    tube(seat, [(-0.08, 4.88, 0.59), (-0.08, 4.92, 0.66), (0.08, 4.92, 0.66), (0.08, 4.88, 0.59)], 0.012, 8, (0.80, 0.68, 0.10))
    # the rear deck behind the seat
    box(room, (0.0, 3.92, 0.88), (S.COCKPIT_W - 0.02, 0.13, 0.12), color=(0.20, 0.21, 0.22))
    return [tub, room, sill, seat, glass], screens


def build_gear():
    """Nose gear (twin wheels, launch bar) folding forwards, main gears folding forwards into the trunks."""
    zg = S.Z_GROUND
    moving = {}
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    hinge = np.array([0.0, 5.26, -0.26])
    c = np.array([0.0, 5.10, zg + 0.28])
    tube(white, [hinge, (0, 5.20, -0.95), (0, 5.12, c[2] + 0.30)], [0.07, 0.065, 0.06], 12)
    tube(metal, [(0, 5.15, -1.05), (0, 5.11, c[2] + 0.06)], 0.045, 12)
    tube(metal, [c + (-0.24, 0, 0), c + (0.24, 0, 0)], 0.03, 10)
    tube(white, [(0, 5.13, c[2] + 0.22), (0, 5.40, c[2] + 0.16), (0, 5.44, c[2] + 0.10)], 0.022, 8)   # launch bar (stowed)
    for sx in (-1.0, 1.0):
        wheel(tire, white, c + np.array([sx * 0.155, 0.0, 0.0]), 0.28, 0.16)
    lamps = Part("light_white", None)
    for z in (-0.80, -0.92):
        tube(white, [(0.08, 5.22, z), (0.08, 5.29, z)], [0.045, 0.05], 12, C_GREY)
        lamps.ngon([(0.08 + 0.042 * math.cos(a), 5.292, z + 0.042 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    moving["gear_nose"] = ([tire, white, metal, lamps], hinge, (1.0, 0.0, 0.0), 105.0, "retract")
    x0, x1, y0, y1 = S.NOSE_WELL
    z_nose = lambda x: float(S.body_bottom(0.5 * (y0 + y1), abs(x))[0])   # noqa: E731
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = gear_door(side * x1, side * 0.003, y0, y1, z_nose)
        moving["door_nose_" + name] = ([part], h, axis, ang, "door")
    wells = [gear_well(S.NOSE_WELL, lambda x, y: float(S.body_bottom(y, abs(x))[0]), -0.05)]

    # main gear: a long trailing leg from the side of the inlet trunk
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    c = np.array([1.55, -0.60, zg + 0.38])
    top, axle = np.array([1.00, -0.35, -0.80]), np.array([1.40, -0.60, c[2] + 0.04])
    knee = top + (axle - top) * 0.55
    tube(white, [top, knee], [0.075, 0.068], 12)
    tube(metal, [knee, axle], 0.05, 12)
    tube(metal, [axle + (0.0, 0, -0.02), c + (0.03, 0, 0)], 0.04, 10)
    tube(white, [knee + (0.0, 0.0, 0.05), top + (-0.05, 0.42, 0.04)], 0.035, 10)
    tube(metal, [knee + (-0.04, -0.02, 0.08), top + (-0.08, -0.15, 0.03)], 0.022, 8)
    wheel(tire, white, c, 0.38, 0.24, (1.0, 0.0, -0.06))
    main = [tire, white, metal]
    a0 = unit((1.0, 0.0, -0.06))
    d0 = unit(axle - top)
    d1 = unit((-0.44, 0.88, 0.17))
    alpha = math.acos(np.clip(np.dot(d0, a0), -1, 1))
    n = unit(np.array([0, 0, 1.0]) - d1 * d1[2])
    a1 = math.cos(alpha) * d1 + math.sin(alpha) * n
    axis, ang = retract_rotation(top, d0, a0, d1, a1)
    moving["gear_main_R"] = (main, top, axis, ang, "retract")
    m = np.array([-1.0, 1.0, 1.0])
    axis, ang = retract_rotation(top * m, d0 * m, a0 * m, d1 * m, a1 * m)
    moving["gear_main_L"] = ([p.mirrored() for p in main], top * m, axis, ang, "retract")
    x0, x1, y0, y1 = S.MAIN_WELL
    ym = 0.5 * (y0 + y1)
    for side, name in ((1.0, "R"), (-1.0, "L")):            # the belly is flat under the trunks
        part, h, axis, ang = gear_door(side * x0, side * x1, y0, y1, lambda x: -0.925)
        moving["door_main_" + name] = ([part], h, axis, ang, "door")
    for side in (1.0, -1.0):
        wells.append(gear_well(S.MAIN_WELL, lambda x, y: min(float(S.body_bottom(y, abs(x))[0]),
                                                             S.intake_bottom(y, x) if y > -0.2 else 9.0), -0.15, side))
    return dict(moving=moving, wells=wells)


def build_stores():
    """Wing tip launchers and the canted underwing pylons (right side) with the station points."""
    part = Part("matte", None, color=C_LIGHT)

    def rail(x, z, y_front, y_back, hw=0.045, hh=0.05):
        ys = [y_front, y_front - 0.10, y_front - 0.35, y_back + 0.25, y_back]
        k = [0.25, 0.75, 1.0, 1.0, 0.55]
        rings = [superellipse(y, z, hw * f, hh * f, 4.0, 4.0, 12, x) for y, f in zip(ys, k)]
        part.grid(rings, close=True)
        part.ngon(rings[0])
        part.ngon(rings[-1])
    tip_le = float(S.wing_le(S.X_TIP))
    rail(RAIL_X, float(S.wing_z(S.X_TIP)), tip_le + 0.55, S.WING_TE + 0.15, RAIL_HW)
    points = {11: (RAIL_X + RAIL_HW + 0.095, tip_le - 0.55, float(S.wing_z(S.X_TIP)))}
    cant = math.radians(4.0)
    for st, x in PYLONS.items():
        le, te = float(S.wing_le(x)), S.WING_TE
        zw = float(S.wing_z(x))
        depth = 0.34
        prof = [(le + 0.30, 0.0), (le + 0.05, depth), (te + 0.45, depth), (te + 0.25, 0.0)]
        down = np.array([math.sin(cant), 0.0, -math.cos(cant)])          # the Super Hornet's pylons toe out 4 degrees
        prism(part, (x, 0.0, zw - 0.02), (0, 1, 0), down, prof, 0.08)
        bottom = np.array([x, 0.0, zw - 0.02]) + down * depth
        rail(bottom[0], bottom[2] - 0.06, le + 0.15, te + 0.35, 0.04, 0.045)
        points[st] = (bottom[0] + down[0] * 0.18, 0.5 * (le + te) - 0.05, bottom[2] - 0.19)
    # fuselage stations under the inlet trunks (AIM-120 on the trunk shoulders)
    for y in (0.6,):
        xi, xo, zt, zb = S.intake_section(y)
        box(part, (0.5 * (xi + xo), y - 0.4, zb - 0.025), (0.035, 0.9, 0.025), color=C_GREY)
        points[7] = (0.5 * (xi + xo), y - 0.45, zb - 0.14)
    return part, points


def build_details():
    grey, metal = Part("matte", None, color=C_GREY), Part("metal", None, color=C_STEEL)
    # pitot and angle of attack probes on the forebody sides
    for side in (1.0, -1.0):
        for y, z, ln in ((8.30, 0.40, 0.18), (7.95, 0.10, 0.12)):
            x = float(S.BODY[2](y))
            tube(metal, [(side * (x - 0.03), y, z), (side * (x + ln * 0.4), y + 0.02, z), (side * (x + ln * 0.4), y + ln, z)],
                 [0.012, 0.010, 0.005], 8)
    # the M61 gun: two slots on top of the nose
    for dx in (-0.035, 0.035):
        z = float(S.body_top(8.15, abs(dx))[0])
        tube(grey, [(dx, 7.85, z - 0.005), (dx, 8.18, z + 0.006)], [0.03, 0.022], 10, (0.05, 0.05, 0.05), squash=0.4)
    # retracted refuelling probe fairing on the right of the nose
    z = float(S.body_top(7.0, 0.42)[0])
    tube(grey, [(0.42, 6.20, z - 0.03), (0.42, 7.10, z + 0.01), (0.40, 7.45, z - 0.02)], [0.06, 0.055, 0.02], 12, C_LIGHT, squash=0.6)
    # blade antennas
    blade = [(0.0, 0.0), (0.16, 0.0), (0.13, 0.16), (0.07, 0.16)]
    prism(grey, (0.0, 1.9, float(S.BODY[0](1.9)) - 0.02), (0, -1, 0), (0, 0, 1), np.array(blade) * 1.5, 0.02)
    prism(grey, (0.0, -1.5, float(S.BODY[0](-1.5)) - 0.02), (0, -1, 0), (0, 0, 1), np.array(blade) * 1.2, 0.02)
    prism(grey, (0.0, 3.4, float(S.BODY[1](3.4)) + 0.02), (0, -1, 0), (0, 0, -1), np.array(blade) * 1.4, 0.02)
    # arresting hook between the nozzles
    tube(grey, [(0, -5.80, -0.50), (0, -7.90, -0.58)], 0.04, 8, (0.80, 0.80, 0.80))
    box(grey, (0.0, -7.98, -0.60), (0.04, 0.09, 0.035), color=C_DARK)
    # static dischargers on the wing tips, stabs and fin tips
    for side in (1.0, -1.0):
        for x in (S.X_TIP - 0.3, S.X_TIP - 0.9):
            a = np.array([side * x, S.WING_TE, float(S.wing_z(x))])
            tube(grey, [a + (0, 0.02, 0), a + (0, -0.16, 0)], 0.004, 5, C_DARK)
        x = S.STAB_X1 - 0.15
        a = np.array([side * x, float(S.stab_te(x)), float(S.stab_z(x))])
        tube(grey, [a + (0, 0.02, 0), a + (0, -0.16, 0)], 0.004, 5, C_DARK)
    return [grey, metal]


def build_lights():
    out = {}

    def lamp(part, c, r=0.035, stretch=(1.0, 2.0, 1.0)):
        rings = []
        for lat in np.linspace(-0.5 * math.pi, 0.5 * math.pi, 7)[1:-1]:
            t = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False)
            rings.append(np.asarray(c) + r * np.asarray(stretch) * np.stack(
                [np.cos(lat) * np.cos(t), np.cos(lat) * np.sin(t), np.full(10, math.sin(lat))], axis=1))
        part.grid(rings, close=True)
        part.ngon(rings[0])
        part.ngon(rings[-1])
    tip_le = float(S.wing_le(S.X_TIP))
    zt = float(S.wing_z(S.X_TIP))
    for name, mat, side in (("light_nav_R", "light_green", 1.0), ("light_nav_L", "light_red", -1.0)):
        p = Part(mat, None)
        lamp(p, (side * (RAIL_X + RAIL_HW - 0.015), tip_le + 0.40, zt))
        y = 3.0
        lamp(p, (side * float(S.LEX(y)) * 0.98, y, float(S.LEX_Z(y)) - 0.02), 0.03, (1.0, 2.0, 0.6))
        out[name] = p
    p = Part("light_white", None)
    for side in (1.0, -1.0):
        tip = fin_point(side, np.array(S.FIN_S1 + 0.01), np.array(float(S.fin_te(S.FIN_S1)) + 0.10), np.array(0.0))
        lamp(p, tip, 0.04, (1.0, 1.0, 1.0))
    out["light_tail"] = p
    p = Part("light_white", None)
    lamp(p, (0.0, -1.0, float(S.BODY[0](-1.0)) + 0.01), 0.045, (1.0, 2.2, 0.7))
    lamp(p, (0.0, 1.0, float(S.body_bottom(1.0, 0.0)[0]) - 0.01), 0.045, (1.0, 2.2, 0.7))
    out["light_strobe"] = p
    p = Part("light_strip", None)
    for side in (1.0, -1.0):
        for y0, y1, z in ((7.10, 7.60, 0.25), (-4.40, -4.90, 0.05)):
            pts = []
            for y in (y0, y1):
                sec = S.Section(y)
                for dz in (-0.016, 0.016):
                    lo, hi = 0.0, 3.0
                    for _ in range(40):
                        mid = 0.5 * (lo + hi)
                        if float(np.ravel(sec.F(np.array([mid]), np.array([z + dz])))[0]) > 0.0:
                            hi = mid
                        else:
                            lo = mid
                    pts.append((side * (lo + 0.004), y, z + dz))
            p.ngon([pts[0], pts[1], pts[3], pts[2]])
        for s0, s1 in ((1.9, 2.5),):                      # on the outer face of each fin
            a = fin_point(side, np.array([s0, s1]), np.array([float(S.fin_le(s0)) - 0.45, float(S.fin_le(s1)) - 0.45]), np.array([0.035, 0.03]))
            b = a + np.array([0.0, -0.05, 0.0])
            p.ngon([a[0], b[0], b[1], a[1]])
    out["light_formation"] = p
    return out


def lex_spoiler():
    """The right LEX spoiler (the Super Hornet's air brake), hinged at its front edge."""
    part = Part("paint", "tb")
    y0, y1, x0, x1 = 3.95, 3.05, 0.95, 1.45
    rings = []
    for y in np.linspace(y0, y1, 5):
        z = float(S.Section(y).top(np.array([x0]))[0]) + 0.003
        z1 = float(S.Section(y).top(np.array([x1]))[0]) + 0.003
        rings.append([(x0, y, z), (x0, y, z + 0.018), (x1, y, z1 + 0.018), (x1, y, z1), (x0, y, z)])
    part.grid(rings, close=True)
    part.ngon(rings[0])
    part.ngon(rings[-1])
    zh = float(S.Section(y0).top(np.array([x0]))[0])
    return part, np.array([x0, y0, zh])


# ============================================================ assembling
def build():
    L.begin("fa18", TEX, uv_coords, "FA18", glass=(0.40, 0.33, 0.16), glass_alpha=0.32)
    collection = L.CTX["collection"]
    body = build_body()
    wing, lef, flap, ail = build_wing()
    fins, rudders = build_fins()
    intakes, ducts = build_intakes()
    glass, frame = build_canopy()
    cockpit, screens = build_cockpit()
    stores, points = build_stores()
    gear_parts = build_gear()
    hud = cockpit.pop()
    build_object("fuselage", [body, wing, wing.mirrored(), fins, intakes, ducts, frame, stores, stores.mirrored()]
                 + build_details() + gear_parts["wells"])
    build_object("cockpit", cockpit)
    for name, part in screens.items():
        build_object(name, [part])
    build_object("nozzle", nozzle(1.0) + nozzle(-1.0))
    build_object("canopy", [glass])
    build_object("hud_glass", [hud])

    # ---- moving surfaces
    a, b = [np.array([x, float(S.wing_le(x) - S.lef_chord(x)), float(S.wing_z(x))]) for x in (S.X_ROOT, S.X_TIP)]
    build_object("lef_R", [lef], (b, a - b))
    build_object("lef_L", [lef.mirrored()], (a * (-1, 1, 1), (b - a) * (-1, 1, 1)))
    a, b = [np.array([x, S.WING_TE + float(S.flap_chord(x)), float(S.wing_z(x))]) for x in (S.X_ROOT, S.X_FLAP)]
    build_object("flap_R", [flap], (a, b - a))
    build_object("flap_L", [flap.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    a, b = [np.array([x, S.WING_TE + float(S.ail_chord(x)), float(S.wing_z(x))]) for x in (S.X_FLAP, S.X_AIL)]
    build_object("ail_R", [ail], (a, b - a))
    build_object("ail_L", [ail.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    stab = Part("paint", "tb")
    airfoil_patch(stab, np.linspace(S.STAB_X0, S.STAB_X1, 10), stab_pos, nc=20, cap0=True, cap1=True)
    a, b = [np.array([x, S.STAB_PIVOT, float(S.stab_z(x))]) for x in (S.STAB_X0, S.STAB_X1)]
    build_object("stab_R", [stab], (a, b - a))
    build_object("stab_L", [stab.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    for name, (part, origin, axis) in rudders.items():
        build_object(name, [part], (origin, axis))
    spoiler, hinge = lex_spoiler()
    build_object("sb_up_R", [spoiler], (hinge, (-1.0, 0.0, 0.0)))
    build_object("sb_up_L", [spoiler.mirrored()], (hinge * (-1, 1, 1), (-1.0, 0.0, 0.0)))

    # ---- gear, lights, reference points
    gear = empty("gear", (0, 0, 0))
    for name, (parts, hinge, axis, angle, kind) in gear_parts["moving"].items():
        obj = build_object(name, parts, (hinge, axis), parent=gear)
        obj[kind] = round(angle, 2)
    for name, part in build_lights().items():
        build_object(name, [part])
    for st, p in points.items():
        empty("store_%d" % st, p)
        empty("store_%d" % (12 - st), (-p[0], p[1], p[2]))
    for side, sfx in ((1.0, "R"), (-1.0, "L")):
        empty("ref_nozzle_" + sfx, (side * S.X_NOZZLE, S.Y_NOZZLE, S.Z_NOZZLE))
        empty("ref_wingtip_" + sfx, (side * (RAIL_X + RAIL_HW), S.WING_TE + 0.3, float(S.wing_z(S.X_TIP))))
        empty("ref_gear_main_" + sfx, (side * 1.55, -0.60, S.Z_GROUND))
        empty("ref_vapor_" + sfx, (side * 1.45, 3.0, float(S.LEX_Z(3.0)) + 0.02))
        empty("ref_nav_" + sfx, (side * (RAIL_X + RAIL_HW), float(S.wing_le(S.X_TIP)) + 0.40, float(S.wing_z(S.X_TIP))))
        tip = fin_point(side, np.array(S.FIN_S1 + 0.05), np.array(float(S.fin_le(S.FIN_S1)) - 0.40), np.array(0.0))
        empty("ref_strobe_" + sfx, tuple(tip))
    empty("ref_eye", (0.0, 4.60, 1.40))
    empty("ref_gun", (0.0, 8.20, float(S.body_top(8.2, 0.0)[0]) + 0.02))
    empty("ref_gear_nose", (0.0, 5.10, S.Z_GROUND))
    empty("ref_tail", (0.0, -8.10, -0.30))
    for obj in collection.objects:
        obj["part"] = 1
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in collection.objects if o.type == "MESH")
    print("objects: %d, triangles: %d" % (len(collection.objects), tris))


# ================================================================ preview
VIEWS = {
    "front": ((11.0, 18.0, 4.0), (0.0, 1.0, 0.2), 50),
    "rear": ((-10.5, -18.0, 5.0), (0.0, -1.0, 0.3), 50),
    "top": ((0.0, 0.6, 38.0), (0.0, 0.6, 0.0), 50),
    "side": ((38.0, 0.6, 0.4), (0.0, 0.6, 0.6), 50),
    "below": ((8.0, 12.0, -8.0), (0.0, 0.5, -0.3), 50),
    "frontlow": ((0.0, 22.0, 0.2), (0.0, 0.0, 0.3), 50),
    "nose": ((3.6, 12.5, 2.2), (0.0, 6.0, 0.8), 50),
    "tail": ((-4.0, -12.5, 2.4), (0.0, -6.0, 0.6), 50),
    "cockpit": ((2.0, 7.6, 2.9), (0.0, 4.9, 1.0), 50),
    "gear": ((5.5, 7.5, -1.2), (0.6, 1.5, -1.0), 50),
    "belly": ((3.0, 2.0, -7.0), (0.0, 1.5, -0.9), 50),
    "inside": ((0.0, 4.60, 1.40), (0.0, 6.2, 1.10), 24),
}


def main():
    L.CTX["prefix"] = "fa18"
    if OPTS["textures"] and os.path.exists(os.path.join(HERE, "fa18_paint.py")):
        import fa18_paint
        importlib.reload(fa18_paint)
        fa18_paint.paint_all(TEX)
    if OPTS["build"]:
        build()
    if OPTS["previews"]:
        L.render_previews(OPTS["previews"], OPTS["views"] or list(VIEWS), VIEWS)
    if OPTS["export"]:
        L.export(OUT, WEB, WEB_TEXTURES)
    if OPTS["save"]:
        os.makedirs(OUT, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fa18.blend"))


main()
