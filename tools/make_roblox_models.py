"""Makes the jet models Roblox can import: the .glb files of web/assets with every mesh cut down to at most MAXTRI triangles
(Roblox refuses a mesh of more than 20000), the textures and vertex colours kept.   python3 tools/make_roblox_models.py
Output: roblox/models/<key>.glb  (import them in Studio: View > Asset Manager > Bulk Import, see roblox/README.md)
Needs: pip install trimesh fast-simplification scipy numpy pillow"""
import os
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


def reduce(g, target):
    """g: a trimesh.Trimesh; returns it with about `target` triangles, UVs / vertex colours carried over from the nearest vertex"""
    if len(g.faces) <= target:                     # kept as it is, but rebuilt clean (some small meshes carry attribute arrays the exporter chokes on)
        v, f, idx = np.asarray(g.vertices), np.asarray(g.faces), np.arange(len(g.vertices))
    else:
        v, f = fast_simplification.simplify(np.asarray(g.vertices, dtype=np.float32), np.asarray(g.faces, dtype=np.int32), target_count=target, agg=7)
        _, idx = cKDTree(np.asarray(g.vertices)).query(v)
    out = trimesh.Trimesh(vertices=v, faces=f, process=False)
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
        total = sum(len(g.faces) for g in scene.geometry.values())
        k = min(1.0, TOTAL / total)
        new = trimesh.Scene()
        count = 0
        for node in scene.graph.nodes_geometry:
            T, gname = scene.graph[node]
            g = scene.geometry[gname]
            target = max(60, min(MAXTRI, int(len(g.faces) * k)))
            r = reduce(g, target)
            new.add_geometry(r, node_name=node, geom_name=gname, transform=T)
            count += len(r.faces)
        data = new.export(file_type="glb")
        with open(os.path.join(OUT, key + ".glb"), "wb") as f:
            f.write(data)
        print("%-8s %6d -> %6d triangles, %5d KB" % (key, total, count, len(data) // 1024))


if __name__ == "__main__":
    main(sys.argv[1:] or KEYS)
