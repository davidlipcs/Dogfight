import dataclasses
import random

from panda3d.core import Vec3

from conftest import run
from dogfight.sim.countermeasures import Flare
from dogfight.sim.missile import Missile, launch_zone
from dogfight.sim.radar import STT
from dogfight.sim.specs import AIM9M, AIM120A, ALE47


def fly_straight(world, spec, seconds=30.0):
    shooter = world.aircraft[0]
    m = Missile(spec, shooter, Vec3(0, 20, 5000), Vec3(0, 260, 0), Vec3(0, 1, 0), random.Random(1))
    world.missiles.append(m)
    v_max = 0.0
    t = 0.0
    while m.alive and t < seconds:
        m.update(0.01, world)
        v_max = max(v_max, m.vel.length())
        t += 0.01
    return v_max, m


def test_aim9m_top_speed(world, make_aircraft):
    make_aircraft()
    v_max, _ = fly_straight(world, AIM9M)
    assert 2.2 * 320 < v_max < 3.0 * 320


def test_aim120a_top_speed(world, make_aircraft):
    make_aircraft()
    v_max, _ = fly_straight(world, AIM120A)
    assert 3.2 * 320 < v_max < 4.4 * 320


def test_launch_zone_is_bigger_head_on():
    head_on, _ = launch_zone(AIM120A, 270.0, 6000.0, 250.0)
    tail, _ = launch_zone(AIM120A, 270.0, 6000.0, -250.0)
    assert head_on > tail > 0
    rmax9, _ = launch_zone(AIM9M, 270.0, 6000.0, 0.0)
    assert rmax9 < head_on


def test_ir_missile_hits_target_from_behind(world, make_aircraft):
    shooter = make_aircraft(pos=(0, 0, 5000))
    target = make_aircraft(pos=(0, 2500, 5000), team="red", name="tgt")
    target.controls.throttle = 1.0
    shooter.select("AIM-9M")
    run(world, 0.2)
    assert shooter.ir_seeker.candidate is target
    assert shooter.toggle_ir_lock()
    m = shooter.fire_missile(world)
    assert m.seeker.target is target
    run(world, 8.0)
    assert not target.alive


def test_flares_can_decoy_a_seeker_without_irccm(world, make_aircraft):
    spec = dataclasses.replace(AIM9M, ccm=0.0)
    shooter = make_aircraft(pos=(0, 0, 5000))
    target = make_aircraft(pos=(0, 3000, 5000), team="red", name="tgt")
    m = Missile(spec, shooter, Vec3(0, 10, 5000), Vec3(0, 260, 0), Vec3(0, 1, 0), random.Random(3), target=target)
    world.missiles.append(m)
    decoyed = False
    for _ in range(6):
        world.add_flare(Flare(target.pos + Vec3(0, -3, -2), target.vel * 0.9, ALE47))
        for _ in range(18):
            run(world, 1.0 / 60.0)
            decoyed = decoyed or getattr(m.seeker.target, "is_flare", False)
    assert decoyed


def test_aim120_datalink_then_pitbull(world, make_aircraft):
    shooter = make_aircraft(pos=(0, 0, 6000))
    target = make_aircraft(pos=(0, 30000, 6000), heading=180.0, team="red", name="tgt")
    shooter.select("AIM-120A")
    assert shooter.radar.try_lock(target)
    run(world, 1.0)
    assert shooter.radar.mode == STT and shooter.radar.locked is target
    m = shooter.fire_missile(world)
    assert m.intended is target
    run(world, 3.0)
    assert m.datalink and not m.active
    for _ in range(200):
        run(world, 0.1)
        if m.active:
            break
    assert m.active
    # the seeker goes active at 16 km but needs to get closer to see a nose-on F-16
    for _ in range(100):
        run(world, 0.1)
        if m.arh_target is not None or not m.alive:
            break
    assert m.arh_target is target or not target.alive


def test_maddog_goes_active_immediately(world, make_aircraft):
    shooter = make_aircraft(pos=(0, 0, 6000))
    shooter.radar.toggle_power()
    shooter.select("AIM-120A")
    m = shooter.fire_missile(world)
    assert m.active and m.intended is None
