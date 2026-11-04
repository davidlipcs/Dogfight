"""Jet kit: the parts every shape module writes the same way - the fuselage table, the canopy - given as data."""

import math

import numpy as np

import jk
from jk import Body, Line, Longeron


def fuselage(table, sharp=None, sharp_top=None, fulls=(1.17, 1.05, 1.0, 1.10, 1.17)):
    """A fuselage from its table: rows (y, spine z, shoulder x, z, upper x, z, edge x, z, lower x, z, keel z).
    -> (ring(y) function, SPINE line, KEEL line).  ``sharp`` / ``sharp_top``: (y0, y1) where the edge / the shoulder
    is a crease (chines)."""
    col = lambda i: [(r[0], r[i]) for r in table]
    body = Body([
        Longeron("spine", 0.0, col(1), full=fulls[0], n=6),
        Longeron("shoulder", col(2), col(3), full=fulls[1], n=4),
        Longeron("upper", col(4), col(5), full=fulls[2], n=4),
        Longeron("edge", col(6), col(7), full=fulls[3], n=5),
        Longeron("lower", col(8), col(9), full=fulls[4], n=5),
        Longeron("keel", 0.0, col(10), n=1),
    ])

    def ring(y):
        body.L[3].sharp = bool(sharp and sharp[0] < y < sharp[1])
        body.L[1].sharp = bool(sharp_top and sharp_top[0] < y < sharp_top[1])
        return body.ring(y)
    return ring, Line(col(1)), Line(col(10))


class Canopy:
    """A canopy from its top line, its sill height and width and the bulge of its sides (point lists over y)."""

    def __init__(self, ws0, ws1, can1, top, sill_z, sill_x, bulge, ex_x=0.85, ex_z=1.10):
        self.Y_WS0, self.Y_WS1, self.Y_CAN1 = ws0, ws1, can1
        self.TOP, self.SILL_Z, self.SILL_X, self.BULGE = Line(top), Line(sill_z), Line(sill_x), Line(bulge)
        self.ex_x, self.ex_z = ex_x, ex_z

    def half(self, y, n=14):
        zt, zs, xs = float(self.TOP(y)), float(self.SILL_Z(y)), float(self.SILL_X(y))
        a = np.linspace(0.0, 0.5 * math.pi, n + 1)
        x = (xs + float(self.BULGE(y))) * np.sin(a) ** self.ex_x
        z = zs + (zt - zs) * np.cos(a) ** self.ex_z
        x[-1] = xs
        return np.stack([x, z], axis=1)

    def stations(self):
        return jk.stations([(self.Y_WS0, self.Y_WS1, 0.05), (self.Y_WS1, self.Y_CAN1, 0.08)])

    def export(self, g):
        """Puts the names the mesh builder reads into the shape module's globals ``g``."""
        g.update(Y_WS0=self.Y_WS0, Y_WS1=self.Y_WS1, Y_CAN1=self.Y_CAN1, CANOPY_TOP=self.TOP, CANOPY_SILL_Z=self.SILL_Z,
                 CANOPY_SILL_X=self.SILL_X, CANOPY_BULGE=self.BULGE, canopy_half=self.half, canopy_stations=self.stations)


def wing(g, le, te, z, t, x_tip, airfoil=None):
    """Planform from the leading / trailing edge kinks [(x, y)...], thickness ratios [(x, t)...]: WING, wing_le,
    wing_te, wing_z, X_WTIP, Z_WING into ``g``.  ``z``: a number or a function of x (dihedral)."""
    LE, TE = jk.Lin(le), jk.Lin(te)
    zf = z if callable(z) else (lambda x, c=float(z): c + 0.0 * np.asarray(x, float))
    xs = sorted(set([p[0] for p in le] + [p[0] for p in te] + [p[0] for p in t]))
    T = jk.Lin(t)
    kw = {} if airfoil is None else dict(airfoil=airfoil)
    g.update(WING=jk.Surface([(x, float(LE(x)), float(TE(x)), float(zf(x)), float(T(x))) for x in xs], nc=20, **kw),
             wing_le=LE, wing_te=TE, wing_z=zf, X_WTIP=x_tip, Z_WING=float(zf(xs[0])))
