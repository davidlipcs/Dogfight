"""An aircraft = flight model + weapons + sensors + damage state."""

import math
import random

from panda3d.core import Vec3

from ..mathutil import DEG, quat_look, safe_normalized
from .countermeasures import Chaff, Flare
from .flight_model import Controls, FlightModel
from .guns import Gun
from .ir_seeker import IRSeeker
from .missile import Missile
from .radar import STT, Radar
from .rwr import RWR
from .specs import AIM9M, FIRING_ORDER, IR, MISSILES

STORE_CD = 0.0011          # drag coefficient added per missile on a pylon
ASSIST_IR_FOV = 10.0       # player lock assist: AIM-9 search cone (deg) ...
ASSIST_IR_CONE = 30.0      # ... and the cone the F key searches when nothing is in the seeker


class Station:
    __slots__ = ("number", "key", "spec", "mount", "loaded", "reload")

    def __init__(self, number, key, mount):
        self.number = number
        self.key = key
        self.spec = MISSILES[key]
        self.mount = Vec3(*mount)
        self.loaded = True
        self.reload = None            # arcade mode: seconds until this rail is reloaded


class Aircraft:
    def __init__(self, spec, name, team, pos, heading_deg, speed, loadout="default",
                 rng=None, is_player=False, livery="viper", lock_assist=False):
        self.spec = spec
        self.name = name
        self.team = team
        self.is_player = is_player
        self.livery = livery
        self.rng = rng or random.Random()
        h = heading_deg * DEG
        fwd = Vec3(math.sin(h), math.cos(h), 0.0)
        self.fm = FlightModel(spec, Vec3(pos), fwd * speed, quat_look(fwd))
        self.fm.engine = 0.9
        self.controls = Controls(throttle=0.9)
        self.trigger = False
        self.gun = Gun(spec.gun, self.rng)
        self.loadout = loadout
        self.stations = []
        self.selected = None
        self.radar = Radar(spec.radar, self, self.rng)
        self.ir_seeker = IRSeeker(AIM9M, self.rng)
        self.rwr = RWR(self)
        self.flares = spec.countermeasures.flares
        self.chaff = spec.countermeasures.chaff
        self.cm_hold = False
        self._cm_timer = 0.0
        self.hp = spec.hp
        self.alive = True
        self.burning = False
        self.crashed = False
        self.death_time = None
        self.kills = 0
        self.last_attacker = None
        self.last_hit_time = -1e9
        self.pilot = None
        self.lock_assist = lock_assist
        self._ir_auto_hold = 0.0
        self.rearm()

    # ----------------------------------------------------------------- state
    @property
    def pos(self):
        return self.fm.pos

    @property
    def vel(self):
        return self.fm.vel

    @property
    def quat(self):
        return self.fm.quat

    @property
    def forward(self):
        return self.fm.quat.getForward()

    @property
    def speed(self):
        return self.fm.vel.length()

    @property
    def mach(self):
        return self.fm.mach

    @property
    def engine_setting(self):
        return self.fm.engine if self.alive else 0.0

    @property
    def damaged(self):
        return self.hp < self.spec.hp * 0.5

    def rearm(self):
        layout = self.spec.loadouts.get(self.loadout, self.spec.loadouts["default"])
        self.stations = [Station(n, key, self.spec.stations[n]) for n, key in sorted(layout.items())]
        self.gun.reload()
        self.flares = self.spec.countermeasures.flares
        self.chaff = self.spec.countermeasures.chaff
        if self.selected is None or self.missile_count(self.selected) == 0:
            self.selected = next((s.key for s in self.stations), None)
        self._update_stores()

    def _update_stores(self):
        loaded = [s for s in self.stations if s.loaded]
        self.fm.store_mass = sum(s.spec.mass for s in loaded)
        self.fm.store_cd = STORE_CD * len(loaded)

    def missile_count(self, key):
        return sum(1 for s in self.stations if s.loaded and s.key == key)

    def weapon_keys(self):
        keys = []
        for s in self.stations:
            if s.key not in keys:
                keys.append(s.key)
        return keys

    @property
    def selected_spec(self):
        return MISSILES.get(self.selected)

    def select(self, key):
        if key in self.weapon_keys():
            self.selected = key
            self.ir_seeker.reset()
            return True
        return False

    def cycle_weapon(self):
        keys = self.weapon_keys()
        if keys:
            i = keys.index(self.selected) if self.selected in keys else -1
            self.select(keys[(i + 1) % len(keys)])

    # ---------------------------------------------------------- simulation
    def physics_step(self, dt, world):
        if self.crashed:
            return
        if self.alive:
            self.fm.step(dt, self.controls, world.terrain)
            event = self.fm.contact_event
            if event == "crash":
                self.crash(world, self.fm.crash_reason)
                return
            if event == "tailstrike":
                world.emit("message", to=self, text="FAROKÜTÉS!", level="bad")
                self.take_damage(30.0, None, "tailstrike", world)
            elif event == "touchdown" and self.fm.sink_rate > 3.0:
                world.emit("message", to=self, text="KEMÉNY LANDOLÁS", level="warn")
            self.gun.update(dt, self, self.trigger, world)
            self._cm_timer -= dt
            if self.cm_hold:
                self.dispense(world)
        else:
            # uncontrolled wreck: corkscrews nose down
            wreck = Controls(throttle=0.0)
            wreck.pitch = -0.3
            wreck.roll = 0.9
            self.fm.step(dt, wreck)
            self.gun.firing = False
            if self.pos.z <= world.terrain.height(self.pos.x, self.pos.y) + 1.5:
                self.crash(world)

    @property
    def on_ground(self):
        return self.fm.on_ground

    def toggle_gear(self):
        return self.fm.set_gear(not self.fm.gear_down)

    def sensor_step(self, dt, world):
        if not self.alive:
            return
        radar = self.radar
        radar.update(dt, world)
        if radar.last_event == "locked":
            world.emit("message", to=self, text="RADAR LOCK", level="good")
        elif radar.last_event == "lost":
            world.emit("message", to=self, text="LOCK LOST", level="warn")
        elif radar.last_event == "decoyed":
            world.emit("message", to=self, text="LOCK LOST - CHAFF", level="warn")

        spec = self.selected_spec
        if spec is not None and spec.guidance == IR:
            if self.ir_seeker.spec is not spec:
                self.ir_seeker = IRSeeker(spec, self.rng)
            self.ir_seeker.acq_fov = ASSIST_IR_FOV if self.lock_assist else None
            slave = None
            if radar.mode == STT and radar.track_pos is not None:
                slave = safe_normalized(radar.track_pos - self.pos)
            result = self.ir_seeker.update(dt, self.pos, self.forward, world.heat_sources(),
                                           world.terrain, slave_dir=slave, exclude=self)
            if result == "lost":
                world.emit("message", to=self, text="SEEKER LOST", level="warn")
            elif result == "decoyed":
                world.emit("message", to=self, text="SEEKER ON FLARE", level="warn")
            # With a radar lock the seeker is slaved and locks on by itself.
            if slave is not None and not self.ir_seeker.locked and self.ir_seeker.candidate is radar.locked:
                self.ir_seeker.lock()
            # lock assist: the seeker locks by itself onto an enemy in its (wide) search cone
            self._ir_auto_hold -= dt
            cand = self.ir_seeker.candidate
            if (self.lock_assist and self._ir_auto_hold <= 0.0 and not self.ir_seeker.locked and cand is not None
                    and not getattr(cand, "is_flare", False) and getattr(cand, "team", self.team) != self.team):
                self.ir_seeker.lock()
                world.emit("message", to=self, text="SEEKER LOCK - Space: indítás", level="good")
        self.rwr.update(world)

    # ------------------------------------------------------------ weapons
    def toggle_ir_lock(self, world=None):
        spec = self.selected_spec
        if spec is None or spec.guidance != IR:
            return False
        if self.ir_seeker.locked:
            self.ir_seeker.unlock()
            self._ir_auto_hold = 3.0
            return False
        if self.lock_assist and world is not None and self.ir_seeker.candidate is None:
            # nothing in the seeker: take the hottest enemy within a wide cone around the nose
            src = self.ir_seeker.best_in_cone(self.pos, self.forward, world.heat_sources(), ASSIST_IR_CONE * DEG,
                                              world.terrain, exclude=self)
            if src is not None and not getattr(src, "is_flare", False) and getattr(src, "team", None) != self.team:
                self.ir_seeker.candidate = src
        return self.ir_seeker.lock()

    def fire_missile(self, world):
        if not self.alive or self.selected is None:
            return None
        by_number = {s.number: s for s in self.stations}
        station = next((by_number[n] for n in FIRING_ORDER
                        if n in by_number and by_number[n].loaded and by_number[n].key == self.selected), None)
        if station is None:
            world.emit("message", to=self, text="NO %s LEFT" % self.selected, level="warn")
            return None
        spec = station.spec
        quat = self.quat
        pos = self.pos + quat.xform(station.mount)
        vel = Vec3(self.vel) - quat.getUp() * (0.0 if abs(station.mount.x) > 4.5 else 4.0)
        if spec.guidance == IR:
            target = self.ir_seeker.target
            axis = self.ir_seeker.axis
        else:
            target = self.radar.locked if self.radar.mode == STT else None
            axis = None
        missile = Missile(spec, self, pos, vel, self.forward, self.rng, target=target, ir_axis=axis)
        station.loaded = False
        self._update_stores()
        if spec.guidance == IR:
            self.ir_seeker.reset()
        world.add_missile(missile)
        if self.missile_count(self.selected) == 0:
            # auto select the other missile type when this one runs out
            for key in self.weapon_keys():
                if self.missile_count(key) > 0:
                    self.select(key)
                    break
        return missile

    def dispense(self, world):
        if self._cm_timer > 0.0 or (self.flares <= 0 and self.chaff <= 0):
            return
        self._cm_timer = self.spec.countermeasures.interval
        down = -self.quat.getUp()
        if self.flares > 0:
            self.flares -= 1
            side = self.quat.getRight() * self.rng.uniform(-12.0, 12.0)
            flare = Flare(self.pos + down * 1.5, self.vel * 0.96 + down * 22.0 + side, self.spec.countermeasures)
            world.add_flare(flare)
        if self.chaff > 0:
            self.chaff -= 1
            world.add_chaff(Chaff(self.pos + down * 1.5, self.vel, self.spec.countermeasures))

    # ------------------------------------------------------------- damage
    def take_damage(self, amount, source, weapon, world):
        if not self.alive:
            return
        self.hp -= amount
        self.last_attacker = source
        self.last_hit_time = world.time
        if self.hp < self.spec.hp * 0.3:
            self.burning = True
        if self.hp <= 0.0:
            self.kill(world, source, weapon)

    def kill(self, world, killer, weapon):
        if not self.alive:
            return
        self.alive = False
        self.burning = True
        self.hp = 0.0
        self.trigger = False
        self.cm_hold = False
        self.death_time = world.time
        if self.radar.on:
            self.radar.toggle_power()
        if killer is not None and killer is not self:
            killer.kills += 1
        world.emit("kill", victim=self, killer=killer, weapon=weapon)

    def crash(self, world, reason=""):
        if self.crashed:
            return
        if self.alive:
            recent = self.last_attacker if world.time - self.last_hit_time < 30.0 else None
            if reason:
                world.emit("message", to=self, text="BALESET: " + reason, level="bad")
            self.kill(world, recent, "crash")
        self.crashed = True
        self.fm.vel = Vec3(0, 0, 0)
        world.emit("explosion", pos=Vec3(self.pos), size=2.5, ground=True)
