"""Direction -> stick inputs ("instructor").

This is what makes War Thunder's mouse aim work: the player only says *where*
the aircraft should point, and an autopilot rolls the lift vector onto that
direction and pulls.  The AI pilots use the very same function.
"""

import math

from ..mathutil import DEG, G, clamp, smoothstep, to_local


def bank_angle(quat):
    right = quat.getRight()
    up = quat.getUp()
    return math.atan2(-right.z, up.z)


def steer_towards(fm, direction, controls, max_g_frac=1.0, precision=1.0):
    """Set controls.pitch / roll / yaw so the nose swings towards ``direction`` (world, unit)."""
    spec = fm.spec
    local = to_local(fm.quat, direction)
    off = math.acos(clamp(local.y, -1.0, 1.0))
    pitch_err = math.atan2(local.z, local.y)          # + = above the nose
    roll_to_target = math.atan2(local.x, local.z)     # rotate lift vector onto target

    # Close to the nose: keep the wings level and fine tune with pitch / rudder.
    w = smoothstep(2.0 * DEG, 14.0 * DEG, off)
    level_err = -bank_angle(fm.quat)
    if local.z < 0.0 and off < 30.0 * DEG:
        # Slightly below the nose: push instead of rolling inverted.
        w *= smoothstep(10.0 * DEG, 30.0 * DEG, off)
    roll_err = w * roll_to_target + (1.0 - w) * level_err
    controls.roll = clamp(roll_err * 2.4 - fm.omega.y * 0.22, -1.0, 1.0)

    # Pull only once the target is roughly in the lift plane.
    align = 1.0 if w < 0.5 else max(0.0, math.cos(roll_to_target)) ** 0.5
    if off > 100.0 * DEG:
        align = max(align, 0.3)
    speed = max(fm.speed, 60.0)
    q_des = clamp(pitch_err * 2.6 * precision, -1.2, 1.2) * align
    nz = q_des * speed / G + fm.quat.getUp().z
    nz = min(nz, spec.g_max * max_g_frac)
    if nz >= 1.0:
        stick = (nz - 1.0) / (spec.g_max - 1.0)
    else:
        stick = (nz - 1.0) / (1.0 - spec.g_min)
    controls.pitch = clamp(stick, -1.0, 1.0)

    # Rudder for the last few degrees (gun aiming).
    controls.yaw = clamp(local.x * 6.0 * precision, -1.0, 1.0) * (1.0 - w)
    return off
