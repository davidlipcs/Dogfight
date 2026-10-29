"""Makes the jet models Roblox can import: the .glb files of web/assets with every mesh cut down to at most MAXTRI triangles
(Roblox refuses a mesh of more than 20000), the textures and vertex colours kept.   python3 tools/make_roblox_models.py
Output: roblox/models/<key>.glb  (import them in Studio: View > Asset Manager > Bulk Import, see roblox/README.md)
Needs: pip install trimesh fast-simplification scipy numpy pillow"""
import json
import os
import struct
import sys

import numpy as np
import trimesh
import fast_simplification
from scipy import ndimage
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web", "assets")
OUT = os.path.join(ROOT, "roblox", "models")
MAXTRI = 15000                    # per mesh (Roblox: 20000)
TOTAL = 42000                     # per jet (the jets are seen small; eight of them fly at once)
KEYS = ["f16", "fa18", "f15", "f22", "f35", "gripen", "typhoon", "rafale", "su35", "su57", "mig29", "mig31", "j20", "t38", "t45", "t6"]


# ---- the paint schemes of the real aircraft: the paint texture of a jet keeps its panel lines, numbers and marks, only the camouflage tones
# are replaced (by the colours of the real jet in the photographs the schemes were made from)
#   tones: the colours of the darkest ... lightest camouflage field (more than one only where the real jet has a camouflage);
#   block: the camouflage is made of squares of that many pixels (a digital pattern); marks: the national marks that replace the red stars
LIVERIES = {
    # Hungarian Air Force MiG-29: one light grey all over, the red-white-green triangle
    "mig29": dict(tones=[(148, 156, 164)] * 3, marks="triangle", clip=4),
    # MiG-31: the pale grey of the Russian interceptors, red stars
    "mig31": dict(tones=[(176, 182, 188)] * 3, clip=5),
    # Su-57: blue-grey digital (pixel) camouflage
    "su57": dict(tones=[(48, 60, 84), (98, 116, 138), (150, 164, 180)], block=20, scatter=0.22, clip=5),
    # Su-35S: pale blue-grey with darker patches
    "su35": dict(tones=[(104, 124, 148), (140, 158, 176), (176, 190, 204)]),
    # Eurofighter Typhoon: grey, in two close tones
    "typhoon": dict(tones=[(128, 136, 144)] * 3, clip=5),
    # Gripen of the Hungarian Air Force: blue-grey, the red-white-green triangle instead of the Swedish roundel
    "gripen": dict(tones=[(66, 78, 96), (92, 104, 122), (116, 128, 144)], marks="triangle", markmask="saturated"),
    # Rafale: dark grey, the French roundels stay
    "rafale": dict(tones=[(76, 82, 90), (98, 104, 112), (120, 126, 134)]),
    # F-35A: the light gunmetal grey
    "f35": dict(tones=[(98, 102, 106), (118, 122, 126), (138, 142, 146)]),
    # F/A-18E: navy grey, lighter below
    "fa18": dict(tones=[(112, 122, 134), (150, 158, 168), (176, 184, 192)]),
    # J-20: grey with a blue tint, the red-yellow marks stay
    "j20": dict(tones=[(96, 106, 120), (118, 128, 142), (138, 148, 160)]),
}


def kmeans1(x, k, iters=12):
    c = np.quantile(x, np.linspace(0.1, 0.9, k))
    for _ in range(iters):
        lab = np.abs(x[:, None] - c[None, :]).argmin(1)
        for i in range(k):
            if (lab == i).any():
                c[i] = x[lab == i].mean()
    return c


def draw_triangle(img, cx, cy, r):
    """the Hungarian roundel: a triangle (apex up), red outside, white, green inside"""
    d = ImageDraw.Draw(img)
    def tri(k, col):
        pts = [(cx, cy - k * r), (cx - k * r * 0.95, cy + k * r * 0.62), (cx + k * r * 0.95, cy + k * r * 0.62)]
        d.polygon(pts, fill=col)
    tri(1.0, (200, 30, 40)); tri(0.7, (240, 240, 240)); tri(0.42, (40, 140, 60))


def repaint(img, spec):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    sat = a.max(2) - a.min(2)
    detail = (sat > 52) | (lum < 46) | (lum > 232)                      # stars, digits, the black parts, the white patches: kept
    tones = np.array(spec["tones"], dtype=np.float32)
    k = len(tones)
    paint = ~detail
    cen = np.sort(kmeans1(lum[paint][::7], k))
    lab = np.abs(lum[:, :, None] - cen[None, None, :]).argmin(2)
    block = spec.get("block")
    if block:                                                           # a digital camouflage: the class of the mean of every square
        h, w = lum.shape
        hb, wb = h // block, w // block
        m = lum[:hb * block, :wb * block].reshape(hb, block, wb, block).mean(axis=(1, 3))
        lb = np.abs(m[:, :, None] - cen[None, None, :]).argmin(2)
        if spec.get("scatter"):                                          # the squares of a digital pattern are never tidy
            rng = np.random.default_rng(5)
            flip = rng.random(lb.shape) < spec["scatter"]
            lb = np.clip(lb + rng.integers(-1, 2, lb.shape) * flip, 0, k - 1)
        lab = np.repeat(np.repeat(lb, block, axis=0), block, axis=1)
        full = np.pad(lab, ((0, h - lab.shape[0]), (0, w - lab.shape[1])), mode="edge")
        lab = np.where(paint, full, 0)
    clip = spec.get("clip", 9)
    delta = np.clip(lum - cen[lab], -clip, clip)[:, :, None]                  # the fine detail (panel lines, grain) is carried over (not the old camouflage's edges)
    out = tones[lab] + delta * spec.get("detail", 1.0)
    out = np.where(detail[:, :, None], a, out)
    out = np.clip(out, 0, 255).astype(np.uint8)
    res = Image.fromarray(out)
    if spec.get("marks") == "triangle":
        if spec.get("markmask") == "saturated":
            red = (sat > 60) & (lum > 60)                                  # any coloured roundel
        else:
            red = (a[:, :, 0] > 150) & (a[:, :, 1] < 90) & (a[:, :, 2] < 90)
        red = ndimage.binary_dilation(red, iterations=2)
        lab2, n = ndimage.label(red)
        for i, sl in enumerate(ndimage.find_objects(lab2)):
            ys, xs = sl
            h, w = ys.stop - ys.start, xs.stop - xs.start
            if 20 <= h <= 400 and 20 <= w <= 400:
                # paint the paint colour over the star first, then the triangle
                mask = (lab2[sl] == i + 1)
                patch = np.asarray(res)[sl].copy()
                patch[mask] = tones[0] if len(set(map(tuple, spec["tones"]))) == 1 else tones[1]
                res.paste(Image.fromarray(patch), (xs.start, ys.start))
                draw_triangle(res, (xs.start + xs.stop) / 2, (ys.start + ys.stop) / 2, max(h, w) * 0.62)
    return res


def glb_colors(path):
    """The COLOR_0 vertex colours of every primitive of a .glb, by the name trimesh gives the geometry (the mesh's name, then name_1, name_2 ...):
    {name: float array (n, 4)}.  trimesh drops them when a mesh has texture coordinates, but they carry the grey / dark paint of the matte and
    metal parts - without them Roblox shows those parts white."""
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    binc = b[20 + n + 8:]
    out = {}
    for m in j["meshes"]:
        for i, p in enumerate(m["primitives"]):
            a = p["attributes"].get("COLOR_0")
            if a is None:
                continue
            acc = j["accessors"][a]
            bv = j["bufferViews"][acc["bufferView"]]
            ct = {5126: "<f4", 5121: "u1", 5123: "<u2"}[acc["componentType"]]
            nc = {"VEC3": 3, "VEC4": 4}[acc["type"]]
            size = np.dtype(ct).itemsize
            stride = bv.get("byteStride") or nc * size
            base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            raw = np.frombuffer(binc, dtype=np.uint8)
            arr = np.empty((acc["count"], nc), dtype=float)
            for k in range(acc["count"]):
                arr[k] = np.frombuffer(raw[base + k * stride: base + k * stride + nc * size].tobytes(), dtype=ct, count=nc)
            if acc.get("normalized"):
                arr = arr / float(np.iinfo(np.dtype(ct)).max)
            if nc == 3:
                arr = np.concatenate([arr, np.ones((len(arr), 1))], axis=1)
            name = m.get("name", "") if i == 0 else "%s_%d" % (m.get("name", ""), i)
            out[name] = arr
    return out


def split_by_colour(g, colours, step=0.06):
    """A mesh without a colour texture, painted by vertex colours: one sub-mesh for every (rounded) colour, each with the colour as the
    material's base colour.  -> [(Trimesh, colour)]"""
    mat = g.visual.material
    faces = np.asarray(g.faces)
    fc = np.round(colours[faces][:, :, :3].mean(axis=1) / step) * step           # one colour for each face: the mean of its corners
    keys, inverse = np.unique(np.round(fc, 3), axis=0, return_inverse=True)
    parts = []
    for i, key in enumerate(keys):
        sel = np.where(inverse.reshape(-1) == i)[0]
        sub = g.submesh([sel], append=True, repair=False)
        base = np.asarray(getattr(mat, "baseColorFactor", None) if getattr(mat, "baseColorFactor", None) is not None else [255, 255, 255, 255], dtype=float) / 255.0
        col = np.clip(key, 0, 1) * base[:3]
        new = trimesh.visual.material.PBRMaterial(
            name=getattr(mat, "name", None), baseColorFactor=[int(c * 255 + 0.5) for c in col] + [int(base[3] * 255 + 0.5)],
            metallicFactor=getattr(mat, "metallicFactor", None), roughnessFactor=getattr(mat, "roughnessFactor", None),
            emissiveFactor=getattr(mat, "emissiveFactor", None), alphaMode=getattr(mat, "alphaMode", None), doubleSided=False)
        sub.visual = trimesh.visual.TextureVisuals(material=new)
        parts.append((sub, col))
    return parts


def reduce(g, target):
    """g: a trimesh.Trimesh; returns it with about `target` triangles, UVs / vertex colours carried over from the nearest vertex"""
    if len(g.faces) <= target:                     # kept as it is, but rebuilt clean (some small meshes carry attribute arrays the exporter chokes on)
        v, f, idx = np.asarray(g.vertices), np.asarray(g.faces), np.arange(len(g.vertices))
    else:
        v, f = fast_simplification.simplify(np.asarray(g.vertices, dtype=np.float32), np.asarray(g.faces, dtype=np.int32), target_count=target, agg=7)
        _, idx = cKDTree(np.asarray(g.vertices)).query(v)
    out = trimesh.Trimesh(vertices=v, faces=f, process=False)
    out.metadata['src_index'] = idx
    vis = g.visual
    if hasattr(vis, "uv") and vis.uv is not None and len(vis.uv) == len(g.vertices):
        out.visual = trimesh.visual.TextureVisuals(uv=np.asarray(vis.uv)[idx], material=vis.material)
    elif vis.kind == "vertex":
        out.visual = trimesh.visual.ColorVisuals(mesh=out, vertex_colors=np.asarray(vis.vertex_colors)[idx])
    elif hasattr(vis, "material"):
        out.visual = trimesh.visual.TextureVisuals(material=vis.material)
    return out


def split(g, parts):
    """a big mesh in `parts` chunks along its longest axis (each one then below the limit)"""
    if parts <= 1:
        return [g]
    axis = int(np.argmax(g.extents))
    c = g.triangles_center[:, axis]
    edges = np.quantile(c, np.linspace(0, 1, parts + 1))
    out = []
    for i in range(parts):
        m = (c >= edges[i]) & (c <= edges[i + 1] if i == parts - 1 else c < edges[i + 1])
        if m.any():
            out.append(g.submesh([np.where(m)[0]], append=True, repair=False))
    return out


def main(keys):
    os.makedirs(OUT, exist_ok=True)
    for key in keys:
        path = os.path.join(SRC, key + ".glb")
        if not os.path.exists(path):
            print("missing", path)
            continue
        scene = trimesh.load(path, force="scene")
        colours = glb_colors(path)
        if key in LIVERIES:
            done = {}
            for g in scene.geometry.values():
                m = getattr(g.visual, "material", None)
                t = getattr(m, "baseColorTexture", None)
                if t is not None:
                    if id(t) not in done:
                        done[id(t)] = repaint(t, LIVERIES[key]).resize((1024, 1024), Image.LANCZOS)
                    m.baseColorTexture = done[id(t)]
        total = sum(len(g.faces) for g in scene.geometry.values())
        k = min(1.0, TOTAL / total)
        new = trimesh.Scene()
        count = 0
        for node in scene.graph.nodes_geometry:
            T, gname = scene.graph[node]
            g = scene.geometry[gname]
            target = max(60, min(MAXTRI, int(len(g.faces) * k)))
            r = reduce(g, target)
            mat = getattr(g.visual, "material", None)
            textured = getattr(mat, "baseColorTexture", None) is not None
            col = colours.get(gname)
            if not textured and col is not None and len(col) == len(g.vertices):
                # the paint of the matte / metal parts (dark intakes, panels, nozzles ...) is in the vertex colours: made a material colour
                r.visual = trimesh.visual.TextureVisuals(material=mat)
                for i, (sub, c) in enumerate(split_by_colour(r, col[r.metadata["src_index"]])):
                    sub.vertex_normals                                      # (computed, so that they are exported)
                    new.add_geometry(sub, node_name="%s_c%d" % (node, i), geom_name="%s_c%d" % (gname, i), transform=T)
                    count += len(sub.faces)
            else:
                r.vertex_normals
                new.add_geometry(r, node_name=node, geom_name=gname, transform=T)
                count += len(r.faces)
        data = new.export(file_type="glb")
        with open(os.path.join(OUT, key + ".glb"), "wb") as f:
            f.write(data)
        print("%-8s %6d -> %6d triangles, %5d KB" % (key, total, count, len(data) // 1024))


if __name__ == "__main__":
    main(sys.argv[1:] or KEYS)
