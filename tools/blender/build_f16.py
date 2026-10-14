"""Builds the high quality F-16C in Blender and exports it as models/f16/f16.glb.

Run it inside Blender (Scripting tab, or through the Blender MCP socket):

    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), {"__file__": path, "OPTS": {...}})

OPTS: build (rebuild the meshes), textures (paint the textures again), export (write the .glb files:
the full resolution ones in models/f16 and the lighter copies the game loads from web/assets),
save (write the .blend), previews (folder for check renders), views (names of the check renders).

Frame: +Y forward, +X right, +Z up, metres (the same as the game's own model); the glTF exporter
turns that into +Y up, -Z forward.  Every moving part is its own object whose origin lies on the
hinge and whose local X axis is the hinge line; a positive rotation about local X is trailing edge
down (flaperons, stabilators), leading edge down (leading edge flaps), trailing edge right (rudder)
or open (speed brakes).
"""

import importlib
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import aircraft_lib as L  # noqa: E402
import f16_shape as S  # noqa: E402

importlib.reload(L)
importlib.reload(S)
from aircraft_lib import (C_BLACK, C_CHROME, C_COCKPIT, C_DARK, C_GREY, C_LIGHT, C_STEEL, C_WHITE, Part,  # noqa: E402
                          airfoil_patch, box, build_object, empty, gear_door, gear_well, prism, retract_rotation,
                          rot_x, rot_y, rotate_about, superellipse, tube, unit, wheel)

OPTS = dict(dict(build=True, textures=True, export=True, save=True, previews=None, views=None), **globals().get("OPTS", {}))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f16")
TEX = os.path.join(OUT, "textures")
WEB = os.path.join(ROOT, "web", "assets")
WEB_TEXTURES = {"f16_basecolor.png": 2048, "f16_normal.png": 2048, "f16_orm.png": 1024}

# atlas (see f16_paint.py): 16 m x 16 m, strips for the top, bottom and side views
ATLAS = 16.0
RAIL_X, RAIL_HW = S.X_TIP + 0.045, 0.055                 # wing tip launcher
YA0 = -6.4


# ================================================================ objects
def uv_coords(pos, nrm, mode):
    """Atlas UVs from the model space position: top view / bottom view / side view strips."""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    u = (y - YA0) / ATLAS
    v_top = np.abs(x) / ATLAS
    v_bot = (5.0 + np.abs(x)) / ATLAS
    v_side = (12.0 + z) / ATLAS
    out = np.zeros((len(pos), 2))
    auto = mode == 0
    top = (auto & (nrm[:, 2] >= 0.55)) | ((mode == 1) & (nrm[:, 2] >= 0.0))
    bot = (auto & (nrm[:, 2] <= -0.35)) | ((mode == 1) & (nrm[:, 2] < 0.0))
    fin_left = (mode == 2) & (nrm[:, 0] < 0.0)
    side = ~(top | bot | fin_left) & (mode != 4)
    out[top] = np.stack([u[top], v_top[top]], axis=1)
    out[bot] = np.stack([u[bot], v_bot[bot]], axis=1)
    out[side] = np.stack([u[side], v_side[side]], axis=1)
    # the left side of the fin has its own island (mirrored, so that the tail code reads correctly)
    fu = (S.FINL_U0 + (S.FINL_Y1 - y) * S.FINL_SCALE) / ATLAS
    fv = (S.FINL_V0 + (z - S.FINL_Z0) * S.FINL_SCALE) / ATLAS
    out[fin_left] = np.stack([fu[fin_left], fv[fin_left]], axis=1)
    return out


# ================================================================ airframe
NH_UP, NH_CUT, NH_LO = 44, 2, 40


def body_ring(sec):
    """Closed 3D ring of a section: down the right side, back up the left."""
    h = sec.half_ring(NH_UP, NH_CUT, NH_LO)
    right = np.stack([h[:, 0], np.full(len(h), sec.y), h[:, 1]], axis=1)
    left = right[-2:0:-1] * np.array([-1.0, 1.0, 1.0])
    return np.vstack([right, left])


def stations(y1, y0, step):
    n = max(1, int(round((y1 - y0) / step)))
    return list(np.linspace(y1, y0, n + 1))


def build_body():
    part = Part("paint", "auto")
    eps = 0.004
    ys = stations(S.Y_NOSE - 0.02, 8.30, 0.03) + stations(8.30, 7.80, 0.05)[1:] + stations(7.80, S.Y_RADOME, 0.086)[1:]
    for a, b in ((S.Y_RADOME, S.Y_STRAKE0), (S.Y_STRAKE0, S.COCKPIT_Y1), (S.COCKPIT_Y1, S.COCKPIT_Y0),
                 (S.COCKPIT_Y0, S.Y_KINK), (S.Y_KINK, S.WING_TE + eps)):
        ys += stations(a, b, 0.10)[1:]
    front = np.array([body_ring(S.Section(y)) for y in ys])
    # the cockpit opening: drop the skin quads under the canopy
    nr, nc = front.shape[:2]
    faces = []
    for i in range(nr - 1):
        for j in range(nc):
            a, b = i * nc + j, i * nc + (j + 1) % nc
            quad = front.reshape(-1, 3)[[a, b, b + nc, a + nc]]
            c = quad.mean(axis=0)
            if S.COCKPIT_Y0 < c[1] < S.COCKPIT_Y1 and abs(c[0]) < S.cockpit_w(c[1]) and c[2] > 0.3:
                continue
            faces.append((a, b, b + nc, a + nc))
    part.add(front.reshape(-1, 3), faces)
    part.fan(front[0], (0.0, S.Y_NOSE, 0.12))
    def behind_wing(y):
        sec = S.Section(min(y, S.WING_TE))
        sec.y = y
        return sec
    mid = np.array([body_ring(behind_wing(y)) for y in stations(S.WING_TE + eps, S.Y_SB0, 0.10)])
    part.grid(mid, close=True)
    part.ngon(mid[-1])                                   # bulkhead in front of the speed brakes
    aft = np.array([body_ring(S.Section(y, shelf=False)) for y in stations(S.Y_SB0, S.Y_BODY_END, 0.08)])
    part.grid(aft, close=True)
    return part.drop(in_main_well)


def in_rect(rect, c, mirror=False):
    x0, x1, y0, y1 = rect
    x = abs(c[0]) if mirror else c[0]
    return x0 < x < x1 and y0 < c[1] < y1


def in_main_well(c):
    return c[2] < -0.45 and in_rect(S.MAIN_WELL, c, True)


def in_nose_well(c):
    return c[2] < -0.6 and in_rect(S.NOSE_WELL, c)


def wing_pos(x, s, side):
    c = float(S.wing_chord(x))
    return np.stack([np.full(len(s), x), S.wing_le(x) - s * c, side * S.yt(s) * c], axis=1)


def stab_pos(x, s, side):
    c = float(S.stab_le(x) - S.stab_te(x))
    return np.stack([np.full(len(s), x), S.stab_le(x) - s * c, S.stab_z(x) + side * S.yt(s, 0.05) * c], axis=1)


def fin_pos(z, s, side):
    c = float(S.fin_le(z) - S.fin_te(z))
    t = 0.053 + (0.032 - 0.053) * (z - S.FIN_Z0) / (S.FIN_Z1 - S.FIN_Z0)
    return np.stack([side * S.yt(s, t) * c, S.fin_le(z) - s * c, np.full(len(s), z)], axis=1)


def lef_f(x):
    return S.lef_chord(x) / S.wing_chord(x)


def flap_f(x):
    return 1.0 - S.flap_chord(x) / S.wing_chord(x)


def rud_f(z):
    return 1.0 - S.rudder_chord(z) / (S.fin_le(z) - S.fin_te(z))


def build_wing():
    """Right wing: (fixed part, leading edge flap, flaperon)."""
    fixed, lef, flap = Part("paint", "tb"), Part("paint", "tb"), Part("paint", "tb")
    inner = np.linspace(S.X_ROOT, S.X_FLAP, 9)
    outer = np.linspace(S.X_FLAP, S.X_TIP, 7)
    airfoil_patch(fixed, inner, wing_pos, lef_f, flap_f, nc=12)
    airfoil_patch(fixed, outer, wing_pos, lef_f, None, nc=16, cap0=True, cap1=True)
    airfoil_patch(lef, np.linspace(S.X_ROOT, S.X_TIP, 15), wing_pos, None, lef_f, nc=10, cap0=True, cap1=True)
    airfoil_patch(flap, inner, wing_pos, flap_f, None, nc=8, cap0=True, cap1=True)
    return fixed, lef, flap


def build_fin():
    fixed, rudder = Part("paint", "fin"), Part("paint", "fin")
    airfoil_patch(fixed, np.linspace(S.FIN_Z0, S.RUD_Z0, 4), fin_pos, nc=22, cap1=True)
    airfoil_patch(fixed, np.linspace(S.RUD_Z0, S.RUD_Z1, 9), fin_pos, None, rud_f, nc=16)
    airfoil_patch(fixed, np.linspace(S.RUD_Z1, S.FIN_Z1, 4), fin_pos, nc=22, cap0=True, cap1=True)
    airfoil_patch(rudder, np.linspace(S.RUD_Z0, S.RUD_Z1, 9), fin_pos, rud_f, None, nc=8, cap0=True, cap1=True)
    # dorsal fairing in front of the fin and the housing at its base
    prism(fixed, (0.0, 0.0, 0.0), (0, -1, 0), (0, 0, 1), [(0.25, 0.45), (0.25, 0.72), (1.25, 0.94), (2.24, 1.34), (2.45, 0.45)],
          0.05)
    rings = []
    for y, hw, hh in ((-2.90, 0.02, 0.02), (-3.30, 0.075, 0.10), (-3.90, 0.105, 0.155), (-4.50, 0.120, 0.175),
                      (-4.98, 0.115, 0.165), (-5.20, 0.085, 0.12), (-5.28, 0.04, 0.06)):
        rings.append(superellipse(y, 0.665, hw, hh, 3.0, 3.0, 20))
    base = Part("paint", "side")
    base.grid(rings, close=True)
    base.ngon(rings[-1])
    return fixed, rudder, base


def build_ventral():
    """Right ventral fin, canted 15 degrees outwards."""
    part = Part("paint", "side")

    def pos(d, s, side):
        le = -3.50 - 0.52 * d / 0.50
        te = -4.66 + 0.06 * d / 0.50
        c = le - te
        return np.stack([side * S.yt(s, 0.06) * c, le - s * c, -np.full(len(s), d)], axis=1)
    airfoil_patch(part, np.linspace(0.0, 0.50, 4), pos, nc=12, cap1=True)
    r = rot_y(-15.0)
    return part.transformed(lambda v: v @ r.T + np.array([0.56, 0.0, -0.60]))


def build_intake():
    skin, duct = Part("paint", "auto"), Part("matte", None, flip=True)

    def ring(y, scale=1.0, dy=0.0, seg=44):
        hw, zt, zb = (float(c(y)) for c in S.INTAKE)
        cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
        r = superellipse(y, cz, hw * scale, hh * scale, 4.2, 2.7, seg)
        rake = S.INTAKE_RAKE * float(S.smoothstep(S.Y_INTAKE - 0.7, S.Y_INTAKE, y))
        r[:, 1] += (r[:, 2] - cz) * rake + dy
        return r
    y0 = S.Y_INTAKE
    ys = [y0, 4.32, 4.2, 4.0, 3.8, 3.4, 3.0, 2.6, 2.2, 1.8, 1.4, 1.0]
    skin.grid([ring(y0, 0.93), ring(y0, 0.955, 0.022), ring(y0, 0.985, 0.022)] + [ring(y) for y in ys], close=True)
    skin.drop(lambda c: in_nose_well(c) or in_main_well(c))
    shades = (0.50, 0.30, 0.13, 0.05, 0.02)
    deep = [ring(y0, 0.93), ring(y0 - 0.35, 0.92), ring(y0 - 1.0, 0.86), ring(y0 - 2.0, 0.76), ring(y0 - 3.2, 0.66)]
    for k in range(len(deep) - 1):
        duct.grid([deep[k], deep[k + 1]], close=True, color=(shades[k],) * 3)
    duct.ngon(deep[-1], (0.01, 0.01, 0.01))
    strut = Part("matte", None)
    box(strut, (0.0, 3.80, -0.56), (0.010, 0.22, 0.30), color=(0.42, 0.43, 0.44))
    return skin, duct, strut


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
    ys = np.concatenate([np.linspace(S.CANOPY_Y1, 5.2, 9), np.linspace(5.2, S.CANOPY_BOW, 14)[1:],
                         np.linspace(S.CANOPY_BOW, S.CANOPY_Y0, 12)[1:]])
    glass.grid([arc(y) for y in ys])
    # the bow between the moving canopy and the fixed aft glass, and the rails along the sills
    col = (0.20, 0.21, 0.22)
    b = S.CANOPY_BOW
    frame.grid([arc(b + 0.05, 0.004, -4, 184), arc(b + 0.045, 0.012, -4, 184), arc(b - 0.045, 0.012, -4, 184),
                arc(b - 0.05, 0.004, -4, 184)], color=col)
    for side in (1.0, -1.0):
        rails = []
        for y in np.linspace(S.CANOPY_Y0 + 0.12, 5.62, 36):
            w, zs = S.canopy_sill(y)
            t = np.radians(np.array([-6.0, -2.0, 4.0, 9.0]))
            g = np.array([0.004, 0.014, 0.014, 0.004])
            h = float(S.CANOPY_H(y))
            rails.append(np.stack([side * (w + g) * np.cos(t), np.full(4, y),
                                   zs + (h + g) * np.maximum(np.sin(t), 0.0) ** (2.0 / 2.25)
                                   + 0.3 * w * np.minimum(np.sin(t), 0.0)], axis=1))
        frame.grid(rails, color=col)
    return glass, frame


def build_cockpit():
    """Tub, sill, ACES II seat, instrument panel, glareshield and HUD."""
    tub, room = Part("matte", None, flip=True, color=C_COCKPIT), Part("matte", None, color=C_COCKPIT)
    screen, glass = Part("screen", None), Part("glass", None)
    w, y0, y1, floor = S.COCKPIT_W - 0.01, S.COCKPIT_Y0, S.COCKPIT_Y1, -0.02
    ys = np.linspace(y0, y1, 18)
    wy = lambda y: S.cockpit_w(y) - 0.01                    # noqa: E731
    sill_out = lambda y: min(wy(y) + 0.075, float(S.CANOPY_W(y)) - 0.012)   # noqa: E731
    rim = [(wy(y), y, float(S.body_top(y, wy(y))[0]) + 0.004) for y in ys]
    rim = np.array(rim + [(-x, y, z) for x, y, z in rim[::-1]])
    low = rim.copy()
    low[:, 2] = floor
    tub.grid([rim, low], close=True)
    tub.ngon(low, (0.20, 0.21, 0.22))
    # sill: covers the cut edge of the skin all around the opening
    sill = Part("matte", None, color=(0.25, 0.27, 0.29))
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
    # side consoles, rear deck and the instrument panel
    for side in (1.0, -1.0):
        box(room, (side * (w - 0.065), 4.45, 0.20), (0.065, 0.55, 0.22))
        box(room, (side * (w - 0.065), 4.45, 0.425), (0.060, 0.50, 0.006), color=(0.10, 0.10, 0.11))
    box(room, (0.0, 3.72, 0.32), (w - 0.01, 0.20, 0.34), color=(0.21, 0.22, 0.23))
    box(room, (0.0, 4.99, 0.52), (w - 0.005, 0.02, 0.23), color=(0.11, 0.11, 0.12))
    box(room, (0.0, 4.86, 0.22), (0.09, 0.13, 0.24), color=(0.14, 0.14, 0.15))
    for x, z, hw_, hh_ in ((-0.16, 0.50, 0.062, 0.062), (0.16, 0.50, 0.062, 0.062), (0.0, 0.62, 0.045, 0.035)):
        box(screen, (x, 4.968, z), (hw_, 0.003, hh_))
    rng = np.random.default_rng(5)
    for _ in range(26):                                   # gauges and switches
        x, z = rng.uniform(-0.27, 0.27), rng.uniform(0.32, 0.72)
        if abs(abs(x) - 0.16) < 0.08 and abs(z - 0.50) < 0.08:
            continue
        box(room, (x, 4.966, z), (0.016, 0.004, 0.016), color=(0.30, 0.31, 0.32))
    # glareshield and HUD
    hood = []
    hw = min(w + 0.02, float(S.CANOPY_W(5.16)) - 0.07)
    for x in np.linspace(-hw, hw, 9):
        zz = 0.80 + 0.045 * (1.0 - (x / hw) ** 2)
        za, zb = min(zz, S.canopy_z(4.86, x) - 0.04), min(zz - 0.05, S.canopy_z(5.16, x) - 0.04)
        hood.append([(x, 4.86, za - 0.02), (x, 4.86, za), (x, 5.16, zb), (x, 5.16, zb - 0.02)])
    room.grid(hood, color=(0.06, 0.06, 0.065))
    box(room, (0.0, 5.10, 0.855), (0.075, 0.10, 0.035), color=(0.09, 0.09, 0.10))
    r = rot_x(22.0)
    for side in (1.0, -1.0):
        box(room, (side * 0.078, 5.02, 0.975), (0.004, 0.012, 0.095), r, (0.09, 0.09, 0.10))
    box(glass, (0.0, 5.02, 0.975), (0.074, 0.002, 0.090), r)
    # ACES II seat, reclined 30 degrees
    seat = Part("matte", None, color=(0.16, 0.17, 0.18))
    r = rot_x(30.0)                                       # the back leans aft
    box(seat, (0.0, 4.60, 0.15), (0.22, 0.24, 0.07))
    box(seat, (0.0, 4.62, 0.235), (0.19, 0.20, 0.03), color=(0.24, 0.27, 0.22))
    back = np.array([0.0, 4.37, 0.16])
    up = r @ np.array([0.0, 0.0, 1.0])
    fwd = r @ np.array([0.0, 1.0, 0.0])
    box(seat, back + up * 0.42 - fwd * 0.03, (0.22, 0.055, 0.44), r)
    box(seat, back + up * 0.40 + fwd * 0.045, (0.17, 0.03, 0.34), r, (0.24, 0.27, 0.22))
    box(seat, back + up * 0.93 + fwd * 0.03, (0.13, 0.075, 0.11), r, (0.10, 0.10, 0.11))
    for side in (1.0, -1.0):
        box(seat, back + up * 0.45 - fwd * 0.03 + np.array([side * 0.235, 0, 0]), (0.012, 0.075, 0.50), r, (0.30, 0.31, 0.32))
        box(seat, (side * 0.235, 4.60, 0.20), (0.012, 0.25, 0.10), color=(0.30, 0.31, 0.32))
    tube(seat, [(-0.07, 4.80, 0.24), (-0.07, 4.84, 0.31), (0.07, 4.84, 0.31), (0.07, 4.80, 0.24)], 0.012, 8, (0.75, 0.62, 0.08))
    # side stick and throttle
    tube(room, [(w - 0.07, 4.62, 0.43), (w - 0.07, 4.63, 0.56)], [0.014, 0.020], 8, (0.07, 0.07, 0.08))
    box(room, (-w + 0.07, 4.66, 0.46), (0.03, 0.06, 0.03), color=(0.07, 0.07, 0.08))
    return [tub, room, sill, seat, screen, glass]


def build_nozzle():
    """F110 style convergent-divergent nozzle: outer flaps over seals, light inner petals, flame holder."""
    metal, inner = Part("metal", None), Part("metal", None, flip=True)
    cz, y0, y1 = S.Z_NOZZLE, S.Y_BODY_END, S.Y_NOZZLE
    prof = [(y0 - 0.03, 0.585), (-5.30, 0.568), (-5.64, 0.512), (y1, 0.440)]

    def circle(y, r, seg):
        t = np.linspace(0.0, 2.0 * math.pi, seg, endpoint=False)
        return np.stack([r * np.cos(t), np.full(seg, y), cz + r * np.sin(t)], axis=1)
    metal.grid([circle(y0 + 0.06, 0.585, 64), circle(y0 + 0.02, 0.600, 64), circle(y0 - 0.05, 0.600, 64),
                circle(y0 - 0.07, 0.586, 64)], close=True, color=(0.40, 0.38, 0.36))
    metal.grid([circle(y, r - 0.014, 64) for y, r in prof], close=True, color=(0.13, 0.12, 0.12))
    n = 16
    rng = np.random.default_rng(11)
    for k in range(n):
        a0 = 2.0 * math.pi * (k + 0.5) / n
        half = 0.40 * 2.0 * math.pi / n
        tone = rng.uniform(-0.025, 0.025)
        strips = []
        for y, r in prof:
            t = a0 + half * np.array([-1.0, -1.0, -0.4, 0.4, 1.0, 1.0])
            rr = r + np.array([-0.014, 0.0, 0.004, 0.004, 0.0, -0.014])
            strips.append(np.stack([rr * np.cos(t), np.full(6, y), cz + rr * np.sin(t)], axis=1))
        for i in range(len(strips) - 1):
            heat = i / (len(strips) - 2)
            col = (0.27 + tone + 0.10 * heat, 0.27 + tone + 0.03 * heat, 0.29 + tone - 0.04 * heat)
            metal.grid(strips[i:i + 2], color=col)
    metal.grid([circle(y1, 0.444, 64), circle(y1 - 0.012, 0.430, 64), circle(y1, 0.412, 64)], close=True,
               color=(0.20, 0.18, 0.17))
    wall = [(y1, 0.412, 0.50), (-5.72, 0.375, 0.44), (-5.46, 0.345, 0.30), (-5.20, 0.42, 0.15), (-4.90, 0.50, 0.08),
            (-4.25, 0.50, 0.04)]
    for (ya, ra, sa), (yb, rb, _sb) in zip(wall, wall[1:]):
        inner.grid([circle(ya, ra, 48), circle(yb, rb, 48)], close=True, color=(sa, sa * 0.92, sa * 0.84))
    inner.ngon(circle(-4.25, 0.50, 48), (0.02, 0.02, 0.02))
    holder = Part("metal", None, color=(0.10, 0.09, 0.085))
    for r in (0.20, 0.36):
        t = np.linspace(0.0, 2.0 * math.pi, 33)
        tube(holder, np.stack([r * np.cos(t), np.full(33, -4.45), cz + r * np.sin(t)], axis=1), 0.018, 6, caps=False)
    for k in range(8):
        a = 2.0 * math.pi * k / 8
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        tube(holder, [np.array([0.0, -4.45, cz]) + d * 0.10, np.array([0.0, -4.45, cz]) + d * 0.49], 0.014, 6)
    tube(holder, [(0, -4.30, cz), (0, -4.55, cz), (0, -4.90, cz)], [0.17, 0.13, 0.015], 16, (0.13, 0.12, 0.11))
    return [metal, inner, holder]


def build_gear():
    """Landing gear that folds into its wells: legs and doors are separate objects on their hinges.
    -> dict(moving={name: (parts, hinge, axis, angle, kind)}, wells)"""
    zg = S.Z_GROUND
    moving = {}
    # ---- nose gear: folds back into the well under the intake
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    hinge = np.array([0.0, 3.80, -0.68])
    c = np.array([0.0, 3.705, zg + 0.23])
    tube(white, [hinge, (0, 3.70, -1.22), (-0.105, 3.705, -1.31), (-0.105, 3.705, c[2] + 0.02)],
         [0.050, 0.046, 0.036, 0.034], 12)
    tube(metal, [(0, 3.705, -1.05), (0, 3.70, -1.22)], 0.03, 12)
    tube(metal, [c + (-0.125, 0, 0), c + (0.09, 0, 0)], 0.02, 10)
    tube(white, [(0, 3.70, -1.10), (0, 3.86, -0.74)], 0.02, 8)
    box(white, (0.0, 3.76, -1.16), (0.02, 0.07, 0.012), rot_x(35.0))
    box(white, (0.0, 3.76, -1.26), (0.02, 0.07, 0.012), rot_x(-35.0))
    wheel(tire, white, c, 0.23, 0.14)
    lamps = Part("light_white", None)
    for z in (-0.98, -1.09):
        tube(white, [(0, 3.745, z), (0, 3.80, z)], [0.042, 0.048], 12, C_GREY)
        lamps.ngon([(0.04 * math.cos(a), 3.802, z + 0.04 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    moving["gear_nose"] = ([tire, white, metal, lamps], hinge, (-1.0, 0.0, 0.0), 90.0, "retract")
    x0, x1, y0, y1 = S.NOSE_WELL
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = gear_door(side * x1, side * 0.003, y0, y1, lambda x: S.intake_bottom(0.5 * (y0 + y1), x))
        moving["door_nose_" + name] = ([part], h, axis, ang, "door")
    wells = [gear_well(S.NOSE_WELL, lambda x, y: S.intake_bottom(y, x), -0.45)]

    # ---- main gears: fold forwards and inwards into the belly
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    c = np.array([1.18, -0.30, zg + 0.34])
    top, axle = np.array([0.60, -0.20, -0.64]), np.array([1.035, -0.30, c[2] + 0.03])
    knee = top + (axle - top) * 0.58
    tube(white, [top, knee], [0.062, 0.056], 12)
    tube(metal, [knee, axle], 0.04, 12)
    tube(white, [axle + (-0.02, 0, 0.03), axle + (0.0, 0, -0.06)], 0.05, 10)
    tube(metal, [axle + (0.0, 0, -0.03), c + (0.02, 0, 0)], 0.032, 10)
    tube(white, [knee + (0.0, 0.0, 0.05), top + (-0.02, 0.30, 0.0)], 0.03, 10)
    tube(metal, [knee + (-0.04, -0.02, 0.06), top + (-0.05, -0.10, 0.04)], 0.018, 8)
    wheel(tire, white, c, 0.34, 0.20, (1.0, 0.0, -0.05))
    main = [tire, white, metal]
    a0 = unit((1.0, 0.0, -0.05))
    d0 = unit(axle - top)
    d1 = unit((-0.22, 0.95, 0.12))
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
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = gear_door(side * x0, side * x1, y0, y1, lambda x: float(S.body_bottom(ym, abs(x))[0]))
        moving["door_main_" + name] = ([part], h, axis, ang, "door")
    for side in (1.0, -1.0):
        wells.append(gear_well(S.MAIN_WELL, lambda x, y: float(S.body_bottom(y, abs(x))[0]), -0.22, side))
    return dict(moving=moving, wells=wells)


def build_stores():
    """Wing tip launchers, underwing launchers and pylons (right side) and their attach points."""
    part = Part("matte", None, color=C_LIGHT)

    def rail(x, z, y_front, y_back, hw=0.045, hh=0.05):
        ys = [y_front, y_front - 0.10, y_front - 0.35, y_back + 0.25, y_back]
        k = [0.25, 0.75, 1.0, 1.0, 0.55]
        rings = [superellipse(y, z, hw * f, hh * f, 4.0, 4.0, 12, x) for y, f in zip(ys, k)]
        part.grid(rings, close=True)
        part.ngon(rings[0])
        part.ngon(rings[-1])
        box(part, (x, 0.5 * (y_front + y_back) - 0.05, z - hh - 0.012), (0.022, 0.5 * (y_front - y_back) - 0.22, 0.014),
            color=C_GREY)
    rail(RAIL_X, 0.0, 0.52, -2.26, RAIL_HW)
    points = {9: (RAIL_X + RAIL_HW + 0.095, -0.80, 0.0)}     # weapon stations (right side; left = 10 - n)
    for name, x, depth, y_front, y_back in ((8, 3.96, 0.10, -0.66, -1.95), (7, 3.05, 0.30, -0.10, -1.98)):
        prof = [(y_front, 0.0), (y_front - 0.25, depth), (y_back + 0.12, depth), (y_back, 0.0)]
        prism(part, (x, 0.0, -0.01), (0, 1, 0), (0, 0, -1), prof, 0.07)
        rail(x, -depth - 0.065, y_front + 0.05, y_back - 0.25, 0.04, 0.045)
        points[name] = (x, 0.5 * (y_front + y_back) - 0.10, -depth - 0.20)
    return part, points


def build_details():
    """Probes, antennas, gun port, hook, static dischargers."""
    grey, metal = Part("matte", None, color=C_GREY), Part("metal", None, color=C_STEEL)
    tube(metal, [(0, S.Y_NOSE - 0.06, 0.12), (0, S.Y_NOSE + 0.02, 0.12), (0, S.Y_NOSE + 0.42, 0.12), (0, S.Y_NOSE + 0.50, 0.12)],
         [0.034, 0.024, 0.016, 0.009], 12)
    for side in (1.0, -1.0):                              # angle of attack probes on the radome
        x = float(S.BODY[2](7.30))
        tube(metal, [(side * (x - 0.02), 7.30, 0.14), (side * (x + 0.07), 7.33, 0.14)], [0.016, 0.006], 8)
        x = float(S.BODY[2](6.55))                        # air data probes
        tube(metal, [(side * (x - 0.02), 6.55, 0.02), (side * (x + 0.05), 6.60, 0.02), (side * (x + 0.05), 6.72, 0.02)],
             [0.010, 0.009, 0.004], 8)
    blade = [(0.0, 0.0), (0.16, 0.0), (0.13, 0.16), (0.07, 0.16)]
    for y in (5.98, 6.13, 6.28, 6.43):                    # IFF "bird slicers" in front of the windscreen
        prism(grey, (0.0, y, float(S.BODY[0](y)) - 0.012), (0, -1, 0), (0, 0, 1), np.array(blade) * 0.55, 0.012)
    prism(grey, (0.0, 1.35, float(S.BODY[0](1.35)) - 0.02), (0, -1, 0), (0, 0, 1), np.array(blade) * 1.6, 0.02)
    prism(grey, (0.0, -0.9, float(S.BODY[0](-0.9)) - 0.02), (0, -1, 0), (0, 0, 1), np.array(blade) * 1.2, 0.02)
    prism(grey, (0.0, 2.6, -0.865), (0, -1, 0), (0, 0, -1), np.array(blade) * 1.5, 0.02)
    prism(grey, (0.0, -1.2, float(S.BODY[1](-1.2)) + 0.02), (0, -1, 0), (0, 0, -1), np.array(blade) * 1.4, 0.02)
    # M61 gun port in the left strake
    sec = S.Section(3.55)
    z = float(sec.top(0.70)[0])
    tube(grey, [(-0.70, 3.20, z + 0.005), (-0.70, 3.95, z + 0.012)], [0.075, 0.03], 12, (0.30, 0.31, 0.33), squash=0.45)
    tube(metal, [(-0.70, 3.55, z + 0.03), (-0.70, 3.80, z + 0.03)], 0.022, 10, (0.05, 0.05, 0.05))
    # arrestor hook between the ventral fins
    tube(grey, [(0, -3.35, -0.775), (0, -4.60, -0.80)], 0.035, 8, C_LIGHT)
    box(grey, (0.0, -4.66, -0.82), (0.03, 0.07, 0.03), color=C_DARK)
    # static dischargers
    wicks = [((S.X_TIP - 0.25, S.WING_TE, 0.0), (0, -1, 0)), ((S.X_TIP - 0.75, S.WING_TE, 0.0), (0, -1, 0)),
             ((S.STAB_X1 - 0.12, float(S.stab_te(S.STAB_X1 - 0.12)), float(S.stab_z(S.STAB_X1 - 0.12))), (0, -1, 0)),
             ((S.STAB_X1 - 0.55, float(S.stab_te(S.STAB_X1 - 0.55)), float(S.stab_z(S.STAB_X1 - 0.55))), (0, -1, 0))]
    for (p, d) in wicks:
        for side in (1.0, -1.0):
            a = np.array(p) * (side, 1, 1)
            tube(grey, [a + np.array(d) * -0.02, a + np.array(d) * 0.16], 0.004, 5, C_DARK)
    for z in (3.25, 2.95):
        tube(grey, [(0, float(S.fin_te(z)) + 0.02, z), (0, float(S.fin_te(z)) - 0.16, z)], 0.004, 5, C_DARK)
    # fin tip: radar warning antenna fairing and the housing lamp
    tube(grey, [(0, float(S.fin_te(3.20)) + 0.30, 3.20), (0, float(S.fin_te(3.20)) - 0.02, 3.20),
                (0, float(S.fin_te(3.20)) - 0.10, 3.20)], [0.03, 0.036, 0.012], 10, C_GREY)
    return [grey, metal]


def build_lights():
    """Position lights, strobe and formation strips as separate emissive objects."""
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
    for name, mat, side in (("light_nav_R", "light_green", 1.0), ("light_nav_L", "light_red", -1.0)):
        p = Part(mat, None)
        lamp(p, (side * (RAIL_X + RAIL_HW - 0.015), float(S.wing_le(S.X_TIP)) - 0.30, 0.0))
        lamp(p, (side * float(S.INTAKE[0](3.6)) + side * 0.005, 3.6, -0.55), 0.03, (0.5, 2.0, 1.0))
        out[name] = p
    p = Part("light_white", None)
    lamp(p, (0.0, -5.29, 0.665), 0.04, (1.0, 1.0, 1.0))
    out["light_tail"] = p
    p = Part("light_white", None)
    lamp(p, (0.0, float(S.fin_le(S.FIN_Z1)) - 0.45, S.FIN_Z1 + 0.012), 0.045, (1.0, 2.2, 0.8))
    out["light_strobe"] = p
    p = Part("light_strip", None)
    for side in (1.0, -1.0):
        for y0, y1, z in ((6.10, 6.55, 0.20), (-3.30, -3.75, 0.30)):
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
        for za, zb in ((2.62, 3.05),):
            ya, yb = float(S.fin_le(za)) - 0.28, float(S.fin_le(zb)) - 0.28
            x = 0.035
            p.ngon([(side * x, ya, za), (side * x, ya - 0.05, za), (side * (x - 0.008), yb - 0.05, zb), (side * (x - 0.008), yb, zb)])
        x = RAIL_X + RAIL_HW + 0.002
        p.ngon([(side * x, -0.6, -0.02), (side * x, -1.5, -0.02), (side * x, -1.5, 0.02), (side * x, -0.6, 0.02)])
    out["light_formation"] = p
    return out


def speed_brake(upper):
    """One half of the right clamshell speed brake (a wedge that continues the shelf)."""
    part = Part("paint", "tb")
    sgn = 1.0 if upper else -1.0
    rings = []
    for y in np.linspace(S.Y_SB0, S.Y_SB1, 6):
        t = (S.Y_SB0 - y) / (S.Y_SB0 - S.Y_SB1)
        h = S.SHELF_H * (1.0 - 0.93 * t ** 1.4)
        x0, x1 = S.X_SB0 - 0.10 * (1 - t), S.X_SHELF - 0.02 * t
        z0 = S.Z_SHELF
        rings.append([(x0, y, z0), (x0, y, z0 + sgn * h), (x1 - 0.03, y, z0 + sgn * h), (x1, y, z0 + sgn * (h - 0.03)),
                      (x1, y, z0)])
    part.grid(rings, close=True)
    part.ngon(rings[0])
    part.ngon(rings[-1])
    return part


def build_missiles():
    """AIM-120C and AIM-9M (nose towards +Y, origin in the middle): exported as their own .glb files."""
    def missile(body, fins, thick=0.012):
        part = Part("matte", None)
        for (ya, ra, col), (yb, rb, _c) in zip(body, body[1:]):
            tube(part, [(0, ya, 0), (0, yb, 0)], [ra, rb], 20, col, caps=False)
        part.ngon(tube(part, [(0, body[-1][0], 0), (0, body[-1][0] + 0.03, 0)], [body[-1][1], body[-1][1] * 0.7], 20,
                       (0.08, 0.08, 0.08), caps=False)[-1], (0.03, 0.03, 0.03))
        for outline, col in fins:
            for k in range(4):
                a = math.radians(45.0 + 90.0 * k)
                prism(part, (0, 0, 0), (0, 1, 0), (math.cos(a), 0.0, math.sin(a)), outline, thick, col)
        return part
    white, grey, dark = (0.80, 0.81, 0.80), (0.60, 0.62, 0.64), (0.22, 0.23, 0.25)
    amraam = missile(
        [(1.825, 0.004, white), (1.76, 0.030, white), (1.62, 0.058, white), (1.42, 0.080, white), (1.22, 0.089, grey),
         (0.98, 0.089, (0.72, 0.58, 0.10)), (0.93, 0.089, grey), (-0.52, 0.089, (0.42, 0.28, 0.14)), (-0.57, 0.089, grey),
         (-1.825, 0.089, grey)],
        [([(0.22, 0.08), (-0.12, 0.08), (-0.12, 0.225), (-0.02, 0.225)], grey),
         ([(-1.40, 0.08), (-1.80, 0.08), (-1.80, 0.225), (-1.66, 0.225)], grey)])
    sidewinder = missile(
        [(1.425, 0.012, (0.05, 0.05, 0.06)), (1.405, 0.034, (0.05, 0.05, 0.06)), (1.36, 0.052, dark), (1.28, 0.0635, dark),
         (1.02, 0.0635, white), (0.62, 0.0635, (0.72, 0.58, 0.10)), (0.58, 0.0635, white), (-1.425, 0.0635, white)],
        [([(1.27, 0.055), (1.03, 0.055), (1.03, 0.19), (1.09, 0.19)], dark),
         ([(-0.86, 0.055), (-1.41, 0.055), (-1.41, 0.315), (-1.13, 0.315)], white)], 0.010)
    return {"AIM-120C": amraam, "AIM-9M": sidewinder}


# ============================================================ assembling


def build():
    L.begin("f16", TEX, uv_coords, "F16")
    collection = L.CTX["collection"]

    body = build_body()
    wing, lef, flap = build_wing()
    fin, rudder, fin_base = build_fin()
    ventral = build_ventral()
    intake, duct, strut = build_intake()
    glass, frame = build_canopy()
    cockpit = build_cockpit()
    stores, points = build_stores()
    hud = cockpit.pop()
    gear_parts = build_gear()
    build_object("fuselage", [body, wing, wing.mirrored(), fin, fin_base, ventral, ventral.mirrored(), intake, duct, strut,
                              frame, stores, stores.mirrored()] + build_details() + gear_parts["wells"])
    build_object("cockpit", cockpit)
    build_object("nozzle", build_nozzle())
    glass.extend(hud)
    build_object("canopy", [glass])

    # ---- moving surfaces
    a, b = [np.array([x, float(S.wing_le(x) - S.lef_chord(x)), 0.0]) for x in (S.X_ROOT, S.X_TIP)]
    build_object("lef_R", [lef], (b, a - b))
    build_object("lef_L", [lef.mirrored()], (a * (-1, 1, 1), (b - a) * (-1, 1, 1)))
    a, b = [np.array([x, S.WING_TE + float(S.flap_chord(x)), 0.0]) for x in (S.X_ROOT, S.X_FLAP)]
    build_object("flap_R", [flap], (a, b - a))
    build_object("flap_L", [flap.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    stab = Part("paint", "tb")
    airfoil_patch(stab, np.linspace(S.STAB_X0, S.STAB_X1, 10), stab_pos, nc=20, cap0=True, cap1=True)
    a, b = [np.array([x, S.STAB_PIVOT, float(S.stab_z(x))]) for x in (S.STAB_X0, S.STAB_X1)]
    build_object("stab_R", [stab], (a, b - a))
    build_object("stab_L", [stab.mirrored()], (b * (-1, 1, 1), (a - b) * (-1, 1, 1)))
    a, b = [np.array([0.0, float(S.fin_te(z) + S.rudder_chord(z)), z]) for z in (S.RUD_Z0, S.RUD_Z1)]
    build_object("rudder", [rudder], (a, b - a))
    for upper, name in ((True, "sb_up"), (False, "sb_lo")):
        sb = speed_brake(upper)
        o = np.array([S.X_SB0, S.Y_SB0, S.Z_SHELF])
        axis = np.array([-1.0, 0.0, 0.0]) if upper else np.array([1.0, 0.0, 0.0])
        build_object(name + "_R", [sb], (o, axis))
        build_object(name + "_L", [sb.mirrored()], (o * (-1, 1, 1), axis))

    # ---- landing gear, lights, reference points
    # legs and doors: a positive rotation of `retract` / `door` degrees about local X folds them away
    gear = empty("gear", (0, 0, 0))
    for name, (parts, hinge, axis, angle, kind) in gear_parts["moving"].items():
        obj = build_object(name, parts, (hinge, axis), parent=gear)
        obj[kind] = round(angle, 2)
    for name, part in build_lights().items():
        build_object(name, [part])
    for st, p in points.items():
        empty("store_%d" % st, p)
        empty("store_%d" % (10 - st), (-p[0], p[1], p[2]))
    empty("ref_nozzle", (0.0, S.Y_NOZZLE, S.Z_NOZZLE))
    empty("ref_eye", (0.0, 4.22, 1.04))
    empty("ref_gear_nose", (0.0, 3.705, S.Z_GROUND))
    empty("ref_gear_main_R", (1.18, -0.30, S.Z_GROUND))
    empty("ref_gear_main_L", (-1.18, -0.30, S.Z_GROUND))
    empty("ref_wingtip_R", (RAIL_X + RAIL_HW, S.WING_TE, 0.0))
    empty("ref_wingtip_L", (-RAIL_X - RAIL_HW, S.WING_TE, 0.0))
    # effect points for the game: navigation lights, strobe, vapour off the strakes, gun muzzle, tail light
    for side, sfx in ((1.0, "R"), (-1.0, "L")):
        empty("ref_nav_" + sfx, (side * (RAIL_X + RAIL_HW - 0.015), float(S.wing_le(S.X_TIP)) - 0.30, 0.0))
        empty("ref_vapor_" + sfx, (side * 0.93, 2.9, 0.08))
        empty("ref_intake_light_" + sfx, (side * 0.66, 3.6, -0.55))
    empty("ref_strobe", (0.0, float(S.fin_le(S.FIN_Z1)) - 0.45, S.FIN_Z1 + 0.04))
    empty("ref_tail", (0.0, -5.34, 0.665))
    empty("ref_gun", (-0.70, 3.95, 0.10))
    for obj in collection.objects:
        obj["part"] = 1
    for k, (name, part) in enumerate(build_missiles().items()):
        obj = build_object(name, [part])
        obj.parent = None
        obj["part"] = 2
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in collection.objects if o.get("part") == 1 and o.type == "MESH")
    print("objects: %d, triangles: %d" % (len(collection.objects), tris))


# ================================================================ preview
VIEWS = {
    "front": ((9.0, 15.0, 3.2), (0.0, 1.0, 0.1), 50),
    "rear": ((-8.5, -15.0, 4.0), (0.0, -1.0, 0.2), 50),
    "top": ((0.0, 1.2, 30.0), (0.0, 1.3, 0.0), 50),
    "side": ((30.0, 1.5, 0.3), (0.0, 1.5, 0.5), 50),
    "below": ((7.0, 10.0, -6.5), (0.0, 0.5, -0.2), 50),
    "nose": ((3.2, 10.5, 1.7), (0.0, 5.0, 0.4), 50),
    "tail": ((-3.0, -9.5, 1.2), (0.0, -4.2, 0.2), 50),
    "cockpit": ((1.9, 6.6, 2.3), (0.0, 4.3, 0.75), 50),
    "gear": ((5.0, 5.5, -1.0), (0.3, 1.5, -1.0), 50),
    "canopy_front": ((1.6, 7.6, 1.15), (0.0, 4.9, 0.85), 50),
    "canopy_side": ((3.2, 4.2, 1.2), (0.0, 4.3, 0.85), 50),
    "canopy_rear": ((-1.4, 1.2, 1.6), (0.0, 3.8, 0.9), 50),
    "belly": ((2.5, 1.0, -6.0), (0.0, 1.2, -0.8), 50),
}


def main():
    if OPTS["textures"]:
        import f16_paint
        importlib.reload(f16_paint)
        f16_paint.paint_all(TEX)
    if OPTS["build"]:
        build()
    if OPTS["previews"]:
        L.render_previews(OPTS["previews"], OPTS["views"] or list(VIEWS), VIEWS)
    if OPTS["export"]:
        L.export(OUT, WEB, WEB_TEXTURES)
    if OPTS["save"]:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "f16.blend"))


main()
