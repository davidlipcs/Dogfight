"""Shared tools for the Blender aircraft builders (build_f16.py, build_fa18.py).

Mesh "parts" are bags of polygons with a material and a UV rule; ``build_object`` turns a list of them
into one Blender object (orientation fixed per island, sharp edges by angle, atlas UVs from the model
space position, vertex colours for the detail materials) and can put its origin on a hinge.

Frame: +Y forward, +X right, +Z up, metres (the glTF exporter turns it into +Y up, -Z forward).
``begin()`` sets the context: material prefix, texture folder, the aircraft's UV function, collection.
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

SHARP = math.radians(50.0)
UV_MODES = {"auto": 0, "tb": 1, "fin": 2, "side": 3, None: 4, "fin2": 5}

# detail colours (sRGB)
C_WHITE = (0.80, 0.81, 0.82)
C_LIGHT = (0.56, 0.58, 0.60)
C_GREY = (0.36, 0.38, 0.40)
C_DARK = (0.17, 0.18, 0.19)
C_BLACK = (0.035, 0.035, 0.04)
C_STEEL = (0.62, 0.63, 0.65)
C_CHROME = (0.85, 0.86, 0.88)
C_COCKPIT = (0.27, 0.29, 0.30)

CTX = {"prefix": None, "tex": None, "uv": None, "collection": None, "root": None, "mats": {}}
AIRCRAFT_COLLECTIONS = ("F16", "FA18", "F22", "F15")


def begin(prefix, tex, uv, collection, **extra):
    """Clears every aircraft collection and starts a new one with an empty root object."""
    clear_scene()
    CTX.update(prefix=prefix, tex=tex, uv=uv, mats={}, **extra)
    col = bpy.data.collections.get(collection) or bpy.data.collections.new(collection)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new(collection, None)
    root.empty_display_size = 1.0
    col.objects.link(root)
    CTX.update(collection=col, root=root)
    return root


def clear_scene():
    for obj in list(bpy.data.objects):
        cols = [c.name for c in obj.users_collection]
        if obj.name in ("Cube", "Light", "Camera") or obj.get("f16") or obj.get("part") or any(c in AIRCRAFT_COLLECTIONS for c in cols):
            bpy.data.objects.remove(obj, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for name in AIRCRAFT_COLLECTIONS:
        col = bpy.data.collections.get(name)
        if col is not None and not col.objects:
            bpy.data.collections.remove(col)


class Part:
    """A bag of polygons that share a material and a UV rule."""

    def __init__(self, mat="paint", uv="auto", flip=False, color=(1.0, 1.0, 1.0)):
        self.mat, self.uv, self.flip, self.color = mat, uv, flip, color
        self.verts, self.uvverts, self.faces, self.cols, self.n = [], [], [], [], 0

    def add(self, verts, faces, color=None, uv_verts=None):
        """``uv_verts``: where the atlas UVs are taken from, if not the vertices themselves."""
        verts = np.asarray(verts, float).reshape(-1, 3)
        col = self.color if color is None else color
        for f in faces:
            self.faces.append(tuple(int(i) + self.n for i in f))
            self.cols.append(col)
        self.verts.append(verts)
        self.uvverts.append(verts if uv_verts is None else np.asarray(uv_verts, float).reshape(-1, 3))
        self.n += len(verts)
        return self

    def drop(self, inside):
        """Removes the faces whose centre is ``inside`` (cut-outs in the skin)."""
        verts = np.concatenate(self.verts)
        kept = [(f, c) for f, c in zip(self.faces, self.cols) if not inside(verts[list(f)].mean(axis=0))]
        self.faces, self.cols = [f for f, _ in kept], [c for _, c in kept]
        return self

    def grid(self, rings, close=False, color=None):
        rings = np.asarray(rings, float)
        nr, nc = rings.shape[:2]
        faces = []
        for i in range(nr - 1):
            for j in range(nc if close else nc - 1):
                a, b = i * nc + j, i * nc + (j + 1) % nc
                faces.append((a, b, b + nc, a + nc))
        return self.add(rings.reshape(-1, 3), faces, color)

    def ngon(self, pts, color=None):
        return self.add(pts, [tuple(range(len(pts)))], color)

    def fan(self, ring, tip, color=None):
        ring = np.asarray(ring, float)
        n = len(ring)
        return self.add(np.vstack([ring, [tip]]), [(j, (j + 1) % n, n) for j in range(n)], color)

    def extend(self, other):
        for v, u in zip(other.verts, other.uvverts):
            self.verts.append(v)
            self.uvverts.append(u)
        for f, c in zip(other.faces, other.cols):
            self.faces.append(tuple(i + self.n for i in f))
            self.cols.append(c)
        self.n += other.n
        return self

    def transformed(self, fn):
        p = Part(self.mat, self.uv, self.flip, self.color)
        p.verts = [fn(v) for v in self.verts]
        p.uvverts = [fn(v) for v in self.uvverts]
        p.faces, p.cols, p.n = list(self.faces), list(self.cols), self.n
        return p

    def mirrored(self):
        return self.transformed(lambda v: v * np.array([-1.0, 1.0, 1.0]))

    def cleaned(self):
        """Merged duplicate vertices, without degenerate or doubled faces."""
        verts = np.concatenate(self.verts) if self.verts else np.zeros((0, 3))
        uvverts = np.concatenate(self.uvverts) if self.uvverts else np.zeros((0, 3))
        key = np.round(verts / 2e-5).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        inv = inv.ravel()
        faces, cols, seen = [], [], set()
        for f, c in zip(self.faces, self.cols):
            g = []
            for i in f:
                j = int(inv[i])
                if not g or g[-1] != j:
                    g.append(j)
            if len(g) > 1 and g[0] == g[-1]:
                g.pop()
            k = tuple(sorted(g))
            if len(g) >= 3 and len(set(g)) == len(g) and k not in seen:
                seen.add(k)
                faces.append(tuple(g))
                cols.append(c)
        return verts[first], faces, cols, uvverts[first]


def viewport_like_game(target=(0.0, 0.0, 0.0), distance=24.0):
    """Saved .blend files open the way the game shows the jet: every 3D view in Material Preview (textures and
    colours), aimed at the aircraft from the front left, with the helper empties hidden."""
    from mathutils import Euler, Vector
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.shading.type = "MATERIAL"
                space.overlay.show_extras = False
                space.overlay.show_relationship_lines = False
                r3 = space.region_3d
                r3.view_perspective = "PERSP"
                r3.view_location = Vector(target)
                r3.view_rotation = Euler((math.radians(68.0), 0.0, math.radians(140.0))).to_quaternion()
                r3.view_distance = distance


def fit_under_canopy(parts, shape, margin=0.07):
    """Moves the parts (the ejection seat) straight down until every point is at least ``margin`` under the
    canopy glass (or under the skin where there is no glass), so the head box never sticks out of the canopy
    whatever the seat's tilt or size.  ``shape`` is the aircraft's shape module.  -> the drop in metres."""
    def limit(x, y):
        if shape.CANOPY_Y0 < y < shape.CANOPY_Y1 and abs(x) < float(shape.CANOPY_W(y)):
            return shape.canopy_z(y, x)
        return float(shape.body_top(y, abs(x))[0])
    drop = 0.0
    for p in parts:
        for v in p.verts:
            for x, y, z in v:
                drop = max(drop, z - (limit(x, y) - margin))
    if drop > 0.0:
        d = np.array([0.0, 0.0, drop])
        for p in parts:
            p.verts = [v - d for v in p.verts]
            p.uvverts = [v - d for v in p.uvverts]
    return drop


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def tube(part, pts, radii, seg=12, color=None, caps=True, squash=1.0):
    """Circular sweep along a polyline (also used as a lathe along a straight axis)."""
    pts = np.asarray(pts, float)
    radii = np.broadcast_to(np.asarray(radii, float), (len(pts),))
    steps = [q - pts[0] for q in (pts[-1], *pts[1:]) if np.linalg.norm(q - pts[0]) > 1e-9]
    d0 = unit(steps[0])
    ref = np.array([0.0, 0.0, 1.0]) if abs(d0[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = unit(np.cross(d0, ref))
    ang = np.linspace(0.0, 2.0 * math.pi, seg, endpoint=False)
    rings = []
    for i, p in enumerate(pts):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        d = unit(d) if np.linalg.norm(d) > 1e-9 else d0
        u = unit(u - d * u.dot(d))                       # parallel transport: no twist along the path
        v = np.cross(d, u)
        rings.append(p + radii[i] * (np.cos(ang)[:, None] * u + squash * np.sin(ang)[:, None] * v))
    part.grid(rings, close=True, color=color)
    if caps:
        part.ngon(rings[0], color)
        part.ngon(rings[-1], color)
    return rings


def box(part, c, h, rot=None, color=None):
    c, h = np.asarray(c, float), np.asarray(h, float)
    corners = np.array([[sx, sy, sz] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], float) * h
    if rot is not None:
        corners = corners @ np.asarray(rot, float).T
    part.add(corners + c, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)], color)


def rotate_about(pts, origin, axis, angle):
    """Rodrigues rotation of points about the line through ``origin`` along ``axis`` (radians)."""
    p = np.asarray(pts, float) - origin
    k = unit(axis)
    c, s = math.cos(angle), math.sin(angle)
    return p * c + np.cross(k, p) * s + np.outer(p @ k, k) * (1.0 - c) + origin


def rot_x(deg):
    a = math.radians(deg)
    return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])


def rot_y(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


def prism(part, origin, u, v, poly, thick, color=None):
    """A flat plate: the 2D polygon (in the u, v plane through origin) extruded to a thickness."""
    origin, u, v = np.asarray(origin, float), unit(u), unit(v)
    n = unit(np.cross(u, v))
    poly = np.asarray(poly, float)
    mid = origin + poly[:, :1] * u + poly[:, 1:2] * v
    k = len(poly)
    part.add(np.vstack([mid + n * thick * 0.5, mid - n * thick * 0.5]),
             [tuple(range(k)), tuple(range(2 * k - 1, k - 1, -1))]
             + [(j, (j + 1) % k, k + (j + 1) % k, k + j) for j in range(k)], color)


def superellipse(y, cz, hw, hh, n_up, n_lo, seg, x0=0.0):
    """Closed ring in the x-z plane at station y."""
    t = np.linspace(0.0, 2.0 * math.pi, seg, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    n = np.where(s >= 0, n_up, n_lo)
    return np.stack([x0 + hw * np.sign(c) * np.abs(c) ** (2.0 / n), np.full(seg, y),
                     cz + hh * np.sign(s) * np.abs(s) ** (2.0 / n)], axis=1)


# ============================================================== materials


def material(key):
    """Material ``<prefix>_<key>``: paint (textured), matte / metal (vertex colours), glass, screen, lamps."""
    prefix = CTX["prefix"]
    name = "%s_%s" % (prefix, key)
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    if not mat.node_tree or not mat.node_tree.nodes:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(file, colorspace, x, y):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.location = (x, y)
        old = bpy.data.images.get(file)
        if old is not None:
            bpy.data.images.remove(old)
        node.image = bpy.data.images.load(os.path.join(CTX["tex"], file))
        node.image.colorspace_settings.name = colorspace
        return node

    def vertex_colour():
        node = nt.nodes.new("ShaderNodeVertexColor")
        node.layer_name = "Col"
        node.location = (-300, 200)
        nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])

    def setup(metallic, roughness, colour=None, emission=None, alpha=None):
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if colour is not None:
            bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
        if emission is not None:
            bsdf.inputs["Emission Color"].default_value = (*emission[0], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission[1]
        if alpha is not None:
            bsdf.inputs["Alpha"].default_value = alpha
            mat.surface_render_method = "BLENDED"

    if key == "paint":
        setup(0.0, 0.55, (0.45, 0.47, 0.49))
        if os.path.exists(os.path.join(CTX["tex"], prefix + "_basecolor.png")):
            nt.links.new(tex(prefix + "_basecolor.png", "sRGB", -700, 300).outputs["Color"], bsdf.inputs["Base Color"])
            orm = tex(prefix + "_orm.png", "Non-Color", -900, 0)
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            sep.location = (-500, 0)
            nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
            nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
            nrm = nt.nodes.new("ShaderNodeNormalMap")
            nrm.location = (-400, -300)
            nrm.uv_map = "UVMap"
            nt.links.new(tex(prefix + "_normal.png", "Non-Color", -700, -300).outputs["Color"], nrm.inputs["Color"])
            nt.links.new(nrm.outputs["Normal"], bsdf.inputs["Normal"])
    elif key == "matte":
        setup(0.0, 0.62)
        vertex_colour()
    elif key == "metal":
        setup(0.85, 0.38)
        vertex_colour()
    elif key == "glass":
        setup(0.75, 0.05, CTX.get("glass", (0.42, 0.33, 0.14)), alpha=CTX.get("glass_alpha", 0.34))
    elif key == "hud":                                     # HUD combiner: nearly clear, a faint green tint
        setup(0.2, 0.05, (0.55, 0.80, 0.62), alpha=0.10)
    elif key == "screen":
        setup(0.0, 0.4, (0.02, 0.05, 0.03), emission=((0.25, 0.9, 0.4), 1.2))
    elif key == "light_red":
        setup(0.0, 0.3, (0.5, 0.02, 0.02), emission=((1.0, 0.05, 0.03), 4.0))
    elif key == "light_green":
        setup(0.0, 0.3, (0.02, 0.5, 0.15), emission=((0.05, 1.0, 0.35), 4.0))
    elif key == "light_white":
        setup(0.0, 0.3, (0.9, 0.9, 0.85), emission=((1.0, 0.98, 0.9), 4.0))
    elif key == "light_strip":
        setup(0.0, 0.5, (0.50, 0.56, 0.32), emission=((0.6, 0.85, 0.35), 0.35))
    mat.use_backface_culling = True
    return mat


def mat_slot(key):
    mats = CTX["mats"]
    if key not in mats:
        mats[key] = material(key)
    return mats[key]


def build_object(name, parts, frame=None, parent=None):
    """One mesh object from a list of parts.  ``frame`` = (origin, x axis) puts the object's
    origin on a hinge with its local X axis along the hinge line."""
    verts, uvverts, faces, cols, mats, slots, modes, flips = [], [], [], [], [], [], [], []
    off = 0
    for p in parts:
        v, f, c, u = p.cleaned()
        if p.mat not in slots:
            slots.append(p.mat)
        verts.append(v)
        uvverts.append(u)
        faces.extend(tuple(i + off for i in g) for g in f)
        cols.extend(c)
        mats.extend([slots.index(p.mat)] * len(f))
        modes.extend([UV_MODES[p.uv]] * len(f))
        flips.extend([p.flip] * len(f))
        off += len(v)
    verts, uvverts = np.concatenate(verts), np.concatenate(uvverts)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], faces)
    for key in slots:
        me.materials.append(mat_slot(key))
    me.polygons.foreach_set("material_index", mats)
    if me.validate():
        print("WARNING: mesh %s was not valid" % name)

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    seen = set()
    for first in bm.faces:                               # orient every island outwards (or inwards: flip)
        if first.index in seen:
            continue
        seen.add(first.index)
        stack, island = [first], []
        while stack:
            f = stack.pop()
            island.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        areas = [f.calc_area() for f in island]
        centres = [f.calc_center_median() for f in island]
        mid = sum((c * a for c, a in zip(centres, areas)), Vector()) / max(sum(areas), 1e-12)
        out = sum(a * f.normal.dot(c - mid) for f, c, a in zip(island, centres, areas))
        if abs(out) < 1e-9:                              # a flat patch: away from the plane of symmetry, or forwards
            n = island[0].normal
            out = n.x * mid.x if abs(n.x) > 0.5 else n.y
        if (out > 0.0) == flips[first.index]:
            for f in island:
                f.normal_flip()
    for face in bm.faces:
        face.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
            e.smooth = False
    bm.to_mesh(me)
    bm.free()

    npoly, nloop = len(me.polygons), len(me.loops)
    loop_v = np.empty(nloop, np.int32)
    me.loops.foreach_get("vertex_index", loop_v)
    total = np.empty(npoly, np.int32)
    me.polygons.foreach_get("loop_total", total)
    normal = np.empty(npoly * 3)
    me.polygons.foreach_get("normal", normal)
    face_of_loop = np.repeat(np.arange(npoly), total)
    nrm = normal.reshape(-1, 3)[face_of_loop]
    if not np.allclose(uvverts, verts):                  # (doors: the normal where the UVs come from)
        poly_v = [p.vertices[:3] for p in me.polygons]
        a, b, c = (uvverts[[v[k] for v in poly_v]] for k in range(3))
        n2 = np.cross(b - a, c - a)
        n2 /= np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-12)
        nrm = rotate_like(n2, normal.reshape(-1, 3))[face_of_loop]
    uv_fn, extra = CTX["uv"], {}
    if "cent" in uv_fn.__code__.co_varnames[:uv_fn.__code__.co_argcount]:
        cent = np.zeros((npoly, 3))                      # face centres: decals are chosen per face
        np.add.at(cent, face_of_loop, uvverts[loop_v])
        extra["cent"] = (cent / total[:, None])[face_of_loop]
    uv = uv_fn(uvverts[loop_v], nrm, np.asarray(modes)[face_of_loop], **extra)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", uv.ravel())
    if any(k in ("matte", "metal") for k in slots):
        rgba = np.concatenate([np.asarray(cols, float)[face_of_loop], np.ones((nloop, 1))], axis=1)
        me.color_attributes.new("Col", "BYTE_COLOR", "CORNER").data.foreach_set("color_srgb", rgba.ravel())

    obj = bpy.data.objects.new(name, me)
    CTX["collection"].objects.link(obj)
    obj.parent = parent or CTX["root"]
    obj["part"] = 1
    if frame is not None:
        origin, axis = np.asarray(frame[0], float), unit(frame[1])
        ref = np.array([0.0, 1.0, 0.0]) if abs(axis[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
        yv = unit(ref - axis * ref.dot(axis))
        zv = np.cross(axis, yv)
        m = Matrix.Identity(4)
        for r in range(3):
            m[r][0], m[r][1], m[r][2], m[r][3] = axis[r], yv[r], zv[r], origin[r]
        me.transform(m.inverted())
        obj.matrix_local = m
    return obj


def empty(name, loc, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.2
    obj.location = loc
    obj.parent = parent or CTX["root"]
    CTX["collection"].objects.link(obj)
    obj["part"] = 1
    return obj


def airfoil_patch(part, span, pos, a_fn=None, b_fn=None, nc=14, cap0=False, cap1=False):
    """Skin of a lifting surface between the chord fractions a(span) .. b(span).

    ``pos(sv, s, side)`` gives the points of the upper (side = 1) or lower (-1) surface.  A patch
    that starts at the leading edge wraps around the nose; cut faces close it towards the neighbouring
    control surface."""
    a_fn = a_fn or (lambda sv: 0.0)
    b_fn = b_fn or (lambda sv: 1.0)
    uppers, lowers = [], []
    for sv in span:
        a, b = float(a_fn(sv)), float(b_fn(sv))
        g = np.linspace(0.0, 1.0, nc + 1)
        if a <= 0.0:
            g = 1.0 - np.cos(0.5 * math.pi * g)
        s = a + (b - a) * g
        uppers.append(pos(sv, s, 1.0))
        lowers.append(pos(sv, s, -1.0))
    uppers, lowers = np.array(uppers), np.array(lowers)
    nose = float(a_fn(span[0])) <= 0.0
    tail = float(b_fn(span[0])) >= 1.0
    if nose:
        part.grid(np.concatenate([uppers[:, ::-1], lowers[:, 1:]], axis=1))
    else:
        part.grid(uppers)
        part.grid(lowers)
        part.grid(np.stack([uppers[:, 0], lowers[:, 0]], axis=1))
    if not tail:
        part.grid(np.stack([uppers[:, -1], lowers[:, -1]], axis=1))
    for wanted, i in ((cap0, 0), (cap1, -1)):
        if wanted:
            part.ngon(np.concatenate([uppers[i], lowers[i][::-1]]))
    return part


def wheel(tire, hub, c, r, w, axis=(1.0, 0.0, 0.0)):
    c, axis = np.asarray(c, float), unit(axis)
    t = np.array([-1.0, -1.0, -0.86, -0.5, 0.5, 0.86, 1.0, 1.0]) * 0.5 * w
    rr = np.array([0.60, 0.86, 0.965, 1.0, 1.0, 0.965, 0.86, 0.60]) * r
    tube(tire, c + t[:, None] * axis, rr, 28, C_BLACK, caps=False)
    t = np.array([-0.5, -0.36, -0.30, 0.30, 0.36, 0.5]) * w
    rr = np.array([0.60, 0.60, 0.30, 0.30, 0.60, 0.60]) * r
    tube(hub, c + t[:, None] * axis, rr, 20, C_WHITE)
    tube(hub, c + np.array([-0.56, 0.56])[:, None] * w * axis, 0.16 * r, 10, C_STEEL)


def rotate_like(n_from, n_to):
    """Keeps the direction of n_from but the side (sign) of n_to."""
    return n_from * np.sign(np.sum(n_from * n_to, axis=1, keepdims=True) + 1e-9)


def gear_door(x_hinge, x_far, y0, y1, z_of, thick=0.02):
    """A gear door, modelled closed (flush with the skin; the UVs come from there) and hung open below its
    hinge at rest.  -> (part, hinge point, axis, closing angle in degrees)"""
    zh, zf = z_of(x_hinge) - 0.003, z_of(x_far) - 0.003
    corners = []
    for sz in (0.0, thick):
        for y in (y0, y1):
            for x, z in ((x_hinge, zh), (x_far, zf)):
                corners.append((x, y, z + sz))
    closed = np.array(corners)
    hinge = np.array([x_hinge, 0.0, zh])
    u_c = unit((x_far - x_hinge, 0.0, zf - zh))
    u_o = np.array([0.0, 0.0, -1.0])
    phi = math.atan2(np.cross(u_c, u_o)[1], u_c.dot(u_o))      # closed -> open about +y
    opened = rotate_about(closed, hinge, (0, 1, 0), phi)
    part = Part("paint", "tb")
    part.add(opened, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)], uv_verts=closed)
    axis = (0.0, -1.0, 0.0) if phi >= 0 else (0.0, 1.0, 0.0)  # opening is +phi about +y: closing is the reverse
    return part, hinge, axis, abs(math.degrees(phi))


def gear_well(rect, z_of, top, mirror=1.0, margin=0.04):
    """Dark open box behind a cut-out in the skin."""
    x0, x1, y0, y1 = rect
    x0, x1, y0, y1 = x0 - margin, x1 + margin, y0 - margin, y1 + margin
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    low = [(mirror * x, y, z_of(x, y) - 0.012) for x, y in pts]
    high = [(mirror * x, y, top) for x, y in pts]
    part = Part("matte", None, flip=True, color=(0.20, 0.21, 0.22))
    for k in range(4):
        part.add([low[k], low[(k + 1) % 4], high[(k + 1) % 4], high[k]], [(0, 1, 2, 3)])
    part.ngon(high, (0.12, 0.12, 0.13))
    return part


def retract_rotation(hinge, d0, a0, d1, a1):
    """Single hinge rotation that swings the leg direction d0 to d1 and the axle a0 to (about) a1.
    -> (axis, angle in degrees)"""
    def frame(d, a):
        d = unit(d)
        a = unit(np.asarray(a, float) - d * np.dot(a, d))
        return np.stack([d, a, np.cross(d, a)], axis=1)
    rot = frame(d1, a1) @ frame(d0, a0).T
    axis, angle = Matrix([list(r) for r in rot]).to_quaternion().to_axis_angle()
    return np.array(axis), math.degrees(angle)


def render_previews(folder, names, views):
    scene = bpy.context.scene
    cam = bpy.data.objects.get("preview_cam")
    if cam is None:
        cam = bpy.data.objects.new("preview_cam", bpy.data.cameras.new("preview_cam"))
        scene.collection.objects.link(cam)
    sun = bpy.data.objects.get("preview_sun")
    if sun is None:
        sun = bpy.data.objects.new("preview_sun", bpy.data.lights.new("preview_sun", "SUN"))
        scene.collection.objects.link(sun)
    sun.data.energy = 3.5
    sun.data.angle = math.radians(3.0)
    sun.rotation_euler = (math.radians(48), math.radians(8), math.radians(35))
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if not world.node_tree or not world.node_tree.nodes:
        world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.55, 0.78, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.1
    scene.camera = cam
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.eevee.taa_render_samples = 24
    except Exception:
        pass
    scene.view_settings.view_transform = "Standard"
    os.makedirs(folder, exist_ok=True)
    for name in names:
        loc, target, lens = views[name]
        cam.location = loc
        cam.data.lens = lens
        cam.data.clip_end = 500.0
        d = Vector(target) - Vector(loc)
        cam.rotation_euler = (0.0, 0.0, -0.5 * math.pi) if name == "top" else d.to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(folder, "%s_%s.png" % (CTX["prefix"], name))
        bpy.ops.render.render(write_still=True)


def export(out, web, web_textures):
    """``out``: full resolution; ``web``: the same meshes with smaller textures for the game."""
    os.makedirs(out, exist_ok=True)
    scene = bpy.context.scene
    wanted = dict(export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
                  export_image_format="JPEG", export_jpeg_quality=88, export_image_quality=88, export_tangents=False,
                  export_extras=True, export_cameras=False, export_lights=False, export_animations=False,
                  export_vertex_color="MATERIAL", export_materials="EXPORT")
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()

    def write(path, pick):
        for obj in scene.objects:
            obj.select_set(pick(obj))
        bpy.ops.export_scene.gltf(filepath=path, **{k: v for k, v in wanted.items() if k in props})
        print("exported %s (%.2f MB)" % (path, os.path.getsize(path) / 1e6))
    weapons = [o for o in scene.objects if o.get("part") == 2 and o.name in CTX["collection"].objects]
    for weapon in weapons:
        weapon.location = (0.0, 0.0, 0.0)
    for folder in (out, web):
        nodes, small = [], []
        if folder == web:                                # swap in the smaller textures
            for node in bpy.data.materials[CTX["prefix"] + "_paint"].node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image.name in web_textures:
                    size = web_textures[node.image.name]
                    img = node.image.copy()
                    img.scale(size, size)
                    img.filepath_raw = os.path.join(CTX["tex"], "web_" + node.image.name)
                    img.file_format = "PNG"
                    img.save()
                    nodes.append((node, node.image))
                    small.append(img)
                    node.image = img
        write(os.path.join(folder, CTX["prefix"] + ".glb"), lambda o: o.get("part") == 1 and o.name in CTX["collection"].objects)
        for weapon in weapons:
            write(os.path.join(folder, weapon.name.lower().replace("-", "") + ".glb"), lambda o, w=weapon: o == w)
        for node, image in nodes:
            node.image = image
        for img in small:
            bpy.data.images.remove(img)
    for i, weapon in enumerate(weapons):                 # park them next to the aircraft in the .blend
        weapon.location = (6.5 + 0.6 * i, 2.0, -1.5)
