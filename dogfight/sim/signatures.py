"""Infrared and radar signatures.

IR: the hot engine nozzle dominates from the rear, the afterburner plume is
visible from every aspect, and at high Mach the skin heats up a little.
Intensity 1.0 = an F-16 at military power seen straight from behind.

Radar: RCS grows from the nose-on value to the beam value.
"""

import math

from ..mathutil import clamp, safe_normalized, smoothstep


def ir_intensity(source, observer_pos):
    """IR intensity of an aircraft or a flare as seen from ``observer_pos``."""
    if getattr(source, "is_flare", False):
        return source.intensity
    if not source.alive and not getattr(source, "burning", False):
        return 0.0
    to_obs = safe_normalized(observer_pos - source.pos)
    rear = -source.forward.dot(to_obs)          # 1 = observer directly behind
    nozzle = 0.15 + 0.85 * smoothstep(-0.35, 0.95, rear)
    engine = source.engine_setting
    if engine > 1.0:
        heat = 2.0 + 0.4 * (engine - 1.0) / 0.1  # afterburner
        plume = 0.35
    else:
        heat = 0.25 + 0.75 * clamp(engine, 0.0, 1.0) ** 1.5
        plume = 0.0
    aero = 0.06 * source.mach ** 2
    burning = 1.5 if getattr(source, "burning", False) else 0.0
    return heat * nozzle + plume + aero + burning


def ir_lock_range(base_range, intensity):
    """Range at which a seeker with ``base_range`` (rear aspect, mil power) can see a source."""
    if intensity <= 0.0:
        return 0.0
    return min(base_range * math.sqrt(intensity), base_range * 1.5)


def rcs(target, observer_pos):
    spec = target.spec
    to_obs = safe_normalized(observer_pos - target.pos)
    side = 1.0 - abs(target.forward.dot(to_obs))
    return spec.rcs_front + (spec.rcs_side - spec.rcs_front) * side


def radar_detection_range(base_range, target_rcs):
    """Radar range equation: R scales with RCS^(1/4); base_range is for 5 m^2."""
    return base_range * (max(target_rcs, 0.01) / 5.0) ** 0.25


def radial_speed(target_vel, observer_pos, target_pos):
    """Target speed along the line of sight (doppler). 0 = beaming / notching."""
    los = safe_normalized(target_pos - observer_pos)
    return target_vel.dot(los)
