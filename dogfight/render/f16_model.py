"""Detailed procedural F-16C Block 50 model.

Everything is generated from real dimensions (15.0 m long, 9.45 m span
without missiles), so no external 3D files are needed:

* blended wing-body fuselage lofted from smooth (Catmull-Rom) cross sections
* NACA 4 % airfoils on wing, stabilators and fin
* chin intake with lip and a dark duct you can look into
* tall bubble canopy (light gold tint) with frame, bow and mirrors over a real cockpit tub:
  ACES II seat, consoles, instrument panel with MFDs, glareshield and HUD (see cockpit.py)
* convergent-divergent nozzle with petals and flame holder
* pitot, AoA probes, IFF "bird slicer" antennas, blade antennas, gun port
* painted texture: two-tone grey (or aggressor camouflage), panel lines,
  rivets, soot, USAF insignia, tail code and serial

The painted parts get UVs from a planar atlas (top / bottom / right / left
views), chosen per triangle from its normal.
"""

import math
import os

import numpy as np
from panda3d.core import (Filename, Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
                          GeomVertexWriter, Mat3, Material, NodePath, PNMImage, PNMTextMaker, Quat, TexGenAttrib,
                          Texture, TextureStage, TransparencyAttrib, Vec3, Vec4)

from .meshbuilder import MeshBuilder, ellipse_ring

# atlas bounds (metres)
X0, X1 = -5.3, 5.3
Y0, Y1 = -8.0, 8.8
Z0, Z1 = -2.3, 4.1
TEX = 2048
Q = TEX // 2

# ------------------------------------------------------------- shape tables
#   y,     top,   bottom, half width, chine z, exponent (lower = sharper blended chine)
FUSELAGE = (
    (-7.00, 0.50, -0.38, 0.52, 0.06, 2.10),
    (-6.40, 0.57, -0.42, 0.61, 0.07, 2.05),
    (-5.40, 0.67, -0.49, 0.76, 0.08, 1.95),
    (-4.20, 0.77, -0.55, 0.90, 0.10, 1.85),
    (-3.00, 0.85, -0.58, 1.02, 0.12, 1.75),
    (-1.50, 0.90, -0.60, 1.08, 0.13, 1.70),
    (0.00, 0.92, -0.60, 0.98, 0.13, 1.72),
    (1.20, 0.94, -0.58, 0.80, 0.13, 1.80),
    (2.00, 0.93, -0.56, 0.70, 0.12, 1.85),
    (3.00, 0.86, -0.54, 0.62, 0.11, 1.90),
    (3.80, 0.79, -0.52, 0.58, 0.10, 1.95),
    (4.60, 0.72, -0.48, 0.58, 0.09, 2.00),
    (5.30, 0.65, -0.42, 0.52, 0.09, 2.00),
    (6.00, 0.57, -0.34, 0.45, 0.10, 2.00),
    (6.60, 0.50, -0.25, 0.38, 0.11, 2.00),      # radome: ogive, not a cone
    (7.15, 0.41, -0.14, 0.29, 0.12, 2.00),
    (7.60, 0.31, -0.04, 0.19, 0.13, 2.00),
    (7.92, 0.22, 0.04, 0.095, 0.13, 2.00),
    (8.08, 0.14, 0.12, 0.004, 0.13, 2.00),
)

INTAKE = (   # y, half width, top, bottom
    (-3.20, 0.28, -0.50, -0.60),
    (-2.50, 0.38, -0.50, -0.68),
    (-1.20, 0.48, -0.48, -0.86),
    (0.20, 0.55, -0.45, -1.03),
    (1.50, 0.58, -0.42, -1.16),
    (2.60, 0.59, -0.38, -1.24),
    (3.30, 0.58, -0.36, -1.27),
    (3.55, 0.56, -0.35, -1.28),
)

CANOPY = (   # y, half width, height above the sill (a tall one-piece bubble)
    (1.40, 0.05, 0.04), (1.72, 0.30, 0.42), (2.10, 0.42, 0.70), (2.60, 0.465, 0.83), (3.20, 0.47, 0.84),
    (3.80, 0.45, 0.74), (4.40, 0.39, 0.56), (4.90, 0.29, 0.36), (5.25, 0.14, 0.13), (5.42, 0.03, 0.02),
)
COCKPIT_OPEN = (1.98, 4.30)       # y range of the cockpit opening in the skin
COCKPIT_RAMP = 0.14
TUB_FLOOR = ((1.98, 0.62), (2.25, 0.20), (2.6, 0.08), (3.55, 0.08), (4.0, 0.30), (4.30, 0.55))
TUB_UV_SPOT = (-5.10, 8.55)       # unused corner of the top-view atlas painted in cockpit grey
TUB_PROFILE = ((0.995, 0.25), (0.985, 0.6), (0.97, 0.9), (0.92, 1.0), (0.5, 1.0), (0.0, 1.0), (-0.5, 1.0),
               (-0.92, 1.0), (-0.97, 0.9), (-0.985, 0.6), (-0.995, 0.25))

WING = ((0.85, 1.59, -3.15), (4.72, -1.95, -3.05))
STRAKE_EDGE = ((1.00, 1.30), (1.18, 1.30), (1.6, 1.10), (2.2, 0.93), (2.8, 0.78), (3.4, 0.64), (4.0, 0.52),
               (4.6, 0.40), (4.85, 0.30))          # (y, half width) of the leading edge root extension             # (x, LE y, TE y) root / tip
STAB = ((0.70, -4.60, -7.05), (2.80, -6.30, -7.10))
FIN = ((0.45, -3.10, -6.95), (3.75, -5.75, -6.65))              # (z, LE y, TE y)


def _catmull(table, y, col):
    ys = [r[0] for r in table]
    if y <= ys[0]:
        return table[0][col]
    if y >= ys[-1]:
        return table[-1][col]
    i = max(k for k in range(len(ys) - 1) if ys[k] <= y)
    p0 = table[max(i - 1, 0)][col]
    p1 = table[i][col]
    p2 = table[i + 1][col]
    p3 = table[min(i + 2, len(ys) - 1)][col]
    t = (y - ys[i]) / (ys[i + 1] - ys[i])
    t2 = t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t2 * t)


def fuselage_top(y):
    return _catmull(FUSELAGE, y, 1)


def _section_params(y):
    return tuple(_catmull(FUSELAGE, y, c) for c in range(1, 6))


def surface_z(y, x):
    """Height of the upper fuselage skin at station y, lateral offset x (ignoring the cockpit cut)."""
    top, bottom, hw, cz, n = _section_params(y)
    c = min(abs(x) / max(hw, 1e-6), 1.0) ** (n / 2.0)
    s = math.sqrt(max(0.0, 1.0 - c * c))
    return cz + (top - cz) * s ** (2.0 / n)


def tub_depth(y):
    a, b = COCKPIT_OPEN
    t = min(max((y - a) / COCKPIT_RAMP, 0.0), 1.0) * min(max((b - y) / COCKPIT_RAMP, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def opening_half_width(y):
    return max(0.14, _canopy_half_width(y) - 0.035)


def cockpit_rim(y):
    """(half width, z) of the edge of the cockpit opening."""
    w = opening_half_width(y)
    return w, surface_z(y, w)


def fuselage_section(y, segments=48):
    """Ring of skin points: the outer arc (left rim -> bottom -> right rim) followed by the cockpit tub
    profile (right rim -> left rim).  Outside the cockpit the tub depth is zero, so those points simply
    lie on the top of the fuselage and every ring has the same number of points."""
    top, bottom, hw, cz, n = _section_params(y)
    e = 2.0 / n
    w = min(opening_half_width(y), hw * 0.9)
    tc = math.acos(min((w / hw) ** (n / 2.0), 1.0))

    def ring_point(t):
        c, s = math.cos(t), math.sin(t)
        h = (top - cz) if s >= 0 else (cz - bottom)
        return Vec3(hw * math.copysign(abs(c) ** e, c), y, cz + h * math.copysign(abs(s) ** e, s))
    t0, t1 = math.pi - tc, 2 * math.pi + tc
    pts = [ring_point(t0 + (t1 - t0) * k / segments) for k in range(segments + 1)]
    depth = tub_depth(y)
    floor = float(np.interp(y, [f[0] for f in TUB_FLOOR], [f[1] for f in TUB_FLOOR]))
    for fx, f in TUB_PROFILE:
        x = fx * w
        zt = surface_z(y, x)
        pts.append(Vec3(x, y, zt + (floor - zt) * f * depth))
    pts.append(Vec3(pts[0]))
    return pts


def naca_points(n=14, thickness=0.04):
    """Closed airfoil outline (chord 0..1) TE -> upper -> LE -> lower -> TE."""
    xs = [0.5 * (1 - math.cos(math.pi * k / n)) for k in range(n + 1)]       # cosine spacing

    def yt(x):
        return 5 * thickness * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    upper = [(x, yt(x)) for x in reversed(xs)]
    lower = [(x, -yt(x)) for x in xs[1:]]
    return upper + lower


# ------------------------------------------------------------ painted mesh
class PaintedMesh:
    """Smooth shaded triangles that get atlas UVs (top / bottom / side views)."""

    def __init__(self):
        self.tris = []

    def tri(self, a, b, c, na, nb, nc, fixed=False):
        self.tris.append((a, b, c, na, nb, nc, fixed))

    def loft(self, rings, hint=None, flip=False, smooth=True, fixed=None):
        """``fixed(i, k)`` -> True gives that face the flat cockpit-grey UV instead of the paint atlas."""
        n = len(rings[0])
        normals = [[Vec3(0, 0, 0) for _ in range(n)] for _ in rings]
        faces = []
        for i in range(len(rings) - 1):
            r0, r1 = rings[i], rings[i + 1]
            center = (sum(r0, Vec3(0)) / n + sum(r1, Vec3(0)) / n) * 0.5
            for k in range(n - 1):
                a, b, c, d = r0[k], r0[k + 1], r1[k + 1], r1[k]
                fn = (b - a).cross(d - a)
                if fn.length() < 1e-12:
                    fn = (c - b).cross(d - b)
                mid = (a + b + c + d) * 0.25
                out = hint(mid) if hint is not None else mid - center
                f = fn.dot(out) < 0.0
                if flip:
                    f = not f
                if f:
                    fn = -fn
                if fn.length() > 1e-12:
                    fn.normalize()
                for ii, kk in ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)):
                    normals[ii][kk] += fn
                faces.append((i, k, f, fn))
        for i, ring in enumerate(rings):
            if (ring[0] - ring[-1]).length() < 1e-6:
                seam = normals[i][0] + normals[i][n - 1]
                normals[i][0] = Vec3(seam)
                normals[i][n - 1] = Vec3(seam)
            for k in range(n):
                if normals[i][k].length() > 1e-12:
                    normals[i][k].normalize()
        for i, k, f, fn in faces:
            idx = ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k))
            p = [rings[a][b] for a, b in idx]
            nn = [normals[a][b] if smooth else fn for a, b in idx]
            fx = bool(fixed and fixed(i, k))
            if f:
                self.tri(p[0], p[3], p[2], nn[0], nn[3], nn[2], fx)
                self.tri(p[0], p[2], p[1], nn[0], nn[2], nn[1], fx)
            else:
                self.tri(p[0], p[1], p[2], nn[0], nn[1], nn[2], fx)
                self.tri(p[0], p[2], p[3], nn[0], nn[2], nn[3], fx)

    def cap(self, ring, center, outward):
        for k in range(len(ring) - 1):
            a, b = ring[k], ring[k + 1]
            fn = (a - center).cross(b - center)
            if fn.dot(outward) < 0:
                a, b = b, a
            n = Vec3(outward)
            n.normalize()
            self.tri(center, a, b, n, n, n)

    def mirrored(self):
        pm = PaintedMesh()
        for a, b, c, na, nb, nc, fx in self.tris:
            m = [Vec3(-v.x, v.y, v.z) for v in (a, b, c, na, nb, nc)]
            pm.tris.append((m[0], m[2], m[1], m[3], m[5], m[4], fx))
        return pm

    def extend(self, other):
        self.tris.extend(other.tris)

    @staticmethod
    def _uv(p, region):
        u_top = (p.x - X0) / (X1 - X0) * 0.5
        v_len = (p.y - Y0) / (Y1 - Y0) * 0.5
        v_side = (p.z - Z0) / (Z1 - Z0) * 0.5
        if region == 0:          # top view: top-left quadrant
            return u_top, 0.5 + v_len
        if region == 1:          # bottom view: top-right quadrant
            return 0.5 + u_top, 0.5 + v_len
        if region == 2:          # right side (+x): bottom-left
            return v_len, v_side
        return 0.5 + (0.5 - v_len), v_side   # left side, mirrored so text reads correctly

    def build(self, name, origin=None, quat_inv=None):
        """UVs come from the model-space position; ``origin`` / ``quat_inv`` then move the
        vertices into a hinge frame (for control surfaces)."""
        fmt = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData(name, fmt, Geom.UHStatic)
        vdata.setNumRows(len(self.tris) * 3)
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        tw = GeomVertexWriter(vdata, "texcoord")
        tub_uv = self._uv(Vec3(TUB_UV_SPOT[0], TUB_UV_SPOT[1], 0.0), 0)
        for a, b, c, na, nb, nc, fx in self.tris:
            fn = (b - a).cross(c - a)
            if fn.length() > 1e-12:
                fn.normalize()
            if fn.z > 0.55:
                region = 0
            elif fn.z < -0.55:
                region = 1
            else:
                region = 2 if fn.x >= 0.0 else 3
            for p, n in ((a, na), (b, nb), (c, nc)):
                u, v = tub_uv if fx else self._uv(p, region)
                if quat_inv is not None:
                    p = quat_inv.xform(p - origin)
                    n = quat_inv.xform(n)
                vw.addData3(p)
                nw.addData3(n)
                tw.addData2(u, v)
        prim = GeomTriangles(Geom.UHStatic)
        prim.setIndexType(Geom.NT_uint32)
        for i in range(len(self.tris)):
            prim.addVertices(3 * i, 3 * i + 1, 3 * i + 2)
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)
        return NodePath(node)


# ---------------------------------------------------------------- geometry
def _yt(x, thickness):
    x = min(max(x, 0.0), 1.0)
    return 5 * thickness * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4)


def _airfoil_part(pm, root, tip, root_z, tip_z, thickness, axis="z", stations=10, chord=(0.0, 1.0),
                  span=(0.0, 1.0), caps=(False, True), points=18):
    """A lifting surface (or a chordwise / spanwise slice of it for control surfaces).

    root / tip = (span position, LE y, TE y); ``chord`` = (a, b) chord fractions, either
    constants or callables of the span position; ``span`` = (t0, t1) fraction of the span.
    Upper, lower and cut faces are lofted separately so every edge stays crisp.
    """
    ca = chord[0] if callable(chord[0]) else (lambda s, v=chord[0]: v)
    cb = chord[1] if callable(chord[1]) else (lambda s, v=chord[1]: v)
    up = Vec3(0, 0, 1) if axis == "z" else Vec3(1, 0, 0)
    uppers, lowers = [], []
    for k in range(stations + 1):
        t = span[0] + (span[1] - span[0]) * k / stations
        sp = root[0] + (tip[0] - root[0]) * t
        le = root[1] + (tip[1] - root[1]) * t
        te = root[2] + (tip[2] - root[2]) * t
        zc = root_z + (tip_z - root_z) * t
        c = le - te
        a, b = ca(sp), cb(sp)
        xs = [a + (b - a) * 0.5 * (1 - math.cos(math.pi * j / points)) for j in range(points + 1)]

        def pt(x, side):
            y = le - x * c
            off = side * _yt(x, thickness) * c
            return Vec3(sp, y, zc + off) if axis == "z" else Vec3(off, y, sp)
        uppers.append([pt(x, 1.0) for x in xs])
        lowers.append([pt(x, -1.0) for x in xs])
    pm.loft(uppers, hint=lambda m: up)
    pm.loft(lowers, hint=lambda m: -up)
    chord_dir = Vec3(0, 1, 0)
    for rings, out in (([[u[0], l[0]] for u, l in zip(uppers, lowers)], chord_dir),
                       ([[u[-1], l[-1]] for u, l in zip(uppers, lowers)], -chord_dir)):
        if (rings[0][0] - rings[0][1]).length() > 1e-4 or (rings[-1][0] - rings[-1][1]).length() > 1e-4:
            pm.loft(rings, hint=lambda m, o=out: o, smooth=False)
    span_dir = Vec3(1, 0, 0) if axis == "z" else Vec3(0, 0, 1)
    for end, wanted, sign in ((0, caps[0], -1.0), (-1, caps[1], 1.0)):
        if not wanted:
            continue
        ring = uppers[end] + lowers[end][::-1] + [uppers[end][0]]
        center = sum(ring[:-1], Vec3(0)) / (len(ring) - 1)
        pm.cap(ring, center, span_dir * sign)
    return uppers, lowers


def _airfoil_surface(pm, root, tip, root_z, tip_z, thickness, axis="z", stations=10, cap=True):
    _airfoil_part(pm, root, tip, root_z, tip_z, thickness, axis, stations, caps=(False, cap))


def _fuselage(pm):
    rings = []
    y = Y0 + 1.0                                     # -7.0
    ys = []
    a, b = COCKPIT_OPEN
    while y < 8.08:
        ys.append(y)
        near_cockpit = a - 0.05 < y < a + COCKPIT_RAMP + 0.05 or b - COCKPIT_RAMP - 0.05 < y < b + 0.05
        y += 0.035 if near_cockpit else 0.12 if y > 6.0 or y < -6.0 else 0.2
    ys.append(8.08)
    for y in ys:
        rings.append(fuselage_section(y))
    segments = len(rings[0]) - len(TUB_PROFILE) - 2       # outer arc faces come first

    def hint(m):
        top, bottom, hw, cz, n = _section_params(m.y)
        if abs(m.x) < min(opening_half_width(m.y), hw * 0.9) and m.z > cz + 0.05:
            return Vec3(-m.x, 0, 3.0 - m.z)          # cockpit tub (or the plain top): faces up / inwards
        return Vec3(m.x, 0, m.z - 0.1)

    def in_tub(i, k):
        return k >= segments and (tub_depth(ys[i]) > 0.0 or tub_depth(ys[i + 1]) > 0.0)
    pm.loft(rings, hint=hint, fixed=in_tub)
    # leading edge root extensions (the F-16's sharp strakes)
    half = PaintedMesh()
    ys = [e[0] for e in STRAKE_EDGE]
    ws = [e[1] for e in STRAKE_EDGE]
    rings = []
    for y in np.linspace(ys[0], ys[-1], 16):
        edge = float(np.interp(y, ys, ws))
        cz = _catmull(FUSELAGE, y, 4) + 0.01
        x_in = 0.25
        prof = ((0.0, -0.065), (0.45, -0.05), (0.8, -0.025), (1.0, 0.0), (0.8, 0.03), (0.45, 0.055), (0.0, 0.075))
        rings.append([Vec3(x_in + (edge - x_in) * f, y, cz + dz) for f, dz in prof])
    half.loft(rings, hint=lambda m: Vec3(m.x - 0.3, 0, (m.z - 0.11) * 4.0))
    pm.extend(half)
    pm.extend(half.mirrored())


def _intake(pm, plain):
    rings = []
    for y, hw, top, bot in INTAKE:
        ring = ellipse_ring(y, hw, (top + bot) * 0.5, (top - bot) * 0.5, segments=28, exponent=3.6)
        # upper lip sticks out further than the lower one
        rings.append([Vec3(p.x, p.y + (p.z - (top + bot) * 0.5) * 0.35 if y > 3.4 else p.y, p.z) for p in ring])
    pm.loft(rings, hint=lambda m: Vec3(m.x, 0, m.z + 0.8))
    outer = rings[-1]
    cz = (INTAKE[-1][2] + INTAKE[-1][3]) * 0.5
    inner = [Vec3(p.x * 0.86, p.y - 0.04, cz + (p.z - cz) * 0.84) for p in outer]
    lip = (0.62, 0.64, 0.66, 1.0)
    plain.loft([outer, inner], lip)
    duct = [inner]
    for depth, scale, dark in ((0.6, 0.8, 0.12), (1.6, 0.72, 0.06), (2.8, 0.6, 0.03)):
        duct.append([Vec3(p.x * scale / 0.86, p.y - depth, cz + (p.z - cz) * scale / 0.84) for p in outer])
    # inward facing duct: build then reverse winding
    mb = MeshBuilder()
    mb.loft(duct, lambda p, n: (0.10, 0.10, 0.11, 1.0) if p.y > 2.6 else (0.03, 0.03, 0.035, 1.0))
    mb.tris = [(a, c, b) for a, b, c in mb.tris]
    mb.verts = [(p, -n, col) for p, n, col in mb.verts]
    plain.extend(mb)
    last = duct[-1]
    center = sum(last, Vec3(0)) / len(last)
    plain._cap(last, center, Vec3(0, 1, 0), (0.02, 0.02, 0.02, 1.0))     # engine face


def _nozzle(plain):
    petals = 15
    rings = []
    for y, r in ((-6.95, 0.53), (-7.12, 0.535), (-7.32, 0.505), (-7.55, 0.465)):
        ring = []
        for k in range(petals * 2 + 1):
            a = 2 * math.pi * k / (petals * 2)
            rr = r * (1.0 + (0.012 if k % 2 else 0.0))
            ring.append(Vec3(math.cos(a) * rr, y, 0.07 + math.sin(a) * rr))
        rings.append(ring)

    def petal_color(p, n):
        a = math.atan2(p.z - 0.07, p.x) % (2 * math.pi)
        k = int(a / (2 * math.pi) * petals)
        heat = max(0.0, min(1.0, (-p.y - 7.0) / 0.55))
        base = 0.40 if k % 2 else 0.34
        return (base + 0.06 * heat * 0.3, base - 0.01, base - 0.03 + 0.05 * heat, 1.0)
    plain.loft(rings, petal_color)
    # inner wall + flame holder
    exit_ring = rings[-1]
    inner = [Vec3(p.x * 0.93, p.y + 0.02, 0.07 + (p.z - 0.07) * 0.93) for p in exit_ring]
    plain.loft([exit_ring, inner], (0.22, 0.20, 0.19, 1.0))
    deep = [Vec3(p.x * 0.95, -6.95, 0.07 + (p.z - 0.07) * 0.95) for p in inner]
    mb = MeshBuilder()
    mb.loft([inner, deep], lambda p, n: (0.16, 0.14, 0.13, 1.0) if p.y < -7.3 else (0.07, 0.06, 0.06, 1.0))
    mb.tris = [(a, c, b) for a, b, c in mb.tris]
    mb.verts = [(p, -n, col) for p, n, col in mb.verts]
    plain.extend(mb)
    plain._cap(deep, Vec3(0, -6.95, 0.07), Vec3(0, -1, 0), (0.05, 0.045, 0.045, 1.0))
    for r in (0.18, 0.32):                       # flame holder rings
        ring = [Vec3(math.cos(a) * r, -7.0, 0.07 + math.sin(a) * r) for a in
                (2 * math.pi * k / 24 for k in range(25))]
        ring2 = [Vec3(p.x * 1.12, p.y, 0.07 + (p.z - 0.07) * 1.12) for p in ring]
        plain.loft([ring, ring2], (0.12, 0.11, 0.10, 1.0))


def _canopy_base(y, w):
    return surface_z(y, w) - 0.005


def _canopy(glass, frame, interior):
    """Bubble canopy sitting on the skin, its frame and the cockpit (returns the textured cockpit meshes)."""
    rings = []
    for y, w, h in CANOPY:
        rings.append(ellipse_ring(y, w, _canopy_base(y, w), h, segments=22, start=0.0, end=math.pi))
    glass.loft(rings, (0.62, 0.54, 0.30, 0.20))
    frame_col = (0.16, 0.17, 0.18, 1.0)
    # aft canopy bow behind the head box, with the three rear view mirrors
    y = 1.93
    w, h = _canopy_half_width(y) + 0.012, float(np.interp(y, [c[0] for c in CANOPY], [c[2] for c in CANOPY])) + 0.012
    arc = ellipse_ring(y, w, _canopy_base(y, w - 0.012), h, segments=14, start=0.0, end=math.pi)
    for p0, p1 in zip(arc, arc[1:]):
        _beam(frame, p0, p1, 0.026, frame_col)
    for k in (4, 7, 10):
        p = arc[k]
        inward = Vec3(-p.x, 0, _canopy_base(y, w) - p.z)
        inward.normalize()
        c = p + inward * 0.05 + Vec3(0, 0.05, 0)
        _box(interior, (c.x, c.y, c.z), (0.045, 0.006, 0.022), (0.55, 0.62, 0.70, 1.0))
    # sill rails along both sides
    for side in (-1, 1):
        pts = []
        for yy in (1.93, 2.4, 3.0, 3.6, 4.2, 4.7, 5.15):
            ww = _canopy_half_width(yy)
            pts.append(Vec3(side * (ww + 0.008), yy, _canopy_base(yy, ww) + 0.012))
        for p0, p1 in zip(pts, pts[1:]):
            _beam(frame, p0, p1, 0.022, frame_col)
    from .cockpit import build_cockpit           # late import keeps the module graph simple
    return build_cockpit(interior, glass, cockpit_rim)


def _canopy_half_width(y):
    ys = [c[0] for c in CANOPY]
    ws = [c[1] for c in CANOPY]
    return float(np.interp(y, ys, ws))


def _box(mb, c, h, color):
    from .models import box          # late import: models imports this module
    box(mb, c, h, color)


def _beam(mb, a, b, r, color):
    d = b - a
    length = d.length()
    d.normalize()
    side = d.cross(Vec3(0, 0, 1))
    if side.length() < 1e-3:
        side = Vec3(1, 0, 0)
    side.normalize()
    up = side.cross(d)
    corners = [side * r + up * r, -side * r + up * r, -side * r - up * r, side * r - up * r]
    r0 = [a + c for c in corners] + [a + corners[0]]
    r1 = [a + d * length + c for c in corners] + [a + d * length + corners[0]]
    mb.loft([r0, r1], color, smooth=False)


def _cylinder(mb, a, b, r, color, segments=8):
    d = b - a
    d.normalize()
    side = d.cross(Vec3(0, 0, 1))
    if side.length() < 1e-3:
        side = d.cross(Vec3(1, 0, 0))
    side.normalize()
    up = side.cross(d)
    rings = []
    for p in (a, b):
        rings.append([p + side * (math.cos(t) * r) + up * (math.sin(t) * r)
                      for t in (2 * math.pi * k / segments for k in range(segments + 1))])
    mb.loft(rings, color, cap_front=color, cap_back=color)


def _details(plain):
    metal = (0.62, 0.63, 0.64, 1.0)
    gray = (0.50, 0.53, 0.56, 1.0)
    # pitot boom and AoA probes
    _cylinder(plain, Vec3(0, 7.95, 0.12), Vec3(0, 8.75, 0.12), 0.022, metal)
    _cylinder(plain, Vec3(0, 8.75, 0.12), Vec3(0, 8.82, 0.12), 0.012, metal)
    for side in (-1, 1):
        _cylinder(plain, Vec3(side * 0.30, 6.25, 0.18), Vec3(side * 0.42, 6.30, 0.18), 0.012, metal, 6)
    # IFF "bird slicer" antennas in front of the canopy (Block 50)
    for y in (5.55, 5.75, 5.95, 6.15):
        z = fuselage_top(y)
        plain.surface(Vec3(0, y + 0.04, z - 0.02), Vec3(0, y - 0.03, z - 0.02), Vec3(0, y - 0.01, z + 0.11),
                      Vec3(0, y - 0.04, z + 0.11), 0.012, 0.008, Vec3(1, 0, 0), gray)
    # blade antennas (UHF on the spine, IFF under the intake)
    plain.surface(Vec3(0, 0.95, 0.93), Vec3(0, 0.55, 0.93), Vec3(0, 0.62, 1.15), Vec3(0, 0.5, 1.15), 0.02, 0.01,
                  Vec3(1, 0, 0), gray)
    plain.surface(Vec3(0, 1.9, -1.15), Vec3(0, 1.6, -1.15), Vec3(0, 1.65, -1.35), Vec3(0, 1.55, -1.35), 0.02, 0.01,
                  Vec3(1, 0, 0), gray)
    # gun port (left strake) and fin tip light
    _box(plain, (-0.80, 3.05, 0.36), (0.07, 0.16, 0.03), (0.06, 0.05, 0.05, 1.0))
    _box(plain, (0.0, -6.62, 3.74), (0.05, 0.14, 0.05), (0.85, 0.85, 0.8, 1.0))
    # wing tip launch rails (LAU-129)
    for side in (-1, 1):
        _box(plain, (side * 4.80, -0.75, 0.12), (0.05, 1.30, 0.045), (0.55, 0.57, 0.59, 1.0))
        _box(plain, (side * 4.80, -0.75, 0.06), (0.03, 1.20, 0.03), (0.35, 0.36, 0.37, 1.0))
    # pylons (airfoil shaped) for stations 2/8 and 3/7
    for side in (-1, 1):
        for x, y, bottom in ((3.75, -0.95, -0.27), (2.60, -0.55, -0.33)):
            _box(plain, (side * x, y, (bottom + 0.08) / 2), (0.045, 0.85, (0.08 - bottom) / 2),
                 (0.58, 0.61, 0.64, 1.0))
            _box(plain, (side * x, y - 0.05, bottom - 0.02), (0.05, 0.75, 0.03), (0.40, 0.41, 0.42, 1.0))


def _hinge_frame(p0, p1):
    """Quat whose local X axis runs along the hinge p0 -> p1."""
    x = p1 - p0
    x.normalize()
    ref = Vec3(0, 1, 0) if abs(x.y) < 0.9 else Vec3(0, 0, 1)
    y = ref - x * ref.dot(x)
    y.normalize()
    z = x.cross(y)
    q = Quat()
    q.setFromMatrix(Mat3(x.x, x.y, x.z, y.x, y.y, y.z, z.x, z.y, z.z))
    return q


def _hinge_sign(q, probe, check):
    """+1 / -1 so that a positive deflection moves ``probe`` (local) the way ``check`` wants."""
    r = Quat()
    r.setHpr((0, 10.0, 0))
    moved = q.xform(r.xform(probe)) - q.xform(probe)
    return 1.0 if check(moved) else -1.0


def _wing_geometry(pm, parts):
    (x0, le0, te0), (x1, le1, te1) = WING

    def t_of(x):
        return (x - x0) / (x1 - x0)

    def chord(x):
        t = t_of(x)
        return (le0 + (le1 - le0) * t) - (te0 + (te1 - te0) * t)

    def lef_f(x):
        return 0.40 / chord(x)

    def flap_f(x):
        return 1.0 - 0.62 / chord(x)
    zr, zt = 0.13, 0.11
    th = 0.045
    tf0, tf1 = t_of(1.25), t_of(3.15)
    _airfoil_part(pm, WING[0], WING[1], zr, zt, th, chord=(lef_f, 1.0), span=(0.0, tf0), stations=2, caps=(False, False))
    _airfoil_part(pm, WING[0], WING[1], zr, zt, th, chord=(lef_f, flap_f), span=(tf0, tf1), stations=6,
                  caps=(False, False))
    _airfoil_part(pm, WING[0], WING[1], zr, zt, th, chord=(lef_f, 1.0), span=(tf1, 1.0), stations=6, caps=(False, True))
    # leading edge flap (droops with angle of attack)
    lef = PaintedMesh()
    _airfoil_part(lef, WING[0], WING[1], zr, zt, th, chord=(0.0, lef_f), span=(t_of(1.05), 1.0), stations=10,
                  caps=(False, True))

    def wpt(x, back):
        t = t_of(x)
        le = le0 + (le1 - le0) * t
        return Vec3(x, le - back, zr + (zt - zr) * t)
    parts.append(dict(name="lef", mesh=lef, p0=wpt(1.05, 0.40), p1=wpt(4.72, 0.40), kind="le"))
    # flaperon
    flap = PaintedMesh()
    _airfoil_part(flap, WING[0], WING[1], zr, zt, th, chord=(flap_f, 1.0), span=(tf0, tf1), stations=4,
                  caps=(True, True))
    tpt = lambda x: Vec3(x, te0 + (te1 - te0) * t_of(x) + 0.62, zr + (zt - zr) * t_of(x))   # noqa: E731
    parts.append(dict(name="flap", mesh=flap, p0=tpt(1.25), p1=tpt(3.15), kind="te"))
    # all moving stabilator
    stab = PaintedMesh()
    _airfoil_part(stab, STAB[0], STAB[1], 0.10, -0.26, 0.045, stations=8, caps=(True, True))
    parts.append(dict(name="stab", mesh=stab, p0=Vec3(0.70, -5.75, 0.10), p1=Vec3(2.80, -5.75, -0.26), kind="te"))


def _fin_geometry(pm, parts):
    (z0, le0, te0), (z1, le1, te1) = FIN

    def t_of(z):
        return (z - z0) / (z1 - z0)

    def chord(z):
        t = t_of(z)
        return (le0 + (le1 - le0) * t) - (te0 + (te1 - te0) * t)

    def rud_f(z):
        return 1.0 - 0.66 / chord(z)
    ra, rb = t_of(0.95), t_of(3.55)
    _airfoil_part(pm, FIN[0], FIN[1], 0.0, 0.0, 0.05, axis="fin", span=(0.0, ra), stations=2, caps=(False, False))
    _airfoil_part(pm, FIN[0], FIN[1], 0.0, 0.0, 0.05, axis="fin", chord=(0.0, rud_f), span=(ra, rb), stations=8,
                  caps=(False, False))
    _airfoil_part(pm, FIN[0], FIN[1], 0.0, 0.0, 0.05, axis="fin", span=(rb, 1.0), stations=2, caps=(False, True))
    rudder = PaintedMesh()
    _airfoil_part(rudder, FIN[0], FIN[1], 0.0, 0.0, 0.05, axis="fin", chord=(rud_f, 1.0), span=(ra, rb), stations=6,
                  caps=(True, True))

    def hpt(z):
        t = t_of(z)
        return Vec3(0.0, te0 + (te1 - te0) * t + 0.66, z)
    parts.append(dict(name="rudder", mesh=rudder, p0=hpt(0.95), p1=hpt(3.55), kind="rudder"))
    # dorsal fillet
    _airfoil_surface(pm, (0.84, -2.10, -3.70), (1.40, -3.55, -3.95), 0.0, 0.0, 0.07, axis="fin", stations=2)


def _speedbrakes(parts):
    """Clamshell speed brakes beside the nozzle (upper and lower petal per side)."""
    for name, z_lo, z_hi in (("sb_up", 0.08, 0.40), ("sb_lo", -0.26, 0.06)):
        pm = PaintedMesh()
        x_in, x_out = 0.60, 0.66
        rings = []
        for y in (-6.22, -6.6, -7.0, -7.22):
            rings.append([Vec3(x_out, y, z_lo), Vec3(x_out, y, z_hi), Vec3(x_in, y, z_hi), Vec3(x_in, y, z_lo),
                          Vec3(x_out, y, z_lo)])
        pm.loft(rings, hint=lambda m: Vec3(m.x - 0.63, 0, m.z - (z_lo + z_hi) / 2), smooth=False)
        pm.cap(rings[-1], sum(rings[-1][:-1], Vec3(0)) / 4, Vec3(0, -1, 0))
        hinge_z = 0.07
        parts.append(dict(name=name, mesh=pm, p0=Vec3(0.55, -6.22, hinge_z), p1=Vec3(0.75, -6.22, hinge_z),
                          kind="up" if name == "sb_up" else "down"))


def build_detailed_f16():
    """Returns dict(skin, plain, glass, lights, parts=[...])."""
    pm = PaintedMesh()
    plain = MeshBuilder()
    glass = MeshBuilder()
    frame = MeshBuilder()
    interior = MeshBuilder()
    lights = MeshBuilder()

    _fuselage(pm)
    _intake(pm, plain)
    half = PaintedMesh()
    right_parts = []
    _wing_geometry(half, right_parts)
    # ventral fin (canted 15 deg outwards)
    vent = PaintedMesh()
    _airfoil_surface(vent, (-0.52, -3.70, -4.90), (-1.05, -4.30, -5.00), 0.0, 0.0, 0.06, axis="fin", stations=2)
    ca, sa = math.cos(math.radians(15)), math.sin(math.radians(15))

    def tilt(v, is_normal=False):
        x = v.x * ca - v.z * sa
        z = v.x * sa + v.z * ca
        return Vec3(x, v.y, z) if is_normal else Vec3(x + 0.55, v.y, z)
    for a, b, c, na, nb, nc, _fx in vent.tris:
        half.tri(tilt(a), tilt(b), tilt(c), tilt(na, True), tilt(nb, True), tilt(nc, True))
    _speedbrakes(right_parts)
    pm.extend(half)
    pm.extend(half.mirrored())

    parts = []
    for part in right_parts:
        parts.append(dict(part, name=part["name"] + "_R", side=1.0))
        mirrored = dict(part, name=part["name"] + "_L", side=-1.0, mesh=part["mesh"].mirrored(),
                        p0=Vec3(-part["p0"].x, part["p0"].y, part["p0"].z),
                        p1=Vec3(-part["p1"].x, part["p1"].y, part["p1"].z))
        parts.append(mirrored)
    _fin_geometry(pm, parts)

    # fin base housing (drag chute / ECM pod of the Block 50)
    rings = []
    for y, hw, hh in ((-5.75, 0.02, 0.02), (-5.95, 0.13, 0.17), (-6.4, 0.17, 0.22), (-7.0, 0.16, 0.21),
                      (-7.25, 0.12, 0.16)):
        rings.append(ellipse_ring(y, hw, 0.80, hh, segments=16))
    pm.loft(rings, hint=lambda m: Vec3(m.x, 0, m.z - 0.8))
    pm.cap(rings[-1], Vec3(0, -7.25, 0.80), Vec3(0, -1, 0))

    _nozzle(plain)
    cockpit_panels, cockpit_screens = _canopy(glass, frame, interior)
    _details(plain)
    _formation_lights(lights)
    plain.extend(frame)
    plain.extend(interior)

    out = dict(skin=pm.build("f16_skin"), plain=plain.build("f16_details"), glass=glass.build("f16_canopy"),
               lights=lights.build("f16_lights"), cockpit=cockpit_panels.build("f16_cockpit"),
               screens=cockpit_screens.build("f16_screens"), parts=[])
    for part in parts:
        p0, p1 = part["p0"], part["p1"]
        q = _hinge_frame(p0, p1)
        qi = Quat(q)
        qi.invertInPlace()
        kind = part["kind"]
        if kind == "te":
            sign = _hinge_sign(q, Vec3(0, -1, 0), lambda m: m.z < 0)       # trailing edge down
        elif kind == "le":
            sign = _hinge_sign(q, Vec3(0, 1, 0), lambda m: m.z < 0)        # leading edge down
        elif kind == "rudder":
            sign = _hinge_sign(q, Vec3(0, 0, -1) if abs(q.getRight().z) > 0.5 else Vec3(0, -1, 0),
                               lambda m: m.x > 0)                            # trailing edge right
        elif kind == "up":
            sign = _hinge_sign(q, Vec3(0, -1, 0), lambda m: m.z > 0)        # opens upwards
        else:
            sign = _hinge_sign(q, Vec3(0, -1, 0), lambda m: m.z < 0)        # opens downwards
        node = part["mesh"].build("surf", origin=p0, quat_inv=qi)
        out["parts"].append(dict(name=part["name"], node=node, pos=p0, quat=q, sign=sign))
    return out


def _formation_lights(mb):
    """Electroluminescent formation strips and position lights (unlit, they glow)."""
    strip = (0.70, 0.95, 0.70, 1.0)
    for side in (-1, 1):
        x = side * (_catmull(FUSELAGE, 4.0, 3) + 0.004)
        mb.quad(Vec3(x, 4.25, 0.24), Vec3(x, 3.75, 0.24), Vec3(x, 3.75, 0.28), Vec3(x, 4.25, 0.28), strip,
                outward=Vec3(side, 0, 0))
        x = side * (_catmull(FUSELAGE, -4.5, 3) + 0.004)
        mb.quad(Vec3(x, -4.3, 0.20), Vec3(x, -4.8, 0.20), Vec3(x, -4.8, 0.24), Vec3(x, -4.3, 0.24), strip,
                outward=Vec3(side, 0, 0))
        x = side * 0.062
        mb.quad(Vec3(x, -4.85, 2.30), Vec3(x, -5.25, 2.70), Vec3(x, -5.25, 2.75), Vec3(x, -4.85, 2.35), strip,
                outward=Vec3(side, 0, 0))


# ----------------------------------------------------------------- texture
class _Painter:
    """Paints the four atlas quadrants with numpy (rows bottom -> top)."""

    def __init__(self):
        self.img = np.ones((TEX, TEX, 3), np.float32)

    # metre -> pixel helpers per quadrant
    @staticmethod
    def top(x, y):
        return (x - X0) / (X1 - X0) * Q, Q + (y - Y0) / (Y1 - Y0) * Q

    @staticmethod
    def bottom(x, y):
        return Q + (x - X0) / (X1 - X0) * Q, Q + (y - Y0) / (Y1 - Y0) * Q

    @staticmethod
    def right(y, z):
        return (y - Y0) / (Y1 - Y0) * Q, (z - Z0) / (Z1 - Z0) * Q

    @staticmethod
    def left(y, z):
        return Q + (Y1 - y) / (Y1 - Y0) * Q, (z - Z0) / (Z1 - Z0) * Q

    def fill_rect(self, c0, r0, c1, r1, color, alpha=1.0):
        c0, c1 = sorted((int(c0), int(c1)))
        r0, r1 = sorted((int(r0), int(r1)))
        c0, r0 = max(c0, 0), max(r0, 0)
        c1, r1 = min(c1, TEX), min(r1, TEX)
        if c1 <= c0 or r1 <= r0:
            return
        reg = self.img[r0:r1, c0:c1]
        reg[:] = reg * (1 - alpha) + np.asarray(color, np.float32) * alpha

    def line(self, p0, p1, color, width=1.6, alpha=1.0, dotted=0):
        (c0, r0), (c1, r1) = p0, p1
        n = int(max(abs(c1 - c0), abs(r1 - r0))) + 1
        cs = np.linspace(c0, c1, n)
        rs = np.linspace(r0, r1, n)
        if dotted:
            keep = (np.arange(n) % dotted) == 0
            cs, rs = cs[keep], rs[keep]
        w = max(1, int(round(width)))
        for dc in range(w):
            for dr in range(w):
                cc = np.clip(cs.astype(int) + dc, 0, TEX - 1)
                rr = np.clip(rs.astype(int) + dr, 0, TEX - 1)
                self.img[rr, cc] = self.img[rr, cc] * (1 - alpha) + np.asarray(color, np.float32) * alpha

    def disc(self, c, r, radius, color, alpha=1.0):
        c, r = int(c), int(r)
        rad = int(radius) + 1
        yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
        mask = (xx * xx + yy * yy) <= radius * radius
        r0, c0 = r - rad, c - rad
        rows = np.clip(np.arange(r0, r0 + 2 * rad + 1), 0, TEX - 1)
        cols = np.clip(np.arange(c0, c0 + 2 * rad + 1), 0, TEX - 1)
        sub = self.img[np.ix_(rows, cols)]
        sub[mask] = sub[mask] * (1 - alpha) + np.asarray(color, np.float32) * alpha
        self.img[np.ix_(rows, cols)] = sub

    def polygon(self, pts, color, alpha=1.0):
        pts = np.asarray(pts, np.float32)
        cmin, rmin = np.floor(pts.min(0)).astype(int)
        cmax, rmax = np.ceil(pts.max(0)).astype(int)
        cmin, rmin = max(cmin, 0), max(rmin, 0)
        cmax, rmax = min(cmax, TEX - 1), min(rmax, TEX - 1)
        if cmax <= cmin or rmax <= rmin:
            return
        yy, xx = np.mgrid[rmin:rmax + 1, cmin:cmax + 1]
        inside = np.zeros(xx.shape, bool)
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            cond = ((y1 > yy) != (y2 > yy)) & (xx < (x2 - x1) * (yy - y1) / (y2 - y1 + 1e-9) + x1)
            inside ^= cond
        sub = self.img[rmin:rmax + 1, cmin:cmax + 1]
        sub[inside] = sub[inside] * (1 - alpha) + np.asarray(color, np.float32) * alpha

    def roundel(self, c, r, radius_px):
        """USAF star-and-bar (low visibility grey)."""
        dark = (0.30, 0.32, 0.35)
        light = (0.62, 0.64, 0.67)
        self.polygon([(c - radius_px * 2.0, r - radius_px * 0.32), (c + radius_px * 2.0, r - radius_px * 0.32),
                      (c + radius_px * 2.0, r + radius_px * 0.32), (c - radius_px * 2.0, r + radius_px * 0.32)],
                     dark, 0.9)
        self.disc(c, r, radius_px, dark, 0.95)
        star = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            rr = radius_px * (0.95 if k % 2 == 0 else 0.38)
            star.append((c + math.cos(a) * rr, r + math.sin(a) * rr))
        self.polygon(star, light, 1.0)


LIVERY_COLORS = {
    "viper": dict(upper=(0.52, 0.55, 0.59), lower=(0.66, 0.68, 0.71), dark=(0.38, 0.40, 0.44),
                  radome=(0.47, 0.49, 0.52), code="HL",
                  serial="AF 90-0700", stripe=(0.15, 0.15, 0.17)),
    "aggressor": dict(upper=(0.78, 0.66, 0.47), lower=(0.70, 0.73, 0.76), radome=(0.42, 0.40, 0.36), code="WA",
                      serial="AF 86-0291", stripe=(0.70, 0.12, 0.10), camo=((0.55, 0.40, 0.26), (0.86, 0.78, 0.60))),
}

_TEXTURES = {}


def _camo(p, quad_fn, coords, colors, seed):
    rng = np.random.default_rng(seed)
    # splinter camouflage: big random polygons
    for _ in range(46):
        cx = rng.uniform(coords[0], coords[1])
        cy = rng.uniform(coords[2], coords[3])
        size = rng.uniform(0.9, 2.2)
        k = rng.integers(len(colors))
        pts = []
        for j in range(5):
            a = j * 2 * math.pi / 5 + rng.uniform(-0.4, 0.4)
            rr = size * rng.uniform(0.5, 1.0)
            pts.append(quad_fn(cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        p.polygon(pts, colors[k], 1.0)


def livery_texture(name):
    if name in _TEXTURES:
        return _TEXTURES[name]
    L = LIVERY_COLORS[name]
    p = _Painter()
    img = p.img
    rng = np.random.default_rng(7)
    up = np.asarray(L["upper"], np.float32)
    lo = np.asarray(L["lower"], np.float32)
    dark = np.asarray(L.get("dark", L["upper"]), np.float32)
    grid = (np.arange(Q) + 0.5) / Q
    xs = X0 + grid * (X1 - X0)                     # top / bottom view columns
    ys = Y0 + grid * (Y1 - Y0)                     # top / bottom view rows, side view columns
    zs = Z0 + grid * (Z1 - Z0)                     # side view rows
    body_hw = np.array([_catmull(FUSELAGE, y, 3) for y in ys], np.float32)
    body_top = np.array([fuselage_top(y) for y in ys], np.float32)
    strake = np.interp(ys, [e[0] for e in STRAKE_EDGE], [e[1] for e in STRAKE_EDGE], left=0.0, right=0.0)

    def smooth(e0, e1, v):
        t = np.clip((v - e0) / (e1 - e0), 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)

    # --- top view: medium grey wings, dark grey spine and strakes (F-16 "Hill grey" scheme)
    dw = np.maximum(body_hw * 0.82, strake * 0.97)
    dw = np.where((ys > -6.9) & (ys < 5.9), dw, 0.0)
    wave = 0.04 * np.sin(ys * 3.1)
    inside = smooth(0.06, -0.06, np.abs(xs)[None, :] - (dw + wave)[:, None])
    top_img = up[None, None, :] * (1 - inside[..., None]) + dark[None, None, :] * inside[..., None]
    # ambient occlusion where wing and body meet
    ao = 1.0 - 0.13 * np.exp(-((np.abs(xs)[None, :] - (body_hw + 0.05)[:, None]) / 0.16) ** 2) * \
        ((ys > -3.3) & (ys < 1.5))[:, None]
    soot = 1.0 - 0.25 * smooth(-6.2, -7.0, ys)[:, None] * (np.abs(xs) < 0.75)[None, :]
    img[Q:, :Q] = top_img * (ao * soot)[..., None]
    img[Q:, Q:] = lo
    img[Q:, Q:] *= (1.0 - 0.10 * np.exp(-((np.abs(xs)[None, :] - (body_hw + 0.05)[:, None]) / 0.16) ** 2)
                    * ((ys > -3.3) & (ys < 1.5))[:, None])[..., None]

    # --- side views: dark spine, medium sides and fin, light belly
    Zg = zs[:, None]
    dark_mask = smooth(body_top - 0.34, body_top - 0.26, Zg) * (1.0 - smooth(body_top + 0.02, body_top + 0.12, Zg))
    dark_mask *= ((ys > -6.9) & (ys < 5.9))[None, :]
    light_mask = smooth(0.12, 0.0, Zg + 0.03 * np.sin(ys * 2.3)[None, :])
    side = np.empty((Q, Q, 3), np.float32)
    side[:] = up
    side = side * (1 - dark_mask[..., None]) + dark * dark_mask[..., None]
    side = side * (1 - light_mask[..., None]) + lo * light_mask[..., None]
    occl = 1.0 - 0.12 * np.exp(-((Zg - 0.02) / 0.09) ** 2) * ((ys > -3.6) & (ys < 4.6))[None, :]
    occl *= 1.0 - 0.14 * np.exp(-((Zg + 0.47) / 0.06) ** 2) * ((ys > -2.4) & (ys < 3.5))[None, :]
    side *= occl[..., None]
    img[:Q, :Q] = side                                       # right side view (columns: y increasing)
    img[:Q, Q:] = side[:, ::-1]                              # left side view is mirrored
    if "camo" in L:
        cam = list(L["camo"]) + [tuple(L["upper"])]
        _camo(p, p.top, (X0, X1, Y0, Y1), cam, 3)
        _camo(p, p.right, (Y0, Y1, 0.1, Z1), cam, 4)
        _camo(p, p.left, (Y0, Y1, 0.1, Z1), cam, 5)

    # radome
    p.fill_rect(*p.top(X0, 6.0), *p.top(X1, Y1), L["radome"])
    p.fill_rect(*p.bottom(X0, 6.0), *p.bottom(X1, Y1), L["radome"])
    for quad in (p.right, p.left):
        c0, r0 = quad(6.0, Z0)
        c1, r1 = quad(Y1, 0.8)
        p.fill_rect(c0, r0, c1, r1, L["radome"])

    panel = (0.30, 0.32, 0.34)
    alpha = 0.17
    # --- panel lines: fuselage stations
    # (station, side view z range) - short, staggered seams instead of hoops around the whole body
    stations = ((6.0, -0.30, 0.55), (4.8, -0.45, 0.45), (1.2, -0.20, 0.50), (-0.5, 0.05, 0.62), (-2.3, -0.35, 0.40),
                (-4.0, -0.10, 0.62), (-5.6, -0.30, 0.50))
    for y, za, zb in stations:
        for quad in (p.top, p.bottom):
            p.line(quad(-0.55, y), quad(0.55, y), panel, 1.3, alpha)
        for quad in (p.right, p.left):
            p.line(quad(y, za), quad(y, zb), panel, 1.3, alpha)
    for x in (-0.75, -0.38, 0.38, 0.75):
        for quad in (p.top, p.bottom):
            p.line(quad(x, -6.9), quad(x, 1.8), panel, 1.4, alpha * 0.8)
    for quad in (p.right, p.left):
        p.line(quad(-6.9, 0.48), quad(5.4, 0.48), panel, 1.4, alpha * 0.8)
        p.line(quad(-6.9, -0.25), quad(3.4, -0.25), panel, 1.4, alpha * 0.7)
        p.line(quad(-6.9, -0.75), quad(3.4, -0.75), panel, 1.4, alpha * 0.7)
        # access panels with rivets
        for (ya, yb, za, zb) in ((3.6, 4.3, -0.1, 0.35), (-1.0, -0.2, 0.1, 0.42), (-3.0, -2.2, -0.2, 0.3),
                                 (-5.3, -4.5, -0.05, 0.35), (1.0, 1.8, -0.55, -0.3)):
            pts = [quad(ya, za), quad(yb, za), quad(yb, zb), quad(ya, zb)]
            for a, b in zip(pts, pts[1:] + pts[:1]):
                p.line(a, b, panel, 1.2, alpha * 0.7)
                p.line(a, b, (0.85, 0.87, 0.9), 1.0, 0.25, dotted=6)
        # fin: rudder hinge line and tail markings
        p.line(quad(-6.15, 0.95), quad(-6.35, 3.6), panel, 1.6, alpha)
        p.line(quad(-6.15, 0.95), quad(-6.95, 0.95), panel, 1.6, alpha)
        c0, r0 = quad(-6.9, 3.25)
        c1, r1 = quad(-5.5, 3.55)
        p.fill_rect(c0, r0, c1, r1, L["stripe"], 0.95)
        # national insignia on the rear fuselage
        c, r = quad(-2.9, 0.5)
        p.roundel(c, r, 0.17 / (Z1 - Z0) * Q)
        # rescue arrow (red) near the cockpit
        c, r = quad(4.95, 0.55)
        p.polygon([(c, r + 10), (c - 9, r - 6), (c + 9, r - 6)], (0.75, 0.12, 0.08), 0.95)
        # exhaust soot
        for k in range(30):
            y = -6.9 + k * 0.03
            c0, r0 = quad(y, -0.5)
            c1, r1 = quad(y + 0.03, 0.7)
            p.fill_rect(c0, r0, c1, r1, (0.18, 0.17, 0.16), 0.02 * (30 - k) / 30 * 3)
    # gun soot (left side only)
    c0, r0 = p.left(3.4, 0.25)
    c1, r1 = p.left(1.2, 0.55)
    p.fill_rect(c0, r0, c1, r1, (0.20, 0.19, 0.18), 0.25)

    # --- wing panel lines (top and bottom), mirrored to both sides
    (wx0, wle0, wte0), (wx1, wle1, wte1) = WING
    for sign in (-1, 1):
        for quad in (p.top, p.bottom):
            def wq(x, y, quad=quad):
                return quad(sign * x, y)

            def le(x):
                return wle0 + (wle1 - wle0) * (x - wx0) / (wx1 - wx0)

            def te(x):
                return wte0 + (wte1 - wte0) * (x - wx0) / (wx1 - wx0)
            # leading edge flap hinge line
            p.line(wq(1.25, le(1.25) - 0.42), wq(4.6, le(4.6) - 0.24), panel, 1.6, alpha)
            # flaperon
            p.line(wq(1.25, te(1.25) + 0.62), wq(3.15, te(3.15) + 0.55), panel, 1.6, alpha)
            p.line(wq(3.15, te(3.15) + 0.55), wq(3.15, te(3.15)), panel, 1.6, alpha)
            # spars and ribs
            for f in (0.35, 0.6):
                p.line(wq(1.3, le(1.3) + (te(1.3) - le(1.3)) * f), wq(4.5, le(4.5) + (te(4.5) - le(4.5)) * f),
                       panel, 1.1, alpha * 0.5)
            for x in (2.0, 2.8, 3.6):
                p.line(wq(x, le(x) - 0.42), wq(x, te(x) + 0.55), (0.85, 0.87, 0.9), 1.0, 0.22, dotted=5)
            # stabilator pivot / spar
            p.line(wq(0.9, -5.6), wq(2.7, -6.55), panel, 1.1, alpha * 0.5)
    # insignia: left wing top, right wing bottom
    c, r = p.top(-3.1, -2.3)
    p.roundel(c, r, 0.38 / (X1 - X0) * Q)
    c, r = p.bottom(3.1, -2.3)
    p.roundel(c, r, 0.38 / (X1 - X0) * Q)
    # air refuelling receptacle (spine)
    c0, r0 = p.top(-0.17, 0.35)
    c1, r1 = p.top(0.17, 0.95)
    p.fill_rect(c0, r0, c1, r1, (0.22, 0.23, 0.24), 0.9)
    for y in (0.95, 1.35, 1.75):
        p.line(p.top(-0.05, y), p.top(0.05, y + 0.25), (0.92, 0.92, 0.9), 2.0, 0.8)

    # cockpit tub grey (the tub faces of the skin all sample this spot)
    c0, r0 = p.top(TUB_UV_SPOT[0] - 0.15, TUB_UV_SPOT[1] - 0.15)
    c1, r1 = p.top(TUB_UV_SPOT[0] + 0.15, TUB_UV_SPOT[1] + 0.15)
    p.fill_rect(c0, r0, c1, r1, (0.15, 0.16, 0.17))

    # weathering: subtle noise + darker panel-to-panel tones
    noise = rng.normal(0.0, 0.012, (TEX // 8, TEX // 8, 1)).astype(np.float32)
    noise = np.kron(noise, np.ones((8, 8, 1), np.float32))
    img *= 1.0 + noise
    fine = rng.normal(0.0, 0.01, (TEX, TEX, 1)).astype(np.float32)
    img *= 1.0 + fine
    np.clip(img, 0.0, 1.0, out=img)

    # numpy -> PNMImage (texture rows are bottom-up, BGR)
    rgb = (img * 255).astype(np.uint8)
    tex = Texture("livery_" + name)
    tex.setup2dTexture(TEX, TEX, Texture.T_unsigned_byte, Texture.F_rgb)
    tex.setRamImage(rgb[:, :, ::-1].tobytes())
    pnm = PNMImage()
    tex.store(pnm)
    _stencil_text(pnm, L)
    tex = Texture("livery_" + name)
    tex.load(pnm)
    tex.setMinfilter(Texture.FT_linear_mipmap_linear)
    tex.setMagfilter(Texture.FT_linear)
    tex.setAnisotropicDegree(4)
    _TEXTURES[name] = tex
    return tex


def _stencil_text(pnm, L):
    """Tail code, serial and NO STEP stencils (PNMImage rows are top-down)."""
    font = None
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"):
        if os.path.exists(path):
            font = Filename.fromOsSpecific(path)
            break
    if font is None:
        return

    def put(text, quad, y, z, height_m, color):
        maker = PNMTextMaker(font, 0)
        if not maker.isValid():
            return
        px = int(height_m / (Z1 - Z0) * Q)
        maker.setPixelSize(max(px, 6))
        maker.setFg(Vec4(color[0], color[1], color[2], 1.0))
        maker.setAlign(PNMTextMaker.ACenter)
        c, r = quad(y, z)
        maker.generateInto(text, pnm, int(c), int(TEX - r))
    dark = (0.24, 0.25, 0.27)
    for quad in (_Painter.right, _Painter.left):
        put(L["code"], quad, -5.55, 2.05, 0.55, dark)
        put(L["serial"], quad, -5.45, 1.55, 0.13, dark)


# ---------------------------------------------------------------- assembly
def _material(shininess, spec):
    m = Material("paint")
    m.setShininess(shininess)
    m.setSpecular(Vec4(spec, spec, spec, 1.0))
    m.setDiffuse(Vec4(1, 1, 1, 1))
    m.setAmbient(Vec4(1, 1, 1, 1))
    return m


_GEOMETRY = {}

PART_NAMES = ("lef", "flap", "stab", "sb_up", "sb_lo")


def build_f16_detailed(livery="viper"):
    if "geom" not in _GEOMETRY:
        _GEOMETRY["geom"] = build_detailed_f16()
    g = _GEOMETRY["geom"]
    root = NodePath("f16_" + livery)
    tex = livery_texture(livery)
    paint = _material(30.0, 0.22)
    skin = g["skin"].copyTo(root)
    skin.setTexture(tex)
    skin.setMaterial(paint)
    g["plain"].copyTo(root).setMaterial(_material(20.0, 0.15))
    lights = g["lights"].copyTo(root)
    lights.setLightOff(1)
    glass = g["glass"].copyTo(root)
    glass.setMaterial(_material(90.0, 0.9))
    glass.setTransparency(TransparencyAttrib.MAlpha)
    glass.setDepthWrite(False)
    glass.setBin("transparent", 5)
    glass.setTwoSided(False)               # invisible from inside: the view out of the cockpit stays clear
    stage = TextureStage("reflection")
    stage.setMode(TextureStage.MAdd)
    glass.setTexture(stage, reflection_texture())
    glass.setTexGen(stage, TexGenAttrib.MEyeSphereMap)
    from .cockpit import cockpit_texture
    ctex = cockpit_texture()
    cockpit = g["cockpit"].copyTo(root)
    cockpit.setMaterial(_material(10.0, 0.08))
    screens = g["screens"].copyTo(root)
    screens.setLightOff(1)
    if ctex is not None:
        cockpit.setTexture(ctex)
        screens.setTexture(ctex)
    for part in g["parts"]:
        pivot = root.attachNewNode("part_" + part["name"])
        pivot.setPos(part["pos"])
        pivot.setQuat(part["quat"])
        pivot.setTag("part", part["name"])
        pivot.setTag("sign", "%.1f" % part["sign"])
        surf = part["node"].copyTo(pivot)
        surf.setTexture(tex)
        surf.setMaterial(paint)
    return root


_REFLECTION = {}


def reflection_texture():
    """Sphere map of sky (top), horizon glare and ground (bottom) for the canopy."""
    if "tex" in _REFLECTION:
        return _REFLECTION["tex"]
    n = 256
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u = (xx / (n - 1)) * 2 - 1
    v = (yy / (n - 1)) * 2 - 1              # rows bottom -> top in texture memory
    r = np.sqrt(u * u + v * v)
    sky = np.stack([0.30 + 0.25 * v, 0.38 + 0.25 * v, 0.50 + 0.25 * v], -1)
    ground = np.stack([np.full_like(v, 0.10), np.full_like(v, 0.11), np.full_like(v, 0.08)], -1)
    col = np.where((v > -0.05)[..., None], sky, ground)
    horizon = np.exp(-((v + 0.05) / 0.08) ** 2)[..., None] * 0.35
    sun = np.exp(-(((u - 0.35) ** 2 + (v - 0.45) ** 2) / 0.006))[..., None] * 0.9
    col = np.clip(col + horizon + sun, 0, 1) * (r <= 1.0)[..., None]
    rgb = (col * 255).astype(np.uint8)
    tex = Texture("canopy_reflection")
    tex.setup2dTexture(n, n, Texture.T_unsigned_byte, Texture.F_rgb)
    tex.setRamImage(rgb[:, :, ::-1].tobytes())
    _REFLECTION["tex"] = tex
    return tex


class ControlSurfaces:
    """Moves the flight controls of one detailed F-16 model like the FLCS would.

    Angles in degrees (positive = trailing edge down / leading edge down /
    rudder trailing edge right / speed brake open); actuators are rate limited.
    """

    RATE = 60.0      # deg/s actuator speed

    def __init__(self, model_root):
        self.parts = {}
        for pivot in model_root.findAllMatches("**/=part"):
            surf = pivot.find("surf")
            self.parts[pivot.getTag("part")] = [surf, float(pivot.getTag("sign")), 0.0]

    def _move(self, name, target, dt):
        part = self.parts.get(name)
        if part is None:
            return
        surf, sign, angle = part
        step = self.RATE * dt
        angle += max(-step, min(step, target - angle))
        part[2] = angle
        surf.setP(angle * sign)

    def update(self, dt, pitch, roll, yaw, alpha_deg, flaps, speedbrake, on_ground=False):
        stab = -pitch * 16.0
        self._move("stab_R", stab - roll * 5.0, dt)
        self._move("stab_L", stab + roll * 5.0, dt)
        self._move("flap_R", flaps * 20.0 - roll * 18.0, dt)
        self._move("flap_L", flaps * 20.0 + roll * 18.0, dt)
        lef = 0.0 if on_ground else max(-2.0, min(25.0, alpha_deg * 1.4 - 2.0))
        self._move("lef_R", lef, dt)
        self._move("lef_L", lef, dt)
        self._move("rudder", yaw * 25.0, dt)
        brake = speedbrake * 60.0
        for name in ("sb_up_R", "sb_up_L", "sb_lo_R", "sb_lo_L"):
            self._move(name, brake, dt)
