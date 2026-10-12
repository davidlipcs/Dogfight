"""Gun (M61A1 Vulcan) and ballistic rounds with swept hit detection."""

import math
import random

from panda3d.core import Vec3

from ..mathutil import G, safe_normalized

GUN_OFFSET = Vec3(-0.75, 2.6, 0.55)     # F-16: left wing root, above the strake


class Bullet:
    __slots__ = ("pos", "vel", "age", "owner", "alive", "k", "damage", "life", "tracer")

    def __init__(self, pos, vel, owner, spec, tracer):
        self.pos = pos
        self.vel = vel
        self.age = 0.0
        self.owner = owner
        self.alive = True
        self.k = spec.drag_k
        self.damage = spec.damage
        self.life = spec.bullet_life
        self.tracer = tracer


class Gun:
    def __init__(self, spec, rng=None):
        self.spec = spec
        self.ammo = spec.ammo
        self.rng = rng or random.Random()
        self.firing = False
        self._acc = 0.0
        self._count = 0

    def reload(self):
        self.ammo = self.spec.ammo

    def update(self, dt, shooter, trigger, world):
        spec = self.spec
        self.firing = trigger and self.ammo > 0 and shooter.alive
        if not self.firing:
            self._acc = 0.0
            return
        self._acc += dt * spec.rate_rpm / 60.0
        n = min(int(self._acc), self.ammo)
        self._acc -= n
        if n <= 0:
            return
        quat = shooter.quat
        fwd = quat.getForward()
        right = quat.getRight()
        up = quat.getUp()
        muzzle = shooter.pos + quat.xform(GUN_OFFSET)
        sigma = spec.dispersion_mrad * 1e-3
        for i in range(n):
            self.ammo -= 1
            self._count += 1
            direction = safe_normalized(fwd + right * self.rng.gauss(0.0, sigma) + up * self.rng.gauss(0.0, sigma))
            vel = shooter.vel + direction * spec.muzzle_velocity
            pos = muzzle + vel * (dt * i / n)
            world.bullets.append(Bullet(pos, vel, shooter, spec, tracer=(self._count % 2 == 0)))


def gun_lead(shooter_pos, shooter_vel, target_pos, target_vel, spec, iterations=4):
    """Direction the nose must point so rounds meet the target -> (unit dir, time of flight).

    Rounds inherit the shooter's velocity, slow down with quadratic drag
    (distance s after time t: t = (e^(k s) - 1) / (k v0)) and drop with gravity.
    """
    rel = target_pos - shooter_pos
    dv = target_vel - shooter_vel
    k = spec.drag_k
    v0 = spec.muzzle_velocity
    tof = rel.length() / v0
    aim = Vec3(rel)
    for _ in range(iterations):
        aim = rel + dv * tof + Vec3(0, 0, 0.5 * G * tof * tof)
        s = aim.length()
        tof = (math.exp(min(k * s, 6.0)) - 1.0) / (k * v0)
    return safe_normalized(aim), tof


def segment_hits_box(p0, p1, center, half):
    """Slab test of segment p0->p1 against an axis aligned box (all in body frame)."""
    t_min = 0.0
    t_max = 1.0
    for a in range(3):
        s = p0[a] - center[a]
        d = p1[a] - p0[a]
        h = half[a]
        if abs(d) < 1e-9:
            if abs(s) > h:
                return False
            continue
        t1 = (-h - s) / d
        t2 = (h - s) / d
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > t_min:
            t_min = t1
        if t2 < t_max:
            t_max = t2
        if t_min > t_max:
            return False
    return True


def update_bullets(world, dt):
    """Move every round once per frame and test the swept segment for hits."""
    terrain = world.terrain
    targets = [ac for ac in world.aircraft if ac.alive]
    survivors = []
    for b in world.bullets:
        old = Vec3(b.pos)
        speed = b.vel.length()
        b.vel -= b.vel * (b.k * speed * dt)
        b.vel.z -= G * dt
        b.pos += b.vel * dt
        b.age += dt
        step_len = (b.pos - old).length()
        for ac in targets:
            if ac is b.owner:
                continue
            rel_end = b.pos - ac.pos
            if rel_end.length() > step_len + 12.0:
                continue
            rel_start = old - (ac.pos - ac.vel * dt)
            conj = ac.quat.conjugate()
            p0 = conj.xform(rel_start)
            p1 = conj.xform(rel_end)
            if any(segment_hits_box(p0, p1, c, h) for c, h in ac.spec.hitboxes):
                b.alive = False
                world.emit("hit", target=ac, pos=Vec3(b.pos), shooter=b.owner)
                ac.take_damage(b.damage, b.owner, "M61A1", world)
                break
        if not b.alive:
            continue
        if b.pos.z < terrain.height(b.pos.x, b.pos.y):
            if b.tracer:
                world.emit("impact", pos=Vec3(b.pos))
            continue
        if b.age < b.life:
            survivors.append(b)
    world.bullets = survivors
