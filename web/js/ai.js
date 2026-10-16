// Mouse-aim instructor, player pilot and enemy AI (port of dogfight/ai/*.py and controls.py).
import { G, DEG, V, add, sub, mul, dot, cross, len, norm, clamp, smoothstep, angleBetween, bankAngle, wrap } from './util.js';
import { ARH } from './specs.js';
import { STT, gunLead, launchZone } from './weapons.js';
import { AI_DT } from './sim.js';

// Mouse-aim "instructor" (War Thunder style): swings the flight path - or with `nose` the nose itself -
// towards `direction`.
//  * the demanded turn rate grows with the angle to the target, so small corrections are gentle
//  * small corrections are flown with little bank plus rudder instead of a big roll
//  * a target a bit below is reached by pushing (negative G), not by rolling inverted; pull/push is chosen
//    with hysteresis, so the aircraft never flip-flops between the two
export function steerTowards(fm, direction, c, maxGFrac = 1, precision = 1, nose = false) {
  const s = fm.spec, q = fm.quat, right = fm.right, up = fm.up, fwd = fm.forward;
  const path = nose || fm.speed <= 30 ? fwd : norm(fm.vel, fwd);
  const lift = norm(cross(right, path), up), side = cross(path, lift);
  const d = norm(direction);
  const off = Math.acos(clamp(dot(d, path), -1, 1));
  const speed = Math.max(fm.speed, 60);
  let perp = sub(d, mul(path, dot(d, path)));
  if (len(perp) > 1e-6) perp = norm(perp);
  const behind = smoothstep(120 * DEG, 170 * DEG, off);
  if (behind > 0 || len(perp) < 0.5) {
    let flat = cross(path, V(0, 0, 1));
    if (len(flat) < 1e-3) flat = right.clone();
    flat = norm(flat);
    let sign = dot(perp, flat);
    if (Math.abs(sign) < 0.15) sign = bankAngle(q) >= 0 ? 1 : -1;
    flat = mul(flat, sign >= 0 ? 1 : -1);
    perp = norm(add(mul(perp, 1 - behind), mul(flat, Math.max(behind, 0.01))), flat);
  }
  // turn rate demand (PD: a path already swinging towards the target eases off)
  const closingRate = dot(fm.accel, perp) / speed;
  const rate = clamp(off * 0.9 * precision - 0.5 * closingRate * (1 - behind), 0, 1.0);
  const acc = add(mul(perp, rate * speed), V(0, 0, G));
  acc.addScaledVector(path, -dot(acc, path));
  const aG = len(acc) / G;
  const rollPull = Math.atan2(dot(acc, side), dot(acc, lift)), rollPush = wrap(rollPull + Math.PI);
  // pull (lift towards the target) or push (lift away, negative G)?
  // modest corrections below are always pushed (the push saturates at about -2.5 G); bigger ones only if
  // the push needed is within limits
  const pushOk = behind === 0 && (off < 40 * DEG || (aG <= -s.gMin * 0.85 && off < 60 * DEG));
  const costPull = Math.abs(rollPull), costPush = Math.abs(rollPush) + 25 * DEG;
  let push = !!fm.steerPush && pushOk;
  if (pushOk && (push ? costPull + 20 * DEG < costPush : costPush + 20 * DEG < costPull)) push = !push;
  fm.steerPush = push;
  let rollErr = push ? rollPush : rollPull;
  // small corrections: keep the bank small (the rudder below does the rest)
  if (off < 45 * DEG && behind === 0) {
    // (nose mode: banks into the turn earlier, so the nose settles on the cursor instead of creeping)
    const cur = bankAngle(q), lim = (20 + 160 * smoothstep((nose ? 2 : 4) * DEG, (nose ? 22 : 40) * DEG, off)) * DEG;
    const base = push && Math.abs(cur) > Math.PI / 2 ? Math.PI : 0;        // inverted flight: limit around 180
    const want = wrap(cur + rollErr - base);
    rollErr = wrap(clamp(want, -lim, lim) + base - cur);
  }
  // load factor along the lift direction we are rolling to, applied as the roll gets there
  const target = add(mul(lift, Math.cos(rollErr)), mul(side, Math.sin(rollErr)));
  let nz = dot(acc, target) / G;
  nz = 1 + (nz - 1) * Math.max(0, Math.cos(clamp(rollErr, -Math.PI / 2, Math.PI / 2)));
  nz = clamp(nz, s.gMin * 0.85, s.gMax * maxGFrac);
  c.roll = clamp(rollErr * 1.8 - fm.omega.y * 0.3, -1, 1);
  c.pitch = clamp(nz >= 1 ? (nz - 1) / (s.gMax - 1) : (nz - 1) / (1 - s.gMin), -1, 1);
  const fine = 1 - smoothstep((nose ? 6 : 3) * DEG, (nose ? 20 : 12) * DEG, off);
  c.yaw = clamp(Math.atan2(dot(d, side), dot(d, path)) * 4 * precision, -1, 1) * fine;
  if (fm.onGround) {
    const he = wrap(Math.atan2(d.x, d.y) - Math.atan2(fwd.x, fwd.y));
    c.roll = 0; c.yaw = clamp(he * 3, -1, 1);
    c.pitch = clamp(Math.asin(clamp(d.z, -1, 1)) * 4, 0, 1);
  }
  return off;
}

const PLAYER_G = 0.85;

export class PlayerPilot {
  constructor(ac) { this.ac = ac; this.aim = ac.forward.clone(); this.pitch = null; this.roll = null; this.yaw = null; ac.pilot = this; }
  think() {}
  get manual() { return this.pitch !== null || this.roll !== null; }
  fly() {
    const c = this.ac.controls, fm = this.ac.fm;
    if (this.manual) {
      // keyboard flying (like War Thunder): the instructor lets go, the jet does exactly what the keys say;
      // an axis without a key holds its attitude instead of fighting the pilot
      c.pitch = this.pitch !== null ? this.pitch : 0;
      c.roll = this.roll !== null ? this.roll : clamp(-fm.omega.y * 0.5, -1, 1);
      c.yaw = this.yaw !== null ? this.yaw : 0;
      // extreme mode: a full pull lets the jet go past the AoA limit (Cobra)
      c.postStall = fm.extreme && c.pitch >= 0.95;
      return;
    }
    // the instructor keeps a little G margin (~7.6 G) so the pilot does not black out; S pulls the full 9 G.
    // In extreme mode (thrust vectoring) it flies the full 9 G turns itself.
    // It puts the nose on the cursor (not the direction of flight), so the jet always points where you aim.
    c.postStall = false;
    steerTowards(fm, this.aim, c, fm.extreme ? 1 : PLAYER_G, fm.extreme ? 1.5 : 1.3, true);
    if (this.yaw !== null) c.yaw = this.yaw;
  }
}

// The AI flies the same jets as the player (with a weaker airframe, specs.js BANDITS); its pilot is a little
// weaker too: less G, less precise, slower to notice missiles, and it only fires inside a cautious part of the
// launch zone.  With an `area` (the combat zone) it patrols there and only goes for enemies inside the zone
// (plus a margin), never for anyone near the home base: taking off and landing is safe.
// maxIr / maxArh: the farthest they ever shoot (m).  Kept well inside what the player can lock and answer,
// so nobody gets a missile from 15 km out of nowhere.
const SKILLS = {
  easy: { g: 0.6, precision: 0.65, missileCd: 36, cm: 0.3, aware: 0.2, gunCone: 0.7, arh: false, zone: 0.5, maxIr: 3500, maxArh: 0 },
  normal: { g: 0.8, precision: 0.85, missileCd: 24, cm: 0.6, aware: 0.45, gunCone: 1.0, arh: true, zone: 0.7, maxIr: 4500, maxArh: 8000 },
  hard: { g: 0.92, precision: 0.95, missileCd: 15, cm: 0.9, aware: 0.75, gunCone: 1.4, arh: true, zone: 0.8, maxIr: 5500, maxArh: 10000 },
};
const MIN_AGL = 450;

export class AIPilot {
  constructor(ac, skill = 'normal', area = null) {
    this.ac = ac; this.skill = SKILLS[skill]; this.rnd = ac.rnd; this.area = area;
    this.state = 'patrol'; this.target = null; this.threat = null; this.aware = new Set(); this.defendTimer = 0;
    this.missileTimer = this.rnd.uniform(6, 14); this.patrolAlt = ac.pos.z;
    this.waypoint = this.patrolPoint();
    ac.pilot = this;
  }
  patrolPoint() {
    const a = this.area, r = this.rnd;
    if (!a) return V(r.uniform(-20000, 20000), r.uniform(-20000, 20000), this.patrolAlt);
    const ang = r.uniform(0, 2 * Math.PI), d = a.r * 0.8 * Math.sqrt(r());
    return V(a.x + Math.sin(ang) * d, a.y + Math.cos(ang) * d, this.patrolAlt);
  }
  // may this enemy be attacked?  inside the combat zone (+ margin) and not in the base's safe area
  fair(t) {
    const a = this.area;
    if (!a) return true;
    if (a.safe && Math.hypot(t.pos.x - a.safe.x, t.pos.y - a.safe.y) < a.safe.r) return false;
    return Math.hypot(t.pos.x - a.x, t.pos.y - a.y) < a.engage;
  }
  think(world) {
    const ac = this.ac;
    this.missileTimer -= AI_DT; ac.trigger = false;
    const enemies = world.enemiesOf(ac).filter((e) => this.fair(e));
    this.target = enemies.reduce((b, e) => (!b || len(sub(e.pos, ac.pos)) < len(sub(b.pos, ac.pos)) ? e : b), null);
    const threat = this.findThreat(world);
    if (threat) { this.threat = threat; this.state = 'defend'; this.defendTimer = 2.5; }
    else if (this.defendTimer > 0) { this.defendTimer -= AI_DT; if (this.threat && !this.threat.alive) this.defendTimer = Math.min(this.defendTimer, 0.5); }
    else { this.threat = null; this.state = this.target ? 'engage' : 'patrol'; }
    const t = this.target;
    if (!t) return;
    const d = len(sub(t.pos, ac.pos)), r = ac.radar;
    if (!r.on) r.togglePower();
    if (r.locked !== t && r.pending !== t && d < r.spec.lockRange) r.tryLock(t);
    if (this.state === 'engage') this.weapons(world, t, d);
  }
  findThreat(world) {
    const ac = this.ac;
    let best = null, bd = 1e9;
    for (const m of world.missiles) {
      if (!m.alive || !m.shooter || m.shooter.team === ac.team) continue;
      if (m.guidedTarget !== ac && m.intended !== ac) continue;
      const d = len(sub(m.pos, ac.pos));
      if (!this.aware.has(m.id)) {
        const warned = m.spec.guidance === ARH && ac.rwr.threats.some((t) => t.level === 'launch' && (t.source === m || t.source === m.shooter));
        const spotted = d < 4500 && this.rnd() < this.skill.aware * 0.5;
        if (warned || spotted) this.aware.add(m.id); else continue;
      }
      if (d < bd) { best = m; bd = d; }
    }
    return best;
  }
  gunSolution(t) { return gunLead(this.ac.pos, this.ac.vel, t.pos, t.vel, this.ac.spec.gun, 2)[0]; }
  weapons(world, t, d) {
    const ac = this.ac;
    if (d < 1100 && angleBetween(ac.forward, this.gunSolution(t)) < this.skill.gunCone * DEG) ac.trigger = true;
    if (this.missileTimer > 0) return;
    let fired = null;
    const closingT = -dot(t.vel, norm(sub(t.pos, ac.pos)));
    const zone = (key) => launchZone(ac.missileSpec(key), ac.speed, ac.pos.z, closingT)[0] * this.skill.zone;
    if (ac.missileCount('AIM-9M') && d > 900 && d < Math.min(this.skill.maxIr, zone('AIM-9M'))) {
      if (ac.selected !== 'AIM-9M') ac.select('AIM-9M');
      else if (ac.irSeeker.candidate === t || ac.irSeeker.target === t) {
        if (!ac.irSeeker.locked) ac.irSeeker.lock();
        if (ac.irSeeker.target === t) fired = ac.fireMissile(world);
      }
    } else if (ac.missileCount('AIM-120A') && this.skill.arh && ac.radar.mode === STT && ac.radar.locked === t) {
      if (d > 2500 && d < Math.min(this.skill.maxArh, zone('AIM-120A'))) {
        if (ac.selected !== 'AIM-120A') ac.select('AIM-120A');
        fired = ac.fireMissile(world);
      }
    }
    if (fired) this.missileTimer = this.skill.missileCd * this.rnd.uniform(0.8, 1.3);
  }
  fly(dt, world) {
    const ac = this.ac, terr = world.terrain;
    let desired, throttle = 1, maxG = this.skill.g;
    if (this.state === 'defend' && this.threat && this.threat.alive) [desired, throttle, maxG] = this.defend(world);
    else if (this.state === 'engage' && this.target) [desired, throttle] = this.pursue(this.target);
    else [desired, throttle] = this.patrol();
    const agl = ac.pos.z - terr.height(ac.pos.x, ac.pos.y);
    const ahead = add(ac.pos, mul(ac.vel, 4));
    const aglAhead = ahead.z - terr.height(ahead.x, ahead.y);
    if (aglAhead < MIN_AGL || agl < MIN_AGL * 0.7) { desired = norm(add(norm(V(ac.vel.x, ac.vel.y, 0)), V(0, 0, 0.9))); maxG = 1; }
    else if (agl < 1800 && desired.z < -0.15) desired = norm(V(desired.x, desired.y, -0.15));
    if (Math.abs(ac.pos.x) > 42000 || Math.abs(ac.pos.y) > 42000) desired = norm(add(norm(V(-ac.pos.x, -ac.pos.y, 0)), mul(desired, 0.3)));
    const a = this.area;
    if (a && Math.hypot(ac.pos.x - a.x, ac.pos.y - a.y) > a.engage + 4000) desired = norm(add(norm(V(a.x - ac.pos.x, a.y - ac.pos.y, 0)), mul(desired, 0.3)));
    steerTowards(ac.fm, desired, ac.controls, maxG, this.skill.precision);
    ac.controls.throttle = throttle;
  }
  pursue(t) {
    const ac = this.ac, rel = sub(t.pos, ac.pos), d = len(rel);
    const desired = d < 2500 ? this.gunSolution(t) : norm(add(rel, mul(t.vel, Math.min(d / 600, 6) * 0.5)));
    let throttle = 1;
    if (d > 5000 || ac.speed < 190) throttle = 1.1;
    else if (d < 900 && -dot(sub(t.vel, ac.vel), norm(rel)) > 80) throttle = 0.6;
    return [desired, throttle];
  }
  defend(world) {
    const ac = this.ac, m = this.threat, los = sub(m.pos, ac.pos), d = len(los);
    const flat = norm(V(los.x, los.y, 0));
    let perp = V(-flat.y, flat.x, 0);
    if (dot(perp, ac.vel) < 0) perp = mul(perp, -1);
    const agl = ac.pos.z - world.terrain.height(ac.pos.x, ac.pos.y);
    const useCm = this.rnd() < this.skill.cm * 0.25;
    if (m.spec.guidance === ARH) {
      if (d < 14000 && useCm) ac.dispense(world);
      return [norm(add(perp, V(0, 0, agl > 2500 ? -0.25 : 0))), 1, this.skill.g];
    }
    if (d < 3500) {
      if (useCm || d < 1500) ac.dispense(world);
      return [norm(add(sub(perp, mul(flat, 0.3)), V(0, 0, -0.1))), 0.65, 1];
    }
    return [norm(add(mul(flat, -1), V(0, 0, -0.05))), 1.1, this.skill.g];
  }
  patrol() {
    const ac = this.ac, to = sub(this.waypoint, ac.pos);
    if (len(V(to.x, to.y, 0)) < 3000) this.waypoint = this.patrolPoint();
    const climb = clamp((this.patrolAlt - ac.pos.z) / 3000, -0.3, 0.3);
    return [norm(add(norm(V(to.x, to.y, 0)), V(0, 0, climb))), 0.95];
  }
}
