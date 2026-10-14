// Aircraft + World (port of dogfight/sim/aircraft.py and world.py).
import { V, add, sub, mul, len, copy, norm, qheading, xform, rng, DEG } from './util.js';
import { FlightModel, Controls } from './flight.js';
import { AIM9M, IR, MISSILES } from './specs.js';
import { IRSeeker, Radar, RWR, Missile, Gun, Flare, Chaff, STT, updateBullets } from './weapons.js';

const STORE_DRAG_AREA = 0.031;                     // m^2 of drag area per missile with its launcher
const ASSIST_IR_FOV = 10, ASSIST_IR_CONE = 30;     // player lock assist: seeker search cone / F-key cone (deg)
export const PHYS_DT = 1 / 100, SENSOR_DT = 1 / 30, AI_DT = 1 / 10;

export class Aircraft {
  constructor(spec, name, team, pos, headingDeg, speed, opts = {}) {
    this.spec = spec; this.name = name; this.team = team;
    this.isPlayer = !!opts.isPlayer; this.livery = opts.livery || 'viper';
    this.rnd = opts.rnd || rng(Math.floor(Math.random() * 1e9));
    const q = qheading(headingDeg, 0);
    this.fm = new FlightModel(spec, pos, mul(xform(q, V(0, 1, 0)), speed), q);
    this.fm.engine = 0.9;
    this.controls = new Controls(0.9);
    this.trigger = false;
    this.gun = new Gun(spec.gun, this.rnd);
    this.loadout = opts.loadout || 'default';
    this.stations = []; this.selected = null;
    this.radar = new Radar(spec.radar, this, this.rnd);
    this.missiles = opts.missiles || MISSILES;        // the player's and the enemies' missiles differ
    this.irSeeker = new IRSeeker(this.missiles['AIM-9M'] || AIM9M, this.rnd);
    this.rwr = new RWR(this);
    this.flares = spec.cm.flares; this.chaff = spec.cm.chaff; this.cmHold = false; this.cmTimer = 0;
    this.hp = spec.hp; this.alive = true; this.burning = false; this.crashed = false; this.deathTime = null;
    this.kills = 0; this.lastAttacker = null; this.lastHitTime = -1e9; this.pilot = null;
    this.lockAssist = !!opts.lockAssist; this.irAutoHold = 0;
    this.rearm();
  }
  get pos() { return this.fm.pos; }
  get vel() { return this.fm.vel; }
  get quat() { return this.fm.quat; }
  get forward() { return this.fm.forward; }
  get speed() { return this.fm.speed; }
  get mach() { return this.fm.mach; }
  get engineSetting() { return this.alive ? this.fm.engine : 0; }
  get damaged() { return this.hp < this.spec.hp * 0.5; }
  get onGround() { return this.fm.onGround; }

  rearm() {
    // a loadout is a name from spec.loadouts or a {station: weapon} table (the menu's loadout editor)
    const layout = typeof this.loadout === 'object' ? this.loadout : this.spec.loadouts[this.loadout] || this.spec.loadouts.default;
    this.stations = Object.keys(layout).map(Number).sort((a, b) => a - b)
      .map((n) => ({ number: n, key: layout[n], spec: this.missileSpec(layout[n]), mount: V(...this.spec.stations[n]), loaded: true }));
    this.gun.reload();
    this.flares = this.spec.cm.flares; this.chaff = this.spec.cm.chaff;
    if (!this.selected || this.missileCount(this.selected) === 0) this.selected = this.stations[0]?.key ?? null;
    this.updateStores();
  }
  updateStores() {
    const loaded = this.stations.filter((s) => s.loaded);
    this.fm.storeMass = loaded.reduce((m, s) => m + s.spec.mass, 0);
    this.fm.storeCd = STORE_DRAG_AREA * loaded.length / this.spec.wingArea;
  }
  missileCount(key) { return this.stations.filter((s) => s.loaded && s.key === key).length; }
  weaponKeys() { return [...new Set(this.stations.map((s) => s.key))]; }
  missileSpec(key) { return this.missiles[key] || MISSILES[key]; }
  get selectedSpec() { return this.selected ? this.missileSpec(this.selected) : null; }
  select(key) {
    if (!this.weaponKeys().includes(key)) return false;
    this.selected = key; this.irSeeker.reset(); return true;
  }
  toggleGear() { return this.fm.setGear(!this.fm.gearDown); }

  physicsStep(dt, world) {
    if (this.crashed) return;
    if (this.alive) {
      this.fm.step(dt, this.controls, world.terrain);
      const ev = this.fm.contactEvent;
      if (ev === 'crash') { this.crash(world, this.fm.crashReason); return; }
      if (ev === 'tailstrike') { world.emit('message', { to: this, text: 'FAROKÜTÉS!', level: 'bad' }); this.takeDamage(30, null, 'tailstrike', world); }
      else if (ev === 'touchdown' && this.fm.sinkRate > 3) world.emit('message', { to: this, text: 'KEMÉNY LANDOLÁS', level: 'warn' });
      this.gun.update(dt, this, this.trigger, world);
      this.cmTimer -= dt;
      if (this.cmHold) this.dispense(world);
    } else {
      const wreck = new Controls(0); wreck.pitch = -0.3; wreck.roll = 0.9;
      this.fm.step(dt, wreck, null);
      this.gun.firing = false;
      if (this.pos.z <= world.terrain.height(this.pos.x, this.pos.y) + 1.5) this.crash(world);
    }
  }

  sensorStep(dt, world) {
    if (!this.alive) return;
    const r = this.radar;
    r.update(dt, world);
    const msg = { locked: ['RADAR LOCK', 'good'], lost: ['LOCK LOST', 'warn'], decoyed: ['LOCK LOST - CHAFF', 'warn'] }[r.lastEvent];
    if (msg) world.emit('message', { to: this, text: msg[0], level: msg[1] });
    const sp = this.selectedSpec;
    if (sp && sp.guidance === IR) {
      if (this.irSeeker.spec !== sp) this.irSeeker = new IRSeeker(sp, this.rnd);
      this.irSeeker.acqFov = this.lockAssist ? ASSIST_IR_FOV : null;
      const slave = r.mode === STT && r.trackPos ? norm(sub(r.trackPos, this.pos)) : null;
      const res = this.irSeeker.update(dt, this.pos, this.forward, world.heatSources(), world.terrain, slave, this);
      if (res === 'lost') world.emit('message', { to: this, text: 'SEEKER LOST', level: 'warn' });
      else if (res === 'decoyed') world.emit('message', { to: this, text: 'SEEKER ON FLARE', level: 'warn' });
      if (slave && !this.irSeeker.locked && this.irSeeker.candidate === r.locked) this.irSeeker.lock();
      // lock assist: the seeker locks by itself onto an enemy in its (wide) search cone
      this.irAutoHold -= dt;
      const c = this.irSeeker.candidate;
      if (this.lockAssist && this.irAutoHold <= 0 && !this.irSeeker.locked && c && !c.isFlare && c.team !== this.team) {
        this.irSeeker.lock();
        world.emit('message', { to: this, text: 'SEEKER LOCK - Space: indítás', level: 'good' });
      }
    }
    this.rwr.update(world);
  }

  toggleIrLock(world = null) {
    const sp = this.selectedSpec;
    if (!sp || sp.guidance !== IR) return false;
    if (this.irSeeker.locked) { this.irSeeker.unlock(); this.irAutoHold = 3; return false; }
    if (this.lockAssist && world && !this.irSeeker.candidate) {
      // nothing in the seeker: look for the hottest enemy within a wide cone around the nose
      const s = this.irSeeker.bestInCone(this.pos, this.forward, world.heatSources(), ASSIST_IR_CONE * DEG, world.terrain, this);
      if (s && !s.isFlare && s.team !== this.team) this.irSeeker.candidate = s;
    }
    return this.irSeeker.lock();
  }

  fireMissile(world) {
    if (!this.alive || !this.selected) return null;
    const byNum = new Map(this.stations.map((s) => [s.number, s]));
    const st = this.spec.firingOrder.map((n) => byNum.get(n)).find((s) => s && s.loaded && s.key === this.selected);
    if (!st) { world.emit('message', { to: this, text: `NINCS TÖBB ${this.selected}`, level: 'warn' }); return null; }
    const sp = st.spec, q = this.quat;
    const pos = add(this.pos, xform(q, st.mount));
    const vel = sub(this.vel, mul(this.fm.up, Math.abs(st.mount.x) > 4.5 ? 0 : 4));
    let target, axis = null;
    if (sp.guidance === IR) { target = this.irSeeker.target; axis = this.irSeeker.axis; }
    else target = this.radar.mode === STT ? this.radar.locked : null;
    const m = new Missile(sp, this, pos, vel, this.forward, this.rnd, target, axis);
    st.loaded = false; this.updateStores();
    if (sp.guidance === IR) this.irSeeker.reset();
    world.addMissile(m);
    if (this.missileCount(this.selected) === 0) {
      const other = this.weaponKeys().find((k) => this.missileCount(k) > 0);
      if (other) this.select(other);
    }
    return m;
  }

  dispense(world) {
    if (this.cmTimer > 0 || (this.flares <= 0 && this.chaff <= 0)) return;
    this.cmTimer = this.spec.cm.interval;
    const down = mul(this.fm.up, -1);
    if (this.flares > 0) {
      this.flares--;
      const side = mul(this.fm.right, this.rnd.uniform(-12, 12));
      world.addFlare(new Flare(add(this.pos, mul(down, 1.5)), add(add(mul(this.vel, 0.96), mul(down, 22)), side), this.spec.cm));
    }
    if (this.chaff > 0) { this.chaff--; world.addChaff(new Chaff(add(this.pos, mul(down, 1.5)), this.vel, this.spec.cm)); }
  }

  takeDamage(amount, source, weapon, world) {
    if (!this.alive) return;
    this.hp -= amount; this.lastAttacker = source; this.lastHitTime = world.time;
    if (this.hp < this.spec.hp * 0.3) this.burning = true;
    if (this.hp <= 0) this.kill(world, source, weapon);
  }
  kill(world, killer, weapon) {
    if (!this.alive) return;
    this.alive = false; this.burning = true; this.hp = 0; this.trigger = false; this.cmHold = false;
    this.deathTime = world.time;
    if (this.radar.on) this.radar.togglePower();
    if (killer && killer !== this) killer.kills++;
    world.emit('kill', { victim: this, killer, weapon });
  }
  crash(world, reason = '') {
    if (this.crashed) return;
    if (this.alive) {
      const recent = world.time - this.lastHitTime < 30 ? this.lastAttacker : null;
      if (reason) world.emit('message', { to: this, text: 'BALESET: ' + reason, level: 'bad' });
      this.kill(world, recent, 'crash');
    }
    this.crashed = true; this.fm.vel = V();
    world.emit('explosion', { pos: copy(this.pos), size: 2.5, ground: true });
  }
}

export class World {
  constructor(terrain, seed = 1) {
    this.terrain = terrain; this.rnd = rng(seed);
    this.aircraft = []; this.missiles = []; this.bullets = []; this.flares = []; this.chaff = []; this.events = [];
    this.time = 0; this.acc = 0; this.sensorAcc = 0; this.aiAcc = 0;
  }
  emit(kind, data) { this.events.push([kind, data]); }
  drainEvents() { const e = this.events; this.events = []; return e; }
  addAircraft(a) { this.aircraft.push(a); return a; }
  addMissile(m) { this.missiles.push(m); this.emit('launch', { missile: m, shooter: m.shooter }); }
  addFlare(f) { this.flares.push(f); this.emit('flare', { flare: f }); }
  addChaff(c) { this.chaff.push(c); this.emit('chaff', { chaff: c }); }
  heatSources() { return this.aircraft.filter((a) => a.alive || (a.burning && !a.crashed)).concat(this.flares); }
  enemiesOf(a) { return this.aircraft.filter((o) => o.team !== a.team && o.alive); }
  update(frameDt) {
    frameDt = Math.min(frameDt, 0.1);
    this.acc += frameDt;
    let steps = 0;
    while (this.acc >= PHYS_DT) {
      this.physics(PHYS_DT); this.acc -= PHYS_DT;
      if (++steps >= 12) { this.acc = 0; break; }
    }
    updateBullets(this, frameDt);
    this.missiles = this.missiles.filter((m) => m.alive);
    this.flares = this.flares.filter((f) => f.alive);
    this.chaff = this.chaff.filter((c) => c.alive);
    this.aircraft = this.aircraft.filter((a) => a.isPlayer || !a.crashed || this.time - a.deathTime < 8);
  }
  physics(dt) {
    this.time += dt;
    for (const a of this.aircraft) if (a.pilot && a.alive) a.pilot.fly(dt, this);
    for (const a of this.aircraft) a.physicsStep(dt, this);
    for (const m of this.missiles) m.update(dt, this);
    for (const f of this.flares) f.update(dt);
    for (const c of this.chaff) c.update(dt);
    this.sensorAcc += dt;
    if (this.sensorAcc >= SENSOR_DT) { for (const a of this.aircraft) a.sensorStep(this.sensorAcc, this); this.sensorAcc = 0; }
    this.aiAcc += dt;
    if (this.aiAcc >= AI_DT) { for (const a of this.aircraft) if (a.pilot && a.alive) a.pilot.think(this); this.aiAcc = 0; }
  }
  detonate(m, pos, ground = false, selfDestruct = false) {
    if (!m.alive) return;
    m.alive = false;
    const sp = m.spec;
    for (const ac of this.aircraft) {
      if (!ac.alive) continue;
      const d = len(sub(ac.pos, pos));
      if (d >= sp.damageRadius) continue;
      const dmg = d <= sp.lethalRadius ? sp.damage : sp.damage * (1 - (d - sp.lethalRadius) / (sp.damageRadius - sp.lethalRadius));
      this.emit('hit', { target: ac, pos: copy(ac.pos), shooter: m.shooter });
      ac.takeDamage(dmg, m.shooter, sp.name, this);
    }
    this.emit('explosion', { pos: copy(pos), size: selfDestruct ? 0.8 : (sp.damage >= 150 ? 1.6 : 1.2), ground });
  }
}

export { DEG };
