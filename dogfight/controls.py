"""Player input: keyboard / mouse polling and the player's "pilot" (mouse aim instructor)."""

import math

from panda3d.core import KeyboardButton, MouseButton, Vec3

from .ai.steering import steer_towards
from .mathutil import quat_look

THROTTLE_RATE = 0.40          # per second while Shift / Ctrl is held (after the first 5 % step)
THROTTLE_STEP = 0.05
MAX_AB = 1.1
HOLD_DELAY = 0.3
PLAYER_G = 0.85              # instructor G limit for the player (fraction of 9 G)


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

    @property
    def manual(self):
        return self.pitch is not None or self.roll is not None

    def fly(self, dt, world):
        c = self.ac.controls
        fm = self.ac.fm
        if self.manual:
            # keyboard flying (like War Thunder): the instructor lets go; an axis without a key holds its
            # attitude instead of fighting the pilot
            c.pitch = self.pitch if self.pitch is not None else 0.0
            c.roll = self.roll if self.roll is not None else max(-1.0, min(1.0, -fm.omega.y * 0.5))
            c.yaw = self.yaw if self.yaw is not None else 0.0
            return
        # the instructor keeps a little G margin (~7.6 G) against blackout; S pulls the full 9 G
        steer_towards(fm, self.aim, c, max_g_frac=PLAYER_G)
        if self.yaw is not None:
            c.yaw = self.yaw


class InputReader:
    def __init__(self, base):
        self.base = base
        self._thr_dir = 0
        self._thr_hold = 0.0
        self.message = None           # callback(text, level) for throttle notices

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

    def _throttle(self, dt, c):
        """Throttle lever with a MIL detent: a tap moves it 5 %, holding slews it.  Going up it stops at
        100 % (MIL); the afterburner needs a new press of Shift there.  Down from AB goes straight to MIL."""
        up, down = self.shift, self.ctrl
        direction = 1 if up and not down else (-1 if down and not up else 0)
        if direction != self._thr_dir:
            self._thr_dir = direction
            self._thr_hold = 0.0
            if direction > 0:
                if c.throttle >= 0.999:
                    if c.throttle < MAX_AB:
                        c.throttle = MAX_AB
                        if self.message:
                            self.message("UTÁNÉGETŐ BE", "warn")
                else:
                    c.throttle = min(1.0, math.floor(c.throttle / THROTTLE_STEP + 1e-6) * THROTTLE_STEP + THROTTLE_STEP)
            elif direction < 0:
                if c.throttle > 1.001:
                    c.throttle = 1.0
                    if self.message:
                        self.message("UTÁNÉGETŐ KI", "info")
                else:
                    c.throttle = max(0.0, math.ceil(c.throttle / THROTTLE_STEP - 1e-6) * THROTTLE_STEP - THROTTLE_STEP)
            return
        if direction == 0:
            return
        self._thr_hold += dt
        if self._thr_hold < HOLD_DELAY:
            return
        if direction > 0 and c.throttle < 1.0:
            c.throttle = min(1.0, c.throttle + THROTTLE_RATE * dt)
        elif direction < 0:
            c.throttle = 1.0 if c.throttle > 1.0 else max(0.0, c.throttle - THROTTLE_RATE * dt)

    def apply(self, dt, pilot, cam):
        """Copy the held keys onto the player's aircraft for this frame."""
        ac = pilot.ac
        pilot.aim = cam.aim_direction()
        pilot.pitch = self.axis("s", "w")      # S = nose up (pull), W = nose down (push)
        pilot.roll = self.axis("d", "a")
        pilot.yaw = self.axis("e", "q")
        if pilot.manual:
            cam.aim = quat_look(ac.forward)      # the mouse aim point rides on the nose while flying with keys
        c = ac.controls
        self._throttle(dt, c)
        c.airbrake = self.key("b")
        c.brakes = self.key("b") and ac.on_ground
        ac.trigger = self.left_mouse
        ac.cm_hold = self.key("x")
        cam.set_free_look(self.key("c") or self.right_mouse)
