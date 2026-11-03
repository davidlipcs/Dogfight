"""JAS 39C Gripen: the shape (pure numpy), measured off its three-view (Wikimedia "Saab JAS 39 Gripen 3-view";
48.87 px per metre - the 14.1 m length from the pitot tip to the nozzle; the 8.4 m span over the tip rails and the
4.5 m height agree within 3 %).

Drawing pixels -> metres:  y = (X - 650) / 48.87 (nose to the right)   x = |Y - 1282| / 48.87 (top view)
z = (1000 - Y) / 48.87 (side view).  The fin is stretched to the real 4.5 m height (the drawing's stands 4.27 m).

The Gripen: a slim pointed nose, the bubble canopy, D-shaped side intakes with the all-moving canards on top of
them, a cranked delta wing (50 degrees, straight trailing edge with two elevons each side), one big fin, one RM12.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "gripen"
Y_NOSE = 6.20
Y_PITOT = 7.00
Z_GROUND = -1.49

# y | spine z | shoulder (x, z) | upper side (x, z) | widest (x, z) | lower side (x, z) | keel z
_T = [
    (6.20, -0.050, 0.000, -0.050, 0.000, -0.050, 0.000, -0.050, 0.000, -0.050, -0.050),
    (6.00, 0.020, 0.050, 0.010, 0.065, -0.020, 0.070, -0.050, 0.050, -0.100, -0.120),
    (5.50, 0.160, 0.130, 0.110, 0.170, 0.030, 0.180, -0.050, 0.130, -0.170, -0.220),
    (5.00, 0.280, 0.200, 0.200, 0.260, 0.100, 0.280, -0.030, 0.200, -0.200, -0.270),
    (4.50, 0.400, 0.260, 0.300, 0.330, 0.160, 0.360, 0.000, 0.260, -0.220, -0.300),
    (4.00, 0.530, 0.310, 0.410, 0.390, 0.220, 0.420, 0.020, 0.310, -0.240, -0.310),
    (3.65, 0.620, 0.340, 0.500, 0.420, 0.280, 0.450, 0.030, 0.340, -0.250, -0.320),
    (3.00, 0.720, 0.380, 0.620, 0.470, 0.350, 0.500, 0.050, 0.380, -0.270, -0.330),
    (2.45, 0.780, 0.400, 0.700, 0.500, 0.450, 0.520, 0.100, 0.400, -0.280, -0.330),
    (1.60, 0.800, 0.430, 0.740, 0.560, 0.600, 0.600, 0.250, 0.430, -0.260, -0.330),
    (1.40, 1.020, 0.450, 0.920, 0.600, 0.700, 0.650, 0.300, 0.450, -0.250, -0.330),
    (0.50, 1.000, 0.500, 0.920, 0.780, 0.750, 0.900, 0.350, 0.700, -0.250, -0.330),
    (-1.00, 0.970, 0.520, 0.900, 0.800, 0.720, 0.900, 0.300, 0.750, -0.200, -0.330),
    (-2.50, 0.960, 0.520, 0.880, 0.800, 0.700, 0.880, 0.300, 0.750, -0.180, -0.320),
    (-3.50, 0.950, 0.500, 0.880, 0.780, 0.680, 0.850, 0.320, 0.720, -0.150, -0.280),
    (-4.50, 0.920, 0.480, 0.850, 0.740, 0.660, 0.800, 0.350, 0.680, -0.100, -0.200),
    (-5.50, 0.880, 0.440, 0.820, 0.660, 0.640, 0.700, 0.380, 0.580, 0.020, -0.060),
    (-6.40, 0.840, 0.380, 0.780, 0.520, 0.620, 0.530, 0.380, 0.460, 0.120, 0.000),
]


def _col(i):
    return [(r[0], r[i]) for r in _T]


SPINE = Line(_col(1))
KEEL = Line(_col(10))
FUSELAGE = Body([
    Longeron("spine", 0.0, _col(1), full=1.17, n=6),
    Longeron("shoulder", _col(2), _col(3), full=1.05, n=4),
    Longeron("upper", _col(4), _col(5), full=1.0, n=4),
    Longeron("widest", _col(6), _col(7), full=1.10, n=5),
    Longeron("lower", _col(8), _col(9), full=1.17, n=5),
    Longeron("keel", 0.0, _col(10), n=1),
])


def fuselage_ring(y):
    return FUSELAGE.ring(y)


def fuselage_stations():
    r = jk.stations([(Y_NOSE, 5.50, 0.03), (5.50, 1.60, 0.10), (1.60, 1.40, 0.05), (1.40, -6.40, 0.15)])
    return r


# ------------------------------------------------------------------ canopy: one piece bubble over a one piece windscreen
Y_WS0, Y_WS1, Y_CAN1 = 3.65, 3.05, 1.45
CANOPY_TOP = Line([(3.65, 0.63), (3.40, 0.88), (3.05, 1.12), (2.70, 1.18), (2.30, 1.17), (1.90, 1.11), (1.60, 1.06),
                   (1.45, 1.03)])
CANOPY_SILL_Z = Line([(3.65, 0.62), (3.00, 0.70), (2.20, 0.76), (1.45, 0.80)])
CANOPY_SILL_X = Line([(3.65, 0.28), (3.30, 0.36), (2.80, 0.39), (2.00, 0.40), (1.70, 0.36), (1.45, 0.28)])
CANOPY_BULGE = Line([(3.65, 0.0), (3.3, 0.02), (2.7, 0.035), (2.0, 0.03), (1.45, 0.0)])


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


# ------------------------------------------------------------------ cranked delta: 50 deg leading edge, straight trailing edge
Z_WING = 0.30
X_WTIP = 4.00
_LE = jk.Lin([(0.85, 0.00), (0.95, -0.10), (4.00, -3.75)])
_TE = jk.Lin([(0.85, -5.00), (4.00, -5.05)])


def wing_le(x):
    return _LE(x)


def wing_te(x):
    return _TE(x)


def wing_z(x):
    return Z_WING - 0.0 * np.asarray(x, float)


WING = Surface([(x, float(_LE(x)), float(_TE(x)), Z_WING, t) for x, t in ((0.85, 0.050), (0.95, 0.050), (2.50, 0.042),
                                                                           (4.00, 0.035))], nc=20)
FLAP = (1.00, 2.50, 0.75, 0.68)          # the inner elevons
AIL = (2.50, 3.90, 0.68, 0.55)           # the outer elevons
LEF = (1.80, 3.90, 0.30, 0.24)
TIP_POD = dict(x=4.06, z=Z_WING, y0=-2.05, y1=-5.20, r=0.06)

# ------------------------------------------------------------------ the canards on the intakes
CANARD_Z = 0.55
CANARD = Surface([
    (0.90, 2.05, 0.25, CANARD_Z, 0.045),
    (2.15, -0.05, -0.25, CANARD_Z, 0.035),
], airfoil=jk.biconvex_t, nc=12)
CANARD_PIVOT = 0.95

# ------------------------------------------------------------------ the D-shaped intakes (they merge into the fuselage)
Y_FACE_TOP, Y_FACE_BOT = 2.45, 2.45
_N = [
    (2.45, 0.53, 0.92, 0.55, -0.15, 2.8),
    (1.50, 0.55, 0.92, 0.58, -0.20, 3.0),
    (0.50, 0.55, 0.90, 0.58, -0.25, 3.0),
    (-0.50, 0.55, 0.86, 0.55, -0.25, 3.0),
    (-1.20, 0.55, 0.80, 0.50, -0.20, 3.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = -1.20
DUCT_DEPTH = 1.5
NOZZLE = dict(x=0.0, z=0.38, y0=-6.40, y1=-6.98, r0=0.46, r1=0.42, petals=16)


def nacelle_rake(d):
    return 0.0


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, -1.20, 0.20)])


# ------------------------------------------------------------------ one fin (stretched to the real height)
BOOM = None
FIN_X, FIN_Z, FIN_CANT = 0.0, 0.95, 0.0
FIN = [
    (0.00, -2.60, -6.05, 0.0, 0.040),
    (0.12, -3.05, -6.05, 0.0, 0.040),
    (2.05, -5.15, -6.05, 0.0, 0.032),
]
RUDDER = (0.25, 1.90, 0.60, 0.45)

# ------------------------------------------------------------------ landing gear
GEAR_NOSE = dict(y=2.90, x=0.0, r=0.22, w=0.14, twin=True)
GEAR_MAIN = dict(y=-2.00, x=1.20, r=0.32, w=0.22)
