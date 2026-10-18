// Three.js scene: aircraft, terrain, sky, clouds, airfield, particles, tracers.
import { THREE, V, add, mul, xform, b64ToArray, DEG, clamp, rng, copy } from './util.js';
import { RUNWAY_LENGTH, RUNWAY_WIDTH, TAXIWAY_OFFSET, TAXIWAY_WIDTH, APRON } from './terrain.js';

export const SUN_DIR = new THREE.Vector3(-0.45, 0.55, 0.70).normalize();
const HORIZON = new THREE.Color(0.72, 0.81, 0.90);
const ZENITH = new THREE.Color(0.19, 0.38, 0.72);

// ------------------------------------------------------------------ geometry
function geom(g) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(b64ToArray(g.pos, Float32Array), 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(b64ToArray(g.nrm, Float32Array), 3));
  if (g.uv) geo.setAttribute('uv', new THREE.BufferAttribute(b64ToArray(g.uv, Float32Array), 2));
  if (g.col) {
    // the vertex colours were picked for Panda3D's non gamma-correct pipeline: convert sRGB -> linear
    const col = b64ToArray(g.col, Float32Array);
    for (let i = 0; i < col.length; i++) if (i % 4 !== 3) col[i] = Math.pow(col[i], 2.2);
    geo.setAttribute('color', new THREE.BufferAttribute(col, 4));
  }
  geo.setIndex(new THREE.BufferAttribute(b64ToArray(g.idx, Uint32Array), 1));
  geo.computeBoundingSphere();
  return geo;
}

function softTexture(size = 64, power = 1.6) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const img = g.createImageData(size, size);
  const h = (size - 1) / 2;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const d = Math.hypot(x - h, y - h) / h;
    const a = Math.pow(Math.max(0, 1 - d), power);
    const i = (y * size + x) * 4;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = 255; img.data[i + 3] = Math.round(a * 255);
  }
  g.putImageData(img, 0, 0);
  return new THREE.CanvasTexture(c);
}

function puffTexture(seed = 3) {
  const size = 128, r = rng(seed);
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  for (let k = 0; k < 9; k++) {
    const x = size * r.uniform(0.3, 0.7), y = size * r.uniform(0.3, 0.68), rad = size * r.uniform(0.16, 0.3);
    const grd = g.createRadialGradient(x, y, 0, x, y, rad);
    const shade = Math.round(255 * (0.86 + 0.14 * (1 - y / size)));
    grd.addColorStop(0, `rgba(${shade},${shade},${shade},0.95)`);
    grd.addColorStop(1, `rgba(${shade},${shade},${shade},0)`);
    g.fillStyle = grd; g.beginPath(); g.arc(x, y, rad, 0, Math.PI * 2); g.fill();
  }
  return new THREE.CanvasTexture(c);
}

// ------------------------------------------------------------------- models
// The aircraft seen from outside are the Blender models (tools/blender/build_f16.py, build_fa18.py ->
// assets/f16.glb, fa18.glb).  The Super Hornet's cockpit is part of its model (with the four displays as
// screen_* objects); the F-16 pilot's own view still uses the older model built from code (assets/f16.json)
// with its detailed instrument panel.
const MOVING = ['lef_L', 'lef_R', 'flap_L', 'flap_R', 'ail_L', 'ail_R', 'stab_L', 'stab_R', 'rudder', 'rudder_L', 'rudder_R',
  'sb_up_L', 'sb_up_R', 'sb_lo_L', 'sb_lo_R', 'vec_L', 'vec_R', 'sb_dorsal'];
const ROT = new THREE.Quaternion(), V3 = new THREE.Vector3();
const VAPOR_STEP = { f16: [0.27, -1.0, -0.03], fa18: [0.45, -1.4, -0.05] };   // second LEX / strake vapour point
const LEGACY_SCREENS = ['mfd_l', 'mfd_r', 'ded', 'rwr'];                   // the quads of f16.json's screens, in order
const MISSILE_MODELS = { 'AIM-9M': 'aim9m', 'AIM-120A': 'aim120c' };
const FOLD = new THREE.Quaternion(), X_AXIS = new THREE.Vector3(1, 0, 0);
const COCKPIT_STATIONS = {      // where the missiles hang on the cockpit view model
  1: [-4.88, -0.55, 0.10], 2: [-3.75, -0.95, -0.38], 3: [-2.60, -0.55, -0.45],
  7: [2.60, -0.55, -0.45], 8: [3.75, -0.95, -0.38], 9: [4.88, -0.55, 0.10],
};

export class Models {
  constructor(data, textures, glb, specs) {
    this.data = data;
    this.tex = textures;
    this.geo = {
      skin: geom(data.skin), plain: geom(data.plain), glass: geom(data.glass), lights: geom(data.lights),
      cockpit: geom(data.cockpit), screens: geom(data.screens), missiles: { 'AIM-9M': geom(data.missiles['AIM-9M']), 'AIM-120A': geom(data.missiles['AIM-120A']) },
    };
    this.parts = data.parts.map((p) => ({ ...p, geo: geom(p.geom) }));
    this.env = this.makeEnv();
    this.mat = {
      plain: new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 0.2, roughness: 0.6 }),
      // front faces only: from inside the cockpit the canopy does not fog the view
      glass: new THREE.MeshStandardMaterial({ vertexColors: true, transparent: true, metalness: 0.9, roughness: 0.05,
        envMap: this.env, envMapIntensity: 1.2, side: THREE.FrontSide, depthWrite: false }),
      lights: new THREE.MeshBasicMaterial({ vertexColors: true }),
      missile: new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 0.3, roughness: 0.45 }),
    };
    this.skin = {};
    for (const name of ['viper', 'aggressor']) {
      const t = textures[name];
      t.anisotropy = 8; t.encoding = THREE.sRGBEncoding;
      this.skin[name] = new THREE.MeshStandardMaterial({ map: t, color: 0xe0e0e0, metalness: 0.12, roughness: 0.62, envMap: this.env, envMapIntensity: 0.35 });
    }
    const ct = textures.cockpit;
    ct.anisotropy = 8; ct.encoding = THREE.sRGBEncoding;
    this.mat.cockpit = new THREE.MeshStandardMaterial({ map: ct, metalness: 0.1, roughness: 0.75 });
    this.mat.screens = new THREE.MeshBasicMaterial({ map: ct });
    this.eye = data.eye;
    this.flameGeo = new THREE.ConeGeometry(0.46, 1, 18, 1, true).rotateX(Math.PI).translate(0, -0.5, 0);
    this.flameCoreGeo = new THREE.ConeGeometry(0.28, 0.55, 14, 1, true).rotateX(Math.PI).translate(0, -0.275, 0);
    this.flameMat = new THREE.MeshBasicMaterial({ color: 0xff8a3c, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    this.flameCoreMat = new THREE.MeshBasicMaterial({ color: 0xfff0c8, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    this.glb = glb;
    this.glbMat = {};
    for (const [key, g] of Object.entries(glb)) this.glbMat[key] = g.materials.map((m) => this.material(m));
    this.types = {};
    for (const spec of Object.values(specs)) this.types[spec.model] = this.typeInfo(spec);
  }
  // Reference points of a Blender model in the aircraft frame (+Y forward, +Z up) and the effects hung on
  // them.  The flight model's origin sits spec.gearHeight above the ground; the model is shifted down so its
  // wheels touch the ground there.
  typeInfo(spec) {
    const marks = this.glb[spec.model].root.children.filter((n) => !n.prims.length && !n.children.length);
    const modelZ = -(spec.gearHeight + marks.find((n) => n.name === 'ref_gear_main_R').position[1]);
    const ref = {};
    for (const n of marks) ref[n.name] = V(n.position[0], -n.position[2], n.position[1] + modelZ);
    const pick = (re) => Object.keys(ref).filter((k) => re.test(k)).sort().map((k) => ref[k]);
    const nozzles = pick(/^ref_nozzle/);
    const step = VAPOR_STEP[spec.model] || VAPOR_STEP.f16;
    const vL = ref.ref_vapor_L, vR = ref.ref_vapor_R;
    const nav = [[ref.ref_nav_L, 0xff2a1a], [ref.ref_nav_R, 0x33ff55], [ref.ref_tail, 0xfffff0]];
    if (ref.ref_intake_light_L) nav.push([ref.ref_intake_light_L, 0xff2a1a], [ref.ref_intake_light_R, 0x33ff55]);
    const legacy = spec.model === 'f16';
    return {
      key: spec.model, spec, modelZ, ref, nozzles, nav, gearHeight: spec.gearHeight,
      flameScale: spec.engines > 1 ? 0.84 : 1,
      tail: nozzles.reduce((a, n) => add(a, mul(n, 1 / nozzles.length)), V()),
      wingtips: [ref.ref_wingtip_L, ref.ref_wingtip_R],
      vapor: [vL, vR, add(vL, V(-step[0], step[1], step[2])), add(vR, V(step[0], step[1], step[2]))],
      strobes: pick(/^ref_strobe/), gun: ref.ref_gun,
      // the pilot's eye: the old F-16 cockpit model has its own; the Hornet's is a point of its model
      cockpit: legacy ? 'legacy' : 'self', eye: legacy ? V(...this.data.eye) : ref.ref_eye,
      // the middle of the displays (N) and the field of view that fits them
      panel: legacy ? V(0, 3.28, 0.63) : { f22: V(0, 4.98, 0.82 + modelZ), f15: V(0, 5.42, 1.13 + modelZ) }[spec.model] || V(0, 5.37, 1.0 + modelZ),
      panelFov: legacy ? 30 : { f22: 42, f15: 38 }[spec.model] || 40,
    };
  }
  // glTF material -> three.js: painted skin (textures), glass, lamps (unlit) or vertex coloured details
  material(m) {
    const def = m.def, pbr = def.pbrMetallicRoughness || {}, base = pbr.baseColorFactor || [1, 1, 1, 1];
    if (def.emissiveFactor) {
      const e = def.emissiveFactor;
      return new THREE.MeshBasicMaterial({ color: new THREE.Color(...[0, 1, 2].map((k) => Math.min(1, e[k] + 0.5 * base[k]))) });
    }
    const common = { metalness: pbr.metallicFactor ?? 1, roughness: pbr.roughnessFactor ?? 1, envMap: this.env };
    if (def.alphaMode === 'BLEND') {
      return new THREE.MeshStandardMaterial({ ...common, color: new THREE.Color(base[0], base[1], base[2]), opacity: base[3], transparent: true,
        envMapIntensity: 1.2, side: THREE.FrontSide, depthWrite: false });
    }
    if (m.map) {
      const mat = new THREE.MeshStandardMaterial({ ...common, map: m.map, normalMap: m.normalMap, roughnessMap: m.ormMap, metalnessMap: m.ormMap, envMapIntensity: 0.35 });
      mat.normalScale.set(1, -1);                       // glTF UVs run top-down
      return mat;
    }
    return new THREE.MeshStandardMaterial({ ...common, vertexColors: true, envMapIntensity: common.metalness > 0.5 ? 0.9 : 0.3 });
  }
  // A copy of a .glb scene (geometry and materials are shared).  Moving parts are registered in `parts`:
  // each one hangs on its hinge and turns about its local X axis.  Gear legs and doors (extras.retract /
  // extras.door = degrees about local X that fold them away) go to `gear`.
  // F-22 internal carriage (in `bays`): doors (extras.bay = degrees that close them, extras.group), launchers
  // rack_N (extras.rack = degrees that swing them down, or slide_x/y/z = metres they slide out) and the
  // missiles' places store_N.
  instance(key, parts, gear, bays) {
    const mats = this.glbMat[key];
    const build = (n) => {
      const o = new THREE.Object3D();
      o.name = n.name; o.position.fromArray(n.position); o.quaternion.fromArray(n.quaternion); o.scale.fromArray(n.scale);
      const fold = n.extras.retract ?? n.extras.door;
      if (gear && fold !== undefined) gear.push({ o, rest: o.quaternion.clone(), angle: fold * DEG, door: n.extras.door !== undefined });
      if (bays && n.extras.bay !== undefined) bays.doors.push({ o, rest: o.quaternion.clone(), angle: n.extras.bay * DEG, group: n.extras.group });
      if (bays && /^rack_/.test(n.name)) {
        bays.racks[Number(n.name.slice(5))] = { o, rest: o.quaternion.clone(), restPos: o.position.clone(), angle: (n.extras.rack || 0) * DEG,
          // glTF frame: x right, y up, z backwards
          slide: n.extras.slide_x !== undefined ? new THREE.Vector3(n.extras.slide_x, n.extras.slide_z, -n.extras.slide_y) : null };
      }
      if (bays && /^store_/.test(n.name)) bays.stores[Number(n.name.slice(6))] = new THREE.Vector3().fromArray(n.position);
      if (n.prims.length) {
        const surf = new THREE.Group();
        for (const p of n.prims) {
          const mesh = new THREE.Mesh(p.geometry, mats[p.material]);
          if (mats[p.material].transparent) mesh.renderOrder = 2;
          surf.add(mesh);
        }
        o.add(surf);
        if (parts && MOVING.includes(n.name)) parts[n.name] = { surf, sign: 1, angle: 0 };
      }
      for (const c of n.children) o.add(build(c));
      return o;
    };
    const model = build(this.glb[key].root);
    model.rotation.x = Math.PI / 2;                     // glTF: +Y up, -Z forward; the game: +Z up, +Y forward
    return model;
  }
  makeEnv() {
    // tiny equirect sky for reflections (canopy, paint sheen)
    const c = document.createElement('canvas');
    c.width = 256; c.height = 128;
    const g = c.getContext('2d');
    const grd = g.createLinearGradient(0, 0, 0, 128);
    grd.addColorStop(0, '#3a66b8'); grd.addColorStop(0.47, '#c9daf0'); grd.addColorStop(0.5, '#e8eef5');
    grd.addColorStop(0.53, '#5a6a4a'); grd.addColorStop(1, '#2c3424');
    g.fillStyle = grd; g.fillRect(0, 0, 256, 128);
    const sun = g.createRadialGradient(150, 30, 0, 150, 30, 18);
    sun.addColorStop(0, 'rgba(255,255,240,1)'); sun.addColorStop(1, 'rgba(255,255,240,0)');
    g.fillStyle = sun; g.fillRect(120, 0, 60, 60);
    const t = new THREE.CanvasTexture(c);
    t.mapping = THREE.EquirectangularReflectionMapping;
    return t;
  }
  aircraft(key = 'f16') {
    const root = new THREE.Group(), parts = {}, gear = [], bays = { doors: [], racks: {}, stores: {} };
    const model = this.instance(key, parts, gear, bays);
    root.userData.bays = bays;
    model.position.z = this.types[key].modelZ;
    root.userData.model = model;
    root.add(model);
    root.userData.parts = parts;
    root.userData.gear = gear;
    root.userData.gearPos = 1;
    return root;
  }
  // gearPos 1 = down and locked, 0 = up: the doors open first, the legs swing into their wells, and on the
  // way up the doors close behind them
  setGear(root, gearPos) {
    if (root.userData.gearPos === gearPos) return;
    root.userData.gearPos = gearPos;
    const legs = clamp((gearPos - 0.15) / 0.85, 0, 1), eased = legs * legs * (3 - 2 * legs);
    const doors = clamp(gearPos / 0.2, 0, 1);
    for (const g of root.userData.gear) {
      g.o.quaternion.copy(g.rest).multiply(FOLD.setFromAxisAngle(X_AXIS, g.angle * (1 - (g.door ? doors : eased))));
      if (!g.door) g.o.visible = gearPos > 0.001;
    }
  }
  missile(key) { const g = new THREE.Group(); g.add(this.instance(MISSILE_MODELS[key])); return g; }
  // a missile for the glTF frame of a model (inside a weapons bay): no axis swap
  bayMissile(key) { const m = this.instance(MISSILE_MODELS[key]); m.rotation.x = 0; return m; }
  // F-22: doors open as far as the jet says, launchers out, the missiles riding on them
  setBays(root, ac) {
    const b = root.userData.bays, model = root.userData.model;
    if (!b || !b.doors.length) return;
    for (const d of b.doors) {
      const open = ac.bayOpen(d.group);
      d.o.quaternion.copy(d.rest).multiply(ROT.setFromAxisAngle(X_AXIS, d.angle * (1 - open)));
    }
    for (const st of ac.stations) {
      const r = b.racks[st.number], m = b.missiles && b.missiles[st.number];
      if (!r) continue;
      const out = ac.rackOut(st);
      if (r.slide) {
        r.o.position.copy(r.restPos).addScaledVector(r.slide, out);
        if (m) m.position.copy(b.stores[st.number]).addScaledVector(r.slide, out);
      } else {
        r.o.quaternion.copy(r.rest).multiply(ROT.setFromAxisAngle(X_AXIS, r.angle * out));
        // the trapeze keeps the missile level: its top rides on the end of the links
        if (m) {
          if (!r.attach) {
            const top = b.stores[st.number].clone().add(V3.set(0, 0.12, 0));
            r.attach = top.sub(r.restPos).applyQuaternion(r.rest.clone().invert());
          }
          m.position.copy(r.attach).applyQuaternion(r.o.quaternion).add(r.restPos).add(V3.set(0, -0.12, 0));
        }
      }
      if (m) m.visible = st.loaded;
    }
  }
  cockpitAircraft(livery) {
    const root = new THREE.Group();
    const add_ = (geo, mat) => { const m = new THREE.Mesh(geo, mat); root.add(m); return m; };
    add_(this.geo.skin, this.skin[livery]);
    add_(this.geo.plain, this.mat.plain);
    add_(this.geo.lights, this.mat.lights);
    add_(this.geo.cockpit, this.mat.cockpit);
    // the four displays (2 MFDs, DED, RWR scope) as separate quads with 0..1 UVs, for the live displays
    const screens = {}, sp = this.geo.screens.attributes.position, suv = this.geo.screens.attributes.uv;
    LEGACY_SCREENS.forEach((name, q) => {
      const pos = [], uv = [], us = [], vs = [];
      for (let i = q * 6; i < q * 6 + 6; i++) { us.push(suv.getX(i)); vs.push(suv.getY(i)); }
      const u0 = Math.min(...us), u1 = Math.max(...us), v0 = Math.min(...vs), v1 = Math.max(...vs);
      for (let i = q * 6; i < q * 6 + 6; i++) {
        pos.push(sp.getX(i), sp.getY(i), sp.getZ(i));
        uv.push((suv.getX(i) - u0) / (u1 - u0), (suv.getY(i) - v0) / (v1 - v0));
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      screens[name] = add_(g, this.mat.screens);
    });
    root.userData.screens = screens;
    const glass = add_(this.geo.glass, this.mat.glass);
    glass.renderOrder = 2;
    const parts = {};
    for (const p of this.parts) {
      const pivot = new THREE.Object3D();
      pivot.position.set(...p.pos);
      pivot.quaternion.set(p.quat[1], p.quat[2], p.quat[3], p.quat[0]);
      const surf = new THREE.Mesh(p.geo, this.skin[livery]);
      pivot.add(surf); root.add(pivot);
      parts[p.name] = { surf, sign: p.sign, angle: 0 };
    }
    root.userData.parts = parts;
    return root;
  }
  cockpitMissile(key) { return new THREE.Mesh(this.geo.missiles[key], this.mat.missile); }
  // The screen_* objects of a Blender model (thin boxes on the instrument panel): UVs projected onto the
  // screen face (u to the right, v up), so a canvas can be shown on them.  Returns {name: [meshes]}.
  modelScreens(model) {
    const out = {};
    model.traverse((o) => {
      if (!/^screen_/.test(o.name)) return;
      const meshes = [];
      o.traverse((m) => { if (m.isMesh) meshes.push(m); });
      for (const m of meshes) {
        const g = m.geometry;
        if (g.userData.screenUV) continue;
        const p = g.attributes.position, n = p.count;
        let x0 = Infinity, x1 = -Infinity, cy = 0, cz = 0;
        for (let i = 0; i < n; i++) { x0 = Math.min(x0, p.getX(i)); x1 = Math.max(x1, p.getX(i)); cy += p.getY(i) / n; cz += p.getZ(i) / n; }
        // the long axis of the screen in the (y, z) plane of the glTF frame is "up" on the display
        let syy = 0, szz = 0, syz = 0;
        for (let i = 0; i < n; i++) { const a = p.getY(i) - cy, b = p.getZ(i) - cz; syy += a * a; szz += b * b; syz += a * b; }
        const ang = 0.5 * Math.atan2(2 * syz, syy - szz);
        let uy = Math.cos(ang), uz = Math.sin(ang);
        if (uy < 0) { uy = -uy; uz = -uz; }
        const proj = (i) => (p.getY(i) - cy) * uy + (p.getZ(i) - cz) * uz;
        let v0 = Infinity, v1 = -Infinity;
        for (let i = 0; i < n; i++) { v0 = Math.min(v0, proj(i)); v1 = Math.max(v1, proj(i)); }
        const uv = new Float32Array(n * 2);
        for (let i = 0; i < n; i++) { uv[i * 2] = (p.getX(i) - x0) / (x1 - x0); uv[i * 2 + 1] = (proj(i) - v0) / (v1 - v0); }
        g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
        g.userData.screenUV = true;
      }
      out[o.name] = meshes;
    });
    return out;
  }
}

// control surfaces like the flight controls move them (rate limited actuators).  Hinge convention of the
// Blender models: + = trailing edge down / leading edge down / rudder trailing edge right / brake open.
export function animateSurfaces(parts, dt, c, alphaDeg, flaps, brake, onGround) {
  const move = (name, target) => {
    const p = parts[name];
    if (!p) return;
    const step = 60 * dt;
    p.angle += clamp(target - p.angle, -step, step);
    p.surf.rotation.x = p.angle * p.sign * DEG;
  };
  const stab = -c.pitch * 16;
  move('stab_R', stab - c.roll * 5); move('stab_L', stab + c.roll * 5);
  // F-22 two dimensional nozzles: both flaps turn with the pitch stick (nose up = exhaust up)
  move('vec_R', -c.pitch * 20); move('vec_L', -c.pitch * 20);
  move('sb_dorsal', brake * 45);                       // F-15: the big speed brake on the back
  if (parts.ail_L) {
    // Super Hornet: ailerons for roll, trailing edge flaps scheduled with AoA (and differential at low
    // speed), LEFs down to 34 degrees, two rudders.  The "speed brake" is the spoilers on the LEX plus the
    // rudders flared out and the ailerons up; on the runway the rudders toe in for the rotation.
    const tef = onGround ? flaps * 30 : flaps * 30 + clamp((alphaDeg - 4) * 0.8, 0, 12);
    move('flap_R', tef - c.roll * 8 * flaps); move('flap_L', tef + c.roll * 8 * flaps);
    const ailBrake = parts.sb_dorsal ? 0 : brake * 15;
    move('ail_R', -c.roll * 25 - ailBrake); move('ail_L', c.roll * 25 - ailBrake);
    const lef = onGround ? 0 : clamp(alphaDeg * 1.2 - 2, -3, 34);
    move('lef_R', lef); move('lef_L', lef);
    const toe = onGround && flaps > 0.5 && !parts.sb_dorsal ? 20 : 0, flare = parts.sb_dorsal ? 0 : brake * 25;
    move('rudder_L', c.yaw * 25 + toe - flare); move('rudder_R', c.yaw * 25 - toe + flare);
    for (const n of ['sb_up_R', 'sb_up_L']) move(n, brake * 55);
    return;
  }
  move('flap_R', flaps * 20 - c.roll * 18); move('flap_L', flaps * 20 + c.roll * 18);
  const lef = onGround ? 0 : clamp(alphaDeg * 1.4 - 2, -2, 25);
  move('lef_R', lef); move('lef_L', lef);
  move('rudder', c.yaw * 25);
  for (const n of ['sb_up_R', 'sb_up_L', 'sb_lo_R', 'sb_lo_L']) move(n, brake * 60);
}

// ------------------------------------------------------------------ particles
const PARTICLE_VS = `
attribute float size; attribute vec4 rgba; varying vec4 vColor; uniform float scale;
#include <fog_pars_vertex>
void main(){ vColor = rgba; vec4 mvPosition = modelViewMatrix * vec4(position,1.0);
  gl_PointSize = clamp(size * scale / -mvPosition.z, 0.0, 512.0); gl_Position = projectionMatrix * mvPosition;
  #include <fog_vertex>
}`;
const PARTICLE_FS = `
uniform sampler2D map; varying vec4 vColor;
#include <fog_pars_fragment>
void main(){ vec4 t = texture2D(map, gl_PointCoord); gl_FragColor = vec4(vColor.rgb, vColor.a * t.a);
  if (gl_FragColor.a < 0.003) discard;
  #include <fog_fragment>
}`;

class Particles {
  constructor(scene, tex, additive, max) {
    this.max = max; this.list = [];
    const g = new THREE.BufferGeometry();
    this.pos = new Float32Array(max * 3); this.size = new Float32Array(max); this.col = new Float32Array(max * 4);
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('size', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('rgba', new THREE.BufferAttribute(this.col, 4).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 0);
    this.uniforms = THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { map: { value: tex }, scale: { value: 600 } }]);
    this.uniforms.map.value = tex;
    const m = new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader: PARTICLE_VS, fragmentShader: PARTICLE_FS,
      transparent: true, depthWrite: false, fog: !additive, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending });
    this.points = new THREE.Points(g, m);
    this.points.frustumCulled = false;
    this.points.renderOrder = additive ? 4 : 3;
    scene.add(this.points);
  }
  spawn(pos, vel, life, size, color, drag = 0, rise = 0) {
    if (this.list.length >= this.max) this.list.shift();
    this.list.push({ p: copy(pos), v: vel ? copy(vel) : V(), age: 0, life, s0: size[0], s1: size[1], c0: color[0], c1: color[1], drag, rise });
  }
  update(dt) {
    const keep = [];
    let n = 0;
    for (const q of this.list) {
      q.age += dt;
      const t = q.age / q.life;
      if (t >= 1) continue;
      if (q.drag) q.v.multiplyScalar(Math.max(0, 1 - q.drag * dt));
      if (q.rise) q.v.z += q.rise * dt;
      q.p.addScaledVector(q.v, dt);
      this.pos[n * 3] = q.p.x; this.pos[n * 3 + 1] = q.p.y; this.pos[n * 3 + 2] = q.p.z;
      this.size[n] = q.s0 + (q.s1 - q.s0) * t;
      for (let k = 0; k < 4; k++) this.col[n * 4 + k] = q.c0[k] + (q.c1[k] - q.c0[k]) * t;
      n++; keep.push(q);
    }
    this.list = keep;
    const g = this.points.geometry;
    g.setDrawRange(0, n);
    for (const a of ['position', 'size', 'rgba']) g.attributes[a].needsUpdate = true;
  }
}

// --------------------------------------------------------------------- scene
export class SceneView {
  constructor(renderer, models, terrain, world) {
    this.renderer = renderer; this.models = models; this.terrain = terrain; this.world = world;
    const scene = this.scene = new THREE.Scene();
    scene.background = HORIZON.clone();
    scene.fog = new THREE.FogExp2(HORIZON.clone(), 1.9e-5);
    this.camera = new THREE.PerspectiveCamera(70, 16 / 9, 0.6, 160000);
    this.camera.up.set(0, 0, 1);
    const sun = new THREE.DirectionalLight(0xfff4e0, 2.2);
    sun.position.copy(SUN_DIR).multiplyScalar(1000);
    scene.add(sun);
    const hemi = new THREE.HemisphereLight(0xbcd2f0, 0x4a5236, 0.95);
    hemi.position.set(0, 0, 1);
    scene.add(hemi);
    // own aircraft in cockpit view: layer 1, drawn in a second pass with a tiny near plane
    sun.layers.enable(1); hemi.layers.enable(1);
    this.cockpitCam = new THREE.PerspectiveCamera(70, 16 / 9, 0.03, 400);
    this.cockpitCam.up.set(0, 0, 1);
    this.cockpitCam.layers.set(1);
    this.glowTex = softTexture(64, 2.2);
    this.smoke = new Particles(scene, softTexture(64, 1.4), false, 2500);
    this.fire = new Particles(scene, this.glowTex, true, 1200);
    this.visuals = new Map(); this.missileVis = new Map();
    this.buildSky(); this.buildSea(); this.buildTerrain(); this.buildClouds(); this.buildAirfield();
    this.warmup = true;            // first update(): compile every shader once, so nothing stalls later
    const tg = new THREE.BufferGeometry();
    this.tracerPos = new Float32Array(6 * 600); this.tracerCol = new Float32Array(6 * 600);
    tg.setAttribute('position', new THREE.BufferAttribute(this.tracerPos, 3).setUsage(THREE.DynamicDrawUsage));
    tg.setAttribute('color', new THREE.BufferAttribute(this.tracerCol, 3).setUsage(THREE.DynamicDrawUsage));
    this.tracers = new THREE.LineSegments(tg, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.tracers.frustumCulled = false;
    scene.add(this.tracers);
    this.time = 0; this.cockpitView = false;
  }

  buildSky() {
    const geo = new THREE.SphereGeometry(1000, 32, 16).rotateX(Math.PI / 2);   // poles on the z axis
    const col = [], p = geo.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const el = p.getZ(i) / 1000;
      const c = el < 0 ? new THREE.Color(0.62, 0.70, 0.76) : HORIZON.clone().lerp(ZENITH, Math.pow(clamp(el / 0.75, 0, 1), 0.8));
      col.push(c.r, c.g, c.b);
    }
    geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    this.sky = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false, depthTest: false }));
    this.sky.renderOrder = -10;
    const sunMat = new THREE.SpriteMaterial({ map: softTexture(64, 2.5), color: 0xfff2cc, blending: THREE.AdditiveBlending, fog: false, depthTest: false, depthWrite: false });
    this.sunSprite = new THREE.Sprite(sunMat);
    this.sunSprite.scale.set(120, 120, 1);
    this.sunSprite.position.copy(SUN_DIR).multiplyScalar(900);
    this.sky.add(this.sunSprite);
    this.scene.add(this.sky);
  }
  buildSea() {
    const g = new THREE.PlaneGeometry(320000, 320000, 32, 32);
    const m = new THREE.Mesh(g, new THREE.MeshPhongMaterial({ color: 0x2b5674, specular: 0x8899aa, shininess: 60 }));
    m.position.z = -1.5;
    this.scene.add(m);
  }
  buildTerrain() {
    const t = this.terrain, n = t.n, cell = t.cell, half = t.half, grid = t.grid;
    const tex = this.models.tex.terrain;
    tex.anisotropy = 8; tex.encoding = THREE.sRGBEncoding;
    const mat = new THREE.MeshLambertMaterial({ map: tex });
    // normals
    const nrm = new Float32Array(n * n * 3);
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
      const hl = t.at(Math.max(i - 1, 0), j), hr = t.at(Math.min(i + 1, n - 1), j);
      const hd = t.at(i, Math.max(j - 1, 0)), hu = t.at(i, Math.min(j + 1, n - 1));
      const v = V(hl - hr, hd - hu, 2 * cell).normalize(), k = (j * n + i) * 3;
      nrm[k] = v.x; nrm[k + 1] = v.y; nrm[k + 2] = v.z;
    }
    const CH = 64, LODS = [[1, 0], [4, 9000], [16, 32000]], chunks = t.res / CH;
    const idxCache = {};
    const indices = (m) => {
      if (idxCache[m]) return idxCache[m];
      const w = m + 1, out = [];
      for (let j = 0; j < m; j++) for (let i = 0; i < m; i++) {
        const a = j * w + i; out.push(a, a + 1, a + w + 1, a, a + w + 1, a + w);
      }
      const border = [];
      for (let k = 0; k < w; k++) border.push(k);
      for (let k = 1; k < w; k++) border.push(k * w + m);
      for (let k = m - 1; k >= 0; k--) border.push(m * w + k);
      for (let k = m - 1; k > 0; k--) border.push(k * w);
      border.push(0);
      const base = w * w;
      for (let k = 0; k < border.length - 1; k++) {
        const a = border[k], b = border[k + 1], la = base + k, lb = base + k + 1;
        out.push(a, la, lb, a, lb, b, a, lb, la, a, b, lb);
      }
      return (idxCache[m] = { idx: out, border });
    };
    this.terrainGroup = new THREE.Group();
    for (let cj = 0; cj < chunks; cj++) for (let ci = 0; ci < chunks; ci++) {
      const lod = new THREE.LOD();
      const cx = -half + (ci + 0.5) * CH * cell, cy = -half + (cj + 0.5) * CH * cell;
      const cz = t.at(ci * CH + CH / 2, cj * CH + CH / 2);
      lod.position.set(cx, cy, cz);
      for (const [step, dist] of LODS) {
        const m = CH / step, w = m + 1, { idx, border } = indices(m);
        const nv = w * w + border.length;
        const pos = new Float32Array(nv * 3), nn = new Float32Array(nv * 3), uv = new Float32Array(nv * 2);
        let v = 0;
        for (let j = 0; j <= CH; j += step) for (let i = 0; i <= CH; i += step) {
          const gi = ci * CH + i, gj = cj * CH + j, k = gj * n + gi;
          pos[v * 3] = -half + gi * cell - cx; pos[v * 3 + 1] = -half + gj * cell - cy; pos[v * 3 + 2] = grid[k] - cz;
          nn[v * 3] = nrm[k * 3]; nn[v * 3 + 1] = nrm[k * 3 + 1]; nn[v * 3 + 2] = nrm[k * 3 + 2];
          uv[v * 2] = gi / (n - 1); uv[v * 2 + 1] = gj / (n - 1);
          v++;
        }
        for (const b of border) {
          pos[v * 3] = pos[b * 3]; pos[v * 3 + 1] = pos[b * 3 + 1]; pos[v * 3 + 2] = pos[b * 3 + 2] - 80;
          nn[v * 3] = nn[b * 3]; nn[v * 3 + 1] = nn[b * 3 + 1]; nn[v * 3 + 2] = nn[b * 3 + 2];
          uv[v * 2] = uv[b * 2]; uv[v * 2 + 1] = uv[b * 2 + 1];
          v++;
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        g.setAttribute('normal', new THREE.BufferAttribute(nn, 3));
        g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
        g.setIndex(idx);
        g.computeBoundingSphere();
        lod.addLevel(new THREE.Mesh(g, mat), dist);
      }
      this.terrainGroup.add(lod);
    }
    this.scene.add(this.terrainGroup);
  }
  buildClouds() {
    const tex = puffTexture(), r = rng(5), lim = this.terrain.half * 0.95;
    const mats = [0.75, 0.85, 0.95].map((o) => new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: o, depthWrite: false }));
    this.clouds = new THREE.Group();
    for (let k = 0; k < 70; k++) {
      const cx = r.uniform(-lim, lim), cy = r.uniform(-lim, lim), cz = r.uniform(2600, 3600), size = r.uniform(500, 1100);
      const puffs = 4 + Math.floor(r() * 5);
      for (let p = 0; p < puffs; p++) {
        const s = new THREE.Sprite(mats[Math.floor(r() * 3)]);
        s.position.set(cx + r.uniform(-1, 1) * size * 0.8, cy + r.uniform(-1, 1) * size * 0.8, cz + r.uniform(-0.15, 0.25) * size);
        const sc = size * r.uniform(0.8, 1.4);
        s.scale.set(sc, sc, 1);
        this.clouds.add(s);
      }
    }
    this.scene.add(this.clouds);
  }
  buildAirfield() {
    const a = this.terrain.airfield, g = new THREE.Group();
    g.position.set(a.x, a.y, a.elevation);
    // runway texture painted on a canvas
    const W = 256, H = 4096, c = document.createElement('canvas');
    c.width = W; c.height = H;
    const x = c.getContext('2d');
    const mx = (m) => (m + RUNWAY_WIDTH / 2) / RUNWAY_WIDTH * W;            // metres across -> px
    const my = (m) => H - (m / RUNWAY_LENGTH) * H;                           // metres from south end -> px
    x.fillStyle = '#353638'; x.fillRect(0, 0, W, H);
    for (let k = 0; k < 4000; k++) {                                         // asphalt texture / tyre marks
      x.fillStyle = `rgba(${Math.random() < 0.5 ? '20,20,22' : '70,70,72'},${Math.random() * 0.25})`;
      x.fillRect(Math.random() * W, Math.random() * H, 2 + Math.random() * 4, 2 + Math.random() * 6);
    }
    x.fillStyle = '#ebebe6';
    x.fillRect(mx(-RUNWAY_WIDTH / 2), 0, mx(-RUNWAY_WIDTH / 2 + 0.9) - mx(-RUNWAY_WIDTH / 2), H);
    x.fillRect(mx(RUNWAY_WIDTH / 2 - 0.9), 0, mx(RUNWAY_WIDTH / 2) - mx(RUNWAY_WIDTH / 2 - 0.9), H);
    for (let y = 120; y < RUNWAY_LENGTH - 120; y += 50) x.fillRect(mx(-0.45), my(y + 30), mx(0.45) - mx(-0.45), my(y) - my(y + 30));
    const end = (base, dir) => {
      for (let k = 0; k < 8; k++) for (const s of [-1, 1]) {
        const off = 3 + k * 2.6, x0 = s * off, x1 = s * (off + 1.8);
        x.fillRect(mx(Math.min(x0, x1)), my(base + dir * 36), Math.abs(mx(x1) - mx(x0)), Math.abs(my(base + dir * 36) - my(base + dir * 6)));
      }
      for (const s of [-1, 1]) {
        const x0 = s * 5.5, x1 = s * 14.5;
        x.fillRect(mx(Math.min(x0, x1)), my(base + dir * (dir > 0 ? 445 : 400)), Math.abs(mx(x1) - mx(x0)), Math.abs(my(0) - my(45)));
        for (const [dist, bars] of [[150, 3], [300, 2], [600, 2], [750, 1]]) for (let b = 0; b < bars; b++) {
          const xb = s * (6 + b * 3), xe = s * (7.8 + b * 3);
          x.fillRect(mx(Math.min(xb, xe)), my(base + dir * (dist + (dir > 0 ? 22 : 0))), Math.abs(mx(xe) - mx(xb)), Math.abs(my(0) - my(22)));
        }
      }
    };
    end(0, 1); end(RUNWAY_LENGTH, -1);
    x.save(); x.font = 'bold 90px sans-serif'; x.textAlign = 'center';
    x.translate(W / 2, my(75)); x.scale(1, 2.2); x.fillText('36', 0, 30); x.restore();
    x.save(); x.font = 'bold 90px sans-serif'; x.textAlign = 'center';
    x.translate(W / 2, my(RUNWAY_LENGTH - 75)); x.rotate(Math.PI); x.scale(1, 2.2); x.fillText('18', 0, 30); x.restore();
    const rtex = new THREE.CanvasTexture(c);
    rtex.anisotropy = 16; rtex.encoding = THREE.sRGBEncoding;
    const rw = new THREE.Mesh(new THREE.PlaneGeometry(RUNWAY_WIDTH + 6, RUNWAY_LENGTH + 120, 1, 12),
      new THREE.MeshLambertMaterial({ map: rtex, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 }));
    rw.position.z = 0.08;
    g.add(rw);
    const concrete = new THREE.MeshLambertMaterial({ color: 0x8a8a85, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2 });
    const slab = (x0, y0, x1, y1) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0), concrete);
      m.position.set((x0 + x1) / 2, (y0 + y1) / 2, 0.05); g.add(m);
    };
    const hl = RUNWAY_LENGTH / 2, tx = TAXIWAY_OFFSET;
    slab(tx - TAXIWAY_WIDTH / 2, -hl, tx + TAXIWAY_WIDTH / 2, hl);
    for (const cy of [-hl + 60, 0, hl - 60]) slab(RUNWAY_WIDTH / 2 + 3, cy - TAXIWAY_WIDTH / 2, tx - TAXIWAY_WIDTH / 2, cy + TAXIWAY_WIDTH / 2);
    const [ax0, ax1, ay0, ay1] = APRON;
    slab(tx + TAXIWAY_WIDTH / 2, ay0, ax1, ay1);
    const yl = new THREE.Mesh(new THREE.PlaneGeometry(0.5, RUNWAY_LENGTH), new THREE.MeshBasicMaterial({ color: 0xd8b52e, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -6 }));
    yl.position.set(tx, 0, 0.07); g.add(yl);
    // hardened aircraft shelters, tower, hangar, tanks
    const shelterMat = new THREE.MeshLambertMaterial({ color: 0x8c8a82 });
    const shelterGeo = new THREE.CylinderGeometry(13, 13, 36, 20, 1, true, -Math.PI / 2, Math.PI)
      .rotateZ(Math.PI / 2).scale(1, 1, 11 / 13);                      // half barrel along x, roof up
    const doorGeo = new THREE.CircleGeometry(12.6, 20, 0, Math.PI).rotateX(Math.PI / 2).rotateZ(Math.PI / 2).scale(1, 1, 11 / 13);
    const doorMat = new THREE.MeshLambertMaterial({ color: 0x4d4e4b, side: THREE.DoubleSide });
    for (let k = 0; k < 6; k++) {
      const s = new THREE.Group();
      s.add(new THREE.Mesh(shelterGeo, new THREE.MeshLambertMaterial({ color: 0x8c8a82, side: THREE.DoubleSide })));
      const door = new THREE.Mesh(doorGeo, doorMat); door.position.x = -17.9; s.add(door);
      const back = new THREE.Mesh(doorGeo, shelterMat); back.position.x = 17.9; s.add(back);
      s.position.set(ax1 - 40, ay0 + 60 + k * 115, 0);
      g.add(s);
    }
    const box = (w, d, h, color, px, py, pz) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, d, h), new THREE.MeshLambertMaterial({ color }));
      m.position.set(px, py, pz); g.add(m); return m;
    };
    box(10, 10, 24, 0x8f8f8a, tx + 80, ay0 - 60, 12);
    box(14, 14, 5, 0x2c4450, tx + 80, ay0 - 60, 26.5);
    box(15, 15, 1, 0x8f8f8a, tx + 80, ay0 - 60, 29.5);
    box(80, 60, 18, 0x737870, tx + 120, ay1 + 80, 9);
    for (let k = 0; k < 4; k++) {
      const tnk = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 9, 18).rotateX(Math.PI / 2), new THREE.MeshLambertMaterial({ color: 0xb4b4a8 }));
      tnk.position.set(ax1 + 60, ay0 + 40 + k * 22, 4.5); g.add(tnk);
    }
    // parked F-16s, Super Hornets, an Eagle and a Raptor
    for (let k = 0; k < 6; k++) {
      const key = ['f16', 'f16', 'fa18', 'fa18', 'f15', 'f22'][k], ac = this.models.aircraft(key);
      ac.position.set(tx + TAXIWAY_WIDTH + 45, ay0 + 90 + k * 48, this.models.types[key].gearHeight);
      ac.rotation.z = Math.PI / 2;
      g.add(ac);
    }
    // runway edge, threshold and approach lights
    const lamp = (px, py, color, size) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glowTex, color, blending: THREE.AdditiveBlending, depthWrite: false }));
      s.position.set(px, py, 0.6); s.scale.set(size, size, 1); g.add(s);
    };
    for (let y = -hl; y <= hl; y += 60) for (const s of [-1, 1]) lamp(s * (RUNWAY_WIDTH / 2 + 2), y, 0xfff2cc, 3);
    for (const s of [-1, 1]) for (let k = 0; k < 6; k++) { lamp(s * (3 + k * 3.5), -hl - 2, 0x4cff66, 3); lamp(s * (3 + k * 3.5), hl + 2, 0x4cff66, 3); }
    for (let d = 1; d <= 10; d++) for (let k = -3; k <= 3; k++) lamp(k * 3, -hl - d * 60, 0xffffe0, 2.5);
    this.scene.add(g);
  }

  // ------------------------------------------------------------------- events
  rand3(s) { const r = this.world.rnd; return V(r.uniform(-s, s), r.uniform(-s, s), r.uniform(-s, s)); }
  handleEvent(kind, d) {
    if (kind === 'explosion') this.explosion(d.pos, d.size || 1, d.ground);
    else if (kind === 'hit') {
      for (let i = 0; i < 3; i++) this.fire.spawn(d.pos, this.rand3(20), 0.18, [1.5, 3.5], [[1, 0.85, 0.5, 1], [1, 0.4, 0.1, 0]]);
      this.smoke.spawn(d.pos, null, 1.2, [2, 6], [[0.3, 0.3, 0.3, 0.6], [0.4, 0.4, 0.4, 0]]);
    } else if (kind === 'impact') this.smoke.spawn(d.pos, V(0, 0, 6), 1.5, [3, 9], [[0.55, 0.48, 0.38, 0.7], [0.6, 0.55, 0.45, 0]]);
    else if (kind === 'chaff') for (let i = 0; i < 3; i++) this.smoke.spawn(d.chaff.pos, add(mul(d.chaff.vel, 0.2), this.rand3(4)), d.chaff.life, [2, 12], [[0.75, 0.78, 0.82, 0.35], [0.8, 0.82, 0.85, 0]], 1.5);
    else if (kind === 'launch') for (let i = 0; i < 4; i++) this.smoke.spawn(d.missile.pos, add(mul(d.missile.vel, 0.9), this.rand3(6)), 1.6, [2, 8], [[0.85, 0.85, 0.85, 0.6], [0.9, 0.9, 0.9, 0]], 2);
  }
  explosion(pos, size, ground) {
    const r = this.world.rnd;
    for (let i = 0; i < 8 * size + 4; i++) this.fire.spawn(add(pos, this.rand3(3 * size)), this.rand3(25 * size), 0.5 + 0.5 * r(), [4 * size, 22 * size], [[1, 0.75, 0.35, 1], [0.9, 0.25, 0.05, 0]], 2.5);
    const sc = ground ? [0.35, 0.3, 0.25, 0.85] : [0.25, 0.23, 0.21, 0.75];
    for (let i = 0; i < 10 * size + 4; i++) this.smoke.spawn(add(pos, this.rand3(4 * size)), this.rand3(12 * size), 4 + 3 * r(), [8 * size, 40 * size], [sc, [0.45, 0.43, 0.42, 0]], 0.8, ground ? 2 : 0.5);
  }

  // ------------------------------------------------------------------- update
  visualFor(ac) {
    let v = this.visuals.get(ac);
    if (v) return v;
    const type = this.models.types[ac.spec.model] || this.models.types.f16;
    const root = new THREE.Group(), outside = this.models.aircraft(type.key);
    root.add(outside);
    const stores = new Map(), bays = outside.userData.bays;
    if (type.spec.bays) {
      // F-22: the missiles hang inside the bays (glTF frame of the model) and ride out on their launchers
      bays.missiles = {};
      for (const st of ac.stations) {
        const m = this.models.bayMissile(st.key);
        m.position.copy(bays.stores[st.number]); outside.userData.model.add(m);
        bays.missiles[st.number] = m; stores.set(st.number, m);
      }
    } else {
      for (const st of ac.stations) {
        const m = this.models.missile(st.key);
        m.position.copy(type.ref[`store_${st.number}`] || st.mount); outside.add(m); stores.set(st.number, m);
      }
    }
    const flames = type.nozzles.map((n) => {
      const flame = new THREE.Group();
      flame.add(new THREE.Mesh(this.models.flameGeo, this.models.flameMat), new THREE.Mesh(this.models.flameCoreGeo, this.models.flameCoreMat));
      flame.position.copy(n);
      root.add(flame);
      return flame;
    });
    const lamps = type.nav.map(([p, col]) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glowTex, color: col, blending: THREE.AdditiveBlending, depthWrite: false }));
      s.position.copy(p); s.scale.set(0.8, 0.8, 1); root.add(s); return s;
    });
    const strobes = type.strobes.map((p) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glowTex, color: 0xffffff, blending: THREE.AdditiveBlending, depthWrite: false }));
      s.position.copy(p); s.scale.set(1.3, 1.3, 1); root.add(s); return s;
    });
    this.scene.add(root);
    v = { root, outside, stores, flames, strobes, lamps, type, trail: 0, phase: Math.random() * 1.2, layer: 0 };
    this.visuals.set(ac, v);
    return v;
  }
  // the player's aircraft as the pilot sees it.  F-16: the old model with the detailed cockpit, shown only in
  // cockpit view; Super Hornet: its own model, cockpit included.  v.screens: the displays (mfd.js draws them).
  addInside(ac, v) {
    if (v.type.cockpit === 'self') { v.inside = null; v.screens = this.models.modelScreens(v.outside); return; }
    const inside = this.models.cockpitAircraft(ac.livery);
    v.screens = {};
    for (const [k, m] of Object.entries(inside.userData.screens)) v.screens[k] = [m];
    v.insideStores = new Map();
    for (const st of ac.stations) {
      const m = this.models.cockpitMissile(st.key);
      m.position.set(...COCKPIT_STATIONS[st.number]); inside.add(m); v.insideStores.set(st.number, m);
    }
    inside.visible = false;
    v.root.add(inside);
    v.inside = inside;
  }
  update(dt, player) {
    this.time += dt;
    const w = this.world, present = new Set();
    for (const ac of w.aircraft) {
      present.add(ac);
      const v = this.visualFor(ac);
      const visible = !ac.crashed;
      v.root.visible = visible;
      if (!visible) continue;
      if (ac === player && !v.screens) this.addInside(ac, v);
      const inside = this.cockpitView && ac === player;
      const layer = inside ? 1 : 0;
      if (v.layer !== layer) { v.root.traverse((o) => o.layers.set(layer)); v.layer = layer; }
      v.outside.visible = !inside || !v.inside;
      if (v.inside) v.inside.visible = inside;
      v.root.position.copy(ac.pos); v.root.quaternion.copy(ac.quat);
      for (const st of ac.stations) {
        const m = v.stores.get(st.number), mi = v.insideStores && v.insideStores.get(st.number);
        if (m && !v.type.spec.bays) m.visible = st.loaded;
        if (mi) mi.visible = st.loaded;
      }
      this.models.setGear(v.outside, ac.fm.gearPos);
      if (v.type.spec.bays) this.models.setBays(v.outside, ac);
      const e = ac.engineSetting;
      v.flames.forEach((flame, k) => {
        if (ac.alive && e > 1) {
          const ab = (e - 1) / 0.1, fl = 1 + 0.08 * Math.sin(this.time * 61 + k * 2.1) + 0.05 * Math.sin(this.time * 23 + k);
          const r = (0.78 + 0.14 * ab) * v.type.flameScale;
          flame.visible = true; flame.scale.set(r, (2 + 3.2 * ab) * fl * v.type.flameScale, r);
        } else flame.visible = false;
      });
      if (ac.alive) {
        for (const model of [v.outside, v.inside]) {
          if (model) animateSurfaces(model.userData.parts, dt, ac.controls, ac.fm.alpha / DEG, ac.fm.flaps, ac.controls.airbrake && !ac.onGround ? 1 : 0, ac.onGround);
        }
        const ph = (this.time + v.phase) % 1.2;
        for (const s of v.strobes) s.visible = ph < 0.06 || (ph > 0.18 && ph < 0.24);
      } else for (const s of v.strobes) s.visible = false;
      this.aircraftEffects(ac, v, dt);
    }
    for (const [ac, v] of [...this.visuals]) if (!present.has(ac)) { this.scene.remove(v.root); this.visuals.delete(ac); }

    const mp = new Set();
    for (const m of w.missiles) {
      mp.add(m);
      let mv = this.missileVis.get(m);
      if (!mv) { mv = { mesh: this.models.missile(m.spec.name), last: copy(m.pos) }; this.scene.add(mv.mesh); this.missileVis.set(m, mv); }
      mv.mesh.position.copy(m.pos);
      mv.mesh.quaternion.setFromUnitVectors(V(0, 1, 0), m.dir);
      if (m.burning) {
        const tail = add(m.pos, mul(m.dir, -m.spec.length / 2));
        this.fire.spawn(tail, m.vel, 0.05, [1.6, 1], [[1, 0.8, 0.5, 1], [1, 0.5, 0.2, 0]]);
        const step = mv.last.distanceTo(m.pos);
        if (step > 7) {
          const n = Math.min(Math.floor(step / 7), 12);
          for (let k = 0; k < n; k++) {
            const p = mv.last.clone().lerp(tail, (k + 1) / n);
            this.smoke.spawn(p, this.rand3(1.5), 5, [1.5, 7], [[0.92, 0.92, 0.92, 0.75 * m.spec.smoke], [0.95, 0.95, 0.95, 0]]);
          }
          mv.last = copy(tail);
        }
      }
    }
    for (const [m, mv] of [...this.missileVis]) if (!mp.has(m)) { this.scene.remove(mv.mesh); this.missileVis.delete(m); }

    for (const f of w.flares) {
      const k = f.intensity / f.peak;
      this.fire.spawn(f.pos, null, 0.06, [5 * k + 1, 4 * k + 1], [[1, 0.95, 0.8, 1], [1, 0.7, 0.4, 0.6]]);
      if (w.rnd() < 0.5) this.smoke.spawn(f.pos, null, 2, [1, 4], [[0.95, 0.95, 0.95, 0.35], [1, 1, 1, 0]]);
    }
    let n = 0;
    for (const b of w.bullets) {
      if (!b.tracer || n >= 600) continue;
      const tail = add(b.pos, mul(b.vel, -0.014));
      this.tracerPos.set([b.pos.x, b.pos.y, b.pos.z, tail.x, tail.y, tail.z], n * 6);
      this.tracerCol.set([1, 0.85, 0.35, 0.6, 0.25, 0.05], n * 6);
      n++;
    }
    const tg = this.tracers.geometry;
    tg.setDrawRange(0, n * 2); tg.attributes.position.needsUpdate = true; tg.attributes.color.needsUpdate = true;
    this.smoke.update(dt); this.fire.update(dt);
    const scale = this.renderer.domElement.height / (2 * Math.tan(this.camera.fov * DEG / 2));
    this.smoke.uniforms.scale.value = scale; this.fire.uniforms.scale.value = scale;
    this.sky.position.copy(this.camera.position);
  }
  // Shaders are compiled the first time a material is drawn. The afterburner flame, missiles in the air and
  // the cockpit pass would otherwise compile in the middle of the game and freeze it for a moment.
  compileAll() {
    const shown = [];
    this.scene.traverse((o) => { if (!o.visible) { shown.push(o); o.visible = true; } });
    for (const layer of [0, 1]) { this.camera.layers.enable(layer); }
    this.renderer.compile(this.scene, this.camera);
    this.camera.layers.set(0);
    for (const o of shown) o.visible = false;
  }
  render() {
    if (this.warmup) { this.warmup = false; this.compileAll(); }
    const r = this.renderer, cam = this.camera;
    r.autoClear = true;
    r.render(this.scene, cam);
    if (!this.cockpitView) return;
    const cc = this.cockpitCam;
    cc.position.copy(cam.position); cc.quaternion.copy(cam.quaternion);
    const vw = cam.view && cam.view.enabled ? cam.view : null;
    if (cc.fov !== cam.fov || cc.aspect !== cam.aspect || (vw ? !cc.view || cc.view.offsetY !== vw.offsetY : cc.view && cc.view.enabled)) {
      cc.fov = cam.fov; cc.aspect = cam.aspect;
      if (vw) cc.setViewOffset(vw.fullWidth, vw.fullHeight, vw.offsetX, vw.offsetY, vw.width, vw.height);
      else cc.clearViewOffset();
      cc.updateProjectionMatrix();
    }
    cc.updateMatrixWorld();
    const bg = this.scene.background;
    this.scene.background = null;              // a colour background would force a clear of pass 1
    r.autoClear = false;
    r.clearDepth();
    r.render(this.scene, cc);
    r.autoClear = true;
    this.scene.background = bg;
  }
  aircraftEffects(ac, v, dt) {
    if (ac.crashed) return;
    const q = ac.quat;
    if (ac.burning || ac.damaged) {
      v.trail -= dt;
      if (v.trail <= 0) {
        v.trail = 0.04;
        const tail = add(ac.pos, xform(q, v.type.tail));
        if (ac.burning) {
          this.fire.spawn(tail, mul(ac.vel, 0.7), 0.35, [4, 8], [[1, 0.6, 0.2, 0.9], [0.8, 0.2, 0.05, 0]], 3);
          this.smoke.spawn(tail, mul(ac.vel, 0.5), 7, [4, 22], [[0.12, 0.11, 0.1, 0.8], [0.3, 0.3, 0.3, 0]], 2);
        } else this.smoke.spawn(tail, mul(ac.vel, 0.5), 3.5, [2, 10], [[0.45, 0.45, 0.45, 0.5], [0.6, 0.6, 0.6, 0]], 2);
      }
    }
    if (!ac.alive) return;
    const alpha = ac.fm.alpha / DEG;
    if (alpha > 13 && ac.speed > 70) {
      const a = 0.38 * Math.min(1, (alpha - 13) / 9);
      for (const s of v.type.vapor) this.smoke.spawn(add(ac.pos, xform(q, s)), mul(ac.vel, 0.9), 0.45, [0.7, 2.8], [[1, 1, 1, a], [1, 1, 1, 0]], 1.5);
    }
    if (ac.fm.gLoad > 5.5 && ac.speed > 120) {
      const a = Math.min(0.45, (ac.fm.gLoad - 5.5) * 0.12);
      for (const t of v.type.wingtips) this.smoke.spawn(add(ac.pos, xform(q, t)), mul(ac.vel, 0.85), 0.7, [0.5, 1.4], [[1, 1, 1, a], [1, 1, 1, 0]], 2);
    }
    if (ac.gun.firing) this.fire.spawn(add(ac.pos, xform(q, add(v.type.gun, V(0, 0.6, 0)))), ac.vel, 0.04, [1.2, 2.2], [[1, 0.85, 0.5, 1], [1, 0.5, 0.1, 0]]);
  }
}
