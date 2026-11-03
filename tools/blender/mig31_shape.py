"""MiG-31 Foxhound: the shape (pure numpy), measured off its three-view (Wikimedia Commons "Mikoyan MiG-31 3-view";
36.36 px per metre: 22.69 m from the pitot tip to the nozzles, 13.46 m span - both the real figures).

Drawing pixels -> metres:  y = (430 - X) / 36.36   x = |Y - 1287| / 36.36 (top view; the front view, drawn turned on
its side, shares that centre line)   z = (930 - Y) / 36.36 (side view; the ground is at Y 1023).
The fins are stretched to the real 6.15 m height (the drawing's jet stands 5.6 m tall).

The MiG-31: a long round nose, the tandem two seat canopy, the huge raked box intakes on the sides of a broad, flat
topped fuselage, a shoulder wing with a small curved glove and 7 degrees of anhedral, twin fins canted out 6 degrees,
ventral fins, stabilators low on the rear fuselage, two big afterburner nozzles side by side.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "mig31"
Y_NOSE = 10.85
Y_PITOT = 11.52
Z_GROUND = -2.58

# y | spine z | shoulder (x, z) | upper side (x, z) | widest (x, z) | lower side (x, z) | keel z
_T = [
    (10.85, -0.450, 0.000, -0.450, 0.000, -0.450, 0.000, -0.450, 0.000, -0.450, -0.450),
    (10.50, -0.360, 0.106, -0.390, 0.140, -0.420, 0.150, -0.455, 0.106, -0.520, -0.550),
    (10.00, -0.270, 0.177, -0.320, 0.230, -0.380, 0.250, -0.445, 0.177, -0.570, -0.620),
    (9.50, -0.140, 0.270, -0.225, 0.350, -0.320, 0.380, -0.430, 0.270, -0.635, -0.720),
    (9.00, -0.020, 0.355, -0.135, 0.460, -0.260, 0.500, -0.410, 0.355, -0.690, -0.800),
    (8.50, 0.100, 0.430, -0.040, 0.555, -0.200, 0.600, -0.380, 0.430, -0.720, -0.860),
    (8.00, 0.220, 0.480, 0.050, 0.620, -0.140, 0.670, -0.350, 0.480, -0.750, -0.920),
    (7.30, 0.420, 0.580, 0.300, 0.730, 0.000, 0.760, -0.300, 0.620, -0.850, -0.970),
    (6.00, 0.580, 0.620, 0.480, 0.770, 0.100, 0.780, -0.300, 0.660, -0.920, -1.000),
    (5.00, 0.630, 0.640, 0.540, 0.780, 0.150, 0.780, -0.300, 0.680, -0.940, -1.020),
    (4.00, 0.670, 0.660, 0.580, 0.800, 0.250, 0.800, -0.300, 0.700, -0.950, -1.030),
    (3.10, 0.720, 0.680, 0.650, 0.840, 0.450, 0.860, 0.000, 0.720, -0.920, -1.040),
    (2.90, 0.950, 0.700, 0.850, 0.900, 0.700, 0.900, 0.300, 0.750, -0.900, -1.040),
    (2.00, 0.960, 0.750, 0.900, 1.000, 0.780, 1.000, 0.400, 0.750, -0.800, -1.040),
    (0.00, 0.970, 0.800, 0.920, 1.200, 0.820, 1.500, 0.620, 0.800, -0.500, -1.000),
    (-3.00, 0.960, 0.800, 0.920, 1.300, 0.820, 1.600, 0.620, 0.800, -0.500, -1.000),
    (-5.50, 0.930, 0.800, 0.900, 1.400, 0.820, 1.650, 0.650, 0.800, -0.500, -0.980),
    (-7.00, 0.880, 0.780, 0.860, 1.400, 0.800, 1.700, 0.700, 0.800, -0.500, -0.950),
    (-9.00, 0.820, 0.700, 0.800, 1.300, 0.760, 1.600, 0.650, 0.700, -0.400, -0.850),
    (-10.30, 0.720, 0.550, 0.700, 0.900, 0.600, 1.000, 0.450, 0.500, -0.300, -0.600),
    (-10.60, 0.550, 0.300, 0.520, 0.450, 0.420, 0.480, 0.300, 0.300, 0.000, -0.200),
    (-10.90, 0.250, 0.000, 0.250, 0.000, 0.250, 0.000, 0.250, 0.000, 0.250, 0.250),
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
    return jk.stations([(Y_NOSE, 10.0, 0.04), (10.0, 3.10, 0.13), (3.10, 2.90, 0.05), (2.90, -10.30, 0.25),
                        (-10.30, -10.90, 0.06)])


# ------------------------------------------------------------------ canopy: tandem, two hoods
Y_WS0, Y_WS1, Y_CAN1 = 7.30, 6.70, 2.90
CANOPY_TOP = Line([(7.30, 0.43), (7.00, 0.78), (6.70, 0.98), (6.30, 1.08), (5.80, 1.10), (5.20, 1.08), (4.60, 1.08),
                   (4.00, 1.06), (3.50, 1.01), (3.10, 0.97), (2.90, 0.95)])
CANOPY_SILL_Z = Line([(7.30, 0.42), (6.00, 0.57), (4.00, 0.66), (2.90, 0.72)])
CANOPY_SILL_X = Line([(7.30, 0.40), (6.80, 0.45), (4.00, 0.45), (3.20, 0.42), (2.90, 0.35)])
CANOPY_BULGE = Line([(7.30, 0.0), (6.8, 0.02), (6.0, 0.03), (4.0, 0.03), (3.2, 0.02), (2.90, 0.0)])
CANOPY_ARCHES = ((6.70, 0.030), (5.10, 0.040), (2.95, 0.035))


def canopy_half(y, n=14):
    zt, zs, xs = float(CANOPY_TOP(y)), float(CANOPY_SILL_Z(y)), float(CANOPY_SILL_X(y))
    bulge = float(CANOPY_BULGE(y))
    a = np.linspace(0.0, 0.5 * math.pi, n + 1)
    x = (xs + bulge) * np.sin(a) ** 0.80
    z = zs + (zt - zs) * np.cos(a) ** 1.15
    x[-1] = xs
    return np.stack([x, z], axis=1)


def canopy_stations():
    return jk.stations([(Y_WS0, Y_WS1, 0.06), (Y_WS1, Y_CAN1, 0.10)])


# ------------------------------------------------------------------ shoulder wing: curved glove, 43 deg, 7 deg anhedral
X_WROOT, X_WTIP = 1.70, 6.70
Z_WROOT = 0.62
ANHEDRAL = 7.0


def wing_z(x):
    x = np.asarray(x, float)
    return Z_WROOT - np.maximum(x - X_WROOT, 0.0) * math.tan(math.radians(ANHEDRAL))


_LE = jk.Lin([(1.70, 1.30), (2.00, 0.40), (2.55, -1.00), (6.70, -4.95)])
_TE = jk.Lin([(1.70, -6.70), (6.70, -6.95)])


def wing_le(x):
    return _LE(x)


def wing_te(x):
    return _TE(x)


WING = Surface([(x, float(_LE(x)), float(_TE(x)), float(wing_z(x)), t)
                for x, t in ((1.70, 0.045), (2.00, 0.045), (2.55, 0.045), (4.60, 0.040), (6.70, 0.035))], nc=20)
FLAP = (2.60, 4.50, 0.90, 0.80)
AIL = (4.50, 6.40, 0.75, 0.60)
LEF = (2.65, 6.60, 0.55, 0.40)

# ------------------------------------------------------------------ the intake boxes and the engine bodies behind them
Y_FACE_TOP, Y_FACE_BOT = 4.90, 2.00          # the intakes' sides are raked: the top lip far forward
_N = [
    (2.00, 0.80, 1.85, 0.80, -1.02, 6.0),
    (1.00, 0.70, 1.85, 0.78, -1.03, 5.0),
    (-1.00, 0.55, 1.85, 0.76, -1.05, 4.5),
    (-4.00, 0.45, 1.85, 0.74, -1.05, 4.0),
    (-7.00, 0.40, 1.82, 0.70, -1.02, 3.5),
    (-9.50, 0.38, 1.75, 0.45, -0.98, 2.8),
    (-10.45, 0.39, 1.71, 0.30, -1.00, 2.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = -10.45
DUCT_DEPTH = 2.4
NOZZLE = dict(x=1.05, z=-0.35, y0=-10.45, y1=-11.15, r0=0.66, r1=0.62, petals=20)


def nacelle_rake(d):
    full = (Y_FACE_TOP - Y_FACE_BOT) / (0.80 + 1.02)
    return full * max(0.0, 1.0 - d / 3.2) ** 1.4


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, 0.5, 0.15), (0.5, -9.5, 0.45), (-9.5, Y_NAC1, 0.12)])


# ------------------------------------------------------------------ tail: the fin and stabilator carriers, fins, ventrals, stabs
BOOM = dict(x=1.82, z=0.10, hw=0.18, hh_up=0.55, hh_lo=0.50, y0=-5.50, y1=-10.70)
FIN_X, FIN_Z, FIN_CANT = 1.70, 0.80, 6.0
# side view: root LE -5.70, root TE -9.85 at z 0.85; tip -9.0 .. -10.0 at z 3.05 - stretched to the real height
FIN = [
    (0.00, -5.70, -9.85, 0.0, 0.040),
    (0.45, -6.40, -9.90, 0.0, 0.040),
    (2.76, -9.25, -10.25, 0.0, 0.032),
]
RUDDER = (0.35, 2.45, 0.90, 0.75)
VENTRAL = dict(x=1.30, z=-1.00, cant=15.0, sections=[(0.0, -6.00, -9.60, 0.0, 0.05), (0.82, -9.05, -9.45, 0.0, 0.05)])
STAB_Z = -0.45
STAB = Surface([
    (1.95, -8.30, -10.60, STAB_Z, 0.040),
    (4.15, -10.25, -10.92, STAB_Z, 0.035),
    (4.30, -10.45, -10.90, STAB_Z, 0.035),
], airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = -9.60

# ------------------------------------------------------------------ landing gear
GEAR_NOSE = dict(y=3.95, x=0.0, r=0.38, w=0.20, twin=True)
GEAR_MAIN = dict(y=-3.00, x=1.82, r=0.48, w=0.30, tandem=0.42)
