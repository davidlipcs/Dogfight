// The pilots of your side: hundreds of them, each with a name, callsign, rank, portrait and skills.  When you
// command, you pick who flies what: the best dogfighters for a fighter sweep, the calm ones for long patrols,
// carrier-qualified pilots for the carrier.  They get tired, wounded, captured or killed; experience makes
// them better.  Portraits: rendered pilots in full flying gear (assets/people/pilots/<nation>_<n>.jpg).
const FIRST = {
  us: ['James', 'Michael', 'Sarah', 'David', 'Emily', 'Chris', 'Jessica', 'Ryan', 'Ashley', 'Tyler', 'Megan', 'Brandon', 'Kevin', 'Laura', 'Marcus', 'Nicole', 'Jason', 'Rachel', 'Derek', 'Alicia'],
  uk: ['Oliver', 'Harry', 'Charlotte', 'George', 'Amelia', 'Thomas', 'Sophie', 'William', 'Jack', 'Emma'],
  fr: ['Louis', 'Camille', 'Hugo', 'Léa', 'Antoine', 'Manon', 'Julien', 'Chloé', 'Mathieu', 'Pierre'],
  de: ['Lukas', 'Anna', 'Felix', 'Lena', 'Jonas', 'Laura', 'Maximilian', 'Sophie', 'Tobias', 'Paul'],
  it: ['Marco', 'Giulia', 'Luca', 'Chiara', 'Andrea', 'Francesca', 'Matteo', 'Sara', 'Davide', 'Alessandro'],
  pl: ['Jakub', 'Anna', 'Piotr', 'Katarzyna', 'Tomasz', 'Magdalena', 'Krzysztof', 'Agnieszka', 'Paweł', 'Marek'],
  se: ['Erik', 'Elin', 'Johan', 'Sara', 'Anders', 'Maja', 'Lars', 'Emma', 'Gustav', 'Karin'],
  hu: ['Bence', 'Anna', 'Dávid', 'Réka', 'Ádám', 'Zsófia', 'Gergő', 'Eszter', 'Balázs', 'Levente', 'Péter', 'Katalin'],
  ru: ['Alexei', 'Dmitri', 'Sergei', 'Ivan', 'Nikolai', 'Andrei', 'Yuri', 'Olga', 'Pavel', 'Mikhail'],
  cn: ['Wei', 'Jun', 'Lei', 'Yang', 'Hao', 'Ming', 'Jie', 'Xin', 'Tao', 'Chen'],
};
const LAST = {
  us: ['Miller', 'Johnson', 'Carter', 'Reyes', 'Thompson', 'Walker', 'Brooks', 'Nguyen', 'Hayes', 'Coleman', 'Sullivan', 'Bennett', 'Ramirez', 'Foster', 'Kim', 'Parker', 'Murphy', 'Grant', 'Hughes', 'Ortiz'],
  uk: ['Smith', 'Taylor', 'Davies', 'Evans', 'Wilson', 'Clarke', 'Wright', 'Hall', 'Wood', 'Price'],
  fr: ['Martin', 'Bernard', 'Dubois', 'Laurent', 'Moreau', 'Lefèvre', 'Girard', 'Roux', 'Fournier', 'Mercier'],
  de: ['Müller', 'Schmidt', 'Weber', 'Wagner', 'Becker', 'Hoffmann', 'Koch', 'Richter', 'Wolf', 'Neumann'],
  it: ['Rossi', 'Bianchi', 'Romano', 'Ricci', 'Marino', 'Greco', 'Bruno', 'Gallo', 'Conti', 'Esposito'],
  pl: ['Nowak', 'Kowalski', 'Wiśniewski', 'Wójcik', 'Kamiński', 'Lewandowski', 'Zieliński', 'Szymański', 'Dąbrowski', 'Mazur'],
  se: ['Andersson', 'Johansson', 'Karlsson', 'Nilsson', 'Eriksson', 'Larsson', 'Olsson', 'Persson', 'Svensson', 'Lindqvist'],
  hu: ['Nagy', 'Kovács', 'Tóth', 'Szabó', 'Horváth', 'Varga', 'Kiss', 'Molnár', 'Németh', 'Farkas', 'Balogh', 'Papp'],
  ru: ['Ivanov', 'Petrov', 'Sokolov', 'Volkov', 'Kuznetsov', 'Morozov', 'Popov', 'Lebedev', 'Kozlov', 'Novikov'],
  cn: ['Wang', 'Li', 'Zhang', 'Liu', 'Chen', 'Yang', 'Zhao', 'Huang', 'Zhou', 'Wu'],
};
const CALLSIGNS = ['Ghost', 'Maverick', 'Iceman', 'Viper', 'Hammer', 'Blade', 'Rooster', 'Phoenix', 'Hondo', 'Bones', 'Spike', 'Torch', 'Rebel',
  'Jester', 'Cyclone', 'Wolf', 'Raven', 'Snake', 'Duke', 'Tex', 'Sparky', 'Reaper', 'Ace', 'Comet', 'Banshee', 'Doc', 'Sly', 'Gunner',
  'Hollywood', 'Sundance', 'Stinger', 'Thor', 'Nomad', 'Racer', 'Saint', 'Shadow', 'Storm', 'Tank', 'Wrench', 'Zeus', 'Bandit', 'Fang',
  'Lobo', 'Mustang', 'Ozzy', 'Puma', 'Rocket', 'Tiger', 'Vandal', 'Wildcat'];
export const RANKS = ['hadnagy', 'főhadnagy', 'százados', 'őrnagy', 'alezredes', 'ezredes', 'dandártábornok'];
export const RANKS_EN = ['2nd Lt', '1st Lt', 'Capt', 'Maj', 'Lt Col', 'Col', 'Brig Gen'];
const PORTRAITS_PER_NATION = 4;
const POWER_NATIONS = { us: ['us'], eu: ['uk', 'fr', 'de', 'it', 'pl', 'se', 'hu'], ru: ['ru'], cn: ['cn'] };
const EU_TYPES = { uk: 'typhoon', fr: 'rafale', de: 'typhoon', it: 'typhoon', pl: 'f16', se: 'gripen', hu: 'gripen' };
const US_TYPES = ['f16', 'f16', 'f35', 'f35', 'fa18', 'f15', 'f22'];

function rng(seed) { let s = seed % 2147483647 || 1; return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; }; }
const pick = (r, a) => a[Math.floor(r() * a.length)];

export function portraitUrl(p) {
  const path = `people/pilots/${p.nation}_${p.portrait}.jpg`;
  return (window.DOGFIGHT_ASSETS && window.DOGFIGHT_ASSETS[path]) || `assets/${path}`;
}

// a squadron's worth of pilots for a power (the player's side), all different
export function makeRoster(power, n = 240, seed = 7) {
  const r = rng(seed * 31 + power.length), out = [], used = new Set();
  const nations = POWER_NATIONS[power] || ['us'];
  for (let i = 0; i < n; i++) {
    const nation = nations.length > 1 ? (r() < 0.22 ? 'hu' : pick(r, nations)) : nations[0];
    let name;
    do { name = `${pick(r, FIRST[nation])} ${pick(r, LAST[nation])}`; } while (used.has(name) && used.size < 900);
    used.add(name);
    const talent = r();
    const skill = (base) => Math.round(Math.min(99, Math.max(25, base + (r() - 0.5) * 30 + talent * 25)));
    const rank = Math.min(5, Math.floor(r() * r() * 6));
    out.push({
      id: i + 1, name, callsign: pick(r, CALLSIGNS), nation, portrait: Math.floor(r() * PORTRAITS_PER_NATION), rank,
      type: power === 'eu' ? EU_TYPES[nation] : power === 'us' ? pick(r, US_TYPES) : power === 'ru' ? pick(r, ['su35', 'su35', 'mig29', 'mig31', 'su57']) : pick(r, ['j20', 'j20', 'su35']),
      dogfight: skill(50 + rank * 4), bvr: skill(48 + rank * 5), nerve: skill(55), carrier: power === 'us' && r() < 0.3 ? skill(55) : 0,
      sorties: Math.floor(rank * 25 + r() * 30), kills: Math.floor(rank * r() * 2), fatigue: 0, status: 'ready', away: 0,
    });
  }
  return out;
}
// one number for a pilot in a kind of mission
export function rating(p, kind = 'sweep') {
  const w = { sweep: [0.55, 0.3, 0.15], cap: [0.3, 0.45, 0.25], intercept: [0.25, 0.55, 0.2], escort: [0.4, 0.4, 0.2], strike: [0.3, 0.3, 0.4] }[kind] || [0.4, 0.4, 0.2];
  const base = p.dogfight * w[0] + p.bvr * w[1] + p.nerve * w[2];
  return Math.round(base * (1 - p.fatigue * 0.4));
}
// after a mission (simulated or flown): experience, tiredness, and what happened to them
export function afterSortie(p, outcome, r = Math.random) {
  p.sorties++; p.fatigue = Math.min(1, p.fatigue + 0.25);
  if (outcome.kills) { p.kills += outcome.kills; p.dogfight = Math.min(99, p.dogfight + outcome.kills); p.bvr = Math.min(99, p.bvr + outcome.kills * 0.5); }
  if (outcome.shotDown) {
    const x = r();
    if (outcome.overEnemy ? x < 0.35 : x < 0.12) { p.status = 'kia'; return 'kia'; }
    if (outcome.overEnemy && x < 0.65) { p.status = 'pow'; p.away = 8; return 'pow'; }
    p.status = 'wounded'; p.away = 4; return 'rescued';
  }
  return 'ok';
}
// a day passes: rest, healing, prisoners exchanged
export function restDay(roster) {
  for (const p of roster) {
    if (p.status === 'ready') p.fatigue = Math.max(0, p.fatigue - 0.12);
    if ((p.status === 'wounded' || p.status === 'pow') && --p.away <= 0) { p.status = 'ready'; p.fatigue = 0.3; }
  }
}
export const STATUS_HU = { ready: 'bevethető', wounded: 'sebesült', pow: 'hadifogoly', kia: 'hősi halott' };
