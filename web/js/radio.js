// The radio: talk to the tower, your wingman / flight lead and the AWACS like a real fighter pilot.
//  * three ways to transmit: hold the radio key (I) and SAY it (speech recognition: the browser's own in Chrome
//    and Edge), or tap the key and TYPE it, or pick it from the numbered list (3..9, 0)
//  * the game understands the real brevity words and radio phrases (ATP-1 / AFTTP 3-1 "multi-service brevity
//    codes", ICAO phraseology), in English like the real ones; the callsign is optional
//  * in the career you can only use what you have been taught (school.js unlocks them lesson by lesson); in free
//    play everything is open
//  * the other side answers - by voice, and in the radio log with the speaker's picture
import { V, sub, len, norm, dot, clamp, DEG } from './util.js';

const $ = (id) => document.getElementById(id);

// id, what to say, other ways to say it, who to, the lesson that teaches it, what it means (Hungarian)
export const CALLS = [
  // ---- tower (ground and the airfield traffic)
  { id: 'radio_check', say: 'RADIO CHECK', alt: ['HOW DO YOU READ', 'COMM CHECK'], to: 'tower', lesson: 'radio1', hu: 'rádiópróba – hallanak-e' },
  { id: 'request_taxi', say: 'REQUEST TAXI', alt: ['READY TO TAXI', 'TAXI'], to: 'tower', lesson: 'radio1', hu: 'gurulási engedélyt kérsz' },
  { id: 'ready_takeoff', say: 'READY FOR TAKEOFF', alt: ['REQUEST TAKEOFF', 'READY FOR DEPARTURE', 'HOLDING SHORT', 'READY'], to: 'tower', lesson: 'radio1', hu: 'felszállásra kész vagy, engedélyt kérsz' },
  { id: 'airborne', say: 'AIRBORNE', alt: ['DEPARTING', 'WHEELS UP'], to: 'tower', lesson: 'radio1', hu: 'a levegőben vagy' },
  { id: 'inbound', say: 'INBOUND FOR LANDING', alt: ['REQUEST LANDING', 'INBOUND', 'RETURNING FOR LANDING', 'FULL STOP'], to: 'tower', lesson: 'radio2', hu: 'leszállni jössz' },
  { id: 'gear_down', say: 'GEAR DOWN', alt: ['THREE GREEN', 'GEAR DOWN AND LOCKED'], to: 'tower', lesson: 'radio2', hu: 'a futómű kint és bezárva' },
  { id: 'clear_runway', say: 'CLEAR OF RUNWAY', alt: ['RUNWAY VACATED', 'CLEAR OF THE RUNWAY'], to: 'tower', lesson: 'radio2', hu: 'leszálltál, elhagytad a kifutót' },
  { id: 'emergency', say: 'MAYDAY', alt: ['EMERGENCY', 'PAN PAN'], to: 'tower', lesson: 'radio2', hu: 'vészhelyzet' },
  // ---- flight (between the lead and the wingman)
  { id: 'ack', say: 'COPY', alt: ['TWO', 'ROGER', 'WILCO', 'ACKNOWLEDGED', 'AFFIRMATIVE'], to: 'flight', lesson: 'radio3', hu: 'vettem (a 2-es így nyugtáz: „TWO”)' },
  { id: 'visual', say: 'VISUAL', alt: ['VISUAL ON LEAD', 'I HAVE YOU'], to: 'flight', lesson: 'radio3', hu: 'látom a saját gépet (vezért / kísérőt)' },
  { id: 'blind', say: 'BLIND', alt: ['NO VISUAL', 'LOST YOU'], to: 'flight', lesson: 'radio3', hu: 'nem látom a saját gépet' },
  { id: 'tally', say: 'TALLY', alt: ['TALLY HO', 'TALLY BANDIT'], to: 'flight', lesson: 'radio4', hu: 'látom az ellenséget' },
  { id: 'no_joy', say: 'NO JOY', alt: ['NO TALLY'], to: 'flight', lesson: 'radio4', hu: 'nem látom az ellenséget' },
  { id: 'fox2', say: 'FOX TWO', alt: ['FOX 2'], to: 'flight', lesson: 'radio4', hu: 'hőkövető rakétát indítottam' },
  { id: 'fox3', say: 'FOX THREE', alt: ['FOX 3'], to: 'flight', lesson: 'radio4', hu: 'aktív radaros rakétát indítottam' },
  { id: 'guns', say: 'GUNS GUNS', alt: ['GUNS'], to: 'flight', lesson: 'radio4', hu: 'gépágyúval lövök' },
  { id: 'splash', say: 'SPLASH ONE', alt: ['SPLASH', 'KILL', 'BANDIT DOWN'], to: 'flight', lesson: 'radio4', hu: 'lelőttem' },
  { id: 'defending', say: 'DEFENDING', alt: ['DEFENSIVE', 'MISSILE INBOUND', 'SPIKED', 'NOTCHING'], to: 'flight', lesson: 'radio4', hu: 'rakéta jön rám, védekezem' },
  { id: 'bingo', say: 'BINGO', alt: ['BINGO FUEL', 'JOKER'], to: 'flight', lesson: 'radio5', hu: 'kevés az üzemanyag – haza kell indulni' },
  { id: 'winchester', say: 'WINCHESTER', alt: ['OUT OF MISSILES', 'NO WEAPONS'], to: 'flight', lesson: 'radio5', hu: 'elfogyott a fegyver' },
  { id: 'rtb', say: 'RTB', alt: ['RETURNING TO BASE', 'RETURN TO BASE', 'HEADING HOME'], to: 'flight', lesson: 'radio5', hu: 'visszatérek a bázisra' },
  // ---- orders to the wingman (when you lead)
  { id: 'engage', say: 'ENGAGE', alt: ['CLEARED HOT', 'ATTACK', 'TWO ENGAGE', 'ENGAGE BANDIT', 'CLEARED TO ENGAGE'], to: 'wing', lesson: 'radio6', hu: 'parancs a kísérőnek: támadj' },
  { id: 'cover', say: 'COVER ME', alt: ['COVER', 'CHECK SIX', 'CHECK MY SIX'], to: 'wing', lesson: 'radio6', hu: 'parancs: védd a hátamat' },
  { id: 'rejoin', say: 'REJOIN', alt: ['FORM UP', 'JOIN UP', 'RETURN TO FORMATION'], to: 'wing', lesson: 'radio6', hu: 'parancs: gyere vissza alakzatba' },
  { id: 'break', say: 'BREAK LEFT', alt: ['BREAK RIGHT', 'BREAK'], to: 'wing', lesson: 'radio6', hu: 'figyelmeztetés: rakéta / ellenség – kitörés' },
  // ---- AWACS (the airborne radar: who is where)
  { id: 'picture', say: 'PICTURE', alt: ['REQUEST PICTURE', 'BOGEY DOPE', 'DECLARE', 'BRAA'], to: 'awacs', lesson: 'radio5', hu: 'hol vannak az ellenséges gépek? (irány, táv, magasság)' },
  { id: 'checking_in', say: 'CHECKING IN', alt: ['ON STATION', 'CHECK IN'], to: 'awacs', lesson: 'radio5', hu: 'bejelentkezel az AWACS-hoz' },
];

const NUM = { 0: 'ZERO', 1: 'ONE', 2: 'TWO', 3: 'THREE', 4: 'FOUR', 5: 'FIVE', 6: 'SIX', 7: 'SEVEN', 8: 'EIGHT', 9: 'NINE' };
const FIX = { 'FOCKS': 'FOX', 'FOCUS': 'FOX', 'FOXTROT': 'FOX', 'TOO': 'TWO', 'TO': 'TWO', 'FOR': 'FOUR', 'TALLEY': 'TALLY', 'TELLY': 'TALLY', 'TALLIES': 'TALLY',
  'SPLASHED': 'SPLASH', 'BINGE': 'BINGO', 'RTV': 'RTB', 'ARE': 'R', 'TEA': 'T', 'BEE': 'B', 'VISUALS': 'VISUAL', 'PICTURES': 'PICTURE',
  'WINCHESTERS': 'WINCHESTER', 'ENGAGED': 'ENGAGE', 'ENGAGING': 'ENGAGE', 'DEFENSIVE': 'DEFENDING', 'GUN': 'GUNS', 'TAXIING': 'TAXI', 'TAKE': 'TAKE', 'OFF': 'OFF' };
export function normalise(text) {
  let t = String(text).toUpperCase().replace(/TAKE[- ]?OFF/g, 'TAKEOFF').replace(/[^A-Z0-9 ]/g, ' ');
  t = t.replace(/\d/g, (d) => ` ${NUM[d]} `);
  return t.split(/\s+/).filter(Boolean).map((w) => FIX[w] || w).join(' ');
}
// does the phrase occur in the words (in order, other words allowed in between: callsigns, "tower", ...)?
function occurs(words, phrase) {
  const p = phrase.split(' ');
  let i = 0;
  for (const w of words) if (w === p[i]) { i++; if (i === p.length) return true; }
  return false;
}
// -> the best matching call (the longest phrase wins: "FOX TWO" over "TWO"), or null
export function recognise(text, allowed = CALLS) {
  const words = normalise(text).split(' ');
  let best = null, bestLen = 0;
  for (const c of allowed) {
    for (const ph of [c.say, ...c.alt]) {
      const n = normalise(ph);
      if (occurs(words, n) && n.length > bestLen) { best = c; bestLen = n.length; }
    }
  }
  return best;
}

// --------------------------------------------------------------------- voices of the other side
class Speaker {
  constructor() {
    this.synth = window.speechSynthesis || null; this.voices = [];
    const pick = () => { this.voices = this.synth ? this.synth.getVoices().filter((v) => /^en/i.test(v.lang)) : []; };
    if (this.synth) { pick(); if ('onvoiceschanged' in this.synth) this.synth.addEventListener('voiceschanged', pick); }
    this.volume = 0.8; this.enabled = true;
  }
  say(text, who) {
    if (!this.synth || !this.enabled) return;
    try {
      const u = new SpeechSynthesisUtterance(text.replace(/\b(\d)-(\d)\b/g, '$1 $2'));
      const female = who === 'awacs' || who === 'instructor_navy';
      const v = this.voices.find((x) => (female ? /female|zira|samantha|jenny|aria|susan|karen/i : /male|david|mark|guy|daniel|alex|fred/i).test(x.name)) || this.voices[0];
      if (v) u.voice = v;
      u.lang = v ? v.lang : 'en-US';
      u.rate = who === 'awacs' ? 1.15 : 1.05; u.pitch = { tower: 0.9, awacs: 1.1, wing: 1.0, lead: 0.85, instructor: 0.8 }[who] || 1;
      u.volume = this.volume;
      this.synth.speak(u);
    } catch (e) { /* no voices */ }
  }
}

export const PORTRAITS = { tower: 'assets/people/tower.png', awacs: 'assets/people/awacs.png', instructor: 'assets/people/instructor.png',
  instructor_navy: 'assets/people/navy_instructor.png', general: 'assets/people/general.png' };
const NAMES = { tower: 'TORONY', awacs: 'AWACS „MAGIC”', wing: 'KÍSÉRŐ', lead: 'VEZÉR', instructor: 'OKTATÓ', you: 'TE' };
const asset = (p) => (window.DOGFIGHT_ASSETS && window.DOGFIGHT_ASSETS[p.replace('assets/', '')]) || p;

// --------------------------------------------------------------------- the radio itself
export class Radio {
  constructor(game) {
    this.g = game; this.speaker = new Speaker(); this.log = []; this.open = false; this.listeners = [];
    this.callsign = 'VIPER 1-1'; this.unlocked = null; this.portraits = {};            // null: everything (free play)
    this.cleared = { taxi: false, takeoff: false, land: false };
    this.SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
    this.listening = false;
    const box = $('radio-input');
    if (box) {
      box.addEventListener('keydown', (e) => {
        e.stopPropagation();
        if (/^[0-9]$/.test(e.key) && !box.value) { this.pick(e.key); e.preventDefault(); return; }
        if (e.key === 'Enter') { this.transmit(box.value, 'type'); box.value = ''; this.close(); e.preventDefault(); }
        else if (e.key === 'Escape') { this.close(); e.preventDefault(); }
      });
      box.addEventListener('keyup', (e) => e.stopPropagation());
    }
  }
  onCall(fn) { this.listeners.push(fn); return () => { this.listeners = this.listeners.filter((f) => f !== fn); }; }
  available() {
    const all = this.unlocked ? CALLS.filter((c) => this.unlocked.has(c.lesson)) : CALLS;
    const g = this.g, p = g.player;
    return all.filter((c) => {
      if (c.to === 'wing') return !!g.wingman && g.wingman.alive;
      if (c.to === 'awacs') return !p || !p.onGround;
      return true;
    });
  }
  // the radio key: tap = the panel (type or pick a number); hold = talk (speech)
  keyDown() {
    if (this.open) { this.close(); return; }
    this.pressT = performance.now();
    if (this.SR && this.g.settings && this.g.settings.voiceRadio !== false) this.startListening();
  }
  keyUp() {
    const held = performance.now() - (this.pressT || 0);
    if (this.listening && held > 400) { this.stopListening(); return; }
    if (this.listening) this.abortListening();
    this.show();
  }
  startListening() {
    try {
      const r = this.rec = new this.SR();
      r.lang = 'en-US'; r.interimResults = true; r.maxAlternatives = 5; r.continuous = false;
      this.heard = []; this.listening = true;
      r.onresult = (e) => {
        const res = e.results[e.results.length - 1];
        this.heard = [...res].map((a) => a.transcript);
        this.g.hud.message(`🎙 ${this.heard[0]}`, 'info', 1.5, 'mic');
        if (res.isFinal && !this.listening) this.finishSpeech();
      };
      r.onerror = (e) => { if (e.error !== 'aborted' && e.error !== 'no-speech') this.g.hud.message(`Mikrofon: ${e.error === 'not-allowed' ? 'nincs engedély' : e.error}`, 'warn', 2.5, 'mic'); };
      r.onend = () => { if (this.waitEnd) { this.waitEnd = false; this.finishSpeech(); } };
      r.start();
      this.g.hud.message('🎙 BESZÉLJ… (engedd el a gombot, ha kész)', 'info', 2, 'mic');
    } catch (e) { this.listening = false; }
  }
  stopListening() { this.listening = false; this.waitEnd = true; try { this.rec.stop(); } catch (e) { this.finishSpeech(); } }
  abortListening() { this.listening = false; this.waitEnd = false; try { this.rec.abort(); } catch (e) { /* ignore */ } }
  finishSpeech() {
    if (this.done === this.rec) return;
    this.done = this.rec;
    const alts = this.heard || [];
    for (const a of alts) if (recognise(a, this.available())) { this.transmit(a, 'voice'); return; }
    if (alts.length) { this.say('you', alts[0]); this.g.hud.message('Nem értették – mondd újra, vagy írd be / válassz számot', 'warn', 2.5, 'mic'); }
    else this.show();                                  // nothing heard (no microphone?): the list and the typing box
  }
  show() {
    this.open = true;
    const list = this.available();
    $('radio').hidden = false;
    $('radio-list').innerHTML = list.slice(0, 10).map((c, i) => `<div><kbd>${(i + 3) % 10}</kbd> <b>${c.say}</b> <span>${c.hu}</span></div>`).join('') +
      (list.length > 10 ? `<div class="hint">…és még ${list.length - 10}: írd be</div>` : '');
    this.menu = list.slice(0, 10);
    const box = $('radio-input');
    box.value = ''; box.focus();
  }
  close() { this.open = false; $('radio').hidden = true; const box = $('radio-input'); if (box) box.blur(); }
  // a digit while the panel is open: that call
  pick(digit) {
    const i = (Number(digit) + 7) % 10, c = this.menu && this.menu[i];
    if (!c) return false;
    this.close();
    this.transmit(c.say, 'menu');
    return true;
  }
  // -> true if understood
  transmit(text, how) {
    if (!text || !text.trim()) return false;
    const call = recognise(text, this.available());
    if (!call) {
      const locked = this.unlocked && recognise(text, CALLS);
      this.say('you', text.toUpperCase());
      this.g.hud.message(locked ? `Ezt még nem tanultad: ${locked.say} (${locked.hu})` : 'Ezt nem értik a rádión – nézd meg a listát (I)', 'warn', 3, 'mic');
      return false;
    }
    this.say('you', `${this.prefix(call)}${this.callsign}, ${call.say}`);
    this.respond(call);
    for (const fn of this.listeners) fn(call, how);
    return true;
  }
  prefix(call) { return { tower: 'TOWER, ', awacs: 'MAGIC, ', wing: 'TWO, ', flight: '' }[call.to] || ''; }
  // a line in the radio log (with the speaker's picture) and spoken by the other side
  say(who, text, delay = 0, speak = true) {
    const go = () => {
      this.log.push({ who, text, t: performance.now() });
      if (this.log.length > 5) this.log.shift();
      this.render();
      if (who !== 'you' && speak) this.speaker.say(text, who);
    };
    if (delay) setTimeout(go, delay); else go();
  }
  render() {
    const el = $('radio-log');
    if (!el) return;
    el.innerHTML = this.log.map((l) => `<div class="rl ${l.who}">${this.portraits[l.who] || PORTRAITS[l.who] ? `<img src="${this.portraits[l.who] || asset(PORTRAITS[l.who])}" alt="">` : ''}<b>${NAMES[l.who] || l.who}</b> ${l.text}</div>`).join('');
    clearTimeout(this.fade);
    el.classList.remove('old');
    this.fade = setTimeout(() => el.classList.add('old'), 9000);
  }
  // ---------------------------------------------------------------- the other side answers
  respond(call) {
    const g = this.g, p = g.player, cs = this.callsign, field = g.terrain.airfield, rwy = '36';
    const R = (who, text) => this.say(who, text, 900 + Math.random() * 700);
    switch (call.id) {
      case 'radio_check': R('tower', `${cs}, ${g.terrain ? 'Tower' : ''}, loud and clear.`); break;
      case 'request_taxi': this.cleared.taxi = true; R('tower', `${cs}, taxi to runway ${rwy}, hold short.`); break;
      case 'ready_takeoff':
        // in training the order matters: taxi clearance first
        if (this.unlocked && !this.cleared.taxi && p && p.onGround) { R('tower', `${cs}, request taxi first.`); break; }
        this.cleared.takeoff = true; R('tower', `${cs}, wind calm, runway ${rwy}, cleared for takeoff.`); break;
      case 'airborne': R('tower', `${cs}, radar contact, climb and maintain angels one five. Contact Magic.`); break;
      case 'inbound': R('tower', `${cs}, runway ${rwy}, report gear down.`); break;
      case 'gear_down':
        if (p && p.fm.gearPos > 0.9) { this.cleared.land = true; R('tower', `${cs}, check gear down, wind calm, runway ${rwy}, cleared to land.`); }
        else R('tower', `${cs}, negative, your gear is not down! Go around.`);
        break;
      case 'clear_runway': R('tower', `${cs}, taxi to parking. Welcome home.`); break;
      case 'emergency': R('tower', `${cs}, roger your mayday, runway ${rwy} is yours, crash crews standing by.`); break;
      case 'picture': R('awacs', this.picture()); break;
      case 'checking_in': R('awacs', `${cs}, Magic, radar contact. ${this.picture(true)}`); break;
      case 'engage': case 'cover': case 'rejoin': case 'break': {
        const w = g.wingman;
        if (!w || !w.alive) { R('awacs', `${cs}, your wingman is not on frequency.`); break; }
        if (w.pilot && w.pilot.order !== undefined) w.pilot.order = call.id === 'break' ? 'engage' : call.id;
        const ans = { engage: 'Two, engaging.', cover: 'Two, in your six.', rejoin: 'Two, rejoining.', break: 'Two, breaking, defending!' }[call.id];
        R('wing', ans);
        break;
      }
      case 'bingo': R(g.wingman && g.wingman.alive ? 'wing' : 'awacs', g.wingman && g.wingman.alive ? 'Two, copy bingo, RTB.' : `${cs}, Magic, copy, vector ${this.homeBearing()} for home.`); break;
      case 'rtb': R('awacs', `${cs}, Magic copies, home plate bearing ${this.homeBearing()}.`); break;
      case 'defending': if (g.wingman && g.wingman.alive) { R('wing', 'Two, coming to help!'); if (g.wingman.pilot) g.wingman.pilot.order = 'engage'; } break;
      case 'splash': R(g.wingman && g.wingman.alive ? 'wing' : 'awacs', g.wingman && g.wingman.alive ? 'Two, good kill!' : `${cs}, Magic, copy splash.`); break;
      default: break;
    }
  }
  homeBearing() {
    const p = this.g.player, f = this.g.terrain.airfield;
    if (!p) return '000';
    return String(Math.round(((Math.atan2(f.x - p.pos.x, f.y - p.pos.y) / DEG) + 360) % 360)).padStart(3, '0');
  }
  // BRAA: bearing, range (nautical miles), altitude (angels = thousands of feet) and aspect of the nearest group
  picture(short = false) {
    const g = this.g, p = g.player, cs = this.callsign;
    if (!p) return `${cs}, Magic, picture clean.`;
    const foes = g.world.aircraft.filter((a) => a.alive && a.team !== p.team);
    if (!foes.length) return `${cs}, Magic, picture clean.`;
    const nearest = foes.reduce((b, a) => (len(sub(a.pos, p.pos)) < len(sub(b.pos, p.pos)) ? a : b));
    const group = foes.filter((a) => len(sub(a.pos, nearest.pos)) < 8000);
    const rel = sub(nearest.pos, p.pos), brg = Math.round(((Math.atan2(rel.x, rel.y) / DEG) + 360) % 360);
    const nm = Math.max(1, Math.round(len(rel) / 1852)), angels = Math.max(1, Math.round(nearest.pos.z * 3.281 / 1000));
    const toMe = norm(sub(p.pos, nearest.pos)), asp = dot(norm(nearest.vel), toMe);
    const aspect = asp > 0.7 ? 'hot' : asp < -0.5 ? 'cold' : 'flanking';
    const count = group.length > 1 ? `${group.length === 2 ? 'two contacts' : group.length + ' contacts'}, ` : '';
    const n = foes.length > group.length ? ` ${short ? '' : `${foes.length - group.length} more further out.`}` : '';
    return `${cs}, Magic, ${foes.length > group.length ? 'lead group' : 'single group'} BRAA ${String(brg).padStart(3, '0')}, ${nm} miles, angels ${angels}, ${aspect}, ${count}hostile.${n}`;
  }
  // the game's own events (missile launched, kill...): an automatic call from the wingman / AWACS
  event(kind) {
    const g = this.g;
    if (kind === 'wing_fox' && g.wingman && g.wingman.alive) this.say('wing', 'Two, fox three!', 300);
    if (kind === 'wing_splash' && g.wingman && g.wingman.alive) this.say('wing', 'Two, splash one!', 300);
    if (kind === 'wing_defending' && g.wingman && g.wingman.alive) this.say('wing', 'Two, defending, missile inbound!', 200);
  }
}
