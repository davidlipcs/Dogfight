"""Billboard sprite particles (smoke, fire, flares, vapour) and procedural textures."""

import math
import random

from panda3d.core import (CardMaker, ColorBlendAttrib, PNMImage, SamplerState, Texture, TransparencyAttrib, Vec3)


def soft_texture(size=64, power=1.6, name="soft"):
    """Round blob with a soft alpha falloff (used for smoke, clouds, glows)."""
    img = PNMImage(size, size, 4)
    c = (size - 1) * 0.5
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            a = max(0.0, 1.0 - d) ** power
            img.setXelA(x, y, 1.0, 1.0, 1.0, a)
    tex = Texture(name)
    tex.load(img)
    tex.setWrapU(SamplerState.WM_clamp)
    tex.setWrapV(SamplerState.WM_clamp)
    tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
    tex.setMagfilter(SamplerState.FT_linear)
    return tex


def puffy_texture(size=64, name="puffy", seed=3):
    """Lumpy cloud puff: several overlapping blobs."""
    rnd = random.Random(seed)
    img = PNMImage(size, size, 4)
    blobs = [(rnd.uniform(0.3, 0.7), rnd.uniform(0.3, 0.7), rnd.uniform(0.18, 0.32)) for _ in range(7)]
    for y in range(size):
        for x in range(size):
            u = x / (size - 1)
            v = y / (size - 1)
            a = 0.0
            for bx, by, br in blobs:
                d = math.hypot(u - bx, v - by) / br
                a = max(a, max(0.0, 1.0 - d * d))
            edge = max(0.0, 1.0 - math.hypot(u - 0.5, v - 0.5) * 2.0)
            a = min(1.0, a * 1.2) * min(1.0, edge * 2.5)
            shade = 0.82 + 0.18 * v          # slightly darker bottom
            img.setXelA(x, y, shade, shade, shade, a)
    tex = Texture(name)
    tex.load(img)
    tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
    tex.setMagfilter(SamplerState.FT_linear)
    return tex


class _Sprite:
    __slots__ = ("np", "pos", "vel", "age", "life", "s0", "s1", "c0", "c1", "drag", "rise")


class SpriteSystem:
    """A pool of camera facing cards with simple per-particle motion and fades."""

    def __init__(self, parent, texture, additive=False, max_count=800, sort=10, name="sprites"):
        self.root = parent.attachNewNode(name)
        self.root.setLightOff(1)
        self.root.setDepthWrite(False)
        self.root.setTexture(texture)
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        if additive:
            self.root.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                                      ColorBlendAttrib.OOne))
            self.root.setBin("fixed", sort)
        else:
            self.root.setBin("transparent", sort)
        cm = CardMaker("card")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        self.card = cm.generate()
        self.max_count = max_count
        self.active = []
        self.free = []

    def spawn(self, pos, vel=None, life=1.0, size=(1.0, 2.0), color=((1, 1, 1, 1), (1, 1, 1, 0)), drag=0.0, rise=0.0):
        if len(self.active) >= self.max_count:
            sprite = self.active.pop(0)
        elif self.free:
            sprite = self.free.pop()
            sprite.np.show()
        else:
            sprite = _Sprite()
            sprite.np = self.root.attachNewNode(self.card.copySubgraph())
            sprite.np.setBillboardPointEye()
        sprite.pos = Vec3(pos)
        sprite.vel = Vec3(vel) if vel is not None else Vec3(0, 0, 0)
        sprite.age = 0.0
        sprite.life = life
        sprite.s0, sprite.s1 = size
        sprite.c0, sprite.c1 = color
        sprite.drag = drag
        sprite.rise = rise
        sprite.np.setPos(sprite.pos)
        sprite.np.setScale(sprite.s0)
        sprite.np.setColorScale(*sprite.c0)
        self.active.append(sprite)

    def update(self, dt):
        alive = []
        for s in self.active:
            s.age += dt
            t = s.age / s.life
            if t >= 1.0:
                s.np.hide()
                self.free.append(s)
                continue
            if s.drag:
                s.vel *= max(0.0, 1.0 - s.drag * dt)
            if s.rise:
                s.vel.z += s.rise * dt
            s.pos += s.vel * dt
            s.np.setPos(s.pos)
            s.np.setScale(s.s0 + (s.s1 - s.s0) * t)
            c0, c1 = s.c0, s.c1
            s.np.setColorScale(c0[0] + (c1[0] - c0[0]) * t, c0[1] + (c1[1] - c0[1]) * t,
                               c0[2] + (c1[2] - c0[2]) * t, c0[3] + (c1[3] - c0[3]) * t)
            alive.append(s)
        self.active = alive

    def clear(self):
        for s in self.active:
            s.np.hide()
            self.free.append(s)
        self.active = []
