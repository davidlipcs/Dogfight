"""Player input: keyboard / mouse polling and the player's "pilot" (mouse aim instructor)."""

import math

from panda3d.core import GamepadButton, InputDevice, KeyboardButton, MouseButton, Vec3

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


class GamepadReader:
    """Xbox / PlayStation pad through Panda3D's input devices (same layout as the browser version):
    left stick flies directly, right stick moves the aim, LT/RT throttle, RB gun, A missile, LB flares,
    X radar lock, B IR lock, Y next weapon, D-pad gear / brake / view / zoom, Start pause, Back help,
    L3 held = look around, R3 = markers."""

    BUTTONS = {"a": "face_a", "b": "face_b", "x": "face_x", "y": "face_y", "lb": "lshoulder", "rb": "rshoulder",
               "start": "start", "back": "back", "l3": "lstick", "r3": "rstick", "up": "dpad_up",
               "down": "dpad_down", "left": "dpad_left", "right": "dpad_right"}

    def __init__(self, base):
        self.device = None
        self.now = {}
        self.prev = {}
        self.axes = dict(lx=0.0, ly=0.0, rx=0.0, ry=0.0, lt=0.0, rt=0.0)
        mgr = getattr(base, "devices", None)
        if mgr is None:
            return
        try:
            pads = mgr.getDevices(InputDevice.DeviceClass.gamepad)
        except Exception:          # no device support on this platform / build
            return
        if pads:
            self.device = pads[0]
        base.accept("connect-device", self._connect)
        base.accept("disconnect-device", self._disconnect)

    def _connect(self, device):
        if self.device is None and device.device_class == InputDevice.DeviceClass.gamepad:
            self.device = device

    def _disconnect(self, device):
        if device is self.device:
            self.device = None

    @property
    def connected(self):
        return self.device is not None

    def poll(self):
        self.prev = self.now
        if self.device is None:
            self.now = {}
            return False
        now = {}
        for name, attr in self.BUTTONS.items():
            state = self.device.findButton(getattr(GamepadButton, attr)())
            now[name] = bool(state and state.pressed)
        self.now = now

        def axis(kind):
            a = self.device.findAxis(kind)
            return a.value if a is not None else 0.0

        def dz(v):
            return 0.0 if abs(v) < 0.12 else math.copysign(((abs(v) - 0.12) / 0.88) ** 1.5, v)
        A = InputDevice.Axis
        self.axes = dict(lx=dz(axis(A.left_x)), ly=dz(axis(A.left_y)), rx=dz(axis(A.right_x)),
                         ry=dz(axis(A.right_y)), lt=axis(A.left_trigger), rt=axis(A.right_trigger))
        return True

    def held(self, name):
        return self.now.get(name, False)

    def pressed(self, name):
        return self.now.get(name, False) and not self.prev.get(name, False)


class InputReader:
    def __init__(self, base):
        self.base = base
        self._thr_dir = 0
        self._thr_hold = 0.0
        self.message = None           # callback(text, level) for throttle notices
        self.pad = GamepadReader(base) if base is not None else None
        self._rt = self._lt = False

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
        up = self.shift or getattr(self, "_pad_up", False)
        down = self.ctrl or getattr(self, "_pad_down", False)
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
        pad = self.pad if self.pad is not None and self.pad.connected else None
        if pad is not None:
            cam.set_free_look(pad.held("l3"))
            ax = pad.axes
            if ax["rx"] or ax["ry"]:       # right stick moves the aim like the mouse (pixels per frame)
                k = dt / max(cam.sensitivity, 1e-3)
                cam.mouse_delta(ax["rx"] * 110.0 * k, -ax["ry"] * 80.0 * k)
        pilot.aim = cam.aim_direction()
        pilot.pitch = self.axis("s", "w")      # S = nose up (pull), W = nose down (push)
        pilot.roll = self.axis("d", "a")
        pilot.yaw = self.axis("e", "q")
        if pad is not None and (pad.axes["lx"] or pad.axes["ly"]):
            # left stick: direct control, stick back = nose up (Panda3D's stick y is + forward)
            if pilot.pitch is None:
                pilot.pitch = -pad.axes["ly"]
            if pilot.roll is None:
                pilot.roll = pad.axes["lx"]
        if pilot.manual:
            cam.aim = quat_look(ac.forward)      # the mouse aim point rides on the nose while flying with keys
        c = ac.controls
        self._pad_up = pad is not None and pad.axes["rt"] > 0.5
        self._pad_down = pad is not None and pad.axes["lt"] > 0.5
        self._throttle(dt, c)
        brake = self.key("b") or (pad is not None and pad.held("down"))
        c.airbrake = brake
        c.brakes = brake and ac.on_ground
        ac.trigger = self.left_mouse or (pad is not None and pad.held("rb"))
        ac.cm_hold = self.key("x") or (pad is not None and pad.held("lb"))
        if pad is None or not pad.held("l3"):
            cam.set_free_look(self.key("c") or self.right_mouse)
