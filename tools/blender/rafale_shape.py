"""Dassault Rafale C: the shape (pure numpy), measured off the Rafale B three-view (its own dimension lines: 15.27 m
long = 487 px, 10.80 m span = 342 px; ~31.8 px per metre), with the one seat canopy of the C.

Drawing pixels -> metres:  top view y = (X - 330) / 31.7, x = |Y - 983| / 31.7 (nose to the right);
side view y = (X - 830) / 31.9, z = (1015 - Y) / 31.9.  Ground at z -1.63 (the main wheels), height 5.34 m.

The Rafale: a slim pointed nose with the chin, the bubble canopy, the two kidney shaped intakes low on the sides with
the close coupled canards on top of them, a 45 degree delta wing low on the body, the big swept fin with the tip
behind the nozzles, two M88 nozzles close together.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "rafale"
Y_NOSE = 7.18
Y_PITOT = 7.45
Z_GROUND = -1.63

# y | spine z | shoulder (x, z) | upper side (x, z) | edge (x, z) | lower side (x, z) | keel z
_T = [
    (7.18, -0.180, 0.000, -0.180, 0.000, -0.180, 0.000, -0.180, 0.000, -0.180, -0.180),
    (7.00, -0.100, 0.045, -0.110, 0.065, -0.150, 0.075, -0.190, 0.050, -0.240, -0.260),
    (6.50, 0.060, 0.130, 0.020, 0.190, -0.060, 0.220, -0.150, 0.150, -0.330, -0.380),
    (6.00, 0.200, 0.210, 0.130, 0.300, 0.020, 0.380, -0.100, 0.250, -0.380, -0.440),
    (5.50, 0.380, 0.280, 0.270, 0.390, 0.090, 0.460, -0.060, 0.320, -0.410, -0.470),
    (5.00, 0.560, 0.330, 0.430, 0.460, 0.160, 0.520, -0.020, 0.380, -0.420, -0.480),
    (4.50, 0.700, 0.360, 0.560, 0.500, 0.230, 0.560, 0.010, 0.420, -0.430, -0.490),
    (4.00, 0.780, 0.380, 0.640, 0.520, 0.280, 0.580, 0.030, 0.440, -0.440, -0.500),
    (3.50, 0.830, 0.390, 0.690, 0.530, 0.310, 0.680, 0.040, 0.460, -0.450, -0.510),
    (3.00, 0.860, 0.400, 0.720, 0.560, 0.330, 0.790, 0.050, 0.500, -0.450, -0.520),
    (2.60, 0.900, 0.410, 0.760, 0.580, 0.350, 0.900, 0.060, 0.540, -0.460, -0.540),
    (2.40, 1.150, 0.440, 1.010, 0.620, 0.450, 0.960, 0.100, 0.560, -0.470, -0.550),
    (2.00, 1.130, 0.460, 1.000, 0.700, 0.500, 1.050, 0.130, 0.600, -0.480, -0.560),
    (1.00, 1.080, 0.500, 0.960, 0.820, 0.550, 1.050, 0.150, 0.700, -0.450, -0.560),
    (0.00, 1.040, 0.540, 0.940, 0.920, 0.560, 1.170, 0.150, 0.820, -0.400, -0.540),
    (-1.00, 1.000, 0.560, 0.920, 0.960, 0.560, 1.180, 0.150, 0.880, -0.350, -0.520),
    (-2.50, 0.980, 0.560, 0.900, 0.970, 0.560, 1.160, 0.150, 0.900, -0.300, -0.480),
    (-4.00, 0.990, 0.560, 0.910, 0.960, 0.570, 1.130, 0.170, 0.900, -0.250, -0.440),
    (-5.50, 0.970, 0.550, 0.900, 0.940, 0.580, 1.100, 0.190, 0.880, -0.200, -0.380),
    (-6.40, 0.930, 0.530, 0.870, 0.900, 0.600, 1.060, 0.200, 0.850, -0.150, -0.320),
    (-6.70, 0.900, 0.400, 0.860, 0.600, 0.700, 0.660, 0.300, 0.550, 0.000, -0.150),
    (-6.95, 0.800, 0.150, 0.790, 0.220, 0.700, 0.250, 0.450, 0.200, 0.250, 0.150),
    (-7.05, 0.600, 0.000, 0.600, 0.000, 0.600, 0.000, 0.600, 0.000, 0.600, 0.600),
]


def _col(i):
    return [(r[0], r[i]) for r in _T]


SPINE = Line(_col(1))
KEEL = Line(_col(10))
FUSELAGE = Body([
    Longeron("spine", 0.0, _col(1), full=1.17, n=6),
    Longeron("shoulder", _col(2), _col(3), full=1.05, n=4),
    Longeron("upper", _col(4), _col(5), full=1.0, n=4),
    Longeron("edge", _col(6), _col(7), full=1.10, n=5),
    Longeron("lower", _col(8), _col(9), full=1.17, n=5),
    Longeron("keel", 0.0, _col(10), n=1),
])


def fuselage_ring(y):
    FUSELAGE.L[3].sharp = 2.4 < y < 6.6                # the nose chine
    return FUSELAGE.ring(y)


def fuselage_stations():
    return jk.stations([(Y_NOSE, 6.50, 0.04), (6.50, 2.60, 0.10), (2.60, 2.40, 0.05), (2.40, -6.40, 0.16),
                        (-6.40, -7.05, 0.05)])


# ------------------------------------------------------------------ canopy (the one seat Rafale C)
Y_WS0, Y_WS1, Y_CAN1 = 5.00, 4.35, 2.45
CANOPY_TOP = Line([(5.00, 0.57), (4.75, 0.86), (4.35, 1.17), (4.00, 1.30), (3.60, 1.36), (3.20, 1.35), (2.85, 1.28),
                   (2.60, 1.20), (2.45, 1.16)])
CANOPY_SILL_Z = Line([(5.00, 0.56), (4.30, 0.66), (3.40, 0.75), (2.45, 0.86)])
CANOPY_SILL_X = Line([(5.00, 0.30), (4.60, 0.37), (4.00, 0.40), (3.00, 0.40), (2.65, 0.35), (2.45, 0.28)])
CANOPY_BULGE = Line([(5.00, 0.0), (4.6, 0.02), (4.0, 0.035), (3.2, 0.035), (2.45, 0.0)])


def canopy_half(y, n=14):
    zt, zs, xs = float(CANOPY_TOP(y)), float(CANOPY_SILL_Z(y)), float(CANOPY_SILL_X(y))
    bulge = float(CANOPY_BULGE(y))
    a = np.linspace(0.0, 0.5 * math.pi, n + 1)
    x = (xs + bulge) * np.sin(a) ** 0.85
    z = zs + (zt - zs) * np.cos(a) ** 1.10
    x[-1] = xs
    return np.stack([x, z], axis=1)


def canopy_stations():
    return jk.stations([(Y_WS0, Y_WS1, 0.05), (Y_WS1, Y_CAN1, 0.08)])


# ------------------------------------------------------------------ delta wing (45 deg), low on the body
Z_WING = 0.15
X_WTIP = 5.30
_LE = jk.Lin([(1.00, 0.00), (1.15, -0.20), (5.30, -4.40)])
_TE = jk.Lin([(1.00, -6.30), (5.30, -6.05)])


def wing_le(x):
    return _LE(x)


def wing_te(x):
    return _TE(x)


def wing_z(x):
    return Z_WING + 0.0 * np.asarray(x, float)


WING = Surface([(x, float(_LE(x)), float(_TE(x)), Z_WING, t) for x, t in ((1.00, 0.050), (1.15, 0.050), (3.00, 0.042),
                                                                           (5.30, 0.035))], nc=20)
FLAP = (1.20, 3.10, 0.80, 0.70)          # inner elevons
AIL = (3.10, 5.10, 0.70, 0.55)           # outer elevons
LEF = (2.40, 5.20, 0.40, 0.28)
TIP_POD = dict(x=5.36, z=Z_WING, y0=-3.20, y1=-6.05, r=0.06)

# ------------------------------------------------------------------ canards on the intakes
CANARD_Z = 0.42
CANARD = Surface([
    (1.20, 1.85, 0.55, CANARD_Z, 0.045),
    (2.70, 0.75, 0.10, CANARD_Z, 0.035),
], airfoil=jk.biconvex_t, nc=12)
CANARD_PIVOT = 0.95
CANARD_X0 = 1.20

# ------------------------------------------------------------------ the intakes, low on the sides (the lower lip forward)
Y_FACE_TOP, Y_FACE_BOT = 2.40, 2.85
_N = [
    (2.85, 0.48, 1.00, 0.20, -0.62, 3.2),
    (2.40, 0.49, 1.16, 0.26, -0.62, 3.0),
    (2.00, 0.50, 1.30, 0.30, -0.62, 3.0),
    (1.20, 0.52, 1.36, 0.30, -0.58, 3.0),
    (0.00, 0.54, 1.22, 0.28, -0.52, 3.0),
    (-1.00, 0.56, 1.15, 0.25, -0.45, 3.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = -1.00
DUCT_DEPTH = 1.6
NOZZLE = dict(x=0.62, z=0.22, y0=-6.65, y1=-7.18, r0=0.43, r1=0.39, petals=16)


def nacelle_rake(d):
    full = (Y_FACE_TOP - Y_FACE_BOT) / (0.28 + 0.62)
    return full * max(0.0, 1.0 - d / 1.2) ** 1.5


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, -1.00, 0.18)])


# ------------------------------------------------------------------ the fin (tip behind the nozzles)
BOOM = None
FIN_X, FIN_Z, FIN_CANT = 0.0, 0.92, 0.0
FIN = [
    (0.00, -3.90, -6.95, 0.0, 0.045),
    (0.25, -4.30, -7.00, 0.0, 0.045),
    (2.73, -7.05, -7.95, 0.0, 0.032),
]
RUDDER = (0.25, 1.85, 0.65, 0.50)

# ------------------------------------------------------------------ landing gear
GEAR_NOSE = dict(y=2.35, x=0.0, r=0.22, w=0.14, twin=True)
GEAR_MAIN = dict(y=-2.50, x=1.35, r=0.33, w=0.22)
