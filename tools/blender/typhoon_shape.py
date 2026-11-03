"""Eurofighter Typhoon: the shape (pure numpy), measured off its three-view (Wikimedia Commons "Eurofighter Typhoon
3-view"; 35.78 px per metre: 15.96 m from the nose to the fin tip).  The span is stretched to the real 10.95 m over
the wing tip pods (the drawing's is 10.4 m) and the ground set for the real 5.28 m height.

Drawing pixels -> metres:  top view (nose to the left) y = (780 - X) / 35.78, x = |Y - 1276.5| / 35.78;
side view y = (773.9 - X) / 35.78, z = (993 - Y) / 35.78 (z = 0: the nose tip).

The Typhoon: a long pointed nose, the bubble canopy, the canards just behind the radome, the big split chin intake
under the cockpit, the 53 degree cranked delta, one big fin with the dorsal intake at its root, two EJ200 nozzles.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "typhoon"
Y_NOSE = 8.00
Y_PITOT = 8.00
Z_GROUND = -1.98
SPAN_K = 10.95 / 10.42           # the real span over the drawing's

# y | spine z | shoulder (x, z) | upper side (x, z) | edge (x, z) | lower side (x, z) | keel z
_T = [
    (8.00, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
    (7.70, 0.120, 0.090, 0.100, 0.120, 0.050, 0.130, 0.000, 0.090, -0.080, -0.110),
    (7.30, 0.260, 0.170, 0.210, 0.220, 0.110, 0.240, 0.000, 0.170, -0.140, -0.190),
    (6.80, 0.420, 0.250, 0.340, 0.320, 0.200, 0.340, 0.020, 0.250, -0.200, -0.250),
    (6.20, 0.600, 0.330, 0.480, 0.400, 0.290, 0.420, 0.050, 0.330, -0.240, -0.290),
    (5.70, 0.760, 0.380, 0.610, 0.450, 0.380, 0.470, 0.080, 0.380, -0.260, -0.300),
    (5.00, 0.880, 0.420, 0.730, 0.500, 0.450, 0.520, 0.110, 0.420, -0.270, -0.310),
    (4.00, 0.980, 0.450, 0.830, 0.540, 0.500, 0.560, 0.120, 0.450, -0.270, -0.310),
    (3.00, 1.050, 0.470, 0.900, 0.600, 0.520, 0.680, 0.120, 0.500, -0.270, -0.310),
    (2.40, 1.080, 0.480, 0.930, 0.700, 0.540, 0.860, 0.110, 0.560, -0.280, -0.330),
    (2.30, 1.140, 0.500, 0.990, 0.740, 0.560, 0.900, 0.110, 0.600, -0.290, -0.350),
    (1.50, 1.120, 0.560, 0.990, 0.860, 0.580, 1.000, 0.100, 0.700, -0.350, -0.480),
    (0.00, 1.060, 0.600, 0.970, 0.920, 0.580, 1.010, 0.080, 0.780, -0.550, -0.700),
    (-1.50, 1.020, 0.620, 0.940, 0.930, 0.570, 1.010, 0.060, 0.800, -0.600, -0.740),
    (-3.00, 1.000, 0.620, 0.920, 0.930, 0.560, 1.000, 0.050, 0.800, -0.580, -0.700),
    (-4.50, 1.020, 0.600, 0.940, 0.920, 0.560, 0.980, 0.050, 0.780, -0.500, -0.600),
    (-5.80, 0.960, 0.570, 0.900, 0.880, 0.560, 0.950, 0.050, 0.740, -0.420, -0.500),
    (-6.40, 0.840, 0.520, 0.800, 0.820, 0.520, 0.900, 0.060, 0.700, -0.360, -0.420),
    (-6.60, 0.700, 0.300, 0.690, 0.500, 0.550, 0.560, 0.150, 0.420, -0.250, -0.300),
    (-6.75, 0.480, 0.000, 0.480, 0.000, 0.480, 0.000, 0.480, 0.000, 0.480, 0.480),
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
    return FUSELAGE.ring(y)


def fuselage_stations():
    return jk.stations([(Y_NOSE, 7.30, 0.04), (7.30, 2.40, 0.10), (2.40, 2.30, 0.05), (2.30, -6.40, 0.16),
                        (-6.40, -6.75, 0.04)])


# ------------------------------------------------------------------ canopy (one seat)
Y_WS0, Y_WS1, Y_CAN1 = 5.75, 5.05, 2.40
CANOPY_TOP = Line([(5.75, 0.78), (5.45, 1.06), (5.05, 1.30), (4.60, 1.46), (4.10, 1.53), (3.60, 1.52), (3.10, 1.42),
                   (2.70, 1.27), (2.40, 1.15)])
CANOPY_SILL_Z = Line([(5.75, 0.77), (5.00, 0.86), (4.00, 0.96), (2.40, 1.06)])
CANOPY_SILL_X = Line([(5.75, 0.32), (5.30, 0.40), (4.60, 0.44), (3.20, 0.44), (2.70, 0.38), (2.40, 0.28)])
CANOPY_BULGE = Line([(5.75, 0.0), (5.3, 0.02), (4.5, 0.04), (3.4, 0.035), (2.40, 0.0)])


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


# ------------------------------------------------------------------ cranked delta (LE 53 deg), straight trailing edge
Z_WING = 0.10
X_WTIP = 5.40
_LE = jk.Lin([(0.95, 2.20), (1.16, 1.82), (5.40, -3.40)])
_TE = jk.Lin([(0.95, -5.05), (5.40, -5.10)])


def wing_le(x):
    return _LE(x)


def wing_te(x):
    return _TE(x)


def wing_z(x):
    return Z_WING + 0.0 * np.asarray(x, float)


WING = Surface([(x, float(_LE(x)), float(_TE(x)), Z_WING, t) for x, t in ((0.95, 0.050), (1.16, 0.050), (3.20, 0.040),
                                                                           (5.40, 0.035))], nc=20)
FLAP = (1.20, 3.20, 0.85, 0.70)
AIL = (3.20, 5.20, 0.70, 0.55)
LEF = (2.30, 5.30, 0.42, 0.30)
TIP_POD = dict(x=5.46, z=Z_WING, y0=-3.05, y1=-5.25, r=0.13)

# ------------------------------------------------------------------ canards behind the radome
CANARD_Z = 0.45
CANARD = Surface([
    (0.50, 5.45, 4.05, CANARD_Z, 0.045),
    (1.97, 3.98, 3.77, CANARD_Z, 0.035),
], airfoil=jk.biconvex_t, nc=12)
CANARD_PIVOT = 4.55

# ------------------------------------------------------------------ the chin intake (two ducts side by side, a splitter)
Y_FACE_TOP, Y_FACE_BOT = 4.35, 3.10            # the face raked back: the top far forward
_N = [
    (3.10, 0.04, 0.66, -0.22, -1.00, 6.0),
    (2.30, 0.04, 0.68, -0.24, -0.98, 5.0),
    (1.00, 0.04, 0.66, -0.30, -0.90, 4.0),
    (0.00, 0.04, 0.60, -0.40, -0.80, 3.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = 0.00
DUCT_DEPTH = 1.5
NOZZLE = dict(x=0.47, z=0.08, y0=-6.40, y1=-6.82, r0=0.43, r1=0.40, petals=16)


def nacelle_rake(d):
    full = (Y_FACE_TOP - Y_FACE_BOT) / (1.00 - 0.22)
    return full * max(0.0, 1.0 - d / 2.2) ** 1.2


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, 0.00, 0.20)])


# ------------------------------------------------------------------ the fin
BOOM = None
FIN_X, FIN_Z, FIN_CANT = 0.0, 1.00, 0.0
FIN = [
    (0.00, -3.25, -6.65, 0.0, 0.045),
    (0.22, -3.80, -6.75, 0.0, 0.045),
    (2.30, -7.15, -8.02, 0.0, 0.032),
]
RUDDER = (0.25, 1.70, 0.70, 0.55)

# ------------------------------------------------------------------ landing gear
GEAR_NOSE = dict(y=2.60, x=0.0, r=0.24, w=0.15, twin=False)
GEAR_MAIN = dict(y=-1.45, x=1.30, r=0.35, w=0.24)
