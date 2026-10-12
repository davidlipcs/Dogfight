import math

import pytest
from panda3d.core import Quat, Vec3

from dogfight.sim.aircraft import Aircraft
from dogfight.sim.specs import F16C
from dogfight.sim.terrain import Terrain
from dogfight.sim.world import World


@pytest.fixture(scope="module")
def terrain():
    return Terrain()


def on_runway(terrain):
    world = World(terrain)
    x, y, hdg = terrain.airfield.start_position()
    ac = world.add_aircraft(Aircraft(F16C, "p", "blue", Vec3(x, y, 0), hdg, 0.0))
    ac.fm.place_on_ground(x, y, terrain.height(x, y), hdg)
    return world, ac


def test_airfield_is_flat(terrain):
    field = terrain.airfield
    heights = [terrain.height(field.x + dx, field.y + dy) for dx in (-20, 0, 20, 190, 400) for dy in (-1500, 0, 1500)]
    assert max(heights) - min(heights) < 0.01
    assert field.on_runway(field.x, field.y)
    assert field.on_paved(field.x + 190.0, field.y)
    assert not field.on_paved(field.x - 300.0, field.y)


def test_afterburner_takeoff(terrain):
    world, ac = on_runway(terrain)
    ac.controls.throttle = 1.1
    y0 = ac.pos.y
    liftoff = None
    for _ in range(3000):
        ac.controls.pitch = 0.8 if ac.fm.ias * 3.6 > 260 else 0.0
        world._physics(0.01)
        if not ac.on_ground:
            liftoff = (ac.pos.y - y0, ac.fm.ias * 3.6)
            break
    assert liftoff is not None and ac.alive
    roll, speed = liftoff
    assert 350.0 < roll < 700.0          # real F-16: ~450 m with afterburner
    assert 290.0 < speed < 370.0         # ~150-180 kt


def test_gear_cannot_retract_on_ground(terrain):
    _, ac = on_runway(terrain)
    assert not ac.toggle_gear()
    assert ac.fm.gear_down


def test_brakes_hold_against_idle_thrust_and_stop(terrain):
    world, ac = on_runway(terrain)
    ac.fm.vel = Vec3(0, 40.0, 0)
    ac.controls.throttle = 0.0
    ac.controls.brakes = True
    for _ in range(1500):
        world._physics(0.01)
    assert ac.speed < 0.5 and ac.alive and ac.on_ground


def approach(terrain, sink, gear=True, bank=0.0):
    field = terrain.airfield
    world = World(terrain)
    ac = world.add_aircraft(Aircraft(F16C, "p", "blue", Vec3(field.x, field.y - 800, field.elevation + 4.0), 0.0, 75.0))
    ac.fm.gear_down = gear
    ac.fm.gear_pos = 1.0 if gear else 0.0
    q = Quat()
    q.setHpr((0.0, 11.0, bank))
    ac.fm.quat = q
    ac.fm.vel = Vec3(0.0, 75.0, -sink)
    ac.fm.engine = 0.0
    ac.controls.throttle = 0.0
    for _ in range(4000):
        ac.controls.brakes = ac.on_ground
        ac.controls.pitch = 0.0
        if not ac.on_ground and ac.alive:
            # hold the sink rate like a pilot in the flare
            ac.controls.pitch = max(-1.0, min(1.0, (-sink - ac.vel.z) * 0.3))
        world._physics(0.01)
        if not ac.alive or (ac.on_ground and ac.speed < 0.5):
            break
    return ac


def test_gentle_landing_and_rollout(terrain):
    ac = approach(terrain, 1.5)
    assert ac.alive and ac.on_ground and ac.speed < 0.5


def test_hard_landing_breaks_the_gear(terrain):
    ac = approach(terrain, 7.0)
    assert not ac.alive
    assert "kemény" in ac.fm.crash_reason


def test_belly_landing_is_a_crash(terrain):
    ac = approach(terrain, 1.5, gear=False)
    assert not ac.alive


def test_banked_touchdown_is_a_crash(terrain):
    ac = approach(terrain, 1.5, bank=25.0)
    assert not ac.alive


def test_flaps_retract_at_high_speed(terrain):
    world, ac = on_runway(terrain)
    ac.controls.throttle = 1.1
    for _ in range(int(12 / 0.01)):           # nose stays down: no rotation input
        world._physics(0.01)
    assert ac.on_ground or math.degrees(math.asin(ac.forward.z)) < 3.0
