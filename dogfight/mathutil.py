"""Small vector / interpolation helpers shared by the simulation and the UI.

World convention (Panda3D): +X = east/right, +Y = north/forward, +Z = up.
Units are SI everywhere: metres, seconds, kilograms, newtons, radians
(degrees only appear in spec tables and on the HUD).
"""

import math

from panda3d.core import Quat, Vec3, lookAt

G = 9.80665
UP = Vec3(0, 0, 1)
DEG = math.pi / 180.0


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def safe_normalized(v, fallback=None):
    length = v.length()
    if length > 1e-9:
        return v / length
    return Vec3(fallback) if fallback is not None else Vec3(0, 1, 0)


def angle_between(a, b):
    """Angle in radians between two (not necessarily unit) vectors."""
    la = a.length()
    lb = b.length()
    if la < 1e-9 or lb < 1e-9:
        return 0.0
    return math.acos(clamp(a.dot(b) / (la * lb), -1.0, 1.0))


def interp_table(table, x):
    """Piecewise linear lookup in a sorted ((x, y), ...) table, clamped at the ends."""
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def quat_axis_angle(axis, angle):
    q = Quat()
    q.setFromAxisAngleRad(angle, axis)
    return q


def quat_look(forward, up=UP):
    """Orientation whose +Y axis points along ``forward``."""
    q = Quat()
    fwd = safe_normalized(forward)
    if abs(fwd.dot(up)) > 0.999:
        up = Vec3(0, 1, 0) if abs(fwd.z) > 0.5 else UP
    lookAt(q, fwd, up)
    return q


def rotate_towards(current, target, max_angle):
    """Rotate unit vector ``current`` towards unit vector ``target`` by at most ``max_angle``."""
    ang = angle_between(current, target)
    if ang <= max_angle or ang < 1e-6:
        return Vec3(target)
    axis = current.cross(target)
    if axis.length() < 1e-9:
        # Opposite vectors: pick any perpendicular axis.
        axis = current.cross(UP) if abs(current.z) < 0.9 else current.cross(Vec3(1, 0, 0))
    axis.normalize()
    return safe_normalized(quat_axis_angle(axis, max_angle).xform(current))


def to_local(quat, v):
    """World vector -> body frame (x right, y forward, z up)."""
    return quat.conjugate().xform(v)


def to_world(quat, v):
    return quat.xform(v)


def closest_approach(p_rel, v_rel, dt):
    """Minimum distance and time of a relative linear motion during [0, dt].

    ``p_rel`` is the starting relative position, ``v_rel`` the relative velocity.
    """
    vv = v_rel.dot(v_rel)
    t = 0.0
    if vv > 1e-9:
        t = clamp(-p_rel.dot(v_rel) / vv, 0.0, dt)
    return (p_rel + v_rel * t).length(), t


def heading_deg(v):
    """Compass heading of a vector (0 = north/+Y, 90 = east/+X)."""
    return math.degrees(math.atan2(v.x, v.y)) % 360.0
