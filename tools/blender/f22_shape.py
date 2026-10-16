"""Shape tables and section maths of the Blender F-22A Raptor (pure numpy).

Shared by the mesh builder (build_f22.py) and the texture painter (f22_paint.py).

Model frame: +Y forward, +X right, +Z up, metres; origin near the centre of gravity, ground at Z_GROUND with
the gear down.  Real dimensions: 18.92 m long (nose to stabilator tips), 13.56 m span, 5.08 m high, 78 m^2
wing.  Diamond wing (leading edge swept 42 degrees, trailing edge swept forward 17), chined forebody, caret
inlets, twin tails canted 28 degrees, two-dimensional thrust vectoring nozzles, three internal weapons bays.
"""

import math

import numpy as np

from f16_shape import Curve, resample, smin, smoothstep, yt   # the same maths as the F-16

Y_NOSE = 9.62
Y_RADOME = 7.60
Y_BODY_END = -7.95        # the nozzles start here
Y_NOZZLE = -8.85          # nozzle exit
X_NOZZLE, Z_NOZZLE = 0.66, 0.02
NOZZLE_W, NOZZLE_H = 0.50, 0.30          # half width / half height of the rectangular exit
Z_GROUND = -1.78

# ------------------------------------------------------------------ wing
TAN_LE = math.tan(math.radians(42.0))
TAN_TE = math.tan(math.radians(17.0))
WING_APEX = 4.59          # leading edge of the theoretical wing at the centre line
WING_TE0 = -5.50          # trailing edge at the centre line (swept forward outboard)
X_ROOT = 1.70             # the wing mesh starts at the body side
X_TIP = 6.78
X_FLAP = 4.05             # flaperon outboard end = aileron inboard end
X_AIL = 6.25
DIHEDRAL = math.radians(-3.25)
Z_WING = 0.30


def wing_le(x):
    return WING_APEX - np.abs(x) * TAN_LE


def wing_te(x):
    return WING_TE0 + np.abs(x) * TAN_TE


def wing_chord(x):
    return wing_le(x) - wing_te(x)


def wing_z(x):
    return Z_WING + np.abs(x) * math.tan(DIHEDRAL)


def wing_t(x):
    """Thickness ratio: 5.9 % at the root, 4.3 % at the tip."""
    return 0.059 + (0.043 - 0.059) * np.clip((np.abs(x) - X_ROOT) / (X_TIP - X_ROOT), 0.0, 1.0)


def lef_chord(x):
    return 0.55 + (0.28 - 0.55) * (np.abs(x) - X_ROOT) / (X_TIP - X_ROOT)


def flap_chord(x):
    return 1.00 + (0.80 - 1.00) * (np.abs(x) - X_ROOT) / (X_FLAP - X_ROOT)


def ail_chord(x):
    return 0.70 + (0.50 - 0.70) * (np.abs(x) - X_FLAP) / (X_AIL - X_FLAP)


Y_KINK = float(wing_le(X_ROOT))       # 3.06: where the chine meets the wing leading edge (over the inlet)
WING_TE = float(wing_te(X_ROOT))      # -4.98: the wing trailing edge at the body side
Y_CHINE0 = 9.40                       # the chine starts at the nose tip

# ---------------------------------------------------------------- tail surfaces
STAB_X0, STAB_X1 = 1.32, 4.40
STAB_LE0, STAB_TE0 = -5.25, -9.30
STAB_LE1 = STAB_LE0 - (STAB_X1 - STAB_X0) * TAN_LE
STAB_TE1 = STAB_TE0 + (STAB_X1 - STAB_X0) * math.tan(math.radians(10.0))
STAB_Z0 = 0.02
STAB_ANHEDRAL = math.radians(0.0)
STAB_PIVOT = -7.20


def stab_le(x):
    return STAB_LE0 + (STAB_LE1 - STAB_LE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_te(x):
    return STAB_TE0 + (STAB_TE1 - STAB_TE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_z(x):
    return STAB_Z0 - (np.abs(x) - STAB_X0) * math.tan(STAB_ANHEDRAL)


# twin tails canted 28 degrees outwards; s = distance up the fin from its root
FIN_X, FIN_ZROOT, FIN_CANT = 1.42, 0.52, math.radians(28.0)
FIN_S0, FIN_S1 = -0.10, 2.65
FIN_LE0, FIN_TE0 = -4.55, -8.15
FIN_SWEEP = math.tan(math.radians(23.0))
FIN_TE_SWEEP = math.tan(math.radians(-27.0))      # the trailing edge is swept forward
RUD_S0, RUD_S1 = 0.12, 1.55


def fin_le(s):
    return FIN_LE0 - s * FIN_SWEEP


def fin_te(s):
    return FIN_TE0 - s * FIN_TE_SWEEP


def rudder_chord(s):
    return 0.95 + (0.75 - 0.95) * (s - RUD_S0) / (RUD_S1 - RUD_S0)


# ------------------------------------------------------------------ body tables
# flat sided, chined forebody; the inlet trunks join the body behind the inlets
#    y,     top,   bottom, half width, n upper, n lower, z of the widest point
_BODY = (
    (9.62, 0.135, 0.115, 0.004, 1.6, 1.6, 0.125),
    (9.45, 0.205, 0.045, 0.080, 1.6, 1.6, 0.125),
    (9.10, 0.315, -0.060, 0.175, 1.6, 1.7, 0.130),
    (8.50, 0.465, -0.190, 0.290, 1.6, 1.8, 0.140),
    (7.70, 0.625, -0.320, 0.400, 1.7, 1.9, 0.150),
    (6.90, 0.770, -0.420, 0.470, 1.8, 2.0, 0.160),
    (6.10, 0.890, -0.500, 0.520, 1.9, 2.1, 0.170),
    (5.20, 0.960, -0.570, 0.555, 2.0, 2.2, 0.180),
    (4.30, 0.990, -0.650, 0.580, 2.0, 2.4, 0.190),
    (3.50, 0.990, -0.730, 0.610, 2.0, 2.6, 0.200),
    (3.00, 0.985, -0.780, 0.650, 2.1, 2.8, 0.200),
    (2.40, 0.975, -0.830, 0.800, 2.2, 3.0, 0.200),
    (1.60, 0.955, -0.860, 1.100, 2.3, 3.2, 0.200),
    (0.80, 0.930, -0.870, 1.400, 2.4, 3.4, 0.200),
    (0.00, 0.900, -0.870, 1.580, 2.5, 3.4, 0.200),
    (-1.50, 0.850, -0.860, 1.640, 2.5, 3.4, 0.190),
    (-3.00, 0.790, -0.830, 1.620, 2.6, 3.2, 0.170),
    (-4.50, 0.700, -0.760, 1.540, 2.6, 3.0, 0.140),
    (-6.00, 0.590, -0.650, 1.420, 2.8, 2.8, 0.110),
    (-7.10, 0.470, -0.540, 1.330, 3.0, 2.8, 0.080),
    (-7.95, 0.360, -0.420, 1.240, 3.2, 3.0, 0.050),
)
BODY = [Curve([(r[0], r[c]) for r in _BODY]) for c in range(1, 7)]

# the chine: half width of its sharp edge and its height, from the nose tip to the wing leading edge
CHINE = Curve([(Y_KINK, X_ROOT), (3.50, 1.06), (4.20, 0.90), (5.00, 0.82), (6.00, 0.74), (6.80, 0.66), (7.60, 0.56),
               (8.40, 0.42), (9.00, 0.28), (Y_CHINE0, 0.12)])
CHINE_Z = Curve([(Y_KINK, float(wing_z(X_ROOT))), (4.0, 0.195), (6.0, 0.17), (8.0, 0.14), (Y_CHINE0, 0.125)])
K_UP = Curve([(Y_CHINE0, 0.015), (7.0, 0.025), (4.5, 0.05), (Y_KINK, 0.10), (0.0, 0.30), (WING_TE, 0.32)])
K_LO = Curve([(Y_CHINE0, 0.015), (7.0, 0.02), (4.5, 0.035), (Y_KINK, 0.06), (WING_TE, 0.14)])

#   y, half width, height above the sill: the frameless one piece bubble canopy
_CANOPY = ((6.25, 0.03, 0.01), (6.05, 0.23, 0.17), (5.80, 0.35, 0.38), (5.45, 0.42, 0.58), (5.00, 0.455, 0.72),
           (4.50, 0.465, 0.79), (4.00, 0.46, 0.79), (3.50, 0.44, 0.71), (3.05, 0.39, 0.56), (2.65, 0.31, 0.36),
           (2.35, 0.21, 0.17), (2.15, 0.10, 0.03))
CANOPY_W = Curve([(r[0], r[1]) for r in _CANOPY])
CANOPY_H = Curve([(r[0], r[2]) for r in _CANOPY])
CANOPY_Y0, CANOPY_Y1 = _CANOPY[-1][0], _CANOPY[0][0]
COCKPIT_Y0, COCKPIT_Y1 = 3.20, 5.45
COCKPIT_W = 0.41

# caret inlets under the chine: (y, inner x, outer x, top, bottom)
_INTAKE = ((3.05, 0.66, 1.50, 0.12, -0.72), (2.70, 0.66, 1.50, 0.12, -0.74), (2.20, 0.68, 1.52, 0.11, -0.77),
           (1.60, 0.70, 1.54, 0.10, -0.79), (1.00, 0.72, 1.56, 0.08, -0.80), (0.20, 0.74, 1.57, 0.06, -0.80))
INTAKE = [Curve([(r[0], r[c]) for r in _INTAKE]) for c in range(1, 5)]
Y_INTAKE = _INTAKE[0][0]
INTAKE_SHEAR = 0.22        # the inlet face leans: its top edge sits further out than the bottom
INTAKE_RAKE_Z, INTAKE_RAKE_X = 0.30, -0.55     # the face is raked: top forward, outer edge aft

# landing gear wells (x0, x1, y0, y1): the nose gear folds forwards, the main gears forwards and inwards
NOSE_WELL = (-0.25, 0.25, 5.20, 6.85)
MAIN_WELL = (0.95, 1.42, -3.40, -1.40)

# internal weapons bays (x0, x1, y0, y1): the main bay under the belly, a side bay in each inlet trunk
MAIN_BAY = (-0.80, 0.80, -2.75, 1.25)
SIDE_BAY = (1.06, 1.40, -0.10, 2.40)           # right side; lower outer corner of the trunk
BAY_ROOF = -0.30


def blade_z(y):
    return float(CHINE_Z(y)) if y > Y_KINK else float(wing_z(X_ROOT))


class Section:
    """Implicit cross section F(x, z) < 0 at station y: superellipse core plus the chine / inboard wing blade,
    joined with fillets (same idea as the F-16 and the Super Hornet)."""

    def __init__(self, y, blade=True):
        self.y = float(y)
        self.zt, self.zb, self.hw, self.nu, self.nl, self.zc = (float(c(y)) for c in BODY)
        self.core = min(self.hw, self.zt - self.zc, self.zc - self.zb)
        self.xlim = None
        self.z0 = self.zc
        self.ghost = 0.0
        if blade and WING_TE - 1.4 < y <= WING_TE:
            self.ghost = float(smoothstep(WING_TE - 1.4, WING_TE, y))
            self.ku, self.kl = float(K_UP(WING_TE)) * self.ghost, float(K_LO(WING_TE)) * self.ghost
            self.z0 = blade_z(WING_TE)
        if blade and WING_TE < y <= Y_CHINE0:
            self.xlim = float(CHINE(y)) if y >= Y_KINK else X_ROOT
            self.z0 = blade_z(y)
            self.ku, self.kl = float(K_UP(y)), float(K_LO(y))
            if y >= Y_KINK:
                self.edge, self.fade = self.xlim, 1.0
            else:
                self.edge = (WING_APEX - y) / TAN_LE
                self.fade = max(0.0, 1.0 - (Y_KINK - y) / 1.0)

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
                tau = np.maximum(tau, np.minimum((self.edge - ax) * 0.10, 0.04) * self.fade)
            fb = np.maximum(np.abs(z - self.z0) - tau, ax - self.xlim)
            f = smin(f, fb, np.where(z >= self.z0, self.ku, self.kl))
        if self.ghost > 0.0:
            fb = np.maximum(np.abs(z - self.z0) + 0.002, ax - X_ROOT)
            f = smin(f, fb, np.where(z >= self.z0, self.ku, self.kl))
        return f

    def _exit(self, cos, sin, rcap, nr=280, iters=30):
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

    def _vertical(self, x, direction, reach=2.2, iters=40):
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

    def half_ring(self, n_up=48, n_cut=2, n_lo=44, dense=380):
        rmax = 1.3 * max(self.hw, self.zt - self.zb, self.xlim or 0.0) + 0.3
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


def body_top(y, x):
    return Section(y).top(x)


def body_bottom(y, x):
    return Section(y).bottom(x)


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


# texture atlas (atlas metres, see f22_paint.py): 20 m x 20 m
ATLAS = 20.0
YA0 = -9.8
V_TOP, V_BOT, V_SIDE = 0.0, 7.0, 16.5       # strips: top (|x| 0..7), bottom (7..14), side (z + V_SIDE: 14..20)
FIN_ISLANDS = {1.0: (12.9, 3.5), -1.0: (16.3, 3.5)}
FIN_ISLAND_SCALE = 0.90
DECALS = ()

FIN_YMIN, FIN_YMAX = -8.20, -4.50


def fin_span_dir(sign):
    return np.array([sign * math.sin(FIN_CANT), 0.0, math.cos(FIN_CANT)])


def fin_normal(sign):
    """Outward normal of the fin plane on the side `sign` (1 = right fin)."""
    return np.array([sign * math.cos(FIN_CANT), 0.0, -math.sin(FIN_CANT)])


def fin_s(x, z):
    return (np.abs(x) - FIN_X) * math.sin(FIN_CANT) + (z - FIN_ZROOT) * math.cos(FIN_CANT)


def fin_island(y, s, sign):
    u0, v0 = FIN_ISLANDS[sign]
    k = FIN_ISLAND_SCALE
    u = u0 + ((np.asarray(y) - FIN_YMIN) if sign > 0 else (FIN_YMAX - np.asarray(y))) * k
    return u, v0 + (np.asarray(s) - FIN_S0) * k


def intake_section(y):
    """(inner x, outer x, top, bottom) of the right inlet trunk at station y."""
    return tuple(float(c(y)) for c in INTAKE)


def intake_bottom(y, x):
    xi, xo, zt, zb = intake_section(y)
    cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
    cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
    t = min(abs(abs(x) - cx) / hw, 1.0)
    return cz - hh * max(0.0, 1.0 - t ** 3.0) ** (1.0 / 3.0)
