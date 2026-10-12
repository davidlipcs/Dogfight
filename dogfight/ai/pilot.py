"""Enemy AI pilot: patrol -> engage (radar, missiles, gun) -> defend (notch, break, decoys)."""

from panda3d.core import Vec3

from ..mathutil import DEG, angle_between, clamp, safe_normalized
from ..sim.guns import gun_lead
from ..sim.radar import STT
from ..sim.specs import ARH
from ..sim.world import AI_DT
from .steering import steer_towards

SKILLS = {
    "easy": dict(g=0.65, precision=0.7, missile_cd=32.0, cm=0.35, aware=0.25, gun_cone=0.8, arh=False),
    "normal": dict(g=0.85, precision=0.9, missile_cd=20.0, cm=0.7, aware=0.5, gun_cone=1.2, arh=True),
    "hard": dict(g=1.0, precision=1.0, missile_cd=12.0, cm=1.0, aware=0.85, gun_cone=1.6, arh=True),
}

MIN_AGL = 450.0


class AIPilot:
    def __init__(self, aircraft, skill="normal", rng=None):
        self.ac = aircraft
        self.skill = SKILLS[skill]
        self.rng = rng or aircraft.rng
        self.state = "patrol"
        self.target = None
        self.threat = None
        self._aware = set()
        self.defend_timer = 0.0
        self.missile_timer = self.rng.uniform(6.0, 14.0)
        self.patrol_alt = aircraft.pos.z
        self.waypoint = Vec3(self.rng.uniform(-15000, 15000), self.rng.uniform(-15000, 15000), self.patrol_alt)
        self.throttle = 0.95
        aircraft.pilot = self

    # ------------------------------------------------------------ thinking
    def think(self, world):
        ac = self.ac
        self.missile_timer -= AI_DT
        ac.trigger = False

        enemies = world.enemies_of(ac)
        self.target = min(enemies, key=lambda e: (e.pos - ac.pos).length(), default=None)

        threat = self._find_threat(world)
        if threat is not None:
            self.threat = threat
            self.state = "defend"
            self.defend_timer = 2.5
        elif self.defend_timer > 0.0:
            self.defend_timer -= AI_DT
            if self.threat is not None and not self.threat.alive:
                self.defend_timer = min(self.defend_timer, 0.5)
        else:
            self.threat = None
            self.state = "engage" if self.target is not None else "patrol"

        tgt = self.target
        if tgt is None:
            return
        dist = (tgt.pos - ac.pos).length()
        radar = ac.radar
        if not radar.on:
            radar.toggle_power()
        if radar.locked is not tgt and radar.pending is not tgt and dist < radar.spec.lock_range:
            radar.try_lock(tgt)
        if self.state == "engage":
            self._weapons(world, tgt, dist)

    def _find_threat(self, world):
        ac = self.ac
        best = None
        best_dist = 1e9
        for m in world.missiles:
            if not m.alive or m.shooter is None or m.shooter.team == ac.team:
                continue
            if m.guided_target is not ac and m.intended is not ac:
                continue
            dist = (m.pos - ac.pos).length()
            if m.id not in self._aware:
                warned = m.spec.guidance == ARH and any(
                    t.level == "launch" and (t.source is m or t.source is m.shooter) for t in ac.rwr.threats)
                spotted = dist < 4500.0 and self.rng.random() < self.skill["aware"] * 0.5
                if warned or spotted:
                    self._aware.add(m.id)
                else:
                    continue
            if dist < best_dist:
                best, best_dist = m, dist
        return best

    def _gun_solution(self, tgt):
        ac = self.ac
        return gun_lead(ac.pos, ac.vel, tgt.pos, tgt.vel, ac.spec.gun, iterations=2)[0]

    def _weapons(self, world, tgt, dist):
        ac = self.ac
        aim = self._gun_solution(tgt)
        if dist < 1100.0 and angle_between(ac.forward, aim) < self.skill["gun_cone"] * DEG:
            ac.trigger = True
        if self.missile_timer > 0.0:
            return
        ir_left = ac.missile_count("AIM-9M")
        arh_left = ac.missile_count("AIM-120A")
        fired = None
        if ir_left and 900.0 < dist < 7000.0:
            if ac.selected != "AIM-9M":
                ac.select("AIM-9M")
            elif ac.ir_seeker.candidate is tgt or ac.ir_seeker.target is tgt:
                if not ac.ir_seeker.locked:
                    ac.ir_seeker.lock()
                if ac.ir_seeker.target is tgt:
                    fired = ac.fire_missile(world)
        elif arh_left and self.skill["arh"] and ac.radar.mode == STT and ac.radar.locked is tgt:
            closing = -(tgt.vel - ac.vel).dot(safe_normalized(tgt.pos - ac.pos))
            max_range = 24000.0 if closing > 150.0 else 11000.0
            if 2500.0 < dist < max_range:
                if ac.selected != "AIM-120A":
                    ac.select("AIM-120A")
                fired = ac.fire_missile(world)
        if fired is not None:
            self.missile_timer = self.skill["missile_cd"] * self.rng.uniform(0.8, 1.3)

    # -------------------------------------------------------------- flying
    def fly(self, dt, world):
        ac = self.ac
        terrain = world.terrain
        desired = None
        throttle = 1.0
        max_g = self.skill["g"]

        if self.state == "defend" and self.threat is not None and self.threat.alive:
            desired, throttle, max_g = self._defend(world)
        elif self.state == "engage" and self.target is not None:
            desired, throttle = self._pursue(self.target)
        else:
            desired, throttle = self._patrol()

        # --- ground avoidance (overrides everything)
        agl = ac.pos.z - terrain.height(ac.pos.x, ac.pos.y)
        ahead = ac.pos + ac.vel * 4.0
        agl_ahead = ahead.z - terrain.height(ahead.x, ahead.y)
        if agl_ahead < MIN_AGL or agl < MIN_AGL * 0.7:
            flat = Vec3(ac.vel.x, ac.vel.y, 0.0)
            desired = safe_normalized(safe_normalized(flat) + Vec3(0, 0, 0.9))
            max_g = 1.0
        elif agl < 1800.0 and desired.z < -0.15:
            desired = safe_normalized(Vec3(desired.x, desired.y, -0.15))

        # --- stay on the map
        if abs(ac.pos.x) > 36000.0 or abs(ac.pos.y) > 36000.0:
            home = Vec3(-ac.pos.x, -ac.pos.y, 0.0)
            desired = safe_normalized(safe_normalized(home) + desired * 0.3)

        steer_towards(ac.fm, desired, ac.controls, max_g_frac=max_g, precision=self.skill["precision"])
        ac.controls.throttle = throttle

    def _pursue(self, tgt):
        ac = self.ac
        rel = tgt.pos - ac.pos
        dist = rel.length()
        if dist < 2500.0:
            desired = self._gun_solution(tgt)
        else:
            lead = min(dist / 600.0, 6.0)
            desired = safe_normalized(rel + tgt.vel * lead * 0.5)
        speed = ac.speed
        if dist > 5000.0 or speed < 190.0:
            throttle = 1.1
        elif dist < 900.0 and -(tgt.vel - ac.vel).dot(safe_normalized(rel)) > 80.0:
            throttle = 0.6           # overshooting - slow down
        else:
            throttle = 1.0
        return desired, throttle

    def _defend(self, world):
        ac = self.ac
        m = self.threat
        los = m.pos - ac.pos
        dist = los.length()
        flat_los = safe_normalized(Vec3(los.x, los.y, 0.0))
        perp = Vec3(-flat_los.y, flat_los.x, 0.0)
        if perp.dot(ac.vel) < 0.0:
            perp = -perp
        agl = ac.pos.z - world.terrain.height(ac.pos.x, ac.pos.y)
        use_cm = self.rng.random() < self.skill["cm"] * 0.25
        if m.spec.guidance == ARH:
            # Notch: put the missile on the 3/9 line (zero doppler) and dive a bit.
            dive = -0.25 if agl > 2500.0 else 0.0
            desired = safe_normalized(perp + Vec3(0, 0, dive))
            if dist < 14000.0 and use_cm:
                ac.dispense(world)
            return desired, 1.0, self.skill["g"]
        # IR missile
        if dist < 3500.0:
            if use_cm or dist < 1500.0:
                ac.dispense(world)
            # hard break across the missile's path, engine back to cool down
            desired = safe_normalized(perp - flat_los * 0.3 + Vec3(0, 0, -0.1))
            return desired, 0.65, 1.0
        away = -flat_los
        return safe_normalized(away + Vec3(0, 0, -0.05)), 1.1, self.skill["g"]

    def _patrol(self):
        ac = self.ac
        to_wp = self.waypoint - ac.pos
        if Vec3(to_wp.x, to_wp.y, 0).length() < 3000.0:
            self.waypoint = Vec3(self.rng.uniform(-20000, 20000), self.rng.uniform(-20000, 20000), self.patrol_alt)
        flat = safe_normalized(Vec3(to_wp.x, to_wp.y, 0.0))
        climb = clamp((self.patrol_alt - ac.pos.z) / 3000.0, -0.3, 0.3)
        return safe_normalized(flat + Vec3(0, 0, climb)), 0.95
