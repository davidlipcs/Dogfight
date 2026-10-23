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

export const APG82 = {
  name: 'AN/APG-82(V)1 AESA', searchRange: 110000, scanAz: 60, scanEl: 14, scanRate: 280, sttGimbal: 60,
  lockRange: 90000, acmRange: 18000, acmAz: 7, acmElLow: -8, acmElHigh: 45, lockTime: 0.35,
  notchSpeed: 20, trackMemory: 0.8, rwrSymbol: '15',
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

// F-15EX Eagle II: the big twin-engine Eagle with the F-16's engines (2 x F110-GE-129), a fly-by-wire 9 G
// airframe and a huge wing - it fights like a heavier, more powerful F-16: lots of thrust, good sustained
// turns.  Missiles hang outside: two pylons per wing (the inner one with two rails) and AIM-120s on the
// conformal fuel tanks.
export const F15EX = {
  id: 'f15', model: 'f15', name: 'F-15EX Eagle II', short: 'F-15EX', callsign: 'Eagle',
  emptyMass: 14500, internalFuel: 10000, wingArea: 56.5, wingSpan: 13.05, length: 19.43,
  // 2 x F110-GE-129 (the F-16's engine): 2 x 76.3 / 2 x 131.6 kN
  engines: 2, thrustDry: 152600, thrustAb: 263200, fuelFlowDry: 3.28, fuelFlowAb: 14.5,
  clAlpha: 3.7, clMax: 1.7, alphaStall: 32, alphaLimit: 30, cd0: 0.0215, kInduced: 0.125, pylonCd: 0.0012,
  waveDrag: [[0, 0], [0.8, 0], [0.88, 0.004], [0.95, 0.018], [1.0, 0.03], [1.05, 0.035], [1.2, 0.036], [1.6, 0.027], [2.2, 0.02]],
  gMax: 9, gMin: -3, rollRate: 240, yawBeta: 7, airbrakeCd: 0.07, hp: 120, rcsFront: 4, rcsSide: 12,
  gearHeight: 2.25, tailStrike: 12, rotateIas: 64,
  hitboxes: [
    [[0, 0.5, 0], [1.4, 9.5, 0.9]], [[0, -1.2, 0.4], [6.5, 2.8, 0.35]],
    [[0, -7.6, 0], [4.3, 1.6, 0.3]], [[0, -7.0, 1.8], [1.6, 1.8, 1.6]],
  ],
  gun: M61A1, gunPos: [1.35, 1.60, 0.75], radar: APG82, cm: ALE47,
  stations: {
    1: [-4.55, -2.45, -0.24], 2: [-2.82, -1.54, -0.27], 3: [-2.28, -1.54, -0.27],
    4: [-1.45, 1.15, -1.08], 5: [-1.45, -0.45, -0.77], 6: [-1.40, -2.05, -0.80],
    7: [1.40, -2.05, -0.80], 8: [1.45, -0.45, -0.77], 9: [1.45, 1.15, -1.08],
    10: [2.28, -1.54, -0.27], 11: [2.82, -1.54, -0.27], 12: [4.55, -2.45, -0.24],
  },
  pylons: {
    1: ['AIM-9M', 'AIM-120A'], 2: ['AIM-9M', 'AIM-120A'], 3: ['AIM-9M', 'AIM-120A'], 10: ['AIM-9M', 'AIM-120A'],
    11: ['AIM-9M', 'AIM-120A'], 12: ['AIM-9M', 'AIM-120A'],
    4: ['AIM-120A'], 5: ['AIM-120A'], 6: ['AIM-120A'], 7: ['AIM-120A'], 8: ['AIM-120A'], 9: ['AIM-120A'],
  },
  prefer: { 'AIM-120A': [4, 9, 5, 8, 6, 7, 1, 12, 3, 10, 2, 11], 'AIM-9M': [2, 11, 3, 10, 1, 12] },
  loadouts: {
    default: { 2: 'AIM-9M', 11: 'AIM-9M', 3: 'AIM-9M', 10: 'AIM-9M', 4: 'AIM-120A', 9: 'AIM-120A', 5: 'AIM-120A', 8: 'AIM-120A' },
  },
  firingOrder: [12, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6],
};

// F-15 ACTIVE (NASA, 1993-99): an F-15B with canards and pitch/yaw thrust-vectoring nozzles on two
// F100-PW-229 engines.  The same Eagle model, re-tuned: no conformal tanks (lighter, less drag, less fuel),
// the -229's thrust (2 x 79 / 2 x 129 kN), canards for more lift, and thrust vectoring on Tab like the F-16.
export const F15A = {
  ...F15EX, id: 'f15a', name: 'F-15 ACTIVE (NASA)', short: 'F-15 ACTIVE', callsign: 'Active',
  emptyMass: 12900, internalFuel: 6100, thrustDry: 158000, thrustAb: 258000, fuelFlowDry: 3.3, fuelFlowAb: 14.8,
  cd0: 0.0198, clMax: 1.85, alphaStall: 34, alphaLimit: 32, rollRate: 270, hp: 110,
  tvc: { vector: 20, alphaNormal: 34, alphaPostStall: 85, rollRate: 300, pitchRate: 2.5, thrustScale: 1.12,
    kScale: 0.75, clMax: 2.5, lowSpeedAuthority: 0.7 },
  loadouts: { default: { 2: 'AIM-9M', 11: 'AIM-9M', 3: 'AIM-9M', 10: 'AIM-9M', 4: 'AIM-120A', 9: 'AIM-120A' } },
};

// F-35A Lightning II: one F135 (125 / 191 kN), 9 G, stealthy, weapons inside (4 AIM-120 in the bays, two
// AIM-9X on the bay doors' outer stations), the GAU-22/A 25 mm gun in the left shoulder (182 rounds).
// Numbers: USAF fact sheet, Lockheed Martin.
export const F35A = {
  ...F15EX, id: 'f35', model: 'f35', name: 'F-35A Lightning II', short: 'F-35A', callsign: 'Lightning', nation: 'us', internal: true,
  mfdLayout: 'fa18', bays: undefined, tvc: undefined,
  emptyMass: 13290, internalFuel: 8278, wingArea: 42.7, wingSpan: 10.7, length: 15.67,
  engines: 1, thrustDry: 125000, thrustAb: 191000, fuelFlowDry: 2.5, fuelFlowAb: 10.5,
  clAlpha: 3.6, clMax: 1.7, alphaStall: 32, alphaLimit: 28, cd0: 0.021, kInduced: 0.12, pylonCd: 0,
  gMax: 9, gMin: -3, rollRate: 220, hp: 110, rcsFront: 0.1, rcsSide: 1, gearHeight: 2.05, tailStrike: 12, rotateIas: 66,
  hitboxes: [[[0, 0, 0], [1.4, 7.8, 0.85]], [[0, -1.5, 0.1], [5.35, 2.4, 0.3]], [[0, -5.5, 1.0], [3.3, 1.4, 1.3]]],
  gun: { ...M61A1, name: 'GAU-22/A', rateRpm: 3300, ammo: 182, muzzle: 1040, damage: 15 }, gunPos: [-0.85, 0.6, 0.95],
  radar: { ...APG77, name: 'AN/APG-81', rwrSymbol: 'LT' },
  stations: { 1: [-0.8, 0.5, -0.6], 2: [0.8, 0.5, -0.6], 3: [-0.8, -1.5, -0.6], 4: [0.8, -1.5, -0.6], 5: [-1.6, 0.0, -0.4], 6: [1.6, 0.0, -0.4] },
  pylons: { 5: ['AIM-9M'], 6: ['AIM-9M'], 1: ['AIM-120A'], 2: ['AIM-120A'], 3: ['AIM-120A'], 4: ['AIM-120A'] },
  prefer: { 'AIM-120A': [1, 2, 3, 4], 'AIM-9M': [5, 6] },
  loadouts: { default: { 5: 'AIM-9M', 6: 'AIM-9M', 1: 'AIM-120A', 2: 'AIM-120A', 3: 'AIM-120A', 4: 'AIM-120A' } },
  firingOrder: [5, 6, 1, 2, 3, 4],
};

// ---------------------------------------------------------------- built in code (proc.js)
// Trainers of the career.  Sources: USAF and US Navy fact sheets (T-6A: PT6A-68, 1,100 shp, 320 mph, +7/-3.5 G;
// T-38C: 2 x J85-GE-5, 2,050 / 2,900 lbf, Mach 1.08, +7.33 G; T-45C: F405-RR-401, 5,527 lbf, ~M0.85, carrier
// capable).  No weapons: gun without ammunition, no stations, no flares, a radar that sees nothing.
const NO_RADAR = { ...APG68, name: '-', searchRange: 1, lockRange: 1, acmRange: 1, rwrSymbol: 'T' };
const NO_STORES = { stations: {}, pylons: {}, prefer: { 'AIM-120A': [], 'AIM-9M': [] }, loadouts: { default: {} }, firingOrder: [] };
const TRAINER = { gun: { ...M61A1, ammo: 0 }, radar: NO_RADAR, cm: { ...ALE47, flares: 0, chaff: 0 }, trainer: true, noAB: true, mfdLayout: 'fa18', ...NO_STORES };
export const T6A = {
  ...TRAINER, id: 't6', model: 't6', proc: true, name: 'T-6A Texan II', short: 'T-6A', callsign: 'Texan',
  emptyMass: 2140, internalFuel: 500, wingArea: 16.3, wingSpan: 10.2, length: 10.2,
  // turboprop: the jet model's thrust stands in for the propeller's (tuned for ~520 km/h at sea level)
  engines: 1, thrustDry: 9800, thrustAb: 9800, fuelFlowDry: 0.09, fuelFlowAb: 0.09,
  clAlpha: 4.8, clMax: 1.55, alphaStall: 18, alphaLimit: 16, cd0: 0.034, kInduced: 0.055, pylonCd: 0,
  waveDrag: [[0, 0], [0.55, 0], [0.62, 0.012], [0.7, 0.05], [0.8, 0.12]],
  gMax: 7, gMin: -3.5, rollRate: 170, yawBeta: 5, airbrakeCd: 0.04, hp: 60, rcsFront: 2, rcsSide: 4,
  gearHeight: 1.62, tailStrike: 14, rotateIas: 42,
  hitboxes: [[[0, 0, 0], [0.6, 5, 0.75]], [[0, 0.2, -0.35], [5.1, 1.0, 0.2]], [[0, -4.5, 0.6], [2.4, 0.6, 1.0]]],
  gunPos: [0, 4, -0.3],
};
export const T38C = {
  ...TRAINER, id: 't38', model: 't38', proc: true, name: 'T-38C Talon', short: 'T-38C', callsign: 'Talon', noAB: false,
  emptyMass: 3270, internalFuel: 1760, wingArea: 15.8, wingSpan: 7.7, length: 14.1,
  engines: 2, thrustDry: 23800, thrustAb: 34200, fuelFlowDry: 0.55, fuelFlowAb: 2.2,
  clAlpha: 3.6, clMax: 1.25, alphaStall: 22, alphaLimit: 19, cd0: 0.0165, kInduced: 0.13, pylonCd: 0,
  waveDrag: [[0, 0], [0.86, 0], [0.92, 0.008], [0.98, 0.03], [1.05, 0.045], [1.2, 0.046], [1.5, 0.04]],
  gMax: 7.33, gMin: -2.9, rollRate: 420, yawBeta: 6, airbrakeCd: 0.05, hp: 70, rcsFront: 1, rcsSide: 3,
  gearHeight: 1.49, tailStrike: 12, rotateIas: 70,
  hitboxes: [[[0, 0, 0], [0.7, 7, 0.65]], [[0, -2, -0.25], [3.85, 1.6, 0.15]], [[0, -5.6, 1.2], [2.3, 1.0, 1.4]]],
  gunPos: [0, 5, -0.2],
};
export const T45C = {
  ...TRAINER, id: 't45', model: 't45', proc: true, name: 'T-45C Goshawk', short: 'T-45C', callsign: 'Goshawk', carrier: true,
  emptyMass: 4460, internalFuel: 1310, wingArea: 17.7, wingSpan: 9.4, length: 12.0,
  engines: 1, thrustDry: 24600, thrustAb: 24600, fuelFlowDry: 0.6, fuelFlowAb: 0.6,
  clAlpha: 4.2, clMax: 1.5, alphaStall: 24, alphaLimit: 22, cd0: 0.0195, kInduced: 0.1, pylonCd: 0,
  waveDrag: [[0, 0], [0.76, 0], [0.82, 0.008], [0.88, 0.035], [0.95, 0.08]],
  gMax: 7.33, gMin: -3, rollRate: 220, yawBeta: 6, airbrakeCd: 0.06, hp: 75, rcsFront: 1.5, rcsSide: 4,
  gearHeight: 1.8, tailStrike: 13, rotateIas: 56,
  hitboxes: [[[0, 0, 0], [0.7, 6, 0.75]], [[0, -0.6, -0.35], [4.7, 1.6, 0.2]], [[0, -4.9, 1.2], [2.3, 0.9, 1.4]]],
  gunPos: [0, 4, -0.4],
};

// The Sukhois (the enemy of the WW3 campaign, flyable in free play too).  Su-35S: 2 x AL-41F1S, 2 x 86.3 /
// 2 x 142 kN, 3-D thrust vectoring, 9 G, Mach 2.25; Su-57: 2 x AL-41F1, 2 x 88 / 2 x 147 kN, stealthy shape,
// weapons inside.  Missiles: R-73 (IR) and R-77 (active radar) - the game's AIM-9M / AIM-120A stations.
const SU_GUN = { ...M61A1, name: 'GSh-30-1', rateRpm: 1650, ammo: 150, muzzle: 860, damage: 16, dispersionMrad: 2.0 };
export const SU35 = {
  ...F15EX, id: 'su35', model: 'su35', proc: true, name: 'Su-35S Flanker-E', short: 'Su-35', callsign: 'Flanker', mfdLayout: 'fa18',
  emptyMass: 18400, internalFuel: 11500, wingArea: 62, wingSpan: 15.3, length: 21.9,
  engines: 2, thrustDry: 172600, thrustAb: 284000, fuelFlowDry: 3.6, fuelFlowAb: 15.5,
  clAlpha: 3.8, clMax: 1.9, alphaStall: 32, alphaLimit: 28, cd0: 0.022, kInduced: 0.12, pylonCd: 0.0012,
  gMax: 9, gMin: -3, rollRate: 260, hp: 130, rcsFront: 10, rcsSide: 20, gearHeight: 2.95, tailStrike: 13, rotateIas: 72,
  hitboxes: [[[0, 0, 0], [1.6, 10.5, 1.0]], [[0, -3.5, 0.1], [7.6, 2.4, 0.3]], [[0, -9, 1.6], [4.6, 1.2, 2.2]]],
  gun: SU_GUN, gunPos: [1.0, 5.5, 0.3], radar: { ...APG82, name: 'N035 Irbis-E', rwrSymbol: '35' },
  tvc: { vector: 15, alphaNormal: 32, alphaPostStall: 90, rollRate: 320, pitchRate: 2.5, thrustScale: 1.1, kScale: 0.8, clMax: 2.5, lowSpeedAuthority: 0.7 },
  // the store_N points of the Blender model (assets/su35.glb)
  stations: { 1: [-7.23, -3.80, -0.37], 2: [-5.30, -2.39, -0.68], 3: [-3.70, -1.47, -0.63], 4: [-1.25, -0.65, -1.41], 5: [1.25, -0.65, -1.41], 6: [3.70, -1.47, -0.63], 7: [5.30, -2.39, -0.68], 8: [7.23, -3.80, -0.37] },
  pylons: { 1: ['AIM-9M'], 8: ['AIM-9M'], 2: ['AIM-9M', 'AIM-120A'], 7: ['AIM-9M', 'AIM-120A'], 3: ['AIM-9M', 'AIM-120A'], 6: ['AIM-9M', 'AIM-120A'], 4: ['AIM-120A'], 5: ['AIM-120A'] },
  prefer: { 'AIM-120A': [4, 5, 3, 6, 2, 7], 'AIM-9M': [1, 8, 2, 7, 3, 6] },
  loadouts: { default: { 1: 'AIM-9M', 8: 'AIM-9M', 2: 'AIM-9M', 7: 'AIM-9M', 3: 'AIM-120A', 6: 'AIM-120A', 4: 'AIM-120A', 5: 'AIM-120A' } },
  firingOrder: [1, 8, 2, 7, 3, 6, 4, 5], bays: undefined,
};
export const SU57 = {
  ...SU35, id: 'su57', model: 'su57', name: 'Su-57 Felon', short: 'Su-57', callsign: 'Felon', internal: true,
  emptyMass: 18000, internalFuel: 10300, wingArea: 78.8, wingSpan: 14.1, length: 20.1,
  thrustDry: 176000, thrustAb: 294000, cd0: 0.0205, rcsFront: 0.25, rcsSide: 1.5, hp: 125, gearHeight: 2.93,
  radar: { ...APG77, name: 'N036 Byelka', rwrSymbol: '57' },
  hitboxes: [[[0, 0, 0], [1.6, 9.8, 0.9]], [[0, -3.0, 0.1], [7.0, 2.6, 0.3]], [[0, -8.5, 0.8], [5.3, 1.2, 1.6]]],
  stations: { 1: [-0.8, 1.0, -0.5], 2: [0.8, 1.0, -0.5], 3: [-0.8, -1.5, -0.5], 4: [0.8, -1.5, -0.5], 5: [-2.6, 1.8, -0.2], 6: [2.6, 1.8, -0.2] },
  pylons: { 5: ['AIM-9M'], 6: ['AIM-9M'], 1: ['AIM-120A'], 2: ['AIM-120A'], 3: ['AIM-120A'], 4: ['AIM-120A'] },
  prefer: { 'AIM-120A': [1, 2, 3, 4], 'AIM-9M': [5, 6] },
  loadouts: { default: { 5: 'AIM-9M', 6: 'AIM-9M', 1: 'AIM-120A', 2: 'AIM-120A', 3: 'AIM-120A', 4: 'AIM-120A' } },
  firingOrder: [5, 6, 1, 2, 3, 4],
};
// More jets built in code: two MiGs, the European canard deltas and the Chinese J-20.  Numbers from the makers'
// and air forces' published data (empty mass, internal fuel, wing area, engines dry / with afterburner, G limit).
// stations: wing tips (IR only), two under each wing (both), two under the fuselage (radar missiles)
function std(tip, mid, inn, fus) {
  const m = (p) => [-p[0], p[1], p[2]];
  return {
    stations: { 1: m(tip), 2: m(mid), 3: m(inn), 4: m(fus), 5: fus, 6: inn, 7: mid, 8: tip },
    pylons: { 1: ['AIM-9M'], 8: ['AIM-9M'], 2: ['AIM-9M', 'AIM-120A'], 7: ['AIM-9M', 'AIM-120A'], 3: ['AIM-9M', 'AIM-120A'], 6: ['AIM-9M', 'AIM-120A'], 4: ['AIM-120A'], 5: ['AIM-120A'] },
    prefer: { 'AIM-120A': [4, 5, 3, 6, 2, 7], 'AIM-9M': [1, 8, 2, 7, 3, 6] },
    loadouts: { default: { 1: 'AIM-9M', 8: 'AIM-9M', 2: 'AIM-9M', 7: 'AIM-9M', 3: 'AIM-120A', 6: 'AIM-120A', 4: 'AIM-120A', 5: 'AIM-120A' } },
    firingOrder: [1, 8, 2, 7, 3, 6, 4, 5],
  };
}
const boxes = (L, span) => [[[0, 0, 0], [1.0, L / 2, 0.8]], [[0, -L * 0.15, 0], [span / 2, L * 0.15, 0.25]], [[0, -L * 0.42, 1.4], [span * 0.25, L * 0.08, 1.4]]];
const jet = (base, o) => ({ ...base, proc: true, mfdLayout: 'fa18', bays: undefined, tvc: undefined, tvcAlways: undefined, ...o,
  hitboxes: boxes(o.length, o.wingSpan) });
const WAVE = [[0, 0], [0.8, 0], [0.88, 0.004], [0.95, 0.018], [1.0, 0.03], [1.05, 0.035], [1.2, 0.037], [1.6, 0.027], [2.2, 0.02]];
export const MIG29 = jet(F16C, {
  id: 'mig29', model: 'mig29', name: 'MiG-29 Fulcrum', short: 'MiG-29', callsign: 'Fulcrum', nation: 'ru',
  emptyMass: 11000, internalFuel: 3400, wingArea: 38, wingSpan: 11.36, length: 17.32,
  engines: 2, thrustDry: 98800, thrustAb: 162800, fuelFlowDry: 2.2, fuelFlowAb: 9.5,
  clAlpha: 3.9, clMax: 1.8, alphaStall: 30, alphaLimit: 26, cd0: 0.021, kInduced: 0.12, waveDrag: WAVE,
  gMax: 9, rollRate: 250, hp: 100, rcsFront: 5, rcsSide: 12, gearHeight: 2.72, tailStrike: 13, rotateIas: 65,
  gun: SU_GUN, gunPos: [-1.0, 4.5, 0.2], radar: { ...APG68, name: 'N019', rwrSymbol: '29' },
  ...std([4.65, -2.48, -0.63], [3.6, -1.91, -0.61], [2.55, -1.30, -0.59], [1.0, -0.85, -1.13]),
});
export const MIG31 = jet(F15EX, {
  id: 'mig31', model: 'mig31', name: 'MiG-31 Foxhound', short: 'MiG-31', callsign: 'Foxhound', nation: 'ru',
  emptyMass: 21820, internalFuel: 14000, wingArea: 61.6, wingSpan: 13.46, length: 22.69,
  engines: 2, thrustDry: 186000, thrustAb: 304000, fuelFlowDry: 4.2, fuelFlowAb: 20,
  clAlpha: 3.4, clMax: 1.3, alphaStall: 20, alphaLimit: 18, cd0: 0.024, kInduced: 0.14,
  waveDrag: [[0, 0], [0.85, 0], [0.95, 0.02], [1.05, 0.03], [1.5, 0.025], [2.5, 0.018], [2.9, 0.02]],
  gMax: 5, gMin: -2, rollRate: 150, hp: 140, rcsFront: 15, rcsSide: 25, gearHeight: 2.88, tailStrike: 12, rotateIas: 80,
  gun: { ...SU_GUN, name: 'GSh-6-23', rateRpm: 8000, ammo: 260, damage: 10 }, gunPos: [1.2, 1.0, -0.5],
  radar: { ...APG82, name: 'Zaslon-M', searchRange: 160000, lockRange: 110000, rwrSymbol: '31' },
  ...std([5.6, -3.21, -0.01], [4.3, -2.58, 0.09], [3.1, -1.96, 0.18], [1.2, -3.05, -0.83]),
});
export const GRIPEN = jet(F16C, {
  id: 'gripen', model: 'gripen', name: 'JAS 39 Gripen C', short: 'Gripen', callsign: 'Gripen', nation: 'se',
  emptyMass: 6800, internalFuel: 2400, wingArea: 30, wingSpan: 8.4, length: 14.1,
  engines: 1, thrustDry: 54000, thrustAb: 80500, fuelFlowDry: 1.2, fuelFlowAb: 5.5,
  clAlpha: 3.6, clMax: 1.7, alphaStall: 28, alphaLimit: 26, cd0: 0.019, kInduced: 0.14, waveDrag: WAVE,
  gMax: 9, rollRate: 280, hp: 85, rcsFront: 0.6, rcsSide: 4, gearHeight: 1.77, tailStrike: 13, rotateIas: 62,
  gun: { ...M61A1, name: 'BK 27', rateRpm: 1700, ammo: 120, muzzle: 1025, damage: 15 }, gunPos: [-0.6, 1.0, -0.4],
  radar: { ...APG68, name: 'PS-05/A', searchRange: 90000, lockRange: 65000, rwrSymbol: 'GR' },
  ...std([4.08, -3.90, -0.21], [3.0, -2.92, -0.57], [1.9, -2.27, -0.57], [0.55, -1.55, -0.61]),
});
export const TYPHOON = jet(F15EX, {
  id: 'typhoon', model: 'typhoon', name: 'Eurofighter Typhoon', short: 'Typhoon', callsign: 'Typhoon', nation: 'uk',
  emptyMass: 11000, internalFuel: 5000, wingArea: 51.2, wingSpan: 10.95, length: 15.96,
  engines: 2, thrustDry: 120000, thrustAb: 180000, fuelFlowDry: 2.4, fuelFlowAb: 9,
  clAlpha: 3.7, clMax: 1.9, alphaStall: 32, alphaLimit: 28, cd0: 0.019, kInduced: 0.12, waveDrag: WAVE,
  gMax: 9, rollRate: 280, hp: 100, rcsFront: 0.5, rcsSide: 4, gearHeight: 2.12, tailStrike: 13, rotateIas: 62,
  gun: { ...M61A1, name: 'BK 27', rateRpm: 1700, ammo: 150, muzzle: 1025, damage: 15 }, gunPos: [0.8, 1.0, -0.3],
  radar: { ...APG79, name: 'Captor-E', rwrSymbol: 'EF' },
  ...std([5.48, -4.95, -0.2], [4.0, -3.54, -0.59], [2.6, -2.53, -0.61], [0.6, -0.55, -0.66]),
});
export const RAFALE = jet(F15EX, {
  id: 'rafale', model: 'rafale', name: 'Dassault Rafale C', short: 'Rafale', callsign: 'Rafale', nation: 'fr',
  emptyMass: 10300, internalFuel: 4700, wingArea: 45.7, wingSpan: 10.9, length: 15.27,
  engines: 2, thrustDry: 100000, thrustAb: 150000, fuelFlowDry: 2.1, fuelFlowAb: 8,
  clAlpha: 3.7, clMax: 1.9, alphaStall: 32, alphaLimit: 29, cd0: 0.019, kInduced: 0.12, waveDrag: WAVE,
  gMax: 9, rollRate: 270, hp: 95, rcsFront: 1, rcsSide: 5, gearHeight: 2.02, tailStrike: 13, rotateIas: 60,
  gun: { ...M61A1, name: 'GIAT 30', rateRpm: 2500, ammo: 125, muzzle: 1025, damage: 16 }, gunPos: [0.9, 0.8, -0.3],
  radar: { ...APG79, name: 'RBE2 AA', rwrSymbol: 'RF' },
  ...std([5.48, -4.68, -0.22], [3.9, -3.42, -0.56], [2.5, -2.62, -0.54], [0.75, -2.05, -0.55]),
});
export const J20 = jet(F15EX, {
  id: 'j20', model: 'j20', name: 'Chengdu J-20', short: 'J-20', callsign: 'Mighty Dragon', nation: 'cn', internal: true,
  emptyMass: 17000, internalFuel: 10000, wingArea: 73, wingSpan: 13.5, length: 20.4,
  engines: 2, thrustDry: 178000, thrustAb: 284000, fuelFlowDry: 3.6, fuelFlowAb: 15,
  clAlpha: 3.7, clMax: 1.8, alphaStall: 30, alphaLimit: 26, cd0: 0.020, kInduced: 0.12, waveDrag: WAVE,
  gMax: 9, rollRate: 230, hp: 120, rcsFront: 0.2, rcsSide: 1.5, gearHeight: 2.5, tailStrike: 13, rotateIas: 72,
  gun: SU_GUN, gunPos: [1.0, 4.0, 0.0], radar: { ...APG77, name: 'KLJ-5', rwrSymbol: '20' },
  ...std([1.6, 1.5, -0.6], [1.0, 0.5, -0.6], [1.0, -1.5, -0.6], [0.5, -3.0, -0.6]),
});

// the missiles under their own names (the game's AIM-9M / AIM-120A stations: IR and active radar)
const NAMES = { ru: ['R-73', 'R-77'], se: ['IRIS-T', 'Meteor'], uk: ['ASRAAM', 'Meteor'], fr: ['MICA IR', 'MICA EM'], cn: ['PL-10', 'PL-15'] };
export const WEAPON_CLASS = {};
for (const [ir, arh] of Object.values(NAMES)) { WEAPON_CLASS[ir] = 'AIM-9M'; WEAPON_CLASS[arh] = 'AIM-120A'; }
const named = (set, n) => (n ? { 'AIM-9M': { ...set['AIM-9M'], name: n[0] }, 'AIM-120A': { ...set['AIM-120A'], name: n[1] } } : set);
export function missilesFor(spec, enemy) {
  const n = NAMES[spec.nation || (spec.id && spec.id.startsWith('su') ? 'ru' : '')];
  return named(enemy ? BANDIT_MISSILES : PLAYER_MISSILES, n);
}
export const RU_MISSILES = named(BANDIT_MISSILES, NAMES.ru);
export const RU_PLAYER_MISSILES = named(PLAYER_MISSILES, NAMES.ru);

export const AIRCRAFT = { f16: F16C, fa18: FA18E, f22: F22A, f15: F15EX, f15a: F15A, f35: F35A, su35: SU35, su57: SU57,
  mig29: MIG29, mig31: MIG31, gripen: GRIPEN, typhoon: TYPHOON, rafale: RAFALE, j20: J20 };
// the menu's picker: groups of jets
export const PLANE_GROUPS = [
  ['USA', ['f16', 'fa18', 'f15', 'f22', 'f35', 'f15a']], ['Oroszország', ['su35', 'su57', 'mig29', 'mig31']],
  ['Európa', ['gripen', 'typhoon', 'rafale']], ['Kína', ['j20']], ['Gyakorlógépek', ['t6', 't38', 't45']],
];
export const TRAINERS = { t6: T6A, t38: T38C, t45: T45C };

// the enemies fly the same jets with a weaker airframe: less G, slower roll, lower angle of attack limit
export const BANDITS = {
  f16: { ...F16C, name: 'F-16C (ellenfél)', gMax: 7, rollRate: 190, alphaLimit: 20 },
  fa18: { ...FA18E, name: 'F/A-18E (ellenfél)', gMax: 6.3, rollRate: 150, alphaLimit: 28 },
  f22: { ...F22A, name: 'F-22A (ellenfél)', gMax: 6.8, rollRate: 190, tvcAlways: false, tvc: undefined },
  f15: { ...F15EX, name: 'F-15EX (ellenfél)', gMax: 7, rollRate: 180, alphaLimit: 22 },
  su35: { ...SU35, name: 'Su-35 (ellenség)', gMax: 7.5, rollRate: 200, alphaLimit: 24, tvc: undefined },
  su57: { ...SU57, name: 'Su-57 (ellenség)', gMax: 7.2, rollRate: 200, alphaLimit: 24, tvc: undefined },
  mig29: { ...MIG29, gMax: 7.2, rollRate: 190, alphaLimit: 22 },
  mig31: { ...MIG31, gMax: 4.5, rollRate: 120 },
  gripen: { ...GRIPEN, gMax: 7.2, rollRate: 210, alphaLimit: 22 },
  typhoon: { ...TYPHOON, gMax: 7.4, rollRate: 210, alphaLimit: 24 },
  rafale: { ...RAFALE, gMax: 7.4, rollRate: 210, alphaLimit: 24 },
  j20: { ...J20, gMax: 7, rollRate: 180, alphaLimit: 22 },
  f35: { ...F35A, name: 'F-35A (ellenfél)', gMax: 7.2, rollRate: 190, alphaLimit: 24 },
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
