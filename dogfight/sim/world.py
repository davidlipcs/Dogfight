"""The simulation world: owns every object and runs the fixed-step loop.

Rendering, audio and the HUD never change the simulation directly; they read
the state and consume the ``events`` queue (launches, explosions, kills ...).
"""

import random

from panda3d.core import Vec3

from .guns import update_bullets

PHYS_DT = 1.0 / 100.0      # flight models and missiles
SENSOR_DT = 1.0 / 30.0     # radars, seekers, RWR
AI_DT = 1.0 / 10.0         # AI decision making
WRECK_LINGER = 8.0         # s a crashed AI wreck stays in the list


class World:
    def __init__(self, terrain, seed=None):
        self.terrain = terrain
        self.rng = random.Random(seed)
        self.aircraft = []
        self.missiles = []
        self.bullets = []
        self.flares = []
        self.chaff = []
        self.events = []
        self.time = 0.0
        self._acc = 0.0
        self._sensor_acc = 0.0
        self._ai_acc = 0.0

    # ---------------------------------------------------------------- events
    def emit(self, kind, **data):
        self.events.append((kind, data))

    def drain_events(self):
        events = self.events
        self.events = []
        return events

    # ---------------------------------------------------------------- objects
    def add_aircraft(self, aircraft):
        self.aircraft.append(aircraft)
        return aircraft

    def add_missile(self, missile):
        self.missiles.append(missile)
        self.emit("launch", missile=missile, shooter=missile.shooter)

    def add_flare(self, flare):
        self.flares.append(flare)
        self.emit("flare", flare=flare)

    def add_chaff(self, chaff):
        self.chaff.append(chaff)
        self.emit("chaff", chaff=chaff)

    def heat_sources(self):
        return [a for a in self.aircraft if a.alive or (a.burning and not a.crashed)] + self.flares

    def enemies_of(self, aircraft):
        return [a for a in self.aircraft if a.team != aircraft.team and a.alive]

    # ------------------------------------------------------------------ loop
    def update(self, frame_dt):
        frame_dt = min(frame_dt, 0.1)
        self._acc += frame_dt
        steps = 0
        while self._acc >= PHYS_DT:
            self._physics(PHYS_DT)
            self._acc -= PHYS_DT
            steps += 1
            if steps >= 12:
                self._acc = 0.0
                break
        update_bullets(self, frame_dt)
        self._cleanup()

    def _physics(self, dt):
        self.time += dt
        for ac in self.aircraft:
            if ac.pilot is not None and ac.alive:
                ac.pilot.fly(dt, self)
        for ac in self.aircraft:
            ac.physics_step(dt, self)
        for m in self.missiles:
            m.update(dt, self)
        for f in self.flares:
            f.update(dt)
        for c in self.chaff:
            c.update(dt)

        self._sensor_acc += dt
        if self._sensor_acc >= SENSOR_DT:
            for ac in self.aircraft:
                ac.sensor_step(self._sensor_acc, self)
            self._sensor_acc = 0.0
        self._ai_acc += dt
        if self._ai_acc >= AI_DT:
            for ac in self.aircraft:
                if ac.pilot is not None and ac.alive:
                    ac.pilot.think(self)
            self._ai_acc = 0.0

    def _cleanup(self):
        self.missiles = [m for m in self.missiles if m.alive]
        self.flares = [f for f in self.flares if f.alive]
        self.chaff = [c for c in self.chaff if c.alive]
        self.aircraft = [a for a in self.aircraft
                         if a.is_player or not a.crashed or self.time - a.death_time < WRECK_LINGER]

    # ---------------------------------------------------------------- damage
    def detonate(self, missile, pos, ground=False, self_destruct=False):
        if not missile.alive:
            return
        missile.alive = False
        spec = missile.spec
        name = spec.name.split()[0]
        for ac in self.aircraft:
            if not ac.alive:
                continue
            dist = (ac.pos - pos).length()
            if dist >= spec.damage_radius:
                continue
            if dist <= spec.lethal_radius:
                dmg = spec.damage
            else:
                dmg = spec.damage * (1.0 - (dist - spec.lethal_radius) / (spec.damage_radius - spec.lethal_radius))
            self.emit("hit", target=ac, pos=Vec3(ac.pos), shooter=missile.shooter)
            ac.take_damage(dmg, missile.shooter, name, self)
        size = 1.6 if spec.damage >= 150 else 1.2
        self.emit("explosion", pos=Vec3(pos), size=size if not self_destruct else 0.8,
                  ground=ground, missile=missile)
