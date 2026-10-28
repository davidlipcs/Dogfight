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
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web", "assets")
OUT = os.path.join(ROOT, "roblox", "models")
MAXTRI = 15000                    # per mesh (Roblox: 20000)
TOTAL = 42000                     # per jet (the jets are seen small; eight of them fly at once)
KEYS = ["f16", "fa18", "f15", "f22", "f35", "gripen", "typhoon", "rafale", "su35", "su57", "mig29", "mig31", "j20", "t38", "t45", "t6"]


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
