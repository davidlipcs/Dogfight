import './shim.mjs';
import fs from 'fs';
const U = await import('./js/util.js');
const { V, rng } = U;
const { Terrain } = await import('./js/terrain.js');
const { Aircraft, World } = await import('./js/sim.js');
const { AIPilot, PlayerPilot } = await import('./js/ai.js');
const S = await import('./js/specs.js');
const terrain = new Terrain(JSON.parse(fs.readFileSync('terrain.json', 'utf8')));

function scenario(name, seed, setup, T) {
  const w = new World(terrain, seed);
  const acs = setup(w);
  const out = [], counts = {};
  const dt = 1 / 60;
  for (let i = 0; i <= T / dt; i++) {
    w.update(dt);
    for (const [k] of w.drainEvents()) counts[k] = (counts[k] || 0) + 1;
    if (i % 300 === 0) out.push({ t: w.time, acs: acs.map((a) => ({ pos: [a.pos.x, a.pos.y, a.pos.z], vel: [a.vel.x, a.vel.y, a.vel.z], hp: a.hp, alive: a.alive, flares: a.flares, ammo: a.gun.ammo, m9: a.missileCount('AIM-9M'), m120: a.missileCount('AIM-120A'), state: a.pilot && a.pilot.state || '' })), nm: w.missiles.length, nf: w.flares.length, counts: { ...counts } });
  }
  return out;
}
const mk = (spec, name, team, x, y, z, hdg, spd, seed, missiles, skill) => {
  const a = new Aircraft(spec, name, team, V(x, y, z), hdg, spd, { rnd: rng(seed), missiles });
  new AIPilot(a, skill, null);
  return a;
};
const out = {
  duel: scenario('duel', 5, (w) => {
    const a = mk(S.F16C, 'A', 'blue', 0, 0, 6000, 90, 250, 11, S.PLAYER_MISSILES, 'normal');
    const b = mk(S.BANDITS.su35, 'B', 'red', 14000, 0, 6200, 270, 250, 22, S.missilesFor(S.BANDITS.su35, true), 'ace');
    w.addAircraft(a); w.addAircraft(b); return [a, b];
  }, 150),
  merge: scenario('merge', 9, (w) => {
    const a = mk(S.FA18E, 'A', 'blue', 0, 0, 5000, 0, 280, 31, S.PLAYER_MISSILES, 'hard');
    const b = mk(S.BANDITS.mig29, 'B', 'red', 2500, 9000, 5100, 200, 260, 32, S.missilesFor(S.BANDITS.mig29, true), 'hard');
    const c = mk(S.BANDITS.f16, 'C', 'red', -3000, 12000, 4800, 180, 250, 33, S.BANDIT_MISSILES, 'normal');
    w.addAircraft(a); w.addAircraft(b); w.addAircraft(c); return [a, b, c];
  }, 150),
  stealth: scenario('stealth', 3, (w) => {
    const a = mk(S.F22A, 'A', 'blue', 20000, -10000, 8000, 45, 300, 41, S.PLAYER_MISSILES, 'ace');
    const b = mk(S.BANDITS.typhoon, 'B', 'red', 30000, 2000, 8100, 250, 260, 42, S.missilesFor(S.BANDITS.typhoon, true), 'ace');
    w.addAircraft(a); w.addAircraft(b); return [a, b];
  }, 150),
};
fs.writeFileSync('ref_sim.json', JSON.stringify(out));
console.log(Object.keys(out).map((k) => k + ':' + out[k].length + ' ' + JSON.stringify(out[k][out[k].length - 1].counts)).join('\n'));
