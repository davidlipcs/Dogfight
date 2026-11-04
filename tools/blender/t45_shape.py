"""T-45C Goshawk: the shape (pure numpy), measured off its three-view (the top view drawn nose up, turned for the
measurement: 45.6 px per metre - the 11.99 m length; the span is scaled to the real 9.39 m, the drawing's is 4 %
wider; the side view 45.3 px per metre).  Ground for the real 4.08 m height.

Drawing -> model:  y_drawing = 0 at the nose probe tip, negative aft; model y = 6.20 + y_drawing; z = 0: the belly
line under the nose.

The Goshawk (the carrier Hawk): the short pointed nose, the stepped tandem canopy, the side intakes under it, the low
wing (26 degrees), the tall fin with its curved leading edge, the anhedral stabilators, one Adour nozzle.
"""

import numpy as np

import jk
import jk_std

NAME = "t45"
Y0 = 6.20
Y_NOSE = Y0 - 0.55
Y_PITOT = Y0
Z_GROUND = -1.13
SPAN_K = 0.958

_D = [
    # y_drw  spine  shoul x z     upper x z      edge x z       lower x z      keel
    (-0.55, 0.020, 0.00, 0.020, 0.00, 0.020, 0.00, 0.020, 0.00, 0.020, 0.020),
    (-1.00, 0.180, 0.10, 0.160, 0.15, 0.110, 0.16, 0.050, 0.12, -0.020, -0.050),
    (-1.80, 0.430, 0.24, 0.380, 0.32, 0.280, 0.35, 0.130, 0.26, -0.040, -0.090),
    (-2.20, 0.560, 0.30, 0.480, 0.40, 0.330, 0.44, 0.160, 0.34, -0.050, -0.100),
    (-3.00, 0.640, 0.34, 0.560, 0.44, 0.380, 0.48, 0.180, 0.38, -0.060, -0.110),
    (-4.20, 0.760, 0.36, 0.680, 0.46, 0.450, 0.50, 0.200, 0.42, -0.060, -0.110),
    (-5.50, 0.900, 0.38, 0.800, 0.50, 0.550, 0.56, 0.250, 0.45, -0.060, -0.110),
    (-5.80, 1.400, 0.40, 1.250, 0.56, 0.700, 0.70, 0.250, 0.52, -0.060, -0.110),
    (-7.00, 1.330, 0.42, 1.200, 0.62, 0.750, 0.82, 0.250, 0.60, -0.060, -0.100),
    (-8.50, 1.230, 0.40, 1.120, 0.58, 0.720, 0.70, 0.250, 0.55, -0.040, -0.080),
    (-9.50, 1.150, 0.36, 1.050, 0.52, 0.700, 0.62, 0.300, 0.50, 0.000, -0.040),
    (-10.50, 1.050, 0.32, 0.970, 0.46, 0.700, 0.55, 0.350, 0.44, 0.100, 0.050),
    (-11.50, 0.950, 0.28, 0.880, 0.40, 0.680, 0.46, 0.400, 0.38, 0.200, 0.150),
    (-11.80, 0.900, 0.20, 0.860, 0.30, 0.680, 0.34, 0.450, 0.28, 0.300, 0.250),
    (-11.95, 0.700, 0.00, 0.700, 0.00, 0.700, 0.00, 0.700, 0.00, 0.700, 0.700),
]
_T = [(Y0 + r[0],) + tuple(r[1:]) for r in _D]
fuselage_ring, SPINE, KEEL = jk_std.fuselage(_T)


def fuselage_stations():
    return jk.stations([(Y_NOSE, Y0 - 1.5, 0.05), (Y0 - 1.5, Y0 - 11.5, 0.13), (Y0 - 11.5, Y0 - 11.95, 0.05)])


jk_std.Canopy(Y0 - 2.20, Y0 - 3.00, Y0 - 5.75,
              top=[(Y0 - 2.20, 0.57), (Y0 - 2.60, 0.85), (Y0 - 3.00, 1.06), (Y0 - 3.60, 1.30), (Y0 - 4.20, 1.48),
                   (Y0 - 4.80, 1.57), (Y0 - 5.30, 1.57), (Y0 - 5.75, 1.50)],
              sill_z=[(Y0 - 2.20, 0.56), (Y0 - 4.00, 0.76), (Y0 - 5.75, 0.95)],
              sill_x=[(Y0 - 2.20, 0.25), (Y0 - 2.60, 0.34), (Y0 - 3.20, 0.40), (Y0 - 5.40, 0.40), (Y0 - 5.75, 0.30)],
              bulge=[(Y0 - 2.20, 0.0), (Y0 - 2.8, 0.02), (Y0 - 4.0, 0.035), (Y0 - 5.4, 0.02), (Y0 - 5.75, 0.0)]).export(globals())
CANOPY_ARCHES = ((Y0 - 3.00, 0.025), (Y0 - 4.25, 0.025), (Y0 - 5.72, 0.030))

jk_std.wing(globals(), le=[(0.75, Y0 - 5.70), (1.00 * SPAN_K, Y0 - 5.95), (4.55 * SPAN_K, Y0 - 7.60)],
            te=[(0.75, Y0 - 8.10), (4.55 * SPAN_K, Y0 - 8.45)],
            z=lambda x: 0.15 + 0.035 * np.maximum(np.asarray(x, float) - 0.75, 0.0),
            t=[(0.75, 0.10), (4.55 * SPAN_K, 0.09)], x_tip=4.55 * SPAN_K)
FLAP = (0.90, 2.60, 0.62, 0.55)
AIL = (2.60, 4.00, 0.52, 0.45)
LEF = None

Y_FACE_TOP, Y_FACE_BOT = Y0 - 4.40, Y0 - 4.55
_N = [
    (Y0 - 4.55, 0.42, 0.88, 0.95, 0.25, 3.0),
    (Y0 - 5.30, 0.44, 0.98, 0.98, 0.20, 3.0),
    (Y0 - 6.80, 0.46, 0.84, 0.95, 0.20, 3.0),
]
NACELLE = [jk.Line([(r[0], r[i]) for r in _N]) for i in range(1, 6)]
Y_NAC1 = Y0 - 6.80
DUCT_DEPTH = 1.0
NOZZLE = dict(x=0.0, z=0.60, y0=Y0 - 11.80, y1=Y0 - 12.20, r0=0.32, r1=0.30, petals=10)


def nacelle_rake(d):
    return 0.0


def nacelle_stations():
    return jk.stations([(Y_FACE_BOT, Y0 - 6.80, 0.15)])


BOOM = None
FIN_X, FIN_Z, FIN_CANT = 0.0, 1.20, 0.0
FIN = [(0.00, Y0 - 9.05, Y0 - 11.60, 0.0, 0.040), (0.40, Y0 - 9.70, Y0 - 11.62, 0.0, 0.040),
       (0.80, Y0 - 10.05, Y0 - 11.62, 0.0, 0.038), (1.20, Y0 - 10.45, Y0 - 11.64, 0.0, 0.036),
       (1.60, Y0 - 10.95, Y0 - 11.66, 0.0, 0.032), (1.75, Y0 - 11.20, Y0 - 11.60, 0.0, 0.030)]
RUDDER = (0.25, 1.55, 0.45, 0.35)
STAB_Z = 0.55
STAB = jk.Surface([(0.40, Y0 - 10.10, Y0 - 11.45, STAB_Z, 0.050), (2.00, Y0 - 11.80, Y0 - 12.05, STAB_Z - 0.28, 0.040)],
                  airfoil=jk.biconvex_t, nc=12)
STAB_PIVOT = Y0 - 11.20

GEAR_NOSE = dict(y=Y0 - 2.60, x=0.0, r=0.22, w=0.14, twin=False)
GEAR_MAIN = dict(y=Y0 - 6.90, x=1.95, r=0.30, w=0.20)
