"""Paints the textures of the table driven jets (numpy, runs inside Blender), same atlas scheme as the others.

Strips: top (|x| from V_TOP), bottom (|x| from V_BOT), sides (z + V_SIDE), the fin islands; see generic_shape.
Paint schemes per jet (jets.py `scheme`), the national insignia (`nation`), panel lines worked out from the
shape tables, rivet rows, weathering.
"""

import math
import os

import numpy as np

import f16_paint as P
import generic_shape as S

N = P.N

SCHEMES = {
    # upper, lower, camouflage patches (or None), radome, markings, where the lower colour starts on the side (z)
    "flanker": dict(upper=(0.56, 0.635, 0.705), lower=(0.70, 0.755, 0.805), camo=(0.36, 0.445, 0.545), radome=(0.80, 0.82, 0.82),
                    mark=(0.20, 0.24, 0.30), split=-0.05, cells=7, thr=0.12),
    "felon": dict(upper=(0.42, 0.47, 0.53), lower=(0.62, 0.67, 0.72), camo=(0.30, 0.34, 0.40), radome=(0.40, 0.45, 0.51),
                  mark=(0.18, 0.20, 0.24), split=0.0, cells=9, thr=0.05, splinter=True),
    "fulcrum": dict(upper=(0.58, 0.61, 0.62), lower=(0.70, 0.73, 0.75), camo=(0.40, 0.43, 0.45), radome=(0.86, 0.87, 0.86),
                    mark=(0.20, 0.21, 0.22), split=-0.1, cells=6, thr=0.1),
    "foxhound": dict(upper=(0.60, 0.62, 0.63), lower=(0.68, 0.70, 0.71), camo=None, radome=(0.80, 0.81, 0.80),
                     mark=(0.20, 0.21, 0.22), split=0.0),
    "gripen": dict(upper=(0.47, 0.50, 0.52), lower=(0.55, 0.58, 0.60), camo=None, radome=(0.40, 0.42, 0.44),
                   mark=(0.18, 0.19, 0.20), split=0.0),
    "raf": dict(upper=(0.56, 0.59, 0.61), lower=(0.62, 0.65, 0.67), camo=None, radome=(0.52, 0.55, 0.57),
                mark=(0.30, 0.32, 0.34), split=0.0),
    "rafale": dict(upper=(0.42, 0.45, 0.48), lower=(0.55, 0.58, 0.61), camo=None, radome=(0.30, 0.32, 0.34),
                   mark=(0.16, 0.17, 0.18), split=0.1),
    "f35": dict(upper=(0.35, 0.37, 0.40), lower=(0.38, 0.40, 0.43), camo=None, radome=(0.40, 0.42, 0.45),
                mark=(0.24, 0.26, 0.29), split=0.0),
    "j20": dict(upper=(0.30, 0.33, 0.36), lower=(0.36, 0.39, 0.42), camo=None, radome=(0.48, 0.51, 0.54),
                mark=(0.14, 0.15, 0.16), split=0.0),
    "trainer": dict(upper=(0.84, 0.85, 0.86), lower=(0.84, 0.85, 0.86), camo=None, radome=(0.84, 0.85, 0.86),
                    mark=(0.10, 0.12, 0.20), split=0.0, stripe=(0.10, 0.17, 0.42)),
    "navy_trainer": dict(upper=(0.86, 0.87, 0.88), lower=(0.86, 0.87, 0.88), camo=None, radome=(0.86, 0.87, 0.88),
                         mark=(0.12, 0.12, 0.13), split=0.0, stripe=(0.86, 0.26, 0.08)),
    "talon": dict(upper=(0.84, 0.85, 0.86), lower=(0.84, 0.85, 0.86), camo=None, radome=(0.84, 0.85, 0.86),
                  mark=(0.10, 0.10, 0.11), split=0.0, stripe=(0.10, 0.10, 0.11)),
}

GLYPHS = dict(P.GLYPHS)
GLYPHS.update({
    "E": [[(4, 5.5), (0.5, 5.5), (0.5, 0.5), (4, 0.5)], [(0.5, 3), (3, 3)]],
    "T": [[(0.3, 5.5), (3.7, 5.5)], [(2, 5.5), (2, 0)]],
    "N": [[(0.5, 0), (0.5, 6), (3.5, 0), (3.5, 6)]],
    "R": [[(0.5, 0), (0.5, 5.5), (2.8, 5.5), (3.5, 4.8), (3.5, 3.7), (2.8, 3), (0.5, 3)], [(2, 3), (3.6, 0)]],
    "Y": [[(0.4, 6), (2, 3.2), (3.6, 6)], [(2, 3.2), (2, 0)]],
    "V": [[(0.4, 6), (2, 0), (3.6, 6)]],
    "S": [[(3.5, 4.6), (2.5, 5.5), (1.5, 5.5), (0.5, 4.6), (0.5, 3.9), (1.4, 3), (2.6, 3), (3.5, 2.1), (3.5, 1.4),
           (2.5, 0.5), (1.5, 0.5), (0.5, 1.4)]],
    "3": [[(0.5, 4.6), (1.5, 5.5), (2.5, 5.5), (3.5, 4.6), (3.5, 3.8), (2.6, 3), (3.5, 2.2), (3.5, 1.4), (2.5, 0.5),
           (1.5, 0.5), (0.5, 1.4)], [(1.4, 3), (2.6, 3)]],
    "5": [[(3.6, 5.5), (0.6, 5.5), (0.5, 3.2), (2.5, 3.4), (3.5, 2.4), (3.5, 1.4), (2.5, 0.5), (1.5, 0.5), (0.5, 1.4)]],
    "7": [[(0.4, 5.5), (3.6, 5.5), (1.6, 0)]],
})


def text(cv, string, centre, height, colour, alpha=1.0):
    old = P.GLYPHS
    P.GLYPHS = GLYPHS
    try:
        P.text(cv, string, centre, height, colour, alpha)
    finally:
        P.GLYPHS = old


def px():
    return N / S.ATLAS


def top(y, x):
    return (np.asarray(y, float) - S.YA0) * px(), (S.V_TOP + np.abs(np.asarray(x, float))) * px()


def bot(y, x):
    return (np.asarray(y, float) - S.YA0) * px(), (S.V_BOT + np.abs(np.asarray(x, float))) * px()


def side(y, z):
    return (np.asarray(y, float) - S.YA0) * px(), (S.V_SIDE + np.asarray(z, float)) * px()


def fin_r(y, s):
    u, v = S.fin_island(y, s, 1.0)
    return u * px(), v * px()


def fin_l(y, s):
    u, v = S.fin_island(y, s, -1.0)
    return u * px(), v * px()


poly, rect = P.poly, P.rect


# ------------------------------------------------------------------ panel lines
def draw_lines(cv, cfg, gear, rng):
    def line(m, pts, width=1.5, strength=0.75):
        cv.groove(poly(m, pts), width, strength)

    def box(m, a0, a1, b0, b1, **kw):
        line(m, [(a0, b0), (a1, b0), (a1, b1), (a0, b1), (a0, b0)], **kw)
    xr, xt = S.X_ROOT, S.X_TIP
    te = lambda x: float(S.wing_te(x))                          # noqa: E731
    le = lambda x: float(S.wing_le(x))                          # noqa: E731
    f0, f1 = S.FLAP[0], S.FLAP[1]
    a0, a1 = S.AIL[0], S.AIL[1]
    flp = lambda x: te(x) + float(S.flap_chord(x))             # noqa: E731
    ail = lambda x: te(x) + float(S.ail_chord(x))              # noqa: E731
    for m in (top, bot):
        line(m, [(te(f0), f0), (flp(f0), f0), (flp(f1), f1), (te(f1), f1)], 2.2, 1.0)
        line(m, [(te(a0), a0), (ail(a0), a0), (ail(a1), a1), (te(a1), a1)], 2.2, 1.0)
        if S.LEF:
            l0, l1, f = S.LEF
            line(m, [(le(l0), l0), (le(l0) - f * float(S.wing_chord(l0)), l0), (le(l1) - f * float(S.wing_chord(l1)), l1), (le(l1), l1)], 2.0, 0.9)
        line(m, [(S.Y_KINK, xr), (S.WING_TE, xr)], 1.6, 0.6)
        for x in np.arange(xr + 0.8, xt - 0.2, 0.85):
            aft = flp(x) if f0 <= x <= f1 else ail(x) if a0 <= x <= a1 else te(x)
            front = le(x) - (S.LEF[2] * float(S.wing_chord(x)) if S.LEF and S.LEF[0] <= x <= S.LEF[1] else 0.05)
            line(m, [(front, x), (aft, x)])
        for f in (0.25, 0.58):
            line(m, [(le(xr) - f * float(S.wing_chord(xr)), xr), (le(xt) - f * float(S.wing_chord(xt)), xt)], 1.3, 0.55)
        for srf in S.SURFACES:
            x0, x1 = srf.x0, srf.x1
            for x in np.linspace(x0 + 0.5, x1 - 0.3, 3):
                line(m, [(float(srf.le(x)) - 0.08, x), (float(srf.te(x)) + 0.05, x)], 1.2, 0.5)
            line(m, [(float(srf.le(x0)) - 0.4, x0), (float(srf.le(x1)) - 0.2, x1)], 1.2, 0.5)
    hw = lambda y: float(S.BODY[2](y))                          # noqa: E731
    zt, zb, zc = (lambda y: float(S.BODY[0](y))), (lambda y: float(S.BODY[1](y))), (lambda y: float(S.BODY[5](y)))
    yr = S.Y_RADOME
    for m in (top, bot):
        line(m, [(yr, 0.0), (yr, hw(yr) * 1.05)], 2.4, 1.0)
    line(side, [(yr, zb(yr) - 0.05), (yr, zt(yr) + 0.05)], 2.4, 1.0)
    ys = np.arange(yr - 0.9, S.Y_BODY_END + 0.3, -1.05)
    for y in ys:
        if not (S.CANOPY_Y0 - 0.05 < y < S.CANOPY_Y1 + 0.05):
            line(top, [(y, 0.0), (y, hw(y) * 0.92)])
        line(bot, [(y, 0.0), (y, hw(y) * 0.92)])
        line(side, [(y, zb(y) + 0.02), (y, zt(y) - 0.05)])
    line(side, [(yr - 0.3, zc(yr)), (S.Y_BODY_END + 0.3, zc(S.Y_BODY_END))], 1.3, 0.6)
    line(top, [(S.CANOPY_Y0 - 0.1, 0.0), (S.Y_BODY_END + 0.4, 0.0)], 1.2, 0.5)
    line(bot, [(yr - 0.2, 0.0), (S.Y_BODY_END + 0.4, 0.0)], 1.2, 0.5)
    for k in range(int(S.ATLAS * 1.6)):                            # access panels
        y = rng.uniform(S.Y_BODY_END + 0.6, yr - 0.5)
        if S.CANOPY_Y0 - 0.2 < y < S.CANOPY_Y1 + 0.2:
            continue
        w, h = rng.uniform(0.25, 0.7), rng.uniform(0.15, 0.4)
        m = (top, bot, side)[k % 3]
        if m is side:
            b = rng.uniform(zb(y) + 0.1, max(zb(y) + 0.11, zt(y) - 0.2))
        else:
            b = rng.uniform(0.05, max(0.1, hw(y) * 0.8 - h))
        box(m, y - w, y, b, b + h, width=1.2, strength=0.55)
    sb = cfg.get("speed_brake")
    if sb:
        box(top, sb["y1"], sb["y0"], 0.0, sb["w"], width=2.2, strength=1.0)
    for d in S.DUCTS:
        y0 = d.y0
        line(side, [(y0 - 0.5, d.section(y0 - 0.5)[3]), (y0 - 0.5, d.section(y0 - 0.5)[2])], 1.6, 0.8)
        for y in np.arange(y0 - 1.5, d.y1, -1.2):
            line(bot, [(y, d.section(y)[0]), (y, d.section(y)[1])], 1.4, 0.6)
    if S.FIN is not None:
        f = S.FIN
        for m in (fin_r, fin_l):
            if f.rudder:
                r0, r1 = f.rudder[0], f.rudder[1]
                hinge = lambda s: float(f.te(s) + f.rudder_chord(s))      # noqa: E731
                line(m, [(float(f.te(r0)), r0), (hinge(r0), r0), (hinge(r1), r1), (float(f.te(r1)), r1)], 2.2, 1.0)
            for s in np.linspace(f.s0 + 0.5, f.s1 - 0.4, 3):
                aft = float(f.te(s) + f.rudder_chord(s)) if f.rudder and f.rudder[0] <= s <= f.rudder[1] else float(f.te(s))
                line(m, [(float(f.le(s)) - 0.05, s), (aft, s)])
    # nose wheel doors, main wells
    x0, x1, y0, y1 = gear["plan"]["nose"]["rect"]
    box(bot, y0, y1, 0.0, x1, width=2.0, strength=1.0)
    for (x0, x1, y0, y1) in gear["painted"]:
        box(bot, y0, y1, x0, x1, width=2.0, strength=1.0)


# ------------------------------------------------------------------ insignia
def star_points(c, fwd, r, inner=0.38, k=5):
    left = np.array([-fwd[1], fwd[0]])
    pts = []
    for i in range(2 * k):
        a = i * math.pi / k
        rr = r * (1.0 if i % 2 == 0 else inner)
        pts.append(c + fwd * math.cos(a) * rr + left * math.sin(a) * rr)
    return pts


def frame(mapfn, a, b):
    c = np.array(mapfn(a, b), float)
    fwd = np.array(mapfn(a + 1.0, b), float) - c
    return c, fwd / np.hypot(*fwd)


def frame_up(mapfn, a, b):
    """For the fin islands: 'up' the fin is the star's up."""
    c = np.array(mapfn(a, b), float)
    up = np.array(mapfn(a, b + 1.0), float) - c
    return c, up / np.hypot(*up)


def insignia(cv, nation, c, fwd, r, low=False):
    rp = r * px()
    if nation == "ru":
        cv.fill(star_points(c, fwd, rp * 1.18), (0.60, 0.07, 0.06), 0.95)
        cv.fill(star_points(c, fwd, rp * 1.08), (0.88, 0.88, 0.86), 0.95)
        cv.fill(star_points(c, fwd, rp), (0.66, 0.06, 0.05), 0.95)
    elif nation == "cn":
        left = np.array([-fwd[1], fwd[0]])
        col = (0.62, 0.07, 0.06) if not low else (0.22, 0.24, 0.27)
        cv.fill([c + left * a * rp + fwd * b * rp for a, b in ((-1.9, -0.32), (1.9, -0.32), (1.9, 0.32), (-1.9, 0.32))], col, 0.9)
        cv.disc(c, rp * 0.95, (0.85, 0.75, 0.15) if not low else (0.30, 0.32, 0.35), 0.9)
        cv.fill(star_points(c, fwd, rp * 0.88), col, 0.95)
    elif nation == "us":
        left = np.array([-fwd[1], fwd[0]])
        col = (0.10, 0.12, 0.30) if not low else (0.30, 0.32, 0.34)
        white = (0.85, 0.86, 0.86) if not low else (0.40, 0.42, 0.44)
        cv.fill([c + left * a * rp + fwd * b * rp for a, b in ((-2.1, -0.36), (2.1, -0.36), (2.1, 0.36), (-2.1, 0.36))], white, 0.9)
        if not low:
            cv.fill([c + left * a * rp + fwd * b * rp for a, b in ((-2.0, -0.12), (2.0, -0.12), (2.0, 0.12), (-2.0, 0.12))], (0.62, 0.08, 0.08), 0.9)
        cv.disc(c, rp, col, 0.9)
        cv.fill(star_points(c, fwd, rp * 0.92), white, 1.0)
    elif nation in ("uk", "fr"):
        cols = [(0.62, 0.70, 0.80), (0.82, 0.62, 0.62)] if nation == "uk" else [(0.12, 0.20, 0.50), (0.88, 0.88, 0.88), (0.70, 0.10, 0.10)]
        if nation == "uk" and not low:
            cols = [(0.12, 0.18, 0.45), (0.86, 0.86, 0.86), (0.70, 0.10, 0.10)]
        for i, col in enumerate(cols):
            cv.disc(c, rp * (1.0 - i * (0.33 if len(cols) == 3 else 0.45)), col, 0.92)
    elif nation == "se":
        cv.disc(c, rp, (0.20, 0.36, 0.62), 0.92)
        left = np.array([-fwd[1], fwd[0]])
        for a, b in ((0.0, 0.42), (-0.38, -0.25), (0.38, -0.25)):
            p = c + left * a * rp + fwd * b * rp
            cv.fill([p + left * u * rp + fwd * v * rp for u, v in ((-0.2, -0.13), (0.2, -0.13), (0.24, 0.13), (0.1, 0.04), (0.0, 0.16),
                                                                    (-0.1, 0.04), (-0.24, 0.13))], (0.95, 0.80, 0.15), 1.0)


# ------------------------------------------------------------------ base colours
def paint_base(cv, cfg, sc, gear, rng):
    PX = px()
    up, lo = np.asarray(sc["upper"], np.float32), np.asarray(sc["lower"], np.float32)
    cv.rgb[:] = up
    camo = None
    if sc.get("camo") is not None:
        cells = max(3, int(S.ATLAS / sc.get("cells", 7) * 2.2))
        n = P.value_noise(rng, cells, cells) + 0.35 * P.value_noise(rng, cells * 3, cells * 3)
        if sc.get("splinter"):
            n = np.round(n * 3.0) / 3.0
        camo = S.smoothstep(sc["thr"] - 0.03, sc["thr"] + 0.03, n)[..., None]
        cv.rgb[:] = up * (1.0 - camo) + np.asarray(sc["camo"], np.float32) * camo
    b0, b1 = int(S.V_BOT * PX), int(2 * S.HALF * PX + 0.1 * PX)
    cv.rgb[b0:b1] = lo
    r0 = b1
    z = ((np.arange(r0, N, dtype=np.float32) + 0.5) / PX - S.V_SIDE)[:, None]
    below = S.smoothstep(0.06, -0.06, z - sc.get("split", 0.0))[..., None]
    cv.rgb[r0:] = cv.rgb[r0:] * (1.0 - below) + lo * below
    if S.FIN is not None:
        for m in (fin_r, fin_l):
            pass                                          # the fins keep the upper colour (and the camouflage)
    ys = np.linspace(S.CANOPY_Y0 + 0.05, S.CANOPY_Y1 - 0.03, 60)
    cv.fill(poly(top, [(yy, 0.0) for yy in (ys[0], ys[-1])] + [(yy, float(S.CANOPY_W(yy)) * 0.96) for yy in ys[::-1]]),
            (0.085, 0.09, 0.095), rough=0.75)
    hw = float(S.BODY[2](S.Y_RADOME))
    for mapfn, c0, c1 in ((top, 0.0, hw + 0.2), (bot, 0.0, hw + 0.2), (side, -2.0, 2.0)):
        cv.fill(rect(mapfn, S.Y_RADOME, S.Y_NOSE + 0.1, c0, c1), sc["radome"], 0.95)
    if cfg.get("antiglare", True):
        cv.fill(rect(top, S.CANOPY_Y1 - 0.05, S.CANOPY_Y1 + 0.55, 0.0, 0.30), (0.10, 0.10, 0.11), 0.9, rough=0.8)
    for nz in S.NOZZLES:                                   # the hot aft end
        ya, yb = nz["y0"] - 0.1, nz["y0"] + 0.9
        x = abs(nz["x"]) + nz["r0"] + 0.15
        for mapfn, c0, c1 in ((top, max(0.0, abs(nz["x"]) - nz["r0"] - 0.2), x), (bot, max(0.0, abs(nz["x"]) - nz["r0"] - 0.2), x),
                              (side, nz["z"] - nz["r0"] - 0.2, nz["z"] + nz["r0"] + 0.2)):
            cv.fill(rect(mapfn, ya, yb, c0, c1), (0.30, 0.285, 0.27), 0.75, rough=0.42, metal=0.85)
    for (x0, x1, y0, y1) in gear["painted"]:              # main gear wells (painted, the door hangs below)
        cv.fill(rect(bot, y0, y1, x0, x1), (0.16, 0.17, 0.18), 1.0, rough=0.8)
    if sc.get("stripe") is not None:                        # trainers: a cheat line along the side, coloured fin tip
        st = sc["stripe"]
        zc = lambda y: float(S.BODY[5](y))                  # noqa: E731
        yy = np.linspace(S.Y_RADOME, S.Y_BODY_END + 0.5, 40)
        cv.fill(poly(side, [(y, zc(y) - 0.04) for y in yy] + [(y, zc(y) + 0.06) for y in yy[::-1]]), st, 0.95)
        if S.FIN is not None:
            f = S.FIN
            s0 = f.s1 - 0.45
            for m in (fin_r, fin_l):
                cv.fill(poly(m, [(float(f.le(s0)) + 0.1, s0), (float(f.le(f.s1)) + 0.1, f.s1 + 0.1), (float(f.te(f.s1)) - 0.1, f.s1 + 0.1),
                                 (float(f.te(s0)) - 0.1, s0)]), st, 0.95)


def paint_markings(cv, cfg, sc, rng):
    nation = cfg.get("nation", "us")
    low = cfg.get("low_vis", False)
    xw = S.X_ROOT + 0.62 * (S.X_TIP - S.X_ROOT)
    yw = 0.5 * (float(S.wing_le(xw)) + float(S.wing_te(xw)))
    rw = min(0.42, 0.28 * float(S.wing_chord(xw)))
    for m in (top, bot):
        c, fwd = frame(m, yw, xw)
        insignia(cv, nation, c, fwd, rw, low)
    if S.FIN is not None:
        f = S.FIN
        sm = f.s0 + 0.55 * (f.s1 - f.s0)
        ym = 0.5 * (float(f.le(sm)) + float(f.te(sm))) - 0.1
        r = min(0.34, 0.20 * float(f.le(sm) - f.te(sm)))
        bort = cfg.get("bort")
        for m in (fin_r, fin_l):
            c, upv = frame_up(m, ym, sm)
            if nation in ("ru", "cn"):
                insignia(cv, nation, c, upv, r, low)
            elif nation in ("uk", "fr", "se"):
                cv.fill(rect(m, ym - 0.32, ym + 0.32, sm - 0.22, sm + 0.22), (0.12, 0.20, 0.50) if nation != "se" else sc["mark"], 0.0)
            if bort:
                s_b = f.s0 + 0.22 * (f.s1 - f.s0)
                yb = 0.5 * (float(f.le(s_b)) + float(f.te(s_b)))
                col = cfg.get("bort_colour", (0.15, 0.25, 0.55) if nation == "ru" else sc["mark"])
                text(cv, bort, np.array(m(yb, s_b), float), 0.30 * px() * S.FIN_ISLAND_SCALE, col, 0.92)
            tail = cfg.get("tail_code")
            if tail:
                s_t = f.s0 + 0.72 * (f.s1 - f.s0)
                yt_ = 0.5 * (float(f.le(s_t)) + float(f.te(s_t)))
                text(cv, tail, np.array(m(yt_, s_t), float), 0.32 * px() * S.FIN_ISLAND_SCALE, sc["mark"], 0.9)
    # roundels on the sides of the intakes / nose (round, so the mirrored side reads the same)
    if nation in ("uk", "fr", "se", "us") and cfg.get("side_roundel"):
        y, z, r = cfg["side_roundel"]
        c, fwd = frame(side, y, z)
        insignia(cv, nation, c, fwd, r, low)
    # rivet rows
    PXv = px()
    zt, zb = (lambda y: float(S.BODY[0](y))), (lambda y: float(S.BODY[1](y)))
    for mapfn, n in ((top, 26), (bot, 22), (side, 30)):
        for _ in range(n):
            y = rng.uniform(S.Y_BODY_END + 0.5, S.Y_RADOME - 0.3)
            b = rng.uniform(0.05, float(S.BODY[2](y)) * 0.8) if mapfn is not side else rng.uniform(zb(y) + 0.1, max(zb(y) + 0.11, zt(y) - 0.15))
            for row in range(int(rng.integers(1, 4))):
                x = y
                for _w in range(int(rng.integers(2, 6))):
                    w = rng.uniform(0.02, 0.06)
                    cv.stroke(poly(mapfn, [(x, b - row * 0.022), (x + w, b - row * 0.022)]), 1.4 * PXv / 195, sc["mark"], 0.45, butt=True)
                    x += w + 0.014


def paint_all(folder, cfg, gear):
    os.makedirs(folder, exist_ok=True)
    sc = SCHEMES[cfg.get("scheme", "trainer")]
    cv = P.Canvas()
    rng = np.random.default_rng(abs(hash(cfg["name"])) % 1000)
    draw_lines(cv, cfg, gear, rng)
    paint_base(cv, cfg, sc, gear, rng)
    paint_markings(cv, cfg, sc, rng)
    P.finish(cv, rng)
    ID = cfg["name"]
    P.save(os.path.join(folder, ID + "_basecolor.png"), cv.rgb)
    P.save(os.path.join(folder, ID + "_normal.png"), P.normal_map(cv), colour=False)
    orm = np.stack([np.ones((N, N), np.float32), np.clip(cv.rough + 0.14 * cv.lines, 0.05, 1.0), cv.metal], axis=2)
    P.save(os.path.join(folder, ID + "_orm.png"), orm, colour=False)
    print("painted", ID)
