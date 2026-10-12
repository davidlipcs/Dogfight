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
    rate = clamp(off * 1.3 * precision - 0.6 * closing_rate * (1.0 - behind), 0.0, 1.2)
    accel = perp * (rate * speed) + Vec3(0, 0, G)
    accel -= path * accel.dot(path)                     # only lift can act sideways
    a_side = accel.dot(side)
    a_lift = accel.dot(lift)
    roll_err = math.atan2(a_side, a_lift)               # roll needed to put lift on accel
    nz = accel.length() / G
    if abs(roll_err) > 100.0 * DEG and nz < 2.0:
        # small correction "below": push a little instead of rolling inverted
        roll_err = _wrap(roll_err + math.pi)
        nz = -nz
    controls.roll = clamp(roll_err * 2.6 - fm.omega.y * 0.25, -1.0, 1.0)

    # pull only as much as the lift vector is already aligned
    align = math.cos(clamp(roll_err, -math.pi / 2, math.pi / 2))
    nz = nz * align if nz > 0 else nz
    nz = clamp(nz, spec.g_min, spec.g_max * max_g_frac)
    if nz >= 1.0:
        stick = (nz - 1.0) / (spec.g_max - 1.0)
    else:
        stick = (nz - 1.0) / (1.0 - spec.g_min)
    controls.pitch = clamp(stick, -1.0, 1.0)

    # rudder for the last couple of degrees (gun tracking)
    fine = 1.0 - smoothstep(1.0 * DEG, 4.0 * DEG, off)
    controls.yaw = clamp(math.atan2(d.dot(side), d.dot(path)) * 5.0 * precision, -1.0, 1.0) * fine
    return off


def level_direction(heading_rad, climb_rad=0.0):
    """Unit vector for a compass heading (0 = north) and a climb angle."""
    c = math.cos(climb_rad)
    return Vec3(math.sin(heading_rad) * c, math.cos(heading_rad) * c, math.sin(climb_rad))
