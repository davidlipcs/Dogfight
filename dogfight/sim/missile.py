"""Guided missiles: AIM-9M (IR) and AIM-120A (active radar + datalink).

Flight: point mass with rocket motor phases, Mach dependent drag, induced
drag when manoeuvring and a G limit that also depends on dynamic pressure -
a slow missile can't turn, so energy matters just like in War Thunder.

Guidance: proportional navigation (``a = N * Vc * LOS-rate``).

AIM-120A sequence::

    launch --(radar lock: datalink updates)--> inertial midcourse
           --(<= seeker_range from target)--> PITBULL (own seeker active)

If the launching aircraft loses its lock before pitbull, the missile flies to
the last known position extrapolated with the last known velocity and then
searches with its own seeker there.  After pitbull it no longer needs the
launcher ("fire and forget").  Without any lock at launch it is a "maddog":
it flies straight and goes active right away.
"""

import itertools
import math

from panda3d.core import Vec3

from ..mathutil import DEG, G, angle_between, closest_approach, interp_table, safe_normalized, smoothstep
from .atmosphere import isa
from .ir_seeker import IRSeeker
from .radar import STT
from .signatures import radar_detection_range, radial_speed, rcs
from .specs import ARH, IR

_ids = itertools.count(1)


class Missile:
    def __init__(self, spec, shooter, pos, vel, direction, rng, target=None, ir_axis=None):
        self.id = next(_ids)
        self.spec = spec
        self.shooter = shooter
        self.rng = rng
        self.pos = Vec3(pos)
        self.vel = Vec3(vel)
        self.dir = safe_normalized(direction)
        self.mass = spec.mass
        self.age = 0.0
        self.alive = True
        self.thrust = 0.0
        self.status = "LAUNCH"       # shown on the HUD missile list
        self.lateral_g = 0.0
        self.closest = 1e9

        # IR seeker carried by the missile (starts with the rail seeker state)
        self.seeker = None
        if spec.guidance == IR:
            self.seeker = IRSeeker(spec, rng)
            self.seeker.axis = Vec3(ir_axis) if ir_axis is not None else Vec3(self.dir)
            self.seeker.target = target

        # Active radar missile state
        self.intended = target       # what the pilot fired at
        self.active = False          # pitbull
        self.datalink = False
        self.arh_target = None       # what the own seeker tracks (aircraft or chaff)
        self.est_pos = Vec3(target.pos) if target is not None else None
        self.est_vel = Vec3(target.vel) if target is not None else None
        self._judged_chaff = set()
        if spec.guidance == ARH and target is None:
            # Maddog: aim point far ahead, seeker goes active immediately.
            self.est_pos = self.pos + self.dir * spec.seeker_range * 0.8
            self.est_vel = Vec3(0, 0, 0)
            self.active = True

    # ---------------------------------------------------------------- props
    @property
    def guided_target(self):
        """The object the missile is currently homing on (for RWR / HUD)."""
        if self.spec.guidance == IR:
            return self.seeker.target if self.seeker else None
        if self.active:
            return self.arh_target
        return self.intended if self.datalink else None

    @property
    def burning(self):
        return self.age < self.spec.burn_time

    def _motor_thrust(self):
        t = self.age
        for duration, thrust in self.spec.motor:
            if t < duration:
                return thrust
            t -= duration
        return 0.0

    # --------------------------------------------------------------- update
    def update(self, dt, world):
        if not self.alive:
            return
        spec = self.spec
        self.age += dt
        rho, a_sound = isa(self.pos.z)
        speed = max(self.vel.length(), 1.0)
        vhat = self.vel / speed
        mach = speed / a_sound
        qbar = 0.5 * rho * speed * speed

        self.thrust = self._motor_thrust()
        if self.thrust > 0.0:
            self.mass -= spec.propellant / spec.burn_time * dt

        # ------------------------------------------------------- guidance
        acc_cmd = Vec3(0, 0, 0)
        if self.age >= max(spec.guidance_delay, spec.rail_time):
            aim = self._guidance(dt, world)
            if aim is not None:
                aim_pos, aim_vel = aim
                acc_cmd = self._pro_nav(aim_pos, aim_vel)
                acc_cmd += Vec3(0, 0, G)          # gravity compensation
        # only the component perpendicular to the flight path is achievable
        acc_cmd -= vhat * acc_cmd.dot(vhat)
        a_max = min(spec.max_g * G, qbar * spec.ref_area * spec.cn_max / self.mass)
        a_len = acc_cmd.length()
        if a_len > a_max:
            acc_cmd *= a_max / a_len
            a_len = a_max
        self.lateral_g = a_len / G

        drag = qbar * spec.ref_area * interp_table(spec.cd_table, mach) + a_len * self.mass * spec.induced_drag
        acc = vhat * ((self.thrust - drag) / self.mass) + acc_cmd + Vec3(0, 0, -G)
        new_vel = self.vel + acc * dt

        # --------------------------------------------------- proximity fuse
        if self.age > spec.arm_time:
            avg_vel = (self.vel + new_vel) * 0.5
            for ac in world.aircraft:
                if not ac.alive:
                    continue
                rel = ac.pos - self.pos
                if rel.length() > 400.0:
                    continue
                dist, t = closest_approach(rel, ac.vel - avg_vel, dt)
                if ac is self.guided_target or ac is self.intended:
                    self.closest = min(self.closest, dist)
                if dist <= spec.fuse_radius:
                    self.pos += avg_vel * t
                    world.detonate(self, self.pos)
                    return

        self.vel = new_vel
        self.pos += self.vel * dt
        if self.vel.length() > 1.0:
            self.dir = safe_normalized(self.vel)

        if self.pos.z <= world.terrain.height(self.pos.x, self.pos.y):
            world.detonate(self, self.pos, ground=True)
        elif self.age > spec.guidance_time:
            world.detonate(self, self.pos, self_destruct=True)
        elif not self.burning and speed < 160.0 and self.age > 3.0:
            self.status = "SLOW"
            if speed < 110.0:
                world.detonate(self, self.pos, self_destruct=True)

    # ------------------------------------------------------------- guidance
    def _pro_nav(self, aim_pos, aim_vel):
        r = aim_pos - self.pos
        dist2 = max(r.dot(r), 1.0)
        v_rel = aim_vel - self.vel
        omega = r.cross(v_rel) / dist2                 # line of sight rotation rate
        r_hat = r / math.sqrt(dist2)
        closing = -v_rel.dot(r_hat)
        vc = max(closing, 0.6 * self.vel.length(), 150.0)
        return omega.cross(r_hat) * (self.spec.nav_gain * vc)

    def _guidance(self, dt, world):
        if self.spec.guidance == IR:
            return self._guidance_ir(dt, world)
        return self._guidance_arh(dt, world)

    def _guidance_ir(self, dt, world):
        seeker = self.seeker
        sources = world.heat_sources()
        seeker.update(dt, self.pos, self.dir, sources, world.terrain, exclude=self.shooter)
        if not seeker.locked:
            # In flight the seeker is uncaged: it grabs whatever is in its FOV.
            seeker.lock()
        if not seeker.locked:
            self.status = "LOST"
            return None
        tgt = seeker.target
        self.status = "FLARE" if getattr(tgt, "is_flare", False) else "TRACK"
        return tgt.pos, tgt.vel

    def _guidance_arh(self, dt, world):
        spec = self.spec
        if not self.active:
            shooter = self.shooter
            radar = shooter.radar if shooter is not None and shooter.alive else None
            if (spec.datalink and radar is not None and radar.mode == STT
                    and radar.locked is self.intended and radar.track_pos is not None):
                self.est_pos = Vec3(radar.track_pos)
                self.est_vel = Vec3(radar.track_vel)
                self.datalink = True
                self.status = "DATALINK"
            else:
                self.datalink = False
                if self.est_pos is None:
                    return None
                self.est_pos += self.est_vel * dt
                self.status = "INERTIAL"
            if (self.est_pos - self.pos).length() <= spec.seeker_range:
                self.active = True
                self.datalink = False
                world.emit("pitbull", missile=self)
        if self.active:
            return self._active_seeker(dt, world)
        return self._loft(self.est_pos), self.est_vel

    def _loft(self, aim):
        """Climb above the target on long shots (lower drag up high)."""
        if not self.spec.loft:
            return aim
        dist = (aim - self.pos).length()
        angle = 22.0 * DEG * smoothstep(12000.0, 40000.0, dist)
        lifted = Vec3(aim)
        lifted.z += math.tan(angle) * dist * 0.5
        return lifted

    def _seeker_ok(self, tgt, world):
        spec = self.spec
        rel = tgt.pos - self.pos
        dist = rel.length()
        if angle_between(self.dir, rel) > spec.gimbal_limit * DEG:
            return False
        if getattr(tgt, "is_chaff", False):
            return dist < spec.seeker_range and tgt.alive
        if not tgt.alive or dist > radar_detection_range(spec.seeker_range, rcs(tgt, self.pos)):
            return False
        if abs(radial_speed(tgt.vel, self.pos, tgt.pos)) < 22.0:   # missile's own doppler notch
            return False
        return world.terrain.line_of_sight(self.pos, tgt.pos)

    def _active_seeker(self, dt, world):
        spec = self.spec
        tgt = self.arh_target
        if tgt is not None and not self._seeker_ok(tgt, world):
            tgt = self.arh_target = None
        if tgt is not None and not getattr(tgt, "is_chaff", False):
            # chaff near the target can steal the track if it is notching-ish
            vr = abs(radial_speed(tgt.vel, self.pos, tgt.pos))
            p = (1.0 - spec.ccm) * (1.0 - smoothstep(25.0, 150.0, vr))
            los = tgt.pos - self.pos
            for ch in world.chaff:
                if ch.id in self._judged_chaff or ch.age < 0.2:
                    continue
                if angle_between(ch.pos - self.pos, los) > 5.0 * DEG:
                    continue
                self._judged_chaff.add(ch.id)
                if self.rng.random() < p:
                    tgt = self.arh_target = ch
                    break
        if tgt is None:
            # search: look around the expected target position / flight path
            axis = (self.est_pos - self.pos) if self.est_pos is not None else self.dir
            best = None
            best_score = 1e18
            for ac in world.aircraft:
                if ac is self.shooter or not ac.alive:
                    continue
                rel = ac.pos - self.pos
                if angle_between(axis, rel) > spec.seeker_fov * DEG:
                    continue
                if not self._seeker_ok(ac, world):
                    continue
                score = rel.length() + (2000.0 if ac is not self.intended else 0.0)
                if self.est_pos is not None:
                    score += (ac.pos - self.est_pos).length()
                if score < best_score:
                    best, best_score = ac, score
            tgt = self.arh_target = best
        if tgt is None:
            self.status = "SEARCH"
            if self.est_pos is None:
                return None
            if self.est_vel is not None:
                self.est_pos += self.est_vel * dt
            return self.est_pos, self.est_vel
        self.status = "CHAFF" if getattr(tgt, "is_chaff", False) else "ACTIVE"
        if not getattr(tgt, "is_chaff", False):
            self.est_pos = Vec3(tgt.pos)
            self.est_vel = Vec3(tgt.vel)
        return tgt.pos, tgt.vel


def time_to_impact(missile):
    """Rough time to go for the HUD."""
    tgt = missile.guided_target
    if tgt is None:
        return None
    rel = tgt.pos - missile.pos
    closing = -(tgt.vel - missile.vel).dot(safe_normalized(rel))
    if closing <= 1.0:
        return None
    return rel.length() / closing


def launch_zone(spec, launch_speed, altitude, target_closing):
    """Very small 1D fly-out model -> (Rmax, Rne) in metres.

    ``target_closing``: target velocity component towards the shooter (m/s).
    Rmax: target keeps its current closure.  Rne ("no escape"): target turns
    cold and runs at 300 m/s.  Cheap enough to run a few times per second.
    """
    def fly(closure):
        mass = spec.mass
        v = launch_speed
        x = 0.0
        t = 0.0
        dt = 0.25
        burn = spec.burn_time
        while t < spec.guidance_time:
            rho, a_sound = isa(altitude + (2500.0 * min(t / 20.0, 1.0) if spec.loft else 0.0))
            thrust = 0.0
            tt = t
            for duration, th in spec.motor:
                if tt < duration:
                    thrust = th
                    break
                tt -= duration
            if t < burn:
                mass -= spec.propellant / burn * dt
            drag = 0.5 * rho * v * v * spec.ref_area * interp_table(spec.cd_table, v / a_sound) * 1.15
            v += (thrust - drag) / mass * dt
            x += v * dt
            t += dt
            if v < 450.0 and t > burn:          # too slow to still out-turn a target
                break
            # x is the distance covered; the target covers closure*t towards us
        return max(0.0, x + closure * t)

    return fly(target_closing), fly(-300.0)


def flyout_time(spec, launch_speed, altitude, distance):
    """Seconds a missile launched now needs to fly ``distance`` metres (same 1D model); None = never."""
    mass = spec.mass
    v = launch_speed
    x = 0.0
    t = 0.0
    dt = 0.1
    path = distance * (1.08 if spec.loft else 1.0)
    burn = spec.burn_time
    while t < spec.guidance_time:
        rho, a_sound = isa(altitude + (2500.0 * min(t / 20.0, 1.0) if spec.loft else 0.0))
        thrust = 0.0
        tt = t
        for duration, th in spec.motor:
            if tt < duration:
                thrust = th
                break
            tt -= duration
        if t < burn:
            mass -= spec.propellant / burn * dt
        drag = 0.5 * rho * v * v * spec.ref_area * interp_table(spec.cd_table, v / a_sound) * 1.15
        v += (thrust - drag) / mass * dt
        x += v * dt
        t += dt
        if x >= path:
            return t
        if v < 250.0 and t > burn:
            return None
    return None
