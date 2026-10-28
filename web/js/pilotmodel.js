// The pilot as a 3D figure: flight helmet with visor and oxygen mask, hose, shoulders and harness, arms to the
// stick, and (full figure, for the parachute) legs and boots.  Metres.  The group is built in the aircraft's frame
// (x right, y forward, z up) with the head centre at the origin, looking along +Y.
// outfit: a pilot skin of skins.js (suit / helmet / visor / accent / decal) or null for the plain issue gear.
import { THREE } from './util.js';
import { helmetTexture } from './skinart.js';

const PLAIN = { suit: 0x59624a, suit2: 0x3f4733, helmet: 0xd2d2cb, helmet2: 0xd2d2cb, pattern: 'none', visor: 0xe8f0f4, visorT: 0.97, mirror: false, accent: 0xd8c860, glove: 0x23262b, pressure: false };
const SKIN = 0xc79a76;

// the game's colours are sRGB values on a renderer without colour management: convert them (as proc.js does) or they come out pale
const lin = (n) => new THREE.Color(n).convertSRGBToLinear();
const mat = (color, rough = 0.6, metal = 0.05, extra = {}) => new THREE.MeshStandardMaterial({ color: lin(color), roughness: rough, metalness: metal, ...extra });

export function buildPilot(outfit, opts = {}) {
  const o = outfit || PLAIN;
  const root = new THREE.Group();
  const g = new THREE.Group();                       // built with Y up and the face toward -Z, turned into the aircraft frame below
  root.add(g);
  g.rotation.x = Math.PI / 2;

  const helmetMat = mat(o.helmet, 0.32, 0.12, o.pattern && o.pattern !== 'none' ? { map: (() => { const t = new THREE.CanvasTexture(helmetTexture(o)); t.wrapS = THREE.RepeatWrapping; return t; })(), color: 0xffffff } : {});
  const darkMat = mat(0x24272b, 0.8, 0.05), suitMat = mat(o.suit, 0.85, 0), accentMat = mat(o.accent, 0.6, 0.05);
  const T = o.visorT === undefined ? 0.3 : o.visorT, showFace = T > 0.5, press = !!o.pressure;
  const add = (geo, m, x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1) => {
    const mesh = new THREE.Mesh(geo, m);
    mesh.position.set(x, y, z); mesh.scale.set(sx, sy, sz);
    g.add(mesh); return mesh;
  };

  // --- the helmet: shell, brow, ear cups, rear
  add(new THREE.SphereGeometry(0.155, 28, 18), helmetMat, 0, press ? 0.03 : 0.012, 0.012, press ? 1.2 : 1.0, press ? 1.25 : 1.1, press ? 1.3 : 1.14);
  if (press) { add(new THREE.TorusGeometry(0.15, 0.022, 10, 24), mat(0xaab2ba, 0.3, 0.8), 0, -0.13, 0.03).rotation.x = Math.PI / 2; for (const s of [-1, 1]) add(new THREE.SphereGeometry(0.03, 10, 8), accentMat, s * 0.17, -0.12, -0.02); }
  add(new THREE.CylinderGeometry(0.152, 0.14, 0.05, 28, 1, true), darkMat, 0, -0.095, 0.01, 1.0, 1, 1.12);          // the neck edge
  for (const s of [-1, 1]) {
    add(new THREE.CylinderGeometry(0.05, 0.05, 0.035, 16), mat(0x30343a, 0.5, 0.4), s * 0.152, -0.015, 0.0).rotation.z = Math.PI / 2;
    add(new THREE.SphereGeometry(0.03, 10, 8), mat(0x9aa0a8, 0.3, 0.8), s * 0.165, -0.04, -0.05);                      // bayonet fitting
  }
  // --- the visor: a dark (or lightly tinted) lens over the face opening
  const opacity = Math.min(0.96, Math.max(0.12, (1 - T) * 1.15));
  const visorMat = new THREE.MeshStandardMaterial({ color: lin(o.visor), roughness: o.mirror ? 0.03 : 0.08, metalness: o.mirror ? 1 : 0.35, transparent: opacity < 0.95, opacity, envMap: opts.env || null, envMapIntensity: 1.6 });
  add(new THREE.SphereGeometry(0.15, 28, 16), visorMat, 0, 0.012, -0.07, 0.97, 0.52, 0.56);
  if (showFace) {                                     // a light visor: the face behind it
    add(new THREE.SphereGeometry(0.125, 18, 12), mat(SKIN, 0.8), 0, 0.002, -0.06, 0.95, 0.5, 0.5);
    for (const s of [-1, 1]) add(new THREE.SphereGeometry(0.014, 8, 6), mat(0x16130f, 0.3), s * 0.045, 0.012, -0.158);
  }
  // --- the oxygen mask and its hose
  add(new THREE.SphereGeometry(0.095, 20, 14), mat(0x2c312e, 0.75, 0.05), 0, -0.07, -0.108, 0.9, 0.78, 0.7);
  add(new THREE.CylinderGeometry(0.02, 0.02, 0.012, 12), mat(0x111315, 0.4, 0.3), 0, -0.075, -0.172).rotation.x = Math.PI / 2;     // exhalation valve
  const hose = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.07, -0.09, -0.14), new THREE.Vector3(-0.14, -0.2, -0.17), new THREE.Vector3(-0.12, -0.34, -0.19), new THREE.Vector3(-0.06, -0.46, -0.21)]);
  add(new THREE.TubeGeometry(hose, 18, 0.017, 8), mat(0x1c231e, 0.9, 0));
  // --- the helmet's marking (the bought outfit): a stripe over the top and a patch on the crown
  // --- neck, collar, shoulders, torso
  add(new THREE.CylinderGeometry(0.058, 0.066, 0.12, 14), mat(SKIN, 0.8), 0, -0.145, 0.03);
  add(new THREE.TorusGeometry(0.075, 0.025, 8, 18), suitMat, 0, -0.2, 0.03).rotation.x = Math.PI / 2;
  add(new THREE.SphereGeometry(0.2, 20, 14), suitMat, 0, -0.36, 0.06, 1.2, 0.8, 0.7);                              // the shoulders
  add(new THREE.CylinderGeometry(0.17, 0.2, 0.34, 18), suitMat, 0, -0.55, 0.08, 1.15, 1, 0.7);                       // the chest
  // the second suit colour: yoke panels over the shoulders and a pocket, the chest patch in the accent colour
  const suit2Mat = mat(o.suit2 === undefined ? o.suit : o.suit2, 0.85, 0);
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.16, 0.05, 0.2), suit2Mat, s * 0.17, -0.28, 0.06).rotation.z = s * -0.35;
  add(new THREE.BoxGeometry(0.1, 0.1, 0.012), accentMat, 0.13, -0.47, -0.088);
  // harness: two straps over the shoulders, a chest strap with a buckle, the risers
  for (const s of [-1, 1]) {
    const strap = add(new THREE.BoxGeometry(0.06, 0.46, 0.012), mat(0x2a2d30, 0.9, 0), s * 0.11, -0.45, -0.075);
    strap.rotation.z = s * 0.16;
    add(new THREE.BoxGeometry(0.075, 0.07, 0.04), mat(0x8e949c, 0.3, 0.85), s * 0.21, -0.32, -0.02);                    // the shoulder fittings
  }
  add(new THREE.BoxGeometry(0.34, 0.04, 0.012), mat(0x2a2d30, 0.9, 0), 0, -0.55, -0.078);
  add(new THREE.BoxGeometry(0.06, 0.06, 0.02), mat(0xb4bac2, 0.25, 0.9), 0, -0.55, -0.085);
  add(new THREE.BoxGeometry(0.09, 0.05, 0.01), accentMat, -0.13, -0.47, -0.088);                                       // the name tape
  // --- arms to the stick and the throttle
  for (const s of [-1, 1]) {
    const upper = add(new THREE.CylinderGeometry(0.045, 0.04, 0.3, 10), suitMat, s * 0.27, -0.55, -0.02);
    upper.rotation.set(-0.7, 0, s * 0.18);
    const fore = add(new THREE.CylinderGeometry(0.04, 0.035, 0.3, 10), suitMat, s * 0.25, -0.62, -0.24);
    fore.rotation.set(-1.25, 0, s * 0.1);
    add(new THREE.SphereGeometry(0.045, 10, 8), mat(o.glove === undefined ? 0x1d1f22 : o.glove, 0.7), s * 0.24, -0.62, -0.38);                           // the gloves
  }
  if (opts.full) {                                     // hanging in the parachute: arms up, legs down, boots
    for (const s of [-1, 1]) {
      add(new THREE.CylinderGeometry(0.08, 0.065, 0.46, 12), suitMat, s * 0.09, -0.98, 0.07);
      add(new THREE.CylinderGeometry(0.058, 0.05, 0.46, 12), suitMat, s * 0.09, -1.4, 0.07);
      add(new THREE.BoxGeometry(0.09, 0.08, 0.2), mat(0x1c1a17, 0.7, 0.05), s * 0.09, -1.66, 0.02);
    }
    add(new THREE.CylinderGeometry(0.17, 0.15, 0.28, 16), suitMat, 0, -0.84, 0.07, 1.25, 1, 0.75);
  }
  root.userData.helmet = true;
  return root;
}
