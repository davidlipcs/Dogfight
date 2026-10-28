// Writes roblox/src/shared/JetInfo.luau: the reference points of the game's .glb jets (engine nozzles, lamps, wing tips, the pilot's eye ...) in the
// aircraft frame (metres, +Y forward, +Z up), worked out like Models.typeInfo of web/js/render.js.
//   node tools/gen_jetinfo_lua.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const S = await import(path.join(root, 'web', 'js', 'specs.js'));
const f16json = JSON.parse(fs.readFileSync(path.join(root, 'web', 'assets', 'f16.json'), 'utf8'));

function glbJson(file) {
  const b = fs.readFileSync(file);
  if (b.readUInt32LE(0) !== 0x46546c67) throw new Error('not a glb: ' + file);
  const len = b.readUInt32LE(12);
  return JSON.parse(b.subarray(20, 20 + len).toString('utf8'));
}
const V = (x, y, z) => ({ x, y, z });
// the bounding box of all the meshes of a glb (in the glb's own frame): the accessor min / max of every POSITION, through the node transforms
function matMul(a, b) {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return o;
}
function nodeMatrix(n) {
  if (n.matrix) return n.matrix;
  const t = n.translation || [0, 0, 0], q = n.rotation || [0, 0, 0, 1], sc = n.scale || [1, 1, 1];
  const [x, y, z, w] = q;
  const r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0, 2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0, 2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0, 0, 0, 0, 1];
  return matMul([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, t[0], t[1], t[2], 1], matMul(r, [sc[0], 0, 0, 0, 0, sc[1], 0, 0, 0, 0, sc[2], 0, 0, 0, 0, 1]));
}
function glbBounds(j) {
  const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
  const walk = (i, parent) => {
    const n = j.nodes[i], m = matMul(parent, nodeMatrix(n));
    if (n.mesh !== undefined) {
      for (const pr of j.meshes[n.mesh].primitives) {
        const a = j.accessors[pr.attributes.POSITION];
        if (!a.min || !a.max) continue;
        for (let c = 0; c < 8; c++) {
          const p = [c & 1 ? a.max[0] : a.min[0], c & 2 ? a.max[1] : a.min[1], c & 4 ? a.max[2] : a.min[2]];
          for (let k = 0; k < 3; k++) {
            const v = m[k] * p[0] + m[4 + k] * p[1] + m[8 + k] * p[2] + m[12 + k];
            lo[k] = Math.min(lo[k], v); hi[k] = Math.max(hi[k], v);
          }
        }
      }
    }
    for (const c of n.children || []) walk(c, m);
  };
  const ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  for (const i of j.scenes[j.scene || 0].nodes) walk(i, ident);
  return { lo, hi };
}
const add = (a, b) => V(a.x + b.x, a.y + b.y, a.z + b.z);
const VAPOR_STEP = { f16: [0.27, -1.0, -0.03], fa18: [0.45, -1.4, -0.05] };
const specs = { ...S.AIRCRAFT, ...S.TRAINERS, ...S.BANDITS };
const seen = {}, out = {};
for (const spec of Object.values(specs)) {
  if (seen[spec.model]) continue;
  seen[spec.model] = true;
  const file = path.join(root, 'web', 'assets', spec.model + '.glb');
  if (!fs.existsSync(file)) continue;
  const j = glbJson(file);
  const scene = j.scenes[j.scene || 0].nodes;
  let nodes = scene.map((i) => j.nodes[i]);
  if (nodes.length === 1) nodes = (nodes[0].children || []).map((i) => j.nodes[i]);
  const marks = nodes.filter((n) => n.mesh === undefined && !(n.children || []).length);
  const gm = marks.find((n) => n.name === 'ref_gear_main_R');
  const modelZ = -(spec.gearHeight + gm.translation[1]);
  const bb = glbBounds(j);
  const ref = {};
  for (const n of marks) { const p = n.translation || [0, 0, 0]; ref[n.name] = V(p[0], -p[2], p[1] + modelZ); }
  const pick = (re) => Object.keys(ref).filter((k) => re.test(k)).sort().map((k) => ref[k]);
  const nozzles = pick(/^ref_nozzle/);
  const step = VAPOR_STEP[spec.model] || VAPOR_STEP.f16;
  const vL = ref.ref_vapor_L, vR = ref.ref_vapor_R;
  const nav = [[ref.ref_nav_L, 0xff2a1a], [ref.ref_nav_R, 0x33ff55], [ref.ref_tail, 0xfffff0]];
  if (ref.ref_intake_light_L) nav.push([ref.ref_intake_light_L, 0xff2a1a], [ref.ref_intake_light_R, 0x33ff55]);
  const legacy = spec.model === 'f16';
  const tail = nozzles.reduce((a, n) => add(a, V(n.x / nozzles.length, n.y / nozzles.length, n.z / nozzles.length)), V(0, 0, 0));
  const panelByModel = { f22: V(0, 4.98, 0.82 + modelZ), f15: V(0, 5.42, 1.13 + modelZ) };
  out[spec.model] = {
    modelZ, gearHeight: spec.gearHeight, flameScale: spec.engines > 1 ? 0.84 : 1, nozzles, tail,
    nav: nav.filter((x) => x[0]).map(([p, c]) => ({ pos: p, color: c })),
    wingtips: [ref.ref_wingtip_L, ref.ref_wingtip_R].filter(Boolean),
    vapor: vL && vR ? [vL, vR, add(vL, V(-step[0], step[1], step[2])), add(vR, V(step[0], step[1], step[2]))] : [],
    strobes: pick(/^ref_strobe/), gun: ref.ref_gun || V(0, 4, 0),
    cockpit: legacy ? 'legacy' : 'self',
    eye: legacy ? V(...f16json.eye) : ref.ref_eye || V(0, 2.4, 1.1),
    panel: legacy ? V(0, 3.28, 0.63) : ref.ref_panel || panelByModel[spec.model] || V(0, 5.37, 1.0 + modelZ),
    panelFov: legacy ? 30 : { f22: 42, f15: 38 }[spec.model] || 40,
    bbox: { min: V(bb.lo[0], -bb.hi[2], bb.lo[1] + modelZ), max: V(bb.hi[0], -bb.lo[2], bb.hi[1] + modelZ) },
    refs: ref,
  };
}
const num = (x) => String(Math.round(x * 10000) / 10000);
const vec = (v) => `{ ${num(v.x)}, ${num(v.y)}, ${num(v.z)} }`;
let src = `--!nonstrict
-- GENERATED by tools/gen_jetinfo_lua.mjs from the .glb models of web/assets - do not edit by hand.
-- Reference points of every jet in the aircraft frame (metres: x right, y forward, z up); vectors are { x, y, z }.
return {
`;
for (const [k, o] of Object.entries(out)) {
  src += `\t${k} = {\n\t\tmodelZ = ${num(o.modelZ)}, gearHeight = ${o.gearHeight}, flameScale = ${o.flameScale}, cockpit = "${o.cockpit}", panelFov = ${o.panelFov},\n`;
  src += `\t\tbbox = { min = ${vec(o.bbox.min)}, max = ${vec(o.bbox.max)} },\n`;
  src += `\t\ttail = ${vec(o.tail)}, gun = ${vec(o.gun)}, eye = ${vec(o.eye)}, panel = ${vec(o.panel)},\n`;
  src += `\t\tnozzles = { ${o.nozzles.map(vec).join(', ')} },\n`;
  src += `\t\twingtips = { ${o.wingtips.map(vec).join(', ')} },\n`;
  src += `\t\tvapor = { ${o.vapor.map(vec).join(', ')} },\n`;
  src += `\t\tstrobes = { ${o.strobes.map(vec).join(', ')} },\n`;
  src += `\t\tnav = { ${o.nav.map((n) => `{ pos = ${vec(n.pos)}, color = 0x${n.color.toString(16).padStart(6, '0')} }`).join(', ')} },\n`;
  src += `\t\trefs = {\n${Object.entries(o.refs).map(([n, v]) => `\t\t\t${n} = ${vec(v)}`).join(',\n')}\n\t\t},\n\t},\n`;
}
src += '}\n';
fs.writeFileSync(path.join(root, 'roblox', 'src', 'shared', 'JetInfo.luau'), src);
console.log('JetInfo.luau:', Object.keys(out).join(' '));
