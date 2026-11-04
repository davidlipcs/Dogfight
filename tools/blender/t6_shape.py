"""T-6A Texan II: the shape (pure numpy), measured off its blueprint style three-view (top view 36.3 px per metre;
the side view drawn 6 % short is scaled to the real 10.16 m length: 42.8 px per metre; the 10.19 m span and the 3.25 m
height are the real figures).

Model y = 5.20 + y_drawing (y_drawing = 0 at the spinner tip, negative aft); z = 0: the spinner axis.

The Texan II: the spinner and the four blade propeller of the PT6A, the long cowling with the exhaust stacks either
side, the stepped tandem canopy, the low straight tapered wing with dihedral, the swept fin with its dorsal fillet,
the tailplane with elevators.
"""

import numpy as np

import jk
import jk_std

NAME = "t6"
Y0 = 5.20
Y_NOSE = Y0
Y_PITOT = Y0
Z_GROUND = -1.64

_D = [
    # y_drw  spine  shoul x z     upper x z      edge x z       lower x z      keel
    (0.00,  0.000, 0.00, 0.000, 0.00, 0.000, 0.00, 0.000, 0.00, 0.000, 0.000),
    (-0.25, 0.110, 0.07, 0.090, 0.10, 0.040, 0.11, 0.000, 0.08, -0.070, -0.100),
    (-0.55, 0.200, 0.15, 0.170, 0.21, 0.080, 0.23, 0.000, 0.17, -0.150, -0.200),
    (-0.75, 0.300, 0.22, 0.250, 0.34, 0.120, 0.38, -0.050, 0.30, -0.420, -0.550),
    (-1.50, 0.360, 0.26, 0.300, 0.38, 0.150, 0.42, -0.080, 0.34, -0.520, -0.630),
    (-2.40, 0.430, 0.28, 0.370, 0.40, 0.200, 0.44, -0.100, 0.36, -0.600, -0.720),
    (-3.30, 0.480, 0.30, 0.420, 0.42, 0.250, 0.46, -0.120, 0.38, -0.700, -0.850),
    (-5.00, 0.640, 0.30, 0.570, 0.42, 0.330, 0.45, -0.120, 0.38, -0.700, -0.840),
    (-6.40, 0.720, 0.26, 0.640, 0.36, 0.380, 0.39, -0.100, 0.32, -0.550, -0.650),
    (-7.40, 0.560, 0.21, 0.500, 0.29, 0.330, 0.31, -0.100, 0.25, -0.450, -0.530),
    (-8.60, 0.460, 0.15, 0.420, 0.21, 0.280, 0.23, -0.100, 0.18, -0.350, -0.420),
    (-9.60, 0.300, 0.09, 0.280, 0.12, 0.200, 0.13, -0.050, 0.10, -0.250, -0.300),
    (-10.16, 0.050, 0.00, 0.050, 0.00, 0.050, 0.00, 0.050, 0.00, 0.050, 0.050),
]
_T = [(Y0 + r[0],) + tuple(r[1:]) for r in _D]
fuselage_ring, SPINE, KEEL = jk_std.fuselage(_T)


def fuselage_stations():
    return jk.stations([(Y_NOSE, Y0 - 0.75, 0.05), (Y0 - 0.75, Y0 - 9.6, 0.13), (Y0 - 9.6, Y0 - 10.16, 0.06)])


jk_std.Canopy(Y0 - 2.55, Y0 - 3.10, Y0 - 6.30,
              top=[(Y0 - 2.55, 0.44), (Y0 - 2.85, 0.66), (Y0 - 3.10, 0.80), (Y0 - 3.60, 0.95), (Y0 - 4.20, 1.04),
                   (Y0 - 4.80, 1.06), (Y0 - 5.40, 1.02), (Y0 - 5.90, 0.90), (Y0 - 6.30, 0.76)],
              sill_z=[(Y0 - 2.55, 0.43), (Y0 - 4.20, 0.52), (Y0 - 6.30, 0.68)],
              sill_x=[(Y0 - 2.55, 0.25), (Y0 - 2.90, 0.36), (Y0 - 3.40, 0.40), (Y0 - 5.80, 0.38), (Y0 - 6.10, 0.32),
                      (Y0 - 6.30, 0.24)],
              bulge=[(Y0 - 2.55, 0.0), (Y0 - 3.0, 0.03), (Y0 - 4.5, 0.045), (Y0 - 5.9, 0.03), (Y0 - 6.30, 0.0)]).export(globals())
CANOPY_ARCHES = ((Y0 - 3.10, 0.025), (Y0 - 4.75, 0.030), (Y0 - 6.25, 0.030))

jk_std.wing(globals(), le=[(0.45, Y0 - 3.30), (5.09, Y0 - 3.95)], te=[(0.45, Y0 - 5.12), (5.09, Y0 - 4.85)],
            z=lambda x: -0.55 + 0.105 * np.maximum(np.asarray(x, float) - 0.45, 0.0),
            t=[(0.45, 0.15), (5.09, 0.12)], x_tip=5.09)
FLAP = (0.55, 2.80, 0.50, 0.38)
AIL = (2.80, 4.70, 0.36, 0.30)
LEF = None
NACELLE = None
NOZZLE = None
EXHAUST = (0.42, Y0 - 1.25, 0.02)        # the exhaust stacks (right side)
PROP = dict(y=Y0 - 0.45, r=1.23, blades=4, chord=0.20)

BOOM = None
FIN_X, FIN_Z, FIN_CANT = 0.0, 0.48, 0.0
FIN = [(0.00, Y0 - 7.40, Y0 - 9.60, 0.0, 0.08), (0.12, Y0 - 8.25, Y0 - 9.55, 0.0, 0.10),
       (1.10, Y0 - 8.66, Y0 - 9.02, 0.0, 0.09)]
RUDDER = (0.15, 1.05, 0.40, 0.30)
STAB_Z = -0.10
STAB = jk.Surface([(0.20, Y0 - 8.95, Y0 - 10.05, STAB_Z, 0.10), (1.60, Y0 - 9.35, Y0 - 9.95, STAB_Z, 0.09)],
                  nc=12)
STAB_PIVOT = Y0 - 9.40

GEAR_NOSE = dict(y=Y0 - 1.85, x=0.0, r=0.20, w=0.13, twin=False)
GEAR_MAIN = dict(y=Y0 - 4.95, x=1.30, r=0.27, w=0.17)
