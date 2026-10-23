// Aircraft built in code (no model file): the trainers of the career (T-6A, T-38C, T-45C) and the Sukhois
// (Su-35, Su-57).  A jet is described by its real dimensions - fuselage cross sections from the nose to the
// tail, wings and tails as tapered slabs, engine nacelles, nozzles, canopy, landing gear - and built into the
// same kind of object the Blender models give (moving parts, gear legs, reference points), in the game's
// frame: +Y forward, +Z up, +X right, the origin at the centre of gravity.
import { THREE, V } from './util.js';

const DEG = Math.PI / 180;

// ---------------------------------------------------------------- geometry
// fuselage: cross sections [y, half width, half height, z centre, roundness (2 = ellipse, 4 = boxy)]
function loft(st, seg = 28) {
  const pos = [], idx = [], rings = st.length;
  for (const [y, hw, hh, zc, ex = 2] of st) {
    for (let k = 0; k < seg; k++) {
      const a = (k / seg) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a), e = 2 / ex;
      pos.push(Math.sign(c) * Math.pow(Math.abs(c), e) * hw, y, zc + Math.sign(s) * Math.pow(Math.abs(s), e) * hh);
    }
  }
  for (let r = 0; r < rings - 1; r++) for (let k = 0; k < seg; k++) {
    const a = r * seg + k, b = r * seg + (k + 1) % seg, c = a + seg, d = b + seg;
    idx.push(a, c, b, b, c, d);
  }
  // caps at both ends
  for (const r of [0, rings - 1]) {
    const ci = pos.length / 3, [y, , , zc] = st[r];
    pos.push(0, y, zc);
    for (let k = 0; k < seg; k++) idx.push(ci, r * seg + k, r * seg + (k + 1) % seg);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
// a lifting surface between a root and a tip section: [le, te] chord positions (y), span positions (x),
// heights (z), thickness as a share of the chord.  Built along +X; `vertical` turns it into a fin (span up).
function slab(root, tip, x0, x1, z0, z1, thick = 0.05) {
  const sec = (le, te, x, z) => {
    const c = le - te, t = c * thick;
    return [[x, le, z], [x, le - c * 0.3, z + t / 2], [x, te, z], [x, le - c * 0.3, z - t / 2]];
  };
  const A = sec(root[0], root[1], x0, z0), B = sec(tip[0], tip[1], x1, z1), pos = [], idx = [];
  for (const p of [...A, ...B]) pos.push(...p);
  for (let k = 0; k < 4; k++) { const a = k, b = (k + 1) % 4; idx.push(a, b, 4 + b, a, 4 + b, 4 + a); }
  idx.push(0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
const mirrorX = (g) => g.clone().scale(-1, 1, 1);
// a fin: a slab built along +X, then stood up (span along +Z) and canted outwards
function fin(x, root, tip, z0, z1, cant, thick = 0.05) {
  const g = slab(root, tip, 0, z1 - z0, 0, 0, thick);
  g.rotateY(-Math.PI / 2 + cant * DEG);       // +X (span) -> +Z, leaning outwards by `cant`
  g.translate(x, 0, z0);
  return g;
}

// ------------------------------------------------------------------ painting
function decal(kind) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const star = (cx, cy, r, fill) => {
    g.beginPath();
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.4 : r;
      g.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
    }
    g.closePath(); g.fillStyle = fill; g.fill();
  };
  if (kind === 'us') {                                  // star and bar
    g.fillStyle = '#ffffff'; g.fillRect(4, 50, 120, 28);
    g.fillStyle = '#b22234'; g.fillRect(8, 60, 112, 8);
    g.fillStyle = '#1b2f6b'; g.beginPath(); g.arc(64, 64, 34, 0, Math.PI * 2); g.fill();
    star(64, 64, 30, '#ffffff');
  } else if (kind === 'ru') {                           // red star with a white and blue border (Russian air force)
    star(64, 66, 60, '#1b3f8f'); star(64, 66, 50, '#ffffff'); star(64, 66, 40, '#cc1d1d');
  } else if (kind === 'cn') {                           // red star with a yellow border and red bars (PLAAF)
    g.fillStyle = '#cc1d1d'; g.fillRect(2, 54, 124, 20); g.fillStyle = '#f2c230'; g.fillRect(2, 60, 124, 8);
    star(64, 64, 46, '#f2c230'); star(64, 64, 38, '#cc1d1d');
  } else {                                              // roundels: [outer, middle, centre] (or the Swedish crowns)
    const ring = { uk: ['#1f3b8a', '#ffffff', '#c8102e'], fr: ['#c8102e', '#ffffff', '#1f3b8a'], se: ['#1f5aa8', '#1f5aa8', '#1f5aa8'] }[kind] || ['#888', '#ccc', '#444'];
    ring.forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(64, 64, 58 - i * 19, 0, Math.PI * 2); g.fill(); });
    if (kind === 'se') {
      g.fillStyle = '#f5c400';
      for (const [cx, cy] of [[64, 40], [44, 76], [84, 76]]) { g.fillRect(cx - 11, cy - 4, 22, 10); for (let k = -1; k <= 1; k++) g.fillRect(cx + k * 8 - 2, cy - 11, 4, 8); }
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.encoding = THREE.sRGBEncoding;
  return t;
}

// ------------------------------------------------------------------ the jets
// every length in metres; y from the nose (+) to the tail (-)
export const DESIGNS = {
  mig29: {
    name: 'MiG-29 Fulcrum', paint: 0x9aa9b6, accent: 0x6f8296, nation: 'ru', camo: true,
    fus: [[8.65, 0.03, 0.03, -0.15], [7.4, 0.35, 0.38, -0.1], [5.8, 0.6, 0.62, 0.05], [4.3, 0.72, 0.82, 0.15], [2.6, 1.1, 0.72, 0.2, 2.4],
      [0.5, 2.1, 0.48, 0.2, 3], [-2.5, 2.2, 0.42, 0.15, 3], [-5.5, 1.6, 0.38, 0.12, 3], [-7.6, 0.5, 0.3, 0.1], [-8.6, 0.25, 0.2, 0.1]],
    canopy: [[5.2, 2.2], 0.86, 0.62], seats: [0.38], antiglare: [6.1, 5.2],
    nacelles: [[1.15, -0.6, [[2.6, 0.5, 0.42, 4], [1.0, 0.6, 0.52, 4], [-3.0, 0.62, 0.55, 3], [-6.6, 0.55, 0.5, 2.4], [-7.9, 0.52, 0.48, 2]]]],
    wing: { root: [0.2, -4.6], tip: [-3.6, -5.2], x0: 2.1, x1: 5.68, z0: 0.12, z1: 0.0, thick: 0.04 },
    htail: { root: [-5.6, -7.9], tip: [-7.3, -8.4], x0: 1.9, x1: 3.9, z0: -0.05, z1: -0.05 },
    vtails: [{ x: 1.75, root: [-4.2, -7.4], tip: [-6.6, -7.8], z0: 0.45, z1: 3.55, cant: 6 }, { x: -1.75, root: [-4.2, -7.4], tip: [-6.6, -7.8], z0: 0.45, z1: 3.55, cant: -6 }],
    nozzles: [[-1.15, -8.0, -0.6, 0.5], [1.15, -8.0, -0.6, 0.5]], gun: [-1.0, 4.5, 0.2],
    gear: [[0, 5.6, -0.6, 1.82, 0.3, -95], [-1.6, -1.2, -0.45, 1.85, 0.42, 95], [1.6, -1.2, -0.45, 1.85, 0.42, 95]],
    decals: { side: [-6.2, 1.88, 2.3], wing: [4.2, -3.6] },
  },
  mig31: {
    name: 'MiG-31 Foxhound', paint: 0xa6aeb5, accent: 0x7d8790, nation: 'ru',
    fus: [[11.3, 0.03, 0.03, -0.1], [9.8, 0.45, 0.5, 0.0], [8.0, 0.7, 0.75, 0.1], [6.5, 0.8, 0.9, 0.2], [4.0, 0.95, 0.95, 0.2, 2.6],
      [1.5, 2.3, 0.95, 0.1, 5], [-4.0, 2.4, 0.85, 0.05, 5], [-8.5, 2.2, 0.75, 0.0, 5], [-11.0, 1.9, 0.65, 0.0, 4]],
    canopy: [[7.4, 3.4], 0.86, 0.62], seats: [0.25, 0.68], antiglare: [8.4, 7.4],
    intakes: [[2.3, 2.2, 0.05, 1.05]],
    wing: { root: [-1.0, -6.2], tip: [-4.6, -6.6], x0: 2.4, x1: 6.73, z0: 0.6, z1: 0.4, thick: 0.04 },
    htail: { root: [-8.0, -11.0], tip: [-10.2, -11.4], x0: 2.1, x1: 4.4, z0: 0.2, z1: 0.2 },
    vtails: [{ x: 1.9, root: [-6.0, -10.4], tip: [-9.0, -10.9], z0: 0.8, z1: 3.6, cant: 8 }, { x: -1.9, root: [-6.0, -10.4], tip: [-9.0, -10.9], z0: 0.8, z1: 3.6, cant: -8 }],
    nozzles: [[-1.0, -11.4, 0.0, 0.62], [1.0, -11.4, 0.0, 0.62]], gun: [1.2, 1.0, -0.5],
    gear: [[0, 7.0, -0.8, 1.73, 0.35, -95], [-2.0, -2.0, -0.7, 1.7, 0.48, 95], [2.0, -2.0, -0.7, 1.7, 0.48, 95]],
    decals: { side: [-8.8, 2.08, 2.4], wing: [4.6, -5.0] },
  },
  gripen: {
    name: 'JAS 39 Gripen', paint: 0x8e98a2, accent: 0x6a7580, nation: 'se',
    fus: [[7.05, 0.03, 0.03, -0.1], [5.9, 0.32, 0.36, 0.0], [4.4, 0.5, 0.6, 0.1], [3.0, 0.58, 0.72, 0.15], [1.0, 0.85, 0.7, 0.1, 2.6],
      [-2.0, 0.82, 0.66, 0.05, 2.4], [-5.0, 0.66, 0.6, 0.05], [-6.6, 0.5, 0.48, 0.05], [-7.05, 0.46, 0.44, 0.05]],
    canopy: [[3.7, 1.3], 0.9, 0.58], seats: [0.35], antiglare: [4.7, 3.7],
    intakes: [[0.75, 1.6, -0.05, 0.8]],
    canards: { root: [1.5, 0.2], tip: [0.6, 0.3], x0: 0.65, x1: 2.3, z0: 0.15, z1: 0.2 },
    wing: { root: [-0.6, -5.6], tip: [-4.9, -5.4], x0: 0.75, x1: 4.2, z0: -0.15, z1: -0.15, thick: 0.035 },
    vtails: [{ x: 0, root: [-2.8, -6.8], tip: [-5.6, -6.9], z0: 0.6, z1: 3.1, cant: 0 }],
    nozzles: [[0, -7.2, 0.05, 0.42]], gun: [-0.6, 1.0, -0.4],
    gear: [[0, 3.4, -0.55, 1.02, 0.2, -95], [-1.0, -2.0, -0.5, 1.0, 0.27, 95], [1.0, -2.0, -0.5, 1.0, 0.27, 95]],
    decals: { side: [-5.6, 0.06, 2.0], wing: [3.0, -4.6] },
  },
  typhoon: {
    name: 'Eurofighter Typhoon', paint: 0xb3bcc4, accent: 0x8a949e, nation: 'uk',
    fus: [[7.98, 0.03, 0.03, -0.1], [6.6, 0.35, 0.4, 0.0], [5.0, 0.55, 0.65, 0.1], [3.4, 0.62, 0.78, 0.18], [1.0, 0.68, 0.72, 0.2, 2.5],
      [-2.5, 0.75, 0.65, 0.1, 2.5], [-5.5, 1.05, 0.55, 0.0, 3], [-7.4, 1.0, 0.5, 0.0, 3], [-7.98, 0.95, 0.48, 0.0, 3]],
    canopy: [[4.2, 1.6], 0.9, 0.6], seats: [0.35], antiglare: [5.2, 4.2],
    chin: [1.4, 3.4, 1.6, 0.75, -0.85],
    canards: { root: [4.3, 3.3], tip: [3.2, 2.9], x0: 0.6, x1: 2.35, z0: 0.0, z1: 0.05 },
    wing: { root: [0.4, -7.0], tip: [-5.8, -6.6], x0: 0.75, x1: 5.47, z0: -0.35, z1: -0.4, thick: 0.035 },
    vtails: [{ x: 0, root: [-3.4, -7.7], tip: [-6.6, -7.9], z0: 0.6, z1: 3.6, cant: 0 }],
    nozzles: [[-0.45, -8.2, -0.05, 0.42], [0.45, -8.2, -0.05, 0.42]], gun: [0.8, 1.0, -0.3],
    gear: [[0, 4.4, -0.9, 1.0, 0.22, -95], [-1.25, -2.6, -0.6, 1.22, 0.3, 95], [1.25, -2.6, -0.6, 1.22, 0.3, 95]],
    decals: { side: [-1.2, 0, 0.1], wing: [3.6, -4.8] },
  },
  rafale: {
    name: 'Dassault Rafale', paint: 0x707881, accent: 0x565d65, nation: 'fr',
    fus: [[7.63, 0.03, 0.03, -0.1], [6.3, 0.32, 0.38, 0.0], [4.8, 0.52, 0.62, 0.1], [3.3, 0.6, 0.75, 0.15], [1.2, 0.95, 0.7, 0.1, 2.6],
      [-2.0, 1.0, 0.62, 0.05, 2.6], [-5.5, 0.95, 0.55, 0.0, 2.6], [-7.2, 0.85, 0.48, 0.0, 2.4], [-7.63, 0.8, 0.45, 0.0, 2.4]],
    canopy: [[4.0, 1.4], 0.9, 0.6], seats: [0.35], antiglare: [5.0, 4.0],
    intakes: [[0.95, 1.9, -0.45, 0.85]],
    canards: { root: [2.0, 0.6], tip: [0.9, 0.5], x0: 0.8, x1: 2.6, z0: 0.25, z1: 0.35 },
    wing: { root: [-0.3, -6.6], tip: [-5.3, -6.4], x0: 0.9, x1: 5.45, z0: -0.3, z1: -0.25, thick: 0.035 },
    vtails: [{ x: 0, root: [-3.2, -7.3], tip: [-6.3, -7.5], z0: 0.55, z1: 3.4, cant: 0 }],
    nozzles: [[-0.5, -7.8, -0.05, 0.4], [0.5, -7.8, -0.05, 0.4]], gun: [0.9, 0.8, -0.3],
    gear: [[0, 4.3, -0.6, 1.2, 0.22, -95], [-1.3, -2.0, -0.6, 1.12, 0.3, 95], [1.3, -2.0, -0.6, 1.12, 0.3, 95]],
    decals: { side: [-1.6, 0, 0.0], wing: [3.6, -4.6] },
  },
  j20: {
    name: 'Chengdu J-20', paint: 0x5e656d, accent: 0x4b5158, nation: 'cn', internal: true,
    fus: [[10.2, 0.03, 0.03, -0.2], [8.6, 0.5, 0.45, -0.1, 3], [6.6, 0.8, 0.65, 0.05, 3], [5.0, 0.95, 0.82, 0.15, 3], [2.5, 1.7, 0.65, 0.15, 3.4],
      [-1.0, 2.2, 0.55, 0.1, 3.5], [-5.0, 2.0, 0.5, 0.05, 3.5], [-8.5, 1.5, 0.45, 0.0, 3], [-10.2, 1.3, 0.4, 0.0, 3]],
    canopy: [[5.9, 3.0], 0.85, 0.62], seats: [0.36], antiglare: [7.0, 5.9], tint: true,
    intakes: [[1.3, 3.4, -0.15, 0.9]],
    canards: { root: [3.2, 1.4], tip: [1.7, 1.2], x0: 1.5, x1: 3.9, z0: 0.3, z1: 0.32 },
    wing: { root: [-0.6, -7.4], tip: [-6.2, -7.6], x0: 2.0, x1: 6.75, z0: 0.2, z1: 0.1, thick: 0.035 },
    vtails: [{ x: 1.4, root: [-6.6, -9.6], tip: [-8.8, -10.0], z0: 0.45, z1: 2.6, cant: 20 }, { x: -1.4, root: [-6.6, -9.6], tip: [-8.8, -10.0], z0: 0.45, z1: 2.6, cant: -20 }],
    nozzles: [[-0.75, -10.5, -0.05, 0.55], [0.75, -10.5, -0.05, 0.55]], gun: [1.0, 4.0, 0.0],
    gear: [[0, 6.5, -0.5, 2.0, 0.32, -95], [-1.8, -2.5, -0.5, 1.85, 0.47, 95], [1.8, -2.5, -0.5, 1.85, 0.47, 95]],
    decals: { side: null, wing: [5.0, -6.0] },
  },
  t6: {
    name: 'T-6A Texan II', paint: 0xf2f3f5, accent: 0x1f3a7a, nation: 'us', prop: true,
    fus: [[5.15, 0.06, 0.06, 0.0], [4.85, 0.42, 0.45, 0.0], [3.9, 0.55, 0.62, 0.05], [2.4, 0.56, 0.72, 0.1], [0.4, 0.52, 0.7, 0.12],
      [-1.5, 0.44, 0.58, 0.15], [-3.5, 0.24, 0.36, 0.3], [-5.0, 0.08, 0.14, 0.45]],
    canopy: [[2.55, -0.85], 0.86, 0.62], seats: [0.24, 0.66], antiglare: [3.4, 2.55],
    wing: { root: [1.25, -0.85], tip: [0.45, -0.45], x0: 0.45, x1: 5.1, z0: -0.48, z1: -0.02, thick: 0.13 },
    htail: { root: [-4.15, -5.0], tip: [-4.7, -5.15], x0: 0.15, x1: 2.45, z0: 0.35, z1: 0.42 },
    vtails: [{ x: 0, root: [-3.2, -5.05], tip: [-4.55, -5.25], z0: 0.35, z1: 2.0, cant: 0 }],
    nozzles: [], gun: [0, 4, -0.3],
    gear: [[0, 3.3, -0.45, 0.9, 0.2, -95], [-1.55, 0.2, -0.5, 0.85, 0.27, 95], [1.55, 0.2, -0.5, 0.85, 0.27, 95]],
    stripes: [[-3.6, -4.2]], decals: { side: [-2.2, 0.0, 0.9], wing: [3.3, -0.1] },
  },
  t38: {
    name: 'T-38C Talon', paint: 0xeef0f3, accent: 0x14284f, nation: 'us',
    fus: [[7.05, 0.02, 0.02, -0.05], [5.8, 0.2, 0.25, 0.0], [4.5, 0.38, 0.45, 0.05], [3.0, 0.5, 0.62, 0.12], [1.0, 0.62, 0.64, 0.08, 2.6],
      [-1.5, 0.66, 0.58, 0.02, 2.6], [-4.5, 0.6, 0.5, 0.0, 2.6], [-6.6, 0.56, 0.42, 0.0, 2.4], [-7.05, 0.52, 0.38, 0.0, 2.4]],
    canopy: [[3.55, 0.1], 0.96, 0.55], seats: [0.22, 0.66], antiglare: [4.6, 3.55],
    wing: { root: [0.7, -3.25], tip: [-1.85, -2.65], x0: 0.5, x1: 3.85, z0: -0.25, z1: -0.25, thick: 0.045 },
    htail: { root: [-4.9, -6.65], tip: [-6.05, -6.95], x0: 0.45, x1: 2.25, z0: 0.05, z1: 0.05 },
    vtails: [{ x: 0, root: [-3.6, -6.7], tip: [-5.95, -6.75], z0: 0.45, z1: 2.95, cant: 0 }],
    intakes: [[0.62, 1.6, -0.6, 0.05]], nozzles: [[-0.28, -7.1, 0.0, 0.24], [0.28, -7.1, 0.0, 0.24]], gun: [0, 5, -0.2],
    gear: [[0, 4.0, -0.45, 0.8, 0.2, -95], [-1.1, -1.6, -0.45, 0.78, 0.26, 95], [1.1, -1.6, -0.45, 0.78, 0.26, 95]],
    stripes: [[-5.6, -6.2]], decals: { side: [-3.8, 0.66, 0.0], wing: [2.6, -2.4] },
  },
  t45: {
    name: 'T-45C Goshawk', paint: 0xf4f4f2, accent: 0xff5a1f, nation: 'us', hook: true,
    fus: [[6.0, 0.02, 0.02, -0.15], [5.2, 0.28, 0.35, -0.1], [3.8, 0.48, 0.62, 0.0], [2.4, 0.55, 0.75, 0.1], [0.8, 0.62, 0.72, 0.1, 2.4],
      [-1.5, 0.6, 0.62, 0.05, 2.4], [-4.0, 0.42, 0.48, 0.15], [-5.95, 0.3, 0.34, 0.25]],
    canopy: [[3.3, 0.15], 0.92, 0.6], seats: [0.22, 0.64], antiglare: [4.3, 3.3],
    wing: { root: [1.2, -2.05], tip: [-1.0, -1.9], x0: 0.5, x1: 4.7, z0: -0.45, z1: -0.28, thick: 0.08 },
    htail: { root: [-4.2, -5.6], tip: [-5.3, -6.0], x0: 0.3, x1: 2.3, z0: 0.2, z1: 0.55 },
    vtails: [{ x: 0, root: [-2.6, -5.65], tip: [-5.0, -6.05], z0: 0.5, z1: 2.65, cant: 0 }],
    intakes: [[0.6, 1.4, -0.7, 0.05]], nozzles: [[0, -6.0, 0.22, 0.3]], gun: [0, 4, -0.4],
    gear: [[0, 3.6, -0.5, 1.05, 0.22, -95], [-1.5, -0.6, -0.55, 0.95, 0.3, 95], [1.5, -0.6, -0.55, 0.95, 0.3, 95]],
    stripes: [[-4.4, -5.0], [5.25, 4.9]], tipColor: true, decals: { side: [-2.9, 0.5, 0.15], wing: [3.4, -0.8] },
  },
  su35: {
    name: 'Su-35S Flanker-E', paint: 0x93a1ae, accent: 0x5e6c7d, nation: 'ru',
    fus: [[11.0, 0.03, 0.03, -0.3], [9.5, 0.45, 0.5, -0.2], [7.5, 0.7, 0.75, 0.0], [6.0, 0.85, 0.95, 0.15], [4.0, 1.25, 0.9, 0.2, 2.4],
      [1.5, 2.6, 0.55, 0.25, 3], [-2.0, 2.8, 0.5, 0.2, 3], [-6.0, 2.3, 0.45, 0.15, 3], [-9.0, 0.6, 0.35, 0.15], [-11.2, 0.3, 0.25, 0.15]],
    canopy: [[7.1, 3.7], 0.86, 0.72], seats: [0.36], antiglare: [8.1, 7.1],
    nacelles: [[1.45, -0.7, [[4.2, 0.55, 0.5, 4], [2.5, 0.68, 0.6, 4], [-2.0, 0.72, 0.62, 3], [-6.5, 0.68, 0.6, 2.4], [-8.4, 0.62, 0.58, 2]]]],
    wing: { root: [0.6, -5.6], tip: [-4.6, -6.4], x0: 2.6, x1: 7.6, z0: 0.15, z1: 0.0, thick: 0.04 },
    htail: { root: [-7.2, -10.0], tip: [-9.4, -10.6], x0: 2.4, x1: 4.6, z0: -0.15, z1: -0.15 },
    vtails: [{ x: 2.15, root: [-5.2, -8.8], tip: [-8.0, -9.4], z0: 0.55, z1: 4.25, cant: 3 }, { x: -2.15, root: [-5.2, -8.8], tip: [-8.0, -9.4], z0: 0.55, z1: 4.25, cant: -3 }],
    nozzles: [[-1.45, -8.7, -0.7, 0.6], [1.45, -8.7, -0.7, 0.6]], gun: [1.0, 5.5, 0.3],
    gear: [[0, 6.2, -0.7, 1.95, 0.35, -95], [-2.2, -1.5, -0.5, 2.05, 0.5, 95], [2.2, -1.5, -0.5, 2.05, 0.5, 95]],
    camo: true, decals: { side: [-7.3, 2.25, 2.6], wing: [5.6, -4.4] },
  },
  su57: {
    name: 'Su-57 Felon', paint: 0x9fa8b2, accent: 0x667383, nation: 'ru', internal: true,
    fus: [[10.0, 0.03, 0.03, -0.2], [8.7, 0.5, 0.42, -0.15, 3], [6.8, 0.82, 0.62, 0.0, 3], [5.3, 0.98, 0.82, 0.15, 3], [3.0, 1.9, 0.6, 0.15, 3.2],
      [0.0, 3.0, 0.45, 0.1, 3.5], [-4.0, 2.9, 0.4, 0.1, 3.5], [-7.5, 1.6, 0.35, 0.1, 3], [-9.6, 0.7, 0.25, 0.1, 2.5]],
    canopy: [[6.4, 3.5], 0.82, 0.66], seats: [0.36], antiglare: [7.4, 6.4], tint: true,
    nacelles: [[1.6, -0.55, [[4.0, 0.62, 0.48, 5], [1.0, 0.7, 0.55, 4], [-4.0, 0.72, 0.58, 3], [-8.0, 0.64, 0.55, 2.4], [-9.0, 0.6, 0.52, 2]]]],
    wing: { root: [1.0, -5.6], tip: [-4.4, -6.0], x0: 3.0, x1: 7.05, z0: 0.1, z1: 0.05, thick: 0.035 },
    htail: { root: [-6.3, -9.3], tip: [-8.6, -9.8], x0: 3.2, x1: 5.3, z0: 0.0, z1: 0.0 },
    vtails: [{ x: 2.3, root: [-5.4, -8.4], tip: [-7.6, -8.9], z0: 0.5, z1: 2.7, cant: 26 }, { x: -2.3, root: [-5.4, -8.4], tip: [-7.6, -8.9], z0: 0.5, z1: 2.7, cant: -26 }],
    nozzles: [[-1.6, -9.3, -0.55, 0.58], [1.6, -9.3, -0.55, 0.58]], gun: [1.0, 5.0, 0.2],
    gear: [[0, 5.5, -0.6, 2.0, 0.33, -95], [-2.0, -1.2, -0.5, 1.95, 0.48, 95], [2.0, -1.2, -0.5, 1.95, 0.48, 95]],
    camo: true, decals: { side: null, wing: [5.4, -4.0] },
  },
};

// where the canopy sits and where the pilot's eye is: the canopy's base is the fuselage top at the cockpit
// (the sill), its height and width come from the design (canopy: [[front, back], width share, height]); the
// front seat's eye is 62 % up inside it, the instrument panel in front of the knees
export function cockpitGeom(d) {
  const [[c0, c1], wRel, hh] = d.canopy, len = c0 - c1, ymid = (c0 + c1) / 2;
  const sec = (y) => {
    for (let i = 0; i < d.fus.length - 1; i++) {
      const a = d.fus[i], b = d.fus[i + 1];
      if (y <= a[0] && y >= b[0]) { const t = (a[0] - y) / (a[0] - b[0]); return a.map((v, k) => v + (b[k] - v) * t); }
    }
    return d.fus[1];
  };
  const f = sec(ymid), hw = f[1] * wRel, base = f[3] + f[2] * 0.82;
  const seats = d.seats || [0.32];
  const eyeY = c0 - len * seats[0] - 0.05, eye = V(0, eyeY, base + hh * 0.62);
  // the panel's top edge sits 18 cm under the eye line, 70 cm in front: the view ahead stays clear
  return { c0, c1, len, hw, hh, base, seats, eye, panelY: eyeY + 0.7, panelZ: eye.z - 0.36 };
}

// reference points (aircraft frame) the game hangs effects on: the same set typeInfo() reads from a Blender model
export function procInfo(spec) {
  const d = DESIGNS[spec.model], w = d.wing;
  const nozzles = d.nozzles.map(([x, y, z]) => V(x, y, z));
  const tip = (s) => V(s * w.x1, w.tip[0] - (w.tip[0] - w.tip[1]) * 0.5, w.z1);
  const tail = nozzles.length ? nozzles.reduce((a, n) => a.add(n.clone().multiplyScalar(1 / nozzles.length)), V()) : V(0, d.fus[d.fus.length - 1][0], 0.3);
  const ck = cockpitGeom(d), eye = ck.eye;
  return {
    key: spec.model, spec, modelZ: 0, ref: {}, nozzles, proc: true,
    nav: [[tip(-1), 0xff2a1a], [tip(1), 0x33ff55], [V(0, d.fus[d.fus.length - 1][0], 1.0), 0xfffff0]],
    gearHeight: spec.gearHeight, flameScale: d.nozzles.length > 1 ? (d.nozzles[0][3] > 0.4 ? 1.15 : 0.55) : 0.7,
    tail, wingtips: [tip(-1), tip(1)],
    vapor: [V(-w.x0, w.root[0] - 0.5, w.z0 + 0.1), V(w.x0, w.root[0] - 0.5, w.z0 + 0.1), V(-w.x0 * 2, w.root[0] - 1.2, w.z0), V(w.x0 * 2, w.root[0] - 1.2, w.z0)],
    strobes: [], gun: V(...d.gun), cockpit: 'self', eye,
    panel: V(0, ck.panelY, ck.panelZ), panelFov: 46,
  };
}

// a camouflage texture (Sukhois): soft splinter blotches of two greys
function camoTex(a, b) {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  g.fillStyle = '#' + a.toString(16).padStart(6, '0'); g.fillRect(0, 0, 256, 256);
  g.fillStyle = '#' + b.toString(16).padStart(6, '0');
  let s = 7;
  const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 26; i++) {
    g.beginPath();
    const x = r() * 256, y = r() * 256;
    for (let k = 0; k < 6; k++) g.lineTo(x + (r() - 0.5) * 90, y + (r() - 0.5) * 90);
    g.closePath(); g.fill();
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.encoding = THREE.sRGBEncoding;
  return t;
}
// planar UVs (top view) so a texture can lie on any part
function topUV(g, scale = 0.12) {
  const p = g.attributes.position, uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) { uv[i * 2] = p.getX(i) * scale + p.getZ(i) * scale * 0.5; uv[i * 2 + 1] = p.getY(i) * scale; }
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return g;
}

const cache = {};
// build one jet.  skin: a hangar paint scheme (tint) for the player, or null
export function buildProc(key, env, skin = null) {
  const d = DESIGNS[key];
  const ck = `${key}:${skin ? skin.id : '-'}`;
  const m = cache[ck] || (cache[ck] = (() => {
    // the design colours are sRGB values: convert them, or the light greys come out white
    const paintCol = new THREE.Color(d.paint).convertSRGBToLinear(), accentCol = new THREE.Color(d.accent).convertSRGBToLinear();
    if (skin && skin.id !== 'factory') { const t = new THREE.Color(skin.color).convertSRGBToLinear(); paintCol.multiply(t); accentCol.multiply(t); }
    const common = { side: THREE.DoubleSide, envMap: env, envMapIntensity: 0.4 };
    const metal = skin && skin.metal !== null && skin.id !== 'factory' ? skin.metal : 0.25, rough = skin && skin.rough !== null && skin.id !== 'factory' ? skin.rough : 0.55;
    const paint = new THREE.MeshStandardMaterial({ ...common, color: paintCol, metalness: metal, roughness: rough,
      map: d.camo && (!skin || skin.id === 'factory') ? camoTex(d.paint, d.accent) : null, emissive: skin ? skin.emissive : 0 });
    return {
      paint, accent: new THREE.MeshStandardMaterial({ ...common, color: accentCol, metalness: metal, roughness: rough }),
      dark: new THREE.MeshStandardMaterial({ ...common, color: 0x1d2024, metalness: 0.2, roughness: 0.8 }),
      metal: new THREE.MeshStandardMaterial({ ...common, color: 0x6a6660, metalness: 0.9, roughness: 0.35 }),
      glass: new THREE.MeshStandardMaterial({ color: d.tint ? 0xc9a24a : 0x8fb6d0, metalness: 0.95, roughness: 0.04, transparent: true, opacity: 0.38,
        envMap: env, envMapIntensity: 1.8, depthWrite: false, side: THREE.DoubleSide }),
      tyre: new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.9 }),
      gearMat: new THREE.MeshStandardMaterial({ color: 0xd8d8d8, metalness: 0.5, roughness: 0.4 }),
      cockpit: new THREE.MeshStandardMaterial({ color: d.nation === 'ru' ? 0x3d8d8a : 0x2a2e33, roughness: 0.85, side: THREE.DoubleSide }),   // Russian cockpits are turquoise
      screen: new THREE.MeshBasicMaterial({ color: 0x0b1a10 }),
      frame: new THREE.MeshStandardMaterial({ ...common, color: d.camo ? 0x5d6672 : 0x2a2d31, metalness: 0.4, roughness: 0.5 }),
      belt: new THREE.MeshStandardMaterial({ color: 0x8a6a2a, roughness: 0.9 }),
      yellow: new THREE.MeshStandardMaterial({ color: 0xe6b81e, roughness: 0.6 }),
      hudGlass: new THREE.MeshBasicMaterial({ color: 0x6bff85, transparent: true, opacity: 0.12, depthWrite: false, side: THREE.DoubleSide }),
      decal: new THREE.MeshBasicMaterial({ map: decal(d.nation), transparent: true, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2 }),
      nozzle: new THREE.MeshStandardMaterial({ color: 0x4a4038, metalness: 0.8, roughness: 0.5, side: THREE.DoubleSide }),
    };
  })());
  const model = new THREE.Group(), parts = {}, gear = [];
  const add = (g, mat, parent = model) => { const o = new THREE.Mesh(g, mat); parent.add(o); return o; };
  const tex = !!m.paint.map;
  const geo = (g) => (tex ? topUV(g) : g);
  // fuselage, with the accent bands (tail stripe, Goshawk nose) as short lofts of the same sections
  add(geo(loft(d.fus)), m.paint);
  for (const [x, z, st] of d.nacelles || []) for (const s of [-1, 1]) {
    const g = geo(loft(st.map(([y, hw, hh, ex]) => [y, hw, hh, 0, ex])));
    g.translate(s * x, 0, z); add(g, m.paint);
    // the intake mouth
    const [y0, hw, hh] = st[0], mouth = new THREE.PlaneGeometry(hw * 1.7, hh * 1.7);
    mouth.rotateX(Math.PI / 2); mouth.translate(s * x, y0 + 0.01, z); add(mouth, m.dark);
  }
  for (const [x, y, z, w] of d.intakes || []) for (const s of [-1, 1]) {
    const box = new THREE.BoxGeometry(w * 0.55, 2.2, w * 1.2); box.translate(s * x * 0.95, y - 1.1, z); add(geo(box), m.paint);
    const mouth = new THREE.PlaneGeometry(w * 0.5, w * 1.1); mouth.rotateX(Math.PI / 2); mouth.translate(s * x * 0.95, y + 0.01, z); add(mouth, m.dark);
  }
  // ventral (chin) intake: Typhoon
  if (d.chin) {
    const [y, l, w, h, z] = d.chin;
    const box = new THREE.BoxGeometry(w, l, h); box.translate(0, y - l / 2, z); add(geo(box), m.paint);
    const mouth = new THREE.PlaneGeometry(w * 0.9, h * 0.8); mouth.rotateX(Math.PI / 2); mouth.translate(0, y + 0.01, z); add(mouth, m.dark);
  }
  // canards (foreplanes), all-moving like the tailplane
  if (d.canards) {
    const c = d.canards;
    for (const sx of [1, -1]) {
      let cg = slab(c.root, c.tip, c.x0, c.x1, c.z0, c.z1, 0.05);
      if (sx < 0) cg = mirrorX(cg);
      add(geo(cg), m.paint);
    }
  }
  for (const [y0, y1] of d.stripes || []) {
    const st = d.fus.filter(([y]) => y <= Math.max(y0, y1) + 1.5 && y >= Math.min(y0, y1) - 1.5);
    if (st.length >= 2) {
      const lerp = (y) => {
        for (let i = 0; i < d.fus.length - 1; i++) {
          const a = d.fus[i], b = d.fus[i + 1];
          if (y <= a[0] && y >= b[0]) { const t = (a[0] - y) / (a[0] - b[0]); return a.map((v, k) => (k === 0 ? y : v + (b[k] - v) * t)); }
        }
        return null;
      };
      const ra = lerp(Math.max(y0, y1)), rb = lerp(Math.min(y0, y1));
      if (ra && rb) add(loft([ra, rb].map(([y, hw, hh, zc, ex]) => [y, hw * 1.012, hh * 1.012, zc, ex])), m.accent);
    }
  }
  // anti-glare panel in front of the canopy
  if (d.antiglare) {
    const [ya, yb] = d.antiglare, f = d.fus.find(([y]) => y <= ya) || d.fus[1];
    const p = new THREE.PlaneGeometry(f[1] * 1.1, ya - yb); p.translate(0, (ya + yb) / 2, f[3] + f[2] * 0.97); add(p, m.dark);
  }
  // canopy and cockpit (cockpitGeom: the canopy sits on the fuselage top, the pilot's eye inside it)
  {
    const k = cockpitGeom(d), { c0, c1, len, hw, hh, base, eye } = k, ymid = (c0 + c1) / 2;
    const g = new THREE.SphereGeometry(1, 32, 14, 0, Math.PI * 2, 0, Math.PI / 2);
    g.rotateX(Math.PI / 2); g.scale(hw, len / 2, hh); g.translate(0, ymid, base);
    add(g, m.glass).renderOrder = 2;
    // frames: the windscreen arch, the arch between the seats (tandem), and the sill rails
    const arch = (y, t = 0.022) => {
      const f = Math.sqrt(Math.max(0, 1 - ((y - ymid) / (len / 2)) ** 2));
      const a = new THREE.TorusGeometry(1, t, 6, 28, Math.PI); a.rotateX(Math.PI / 2); a.scale(hw * f, 1, hh * f); a.translate(0, y, base);
      add(a, m.frame);
    };
    arch(c0 - len * 0.2);
    if (k.seats.length > 1) arch(c0 - len * 0.55, 0.02);
    for (const sx of [-1, 1]) { const r = new THREE.BoxGeometry(0.035, len * 0.92, 0.035); r.translate(sx * hw * 0.99, ymid, base); add(r, m.frame); }
    // cockpit floor tray just under the sill (hidden from outside by the fuselage)
    const tray = new THREE.BoxGeometry(hw * 1.8, len * 0.9, 0.06); tray.translate(0, ymid, base - 0.02); add(tray, m.cockpit);
    // ejection seats with head boxes, a centre stick and a throttle on the left console
    for (const ky of k.seats) {
      const sy = c0 - len * ky;
      const back = new THREE.BoxGeometry(0.5, 0.14, 0.75); back.translate(0, sy - 0.32, base + 0.38); add(back, m.dark);
      const head = new THREE.BoxGeometry(0.42, 0.22, 0.26); head.translate(0, sy - 0.3, base + 0.86); add(head, m.dark);
      const pan = new THREE.BoxGeometry(0.46, 0.45, 0.1); pan.translate(0, sy - 0.1, base + 0.05); add(pan, m.dark);
      for (const sx of [-1, 1]) { const st = new THREE.BoxGeometry(0.03, 0.03, 0.55); st.translate(sx * 0.16, sy - 0.24, base + 0.5); add(st, m.belt); }
      const stick = new THREE.CylinderGeometry(0.016, 0.02, 0.2, 8); stick.rotateX(Math.PI / 2); stick.translate(0, sy + 0.24, base - 0.02); add(stick, m.dark);
      const grip = new THREE.BoxGeometry(0.04, 0.045, 0.08); grip.translate(0, sy + 0.24, base + 0.1); add(grip, m.dark);
      const thr = new THREE.BoxGeometry(0.05, 0.12, 0.12); thr.translate(-hw * 0.72, sy + 0.05, base + 0.12); add(thr, m.metal);
      for (const sx of [-1, 1]) { const con = new THREE.BoxGeometry(hw * 0.32, 0.8, 0.12); con.translate(sx * hw * 0.78, sy + 0.1, base + 0.03); add(con, m.cockpit); }
    }
    // instrument panel under the coaming, two big live displays (named like the Super Hornet's DDIs), a small
    // centre one, and the HUD combiner glass on top
    const py = k.panelY, pz = k.panelZ, pw = Math.min(hw * 1.7, 1.05);
    const panel = new THREE.BoxGeometry(pw, 0.06, 0.36); panel.rotateX(-0.2); panel.translate(0, py + 0.03, pz); add(panel, m.cockpit);
    const coam = new THREE.BoxGeometry(pw * 0.9, 0.22, 0.035); coam.translate(0, py - 0.06, pz + 0.19); add(coam, m.dark);
    const sw = Math.min(0.24, pw * 0.27);
    for (const [name, x, z, w] of [['screen_ddi_l', -pw * 0.27, pz + 0.03, sw], ['screen_ddi_r', pw * 0.27, pz + 0.03, sw], ['screen_ampcd', 0, pz - 0.1, sw * 0.62]]) {
      const sg = new THREE.PlaneGeometry(w, w); sg.rotateX(Math.PI / 2 - 0.2); sg.translate(x, py - 0.002, z);
      sg.userData.screenUV = true;
      const sm = add(sg, m.screen); sm.name = name;
      const bezel = new THREE.PlaneGeometry(w * 1.18, w * 1.18); bezel.rotateX(Math.PI / 2 - 0.2); bezel.translate(x, py + 0.004, z); add(bezel, m.dark);
    }
    const hz = eye.z - 0.07;
    const hud = new THREE.PlaneGeometry(0.16, 0.13); hud.rotateX(Math.PI / 2 - 0.35); hud.translate(0, py - 0.12, hz); add(hud, m.hudGlass).renderOrder = 3;
    // HUD frame and the windscreen pillars
    const hf = new THREE.TorusGeometry(0.1, 0.008, 4, 4, Math.PI * 2); hf.rotateZ(Math.PI / 4); hf.scale(0.85, 1, 0.75); hf.rotateX(Math.PI / 2 - 0.35); hf.translate(0, py - 0.12, hz); add(hf, m.dark);
    if (d.nation === 'ru') {
      // a Sukhoi / MiG cockpit: the turquoise panel, a deep glare shield, thick windscreen frame, the K-36D seat with
      // its yellow-black ejection handles, twin throttle levers on the left, rows of switches on the side consoles
      const yS = c0 - len * k.seats[0];
      const handle = new THREE.TorusGeometry(0.07, 0.014, 6, 12, Math.PI); handle.rotateX(Math.PI / 2); handle.translate(0, yS + 0.02, base + 0.12); add(handle, m.yellow);
      for (const sx of [-1, 1]) {
        const lever = new THREE.BoxGeometry(0.025, 0.03, 0.16); lever.rotateX(-0.4); lever.translate(-hw * 0.72 + sx * 0.03, yS + 0.08, base + 0.18); add(lever, m.metal);
        for (let i = 0; i < 4; i++) { const sw = new THREE.BoxGeometry(0.03, 0.03, 0.03); sw.translate(sx * hw * 0.78, yS - 0.2 + i * 0.12, base + 0.1); add(sw, i % 2 ? m.yellow : m.metal); }
      }
      const head = new THREE.BoxGeometry(0.46, 0.26, 0.34); head.translate(0, yS - 0.32, base + 0.95); add(head, m.cockpit);
      // two small round standby gauges either side of the centre display
      for (const sx of [-1, 1]) { const gg = new THREE.CircleGeometry(0.035, 16); gg.rotateX(Math.PI / 2 - 0.2); gg.translate(sx * pw * 0.13, py - 0.004, pz - 0.1); add(gg, m.screen); }
    }
  }

  // wings with ailerons, tailplanes (all moving), fins
  const w = d.wing;
  for (const s of [1, -1]) {
    let g = slab(w.root, w.tip, w.x0, w.x1, w.z0, w.z1, w.thick);
    if (s < 0) g = mirrorX(g);
    add(geo(g), m.paint);
    // aileron: the outer trailing edge, hinged at its leading edge
    const a0 = w.x0 + (w.x1 - w.x0) * 0.55, a1 = w.x0 + (w.x1 - w.x0) * 0.92, at = (x) => (x - w.x0) / (w.x1 - w.x0);
    const te = (x) => w.root[1] + (w.tip[1] - w.root[1]) * at(x), le = (x) => w.root[0] + (w.tip[0] - w.root[0]) * at(x);
    const ch = (x) => (le(x) - te(x)) * 0.25, zz = (x) => w.z0 + (w.z1 - w.z0) * at(x);
    const hy = (te(a0) + ch(a0) + te(a1) + ch(a1)) / 2, hz = (zz(a0) + zz(a1)) / 2;
    let ag = slab([te(a0) + ch(a0) - hy, te(a0) - hy], [te(a1) + ch(a1) - hy, te(a1) - hy], a0, a1, zz(a0) - hz + 0.02, zz(a1) - hz + 0.02, 0.04);
    if (s < 0) ag = mirrorX(ag);
    const surf = new THREE.Group(); surf.position.set(0, hy, hz); add(ag, d.tipColor ? m.accent : m.paint, surf);
    model.add(surf); parts[s > 0 ? 'ail_R' : 'ail_L'] = { surf, sign: 1, angle: 0 };
    if (d.tipColor) {
      let tg = slab([le(w.x1 - 0.5), te(w.x1 - 0.5)], w.tip, w.x1 - 0.5, w.x1 + 0.01, zz(w.x1 - 0.5) + 0.01, w.z1 + 0.01, w.thick * 1.1);
      if (s < 0) tg = mirrorX(tg);
      add(tg, m.accent);
    }
    // tailplane, turning about its quarter chord (the deltas with canards have none)
    if (!d.htail) continue;
    const h = d.htail, hq = h.root[0] - (h.root[0] - h.root[1]) * 0.35;
    let hg = slab([h.root[0] - hq, h.root[1] - hq], [h.tip[0] - hq, h.tip[1] - hq], h.x0, h.x1, 0, h.z1 - h.z0, 0.05);
    if (s < 0) hg = mirrorX(hg);
    const hs = new THREE.Group(); hs.position.set(0, hq, h.z0); add(geo(hg), m.paint, hs);
    model.add(hs); parts[s > 0 ? 'stab_R' : 'stab_L'] = { surf: hs, sign: 1, angle: 0 };
  }
  for (const f of d.vtails) {
    const g = fin(f.x, f.root, f.tip, f.z0, f.z1, f.cant);
    add(geo(g), d.stripes && d.vtails.length === 1 ? m.paint : m.paint);
    if (d.tipColor || d.accentFin) add(fin(f.x * 1.001, [f.tip[0] + 0.5, f.tip[1] + 0.1], f.tip, f.z1 - 0.6, f.z1 + 0.01, f.cant, 0.06), m.accent);
  }
  // nozzles: short open cylinders with a dark inside
  for (const [x, y, z, r] of d.nozzles) {
    const n = new THREE.CylinderGeometry(r * 0.92, r, 0.9, 20, 1, true); n.translate(x, y + 0.45, z); add(n, m.nozzle);
    const inner = new THREE.CircleGeometry(r * 0.88, 20); inner.rotateX(Math.PI / 2); inner.translate(x, y + 0.6, z); add(inner, m.dark);
  }
  // T-6: propeller (spinner and four blades) turning about +Y
  let prop = null;
  if (d.prop) {
    prop = new THREE.Group(); prop.position.set(0, d.fus[0][0], d.fus[0][3]);
    const sp = new THREE.ConeGeometry(0.22, 0.55, 16); sp.translate(0, 0.27, 0); add(sp, m.dark, prop);
    for (let k = 0; k < 4; k++) {
      const b = new THREE.BoxGeometry(0.16, 0.04, 1.2); b.translate(0, 0.05, 0.65); b.rotateY(k * Math.PI / 2); add(b, m.dark, prop);
    }
    const disc = new THREE.CircleGeometry(1.3, 32); disc.rotateX(Math.PI / 2);
    prop.add(Object.assign(new THREE.Mesh(disc, new THREE.MeshBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.08, depthWrite: false, side: THREE.DoubleSide })), { renderOrder: 3 }));
    model.add(prop);
  }
  // landing gear: [x, y, z of the hinge, leg length, wheel radius, fold angle]
  for (const [x, y, z, l, r, fold] of d.gear) {
    const pivot = new THREE.Group(); pivot.position.set(x, y, z);
    const leg = new THREE.CylinderGeometry(0.06, 0.07, l, 8); leg.rotateX(Math.PI / 2); leg.translate(0, 0, -l / 2); add(leg, m.gearMat, pivot);
    const wheel = new THREE.CylinderGeometry(r, r, r * 0.7, 18); wheel.rotateZ(Math.PI / 2); wheel.translate(0, 0, -l); add(wheel, m.tyre, pivot);
    model.add(pivot);
    gear.push({ o: pivot, rest: pivot.quaternion.clone(), angle: fold * DEG, door: false });
  }
  // tail hook (Goshawk)
  if (d.hook) { const h = new THREE.BoxGeometry(0.06, 1.6, 0.06); h.rotateX(0.35); h.translate(0, -4.6, -0.55); add(h, m.dark); }
  // national markings: on both sides of the fuselage (or fins) and on top of both wings
  if (d.decals) {
    const [y, x, z] = d.decals.side || [0, 0, 0], s = d.nation === 'us' ? 1.0 : 1.3;
    for (const sx of d.decals.side ? [-1, 1] : []) {
      const p = new THREE.PlaneGeometry(s, s); p.rotateY(Math.PI / 2); p.rotateX(Math.PI / 2); p.rotateY(sx < 0 ? Math.PI : 0);
      const fx = x === 0 ? (d.fus.find(([yy]) => yy <= y) || d.fus[2])[1] * 1.03 : x;
      p.translate(sx * fx, y, z);
      add(p, m.decal);
    }
    const [wx, wy] = d.decals.wing;
    for (const sx of [-1, 1]) {
      const p = new THREE.PlaneGeometry(d.nation === 'us' ? 1.1 : 1.4, d.nation === 'us' ? 1.1 : 1.4);
      const zz = w.z0 + (w.z1 - w.z0) * ((wx - w.x0) / (w.x1 - w.x0)) + 0.06;
      p.translate(sx * wx, wy, zz); add(p, m.decal);
    }
  }
  model.userData.prop = prop;
  return { model, parts, gear };
}
