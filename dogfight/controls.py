"""Player input: keyboard / mouse polling and the player's "pilot" (mouse aim instructor)."""

from panda3d.core import KeyboardButton, MouseButton, Vec3

from .ai.steering import steer_towards

THROTTLE_RATE = 0.55          # per second while Shift / Ctrl is held


class PlayerPilot:
    """Runs inside the fixed physics step so the instructor is frame-rate independent."""

    def __init__(self, aircraft):
        self.ac = aircraft
        self.aim = Vec3(aircraft.forward)
        self.pitch = None             # keyboard overrides (None = instructor)
        self.roll = None
        self.yaw = None
        aircraft.pilot = self

    def think(self, world):
        pass

    def fly(self, dt, world):
        c = self.ac.controls
        steer_towards(self.ac.fm, self.aim, c)
        if self.pitch is not None:
            c.pitch = self.pitch
        if self.roll is not None:
            c.roll = self.roll
        if self.yaw is not None:
            c.yaw = self.yaw


class InputReader:
    def __init__(self, base):
        self.base = base

    def key(self, ch):
        return self.button(KeyboardButton.asciiKey(ch))

    def button(self, handle):
        watcher = getattr(self.base, "mouseWatcherNode", None)
        return watcher is not None and watcher.isButtonDown(handle)

    @property
    def shift(self):
        return any(self.button(b) for b in (KeyboardButton.shift(), KeyboardButton.lshift(), KeyboardButton.rshift()))

    @property
    def ctrl(self):
        return any(self.button(b) for b in (KeyboardButton.control(), KeyboardButton.lcontrol(),
                                            KeyboardButton.rcontrol()))

    @property
    def left_mouse(self):
        return self.button(MouseButton.one())

    @property
    def right_mouse(self):
        return self.button(MouseButton.three())

    def axis(self, positive, negative):
        if self.key(positive) and not self.key(negative):
            return 1.0
        if self.key(negative) and not self.key(positive):
            return -1.0
        return None

    def apply(self, dt, pilot, cam):
        """Copy the held keys onto the player's aircraft for this frame."""
        ac = pilot.ac
        pilot.aim = cam.aim_direction()
        pilot.pitch = self.axis("w", "s")
        pilot.roll = self.axis("d", "a")
        pilot.yaw = self.axis("e", "q")
        c = ac.controls
        if self.shift:
            c.throttle = min(1.1, c.throttle + THROTTLE_RATE * dt)
        if self.ctrl:
            c.throttle = max(0.0, c.throttle - THROTTLE_RATE * dt)
        c.airbrake = self.key("b")
        c.brakes = self.key("b") and ac.on_ground
        ac.trigger = self.left_mouse
        ac.cm_hold = self.key("x")
        cam.set_free_look(self.key("c") or self.right_mouse)
