"""Procedural island map with small hills, mid-size mountains and a big alpine range.

The height field is generated with vectorised (numpy) Perlin noise on a
1025 x 1025 grid (100 m between samples, ~102 km across) and cached on disk,
so only the very first start takes a few seconds.

Layout (north = +Y, the player starts in the south heading north)::

    north : a long, snow capped mountain range, peaks 3000-3800 m
    east  : a big isolated massif (~3200 m)
    west  : medium mountains (1200-2200 m)
    centre: a valley with a lake
    south : rolling hills and small mountains (200-900 m)
    edges : coastline with bays, open sea beyond
"""

import math
import os
import tempfile

import numpy as np

from ..mathutil import clamp

SEA_LEVEL = 0.0
CACHE_VERSION = 4

# (x, y, radius, height) of individual mountains, metres
MASSIFS = (
    (24000.0, -4000.0, 6500.0, 2600.0),     # big eastern massif
    (-27000.0, -12000.0, 5200.0, 1300.0),   # western mountains
    (-33000.0, -2000.0, 4200.0, 1100.0),
    (-20000.0, -21000.0, 3500.0, 700.0),
    (12000.0, -28000.0, 3000.0, 600.0),     # small mountains in the south
    (30000.0, -24000.0, 3800.0, 900.0),
    (-6000.0, -34000.0, 2600.0, 450.0),
    (6000.0, 22000.0, 4000.0, 900.0),       # foothills of the northern range
)

# The northern range follows this poly-line (x, y)
RANGE_LINE = ((-40000.0, 14000.0), (-20000.0, 24000.0), (0.0, 30000.0), (18000.0, 26000.0), (38000.0, 34000.0))


# ------------------------------------------------------------------ noise
class _Perlin:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.perm = np.concatenate([rng.permutation(256)] * 2).astype(np.int64)
        angles = rng.uniform(0.0, 2.0 * math.pi, 256)
        self.grads = np.stack([np.cos(angles), np.sin(angles)], axis=1)

    def noise(self, x, y):
        xi = np.floor(x).astype(np.int64)
        yi = np.floor(y).astype(np.int64)
        xf = (x - xi).astype(np.float32)
        yf = (y - yi).astype(np.float32)
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
        # gradients for the lattice corners actually used (one fancy index per corner)
        x0, y0 = int(xi.min()), int(yi.min())
        lx = np.arange(x0, int(xi.max()) + 2)
        ly = np.arange(y0, int(yi.max()) + 2)
        hashed = self.perm[(self.perm[lx & 255][None, :] + ly[:, None]) & 255]
        gx = self.grads[hashed, 0].astype(np.float32)
        gy = self.grads[hashed, 1].astype(np.float32)
        ix = xi - x0
        iy = yi - y0
        n00 = gx[iy, ix] * xf + gy[iy, ix] * yf
        n10 = gx[iy, ix + 1] * (xf - 1) + gy[iy, ix + 1] * yf
        n01 = gx[iy + 1, ix] * xf + gy[iy + 1, ix] * (yf - 1)
        n11 = gx[iy + 1, ix + 1] * (xf - 1) + gy[iy + 1, ix + 1] * (yf - 1)
        a = n00 + (n10 - n00) * u
        b = n01 + (n11 - n01) * u
        return (a + (b - a) * v) * 1.41    # roughly -1..1

    def fbm(self, x, y, octaves, lacunarity=2.03, gain=0.5):
        total = np.zeros_like(x)
        amp = 1.0
        norm = 0.0
        for o in range(octaves):
            total += amp * self.noise(x + o * 17.3, y - o * 9.1)
            norm += amp
            x = x * lacunarity
            y = y * lacunarity
            amp *= gain
        return total / norm

    def ridged(self, x, y, octaves, lacunarity=2.1, gain=0.5):
        """Ridged multifractal: sharp crests, smooth valleys (0..1)."""
        total = np.zeros_like(x)
        weight = np.ones_like(x)
        amp = 0.5
        norm = 0.0
        for o in range(octaves):
            n = 1.0 - np.abs(self.noise(x + o * 31.7, y + o * 7.9))
            n = n * n * weight
            weight = np.clip(n * 2.0, 0.0, 1.0)
            total += n * amp
            norm += amp
            x = x * lacunarity
            y = y * lacunarity
            amp *= gain
        return total / norm


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _distance_to_polyline(x, y, points):
    best = np.full_like(x, 1e12)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx = x1 - x0
        dy = y1 - y0
        t = np.clip(((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
        d = np.hypot(x - (x0 + t * dx), y - (y0 + t * dy))
        best = np.minimum(best, d)
    return best


def generate_heights(size, n, seed):
    half = size * 0.5
    coords = np.linspace(-half, half, n)
    X, Y = np.meshgrid(coords.astype(np.float32), coords.astype(np.float32))          # row = y index, column = x index
    p = _Perlin(seed)
    q = _Perlin(seed + 101)

    # domain warp - makes everything less "noise looking"
    wx = p.fbm(X / 21000.0, Y / 21000.0, 3) * 3500.0
    wy = q.fbm(X / 21000.0 + 5.2, Y / 21000.0 - 1.3, 3) * 3500.0
    Xw = X + wx
    Yw = Y + wy

    # lowlands + small hills everywhere
    h = 90.0 + 160.0 * p.fbm(Xw / 26000.0, Yw / 26000.0, 3)
    hilly = _smoothstep(-0.35, 0.45, q.fbm(X / 30000.0 + 3.3, Y / 30000.0 + 8.1, 2))
    hills = np.clip(p.fbm(Xw / 4800.0, Yw / 4800.0, 5) * 0.5 + 0.5, 0.0, 1.0)
    h += hills ** 1.4 * 850.0 * (0.3 + 0.7 * hilly)

    # medium mountains scattered over the island (ridged, 600-1800 m)
    medium_mask = _smoothstep(0.05, 0.5, q.fbm(X / 24000.0 - 7.7, Y / 24000.0 + 2.9, 3))
    h += medium_mask * 1500.0 * p.ridged(Xw / 7000.0 + 3.1, Yw / 7000.0 - 5.3, 6) ** 1.5

    # big northern range: ridged noise inside a band around the poly-line
    dist = _distance_to_polyline(Xw, Yw, RANGE_LINE)
    band = np.exp(-(dist / 8500.0) ** 2)
    crest = p.ridged(Xw / 11000.0, Yw / 11000.0, 7)
    h += band * (900.0 + 3100.0 * crest ** 1.3)

    # individual mountains (one shared ridged field gives them crests and gullies)
    detail = q.ridged(Xw / 4500.0, Yw / 4500.0, 6)
    for cx, cy, radius, height in MASSIFS:
        shape = np.exp(-((Xw - cx) ** 2 + (Yw - cy) ** 2) / (radius * radius))
        h += shape * height * (0.55 + 0.75 * detail)

    # valley with a lake in the middle of the island
    lake = np.exp(-(((X - 4000.0) ** 2) / 4200.0 ** 2 + ((Y - 5000.0) ** 2) / 2800.0 ** 2))
    h = h * (1.0 - 0.85 * lake) - 140.0 * lake

    # fine detail (rocks, gullies) scaled by height so plains stay smooth
    h += p.fbm(X / 900.0, Y / 900.0, 3) * (8.0 + 0.03 * np.clip(h, 0.0, None))

    # coastline with bays
    radial = np.hypot(X, Y) / half + 0.2 * q.fbm(X / 22000.0, Y / 22000.0, 4)
    coast = _smoothstep(0.74, 0.93, radial)
    h = h * (1.0 - coast) - 220.0 * coast
    return h.astype(np.float32)


# ---------------------------------------------------------------- terrain
class Terrain:
    def __init__(self, size=102400.0, resolution=1024, seed=1974, cache=True):
        self.size = size
        self.res = resolution                 # cells per side (grid has res + 1 samples)
        self.cell = size / resolution
        self.half = size * 0.5
        self.seed = seed
        self.grid = self._load_or_generate(cache)
        self.max_height = float(self.grid.max())
        self._rows = self.grid.tolist()       # plain lists: much faster scalar lookups

    def _load_or_generate(self, cache):
        n = self.res + 1
        path = os.path.join(tempfile.gettempdir(), "dogfight_terrain_v%d_%d_%d_%d.npy"
                            % (CACHE_VERSION, self.seed, n, int(self.size)))
        if cache and os.path.exists(path):
            try:
                grid = np.load(path)
                if grid.shape == (n, n):
                    return grid
            except (OSError, ValueError):
                pass
        grid = generate_heights(self.size, n, self.seed)
        if cache:
            try:
                np.save(path, grid)
            except OSError:
                pass
        return grid

    def raw_height(self, x, y):
        """Bilinear height, may be below sea level (lake / sea floor)."""
        gx = (x + self.half) / self.cell
        gy = (y + self.half) / self.cell
        if gx < 0.0 or gy < 0.0 or gx >= self.res or gy >= self.res:
            return -220.0
        i = int(gx)
        j = int(gy)
        fx = gx - i
        fy = gy - j
        row0 = self._rows[j]
        row1 = self._rows[j + 1]
        h0 = row0[i] + (row0[i + 1] - row0[i]) * fx
        h1 = row1[i] + (row1[i + 1] - row1[i]) * fx
        return h0 + (h1 - h0) * fy

    def height(self, x, y):
        """Collision height (the water surface counts as ground)."""
        return max(self.raw_height(x, y), SEA_LEVEL)

    def line_of_sight(self, a, b, samples=12):
        """True when the straight line a->b does not pass below the terrain."""
        if a.z > self.max_height and b.z > self.max_height:
            return True
        dx = b.x - a.x
        dy = b.y - a.y
        dz = b.z - a.z
        for k in range(1, samples):
            t = k / samples
            z = a.z + dz * t
            if z < self.max_height and z < self.height(a.x + dx * t, a.y + dy * t):
                return False
        return True

    def clamp_inside(self, x, y, margin=8000.0):
        lim = self.half - margin
        return clamp(x, -lim, lim), clamp(y, -lim, lim)
