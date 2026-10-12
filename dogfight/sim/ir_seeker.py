"""Infrared seeker head (AIM-9M), used on the rail and inside the missile.

Works like the War Thunder Sidewinder:

* **Caged** - the seeker looks along the boresight (or where the radar
  points it when a radar lock exists).  The growl gets a high pitch when a
  heat source is inside the small seeker FOV and close enough.
* **Locked** - the pilot pressed lock: the head now tracks that heat source
  on its own up to the gimbal limit with a limited tracking rate.
* Each flare that appears close to the tracked target gets one chance to
  steal the lock; IRCCM (``spec.ccm``) is the probability to ignore it.
"""

from ..mathutil import DEG, angle_between, rotate_towards, safe_normalized
from .signatures import ir_intensity, ir_lock_range


class IRSeeker:
    def __init__(self, spec, rng):
        self.spec = spec
        self.rng = rng
        self.axis = None             # world unit vector the head looks along
        self.target = None           # tracked heat source (aircraft or flare)
        self.candidate = None        # best source inside the caged FOV (lock tone)
        self._judged_flares = set()

    @property
    def locked(self):
        return self.target is not None

    def reset(self):
        self.target = None
        self.candidate = None
        self._judged_flares.clear()

    # ----------------------------------------------------------------- checks
    def visible(self, source, origin, terrain):
        if not source.alive:
            return False
        dist = (source.pos - origin).length()
        rng = ir_lock_range(self.spec.seeker_range, ir_intensity(source, origin))
        if dist > rng:
            return False
        return terrain is None or terrain.line_of_sight(origin, source.pos)

    def best_in_cone(self, origin, axis, sources, half_angle, terrain, exclude=None):
        best = None
        best_score = 0.0
        for src in sources:
            if src is exclude or not src.alive:
                continue
            to_src = src.pos - origin
            dist = to_src.length()
            if dist < 1.0:
                continue
            off = angle_between(axis, to_src)
            if off > half_angle:
                continue
            intensity = ir_intensity(src, origin)
            if dist > ir_lock_range(self.spec.seeker_range, intensity):
                continue
            score = intensity / (dist * dist) * (1.0 - 0.5 * off / half_angle)
            if score > best_score and (terrain is None or terrain.line_of_sight(origin, src.pos)):
                best = src
                best_score = score
        return best

    # ----------------------------------------------------------------- update
    def update(self, dt, origin, boresight, sources, terrain, slave_dir=None, exclude=None):
        """Advance the seeker one tick.

        ``boresight``: launcher nose / missile body axis (gimbal reference).
        ``slave_dir``: optional direction the caged head is pointed to (radar).
        Returns ``"lost"`` when an existing lock was broken this tick.
        """
        spec = self.spec
        fov = spec.seeker_fov * DEG
        if self.axis is None:
            self.axis = safe_normalized(boresight)

        if self.target is None:
            want = slave_dir if slave_dir is not None else boresight
            if angle_between(boresight, want) > spec.gimbal_limit * DEG:
                want = boresight
            self.axis = safe_normalized(want)
            self.candidate = self.best_in_cone(origin, self.axis, sources, fov, terrain, exclude)
            return None

        tgt = self.target
        to_tgt = tgt.pos - origin
        desired = safe_normalized(to_tgt)
        self.axis = rotate_towards(self.axis, desired, spec.track_rate * DEG * dt)
        self.candidate = tgt
        if (not self.visible(tgt, origin, terrain)
                or angle_between(self.axis, desired) > fov * 1.6
                or angle_between(boresight, self.axis) > spec.gimbal_limit * DEG):
            self.target = None
            self.candidate = None
            return "lost"

        # Decoys: each new flare near the target gets one roll of the dice.
        tgt_heat = ir_intensity(tgt, origin)
        for src in sources:
            if not getattr(src, "is_flare", False) or src is tgt or src.id in self._judged_flares:
                continue
            if angle_between(self.axis, src.pos - origin) > fov * 2.0:
                continue
            if src.intensity < 0.6 * tgt_heat:
                continue          # still igniting / too weak - judge it later
            self._judged_flares.add(src.id)
            if self.rng.random() > spec.ccm:
                self.target = src
                return "decoyed"
        return None

    def lock(self):
        """Pilot pressed lock: start tracking the current candidate."""
        if self.candidate is not None:
            self.target = self.candidate
            return True
        return False

    def unlock(self):
        self.target = None

    def angle_off(self, boresight):
        return angle_between(boresight, self.axis) if self.axis is not None else 0.0

    def tone(self):
        """'none' | 'growl' (searching) | 'lock' (high pitch: target in FOV or tracked)."""
        if self.target is not None or self.candidate is not None:
            return "lock"
        return "growl"
