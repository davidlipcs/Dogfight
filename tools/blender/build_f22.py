"""Builds the F-22A Raptor in Blender and exports it (models/f22/f22.glb, web/assets/f22.glb).

Run it inside Blender like build_f16.py:

    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), {"__file__": path, "OPTS": {...}})

OPTS: build, textures, export, save, previews, views (see build_f16.py).

Same conventions as the other jets: +Y forward, +X right, +Z up, metres.  Moving parts sit on their hinges
with the local X axis along the hinge (a positive rotation: trailing edge down, leading edge down, rudder
trailing edge right); gear legs and doors carry `retract` / `door`.  The weapons are carried inside:

* `bay_*` objects are the weapons bay doors, modelled open, with `bay` = degrees about local X that close
  them and `group` = "main" (the six AIM-120 bay) or "side_L" / "side_R" (one AIM-9 each);
* `rack_N` objects are the launchers of station N: on the AIM-120 stations a trapeze (LAU-142 style) that
  swings down by `rack` degrees about local X, keeping the missile level; on the AIM-9 stations a rail
  (LAU-141 style) that slides out by (`slide_x`, `slide_y`, `slide_z`) metres;
* `store_N` empties are the missiles' places inside the bays (retracted).
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
import f22_shape as S  # noqa: E402

importlib.reload(L)
importlib.reload(f16_shape)
importlib.reload(S)
from aircraft_lib import (C_BLACK, C_CHROME, C_COCKPIT, C_DARK, C_GREY, C_LIGHT, C_STEEL, C_WHITE, Part,  # noqa: E402
                          airfoil_patch, box, build_object, empty, gear_door, gear_well, prism, retract_rotation,
                          rot_x, rotate_about, superellipse, tube, unit, wheel)

OPTS = dict(dict(build=True, textures=True, export=True, save=True, previews=None, views=None, pose=None),
            **globals().get("OPTS", {}))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f22")
TEX = os.path.join(OUT, "textures")
WEB = os.path.join(ROOT, "web", "assets")
WEB_TEXTURES = {"f22_basecolor.png": 2048, "f22_normal.png": 2048, "f22_orm.png": 1024}

# AIM-120 stations in the main bay: station -> (x, y of the missile centre); 2 3 4 left, 5 6 7 right
MAIN_STATIONS = {2: (-0.66, -0.75), 3: (-0.43, -0.35), 4: (-0.20, -0.75), 5: (0.20, -0.75), 6: (0.43, -0.35), 7: (0.66, -0.75)}
SIDE_STATIONS = {1: -1.0, 8: 1.0}               # AIM-9 in the side bays
TRAPEZE_L, TRAPEZE_PHI0, TRAPEZE_PHI1 = 0.75, 8.0, 90.0
HINGE_Z = S.BAY_ROOF - 0.03
SIDE_SLIDE = np.array([0.10, 0.0, -0.44])      # the AIM-9 rail pushes the missile out of the trunk


# ================================================================ texture atlas
def uv_coords(pos, nrm, mode, cent=None):
    """Strips of planar views (see f22_shape: ATLAS, V_TOP / V_BOT / V_SIDE) plus one island per fin."""
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
    """Cut-outs in the skin: gear wells and weapons bays."""
    return ((c[2] < -0.5 and in_rect(S.MAIN_WELL, c, True)) or (c[2] < -0.2 and in_rect(S.NOSE_WELL, c))
            or (c[2] < -0.6 and in_rect(S.MAIN_BAY, c)) or (c[2] < -0.45 and in_rect(S.SIDE_BAY, c, True)))


def build_body():
    part = Part("paint", "auto")
    eps = 0.004
    ys = stations(S.Y_NOSE - 0.02, 9.20, 0.035) + stations(9.20, 8.50, 0.07)[1:] + stations(8.50, S.Y_RADOME, 0.10)[1:]
    for a, b in ((S.Y_RADOME, S.COCKPIT_Y1), (S.COCKPIT_Y1, S.COCKPIT_Y0), (S.COCKPIT_Y0, S.Y_KINK),
                 (S.Y_KINK, S.WING_TE + eps)):
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
    part.fan(front[0], (0.0, S.Y_NOSE, 0.125))

    def behind_wing(y):
        sec = S.Section(min(y, S.WING_TE))
        sec.y = y
        return sec

    def aft_ring(y):
        r = body_ring(behind_wing(y)) if y > -4.0 else body_ring(S.Section(y, blade=False))
        return r
    aft = np.array([aft_ring(y) for y in stations(S.WING_TE + eps, S.Y_BODY_END, 0.11)])
    part.grid(aft, close=True)
    part.ngon(aft[-1])                                    # the engine bulkhead (hidden by the nozzles)
    return part.drop(in_holes)


def wing_pos(x, s, side):
    c = float(S.wing_chord(x))
    t = float(S.wing_t(x))
    return np.stack([np.full(len(s), x), S.wing_le(x) - s * c, float(S.wing_z(x)) + side * f16_shape.yt(s, t) * c], axis=1)


def stab_pos(x, s, side):
    c = float(S.stab_le(x) - S.stab_te(x))
    return np.stack([np.full(len(s), x), S.stab_le(x) - s * c, S.stab_z(x) + side * f16_shape.yt(s, 0.04) * c], axis=1)


def lef_f(x):
    return S.lef_chord(x) / S.wing_chord(x)


def flap_f(x):
    return 1.0 - S.flap_chord(x) / S.wing_chord(x)


def ail_f(x):
    return 1.0 - S.ail_chord(x) / S.wing_chord(x)


def build_wing():
    """Right wing: fixed part, leading edge flap, flaperon, aileron."""
    fixed, lef, flap, ail = (Part("paint", "tb") for _ in range(4))
    inner = np.linspace(S.X_ROOT, S.X_FLAP, 9)
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
    root = np.array([sign * S.FIN_X, 0.0, S.FIN_ZROOT])
    return root + S.fin_span_dir(sign) * s[..., None] + np.array([0.0, 1.0, 0.0]) * y[..., None] + S.fin_normal(sign) * off[..., None]


def build_fins():
    """(fixed fins, {rudder_R, rudder_L}) of the twin canted tails."""
    fixed = Part("paint", "fin")
    rudders = {}
    for sign, name in ((1.0, "R"), (-1.0, "L")):
        def pos(sv, s, side, sign=sign):
            c = float(S.fin_le(sv) - S.fin_te(sv))
            t = 0.05 + (0.035 - 0.05) * (sv - S.FIN_S0) / (S.FIN_S1 - S.FIN_S0)
            sv_arr = np.full(len(s), sv)
            return fin_point(sign, sv_arr, S.fin_le(sv) - s * c, side * f16_shape.yt(s, t) * c)

        def rud_f(sv):
            return 1.0 - S.rudder_chord(sv) / float(S.fin_le(sv) - S.fin_te(sv))
        airfoil_patch(fixed, np.linspace(S.FIN_S0, S.RUD_S0, 3), pos, nc=20, cap1=True)
        airfoil_patch(fixed, np.linspace(S.RUD_S0, S.RUD_S1, 8), pos, None, rud_f, nc=16)
        airfoil_patch(fixed, np.linspace(S.RUD_S1, S.FIN_S1, 8), pos, nc=20, cap0=True, cap1=True)
        rud = Part("paint", "fin")
        airfoil_patch(rud, np.linspace(S.RUD_S0, S.RUD_S1, 8), pos, rud_f, None, nc=8, cap0=True, cap1=True)
        a, b = (fin_point(sign, np.array(s), np.array(float(S.fin_te(s) + S.rudder_chord(s))), np.array(0.0))
                for s in (S.RUD_S0, S.RUD_S1))
        rudders["rudder_" + name] = (rud, a, b - a)
    return fixed, rudders


def intake_ring(y, scale=1.0, dy=0.0, seg=40, sign=1.0):
    xi, xo, zt, zb = S.intake_section(y)
    cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
    cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
    r = superellipse(y, cz, hw * scale, hh * scale, 10.0, 7.0, seg, cx)
    r[:, 0] += (r[:, 2] - cz) * S.INTAKE_SHEAR
    rake = float(S.smoothstep(S.Y_INTAKE - 0.9, S.Y_INTAKE, y))
    r[:, 1] += ((r[:, 2] - cz) * S.INTAKE_RAKE_Z + (r[:, 0] - cx) * S.INTAKE_RAKE_X) * rake + dy
    r[:, 0] *= sign
    return r[::-1] if sign < 0 else r


def build_intakes():
    """Caret inlets under the chine (both sides): trunk skin with a sharp lip, dark duct."""
    skin, duct = Part("paint", "auto"), Part("matte", None, flip=True)
    y0 = S.Y_INTAKE
    ys = [y0, 2.95, 2.80, 2.50, 2.10, 1.60, 1.10, 0.60, 0.20]
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


def nozzles():
    """Two-dimensional F119 nozzles: a fixed housing that turns from the round engine to a flat rectangle,
    with side walls, and the moving upper / lower flaps (vec_L, vec_R: they turn together to vector the
    thrust up and down)."""
    housing, inner = Part("paint", "auto"), Part("metal", None, flip=True)
    flaps = {}
    yt_ = -8.32                                             # the throat: where the flaps are hinged
    for sign, name in ((1.0, "R"), (-1.0, "L")):
        cx, cz = sign * S.X_NOZZLE, S.Z_NOZZLE
        rings = []
        for y, w, h, n in ((S.Y_BODY_END + 0.04, 0.62, 0.42, 3.0), (-8.10, 0.60, 0.38, 5.0), (yt_, S.NOZZLE_W + 0.04,
                                                                                               S.NOZZLE_H + 0.06, 9.0)):
            rings.append(superellipse(y, cz, w, h, n, n, 48, cx))
        housing.grid(rings, close=True)
        # side walls past the throat, out to the exit
        for s in (-1.0, 1.0):
            x = cx + s * (S.NOZZLE_W + 0.02)
            box(housing, (x, -8.62, cz), (0.025, 0.30, S.NOZZLE_H + 0.05))
        wall = [(yt_ - 0.02, S.NOZZLE_W, S.NOZZLE_H, 0.30), (S.Y_BODY_END, 0.55, 0.36, 0.12), (-7.6, 0.45, 0.30, 0.05)]
        for (ya, wa, ha, sa), (yb, wb, hb, _sb) in zip(wall, wall[1:]):
            inner.grid([superellipse(ya, cz, wa, ha, 6, 6, 32, cx), superellipse(yb, cz, wb, hb, 6, 6, 32, cx)], close=True,
                       color=(sa, sa * 0.9, sa * 0.8))
        inner.ngon(superellipse(-7.6, cz, 0.45, 0.30, 6, 6, 32, cx), (0.03, 0.03, 0.03))
        fl = Part("metal", None)
        for s in (1.0, -1.0):                                # upper and lower flap: plates converging to the exit
            z0, z1 = cz + s * (S.NOZZLE_H + 0.02), cz + s * (S.NOZZLE_H - 0.06)
            pts = []
            for y, z in ((yt_, z0), (S.Y_NOZZLE, z1)):
                for xx in (-S.NOZZLE_W, S.NOZZLE_W):
                    pts.append((cx + xx, y, z))
            a, b, c, d = pts
            th = np.array([0.0, 0.0, s * 0.03])
            fl.add([a, b, d, c], [(0, 1, 2, 3)], color=(0.30, 0.29, 0.28))
            fl.add([a + th, c + th, d + th, b + th], [(0, 1, 2, 3)], color=(0.34, 0.33, 0.32))
            fl.add([a, c, c + th, a + th], [(0, 1, 2, 3)], color=(0.30, 0.29, 0.28))
            fl.add([b, b + th, d + th, d], [(0, 1, 2, 3)], color=(0.30, 0.29, 0.28))
            fl.add([c, d, d + th, c + th], [(0, 1, 2, 3)], color=(0.22, 0.20, 0.19))
        flaps["vec_" + name] = (fl, np.array([cx, yt_, cz]))
    return [housing, inner], flaps


def build_canopy():
    """The F-22's frameless, gold tinted one piece canopy, with a thin sill rail."""
    glass, frame = Part("glass", None), Part("matte", None)

    def arc(y, grow=0.0, a0=-14.0, a1=194.0, seg=34):
        w, zs = S.canopy_sill(y)
        h = float(S.CANOPY_H(y)) + grow
        w += grow
        t = np.radians(np.linspace(a0, a1, seg + 1))
        c, s = np.cos(t), np.sin(t)
        z = np.where(s >= 0, zs + h * np.abs(s) ** (2.0 / 2.25), zs + 0.3 * w * s)
        return np.stack([w * np.sign(c) * np.abs(c) ** (2.0 / 2.25), np.full(len(t), y), z], axis=1)
    ys = np.linspace(S.CANOPY_Y1, S.CANOPY_Y0, 34)
    glass.grid([arc(y) for y in ys])
    col = (0.16, 0.17, 0.18)
    for side in (1.0, -1.0):
        rails = []
        for y in np.linspace(S.CANOPY_Y0 + 0.10, S.CANOPY_Y1 - 0.12, 44):
            w, zs = S.canopy_sill(y)
            t = np.radians(np.array([-6.0, -2.0, 3.0, 6.0]))
            g = np.array([0.003, 0.012, 0.012, 0.003])
            h = float(S.CANOPY_H(y))
            rails.append(np.stack([side * (w + g) * np.cos(t), np.full(4, y),
                                   zs + (h + g) * np.maximum(np.sin(t), 0.0) ** (2.0 / 2.25)
                                   + 0.3 * w * np.minimum(np.sin(t), 0.0)], axis=1))
        frame.grid(rails, color=col)
    return glass, frame


def build_cockpit():
    """Tub, sill, ACES II seat, the glass cockpit (PMFD, three MFDs, two UFDs: screen_* objects), ICP,
    glareshield, wide HUD, side stick and throttles.  Returns (static parts, {screen name: part})."""
    tub, room = Part("matte", None, flip=True, color=C_COCKPIT), Part("matte", None, color=C_COCKPIT)
    hudglass = Part("hud", None)
    y0, y1, floor = S.COCKPIT_Y0, S.COCKPIT_Y1, 0.30
    ys = np.linspace(y0, y1, 18)
    wy = lambda y: S.cockpit_w(y) - 0.01                    # noqa: E731
    sill_out = lambda y: min(wy(y) + 0.075, float(S.CANOPY_W(y)) - 0.012)   # noqa: E731
    rim = [(wy(y), y, float(S.body_top(y, wy(y))[0]) + 0.004) for y in ys]
    rim = np.array(rim + [(-x, y, z) for x, y, z in rim[::-1]])
    low = rim.copy()
    low[:, 2] = floor
    tub.grid([rim, low], close=True)
    tub.ngon(low, (0.20, 0.21, 0.22))
    sill = Part("matte", None, color=(0.22, 0.23, 0.24))
    for side in (1.0, -1.0):
        strips = []
        for y in np.linspace(y0 - 0.07, y1 + 0.07, 30):
            xs = np.array([wy(y) - 0.045, wy(y) - 0.045, sill_out(y), sill_out(y)])
            top = S.body_top(y, np.array([wy(y) - 0.045, sill_out(y)])) + 0.012
            strips.append(np.stack([side * xs, np.full(4, y), [top[0] - 0.05, top[0], top[1], top[1] - 0.02]], axis=1))
        sill.grid(strips)

    # ---- the glass cockpit: panel tilted back 15 degrees, its face at y ~ 4.95
    w = 0.40
    tilt = rot_x(-15.0)
    pan_c = np.array([0.0, 4.98, 0.83])
    pan_n = tilt @ np.array([0.0, -1.0, 0.0])
    pan_up = tilt @ np.array([0.0, 0.0, 1.0])
    box(room, pan_c - pan_n * 0.03, (w, 0.03, 0.28), tilt, (0.11, 0.115, 0.12))
    box(room, (0.0, 4.92, 0.36), (0.15, 0.12, 0.07), color=(0.13, 0.135, 0.14))          # knee well column
    screens = {}

    def display(name, cx, cz, hw, hh, buttons=True):
        c = pan_c + np.array([cx, 0.0, 0.0]) + pan_up * cz
        box(room, c + pan_n * 0.012, (hw + 0.026, 0.012, hh + 0.026), tilt, (0.06, 0.06, 0.065))
        if buttons:
            for k in range(5):
                t = (k - 2) / 2.6
                for off in ((t * hw, hh + 0.017), (t * hw, -hh - 0.017), (hw + 0.017, t * hh), (-hw - 0.017, t * hh)):
                    p = c + pan_n * 0.026 + np.array([off[0], 0.0, 0.0]) + pan_up * off[1]
                    box(room, p, (0.007, 0.005, 0.005), tilt, (0.30, 0.31, 0.31))
        scr = Part("screen", None)
        box(scr, c + pan_n * 0.024, (hw, 0.002, hh), tilt)
        screens[name] = scr
    display("screen_pmfd", 0.0, -0.01, 0.100, 0.100)          # primary multifunction display (8 x 8 in)
    display("screen_mfd_l", -0.245, -0.03, 0.080, 0.080)      # secondary displays (6.25 x 6.25 in)
    display("screen_mfd_r", 0.245, -0.03, 0.080, 0.080)
    display("screen_mfd_c", 0.0, -0.245, 0.080, 0.080)
    display("screen_ufd_l", -0.155, 0.195, 0.052, 0.040, buttons=False)     # up front displays beside the ICP
    display("screen_ufd_r", 0.155, 0.195, 0.052, 0.040, buttons=False)
    c = pan_c + pan_up * 0.195                                # integrated control panel (keypad)
    box(room, c + pan_n * 0.015, (0.075, 0.015, 0.05), tilt, (0.07, 0.07, 0.075))
    for k in range(12):
        p = c + pan_n * 0.032 + np.array([-0.045 + 0.03 * (k % 4), 0.0, 0.0]) + pan_up * (0.03 - 0.022 * (k // 4))
        box(room, p, (0.010, 0.005, 0.007), tilt, (0.28, 0.29, 0.29))
    # glareshield and the wide-angle HUD
    hood = []
    hw = min(w + 0.02, float(S.CANOPY_W(5.15)) - 0.08)
    for x in np.linspace(-hw, hw, 11):
        zz = 1.12 + 0.03 * (1.0 - (x / hw) ** 2)
        za, zb = min(zz, S.canopy_z(4.92, x) - 0.05), min(zz - 0.03, S.canopy_z(5.25, x) - 0.05)
        hood.append([(x, 4.92, za - 0.02), (x, 4.92, za), (x, 5.25, zb), (x, 5.25, zb - 0.02)])
    room.grid(hood, color=(0.05, 0.05, 0.055))
    box(room, (0.0, 5.10, 1.145), (0.11, 0.12, 0.035), color=(0.07, 0.07, 0.08))
    r = rot_x(22.0)
    for side in (1.0, -1.0):
        box(room, (side * 0.118, 5.06, 1.25), (0.005, 0.012, 0.08), r, (0.07, 0.07, 0.08))
    box(hudglass, (0.0, 5.06, 1.25), (0.115, 0.002, 0.08), r)
    # side consoles, throttles on the left, side stick on the right
    for side in (1.0, -1.0):
        box(room, (side * (S.COCKPIT_W - 0.08), 4.05, 0.62), (0.07, 0.62, 0.17))
        box(room, (side * (S.COCKPIT_W - 0.08), 4.05, 0.795), (0.065, 0.58, 0.006), color=(0.09, 0.09, 0.10))
        rng = np.random.default_rng(5 if side > 0 else 6)
        for _ in range(14):
            p = (side * (S.COCKPIT_W - 0.08) + rng.uniform(-0.045, 0.045), rng.uniform(3.55, 4.55), 0.804)
            box(room, p, (0.008, 0.008, 0.006), color=(0.30, 0.31, 0.32))
    for dx in (-0.015, 0.025):
        tube(room, [(-S.COCKPIT_W + 0.08 + dx, 4.30, 0.80), (-S.COCKPIT_W + 0.08 + dx, 4.36, 0.91)], 0.012, 8, (0.08, 0.08, 0.09))
        box(room, (-S.COCKPIT_W + 0.08 + dx, 4.37, 0.93), (0.018, 0.035, 0.02), color=(0.07, 0.07, 0.08))
    xs = S.COCKPIT_W - 0.08
    tube(room, [(xs, 4.42, 0.80), (xs, 4.44, 0.88), (xs, 4.46, 0.93)], [0.016, 0.014, 0.013], 8, (0.08, 0.08, 0.09))
    box(room, (xs, 4.46, 0.96), (0.02, 0.026, 0.04), color=(0.06, 0.06, 0.07))
    # ACES II ejection seat, reclined 15 degrees
    seat = Part("matte", None, color=(0.15, 0.16, 0.17))
    r = rot_x(15.0)
    box(seat, (0.0, 4.10, 0.45), (0.22, 0.24, 0.08))
    box(seat, (0.0, 4.12, 0.545), (0.19, 0.20, 0.03), color=(0.22, 0.24, 0.20))
    back = np.array([0.0, 3.86, 0.47])
    up = r @ np.array([0.0, 0.0, 1.0])
    fwd = r @ np.array([0.0, 1.0, 0.0])
    box(seat, back + up * 0.40 - fwd * 0.04, (0.22, 0.06, 0.42), r)
    box(seat, back + up * 0.38 + fwd * 0.035, (0.17, 0.03, 0.33), r, (0.22, 0.24, 0.20))
    box(seat, back + up * 0.88, (0.14, 0.08, 0.12), r, (0.10, 0.10, 0.11))
    tube(seat, [(-0.08, 4.32, 0.54), (-0.08, 4.36, 0.61), (0.08, 4.36, 0.61), (0.08, 4.32, 0.54)], 0.012, 8, (0.80, 0.68, 0.10))
    box(room, (0.0, 3.35, 0.82), (S.COCKPIT_W - 0.02, 0.13, 0.12), color=(0.18, 0.19, 0.20))
    drop = L.fit_under_canopy([seat], S)                  # the head box stays under the canopy
    print("seat lowered by %.3f m" % drop)
    return [tub, room, sill, seat, hudglass], screens


def build_gear():
    """Nose gear folding forwards, main gears folding forwards and up into the wells outboard of the bay."""
    zg = S.Z_GROUND
    moving = {}
    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    hinge = np.array([0.0, 5.32, -0.42])
    c = np.array([0.0, 5.12, zg + 0.31])
    tube(white, [hinge, (0, 5.24, -1.00), (0, 5.15, c[2] + 0.28)], [0.065, 0.06, 0.055], 12)
    tube(metal, [(0, 5.17, -1.10), (0, 5.13, c[2] + 0.04)], 0.042, 12)
    tube(metal, [c + (-0.14, 0, 0), c + (0.14, 0, 0)], 0.028, 10)
    wheel(tire, white, c, 0.31, 0.17)
    lamps = Part("light_white", None)
    tube(white, [(0.07, 5.25, -0.92), (0.07, 5.32, -0.92)], [0.04, 0.045], 12, C_GREY)
    lamps.ngon([(0.07 + 0.038 * math.cos(a), 5.322, -0.92 + 0.038 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    moving["gear_nose"] = ([tire, white, metal, lamps], hinge, (1.0, 0.0, 0.0), 100.0, "retract")
    x0, x1, y0, y1 = S.NOSE_WELL
    z_nose = lambda x: float(S.body_bottom(0.5 * (y0 + y1), abs(x))[0])   # noqa: E731
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = gear_door(side * x1, side * 0.003, y0, y1, z_nose)
        moving["door_nose_" + name] = ([part], h, axis, ang, "door")
    wells = [gear_well(S.NOSE_WELL, lambda x, y: float(S.body_bottom(y, abs(x))[0]), -0.05)]

    tire, white, metal = Part("matte", None), Part("matte", None, color=C_WHITE), Part("metal", None, color=C_CHROME)
    c = np.array([1.62, -1.85, zg + 0.37])
    top, axle = np.array([1.18, -2.25, -0.70]), np.array([1.50, -1.85, c[2] + 0.04])
    knee = top + (axle - top) * 0.55
    tube(white, [top, knee], [0.075, 0.068], 12)
    tube(metal, [knee, axle], 0.05, 12)
    tube(metal, [axle + (0.0, 0, -0.02), c + (0.03, 0, 0)], 0.04, 10)
    tube(white, [knee + (0.0, 0.0, 0.05), top + (-0.05, 0.40, 0.04)], 0.035, 10)
    wheel(tire, white, c, 0.37, 0.23, (1.0, 0.0, -0.05))
    main = [tire, white, metal]
    a0 = unit((1.0, 0.0, -0.05))
    d0 = unit(axle - top)
    d1 = unit((-0.20, 0.97, 0.12))
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
        wells.append(gear_well(S.MAIN_WELL, lambda x, y: float(S.body_bottom(y, abs(x))[0]), -0.15, side))
    return dict(moving=moving, wells=wells)


def bay_door(x_hinge, x_far, y0, y1, z_of, thick=0.018):
    """A weapons bay door (sawtooth ends are painted), modelled open like a gear door."""
    part, h, axis, ang = gear_door(x_hinge, x_far, y0, y1, z_of, thick)
    return part, h, axis, ang


def build_bays():
    """Weapons bays: dark boxes behind the cut-outs, doors (moving), launchers (moving), station points."""
    wells, doors, racks, points = [], {}, {}, {}
    belly = lambda x, y: float(S.body_bottom(y, abs(x))[0])     # noqa: E731
    wells.append(gear_well(S.MAIN_BAY, belly, S.BAY_ROOF, margin=0.02))
    x0, x1, y0, y1 = S.MAIN_BAY
    zm = lambda x: float(S.body_bottom(0.5 * (y0 + y1), abs(x))[0])      # noqa: E731
    for side, name in ((1.0, "R"), (-1.0, "L")):
        part, h, axis, ang = bay_door(side * x1, side * 0.004, y0, y1, zm)
        doors["bay_main_" + name] = (part, h, axis, ang, "main")
    # side bays in the lower outer corner of each inlet trunk
    sx0, sx1, sy0, sy1 = S.SIDE_BAY

    def trunk(x, y):
        return min(float(S.body_bottom(y, abs(x))[0]), S.intake_bottom(y, x) if y > 0.2 else 9.0)
    for side, name in ((1.0, "R"), (-1.0, "L")):
        wells.append(gear_well(S.SIDE_BAY, trunk, -0.32, side, margin=0.02))
        zs = lambda x: trunk(x, 0.5 * (sy0 + sy1))            # noqa: E731
        part, h, axis, ang = bay_door(side * sx1, side * sx0, sy0, sy1, zs)
        doors["bay_side_" + name] = (part, h, axis, ang, "side_" + name)
    # AIM-120 trapeze launchers: two parallel links from the bay roof; the missile hangs level below them
    phi0 = math.radians(TRAPEZE_PHI0)
    for st, (x, yc) in MAIN_STATIONS.items():
        hinge = np.array([x, yc + TRAPEZE_L * math.cos(phi0), HINGE_Z])
        attach = hinge + TRAPEZE_L * np.array([0.0, -math.cos(phi0), -math.sin(phi0)])
        part = Part("metal", None, color=(0.42, 0.43, 0.45))
        for dx in (-0.045, 0.045):
            tube(part, [hinge + (dx, 0, 0), attach + (dx, 0, 0)], 0.016, 8)
        tube(part, [hinge + (-0.06, 0, 0), hinge + (0.06, 0, 0)], 0.022, 8, (0.25, 0.26, 0.27))
        box(part, attach + (0.0, 0.0, -0.015), (0.03, 0.42, 0.012), color=(0.30, 0.31, 0.32))
        racks["rack_%d" % st] = (part, hinge, {"rack": TRAPEZE_PHI1 - TRAPEZE_PHI0})
        points[st] = (x, yc, float(attach[2]) - 0.12)
    # AIM-9 rails in the side bays: they slide down and out of the trunk
    for st, side in SIDE_STATIONS.items():
        x, yc, z = side * 1.23, 1.15, -0.60
        part = Part("metal", None, color=(0.42, 0.43, 0.45))
        box(part, (x, yc, z + 0.085), (0.025, 0.95, 0.018))
        for dy in (-0.55, 0.55):
            box(part, (x, yc + dy, z + 0.20), (0.02, 0.03, 0.10))
        racks["rack_%d" % st] = (part, np.array([x, yc, z + 0.085]),
                                 {"slide_x": float(side * SIDE_SLIDE[0]), "slide_y": 0.0, "slide_z": float(SIDE_SLIDE[2])})
        points[st] = (x, yc, z)
    return wells, doors, racks, points


def build_details():
    grey, metal = Part("matte", None, color=C_GREY), Part("metal", None, color=C_STEEL)
    blade = [(0.0, 0.0), (0.16, 0.0), (0.13, 0.12), (0.07, 0.12)]
    prism(grey, (0.0, 1.2, float(S.BODY[0](1.2)) - 0.02), (0, -1, 0), (0, 0, 1), np.array(blade) * 1.2, 0.02)
    prism(grey, (0.0, 4.6, float(S.BODY[1](4.6)) + 0.02), (0, -1, 0), (0, 0, -1), np.array(blade) * 1.1, 0.02)
    # the gun port door over the right wing root
    z = float(S.body_top(2.1, 1.20)[0])
    box(grey, (1.20, 2.10, z + 0.004), (0.10, 0.22, 0.006), color=(0.36, 0.37, 0.38))
    # static dischargers
    for side in (1.0, -1.0):
        for x in (S.X_TIP - 0.25, S.X_TIP - 0.8):
            a = np.array([side * x, float(S.wing_te(x)), float(S.wing_z(x))])
            tube(grey, [a + (0, 0.02, 0), a + (0, -0.14, 0)], 0.004, 5, C_DARK)
    return [grey, metal]


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
    x = S.X_TIP - 0.10
    le, zt = float(S.wing_le(x)), float(S.wing_z(x))
    for name, mat, side in (("light_nav_R", "light_green", 1.0), ("light_nav_L", "light_red", -1.0)):
        p = Part(mat, None)
        lamp(p, (side * x, le - 0.25, zt), 0.025, (1.0, 2.0, 0.6))
        out[name] = p
    p = Part("light_white", None)
    for side in (1.0, -1.0):
        tip = fin_point(side, np.array(S.FIN_S1 - 0.05), np.array(float(S.fin_te(S.FIN_S1)) + 0.10), np.array(0.0))
        lamp(p, tip, 0.03, (1.0, 1.0, 1.0))
    out["light_tail"] = p
    p = Part("light_strip", None)
    for side in (1.0, -1.0):
        for s0, s1 in ((1.6, 2.2),):
            a = fin_point(side, np.array([s0, s1]), np.array([float(S.fin_le(s0)) - 0.45, float(S.fin_le(s1)) - 0.45]), np.array([0.03, 0.025]))
            b = a + np.array([0.0, -0.05, 0.0])
            p.ngon([a[0], b[0], b[1], a[1]])
    out["light_formation"] = p
    return out


# ============================================================ assembling
def build():
    L.begin("f22", TEX, uv_coords, "F22", glass=(0.55, 0.42, 0.12), glass_alpha=0.36)
    collection = L.CTX["collection"]
    body = build_body()
    wing, lef, flap, ail = build_wing()
    fins, rudders = build_fins()
    intakes, ducts = build_intakes()
    glass, frame = build_canopy()
    cockpit, screens = build_cockpit()
    gear_parts = build_gear()
    bay_wells, doors, racks, points = build_bays()
    housing, vec = nozzles()
    hud = cockpit.pop()
    build_object("fuselage", [body, wing, wing.mirrored(), fins, intakes, ducts, frame] + build_details()
                 + gear_parts["wells"] + bay_wells)
    build_object("cockpit", cockpit)
    for name, part in screens.items():
        build_object(name, [part])
    build_object("nozzle", housing)
    build_object("canopy", [glass])
    build_object("hud_glass", [hud])

    # ---- moving surfaces
    def te(x):
        return float(S.wing_te(x))
    a, b = [np.array([x, float(S.wing_le(x) - S.lef_chord(x)), float(S.wing_z(x))]) for x in (S.X_ROOT, S.X_TIP)]
    build_object("lef_R", [lef], (b, a - b))
    build_object("lef_L", [lef.mirrored()], (a * (-1, 1, 1), (b - a) * (-1, 1, 1)))
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
    for name, (part, hinge) in vec.items():
        build_object(name, [part], (hinge, (1.0, 0.0, 0.0)))

    # ---- gear, weapons bays, lights, reference points
    gear = empty("gear", (0, 0, 0))
    for name, (parts, hinge, axis, angle, kind) in gear_parts["moving"].items():
        obj = build_object(name, parts, (hinge, axis), parent=gear)
        obj[kind] = round(angle, 2)
    for name, (part, hinge, axis, angle, group) in doors.items():
        obj = build_object(name, [part], (hinge, axis))
        obj["bay"] = round(angle, 2)
        obj["group"] = group
    for name, (part, hinge, props) in racks.items():
        obj = build_object(name, [part], (hinge, (1.0, 0.0, 0.0)))
        for k, v in props.items():
            obj[k] = round(float(v), 3)
    for name, part in build_lights().items():
        build_object(name, [part])
    for st, p in points.items():
        empty("store_%d" % st, p)
    for side, sfx in ((1.0, "R"), (-1.0, "L")):
        empty("ref_nozzle_" + sfx, (side * S.X_NOZZLE, S.Y_NOZZLE, S.Z_NOZZLE))
        empty("ref_wingtip_" + sfx, (side * (S.X_TIP - 0.05), float(S.wing_te(S.X_TIP)) + 0.3, float(S.wing_z(S.X_TIP))))
        empty("ref_gear_main_" + sfx, (side * 1.62, -1.85, S.Z_GROUND))
        empty("ref_vapor_" + sfx, (side * 1.75, 1.4, float(S.wing_z(1.75)) + 0.08))
        x = S.X_TIP - 0.10
        empty("ref_nav_" + sfx, (side * x, float(S.wing_le(x)) - 0.25, float(S.wing_z(x))))
        tip = fin_point(side, np.array(S.FIN_S1 + 0.04), np.array(float(S.fin_le(S.FIN_S1)) - 0.40), np.array(0.0))
        empty("ref_strobe_" + sfx, tuple(tip))
    empty("ref_eye", (0.0, 4.02, 1.30))
    empty("ref_gun", (1.20, 2.35, float(S.body_top(2.1, 1.20)[0]) + 0.02))
    empty("ref_gear_nose", (0.0, 5.12, S.Z_GROUND))
    empty("ref_tail", (0.0, -8.40, 0.05))
    for obj in collection.objects:
        obj["part"] = 1
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in collection.objects if o.type == "MESH")
    print("objects: %d, triangles: %d" % (len(collection.objects), tris))
    # the missiles' launch points with the launchers out (for specs.js)
    phi1 = math.radians(TRAPEZE_PHI1)
    for st, (x, yc) in MAIN_STATIONS.items():
        hinge = np.array([x, yc + TRAPEZE_L * math.cos(math.radians(TRAPEZE_PHI0)), HINGE_Z])
        att = hinge + TRAPEZE_L * np.array([0.0, -math.cos(phi1), -math.sin(phi1)])
        print("launch %d: %.3f %.3f %.3f" % (st, att[0], att[1], att[2] - 0.12))
    for st, p in points.items():
        if st in SIDE_STATIONS:
            q = np.array(p) + SIDE_SLIDE * np.array([np.sign(p[0]), 1, 1])
            print("launch %d: %.3f %.3f %.3f" % (st, q[0], q[1], q[2]))


# ================================================================ preview
VIEWS = {
    "front": ((11.0, 18.0, 4.0), (0.0, 0.0, 0.2), 50),
    "rear": ((-10.5, -18.0, 5.0), (0.0, -1.5, 0.3), 50),
    "top": ((0.0, 0.0, 40.0), (0.0, 0.0, 0.0), 50),
    "side": ((40.0, 0.0, 0.4), (0.0, 0.0, 0.6), 50),
    "below": ((8.0, 10.0, -9.0), (0.0, 0.0, -0.5), 50),
    "frontlow": ((0.0, 22.0, 0.3), (0.0, 0.0, 0.3), 50),
    "nose": ((3.6, 12.0, 2.0), (0.0, 5.5, 0.6), 50),
    "tail": ((-4.5, -14.0, 2.6), (0.0, -7.0, 0.6), 50),
    "cockpit": ((2.0, 7.0, 2.8), (0.0, 4.4, 1.0), 50),
    "bay": ((3.5, 3.0, -5.5), (0.0, -0.3, -0.9), 45),
    "inside": ((0.0, 4.02, 1.30), (0.0, 5.6, 1.0), 24),
}


def pose(gear=0.0, bays=0.0, racks=0.0):
    """Preview poses: gear 1 = folded away, bays 1 = doors closed, racks 1 = launchers out."""
    from mathutils import Matrix, Vector
    bpy.context.view_layer.update()                      # matrix_local is only valid after an update
    for o in bpy.data.objects:
        if "part" not in o.keys():
            continue
        rest = o.matrix_local.copy()
        if "retract" in o.keys() or "door" in o.keys():
            o.matrix_local = rest @ Matrix.Rotation(math.radians(o.get("retract", o.get("door", 0.0)) * gear), 4, "X")
        elif "bay" in o.keys():
            o.matrix_local = rest @ Matrix.Rotation(math.radians(o["bay"] * bays), 4, "X")
        elif "rack" in o.keys():
            o.matrix_local = rest @ Matrix.Rotation(math.radians(o["rack"] * racks), 4, "X")
        elif "slide_x" in o.keys():
            o.matrix_local = Matrix.Translation(Vector((o["slide_x"], o["slide_y"], o["slide_z"])) * racks) @ rest


def main():
    L.CTX["prefix"] = "f22"
    if OPTS["textures"] and os.path.exists(os.path.join(HERE, "f22_paint.py")):
        import f22_paint
        importlib.reload(f22_paint)
        f22_paint.paint_all(TEX)
    if OPTS["build"]:
        build()
    if OPTS["pose"]:
        pose(**OPTS["pose"])
    if OPTS["previews"]:
        L.render_previews(OPTS["previews"], OPTS["views"] or list(VIEWS), VIEWS)
    if OPTS["export"]:
        L.export(OUT, WEB, WEB_TEXTURES)
    if OPTS["save"]:
        os.makedirs(OUT, exist_ok=True)
        L.viewport_like_game()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "f22.blend"))


main()
