import math

from panda3d.core import Vec3

from dogfight.ai.steering import bank_angle, steer_towards
from dogfight.mathutil import DEG, angle_between, quat_look
from dogfight.sim.flight_model import Controls, FlightModel
from dogfight.sim.specs import F16C


def fly(direction, seconds, speed=250.0, max_g_frac=1.0, dt=0.01):
    fm = FlightModel(F16C, Vec3(0, 0, 5000), Vec3(0, speed, 0), quat_look(Vec3(0, 1, 0)))
    fm.engine = 1.0
    c = Controls(throttle=1.0)
    log = []
    for _ in range(int(seconds / dt)):
        steer_towards(fm, direction, c, max_g_frac=max_g_frac)
        fm.step(dt, c, None)
        log.append((bank_angle(fm.quat) / DEG, fm.g_load, angle_between(fm.vel, direction) / DEG))
    return fm, log


def test_small_correction_uses_little_bank():
    d = Vec3(math.sin(5 * DEG), math.cos(5 * DEG), 0)
    _, log = fly(d, 4.0)
    assert max(abs(b) for b, _, _ in log) < 25.0
    assert log[-1][2] < 1.5


def test_target_a_bit_below_is_pushed_not_rolled_inverted():
    d = Vec3(0, math.cos(20 * DEG), -math.sin(20 * DEG))
    _, log = fly(d, 3.0)
    assert max(abs(b) for b, _, _ in log) < 10.0          # wings stay level
    assert min(g for _, g, _ in log) < -1.0               # negative G push
    assert log[-1][2] < 6.0


def test_hard_turn_respects_the_g_margin():
    _, log = fly(Vec3(1, 0, 0), 4.0, max_g_frac=0.85)
    assert max(g for _, g, _ in log) < 0.85 * F16C.g_max + 0.3
    assert log[-1][2] < 30.0                               # still turns hard (90 deg in ~4.5 s)
