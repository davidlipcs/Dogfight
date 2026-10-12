"""Mouse-aim camera (War Thunder style) with chase and cockpit views.

The mouse rotates an "aim" orientation; the camera looks along it and the
instructor (ai.steering) flies the aircraft towards it.  The camera slowly
rolls itself back to the horizon so the world stays level, but you can still
loop - it just flips over the top like in WT.
"""

import math

from panda3d.core import Quat, Vec3

from .mathutil import DEG, UP, clamp, quat_axis_angle, quat_look

CHASE_DISTANCE = 26.0
CHASE_HEIGHT = 5.5
COCKPIT_EYE = Vec3(0.0, 3.6, 1.15)


class FlightCamera:
    def __init__(self, base, terrain, sensitivity=0.09, invert_y=False):
        self.base = base
        self.terrain = terrain
        self.sensitivity = sensitivity
        self.invert_y = invert_y
        self.aim = Quat()
        self.look = Quat()           # free-look orientation
        self.free_look = False
        self.cockpit = False
        self.position = Vec3(0, 0, 0)
        self.fov = 70.0
        self._phase = 0.0

    def reset(self, aircraft):
        self.aim = quat_look(aircraft.forward)
        self.look = Quat(self.aim)

    def aim_direction(self):
        return self.aim.getForward()

    def toggle_view(self):
        self.cockpit = not self.cockpit

    def set_free_look(self, active):
        if active and not self.free_look:
            self.look = Quat(self.aim)
        self.free_look = active

    def mouse_delta(self, dx, dy):
        """dx, dy in pixels (y grows downwards on screen)."""
        yaw = -dx * self.sensitivity * DEG
        pitch = -dy * self.sensitivity * DEG * (-1.0 if self.invert_y else 1.0)
        q = self.look if self.free_look else self.aim
        q = q * quat_axis_angle(UP, yaw)                  # yaw around world up
        q = quat_axis_angle(Vec3(1, 0, 0), pitch) * q     # pitch around local right
        q.normalize()
        if self.free_look:
            self.look = q
        else:
            self.aim = q

    @staticmethod
    def _level(q, dt, rate=1.6):
        """Roll ``q`` back towards a level horizon."""
        fwd = q.getForward()
        if abs(fwd.z) > 0.96:
            return q
        up = q.getUp()
        want_up = UP - fwd * fwd.dot(UP)
        want_up.normalize()
        ang = math.atan2(up.cross(want_up).dot(fwd), up.dot(want_up))
        if abs(ang) < 2.5:
            step = clamp(ang, -rate * dt, rate * dt)
        else:
            step = ang * min(1.0, rate * 0.6 * dt)
        return quat_axis_angle(Vec3(0, 1, 0), step) * q

    def update(self, dt, aircraft, zoom=False):
        self.aim = self._level(self.aim, dt)
        if self.free_look:
            self.look = self._level(self.look, dt)
        if aircraft is None:
            return
        view = self.look if self.free_look else self.aim
        cam_np = self.base.camera
        if self.cockpit and aircraft.alive:
            self.position = aircraft.pos + aircraft.quat.xform(COCKPIT_EYE)
        else:
            dist = CHASE_DISTANCE if aircraft.alive else 70.0
            self.position = aircraft.pos - view.getForward() * dist + view.getUp() * CHASE_HEIGHT
            ground = self.terrain.height(self.position.x, self.position.y)
            if self.position.z < ground + 3.0:
                self.position.z = ground + 3.0
        cam_np.setPos(self.position)
        cam_np.setQuat(view)

        # gun / G shake
        self._phase += dt
        shake = 0.0
        if aircraft.alive and aircraft.gun.firing:
            shake += 0.07
        if aircraft.alive and aircraft.fm.g_load > 6.0:
            shake += (aircraft.fm.g_load - 6.0) * 0.03
        if shake > 0.0:
            cam_np.setHpr(cam_np, math.sin(self._phase * 71.0) * shake, math.sin(self._phase * 53.0) * shake, 0)

        target_fov = 32.0 if zoom else (75.0 if self.cockpit else 70.0)
        self.fov += (target_fov - self.fov) * min(1.0, dt * 8.0)
        self.base.camLens.setFov(self.fov)
