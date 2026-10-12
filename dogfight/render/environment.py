"""Terrain mesh, sea, sky dome, sun, haze and clouds."""

import math
import random

from panda3d.core import (AmbientLight, CardMaker, ColorBlendAttrib, DirectionalLight, Fog, Point3, TransparencyAttrib,
                          Vec3, Vec4)

from ..mathutil import smoothstep
from .effects import puffy_texture, soft_texture
from .meshbuilder import MeshBuilder
from .terrain_mesh import build_terrain_node

HORIZON = (0.72, 0.81, 0.90)
ZENITH = (0.19, 0.38, 0.72)
GROUND_HAZE = (0.62, 0.70, 0.76)
SUN_DIR = Vec3(-0.45, 0.55, 0.70)     # direction *towards* the sun


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


class Environment:
    def __init__(self, base, terrain, cloud_count=70, seed=5):
        self.base = base
        self.root = base.render.attachNewNode("environment")
        self._lights(base)
        self._fog(base)
        self.terrain_np = self._terrain(terrain)
        self.sea_np = self._sea()
        self.sky_np = self._sky(base)
        self.clouds_np = self._clouds(terrain, cloud_count, seed)

    # ------------------------------------------------------------- lighting
    def _lights(self, base):
        sun = DirectionalLight("sun")
        sun.setColor(Vec4(1.0, 0.96, 0.88, 1))
        sun_np = base.render.attachNewNode(sun)
        sun_np.lookAt(Point3(-SUN_DIR.x, -SUN_DIR.y, -SUN_DIR.z))   # light travels away from the sun
        base.render.setLight(sun_np)
        amb = AmbientLight("ambient")
        amb.setColor(Vec4(0.44, 0.47, 0.54, 1))
        base.render.setLight(base.render.attachNewNode(amb))

    def _fog(self, base):
        fog = Fog("haze")
        fog.setColor(*HORIZON)
        fog.setExpDensity(1.9e-5)
        base.render.setFog(fog)
        base.setBackgroundColor(*HORIZON)

    # -------------------------------------------------------------- terrain
    def _terrain(self, terrain):
        np_ = build_terrain_node(terrain, seed=terrain.seed)
        np_.reparentTo(self.root)
        return np_

    def _sea(self):
        # A grid of 10 km tiles: one gigantic quad gets clipped badly at the horizon.
        mb = MeshBuilder()
        tile = 10000.0
        count = 32
        z = -1.5           # a hair below the waterline so beaches don't z-fight
        color = (0.17, 0.33, 0.45, 1.0)
        up = Vec3(0, 0, 1)
        start = -tile * count / 2
        for j in range(count):
            for i in range(count):
                x0 = start + i * tile
                y0 = start + j * tile
                mb.quad(Vec3(x0, y0, z), Vec3(x0 + tile, y0, z), Vec3(x0 + tile, y0 + tile, z), Vec3(x0, y0 + tile, z),
                        color, outward=up)
        np = mb.build("sea")
        np.reparentTo(self.root)
        return np

    # ------------------------------------------------------------------ sky
    def _sky(self, base):
        mb = MeshBuilder()
        rings = []
        for el in (-30, -5, 0, 4, 10, 22, 40, 65, 90):
            e = math.radians(el)
            ring = []
            for k in range(25):
                a = 2 * math.pi * k / 24
                ring.append(Vec3(math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)) * 1000.0)
            rings.append(ring)

        def sky_color(p, n):
            el = p.z / 1000.0
            if el < 0.0:
                return GROUND_HAZE + (1.0,)
            t = smoothstep(0.0, 0.75, el) ** 0.8
            return _mix(HORIZON, ZENITH, t) + (1.0,)
        mb.loft(rings, sky_color)
        sky = mb.build("sky")
        sky.reparentTo(base.camera)
        sky.setCompass()
        sky.setTwoSided(True)
        sky.setBin("background", 0)
        sky.setDepthWrite(False)
        sky.setDepthTest(False)
        sky.setLightOff(1)
        sky.setFogOff(1)
        # sun disc
        cm = CardMaker("sun")
        cm.setFrame(-1, 1, -1, 1)
        sun = sky.attachNewNode(cm.generate())
        d = Vec3(SUN_DIR)
        d.normalize()
        sun.setPos(d * 900.0)
        sun.setScale(60.0)
        sun.setBillboardPointEye()
        sun.setTexture(soft_texture(64, power=2.5, name="sun"))
        sun.setTransparency(TransparencyAttrib.MAlpha)
        sun.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                            ColorBlendAttrib.OOne))
        sun.setColor(1.0, 0.95, 0.8, 1.0)
        return sky

    # --------------------------------------------------------------- clouds
    def _clouds(self, terrain, count, seed):
        rnd = random.Random(seed)
        root = self.root.attachNewNode("clouds")
        root.setLightOff(1)
        root.setDepthWrite(False)
        root.setTransparency(TransparencyAttrib.MAlpha)
        root.setBin("transparent", 0)
        root.setTexture(puffy_texture())
        cm = CardMaker("cloud")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        card = cm.generate()
        lim = terrain.half * 0.95
        for _ in range(count):
            cx = rnd.uniform(-lim, lim)
            cy = rnd.uniform(-lim, lim)
            cz = rnd.uniform(2600.0, 3600.0)
            size = rnd.uniform(500.0, 1100.0)
            for _ in range(rnd.randint(4, 8)):
                puff = root.attachNewNode(card.copySubgraph())
                puff.setPos(cx + rnd.uniform(-1, 1) * size * 0.8, cy + rnd.uniform(-1, 1) * size * 0.8,
                            cz + rnd.uniform(-0.15, 0.25) * size)
                puff.setScale(size * rnd.uniform(0.8, 1.4))
                puff.setBillboardPointEye()
                shade = rnd.uniform(0.9, 1.0)
                puff.setColorScale(shade, shade, shade, rnd.uniform(0.75, 0.95))
        return root
