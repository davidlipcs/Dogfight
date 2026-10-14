"""Paints the textures of the Blender F/A-18E Super Hornet (numpy, runs inside Blender).

The same 4096 x 4096 atlas scheme as the F-16 (see f16_paint.py), but 20 m x 20 m (204.8 px per metre):

    v  0 .. 7 m    top view of the right half (the left half mirrors it), u = y - YA0
    v  7 .. 14 m   bottom view of the right half
    v 14 .. 20 m   side view, v = z + 16.5 (the left side mirrors it)
    two islands in the empty corner of the top view: the outer faces of the two fins

US Navy tactical paint scheme: FS 36320 dark ghost grey on top, FS 36375 light ghost grey below and on the
sides, low visibility markings: "NAVY", the national insignia, modex 200 and the NG tail code.
"""

import math
import os

import numpy as np

import f16_paint as P
import fa18_shape as S

N = P.N
PX = N / S.ATLAS
UPPER = (0.415, 0.445, 0.480)        # FS 36320
LOWER = (0.600, 0.630, 0.655)        # FS 36375
MARK = (0.27, 0.29, 0.31)
METAL = (0.30, 0.285, 0.27)

# extra stencil letters (4 x 6 grid, like f16_paint.GLYPHS)
GLYPHS = dict(P.GLYPHS)
GLYPHS.update({
    "N": [[(0.5, 0), (0.5, 6)], [(3.5, 0), (3.5, 6)], [(0.5, 6), (3.5, 0)]],
    "V": [[(0.3, 6), (2, 0.2), (3.7, 6)]],
    "Y": [[(0.3, 6), (2, 3.2), (3.7, 6)], [(2, 3.2), (2, 0)]],
    "G": [[(3.5, 4.6), (2.5, 5.5), (1.5, 5.5), (0.5, 4.5), (0.5, 1.5), (1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 2.8),
           (2.2, 2.8)]],
    "E": [[(4, 5.5), (0.5, 5.5), (0.5, 0.5), (4, 0.5)], [(0.5, 3), (3, 3)]],
    "S": [[(3.5, 4.6), (2.5, 5.5), (1.5, 5.5), (0.5, 4.6), (0.5, 3.9), (1.4, 3), (2.6, 3), (3.5, 2.1), (3.5, 1.4),
           (2.5, 0.5), (1.5, 0.5), (0.5, 1.4)]],
    "U": [[(0.5, 6), (0.5, 1.5), (1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 6)]],
    "R": [[(0.5, 0), (0.5, 5.5), (2.5, 5.5), (3.5, 4.5), (3.5, 3.8), (2.5, 2.9), (0.5, 2.9)], [(2.2, 2.9), (3.6, 0)]],
    "C": [[(3.5, 4.6), (2.5, 5.5), (1.5, 5.5), (0.5, 4.5), (0.5, 1.5), (1.5, 0.5), (2.5, 0.5), (3.5, 1.4)]],
})


def text(cv, string, centre, height, colour, alpha=1.0):
    old = P.GLYPHS
    P.GLYPHS = GLYPHS
    try:
        P.text(cv, string, centre, height, colour, alpha)
    finally:
        P.GLYPHS = old


# ---------------------------------------------------------------- mappings (atlas pixels, rows bottom up)
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


# ------------------------------------------------------------------ panel lines
def draw_lines(cv):
    def line(m, pts, width=1.5, strength=0.75):
        cv.groove(poly(m, pts), width, strength)

    def box(m, a0, a1, b0, b1, **kw):
        line(m, [(a0, b0), (a1, b0), (a1, b1), (a0, b1), (a0, b0)], **kw)

    xr, xt, te = S.X_ROOT, S.X_TIP, S.WING_TE
    lef = lambda x: float(S.wing_le(x) - S.lef_chord(x))      # noqa: E731
    flp = lambda x: te + float(S.flap_chord(x))                # noqa: E731
    ail = lambda x: te + float(S.ail_chord(x))                 # noqa: E731
    for m in (top, bot):
        line(m, [(lef(xr), xr), (lef(xt), xt)], 2.2, 1.0)
        line(m, [(flp(xr), xr), (flp(S.X_FLAP), S.X_FLAP), (te, S.X_FLAP)], 2.2, 1.0)
        line(m, [(ail(S.X_FLAP), S.X_FLAP), (ail(S.X_AIL), S.X_AIL), (te, S.X_AIL)], 2.2, 1.0)
        line(m, [(S.Y_KINK, xr), (te, xr)], 1.6, 0.6)
        line(m, [(float(S.wing_le(S.X_FLAP)), S.X_FLAP), (te, S.X_FLAP)], 1.8, 0.8)      # wing fold line
        for yr, yt_ in ((0.6, -1.25), (-0.6, -1.70), (-1.7, -2.25)):
            line(m, [(yr, xr), (yt_, xt)])
        for x in (2.45, 3.10, 3.60, 4.75, 5.40, 6.0):
            line(m, [(lef(x), x), (flp(x) if x < S.X_FLAP else (ail(x) if x < S.X_AIL else te), x)])
        for x in (3.1, 4.25, 5.4):
            line(m, [(float(S.wing_le(x)), x), (lef(x), x)], 1.3, 0.6)
        box(m, -0.80, -0.30, 2.62, 2.98, width=1.2, strength=0.55)
        box(m, -1.60, -1.20, 3.90, 4.20, width=1.2, strength=0.55)
        x0, x1 = S.STAB_X0, S.STAB_X1
        line(m, [(S.STAB_LE0 - 0.9, x0), (float(S.stab_le(x1)) - 0.35, x1)])
        line(m, [(S.STAB_LE0 - 1.8, x0), (float(S.stab_le(x1)) - 0.65, x1)])
        for x in (1.8, 2.5, 3.2):
            line(m, [(float(S.stab_le(x)), x), (float(S.stab_te(x)), x)], 1.3, 0.6)
    # ---- top of the fuselage and the LEX
    line(top, [(S.Y_RADOME, 0.0), (S.Y_RADOME, 0.50)], 2.4, 1.0)
    for y in (7.3, 6.8):
        line(top, [(y, 0.0), (y, 0.58)])
    for y in (5.2, 4.4, 3.6, 2.8, 2.0):
        line(top, [(y, 0.55), (y, float(S.LEX(y)) - 0.02)])
    line(top, [(1.5, 0.75), (6.0, 0.55)])
    box(top, 3.05, 3.95, 0.95, 1.45, width=2.0, strength=1.0)            # LEX spoiler
    for y in (2.6, 1.8, 0.9, 0.0, -0.9, -1.8, -2.7, -3.6, -4.5, -5.4, -6.3, -7.1):
        line(top, [(y, 0.0), (y, 0.95 if y > -3.0 else 1.05)])
    line(top, [(2.8, 0.22), (-7.4, 0.20)])
    line(top, [(1.0, 0.62), (-7.0, 0.70)])
    box(top, -3.40, -2.80, 0.30, 0.55, width=1.2, strength=0.55)
    box(top, -5.40, -4.60, 0.25, 0.55, width=1.2, strength=0.55)
    # ---- belly
    line(bot, [(S.Y_RADOME, 0.0), (S.Y_RADOME, 0.50)], 2.4, 1.0)
    for y in (7.0, 6.6, 4.6, 3.9, 3.0, 2.0, -1.5, -2.4, -3.3, -4.2, -5.1, -6.0, -6.9):
        line(bot, [(y, 0.0), (y, 1.0)])
    x0, x1, y0, y1 = S.NOSE_WELL
    box(bot, y0, y1, 0.0, x1, width=2.0, strength=1.0)
    x0, x1, y0, y1 = S.MAIN_WELL
    box(bot, y0, y1, x0, x1, width=2.0, strength=1.0)
    line(bot, [(-7.5, 0.25), (-1.5, 0.25)])
    # ---- sides
    zt, zb = (lambda y: float(S.BODY[0](y))), (lambda y: float(S.BODY[1](y)))
    line(side, [(S.Y_RADOME, zb(S.Y_RADOME) - 0.02), (S.Y_RADOME, zt(S.Y_RADOME) + 0.02)], 2.4, 1.0)
    for y in (7.3, 6.8, 6.3, 3.0, 2.2, 1.4, 0.6, -0.4, -1.4, -2.4, -3.4, -4.4, -5.4, -6.4, -7.2):
        line(side, [(y, zb(y)), (y, 0.30 if y < 6.5 else zt(y) - 0.1)])
    line(side, [(6.2, 0.20), (S.Y_RADOME, 0.22)])
    box(side, 6.85, 7.55, -0.10, 0.25, width=1.3, strength=0.6)
    box(side, 6.10, 6.65, -0.25, 0.10, width=1.3, strength=0.6)
    line(side, [(-7.4, -0.30), (2.8, -0.35)])
    box(side, -2.0, -1.0, -0.55, -0.35, width=1.3, strength=0.6)
    box(side, -5.6, -4.8, -0.45, -0.20, width=1.3, strength=0.6)
    # ---- fins (both islands) and the inner faces on the side strip
    for m in (fin_r, fin_l):
        hinge = lambda s: float(S.fin_te(s) + S.rudder_chord(s))      # noqa: E731
        line(m, [(hinge(S.RUD_S0), S.RUD_S0), (hinge(S.RUD_S1), S.RUD_S1)], 2.2, 1.0)
        for s in (S.RUD_S0, S.RUD_S1):
            line(m, [(hinge(s), s), (float(S.fin_te(s)), s)], 2.2, 1.0)
        for s in (0.6, 1.2, 1.9, 2.45):
            line(m, [(float(S.fin_le(s)), s), (float(S.fin_te(s)) if s > S.RUD_S1 else hinge(min(s, S.RUD_S1)), s)])
        for back in (0.25, 1.1):
            line(m, [(float(S.fin_le(0.0)) - back * 1.4, 0.0), (float(S.fin_le(2.6)) - back * 0.7, 2.6)])


def star_and_bar(cv, mapfn, y, x, r, colour, flip=False):
    """Low visibility national insignia; the star points forward."""
    c = np.array(mapfn(y, x), float)
    fwd = np.array(mapfn(y + 1.0, x), float) - c
    fwd /= np.hypot(*fwd)
    left = np.array([-fwd[1], fwd[0]])
    rp = r * PX
    dark = tuple(0.62 * v for v in colour)
    cv.fill([c + left * a * rp + fwd * b * rp for a, b in ((-2.1, -0.36), (2.1, -0.36), (2.1, 0.36), (-2.1, 0.36))], colour, 0.9)
    cv.disc(c, rp, colour, 0.9)
    star = []
    for k in range(10):
        a = k * math.pi / 5.0
        rr = rp * (0.92 if k % 2 == 0 else 0.36)
        star.append(c + fwd * math.cos(a) * rr + left * math.sin(a) * rr)
    cv.fill(star, dark, 1.0)


# ------------------------------------------------------------------ livery
def paint_base(cv, rng):
    cols = (np.arange(N, dtype=np.float32) + 0.5) / PX + S.YA0
    up, low = np.asarray(UPPER, np.float32), np.asarray(LOWER, np.float32)
    zc = S.BODY[5](cols).astype(np.float32)
    # top view: dark ghost grey all over
    cv.rgb[0:int(7 * PX)] = up
    cv.rgb[int(7 * PX):int(14 * PX)] = low
    # side view: dark above the LEX / wing line, light below, a soft countershading edge
    r0, r1 = int(14 * PX), N
    z = ((np.arange(r0, r1, dtype=np.float32) + 0.5) / PX - S.V_SIDE)[:, None]
    edge = zc[None, :] + 0.05 + 0.05 * np.sin(cols * 1.7)[None, :]
    below = S.smoothstep(0.06, -0.06, z - edge)[..., None]
    cv.rgb[r0:r1] = up * (1.0 - below) + low * below
    # fin islands: the dark grey
    for m in (fin_r, fin_l):
        cv.fill(poly(m, [(S.FIN_YMIN - 0.1, S.FIN_S0 - 0.1), (S.FIN_YMAX + 0.1, S.FIN_S0 - 0.1), (S.FIN_YMAX + 0.1, S.FIN_S1 + 0.1),
                         (S.FIN_YMIN - 0.1, S.FIN_S1 + 0.1)]), UPPER)
    # the skin under the canopy, the hot aft end around the nozzles
    ys = np.linspace(S.CANOPY_Y0 + 0.05, S.CANOPY_Y1 - 0.03, 60)
    cv.fill(poly(top, [(yy, 0.0) for yy in (ys[0], ys[-1])] + [(yy, float(S.CANOPY_W(yy)) * 0.96) for yy in ys[::-1]]),
            (0.085, 0.09, 0.095), rough=0.75)
    for mapfn, b0, b1 in ((top, 0.0, 1.10), (bot, 0.0, 1.10), (side, -0.75, 0.45)):
        c0 = int((-7.25 - S.YA0) * PX)
        rr0, rr1 = int(mapfn(0.0, b0)[1]), int(mapfn(0.0, b1)[1])
        ramp = S.smoothstep(c0 + 8, c0 - 8, np.arange(0, c0 + 10, dtype=np.float32))[None, :]
        win = (slice(rr0, rr1), slice(0, c0 + 10))
        cv._blend(win, np.broadcast_to(ramp, (rr1 - rr0, c0 + 10)).astype(np.float32), METAL, 1.0, rough=0.42, metal=1.0)


def paint_markings(cv, rng):
    star_and_bar(cv, top, -0.9, 4.6, 0.30, (0.30, 0.32, 0.35))
    star_and_bar(cv, bot, -0.9, 4.6, 0.30, (0.45, 0.48, 0.50))
    star_and_bar(cv, side, 0.9, -0.38, 0.22, (0.42, 0.45, 0.48))         # on the inlet trunks
    # NAVY under the tails, modex on the nose and the flaps, tail code and squadron band on the fins
    text(cv, "NAVY", np.array(side(-4.0, -0.30), float), 0.34 * PX, MARK)
    text(cv, "200", np.array(side(6.9, 0.10), float), 0.30 * PX, MARK)
    for m in (fin_r, fin_l):
        text(cv, "NG", np.array(m(-4.20, 1.35), float), 0.60 * PX * S.FIN_ISLAND_SCALE, MARK)
        text(cv, "200", np.array(m(-4.75, 0.55), float), 0.26 * PX * S.FIN_ISLAND_SCALE, MARK)
        s0, s1 = 2.25, 2.42
        cv.fill(poly(m, [(float(S.fin_le(s0)) + 0.02, s0), (float(S.fin_le(s1)) + 0.02, s1), (float(S.fin_te(s1)) - 0.02, s1),
                         (float(S.fin_te(s0)) - 0.02, s0)]), (0.10, 0.10, 0.11))
        cv.fill(poly(m, [(float(S.fin_le(s1)) + 0.02, s1), (float(S.fin_le(2.52)) + 0.02, 2.52), (float(S.fin_te(2.52)) - 0.02, 2.52),
                         (float(S.fin_te(s1)) - 0.02, s1)]), (0.80, 0.66, 0.12))
    # radome: a slightly different grey and the lightning diverter strips
    for mapfn, b0, b1 in ((top, 0.0, 0.6), (bot, 0.0, 0.6), (side, -0.4, 0.9)):
        cv.fill(rect(mapfn, S.Y_RADOME, S.Y_NOSE + 0.1, b0, b1), (0.47, 0.49, 0.51), 0.85)
    ys = np.linspace(S.Y_RADOME + 0.05, 9.3, 14)
    zt, zb, hw, zc = (S.BODY[k](ys) for k in (0, 1, 2, 5))
    strip = (0.58, 0.58, 0.56)
    for mapfn, pts in ((top, np.stack([ys, hw * 0.5], axis=1)), (bot, np.stack([ys, hw * 0.5], axis=1)),
                       (side, np.stack([ys, zc], axis=1)), (side, np.stack([ys, zc + (zt - zc) * 0.6], axis=1))):
        cv.stroke(poly(mapfn, pts), 2.0, strip, 0.7)
    # walkway outlines on the LEX, the canopy release and rescue arrows, small stencils
    for y0, y1, x0, x1 in ((2.3, 3.0, 0.75, 1.25),):
        cv.stroke(poly(top, [(y0, x0), (y1, x0), (y1, x1), (y0, x1), (y0, x0)]), 2.0, (0.30, 0.32, 0.34), 0.8)
    cv.fill(poly(side, [(5.55, 0.48), (5.95, 0.48), (5.95, 0.44), (6.05, 0.515), (5.95, 0.59), (5.95, 0.55), (5.55, 0.55)]),
            (0.70, 0.58, 0.10), 0.85)
    for mapfn, (a0, a1, b0, b1), n in ((top, (-6.5, 7.0, 0.05, 0.45), 26), (top, (-2.4, 1.0, 2.2, 5.6), 22),
                                       (bot, (-6.5, 5.0, 0.05, 0.6), 22), (side, (-6.8, 6.0, -0.65, -0.05), 30)):
        for _ in range(n):
            y, b = rng.uniform(a0, a1), rng.uniform(b0, b1)
            for row in range(int(rng.integers(1, 4))):
                x = y
                for _w in range(int(rng.integers(2, 6))):
                    w = rng.uniform(0.02, 0.06)
                    cv.stroke(poly(mapfn, [(x, b - row * 0.022), (x + w, b - row * 0.022)]), 1.6, MARK, 0.55, butt=True)
                    x += w + 0.014


def copy_decals(cv):
    """Left side islands: a mirrored copy of the side strip under each box (colour, lines, roughness)."""
    for y0, y1, z0, z1, u0, v0 in S.DECALS:
        c0, r0 = (int(round(v)) for v in side(y0, z0))
        c1, r1 = (int(round(v)) for v in side(y1, z1))
        d0, e0 = int(round(u0 * PX)), int(round(v0 * PX))
        for layer in (cv.rgb, cv.lines, cv.rough, cv.metal):
            block = layer[r0:r1, c0:c1][:, ::-1]
            layer[e0:e0 + (r1 - r0), d0:d0 + (c1 - c0)] = block


def decal(y0, z0):
    """Pixel position of a left side point (y, z) in its island."""
    for b in S.DECALS:
        if b[0] <= y0 <= b[1] and b[2] <= z0 <= b[3]:
            return np.array([(b[4] + (b[1] - y0)) * PX, (b[5] + (z0 - b[2])) * PX])
    raise ValueError("no decal box at %s" % ((y0, z0),))


def paint_all(folder):
    os.makedirs(folder, exist_ok=True)
    cv = P.Canvas()
    rng = np.random.default_rng(18)
    draw_lines(cv)
    paint_base(cv, rng)
    copy_decals(cv)
    paint_markings(cv, rng)
    text(cv, "NAVY", decal(-4.0, -0.30), 0.34 * PX, MARK)
    text(cv, "200", decal(6.9, 0.10), 0.30 * PX, MARK)
    P.finish(cv, rng)
    P.save(os.path.join(folder, "fa18_basecolor.png"), cv.rgb)
    P.save(os.path.join(folder, "fa18_normal.png"), P.normal_map(cv), colour=False)
    orm = np.stack([np.ones((N, N), np.float32), np.clip(cv.rough + 0.14 * cv.lines, 0.05, 1.0), cv.metal], axis=2)
    P.save(os.path.join(folder, "fa18_orm.png"), orm, colour=False)
    print("painted fa18")
