from dogfight.controls import InputReader
from dogfight.sim.flight_model import Controls


class Keys(InputReader):
    """InputReader with scripted Shift / Ctrl instead of a Panda3D window."""

    def __init__(self):
        super().__init__(base=None)
        self.up = self.down = False

    @property
    def shift(self):
        return self.up

    @property
    def ctrl(self):
        return self.down


def frames(keys, c, seconds, dt=1.0 / 60.0):
    for _ in range(int(round(seconds / dt))):
        keys._throttle(dt, c)


def test_tap_moves_throttle_five_percent():
    keys, c = Keys(), Controls(throttle=0.5)
    keys.up = True
    frames(keys, c, 0.1)
    keys.up = False
    frames(keys, c, 0.1)
    assert abs(c.throttle - 0.55) < 1e-9
    keys.down = True
    frames(keys, c, 0.1)
    keys.down = False
    frames(keys, c, 0.1)
    assert abs(c.throttle - 0.5) < 1e-9


def test_holding_stops_at_mil_and_afterburner_needs_a_new_press():
    keys, c = Keys(), Controls(throttle=0.2)
    keys.up = True
    frames(keys, c, 5.0)
    assert c.throttle == 1.0                    # detent: no afterburner while still holding
    keys.up = False
    frames(keys, c, 0.1)
    keys.up = True
    frames(keys, c, 0.1)
    assert c.throttle > 1.0                     # second press lights the afterburner
    keys.up = False
    keys.down = True
    frames(keys, c, 0.1)
    assert c.throttle == 1.0                    # down from AB goes straight to MIL


def test_throttle_stops_when_key_released():
    keys, c = Keys(), Controls(throttle=0.2)
    keys.up = True
    frames(keys, c, 1.0)
    keys.up = False
    level = c.throttle
    frames(keys, c, 1.0)
    assert c.throttle == level
