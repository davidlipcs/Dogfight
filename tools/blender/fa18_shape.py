"""Shape tables and section maths of the Blender F/A-18E Super Hornet (pure numpy).

Shared by the mesh builder (build_fa18.py) and the texture painter (fa18_paint.py).

Model frame: +Y forward, +X right, +Z up, metres; origin at the centre of gravity (about 25 % MAC),
ground at Z_GROUND with the gear down.  Real dimensions: 18.31 m long, 13.62 m span over the wing tip
missiles, 4.88 m high, 46.45 m^2 wing; LEX, caret inlets, twin canted fins, two F414 engines.
"""

import math

import numpy as np

from f16_shape import Curve, resample, smin, smoothstep, yt   # the same maths as the F-16

Y_NOSE = 9.70             # radome tip
Y_RADOME = 7.75
Y_BODY_END = -7.62        # the nozzles start here
Y_NOZZLE = -8.61          # nozzle exit plane
X_NOZZLE, Z_NOZZLE = 0.56, -0.12
Z_GROUND = -1.75

# ------------------------------------------------------------------ wing
TAN_LE = math.tan(math.radians(28.0))
WING_APEX = 2.463         # leading edge of the theoretical wing at the centre line
WING_TE = -2.90           # (nearly) unswept trailing edge
X_ROOT = 2.00             # the wing mesh starts at the LEX junction
X_TIP = 6.55
X_FLAP = 4.25             # flap outboard end = aileron inboard end (also the wing fold line)
X_AIL = 6.20
DIHEDRAL = math.radians(-3.0)
Z_WING = 0.32             # wing plane at the centre line


def wing_le(x):
    return WING_APEX - np.abs(x) * TAN_LE


def wing_chord(x):
    return wing_le(x) - WING_TE


def wing_z(x):
    return Z_WING + np.abs(x) * math.tan(DIHEDRAL)


def wing_t(x):
    """Thickness ratio: 5 % at the root, 3.5 % at the tip."""
    return 0.05 + (0.035 - 0.05) * np.clip((np.abs(x) - X_ROOT) / (X_TIP - X_ROOT), 0.0, 1.0)


def lef_chord(x):
    return 0.62 + (0.32 - 0.62) * (np.abs(x) - X_ROOT) / (X_TIP - X_ROOT)


def flap_chord(x):
    return 0.95 + (0.80 - 0.95) * (np.abs(x) - X_ROOT) / (X_FLAP - X_ROOT)


def ail_chord(x):
    return 0.62 + (0.50 - 0.62) * (np.abs(x) - X_FLAP) / (X_AIL - X_FLAP)


Y_KINK = float(wing_le(X_ROOT))       # 1.40: where the LEX meets the wing leading edge
Y_STRAKE0 = 6.10                      # the LEX grows out of the forebody chine here

# ---------------------------------------------------------------- tail surfaces
STAB_X0, STAB_X1 = 1.12, 3.65
STAB_LE0, STAB_TE0 = -5.00, -7.90
STAB_LE1 = STAB_LE0 - (STAB_X1 - STAB_X0) * math.tan(math.radians(42.0))
STAB_TE1 = -8.25
STAB_Z0 = -0.10
STAB_ANHEDRAL = math.radians(2.0)
STAB_PIVOT = -6.55


def stab_le(x):
    return STAB_LE0 + (STAB_LE1 - STAB_LE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_te(x):
    return STAB_TE0 + (STAB_TE1 - STAB_TE0) * (np.abs(x) - STAB_X0) / (STAB_X1 - STAB_X0)


def stab_z(x):
    return STAB_Z0 - (np.abs(x) - STAB_X0) * math.tan(STAB_ANHEDRAL)


# twin fins: in the fin's own plane, s = distance up the fin from its root (canted 20 degrees outwards)
FIN_X, FIN_ZROOT, FIN_CANT = 0.98, 0.30, math.radians(20.0)
FIN_S0, FIN_S1 = -0.10, 2.75
FIN_LE0, FIN_TE0 = -2.70, -5.70
FIN_SWEEP = math.tan(math.radians(38.0))
RUD_S0, RUD_S1 = 0.15, 1.75


def fin_le(s):
    return FIN_LE0 - (s - 0.0) * FIN_SWEEP


def fin_te(s):
    return FIN_TE0 - (s - 0.0) * 0.20


def rudder_chord(s):
    return 0.80 + (0.62 - 0.80) * (s - RUD_S0) / (RUD_S1 - RUD_S0)


# ------------------------------------------------------------------ body tables
#    y,     top,   bottom, half width, n upper, n lower, z of the widest point
_BODY = (
    (9.70, 0.225, 0.215, 0.004, 2.0, 2.0, 0.22),
    (9.60, 0.282, 0.158, 0.060, 2.0, 2.0, 0.22),
    (9.40, 0.358, 0.082, 0.136, 2.0, 2.0, 0.22),
    (9.10, 0.448, -0.010, 0.222, 2.0, 2.0, 0.22),
    (8.70, 0.540, -0.100, 0.310, 2.0, 2.0, 0.22),
    (8.20, 0.630, -0.180, 0.395, 2.0, 2.05, 0.23),
    (7.75, 0.700, -0.240, 0.460, 2.05, 2.1, 0.24),
    (7.20, 0.800, -0.300, 0.530, 2.15, 2.25, 0.25),
    (6.50, 0.930, -0.380, 0.620, 2.25, 2.45, 0.28),
    (6.10, 0.960, -0.420, 0.640, 2.30, 2.60, 0.30),
    (5.20, 0.990, -0.500, 0.665, 2.40, 2.90, 0.30),
    (4.20, 1.000, -0.620, 0.700, 2.40, 3.10, 0.28),
    (3.20, 1.040, -0.780, 0.780, 2.20, 3.20, 0.26),
    (2.30, 1.070, -0.900, 0.950, 2.00, 3.20, 0.24),
    (1.40, 1.020, -0.950, 1.100, 1.90, 3.10, 0.22),
    (0.00, 0.920, -0.950, 1.180, 1.85, 3.00, 0.20),
    (-1.50, 0.820, -0.920, 1.160, 1.85, 2.90, 0.18),
    (-2.90, 0.720, -0.850, 1.100, 1.90, 2.80, 0.15),
    (-4.50, 0.560, -0.700, 0.900, 2.00, 2.60, 0.05),
    (-6.00, 0.440, -0.600, 0.700, 2.00, 2.40, -0.02),
    (-7.62, 0.320, -0.520, 0.560, 2.00, 2.20, -0.06),
)
BODY = [Curve([(r[0], r[c]) for r in _BODY]) for c in range(1, 7)]

# twin engine nacelles take over the aft body: (y, weight, radius)
NACELLE = Curve([(1.0, 0.0), (-2.0, 0.6), (-3.5, 1.0), (-7.62, 1.0)])
NACELLE_R = Curve([(-2.0, 0.55), (-5.0, 0.53), (-7.62, 0.475)])

LEX = Curve([(Y_KINK, X_ROOT), (2.30, 1.70), (3.20, 1.40), (4.20, 1.08), (5.20, 0.78), (Y_STRAKE0, 0.52)])
LEX_Z = Curve([(Y_KINK, float(wing_z(X_ROOT))), (3.0, 0.28), (4.5, 0.38), (5.5, 0.46), (Y_STRAKE0, 0.52)])
K_UP = Curve([(Y_STRAKE0, 0.04), (5.0, 0.10), (3.5, 0.15), (1.4, 0.26), (0.0, 0.34), (WING_TE, 0.30)])
K_LO = Curve([(Y_STRAKE0, 0.03), (4.4, 0.06), (2.5, 0.10), (WING_TE, 0.12)])

#   y, half width, height above the sill: windscreen, then the one piece canopy
_CANOPY = ((6.38, 0.03, 0.01), (6.20, 0.30, 0.18), (5.98, 0.45, 0.38), (5.72, 0.52, 0.56), (5.30, 0.555, 0.68),
           (4.85, 0.56, 0.73), (4.40, 0.555, 0.72), (3.95, 0.53, 0.64), (3.55, 0.46, 0.47), (3.20, 0.37, 0.28),
           (2.95, 0.26, 0.12), (2.78, 0.12, 0.02))
CANOPY_W = Curve([(r[0], r[1]) for r in _CANOPY])
CANOPY_H = Curve([(r[0], r[2]) for r in _CANOPY])
CANOPY_Y0, CANOPY_Y1 = _CANOPY[-1][0], _CANOPY[0][0]
WINDSCREEN_ARCH = 5.72
COCKPIT_Y0, COCKPIT_Y1 = 3.78, 5.58
COCKPIT_W = 0.40

# caret inlets under the LEX: (y, inner x, outer x, top, bottom); the lip is raked back at the bottom and inwards
_INTAKE = ((2.90, 0.70, 1.52, 0.17, -0.90), (2.60, 0.70, 1.51, 0.17, -0.91), (2.10, 0.68, 1.46, 0.17, -0.92),
           (1.40, 0.66, 1.38, 0.16, -0.92), (0.60, 0.64, 1.26, 0.15, -0.92), (-0.20, 0.62, 1.16, 0.14, -0.91))
INTAKE = [Curve([(r[0], r[c]) for r in _INTAKE]) for c in range(1, 5)]
Y_INTAKE = _INTAKE[0][0]

# landing gear wells (x0, x1, y0, y1): nose gear folds forwards, the main gears forwards into the trunks
NOSE_WELL = (-0.27, 0.27, 5.05, 6.85)
MAIN_WELL = (0.36, 1.10, -1.05, 0.95)


def blade_z(y):
    return float(LEX_Z(y)) if y > Y_KINK else float(wing_z(X_ROOT))


class Section:
    """Implicit cross section F(x, z) < 0 at station y: superellipse core, twin nacelles aft, the LEX /
    inboard wing blade, joined with fillets.  (Same idea as the F-16, see f16_shape.Section.)"""

    def __init__(self, y, blade=True):
        self.y = float(y)
        self.zt, self.zb, self.hw, self.nu, self.nl, self.zc = (float(c(y)) for c in BODY)
        self.core = min(self.hw, self.zt - self.zc, self.zc - self.zb)
        self.nac = float(NACELLE(y))
        self.nr = float(NACELLE_R(y))
        self.xlim = None
        self.z0 = self.zc
        self.ghost = 0.0
        if blade and WING_TE - 1.4 < y <= WING_TE:
            self.ghost = float(smoothstep(WING_TE - 1.4, WING_TE, y))
            self.ku, self.kl = float(K_UP(WING_TE)) * self.ghost, float(K_LO(WING_TE)) * self.ghost
            self.z0 = blade_z(WING_TE)
        if blade and WING_TE < y <= Y_STRAKE0:
            self.xlim = float(LEX(y)) if y >= Y_KINK else X_ROOT
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
        if self.nac > 0.0:                       # the engines bulge out of the aft body
            fn = np.hypot(ax - X_NOZZLE, z - Z_NOZZLE) - self.nr * self.nac
            f = smin(f, fn, 0.22)
        if self.xlim is not None:
            c = wing_chord(ax)
            s = (wing_le(ax) - self.y) / c
            tau = np.where((s > 0.0) & (s < 1.0), yt(s, wing_t(X_ROOT)) * c, -1.0)
            if self.fade > 0.0:
                tau = np.maximum(tau, np.minimum((self.edge - ax) * 0.14, 0.055) * self.fade)
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
        rmax = 1.3 * max(self.hw + self.nac * 0.6, self.zt - self.zb, self.xlim or 0.0) + 0.3
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


# texture atlas (atlas metres, see fa18_paint.py): 20 m x 20 m
ATLAS = 20.0
YA0 = -9.0
V_TOP, V_BOT, V_SIDE = 0.0, 7.0, 16.5       # strips: top (|x| 0..7), bottom (7..14), side (z + V_SIDE: 14..19.5)
# the outer faces of the fins: one island each (so that the codes read correctly on both sides),
# in the empty corner of the top view ahead of the wing: (u0, v0) atlas metres, fin s along v
FIN_ISLANDS = {1.0: (12.8, 3.4), -1.0: (16.4, 3.4)}
FIN_ISLAND_SCALE = 0.95
# left side markings: the side strip is mirrored, so text on the left side gets its own islands
# (y0, y1, z0, z1, u0, v0): faces of the left side whose centre lies in the box map to the island, u running aft
DECALS = ((-4.95, -3.05, -0.56, -0.04, 16.3, 6.40),       # NAVY under the tails
          (6.45, 7.35, -0.12, 0.32, 18.5, 6.40))          # modex on the nose

FIN_YMIN, FIN_YMAX = -6.40, -2.55            # chordwise extent of the fins (for their texture islands)


def fin_span_dir(sign):
    return np.array([sign * math.sin(FIN_CANT), 0.0, math.cos(FIN_CANT)])


def fin_normal(sign):
    """Outward normal of the fin plane on the side `sign` (1 = right fin)."""
    return np.array([sign * math.cos(FIN_CANT), 0.0, -math.sin(FIN_CANT)])


def fin_s(x, z):
    """Distance up the fin from its root line, for points on either fin."""
    return (np.abs(x) - FIN_X) * math.sin(FIN_CANT) + (z - FIN_ZROOT) * math.cos(FIN_CANT)


def fin_island(y, s, sign):
    """Atlas metres (u, v) of a point on the OUTER face of a fin: right fin u grows forwards, left fin u
    grows aft, so that text painted left to right reads correctly from either side."""
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
