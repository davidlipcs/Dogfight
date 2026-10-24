// World War 3: the strategic game behind the career.
//  * four powers that start at war with everybody - the USA, Europe (the European air forces fight together
//    from the first day), Russia and China.  Trust is earned (joint missions, help when somebody is attacked,
//    keeping promises) and only then can two powers ally.
//  * every power has its real air force (fighters by type, public estimates 2025-26: FlightGlobal World Air
//    Forces, IISS Military Balance, open source counts) and builds new jets every month at the real rate.
//    You see your own numbers exactly, the others only as intelligence estimates.
//  * the war is fought on fronts at real places (the world map); every day the fronts fight it out by the
//    quality and number of the jets and pilots sent there; your own missions add what you actually did.
//  * a power whose fighters are gone is out; the last power (or alliance) with an air force wins.
import { clamp } from './util.js';

export const DAY_PER_MISSION = 2;

// air-to-air quality of each type (sensors, missiles, stealth, agility; 10 = best)
export const QUALITY = { f22: 10, f35: 8.6, su57: 7.6, j20: 8.0, f15: 7.6, su35: 7.4, typhoon: 7.6, rafale: 7.5, gripen: 6.7,
  f16: 6.6, fa18: 6.6, mig31: 5.6, mig29: 5.4, f15a: 7.2 };

// what a new jet costs (million dollars, flyaway, public figures) - nobody builds what they cannot pay for
export const COST = { f22: 150, f35: 82, f15: 90, f16: 65, fa18: 70, typhoon: 100, rafale: 95, gripen: 55, su35: 85, su57: 100, j20: 110, mig31: 60, mig29: 30, f15a: 40 };

// fighters by type (count in service), the factory lines (the most they can build per month) and the daily
// money the air force gets for new jets (million dollars a day)
export const POWERS = {
  us: { name: 'Egyesült Államok', short: 'USA', colour: '#4a7fd8', nations: ['us'],
    fleet: { f22: 180, f35: 650, f15: 30, f16: 900, fa18: 500 }, production: { f35: 10, f15: 2 }, income: 24, pilots: 3200, skill: 1.0,
    home: { lat: 38.9, lon: -77.0 } },
  eu: { name: 'Európa', short: 'EU', colour: '#3cc0a0', nations: ['uk', 'fr', 'de', 'it', 'pl', 'se', 'hu'],
    fleet: { typhoon: 370, rafale: 200, gripen: 104, f35: 75, f16: 48 }, production: { typhoon: 1, rafale: 1.5, gripen: 1, f35: 2 }, income: 9, pilots: 1300, skill: 0.95,
    home: { lat: 50.8, lon: 4.4 } },
  ru: { name: 'Oroszország', short: 'RU', colour: '#d84a4a', nations: ['ru'],
    fleet: { su35: 130, su57: 28, mig31: 120, mig29: 90 }, production: { su35: 1.5, su57: 1 }, income: 5, pilots: 1100, skill: 0.85,
    home: { lat: 55.75, lon: 37.6 } },
  cn: { name: 'Kína', short: 'CN', colour: '#e0b030', nations: ['cn'],
    fleet: { j20: 300, su35: 24 }, production: { j20: 10 }, income: 20, pilots: 1500, skill: 0.85,
    home: { lat: 39.9, lon: 116.4 } },
};
export const NATION_NAMES = { us: 'USA', uk: 'Egyesült Királyság', fr: 'Franciaország', de: 'Németország', it: 'Olaszország', pl: 'Lengyelország',
  se: 'Svédország', hu: 'Magyarország', ru: 'Oroszország', cn: 'Kína' };

// the fronts: real places (the battle is fought on the world map there) and who meets whom
export const FRONTS = [
  { id: 'baltic', name: 'Baltikum', lat: 57.6, lon: 24.6, sides: ['eu', 'us', 'ru'], why: 'Észtország, Lettország, Litvánia légtere' },
  { id: 'poland', name: 'Lengyel–belarusz határ', lat: 52.6, lon: 23.4, sides: ['eu', 'us', 'ru'], why: 'a Suwałki-folyosó' },
  { id: 'blacksea', name: 'Fekete-tenger', lat: 44.6, lon: 33.6, sides: ['eu', 'us', 'ru'], why: 'a Krím és a tengeri útvonalak' },
  { id: 'arctic', name: 'Észak-Norvégia', lat: 69.6, lon: 19.0, sides: ['eu', 'us', 'ru'], why: 'a Kola-félsziget bázisai' },
  { id: 'hungary', name: 'Magyarország', lat: 47.5, lon: 19.05, sides: ['eu', 'ru'], why: 'Európa szíve – a magyar Gripenek otthona' },
  { id: 'alaska', name: 'Alaszka – Bering-szoros', lat: 64.8, lon: -165.0, sides: ['us', 'ru'], why: 'Amerika és Oroszország 80 km-re' },
  { id: 'taiwan', name: 'Tajvani-szoros', lat: 24.4, lon: 119.6, sides: ['us', 'cn'], why: 'a Csendes-óceán kulcsa' },
  { id: 'scs', name: 'Dél-kínai-tenger', lat: 15.5, lon: 114.5, sides: ['us', 'cn'], why: 'mesterséges szigetek, kifutópályákkal' },
  { id: 'japan', name: 'Japán-tenger', lat: 40.0, lon: 134.5, sides: ['us', 'cn', 'ru'], why: 'három nagyhatalom találkozik' },
  { id: 'siberia', name: 'Amur-folyó (orosz–kínai határ)', lat: 48.4, lon: 135.1, sides: ['ru', 'cn'], why: 'a két szomszéd régi vitája' },
  { id: 'atlantic', name: 'Izland – az Atlanti-óceán kapuja', lat: 63.98, lon: -22.6, sides: ['us', 'eu'], why: 'Keflavík és a GIUK-rés: itt csak az európai légierővel kerülsz szembe' },
  { id: 'india', name: 'Himalája – Ladakh', lat: 34.2, lon: 77.6, sides: ['cn', 'us'], why: 'a világ teteje' },
];

const POWER_IDS = Object.keys(POWERS);
const pairKey = (a, b) => [a, b].sort().join('-');
const KEY = 'dogfight-war';

export function totalFleet(fleet) { return Object.values(fleet).reduce((s, v) => s + v, 0); }
export function strength(fleet, skill = 1) { return Object.entries(fleet).reduce((s, [k, v]) => s + v * (QUALITY[k] || 6), 0) * skill; }

// a fresh war: everybody against everybody, Europe together; trust from history
export function newWar(playerPower = 'us', seed = Date.now()) {
  const w = { version: 1, seed, day: 0, started: false, player: playerPower, powers: {}, trust: {}, allied: {}, war: {}, fronts: {},
    intel: {}, log: [], offers: [], over: null, missions: 0, policy: { production: {}, focus: null } };
  for (const id of POWER_IDS) {
    const p = POWERS[id];
    w.powers[id] = { fleet: { ...p.fleet }, start: totalFleet(p.fleet), lost: {}, built: {}, out: false, pilots: p.pilots, money: p.income * 20, spent: 0 };
  }
  const T = { 'eu-us': 25, 'ru-us': -60, 'cn-us': -55, 'eu-ru': -55, 'cn-eu': -25, 'cn-ru': 5 };
  for (const [k, v] of Object.entries(T)) { w.trust[k] = v; w.allied[k] = false; w.war[k] = true; }
  for (const f of FRONTS) w.fronts[f.id] = { control: {}, heat: 0.5, lastBattle: null };
  for (const id of POWER_IDS) if (id !== playerPower) w.intel[id] = 0.35;   // estimate error (+-35 %)
  return w;
}
export function loadWar() {
  try {
    const w = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (w) for (const f of FRONTS) if (!w.fronts[f.id]) w.fronts[f.id] = { control: {}, heat: 0.5, lastBattle: null };   // fronts added since the save
    return w;
  } catch (e) { return null; }
}
export function saveWar(w) { try { localStorage.setItem(KEY, JSON.stringify(w)); } catch (e) { /* private mode */ } }

export const trustOf = (w, a, b) => w.trust[pairKey(a, b)] || 0;
export const alliedWith = (w, a, b) => a === b || !!w.allied[pairKey(a, b)];
export const atWar = (w, a, b) => a !== b && !w.allied[pairKey(a, b)] && !!w.war[pairKey(a, b)];
export function changeTrust(w, a, b, d, why) {
  const k = pairKey(a, b);
  w.trust[k] = clamp((w.trust[k] || 0) + d, -100, 100);
  if (why) log(w, `${POWERS[a].short}–${POWERS[b].short} bizalom ${d > 0 ? '+' : ''}${d}: ${why}`);
}
function log(w, text) { w.log.unshift({ day: w.day, text }); if (w.log.length > 80) w.log.pop(); }

// what the player sees of a power's air force: exact for your own and your allies, an estimate for the rest
export function seenFleet(w, id) {
  const real = w.powers[id].fleet;
  if (id === w.player || alliedWith(w, id, w.player)) return { fleet: { ...real }, exact: true };
  const e = w.intel[id] || 0.35, out = {};
  for (const [k, v] of Object.entries(real)) {
    const noise = Math.sin((w.seed % 997) + k.length * 7.3 + w.day * 0.13 + id.length) * e;   // stable per day
    out[k] = Math.max(0, Math.round(v * (1 + noise) / 5) * 5);
  }
  return { fleet: out, exact: false, error: e };
}

// ---------------------------------------------------------------- diplomacy
// an alliance offer: accepted when trust is high enough (and the other side is not losing badly to us)
export function proposeAlliance(w, from, to) {
  const t = trustOf(w, from, to);
  if (alliedWith(w, from, to)) return { ok: false, text: 'Már szövetségesek vagytok.' };
  if (t < 60) return { ok: false, text: `${POWERS[to].name} nem bízik bennetek eléggé (bizalom: ${Math.round(t)} / 60).` };
  w.allied[pairKey(from, to)] = true; w.war[pairKey(from, to)] = false;
  log(w, `SZÖVETSÉG: ${POWERS[from].name} és ${POWERS[to].name}`);
  return { ok: true, text: `${POWERS[to].name} elfogadta: szövetségesek vagytok!` };
}
export function proposeCeasefire(w, from, to) {
  const t = trustOf(w, from, to), weak = w.powers[to].fleet && totalFleet(w.powers[to].fleet) / w.powers[to].start;
  if (t > 0 || weak < 0.35) {
    w.war[pairKey(from, to)] = false; log(w, `TŰZSZÜNET: ${POWERS[from].name} és ${POWERS[to].name}`);
    changeTrust(w, from, to, 10, 'tűzszünet');
    return { ok: true, text: `Tűzszünet ${POWERS[to].name} és köztetek.` };
  }
  return { ok: false, text: `${POWERS[to].name} elutasította a tűzszünetet.` };
}
export function declareWar(w, from, to) {
  w.allied[pairKey(from, to)] = false; w.war[pairKey(from, to)] = true;
  changeTrust(w, from, to, -40, 'hadüzenet');
  for (const o of POWER_IDS) if (o !== from && o !== to && alliedWith(w, o, to)) changeTrust(w, from, o, -20, `megtámadtátok a szövetségesét (${POWERS[to].short})`);
}

// ---------------------------------------------------------------- the daily battles on the fronts
// each power puts its jets on its fronts (more where its enemies are strong), and every front where enemies
// meet has a battle: losses by Lanchester's square law, scaled down to a day of fighting
function seeded(w) { let s = (w.seed + w.day * 7919) % 2147483647; return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; }; }
export function simulateDay(w, skip = null) {
  const r = seeded(w), report = [];
  w.day++;
  // production: each line builds at most its monthly rate, and every jet is paid for from the budget - when the money
  // is gone the lines stand still (the factories the enemy has bombed make less, too)
  for (const id of POWER_IDS) {
    const P = w.powers[id];
    if (P.out) continue;
    if (P.money === undefined) { P.money = POWERS[id].income * 20; P.spent = 0; }          // an older save
    const dmg = (P.damage || 0) > 0 ? 1 - P.damage : 1;
    P.money += POWERS[id].income * dmg;                                                   // the budget of the day
    P.money = Math.min(P.money, POWERS[id].income * 60);                                  // no endless savings: two months at most
    P.fleetFrac = P.fleetFrac || {};
    // the line the government wants first (the player chooses it for his own side), then the others
    const order = Object.keys(POWERS[id].production).sort((a, b) => (a === (w.policy.production && w.policy.production[id]) ? -1 : b === (w.policy.production && w.policy.production[id]) ? 1 : 0));
    for (const k of order) {
      const perMonth = POWERS[id].production[k], cost = COST[k] || 80;
      P.fleetFrac[k] = Math.min(1.5, (P.fleetFrac[k] || 0) + perMonth / 30 * dmg);          // the line's progress, never more than a jet and a half ahead
      while (P.fleetFrac[k] >= 1 && P.money >= cost) {
        P.fleetFrac[k] -= 1; P.money -= cost; P.spent += cost;
        P.fleet[k] = (P.fleet[k] || 0) + 1; P.built[k] = (P.built[k] || 0) + 1;
      }
    }
    if (P.damage) P.damage = Math.max(0, P.damage - 0.01);       // repairs
  }
  if (!w.started) return report;
  for (const f of FRONTS) {
    if (skip === f.id) continue;
    const sides = f.sides.filter((s) => !w.powers[s].out);
    // the hostile pairs at this front
    for (let i = 0; i < sides.length; i++) for (let j = i + 1; j < sides.length; j++) {
      const a = sides[i], b = sides[j];
      if (!atWar(w, a, b)) continue;
      const heat = w.fronts[f.id].heat * (0.6 + 0.8 * r());
      const commit = (id) => {                                      // a slice of the air force on this front today
        const fronts = FRONTS.filter((x) => x.sides.includes(id)).length;
        return 0.06 * heat / Math.max(1, fronts / 3);
      };
      const ca = commit(a), cb = commit(b);
      const sa = strength(w.powers[a].fleet, POWERS[a].skill) * ca, sb = strength(w.powers[b].fleet, POWERS[b].skill) * cb;
      if (sa < 1 || sb < 1) continue;
      const ka = 0.05 * sb / (sa + sb), kb = 0.05 * sa / (sa + sb);   // fraction of the committed jets lost
      const la = loseJets(w, a, ka * ca), lb = loseJets(w, b, kb * cb);
      w.fronts[f.id].lastBattle = { day: w.day, a, b, la, lb };
      changeTrust(w, a, b, -0.02);                                                 // a day of fighting: a little less trust
      report.push({ front: f.id, a, b, la, lb });
    }
  }
  checkOut(w);
  return report;
}
// remove a fraction of a power's fleet (spread over the types; the better ones survive a little better)
export function loseJets(w, id, frac) {
  const P = w.powers[id];
  let total = 0;
  for (const [k, v] of Object.entries(P.fleet)) {
    const q = QUALITY[k] || 6, f = frac * (1.25 - q / 20);
    const exact = v * f, n = Math.floor(exact) + (Math.random() < exact % 1 ? 1 : 0);
    const lost = Math.min(v, n);
    P.fleet[k] = v - lost; P.lost[k] = (P.lost[k] || 0) + lost; total += lost;
  }
  return total;
}
// the jets of a mission (what really happened in the player's battle): by type
export function applyMission(w, result) {
  for (const [power, byType] of Object.entries(result.losses || {})) {
    const P = w.powers[power];
    if (!P) continue;
    for (const [k, n] of Object.entries(byType)) { const m = Math.min(P.fleet[k] || 0, n); P.fleet[k] = (P.fleet[k] || 0) - m; P.lost[k] = (P.lost[k] || 0) + m; }
  }
  if (result.front && w.fronts[result.front]) w.fronts[result.front].heat = clamp(w.fronts[result.front].heat + (result.won ? -0.05 : 0.08), 0.2, 1);
  for (const [other, d] of Object.entries(result.trust || {})) changeTrust(w, w.player, other, d, result.trustWhy);
  if (result.intel) for (const id of Object.keys(w.intel)) w.intel[id] = Math.max(0.05, w.intel[id] - result.intel);
  if (result.strike) { const P = w.powers[result.strike]; P.damage = clamp((P.damage || 0) + 0.25, 0, 0.8); log(w, `Gyárak bombázva: ${POWERS[result.strike].name} gyártása -25 %`); }
  w.missions++;
  checkOut(w);
}
function checkOut(w) {
  for (const id of POWER_IDS) {
    const P = w.powers[id];
    if (!P.out && totalFleet(P.fleet) <= Math.max(3, P.start * 0.02)) { P.out = true; log(w, `${POWERS[id].name} légiereje megsemmisült – kiesett a háborúból!`); }
  }
  // the end: everybody left is allied (or at peace) with everybody else
  const left = POWER_IDS.filter((id) => !w.powers[id].out);
  const fighting = left.some((a) => left.some((b) => a < b && atWar(w, a, b)));
  if (!fighting && !w.over) {
    w.over = { day: w.day, winners: left, player: left.includes(w.player) };
    log(w, left.includes(w.player) ? 'A HÁBORÚ VÉGET ÉRT – GYŐZTETEK!' : 'A HÁBORÚ VÉGET ÉRT – a te oldalad elvesztette a légierejét.');
  }
  if (w.powers[w.player].out && !w.over) w.over = { day: w.day, winners: left, player: false };
}

// the other powers' own decisions every few days.  They follow the trust between them (and towards you):
//  - an alliance falls apart when the trust collapses (below 20); a truce is called off when it is low (below -40)
//  - allies help each other: the strong one sends jets to the one that is losing
//  - deep hatred means attacks on the enemy's factories
//  - a common enemy brings them closer, high trust makes them ally; a power that is badly beaten asks for a ceasefire
//  - towards you: offers of an alliance (trust 70+) or of a ceasefire (25+ when somebody is losing), visible in the
//    politics screen and the log; and the ones who hate you hit your factories
export function aiDiplomacy(w) {
  const r = seeded(w), ratio = (id) => totalFleet(w.powers[id].fleet) / Math.max(1, w.powers[id].start);
  w.offers = (w.offers || []).filter((o) => w.day - o.day <= 10 && !w.powers[o.from].out);
  const hasOffer = (from, type) => w.offers.some((o) => o.from === from && o.type === type);
  const hit = (id, by, d) => { const P = w.powers[id]; P.damage = clamp((P.damage || 0) + d, 0, 0.8); log(w, `${POWERS[by].name} bombázta ${id === w.player ? 'a te' : `${POWERS[id].name}`} gyárait (a gyártás −${Math.round(d * 100)} %)`); };
  for (const a of POWER_IDS) for (const b of POWER_IDS) {
    if (a >= b || w.powers[a].out || w.powers[b].out) continue;
    const pl = a === w.player || b === w.player, other = a === w.player ? b : a;
    if (!pl) {
      const common = POWER_IDS.filter((c) => c !== a && c !== b && atWar(w, a, c) && atWar(w, b, c)).length;
      changeTrust(w, a, b, common * 0.6);
    }
    const t = trustOf(w, a, b);
    // an alliance dies of distrust (yours included)
    if (alliedWith(w, a, b) && t < 20) {
      w.allied[pairKey(a, b)] = false; w.war[pairKey(a, b)] = true;
      log(w, `SZÖVETSÉG FELBONTVA: ${POWERS[a].name} és ${POWERS[b].name} (bizalom ${Math.round(t)})`);
      continue;
    }
    // a truce is called off when the trust is gone
    if (!alliedWith(w, a, b) && !atWar(w, a, b) && t < -40) { declareWar(w, a, b); log(w, `TŰZSZÜNET FELMONDVA: ${POWERS[a].name} és ${POWERS[b].name}`); continue; }
    if (alliedWith(w, a, b)) {
      // the strong ally helps the weak one: two of its best jets
      const [s, wk] = ratio(a) >= ratio(b) ? [a, b] : [b, a];
      if (ratio(wk) < 0.6 && ratio(s) > 0.8 && r() < 0.35) {
        const type = Object.keys(w.powers[s].fleet).sort((x, y) => (QUALITY[y] || 6) - (QUALITY[x] || 6)).find((k) => w.powers[s].fleet[k] > 10);
        if (type) { w.powers[s].fleet[type] -= 2; w.powers[wk].fleet[type] = (w.powers[wk].fleet[type] || 0) + 2; changeTrust(w, a, b, 1); log(w, `${POWERS[s].name} 2 ${type.toUpperCase()}-t küldött szövetségesének (${POWERS[wk].name})`); }
      }
      continue;
    }
    if (atWar(w, a, b)) {
      const weak = Math.min(ratio(a), ratio(b));
      if (!pl && t >= 10 && weak < 0.55) { w.war[pairKey(a, b)] = false; changeTrust(w, a, b, 10); log(w, `TŰZSZÜNET: ${POWERS[a].name} és ${POWERS[b].name} (a veszteségektől megfogyatkozva)`); continue; }
      if (t <= -60 && r() < 0.06) { const victim = pl ? w.player : (ratio(a) < ratio(b) ? a : b); hit(victim, victim === a ? b : a, 0.15); }
    }
    if (!pl && !alliedWith(w, a, b) && t >= 70) { w.allied[pairKey(a, b)] = true; w.war[pairKey(a, b)] = false; log(w, `SZÖVETSÉG: ${POWERS[a].name} és ${POWERS[b].name}`); continue; }
    if (pl) {
      if (t >= 70 && !hasOffer(other, 'alliance')) { w.offers.push({ from: other, type: 'alliance', day: w.day }); log(w, `${POWERS[other].name} szövetséget ajánl neked (bizalom ${Math.round(t)})`); }
      else if (atWar(w, a, b) && t >= 25 && (ratio(other) < 0.55 || ratio(w.player) < 0.5) && !hasOffer(other, 'ceasefire')) { w.offers.push({ from: other, type: 'ceasefire', day: w.day }); log(w, `${POWERS[other].name} tűzszünetet ajánl (bizalom ${Math.round(t)})`); }
    }
  }
}
// the player answers an offer
export function answerOffer(w, i, accept) {
  const o = (w.offers || [])[i];
  if (!o) return { ok: false, text: '' };
  w.offers.splice(i, 1);
  if (!accept) { changeTrust(w, w.player, o.from, -3, 'elutasítottad az ajánlatukat'); return { ok: true, text: 'Elutasítottad.' }; }
  return o.type === 'alliance' ? proposeAlliance(w, w.player, o.from) : proposeCeasefire(w, w.player, o.from);
}
// enemy jets of a front for a mission there: what types (by the fleet) and how good (the power's skill)
export function frontEnemies(w, frontId) {
  const f = FRONTS.find((x) => x.id === frontId);
  return f.sides.filter((s) => atWar(w, w.player, s) && !w.powers[s].out);
}
export function pickTypes(fleet, n, rnd = Math.random) {
  const entries = Object.entries(fleet).filter(([, v]) => v > 0), sum = entries.reduce((s, [, v]) => s + v, 0), out = [];
  for (let i = 0; i < n && sum > 0; i++) {
    let x = rnd() * sum;
    for (const [k, v] of entries) { x -= v; if (x <= 0) { out.push(k); break; } }
  }
  return out;
}

// the budget as the player sees it: money, the daily income, and how many jets a month it really pays for
export function budgetOf(w, id) {
  const P = w.powers[id], inc = POWERS[id].income * (1 - (P.damage || 0));
  let monthly = 0, cost = 0;
  for (const [k, perMonth] of Object.entries(POWERS[id].production)) { monthly += perMonth; cost += perMonth * (COST[k] || 80); }
  const afford = Math.min(monthly, inc * 30 / (cost / monthly));
  return { money: Math.round(P.money || 0), income: Math.round(inc * 10) / 10, perMonth: Math.round(afford * 10) / 10, capacity: monthly };
}
