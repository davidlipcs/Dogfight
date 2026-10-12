"""Terrain rendering: per-vertex colours + chunked mesh with distance LOD.

The 1025 x 1025 height grid is cut into 16 x 16 chunks.  Every chunk has
three levels of detail (100 m, 400 m and 1600 m between vertices) that a
LODNode swaps by distance, and "skirts" hanging down from the chunk edges
hide the cracks between neighbouring chunks of different detail.
"""

import numpy as np
from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexArrayFormat, GeomVertexData, GeomVertexFormat,
                          InternalName, LODNode, NodePath, PNMImage, Texture)

from ..sim.terrain import _Perlin

CHUNK = 64                                   # cells per chunk side
LODS = ((1, 0.0, 9000.0), (4, 9000.0, 32000.0), (16, 32000.0, 400000.0))   # (step, near, far)
SKIRT = 80.0                                 # m

_FORMAT = None


def _format():
    global _FORMAT
    if _FORMAT is None:
        arr = GeomVertexArrayFormat()
        arr.addColumn(InternalName.getVertex(), 3, Geom.NT_float32, Geom.C_point)
        arr.addColumn(InternalName.getNormal(), 3, Geom.NT_float32, Geom.C_normal)
        arr.addColumn(InternalName.getColor(), 4, Geom.NT_float32, Geom.C_color)
        _FORMAT = GeomVertexFormat.registerFormat(arr)
    return _FORMAT


# ------------------------------------------------------------------ colours
def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _mix(a, b, t):
    return a + (np.asarray(b, np.float32) - a) * t[..., None]


def terrain_normals(grid, cell):
    gy, gx = np.gradient(grid.astype(np.float32), cell)
    n = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n.astype(np.float32)


def terrain_colors(grid, normals, seed=0):
    """RGBA per sample from height, slope and some noise (fields / forests)."""
    rng = np.random.default_rng(seed)
    h = grid
    steep = 1.0 - normals[..., 2]                      # 0 flat .. 1 vertical
    n = h.shape[0]
    # natural looking patches (fields vs. forest)
    coords = np.linspace(0.0, 1.0, n, dtype=np.float32) * 40.0
    X, Y = np.meshgrid(coords, coords)
    patches = np.clip(_Perlin(seed + 7).fbm(X, Y, 4) * 0.6 + 0.5, 0.0, 1.0)
    fine = rng.random((n, n)).astype(np.float32)

    sand = (0.76, 0.71, 0.53)
    field = (0.50, 0.53, 0.29)
    grass = (0.33, 0.46, 0.22)
    forest = (0.17, 0.29, 0.14)
    rock = (0.45, 0.42, 0.38)
    dark_rock = (0.33, 0.31, 0.29)
    snow = (0.94, 0.95, 0.97)

    col = np.empty(h.shape + (3,), np.float32)
    col[:] = grass
    col = _mix(col, field, (patches > 0.55).astype(np.float32) * (1.0 - _smooth(250.0, 500.0, h)))
    col = _mix(col, forest, _smooth(300.0, 800.0, h) * (patches < 0.75) * (1.0 - _smooth(1500.0, 1900.0, h)))
    col = _mix(col, rock, _smooth(1700.0, 2100.0, h))
    col = _mix(col, dark_rock, _smooth(0.30, 0.55, steep))
    snow_line = 2350.0 + 250.0 * patches
    col = _mix(col, snow, _smooth(snow_line, snow_line + 200.0, h) * (1.0 - _smooth(0.45, 0.7, steep)))
    col = _mix(col, sand, 1.0 - _smooth(4.0, 25.0, h))
    col = _mix(col, (0.22, 0.30, 0.30), 1.0 - _smooth(-30.0, 0.0, h))      # wet / underwater
    col *= (0.92 + 0.12 * fine)[..., None]
    rgba = np.ones(h.shape + (4,), np.float32)
    rgba[..., :3] = np.clip(col, 0.0, 1.0)
    return rgba


# ------------------------------------------------------------------- mesh
def _grid_indices(m):
    """Triangle indices of an (m+1) x (m+1) vertex grid (counter-clockwise from above)."""
    i, j = np.meshgrid(np.arange(m), np.arange(m))
    a = (j * (m + 1) + i).ravel()
    b = a + 1
    c = a + m + 2
    d = a + m + 1
    return np.stack([a, b, c, a, c, d], axis=1).reshape(-1, 3)


def _border(m):
    """Indices of the border vertices of an (m+1)^2 grid, in a closed loop."""
    w = m + 1
    bottom = [k for k in range(w)]
    right = [k * w + m for k in range(1, w)]
    top = [m * w + k for k in range(m - 1, -1, -1)]
    left = [k * w for k in range(m - 1, 0, -1)]
    return np.array(bottom + right + top + left + [0], np.int64)


def _build_geom(verts, tris, name):
    vdata = GeomVertexData(name, _format(), Geom.UHStatic)
    vdata.uncleanSetNumRows(len(verts))
    memoryview(vdata.modifyArray(0)).cast("B")[:] = verts.astype(np.float32).tobytes()
    prim = GeomTriangles(Geom.UHStatic)
    prim.setIndexType(Geom.NT_uint32)
    idx = prim.modifyVertices()
    idx.uncleanSetNumRows(tris.size)
    memoryview(idx).cast("B")[:] = tris.astype(np.uint32).tobytes()
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(geom)
    return node


def build_terrain_node(terrain, seed=0):
    grid = terrain.grid
    cell = terrain.cell
    half = terrain.half
    normals = terrain_normals(grid, cell)
    colors = terrain_colors(grid, normals, seed)
    root = NodePath("terrain")
    res = terrain.res
    chunks = res // CHUNK
    index_cache = {}
    for cj in range(chunks):
        for ci in range(chunks):
            lod = LODNode("chunk")
            lod_np = root.attachNewNode(lod)
            cx = -half + (ci + 0.5) * CHUNK * cell
            cy = -half + (cj + 0.5) * CHUNK * cell
            center_z = float(grid[cj * CHUNK + CHUNK // 2, ci * CHUNK + CHUNK // 2])
            lod.setCenter((cx, cy, center_z))
            for step, near, far in LODS:
                m = CHUNK // step
                sl = (slice(cj * CHUNK, cj * CHUNK + CHUNK + 1, step), slice(ci * CHUNK, ci * CHUNK + CHUNK + 1, step))
                hz = grid[sl]
                xs = -half + np.arange(ci * CHUNK, ci * CHUNK + CHUNK + 1, step) * cell
                ys = -half + np.arange(cj * CHUNK, cj * CHUNK + CHUNK + 1, step) * cell
                X, Y = np.meshgrid(xs, ys)
                verts = np.concatenate([np.stack([X, Y, hz], -1).reshape(-1, 3),
                                        normals[sl].reshape(-1, 3), colors[sl].reshape(-1, 4)], axis=1)
                if m not in index_cache:
                    tris = _grid_indices(m)
                    border = _border(m)
                    nb = len(border)
                    base = (m + 1) * (m + 1)
                    top = border[:-1]
                    nxt = border[1:]
                    low = base + np.arange(nb - 1)
                    low_nxt = base + np.arange(1, nb)
                    skirt = np.concatenate([np.stack([top, low, low_nxt], 1), np.stack([top, low_nxt, nxt], 1),
                                            np.stack([top, low_nxt, low], 1), np.stack([top, nxt, low_nxt], 1)])
                    index_cache[m] = (np.concatenate([tris, skirt]), border)
                tris, border = index_cache[m]
                skirt_verts = verts[border].copy()
                skirt_verts[:, 2] -= SKIRT
                node = _build_geom(np.concatenate([verts, skirt_verts]), tris, "terrain_%d_%d_%d" % (ci, cj, step))
                lod_np.attachNewNode(node)
                lod.addSwitch(far, near)
    return root


def map_preview(terrain, size=512, seed=0):
    """Top-down coloured, hill-shaded picture of the map (for the README / debugging)."""
    step = max(1, terrain.grid.shape[0] // size)
    grid = terrain.grid[::step, ::step]
    normals = terrain_normals(grid, terrain.cell * step)
    col = terrain_colors(grid, normals, seed)[..., :3]
    sun = np.array([-0.45, 0.55, 0.70], np.float32)
    sun /= np.linalg.norm(sun)
    shade = np.clip(normals @ sun, 0.0, 1.0) * 0.75 + 0.35
    col = np.clip(col * shade[..., None], 0.0, 1.0)
    water = grid < 0.0
    col[water] = (0.17, 0.33, 0.45)
    n = grid.shape[0]
    img = PNMImage(n, n, 3)
    rgb = (col[::-1] * 255).astype(np.uint8)                 # image rows go top -> bottom (north up)
    tex = Texture()
    tex.setup2dTexture(n, n, Texture.T_unsigned_byte, Texture.F_rgb)
    tex.setRamImage(rgb[::-1, :, ::-1].tobytes())            # textures are bottom-up BGR
    tex.store(img)
    return img
