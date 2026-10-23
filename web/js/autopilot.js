// The instructor (or an AI flight lead) flying a whole sortie: take-off, a climb out, the airfield traffic
// pattern (a left hand circuit), a 3 degree final approach, the flare, the landing roll and the brakes.
// Used in the career's back seat lessons (you only talk to the tower) and by AI leads in formation lessons.
// phase -> the radio call the student is expected to make there (school.js checks them).
import { V, add, sub, mul, len, norm, clamp, dot, DEG, wrap } from './util.js';
import { steerTowards } from './ai.js';

const GLIDE = 3 * DEG;

export class InstructorPilot {
  // field: the air base (runway north-south through field.x / field.y); circuits: how many patterns before landing
  constructor(ac, field, { circuits = 1, height = 450, onPhase = null } = {}) {
    this.ac = ac; this.field = field; this.circuits = circuits; this.height = height; this.onPhase = onPhase;
    this.phase = ac.onGround ? 'hold' : 'downwind'; this.holdT = 0; this.wp = 0; this.t = 0;
    this.vRot = (ac.spec.rotateIas || 60) + 6; this.vApp = (ac.spec.rotateIas || 60) * (ac.spec.trainer && ac.spec.noAB ? 1.28 : 1.42);
    ac.pilot = this;
  }
  think() {}
  set(phase) { if (this.phase !== phase) { this.phase = phase; this.t = 0; if (this.onPhase) this.onPhase(phase); } }
  // released by the tower (school.js): the take-off roll starts
  release() { if (this.phase === 'hold') this.set('roll'); }
  pattern() {
    const f = this.field, h = f.elevation + this.height, y0 = f.y - 1500;
    // left hand circuit: up wind north, cross wind west, down wind south, base east, final north
    return [V(f.x, f.y + 3500, h), V(f.x - 3200, f.y + 4500, h), V(f.x - 3400, f.y - 2000, h), V(f.x - 3000, y0 - 5200, h - 120), V(f.x - 600, y0 - 6600, h - 180)];
  }
  fly(dt) {
    const ac = this.ac, fm = ac.fm, c = ac.controls, f = this.field;
    this.t += dt;
    c.brakes = false; c.airbrake = false;
    const hdgErr = (wantDeg) => wrap(wantDeg * DEG - Math.atan2(ac.forward.x, ac.forward.y));
    if (this.phase === 'hold') { c.throttle = 0.05; c.brakes = true; c.pitch = 0; c.roll = 0; c.yaw = 0; return; }
    if (this.phase === 'roll') {
      c.throttle = ac.spec.noAB ? 1 : 1;
      c.yaw = clamp(hdgErr(0) * 4 - (ac.pos.x - f.x) * 0.02, -1, 1); c.roll = 0;
      c.pitch = fm.ias > this.vRot ? 0.55 : 0;
      if (!fm.onGround && ac.pos.z - f.elevation > 8) this.set('climb');
      return;
    }
    const agl = ac.pos.z - Math.max(0, f.elevation);
    if (this.phase === 'climb') {
      const to = V(f.x, ac.pos.y + 3000, f.elevation + this.height + 150);
      steerTowards(fm, norm(sub(to, ac.pos)), c, 0.45, 0.8);
      c.throttle = 1;
      if (agl > 60 && fm.gearDown) ac.toggleGear();
      if (ac.pos.y > f.y + 2500 || agl > this.height) { this.set('crosswind'); this.wp = 1; }
      return;
    }
    if (this.phase === 'crosswind' || this.phase === 'downwind' || this.phase === 'base') {
      const pts = this.pattern(), tgt = pts[this.wp];
      steerTowards(fm, norm(sub(tgt, ac.pos)), c, 0.45, 0.8);
      const want = this.phase === 'base' ? this.vApp * 1.15 : this.vApp * 1.6;
      c.throttle = clamp(0.55 + (want - fm.ias) * 0.04, 0.15, 1);
      if (this.phase !== 'base' && fm.gearDown && agl > 60) ac.toggleGear();
      if (len(V(tgt.x - ac.pos.x, tgt.y - ac.pos.y, 0)) < 700) {
        this.wp++;
        if (this.wp === 2) this.set('downwind');
        if (this.wp === 3) { this.set('base'); if (!fm.gearDown) ac.toggleGear(); }
        if (this.wp >= pts.length) this.set('final');
      }
      return;
    }
    if (this.phase === 'final') {
      const y0 = f.y - 1500 + 250, dist = y0 - ac.pos.y;           // aim 250 m past the threshold
      const zWant = f.elevation + fm.gearHeight * 0 + Math.max(0, dist) * Math.tan(GLIDE);
      // flight path: the glide slope, steeper when high, shallower when low; heading for the centre line
      const gamma = -Math.tan(GLIDE) + clamp((zWant - ac.pos.z) / 250, -0.05, 0.04);
      const dir = norm(V(clamp((f.x - ac.pos.x) / 1500, -0.25, 0.25), 1, gamma));
      steerTowards(fm, dir, c, 0.35, 1.0);
      c.throttle = clamp(0.35 + (this.vApp - fm.ias) * 0.05, 0.05, 1);
      if (!fm.gearDown) ac.toggleGear();
      if (agl < 12 + fm.gearHeight) this.set('flare');
      return;
    }
    if (this.phase === 'flare') {
      // the flare: the sink rate comes down to about a metre a second just above the runway, the speed held;
      // the nose never goes past the tail strike angle
      const jet = this.vApp > 70, h = agl - fm.gearHeight;
      const sink = clamp((jet ? 1.2 : 0.8) + h * 0.12, jet ? 1.2 : 0.8, 3);
      const dir = norm(V(clamp((f.x - ac.pos.x) / 1500, -0.1, 0.1), 1, -sink / Math.max(30, ac.speed)));
      steerTowards(fm, dir, c, 0.4, 1.2);
      const pitch = Math.asin(clamp(ac.forward.z, -1, 1)) / DEG, lim = (ac.spec.tailStrike ?? 13) - 3;
      if (pitch > lim) c.pitch = Math.min(c.pitch, -0.2);
      c.throttle = clamp(0.25 + (this.vApp * 0.9 - fm.ias) * 0.05, 0, 0.8);
      if (fm.onGround) this.set('rollout');
      return;
    }
    if (this.phase === 'rollout') {
      c.throttle = 0; c.pitch = 0; c.roll = 0; c.brakes = this.t > 1.5;
      c.yaw = clamp(hdgErr(0) * 4 - (ac.pos.x - f.x) * 0.02, -1, 1);
      if (ac.speed < 2) this.set('stopped');
      return;
    }
    if (this.phase === 'stopped') { c.throttle = 0; c.brakes = true; }
  }
}
