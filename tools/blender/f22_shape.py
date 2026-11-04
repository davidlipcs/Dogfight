"""F-22A Raptor: the shape (pure numpy), measured off its three-view (38.1 px per metre: the 18.92 m length and the
13.56 m span both fit; the 5.08 m height with the gear down too).

Drawing -> model:  top view (nose to the right, tip X 738, centre line Y 1105): y_drawing = (X - 738) / 38.1;
side view (nose to the left, tip X 328, axis Y 890): y_drawing = (328 - X) / 38.1, z = (890 - Y) / 38.1;
model y = 9.62 + y_drawing (the frame of the game's earlier F-22, so its weapon stations stay where they were).

The Raptor: the chined nose, the big one piece canopy, the caret intakes raked back, the diamond wing (42 degree
leading edge, the trailing edge swept forward outboard), two fins canted 28 degrees, the stabilators beside the flat
two-dimensional nozzles, the main weapons bay under the body and a side bay in each intake trunk.
"""

import numpy as np

import jk
import jk_std

NAME = "f22"
Y0 = 9.62
Y_NOSE = Y0
Y_PITOT = Y0
Z_GROUND = -1.85

_D = [
    # y_drw  spine  shoul x z     upper x z      edge x z       lower x z      keel
    (0.00,  0.000, 0.00, 0.000, 0.00, 0.000, 0.00, 0.000, 0.00, 0.000, 0.000),
    (-0.50, 0.120, 0.10, 0.090, 0.14, 0.040, 0.16, -0.020, 0.12, -0.100, -0.160),
    (-1.00, 0.270, 0.20, 0.200, 0.28, 0.100, 0.33, -0.040, 0.24, -0.200, -0.290),
    (-2.00, 0.500, 0.34, 0.390, 0.50, 0.200, 0.60, -0.080, 0.42, -0.340, -0.450),
    (-3.00, 0.700, 0.40, 0.580, 0.62, 0.280, 0.82, -0.100, 0.52, -0.440, -0.580),
    (-4.00, 0.800, 0.44, 0.680, 0.70, 0.320, 1.02, -0.110, 0.58, -0.500, -0.660),
    (-5.00, 0.880, 0.48, 0.760, 0.78, 0.350, 1.30, -0.120, 0.60, -0.560, -0.840),
    (-6.00, 0.950, 0.50, 0.830, 0.90, 0.380, 1.85, -0.050, 0.65, -0.600, -0.840),
    (-7.00, 1.000, 0.55, 0.880, 1.00, 0.400, 2.15, 0.000, 0.70, -0.620, -0.840),
    (-8.00, 0.940, 0.60, 0.860, 1.15, 0.400, 2.30, 0.050, 0.80, -0.680, -0.750),
    (-9.50, 0.900, 0.65, 0.840, 1.25, 0.400, 2.40, 0.050, 0.85, -0.700, -0.750),
    (-11.00, 0.870, 0.68, 0.820, 1.30, 0.400, 2.40, 0.050, 0.88, -0.690, -0.740),
    (-12.50, 0.850, 0.70, 0.800, 1.35, 0.400, 2.30, 0.050, 0.90, -0.600, -0.660),
    (-13.50, 0.820, 0.70, 0.780, 1.40, 0.400, 2.20, 0.050, 0.90, -0.420, -0.560),
    (-15.00, 0.700, 0.70, 0.660, 1.40, 0.350, 2.00, 0.050, 0.90, -0.300, -0.380),
    (-16.00, 0.520, 0.68, 0.490, 1.30, 0.290, 1.72, 0.050, 0.85, -0.200, -0.250),
    (-16.60, 0.420, 0.45, 0.390, 0.80, 0.240, 0.95, 0.050, 0.62, -0.080, -0.130),
    (-17.20, 0.300, 0.15, 0.290, 0.22, 0.250, 0.25, 0.150, 0.20, 0.060, 0.050),
    (-17.70, 0.200, 0.00, 0.200, 0.00, 0.200, 0.00, 0.200, 0.00, 0.200, 0.200),
]
_T = [(Y0 + r[0],) + tuple(r[1:]) for r in _D]
fuselage_ring, SPINE, KEEL = jk_std.fuselage(_T, sharp=(Y0 - 16.6, Y0 - 0.3), sharp_top=(Y0 - 9.0, Y0 - 1.0))


def fuselage_stations():
    return jk.stations([(Y_NOSE, Y0 - 1.0, 0.05), (Y0 - 1.0, Y0 - 16.0, 0.15), (Y0 - 16.0, Y0 - 17.7, 0.10)])


jk_std.Canopy(Y0 - 2.30, Y0 - 3.10, Y0 - 6.30,
              top=[(Y0 - 2.30, 0.66), (Y0 - 2.70, 0.92), (Y0 - 3.10, 1.13), (Y0 - 3.60, 1.33), (Y0 - 4.30, 1.50),
                   (Y0 - 5.00, 1.46), (Y0 - 5.60, 1.32), (Y0 - 6.00, 1.18), (Y0 - 6.30, 1.06)],
              sill_z=[(Y0 - 2.30, 0.65), (Y0 - 4.30, 0.78), (Y0 - 6.30, 0.92)],
              sill_x=[(Y0 - 2.30, 0.28), (Y0 - 2.80, 0.42), (Y0 - 3.60, 0.50), (Y0 - 5.40, 0.50), (Y0 - 6.00, 0.40),
                      (Y0 - 6.30, 0.30)],
              bulge=[(Y0 - 2.30, 0.0), (Y0 - 3.0, 0.03), (Y0 - 4.3, 0.05), (Y0 - 5.6, 0.03), (Y0 - 6.30, 0.0)]).export(globals())
CANOPY_ARCHES = ((Y0 - 6.25, 0.035),)

jk_std.wing(globals(), le=[(2.20, Y0 - 7.60), (6.78, Y0 - 12.82)], te=[(2.20, Y0 - 15.40), (3.20, Y0 - 15.40), (6.78, Y0 - 13.95)],
            z=lambda x: 0.35 - 0.057 * np.maximum(np.asarray(x, float) - 2.2, 0.0),
            t=[(2.20, 0.050), (6.78, 0.035)], x_tip=6.78)
FLAP = (2.30, 4.00, 0.95, 0.80)          # the flaperons
AIL = (4.00, 6.20, 0.70, 0.55)
LEF = (2.40, 6.70, 0.55, 0.35)

# the caret intakes, raked back from the top; the side bays in their lower outer corners
Y_FACE_TOP, Y_FACE_BOT = Y0 - 5.00, Y0 - 6.40
_N = [
    (Y0 - 6.40, 0.70, 1.95, 0.40, -0.80, 3.0),
    (Y0 - 7.50, 0.70, 2.00, 0.40, -0.82, 3.0),
    (Y0 - 9.50, 0.75, 1.80, 0.40, -0.80, 3.0),
    (Y0 - 11.50, 0.80, 1.60, 0.40, -0.70, 3.0),
]
NACELLE = [jk.Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = Y0 - 11.50
DUCT_DEPTH = 1.8
NOZZLE = dict(x=0.66, z=0.02, y0=Y0 - 16.60, y1=Y0 - 17.60, r0=0.52, r1=0.45, hw=0.56, hh=0.36, n=6.0, petals=4)


def nacelle_rake(d):
    return (Y_FACE_TOP - Y_FACE_BOT) / (0.40 + 0.80) * max(0.0, 1.0 - d / 1.6) ** 1.3


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, Y0 - 11.50, 0.20)])


# the weapons bays: the main bay between the trunks, a side bay in each trunk (right side; the left is mirrored)
MAIN_BAY = (0.0, 0.80, Y0 - 12.37, Y0 - 8.37)
SIDE_BAY = (1.06, 1.40, Y0 - 9.72, Y0 - 7.22)
BAY_ROOF = -0.30
HOLES = [(MAIN_BAY[0], MAIN_BAY[1], MAIN_BAY[2], MAIN_BAY[3], -0.55),
         (SIDE_BAY[0], SIDE_BAY[1], SIDE_BAY[2], SIDE_BAY[3], -0.55)]

BOOM = None
FIN_X, FIN_Z, FIN_CANT = 2.05, 0.85, 28.0
FIN = [(0.00, Y0 - 13.30, Y0 - 16.90, 0.0, 0.040), (2.75, Y0 - 14.85, Y0 - 15.95, 0.0, 0.030)]
RUDDER = (0.25, 2.35, 0.75, 0.55)
STAB_Z = 0.15
STAB = jk.Surface([(1.90, Y0 - 15.50, Y0 - 18.85, STAB_Z, 0.040), (4.48, Y0 - 17.20, Y0 - 18.40, STAB_Z, 0.032)],
                  airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = Y0 - 17.00

GEAR_NOSE = dict(y=Y0 - 5.65, x=0.0, r=0.28, w=0.17, twin=False)
GEAR_MAIN = dict(y=Y0 - 11.80, x=1.60, r=0.45, w=0.30)
