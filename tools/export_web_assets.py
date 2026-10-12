"""Export the procedural F-16, missiles, liveries and terrain for the browser version (web/)."""

import base64
import json
import os
import sys

import numpy as np
from panda3d.core import Filename, GeomVertexReader, NodePath, PNMImage, Texture

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dogfight.render.f16_model import build_detailed_f16, livery_texture  # noqa: E402
from dogfight.render.models import build_gear, build_missile  # noqa: E402
from dogfight.render.terrain_mesh import terrain_colors, terrain_normals  # noqa: E402
from dogfight.sim.terrain import Terrain  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "assets")


def b64(arr):
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode("ascii")


def geometry(np_):
    pos, nrm, uv, col, idx = [], [], [], [], []
    base = 0
    nodes = list(np_.findAllMatches("**/+GeomNode"))
    if np_.node().isGeomNode() and np_ not in nodes:
        nodes.insert(0, np_)
    for gnp in nodes:
        mat = gnp.getMat(np_)
        node = gnp.node()
        for gi in range(node.getNumGeoms()):
            geom = node.getGeom(gi).decompose()
            vdata = geom.getVertexData()
            n = vdata.getNumRows()
            rv = GeomVertexReader(vdata, "vertex")
            rn = GeomVertexReader(vdata, "normal")
            has_uv = vdata.hasColumn("texcoord")
            has_col = vdata.hasColumn("color")
            rt = GeomVertexReader(vdata, "texcoord") if has_uv else None
            rc = GeomVertexReader(vdata, "color") if has_col else None
            for _ in range(n):
                p = mat.xformPoint(rv.getData3())
                q = mat.xformVec(rn.getData3())
                pos.extend((p.x, p.y, p.z))
                nrm.extend((q.x, q.y, q.z))
                if rt:
                    t = rt.getData2()
                    uv.extend((t.x, t.y))
                if rc:
                    c = rc.getData4()
                    col.extend((c.x, c.y, c.z, c.w))
            for pi in range(geom.getNumPrimitives()):
                prim = geom.getPrimitive(pi)
                for k in range(prim.getNumVertices()):
                    idx.append(base + prim.getVertex(k))
            base += n
    out = dict(pos=b64(np.array(pos, np.float32)), nrm=b64(np.array(nrm, np.float32)),
               idx=b64(np.array(idx, np.uint32)), count=len(idx))
    if uv:
        out["uv"] = b64(np.array(uv, np.float32))
    if col:
        out["col"] = b64(np.array(col, np.float32))
    return out


def save_texture(tex, path, size=None):
    img = PNMImage()
    tex.store(img)
    if size:
        small = PNMImage(size, size, img.getNumChannels())
        small.gaussianFilterFrom(1.0, img)
        img = small
    img.write(Filename.fromOsSpecific(path))


def main():
    os.makedirs(OUT, exist_ok=True)
    g = build_detailed_f16()
    model = dict(skin=geometry(g["skin"]), plain=geometry(g["plain"]), glass=geometry(g["glass"]),
                 lights=geometry(g["lights"]), gear=geometry(build_gear()), parts=[],
                 missiles={k: geometry(build_missile(k)) for k in ("AIM-9M", "AIM-120A")})
    for part in g["parts"]:
        q = part["quat"]
        model["parts"].append(dict(name=part["name"], pos=[part["pos"].x, part["pos"].y, part["pos"].z],
                                   quat=[q.getR(), q.getI(), q.getJ(), q.getK()], sign=part["sign"],
                                   geom=geometry(part["node"])))
    with open(os.path.join(OUT, "f16.json"), "w") as f:
        json.dump(model, f, separators=(",", ":"))
    for livery in ("viper", "aggressor"):
        save_texture(livery_texture(livery), os.path.join(OUT, "livery_%s.jpg" % livery))

    terrain = Terrain()
    grid = terrain.grid
    q = np.clip(np.round(grid * 4.0), -32768, 32767).astype("<i2")
    a = terrain.airfield
    with open(os.path.join(OUT, "terrain.json"), "w") as f:
        json.dump(dict(size=terrain.size, res=terrain.res, scale=0.25, heights=b64(q),
                       airfield=dict(x=a.x, y=a.y, elevation=a.elevation)), f, separators=(",", ":"))
    normals = terrain_normals(grid, terrain.cell)
    col = terrain_colors(grid, normals, terrain.seed)[..., :3]
    n = 2048
    xs = np.linspace(0, grid.shape[0] - 1, n)
    i0 = np.floor(xs).astype(int).clip(0, grid.shape[0] - 2)
    f_ = (xs - i0)[None, :, None]
    rows = col[i0] * (1 - (xs - i0)[:, None, None]) + col[i0 + 1] * (xs - i0)[:, None, None]
    up = rows[:, i0] * (1 - f_) + rows[:, i0 + 1] * f_
    up *= (0.94 + 0.12 * np.random.default_rng(3).random((n, n)))[..., None]
    rgb = (np.clip(up, 0, 1) * 255).astype(np.uint8)
    tex = Texture()
    tex.setup2dTexture(n, n, Texture.T_unsigned_byte, Texture.F_rgb)
    tex.setRamImage(rgb[:, :, ::-1].tobytes())          # row 0 = south (texture rows are bottom-up)
    save_texture(tex, os.path.join(OUT, "terrain_color.jpg"))
    for name in sorted(os.listdir(OUT)):
        print("%-22s %8.1f KB" % (name, os.path.getsize(os.path.join(OUT, name)) / 1024))


if __name__ == "__main__":
    main()
