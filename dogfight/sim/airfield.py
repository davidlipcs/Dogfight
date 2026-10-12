"""The home air base: runway 18/36, parallel taxiway, apron with shelters.

All geometry is axis aligned (the runway points north), which keeps the
flattening of the terrain and the "am I on the runway?" checks trivial.
"""

import numpy as np

RUNWAY_LENGTH = 3000.0      # m (typical F-16 base, e.g. Aviano 2700 m, Hill AFB 4100 m)
RUNWAY_WIDTH = 45.0
TAXIWAY_OFFSET = 190.0      # m east of the runway centreline
TAXIWAY_WIDTH = 23.0
APRON = (260.0, 520.0, -350.0, 350.0)     # x0, x1, y0, y1 relative to the base centre


class Airfield:
    def __init__(self, x, y, name="Viper Base"):
        self.x = x
        self.y = y
        self.name = name
        self.elevation = 0.0

    # ------------------------------------------------------------ geometry
    @property
    def south_threshold(self):
        return self.y - RUNWAY_LENGTH * 0.5

    @property
    def north_threshold(self):
        return self.y + RUNWAY_LENGTH * 0.5

    def on_runway(self, x, y, margin=0.0):
        return (abs(x - self.x) <= RUNWAY_WIDTH * 0.5 + margin
                and abs(y - self.y) <= RUNWAY_LENGTH * 0.5 + margin)

    def on_paved(self, x, y):
        """Runway, taxiway or apron (low rolling friction, rearming allowed)."""
        dx = x - self.x
        dy = y - self.y
        if self.on_runway(x, y, margin=3.0):
            return True
        if abs(dx - TAXIWAY_OFFSET) <= TAXIWAY_WIDTH * 0.5 and abs(dy) <= RUNWAY_LENGTH * 0.5:
            return True
        for cy in (-RUNWAY_LENGTH * 0.5 + 60.0, 0.0, RUNWAY_LENGTH * 0.5 - 60.0):   # connectors
            if 0.0 <= dx <= TAXIWAY_OFFSET and abs(dy - cy) <= TAXIWAY_WIDTH * 0.5:
                return True
        x0, x1, y0, y1 = APRON
        return x0 - 70.0 <= dx <= x1 and y0 <= dy <= y1

    def on_base(self, x, y):
        return abs(x - self.x) < 700.0 and abs(y - self.y) < RUNWAY_LENGTH * 0.5 + 300.0

    def start_position(self):
        """Lined up on runway 36 (south end), facing north."""
        return self.x, self.south_threshold + 120.0, 0.0

    # ------------------------------------------------------------- terrain
    def flatten(self, grid, half, cell):
        """Level the terrain under the base (smooth blend into the hills around)."""
        n = grid.shape[0]
        coords = np.linspace(-half, half, n, dtype=np.float32)
        X, Y = np.meshgrid(coords, coords)
        dx = np.abs(X - (self.x + 200.0)) - 650.0              # flat core: runway .. apron
        dy = np.abs(Y - self.y) - (RUNWAY_LENGTH * 0.5 + 500.0)
        dist = np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
        core = dist <= 0.0
        self.elevation = float(np.round(np.median(grid[core])))
        t = np.clip(dist / 900.0, 0.0, 1.0)
        blend = t * t * (3.0 - 2.0 * t)
        grid[:] = self.elevation + (grid - self.elevation) * blend
        return grid


HOME_BASE = (19000.0, -26000.0)
