// F-16C Block 50 / AIM-9M / AIM-120A / M61A1 / APG-68 data (same numbers as dogfight/sim/specs.py).
export const IR = 'IR', ARH = 'ARH';

export const M61A1 = {
  name: 'M61A1', rateRpm: 6000, ammo: 511, muzzle: 1050, dragK: 3.7e-4, dispersionMrad: 1.6,
  damage: 9, life: 3.0, maxLeadRange: 1800,
};

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

export const APG68 = {
  name: 'AN/APG-68(V)9', searchRange: 74000, scanAz: 60, scanEl: 12, scanRate: 120, sttGimbal: 60,
  lockRange: 55000, acmRange: 16000, acmAz: 6, acmElLow: -6, acmElHigh: 40, lockTime: 0.5,
  notchSpeed: 25, trackMemory: 0.6, rwrSymbol: '16',
};

export const ALE47 = { flares: 30, chaff: 30, flareIntensity: 3.0, flareLife: 4.0, chaffLife: 5.0, interval: 0.35 };

export const F16C = {
  name: 'F-16C Block 50', emptyMass: 8900, internalFuel: 3200, wingArea: 27.87, wingSpan: 9.96, length: 15.06,
  thrustDry: 76300, thrustAb: 131600, fuelFlowDry: 1.35, fuelFlowAb: 6.2,
  clAlpha: 4.1, clMax: 1.8, alphaStall: 30, alphaLimit: 25, cd0: 0.0205, kInduced: 0.118,
  waveDrag: [[0, 0], [0.8, 0], [0.88, 0.004], [0.95, 0.018], [1.0, 0.03], [1.05, 0.035], [1.2, 0.037], [1.6, 0.027], [2.2, 0.02]],
  gMax: 9, gMin: -3, rollRate: 270, yawBeta: 6, airbrakeCd: 0.06, hp: 100, rcsFront: 1.5, rcsSide: 6,
  hitboxes: [
    [[0, 0, 0], [0.95, 7.5, 1.05]], [[0, -1.0, 0.1], [4.9, 2.4, 0.35]],
    [[0, -5.6, 0.2], [2.8, 1.3, 0.3]], [[0, -5.4, 2.0], [0.3, 1.5, 1.3]],
  ],
  gun: M61A1, radar: APG68, cm: ALE47,
  stations: {
    1: [-4.88, -0.55, 0.10], 2: [-3.75, -0.95, -0.38], 3: [-2.60, -0.55, -0.45],
    7: [2.60, -0.55, -0.45], 8: [3.75, -0.95, -0.38], 9: [4.88, -0.55, 0.10],
  },
  loadouts: {
    default: { 1: 'AIM-9M', 9: 'AIM-9M', 2: 'AIM-9M', 8: 'AIM-9M', 3: 'AIM-120A', 7: 'AIM-120A' },
  },
};
export const FIRING_ORDER = [9, 1, 8, 2, 7, 3];
