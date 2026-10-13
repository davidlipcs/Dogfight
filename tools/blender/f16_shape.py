"""Shape tables and section maths of the Blender F-16C (pure numpy).

Shared by the mesh builder (build_f16.py) and the texture painter (f16_paint.py), so the painted
panel lines always sit on the geometry.

Model frame: +Y forward, +X right, +Z up, metres.  The origin is the centre of gravity (35 % MAC),
the wing chord plane is z = 0 and the ground is at Z_GROUND with the gear down.
Real dimensions: 15.03 m long with the pitot, 9.45 m span over the tip launchers, 5.09 m high.
"""

import math

import numpy as np

TAN40 = math.tan(math.radians(40.0))

Y_NOSE = 8.54            # radome tip (the pitot adds 0.5 m)
Y_RADOME = 6.94          # radome / fuselage joint
Y_BODY_END = -5.02       # the nozzle starts here
Y_NOZZLE = -5.98         # nozzle exit plane
Z_NOZZLE = -0.10
Z_GROUND = -1.75

# ------------------------------------------------------------------ wing
WING_APEX = 2.72         # leading edge at the centre line (theoretical wing)
WING_TE = -2.25          # unswept trailing edge
X_ROOT = 1.30            # the wing mesh starts here; inboard of it the wing is part of the body
X_TIP = 4.60
X_FLAP = 3.22            # outboard end of the flaperon
WING_T = 0.04            # NACA 64A204: 4 % thick


def wing_le(x):
    return WING_APEX - np.abs(x) * TAN40


def wing_chord(x):
    return wing_le(x) - WING_TE


def lef_chord(x):
    """Chord of the leading edge flap."""
    return 0.46 + (0.24 - 0.46) * (np.abs(x) - X_ROOT) / (X_TIP - X_ROOT)


def flap_chord(x):
    """Chord of the flaperon."""
    return 0.78 + (0.60 - 0.78) * (np.abs(x) - X_ROOT) / (X_FLAP - X_ROOT)


Y_KINK = float(wing_le(X_ROOT))      # where the strake meets the wing leading edge
Y_STRAKE0 = 5.60                     # the strake grows out of the forebody here

# ------------------------------------------------------- aft body, tail surfaces
X_SHELF = 1.07           # half width of the shelf that carries the stabilators and speed brakes
Z_SHELF = -0.03
SHELF_H = 0.12           # half thickness
Y_SB0 = -4.55            # speed brake hinge line: the fixed shelf ends here
Y_SB1 = -5.62
X_SB0 = 0.66             # inboard edge of the speed brakes

STAB_X0, STAB_X1 = 1.10, 2.79
STAB_LE0, STAB_TE0 = -3.20, -5.75
STAB_LE1, STAB_TE1 = STAB_LE0 - (STAB_X1 - STAB_X0) * TAN40, -5.57
STAB_Z0 = -0.02
STAB_ANHEDRAL = math.radians(10.0)
STAB_PIVOT = -4.72

FIN_Z0, FIN_ZB, FIN_Z1 = 0.50, 0.60, 3.30
FIN_SWEEP = math.tan(math.radians(47.5))
RUD_Z0, RUD_Z1 = 1.02, 3.02


# the left side of the fin gets its own island in the texture atlas (atlas metres, see f16_paint.py)
FINL_U0, FINL_V0, FINL_Y1, FINL_Z0, FINL_SCALE = 7.70, 2.52, -0.20, 0.45, 0.85


def fin_le(z):
    return -1.48 - (z - FIN_ZB) * FIN_SWEEP


def fin_te(z):
    return -4.23 - (z - FIN_ZB) * (1.20 / 2.75)


def rudder_chord(z):
    return 0.78 + (0.46 - 0.78) * (z - RUD_Z0) / (RUD_Z1 - RUD_Z0)


def stab_le(x):
    return STAB_LE0 + (STAB_LE1 - STAB_LE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_te(x):
    return STAB_TE0 + (STAB_TE1 - STAB_TE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_z(x):
    return STAB_Z0 - (np.abs(x) - STAB_X0) * math.tan(STAB_ANHEDRAL)


# ----------------------------------------------------------------- helpers
class Curve:
    """Monotone cubic (PCHIP) through (x, y) points; clamps outside the table."""

    def __init__(self, pts):
        pts = sorted(pts)
        self.x = np.array([p[0] for p in pts], float)
        self.y = np.array([p[1] for p in pts], float)
        h = np.diff(self.x)
        d = np.diff(self.y) / h
        m = np.zeros_like(self.x)
        m[0], m[-1] = d[0], d[-1]
        for i in range(1, len(self.x) - 1):
            if d[i - 1] * d[i] > 0.0:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        self.m = m

    def __call__(self, t):
        t = np.clip(np.asarray(t, float), self.x[0], self.x[-1])
        i = np.clip(np.searchsorted(self.x, t, side="right") - 1, 0, len(self.x) - 2)
        h = self.x[i + 1] - self.x[i]
        s = (t - self.x[i]) / h
        s2, s3 = s * s, s * s * s
        return ((2 * s3 - 3 * s2 + 1) * self.y[i] + (s3 - 2 * s2 + s) * h * self.m[i]
                + (-2 * s3 + 3 * s2) * self.y[i + 1] + (s3 - s2) * h * self.m[i + 1])


def smoothstep(e0, e1, v):
    t = np.clip((np.asarray(v, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smin(a, b, k):
    """Polynomial smooth minimum: a fillet of width ~k where the two shapes meet."""
    k = np.maximum(k, 1e-4)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def yt(s, t=WING_T):
    """Half thickness of a NACA 4-digit style section with a closed trailing edge (chord = 1)."""
    s = np.clip(s, 0.0, 1.0)
    return 5.0 * t * (0.2969 * np.sqrt(s) - 0.1260 * s - 0.3516 * s ** 2 + 0.2843 * s ** 3 - 0.1036 * s ** 4)


# ------------------------------------------------------------- body tables
#    y,    top,   bottom, half width, n upper, n lower, z of the widest point
_BODY = (
    (8.54, 0.123, 0.117, 0.004, 2.00, 2.00, 0.120),
    (8.47, 0.186, 0.060, 0.063, 2.00, 2.00, 0.123),
    (8.34, 0.250, 0.008, 0.121, 2.00, 2.00, 0.129),
    (8.14, 0.322, -0.052, 0.187, 2.00, 2.00, 0.135),
    (7.84, 0.402, -0.120, 0.261, 2.00, 2.00, 0.141),
    (7.54, 0.462, -0.172, 0.318, 2.00, 2.00, 0.145),
    (7.24, 0.508, -0.214, 0.364, 2.00, 2.00, 0.147),
    (6.94, 0.545, -0.246, 0.400, 2.00, 2.02, 0.149),
    (6.50, 0.588, -0.262, 0.446, 2.08, 2.10, 0.150),
    (6.00, 0.628, -0.255, 0.488, 2.15, 2.30, 0.140),
    (5.50, 0.658, -0.225, 0.520, 2.22, 2.55, 0.120),
    (5.00, 0.684, -0.192, 0.548, 2.30, 2.90, 0.090),
    (4.40, 0.704, -0.165, 0.580, 2.40, 3.20, 0.055),
    (3.60, 0.735, -0.400, 0.640, 2.30, 3.00, 0.020),
    (2.80, 0.900, -0.660, 0.740, 1.95, 3.10, 0.000),
    (2.40, 0.955, -0.740, 0.800, 1.80, 3.20, 0.000),
    (1.60, 0.880, -0.800, 0.870, 1.75, 3.25, 0.000),
    (0.80, 0.800, -0.820, 0.930, 1.75, 3.30, 0.000),
    (0.00, 0.730, -0.820, 0.950, 1.75, 3.30, -0.002),
    (-1.00, 0.670, -0.810, 0.930, 1.78, 3.20, -0.010),
    (-2.00, 0.620, -0.790, 0.870, 1.82, 3.00, -0.020),
    (-3.00, 0.575, -0.760, 0.770, 1.90, 2.60, -0.040),
    (-3.80, 0.545, -0.740, 0.695, 1.96, 2.20, -0.070),
    (-4.55, 0.525, -0.725, 0.640, 2.00, 2.00, -0.100),
    (-5.02, 0.490, -0.690, 0.590, 2.00, 2.00, -0.100),
)
BODY = [Curve([(r[0], r[c]) for r in _BODY]) for c in range(1, 7)]

STRAKE = Curve([(Y_KINK, X_ROOT), (1.90, 1.205), (2.20, 1.110), (2.60, 1.005), (3.20, 0.885), (3.80, 0.780),
                (4.40, 0.685), (5.00, 0.600), (Y_STRAKE0, 0.520)])
K_UP = Curve([(Y_STRAKE0, 0.04), (5.0, 0.12), (4.0, 0.22), (3.0, 0.32), (1.6, 0.42), (0.0, 0.45), (WING_TE, 0.40)])
K_LO = Curve([(Y_STRAKE0, 0.03), (4.4, 0.08), (3.0, 0.12), (1.6, 0.16), (WING_TE, 0.16)])
K_SHELF = 0.10

#   y, half width, height above the sill
_CANOPY = ((5.84, 0.02, 0.005), (5.72, 0.16, 0.075), (5.50, 0.275, 0.21), (5.20, 0.365, 0.38), (4.90, 0.42, 0.53),
           (4.50, 0.455, 0.66), (4.10, 0.468, 0.725), (3.70, 0.462, 0.72), (3.40, 0.45, 0.68), (3.10, 0.42, 0.57),
           (2.80, 0.37, 0.41), (2.55, 0.31, 0.24), (2.40, 0.25, 0.11), (2.30, 0.14, 0.02))
CANOPY_W = Curve([(r[0], r[1]) for r in _CANOPY])
CANOPY_H = Curve([(r[0], r[2]) for r in _CANOPY])
CANOPY_Y0, CANOPY_Y1 = _CANOPY[-1][0], _CANOPY[0][0]
CANOPY_BOW = 3.40                    # frame between the moving canopy and the fixed aft glass
COCKPIT_Y0, COCKPIT_Y1 = 3.52, 5.22  # the opening in the skin
COCKPIT_W = 0.31

#   y, half width, top, bottom of the intake trunk
_INTAKE = ((4.39, 0.565, -0.245, -0.875), (4.20, 0.585, -0.235, -0.890), (3.80, 0.610, -0.220, -0.895),
           (3.20, 0.650, -0.200, -0.890), (2.60, 0.710, -0.200, -0.870), (2.00, 0.770, -0.200, -0.845),
           (1.60, 0.800, -0.200, -0.815), (1.00, 0.800, -0.200, -0.780))
INTAKE = [Curve([(r[0], r[c]) for r in _INTAKE]) for c in range(1, 4)]
Y_INTAKE = _INTAKE[0][0]
INTAKE_RAKE = 0.38                   # the upper lip sits further forward than the lower one


def shelf_half_thickness(y):
    if y < Y_SB0:
        return 0.0
    return SHELF_H * float(smoothstep(0.3, -1.5, y))


def blade_z(y):
    """Height of the strake / wing plane."""
    return float(BODY[5](y)) if y > 0.8 else 0.0


class Section:
    """Implicit cross section F(x, z) < 0 of the blended body at station y: the superellipse core,
    the strake / inboard wing blade and the aft shelf, joined with fillets."""

    def __init__(self, y, blade=True, shelf=True):
        self.y = float(y)
        self.zt, self.zb, self.hw, self.nu, self.nl, self.zc = (float(c(y)) for c in BODY)
        self.core = min(self.hw, self.zt - self.zc, self.zc - self.zb)
        self.xlim = None
        self.z0 = self.zc
        self.ghost = 0.0
        if blade and WING_TE - 1.2 < y <= WING_TE:
            # behind the trailing edge the wing root fillet fades out instead of ending in a step
            self.ghost = float(smoothstep(WING_TE - 1.2, WING_TE, y))
            self.ku, self.kl = float(K_UP(WING_TE)) * self.ghost, float(K_LO(WING_TE)) * self.ghost
        if blade and WING_TE < y <= Y_STRAKE0:
            self.xlim = float(STRAKE(y)) if y >= Y_KINK else X_ROOT
            self.z0 = blade_z(y)
            self.ku, self.kl = float(K_UP(y)), float(K_LO(y))
            if y >= Y_KINK:
                self.edge, self.fade = self.xlim, 1.0
            else:                                    # the sharp strake edge fades into the wing nose
                self.edge = (WING_APEX - y) / TAN40
                self.fade = max(0.0, 1.0 - (Y_KINK - y) / 0.9)
        self.hs = shelf_half_thickness(y) if shelf else 0.0

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
            tau = np.where((s > 0.0) & (s < 1.0), yt(s) * c, -1.0)
            if self.fade > 0.0:
                tau = np.maximum(tau, np.minimum((self.edge - ax) * 0.16, 0.05) * self.fade)
            fb = np.maximum(np.abs(z - self.z0) - tau, ax - self.xlim)
            f = smin(f, fb, np.where(z >= self.z0, self.ku, self.kl))
        if self.ghost > 0.0:
            fb = np.maximum(np.abs(z) + 0.002, ax - X_ROOT)
            f = smin(f, fb, np.where(z >= 0.0, self.ku, self.kl))
        if self.hs > 0.004:
            r = min(0.035, self.hs * 0.6)
            qx = ax - (X_SHELF - r)
            qz = np.abs(z - Z_SHELF) - (self.hs - r)
            fs = np.hypot(np.maximum(qx, 0.0), np.maximum(qz, 0.0)) + np.minimum(np.maximum(qx, qz), 0.0) - r
            f = smin(f, fs, K_SHELF)
        return f

    # ------------------------------------------------------------------
    def _exit(self, cos, sin, rcap, nr=260, iters=30):
        """First point where each ray from (0, z0) leaves the section."""
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

    def _vertical(self, x, direction, reach=1.8, iters=40):
        """Surface height above (direction = 1) or below (-1) the points (x, z0)."""
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

    def half_ring(self, n_up=44, n_cut=2, n_lo=40, dense=360):
        """Points (x >= 0, z) from the top centre down to the bottom centre: the upper skin, the cut
        face at the wing root (a single point where the edge is sharp) and the lower skin, each with
        a fixed number of segments so that all rings loft into one grid."""
        rmax = 1.3 * max(self.hw, self.zt - self.zb, self.xlim or 0.0, X_SHELF if self.hs else 0.0) + 0.3
        cap0 = rmax if self.xlim is None else min(rmax, self.xlim - 1e-6)
        r0 = float(self._exit(np.array([1.0]), np.array([0.0]), np.array([cap0]))[0])
        if self.xlim is not None and r0 >= cap0 - 1e-5:
            xe = cap0
            zu, zl = float(self.top(xe)[0]), float(self.bottom(xe)[0])
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


def resample(pts, n):
    """n segments of equal arc length along a polyline."""
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] < 1e-9:
        return np.repeat(pts[:1], n + 1, axis=0)
    t = np.linspace(0.0, s[-1], n + 1)
    return np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], axis=1)


def body_top(y, x):
    """Height of the upper skin at station y, lateral offset(s) x."""
    return Section(y).top(x)


def body_bottom(y, x):
    return Section(y).bottom(x)


def canopy_sill(y):
    """(half width, z) of the canopy base at station y."""
    w = float(CANOPY_W(y))
    return w, float(body_top(y, w)[0]) - 0.012
