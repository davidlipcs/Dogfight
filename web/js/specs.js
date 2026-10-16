// Aircraft, missile, gun, radar and countermeasure data.  F-16C Block 50 (F110-GE-129, APG-68) and
// F/A-18E Super Hornet (2 x F414-GE-400, APG-79), AIM-9M / AIM-120A, M61A1 / M61A2.
export const IR = 'IR', ARH = 'ARH';

export const M61A1 = {
  name: 'M61A1', rateRpm: 6000, ammo: 511, muzzle: 1050, dragK: 3.7e-4, dispersionMrad: 1.6,
  damage: 9, life: 3.0, maxLeadRange: 1800,
};
// the Super Hornet's lighter M61A2 in the nose: same 20 mm rounds, 412 of them
export const M61A2 = { ...M61A1, name: 'M61A2', ammo: 412, dispersionMrad: 1.4 };

export const AIM9M = {
  name: 'AIM-9M', guidance: IR, mass: 86, propellant: 22, diameter: 0.127, length: 2.87,
  motor: [[5.0, 9200]],
  cd: [[0.5, 0.36], [0.9, 0.42], [1.1, 0.72], [1.6, 0.6], [2.5, 0.48], [4.0, 0.4]],
  cnMax: 18, maxG: 30, inducedDrag: 0.16, navGain: 4, guidanceDelay: 0.2, guidanceTime: 60, armTime: 0.6,
  fuseRadius: 6, lethalRadius: 4, damageRadius: 14, damage: 140,
  seekerFov: 2.5, gimbal: 40, trackRate: 30, seekerRange: 9000, ccm: 0.65, minRange: 400,
  datalink: false, loft: false, smoke: 0.35, railTime: 0.25,
};

export const AIM120A = {
  name: 'AIM-120A', guidance: ARH, mass: 152, propellant: 50, diameter: 0.178, length: 3.65,
  motor: [[3.0, 28500], [5.0, 9500]],
  cd: [[0.5, 0.34], [0.9, 0.4], [1.1, 0.7], [1.6, 0.58], [2.5, 0.45], [4.5, 0.36]],
  cnMax: 20, maxG: 38, inducedDrag: 0.13, navGain: 4, guidanceDelay: 0.45, guidanceTime: 80, armTime: 1.0,
  fuseRadius: 9, lethalRadius: 6, damageRadius: 22, damage: 160,
  seekerFov: 15, gimbal: 50, trackRate: 25, seekerRange: 16000, ccm: 0.55, minRange: 1200,
  datalink: true, loft: true, smoke: 0.3, railTime: 0.25,
};
for (const m of [AIM9M, AIM120A]) {
  m.refArea = Math.PI * (m.diameter / 2) ** 2;
  m.burnTime = m.motor.reduce((s, p) => s + p[0], 0);
}
export const MISSILES = { 'AIM-9M': AIM9M, 'AIM-120A': AIM120A };

// The game is tuned in the player's favour: the player's missiles are much harder to dodge and deadly up
// close, the enemies' are weaker.  (motor: thrust scale; the rest replaces the real values)
function variant(base, motor, changes) {
  const m = { ...base, ...changes, motor: base.motor.map(([t, f]) => [t, f * motor]) };
  m.refArea = base.refArea; m.burnTime = base.burnTime;
  return m;
}
export const PLAYER_MISSILES = {
  'AIM-9M': variant(AIM9M, 1.3, { maxG: 55, cnMax: 32, tvc: 0.7, railTime: 0.1, navGain: 5, guidanceDelay: 0.1, armTime: 0.25, minRange: 150,
    fuseRadius: 12, lethalRadius: 9, damageRadius: 24, damage: 220, seekerFov: 6, gimbal: 70, trackRate: 120,
    seekerRange: 12000, ccm: 0.99 }),
  'AIM-120A': variant(AIM120A, 1.25, { maxG: 55, cnMax: 30, tvc: 0.4, railTime: 0.1, navGain: 5, guidanceDelay: 0.25, armTime: 0.45, minRange: 350,
    fuseRadius: 14, lethalRadius: 11, damageRadius: 30, damage: 240, seekerFov: 22, gimbal: 70, trackRate: 90,
    seekerRange: 20000, ccm: 0.98, notch: 8 }),
};
export const BANDIT_MISSILES = {
  'AIM-9M': variant(AIM9M, 0.85, { maxG: 20, cnMax: 13, navGain: 3.2, guidanceDelay: 0.35, armTime: 0.8, minRange: 700,
    fuseRadius: 4.5, lethalRadius: 2.5, damageRadius: 10, damage: 100, seekerFov: 2, gimbal: 30, trackRate: 18,
    seekerRange: 6500, ccm: 0.4 }),
  'AIM-120A': variant(AIM120A, 0.85, { maxG: 25, cnMax: 14, navGain: 3.2, guidanceDelay: 0.6, armTime: 1.3, minRange: 2000,
    fuseRadius: 7, lethalRadius: 4, damageRadius: 15, damage: 110, seekerFov: 12, gimbal: 40, trackRate: 18,
    seekerRange: 11000, ccm: 0.3, notch: 40 }),
};

export const APG68 = {
  name: 'AN/APG-68(V)9', searchRange: 74000, scanAz: 60, scanEl: 12, scanRate: 120, sttGimbal: 60,
  lockRange: 55000, acmRange: 16000, acmAz: 6, acmElLow: -6, acmElHigh: 40, lockTime: 0.5,
  notchSpeed: 25, trackMemory: 0.6, rwrSymbol: '16',
};

// AESA: the beam jumps electronically, so the whole scan volume is covered much faster and locks are quicker
export const APG79 = {
  name: 'AN/APG-79 AESA', searchRange: 90000, scanAz: 60, scanEl: 14, scanRate: 260, sttGimbal: 60,
  lockRange: 70000, acmRange: 18000, acmAz: 7, acmElLow: -8, acmElHigh: 45, lockTime: 0.35,
  notchSpeed: 20, trackMemory: 0.8, rwrSymbol: '18',
};

// The Raptor's AESA: longest range, fastest scan and lock, and low probability of intercept: an RWR only
// notices it when it locks on (lpi), not while it searches
export const APG77 = {
  name: 'AN/APG-77 AESA', searchRange: 120000, scanAz: 60, scanEl: 15, scanRate: 300, sttGimbal: 60,
  lockRange: 100000, acmRange: 20000, acmAz: 7, acmElLow: -8, acmElHigh: 45, lockTime: 0.3,
  notchSpeed: 15, trackMemory: 1.0, rwrSymbol: '22', lpi: true,
};

export const ALE47 = { flares: 30, chaff: 30, flareIntensity: 3.0, flareLife: 4.0, chaffLife: 5.0, interval: 0.35 };

// Station numbers follow the real aircraft (1 = left wingtip).  `pylons`: what each station can carry;
// `prefer`: the order a weapon fills the stations in (the loadout editor in the menu uses it).
export const F16C = {
  id: 'f16', model: 'f16', name: 'F-16C Block 50', short: 'F-16C', callsign: 'Viper',
  emptyMass: 8900, internalFuel: 3200, wingArea: 27.87, wingSpan: 9.96, length: 15.06,
  // F110-GE-129: 76.3 kN military, 131.6 kN with afterburner; TSFC ~0.76 / ~1.95 lb/lbf/h
  engines: 1, thrustDry: 76300, thrustAb: 131600, fuelFlowDry: 1.64, fuelFlowAb: 7.25,
  clAlpha: 4.1, clMax: 1.8, alphaStall: 30, alphaLimit: 25, cd0: 0.0205, kInduced: 0.118, pylonCd: 0.0010,
  waveDrag: [[0, 0], [0.8, 0], [0.88, 0.004], [0.95, 0.018], [1.0, 0.03], [1.05, 0.035], [1.2, 0.037], [1.6, 0.027], [2.2, 0.02]],
  gMax: 9, gMin: -3, rollRate: 270, yawBeta: 6, airbrakeCd: 0.06, hp: 100, rcsFront: 1.5, rcsSide: 6,
  gearHeight: 2.05, tailStrike: 13, rotateIas: 60,
  // fuselage, wings, stabilators, fin: [centre], [half size] around the Blender model (assets/f16.glb)
  hitboxes: [
    [[0, 1.3, -0.25], [0.95, 7.3, 0.95]], [[0, -0.4, -0.3], [4.75, 2.0, 0.3]],
    [[0, -4.5, -0.45], [2.8, 1.3, 0.3]], [[0, -3.9, 1.65], [0.3, 1.6, 1.35]],
  ],
  gun: M61A1, gunPos: [-0.70, 3.95, -0.20], radar: APG68, cm: ALE47,
  stations: {       // the store_* points of the model
    1: [-4.80, -0.80, -0.30], 2: [-3.96, -1.41, -0.60], 3: [-3.05, -1.14, -0.80],
    7: [3.05, -1.14, -0.80], 8: [3.96, -1.41, -0.60], 9: [4.80, -0.80, -0.30],
  },
  pylons: { 1: ['AIM-9M', 'AIM-120A'], 2: ['AIM-9M', 'AIM-120A'], 3: ['AIM-9M', 'AIM-120A'], 7: ['AIM-9M', 'AIM-120A'], 8: ['AIM-9M', 'AIM-120A'], 9: ['AIM-9M', 'AIM-120A'] },
  prefer: { 'AIM-120A': [3, 7, 1, 9, 2, 8], 'AIM-9M': [1, 9, 2, 8, 3, 7] },
  loadouts: {
    default: { 1: 'AIM-9M', 9: 'AIM-9M', 2: 'AIM-9M', 8: 'AIM-9M', 3: 'AIM-120A', 7: 'AIM-120A' },
  },
  firingOrder: [9, 1, 8, 2, 7, 3],
  // EXTRÉM mód (Tab): tolóerő-vektorálás, mint a kísérleti F-16 MATV / VISTA.  A fúvócső ±20°-ot fordul, így
  // a gép kis sebességen is tud forgatni, 9 G-t tart, és teljes húzásra át tud menni nagy állásszögbe (Cobra).
  tvc: {
    vector: 20, alphaNormal: 32, alphaPostStall: 80, rollRate: 330, pitchRate: 2.4, thrustScale: 1.2,
    kScale: 0.75, clMax: 2.4, lowSpeedAuthority: 0.65,
  },
};

// F/A-18E: heavier, more wing, two engines.  Lower thrust to weight than the Viper and more drag (the canted
// pylons are famous for it), but the big LEX and the flight controls let it fly at very high angles of attack:
// it points its nose better at low speed and loses energy faster.
export const FA18E = {
  id: 'fa18', model: 'fa18', name: 'F/A-18E Super Hornet', short: 'F/A-18E', callsign: 'Rhino',
  emptyMass: 14552, internalFuel: 6530, wingArea: 46.45, wingSpan: 13.62, length: 18.31,
  // 2 x F414-GE-400: 57.8 kN military, 97.9 kN with afterburner each; TSFC ~0.84 / ~1.85 lb/lbf/h
  engines: 2, thrustDry: 115600, thrustAb: 195800, fuelFlowDry: 2.75, fuelFlowAb: 10.3,
  clAlpha: 4.4, clMax: 2.0, alphaStall: 38, alphaLimit: 40, cd0: 0.0235, kInduced: 0.105, pylonCd: 0.0035,
  waveDrag: [[0, 0], [0.78, 0], [0.86, 0.005], [0.94, 0.024], [1.0, 0.040], [1.05, 0.046], [1.2, 0.047], [1.6, 0.036], [2.0, 0.03]],
  gMax: 7.5, gMin: -3, rollRate: 220, yawBeta: 8, airbrakeCd: 0.05, hp: 115, rcsFront: 1.0, rcsSide: 8,
  gearHeight: 1.95, tailStrike: 12, rotateIas: 64,
  hitboxes: [
    [[0, 0.6, -0.2], [1.15, 9.0, 0.9]], [[0, -0.8, -0.1], [6.7, 2.3, 0.3]],
    [[0, -6.7, -0.3], [3.7, 1.3, 0.3]], [[0, -4.3, 1.4], [1.8, 1.6, 1.3]],
  ],
  gun: M61A2, gunPos: [0, 8.20, 0.45], radar: APG79, cm: ALE47,
  stations: {
    1: [-6.76, -1.57, -0.22], 2: [-4.79, -1.53, -0.68], 3: [-3.64, -1.23, -0.62], 4: [-2.49, -0.92, -0.56], 5: [-0.95, 0.15, -1.26],
    7: [0.95, 0.15, -1.26], 8: [2.49, -0.92, -0.56], 9: [3.64, -1.23, -0.62], 10: [4.79, -1.53, -0.68], 11: [6.76, -1.57, -0.22],
  },
  pylons: {
    1: ['AIM-9M'], 11: ['AIM-9M'], 5: ['AIM-120A'], 7: ['AIM-120A'],
    2: ['AIM-9M', 'AIM-120A'], 3: ['AIM-9M', 'AIM-120A'], 4: ['AIM-9M', 'AIM-120A'],
    8: ['AIM-9M', 'AIM-120A'], 9: ['AIM-9M', 'AIM-120A'], 10: ['AIM-9M', 'AIM-120A'],
  },
  prefer: { 'AIM-120A': [5, 7, 4, 8, 3, 9, 2, 10], 'AIM-9M': [1, 11, 2, 10, 3, 9, 4, 8] },
  loadouts: {
    default: { 1: 'AIM-9M', 11: 'AIM-9M', 2: 'AIM-9M', 10: 'AIM-9M', 3: 'AIM-120A', 9: 'AIM-120A', 4: 'AIM-120A', 8: 'AIM-120A', 5: 'AIM-120A', 7: 'AIM-120A' },
  },
  firingOrder: [11, 1, 10, 2, 9, 3, 8, 4, 7, 5],
};

// F-22A: stealth (tiny radar cross section, colder exhaust), everything carried inside: 6 AIM-120 in the main
// bay, one AIM-9 in each side bay.  Firing opens the doors and swings the missile out on its launcher first
// (about 0.7 s), and while a door is open the jet is easy to see on radar.  2 x F119: supercruise, high thrust;
// two dimensional thrust vectoring is always on.  The game caps it at 8 G.
export const F22A = {
  id: 'f22', model: 'f22', name: 'F-22A Raptor', short: 'F-22A', callsign: 'Raptor',
  emptyMass: 19700, internalFuel: 8200, wingArea: 78.04, wingSpan: 13.56, length: 18.92,
  // 2 x F119-PW-100: ~116 kN military, ~156 kN with afterburner each; TSFC ~0.75 / ~1.9 lb/lbf/h
  engines: 2, thrustDry: 232000, thrustAb: 312000, fuelFlowDry: 4.9, fuelFlowAb: 16.8,
  clAlpha: 3.6, clMax: 1.9, alphaStall: 40, alphaLimit: 35, cd0: 0.0190, kInduced: 0.16, pylonCd: 0,
  waveDrag: [[0, 0], [0.86, 0], [0.94, 0.004], [1.0, 0.011], [1.06, 0.016], [1.15, 0.017], [1.4, 0.016], [1.8, 0.014], [2.2, 0.013]],
  gMax: 8, gMin: -3, rollRate: 250, yawBeta: 8, airbrakeCd: 0.05, hp: 120,
  rcsFront: 0.0006, rcsSide: 0.006, rcsBay: 1.5, irScale: 0.65,
  gearHeight: 1.98, tailStrike: 12, rotateIas: 66,
  hitboxes: [
    [[0, 0.2, -0.1], [1.6, 9.0, 0.8]], [[0, -1.5, 0.05], [6.8, 2.6, 0.3]],
    [[0, -7.4, -0.2], [4.4, 1.4, 0.3]], [[0, -6.3, 1.3], [2.2, 1.6, 1.2]],
  ],
  gun: { ...M61A2, ammo: 480 }, gunPos: [1.20, 2.35, 0.55], radar: APG77, cm: ALE47,
  // launch points: where the missile leaves its launcher (trapeze down, rail out); the missiles sit inside the
  // bays until then (render.js reads those places from the model)
  stations: {
    1: [-1.33, 1.15, -1.24], 2: [-0.66, -0.01, -1.40], 3: [-0.43, 0.39, -1.40], 4: [-0.20, -0.01, -1.40],
    5: [0.20, -0.01, -1.40], 6: [0.43, 0.39, -1.40], 7: [0.66, -0.01, -1.40], 8: [1.33, 1.15, -1.24],
  },
  pylons: { 1: ['AIM-9M'], 8: ['AIM-9M'], 2: ['AIM-120A'], 3: ['AIM-120A'], 4: ['AIM-120A'], 5: ['AIM-120A'], 6: ['AIM-120A'], 7: ['AIM-120A'] },
  prefer: { 'AIM-120A': [4, 5, 3, 6, 2, 7], 'AIM-9M': [1, 8] },
  loadouts: {
    default: { 1: 'AIM-9M', 8: 'AIM-9M', 2: 'AIM-120A', 3: 'AIM-120A', 4: 'AIM-120A', 5: 'AIM-120A', 6: 'AIM-120A', 7: 'AIM-120A' },
  },
  firingOrder: [8, 1, 7, 2, 6, 3, 5, 4],
  // internal carriage: which door each station opens, how it is launched, and the timing (s)
  bays: { 1: 'side_L', 8: 'side_R', 2: 'main', 3: 'main', 4: 'main', 5: 'main', 6: 'main', 7: 'main' },
  launch: {
    'AIM-120A': { open: 0.30, out: [0.30, 0.65], release: 0.70, back: [0.80, 1.15], close: [1.15, 1.45], eject: 8 },
    'AIM-9M': { open: 0.25, out: [0.25, 0.55], release: 0.75, back: [0.85, 1.15], close: [1.15, 1.40], eject: 2 },
  },
  tvcAlways: true,
  tvc: {
    vector: 20, alphaNormal: 35, alphaPostStall: 60, rollRate: 260, pitchRate: 2.0, thrustScale: 1.0,
    kScale: 1.0, clMax: 2.1, lowSpeedAuthority: 0.5,
  },
};

export const AIRCRAFT = { f16: F16C, fa18: FA18E, f22: F22A };

// the enemies fly the same jets with a weaker airframe: less G, slower roll, lower angle of attack limit
export const BANDITS = {
  f16: { ...F16C, name: 'F-16C (ellenfél)', gMax: 7, rollRate: 190, alphaLimit: 20 },
  fa18: { ...FA18E, name: 'F/A-18E (ellenfél)', gMax: 6.3, rollRate: 150, alphaLimit: 28 },
  f22: { ...F22A, name: 'F-22A (ellenfél)', gMax: 6.8, rollRate: 190, tvcAlways: false, tvc: undefined },
};
export const F16C_BANDIT = BANDITS.f16;

// Station layout for `n9` AIM-9s and `n120` AIM-120s: every weapon first takes the stations only it can use,
// then the shared ones in its order of preference.  Returns {station: weapon} and what did not fit.
export function buildLoadout(spec, n9, n120) {
  const layout = {}, want = { 'AIM-9M': n9, 'AIM-120A': n120 };
  for (const pass of ['own', 'shared']) {
    for (const key of ['AIM-120A', 'AIM-9M']) {
      for (const st of spec.prefer[key]) {
        if (want[key] <= 0) break;
        const ok = spec.pylons[st] || [];
        if (layout[st] || !ok.includes(key) || (pass === 'own') !== (ok.length === 1)) continue;
        layout[st] = key; want[key]--;
      }
    }
  }
  return { layout, left: want };
}
export function loadoutLimits(spec) {
  const n = (k) => Object.values(spec.pylons).filter((p) => p.includes(k)).length;
  return { 'AIM-9M': n('AIM-9M'), 'AIM-120A': n('AIM-120A'), total: Object.keys(spec.pylons).length };
}
