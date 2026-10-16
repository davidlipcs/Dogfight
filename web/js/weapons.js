// Sensors and weapons: IR seeker, APG-68 radar, RWR, missiles, gun, decoys
// (port of dogfight/sim/{signatures,ir_seeker,radar,rwr,missile,guns,countermeasures}.py).
import {
  G, DEG, V, add, sub, mul, dot, cross, len, norm, copy, clamp, smoothstep, angleBetween, interp, rotateTowards,
  closestApproach, toLocal, xform,
} from './util.js';
import { isa } from './flight.js';
import { IR, ARH } from './specs.js';

// ------------------------------------------------------------------ signatures
export function irIntensity(src, obs) {
  if (src.isFlare) return src.intensity;
  return irIntensityRaw(src, obs) * (src.spec && src.spec.irScale ? src.spec.irScale : 1);   // F-22: cooler, shielded exhaust
}
function irIntensityRaw(src, obs) {
  if (!src.alive && !src.burning) return 0;
  const toObs = norm(sub(obs, src.pos));
  const rear = -dot(src.forward, toObs);
  const nozzle = 0.15 + 0.85 * smoothstep(-0.35, 0.95, rear);
  const e = src.engineSetting;
  let heat, plume = 0;
  if (e > 1) { heat = 2.0 + 0.4 * (e - 1) / 0.1; plume = 0.35; } else heat = 0.25 + 0.75 * Math.pow(clamp(e, 0, 1), 1.5);
  return heat * nozzle + plume + 0.06 * src.mach * src.mach + (src.burning ? 1.5 : 0);
}
export const irLockRange = (base, I) => (I <= 0 ? 0 : Math.min(base * Math.sqrt(I), base * 1.5));
export function rcs(tgt, obs) {
  const toObs = norm(sub(obs, tgt.pos));
  const side = 1 - Math.abs(dot(tgt.forward, toObs));
  const r = tgt.spec.rcsFront + (tgt.spec.rcsSide - tgt.spec.rcsFront) * side;
  // F-22 with a weapons bay door open: the cavity and the missile shine on radar for a moment
  return tgt.spec.rcsBay && tgt.bayOpenAny > 0.2 ? Math.max(r, tgt.spec.rcsBay * tgt.bayOpenAny) : r;
}
export const radarRange = (base, r) => base * Math.pow(Math.max(r, 1e-5) / 5, 0.25);     // no floor: stealth works
export const radialSpeed = (vel, obs, pos) => dot(vel, norm(sub(pos, obs)));

// ------------------------------------------------------------- countermeasures
let ids = 1;
export class Flare {
  constructor(pos, vel, cm) {
    this.id = ids++; this.isFlare = true; this.alive = true;
    this.pos = copy(pos); this.vel = copy(vel); this.age = 0; this.life = cm.flareLife; this.peak = cm.flareIntensity;
  }
  get intensity() {
    if (this.age < 0.15) return this.peak * this.age / 0.15;
    return this.peak * Math.pow(Math.max(0, 1 - (this.age - 0.15) / (this.life - 0.15)), 0.7);
  }
  update(dt) {
    this.age += dt;
    const s = len(this.vel);
    this.vel.multiplyScalar(1 - Math.min(1, 0.0025 * s * dt));
    this.vel.z -= G * dt;
    this.pos.addScaledVector(this.vel, dt);
    if (this.age >= this.life) this.alive = false;
  }
}
export class Chaff {
  constructor(pos, vel, cm) {
    this.id = ids++; this.isChaff = true; this.alive = true;
    this.pos = copy(pos); this.vel = mul(vel, 0.3); this.age = 0; this.life = cm.chaffLife;
  }
  update(dt) {
    this.age += dt;
    this.vel.multiplyScalar(1 - Math.min(1, 3 * dt));
    this.vel.z -= 1.5 * dt;
    this.pos.addScaledVector(this.vel, dt);
    if (this.age >= this.life) this.alive = false;
  }
}

// --------------------------------------------------------------------- IR seeker
export class IRSeeker {
  constructor(spec, rnd) {
    this.spec = spec; this.rnd = rnd; this.axis = null; this.target = null; this.candidate = null; this.judged = new Set();
    this.acqFov = null;        // wider search cone (deg) for the player's lock assist; null = real seeker FOV
    this.snap = false;
  }
  get locked() { return this.target !== null; }
  reset() { this.target = null; this.candidate = null; this.judged.clear(); }
  visible(src, origin, terrain) {
    if (!src.alive) return false;
    const d = len(sub(src.pos, origin));
    if (d > irLockRange(this.spec.seekerRange, irIntensity(src, origin))) return false;
    return !terrain || terrain.lineOfSight(origin, src.pos);
  }
  bestInCone(origin, axis, sources, half, terrain, exclude) {
    let best = null, bestScore = 0;
    for (const s of sources) {
      if (s === exclude || !s.alive) continue;
      const to = sub(s.pos, origin), d = len(to);
      if (d < 1) continue;
      const off = angleBetween(axis, to);
      if (off > half) continue;
      const I = irIntensity(s, origin);
      if (d > irLockRange(this.spec.seekerRange, I)) continue;
      const score = I / (d * d) * (1 - 0.5 * off / half);
      if (score > bestScore && (!terrain || terrain.lineOfSight(origin, s.pos))) { best = s; bestScore = score; }
    }
    return best;
  }
  update(dt, origin, boresight, sources, terrain, slaveDir = null, exclude = null) {
    const sp = this.spec, fov = sp.seekerFov * DEG;
    if (!this.axis) this.axis = norm(boresight);
    if (!this.target) {
      let want = slaveDir || boresight;
      if (angleBetween(boresight, want) > sp.gimbal * DEG) want = boresight;
      this.axis = norm(want);
      this.candidate = this.bestInCone(origin, this.axis, sources, (this.acqFov || sp.seekerFov) * DEG, terrain, exclude);
      return null;
    }
    const tgt = this.target;
    const desired = norm(sub(tgt.pos, origin));
    if (this.snap) { this.axis = desired; this.snap = false; }     // seeker head jumps onto what it locked
    this.axis = rotateTowards(this.axis, desired, sp.trackRate * DEG * dt);
    this.candidate = tgt;
    if (!this.visible(tgt, origin, terrain) || angleBetween(this.axis, desired) > fov * 1.6
      || angleBetween(boresight, this.axis) > sp.gimbal * DEG) {
      this.target = null; this.candidate = null; return 'lost';
    }
    const heat = irIntensity(tgt, origin);
    for (const s of sources) {
      if (!s.isFlare || s === tgt || this.judged.has(s.id)) continue;
      if (angleBetween(this.axis, sub(s.pos, origin)) > fov * 2) continue;
      if (s.intensity < 0.6 * heat) continue;
      this.judged.add(s.id);
      if (this.rnd() > sp.ccm) { this.target = s; return 'decoyed'; }
    }
    return null;
  }
  lock() { if (this.candidate) { this.target = this.candidate; this.snap = true; return true; } return false; }
  unlock() { this.target = null; }
  tone() { return this.target || this.candidate ? 'lock' : 'growl'; }
}

// ------------------------------------------------------------------------ radar
export const OFF = 'OFF', SEARCH = 'SRCH', ACM = 'ACM', STT = 'STT';
export class Radar {
  constructor(spec, owner, rnd) {
    this.spec = spec; this.owner = owner; this.rnd = rnd;
    this.mode = SEARCH; this.beamAz = -spec.scanAz * DEG; this.beamDir = 1;
    this.contacts = new Map(); this.selected = null; this.locked = null; this.pending = null; this.pendingTime = 0;
    this.lostTime = 0; this.trackPos = null; this.trackVel = null; this.notched = false; this.judged = new Set(); this.lastEvent = null;
  }
  get on() { return this.mode !== OFF; }
  anglesTo(pos) {
    const rel = sub(pos, this.owner.pos), l = toLocal(this.owner.quat, rel);
    return [Math.atan2(l.x, l.y), Math.atan2(l.z, Math.hypot(l.x, l.y)), len(rel)];
  }
  inNotch(t) { return Math.abs(radialSpeed(t.vel, this.owner.pos, t.pos)) < this.spec.notchSpeed; }
  canDetect(t, world, maxRange) {
    if (t === this.owner || !t.alive) return false;
    const d = len(sub(t.pos, this.owner.pos));
    if (d > maxRange || d > radarRange(this.spec.searchRange, rcs(t, this.owner.pos)) || this.inNotch(t)) return false;
    return world.terrain.lineOfSight(this.owner.pos, t.pos);
  }
  togglePower() {
    if (this.mode === OFF) this.mode = SEARCH; else { this.dropLock(); this.mode = OFF; this.contacts.clear(); }
  }
  setAcm() { this.dropLock(); this.mode = ACM; this.pending = null; }
  setSearch() { this.dropLock(); this.mode = SEARCH; }
  tryLock(t) {
    if (this.mode === OFF || !t || !t.alive) return false;
    const [az, el, d] = this.anglesTo(t.pos), gim = this.spec.sttGimbal * DEG;
    if (Math.abs(az) > gim || Math.abs(el) > gim || d > this.spec.lockRange) return false;
    this.pending = t; this.pendingTime = 0; return true;
  }
  lockButton() {
    if (this.mode === OFF) { this.mode = SEARCH; return 'on'; }
    if (this.mode === STT) { this.setSearch(); return 'unlocked'; }
    if (this.mode === SEARCH && this.selected && this.contacts.has(this.selected) && this.tryLock(this.selected)) return 'locking';
    if (this.mode === SEARCH) { this.setAcm(); return 'acm'; }
    this.setSearch(); return 'search';
  }
  // lock assist: lock the enemy closest to `dir` (where the player looks); pressed again it moves on to the
  // next one, or unlocks when there is no other
  quickLock(world, dir, coneDeg = 30) {
    if (this.mode === OFF) this.mode = SEARCH;
    const gim = this.spec.sttGimbal * DEG, own = this.owner;
    const cands = [];
    for (const t of world.aircraft) {
      if (t === own || !t.alive || t.team === own.team) continue;
      const rel = sub(t.pos, own.pos), off = angleBetween(dir, rel);
      const [az, el, d] = this.anglesTo(t.pos);
      if (off > coneDeg * DEG || d > this.spec.lockRange || Math.abs(az) > gim || Math.abs(el) > gim) continue;
      if (!world.terrain.lineOfSight(own.pos, t.pos)) continue;
      cands.push({ t, off });
    }
    cands.sort((a, b) => a.off - b.off);
    const current = this.locked || this.pending;
    if (!cands.length) return current ? 'keep' : 'none';
    let pick = cands[0].t;
    const i = cands.findIndex((c) => c.t === current);
    if (i >= 0) {
      pick = cands[(i + 1) % cands.length].t;
      if (pick === current) { this.setSearch(); return 'unlocked'; }
    }
    this.dropLock(); this.mode = SEARCH;
    if (!this.tryLock(pick)) return 'none';
    this.pendingTime = this.spec.lockTime * 0.5; this.selected = pick;
    return 'locking';
  }
  cycleTarget() {
    if (!this.contacts.size) { this.selected = null; return; }
    const order = [...this.contacts.values()].sort((a, b) => (Math.abs(a.az) + Math.abs(a.el)) - (Math.abs(b.az) + Math.abs(b.el)));
    const ts = order.map((c) => c.target);
    const i = ts.indexOf(this.selected);
    this.selected = i >= 0 ? ts[(i + 1) % ts.length] : ts[0];
  }
  dropLock() { this.locked = null; this.pending = null; this.trackPos = null; this.trackVel = null; this.notched = false; this.lostTime = 0; }
  update(dt, world) {
    this.lastEvent = null;
    const sp = this.spec;
    if (this.mode === OFF) return;
    if (this.mode === SEARCH) this.search(dt, world);
    else if (this.mode === ACM) this.acm(world);
    if (this.mode === STT) this.track(dt, world);
    if (this.pending && this.mode !== STT) this.acquire(dt, world);
    const frame = 2 * (2 * sp.scanAz / sp.scanRate);
    for (const [t, c] of [...this.contacts]) if (world.time - c.time > frame * 1.3 || !t.alive) this.contacts.delete(t);
    if (this.selected && !this.contacts.has(this.selected) && this.selected !== this.locked) this.selected = null;
  }
  search(dt, world) {
    const sp = this.spec, lim = sp.scanAz * DEG, old = this.beamAz;
    this.beamAz += this.beamDir * sp.scanRate * DEG * dt;
    if (this.beamAz > lim || this.beamAz < -lim) { this.beamAz = clamp(this.beamAz, -lim, lim); this.beamDir = -this.beamDir; }
    const lo = Math.min(old, this.beamAz) - 2 * DEG, hi = Math.max(old, this.beamAz) + 2 * DEG;
    for (const t of world.aircraft) {
      if (t === this.owner || !t.alive) continue;
      const [az, el, d] = this.anglesTo(t.pos);
      if (az < lo || az > hi || Math.abs(el) > sp.scanEl * DEG) continue;
      if (this.canDetect(t, world, sp.searchRange * 1.3)) this.contacts.set(t, { target: t, pos: copy(t.pos), vel: copy(t.vel), time: world.time, range: d, az, el });
    }
    if (!this.selected && this.contacts.size) this.cycleTarget();
  }
  acm(world) {
    const sp = this.spec;
    let best = null, bestD = sp.acmRange;
    for (const t of world.aircraft) {
      if (t === this.owner || !t.alive) continue;
      const [az, el, d] = this.anglesTo(t.pos);
      if (Math.abs(az) > sp.acmAz * DEG || el < sp.acmElLow * DEG || el > sp.acmElHigh * DEG) continue;
      if (d < bestD && this.canDetect(t, world, sp.acmRange)) { best = t; bestD = d; }
    }
    if (best && !this.pending) { this.pending = best; this.pendingTime = sp.lockTime * 0.4; }
  }
  acquire(dt, world) {
    const t = this.pending, [az, el, d] = this.anglesTo(t.pos), gim = this.spec.sttGimbal * DEG;
    if (Math.abs(az) > gim || Math.abs(el) > gim || d > this.spec.lockRange || !this.canDetect(t, world, this.spec.lockRange)) { this.pending = null; return; }
    this.pendingTime += dt;
    if (this.pendingTime >= this.spec.lockTime) {
      this.locked = t; this.selected = t; this.pending = null; this.mode = STT; this.lostTime = 0;
      this.trackPos = copy(t.pos); this.trackVel = copy(t.vel); this.judged.clear(); this.lastEvent = 'locked';
    }
  }
  track(dt, world) {
    const t = this.locked, sp = this.spec;
    let valid = t && t.alive;
    this.notched = false;
    let az = 0, el = 0, d = 0;
    if (valid) {
      [az, el, d] = this.anglesTo(t.pos);
      const gim = sp.sttGimbal * DEG;
      this.notched = this.inNotch(t);
      valid = Math.abs(az) <= gim && Math.abs(el) <= gim && d <= sp.lockRange * 1.25 && !this.notched
        && d <= radarRange(sp.searchRange, rcs(t, this.owner.pos)) * 1.2 && world.terrain.lineOfSight(this.owner.pos, t.pos);
    }
    if (valid && this.chaffDecoyed(t, world)) { this.lastEvent = 'decoyed'; this.dropLock(); this.mode = SEARCH; return; }
    if (valid) {
      this.lostTime = 0; this.trackPos = copy(t.pos); this.trackVel = copy(t.vel);
      this.contacts.set(t, { target: t, pos: copy(t.pos), vel: copy(t.vel), time: world.time, range: d, az, el });
      return;
    }
    this.lostTime += dt;
    if (this.trackPos) this.trackPos.addScaledVector(this.trackVel, dt);
    if (this.lostTime > sp.trackMemory) { this.lastEvent = 'lost'; this.dropLock(); this.mode = SEARCH; }
  }
  chaffDecoyed(t, world) {
    if (!world.chaff.length) return false;
    const los = sub(t.pos, this.owner.pos), d = len(los);
    const vr = Math.abs(radialSpeed(t.vel, this.owner.pos, t.pos));
    const eff = 0.55 * (1 - smoothstep(this.spec.notchSpeed, 6 * this.spec.notchSpeed, vr));
    for (const ch of world.chaff) {
      if (this.judged.has(ch.id) || ch.age < 0.3) continue;
      const rel = sub(ch.pos, this.owner.pos);
      if (Math.abs(len(rel) - d) > 600 || angleBetween(rel, los) > 4 * DEG) continue;
      this.judged.add(ch.id);
      if (this.rnd() < eff) return true;
    }
    return false;
  }
  isPainting(t) {
    if (this.mode === STT && this.locked === t) return 'lock';
    if ((this.mode === SEARCH || this.mode === ACM) && this.contacts.has(t)) return 'search';
    if (this.pending === t) return 'lock';
    return null;
  }
}

// -------------------------------------------------------------------------- RWR
const LEVELS = { search: 1, lock: 2, launch: 3 };
export class RWR {
  constructor(owner) { this.owner = owner; this.threats = []; this.incoming = []; this.newSearch = false; this.known = new Set(); }
  get maxLevel() { return this.threats.reduce((m, t) => Math.max(m, LEVELS[t.level]), 0); }
  bearing(pos) { const l = toLocal(this.owner.quat, sub(pos, this.owner.pos)); return Math.atan2(l.x, l.y); }
  update(world) {
    const o = this.owner, found = new Map();
    for (const ac of world.aircraft) {
      if (ac === o || !ac.alive || !ac.radar.on) continue;
      const lvl = ac.radar.isPainting(o);
      if (lvl === 'search' && ac.spec.radar.lpi) continue;       // LPI radar (F-22): not heard while searching
      if (lvl) found.set(ac, { source: ac, symbol: ac.spec.radar.rwrSymbol, level: lvl, bearing: this.bearing(ac.pos) });
    }
    for (const m of world.missiles) {
      if (!m.alive || m.spec.guidance !== ARH || m.guidedTarget !== o) continue;
      if (m.active) found.set(m, { source: m, symbol: 'M', level: 'launch', bearing: this.bearing(m.pos) });
      else if (m.datalink && found.has(m.shooter)) found.get(m.shooter).level = 'launch';
    }
    // missile approach warning (player only): every missile flying at us, IR ones included, that the
    // radar warner alone would miss
    this.incoming = [];
    if (o.isPlayer) {
      for (const m of world.missiles) {
        if (!m.alive || !m.shooter || m.shooter.team === o.team) continue;
        if (m.guidedTarget !== o && m.intended !== o) continue;
        const d = len(sub(m.pos, o.pos));
        if (d > 15000) continue;
        this.incoming.push({ missile: m, dist: d });
        if (!found.has(m)) found.set(m, { source: m, symbol: 'M', level: 'launch', bearing: this.bearing(m.pos) });
      }
      this.incoming.sort((a, b) => a.dist - b.dist);
    }
    this.threats = [...found.values()].sort((a, b) => LEVELS[b.level] - LEVELS[a.level]);
    const keys = new Set(found.keys());
    this.newSearch = [...keys].some((k) => !this.known.has(k));
    this.known = keys;
  }
}

// --------------------------------------------------------------------- missiles
let mids = 1;
export class Missile {
  constructor(spec, shooter, pos, vel, dir, rnd, target = null, irAxis = null) {
    this.id = mids++; this.spec = spec; this.shooter = shooter; this.rnd = rnd;
    this.pos = copy(pos); this.vel = copy(vel); this.dir = norm(dir); this.mass = spec.mass;
    this.age = 0; this.alive = true; this.thrust = 0; this.status = 'LAUNCH';
    this.seeker = null;
    if (spec.guidance === IR) { this.seeker = new IRSeeker(spec, rnd); this.seeker.axis = irAxis ? copy(irAxis) : copy(this.dir); this.seeker.target = target; }
    this.intended = target; this.active = false; this.datalink = false; this.arhTarget = null;
    this.estPos = target ? copy(target.pos) : null; this.estVel = target ? copy(target.vel) : null;
    this.judged = new Set();
    if (spec.guidance === ARH && !target) { this.estPos = add(this.pos, mul(this.dir, spec.seekerRange * 0.8)); this.estVel = V(); this.active = true; }
  }
  get guidedTarget() {
    if (this.spec.guidance === IR) return this.seeker ? this.seeker.target : null;
    if (this.active) return this.arhTarget;
    return this.datalink ? this.intended : null;
  }
  get burning() { return this.age < this.spec.burnTime; }
  motorThrust() {
    let t = this.age;
    for (const [d, th] of this.spec.motor) { if (t < d) return th; t -= d; }
    return 0;
  }
  update(dt, world) {
    if (!this.alive) return;
    const sp = this.spec;
    this.age += dt;
    const [rho, aS] = isa(this.pos.z);
    const speed = Math.max(len(this.vel), 1), vhat = mul(this.vel, 1 / speed), mach = speed / aS, qbar = 0.5 * rho * speed * speed;
    this.thrust = this.motorThrust();
    if (this.thrust > 0) this.mass -= sp.propellant / sp.burnTime * dt;
    let acmd = V();
    if (!this.defeated) this.checkCobra(world);
    if (this.age >= Math.max(sp.guidanceDelay, sp.railTime) && !this.defeated) {
      const aim = this.guidance(dt, world);
      if (aim) { acmd = this.proNav(aim[0], aim[1]); acmd.z += G; }
    } else if (this.defeated) this.status = 'MISSED';
    acmd.addScaledVector(vhat, -dot(acmd, vhat));
    // fins, plus thrust vectoring while the motor burns (spec.tvc: share of the thrust that can push sideways)
    const tvc = sp.tvc && this.thrust > 0 ? this.thrust * sp.tvc / this.mass : 0;
    const aMax = Math.min(sp.maxG * G, qbar * sp.refArea * sp.cnMax / this.mass + tvc);
    let aLen = len(acmd);
    if (aLen > aMax) { acmd.multiplyScalar(aMax / aLen); aLen = aMax; }
    const drag = qbar * sp.refArea * interp(sp.cd, mach) + aLen * this.mass * sp.inducedDrag;
    const acc = add(add(mul(vhat, (this.thrust - drag) / this.mass), acmd), V(0, 0, -G));
    const newVel = add(this.vel, mul(acc, dt));
    if (this.age > sp.armTime) {
      const avg = mul(add(this.vel, newVel), 0.5);
      for (const ac of world.aircraft) {
        if (!ac.alive || ac === this.shooter) continue;            // the fuse never triggers on the launching jet
        const rel = sub(ac.pos, this.pos);
        if (len(rel) > 400) continue;
        const [d, t] = closestApproach(rel, sub(ac.vel, avg), dt);
        if (d <= sp.fuseRadius) { this.pos.addScaledVector(avg, t); world.detonate(this, this.pos); return; }
      }
    }
    this.vel = newVel;
    this.pos.addScaledVector(this.vel, dt);
    if (len(this.vel) > 1) this.dir = norm(this.vel);
    if (this.pos.z <= world.terrain.height(this.pos.x, this.pos.y)) world.detonate(this, this.pos, true);
    else if (this.age > sp.guidanceTime) world.detonate(this, this.pos, false, true);
    else if (!this.burning && speed < 160 && this.age > 3) { this.status = 'SLOW'; if (speed < 110) world.detonate(this, this.pos, false, true); }
  }
  // A target that suddenly stands on its tail (Cobra, AoA > 40 degrees) when the missile is 4 s or less away
  // loses most of its speed in a moment: the missile cannot turn that hard and its seeker loses the target
  // in the clutter - it overshoots.  Too early (more than 4 s) the missile simply re-aims and the jet has
  // thrown away its energy.
  checkCobra(world) {
    const t = this.guidedTarget || this.intended;
    if (!t || !t.fm || !t.alive || t.fm.alpha < 40 * DEG) return;
    const rel = sub(t.pos, this.pos), d = len(rel), closing = -dot(sub(t.vel, this.vel), norm(rel));
    const ttg = closing > 1 ? d / closing : 99;
    if (ttg > 4 || this.cobraJudged) return;
    this.cobraJudged = true;
    if (this.rnd() < (t.isPlayer ? 0.9 : 0.6)) {
      this.defeated = true;
      world.emit('message', { to: t, text: 'COBRA - A RAKÉTA ELVESZTETT!', level: 'good' });
    }
  }
  proNav(aimPos, aimVel) {
    const r = sub(aimPos, this.pos), d2 = Math.max(dot(r, r), 1), vRel = sub(aimVel, this.vel);
    const omega = mul(cross(r, vRel), 1 / d2), rHat = mul(r, 1 / Math.sqrt(d2));
    const vc = Math.max(-dot(vRel, rHat), 0.6 * len(this.vel), 150);
    return mul(cross(omega, rHat), this.spec.navGain * vc);
  }
  guidance(dt, world) { return this.spec.guidance === IR ? this.guidanceIR(dt, world) : this.guidanceARH(dt, world); }
  guidanceIR(dt, world) {
    const s = this.seeker;
    s.update(dt, this.pos, this.dir, world.heatSources(), world.terrain, null, this.shooter);
    if (!s.locked) s.lock();
    if (!s.locked) { this.status = 'LOST'; return null; }
    this.status = s.target.isFlare ? 'FLARE' : 'TRACK';
    return [s.target.pos, s.target.vel];
  }
  guidanceARH(dt, world) {
    const sp = this.spec;
    if (!this.active) {
      const sh = this.shooter, radar = sh && sh.alive ? sh.radar : null;
      if (sp.datalink && radar && radar.mode === STT && radar.locked === this.intended && radar.trackPos) {
        this.estPos = copy(radar.trackPos); this.estVel = copy(radar.trackVel); this.datalink = true; this.status = 'DATALINK';
      } else {
        this.datalink = false;
        if (!this.estPos) return null;
        this.estPos.addScaledVector(this.estVel, dt); this.status = 'INERTIAL';
      }
      if (len(sub(this.estPos, this.pos)) <= sp.seekerRange) { this.active = true; this.datalink = false; world.emit('pitbull', { missile: this }); }
    }
    if (this.active) return this.activeSeeker(dt, world);
    return [this.loft(this.estPos), this.estVel];
  }
  loft(aim) {
    if (!this.spec.loft) return aim;
    const d = len(sub(aim, this.pos)), ang = 22 * DEG * smoothstep(12000, 40000, d);
    return V(aim.x, aim.y, aim.z + Math.tan(ang) * d * 0.5);
  }
  seekerOk(t, world) {
    const sp = this.spec, rel = sub(t.pos, this.pos), d = len(rel);
    if (angleBetween(this.dir, rel) > sp.gimbal * DEG) return false;
    if (t.isChaff) return d < sp.seekerRange && t.alive;
    if (!t.alive || d > radarRange(sp.seekerRange, rcs(t, this.pos))) return false;
    if (Math.abs(radialSpeed(t.vel, this.pos, t.pos)) < (sp.notch ?? 22)) return false;        // beaming: Doppler notch
    return world.terrain.lineOfSight(this.pos, t.pos);
  }
  activeSeeker(dt, world) {
    const sp = this.spec;
    let t = this.arhTarget;
    if (t && !this.seekerOk(t, world)) t = this.arhTarget = null;
    if (t && !t.isChaff) {
      const vr = Math.abs(radialSpeed(t.vel, this.pos, t.pos)), p = (1 - sp.ccm) * (1 - smoothstep(25, 150, vr));
      const los = sub(t.pos, this.pos);
      for (const ch of world.chaff) {
        if (this.judged.has(ch.id) || ch.age < 0.2 || angleBetween(sub(ch.pos, this.pos), los) > 5 * DEG) continue;
        this.judged.add(ch.id);
        if (this.rnd() < p) { t = this.arhTarget = ch; break; }
      }
    }
    if (!t) {
      const axis = this.estPos ? sub(this.estPos, this.pos) : this.dir;
      let best = null, bestScore = 1e18;
      for (const ac of world.aircraft) {
        if (ac === this.shooter || !ac.alive) continue;
        const rel = sub(ac.pos, this.pos);
        if (angleBetween(axis, rel) > sp.seekerFov * DEG || !this.seekerOk(ac, world)) continue;
        let score = len(rel) + (ac !== this.intended ? 2000 : 0);
        if (this.estPos) score += len(sub(ac.pos, this.estPos));
        if (score < bestScore) { best = ac; bestScore = score; }
      }
      t = this.arhTarget = best;
    }
    if (!t) {
      this.status = 'SEARCH';
      if (!this.estPos) return null;
      if (this.estVel) this.estPos.addScaledVector(this.estVel, dt);
      return [this.estPos, this.estVel];
    }
    this.status = t.isChaff ? 'CHAFF' : 'ACTIVE';
    if (!t.isChaff) { this.estPos = copy(t.pos); this.estVel = copy(t.vel); }
    return [t.pos, t.vel];
  }
}

export function timeToImpact(m) {
  const t = m.guidedTarget;
  if (!t) return null;
  const rel = sub(t.pos, m.pos), closing = -dot(sub(t.vel, m.vel), norm(rel));
  return closing > 1 ? len(rel) / closing : null;
}

export function launchZone(spec, launchSpeed, altitude, closing) {
  const fly = (closure) => {
    let mass = spec.mass, v = launchSpeed, x = 0, t = 0;
    const dt = 0.25;
    while (t < spec.guidanceTime) {
      const [rho, aS] = isa(altitude + (spec.loft ? 2500 * Math.min(t / 20, 1) : 0));
      let thrust = 0, tt = t;
      for (const [d, th] of spec.motor) { if (tt < d) { thrust = th; break; } tt -= d; }
      if (t < spec.burnTime) mass -= spec.propellant / spec.burnTime * dt;
      const drag = 0.5 * rho * v * v * spec.refArea * interp(spec.cd, v / aS) * 1.15;
      v += (thrust - drag) / mass * dt; x += v * dt; t += dt;
      if (v < 450 && t > spec.burnTime) break;          // too slow to still out-turn a target
    }
    return Math.max(0, x + closure * t);
  };
  return [fly(closing), fly(-300)];
}

// time a missile launched now needs to fly `range` metres (same 1-D fly-out model as the DLZ); null = never
export function flyoutTime(spec, launchSpeed, altitude, range) {
  let mass = spec.mass, v = launchSpeed, x = 0, t = 0;
  const dt = 0.1, path = range * (spec.loft ? 1.08 : 1.0);
  while (t < spec.guidanceTime) {
    const [rho, aS] = isa(altitude + (spec.loft ? 2500 * Math.min(t / 20, 1) : 0));
    let thrust = 0, tt = t;
    for (const [d, th] of spec.motor) { if (tt < d) { thrust = th; break; } tt -= d; }
    if (t < spec.burnTime) mass -= spec.propellant / spec.burnTime * dt;
    const drag = 0.5 * rho * v * v * spec.refArea * interp(spec.cd, v / aS) * 1.15;
    v += (thrust - drag) / mass * dt; x += v * dt; t += dt;
    if (x >= path) return t;
    if (v < 250 && t > spec.burnTime) return null;
  }
  return null;
}

// -------------------------------------------------------------------------- gun
export const GUN_OFFSET = V(-0.70, 3.95, -0.20);       // the gun port in the left strake
export class Gun {
  constructor(spec, rnd) { this.spec = spec; this.ammo = spec.ammo; this.rnd = rnd; this.firing = false; this.acc = 0; this.count = 0; }
  reload() { this.ammo = this.spec.ammo; }
  update(dt, shooter, trigger, world) {
    const sp = this.spec;
    this.firing = trigger && this.ammo > 0 && shooter.alive;
    if (!this.firing) { this.acc = 0; return; }
    this.acc += dt * sp.rateRpm / 60;
    const n = Math.min(Math.floor(this.acc), this.ammo);
    this.acc -= n;
    if (n <= 0) return;
    const q = shooter.quat, fwd = shooter.forward, right = shooter.fm.right, up = shooter.fm.up;
    const muzzle = add(shooter.pos, xform(q, shooter.spec.gunPos ? V(...shooter.spec.gunPos) : GUN_OFFSET)), sig = sp.dispersionMrad * 1e-3;
    for (let i = 0; i < n; i++) {
      this.ammo--; this.count++;
      const dir = norm(add(add(fwd, mul(right, this.rnd.gauss(0, sig))), mul(up, this.rnd.gauss(0, sig))));
      const vel = add(shooter.vel, mul(dir, sp.muzzle));
      world.bullets.push({ pos: add(muzzle, mul(vel, dt * i / n)), vel, age: 0, owner: shooter, alive: true, tracer: this.count % 2 === 0, spec: sp });
    }
  }
}

export function gunLead(sPos, sVel, tPos, tVel, spec, iterations = 4) {
  const rel = sub(tPos, sPos), dv = sub(tVel, sVel), k = spec.dragK, v0 = spec.muzzle;
  let tof = len(rel) / v0, aim = copy(rel);
  for (let i = 0; i < iterations; i++) {
    aim = add(add(rel, mul(dv, tof)), V(0, 0, 0.5 * G * tof * tof));
    tof = (Math.exp(Math.min(k * len(aim), 6)) - 1) / (k * v0);
  }
  return [norm(aim), tof];
}

function segHitsBox(p0, p1, c, h) {
  let t0 = 0, t1 = 1;
  const a = [p0.x, p0.y, p0.z], b = [p1.x, p1.y, p1.z];
  for (let i = 0; i < 3; i++) {
    const s = a[i] - c[i], d = b[i] - a[i];
    if (Math.abs(d) < 1e-9) { if (Math.abs(s) > h[i]) return false; continue; }
    let u0 = (-h[i] - s) / d, u1 = (h[i] - s) / d;
    if (u0 > u1) [u0, u1] = [u1, u0];
    t0 = Math.max(t0, u0); t1 = Math.min(t1, u1);
    if (t0 > t1) return false;
  }
  return true;
}

export function updateBullets(world, dt) {
  const targets = world.aircraft.filter((a) => a.alive), keep = [];
  for (const b of world.bullets) {
    const old = copy(b.pos), sp = len(b.vel);
    b.vel.multiplyScalar(1 - b.spec.dragK * sp * dt);
    b.vel.z -= G * dt;
    b.pos.addScaledVector(b.vel, dt);
    b.age += dt;
    const step = len(sub(b.pos, old));
    for (const ac of targets) {
      if (ac === b.owner) continue;
      const relEnd = sub(b.pos, ac.pos);
      if (len(relEnd) > step + 12) continue;
      const relStart = sub(old, sub(ac.pos, mul(ac.vel, dt)));
      const p0 = toLocal(ac.quat, relStart), p1 = toLocal(ac.quat, relEnd);
      if (ac.spec.hitboxes.some(([c, h]) => segHitsBox(p0, p1, c, h))) {
        b.alive = false;
        world.emit('hit', { target: ac, pos: copy(b.pos), shooter: b.owner });
        ac.takeDamage(b.spec.damage, b.owner, b.spec.name, world);
        break;
      }
    }
    if (!b.alive) continue;
    if (b.pos.z < world.terrain.height(b.pos.x, b.pos.y)) { if (b.tracer) world.emit('impact', { pos: copy(b.pos) }); continue; }
    if (b.age < b.spec.life) keep.push(b);
  }
  world.bullets = keep;
}
