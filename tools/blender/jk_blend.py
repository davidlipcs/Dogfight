"""Jet kit, the Blender side: turns a jet's pieces (<jet>_mesh.airframe()) into the game's objects, adds the
cockpit, the landing gear, the lights, the weapon stations and the reference points, paints it (3D painting: every
texel of the atlas knows its point on the aircraft, so camouflage, insignia and panel lines are drawn on the
aircraft itself, seamless across the UV islands) and exports the .glb.

The game's contract (web/js/render.js, tools/make_roblox_models.py, tools/gen_jetinfo_lua.mjs):
  objects: fuselage, canopy, cockpit, hud_glass, screen_ddi_l / screen_ddi_r / screen_ampcd / screen_ufcd, nozzle,
           moving surfaces (lef_*, flap_*, ail_*, stab_*, rudder_*: hinged, turning about their local X),
           gear_* legs (extras.retract) and door_* (extras.door), light_nav_L / _R, light_tail
  empties: ref_eye, ref_panel, ref_gear_nose, ref_gear_main_L / _R (wheel contact), ref_nozzle_L / _R (exit
           centres), ref_nav_L / _R, ref_tail, ref_strobe_L / _R, ref_vapor_L / _R, ref_wingtip_L / _R, ref_gun,
           store_1 .. store_8 (left outer .. right outer, as specs.js std())
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import aircraft_lib as L
from aircraft_lib import (C_BLACK, C_DARK, C_GREY, C_LIGHT, C_STEEL, C_WHITE, Part, box, build_object, empty,
                          prism, rotate_about, tube, unit, wheel)

C_DUCT = (0.06, 0.06, 0.065)
C_NOZZLE = (0.42, 0.40, 0.37)
C_COCKPIT = (0.17, 0.18, 0.19)
C_COCKPIT_RU = (0.27, 0.42, 0.44)          # the turquoise of Russian cockpits


def no_uv(pos, nrm, mode, **_):
    return np.zeros((len(pos), 2))


def begin(name, out_dir):
    tex = os.path.join(out_dir, "textures")
    os.makedirs(tex, exist_ok=True)
    root = L.begin(name, tex, no_uv, name.upper(), glass=(0.40, 0.36, 0.18), glass_alpha=0.30)
    return root, tex


def part_of(piece, color=None):
    mat = {"paint": "paint", "glass": "glass", "dark": "matte", "metal": "metal"}[piece.mat]
    col = color or {"dark": C_DUCT, "metal": C_NOZZLE}.get(piece.mat, (1.0, 1.0, 1.0))
    p = Part(mat, "auto" if mat == "paint" else None, color=col)
    p.add(piece.verts, piece.faces)
    return p


def obj(name, pieces, hinge=None, colors=None):
    parts = [part_of(p, (colors or {}).get(i)) for i, p in enumerate(pieces)]
    frame = None
    if hinge is not None:
        frame = (np.asarray(hinge[0], float), unit(hinge[1]))
    return build_object(name, parts, frame=frame)


# ------------------------------------------------------------------ cockpit
def cockpit(c):
    """A fighter cockpit under the canopy.  c: seat_y (seat back foot), floor_z, sill_z, panel_y, panel_z,
    width (half), russian (colour), canopy_z(y, x) -> glass height (everything is kept 6 cm under it)."""
    room = Part("matte", None, color=C_COCKPIT_RU if c.get("russian") else C_COCKPIT)
    dark = Part("matte", None, color=C_DARK)
    w, y0, y1 = c["width"], min([c["seat_y"]] + list(c.get("rear_seats", ()))) - 0.55, c["panel_y"] + 0.15
    fz, sz = c["floor_z"], c["sill_z"]
    # tub: floor, side walls (consoles), rear bulkhead
    box(room, (0, 0.5 * (y0 + y1), fz), (w, 0.5 * (y1 - y0), 0.02))
    for s in (-1, 1):
        box(room, (s * (w - 0.03), 0.5 * (y0 + y1), 0.5 * (fz + sz)), (0.03, 0.5 * (y1 - y0), 0.5 * (sz - fz)))
        box(dark, (s * (w - 0.12), c["seat_y"] + 0.25, sz - 0.12), (0.09, 0.35, 0.02))           # side consoles
    box(room, (0, y0, 0.5 * (fz + sz + 0.1)), (w, 0.02, 0.5 * (sz + 0.1 - fz)))
    # instrument panel and glare shield
    pz, py = c["panel_z"], c["panel_y"]
    panel = Part("matte", None, color=(0.13, 0.14, 0.15))
    box(panel, (0, py, pz - 0.10), (w - 0.04, 0.03, 0.22))                           # the panel face
    box(dark, (0, py + 0.02, pz + 0.135), (w - 0.06, 0.10, 0.02))                    # glare shield over it
    # ejection seat (K-36 like: big head box, yellow-black handle)
    sy = c["seat_y"]
    seat = Part("matte", None, color=(0.20, 0.21, 0.22))
    box(seat, (0, sy + 0.18, fz + 0.30), (0.24, 0.24, 0.06))                       # pan
    tilt = np.array([[1, 0, 0], [0, math.cos(0.30), -math.sin(0.30)], [0, math.sin(0.30), math.cos(0.30)]])
    box(seat, (0, sy - 0.02, fz + 0.70), (0.25, 0.06, 0.40), rot=tilt)             # back
    box(seat, (0, sy - 0.14, fz + 1.13), (0.17, 0.09, 0.15), rot=tilt)             # head box
    box(Part("matte", None), (0, sy + 0.05, fz + 0.42), (0.20, 0.03, 0.03))
    handle = Part("matte", None, color=(0.85, 0.70, 0.10))
    box(handle, (0, sy + 0.40, fz + 0.36), (0.06, 0.02, 0.025))
    stick = Part("matte", None, color=C_BLACK)
    tube(stick, [(0, sy + 0.55, fz + 0.05), (0, sy + 0.62, fz + 0.50)], [0.02, 0.016], 8, C_BLACK)
    box(stick, (0, sy + 0.63, fz + 0.55), (0.025, 0.03, 0.05))
    for sy2 in c.get("rear_seats", ()):                  # the back seats of a two seater: seat, its panel, its stick
        box(seat, (0, sy2 + 0.18, fz + 0.36), (0.24, 0.24, 0.06))
        box(seat, (0, sy2 - 0.02, fz + 0.76), (0.25, 0.06, 0.40), rot=tilt)
        box(seat, (0, sy2 - 0.14, fz + 1.19), (0.17, 0.09, 0.15), rot=tilt)
        box(panel, (0, sy2 + 1.02, fz + 0.62), (w - 0.06, 0.03, 0.17))
        box(dark, (0, sy2 + 1.02, fz + 0.62), (0.18, 0.035, 0.12))
        tube(stick, [(0, sy2 + 0.55, fz + 0.05), (0, sy2 + 0.62, fz + 0.50)], [0.02, 0.016], 8, C_BLACK)
    parts = [room, dark, panel, seat, handle, stick]
    # keep it all under the glass
    for p in parts:
        for i, v in enumerate(p.verts):
            lim = np.array([c["canopy_z"](yy, xx) - 0.06 for xx, yy, _z in v])
            v[:, 2] = np.minimum(v[:, 2], lim)
            p.verts[i] = v
            p.uvverts[i] = v
    build_object("cockpit", parts)
    # screens (the game draws its pages on them): two DDIs, the AMPCD under them, the up front display
    sw = min(0.115, (w - 0.08) / 2.6)
    for name, x, z, hw, hh in (("screen_ddi_l", -1.25 * sw, pz, sw, sw), ("screen_ddi_r", 1.25 * sw, pz, sw, sw),
                               ("screen_ampcd", 0.0, pz - 0.20, 0.75 * sw, 0.6 * sw),
                               ("screen_ufcd", 0.0, pz + 0.09, 0.55 * sw, 0.35 * sw)):
        sp = Part("screen", None)
        box(sp, (x, py - 0.034, z - 0.06), (hw, 0.004, hh))
        build_object(name, [sp])
    hud = Part("hud", None)
    hz = pz + 0.16
    prism(hud, (0, py + 0.02, hz), (1, 0, 0), (0, -0.35, 1), [(-0.07, 0), (0.07, 0), (0.07, 0.15), (-0.07, 0.15)], 0.006)
    build_object("hud_glass", [hud])
    empty("ref_eye", (0.0, sy + 0.05, fz + 1.02))
    empty("ref_panel", (0.0, py, pz))


# ------------------------------------------------------------------ landing gear
def gear_leg(name, hinge, axle, r, w, twin, retract_axis, retract_deg, ground_z, x_side=0.0, tandem=0.0):
    """A leg from its hinge (in the bay) to the axle; wheels; retracts about ``retract_axis`` by ``retract_deg``."""
    hinge, axle = np.asarray(hinge, float), np.asarray(axle, float)
    strut = Part("metal", None, color=C_STEEL)
    paint = Part("matte", None, color=(0.55, 0.58, 0.60))
    tube(paint, [hinge, hinge + 0.55 * (axle - hinge)], 0.075, 12, (0.55, 0.58, 0.60))
    tube(strut, [hinge + 0.50 * (axle - hinge), axle + np.array([0, 0, 0.12])], 0.05, 12, C_STEEL)
    tire, hub = Part("matte", None), Part("matte", None)
    if twin:
        for s in (-1, 1):
            wheel(tire, hub, axle + np.array([s * (0.5 * w + 0.04), 0, 0]), r, w)
        tube(strut, [axle - np.array([0.5 * w + 0.06, 0, 0]), axle + np.array([0.5 * w + 0.06, 0, 0])], 0.035, 8, C_STEEL)
    elif tandem:
        # two wheels one behind the other, staggered either side of the leg (MiG-25 / MiG-31)
        side = 1.0 if x_side >= 0 else -1.0
        for k, dy in ((1, tandem), (-1, -tandem)):
            c = axle + np.array([k * side * (0.5 * w + 0.05), dy, 0.0])
            wheel(tire, hub, c, r, w)
            tube(strut, [axle + np.array([0, dy, 0]), c + np.array([k * side * (0.5 * w + 0.03), 0, 0])], 0.04, 8, C_STEEL)
        tube(strut, [axle + np.array([0, tandem, 0]), axle - np.array([0, tandem, 0])], 0.05, 8, C_STEEL)
    else:
        side = 1.0 if x_side >= 0 else -1.0
        wheel(tire, hub, axle + np.array([side * (0.5 * w + 0.05), 0, 0]), r, w)
        tube(strut, [axle, axle + np.array([side * (w + 0.08), 0, 0])], 0.04, 8, C_STEEL)
    o = build_object(name, [paint, strut, tire, hub], frame=(hinge, unit(retract_axis)))
    o["retract"] = float(retract_deg)
    return o


def gear_door(name, hinge_a, hinge_b, far, closing_deg, thick=0.02):
    """A door drawn open: the hinge line a-b and the far edge point (open); it closes by ``closing_deg`` about the
    hinge axis (a -> b)."""
    a, b, f = (np.asarray(v, float) for v in (hinge_a, hinge_b, far))
    off = f - 0.5 * (a + b)
    quad = np.array([a, b, b + off, a + off])
    p = Part("paint", "auto")
    n = unit(np.cross(b - a, off))
    p.add(np.vstack([quad, quad + n * thick]), [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3),
                                                   (3, 7, 4, 0)])
    o = build_object(name, [p], frame=(a, unit(b - a)))
    o["door"] = float(closing_deg)
    return o


# ------------------------------------------------------------------ small things
def lamp(name, centre, mat, r=0.035):
    p = Part(mat, None)
    c = np.asarray(centre, float)
    tube(p, [c - np.array([0, 0.06, 0]), c + np.array([0, 0.03, 0])], [r * 0.6, r], 10, None)
    return build_object(name, [p])


def pylon(part, x, y_front, y_back, z_top, depth, rail=True):
    """A wing / fuselage pylon (a flat fairing) with a launch rail under it -> the store point."""
    prof = [(y_front, 0.0), (y_front - 0.25, depth), (y_back + 0.30, depth), (y_back, 0.0)]
    prism(part, (x, 0.0, z_top + 0.02), (0, 1, 0), (0, 0, -1), prof, 0.08)
    yc = 0.5 * (y_front + y_back)
    if rail:
        box(part, (x, yc - 0.1, z_top - depth - 0.03), (0.035, 0.95, 0.03))
    return (x, yc - 0.05, z_top - depth - 0.16)


# ------------------------------------------------------------------ painting
def smart_uv(objects, margin=0.006):
    """One shared UV atlas for the painted objects (Blender's Smart UV Project, all of them at once)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


def bake_positions(objects, size):
    """Rasterizes the painted triangles of ``objects`` into the atlas: per texel the point on the aircraft (model
    space, the moving parts at rest), its normal and which object it is on.  -> pos (H, W, 3), nrm, obj id, mask"""
    H = W = size
    pos = np.zeros((H, W, 3), np.float32)
    nrm = np.zeros((H, W, 3), np.float32)
    oid = np.full((H, W), -1, np.int16)
    zbuf = np.zeros((H, W), bool)
    for k, o in enumerate(objects):
        me = o.data
        mw = np.array(o.matrix_world)
        paint_slots = {i for i, m in enumerate(me.materials) if m and m.name.endswith("_paint")}
        uv = np.zeros(len(me.loops) * 2)
        me.uv_layers.active.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        co = np.zeros(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        me.calc_loop_triangles()
        for tri in me.loop_triangles:
            if tri.material_index not in paint_slots:
                continue
            li = list(tri.loops)
            vi = list(tri.vertices)
            u = uv[li]
            P = co[vi]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            ln = np.linalg.norm(n)
            if ln < 1e-12:
                continue
            n /= ln
            px = u[:, 0] * W - 0.5
            py = (1.0 - u[:, 1]) * H - 0.5
            x0, x1 = int(max(0, math.floor(px.min()) - 1)), int(min(W - 1, math.ceil(px.max()) + 1))
            y0, y1 = int(max(0, math.floor(py.min()) - 1)), int(min(H - 1, math.ceil(py.max()) + 1))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
            den = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
            if abs(den) < 1e-12:
                continue
            l0 = ((py[1] - py[2]) * (gx - px[2]) + (px[2] - px[1]) * (gy - py[2])) / den
            l1 = ((py[2] - py[0]) * (gx - px[2]) + (px[0] - px[2]) * (gy - py[2])) / den
            l2 = 1.0 - l0 - l1
            e = -0.6 / max(abs(den), 1.0) ** 0.5            # a hair of overlap: no cracks between triangles
            m = (l0 >= e) & (l1 >= e) & (l2 >= e)
            if not m.any():
                continue
            ys, xs = np.where(m)
            p = l0[m][:, None] * P[0] + l1[m][:, None] * P[1] + l2[m][:, None] * P[2]
            pos[y0 + ys, x0 + xs] = p
            nrm[y0 + ys, x0 + xs] = n
            oid[y0 + ys, x0 + xs] = k
            zbuf[y0 + ys, x0 + xs] = True
    return pos, nrm, oid, zbuf


def dilate(img, mask, steps=24):
    """Spreads the painted texels into the empty margins round the islands (no seams in the mip maps)."""
    img = img.astype(np.float32).copy()
    filled = mask.copy()
    for _ in range(steps):
        acc = np.zeros_like(img)
        cnt = np.zeros(mask.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            f = np.roll(filled, (dy, dx), axis=(0, 1))
            acc += np.roll(img, (dy, dx), axis=(0, 1)) * f[..., None]
            cnt += f
        grow = (~filled) & (cnt > 0)
        if not grow.any():
            break
        img[grow] = acc[grow] / cnt[grow][:, None]
        filled |= grow
    return img


def save_png(arr, path):
    img = bpy.data.images.new(os.path.basename(path), arr.shape[1], arr.shape[0], alpha=True)
    rgba = np.ones((arr.shape[0], arr.shape[1], 4), np.float32)
    rgba[..., :3] = arr[::-1] / 255.0 if arr.dtype == np.uint8 else arr[::-1]
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def paint(objects, painter, tex, prefix, size=2048):
    """UV atlas, 3D bake, ``painter(pos, nrm, oid, names) -> (rgb 0..1 sRGB, roughness, metallic)`` arrays,
    the textures, and the paint material refreshed with them."""
    smart_uv(objects)
    pos, nrm, oid, mask = bake_positions(objects, size)
    names = [o.name for o in objects]
    rgb, rough, metal = painter(pos, nrm, oid, names, mask)
    rgb = dilate(np.clip(rgb, 0, 1), mask)
    orm = np.stack([np.ones_like(rough), rough, metal], axis=-1)
    orm = dilate(np.clip(orm, 0, 1), mask)
    save_png((rgb * 255 + 0.5).astype(np.uint8), os.path.join(tex, prefix + "_basecolor.png"))
    save_png((orm * 255 + 0.5).astype(np.uint8), os.path.join(tex, prefix + "_orm.png"))
    flat = np.zeros((256, 256, 3), np.uint8)
    flat[...] = (128, 128, 255)
    save_png(flat, os.path.join(tex, prefix + "_normal.png"))
    # rebuild the paint material with the new textures (the old one renamed first: L.material() deletes a
    # material of the same name, which would empty the slots)
    old = L.CTX["mats"].pop("paint", None)
    if old is not None:
        old.name = prefix + "_paint_untextured"
    new = L.material("paint")
    L.CTX["mats"]["paint"] = new
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for i, m in enumerate(o.data.materials):
            if m is not None and m == old:
                o.data.materials[i] = new
    if old is not None and old.users == 0:
        bpy.data.materials.remove(old)
    return pos, mask


# ------------------------------------------------------------------ export
def finish(out_dir, web_dir, prefix):
    for o in L.CTX["collection"].objects:
        o["part"] = 1
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in L.CTX["collection"].objects if o.type == "MESH")
    print("objects: %d, triangles: %d" % (len(L.CTX["collection"].objects), tris))
    L.export(out_dir, web_dir, {prefix + "_basecolor.png": 2048, prefix + "_normal.png": 256, prefix + "_orm.png": 1024})


# ================================================================== a whole jet, from its shape module
def canopy_z_fn(S):
    """Height of the glass at (x, y) (the cockpit is kept under it); the top of the skin elsewhere."""
    def canopy_z(y, x):
        if S.Y_CAN1 < y < S.Y_WS0:
            h = S.canopy_half(y)
            if abs(x) <= h[-1, 0]:
                return float(np.interp(abs(x), h[::-1, 0], h[::-1, 1]))
        return float(S.SPINE(y))
    return canopy_z


def canopy_frame(S, arches=None):
    """The canopy frame: the windscreen arch, the hood's rear bow, the sill rails (painted like the jet)."""
    p = Part("paint", "auto")
    for y, r in (arches or getattr(S, "CANOPY_ARCHES", None) or ((S.Y_WS1, 0.028), (S.Y_CAN1 + 0.05, 0.035))):
        h = S.canopy_half(y)
        pts = [(-hx, y, hz + 0.004) for hx, hz in h[::-1]] + [(hx, y, hz + 0.004) for hx, hz in h[1:]]
        tube(p, pts, r, 8, caps=True)
    for s in (-1, 1):
        ys = np.linspace(S.Y_WS0 - 0.02, S.Y_CAN1 + 0.02, 14)
        pts = [(s * float(S.CANOPY_SILL_X(y)), y, float(S.CANOPY_SILL_Z(y)) + 0.01) for y in ys]
        tube(p, pts, 0.022, 6, caps=True)
    return build_object("canopy_frame", [p])


def pitot(part, y0, y1, z, r=0.035, vanes=True):
    tube(part, [(0, y0, z), (0, y0 + 0.35 * (y1 - y0), z), (0, y1, z)], [r, r * 0.63, r * 0.34], 10)
    if vanes:
        for k in range(4):
            a = math.radians(45 + 90 * k)
            prism(part, (0, y0 + 0.55 * (y1 - y0), z), (0, 1, 0), (math.cos(a), 0, math.sin(a)),
                  [(0.0, 0.015), (-0.10, 0.015), (-0.10, 0.07), (-0.04, 0.07)], 0.004)


def ball(part, c, r=0.13, n=6, seg=16):
    """A half sphere (an IRST window) standing on c."""
    c = np.asarray(c, float)
    for i in range(n):
        a0, a1 = 0.5 * math.pi * i / n, 0.5 * math.pi * (i + 1) / n
        rings = []
        for a in (a0, a1):
            rr, zz = r * math.cos(a), r * math.sin(a)
            rings.append([c + np.array([rr * math.cos(t), rr * math.sin(t), zz]) for t in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
        part.grid(rings, close=True)


def wing_stores(S, stations, fus=None, depth=0.30):
    """Pylons with launch rails under the wing at the given (station number on the right, x) and a fuselage
    station (x, y, z of the rail); store_N empties on both sides (left = 9 - N)."""
    part = Part("paint", "auto")
    pts = {}
    for stn, x in stations:
        le, te = float(S.wing_le(x)), float(S.wing_te(x))
        c = le - te
        zl = float(S.wing_z(x)) - float(S.WING.t(x)) * c * 0.55
        pts[stn] = pylon(part, x, le - 0.35 * c + 0.95, le - 0.35 * c - 1.15, zl, depth)
    if fus is not None:
        fx, fy, fz = fus
        box(part, (fx, fy, fz - 0.04), (0.04, 0.80, 0.04))
        pts[5] = (fx, fy - 0.05, fz - 0.20)
    build_object("pylons", [part])
    for stn, p in pts.items():
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))
    return pts


def landing_gear(S, nose_hinge_dy=0.30, nose_retract=((-1.0, 0.0, 0.0), 95.0), main_hinge=None,
                 main_retract=((1.0, 0.0, 0.0), 92.0), nose_doors=None, main_doors=None, mudguard=True):
    """Nose leg (in the bay, folding by nose_retract), two main legs (hinge (x, y, z) on the right side),
    their doors: [(hinge a, hinge b, far edge, closing degrees)] for the right side (mirrored for the left)."""
    zg = S.Z_GROUND
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    empty("gear", (0.0, 0.0, 0.0))
    hinge = (0.0, gn["y"] + nose_hinge_dy, float(S.KEEL(gn["y"])) + 0.05)
    axle = (0.0, gn["y"], zg + gn["r"])
    gear_leg("gear_nose", hinge, axle, gn["r"], gn["w"], gn.get("twin", True), nose_retract[0], nose_retract[1], zg)
    if mudguard:
        guard = Part("matte", None, color=(0.55, 0.58, 0.60))
        box(guard, (0.0, gn["y"], zg + 2 * gn["r"] + 0.05), (0.26 if gn.get("twin", True) else 0.15, 0.20, 0.015))
        g = build_object("gear_nose_guard", [guard], frame=(np.array(hinge), unit(nose_retract[0])))
        g["retract"] = float(nose_retract[1])
    for k, (a, b, f, deg) in enumerate(nose_doors or []):
        for s, sfx in ((1, "R"), (-1, "L")):
            m = np.array([s, 1.0, 1.0])
            gear_door("door_nose_%s%s" % (sfx, "" if k == 0 else str(k + 1)), np.array(a) * m, np.array(b) * m,
                      np.array(f) * m, deg * -s)
    for s, sfx in ((1, "R"), (-1, "L")):
        m = np.array([s, 1.0, 1.0])
        h = np.array(main_hinge or (gm["x"] - 0.05, gm["y"] - 0.20, -0.18)) * m
        axle = (s * gm["x"], gm["y"], zg + gm["r"])
        gear_leg("gear_main_" + sfx, h, axle, gm["r"], gm["w"], gm.get("twin", False), main_retract[0],
                 main_retract[1], zg, x_side=s, tandem=gm.get("tandem", 0.0))
        for k, (a, b, f, deg) in enumerate(main_doors or []):
            gear_door("door_main_%s%s" % (sfx, "" if k == 0 else str(k + 1)), np.array(a) * m, np.array(b) * m,
                      np.array(f) * m, deg * -s)
    empty("ref_gear_nose", (0.0, gn["y"], zg))
    for s, sfx in ((1, "R"), (-1, "L")):
        empty("ref_gear_main_" + sfx, (s * gm["x"], gm["y"], zg))


def lights_and_refs(S, tail_light, vapor, gun, strobe_y=None, nozzles=None):
    xt = S.TIP_POD["x"] + S.TIP_POD["r"] if getattr(S, "TIP_POD", None) else S.X_WTIP
    zt = float(S.wing_z(S.X_WTIP))
    yl = float(S.wing_le(S.X_WTIP - 0.1)) - 0.45
    lamp("light_nav_L", (-xt + 0.02, yl, zt), "light_red")
    lamp("light_nav_R", (xt - 0.02, yl, zt), "light_green")
    lamp("light_tail", tail_light, "light_white", r=0.03)
    tipz = S.FIN_Z + S.FIN[-1][0] * math.cos(math.radians(S.FIN_CANT))
    tipx = S.FIN_X + S.FIN[-1][0] * math.sin(math.radians(S.FIN_CANT))
    sy = strobe_y if strobe_y is not None else S.FIN[-1][1] - 0.15
    for s, sfx in ((1, "R"), (-1, "L")):
        empty("ref_nav_" + sfx, (s * (xt - 0.02), yl, zt))
        empty("ref_wingtip_" + sfx, (s * xt, float(S.wing_te(S.X_WTIP)) + 0.4, zt))
        empty("ref_strobe_" + sfx, (s * tipx if tipx > 0.01 else s * 0.02, sy, tipz + 0.02))
        empty("ref_vapor_" + sfx, (s * vapor[0], vapor[1], vapor[2]))
    n = S.NOZZLE
    if abs(n["x"]) < 1e-6:
        empty("ref_nozzle", (0.0, n["y1"], n["z"]))
    else:
        for s, sfx in ((1, "R"), (-1, "L")):
            empty("ref_nozzle_" + sfx, (s * n["x"], n["y1"], n["z"]))
    empty("ref_tail", tail_light)
    empty("ref_gun", gun)


def build_jet(S, M, painter, name, out_dir, web_dir, details=None, stores=None, gear=None, refs=None, cockpit=None,
              texture=2048):
    """The standard twin engine jet: the airframe pieces as the game's objects, then the details, the stores,
    the gear, the cockpit, the lights and refs (callables), the paint, the export."""
    root, tex = begin(name, out_dir)
    parts = M.airframe()
    painted = []
    hot = []
    for k, pc in parts.items():
        base = k.split("_")[0]
        if base in ("nozzle", "duct"):
            hot.append(pc)
        elif k == "canopy":
            obj("canopy", [pc])
        elif base in ("lef", "flap", "ail", "stab", "rudder"):
            painted.append(obj(k, [pc], hinge=pc.hinge))
        else:
            painted.append(obj(k, [pc]))
    obj("nozzle", hot)
    canopy_frame(S)
    for fn in (details, stores, gear):
        if fn:
            fn()
    c = dict(seat_y=S.Y_CAN1 + 0.75, floor_z=float(S.CANOPY_SILL_Z(0.5 * (S.Y_WS1 + S.Y_CAN1))) - 0.62,
             sill_z=float(S.CANOPY_SILL_Z(0.5 * (S.Y_WS1 + S.Y_CAN1))), panel_y=S.Y_WS1 - 0.10,
             panel_z=float(S.CANOPY_SILL_Z(S.Y_WS1)) + 0.05, width=0.40, russian=False, canopy_z=canopy_z_fn(S))
    c.update(cockpit or {})
    globals()["cockpit"](c)
    if refs:
        refs()
    painted += [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("door_") or o.name in
                                                                         ("canopy_frame", "pylons"))]
    paint(painted, painter, tex, name, size=texture)
    finish(out_dir, web_dir, name)
