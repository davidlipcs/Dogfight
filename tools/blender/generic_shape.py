"""Shape maths of the table driven Blender jets (pure numpy), configured per aircraft from jets.py.

The same ideas as the hand built F-15 / F-22 shape modules: the fuselage is an implicit cross section at each
station y (a superellipse core, plus a thin blade: the leading edge root extension / chine ahead of the wing and
the inboard wing behind it, joined with smooth fillets), the lifting surfaces are thin airfoils on piecewise
linear planforms, the inlet ducts and engine nacelles are superellipse sweeps.

Model frame: +Y forward, +X right, +Z up, metres; origin near the centre of gravity, ground at Z_GROUND with the
gear down.  configure(cfg) fills the module level names that the builder (build_generic.py) and the painter
(generic_paint.py) use, with the same names as the F-15 module where they mean the same thing.
"""

import math

import numpy as np

from f16_shape import Curve, resample, smin, smoothstep, yt   # noqa: F401  (re-exported)

CFG = {}


class Lin:
    """Piecewise linear table (planform edges with kinks); clamps outside."""

    def __init__(self, pts):
        pts = sorted(pts)
        self.x = np.array([p[0] for p in pts], float)
        self.y = np.array([p[1] for p in pts], float)

    def __call__(self, x):
        return np.interp(np.asarray(x, float), self.x, self.y)


class Const:
    def __init__(self, v):
        self.v = float(v)

    def __call__(self, x):
        return np.full(np.shape(x), self.v) if np.ndim(x) else self.v


def _curve(pts):
    pts = list(pts)
    return Curve(pts) if len(pts) > 1 else Const(pts[0][1])


# ------------------------------------------------------------------ planform helpers (filled by configure)
def wing_le(x):
    return WLE(np.abs(x))


def wing_te(x):
    return WTE(np.abs(x))


def wing_chord(x):
    return wing_le(x) - wing_te(x)


def wing_z(x):
    return Z_WING + (np.abs(x) - X_ROOT) * math.tan(DIHEDRAL)


def wing_t(x):
    return T_ROOT + (T_TIP - T_ROOT) * np.clip((np.abs(x) - X_ROOT) / (X_TIP - X_ROOT), 0.0, 1.0)


def _lin_chord(spec, x):
    x0, x1, c0, c1 = spec
    return c0 + (c1 - c0) * np.clip((np.abs(x) - x0) / (x1 - x0), 0.0, 1.0)


def flap_chord(x):
    return _lin_chord(FLAP, x)


def ail_chord(x):
    return _lin_chord(AIL, x)


class Surface:
    """A horizontal tail or canard (or any trapezoid panel): root x0 .. tip x1, leading / trailing edge lines."""

    def __init__(self, d):
        self.d = d
        self.x0, self.x1 = d["x0"], d["x1"]
        self.le0, self.te0 = d["le0"], d["te0"]
        span = self.x1 - self.x0
        self.le1 = d.get("le1", self.le0 - span * math.tan(math.radians(d.get("sweep", 45.0))))
        self.te1 = d.get("te1", self.te0 - span * math.tan(math.radians(d.get("te_sweep", 0.0))))
        self.z0 = d.get("z", 0.0)
        self.dih = math.radians(d.get("dihedral", 0.0))
        self.pivot = d.get("pivot", 0.5 * (self.le0 + self.te0))
        self.t = d.get("t", 0.045)
        self.canard = d.get("canard", False)

    def le(self, x):
        return self.le0 + (self.le1 - self.le0) * (np.abs(x) - self.x0) / (self.x1 - self.x0)

    def te(self, x):
        return self.te0 + (self.te1 - self.te0) * (np.abs(x) - self.x0) / (self.x1 - self.x0)

    def z(self, x):
        return self.z0 + (np.abs(x) - self.x0) * math.tan(self.dih)


class Fin:
    """A vertical (or canted) fin: s = distance up the fin from its root along the span direction."""

    def __init__(self, d):
        self.d = d
        self.x, self.zroot = d.get("x", 0.0), d["z"]
        self.cant = math.radians(d.get("cant", 0.0))
        self.twin = self.x > 1e-6
        self.s0, self.s1 = d.get("s0", -0.10), d["s1"]
        self.le0, self.te0 = d["le0"], d["te0"]
        self.sweep = math.tan(math.radians(d.get("sweep", 40.0)))
        self.te_sweep = math.tan(math.radians(d.get("te_sweep", 0.0)))
        self.rudder = d.get("rudder")               # (s0, s1, chord0, chord1) or None
        self.moving = d.get("moving", False)        # all moving fin (pivot y)
        self.pivot = d.get("pivot")
        self.t0, self.t1 = d.get("t", (0.05, 0.035))

    def le(self, s):
        return self.le0 - np.asarray(s, float) * self.sweep

    def te(self, s):
        return self.te0 - np.asarray(s, float) * self.te_sweep

    def rudder_chord(self, s):
        r0, r1, c0, c1 = self.rudder
        return c0 + (c1 - c0) * (np.asarray(s, float) - r0) / (r1 - r0)

    def span_dir(self, sign):
        return np.array([sign * math.sin(self.cant), 0.0, math.cos(self.cant)])

    def normal(self, sign):
        return np.array([sign * math.cos(self.cant), 0.0, -math.sin(self.cant)])

    def s_of(self, x, z):
        return (np.abs(x) - self.x) * math.sin(self.cant) + (z - self.zroot) * math.cos(self.cant)

    def point(self, sign, s, y, off):
        root = np.array([sign * self.x, 0.0, self.zroot])
        s, y, off = (np.asarray(v, float) for v in (s, y, off))
        return root + self.span_dir(sign) * s[..., None] + np.array([0.0, 1.0, 0.0]) * y[..., None] + self.normal(sign) * off[..., None]

    def y_range(self):
        ys = [float(self.le(self.s0)), float(self.le(self.s1)), float(self.te(self.s0)), float(self.te(self.s1))]
        return min(ys), max(ys)


class Duct:
    """An inlet trunk / engine nacelle: (y, inner x, outer x, top, bottom, n upper, n lower) rows, mirrored
    (two of them) or on the centre line (`centre`: inner x = -outer x)."""

    def __init__(self, d):
        self.d = d
        rows = d["table"]
        self.cols = [_curve([(r[0], r[c]) for r in rows]) for c in range(1, 7)]
        self.y0 = max(r[0] for r in rows)
        self.y1 = min(r[0] for r in rows)
        self.mirror = d.get("mirror", True)
        self.rake = d.get("rake", 0.42)            # metres forward per metre up at the face (top lip ahead)
        self.depth = d.get("depth", 3.0)           # how far the dark duct is drawn in
        self.side_rake = d.get("side_rake", 0.0)   # metres forward per metre outboard (Typhoon style faces)

    def section(self, y):
        return tuple(float(c(y)) for c in self.cols)

    def bottom(self, y, x):
        xi, xo, zt, zb, nu, nl = self.section(y)
        cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
        cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
        t = min(abs(abs(x) - cx) / hw, 1.0) if self.mirror else min(abs(x) / hw, 1.0)
        return cz - hh * max(0.0, 1.0 - t ** nl) ** (1.0 / nl)

    def covers(self, y, x):
        if not (self.y1 <= y <= self.y0):
            return False
        xi, xo = self.section(y)[:2]
        return xi < abs(x) < xo if self.mirror else abs(x) < xo


# ------------------------------------------------------------------ the fuselage section
class Section:
    """Implicit cross section F(x, z) < 0 at station y: superellipse core plus the chine / LERX / inboard wing
    blade, joined with fillets (as in the F-15 and F-22 modules)."""

    def __init__(self, y, blade=True):
        self.y = float(y)
        self.zt, self.zb, self.hw, self.nu, self.nl, self.zc = (float(c(y)) for c in BODY)
        self.core = min(self.hw, self.zt - self.zc, self.zc - self.zb)
        self.xlim = None
        self.z0 = self.zc
        self.ghost = 0.0
        self.fade = 0.0
        if not WING_BLADE:
            return
        if blade and WING_TE - 1.4 < y <= WING_TE:
            self.ghost = float(smoothstep(WING_TE - 1.4, WING_TE, y))
            self.ku, self.kl = float(K_UP(WING_TE)) * self.ghost, float(K_LO(WING_TE)) * self.ghost
            self.z0 = blade_z(WING_TE)
        if blade and WING_TE < y <= Y_CHINE0:
            self.z0 = blade_z(y)
            self.ku, self.kl = float(K_UP(y)), float(K_LO(y))
            if CHINE is not None and y >= Y_KINK:
                self.xlim = float(CHINE(y))
                self.edge, self.fade = self.xlim, 1.0
            else:
                self.xlim = X_ROOT
                self.edge = X_ROOT + (Y_KINK - y) / TAN_LE0
                self.fade = max(0.0, 1.0 - (Y_KINK - y) / 1.0) if (CHINE is not None and y <= Y_KINK) else 0.0

    def F(self, x, z):
        ax = np.abs(x)
        dz = z - self.zc
        up = dz >= 0.0
        h = np.where(up, self.zt - self.zc, self.zc - self.zb)
        n = np.where(up, self.nu, self.nl)
        q = (ax / self.hw) ** n + (np.abs(dz) / h) ** n
        f = (q ** (1.0 / n) - 1.0) * self.core
        if self.xlim is not None:
            c = wing_chord(ax)
            s = (wing_le(ax) - self.y) / c
            tau = np.where((s > 0.0) & (s < 1.0), yt(s, wing_t(X_ROOT)) * c, -1.0)
            if self.fade > 0.0:
                tau = np.maximum(tau, np.minimum((self.edge - ax) * 0.10, CHINE_T) * self.fade)
            fb = np.maximum(np.abs(z - self.z0) - tau, ax - self.xlim)
            f = smin(f, fb, np.where(z >= self.z0, self.ku, self.kl))
        if self.ghost > 0.0:
            fb = np.maximum(np.abs(z - self.z0) + 0.002, ax - X_ROOT)
            f = smin(f, fb, np.where(z >= self.z0, self.ku, self.kl))
        return f

    def _exit(self, cos, sin, rcap, nr=300, iters=30):
        t = np.linspace(0.0, 1.0, nr)
        rs = rcap[:, None] * t[None, :]
        out = self.F(rs * cos[:, None], self.z0 + rs * sin[:, None]) > 0.0
        out[:, 0] = False
        hit = out.any(axis=1)
        idx = np.where(hit, np.argmax(out, axis=1), nr - 1)
        rows = np.arange(len(rcap))
        lo, hi = rs[rows, idx - 1], rs[rows, idx]
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            o = self.F(mid * cos, self.z0 + mid * sin) > 0.0
            hi = np.where(o, mid, hi)
            lo = np.where(o, lo, mid)
        return np.where(hit, 0.5 * (lo + hi), rcap)

    def _vertical(self, x, direction, reach=3.0, iters=40):
        x = np.atleast_1d(np.asarray(x, float))
        lo = np.full(x.shape, self.z0)
        hi = lo + direction * reach
        inside = self.F(x, lo) < 0.0
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            o = self.F(x, mid) > 0.0
            hi = np.where(o, mid, hi)
            lo = np.where(o, lo, mid)
        return np.where(inside, 0.5 * (lo + hi), self.z0)

    def top(self, x):
        return self._vertical(x, 1.0)

    def bottom(self, x):
        return self._vertical(x, -1.0)

    def _edge(self, x, iters=40):
        out = []
        for d in (1.0, -1.0):
            lo, hi = self.z0, self.z0 + d * 0.6
            for _ in range(iters):
                mid = 0.5 * (lo + hi)
                if float(np.ravel(self.F(np.array([x]), np.array([mid])))[0]) > 0.0:
                    hi = mid
                else:
                    lo = mid
            out.append(0.5 * (lo + hi))
        return out

    def half_ring(self, n_up=48, n_cut=2, n_lo=44, dense=400):
        rmax = 1.3 * max(self.hw, self.zt - self.zb, self.xlim or 0.0) + 0.3
        cap0 = rmax if self.xlim is None else min(rmax, self.xlim - 1e-6)
        r0 = float(self._exit(np.array([1.0]), np.array([0.0]), np.array([cap0]))[0])
        if self.xlim is not None and r0 >= cap0 - 1e-5:
            xe = cap0
            zu, zl = self._edge(xe)
        else:
            xe, zu, zl = r0, self.z0, self.z0
            cap0 = None
        u = np.linspace(0.0, 1.0, dense) ** 2.2
        halves = []
        for zc, end in ((zu, 0.5 * math.pi), (zl, -0.5 * math.pi)):
            th0 = math.atan2(zc - self.z0, xe)
            th = th0 + (end - th0) * u
            cos, sin = np.cos(th), np.sin(th)
            rcap = np.full(dense, rmax)
            if cap0 is not None:
                rcap = np.minimum(rcap, cap0 / np.maximum(cos, 1e-9))
            r = self._exit(cos, sin, rcap)
            pts = np.stack([r * cos, self.z0 + r * sin], axis=1)
            pts[0] = (xe, zc)
            pts[-1, 0] = 0.0
            halves.append(pts)
        upper = resample(halves[0][::-1], n_up)
        lower = resample(halves[1], n_lo)
        t = np.linspace(0.0, 1.0, n_cut + 1)[1:-1, None]
        cut = np.array([xe, zu]) * (1.0 - t) + np.array([xe, zl]) * t
        return np.concatenate([upper, cut, lower], axis=0)


def blade_z(y):
    if CHINE_Z is not None and y > Y_KINK:
        return float(CHINE_Z(y))
    return float(wing_z(X_ROOT))


def body_top(y, x):
    return Section(y).top(x)


def body_bottom(y, x):
    return Section(y).bottom(x)


def body_hw(y):
    return float(BODY[2](y))


def lower_z(x, y, strict=False):
    """The lowest skin under (x, y): the body or a duct / nacelle hanging under it.  Outside the body (and the
    ducts): 9.0 with `strict`, else the body's underside at its edge."""
    hw = body_hw(y)
    z = float(body_bottom(y, abs(x))[0]) if abs(x) < hw else (9.0 if strict else float(body_bottom(y, hw * 0.95)[0]))
    for d in DUCTS:
        if d.covers(y, x):
            z = min(z, d.bottom(y, x))
    return z


def canopy_sill(y):
    w = float(CANOPY_W(y))
    return w, float(body_top(y, w)[0]) - 0.012


def canopy_z(y, x):
    w, zs = canopy_sill(y)
    c = min(abs(x) / w, 1.0) ** 1.125
    return zs + float(CANOPY_H(y)) * max(0.0, 1.0 - c * c) ** (0.5 * 0.889)


def cockpit_w(y):
    y = min(max(y, COCKPIT_Y0), COCKPIT_Y1)
    return min(COCKPIT_W, float(CANOPY_W(y)) - 0.075)


def skin_limit(x, y):
    """The highest a cockpit part may reach at (x, y): the canopy glass, or the skin where there is none."""
    if CANOPY_Y0 < y < CANOPY_Y1 and abs(x) < float(CANOPY_W(y)):
        return canopy_z(y, x)
    return float(body_top(y, abs(x))[0])


# ------------------------------------------------------------------ texture atlas
def fin_s(x, z):
    return FIN.s_of(x, z) if FIN is not None else np.zeros(np.shape(x))


def fin_island(y, s, sign):
    u0, v0 = FIN_ISLANDS[sign]
    k = FIN_ISLAND_SCALE
    u = u0 + ((np.asarray(y) - FIN_YMIN) if sign > 0 else (FIN_YMAX - np.asarray(y))) * k
    return u, v0 + (np.asarray(s) - FIN.s0) * k


def _occupancy(step=0.05):
    """Atlas metres occupied in the top / bottom strips: (u, |x|) grid of the planform."""
    ys = YA0 + (np.arange(int(ATLAS / step)) + 0.5) * step
    xs = (np.arange(int(HALF / step)) + 0.5) * step
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    m = 0.12
    hw = np.interp(ys, BODY[2].x, BODY[2].y)
    hw = np.where((ys > BODY[2].x.min()) & (ys < BODY[2].x.max()), hw, 0.0)
    occ = X < hw[:, None] + m
    if CHINE is not None:
        ch = np.array([float(CHINE(y)) if Y_KINK <= y <= Y_CHINE0 else 0.0 for y in ys])
        occ |= X < ch[:, None] + m
    occ |= (X >= X_ROOT - m) & (X <= X_TIP + m) & (Y <= wing_le(np.clip(X, X_ROOT, X_TIP)) + m) & (Y >= wing_te(np.clip(X, X_ROOT, X_TIP)) - m)
    occ |= (X < X_ROOT + m) & (Y < Y_KINK + m) & (Y > WING_TE - m)
    for srf in SURFACES:
        xx = np.clip(X, srf.x0, srf.x1)
        occ |= (X >= srf.x0 - m - 0.6) & (X <= srf.x1 + m) & (Y <= srf.le(xx) + m) & (Y >= srf.te(xx) - m)
    for d in DUCTS:
        for i, y in enumerate(ys):
            if d.y1 - m <= y <= d.y0 + m:
                xo = d.section(min(max(y, d.y1), d.y0))[1]
                occ[i] |= xs < xo + m
    for b in BOOMS:
        occ |= (np.abs(X - b["x"]) < b["r"] + m) & (Y <= b["y0"] + m) & (Y >= b["y1"] - m)
    for p in SHELVES:
        occ |= (X <= p["x1"] + m) & (Y <= p["y0"] + m) & (Y >= p["y1"] - m)
    return occ, step


def _place_islands():
    """Two free rectangles in the top / bottom strips for the outer faces of the fin(s)."""
    global FIN_ISLAND_SCALE, FIN_ISLANDS
    if FIN is None:
        FIN_ISLANDS, FIN_ISLAND_SCALE = {1.0: (0.0, 0.0), -1.0: (0.0, 0.0)}, 1.0
        return
    occ, step = _occupancy()
    nu, nx = occ.shape
    strips = []
    for v0 in (V_TOP, V_BOT):                    # each strip has its own free cells
        strips.append((v0, occ.copy()))
    L0, H0 = FIN_YMAX - FIN_YMIN + 0.1, FIN.s1 - FIN.s0 + 0.1
    for k in np.arange(1.0, 0.3, -0.05):
        w, h = int(math.ceil(L0 * k / step)) + 2, int(math.ceil(H0 * k / step)) + 2
        if w >= nu or h >= nx:
            continue
        found = []
        grids = [(v0, g.copy()) for v0, g in strips]
        for _sign in (1.0, -1.0):
            ok = False
            for gi, (v0, g) in enumerate(grids):
                # summed area table: a w x h window with no occupied cell
                sat = np.pad(g.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
                win = sat[w:, h:] - sat[:-w, h:] - sat[w:, :-h] + sat[:-w, :-h]
                free = np.argwhere(win == 0)
                if len(free):
                    i, j = free[np.argmin(free[:, 1] * 10000 + free[:, 0])]
                    g[i:i + w, j:j + h] = True
                    found.append((YA0 + (i + 1) * step - YA0, v0 + (j + 1) * step))
                    ok = True
                    break
            if not ok:
                break
        if len(found) == 2:
            FIN_ISLAND_SCALE = float(k)
            FIN_ISLANDS = {1.0: found[0], -1.0: found[1]}
            return
    raise RuntimeError("no room for the fin islands in the atlas")


# ------------------------------------------------------------------ configure
def configure(cfg):
    g = globals()
    CFG.clear()
    CFG.update(cfg)
    g["NAME"] = cfg["name"]
    g["Y_NOSE"] = cfg["y_nose"]
    g["Y_RADOME"] = cfg.get("y_radome", cfg["y_nose"] - 2.0)
    g["Z_GROUND"] = cfg["z_ground"]
    body = cfg["body"]
    g["BODY"] = [Curve([(r[0], r[c]) for r in body]) for c in range(1, 7)]
    g["Y_BODY_END"] = min(r[0] for r in body)
    g["NOSE_Z"] = body[0][6] if body[0][0] == max(r[0] for r in body) else 0.0
    w = cfg["wing"]
    g["X_ROOT"], g["X_TIP"] = w["le"][0][0], w["le"][-1][0]
    g["WLE"], g["WTE"] = Lin(w["le"]), Lin(w["te"])
    g["Z_WING"] = w["z"]
    g["DIHEDRAL"] = math.radians(w.get("dihedral", 0.0))
    g["T_ROOT"], g["T_TIP"] = w.get("t", (0.05, 0.035))
    g["FLAP"], g["AIL"] = w["flap"], w["ail"]
    g["X_FLAP"], g["X_AIL"] = w["flap"][1], w["ail"][1]
    g["LEF"] = w.get("lef")                        # (x0, x1, chord fraction) or None
    g["WING_KINKS"] = sorted(set([p[0] for p in w["le"]] + [p[0] for p in w["te"]]))
    g["Y_KINK"] = float(wing_le(X_ROOT))
    g["WING_TE"] = float(wing_te(X_ROOT))
    x1 = w["le"][1][0]
    g["TAN_LE0"] = max((float(wing_le(X_ROOT)) - float(wing_le(x1))) / (x1 - X_ROOT), 0.2)
    g["WING_BLADE"] = cfg.get("wing_blade", True)
    ch = cfg.get("chine")
    if ch:
        g["CHINE"] = Curve([(r[0], r[1]) for r in ch] + [(Y_KINK, X_ROOT)])
        g["CHINE_Z"] = Curve([(r[0], r[2]) for r in ch] + [(Y_KINK, float(wing_z(X_ROOT)))])
        g["Y_CHINE0"] = max(r[0] for r in ch)
    else:
        g["CHINE"], g["CHINE_Z"] = None, None
        g["Y_CHINE0"] = Y_KINK + 0.9
    g["CHINE_T"] = cfg.get("chine_t", 0.04)
    k = cfg.get("fillet", {})
    g["K_UP"] = _curve(k.get("up", [(Y_KINK, 0.06), (0.5 * (Y_KINK + WING_TE), 0.18), (WING_TE, 0.20)]))
    g["K_LO"] = _curve(k.get("lo", [(Y_KINK, 0.04), (WING_TE, 0.10)]))
    c = cfg["canopy"]
    rows = c["table"]
    g["CANOPY_W"] = Curve([(r[0], r[1]) for r in rows])
    g["CANOPY_H"] = Curve([(r[0], r[2]) for r in rows])
    g["CANOPY_Y0"], g["CANOPY_Y1"] = min(r[0] for r in rows), max(r[0] for r in rows)
    g["ARCHES"] = c.get("arches", [])
    g["WINDSCREEN_ARCH"] = (c.get("arches") or [CANOPY_Y1 - 0.6])[0]
    g["CANOPY_TINT"] = c.get("tint", (0.40, 0.36, 0.20))
    ck = cfg["cockpit"]
    g["SEATS"] = ck["seats"]
    g["COCKPIT_W"] = ck.get("w", 0.40)
    g["COCKPIT_Y1"] = ck.get("y1", WINDSCREEN_ARCH - 0.08)
    g["COCKPIT_Y0"] = ck.get("y0", min(SEATS) - 0.40)
    g["DUCTS"] = [Duct(d) for d in cfg.get("ducts", [])]
    g["BOOMS"] = cfg.get("booms", [])
    g["SHELVES"] = cfg.get("shelves", [])
    g["STAB"] = Surface(cfg["stab"]) if cfg.get("stab") else None
    g["CANARD"] = Surface(dict(cfg["canard"], canard=True)) if cfg.get("canard") else None
    g["SURFACES"] = [s for s in (STAB, CANARD) if s is not None]
    fins = cfg.get("fins", [])
    g["FINS"] = [Fin(f) for f in fins]
    g["FIN"] = FINS[0] if FINS else None
    g["VENTRALS"] = [Fin(f) for f in cfg.get("ventrals", [])]
    g["NOZZLES"] = cfg.get("nozzles", [])
    if FIN is not None:
        g["FIN_YMIN"], g["FIN_YMAX"] = FIN.y_range()
        g["FIN_X"], g["FIN_ZROOT"], g["FIN_CANT"] = FIN.x, FIN.zroot, FIN.cant
        g["FIN_S0"], g["FIN_S1"] = FIN.s0, FIN.s1
    # atlas: top strip (|x| 0..HALF), bottom strip (HALF..2 HALF), side strip (z + V_SIDE) above them
    g["HALF"] = max(X_TIP, max([s.x1 for s in SURFACES] + [0.0])) + 0.15
    zmin = min([r[2] for r in body] + [min(r[4] for r in d.d["table"]) for d in DUCTS]) - 0.15
    zmax = max(r[1] for r in body) + max(r[2] for r in rows) + 0.15
    for f in FINS + VENTRALS:
        tip = f.zroot + f.s1 * math.cos(f.cant)
        if f.twin or f in VENTRALS:
            zmin, zmax = min(zmin, tip - 0.15), max(zmax, tip + 0.15)
    zmin, zmax = cfg.get("side_z", (zmin, zmax))
    g["V_TOP"], g["V_BOT"] = 0.0, HALF
    g["V_SIDE"] = 2.0 * HALF + 0.1 - zmin
    ymin = min(Y_BODY_END, min([n["y0"] - n["len"] for n in NOZZLES] + [Y_BODY_END]),
               min([s.te1 for s in SURFACES] + [Y_BODY_END]), (FIN_YMIN if FIN is not None else Y_BODY_END))
    length = Y_NOSE - ymin + 0.5
    g["ATLAS"] = max(length, 2.0 * HALF + 0.1 + (zmax - zmin) + 0.1)
    g["YA0"] = ymin - 0.25
    g["ZMAX_SIDE"] = ATLAS - V_SIDE
    g["DECALS"] = ()
    _place_islands()
    g["NOSE_WELL"] = None
    g["MAIN_WELL"] = None
    return g


def summary():
    return ("%s: atlas %.1f m (%.0f px/m), half span %.2f, side z %.2f..%.2f, fin islands %s x %.2f"
            % (NAME, ATLAS, 4096 / ATLAS, HALF, -V_SIDE + 2 * HALF + 0.1, ZMAX_SIDE,
               {k: (round(v[0], 2), round(v[1], 2)) for k, v in FIN_ISLANDS.items()}, FIN_ISLAND_SCALE))
