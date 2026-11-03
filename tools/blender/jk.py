"""Jet kit: the geometry of the Blender jets (pure numpy, no Blender), shared by every builder.

Every jet is described by its own <jet>_shape.py with numbers measured off its three-view drawing; this module
turns those numbers into meshes:

* ``Line``      a smooth, overshoot free curve through measured points (monotone cubic, PCHIP), v(y).
* ``Body``      a lofted body (fuselage, nacelle, canopy, pod): at every station y its cross-section runs through
                its *longerons* - lines measured off the top and side views (the spine, the widest line, a chine,
                the keel ...) - joined by cubic Hermite arcs.  So the top view outline is exactly the widest
                longeron and the side view outline exactly the spine and the keel: the drawing, by construction.
* ``Surface``   a lifting surface (wing, stabilator, fin, canard) from its planform (leading / trailing edge at
                spanwise stations) and an airfoil, cut into its moving parts (flaps, ailerons, slats, rudders).

Frame: +Y forward, +X right (starboard), +Z up, metres; origin near the centre of gravity, ground at Z_GROUND.
Meshes are (vertices, quads) pairs; aircraft_lib.Part takes them as they are.
"""

import math

import numpy as np


# ------------------------------------------------------------------ curves
class Line:
    """v(t) through the points (t, v): monotone piecewise cubic (Fritsch-Carlson), so it never bulges past the
    measured points; constant outside the measured range.  ``Line(c)`` with a number is a constant."""

    def __init__(self, pts):
        if np.isscalar(pts):
            pts = [(-1e3, float(pts)), (1e3, float(pts))]
        pts = sorted((float(a), float(b)) for a, b in pts)
        t = np.array([p[0] for p in pts])
        v = np.array([p[1] for p in pts])
        if len(t) == 1:
            t, v = np.array([t[0] - 1.0, t[0] + 1.0]), np.array([v[0], v[0]])
        if np.any(np.diff(t) <= 0):
            raise ValueError("Line: the t values must be distinct: %s" % (t,))
        h = np.diff(t)
        d = np.diff(v) / h
        m = np.zeros_like(v)
        m[0], m[-1] = d[0], d[-1]
        for i in range(1, len(v) - 1):
            if d[i - 1] * d[i] <= 0.0:
                m[i] = 0.0
            else:
                w1, w2 = 2.0 * h[i] + h[i - 1], h[i] + 2.0 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        self.t, self.v, self.m = t, v, m

    def __call__(self, x):
        x = np.asarray(x, float)
        xc = np.clip(x, self.t[0], self.t[-1])
        i = np.clip(np.searchsorted(self.t, xc) - 1, 0, len(self.t) - 2)
        h = self.t[i + 1] - self.t[i]
        s = (xc - self.t[i]) / h
        h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
        out = h00 * self.v[i] + h10 * h * self.m[i] + h01 * self.v[i + 1] + h11 * h * self.m[i + 1]
        return float(out) if out.ndim == 0 else out

    def lo(self):
        return float(self.t[0])

    def hi(self):
        return float(self.t[-1])


class Lin:
    """Piecewise linear v(t) (planform edges, which are straight between their kinks)."""

    def __init__(self, pts):
        pts = sorted((float(a), float(b)) for a, b in pts)
        self.t = np.array([p[0] for p in pts])
        self.v = np.array([p[1] for p in pts])

    def __call__(self, x):
        out = np.interp(np.asarray(x, float), self.t, self.v)
        return float(out) if np.ndim(out) == 0 else out


def ease(n, k=1.0):
    """n+1 parameters 0..1, closer together at both ends by ``k`` (0 = uniform, 1 = cosine)."""
    u = np.linspace(0.0, 1.0, n + 1)
    return (1.0 - k) * u + k * 0.5 * (1.0 - np.cos(np.pi * u))


def stations(pairs):
    """Station list from [(y_from, y_to, step), ...] (front to back), without repeats."""
    out = []
    for a, b, step in pairs:
        n = max(1, int(round(abs(a - b) / step)))
        for y in np.linspace(a, b, n + 1):
            if not out or abs(out[-1] - y) > 1e-9:
                out.append(float(y))
    return out


# ------------------------------------------------------------------ lofted bodies
class Longeron:
    """One line along a body: x(y), z(y) (right half, x >= 0).

    ``x`` / ``z``: numbers, point lists [(y, v)...] or callables.  ``tan``: the direction the cross-section runs
    through this point, as an angle in degrees in the (x, z) plane measured from +x towards +z (None: from the
    neighbours); a number or a callable of y.  ``sharp``: the section has a crease here (a chine edge): the arcs
    on both sides aim straight at their other ends.  ``full``: how full the arc to the *next* longeron bulges
    (1.0: Catmull-Rom like, 1.17: a quarter ellipse between a horizontal and a vertical tangent, more: boxier).
    ``n``: points on the arc to the next longeron.
    """

    def __init__(self, name, x, z, tan=None, sharp=False, full=1.0, n=6):
        self.name = name
        self.fx, self.fz = self._fn(x), self._fn(z)
        self.tan = tan if (tan is None or callable(tan)) else (lambda y, a=float(tan): a)
        self.sharp = sharp
        self.full = full if callable(full) else (lambda y, f=float(full): f)
        self.n = n

    @staticmethod
    def _fn(v):
        if callable(v):
            return v
        if np.isscalar(v):
            return lambda y, c=float(v): c + 0.0 * np.asarray(y, float)
        return Line(v)

    def at(self, y):
        return np.array([float(self.fx(y)), float(self.fz(y))])


def _unit(v):
    n = math.hypot(v[0], v[1])
    return v / n if n > 1e-12 else np.array([0.0, 0.0])


class Body:
    """A body lofted through its longerons (ordered round the right half: top centre ... bottom centre).

    The first and the last longeron are on the centre line (x = 0) for a closed body (fuselage); with
    ``closed=False`` the section is a free strip (an open shell: a canopy on its sill).  ``ring(y)`` is the full
    cross-section (the right half and its mirror), the same number of points at every station."""

    def __init__(self, longerons, mirror=True, x_offset=0.0):
        self.L = longerons
        self.mirror = mirror
        self.x_offset = x_offset

    def half(self, y):
        P = [l.at(y) for l in self.L]
        n = len(P)
        tin, tout = [], []
        for k in range(n):
            l = self.L[k]
            a = l.tan(y) if l.tan is not None else None
            if a is not None:
                t = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
                tin.append(t)
                tout.append(t)
                continue
            prev = P[k - 1] if k > 0 else None
            nxt = P[k + 1] if k < n - 1 else None
            if k == 0 and self.mirror:                   # top centre: across, outwards
                t = np.array([1.0, 0.0])
                tin.append(t)
                tout.append(t)
            elif k == n - 1 and self.mirror:             # bottom centre: across, inwards
                t = np.array([-1.0, 0.0])
                tin.append(t)
                tout.append(t)
            elif l.sharp or prev is None or nxt is None:
                ti = _unit(P[k] - prev) if prev is not None else _unit(nxt - P[k])
                to = _unit(nxt - P[k]) if nxt is not None else ti
                tin.append(ti)
                tout.append(to)
            else:
                t = _unit(nxt - prev)
                tin.append(t)
                tout.append(t)
        pts = []
        for k in range(n - 1):
            a, b = P[k], P[k + 1]
            ch = math.hypot(*(b - a))
            f = float(self.L[k].full(y))
            m0, m1 = tout[k] * f * ch, tin[k + 1] * f * ch
            m = self.L[k].n
            s = np.linspace(0.0, 1.0, m + 1)[:-1] if k < n - 2 else np.linspace(0.0, 1.0, m + 1)
            h00, h10 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s
            h01, h11 = -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
            seg = h00[:, None] * a + h10[:, None] * m0 + h01[:, None] * b + h11[:, None] * m1
            pts.append(seg)
        h = np.vstack(pts)
        if self.mirror:
            h[:, 0] = np.maximum(h[:, 0], 0.0)
            h[0, 0] = 0.0
            h[-1, 0] = 0.0
        return h

    def ring(self, y):
        h = self.half(y)
        right = np.stack([h[:, 0] + self.x_offset, np.full(len(h), y), h[:, 1]], axis=1)
        if not self.mirror:
            return right
        left = right[-2:0:-1] * np.array([-1.0, 1.0, 1.0])
        return np.vstack([right, left])

    def rings(self, ys):
        return np.array([self.ring(y) for y in ys])


def grid_faces(nr, nc, close=True):
    faces = []
    for i in range(nr - 1):
        for j in range(nc if close else nc - 1):
            a, b = i * nc + j, i * nc + (j + 1) % nc
            faces.append((a, b, b + nc, a + nc))
    return faces


# ------------------------------------------------------------------ superellipse rings (pods, nacelles, nozzles)
def rounded_ring(cx, cz, hw, hh_up, hh_lo, n_up=2.0, n_lo=2.0, seg=32, y=0.0, start=0.5 * math.pi):
    """A closed superellipse-ish ring (top half and bottom half may differ), counter-clockwise seen from the
    front, starting at the top."""
    a = start + np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    c, s = np.cos(a), np.sin(a)
    up = s >= 0
    ex = np.where(up, 2.0 / n_up, 2.0 / n_lo)
    x = cx + hw * np.sign(c) * np.abs(c) ** ex
    z = cz + np.where(up, hh_up, hh_lo) * np.sign(s) * np.abs(s) ** ex
    return np.stack([x, np.full(seg, y), z], axis=1)


# ------------------------------------------------------------------ airfoils and lifting surfaces
def naca_t(s, t):
    """Half thickness (fraction of the chord) of a NACA 4 digit section of thickness ratio ``t`` at chord
    position ``s`` (0 = leading edge, 1 = trailing edge), with a closed trailing edge."""
    s = np.clip(s, 0.0, 1.0)
    return 5.0 * t * (0.2969 * np.sqrt(s) - 0.1260 * s - 0.3516 * s ** 2 + 0.2843 * s ** 3 - 0.1036 * s ** 4)


def biconvex_t(s, t):
    """Half thickness of a sharp edged biconvex section (fins of fast jets, thin stabilators)."""
    s = np.clip(s, 0.0, 1.0)
    return 2.0 * t * s * (1.0 - s)


class Surface:
    """A lifting surface on spanwise stations.

    ``sections``: [(span, le, te, h, t), ...] root first: ``span`` the spanwise coordinate (x for a wing, the
    distance up a fin), ``le`` / ``te`` the y of the leading / trailing edge, ``h`` the height of the chord line,
    ``t`` the thickness ratio.  ``frame(span, y, h)`` maps those to model space (x, y, z) - a wing:
    (span, y, h); a canted fin: rotated about the y axis.  ``airfoil``: naca_t or biconvex_t.
    """

    def __init__(self, sections, frame=None, airfoil=naca_t, nc=18):
        self.sec = sorted(sections, key=lambda r: r[0])
        sp = [r[0] for r in self.sec]
        self.span0, self.span1 = sp[0], sp[-1]
        self.le = Lin([(r[0], r[1]) for r in self.sec])
        self.te = Lin([(r[0], r[2]) for r in self.sec])
        self.h = Lin([(r[0], r[3]) for r in self.sec])
        self.t = Lin([(r[0], r[4]) for r in self.sec])
        self.frame = frame or (lambda span, y, h: np.stack(np.broadcast_arrays(span, y, h), axis=-1))
        self.airfoil = airfoil
        self.nc = nc
        self.kinks = sp

    def chord(self, span):
        return self.le(span) - self.te(span)

    def point(self, span, s, side):
        """Model space point at spanwise ``span``, chord fraction ``s`` (0 = LE), ``side`` +1 upper / -1 lower."""
        span = np.asarray(span, float)
        c = self.chord(span)
        y = self.le(span) - s * c
        h = self.h(span) + side * self.airfoil(s, self.t(span)) * c
        return self.frame(span, y, h)

    def spans(self, a, b, step=0.25):
        """Spanwise stations from a to b through every kink."""
        out = [a]
        for k in self.kinks:
            if a + 1e-6 < k < b - 1e-6:
                out.append(k)
        out.append(b)
        res = []
        for u, v in zip(out, out[1:]):
            n = max(1, int(math.ceil((v - u) / step)))
            res += list(np.linspace(u, v, n + 1))[:-1]
        res.append(b)
        return np.array(res)

    def patch(self, span_a, span_b, s0, s1, nc=None, step=0.25, cap0=False, cap1=False, s0f=None, s1f=None):
        """The skin between spans a..b and chord fractions s0..s1 (callables of span allowed) -> (verts, faces).
        Upper skin from s0 to s1 then the lower skin back: one closed strip per span station."""
        nc = nc or self.nc
        spans = self.spans(span_a, span_b, step)
        rings = []
        for sp in spans:
            a = s0(sp) if callable(s0) else s0
            b = s1(sp) if callable(s1) else s1
            k = 1.0 if (a <= 1e-6 and b >= 1 - 1e-6) else 0.6
            u = a + (b - a) * ease(nc, k if a <= 1e-6 else 0.3)
            up = self.point(sp, u, 1.0)
            lo = self.point(sp, u[::-1], -1.0)
            ring = np.vstack([up, lo[1:-1]]) if (a <= 1e-6 and b >= 1 - 1e-6) else np.vstack([up, lo])
            rings.append(ring)
        rings = np.array(rings)
        nr, ncol = rings.shape[:2]
        verts = rings.reshape(-1, 3)
        faces = grid_faces(nr, ncol, close=True)
        if cap0:
            faces.append(tuple(range(ncol))[::-1])
        if cap1:
            faces.append(tuple(range((nr - 1) * ncol, nr * ncol)))
        return verts, faces

    def tip_cap(self, span, rounding=0.0, n=4):
        """A closed tip: the last section, flattened to a point line (rounded wing tips: ``rounding`` metres)."""
        u = ease(self.nc, 1.0)
        up = self.point(span, u, 1.0)
        lo = self.point(span, u[::-1], -1.0)
        ring = np.vstack([up, lo[1:-1]])
        return ring


# ------------------------------------------------------------------ small helpers
def mirror_x(v):
    return np.asarray(v, float) * np.array([-1.0, 1.0, 1.0])


def rot_y(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])


def fin_frame(x_root, z_root, cant_deg, outward=1.0):
    """A fin standing on (x_root, z_root), leaning outwards by ``cant_deg`` from vertical: span = distance up the
    fin, h = the fin's own thickness direction (towards +x when it stands straight)."""
    c, s = math.cos(math.radians(cant_deg)), math.sin(math.radians(cant_deg))

    def frame(span, y, h):
        span, y, h = np.broadcast_arrays(np.asarray(span, float), np.asarray(y, float), np.asarray(h, float))
        x = x_root + outward * (span * s + h * c)
        z = z_root + span * c - h * s
        return np.stack([x, y, z], axis=-1)
    return frame
