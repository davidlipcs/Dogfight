// Mouse-aim instructor, player pilot and enemy AI (port of dogfight/ai/*.py and controls.py).
import { G, DEG, V, add, sub, mul, dot, cross, len, norm, clamp, smoothstep, angleBetween, bankAngle, wrap } from './util.js';
import { ARH } from './specs.js';
import { STT, gunLead } from './weapons.js';
import { AI_DT } from './sim.js';

export function steerTowards(fm, direction, c, maxGFrac = 1, precision = 1) {
  const s = fm.spec, q = fm.quat, right = fm.right, up = fm.up, fwd = fm.forward;
  const path = fm.speed > 30 ? norm(fm.vel, fwd) : fwd;
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
  const closingRate = dot(fm.accel, perp) / speed;
  const rate = clamp(off * 1.3 * precision - 0.6 * closingRate * (1 - behind), 0, 1.2);
  const acc = add(mul(perp, rate * speed), V(0, 0, G));
  acc.addScaledVector(path, -dot(acc, path));
  let rollErr = Math.atan2(dot(acc, side), dot(acc, lift));
  let nz = len(acc) / G;
  if (Math.abs(rollErr) > 100 * DEG && nz < 2) { rollErr = wrap(rollErr + Math.PI); nz = -nz; }
  c.roll = clamp(rollErr * 2.6 - fm.omega.y * 0.25, -1, 1);
  const align = Math.cos(clamp(rollErr, -Math.PI / 2, Math.PI / 2));
  if (nz > 0) nz *= align;
  nz = clamp(nz, s.gMin, s.gMax * maxGFrac);
  c.pitch = clamp(nz >= 1 ? (nz - 1) / (s.gMax - 1) : (nz - 1) / (1 - s.gMin), -1, 1);
  const fine = 1 - smoothstep(1 * DEG, 4 * DEG, off);
  c.yaw = clamp(Math.atan2(dot(d, side), dot(d, path)) * 5 * precision, -1, 1) * fine;
  if (fm.onGround) {
    const he = wrap(Math.atan2(d.x, d.y) - Math.atan2(fwd.x, fwd.y));
    c.roll = 0; c.yaw = clamp(he * 3, -1, 1);
    c.pitch = clamp(Math.asin(clamp(d.z, -1, 1)) * 4, 0, 1);
  }
  return off;
}

export class PlayerPilot {
  constructor(ac) { this.ac = ac; this.aim = ac.forward.clone(); this.pitch = null; this.roll = null; this.yaw = null; ac.pilot = this; }
  think() {}
  fly() {
    const c = this.ac.controls;
    steerTowards(this.ac.fm, this.aim, c);
    if (this.pitch !== null) c.pitch = this.pitch;
    if (this.roll !== null) c.roll = this.roll;
    if (this.yaw !== null) c.yaw = this.yaw;
  }
}

const SKILLS = {
  easy: { g: 0.65, precision: 0.7, missileCd: 32, cm: 0.35, aware: 0.25, gunCone: 0.8, arh: false },
  normal: { g: 0.85, precision: 0.9, missileCd: 20, cm: 0.7, aware: 0.5, gunCone: 1.2, arh: true },
  hard: { g: 1, precision: 1, missileCd: 12, cm: 1, aware: 0.85, gunCone: 1.6, arh: true },
};
const MIN_AGL = 450;

export class AIPilot {
  constructor(ac, skill = 'normal') {
    this.ac = ac; this.skill = SKILLS[skill]; this.rnd = ac.rnd;
    this.state = 'patrol'; this.target = null; this.threat = null; this.aware = new Set(); this.defendTimer = 0;
    this.missileTimer = this.rnd.uniform(6, 14); this.patrolAlt = ac.pos.z;
    this.waypoint = V(this.rnd.uniform(-15000, 15000), this.rnd.uniform(-15000, 15000), this.patrolAlt);
    ac.pilot = this;
  }
  think(world) {
    const ac = this.ac;
    this.missileTimer -= AI_DT; ac.trigger = false;
    const enemies = world.enemiesOf(ac);
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
    if (ac.missileCount('AIM-9M') && d > 900 && d < 7000) {
      if (ac.selected !== 'AIM-9M') ac.select('AIM-9M');
      else if (ac.irSeeker.candidate === t || ac.irSeeker.target === t) {
        if (!ac.irSeeker.locked) ac.irSeeker.lock();
        if (ac.irSeeker.target === t) fired = ac.fireMissile(world);
      }
    } else if (ac.missileCount('AIM-120A') && this.skill.arh && ac.radar.mode === STT && ac.radar.locked === t) {
      const closing = -dot(sub(t.vel, ac.vel), norm(sub(t.pos, ac.pos)));
      if (d > 2500 && d < (closing > 150 ? 24000 : 11000)) {
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
    if (len(V(to.x, to.y, 0)) < 3000) this.waypoint = V(this.rnd.uniform(-20000, 20000), this.rnd.uniform(-20000, 20000), this.patrolAlt);
    const climb = clamp((this.patrolAlt - ac.pos.z) / 3000, -0.3, 0.3);
    return [norm(add(norm(V(to.x, to.y, 0)), V(0, 0, climb))), 0.95];
  }
}
