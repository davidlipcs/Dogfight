"""MiG-29 (9.12) Fulcrum: the shape, measured off the MiG-29UB three-view (1/72, its scale bar: 55.3 px per metre on the
reference scan), with the single seat canopy of the 9.12 taken from photographs.

How the numbers were read (image pixels of the reference scan -> model metres):
  top view:   y = 0.90 + (598 - X) / 55.3      x = |Y - 927| / 55.3
  side view:  y = 0.90 + (604 - X) / 55.3      z = (1405 - Y) / 55.3     (z = 0: the wing chord plane)
  sections A' (y 6.40), B' (5.22), C' (4.41), D' (2.69): the shapes of the forebody, the cockpit walls and the LERX.

Real figures for the check: length 17.32 m with the pitot, span 11.36 m, wing sweep 42 degrees, anhedral 2 degrees.

Pure numpy: build_mig29.py turns it into Blender objects, preview.py into a quick mesh.
"""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron, Surface

NAME = "mig29"
Y_NOSE = 8.95             # radome tip
Y_PITOT = 9.90            # pitot tip
Z_GROUND = -1.99          # side view ground line (Y 1515)

# ------------------------------------------------------------------ fuselage longerons
# columns: y | spine z | upper shoulder (x, z) | LERX root / wall foot (x, z) | edge (x, z) | lower side (x, z) | keel z
# nose: a round section (A'); cockpit: vertical walls (B', C') under the canopy; LERX: the thin sloping blade with a
# sharp edge (C', D'); over the wing the edge hides inside the wing root; aft: the low deck over the nacelles
# between the fin booms, closing on the brake chute cone.
_T = [
    # y      sp     x1    z1     x2    z2     x3    z3     x4    z4     keel
    (8.95,  0.045, 0.00, 0.045, 0.00, 0.045, 0.00, 0.045, 0.00, 0.045, 0.040),
    (8.82,  0.140, 0.08, 0.120, 0.10, 0.090, 0.11, 0.060, 0.08, 0.000, -0.030),
    (8.64,  0.215, 0.12, 0.175, 0.15, 0.115, 0.165, 0.065, 0.12, -0.030, -0.070),
    (8.46,  0.270, 0.16, 0.215, 0.205, 0.140, 0.22, 0.070, 0.16, -0.075, -0.125),
    (8.28,  0.310, 0.20, 0.245, 0.250, 0.160, 0.27, 0.075, 0.19, -0.110, -0.170),
    (8.10,  0.350, 0.23, 0.275, 0.300, 0.175, 0.33, 0.080, 0.23, -0.135, -0.200),
    (7.74,  0.450, 0.28, 0.345, 0.365, 0.205, 0.40, 0.085, 0.28, -0.170, -0.250),
    (7.37,  0.550, 0.33, 0.415, 0.430, 0.235, 0.47, 0.090, 0.33, -0.190, -0.265),
    (7.00,  0.610, 0.345, 0.460, 0.450, 0.250, 0.49, 0.090, 0.345, -0.200, -0.275),
    (6.40,  0.700, 0.345, 0.540, 0.455, 0.270, 0.49, 0.090, 0.345, -0.210, -0.300),
    (5.85,  0.740, 0.420, 0.720, 0.485, 0.200, 0.55, 0.090, 0.42, -0.170, -0.310),
    (5.20,  0.800, 0.460, 0.780, 0.500, 0.150, 0.67, 0.085, 0.47, -0.120, -0.330),
    (4.84,  0.830, 0.465, 0.810, 0.505, 0.200, 0.76, 0.083, 0.50, -0.110, -0.340),
    (4.30,  0.870, 0.465, 0.850, 0.520, 0.330, 0.92, 0.080, 0.55, -0.100, -0.340),
    (3.76,  0.900, 0.465, 0.880, 0.535, 0.430, 1.08, 0.075, 0.60, -0.110, -0.300),
    (3.40,  0.925, 0.465, 0.905, 0.545, 0.480, 1.18, 0.071, 0.65, -0.115, -0.275),
    (3.25,  1.040, 0.440, 0.990, 0.548, 0.500, 1.23, 0.070, 0.67, -0.118, -0.262),
    (3.03,  1.030, 0.440, 0.985, 0.550, 0.520, 1.28, 0.068, 0.70, -0.120, -0.250),
    (2.67,  1.000, 0.440, 0.960, 0.560, 0.560, 1.39, 0.060, 0.75, -0.120, -0.230),
    (2.31,  0.975, 0.450, 0.930, 0.580, 0.520, 1.48, 0.050, 0.80, -0.120, -0.220),
    (1.95,  0.930, 0.460, 0.880, 0.620, 0.470, 1.57, 0.040, 0.85, -0.120, -0.220),
    (1.59,  0.870, 0.470, 0.820, 0.680, 0.400, 1.63, 0.030, 0.90, -0.120, -0.220),
    (1.23,  0.790, 0.480, 0.740, 0.740, 0.330, 1.68, 0.020, 0.95, -0.120, -0.220),
    (0.90,  0.690, 0.490, 0.640, 0.800, 0.250, 1.58, 0.000, 1.00, -0.110, -0.220),
    (0.50,  0.600, 0.500, 0.550, 0.850, 0.190, 1.55, 0.000, 1.00, -0.100, -0.220),
    (0.00,  0.480, 0.500, 0.440, 0.900, 0.140, 1.55, 0.000, 1.00, -0.100, -0.220),
    (-0.50, 0.370, 0.500, 0.340, 0.950, 0.110, 1.55, 0.000, 1.00, -0.100, -0.220),
    (-1.00, 0.280, 0.500, 0.255, 0.980, 0.095, 1.55, 0.000, 1.00, -0.100, -0.220),
    (-1.50, 0.190, 0.490, 0.175, 1.000, 0.085, 1.55, 0.000, 1.00, -0.100, -0.220),
    (-2.00, 0.130, 0.480, 0.120, 1.000, 0.075, 1.55, 0.000, 1.00, -0.100, -0.220),
    (-2.50, 0.090, 0.470, 0.085, 1.000, 0.065, 1.55, 0.005, 1.00, -0.100, -0.220),
    (-3.06, 0.050, 0.460, 0.050, 1.000, 0.060, 1.55, 0.010, 1.00, -0.100, -0.220),
    (-3.40, 0.035, 0.450, 0.035, 1.000, 0.055, 1.70, 0.020, 1.10, -0.090, -0.220),
    (-4.00, 0.000, 0.440, 0.000, 1.000, 0.040, 1.70, 0.020, 1.10, -0.090, -0.210),
    (-4.60, -0.035, 0.400, -0.040, 1.000, 0.010, 1.70, 0.020, 1.10, -0.090, -0.200),
    (-4.90, -0.055, 0.320, -0.060, 0.700, -0.020, 1.00, -0.010, 0.70, -0.080, -0.185),
    (-5.10, -0.075, 0.180, -0.080, 0.300, -0.060, 0.33, -0.080, 0.25, -0.110, -0.160),
    (-5.30, -0.100, 0.060, -0.100, 0.090, -0.110, 0.10, -0.120, 0.07, -0.130, -0.140),
    (-5.40, -0.120, 0.000, -0.120, 0.000, -0.120, 0.00, -0.120, 0.00, -0.120, -0.120),
]
_A = np.array(_T)


def _col(i):
    return [(r[0], r[i]) for r in _T]


Y_LERX0 = 6.40            # the LERX edge leaves the round forebody here
SPINE = Line(_col(1))
KEEL = Line(_col(10))


def _edge_sharp(y):
    return y < Y_LERX0


FUSELAGE = Body([
    Longeron("spine", 0.0, _col(1), full=1.17, n=5),
    Longeron("shoulder", _col(2), _col(3), full=1.05, n=4),
    Longeron("wall_foot", _col(4), _col(5), full=1.0, n=4),
    Longeron("edge", _col(6), _col(7), full=1.05, n=5),
    Longeron("lower", _col(8), _col(9), full=1.17, n=5),
    Longeron("keel", 0.0, _col(10), n=1),
])
FUSELAGE.L[3].sharp = False                  # set per station in fuselage_ring()


def fuselage_ring(y):
    FUSELAGE.L[3].sharp = _edge_sharp(y)
    return FUSELAGE.ring(y)


def fuselage_stations():
    return jk.stations([(Y_NOSE, 8.40, 0.03), (8.40, 7.40, 0.08), (7.40, 6.40, 0.12), (6.40, 3.00, 0.12),
                        (3.00, 0.90, 0.12), (0.90, -3.06, 0.15), (-3.06, -4.60, 0.12), (-4.60, -5.40, 0.05)])


# ------------------------------------------------------------------ canopy (single seat 9.12: windscreen + one piece hood)
Y_WS0, Y_WS1, Y_CAN1 = 5.95, 5.30, 3.25       # windscreen base, windscreen / hood joint, hood rear end
CANOPY_TOP = Line([(5.95, 0.745), (5.80, 0.93), (5.60, 1.11), (5.30, 1.28), (5.00, 1.38), (4.60, 1.44), (4.20, 1.45),
                   (3.85, 1.41), (3.60, 1.32), (3.40, 1.19), (3.25, 1.07)])
CANOPY_SILL_Z = Line([(5.95, 0.740), (5.30, 0.800), (4.40, 0.870), (3.60, 0.925), (3.25, 0.945)])
CANOPY_SILL_X = Line([(5.95, 0.30), (5.70, 0.40), (5.30, 0.445), (4.60, 0.455), (3.80, 0.45), (3.45, 0.40), (3.25, 0.30)])
CANOPY_BULGE = Line([(5.95, 0.0), (5.60, 0.015), (5.1, 0.035), (4.3, 0.045), (3.6, 0.03), (3.25, 0.0)])


def canopy_half(y, n=14):
    """Right half of the glass at station y: from the top centre down to the sill (x, z)."""
    zt, zs, xs = float(CANOPY_TOP(y)), float(CANOPY_SILL_Z(y)), float(CANOPY_SILL_X(y))
    bulge = float(CANOPY_BULGE(y))
    a = np.linspace(0.0, 0.5 * math.pi, n + 1)
    x = (xs + bulge) * np.sin(a) ** 0.85
    z = zs + (zt - zs) * np.cos(a) ** 1.10
    x[-1] = xs
    return np.stack([x, z], axis=1)


def canopy_stations():
    return jk.stations([(Y_WS0, Y_WS1, 0.05), (Y_WS1, Y_CAN1, 0.08)])


# ------------------------------------------------------------------ wing (42 deg leading edge, 2 deg anhedral)
DIHEDRAL = -2.0
X_WROOT, X_WTIP = 1.40, 5.75


def wing_le(x):
    return 0.90 - 0.90 * (np.asarray(x, float) - 2.04)


def wing_te(x):
    return -3.06 - 0.185 * (np.asarray(x, float) - 2.04)


def wing_z(x):
    return (np.asarray(x, float) - 1.55) * math.tan(math.radians(DIHEDRAL)) * (np.asarray(x, float) > 1.55)


WING = Surface([
    (1.40, float(wing_le(1.40)), float(wing_te(1.40)), 0.0, 0.055),
    (1.70, float(wing_le(1.70)), float(wing_te(1.70)), 0.0, 0.055),
    (3.70, float(wing_le(3.70)), float(wing_te(3.70)), float(wing_z(3.70)), 0.047),
    (5.55, float(wing_le(5.55)), float(wing_te(5.55)), float(wing_z(5.55)), 0.040),
    (5.68, float(wing_le(5.68)) - 0.06, float(wing_te(5.68)), float(wing_z(5.68)), 0.040),
    (5.75, float(wing_le(5.75)) - 0.20, float(wing_te(5.75)) + 0.02, float(wing_z(5.75)), 0.040),
], nc=20)
FLAP = (1.72, 3.66, 0.70, 0.62)       # x0, x1, chord at x0, chord at x1 (metres)
AIL = (3.70, 5.30, 0.58, 0.48)
LEF = (1.72, 5.50, 0.42, 0.30)        # leading edge flap: chord in metres

# ------------------------------------------------------------------ engine nacelles (under the LERX and the wing)
# the intake face is raked: its top (under the LERX) at y 4.23, its lower lip at y 2.06 (side view)
Y_FACE_TOP, Y_FACE_BOT = 4.23, 2.06
# (y at the bottom of the ring, inner x, outer x, top z, bottom z, roundness)
_N = [
    (2.06, 0.58, 1.20, -0.08, -1.08, 4.0),
    (1.70, 0.56, 1.28, -0.08, -1.15, 3.6),
    (1.00, 0.53, 1.40, -0.08, -1.21, 3.2),
    (0.00, 0.50, 1.48, -0.08, -1.25, 3.0),
    (-1.50, 0.49, 1.49, -0.08, -1.26, 2.9),
    (-3.00, 0.49, 1.49, -0.08, -1.27, 2.8),
    (-3.90, 0.50, 1.48, -0.12, -1.27, 2.6),
    (-4.50, 0.51, 1.47, -0.20, -1.25, 2.3),
    (-5.07, 0.52, 1.46, -0.27, -1.21, 2.0),
]
NACELLE = [Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = -5.07
NOZZLE = dict(x=0.99, z=-0.74, y0=-5.07, y1=-5.85, r0=0.47, r1=0.43, petals=16)


def nacelle_rake(d):
    """Metres the ring at depth d (behind the lower lip) leans forward per metre up."""
    full = (Y_FACE_TOP - Y_FACE_BOT) / (1.08 - 0.08)
    return full * max(0.0, 1.0 - d / 1.8) ** 1.5


# ------------------------------------------------------------------ fin booms, fins, stabilators
BOOM = dict(x=1.81, z=-0.10, hw=0.10, hh_up=0.22, hh_lo=0.24, y0=-2.40, y1=-6.55)
FIN_X, FIN_Z, FIN_CANT = 1.81, 0.06, 6.0
# side view: root LE (fillet) y -1.65 at z 0.09, LE kink -3.19 at 0.54, LE tip -5.50 at 2.48, tip TE -6.08 at 2.21,
# TE root -5.86 at 0.18; span = height / cos(cant)
# The drawing's fin tip stands 4.47 m off the ground, the real jet 4.73 m (and the photographs agree with the real
# figure): the fin heights are stretched by FIN_STRETCH, its stations stay where the drawing has them.
_c = math.cos(math.radians(FIN_CANT))
FIN_STRETCH = (2.74 - FIN_Z) / (2.48 - FIN_Z)
FIN = [
    (0.00, -1.65, -5.86, 0.0, 0.045),
    ((0.54 - FIN_Z) / _c * FIN_STRETCH, -3.19, -5.90, 0.0, 0.045),
    ((2.21 - FIN_Z) / _c * FIN_STRETCH, -5.27, -6.08, 0.0, 0.035),
    ((2.48 - FIN_Z) / _c * FIN_STRETCH, -5.50, -5.66, 0.0, 0.030),
]
RUDDER = (0.28, 2.20, 0.58, 0.48)      # span from, to; chord there
STAB = Surface([
    (1.82, -3.91, -6.47, -0.12, 0.045),
    (3.70, -6.07, -7.33, -0.12, 0.035),
    (3.82, -6.22, -7.37, -0.12, 0.035),
    (3.89, -6.40, -7.36, -0.12, 0.035),
], airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = -5.10

# ------------------------------------------------------------------ landing gear (side view)
GEAR_NOSE = dict(y=3.05, x=0.0, r=0.27, w=0.18, twin=True)
GEAR_MAIN = dict(y=-0.82, x=1.30, r=0.42, w=0.28)
