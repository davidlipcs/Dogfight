import './shim.mjs';
import fs from 'fs';
globalThis.localStorage = { getItem() { return null; }, setItem() {} };
const U = await import('./js/util.js');
const { V } = U;
const { Terrain } = await import('./js/terrain.js');
const { Race } = await import('./js/race.js');
const { CanyonRun } = await import('./js/canyon.js');
const { TubeRun } = await import('./js/tube.js');
const terrain = new Terrain(JSON.parse(fs.readFileSync('terrain.json', 'utf8')));
const scene = { add() {}, remove() {} };
const field = terrain.airfield;
const arr = (v) => [v.x, v.y, v.z];
const rings = (r) => r.rings.map((x) => [arr(x.c), arr(x.n)]);
// fly a straight line through each ring (and a miss) and record the events
function fly(r, miss) {
  const evs = [];
  let pos = V(0, 0, 0), prev = null;
  for (let k = 0; k < r.rings.length * 3 && !r.finished; k++) {
    const g = r.rings[(r.next) % r.rings.length];
    const off = miss && k === 2 ? 1.2 * r.R : 0;
    const side = V(g.n.y, -g.n.x, 0);
    const a = V(g.c.x - g.n.x * 30 + side.x * off, g.c.y - g.n.y * 30 + side.y * off, g.c.z);
    const b = V(g.c.x + g.n.x * 30 + side.x * off, g.c.y + g.n.y * 30 + side.y * off, g.c.z);
    const ac = { pos: b };
    const ev = r.update(0.5, ac, a);
    evs.push([ev, r.next, r.time, r.penalty || 0]);
    if (miss && k === 2) { /* then go through */ }
  }
  return evs;
}
const out = {};
const race = new Race(terrain, scene, V(field.x, field.y + 3000, 0), 0);
out.race = { rings: rings(race), ev: fly(race, true), fin: race.finished, rec: race.record };
const canyon = new CanyonRun(terrain, scene);
out.canyon = { rings: rings(canyon), target: arr(canyon.targetPos), idx: canyon.targetIdx, ev: fly(canyon, false), success: canyon.success, time: canyon.time };
const tube = new TubeRun(terrain, scene, V(field.x, field.y + 3500, 0));
const pose = tube.startPose();
out.tube = { rings: rings(tube), lap: tube.lapLength, pose: [arr(pose.pos), pose.heading], off: tube.offAxis(V(field.x + 10, field.y + 3500, 900)), ev: fly(tube, false), fin: tube.finalTime, bestLap: tube.bestLap };
console.log(JSON.stringify(out));
