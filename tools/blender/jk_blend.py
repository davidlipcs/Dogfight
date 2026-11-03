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
    w, y0, y1 = c["width"], c["seat_y"] - 0.55, c["panel_y"] + 0.15
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
def gear_leg(name, hinge, axle, r, w, twin, retract_axis, retract_deg, ground_z, x_side=0.0):
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
