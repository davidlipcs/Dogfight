// Small vector / quaternion helpers on top of THREE (global from the UMD build).
// World: +X east, +Y north, +Z up (same as the Python version). SI units.
export const THREE = window.THREE;
export const G = 9.80665;
export const DEG = Math.PI / 180;

export const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
export const add = (a, b) => V(a.x + b.x, a.y + b.y, a.z + b.z);
export const sub = (a, b) => V(a.x - b.x, a.y - b.y, a.z - b.z);
export const mul = (a, s) => V(a.x * s, a.y * s, a.z * s);
export const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
export const cross = (a, b) => V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
export const len = (a) => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const copy = (a) => V(a.x, a.y, a.z);

export function norm(a, fallback) {
  const l = len(a);
  if (l > 1e-9) return V(a.x / l, a.y / l, a.z / l);
  return fallback ? copy(fallback) : V(0, 1, 0);
}

export const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
export const lerp = (a, b, t) => a + (b - a) * t;
export function smoothstep(e0, e1, x) {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
}

export function angleBetween(a, b) {
  const la = len(a), lb = len(b);
  if (la < 1e-9 || lb < 1e-9) return 0;
  return Math.acos(clamp(dot(a, b) / (la * lb), -1, 1));
}

export function interp(table, x) {
  if (x <= table[0][0]) return table[0][1];
  for (let i = 0; i < table.length - 1; i++) {
    const [x0, y0] = table[i], [x1, y1] = table[i + 1];
    if (x <= x1) return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
  }
  return table[table.length - 1][1];
}

// ---- quaternions. qmul(a, b) = a*b : b is applied first.
export const Q = () => new THREE.Quaternion();
export function qaxis(axis, angle) {
  return new THREE.Quaternion().setFromAxisAngle(norm(axis), angle);
}
export const qmul = (a, b) => a.clone().multiply(b);
export const xform = (q, v) => v.clone().applyQuaternion(q);
export const toLocal = (q, v) => v.clone().applyQuaternion(q.clone().invert());
export const fwdOf = (q) => xform(q, V(0, 1, 0));
export const upOf = (q) => xform(q, V(0, 0, 1));
export const rightOf = (q) => xform(q, V(1, 0, 0));

// Orientation whose +Y axis points along forward and +Z as close to `up` as possible.
export function qlook(forward, up = V(0, 0, 1)) {
  const y = norm(forward);
  let u = up;
  if (Math.abs(dot(y, u)) > 0.999) u = Math.abs(y.z) > 0.5 ? V(0, 1, 0) : V(0, 0, 1);
  const x = norm(cross(y, u));
  const z = cross(x, y);
  const m = new THREE.Matrix4().makeBasis(x, y, z);
  return new THREE.Quaternion().setFromRotationMatrix(m);
}

// compass heading (deg, clockwise from north) + pitch (deg) -> quaternion
export function qheading(headingDeg, pitchDeg = 0) {
  return qmul(qaxis(V(0, 0, 1), -headingDeg * DEG), qaxis(V(1, 0, 0), pitchDeg * DEG));
}

export function rotateTowards(cur, target, maxAngle) {
  const ang = angleBetween(cur, target);
  if (ang <= maxAngle || ang < 1e-6) return copy(target);
  let axis = cross(cur, target);
  if (len(axis) < 1e-9) axis = Math.abs(cur.z) < 0.9 ? cross(cur, V(0, 0, 1)) : cross(cur, V(1, 0, 0));
  return norm(xform(qaxis(axis, maxAngle), cur));
}

export function closestApproach(pRel, vRel, dt) {
  const vv = dot(vRel, vRel);
  let t = 0;
  if (vv > 1e-9) t = clamp(-dot(pRel, vRel) / vv, 0, dt);
  return [len(add(pRel, mul(vRel, t))), t];
}

export const headingDeg = (v) => ((Math.atan2(v.x, v.y) / DEG) % 360 + 360) % 360;

export function bankAngle(q) {
  const r = rightOf(q), u = upOf(q);
  return Math.atan2(-r.z, u.z);
}

export const wrap = (a) => ((((a + Math.PI) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) - Math.PI;

// seeded random (mulberry32)
export function rng(seed = 1) {
  let a = seed >>> 0;
  const r = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  r.uniform = (lo, hi) => lo + (hi - lo) * r();
  r.gauss = (mu = 0, sigma = 1) => {
    const u = Math.max(r(), 1e-12), v = r();
    return mu + sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  return r;
}

export function b64ToArray(b64, Type) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Type(bytes.buffer);
}
