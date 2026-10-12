"""Procedural height field: an island with hills and a mountain range.

Used both for collision / radar line of sight (here) and for the visible
terrain mesh (render.environment builds the mesh from the same grid).
"""

import math
import random

from ..mathutil import clamp, smoothstep

SEA_LEVEL = 0.0


class _ValueNoise:
    def __init__(self, seed):
        rnd = random.Random(seed)
        self.perm = list(range(256))
        rnd.shuffle(self.perm)
        self.perm += self.perm
        self.values = [rnd.uniform(-1.0, 1.0) for _ in range(256)]

    def _lattice(self, ix, iy):
        return self.values[self.perm[(self.perm[ix & 255] + iy) & 255]]

    def noise(self, x, y):
        ix = math.floor(x)
        iy = math.floor(y)
        fx = x - ix
        fy = y - iy
        sx = fx * fx * (3 - 2 * fx)
        sy = fy * fy * (3 - 2 * fy)
        a = self._lattice(ix, iy)
        b = self._lattice(ix + 1, iy)
        c = self._lattice(ix, iy + 1)
        d = self._lattice(ix + 1, iy + 1)
        top = a + (b - a) * sx
        bottom = c + (d - c) * sx
        return top + (bottom - top) * sy

    def fbm(self, x, y, octaves=5, lacunarity=2.03, gain=0.5):
        total = 0.0
        amp = 1.0
        norm = 0.0
        for _ in range(octaves):
            total += amp * self.noise(x, y)
            norm += amp
            x *= lacunarity
            y *= lacunarity
            amp *= gain
        return total / norm


class Terrain:
    def __init__(self, size=90000.0, resolution=180, seed=1974):
        self.size = size
        self.res = resolution
        self.cell = size / resolution
        self.half = size * 0.5
        self.seed = seed
        noise = _ValueNoise(seed)
        ridge = _ValueNoise(seed + 1)
        self.heights = []
        for j in range(resolution + 1):
            row = []
            y = -self.half + j * self.cell
            for i in range(resolution + 1):
                x = -self.half + i * self.cell
                row.append(self._shape(noise, ridge, x, y))
            self.heights.append(row)

    def _shape(self, noise, ridge, x, y):
        base = noise.fbm(x / 16000.0, y / 16000.0, octaves=5)
        h = 260.0 + 700.0 * base
        # Mountain range: ridged noise, masked to one band of the map.
        mask = smoothstep(0.05, 0.45, noise.fbm(x / 34000.0 + 11.3, y / 34000.0 - 4.1, octaves=2))
        r = 1.0 - abs(ridge.fbm(x / 9000.0, y / 9000.0, octaves=4))
        h += mask * 2300.0 * r * r
        # Sea all around the island.
        dist = math.hypot(x, y) / self.half
        h = h * (1.0 - smoothstep(0.72, 0.97, dist)) - 180.0 * smoothstep(0.8, 1.0, dist)
        return h

    def raw_height(self, x, y):
        """Bilinear height, may be below sea level."""
        gx = (x + self.half) / self.cell
        gy = (y + self.half) / self.cell
        if gx < 0 or gy < 0 or gx >= self.res or gy >= self.res:
            return -180.0
        i = int(gx)
        j = int(gy)
        fx = gx - i
        fy = gy - j
        row0 = self.heights[j]
        row1 = self.heights[j + 1]
        h0 = row0[i] + (row0[i + 1] - row0[i]) * fx
        h1 = row1[i] + (row1[i + 1] - row1[i]) * fx
        return h0 + (h1 - h0) * fy

    def height(self, x, y):
        """Collision height (water surface counts as ground)."""
        return max(self.raw_height(x, y), SEA_LEVEL)

    def line_of_sight(self, a, b, samples=10):
        """True when the straight line a->b does not pass below the terrain."""
        dx = b.x - a.x
        dy = b.y - a.y
        dz = b.z - a.z
        for k in range(1, samples):
            t = k / samples
            z = a.z + dz * t
            if z < 2600.0 and z < self.height(a.x + dx * t, a.y + dy * t):
                return False
        return True

    def clamp_inside(self, x, y, margin=8000.0):
        lim = self.half - margin
        return clamp(x, -lim, lim), clamp(y, -lim, lim)
