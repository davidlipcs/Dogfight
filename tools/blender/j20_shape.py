"""Chengdu J-20: the shape (pure numpy), measured off the "Chengdu J-20 Black Eagle" three-view (40.3 px per metre:
the 20.3 m from the radome tip to the nozzles; the 13.1 m span agrees with the published 12.9-13.5 m).

Drawing pixels -> metres:  top view y = (X - 520) / 40.3, x = |Y - 1012| / 40.3 (nose to the right);
side view y = (X - 515) / 40.3, z = (690 - Y) / 40.3.  The ground is set for the real 4.45 m height.

The J-20: a long chined nose, the bubble canopy, the side DSI intakes with the canards on top of them, the LERX
running from the canards into the 48 degree delta, a wide flat body, two all-moving fins canted 24 degrees on short
tail booms, ventral fins under them, two nozzles close together.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "j20"
Y_NOSE = 10.05
Y_PITOT = 11.20
Z_GROUND = -2.15

# y | spine z | shoulder (x, z) | upper deck (x, z) | edge: chine -> LERX -> (wing) (x, z) | lower (x, z) | keel z
_T = [
    (10.05, -0.220, 0.000, -0.220, 0.000, -0.220, 0.000, -0.220, 0.000, -0.220, -0.220),
    (9.80, -0.120, 0.080, -0.140, 0.110, -0.180, 0.120, -0.215, 0.080, -0.300, -0.330),
    (9.50, -0.030, 0.150, -0.070, 0.210, -0.140, 0.250, -0.205, 0.150, -0.370, -0.410),
    (8.50, 0.200, 0.250, 0.120, 0.360, -0.040, 0.420, -0.180, 0.260, -0.520, -0.560),
    (7.50, 0.400, 0.320, 0.300, 0.460, 0.080, 0.550, -0.150, 0.340, -0.620, -0.660),
    (6.60, 0.570, 0.360, 0.460, 0.520, 0.200, 0.620, -0.120, 0.400, -0.700, -0.730),
    (5.50, 0.650, 0.390, 0.550, 0.560, 0.260, 0.680, -0.080, 0.440, -0.760, -0.790),
    (4.40, 0.700, 0.420, 0.610, 0.640, 0.300, 0.800, -0.040, 0.480, -0.800, -0.830),
    (3.50, 0.720, 0.460, 0.630, 0.780, 0.300, 1.300, 0.150, 0.560, -0.860, -0.900),
    (3.00, 0.740, 0.480, 0.640, 0.850, 0.290, 1.650, 0.170, 0.620, -0.900, -0.950),
    (1.00, 0.720, 0.520, 0.630, 1.000, 0.280, 2.000, 0.150, 0.750, -1.000, -1.050),
    (-1.00, 0.710, 0.560, 0.620, 1.100, 0.270, 2.200, 0.120, 0.850, -1.050, -1.120),
    (-3.00, 0.700, 0.580, 0.610, 1.150, 0.260, 2.350, 0.100, 0.900, -1.080, -1.150),
    (-5.00, 0.700, 0.580, 0.610, 1.150, 0.260, 2.350, 0.100, 0.900, -1.050, -1.120),
    (-7.50, 0.620, 0.550, 0.550, 1.100, 0.230, 2.250, 0.080, 0.900, -0.900, -0.980),
    (-8.50, 0.550, 0.520, 0.490, 1.050, 0.200, 1.900, 0.050, 0.850, -0.750, -0.780),
    (-9.30, 0.420, 0.480, 0.380, 0.950, 0.150, 1.550, 0.000, 0.800, -0.650, -0.680),
    (-9.70, 0.250, 0.300, 0.230, 0.500, 0.100, 0.600, -0.050, 0.450, -0.500, -0.550),
    (-9.95, 0.050, 0.000, 0.050, 0.000, 0.050, 0.000, 0.050, 0.000, 0.050, 0.050),
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
    FUSELAGE.L[3].sharp = -9.0 < y < 9.9              # the chine, the LERX: a sharp edge all along
    FUSELAGE.L[1].sharp = 0.0 < y < 8.5
    return FUSELAGE.ring(y)


def fuselage_stations():
    return jk.stations([(Y_NOSE, 9.50, 0.05), (9.50, 3.50, 0.13), (3.50, -9.30, 0.18), (-9.30, -9.95, 0.06)])


# ------------------------------------------------------------------ canopy
Y_WS0, Y_WS1, Y_CAN1 = 6.65, 6.10, 4.05
CANOPY_TOP = Line([(6.65, 0.60), (6.40, 0.86), (6.10, 1.04), (5.70, 1.16), (5.20, 1.17), (4.70, 1.10), (4.35, 0.98),
                   (4.05, 0.84)])
CANOPY_SILL_Z = Line([(6.65, 0.59), (5.50, 0.66), (4.05, 0.71)])
CANOPY_SILL_X = Line([(6.65, 0.30), (6.30, 0.38), (5.60, 0.41), (4.70, 0.40), (4.30, 0.35), (4.05, 0.26)])
CANOPY_BULGE = Line([(6.65, 0.0), (6.3, 0.02), (5.5, 0.035), (4.6, 0.03), (4.05, 0.0)])


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


# ------------------------------------------------------------------ delta wing (48 deg)
Z_WING = 0.10
X_WTIP = 6.55
_LE = jk.Lin([(2.25, -1.20), (6.55, -6.35)])
_TE = jk.Lin([(2.25, -8.25), (6.55, -7.75)])


def wing_le(x):
    return _LE(x)


def wing_te(x):
    return _TE(x)


def wing_z(x):
    return Z_WING + 0.0 * np.asarray(x, float)


WING = Surface([(x, float(_LE(x)), float(_TE(x)), Z_WING, t) for x, t in ((2.25, 0.045), (4.40, 0.040), (6.55, 0.032))],
               nc=20)
FLAP = (2.40, 4.40, 0.95, 0.80)
AIL = (4.40, 6.30, 0.80, 0.55)
LEF = (2.60, 6.40, 0.50, 0.30)

# ------------------------------------------------------------------ canards on the intakes
CANARD_Z = 0.25
CANARD = Surface([
    (1.90, 3.50, 0.80, CANARD_Z, 0.040),
    (4.00, 1.25, 0.50, CANARD_Z, 0.030),
], airfoil=jk.biconvex_t, nc=12)
CANARD_PIVOT = 1.60

# ------------------------------------------------------------------ the DSI intakes (raked: the top lip forward)
Y_FACE_TOP, Y_FACE_BOT = 4.00, 3.25
_N = [
    (3.25, 0.72, 1.45, 0.18, -0.90, 3.4),
    (2.40, 0.74, 1.80, 0.20, -0.95, 3.2),
    (1.00, 0.76, 1.90, 0.18, -1.00, 3.0),
    (-1.00, 0.80, 1.90, 0.14, -1.05, 3.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = -1.00
DUCT_DEPTH = 1.6
NOZZLE = dict(x=0.92, z=-0.20, y0=-9.55, y1=-10.15, r0=0.56, r1=0.52, petals=16)


def nacelle_rake(d):
    full = (Y_FACE_TOP - Y_FACE_BOT) / (0.18 + 0.90)
    return full * max(0.0, 1.0 - d / 1.6) ** 1.4


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, -1.00, 0.18)])


# ------------------------------------------------------------------ tail booms, canted all-moving fins, ventral fins
BOOM = dict(x=2.10, z=0.25, hw=0.16, hh_up=0.30, hh_lo=0.35, y0=-6.80, y1=-10.70)
FIN_X, FIN_Z, FIN_CANT = 2.15, 0.55, 24.0
FIN = [
    (0.00, -7.90, -10.40, 0.0, 0.040),
    (1.80, -10.00, -11.30, 0.0, 0.030),
]
RUDDER = (0.15, 1.65, 1.10, 0.75)
VENTRAL = dict(x=1.70, z=-0.55, cant=28.0, sections=[(0.0, -8.10, -10.30, 0.0, 0.045), (0.85, -9.50, -10.40, 0.0, 0.040)])

# ------------------------------------------------------------------ landing gear
GEAR_NOSE = dict(y=5.40, x=0.0, r=0.30, w=0.18, twin=False)
GEAR_MAIN = dict(y=-2.80, x=1.45, r=0.45, w=0.30)
