"""F-15EX Eagle II: the shape (pure numpy), measured off A. V. Khaustov's F-15E Strike Eagle drawing (Aviatsiya i
Vremya 2/2004; its scale bar: 25.7 px per metre - the 19.43 m and the 13.05 m of its table both fit).  The EX is the
E airframe: two seats, the conformal fuel tanks along the intakes.

Drawing -> model:  top view (nose to the right, tip at X 512, centre line Y 1096.5): y_drawing = (X - 512) / 25.7;
side view (nose to the left, tip at X 12, Y 909): y_drawing = (12 - X) / 25.7, z = (909 - Y) / 25.7;
model y = 9.90 + y_drawing.  Ground for the real 5.63 m height.

The Eagle: the long pointed nose, the big two seat canopy, the huge raked rectangular intakes on the sides with the
conformal tanks behind them, the high 45 degree cropped delta wing, the tail booms carrying the two upright fins and
the stabilators, two F110 nozzles side by side.
"""

import numpy as np

import jk
import jk_std

NAME = "f15"
Y0 = 9.90
Y_NOSE = Y0
Y_PITOT = Y0
Z_GROUND = -1.86

_D = [
    # y_drw  spine  shoul x z     upper x z      edge x z       lower x z      keel
    (0.00,  0.000, 0.00, 0.000, 0.00, 0.000, 0.00, 0.000, 0.00, 0.000, 0.000),
    (-0.50, 0.280, 0.12, 0.240, 0.19, 0.140, 0.21, 0.000, 0.15, -0.140, -0.180),
    (-1.50, 0.620, 0.25, 0.520, 0.38, 0.300, 0.42, 0.100, 0.32, -0.220, -0.350),
    (-2.30, 0.820, 0.30, 0.700, 0.45, 0.450, 0.52, 0.150, 0.40, -0.250, -0.390),
    (-3.10, 1.020, 0.33, 0.920, 0.50, 0.650, 0.58, 0.250, 0.45, -0.250, -0.420),
    (-4.50, 1.080, 0.36, 0.980, 0.54, 0.750, 0.62, 0.350, 0.48, -0.300, -0.500),
    (-5.40, 1.100, 0.38, 1.000, 0.56, 0.800, 0.62, 0.400, 0.50, -0.350, -0.550),
    (-7.70, 1.180, 0.40, 1.080, 0.55, 0.880, 0.62, 0.500, 0.50, -0.400, -0.620),
    (-9.30, 1.050, 0.42, 0.980, 0.60, 0.850, 0.62, 0.550, 0.52, -0.400, -0.620),
    (-11.20, 0.930, 0.45, 0.880, 0.62, 0.780, 0.64, 0.550, 0.55, -0.350, -0.550),
    (-13.20, 0.820, 0.45, 0.780, 0.62, 0.700, 0.64, 0.500, 0.55, -0.300, -0.500),
    (-15.10, 0.700, 0.42, 0.660, 0.58, 0.580, 0.60, 0.420, 0.50, -0.250, -0.420),
    (-16.80, 0.600, 0.35, 0.550, 0.50, 0.480, 0.52, 0.350, 0.42, -0.150, -0.300),
    (-17.30, 0.300, 0.00, 0.300, 0.00, 0.300, 0.00, 0.300, 0.00, 0.300, 0.300),
]
_T = [(Y0 + r[0],) + tuple(r[1:]) for r in _D]
fuselage_ring, SPINE, KEEL = jk_std.fuselage(_T)


def fuselage_stations():
    return jk.stations([(Y_NOSE, Y0 - 1.5, 0.05), (Y0 - 1.5, Y0 - 16.8, 0.16), (Y0 - 16.8, Y0 - 17.3, 0.06)])


jk_std.Canopy(Y0 - 3.10, Y0 - 3.90, Y0 - 7.70,
              top=[(Y0 - 3.10, 1.03), (Y0 - 3.50, 1.30), (Y0 - 3.90, 1.52), (Y0 - 4.60, 1.74), (Y0 - 5.60, 1.83),
                   (Y0 - 6.60, 1.68), (Y0 - 7.20, 1.45), (Y0 - 7.70, 1.21)],
              sill_z=[(Y0 - 3.10, 1.02), (Y0 - 5.40, 1.05), (Y0 - 7.70, 1.15)],
              sill_x=[(Y0 - 3.10, 0.30), (Y0 - 3.60, 0.42), (Y0 - 4.40, 0.47), (Y0 - 7.00, 0.47), (Y0 - 7.50, 0.38),
                      (Y0 - 7.70, 0.30)],
              bulge=[(Y0 - 3.10, 0.0), (Y0 - 3.9, 0.03), (Y0 - 5.5, 0.045), (Y0 - 7.2, 0.025), (Y0 - 7.70, 0.0)]).export(globals())
CANOPY_ARCHES = ((Y0 - 3.90, 0.030), (Y0 - 5.45, 0.025), (Y0 - 7.65, 0.035))

jk_std.wing(globals(), le=[(1.45, Y0 - 8.57), (6.55, Y0 - 13.67)], te=[(1.45, Y0 - 15.00), (6.55, Y0 - 15.25)],
            z=lambda x: 0.62 - 0.0175 * np.maximum(np.asarray(x, float) - 1.45, 0.0),
            t=[(1.45, 0.066), (6.55, 0.030)], x_tip=6.55)
FLAP = (1.70, 3.60, 1.05, 0.85)
AIL = (3.60, 5.95, 0.80, 0.55)
LEF = None

# the rectangular raked intakes and the engine bays (the conformal tanks on their sides)
Y_FACE_TOP, Y_FACE_BOT = Y0 - 5.00, Y0 - 5.50
_N = [
    (Y0 - 5.50, 0.60, 1.42, 0.80, -0.62, 6.0),
    (Y0 - 7.00, 0.58, 1.66, 0.66, -0.70, 5.0),
    (Y0 - 12.00, 0.56, 1.68, 0.62, -0.70, 4.5),
    (Y0 - 14.50, 0.50, 1.55, 0.62, -0.60, 3.5),
    (Y0 - 16.50, 0.38, 1.55, 0.68, -0.48, 2.4),
    (Y0 - 17.00, 0.35, 1.55, 0.72, -0.48, 2.2),
]
NACELLE = [jk.Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = Y0 - 17.00
DUCT_DEPTH = 2.0
NOZZLE = dict(x=0.95, z=0.12, y0=Y0 - 17.00, y1=Y0 - 18.10, r0=0.62, r1=0.57, petals=18)


def nacelle_rake(d):
    return (Y_FACE_TOP - Y_FACE_BOT) / (0.80 + 0.62) * max(0.0, 1.0 - d / 1.2) ** 1.4


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, Y0 - 15.5, 0.30), (Y0 - 15.5, Y0 - 17.0, 0.12)])


BOOM = dict(x=1.68, z=0.42, hw=0.20, hh_up=0.28, hh_lo=0.28, y0=Y0 - 13.0, y1=Y0 - 19.20)
FIN_X, FIN_Z, FIN_CANT = 1.68, 0.70, 2.0
FIN = [(0.00, Y0 - 15.10, Y0 - 17.95, 0.0, 0.040), (3.07, Y0 - 17.00, Y0 - 18.30, 0.0, 0.032)]
RUDDER = (0.20, 1.60, 0.80, 0.70)
STAB_Z = 0.20
STAB = jk.Surface([(1.85, Y0 - 15.95, Y0 - 19.05, STAB_Z, 0.045), (4.34, Y0 - 18.50, Y0 - 19.45, STAB_Z, 0.035)],
                  airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = Y0 - 17.60

GEAR_NOSE = dict(y=Y0 - 4.20, x=0.0, r=0.28, w=0.18, twin=False)
GEAR_MAIN = dict(y=Y0 - 9.62, x=1.38, r=0.42, w=0.30)
