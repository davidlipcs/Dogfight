// Point-mass aerodynamics + fly-by-wire (G command with AoA limiter) + landing gear.  Everything that
// differs between the aircraft comes from the spec (specs.js): mass, wing, engines, drag polar, limits.
import { G, DEG, V, add, sub, mul, dot, cross, len, norm, clamp, interp, qaxis, qmul, fwdOf, upOf, rightOf, qheading } from './util.js';

const R_AIR = 287.05, GAMMA = 1.4;
export const RHO0 = 1.225;
const RHO_TROPOPAUSE = 0.36392;

export function isa(alt) {
  const h = clamp(alt, 0, 32000);
  let temp, p;
  if (h < 11000) { temp = 288.15 - 0.0065 * h; p = 101325 * Math.pow(temp / 288.15, 5.25588); }
  else if (h < 20000) { temp = 216.65; p = 22632.1 * Math.exp(-G * (h - 11000) / (R_AIR * temp)); }
  else { temp = 216.65 + 0.001 * (h - 20000); p = 5474.89 * Math.pow(temp / 216.65, -G / (R_AIR * 0.001)); }
  return [p / (R_AIR * temp), Math.sqrt(GAMMA * R_AIR * temp)];
}

const CLA_MACH = [[0, 1], [0.8, 1.08], [0.95, 1.12], [1.1, 0.95], [1.5, 0.8], [2.2, 0.62]];
const K_ALPHA = 6, K_BETA = 3, TAU_PITCH = 0.06, TAU_ROLL = 0.09, TAU_YAW = 0.12;
export const MAX_AB = 1.1;
const G_ONSET = 10;
const SPOOL_UP_CORE = 0.30, SPOOL_DOWN_CORE = 0.40, SPOOL_UP_AB = 0.07, SPOOL_DOWN_AB = 0.25;
export const GEAR_HEIGHT = 2.05;                      // F-16 (each spec has its own gearHeight)
const GEAR_TIME = 4, GEAR_CD = 0.022, FLAP_CL = 0.22, FLAP_CD = 0.012;
const MU_PAVED = 0.02, MU_GRASS = 0.07, MU_BRAKE = 0.45, MAX_SINK = 4.2, MAX_BANK = 12;
const NWS_RATE = 0.45;

export class Controls {
  constructor(throttle = 0.85) {
    this.pitch = 0; this.roll = 0; this.yaw = 0; this.throttle = throttle; this.airbrake = false; this.brakes = false;
    this.postStall = false;               // extreme mode + full aft stick: the AoA limiter lets go (Cobra)
  }
}

export class FlightModel {
  constructor(spec, pos, vel, quat, fuel) {
    this.spec = spec;
    this.pos = pos.clone(); this.vel = vel.clone(); this.quat = quat.clone();
    this.omega = V();                       // x pitch, y roll, z yaw-left (local)
    this.fuel = fuel ?? spec.internalFuel;
    this.storeMass = 0; this.storeCd = 0;
    this.engine = 0.85; this.nzCmd = 1;
    this.alpha = 0; this.beta = 0; this.mach = 0; this.ias = len(vel); this.rho = RHO0; this.qbar = 0;
    this.gLoad = 1; this.thrust = 0; this.accel = V();
    this.gearDown = false; this.gearPos = 0; this.onGround = false; this.groundPitch = 0;
    this.contactEvent = null; this.crashReason = ''; this.sinkRate = 0; this.flaps = 0;
    this.gearHeight = spec.gearHeight ?? GEAR_HEIGHT; this.drag = 0; this.fuelFlow = 0;
    this.extreme = false; this.vectorAngle = 0;             // F-16 extreme mode: thrust vectoring on
  }
  // the thrust vectoring settings while extreme mode is on (only jets with spec.tvc have it)
  get tvc() { return this.extreme && this.spec.tvc ? this.spec.tvc : null; }
  get mass() { return this.spec.emptyMass + this.fuel + this.storeMass; }
  get speed() { return len(this.vel); }
  get forward() { return fwdOf(this.quat); }
  get up() { return upOf(this.quat); }
  get right() { return rightOf(this.quat); }

  placeOnGround(x, y, groundZ, headingDeg) {
    this.pos = V(x, y, groundZ + this.gearHeight); this.vel = V();
    this.quat = qheading(headingDeg, 0); this.omega = V();
    this.gearDown = true; this.gearPos = 1; this.onGround = true; this.groundPitch = 0; this.engine = 0; this.nzCmd = 1;
    this.groundZ = groundZ; this.arrest = 0; this.catapultAcc = 0;
  }
  setGear(down) {
    if (!down && this.onGround) return false;
    this.gearDown = down; return true;
  }

  liftCoefficient(alpha, mach) {
    const s = this.spec;
    const cla = s.clAlpha * interp(CLA_MACH, mach);
    const a = Math.abs(alpha), stall = s.alphaStall * DEG, clMax = this.tvc ? this.tvc.clMax : s.clMax;
    let cl;
    if (a <= stall) cl = Math.min(cla * a, clMax);
    else {
      const peak = Math.min(cla * stall, clMax);
      const t = clamp((a - stall) / (15 * DEG), 0, 1);
      cl = peak * (1 - t) + 0.95 * Math.sin(2 * Math.min(a, Math.PI - a)) * t;
    }
    return Math.sign(alpha || 1) * cl;
  }
  thrustAt(setting, rho, mach) {
    const s = this.spec;
    if (this.fuel <= 0) return 0;
    const lapse = rho >= RHO_TROPOPAUSE ? Math.pow(rho / RHO0, 0.75)
      : Math.pow(RHO_TROPOPAUSE / RHO0, 0.75) * Math.pow(rho / RHO_TROPOPAUSE, 1.25);
    const dry = s.thrustDry * (0.04 + 0.96 * Math.pow(Math.min(setting, 1), 1.6)) * lapse * (1 + 0.02 * mach);
    if (setting <= 1) return dry;
    const ab = clamp((setting - 1) / (MAX_AB - 1), 0, 1);
    return dry + (s.thrustAb * lapse * (1 + 0.3 * mach) - dry) * ab;
  }
  spool(target, dt) {
    let e = this.engine;
    if (target > e) {
      if (e < 1) e = Math.min(e + SPOOL_UP_CORE * (0.45 + 0.55 * e) * dt, Math.min(target, 1));
      else if (this.fuel > 0) e = Math.min(e + SPOOL_UP_AB * dt, target);
    } else if (target < e) e = Math.max(e - (e > 1 ? SPOOL_DOWN_AB : SPOOL_DOWN_CORE) * dt, target);
    this.engine = e;
  }
  get afterburner() { return this.engine > 1.001 && this.fuel > 0; }

  step(dt, c, terrain) {
    const s = this.spec;
    const fwd = this.forward, up = this.up, right = this.right;
    const [rho, aSound] = isa(this.pos.z);
    const speed = this.speed;
    const vhat = speed > 1 ? mul(this.vel, 1 / speed) : fwd.clone();
    const alpha = speed > 1 ? Math.atan2(-dot(this.vel, up), dot(this.vel, fwd)) : 0;
    const beta = Math.asin(clamp(dot(this.vel, right) / Math.max(speed, 1), -1, 1));
    const mach = speed / aSound;
    const qbar = 0.5 * rho * speed * speed;
    const mass = this.mass;

    this.spool(clamp(c.throttle, 0, MAX_AB), dt);
    const tv = this.tvc;
    const thrust = this.thrustAt(this.engine, rho, mach) * (tv ? tv.thrustScale : 1);
    this.thrust = thrust;
    const sfc = this.engine <= 1 ? s.fuelFlowDry / s.thrustDry : s.fuelFlowAb / s.thrustAb;
    this.fuelFlow = thrust * sfc;
    this.fuel = Math.max(0, this.fuel - this.fuelFlow * dt);

    let cl = this.liftCoefficient(alpha, mach);
    const flaps = this.gearPos * clamp((125 - speed * Math.sqrt(rho / RHO0)) / 25, 0, 1);
    this.flaps = flaps;
    if (flaps > 0 && alpha > -0.05) cl += FLAP_CL * flaps;
    const liftDir = norm(cross(right, vhat), up);
    const sideDir = cross(vhat, liftDir);
    let cd = s.cd0 + (s.pylonCd || 0) + interp(s.waveDrag, mach) + s.kInduced * (tv ? tv.kScale : 1) * cl * cl + this.storeCd + 0.8 * Math.sin(alpha) ** 2;
    if (c.airbrake) cd += s.airbrakeCd;
    cd += GEAR_CD * this.gearPos + FLAP_CD * flaps;
    const area = s.wingArea;
    this.drag = qbar * area * cd;
    // thrust vectoring: the nozzle turns with the pitch stick, part of the thrust pushes the tail down (nose up)
    const vec = tv && !this.onGround ? clamp(c.pitch, -1, 1) * tv.vector * DEG : 0;
    this.vectorAngle += (vec - this.vectorAngle) * Math.min(1, dt * 8);
    const force = add(add(add(mul(liftDir, qbar * area * cl), mul(sideDir, -qbar * area * 1.1 * beta)),
      mul(vhat, -qbar * area * cd)), add(mul(fwd, thrust * Math.cos(this.vectorAngle)), mul(up, thrust * Math.sin(this.vectorAngle))));
    const acc = add(mul(force, 1 / mass), V(0, 0, -G));

    // landing gear
    const target = this.gearDown ? 1 : 0;
    this.gearPos += clamp(target - this.gearPos, -dt / GEAR_TIME, dt / GEAR_TIME);
    this.contactEvent = null;
    if (terrain) {
      const groundZ = terrain.height(this.pos.x, this.pos.y);
      const tele = { force, mass, alpha, mach, rho, qbar, speed };
      if (this.onGround) { this.groundStep(dt, c, acc, terrain, tele); return; }
      if (this.pos.z - groundZ <= this.gearHeight) {
        if (this.touchdown(groundZ, terrain)) this.groundStep(dt, c, acc, terrain, tele);
        return;
      }
    }

    // FLCS pitch: G command with AoA limiter and onset limit
    const stick = clamp(c.pitch, -1, 1);
    let nz = stick >= 0 ? 1 + stick * (s.gMax - 1) : 1 + stick * (1 - s.gMin);
    this.nzCmd += clamp(nz - this.nzCmd, -G_ONSET * dt, G_ONSET * dt);
    nz = this.nzCmd;
    const claEff = s.clAlpha * interp(CLA_MACH, mach);
    // AoA limit: normal, or in extreme mode 30 degrees (the mouse instructor) / 80 with full aft stick (Cobra)
    const alphaLim = (tv ? (c.postStall ? tv.alphaPostStall : tv.alphaNormal) : s.alphaLimit) * DEG;
    let alphaReq = qbar > 1 ? nz * mass * G / (qbar * area * claEff) : alphaLim * (nz > 0 ? 1 : -1);
    alphaReq = clamp(alphaReq, -10 * DEG, alphaLim);
    // Cobra: below ~600 km/h a full pull with vectored thrust throws the nose straight up to the limit
    if (tv && c.postStall && speed < 170) alphaReq = alphaLim;
    const vSafe = Math.max(speed, 30);
    const pathPitch = dot(acc, liftDir) / vSafe;
    const pathLat = dot(acc, sideDir) / vSafe;
    // the vectored nozzle keeps pitch and roll authority even when the air is too slow for the tail
    const authority = clamp(qbar / 9000 + (tv ? tv.lowSpeedAuthority : 0), 0.12, 1);
    const qMax = tv ? tv.pitchRate : 0.9;
    const qCmd = clamp(pathPitch + K_ALPHA * (alphaReq - alpha) * authority, -qMax, qMax);
    const rollEff = clamp(qbar / 9000 + (tv ? tv.lowSpeedAuthority * 0.5 : 0), 0.15, 1)
      * (1 - 0.5 * clamp(alpha / alphaLim, 0, 1));
    const pCmd = clamp(c.roll, -1, 1) * (tv ? tv.rollRate : s.rollRate) * DEG * rollEff;
    const betaCmd = -clamp(c.yaw, -1, 1) * s.yawBeta * DEG;
    const rCmd = pathLat + K_BETA * (beta - betaCmd) * authority;
    this.omega.x += (qCmd - this.omega.x) * Math.min(1, dt / TAU_PITCH);
    this.omega.y += (pCmd - this.omega.y) * Math.min(1, dt / TAU_ROLL);
    this.omega.z += (-rCmd - this.omega.z) * Math.min(1, dt / TAU_YAW);

    this.vel.addScaledVector(acc, dt);
    this.pos.addScaledVector(this.vel, dt);
    const rot = mul(this.omega, dt);
    const ang = len(rot);
    if (ang > 1e-9) { this.quat = qmul(this.quat, qaxis(rot, ang)); this.quat.normalize(); }

    this.alpha = alpha; this.beta = beta; this.mach = mach; this.rho = rho; this.qbar = qbar;
    this.ias = speed * Math.sqrt(rho / RHO0); this.accel = acc;
    this.gLoad = dot(mul(force, 1 / mass), up) / G;
  }

  touchdown(groundZ, terrain) {
    const fwd = this.forward, s = this.spec;
    const pitch = Math.asin(clamp(fwd.z, -1, 1)) / DEG;
    const r = this.right;
    const bank = Math.atan2(-r.z, this.up.z) / DEG;
    this.sinkRate = Math.max(0, -this.vel.z);
    let reason = '';
    if (this.gearPos < 0.98) reason = this.gearPos < 0.1 ? 'futómű nélkül értél földet' : 'a futómű nem volt kint';
    else if (this.sinkRate > MAX_SINK) reason = `túl kemény földetérés (${this.sinkRate.toFixed(1)} m/s)`;
    else if (Math.abs(bank) > MAX_BANK) reason = 'szárnyvéggel értél földet';
    else if (pitch < -3) reason = 'orral értél földet';
    else if (pitch > (s.tailStrike ?? 13) + 7) reason = 'farokkal értél földet';
    else if (terrain.slope(this.pos.x, this.pos.y) > 6 * DEG) reason = 'egyenetlen terep';
    else if (terrain.isWater && terrain.isWater(this.pos.x, this.pos.y)) reason = 'a tengerbe csapódtál';
    if (reason) {
      this.contactEvent = 'crash'; this.crashReason = reason; this.pos.z = groundZ + 1; return false;
    }
    this.onGround = true;
    this.contactEvent = pitch > (s.tailStrike ?? 13) + 2 ? 'tailstrike' : 'touchdown';
    this.groundPitch = Math.max(0, pitch) * DEG;
    this.omega = V(); this.nzCmd = 1;
    this.pos.z = groundZ + this.gearHeight; this.vel.z = 0; this.groundZ = groundZ;
    return true;
  }

  groundStep(dt, c, acc, terrain, t) {
    const fwd = this.forward;
    let heading = Math.atan2(fwd.x, fwd.y);
    const hDir = V(Math.sin(heading), Math.cos(heading), 0);
    const hRight = V(hDir.y, -hDir.x, 0);
    let normal = 0;
    if (acc.z < 0) { normal = -acc.z; acc.z = 0; }
    const paved = terrain.airfield ? terrain.airfield.onPaved(this.pos.x, this.pos.y) : true;
    const mu = (paved ? MU_PAVED : MU_GRASS) + (c.brakes || this.parkBrake ? MU_BRAKE : 0);
    const u = dot(this.vel, hDir), w = dot(this.vel, hRight);
    if (Math.abs(u) > 1e-3) {
      const decel = Math.min(mu * normal, Math.abs(u) / dt);
      acc.addScaledVector(hDir, -Math.sign(u) * decel);
    } else if (normal > 0) {
      const along = dot(acc, hDir), hold = mu * normal;
      acc.addScaledVector(hDir, -(Math.abs(along) <= hold ? along : Math.sign(along) * hold));
    }
    // carrier: the catapult shuttle pulls forward, the arresting wire holds back (set by the game)
    if (this.catapultAcc) acc.addScaledVector(hDir, this.catapultAcc);
    if (this.arrest) {
      if (u > 1.2) acc.addScaledVector(hDir, -Math.min(this.arrest, u / dt));
      else this.arrest = 0;
    }
    const grip = 0.8 * normal;
    acc.addScaledVector(hRight, -clamp(w / Math.max(dt, 0.02), -grip, grip));

    const gs = Math.max(Math.abs(u), 0.1);
    const nws = this.groundPitch < 2 * DEG ? NWS_RATE * Math.min(1, 8 / gs) : 0;
    const yawRate = clamp(c.yaw, -1, 1) * (nws + 0.03 * Math.min(gs / 60, 1)) * (gs > 0.3 ? 1 : 0);
    const ias = t.speed * Math.sqrt(t.rho / RHO0);
    const auth = clamp((ias - (this.spec.rotateIas ?? 60)) / 12, 0, 1), tailStrike = this.spec.tailStrike ?? 13;
    const stick = clamp(c.pitch, -1, 1);
    let pitchRate = stick > 0 ? stick * 7 * DEG * auth : 0;
    if (pitchRate <= 0) pitchRate = -3.5 * DEG;
    if (this.catapultAcc && ias > (this.spec.rotateIas ?? 60) - 4) pitchRate = Math.max(pitchRate, 9 * DEG);   // catapult: hands-off rotation
    this.groundPitch = clamp(this.groundPitch + pitchRate * dt, 0, tailStrike * DEG);

    this.vel.addScaledVector(acc, dt);
    this.pos.addScaledVector(this.vel, dt);
    heading += yawRate * dt;
    this.quat = qheading(heading / DEG, this.groundPitch / DEG);
    this.omega = V(this.groundPitch > 0 ? pitchRate : 0, 0, 0);
    const ng = terrain.height(this.pos.x, this.pos.y);
    if (this.groundZ !== undefined && this.groundZ - ng > 3) {
      // rolled off an edge (the carrier's deck): from here it flies - or falls
      this.onGround = false; this.groundZ = undefined; this.catapultAcc = 0;
      this.alpha = t.alpha; this.mach = t.mach; this.rho = t.rho; this.qbar = t.qbar; this.ias = ias; this.accel = acc;
      return;
    }
    this.groundZ = ng;
    if (normal === 0 && this.vel.z > 0) {
      if (this.pos.z > ng + this.gearHeight + 0.3) { this.onGround = false; this.groundZ = undefined; }
    } else { this.pos.z = ng + this.gearHeight; this.vel.z = 0; }
    this.alpha = t.alpha; this.beta = 0; this.mach = t.mach; this.rho = t.rho; this.qbar = t.qbar;
    this.ias = ias; this.accel = acc;
    this.gLoad = dot(mul(t.force, 1 / t.mass), this.up) / G + normal / G;
  }
}

