// Career: what the player did over every match, kept in this browser (localStorage), plus the score of the
// running match and the medals (achievements).  Nothing here touches the simulation.
const KEY = 'dogfight-career';

export const ACHIEVEMENTS = [
  { id: 'first', name: 'Első győzelem', desc: 'Lőj le egy ellenséget' },
  { id: 'guns', name: 'Közelharcos', desc: 'Lelövés gépágyúval' },
  { id: 'fox2', name: 'Fox 2!', desc: 'Lelövés AIM-9M hőkövetővel' },
  { id: 'fox3', name: 'Fox 3!', desc: 'Lelövés AIM-120A-val' },
  { id: 'maneuver', name: 'Manőverkill', desc: 'Az üldözött ellenség a földbe csapódik' },
  { id: 'ace', name: 'Ász', desc: '5 lelövés egyetlen életen belül' },
  { id: 'evade', name: 'Kicselezve', desc: 'Kerülj ki egy rád kilőtt rakétát' },
  { id: 'cobra', name: 'Kobra', desc: 'Rázz le egy rakétát Cobra manőverrel (F-16 extrém mód)' },
  { id: 'home', name: 'Hazaértem', desc: 'Szállj le a bázison, és fegyverezz újra' },
  { id: 'wave5', name: 'Kitartó', desc: 'Érd el az 5. hullámot' },
  { id: 'stealth', name: 'Raptor-vadász', desc: 'Lőj le egy F-22A-t' },
  { id: 'duel3', name: 'Párbajhős', desc: 'Nyerj 3 párbajt egymás után' },
  { id: 'survivor', name: 'Túlélő', desc: 'Túlélés módban érd el a 4. hullámot' },
  { id: 'veteran', name: 'Veterán', desc: 'Lelövés Nehéz vagy Ász fokozaton' },
  { id: 'team', name: 'Csapatjátékos', desc: 'A kísérőd lelő egy ellenséget' },
  { id: 'score5k', name: 'Ötezres', desc: 'Szerezz 5000 pontot egy játékban' },
];

const FRESH = () => ({
  matches: 0, kills: 0, deaths: 0, gunKills: 0, irKills: 0, arhKills: 0, crashKills: 0, missilesFired: 0,
  flightTime: 0, bestScore: 0, bestWave: 0, bestStreak: 0, bestSurvival: 0, duelWins: 0, perPlane: {}, medals: {},
});

export class Career {
  constructor() {
    this.data = FRESH();
    try { Object.assign(this.data, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* private mode */ }
    this.dirty = false; this.saveTimer = 0;
  }
  save() {
    this.dirty = false;
    try { localStorage.setItem(KEY, JSON.stringify(this.data)); } catch (e) { /* private mode, full */ }
  }
  // flight time ticks every frame: write it out now and then, not every frame
  tick(dt) {
    this.data.flightTime += dt;
    this.saveTimer += dt;
    if (this.saveTimer > 10) { this.saveTimer = 0; this.save(); }
  }
  reset() { this.data = FRESH(); this.save(); }
  has(id) { return !!this.data.medals[id]; }
  // returns the achievement when it is new
  award(id) {
    if (this.has(id)) return null;
    const a = ACHIEVEMENTS.find((x) => x.id === id);
    if (!a) return null;
    this.data.medals[id] = Date.now();
    this.save();
    return a;
  }
  best(key, value) { if (value > (this.data[key] || 0)) { this.data[key] = value; this.dirty = true; } }
}

// points for a kill: by weapon, times the difficulty, plus a bonus for a streak (kills in one life)
export const DIFF_MULT = { easy: 0.6, normal: 1, hard: 1.5, ace: 2 };
export function killPoints(weapon, difficulty, streak) {
  const base = weapon === 'crash' ? 120 : weapon === 'AIM-9M' ? 100 : weapon === 'AIM-120A' ? 80 : 150;
  const streakMult = 1 + Math.min(4, Math.max(0, streak - 1)) * 0.25;
  return Math.round(base * (DIFF_MULT[difficulty] || 1) * streakMult);
}
export const isGun = (weapon) => !!weapon && !['AIM-9M', 'AIM-120A', 'crash', 'tailstrike'].includes(weapon);
export function weaponLabel(weapon) {
  if (weapon === 'crash') return 'MANŐVER';
  if (weapon === 'AIM-9M' || weapon === 'AIM-120A') return weapon;
  return 'ÁGYÚ';
}

export function formatTime(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h} ó ${m} p` : `${m} perc`;
}
