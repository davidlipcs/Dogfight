"""Shape tables and section maths of the Blender F-15EX Eagle II (pure numpy).

Shared by the mesh builder (build_f15.py) and the texture painter (f15_paint.py).

Model frame: +Y forward, +X right, +Z up, metres; origin near the centre of gravity, ground at Z_GROUND with
the gear down.  Real dimensions: 19.43 m long, 13.05 m span, 5.63 m high, 56.5 m^2 wing.  Shoulder mounted
cropped delta wing (leading edge 45 degrees), big rectangular side inlets, conformal fuel tanks along the inlet
trunks, twin vertical tails on tail booms, all moving stabilators, two F110 engines, tandem two seat cockpit.
"""

import math

import numpy as np

from f16_shape import Curve, resample, smin, smoothstep, yt   # the same maths as the F-16

Y_NOSE = 9.90
Y_RADOME = 7.90
Y_BODY_END = -7.70        # the nozzles start here
Y_NOZZLE = -8.60          # nozzle exit
X_NOZZLE, Z_NOZZLE = 0.60, 0.15
Z_GROUND = -2.05

# ------------------------------------------------------------------ wing (shoulder mounted)
TAN_LE = math.tan(math.radians(45.0))
TAN_TE = math.tan(math.radians(5.0))       # the trailing edge is swept forward a little
WING_APEX = 3.85
WING_TE0 = -4.30
X_ROOT = 1.45
X_TIP = 6.52
X_FLAP = 3.60              # flap outboard end = aileron inboard end
X_AIL = 5.95
DIHEDRAL = math.radians(-1.0)
Z_WING = 0.62


def wing_le(x):
    return WING_APEX - np.abs(x) * TAN_LE


def wing_te(x):
    return WING_TE0 + np.abs(x) * TAN_TE


def wing_chord(x):
    return wing_le(x) - wing_te(x)


def wing_z(x):
    return Z_WING + np.abs(x) * math.tan(DIHEDRAL)


def wing_t(x):
    """Thickness ratio: 6.6 % at the root, 3 % at the tip."""
    return 0.066 + (0.030 - 0.066) * np.clip((np.abs(x) - X_ROOT) / (X_TIP - X_ROOT), 0.0, 1.0)


def flap_chord(x):
    return 1.05 + (0.85 - 1.05) * (np.abs(x) - X_ROOT) / (X_FLAP - X_ROOT)


def ail_chord(x):
    return 0.80 + (0.55 - 0.80) * (np.abs(x) - X_FLAP) / (X_AIL - X_FLAP)


Y_KINK = float(wing_le(X_ROOT))       # 2.40: the wing leading edge at the body side
WING_TE = float(wing_te(X_ROOT))      # -4.17

# ---------------------------------------------------------------- tail booms and tail surfaces
BOOM_X, BOOM_Z, BOOM_R = 1.50, 0.30, 0.24
BOOM_Y0, BOOM_Y1 = -4.6, -9.15
STAB_X0, STAB_X1 = 1.72, 4.30
STAB_LE0, STAB_TE0 = -5.85, -9.45
STAB_LE1 = STAB_LE0 - (STAB_X1 - STAB_X0) * math.tan(math.radians(45.0))
STAB_TE1 = STAB_TE0
STAB_Z0 = 0.22
STAB_ANHEDRAL = math.radians(0.0)
STAB_PIVOT = -8.05


def stab_le(x):
    return STAB_LE0 + (STAB_LE1 - STAB_LE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_te(x):
    return STAB_TE0 + (STAB_TE1 - STAB_TE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_z(x):
    return STAB_Z0 - (np.abs(x) - STAB_X0) * math.tan(STAB_ANHEDRAL)


# twin vertical tails on the booms (2 degrees outward), s = distance up the fin from its root
FIN_X, FIN_ZROOT, FIN_CANT = BOOM_X, BOOM_Z + 0.18, math.radians(2.0)
FIN_S0, FIN_S1 = -0.10, 3.10
FIN_LE0, FIN_TE0 = -5.35, -8.85
FIN_SWEEP = math.tan(math.radians(36.0))
FIN_TE_SWEEP = math.tan(math.radians(-8.0))
RUD_S0, RUD_S1 = 0.10, 1.40


def fin_le(s):
    return FIN_LE0 - s * FIN_SWEEP


def fin_te(s):
    return FIN_TE0 - s * FIN_TE_SWEEP


def rudder_chord(s):
    return 0.90 + (0.75 - 0.90) * (s - RUD_S0) / (RUD_S1 - RUD_S0)


# ------------------------------------------------------------------ body tables
# the long, slim forebody; aft of the inlets the wide, flat engine body with the conformal tanks
#    y,     top,   bottom, half width, n upper, n lower, z of the widest point
_BODY = (
    (9.90, 0.385, 0.365, 0.004, 2.0, 2.0, 0.375),
    (9.75, 0.455, 0.290, 0.085, 2.0, 2.0, 0.375),
    (9.45, 0.560, 0.180, 0.190, 2.0, 2.0, 0.37),
    (8.90, 0.700, 0.040, 0.320, 2.0, 2.0, 0.37),
    (8.10, 0.860, -0.110, 0.440, 2.0, 2.05, 0.37),
    (7.30, 0.990, -0.230, 0.520, 2.05, 2.15, 0.38),
    (6.50, 1.090, -0.330, 0.570, 2.1, 2.3, 0.40),
    (5.70, 1.140, -0.410, 0.600, 2.2, 2.5, 0.42),
    (4.80, 1.170, -0.480, 0.620, 2.2, 2.7, 0.44),
    (4.00, 1.180, -0.540, 0.640, 2.2, 2.9, 0.46),
    (3.30, 1.180, -0.600, 0.700, 2.3, 3.0, 0.48),
    (2.50, 1.160, -0.700, 1.050, 2.5, 3.2, 0.48),
    (1.60, 1.120, -0.780, 1.420, 2.8, 3.4, 0.48),
    (0.60, 1.080, -0.800, 1.560, 3.0, 3.6, 0.48),
    (-0.80, 1.040, -0.800, 1.600, 3.2, 3.6, 0.47),
    (-2.40, 0.990, -0.780, 1.580, 3.2, 3.4, 0.45),
    (-4.00, 0.930, -0.720, 1.460, 3.0, 3.2, 0.42),
    (-5.50, 0.860, -0.620, 1.240, 2.8, 3.0, 0.38),
    (-6.80, 0.760, -0.500, 1.080, 2.6, 2.8, 0.32),
    (-7.70, 0.660, -0.400, 1.000, 2.6, 2.6, 0.27),
)
BODY = [Curve([(r[0], r[c]) for r in _BODY]) for c in range(1, 7)]

K_UP = Curve([(Y_KINK, 0.06), (0.0, 0.20), (WING_TE, 0.22)])
K_LO = Curve([(Y_KINK, 0.04), (WING_TE, 0.10)])

#   y, half width, height above the sill: tandem canopy (windscreen, then one long bubble over both seats)
_CANOPY = ((6.70, 0.03, 0.01), (6.50, 0.25, 0.16), (6.25, 0.37, 0.36), (5.95, 0.44, 0.52), (5.50, 0.48, 0.64),
           (5.00, 0.49, 0.70), (4.40, 0.49, 0.72), (3.80, 0.48, 0.70), (3.20, 0.45, 0.62), (2.65, 0.40, 0.46),
           (2.20, 0.30, 0.25), (1.85, 0.16, 0.06), (1.70, 0.05, 0.01))
CANOPY_W = Curve([(r[0], r[1]) for r in _CANOPY])
CANOPY_H = Curve([(r[0], r[2]) for r in _CANOPY])
CANOPY_Y0, CANOPY_Y1 = _CANOPY[-1][0], _CANOPY[0][0]
WINDSCREEN_ARCH = 5.95
COCKPIT_Y0, COCKPIT_Y1 = 2.55, 5.85           # both cockpits
COCKPIT_W = 0.40
FRONT_SEAT_Y, REAR_SEAT_Y = 4.45, 3.05

# rectangular side inlets with a hinged ramp on top: (y, inner x, outer x, top, bottom); the face is raked
_INTAKE = ((4.10, 0.66, 1.42, 0.86, -0.58), (3.70, 0.66, 1.44, 0.86, -0.62), (3.10, 0.68, 1.48, 0.84, -0.68),
           (2.40, 0.70, 1.52, 0.80, -0.74), (1.60, 0.72, 1.56, 0.76, -0.78), (0.80, 0.74, 1.58, 0.72, -0.80))
INTAKE = [Curve([(r[0], r[c]) for r in _INTAKE]) for c in range(1, 5)]
Y_INTAKE = _INTAKE[0][0]
INTAKE_RAKE_Z = -0.55       # the face leans back: the bottom lip is further aft... (top forward)

# landing gear wells (x0, x1, y0, y1)
NOSE_WELL = (-0.22, 0.22, 5.60, 7.20)
MAIN_WELL = (0.70, 1.30, -1.20, 0.70)


class Section:
    """Implicit cross section F(x, z) < 0 at station y: superellipse core plus the inboard wing blade."""

    def __init__(self, y, blade=True):
        self.y = float(y)
        self.zt, self.zb, self.hw, self.nu, self.nl, self.zc = (float(c(y)) for c in BODY)
        self.core = min(self.hw, self.zt - self.zc, self.zc - self.zb)
        self.xlim = None
        self.z0 = self.zc
        self.ghost = 0.0
        zw = float(wing_z(X_ROOT))
        if blade and WING_TE - 1.4 < y <= WING_TE:
            self.ghost = float(smoothstep(WING_TE - 1.4, WING_TE, y))
            self.ku, self.kl = float(K_UP(WING_TE)) * self.ghost, float(K_LO(WING_TE)) * self.ghost
            self.z0 = zw
        if blade and WING_TE < y <= Y_KINK + 0.9:
            self.xlim = X_ROOT
            self.z0 = zw
            self.ku, self.kl = float(K_UP(y)), float(K_LO(y))
            self.edge = (WING_APEX - y) / TAN_LE
            self.fade = max(0.0, 1.0 - (Y_KINK - y) / 1.0) if y <= Y_KINK else 1.0

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

    def _vertical(self, x, direction, reach=2.4, iters=40):
        x = np.atleast_1d(np.asarray(x, float))
        lo = np.full(x.shape, self.zc)
        hi = lo + direction * reach
        inside = self.F(x, lo) < 0.0
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            o = self.F(x, mid) > 0.0
            hi = np.where(o, mid, hi)
            lo = np.where(o, lo, mid)
        return np.where(inside, 0.5 * (lo + hi), self.zc)

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
            zu, zl = float(self._vertical(np.array([xe]), 1.0)[0]), float(self._vertical(np.array([xe]), -1.0)[0])
            # the blade sits at z0: search from there for the skin above / below it
            sec_up, sec_lo = self._edge(xe)
            zu, zl = sec_up, sec_lo
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

    def _edge(self, x, iters=40):
        """Upper and lower skin heights at the blade edge x (searching from the blade plane)."""
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


# texture atlas (atlas metres, see f15_paint.py): 21 m x 21 m
ATLAS = 21.0
YA0 = -10.4
V_TOP, V_BOT, V_SIDE = 0.0, 7.0, 17.0        # strips: top (|x| 0..7), bottom (7..14), side (z + V_SIDE: 14.5..21)
FIN_ISLANDS = {1.0: (13.2, 3.0), -1.0: (17.1, 3.0)}
FIN_ISLAND_SCALE = 0.95
DECALS = ()
FIN_YMIN, FIN_YMAX = -9.00, -5.20


def fin_span_dir(sign):
    return np.array([sign * math.sin(FIN_CANT), 0.0, math.cos(FIN_CANT)])


def fin_normal(sign):
    return np.array([sign * math.cos(FIN_CANT), 0.0, -math.sin(FIN_CANT)])


def fin_s(x, z):
    return (np.abs(x) - FIN_X) * math.sin(FIN_CANT) + (z - FIN_ZROOT) * math.cos(FIN_CANT)


def fin_island(y, s, sign):
    u0, v0 = FIN_ISLANDS[sign]
    k = FIN_ISLAND_SCALE
    u = u0 + ((np.asarray(y) - FIN_YMIN) if sign > 0 else (FIN_YMAX - np.asarray(y))) * k
    return u, v0 + (np.asarray(s) - FIN_S0) * k


def intake_section(y):
    return tuple(float(c(y)) for c in INTAKE)


def intake_bottom(y, x):
    xi, xo, zt, zb = intake_section(y)
    cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi)
    cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb)
    t = min(abs(abs(x) - cx) / hw, 1.0)
    return cz - hh * max(0.0, 1.0 - t ** 4.0) ** (1.0 / 4.0)
