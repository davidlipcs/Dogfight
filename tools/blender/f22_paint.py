"""Paints the textures of the Blender F-22A Raptor (numpy, runs inside Blender).

Same 4096 x 4096 atlas scheme as the other jets (20 m x 20 m, see f22_shape: ATLAS, V_TOP / V_BOT / V_SIDE,
two fin islands).  Two-tone grey: FS 36375 light grey with soft FS 36170 darker patches on the upper and side
surfaces, the slightly metallic "Have Glass" finish, very few panel lines (a stealth skin) but sawtooth edges on
every door, low visibility markings: the national insignia and the FF tail code.
"""

import math
import os

import numpy as np

import f16_paint as P
import f22_shape as S

N = P.N
PX = N / S.ATLAS
LIGHT = (0.585, 0.605, 0.625)       # FS 36375
DARK = (0.470, 0.490, 0.510)        # FS 36170
MARK = (0.30, 0.31, 0.33)
METAL = (0.30, 0.285, 0.27)


def top(y, x):
    return (np.asarray(y, float) - S.YA0) * PX, (S.V_TOP + np.asarray(x, float)) * PX


def bot(y, x):
    return (np.asarray(y, float) - S.YA0) * PX, (S.V_BOT + np.asarray(x, float)) * PX


def side(y, z):
    return (np.asarray(y, float) - S.YA0) * PX, (S.V_SIDE + np.asarray(z, float)) * PX


def fin_r(y, s):
    u, v = S.fin_island(y, s, 1.0)
    return u * PX, v * PX


def fin_l(y, s):
    u, v = S.fin_island(y, s, -1.0)
    return u * PX, v * PX


poly, rect = P.poly, P.rect


def sawtooth(m, y0, y1, a0, a1, teeth=6, depth=0.12):
    """Outline of a door with the stealthy sawtooth ends (front and back edges zigzag)."""
    pts = []
    for k in range(teeth * 2 + 1):
        a = a0 + (a1 - a0) * k / (teeth * 2)
        pts.append((y1 - (depth if k % 2 else 0.0), a))
    for k in range(teeth * 2 + 1):
        a = a1 - (a1 - a0) * k / (teeth * 2)
        pts.append((y0 + (depth if k % 2 else 0.0), a))
    pts.append(pts[0])
    return poly(m, pts)


# ------------------------------------------------------------------ panel lines
def draw_lines(cv):
    def line(m, pts, width=1.5, strength=0.7):
        cv.groove(poly(m, pts), width, strength)

    xr, xt = S.X_ROOT, S.X_TIP
    lef = lambda x: float(S.wing_le(x) - S.lef_chord(x))      # noqa: E731
    flp = lambda x: float(S.wing_te(x) + S.flap_chord(x))      # noqa: E731
    ail = lambda x: float(S.wing_te(x) + S.ail_chord(x))       # noqa: E731
    for m in (top, bot):
        line(m, [(lef(xr), xr), (lef(xt), xt)], 2.0, 0.9)
        line(m, [(flp(xr), xr), (flp(S.X_FLAP), S.X_FLAP), (float(S.wing_te(S.X_FLAP)), S.X_FLAP)], 2.0, 0.9)
        line(m, [(ail(S.X_FLAP), S.X_FLAP), (ail(S.X_AIL), S.X_AIL), (float(S.wing_te(S.X_AIL)), S.X_AIL)], 2.0, 0.9)
        line(m, [(S.Y_KINK, xr), (S.WING_TE, xr)], 1.3, 0.45)
        for x in (3.0, 4.6):
            line(m, [(float(S.wing_le(x)), x), (lef(x), x)], 1.1, 0.45)
        x0, x1 = S.STAB_X0, S.STAB_X1
        line(m, [(S.STAB_LE0 - 1.4, x0), (float(S.stab_le(x1)) - 0.25, x1)], 1.2, 0.45)
    # top: a few access panels with sawtooth edges, the canopy surround
    for y0, y1, a0, a1 in ((-1.2, 0.2, 0.15, 0.55), (-4.2, -3.0, 0.20, 0.60), (5.8, 6.6, 0.05, 0.30)):
        cv.groove(sawtooth(top, y0, y1, a0, a1, 4, 0.08), 1.3, 0.55)
    # belly: weapons bay doors, gear doors (all sawtooth)
    x0, x1, y0, y1 = S.MAIN_BAY
    cv.groove(sawtooth(bot, y0, y1, 0.0, x1, 6, 0.14), 2.0, 1.0)
    for rect_ in (S.MAIN_WELL, S.SIDE_BAY):
        a0, a1, b0, b1 = rect_
        cv.groove(sawtooth(bot, b0, b1, a0, a1, 4, 0.10), 2.0, 1.0)
    x0, x1, y0, y1 = S.NOSE_WELL
    cv.groove(sawtooth(bot, y0, y1, 0.0, x1, 4, 0.08), 2.0, 1.0)
    # sides: the inlet lip and the gun door line
    line(side, [(S.Y_INTAKE - 0.15, -0.70), (S.Y_INTAKE - 0.15, 0.10)], 1.2, 0.4)
    # fins: rudder hinge
    for m in (fin_r, fin_l):
        hinge = lambda s: float(S.fin_te(s) + S.rudder_chord(s))      # noqa: E731
        line(m, [(hinge(S.RUD_S0), S.RUD_S0), (hinge(S.RUD_S1), S.RUD_S1)], 2.0, 0.9)
        for s in (S.RUD_S0, S.RUD_S1):
            line(m, [(hinge(s), s), (float(S.fin_te(s)), s)], 2.0, 0.9)


def blob(rng, mapfn, cy, cx, ry, rx, n=28):
    """A soft, irregular camouflage patch around (cy, cx) in the view `mapfn`."""
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    k = 1.0 + 0.22 * np.sin(3 * t + rng.uniform(0, 6)) + 0.12 * np.sin(5 * t + rng.uniform(0, 6))
    return poly(mapfn, np.stack([cy + ry * k * np.cos(t), cx + rx * k * np.sin(t)], axis=1))


def paint_base(cv, rng):
    cv.rgb[:] = np.asarray(LIGHT, np.float32)
    cv.rough[:] = 0.46                       # Have Glass: smooth, a little metallic
    cv.metal[:] = 0.10
    # darker patches on the top and the sides (the two-tone scheme), a few under the wings
    patches = [(top, 5.8, 0.3, 1.6, 0.35), (top, 2.6, 0.9, 1.3, 0.6), (top, -0.6, 1.4, 1.8, 0.8), (top, -3.6, 0.8, 1.5, 0.6),
               (top, -1.0, 3.6, 1.2, 0.9), (top, -2.4, 5.6, 0.9, 0.6), (top, -6.4, 0.9, 1.2, 0.5), (top, -7.3, 2.9, 0.9, 0.7),
               (side, 7.2, 0.25, 1.4, 0.25), (side, 3.6, -0.15, 1.2, 0.35), (side, -0.8, 0.05, 1.8, 0.35), (side, -5.0, 0.10, 1.6, 0.30),
               (bot, -0.6, 3.6, 1.1, 0.8), (bot, -5.8, 2.4, 1.0, 0.6)]
    for m, cy, cx, ry, rx in patches:
        cv.fill(blob(rng, m, cy, cx, ry, rx), DARK, 0.85)
    for m in (fin_r, fin_l):
        cv.fill(poly(m, [(S.FIN_YMIN - 0.1, S.FIN_S0 - 0.1), (S.FIN_YMAX + 0.1, S.FIN_S0 - 0.1), (S.FIN_YMAX + 0.1, S.FIN_S1 + 0.1),
                         (S.FIN_YMIN - 0.1, S.FIN_S1 + 0.1)]), LIGHT)
        cv.fill(blob(rng, m, -6.3, 1.2, 1.3, 0.7), DARK, 0.9)
    # the skin under the canopy, the hot nozzle area
    ys = np.linspace(S.CANOPY_Y0 + 0.05, S.CANOPY_Y1 - 0.03, 60)
    cv.fill(poly(top, [(yy, 0.0) for yy in (ys[0], ys[-1])] + [(yy, float(S.CANOPY_W(yy)) * 0.96) for yy in ys[::-1]]),
            (0.08, 0.085, 0.09), rough=0.75)
    for m, b0, b1 in ((top, 0.0, 1.30), (bot, 0.0, 1.30), (side, -0.45, 0.50)):
        cv.fill(rect(m, S.Y_NOZZLE - 0.3, -7.70, b0, b1), METAL, 0.85, rough=0.45, metal=0.9)


def star_and_bar(cv, mapfn, y, x, r, colour):
    c = np.array(mapfn(y, x), float)
    fwd = np.array(mapfn(y + 1.0, x), float) - c
    fwd /= np.hypot(*fwd)
    left = np.array([-fwd[1], fwd[0]])
    rp = r * PX
    cv.fill([c + left * a * rp + fwd * b * rp for a, b in ((-2.1, -0.36), (2.1, -0.36), (2.1, 0.36), (-2.1, 0.36))], colour, 0.85)
    cv.disc(c, rp, colour, 0.85)
    star = []
    for k in range(10):
        a = k * math.pi / 5.0
        rr = rp * (0.92 if k % 2 == 0 else 0.36)
        star.append(c + fwd * math.cos(a) * rr + left * math.sin(a) * rr)
    cv.fill(star, tuple(0.65 * v for v in colour), 1.0)


def paint_markings(cv, rng):
    star_and_bar(cv, top, -1.6, 4.4, 0.28, (0.36, 0.38, 0.40))
    star_and_bar(cv, bot, -1.6, 4.4, 0.28, (0.46, 0.48, 0.50))
    for m in (fin_r, fin_l):
        P.text(cv, "FF", np.array(m(-6.55, 1.35), float), 0.55 * PX * S.FIN_ISLAND_SCALE, MARK, 0.9)
        P.text(cv, "AF", np.array(m(-7.15, 0.55), float), 0.18 * PX * S.FIN_ISLAND_SCALE, MARK, 0.9)
        s0, s1 = 2.20, 2.35                                   # a thin dark squadron band near the top
        cv.fill(poly(m, [(float(S.fin_le(s0)) - 0.02, s0), (float(S.fin_le(s1)) - 0.02, s1), (float(S.fin_te(s1)) + 0.02, s1),
                         (float(S.fin_te(s0)) + 0.02, s0)]), (0.24, 0.25, 0.27), 0.9)
    # walkway and small stencils
    for mapfn, (a0, a1, b0, b1), n in ((top, (-6.0, 6.0, 0.05, 0.6), 18), (bot, (-6.0, 5.0, 0.05, 0.7), 14)):
        for _ in range(n):
            y, b = rng.uniform(a0, a1), rng.uniform(b0, b1)
            x = y
            for _w in range(int(rng.integers(2, 5))):
                w = rng.uniform(0.02, 0.05)
                cv.stroke(poly(mapfn, [(x, b), (x + w, b)]), 1.5, MARK, 0.45, butt=True)
                x += w + 0.014


def paint_all(folder):
    os.makedirs(folder, exist_ok=True)
    cv = P.Canvas()
    rng = np.random.default_rng(22)
    draw_lines(cv)
    paint_base(cv, rng)
    paint_markings(cv, rng)
    P.finish(cv, rng)
    P.save(os.path.join(folder, "f22_basecolor.png"), cv.rgb)
    P.save(os.path.join(folder, "f22_normal.png"), P.normal_map(cv), colour=False)
    orm = np.stack([np.ones((N, N), np.float32), np.clip(cv.rough + 0.12 * cv.lines, 0.05, 1.0), cv.metal], axis=2)
    P.save(os.path.join(folder, "f22_orm.png"), orm, colour=False)
    print("painted f22")
