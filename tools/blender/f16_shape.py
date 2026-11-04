"""F-16C Fighting Falcon: the shape (pure numpy), measured off the F-16A/B three-view (the top view turned with its nose
to the right: 38.3 px per metre; the side view 37.2 px per metre - both the 15.03 m from the pitot tip to the nozzle).
The fin is lowered to the real 5.09 m height (the drawing's jet stands 5.55 m tall); the C differs from the A
outwardly only in details.

Drawing -> model:  y = 8.00 + y_drawing (y_drawing = 0 at the pitot tip, negative aft); x, z as measured (z = 0: the
radome axis; the wing plane is 0.60 above it).

The F-16: a short pointed radome, the one piece bubble canopy, the curved strakes from the canopy to the wing, the
"smiling" intake under the cockpit, a 40 degree cropped delta wing with the launch rails at the tips, one big fin,
two ventral fins, the stabilators beside the single F110 nozzle.
"""

import numpy as np

import jk
import jk_std

NAME = "f16"
Y0 = 8.00
Y_NOSE = Y0 - 0.38          # radome tip
Y_PITOT = Y0
Z_GROUND = -1.52

_D = [
    # y_drw  spine  shoul x z     upper x z      edge x z       lower x z      keel
    (-0.38, 0.020, 0.00, 0.020, 0.00, 0.020, 0.00, 0.020, 0.00, 0.020, 0.020),
    (-0.70, 0.180, 0.08, 0.150, 0.13, 0.090, 0.15, 0.020, 0.11, -0.040, -0.060),
    (-1.00, 0.380, 0.15, 0.330, 0.23, 0.220, 0.25, 0.120, 0.18, -0.010, -0.050),
    (-1.50, 0.560, 0.20, 0.480, 0.33, 0.330, 0.38, 0.180, 0.28, 0.000, -0.030),
    (-2.00, 0.730, 0.24, 0.620, 0.40, 0.450, 0.46, 0.250, 0.34, 0.000, -0.030),
    (-2.50, 0.860, 0.27, 0.750, 0.43, 0.550, 0.48, 0.300, 0.36, 0.020, 0.000),
    (-3.00, 1.020, 0.30, 0.930, 0.48, 0.700, 0.56, 0.400, 0.42, 0.030, 0.030),
    (-3.50, 1.080, 0.32, 1.000, 0.52, 0.780, 0.67, 0.550, 0.45, 0.050, 0.050),
    (-4.00, 1.110, 0.34, 1.030, 0.56, 0.820, 0.72, 0.580, 0.47, 0.050, 0.050),
    (-5.00, 1.150, 0.38, 1.060, 0.62, 0.850, 0.87, 0.600, 0.55, 0.100, 0.050),
    (-6.00, 1.180, 0.42, 1.100, 0.68, 0.880, 1.11, 0.600, 0.62, 0.120, 0.050),
    (-7.00, 1.200, 0.45, 1.140, 0.72, 0.900, 1.37, 0.600, 0.66, 0.150, 0.100),
    (-8.00, 1.210, 0.48, 1.150, 0.76, 0.920, 1.75, 0.600, 0.70, 0.150, 0.100),
    (-9.00, 1.210, 0.50, 1.150, 0.78, 0.920, 1.00, 0.600, 0.72, 0.150, 0.100),
    (-10.00, 1.210, 0.50, 1.150, 0.80, 0.920, 1.05, 0.600, 0.75, 0.150, 0.100),
    (-10.70, 1.230, 0.50, 1.170, 0.82, 0.920, 1.08, 0.600, 0.70, -0.100, -0.420),
    (-11.50, 1.260, 0.49, 1.190, 0.82, 0.930, 1.08, 0.610, 0.68, -0.200, -0.430),
    (-12.50, 1.290, 0.46, 1.210, 0.78, 0.950, 1.08, 0.620, 0.64, -0.100, -0.350),
    (-13.50, 1.300, 0.40, 1.200, 0.70, 0.950, 0.95, 0.620, 0.58, 0.000, -0.220),
    (-14.00, 1.200, 0.35, 1.120, 0.65, 0.950, 0.85, 0.620, 0.55, 0.100, -0.130),
    (-14.30, 1.050, 0.30, 1.000, 0.55, 0.900, 0.65, 0.600, 0.45, 0.200, 0.000),
    (-14.55, 0.750, 0.00, 0.750, 0.00, 0.750, 0.00, 0.750, 0.00, 0.750, 0.750),
]
_T = [(Y0 + r[0],) + tuple(r[1:]) for r in _D]
fuselage_ring, SPINE, KEEL = jk_std.fuselage(_T, sharp=(Y0 - 9.2, Y0 - 3.2))


def fuselage_stations():
    return jk.stations([(Y_NOSE, Y0 - 1.5, 0.05), (Y0 - 1.5, Y0 - 3.0, 0.12), (Y0 - 3.0, Y0 - 10.5, 0.13),
                        (Y0 - 10.5, Y0 - 14.0, 0.16), (Y0 - 14.0, Y0 - 14.55, 0.06)])


jk_std.Canopy(Y0 - 3.00, Y0 - 3.60, Y0 - 6.40,
              top=[(Y0 - 3.00, 1.05), (Y0 - 3.30, 1.26), (Y0 - 3.60, 1.42), (Y0 - 4.00, 1.56), (Y0 - 4.60, 1.63),
                   (Y0 - 5.00, 1.58), (Y0 - 5.50, 1.50), (Y0 - 6.00, 1.41), (Y0 - 6.40, 1.33)],
              sill_z=[(Y0 - 3.00, 1.03), (Y0 - 4.60, 1.10), (Y0 - 6.40, 1.19)],
              sill_x=[(Y0 - 3.00, 0.28), (Y0 - 3.40, 0.37), (Y0 - 4.00, 0.41), (Y0 - 5.80, 0.41), (Y0 - 6.20, 0.36),
                      (Y0 - 6.40, 0.28)],
              bulge=[(Y0 - 3.00, 0.0), (Y0 - 3.6, 0.03), (Y0 - 4.6, 0.045), (Y0 - 5.8, 0.03), (Y0 - 6.40, 0.0)]).export(globals())
CANOPY_ARCHES = ((Y0 - 4.13, 0.030), (Y0 - 6.35, 0.030))

jk_std.wing(globals(), le=[(1.00, Y0 - 7.06), (4.70, Y0 - 10.00)], te=[(1.00, Y0 - 11.15), (4.70, Y0 - 11.15)],
            z=0.60, t=[(1.00, 0.040), (4.70, 0.040)], x_tip=4.70)
FLAP = (1.10, 2.70, 0.80, 0.70)          # the flaperons, inner part
AIL = (2.70, 4.20, 0.70, 0.62)           # and outer part
LEF = (1.10, 4.65, 0.42, 0.28)
TIP_POD = dict(x=4.78, z=0.60, y0=Y0 - 9.85, y1=Y0 - 11.40, r=0.06)

# the intake under the cockpit (one, on the centre line): the top lip forward
NACELLE_CENTRE = True
Y_FACE_TOP, Y_FACE_BOT = Y0 - 4.30, Y0 - 4.65
_N = [
    (Y0 - 4.65, 0.0, 0.48, 0.05, -0.60, 2.4),
    (Y0 - 6.00, 0.0, 0.52, 0.08, -0.60, 2.4),
    (Y0 - 8.50, 0.0, 0.55, 0.10, -0.52, 2.6),
    (Y0 - 10.70, 0.0, 0.55, 0.10, -0.44, 2.8),
]
NACELLE = [jk.Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = Y0 - 10.70
DUCT_DEPTH = 1.5
NOZZLE = dict(x=0.0, z=0.55, y0=Y0 - 14.25, y1=Y0 - 15.00, r0=0.58, r1=0.52, petals=15)


def nacelle_rake(d):
    return (Y_FACE_TOP - Y_FACE_BOT) / (0.05 + 0.60) * max(0.0, 1.0 - d / 1.0) ** 1.4


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, Y0 - 10.70, 0.20)])


BOOM = None
FIN_X, FIN_Z, FIN_CANT = 0.0, 1.30, 0.0
FIN = [(0.00, Y0 - 10.25, Y0 - 14.60, 0.0, 0.040), (0.25, Y0 - 10.85, Y0 - 14.60, 0.0, 0.040),
       (2.25, Y0 - 13.10, Y0 - 14.25, 0.0, 0.030)]
RUDDER = (0.25, 1.95, 0.70, 0.55)
VENTRAL = dict(x=0.55, z=-0.30, cant=15.0, sections=[(0.0, Y0 - 10.55, Y0 - 12.10, 0.0, 0.05),
                                                     (0.55, Y0 - 11.25, Y0 - 12.00, 0.0, 0.05)])
STAB_Z = 0.55
STAB = jk.Surface([(1.08, Y0 - 12.10, Y0 - 14.65, STAB_Z, 0.040), (2.79, Y0 - 14.10, Y0 - 14.65, STAB_Z, 0.032)],
                  airfoil=jk.biconvex_t, nc=14)
STAB_PIVOT = Y0 - 13.70

GEAR_NOSE = dict(y=Y0 - 5.13, x=0.0, r=0.25, w=0.16, twin=False)
GEAR_MAIN = dict(y=Y0 - 9.34, x=1.18, r=0.36, w=0.26)
