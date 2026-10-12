import random

from panda3d.core import Quat, Vec3

from conftest import run
from dogfight.ai.pilot import AIPilot
from dogfight.sim.aircraft import Aircraft
from dogfight.sim.guns import gun_lead, segment_hits_box
from dogfight.sim.specs import F16C
from dogfight.sim.terrain import Terrain
from dogfight.sim.world import World


def test_segment_box():
    half = (1.0, 1.0, 1.0)
    center = (0.0, 0.0, 0.0)
    assert segment_hits_box(Vec3(-5, 0, 0), Vec3(5, 0, 0), center, half)
    assert not segment_hits_box(Vec3(-5, 3, 0), Vec3(5, 3, 0), center, half)
    assert not segment_hits_box(Vec3(-5, 0, 0), Vec3(-2, 0, 0), center, half)


def test_gun_hits_target_ahead(world, make_aircraft):
    shooter = make_aircraft(pos=(0, 0, 5000))
    target = make_aircraft(pos=(30, 350, 5000), team="red")
    run(world, 3.0)                      # both settle at the same trim AoA
    # put the target on the gun line (the nose points a few degrees above the flight path)
    target.fm.pos = shooter.pos + shooter.forward * 350.0
    target.fm.vel = Vec3(shooter.vel)
    target.fm.quat = Quat(shooter.quat)
    target.fm.omega = Vec3(shooter.fm.omega)
    shooter.trigger = True
    run(world, 1.0)
    shooter.trigger = False
    run(world, 1.0)
    assert target.hp < F16C.hp
    assert shooter.gun.ammo < F16C.gun.ammo


def test_gun_lead_points_ahead_of_crossing_target():
    aim, tof = gun_lead(Vec3(0, 0, 0), Vec3(0, 200, 0), Vec3(0, 800, 0), Vec3(200, 200, 0), F16C.gun)
    assert aim.x > 0.05          # lead to the right
    assert 0.5 < tof < 1.2


def test_countermeasures_are_consumed(world, make_aircraft):
    ac = make_aircraft()
    ac.cm_hold = True
    run(world, 1.0)
    assert ac.flares < F16C.countermeasures.flares
    assert world.flares and world.chaff


def test_ai_battle_runs_without_errors():
    terrain = Terrain(size=60000.0, resolution=60, seed=3)
    world = World(terrain, seed=5)
    rng = random.Random(9)
    blue = Aircraft(F16C, "blue", "blue", Vec3(0, -12000, 5000), 0.0, 250.0, rng=rng)
    AIPilot(blue, "hard")
    world.add_aircraft(blue)
    for i in range(2):
        red = Aircraft(F16C, "red%d" % i, "red", Vec3(i * 3000.0, 12000, 5500), 180.0, 250.0,
                       rng=random.Random(i), livery="aggressor")
        AIPilot(red, "normal")
        world.add_aircraft(red)
    kinds = set()
    for _ in range(int(150 / (1 / 30.0))):
        world.update(1 / 30.0)
        kinds.update(k for k, _ in world.drain_events())
    assert "launch" in kinds or "hit" in kinds
    for ac in world.aircraft:
        if ac.alive:
            assert ac.pos.z > terrain.height(ac.pos.x, ac.pos.y)
