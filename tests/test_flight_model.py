from panda3d.core import Vec3

from dogfight.mathutil import DEG, quat_look
from dogfight.sim.flight_model import Controls, FlightModel
from dogfight.sim.specs import F16C

DT = 0.01


def make(alt=3000.0, speed=200.0):
    fm = FlightModel(F16C, Vec3(0, 0, alt), Vec3(0, speed, 0), quat_look(Vec3(0, 1, 0)), fuel=2500)
    fm.store_mass = 4 * 86 + 2 * 152
    fm.store_cd = 0.0066
    return fm


def hold_altitude(fm, c, alt):
    c.pitch = max(-1.0, min(1.0, -0.02 * (fm.pos.z - alt) - 0.05 * fm.vel.z))


def test_neutral_stick_holds_one_g():
    fm = make()
    c = Controls(0.8)
    for _ in range(int(10 / DT)):
        fm.step(DT, c)
    assert abs(fm.g_load - 1.0) < 0.1
    assert abs(fm.vel.z) < 5.0


def test_top_speed_sea_level_is_about_mach_1_2():
    fm = make(alt=200.0, speed=250.0)
    c = Controls(1.1)
    for _ in range(int(200 / DT)):
        hold_altitude(fm, c, 200.0)
        fm.step(DT, c)
    kmh = fm.speed * 3.6
    assert 1350.0 < kmh < 1650.0


def test_g_and_aoa_limits_are_respected():
    for speed in (130.0, 200.0, 320.0):
        fm = make(speed=speed)
        c = Controls(1.0)
        c.pitch = 1.0
        max_g = 0.0
        max_alpha = 0.0
        for _ in range(int(3 / DT)):
            fm.step(DT, c)
            max_g = max(max_g, fm.g_load)
            max_alpha = max(max_alpha, fm.alpha / DEG)
        assert max_g < F16C.g_max + 0.3
        assert max_alpha < F16C.alpha_limit + 1.5


def test_hard_turn_bleeds_energy():
    fm = make(speed=250.0)
    c = Controls(1.0)
    c.pitch = 1.0
    for _ in range(int(8 / DT)):
        fm.step(DT, c)
    assert fm.speed < 220.0


def test_roll_rate():
    fm = make(speed=220.0)
    c = Controls(1.0)
    c.roll = 1.0
    for _ in range(int(1.0 / DT)):
        fm.step(DT, c)
    assert 200.0 < fm.omega.y / DEG < 290.0


def test_afterburner_burns_more_fuel():
    a = make()
    b = make()
    ca = Controls(1.0)
    cb = Controls(1.1)
    for _ in range(int(20 / DT)):
        a.step(DT, ca)
        b.step(DT, cb)
    assert (2500 - b.fuel) > 2.5 * (2500 - a.fuel)
