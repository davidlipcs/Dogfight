"""Su-57 Felon: the shape (pure numpy), measured off the side, top and bottom views of its three-view (46.77 px per
metre; 20.1 m long, 14.1 m span, 4.6 m high - the drawing agrees with the real figures within 1 %).

Drawing pixels -> metres:  y = (560 - X) / 46.77   x = |Y - Yc| / 46.77 (top view Yc = 1019.5, bottom view 1691)
z = (585 - Y) / 46.77 (side view).

What makes it a Su-57: the long chined nose, the one piece bubble canopy, the LEVCON panels ahead of the 49 degree
wing, the flat wide centre body (the weapon bays) between the two widely spaced engine nacelles, the raked trapezoid
intakes under the LEVCONs, the small all-moving fins canted out 25 degrees, the stabilators beside the nozzles and the
long tail sting between them.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "su57"
Y_NOSE = 10.05
Y_PITOT = 10.05
Z_GROUND = -1.62

# y | spine z | shoulder (x, z) | deck (x, z) | edge: nose chine -> LEVCON -> glove -> (inside the wing) -> boom (x, z) |
# lower side (x, z) | keel z
_T = [
    (10.05, 0.200, 0.000, 0.200, 0.000, 0.200, 0.000, 0.200, 0.000, 0.200, 0.200),
    (9.75, 0.300, 0.100, 0.280, 0.170, 0.240, 0.200, 0.210, 0.140, 0.140, 0.110),
    (9.50, 0.360, 0.170, 0.320, 0.270, 0.260, 0.300, 0.220, 0.220, 0.120, 0.060),
    (9.00, 0.480, 0.240, 0.420, 0.360, 0.310, 0.400, 0.250, 0.300, 0.070, -0.030),
    (8.50, 0.580, 0.310, 0.510, 0.470, 0.370, 0.520, 0.280, 0.380, 0.050, -0.090),
    (8.00, 0.670, 0.380, 0.590, 0.570, 0.420, 0.630, 0.300, 0.450, 0.030, -0.130),
    (7.50, 0.800, 0.420, 0.700, 0.650, 0.460, 0.720, 0.310, 0.500, 0.010, -0.150),
    (7.00, 0.950, 0.450, 0.850, 0.720, 0.500, 0.780, 0.320, 0.550, 0.000, -0.170),
    (6.00, 1.000, 0.480, 0.950, 0.780, 0.540, 0.840, 0.330, 0.600, -0.010, -0.190),
    (5.00, 1.050, 0.500, 1.000, 0.840, 0.570, 0.900, 0.330, 0.640, -0.020, -0.200),
    (4.45, 1.080, 0.520, 1.030, 0.870, 0.580, 0.930, 0.330, 0.660, -0.040, -0.210),
    (4.15, 1.390, 0.560, 1.250, 0.880, 0.640, 0.950, 0.340, 0.680, -0.050, -0.220),
    (3.50, 1.300, 0.600, 1.180, 1.050, 0.720, 1.550, 0.370, 0.900, 0.000, -0.250),
    (2.80, 1.230, 0.620, 1.120, 1.250, 0.780, 2.150, 0.400, 1.100, 0.100, -0.300),
    (2.45, 1.200, 0.640, 1.100, 1.350, 0.800, 2.520, 0.420, 1.300, 0.200, -0.330),
    (1.60, 1.150, 0.660, 1.070, 1.500, 0.820, 2.700, 0.440, 1.500, 0.250, -0.380),
    (0.60, 1.100, 0.680, 1.040, 1.600, 0.820, 2.980, 0.450, 1.700, 0.300, -0.400),
    (0.05, 1.090, 0.690, 1.040, 1.620, 0.820, 3.200, 0.450, 1.700, 0.320, -0.410),
    (-0.40, 1.080, 0.700, 1.035, 1.650, 0.820, 2.300, 0.450, 1.600, 0.400, -0.420),
    (-2.00, 1.090, 0.720, 1.050, 1.700, 0.850, 2.300, 0.450, 1.600, 0.400, -0.420),
    (-3.50, 1.100, 0.720, 1.060, 1.750, 0.880, 2.300, 0.450, 1.600, 0.400, -0.400),
    (-4.50, 1.100, 0.700, 1.060, 1.800, 0.920, 2.320, 0.550, 1.600, 0.450, -0.350),
    (-5.50, 1.080, 0.680, 1.050, 1.800, 0.950, 2.350, 0.700, 1.600, 0.500, -0.300),
    (-6.40, 1.030, 0.650, 1.000, 1.700, 0.980, 2.300, 0.800, 1.500, 0.600, -0.200),
    (-6.80, 0.970, 0.600, 0.950, 0.850, 0.900, 0.950, 0.700, 0.850, 0.300, -0.050),
    (-7.50, 0.900, 0.450, 0.880, 0.550, 0.800, 0.580, 0.650, 0.500, 0.450, 0.350),
    (-8.50, 0.820, 0.400, 0.800, 0.500, 0.740, 0.520, 0.650, 0.450, 0.520, 0.450),
    (-9.20, 0.760, 0.300, 0.740, 0.400, 0.700, 0.450, 0.640, 0.380, 0.560, 0.500),
    (-9.70, 0.700, 0.180, 0.680, 0.240, 0.650, 0.260, 0.620, 0.220, 0.580, 0.550),
    (-10.05, 0.620, 0.000, 0.620, 0.000, 0.620, 0.000, 0.620, 0.000, 0.620, 0.620),
]


def _col(i):
    return [(r[0], r[i]) for r in _T]


SPINE = Line(_col(1))
KEEL = Line(_col(10))
FUSELAGE = Body([
    Longeron("spine", 0.0, _col(1), full=1.10, n=6),
    Longeron("shoulder", _col(2), _col(3), full=1.05, n=4),
    Longeron("deck", _col(4), _col(5), full=1.0, n=5),
    Longeron("edge", _col(6), _col(7), full=1.0, n=5),
    Longeron("lower", _col(8), _col(9), full=1.05, n=5),
    Longeron("keel", 0.0, _col(10), n=1),
])


def fuselage_ring(y):
    FUSELAGE.L[3].sharp = -6.6 < y < 9.6               # the chines, the LEVCON, the glove: sharp edges
    FUSELAGE.L[1].sharp = 0.0 < y < 9.0                 # the flat sided top of the forebody
    return FUSELAGE.ring(y)


def fuselage_stations():
    return jk.stations([(Y_NOSE, 9.50, 0.05), (9.50, 4.50, 0.12), (4.50, 4.15, 0.05), (4.15, 0.05, 0.12),
                        (0.05, -6.40, 0.18), (-6.40, -7.50, 0.10), (-7.50, -10.05, 0.18)])


# ------------------------------------------------------------------ canopy: one piece bubble
Y_WS0, Y_WS1, Y_CAN1 = 7.65, 6.90, 4.30
CANOPY_TOP = Line([(7.65, 0.93), (7.40, 1.16), (7.00, 1.40), (6.50, 1.58), (6.00, 1.67), (5.50, 1.66), (5.00, 1.60),
                   (4.60, 1.50), (4.30, 1.40)])
CANOPY_SILL_Z = Line([(7.65, 0.92), (6.00, 0.99), (4.30, 1.09)])
CANOPY_SILL_X = Line([(7.65, 0.30), (7.20, 0.44), (6.50, 0.50), (5.00, 0.50), (4.60, 0.44), (4.30, 0.32)])
CANOPY_BULGE = Line([(7.65, 0.0), (7.2, 0.02), (6.5, 0.04), (5.5, 0.045), (4.7, 0.03), (4.30, 0.0)])


def canopy_half(y, n=14):
    zt, zs, xs = float(CANOPY_TOP(y)), float(CANOPY_SILL_Z(y)), float(CANOPY_SILL_X(y))
    bulge = float(CANOPY_BULGE(y))
    a = np.linspace(0.0, 0.5 * math.pi, n + 1)
    x = (xs + bulge) * np.sin(a) ** 0.85
    z = zs + (zt - zs) * np.cos(a) ** 1.10
    x[-1] = xs
    return np.stack([x, z], axis=1)


def canopy_stations():
    return jk.stations([(Y_WS0, Y_WS1, 0.06), (Y_WS1, Y_CAN1, 0.10)])


# ------------------------------------------------------------------ wing: 49 deg leading edge, trailing edge swept forward
Z_WING = 0.45
X_WTIP = 7.00
TAN_LE = math.tan(math.radians(49.0))


def wing_le(x):
    x = np.asarray(x, float)
    return np.where(x < 3.24, 0.05, 0.05 - (x - 3.24) * TAN_LE)


def wing_te(x):
    x = np.asarray(x, float)
    return -6.18 + (x - 3.24) * (6.18 - 5.60) / (6.60 - 3.24)


def wing_z(x):
    return Z_WING + 0.0 * np.asarray(x, float)


WING = Surface([
    (2.30, 0.05, float(wing_te(2.30)), Z_WING, 0.050),
    (3.24, 0.05, float(wing_te(3.24)), Z_WING, 0.050),
    (6.60, float(wing_le(6.60)), float(wing_te(6.60)), Z_WING, 0.035),
    (7.00, float(wing_le(7.00)), -5.09, Z_WING, 0.035),
], nc=20)
FLAP = (3.30, 5.00, 0.95, 0.85)
AIL = (5.00, 6.55, 0.85, 0.70)
LEF = (3.30, 6.90, 0.75, 0.40)

# ------------------------------------------------------------------ nacelles: widely spaced, raked trapezoid intakes
Y_FACE_TOP, Y_FACE_BOT = 3.20, 2.30
_N = [
    (2.30, 0.95, 1.98, 0.30, -0.30, 4.0),
    (1.50, 0.95, 2.00, 0.35, -0.45, 3.5),
    (0.50, 0.95, 2.02, 0.38, -0.58, 3.2),
    (-0.70, 0.95, 2.02, 0.40, -0.64, 3.0),
    (-1.70, 0.95, 2.00, 0.42, -0.60, 2.8),
    (-3.00, 0.94, 2.00, 0.44, -0.38, 2.6),
    (-4.50, 0.93, 2.02, 0.50, -0.20, 2.4),
    (-6.00, 0.93, 2.03, 0.85, -0.06, 2.2),
    (-6.60, 0.93, 2.03, 1.10, 0.00, 2.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = -6.60
DUCT_DEPTH = 1.8
NOZZLE = dict(x=1.48, z=0.55, y0=-6.60, y1=-8.30, r0=0.55, r1=0.50, petals=18)


def nacelle_rake(d):
    full = (Y_FACE_TOP - Y_FACE_BOT) / (0.30 + 0.30)
    return full * max(0.0, 1.0 - d / 1.4) ** 1.5


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, 0.8, 0.12), (0.8, -5.6, 0.40), (-5.6, Y_NAC1, 0.12)])


# ------------------------------------------------------------------ booms, fins (canted 25 deg), stabilators
BOOM = dict(x=2.28, z=0.74, hw=0.15, hh_up=0.20, hh_lo=0.24, y0=-5.20, y1=-8.95)
FIN_X, FIN_Z, FIN_CANT = 2.35, 1.02, 25.0
# the drawing's fin tip stands 4.47 m off the ground, the real jet is 4.6 m tall: the fin span is 2.25 m, not 1.93
FIN = [
    (0.00, -4.45, -7.32, 0.0, 0.040),
    (2.25, -6.88, -7.28, 0.0, 0.030),
]
RUDDER = (0.20, 2.05, 0.70, 0.28)
STAB_Z = 0.55
STAB = Surface([
    (2.20, -5.65, -8.66, STAB_Z, 0.040),
    (4.85, -7.62, -8.40, STAB_Z, 0.032),
    (5.00, -7.78, -8.15, STAB_Z, 0.030),
], airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = -7.00

# ------------------------------------------------------------------ landing gear
GEAR_NOSE = dict(y=3.42, x=0.0, r=0.33, w=0.18, twin=True)
GEAR_MAIN = dict(y=-2.60, x=1.85, r=0.52, w=0.32)
