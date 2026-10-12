"""Flares (IR decoys) and chaff (radar decoys)."""

import itertools

from panda3d.core import Vec3

from ..mathutil import G

_ids = itertools.count(1)


class Flare:
    is_flare = True
    alive = True

    def __init__(self, pos, vel, spec):
        self.id = next(_ids)
        self.pos = Vec3(pos)
        self.vel = Vec3(vel)
        self.age = 0.0
        self.life = spec.flare_life
        self.peak = spec.flare_intensity

    @property
    def intensity(self):
        # Ignites in 0.15 s, then burns down.
        if self.age < 0.15:
            return self.peak * self.age / 0.15
        return self.peak * max(0.0, 1.0 - (self.age - 0.15) / (self.life - 0.15)) ** 0.7

    def update(self, dt):
        self.age += dt
        speed = self.vel.length()
        self.vel -= self.vel * min(1.0, 0.0025 * speed * dt)
        self.vel.z -= G * dt
        self.pos += self.vel * dt
        if self.age >= self.life:
            self.alive = False


class Chaff:
    is_chaff = True
    alive = True

    def __init__(self, pos, vel, spec):
        self.id = next(_ids)
        self.pos = Vec3(pos)
        # Chaff stops almost instantly in the air stream - that is why a
        # pulse-doppler radar can reject it unless the target is notching.
        self.vel = Vec3(vel) * 0.3
        self.age = 0.0
        self.life = spec.chaff_life

    def update(self, dt):
        self.age += dt
        self.vel -= self.vel * min(1.0, 3.0 * dt)
        self.vel.z -= 1.5 * dt
        self.pos += self.vel * dt
        if self.age >= self.life:
            self.alive = False
