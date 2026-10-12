"""Direction -> stick inputs ("instructor").

This is what makes War Thunder's mouse aim work: the player only says *where*
the aircraft should go, and an autopilot banks and pulls like a pilot would.
The AI pilots use the very same function.

It steers the *flight path* (velocity vector), not the nose, so pointing the
mouse at the horizon gives level flight; the nose sits a few degrees higher
(angle of attack) exactly like on a real aircraft.

Pointing at the horizon to the side therefore gives a properly banked,
level turn, and pointing straight ahead gives 1 G level flight.
"""

import math

from panda3d.core import Vec3

from ..mathutil import DEG, G, clamp, safe_normalized, smoothstep


def bank_angle(quat):
    right = quat.getRight()
    up = quat.getUp()
    return math.atan2(-right.z, up.z)


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def steer_towards(fm, direction, controls, max_g_frac=1.0, precision=1.0):
    """Set controls.pitch / roll / yaw so the flight path swings towards ``direction``.

    1. desired path turn rate = gain * angle to the target (capped)
    2. needed acceleration = turn rate * speed towards the target + 1 g against gravity
    3. roll the lift vector onto that acceleration and pull the matching load factor
    """
    spec = fm.spec
    quat = fm.quat
    right = quat.getRight()
    up = quat.getUp()
    fwd = quat.getForward()
    path = safe_normalized(fm.vel, fwd) if fm.speed > 30.0 else fwd
    lift = safe_normalized(right.cross(path), up)      # current lift direction
    side = path.cross(lift)
    d = safe_normalized(direction)
    off = math.acos(clamp(d.dot(path), -1.0, 1.0))
    speed = max(fm.speed, 60.0)

    perp = d - path * d.dot(path)
    if perp.length() > 1e-6:
        perp.normalize()
    # target (almost) behind: turn in the horizontal plane instead of a random direction
    behind = smoothstep(120.0 * DEG, 170.0 * DEG, off)
    if behind > 0.0 or perp.length() < 0.5:
        flat = path.cross(Vec3(0, 0, 1))
        if flat.length() < 1e-3:
            flat = Vec3(right)
        flat.normalize()
        sign = perp.dot(flat)
        if abs(sign) < 0.15:
            sign = 1.0 if bank_angle(quat) >= 0.0 else -1.0
        flat *= 1.0 if sign >= 0.0 else -1.0
        perp = safe_normalized(perp * (1.0 - behind) + flat * max(behind, 0.01), flat)
    # PD: the flight path already swinging towards the target means "ease off"
    closing_rate = fm.accel.dot(perp) / speed
    rate = clamp(off * 0.9 * precision - 0.5 * closing_rate * (1.0 - behind), 0.0, 1.0)
    accel = perp * (rate * speed) + Vec3(0, 0, G)
    accel -= path * accel.dot(path)                     # only lift can act sideways
    a_g = accel.length() / G
    roll_pull = math.atan2(accel.dot(side), accel.dot(lift))   # roll needed to put lift on accel
    roll_push = _wrap(roll_pull + math.pi)
    # pull (lift towards the target) or push (negative G)?  Modest corrections below are pushed (the push
    # saturates at about -2.5 G) instead of rolling inverted; hysteresis stops it flip-flopping.
    push_ok = behind == 0.0 and (off < 40.0 * DEG or (a_g <= -spec.g_min * 0.85 and off < 60.0 * DEG))
    cost_pull = abs(roll_pull)
    cost_push = abs(roll_push) + 25.0 * DEG
    push = getattr(fm, "steer_push", False) and push_ok
    if push_ok and ((cost_pull + 20.0 * DEG < cost_push) if push else (cost_push + 20.0 * DEG < cost_pull)):
        push = not push
    fm.steer_push = push
    roll_err = roll_push if push else roll_pull
    # small corrections: keep the bank small, the rudder does the rest (War Thunder instructor feel)
    if off < 45.0 * DEG and behind == 0.0:
        cur = bank_angle(quat)
        lim = (20.0 + 160.0 * smoothstep(4.0 * DEG, 40.0 * DEG, off)) * DEG
        base = math.pi if (push and abs(cur) > math.pi / 2) else 0.0
        want = _wrap(cur + roll_err - base)
        roll_err = _wrap(clamp(want, -lim, lim) + base - cur)
    controls.roll = clamp(roll_err * 1.8 - fm.omega.y * 0.3, -1.0, 1.0)

    # load factor along the lift direction we roll to, applied as the roll gets there
    target = lift * math.cos(roll_err) + side * math.sin(roll_err)
    nz = accel.dot(target) / G
    nz = 1.0 + (nz - 1.0) * max(0.0, math.cos(clamp(roll_err, -math.pi / 2, math.pi / 2)))
    nz = clamp(nz, spec.g_min * 0.85, spec.g_max * max_g_frac)
    if nz >= 1.0:
        stick = (nz - 1.0) / (spec.g_max - 1.0)
    else:
        stick = (nz - 1.0) / (1.0 - spec.g_min)
    controls.pitch = clamp(stick, -1.0, 1.0)

    # rudder for small corrections (gun tracking, flat turns)
    fine = 1.0 - smoothstep(3.0 * DEG, 12.0 * DEG, off)
    controls.yaw = clamp(math.atan2(d.dot(side), d.dot(path)) * 4.0 * precision, -1.0, 1.0) * fine

    if fm.on_ground:
        # taxi / take-off roll: wings stay level, steer the nose wheel towards the aim heading
        heading_err = _wrap(math.atan2(d.x, d.y) - math.atan2(fwd.x, fwd.y))
        controls.roll = 0.0
        controls.yaw = clamp(heading_err * 3.0, -1.0, 1.0)
        climb = math.asin(clamp(d.z, -1.0, 1.0))
        controls.pitch = clamp(climb * 4.0, 0.0, 1.0)      # aim above the horizon = rotate
    return off


def level_direction(heading_rad, climb_rad=0.0):
    """Unit vector for a compass heading (0 = north) and a climb angle."""
    c = math.cos(climb_rad)
    return Vec3(math.sin(heading_rad) * c, math.cos(heading_rad) * c, math.sin(climb_rad))
