import math
import random

from panda3d.core import Vec3

from conftest import run
from dogfight.mathutil import quat_look
from dogfight.sim.ir_seeker import IRSeeker
from dogfight.sim.radar import ACM, SEARCH, STT
from dogfight.sim.signatures import ir_intensity, ir_lock_range
from dogfight.sim.specs import AIM9M


def test_search_detects_target_ahead(world, make_aircraft):
    me = make_aircraft()
    bandit = make_aircraft(pos=(2000, 30000, 5500), heading=180.0, team="red")
    run(world, 2.5)
    assert bandit in me.radar.contacts
    assert me.radar.selected is bandit


def test_target_behind_is_not_seen(world, make_aircraft):
    me = make_aircraft()
    bandit = make_aircraft(pos=(0, -10000, 5000), team="red")
    run(world, 2.5)
    assert bandit not in me.radar.contacts


def test_lock_button_locks_selected_contact(world, make_aircraft):
    me = make_aircraft()
    bandit = make_aircraft(pos=(0, 25000, 5000), heading=180.0, team="red")
    run(world, 2.5)
    assert me.radar.lock_button() == "locking"
    run(world, 1.0)
    assert me.radar.mode == STT and me.radar.locked is bandit
    assert me.radar.lock_button() == "unlocked"
    assert me.radar.mode == SEARCH


def test_beaming_target_breaks_lock(world, make_aircraft):
    me = make_aircraft()
    bandit = make_aircraft(pos=(0, 20000, 5000), heading=180.0, team="red")
    assert me.radar.try_lock(bandit)
    run(world, 1.0)
    assert me.radar.mode == STT
    # turn the bandit onto the 3/9 line: zero radial speed = in the doppler notch
    bandit.fm.quat = quat_look(Vec3(1, 0, 0))
    bandit.fm.vel = Vec3(250.0, 0.0, 0.0)
    assert me.radar.in_notch(bandit)
    run(world, 1.5)
    assert me.radar.locked is not bandit


def test_acm_auto_locks_target_in_front(world, make_aircraft):
    me = make_aircraft()
    bandit = make_aircraft(pos=(0, 6000, 5200), heading=180.0, team="red")
    me.radar.contacts.clear()
    me.radar.selected = None
    assert me.radar.lock_button() == "acm"
    assert me.radar.mode == ACM
    run(world, 1.0)
    assert me.radar.mode == STT and me.radar.locked is bandit


def test_rwr_sees_lock(world, make_aircraft):
    me = make_aircraft()
    bandit = make_aircraft(pos=(0, 20000, 5000), heading=180.0, team="red")
    assert bandit.radar.try_lock(me)
    run(world, 1.0)
    levels = {t.level for t in me.rwr.threats}
    assert "lock" in levels


def test_ir_range_rear_vs_front(world, make_aircraft):
    target = make_aircraft(pos=(0, 0, 5000))
    behind = Vec3(0, -5000, 5000)
    ahead = Vec3(0, 5000, 5000)
    rear_range = ir_lock_range(AIM9M.seeker_range, ir_intensity(target, behind))
    front_range = ir_lock_range(AIM9M.seeker_range, ir_intensity(target, ahead))
    assert rear_range > 2.0 * front_range
    target.fm.engine = 1.1
    ab_range = ir_lock_range(AIM9M.seeker_range, ir_intensity(target, behind))
    assert ab_range > rear_range


def test_seeker_tone_and_lock(world, make_aircraft):
    me = make_aircraft()
    target = make_aircraft(pos=(0, 3000, 5000), team="red")
    seeker = IRSeeker(AIM9M, random.Random(1))
    seeker.update(0.03, me.pos, me.forward, world.heat_sources(), world.terrain, exclude=me)
    assert seeker.tone() == "lock"
    assert seeker.lock()

    def sweep(start_deg, end_deg, steps):
        result = None
        for k in range(steps + 1):
            a = math.radians(start_deg + (end_deg - start_deg) * k / steps)
            target.fm.pos = Vec3(3000 * math.sin(a), 3000 * math.cos(a), 5000)
            result = seeker.update(1 / 30, me.pos, me.forward, world.heat_sources(), world.terrain,
                                   exclude=me) or result
        return result

    # the target drifts 20 deg off the nose at 15 deg/s: a locked head follows it
    assert sweep(0.0, 20.0, 40) is None
    assert seeker.target is target
    # beyond the 40 deg gimbal limit the lock breaks
    assert sweep(20.0, 50.0, 60) == "lost"
    assert not seeker.locked


def test_quick_lock_picks_target_closest_to_view(world, make_aircraft):
    me = make_aircraft()
    left = make_aircraft(pos=(-6000, 20000, 5000), heading=180.0, team="red")
    right = make_aircraft(pos=(4000, 20000, 5000), heading=180.0, team="red")
    look = Vec3(4000, 20000, 0)
    look.normalize()
    assert me.radar.quick_lock(world, look) == "locking"
    run(world, 0.6)
    assert me.radar.mode == STT and me.radar.locked is right
    # pressed again: moves on to the other enemy
    assert me.radar.quick_lock(world, look) == "locking"
    run(world, 0.6)
    assert me.radar.locked is left


def test_quick_lock_ignores_targets_far_from_view(world, make_aircraft):
    me = make_aircraft()
    make_aircraft(pos=(15000, 15000, 5000), heading=180.0, team="red")     # 45 deg off
    assert me.radar.quick_lock(world, Vec3(0, 1, 0)) == "none"


def test_ir_lock_assist_locks_off_boresight_target(world, make_aircraft):
    me = make_aircraft()
    me.lock_assist = True
    me.radar.toggle_power()                                     # no radar slaving
    bandit = make_aircraft(pos=(300, 3000, 5000), heading=0.0, team="red")   # ~6 deg off the nose, tail on
    assert me.select("AIM-9M")
    run(world, 0.3)
    assert me.ir_seeker.locked and me.ir_seeker.target is bandit


def test_ir_without_assist_needs_target_in_narrow_fov(world, make_aircraft):
    me = make_aircraft()
    me.radar.toggle_power()
    make_aircraft(pos=(300, 3000, 5000), heading=0.0, team="red")
    me.select("AIM-9M")
    run(world, 0.3)
    assert me.ir_seeker.candidate is None and not me.ir_seeker.locked
