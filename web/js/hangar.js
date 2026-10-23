// Hangar: credits earned in the air (1 point = 1 credit) and what they buy - a new jet, paint schemes,
// engine-room upgrades and mods.  Kept in this browser like the career; the whole save (settings, menu,
// career, hangar) can be downloaded to a file and loaded back on another device.
const KEY = 'dogfight-hangar';
export const START_CREDITS = 500;

// paint schemes: a tint (multiplies the factory paint), a glow added on top, and the finish
export const SKINS = [
  { id: 'factory', name: 'Gyári festés', price: 0, color: 0xffffff, emissive: 0x000000, metal: null, rough: null },
  { id: 'desert', name: 'Sivatagi agresszor', price: 400, color: 0xe2c08c, emissive: 0x1a1006, metal: null, rough: null },
  { id: 'navy', name: 'Tengerész kék', price: 400, color: 0x8fb0e8, emissive: 0x020814, metal: null, rough: null },
  { id: 'arctic', name: 'Sarkvidéki fehér', price: 500, color: 0xffffff, emissive: 0x3a3e44, metal: null, rough: 0.5 },
  { id: 'forest', name: 'Erdei zöld', price: 500, color: 0x9ab88a, emissive: 0x040a02, metal: null, rough: null },
  { id: 'night', name: 'Éjfekete', price: 700, color: 0x45474e, emissive: 0x000000, metal: 0.3, rough: 0.35 },
  { id: 'red', name: 'Vörös ördög', price: 800, color: 0xe06a5c, emissive: 0x1c0300, metal: null, rough: 0.45 },
  { id: 'purple', name: 'Lila villám', price: 800, color: 0xb490f0, emissive: 0x0c0418, metal: null, rough: 0.45 },
  { id: 'gold', name: 'Arany ász', price: 2500, color: 0xf0c860, emissive: 0x2a1800, metal: 0.85, rough: 0.28 },
  { id: 'chrome', name: 'Króm', price: 3000, color: 0xe8eef4, emissive: 0x101418, metal: 1.0, rough: 0.12 },
];

// engine room: each level costs more; what a level gives is in `per`
export const UPGRADES = [
  { id: 'engine', name: 'Hajtómű-tuning', desc: '+5% tolóerő szintenként', per: 0.05, prices: [600, 1400, 3000] },
  { id: 'armor', name: 'Páncélzat', desc: '+20 életerő szintenként', per: 20, prices: [500, 1200, 2500] },
  { id: 'cm', name: 'Nagyobb ALE-47', desc: '+10 flare és +10 chaff szintenként', per: 10, prices: [300, 800, 1600] },
  { id: 'ammo', name: 'Lőszertár', desc: '+25% gépágyú-lőszer szintenként', per: 0.25, prices: [300, 800, 1600] },
];

// mods: bought once, then switched on or off in the hangar
export const MODS = [
  { id: 'bullettime', name: 'Bullet time', desc: 'O gomb: 4 mp-re lelassul az idő (20 mp alatt töltődik)', price: 1500 },
  { id: 'infcm', name: 'Végtelen flare', desc: 'A flare és a chaff sosem fogy el', price: 1200 },
  { id: 'bigboom', name: 'Óriás robbanás', desc: 'A rakétáid 60%-kal nagyobb körben sebeznek', price: 1800 },
  { id: 'tracer', name: 'Lila nyomjelző', desc: 'A gépágyúd lila nyomjelzőt lő', price: 300 },
];

// jets that have to be bought (the four of the base game are free)
export const PLANES = [
  { id: 'f15a', name: 'F-15 ACTIVE (NASA)', price: 3000, desc: 'Kísérleti F-15: kacsaszárny és tolóerő-vektoros fúvócsövek. Tab = TVC: 9 G nagy állásszögben is, Cobra, 300°/s orsózás. Könnyebb, mint az F-15EX.' },
];

const FRESH = () => ({ credits: START_CREDITS, earned: 0, skins: { factory: true }, skin: 'factory', upgrades: {}, mods: {}, modsOn: {}, planes: {} });

export class Hangar {
  constructor() {
    this.data = FRESH();
    try { Object.assign(this.data, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* private mode */ }
    this.listeners = [];
  }
  save() {
    try { localStorage.setItem(KEY, JSON.stringify(this.data)); } catch (e) { /* private mode */ }
    for (const f of this.listeners) f();
  }
  onChange(f) { this.listeners.push(f); }
  earn(n) { if (n > 0) { this.data.credits += n; this.data.earned += n; this.saveSoon(); } }
  saveSoon() { clearTimeout(this.t); this.t = setTimeout(() => this.save(), 400); }
  spend(price) {
    if (this.data.credits < price) return false;
    this.data.credits -= price; return true;
  }
  buySkin(id) {
    const s = SKINS.find((x) => x.id === id);
    if (!s || this.data.skins[id] || !this.spend(s.price)) return false;
    this.data.skins[id] = true; this.data.skin = id; this.save(); return true;
  }
  equipSkin(id) { if (this.data.skins[id]) { this.data.skin = id; this.save(); } }
  level(id) { return this.data.upgrades[id] || 0; }
  buyUpgrade(id) {
    const u = UPGRADES.find((x) => x.id === id), lv = this.level(id);
    if (!u || lv >= u.prices.length || !this.spend(u.prices[lv])) return false;
    this.data.upgrades[id] = lv + 1; this.save(); return true;
  }
  buyMod(id) {
    const m = MODS.find((x) => x.id === id);
    if (!m || this.data.mods[id] || !this.spend(m.price)) return false;
    this.data.mods[id] = true; this.data.modsOn[id] = true; this.save(); return true;
  }
  toggleMod(id) { if (this.data.mods[id]) { this.data.modsOn[id] = !this.data.modsOn[id]; this.save(); } }
  modOn(id) { return !!(this.data.mods[id] && this.data.modsOn[id]); }
  ownsPlane(id) { return !PLANES.some((p) => p.id === id) || !!this.data.planes[id]; }
  buyPlane(id) {
    const p = PLANES.find((x) => x.id === id);
    if (!p || this.data.planes[id] || !this.spend(p.price)) return false;
    this.data.planes[id] = true; this.save(); return true;
  }
  get skin() { return SKINS.find((s) => s.id === this.data.skin) || SKINS[0]; }
  // the player's jet with the engine-room upgrades applied (a copy: the base spec stays as it is)
  upgraded(spec) {
    const e = 1 + this.level('engine') * 0.05, cm = this.level('cm') * 10, ammo = 1 + this.level('ammo') * 0.25;
    return {
      ...spec, thrustDry: spec.thrustDry * e, thrustAb: spec.thrustAb * e, hp: spec.hp + this.level('armor') * 20,
      cm: { ...spec.cm, flares: spec.cm.flares + cm, chaff: spec.cm.chaff + cm },
      gun: { ...spec.gun, ammo: Math.round(spec.gun.ammo * ammo) },
    };
  }
}

// the whole save in one file: every localStorage entry of the game
export function exportSave() {
  const out = { game: 'Dogfight Plus', version: 1, saved: new Date().toISOString(), data: {} };
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k && k.startsWith('dogfight-') && !k.startsWith('dogfight-backup-')) out.data[k] = localStorage.getItem(k);
  }
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `dogfight-mentes-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
// returns an error text, or null when it worked (the page reloads to pick everything up)
export async function importSave(file) {
  let j;
  try { j = JSON.parse(await file.text()); } catch (e) { return 'Ez nem egy Dogfight mentés (hibás fájl).'; }
  if (!j || j.game !== 'Dogfight Plus' || typeof j.data !== 'object') return 'Ez nem egy Dogfight mentés.';
  const keys = Object.keys(j.data).filter((k) => k.startsWith('dogfight-') && typeof j.data[k] === 'string');
  if (!keys.length) return 'A mentés üres.';
  for (const k of keys) { try { JSON.parse(j.data[k]); } catch (e) { return `Sérült bejegyzés: ${k}`; } }
  // keep what is there now, in case the loaded file is not what the player wanted
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith('dogfight-') && !k.startsWith('dogfight-backup')) localStorage.setItem('dogfight-backup-' + k.slice(9), localStorage.getItem(k));
    }
    for (const k of keys) localStorage.setItem(k, j.data[k]);
  } catch (e) { return 'Nem sikerült menteni (tele a tárhely?).'; }
  return null;
}
