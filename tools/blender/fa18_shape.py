"""F/A-18E Super Hornet: the shape (pure numpy), measured off its three-view (the top view drawn turned 24.7 degrees:
measured on the image turned back about the nose; 47.95 px per metre there, the side view 48.0 px per metre after a
2.3 % correction to the same 18.2 m from the radome tip to the nozzles).  The wing span is scaled to the real 13.62 m
over the tip launchers (the drawing's is 6 % wider), the ground set for the real 4.88 m height.

Drawing -> model:  y = 9.30 + y_drawing (y_drawing = 0 at the radome tip, negative aft), x and z as measured.

The Super Hornet: the long round nose, the big one piece canopy, the huge LEX from the windscreen to the wing, the
rectangular raked intakes under it, a trapezoid wing with leading edge flaps, two fins canted 20 degrees out,
stabilators beside the nozzles, two F414 nozzles close together.
"""

import numpy as np

import jk
import jk_std

NAME = "fa18"
Y0 = 9.30
Y_NOSE = Y0
Y_PITOT = Y0
Z_GROUND = -1.72
SPAN_K = 0.952

_D = [
    # y_drw  spine  shoul x z     upper x z      edge x z       lower x z      keel
    (0.00,  0.040, 0.00, 0.040, 0.00, 0.040, 0.00, 0.040, 0.00, 0.040, 0.040),
    (-0.50, 0.300, 0.12, 0.250, 0.20, 0.150, 0.23, 0.050, 0.18, -0.100, -0.200),
    (-1.00, 0.460, 0.19, 0.380, 0.30, 0.240, 0.35, 0.100, 0.28, -0.150, -0.270),
    (-1.50, 0.600, 0.25, 0.500, 0.38, 0.330, 0.44, 0.150, 0.35, -0.200, -0.300),
    (-2.50, 0.800, 0.28, 0.680, 0.42, 0.450, 0.47, 0.200, 0.38, -0.220, -0.340),
    (-3.50, 0.930, 0.30, 0.850, 0.46, 0.600, 0.52, 0.300, 0.40, -0.200, -0.340),
    (-4.60, 1.050, 0.36, 0.950, 0.50, 0.750, 0.55, 0.400, 0.45, -0.300, -0.550),
    (-5.50, 1.150, 0.40, 1.050, 0.62, 0.850, 1.04, 0.380, 0.55, -0.550, -0.850),
    (-6.50, 1.200, 0.45, 1.120, 0.78, 0.900, 1.48, 0.360, 0.70, -0.600, -0.800),
    (-7.50, 1.300, 0.50, 1.220, 0.90, 0.950, 1.84, 0.340, 0.80, -0.620, -0.720),
    (-8.50, 1.300, 0.55, 1.220, 1.00, 0.950, 2.09, 0.320, 0.85, -0.620, -0.700),
    (-9.50, 1.250, 0.58, 1.180, 1.05, 0.920, 2.23, 0.300, 0.90, -0.620, -0.700),
    (-10.00, 1.200, 0.60, 1.130, 1.08, 0.900, 2.40, 0.300, 0.92, -0.620, -0.700),
    (-11.00, 1.120, 0.62, 1.050, 1.10, 0.850, 1.60, 0.300, 1.00, -0.620, -0.700),
    (-12.00, 1.020, 0.62, 0.960, 1.12, 0.780, 1.55, 0.280, 1.05, -0.600, -0.680),
    (-13.00, 0.960, 0.62, 0.900, 1.12, 0.720, 1.50, 0.250, 1.05, -0.580, -0.660),
    (-14.00, 0.900, 0.60, 0.850, 1.10, 0.680, 1.45, 0.220, 1.00, -0.550, -0.640),
    (-15.00, 0.800, 0.58, 0.760, 1.05, 0.620, 1.40, 0.200, 0.95, -0.520, -0.620),
    (-16.00, 0.720, 0.55, 0.680, 1.00, 0.550, 1.30, 0.150, 0.90, -0.480, -0.600),
    (-16.80, 0.620, 0.50, 0.580, 0.95, 0.480, 1.15, 0.100, 0.85, -0.420, -0.550),
    (-17.20, 0.400, 0.30, 0.350, 0.50, 0.300, 0.60, 0.100, 0.45, -0.200, -0.300),
    (-17.40, 0.100, 0.00, 0.100, 0.00, 0.100, 0.00, 0.100, 0.00, 0.100, 0.100),
]
_T = [(Y0 + r[0],) + tuple(r[1:]) for r in _D]
fuselage_ring, SPINE, KEEL = jk_std.fuselage(_T, sharp=(-0.8, 4.75))


def fuselage_stations():
    return jk.stations([(Y_NOSE, 8.30, 0.05), (8.30, 4.70, 0.12), (4.70, -0.70, 0.13), (-0.70, -8.10, 0.18)])


jk_std.Canopy(Y0 - 3.40, Y0 - 4.60, Y0 - 7.10,
              top=[(Y0 - 3.40, 0.95), (Y0 - 4.00, 1.27), (Y0 - 4.60, 1.53), (Y0 - 5.10, 1.68), (Y0 - 5.60, 1.66),
                   (Y0 - 6.20, 1.56), (Y0 - 6.70, 1.45), (Y0 - 7.10, 1.35)],
              sill_z=[(Y0 - 3.40, 0.94), (Y0 - 5.00, 1.05), (Y0 - 7.10, 1.25)],
              sill_x=[(Y0 - 3.40, 0.30), (Y0 - 3.90, 0.40), (Y0 - 4.60, 0.44), (Y0 - 6.40, 0.44), (Y0 - 6.90, 0.38),
                      (Y0 - 7.10, 0.30)],
              bulge=[(Y0 - 3.40, 0.0), (Y0 - 4.2, 0.03), (Y0 - 5.4, 0.04), (Y0 - 6.6, 0.025), (Y0 - 7.10, 0.0)]).export(globals())

jk_std.wing(globals(), le=[(1.40, Y0 - 9.50), (2.50 * SPAN_K, Y0 - 10.01), (7.00 * SPAN_K, Y0 - 12.17)],
            te=[(1.40, Y0 - 14.40), (2.50 * SPAN_K, Y0 - 14.29), (7.00 * SPAN_K, Y0 - 13.79)],
            z=0.25, t=[(1.40, 0.050), (4.00, 0.044), (7.00 * SPAN_K, 0.040)], x_tip=7.00 * SPAN_K)
FLAP = (2.50, 4.30, 1.00, 0.80)
AIL = (4.30, 6.40, 0.75, 0.55)
LEF = (2.50, 6.50, 0.55, 0.38)
TIP_POD = dict(x=7.00 * SPAN_K + 0.06, z=0.25, y0=Y0 - 10.95, y1=Y0 - 14.00, r=0.06)

# the rectangular intakes under the LEX: the face raked, the top lip forward
Y_FACE_TOP, Y_FACE_BOT = Y0 - 4.95, Y0 - 5.70
_N = [
    (Y0 - 5.70, 0.56, 1.22, 0.28, -0.95, 6.0),
    (Y0 - 6.50, 0.58, 1.28, 0.28, -0.90, 5.0),
    (Y0 - 8.00, 0.62, 1.28, 0.25, -0.80, 4.0),
    (Y0 - 9.50, 0.66, 1.25, 0.22, -0.72, 3.5),
]
NACELLE = [jk.Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = Y0 - 9.50
DUCT_DEPTH = 1.6
NOZZLE = dict(x=0.58, z=0.04, y0=Y0 - 16.80, y1=Y0 - 18.20, r0=0.46, r1=0.42, petals=16)


def nacelle_rake(d):
    return (Y_FACE_TOP - Y_FACE_BOT) / (0.28 + 0.95) * max(0.0, 1.0 - d / 1.4) ** 1.4


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, Y0 - 9.50, 0.20)])


BOOM = None
FIN_X, FIN_Z, FIN_CANT = 1.05, 0.88, 20.0
FIN = [(0.00, Y0 - 13.90, Y0 - 17.35, 0.0, 0.045), (2.45, Y0 - 16.20, Y0 - 17.00, 0.0, 0.032)]
RUDDER = (0.25, 1.70, 0.65, 0.55)
STAB_Z = 0.10
STAB = jk.Surface([(1.25, Y0 - 13.70, Y0 - 18.35, STAB_Z, 0.040), (3.98, Y0 - 18.10, Y0 - 19.20, STAB_Z, 0.032)],
                  airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = Y0 - 16.80

GEAR_NOSE = dict(y=Y0 - 5.83, x=0.0, r=0.28, w=0.16, twin=True)
GEAR_MAIN = dict(y=Y0 - 12.60, x=1.55, r=0.43, w=0.30)
