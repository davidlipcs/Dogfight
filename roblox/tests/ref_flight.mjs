import './shim.mjs';
import fs from 'fs';
const U = await import('./js/util.js');
const { V, qheading } = U;
const { Terrain } = await import('./js/terrain.js');
const { FlightModel, Controls } = await import('./js/flight.js');
const S = await import('./js/specs.js');
const terrain = new Terrain(JSON.parse(fs.readFileSync('terrain.json', 'utf8')));

function run(spec, setup, ctl, T, extreme = false) {
  const fm = setup(spec);
  fm.extreme = extreme;
  const c = new Controls(0.9);
  const dt = 0.01, out = [];
  for (let i = 0; i <= T / dt; i++) {
    const t = i * dt;
    ctl(c, t);
    fm.step(dt, c, terrain);
    if (i % 500 === 0) out.push({ t, pos: [fm.pos.x, fm.pos.y, fm.pos.z], vel: [fm.vel.x, fm.vel.y, fm.vel.z], q: [fm.quat.x, fm.quat.y, fm.quat.z, fm.quat.w], om: [fm.omega.x, fm.omega.y, fm.omega.z], eng: fm.engine, fuel: fm.fuel, g: fm.gLoad, alpha: fm.alpha, gear: fm.gearPos, on: fm.onGround, ev: fm.contactEvent, ias: fm.ias });
  }
  return out;
}
const air = (alt, spd, hdg) => (spec) => new FlightModel(spec, V(0, 0, alt), U.fwdOf(qheading(hdg, 0)).multiplyScalar(spd), qheading(hdg, 0));
const ctlA = (c, t) => { c.throttle = t < 6 ? 1.1 : 0.7; c.pitch = t < 3 ? 0.4 : t < 9 ? -0.2 + 0.1 * Math.sin(t) : 0.6; c.roll = t > 4 && t < 7 ? 1 : t > 10 && t < 12 ? -1 : 0; c.yaw = t > 14 ? 0.5 : 0; c.airbrake = t > 18 && t < 20; c.postStall = false; };
const ctlB = (c, t) => { c.throttle = 1.1; c.pitch = t < 2 ? 0 : 1; c.roll = 0; c.yaw = 0; c.postStall = t > 3; };
const f = terrain.airfield;
const ground = (spec) => { const fm = new FlightModel(spec, V(), V(), qheading(0)); fm.placeOnGround(f.x, f.y - 1400, terrain.height(f.x, f.y - 1400), 0); return fm; };
const ctlG = (c, t) => { c.throttle = t < 1 ? 0.4 : 1.1; c.brakes = t < 1; c.pitch = t > 22 ? 0.6 : 0; c.yaw = 0.05; c.roll = 0; };
const out = {
  f16_air: run(S.F16C, air(5000, 250, 45), ctlA, 25),
  fa18_air: run(S.FA18E, air(3000, 200, 270), ctlA, 25),
  f16_tvc: run(S.F16C, air(6000, 120, 10), ctlB, 12, true),
  f22_air: run(S.F22A, air(8000, 300, 100), ctlA, 25),
  t6_air: run(S.T6A, air(2000, 110, 0), ctlA, 25),
  f16_takeoff: run(S.F16C, ground, ctlG, 60),
  su35_air: run(S.AIRCRAFT.su35, air(4000, 260, 0), ctlA, 20),
};
fs.writeFileSync('ref_flight.json', JSON.stringify(out));
console.log('ok', Object.keys(out).map((k) => k + ':' + out[k].length).join(' '));
