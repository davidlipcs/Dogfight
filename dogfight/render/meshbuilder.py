"""Tiny procedural mesh builder (vertex + normal + colour) on top of Panda3D Geoms."""

import math

from panda3d.core import (Geom, GeomEnums, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
                          GeomVertexWriter, NodePath, Vec3)


class MeshBuilder:
    def __init__(self):
        self.verts = []        # (pos Vec3, normal Vec3, colour tuple)
        self.tris = []

    # ---------------------------------------------------------- primitives
    def vertex(self, pos, normal, color):
        self.verts.append((Vec3(pos), Vec3(normal), color))
        return len(self.verts) - 1

    def tri(self, a, b, c, color, outward=None):
        """Flat shaded triangle.  ``outward`` (optional) fixes the winding."""
        a, b, c = Vec3(a), Vec3(b), Vec3(c)
        n = (b - a).cross(c - a)
        if n.length() < 1e-12:
            return
        if outward is not None and n.dot(outward) < 0.0:
            b, c = c, b
            n = -n
        n.normalize()
        col = color((a + b + c) / 3.0, n) if callable(color) else color
        i = len(self.verts)
        self.verts.extend(((a, n, col), (b, n, col), (c, n, col)))
        self.tris.append((i, i + 1, i + 2))

    def quad(self, a, b, c, d, color, outward=None):
        self.tri(a, b, c, color, outward)
        self.tri(a, c, d, color, outward)

    def poly(self, points, color, outward=None):
        for k in range(1, len(points) - 1):
            self.tri(points[0], points[k], points[k + 1], color, outward)

    # ---------------------------------------------------------------- loft
    def loft(self, rings, color, smooth=True, cap_front=None, cap_back=None):
        """Skin consecutive rings (lists of Vec3 with equal length, closed or open).

        Winding is chosen so that faces point away from each ring's centre.
        ``cap_front`` / ``cap_back``: colour to close the last / first ring.
        """
        n = len(rings[0])
        centers = [sum(r, Vec3(0, 0, 0)) / len(r) for r in rings]
        if not smooth:
            for i in range(len(rings) - 1):
                r0, r1 = rings[i], rings[i + 1]
                mid = (centers[i] + centers[i + 1]) * 0.5
                for k in range(n - 1):
                    a, b, c, d = r0[k], r0[k + 1], r1[k + 1], r1[k]
                    face_mid = (a + b + c + d) * 0.25
                    self.quad(a, b, c, d, color, outward=face_mid - mid)
        else:
            normals = [[Vec3(0, 0, 0) for _ in range(n)] for _ in rings]
            faces = []
            for i in range(len(rings) - 1):
                r0, r1 = rings[i], rings[i + 1]
                mid = (centers[i] + centers[i + 1]) * 0.5
                for k in range(n - 1):
                    a, b, c, d = r0[k], r0[k + 1], r1[k + 1], r1[k]
                    fn = (b - a).cross(d - a)
                    if fn.length() < 1e-12:
                        fn = (c - b).cross(d - b)
                    face_mid = (a + b + c + d) * 0.25
                    flip = fn.dot(face_mid - mid) < 0.0
                    if flip:
                        fn = -fn
                    if fn.length() > 1e-12:
                        fn.normalize()
                    for (ii, kk) in ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)):
                        normals[ii][kk] += fn
                    faces.append((i, k, flip))
            for i, ring in enumerate(rings):
                if (ring[0] - ring[-1]).length() < 1e-6:      # closed ring: weld the seam normals
                    seam = normals[i][0] + normals[i][n - 1]
                    normals[i][0] = Vec3(seam)
                    normals[i][n - 1] = Vec3(seam)
            index = {}
            for i, ring in enumerate(rings):
                for k, p in enumerate(ring):
                    nrm = normals[i][k]
                    if nrm.length() > 1e-12:
                        nrm.normalize()
                    col = color(p, nrm) if callable(color) else color
                    index[(i, k)] = self.vertex(p, nrm, col)
            for i, k, flip in faces:
                a, b, c, d = index[(i, k)], index[(i, k + 1)], index[(i + 1, k + 1)], index[(i + 1, k)]
                if flip:
                    self.tris.append((a, d, c))
                    self.tris.append((a, c, b))
                else:
                    self.tris.append((a, b, c))
                    self.tris.append((a, c, d))
        if cap_back is not None:
            self._cap(rings[0], centers[0], centers[0] - centers[1], cap_back)
        if cap_front is not None:
            self._cap(rings[-1], centers[-1], centers[-1] - centers[-2], cap_front)

    def _cap(self, ring, center, outward, color):
        for k in range(len(ring) - 1):
            self.tri(center, ring[k], ring[k + 1], color, outward)

    # ------------------------------------------------------- lifting surface
    def surface(self, root_le, root_te, tip_le, tip_te, t_root, t_tip, thick_dir, color, ridge=0.42):
        """A thin wing-like slab with a diamond airfoil (top + bottom + tip cap)."""
        root_le, root_te, tip_le, tip_te = Vec3(root_le), Vec3(root_te), Vec3(tip_le), Vec3(tip_te)
        n = Vec3(thick_dir)
        n.normalize()
        rm = root_le + (root_te - root_le) * ridge
        tm = tip_le + (tip_te - tip_le) * ridge
        for sign in (1.0, -1.0):
            out = n * sign
            rr = rm + n * (sign * t_root * 0.5)
            tr = tm + n * (sign * t_tip * 0.5)
            self.quad(root_le, tip_le, tr, rr, color, outward=out)
            self.quad(rr, tr, tip_te, root_te, color, outward=out)
        span_out = (tip_le + tip_te) * 0.5 - (root_le + root_te) * 0.5
        top = tm + n * (t_tip * 0.5)
        bottom = tm - n * (t_tip * 0.5)
        self.quad(tip_le, top, tip_te, bottom, color, outward=span_out)

    # ---------------------------------------------------------- transforms
    def mirrored_x(self):
        """Copy of this mesh mirrored across the YZ plane (winding fixed)."""
        mb = MeshBuilder()
        for p, nrm, col in self.verts:
            mb.verts.append((Vec3(-p.x, p.y, p.z), Vec3(-nrm.x, nrm.y, nrm.z), col))
        mb.tris = [(a, c, b) for a, b, c in self.tris]
        return mb

    def extend(self, other):
        base = len(self.verts)
        self.verts.extend(other.verts)
        self.tris.extend((a + base, b + base, c + base) for a, b, c in other.tris)

    def build(self, name="mesh"):
        fmt = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData(name, fmt, Geom.UHStatic)
        vdata.setNumRows(len(self.verts))
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        cw = GeomVertexWriter(vdata, "color")
        for p, nrm, col in self.verts:
            vw.addData3(p)
            nw.addData3(nrm)
            cw.addData4(col[0], col[1], col[2], col[3] if len(col) > 3 else 1.0)
        prim = GeomTriangles(Geom.UHStatic)
        if len(self.verts) > 65000:
            prim.setIndexType(GeomEnums.NT_uint32)
        for a, b, c in self.tris:
            prim.addVertices(a, b, c)
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)
        return NodePath(node)


def ellipse_ring(y, half_w, z_center, half_h, segments=16, exponent=2.0, start=0.0, end=2 * math.pi):
    """Ring of points around the Y axis (superellipse when exponent > 2)."""
    pts = []
    e = 2.0 / exponent
    for k in range(segments + 1):
        t = start + (end - start) * k / segments
        c = math.cos(t)
        s = math.sin(t)
        x = half_w * math.copysign(abs(c) ** e, c)
        z = z_center + half_h * math.copysign(abs(s) ** e, s)
        pts.append(Vec3(x, y, z))
    return pts
