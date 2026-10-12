import os
import random
import sys

import pytest
from panda3d.core import Vec3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dogfight.sim.aircraft import Aircraft  # noqa: E402
from dogfight.sim.specs import F16C  # noqa: E402
from dogfight.sim.world import World  # noqa: E402


class FlatTerrain:
    seed = 0

    def height(self, x, y):
        return 0.0

    def raw_height(self, x, y):
        return 0.0

    def line_of_sight(self, a, b, samples=10):
        return True

    def clamp_inside(self, x, y, margin=0.0):
        return x, y

    def slope(self, x, y, d=6.0):
        return 0.0


@pytest.fixture
def world():
    return World(FlatTerrain(), seed=1)


@pytest.fixture
def make_aircraft(world):
    def make(pos=(0, 0, 5000), heading=0.0, speed=250.0, team="blue", name="ac", **kw):
        ac = Aircraft(F16C, name, team, Vec3(*pos), heading, speed, rng=random.Random(7), **kw)
        world.add_aircraft(ac)
        return ac
    return make


def run(world, seconds, dt=1.0 / 60.0):
    for _ in range(int(seconds / dt)):
        world.update(dt)
