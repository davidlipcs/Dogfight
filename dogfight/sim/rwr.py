"""Radar warning receiver.

Lists every radar emitter that illuminates the owner and how dangerous it is:
``search`` (being scanned), ``lock`` (STT on us), ``launch`` (a radar guided
missile is being guided onto us - datalink or its own active seeker).
"""

import math

from ..mathutil import to_local
from .specs import ARH

LEVELS = {"search": 1, "lock": 2, "launch": 3}


class Threat:
    __slots__ = ("source", "symbol", "level", "bearing", "distance")

    def __init__(self, source, symbol, level, bearing, distance):
        self.source = source
        self.symbol = symbol
        self.level = level
        self.bearing = bearing        # rad, relative to the nose (+ = right)
        self.distance = distance


class RWR:
    def __init__(self, owner):
        self.owner = owner
        self.threats = []
        self.new_search = False       # a new emitter appeared this update (beep)
        self.incoming = []            # (distance, missile) of every missile flying at the player
        self._known = set()

    @property
    def max_level(self):
        return max((LEVELS[t.level] for t in self.threats), default=0)

    def _bearing(self, pos):
        local = to_local(self.owner.quat, pos - self.owner.pos)
        return math.atan2(local.x, local.y)

    def update(self, world):
        owner = self.owner
        found = {}
        for ac in world.aircraft:
            if ac is owner or not ac.alive or not ac.radar.on:
                continue
            level = ac.radar.is_painting(owner)
            if level is None:
                continue
            found[ac] = Threat(ac, ac.spec.radar.rwr_symbol, level, self._bearing(ac.pos),
                               (ac.pos - owner.pos).length())
        for m in world.missiles:
            if not m.alive or m.spec.guidance != ARH or m.guided_target is not owner:
                continue
            if m.active:
                found[m] = Threat(m, "M", "launch", self._bearing(m.pos), (m.pos - owner.pos).length())
            elif m.datalink and m.shooter in found:
                found[m.shooter].level = "launch"
        # missile approach warning (player only): every missile flying at us, IR ones included
        self.incoming = []
        if owner.is_player:
            for m in world.missiles:
                if not m.alive or m.shooter is None or m.shooter.team == owner.team:
                    continue
                if m.guided_target is not owner and m.intended is not owner:
                    continue
                dist = (m.pos - owner.pos).length()
                if dist > 15000.0:
                    continue
                self.incoming.append((dist, m))
                if m not in found:
                    found[m] = Threat(m, "M", "launch", self._bearing(m.pos), dist)
            self.incoming.sort(key=lambda e: e[0])
        self.threats = sorted(found.values(), key=lambda t: -LEVELS[t.level])
        keys = set(found)
        self.new_search = bool(keys - self._known)
        self._known = keys
