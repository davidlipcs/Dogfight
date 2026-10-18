"""Paints the textures of the Blender F-15EX Eagle II (numpy, runs inside Blender).

Same 4096 x 4096 atlas scheme as the other jets (21 m x 21 m, see f15_shape: ATLAS, V_TOP / V_BOT / V_SIDE, two fin
islands).  "Mod Eagle" two-tone grey: FS 36176 dark grey on the upper surfaces and the sides above the wing line,
FS 36251 medium grey below, a lighter radome, panel lines and rivet rows, the national insignia and the ET tail
code of the Eglin test wing.
"""

import math
import os

import numpy as np

import f16_paint as P
import f15_shape as S

N = P.N
PX = N / S.ATLAS
DARK = (0.380, 0.405, 0.430)        # FS 36176
MEDIUM = (0.505, 0.535, 0.565)      # FS 36251
MARK = (0.20, 0.21, 0.23)
METAL = (0.30, 0.285, 0.27)

GLYPHS = dict(P.GLYPHS)
GLYPHS.update({
    "E": [[(4, 5.5), (0.5, 5.5), (0.5, 0.5), (4, 0.5)], [(0.5, 3), (3, 3)]],
    "T": [[(0.3, 5.5), (3.7, 5.5)], [(2, 5.5), (2, 0)]],
    "X": [[(0.5, 6), (3.5, 0)], [(3.5, 6), (0.5, 0)]],
    "U": [[(0.5, 6), (0.5, 1.5), (1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 6)]],
    "S": [[(3.5, 4.6), (2.5, 5.5), (1.5, 5.5), (0.5, 4.6), (0.5, 3.9), (1.4, 3), (2.6, 3), (3.5, 2.1), (3.5, 1.4),
           (2.5, 0.5), (1.5, 0.5), (0.5, 1.4)]],
})


def text(cv, string, centre, height, colour, alpha=1.0):
    old = P.GLYPHS
    P.GLYPHS = GLYPHS
    try:
        P.text(cv, string, centre, height, colour, alpha)
    finally:
        P.GLYPHS = old


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


def draw_lines(cv):
    def line(m, pts, width=1.5, strength=0.75):
        cv.groove(poly(m, pts), width, strength)

    def box(m, a0, a1, b0, b1, **kw):
        line(m, [(a0, b0), (a1, b0), (a1, b1), (a0, b1), (a0, b0)], **kw)
    xr, xt = S.X_ROOT, S.X_TIP
    te = lambda x: float(S.wing_te(x))                          # noqa: E731
    flp = lambda x: te(x) + float(S.flap_chord(x))             # noqa: E731
    ail = lambda x: te(x) + float(S.ail_chord(x))              # noqa: E731
    for m in (top, bot):
        line(m, [(flp(xr), xr), (flp(S.X_FLAP), S.X_FLAP), (te(S.X_FLAP), S.X_FLAP)], 2.2, 1.0)
        line(m, [(ail(S.X_FLAP), S.X_FLAP), (ail(S.X_AIL), S.X_AIL), (te(S.X_AIL), S.X_AIL)], 2.2, 1.0)
        line(m, [(S.Y_KINK, xr), (S.WING_TE, xr)], 1.6, 0.6)
        for x in (2.2, 3.0, 3.8, 4.6, 5.4):
            line(m, [(float(S.wing_le(x)) - 0.05, x), (flp(x) if x < S.X_FLAP else ail(x) if x < S.X_AIL else te(x), x)])
        for f in (0.25, 0.55):
            line(m, [(float(S.wing_le(xr)) - f * float(S.wing_chord(xr)), xr), (float(S.wing_le(xt)) - f * float(S.wing_chord(xt)), xt)], 1.3, 0.55)
        x0, x1 = S.STAB_X0, S.STAB_X1
        line(m, [(S.STAB_LE0 - 0.8, x0), (float(S.stab_le(x1)) - 0.25, x1)], 1.2, 0.5)
        for x in (2.3, 3.2):
            line(m, [(float(S.stab_le(x)), x), (float(S.stab_te(x)), x)], 1.2, 0.5)
    # top of the fuselage
    line(top, [(S.Y_RADOME, 0.0), (S.Y_RADOME, 0.46)], 2.4, 1.0)
    for y in (7.2, 6.6, 2.6, 1.6, 0.6, -0.6, -1.8, -3.0, -4.2, -5.4, -6.6):
        line(top, [(y, 0.0), (y, float(S.BODY[2](y)) * 0.9)])
    box(top, 0.05, 1.55, 0.0, 0.50, width=2.2, strength=1.0)             # the dorsal speed brake
    line(top, [(2.4, 0.62), (-7.4, 0.62)])
    box(top, -3.6, -2.8, 0.75, 1.10, width=1.2, strength=0.55)
    box(top, -5.8, -4.9, 0.75, 1.05, width=1.2, strength=0.55)
    # belly and sides
    line(bot, [(S.Y_RADOME, 0.0), (S.Y_RADOME, 0.46)], 2.4, 1.0)
    for y in (7.0, 6.4, 4.0, 3.0, 2.0, -1.8, -2.8, -3.8, -4.8, -5.8, -6.8):
        line(bot, [(y, 0.0), (y, 1.2)])
    x0, x1, y0, y1 = S.NOSE_WELL
    box(bot, y0, y1, 0.0, x1, width=2.0, strength=1.0)
    x0, x1, y0, y1 = S.MAIN_WELL
    box(bot, y0, y1, x0, x1, width=2.0, strength=1.0)
    zt, zb = (lambda y: float(S.BODY[0](y))), (lambda y: float(S.BODY[1](y)))
    line(side, [(S.Y_RADOME, zb(S.Y_RADOME) - 0.02), (S.Y_RADOME, zt(S.Y_RADOME) + 0.02)], 2.4, 1.0)
    for y in (7.3, 6.7, 3.6, 2.8, 2.0, 1.2, 0.4, -0.6, -1.6, -2.6, -3.6, -4.6, -5.6, -6.6):
        line(side, [(y, zb(y)), (y, 0.60 if y < 6.0 else zt(y) - 0.12)])
    line(side, [(-7.4, 0.05), (4.0, 0.10)])
    box(side, 6.6, 7.4, 0.15, 0.55, width=1.3, strength=0.6)
    line(side, [(S.Y_INTAKE - 0.6, -0.55), (S.Y_INTAKE - 0.6, 0.85)], 1.6, 0.8)                # the intake ramp line
    for m in (fin_r, fin_l):
        hinge = lambda s: float(S.fin_te(s) + S.rudder_chord(s))      # noqa: E731
        line(m, [(hinge(S.RUD_S0), S.RUD_S0), (hinge(S.RUD_S1), S.RUD_S1)], 2.2, 1.0)
        for s in (S.RUD_S0, S.RUD_S1):
            line(m, [(hinge(s), s), (float(S.fin_te(s)), s)], 2.2, 1.0)
        for s in (0.7, 1.6, 2.3):
            line(m, [(float(S.fin_le(s)), s), (float(S.fin_te(s)) if s > S.RUD_S1 else hinge(s), s)])


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


def paint_base(cv, rng):
    cols = (np.arange(N, dtype=np.float32) + 0.5) / PX + S.YA0
    dk, md = np.asarray(DARK, np.float32), np.asarray(MEDIUM, np.float32)
    cv.rgb[0:int(7 * PX)] = dk                          # upper surfaces: dark grey
    cv.rgb[int(7 * PX):int(14 * PX)] = md               # lower surfaces: medium grey
    r0, r1 = int(14 * PX), N                            # sides: dark above the wing line, medium below
    z = ((np.arange(r0, r1, dtype=np.float32) + 0.5) / PX - S.V_SIDE)[:, None]
    edge = 0.35 + 0.0 * cols[None, :]
    below = S.smoothstep(0.07, -0.07, z - edge)[..., None]
    cv.rgb[r0:r1] = dk * (1.0 - below) + md * below
    for m in (fin_r, fin_l):
        cv.fill(poly(m, [(S.FIN_YMIN - 0.1, S.FIN_S0 - 0.1), (S.FIN_YMAX + 0.1, S.FIN_S0 - 0.1), (S.FIN_YMAX + 0.1, S.FIN_S1 + 0.1),
                         (S.FIN_YMIN - 0.1, S.FIN_S1 + 0.1)]), DARK)
    ys = np.linspace(S.CANOPY_Y0 + 0.05, S.CANOPY_Y1 - 0.03, 60)
    cv.fill(poly(top, [(yy, 0.0) for yy in (ys[0], ys[-1])] + [(yy, float(S.CANOPY_W(yy)) * 0.96) for yy in ys[::-1]]),
            (0.085, 0.09, 0.095), rough=0.75)
    # radome and the anti-glare panel ahead of the windscreen
    for mapfn, b0, b1 in ((top, 0.0, 0.6), (bot, 0.0, 0.6), (side, 0.0, 1.0)):
        cv.fill(rect(mapfn, S.Y_RADOME, S.Y_NOSE + 0.1, b0, b1), (0.56, 0.58, 0.60), 0.9)
    cv.fill(rect(top, S.CANOPY_Y1 - 0.05, S.CANOPY_Y1 + 0.55, 0.0, 0.32), (0.10, 0.10, 0.11), 0.9, rough=0.8)
    # the hot aft end around the nozzles and the boom tails
    for mapfn, b0, b1 in ((top, 0.0, 1.10), (bot, 0.0, 1.10), (side, -0.30, 0.65)):
        cv.fill(rect(mapfn, S.Y_NOZZLE - 0.2, -7.30, b0, b1), METAL, 0.85, rough=0.42, metal=0.9)


def paint_markings(cv, rng):
    star_and_bar(cv, top, -1.0, 4.4, 0.30, (0.30, 0.32, 0.34))
    star_and_bar(cv, bot, -1.0, 4.4, 0.30, (0.42, 0.44, 0.47))
    star_and_bar(cv, side, 1.0, 0.05, 0.24, (0.30, 0.32, 0.34))          # on the inlet sides
    for m in (fin_r, fin_l):
        text(cv, "ET", np.array(m(-7.30, 1.75), float), 0.62 * PX * S.FIN_ISLAND_SCALE, MARK, 0.9)
        text(cv, "AF", np.array(m(-7.80, 0.80), float), 0.20 * PX * S.FIN_ISLAND_SCALE, MARK, 0.9)
        text(cv, "20001", np.array(m(-6.80, 0.80), float), 0.20 * PX * S.FIN_ISLAND_SCALE, MARK, 0.9)
        s0, s1 = 2.70, 2.90                               # a white / black band near the top (test wing)
        cv.fill(poly(m, [(float(S.fin_le(s0)) - 0.02, s0), (float(S.fin_le(s1)) - 0.02, s1), (float(S.fin_te(s1)) + 0.02, s1),
                         (float(S.fin_te(s0)) + 0.02, s0)]), (0.85, 0.86, 0.87), 0.9)
        s0, s1 = 2.55, 2.70
        cv.fill(poly(m, [(float(S.fin_le(s0)) - 0.02, s0), (float(S.fin_le(s1)) - 0.02, s1), (float(S.fin_te(s1)) + 0.02, s1),
                         (float(S.fin_te(s0)) + 0.02, s0)]), (0.10, 0.10, 0.11), 0.9)
    for mapfn, (a0, a1, b0, b1), n in ((top, (-6.5, 7.0, 0.05, 0.55), 24), (top, (-3.0, 1.5, 1.8, 5.2), 20),
                                       (bot, (-6.5, 5.0, 0.05, 0.9), 20), (side, (-6.8, 6.0, -0.5, 0.25), 28)):
        for _ in range(n):
            y, b = rng.uniform(a0, a1), rng.uniform(b0, b1)
            for row in range(int(rng.integers(1, 4))):
                x = y
                for _w in range(int(rng.integers(2, 6))):
                    w = rng.uniform(0.02, 0.06)
                    cv.stroke(poly(mapfn, [(x, b - row * 0.022), (x + w, b - row * 0.022)]), 1.6, MARK, 0.5, butt=True)
                    x += w + 0.014


def paint_all(folder):
    os.makedirs(folder, exist_ok=True)
    cv = P.Canvas()
    rng = np.random.default_rng(15)
    draw_lines(cv)
    paint_base(cv, rng)
    paint_markings(cv, rng)
    P.finish(cv, rng)
    P.save(os.path.join(folder, "f15_basecolor.png"), cv.rgb)
    P.save(os.path.join(folder, "f15_normal.png"), P.normal_map(cv), colour=False)
    orm = np.stack([np.ones((N, N), np.float32), np.clip(cv.rough + 0.14 * cv.lines, 0.05, 1.0), cv.metal], axis=2)
    P.save(os.path.join(folder, "f15_orm.png"), orm, colour=False)
    print("painted f15")
