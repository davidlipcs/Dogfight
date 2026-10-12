"""Pulse-doppler fire control radar (AN/APG-68 style).

Modes (as in War Thunder):

* ``SEARCH`` - the beam sweeps +-60 deg in azimuth; every target the beam
  paints shows up as a contact on the B-scope for a few seconds.
* ``ACM``    - close range auto acquisition: a narrow vertical window in
  front of the nose; the first target found there is locked automatically.
* ``STT``    - single target track (lock).  Gives range / closure / target
  velocity for the gun lead indicator, slaves the AIM-9 seeker and feeds the
  AIM-120 datalink.

A pulse-doppler radar filters out everything that has (almost) no radial
velocity - ground clutter and chaff.  A target that flies perpendicular to
the beam ("beaming" / "notching") falls into that filter and disappears.
Chaff only works against a lock when the target is close to the notch.
"""

import math

from panda3d.core import Vec3

from ..mathutil import DEG, angle_between, smoothstep, to_local
from .signatures import radar_detection_range, radial_speed, rcs

OFF, SEARCH, ACM, STT = "OFF", "SRCH", "ACM", "STT"


class Contact:
    __slots__ = ("target", "pos", "vel", "time", "range", "az", "el")

    def __init__(self, target, pos, vel, time, rng, az, el):
        self.target = target
        self.pos = pos
        self.vel = vel
        self.time = time
        self.range = rng
        self.az = az
        self.el = el


class Radar:
    def __init__(self, spec, owner, rng):
        self.spec = spec
        self.owner = owner
        self.rng = rng
        self.mode = SEARCH
        self.beam_az = -spec.scan_az * DEG
        self.beam_dir = 1.0
        self.contacts = {}           # target -> Contact
        self.selected = None         # target picked on the scope (SEARCH)
        self.locked = None           # STT target
        self.pending = None          # target being acquired
        self.pending_time = 0.0
        self.lost_time = 0.0
        self.track_pos = None
        self.track_vel = None
        self.notched = False         # current STT target is in the doppler notch
        self._judged_chaff = set()
        self.last_event = None       # "locked" | "lost" | "decoyed" (consumed by Aircraft)

    # ------------------------------------------------------------- geometry
    def angles_to(self, pos):
        """(az, el, range) of a world position in the owner's body frame."""
        rel = pos - self.owner.pos
        local = to_local(self.owner.quat, rel)
        az = math.atan2(local.x, local.y)
        el = math.atan2(local.z, math.hypot(local.x, local.y))
        return az, el, rel.length()

    def in_notch(self, target):
        vr = radial_speed(target.vel, self.owner.pos, target.pos)
        return abs(vr) < self.spec.notch_speed

    def can_detect(self, target, world, max_range):
        if target is self.owner or not target.alive:
            return False
        dist = (target.pos - self.owner.pos).length()
        if dist > max_range:
            return False
        if dist > radar_detection_range(self.spec.search_range, rcs(target, self.owner.pos)):
            return False
        if self.in_notch(target):
            return False
        return world.terrain.line_of_sight(self.owner.pos, target.pos)

    @property
    def on(self):
        return self.mode != OFF

    # ------------------------------------------------------------- commands
    def toggle_power(self):
        if self.mode == OFF:
            self.mode = SEARCH
        else:
            self._drop_lock()
            self.mode = OFF
            self.contacts.clear()

    def set_acm(self):
        self._drop_lock()
        self.mode = ACM
        self.pending = None

    def set_search(self):
        self._drop_lock()
        self.mode = SEARCH

    def try_lock(self, target):
        """Start acquiring ``target`` (it must be inside the STT gimbal and lock range)."""
        if self.mode == OFF or target is None or not target.alive:
            return False
        az, el, dist = self.angles_to(target.pos)
        gimbal = self.spec.stt_gimbal * DEG
        if abs(az) > gimbal or abs(el) > gimbal or dist > self.spec.lock_range:
            return False
        self.pending = target
        self.pending_time = 0.0
        return True

    def lock_button(self):
        """War Thunder style lock key: lock / unlock / fall back to ACM."""
        if self.mode == OFF:
            self.mode = SEARCH
            return "on"
        if self.mode == STT:
            self.set_search()
            return "unlocked"
        if self.mode == SEARCH and self.selected in self.contacts:
            if self.try_lock(self.selected):
                return "locking"
        if self.mode == SEARCH:
            self.set_acm()
            return "acm"
        self.set_search()
        return "search"

    def cycle_target(self):
        """Select the next search contact (sorted by angle off the nose)."""
        if not self.contacts:
            self.selected = None
            return
        order = sorted(self.contacts.values(), key=lambda c: abs(c.az) + abs(c.el))
        targets = [c.target for c in order]
        if self.selected in targets:
            self.selected = targets[(targets.index(self.selected) + 1) % len(targets)]
        else:
            self.selected = targets[0]

    def _drop_lock(self):
        self.locked = None
        self.pending = None
        self.track_pos = None
        self.track_vel = None
        self.notched = False
        self.lost_time = 0.0

    # --------------------------------------------------------------- update
    def update(self, dt, world):
        self.last_event = None
        spec = self.spec
        if self.mode == OFF:
            return
        if self.mode == SEARCH:
            self._search(dt, world)
        elif self.mode == ACM:
            self._acm(dt, world)
        if self.mode == STT:
            self._track(dt, world)
        if self.pending is not None and self.mode != STT:
            self._acquire(dt, world)
        # expire old contacts
        frame = 2.0 * (2.0 * spec.scan_az / spec.scan_rate)
        for tgt in [t for t, c in self.contacts.items() if world.time - c.time > frame * 1.3 or not t.alive]:
            del self.contacts[tgt]
        if self.selected is not None and self.selected not in self.contacts and self.selected is not self.locked:
            self.selected = None

    def _search(self, dt, world):
        spec = self.spec
        limit = spec.scan_az * DEG
        old = self.beam_az
        self.beam_az += self.beam_dir * spec.scan_rate * DEG * dt
        if self.beam_az > limit or self.beam_az < -limit:
            self.beam_az = max(-limit, min(limit, self.beam_az))
            self.beam_dir = -self.beam_dir
        lo, hi = min(old, self.beam_az) - 2 * DEG, max(old, self.beam_az) + 2 * DEG
        for tgt in world.aircraft:
            if tgt is self.owner or not tgt.alive:
                continue
            az, el, dist = self.angles_to(tgt.pos)
            if not (lo <= az <= hi) or abs(el) > spec.scan_el * DEG:
                continue
            if self.can_detect(tgt, world, spec.search_range * 1.3):
                self.contacts[tgt] = Contact(tgt, Vec3(tgt.pos), Vec3(tgt.vel), world.time, dist, az, el)
        if self.selected is None and self.contacts:
            self.cycle_target()

    def _acm(self, dt, world):
        spec = self.spec
        best = None
        best_dist = spec.acm_range
        for tgt in world.aircraft:
            if tgt is self.owner or not tgt.alive:
                continue
            az, el, dist = self.angles_to(tgt.pos)
            if abs(az) > spec.acm_az * DEG or not (spec.acm_el_low * DEG <= el <= spec.acm_el_high * DEG):
                continue
            if dist < best_dist and self.can_detect(tgt, world, spec.acm_range):
                best = tgt
                best_dist = dist
        if best is not None and self.pending is None:
            self.pending = best
            self.pending_time = spec.lock_time * 0.4   # ACM locks faster

    def _acquire(self, dt, world):
        tgt = self.pending
        az, el, dist = self.angles_to(tgt.pos)
        gimbal = self.spec.stt_gimbal * DEG
        if (abs(az) > gimbal or abs(el) > gimbal or dist > self.spec.lock_range
                or not self.can_detect(tgt, world, self.spec.lock_range)):
            self.pending = None
            return
        self.pending_time += dt
        if self.pending_time >= self.spec.lock_time:
            self.locked = tgt
            self.selected = tgt
            self.pending = None
            self.mode = STT
            self.lost_time = 0.0
            self.track_pos = Vec3(tgt.pos)
            self.track_vel = Vec3(tgt.vel)
            self._judged_chaff.clear()
            self.last_event = "locked"

    def _track(self, dt, world):
        tgt = self.locked
        spec = self.spec
        valid = tgt is not None and tgt.alive
        self.notched = False
        if valid:
            az, el, dist = self.angles_to(tgt.pos)
            gimbal = spec.stt_gimbal * DEG
            self.notched = self.in_notch(tgt)
            valid = (abs(az) <= gimbal and abs(el) <= gimbal and dist <= spec.lock_range * 1.25
                     and not self.notched
                     and dist <= radar_detection_range(spec.search_range, rcs(tgt, self.owner.pos)) * 1.2
                     and world.terrain.line_of_sight(self.owner.pos, tgt.pos))
        if valid and self._chaff_decoyed(tgt, world):
            self.last_event = "decoyed"
            self._drop_lock()
            self.mode = SEARCH
            return
        if valid:
            self.lost_time = 0.0
            self.track_pos = Vec3(tgt.pos)
            self.track_vel = Vec3(tgt.vel)
            self.contacts[tgt] = Contact(tgt, Vec3(tgt.pos), Vec3(tgt.vel), world.time, dist, az, el)
            return
        self.lost_time += dt
        if self.track_pos is not None:
            self.track_pos += self.track_vel * dt     # coast on the last track
        if self.lost_time > spec.track_memory:
            self.last_event = "lost"
            self._drop_lock()
            self.mode = SEARCH

    def _chaff_decoyed(self, tgt, world):
        if not world.chaff:
            return False
        los = tgt.pos - self.owner.pos
        dist = los.length()
        vr = abs(radial_speed(tgt.vel, self.owner.pos, tgt.pos))
        # Chaff hangs still in the air: only fools a PD radar near the notch.
        effectiveness = 0.55 * (1.0 - smoothstep(self.spec.notch_speed, 6.0 * self.spec.notch_speed, vr))
        for ch in world.chaff:
            if ch.id in self._judged_chaff or ch.age < 0.3:
                continue
            rel = ch.pos - self.owner.pos
            if abs(rel.length() - dist) > 600.0 or angle_between(rel, los) > 4.0 * DEG:
                continue
            self._judged_chaff.add(ch.id)
            if self.rng.random() < effectiveness:
                return True
        return False

    # --------------------------------------------------------------- queries
    def is_painting(self, target):
        """Used by the target's RWR: (level, source) or None."""
        if self.mode == STT and self.locked is target:
            return "lock"
        if self.mode in (SEARCH, ACM) and target in self.contacts:
            return "search"
        if self.pending is target:
            return "lock"
        return None
