"""Paints the textures of the Blender F-16 with numpy (runs inside Blender, no other packages).

One 4096 x 4096 atlas of 16 m x 16 m (256 px per metre), in strips of planar views:

    rows    0 .. 5 m   top view of the right half (the left half mirrors it), u = y, v = |x|
    rows    5 .. 10 m  bottom view of the right half
    rows   10 .. 15.5  side view, v = z + 2 (the left side mirrors it)
    island in the empty corner of the top view: the left side of the fin, so that the tail code
    reads correctly on both sides

Outputs: base colour (two liveries), tangent space normal map (panel lines) and an ORM map
(G = roughness, B = metallic).
"""

import math
import os

import numpy as np

import f16_shape as S

N = 4096
PX = N / 16.0
YA0 = -6.4
ROWS_TOP, ROWS_BOT, ROWS_SIDE = (0, 1280), (1280, 2560), (2560, 3968)

GREY_DARK = (0.375, 0.395, 0.415)      # FS 36118
GREY_MID = (0.500, 0.525, 0.540)       # FS 36270
GREY_LIGHT = (0.625, 0.650, 0.670)     # FS 36375
RADOME = (0.455, 0.465, 0.470)
METAL = (0.30, 0.285, 0.27)

LIVERIES = {
    "viper": dict(upper=GREY_MID, dark=GREY_DARK, lower=GREY_LIGHT, fin=GREY_MID, radome=RADOME, code="HL",
                  serial=("AF", "88", "490"), band=(0.74, 0.60, 0.10), mark=(0.20, 0.21, 0.23), star=(0.60, 0.62, 0.64)),
    "aggressor": dict(upper=(0.70, 0.58, 0.40), dark=(0.47, 0.33, 0.21), lower=(0.60, 0.66, 0.72), fin=(0.70, 0.58, 0.40),
                      radome=(0.36, 0.33, 0.29), code="WA", serial=("AF", "86", "291"), band=(0.62, 0.10, 0.08),
                      mark=(0.16, 0.13, 0.11), star=(0.62, 0.12, 0.10), camo=((0.47, 0.33, 0.21), (0.82, 0.74, 0.56))),
}


# ---------------------------------------------------------------- mappings
def top(y, x):
    return (np.asarray(y, float) - YA0) * PX, np.asarray(x, float) * PX


def bot(y, x):
    return (np.asarray(y, float) - YA0) * PX, (5.0 + np.asarray(x, float)) * PX


def side(y, z):
    return (np.asarray(y, float) - YA0) * PX, (12.0 + np.asarray(z, float)) * PX


def finl(y, z):
    return ((S.FINL_U0 + (S.FINL_Y1 - np.asarray(y, float)) * S.FINL_SCALE) * PX,
            (S.FINL_V0 + (np.asarray(z, float) - S.FINL_Z0) * S.FINL_SCALE) * PX)


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self):
        self.rgb = np.zeros((N, N, 3), np.float32)
        self.lines = np.zeros((N, N), np.float32)       # panel line coverage (also the groove depth)
        self.rough = np.full((N, N), 0.56, np.float32)
        self.metal = np.zeros((N, N), np.float32)

    @staticmethod
    def _window(c0, r0, c1, r1, pad=3):
        c0, r0 = max(int(math.floor(c0)) - pad, 0), max(int(math.floor(r0)) - pad, 0)
        c1, r1 = min(int(math.ceil(c1)) + pad, N), min(int(math.ceil(r1)) + pad, N)
        if c1 <= c0 or r1 <= r0:
            return None
        cc, rr = np.meshgrid(np.arange(c0, c1, dtype=np.float32) + 0.5, np.arange(r0, r1, dtype=np.float32) + 0.5)
        return (slice(r0, r1), slice(c0, c1)), cc, rr

    def _segments(self, pts, step=220.0):
        """Split a pixel polyline into short pieces (small windows keep the rasteriser fast)."""
        pts = [np.asarray(p, float) for p in pts]
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.ceil(np.hypot(*(b - a)) / step)))
            for k in range(n):
                yield a + (b - a) * k / n, a + (b - a) * (k + 1) / n

    @staticmethod
    def _seg_cover(cc, rr, a, b, half, butt=False):
        d = b - a
        length = max(float(np.hypot(*d)), 1e-6)
        ux, uy = d / length
        t = (cc - a[0]) * ux + (rr - a[1]) * uy
        s = (rr - a[1]) * ux - (cc - a[0]) * uy
        if butt:
            dist = np.maximum(np.abs(s) - half, np.abs(t - 0.5 * length) - 0.5 * length)
        else:
            dist = np.hypot(s, t - np.clip(t, 0.0, length)) - half
        return np.clip(0.5 - dist, 0.0, 1.0)

    def groove(self, pts, width=1.5, strength=1.0):
        """A panel line: collected in the line layer, applied to colour / normal / roughness at the end."""
        for a, b in self._segments(pts):
            w = self._window(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), 3 + int(width))
            if w is None:
                continue
            m = self._seg_cover(w[1], w[2], a, b, 0.5 * width) * strength
            self.lines[w[0]] = np.maximum(self.lines[w[0]], m)

    def _blend(self, win, cover, colour, alpha=1.0, rough=None, metal=None):
        m = (cover * alpha)[..., None]
        if colour is not None:
            self.rgb[win] = self.rgb[win] * (1.0 - m) + np.asarray(colour, np.float32) * m
        if rough is not None:
            self.rough[win] = self.rough[win] * (1.0 - m[..., 0]) + rough * m[..., 0]
        if metal is not None:
            self.metal[win] = self.metal[win] * (1.0 - m[..., 0]) + metal * m[..., 0]

    def stroke(self, pts, width, colour, alpha=1.0, butt=False):
        for a, b in self._segments(pts):
            w = self._window(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), 3 + int(width))
            if w is not None:
                self._blend(w[0], self._seg_cover(w[1], w[2], a, b, 0.5 * width, butt), colour, alpha)

    def disc(self, c, radius, colour, alpha=1.0, **kw):
        w = self._window(c[0] - radius, c[1] - radius, c[0] + radius, c[1] + radius)
        if w is not None:
            self._blend(w[0], np.clip(0.5 + radius - np.hypot(w[1] - c[0], w[2] - c[1]), 0.0, 1.0), colour, alpha, **kw)

    def fill(self, contours, colour, alpha=1.0, **kw):
        """Even-odd fill of one or more closed contours (pixel coordinates), 3 x 3 supersampled."""
        if isinstance(contours[0][0], (int, float, np.floating)):
            contours = [contours]
        contours = [np.asarray(c, float) for c in contours]
        allp = np.concatenate(contours)
        w = self._window(allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max(), 1)
        if w is None:
            return
        cover = np.zeros(w[1].shape, np.float32)
        for dx in (-1.0 / 3.0, 0.0, 1.0 / 3.0):
            for dy in (-1.0 / 3.0, 0.0, 1.0 / 3.0):
                inside = np.zeros(w[1].shape, bool)
                x, y = w[1] + dx, w[2] + dy
                for c in contours:
                    for (x1, y1), (x2, y2) in zip(c, np.roll(c, -1, axis=0)):
                        if y1 == y2:
                            continue
                        inside ^= ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
                cover += inside
        self._blend(w[0], cover / 9.0, colour, alpha, **kw)


# ------------------------------------------------------------ stencil font
#  block letters on a 4 x 6 grid, stroke one unit wide (the look of military stencils)
GLYPHS = {
    "H": [[(0.5, 0), (0.5, 6)], [(3.5, 0), (3.5, 6)], [(0.5, 3), (3.5, 3)]],
    "L": [[(0.5, 6), (0.5, 0.5), (4, 0.5)]],
    "A": [[(0.5, 0), (0.5, 4.5), (1.5, 5.5), (2.5, 5.5), (3.5, 4.5), (3.5, 0)], [(0.5, 2.4), (3.5, 2.4)]],
    "F": [[(4, 5.5), (0.5, 5.5), (0.5, 0)], [(0.5, 3), (3, 3)]],
    "W": [[(0.4, 6), (0.4, 1.4), (1.2, 0.5), (2, 1.6), (2.8, 0.5), (3.6, 1.4), (3.6, 6)], [(2, 1.6), (2, 3.6)]],
    "0": [[(1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 4.5), (2.5, 5.5), (1.5, 5.5), (0.5, 4.5), (0.5, 1.5), (1.5, 0.5)]],
    "1": [[(2, 0), (2, 6)], [(0.9, 4.4), (2, 5.5)]],
    "2": [[(0.5, 4.5), (1.5, 5.5), (2.5, 5.5), (3.5, 4.5), (3.5, 3.6), (0.5, 1.3), (0.5, 0.5), (4, 0.5)]],
    "4": [[(3, 0), (3, 6)], [(3, 5.5), (0.5, 2.1), (4, 2.1)]],
    "6": [[(3.5, 4.6), (2.5, 5.5), (1.5, 5.5), (0.5, 4.5), (0.5, 1.5), (1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 2.4),
           (2.5, 3.3), (0.5, 3.3)]],
    "8": [[(1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 2.2), (2.7, 3), (3.5, 3.8), (3.5, 4.5), (2.5, 5.5), (1.5, 5.5),
           (0.5, 4.5), (0.5, 3.8), (1.3, 3), (0.5, 2.2), (0.5, 1.5), (1.5, 0.5)], [(1.3, 3), (2.7, 3)]],
    "9": [[(0.5, 1.4), (1.5, 0.5), (2.5, 0.5), (3.5, 1.5), (3.5, 4.5), (2.5, 5.5), (1.5, 5.5), (0.5, 4.5), (0.5, 3.6),
           (1.5, 2.7), (3.5, 2.7)]],
}


def text(cv, string, centre, height, colour, alpha=1.0):
    """Stencil text centred on a pixel position, ``height`` in pixels."""
    unit = height / 6.0
    advance = 5.0 * unit
    x0 = centre[0] - 0.5 * (advance * len(string) - unit)
    y0 = centre[1] - 0.5 * height
    for i, ch in enumerate(string):
        for line in GLYPHS.get(ch, []):
            pts = [(x0 + i * advance + gx * unit, y0 + gy * unit) for gx, gy in line]
            for a, b in zip(pts, pts[1:]):
                cv.stroke([a, b], unit, colour, alpha, butt=True)
            for p in pts[1:-1]:
                cv.disc(p, 0.5 * unit, colour, alpha)
            if pts[0] == pts[-1]:
                cv.disc(pts[0], 0.5 * unit, colour, alpha)


# ----------------------------------------------------------------- helpers
def value_noise(rng, cells_r, cells_c):
    g = rng.random((cells_r + 2, cells_c + 2)).astype(np.float32) * 2.0 - 1.0

    def axis(cells):
        t = np.linspace(0.0, cells, N, endpoint=False, dtype=np.float32)
        i = t.astype(np.int32)
        f = t - i
        return i, f * f * (3.0 - 2.0 * f)
    ri, rf = axis(cells_r)
    ci, cf = axis(cells_c)
    rows = g[ri] * (1.0 - rf[:, None]) + g[ri + 1] * rf[:, None]
    return rows[:, ci] * (1.0 - cf[None, :]) + rows[:, ci + 1] * cf[None, :]


def box_blur(a, radius):
    for ax in (0, 1):
        c = np.cumsum(a, axis=ax, dtype=np.float64)
        pad = [(0, 0), (0, 0)]
        pad[ax] = (radius + 1, radius)
        c = np.pad(c, pad, mode="edge")
        n = a.shape[ax]
        hi = np.take(c, np.arange(n) + 2 * radius + 1, axis=ax)
        lo = np.take(c, np.arange(n), axis=ax)
        a = ((hi - lo) / (2 * radius + 1)).astype(np.float32)
    return a


def poly(mapfn, pts):
    a, b = np.array(pts, float).T
    return np.stack(mapfn(a, b), axis=1)


def rect(mapfn, a0, a1, b0, b1):
    return poly(mapfn, [(a0, b0), (a1, b0), (a1, b1), (a0, b1)])


# -------------------------------------------------------------- panel lines
def draw_lines(cv):
    def line(mapfn, pts, width=1.5, strength=0.75):
        cv.groove(poly(mapfn, pts), width, strength)

    def box(mapfn, a0, a1, b0, b1, **kw):
        line(mapfn, [(a0, b0), (a1, b0), (a1, b1), (a0, b1), (a0, b0)], **kw)

    xr, xt, xf, te = S.X_ROOT, S.X_TIP, S.X_FLAP, S.WING_TE
    lef = lambda x: float(S.wing_le(x) - S.lef_chord(x))      # noqa: E731
    flp = lambda x: te + float(S.flap_chord(x))                # noqa: E731
    for m in (top, bot):
        # wing: control surface gaps, root seam, spars and ribs
        line(m, [(lef(xr), xr), (lef(xt), xt)], 2.2, 1.0)
        line(m, [(flp(xr), xr), (flp(xf), xf), (te, xf)], 2.2, 1.0)
        line(m, [(S.Y_KINK, xr), (te, xr)], 1.6, 0.6)
        for yr, yt_ in ((0.62, -1.40), (-0.20, -1.62), (-0.95, -1.90)):
            line(m, [(yr, xr), (yt_, xt)])
        for x in (1.85, 2.40, 3.05, 3.62, 3.96, 4.30):
            line(m, [(lef(x), x), (flp(x) if x < xf else te, x)])
        for x in (2.10, 2.90, 3.70):
            line(m, [(float(S.wing_le(x)), x), (lef(x), x)], 1.3, 0.6)
        line(m, [(flp(2.26), 2.26), (te, 2.26)], 1.3, 0.6)
        box(m, -0.62, -0.22, 1.58, 1.92, width=1.2, strength=0.55)
        box(m, -1.32, -0.98, 2.58, 2.88, width=1.2, strength=0.55)
        # stabilator and speed brake
        x0, x1 = S.STAB_X0, S.STAB_X1
        line(m, [(S.STAB_LE0 - 0.95, x0), (float(S.stab_le(x1)) - 0.38, x1)])
        line(m, [(S.STAB_LE0 - 1.75, x0), (float(S.stab_le(x1)) - 0.66, x1)])
        for x in (1.62, 2.20, 2.66):
            line(m, [(float(S.stab_le(x)), x), (float(S.stab_te(x)), x)], 1.3, 0.6)
        line(m, [(S.Y_SB0, 0.86), (S.Y_SB1, 0.86)], 1.3, 0.6)
        # shelf
        for y in (-2.80, -3.40, -4.00):
            line(m, [(y, 0.55), (y, S.X_SHELF)])
    # ---- top of the fuselage
    line(top, [(S.Y_RADOME, 0.0), (S.Y_RADOME, 0.42)], 2.4, 1.0)
    for y in (6.52, 6.08):
        line(top, [(y, 0.0), (y, 0.50)])
    line(top, [(5.92, 0.19), (S.Y_RADOME, 0.17)])
    box(top, 6.14, 6.46, 0.03, 0.15, width=1.2, strength=0.55)
    for y in (2.12, 2.72, 3.32, 3.92, 4.52, 5.10):
        line(top, [(y, 0.50), (y, float(S.STRAKE(y)) - 0.015)])
    line(top, [(1.30, 0.66), (4.90, 0.50)])
    for y in (2.05, 1.45, 0.20, -0.55, -1.35, -2.15, -2.95, -3.75, -4.50):
        line(top, [(y, 0.0), (y, 0.72 if y > -3.0 else 0.56)])
    line(top, [(2.05, 0.21), (-4.75, 0.19)])
    line(top, [(1.45, 0.50), (-4.50, 0.42)])
    line(top, [(S.Y_KINK, 1.02), (te, 1.02)], 1.3, 0.55)
    box(top, 0.42, 1.05, 0.0, 0.105, width=1.8, strength=0.9)          # air refuelling receptacle
    box(top, -1.20, -0.70, 0.26, 0.44, width=1.2, strength=0.55)
    box(top, -2.60, -2.20, 0.24, 0.40, width=1.2, strength=0.55)
    # ---- belly
    line(bot, [(S.Y_RADOME, 0.0), (S.Y_RADOME, 0.42)], 2.4, 1.0)
    for y in (6.52, 6.08, 5.50, 4.95):
        line(bot, [(y, 0.0), (y, 0.52)])
    for y in (4.10, 3.02, 2.20, 1.50, 0.60, -1.00, -1.80, -2.60, -3.40, -4.20):
        line(bot, [(y, 0.0), (y, 0.80 if y > -3.0 else 0.62)])
    line(bot, [(4.30, 0.30), (-4.60, 0.30)])
    line(bot, [(1.50, 0.62), (-4.20, 0.52)])
    x0, x1, y0, y1 = S.NOSE_WELL                                        # gear doors (the wells are cut out)
    box(bot, y0, y1, 0.0, x1, width=2.0, strength=1.0)
    x0, x1, y0, y1 = S.MAIN_WELL
    box(bot, y0, y1, x0, x1, width=2.0, strength=1.0)
    line(bot, [(0.5 * (y0 + y1), x0 + 0.05), (0.5 * (y0 + y1), x1 - 0.05)], 1.3, 0.5)
    box(bot, -3.95, -1.95, 0.0, 0.50, width=1.6, strength=0.8)          # engine access doors
    line(bot, [(-2.95, 0.0), (-2.95, 0.50)])
    for x in (3.05, 3.96):
        box(bot, -1.95, -0.20 if x < 3.5 else -0.70, x - 0.05, x + 0.05, width=1.2, strength=0.5)
    # ---- sides
    zt, zb = (lambda y: float(S.BODY[0](y))), (lambda y: float(S.BODY[1](y)))
    line(side, [(S.Y_RADOME, zb(S.Y_RADOME) - 0.02), (S.Y_RADOME, zt(S.Y_RADOME) + 0.02)], 2.4, 1.0)
    for y in (6.52, 6.08, 5.60, 5.10, 4.60):
        line(side, [(y, zb(y) - 0.02), (y, zt(y) - 0.08)])
    line(side, [(5.20, 0.16), (S.Y_RADOME, 0.165)])
    line(side, [(4.60, -0.06), (S.Y_RADOME, -0.10)])
    box(side, 6.14, 6.84, -0.07, 0.13, width=1.3, strength=0.6)
    box(side, 5.66, 6.02, 0.20, 0.44, width=1.3, strength=0.6)
    box(side, 5.20, 5.54, -0.05, 0.13, width=1.3, strength=0.6)
    for y in (3.90, 3.20, 2.50):
        line(side, [(y, float(S.INTAKE[2](y))), (y, -0.22)])
    line(side, [(1.20, -0.55), (4.30, -0.56)])
    for y in (1.50, 0.60, -0.30, -1.20, -2.10, -3.00, -3.90, -4.60):
        line(side, [(y, zb(y)), (y, -0.12)])
    line(side, [(1.50, -0.46), (-4.80, -0.42)])
    for y in (2.05, 1.45, 0.20, -0.55, -1.35, -2.15, -2.95, -3.75, -4.50):
        line(side, [(y, 0.12), (y, zt(y))])
    box(side, 0.10, 0.85, -0.70, -0.52, width=1.3, strength=0.6)
    box(side, -3.70, -3.10, -0.60, -0.42, width=1.3, strength=0.6)
    # ---- fin (both sides)
    for m in (side, finl):
        hinge = lambda z: float(S.fin_te(z) + S.rudder_chord(z))      # noqa: E731
        line(m, [(hinge(S.RUD_Z0), S.RUD_Z0), (hinge(S.RUD_Z1), S.RUD_Z1)], 2.2, 1.0)
        for z in (S.RUD_Z0, S.RUD_Z1):
            line(m, [(hinge(z), z), (float(S.fin_te(z)), z)], 2.2, 1.0)
        for z in (1.02, 1.62, 2.30, 2.98):
            line(m, [(float(S.fin_le(z)), z), (hinge(min(max(z, S.RUD_Z0), S.RUD_Z1)), z)])
        line(m, [(float(S.fin_le(3.17)), 3.17), (float(S.fin_te(3.17)), 3.17)], 1.8, 0.9)
        for back in (0.16, 0.62):
            line(m, [(float(S.fin_le(0.80)) - back * 1.6, 0.80), (float(S.fin_le(3.20)) - back * 0.75, 3.20)])
        for z in (1.70, 2.40):
            line(m, [(hinge(z), z), (float(S.fin_te(z)), z)], 1.3, 0.6)


# ------------------------------------------------------------------ livery
def star_and_bar(cv, mapfn, y, x, r, colour):
    """Low visibility national insignia, the star points forward."""
    c = np.array(mapfn(y, x), float)
    fwd = np.array(mapfn(y + 1.0, x), float) - c
    fwd /= np.hypot(*fwd)
    left = np.array([-fwd[1], fwd[0]])
    rp = r * PX
    cv.fill([c + left * a * rp + fwd * b * rp for a, b in ((-2.1, -0.36), (2.1, -0.36), (2.1, 0.36), (-2.1, 0.36))], colour, 0.9)
    cv.disc(c, rp, colour, 0.9)
    dark = tuple(0.55 * v for v in colour)
    star = []
    for k in range(10):
        a = k * math.pi / 5.0
        rr = rp * (0.92 if k % 2 == 0 else 0.36)
        star.append(c + fwd * math.cos(a) * rr + left * math.sin(a) * rr)
    cv.fill(star, dark, 1.0)
    for sgn in (-1.0, 1.0):
        cv.fill([c + left * sgn * a * rp + fwd * b * rp for a, b in ((1.15, -0.10), (2.0, -0.10), (2.0, 0.10), (1.15, 0.10))],
                dark, 1.0)


def paint_base(cv, L, rng):
    cols = (np.arange(N, dtype=np.float32) + 0.5) / PX + YA0                 # y of every column
    up, dark, low = (np.asarray(L[k], np.float32) for k in ("upper", "dark", "lower"))
    radome = np.asarray(L["radome"], np.float32)
    is_radome = S.smoothstep(S.Y_RADOME - 0.006, S.Y_RADOME + 0.006, cols)[None, :, None]
    hw = S.BODY[2](cols).astype(np.float32)
    zc = S.BODY[5](cols).astype(np.float32)
    ztop = S.BODY[0](cols).astype(np.float32)

    # ---- top view: medium grey nose, dark grey from the canopy back (wings included)
    r0, r1 = ROWS_TOP
    x = ((np.arange(r0, r1, dtype=np.float32) + 0.5) / PX)[:, None]
    y = cols[None, :]
    aft = S.smoothstep(0.035, -0.035, y - (3.05 - 0.45 * x) + 0.03 * np.sin(x * 9.0))[..., None]
    img = up * (1.0 - aft) + dark * aft
    cv.rgb[r0:r1] = img * (1.0 - is_radome) + radome * is_radome
    # ---- bottom view
    r0, r1 = ROWS_BOT
    cv.rgb[r0:r1] = low * (1.0 - is_radome) + radome * is_radome
    # ---- side view: upper colours above the wing plane, light grey below, the fin in the nose colour
    r0, r1 = ROWS_SIDE
    z = ((np.arange(r0, r1, dtype=np.float32) + 0.5) / PX - 12.0)[:, None]
    aft = S.smoothstep(0.035, -0.035, y - 2.74 + 0.0 * z)[..., None]
    img = up * (1.0 - aft) + dark * aft
    below = S.smoothstep(0.03, -0.03, z - (zc[None, :] - 0.035))[..., None]
    img = img * (1.0 - below) + low * below
    fin = (S.smoothstep(0.10, 0.16, z - ztop[None, :]) * (y < -0.20))[..., None]
    img = img * (1.0 - fin) + np.asarray(L["fin"], np.float32) * fin
    cv.rgb[r0:r1] = img * (1.0 - is_radome) + radome * is_radome
    if "camo" in L:
        for mapfn, (a0, a1, b0, b1), n in ((top, (-6.2, 6.8, 0.0, 5.0), 60), (side, (-6.2, 6.8, -0.05, 1.0), 22)):
            for _ in range(n):
                cy, cx = rng.uniform(a0, a1), rng.uniform(b0, b1)
                size = rng.uniform(0.5, 1.5)
                pts = []
                for j in range(6):
                    a = j * math.pi / 3.0 + rng.uniform(-0.4, 0.4)
                    rr = size * rng.uniform(0.5, 1.0)
                    pts.append((min(cy + math.cos(a) * rr * 1.5, S.Y_RADOME - 0.02), min(max(cx + math.sin(a) * rr, b0), b1)))
                cv.fill(poly(mapfn, pts), L["camo"][int(rng.integers(len(L["camo"])))])
    # ---- the skin under the canopy
    ys = np.linspace(S.CANOPY_Y0 + 0.05, S.CANOPY_Y1 - 0.03, 60)
    cv.fill(poly(top, [(yy, 0.0) for yy in (ys[0], ys[-1])] + [(yy, float(S.CANOPY_W(yy)) * 0.96) for yy in ys[::-1]]),
            (0.085, 0.09, 0.095), rough=0.75)
    # ---- bare metal around the engine exhaust
    for mapfn, b0, b1 in ((top, 0.0, 0.55), (bot, 0.0, 0.55), (side, -0.78, 0.50)):
        c0 = int((-4.86 - YA0) * PX)
        rr0, rr1 = int(mapfn(0.0, b0)[1]), int(mapfn(0.0, b1)[1])
        ramp = S.smoothstep(c0 + 6, c0 - 6, np.arange(0, c0 + 8, dtype=np.float32))[None, :]
        win = (slice(rr0, rr1), slice(0, c0 + 8))
        cv._blend(win, np.broadcast_to(ramp, (rr1 - rr0, c0 + 8)).astype(np.float32), METAL, 1.0, rough=0.42, metal=1.0)
    # ---- the fin island (left side)
    cv.fill(rect(finl, -5.60, -0.20, S.FINL_Z0, 3.40), L["fin"])
    cv.fill(rect(finl, -5.60, -0.20, S.FINL_Z0, 0.74), L["dark"])


def paint_markings(cv, L, rng):
    mark = L["mark"]
    star_and_bar(cv, top, -1.08, 3.28, 0.27, L["star"])
    star_and_bar(cv, bot, -1.08, 3.28, 0.27, tuple(0.72 * v for v in L["lower"]) if "camo" not in L else L["star"])
    # radome: lightning diverter strips
    strip = tuple(min(1.0, v + 0.14) for v in L["radome"])
    ys = np.linspace(S.Y_RADOME + 0.05, 8.22, 14)
    zt, zb, hw, zc = (S.BODY[k](ys) for k in (0, 1, 2, 5))
    for mapfn, pts in ((top, np.stack([ys, hw * 0.50], axis=1)), (bot, np.stack([ys, hw * 0.50], axis=1)),
                       (top, np.stack([ys, hw * 0.0 + 0.004], axis=1)), (side, np.stack([ys, zc], axis=1)),
                       (side, np.stack([ys, zc + (zt - zc) * 0.62], axis=1)), (side, np.stack([ys, zc - (zc - zb) * 0.62], axis=1))):
        cv.stroke(poly(mapfn, pts), 2.0, strip, 0.8)
    # air refuelling receptacle guide marks
    for dx in (0.16, 0.24):
        cv.stroke(poly(top, [(1.30, dx), (0.42, dx - 0.05)]), 2.0, tuple(min(1.0, v + 0.2) for v in L["dark"]), 0.7)
    # tail: unit band, tail code and serial number
    for mapfn in (side, finl):
        za, zb_ = 2.99, 3.14
        cv.fill(poly(mapfn, [(float(S.fin_le(za)) + 0.02, za), (float(S.fin_le(zb_)) + 0.02, zb_), (float(S.fin_te(zb_)) - 0.02, zb_),
                             (float(S.fin_te(za)) - 0.02, za)]), L["band"])
        for z in (za, zb_):
            cv.stroke(poly(mapfn, [(float(S.fin_le(z)), z), (float(S.fin_te(z)), z)]), 2.0, (0.05, 0.05, 0.05))
        k = S.FINL_SCALE if mapfn is finl else 1.0
        text(cv, L["code"], np.array(mapfn(-3.80, 2.18), float), 0.44 * PX * k, mark)
        aa, bb, cc = L["serial"]
        sgn = -1.0 if mapfn is finl else 1.0
        base = np.array(mapfn(-3.17, 1.47), float)
        text(cv, cc, base + (sgn * 0.0 + 0.16 * PX * k, 0.0), 0.30 * PX * k, mark)
        text(cv, aa, base + (-0.46 * PX * k, 0.085 * PX * k), 0.125 * PX * k, mark)
        text(cv, bb, base + (-0.46 * PX * k, -0.085 * PX * k), 0.125 * PX * k, mark)
    # small stencils and maintenance markings: clusters of dashes
    # (kept away from the seams between the top, side and bottom views)
    for mapfn, (a0, a1, b0, b1), n in ((top, (-4.6, 6.6, 0.04, 0.38), 26), (top, (-2.1, 0.4, 1.4, 4.2), 22),
                                       (bot, (-4.4, 4.0, 0.04, 0.45), 24), (bot, (-2.1, 0.4, 1.4, 4.2), 18),
                                       (side, (-4.6, 4.2, -0.62, -0.24), 30), (side, (4.7, 6.8, -0.08, 0.36), 12)):
        for _ in range(n):
            y, b = rng.uniform(a0, a1), rng.uniform(b0, b1)
            for row in range(int(rng.integers(1, 4))):
                x = y
                for _w in range(int(rng.integers(2, 6))):
                    w = rng.uniform(0.02, 0.06)
                    cv.stroke(poly(mapfn, [(x, b - row * 0.022), (x + w, b - row * 0.022)]), 1.6, mark, 0.55, butt=True)
                    x += w + 0.014
    # rescue arrow and the no-step bands on the strake
    cv.fill(poly(side, [(5.05, 0.30), (5.42, 0.30), (5.42, 0.26), (5.52, 0.335), (5.42, 0.41), (5.42, 0.37), (5.05, 0.37)]),
            (0.70, 0.58, 0.10), 0.85)


def finish(cv, rng):
    """Weathering, then the panel lines on top."""
    n = 0.045 * value_noise(rng, 14, 14) + 0.030 * value_noise(rng, 70, 70) + 0.018 * value_noise(rng, 400, 400)
    n += 0.035 * value_noise(rng, 600, 10)                 # streaks along the airflow
    cv.rgb *= (1.0 + n)[..., None]
    cv.rough += 0.9 * n
    wash = box_blur(cv.lines, 5)
    cv.rgb *= (1.0 - 0.34 * cv.lines - 0.22 * wash)[..., None]
    np.clip(cv.rgb, 0.0, 1.0, out=cv.rgb)


def normal_map(cv):
    h = -box_blur(cv.lines, 1)
    dx = np.zeros_like(h)
    dy = np.zeros_like(h)
    dx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5
    dy[1:-1, :] = (h[2:, :] - h[:-2, :]) * 0.5
    k = 2.2
    nrm = np.stack([-k * dx, -k * dy, np.ones_like(h)], axis=2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return nrm * 0.5 + 0.5


def save(path, rgb, colour=True):
    import bpy
    name = os.path.basename(path)
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, N, N, alpha=False)
    if not colour:
        img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((N, N, 4), np.float32)
    rgba[..., :3] = rgb
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def paint_all(folder, liveries=("viper", "aggressor")):
    os.makedirs(folder, exist_ok=True)
    lines = None
    for name in liveries:
        cv = Canvas()
        rng = np.random.default_rng(16)
        if lines is None:
            draw_lines(cv)
            lines = cv.lines
        cv.lines = lines
        L = LIVERIES[name]
        paint_base(cv, L, rng)
        paint_markings(cv, L, rng)
        finish(cv, rng)
        save(os.path.join(folder, "f16_basecolor.png" if name == "viper" else "f16_basecolor_%s.png" % name), cv.rgb)
        if name == "viper":
            save(os.path.join(folder, "f16_normal.png"), normal_map(cv), colour=False)
            orm = np.stack([np.ones((N, N), np.float32), np.clip(cv.rough + 0.14 * cv.lines, 0.05, 1.0), cv.metal], axis=2)
            save(os.path.join(folder, "f16_orm.png"), orm, colour=False)
        print("painted", name)
