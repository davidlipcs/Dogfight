// Career mode: from the recruiting office to command in World War 3.
//   enlist -> kit and centrifuge -> radio class 1 (the tower) -> the back seat of a T-6 (the instructor flies,
//   you talk to the tower) -> primary training on the T-6 (you fly, with clearances) -> radio class 2 (the
//   flight, the fight) -> Air Force or Navy -> T-38C / T-45C -> radio class 3 (AWACS, orders) -> fighter
//   conversion (a dogfight) -> wings -> air policing as a wingman, then as a flight lead -> World War 3.
// In the war: missions at real places (world map), your own flights and the other powers' air forces
// (campaign.js), the pilots you command (roster.js), awards and promotions; at the top, the politics.
import { CALLS, recognise } from './radio.js';
import { School, gearUp } from './school.js';
import { InstructorPilot } from './autopilot.js';
import { Sortie } from './sortie.js';
import { POWERS, FRONTS, QUALITY, NATION_NAMES, newWar, loadWar, saveWar, seenFleet, totalFleet, trustOf, alliedWith, atWar,
  proposeAlliance, proposeCeasefire, simulateDay, aiDiplomacy, applyMission, pickTypes, frontEnemies, changeTrust } from './campaign.js';
import { makeRoster, rating, afterSortie, restDay, portraitUrl, RANKS, STATUS_HU } from './roster.js';
const TODS = [['day', 'nappal'], ['overcast', 'borult'], ['sunset', 'naplemente'], ['night', 'éjszaka']];
const KINDS = { sweep: 'Légtérfölény (sweep)', cap: 'Légtérvédelmi járőr (CAP)' };

const $ = (id) => document.getElementById(id);
const KEY = 'dogfight-career2', ROSTER_KEY = 'dogfight-roster';
const asset = (p) => (window.DOGFIGHT_ASSETS && window.DOGFIGHT_ASSETS[p]) || `assets/${p}`;
const person = (n) => asset(`people/${n}.png`);

const STAGES = [
  { id: 'enlist', name: 'Jelentkezés a légierőhöz' },
  { id: 'gear', name: 'Felszerelés és centrifuga (7 G)' },
  { id: 'class1', name: 'Rádióóra 1 – beszélgetés a toronnyal', lessons: ['radio1', 'radio2'] },
  { id: 'backseat', name: 'Hátsó ülés – T-6A: az oktató repül, te rádiózol' },
  { id: 't6', name: 'Alapképzés – T-6A Texan II: te repülsz' },
  { id: 'class2', name: 'Rádióóra 2 – kötelék és légiharc', lessons: ['radio3', 'radio4'] },
  { id: 'branch', name: 'Fegyvernem: Air Force vagy Navy' },
  { id: 'adv', name: 'Haladó képzés – T-38C Talon / T-45C Goshawk' },
  { id: 'class3', name: 'Rádióóra 3 – AWACS, üzemanyag, parancsok', lessons: ['radio5', 'radio6'] },
  { id: 'bfm', name: 'Vadászgép-átképzés: légiharc egy oktató ellen' },
  { id: 'wings', name: 'Szárnyavatás – hadnagy' },
  { id: 'qra', name: 'Légtérrendészet (Baltikum) – 3 bevetés kísérőként (2-es)' },
  { id: 'qralead', name: 'Kötelékvezető – 2 bevetés vezérként' },
  { id: 'ww3', name: 'A 3. világháború' },
];
const QUIZ = {
  radio_check: 'Beültél, és ellenőriznéd, hall-e a torony.', request_taxi: 'Állsz a parkolóban, gurulni szeretnél a pályához.',
  ready_takeoff: 'A pálya elején állsz, mindennel készen.', airborne: 'Most emelkedtél el a pályáról.', inbound: 'Visszatérsz a bázisra, le akarsz szállni.',
  gear_down: 'A végső egyenesen kiengedted a futóművet – jelentsd.', clear_runway: 'Leszálltál, és lehajtottál a pályáról.', emergency: 'Leállt a hajtómű – vészhelyzet!',
  ack: 'A vezér parancsot adott – nyugtázd (2-esként a válasz: „TWO”).', visual: 'Látod a vezér gépét.', blind: 'Elvesztetted szem elől a vezért.',
  tally: 'Meglátod az ellenséges gépet.', no_joy: 'Nem látod az ellenséget, amit mutatnak.', fox2: 'Hőkövető rakétát indítasz.', fox3: 'Aktív radaros rakétát (AMRAAM) indítasz.',
  guns: 'Gépágyúval tüzelsz.', splash: 'Lelőtted az ellenfelet.', defending: 'Rakéta jön rád, kitérsz.', bingo: 'Annyi üzemanyagod maradt, amennyi a hazaúthoz kell.',
  winchester: 'Elfogyott minden fegyvered.', rtb: 'Hazaindulsz a bázisra.', engage: 'A kísérőd támadja meg az ellenséget.', cover: 'A kísérőd védje a hátadat.',
  rejoin: 'A kísérőd jöjjön vissza alakzatba.', break: 'Rakéta jön a kísérődre – figyelmeztesd, hogy törjön ki.', picture: 'Az AWACS-tól kérdezed, hol az ellenség.',
  checking_in: 'Bejelentkezel az AWACS-nál.',
};

export class CareerMode {
  constructor(launch) {
    this.launch = launch;                       // (opts, place) -> Promise<game>: starts a flight
    this.load();
    this.root = $('career-screen');
  }
  load() {
    try { this.s = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { this.s = null; }
    try { this.roster = JSON.parse(localStorage.getItem(ROSTER_KEY) || 'null'); } catch (e) { this.roster = null; }
    this.war = loadWar();
  }
  save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(this.s));
      if (this.roster) localStorage.setItem(ROSTER_KEY, JSON.stringify(this.roster));
    } catch (e) { /* private mode */ }
    if (this.war) saveWar(this.war);
  }
  get stage() { return this.s ? STAGES.find((x) => x.id === this.s.stage) : STAGES[0]; }
  next() {
    const i = STAGES.findIndex((x) => x.id === this.s.stage);
    this.s.stage = STAGES[Math.min(STAGES.length - 1, i + 1)].id;
    this.save();
  }
  unlockedSet() { return new Set(this.s ? this.s.lessons : []); }
  // a flight: only the radio calls taught so far, your callsign; back here (paused) when it ends
  async go(opts, place) {
    this.root.hidden = true;
    const g = await this.launch({ radioUnlocked: this.unlockedSet(), callsign: `${this.s.callsign} 1-1`, ...opts }, place);
    if (!g) { this.root.hidden = false; this.render(); }
    return g;
  }
  stopFlight() {
    const g = window.game;
    if (!g) return;
    g.inMenu = true; g.pause(); g.showOverlay(null);
    if (g.player) g.player.autopilot = null;
    const t = document.getElementById('tutorial'); if (t) t.hidden = true;
  }
  // ------------------------------------------------------------------ screens
  open() { $('menu').hidden = true; this.root.hidden = false; this.render(); }
  close() { this.root.hidden = true; if (this.onClose) this.onClose(); else $('menu').hidden = false; }
  frame(inner, eyebrow = 'Karrier') {
    this.root.innerHTML = `<div class="card cr-card"><div class="cr-top"><div class="eyebrow">${eyebrow}</div><button type="button" class="small" id="cr-close">✕ Főmenü</button></div>${inner}</div>`;
    $('cr-close').onclick = () => this.close();
  }
  render() {
    if (!this.s) { this.enlist(); return; }
    if (!this.s.alive) { this.memorial(); return; }
    if (this.s.stage === 'ww3' && this.war && this.war.started) { this.warRoom(); return; }
    const cur = STAGES.findIndex((x) => x.id === this.s.stage);
    const rows = STAGES.map((st, i) => `<li class="${i < cur ? 'done' : i === cur ? 'now' : ''}">${i < cur ? '✓' : i === cur ? '▶' : '·'} ${st.name}</li>`).join('');
    this.frame(`<div class="cr-head"><img src="${portraitUrl({ nation: this.s.nation || 'us', portrait: this.s.portrait || 0 })}" alt="">
        <div><h1>${this.s.name} „${this.s.callsign}”</h1><div class="hint">${this.rankName()} · ${this.s.branch ? (this.s.branch === 'navy' ? 'US Navy' : 'US Air Force') : 'pilótanövendék'} · ${this.s.permadeath ? 'valódi halál: BE' : 'valódi halál: ki'}</div>
        <div class="hint">Bevetések: ${this.s.sorties || 0} · lelövések: ${this.s.kills || 0} · rádiófegyelem: ${this.s.radioAvg || '-'}% · kitüntetések: ${(this.s.awards || []).length}</div></div></div>
      <ol class="cr-stages">${rows}</ol>
      <div class="buttons"><button type="button" class="primary" id="cr-go">▶ ${this.stage.name}</button>
      <button type="button" class="small" id="cr-calls">Megtanult rádióhívások (${this.s.lessons.length ? CALLS.filter((c) => this.s.lessons.includes(c.lesson)).length : 0})</button>
      <button type="button" class="small" id="cr-logb">Repülési napló (${(this.s.logbook || []).length})</button>
      <button type="button" class="small" id="cr-reset">Új karrier</button></div>`);
    $('cr-logb').onclick = () => this.logbookScreen();
    $('cr-go').onclick = () => this.play();
    $('cr-calls').onclick = () => this.callsList();
    $('cr-reset').onclick = () => { if (confirm('Biztosan új karriert kezdesz? A mostani elveszik.')) { this.s = null; this.war = null; this.roster = null; localStorage.removeItem(KEY); localStorage.removeItem(ROSTER_KEY); this.render(); } };
  }
  rankName() {
    if (!this.s.rank && !this.s.wings) return 'pilótanövendék';
    return RANKS[this.s.rank || 0];
  }
  enlist() {
    const pick = (i) => `<label class="cr-face"><input type="radio" name="cr-face" value="${i}" ${i === 0 ? 'checked' : ''}><img src="${portraitUrl({ nation: 'us', portrait: i })}" alt=""></label>`;
    this.frame(`<div class="cr-recruit"><img src="${person('general')}" alt="" class="cr-big"><div>
      <h1>Jelentkezés</h1><p>„Szóval vadászpilóta akarsz lenni? Hosszú út: felszerelés, centrifuga, rádió, T-6, aztán a sugárhajtású gyakorló, és csak utána a vadászgép.
      Közben a világ egyre feszültebb… ha kitör a háború, rád is szükség lesz.”</p>
      <div class="opts"><div class="row"><label class="label" for="cr-name">Neved</label><input id="cr-name" type="text" value="${['Kovács Bence', 'John Carter'][0]}"></div>
      <div class="row"><label class="label" for="cr-cs">Hívójeled</label><input id="cr-cs" type="text" value="Viper" maxlength="12"></div>
      <div class="row"><span class="label">Sisak</span><div class="cr-faces">${[0, 1, 2, 3].map(pick).join('')}</div></div>
      <div class="row"><span class="label">Halál</span><label class="hint"><input type="checkbox" id="cr-perma"> <b>Valódi halál</b>: ha lelőnek és nem katapultálsz (Ctrl+E kétszer), a karriered véget ér. Kikapcsolva: kórház, kimaradsz néhány bevetésből.</label></div></div>
      <div class="buttons"><button type="button" class="primary" id="cr-sign">Aláírom ▶</button></div></div></div>`, 'Karrier · toborzóiroda');
    $('cr-sign').onclick = () => {
      const face = Number(document.querySelector('input[name=cr-face]:checked').value);
      this.s = { stage: 'gear', name: $('cr-name').value.trim() || 'Pilóta', callsign: ($('cr-cs').value.trim() || 'Viper').toUpperCase(), permadeath: $('cr-perma').checked,
        nation: 'us', portrait: face, lessons: [], rank: 0, wings: false, branch: null, sorties: 0, kills: 0, awards: [], alive: true, qra: 0, radio: [] };
      this.save(); this.render();
    };
  }
  callsList() {
    const known = CALLS.filter((c) => this.s.lessons.includes(c.lesson));
    this.frame(`<h2>Megtanult rádióhívások</h2><p class="hint">Repülés közben: <kbd>I</kbd> röviden = lista és beírás, <kbd>I</kbd> nyomva tartva = mondd ki (angolul). A hívójel elhagyható.</p>
      <div class="cr-calls">${known.length ? known.map((c) => `<div><b>${c.say}</b> <span>${c.hu}</span> <i>${c.alt.slice(0, 3).join(' · ')}</i></div>`).join('') : '<p>Még egyet sem – a rádióórákon tanulod meg őket.</p>'}</div>
      <div class="buttons"><button type="button" id="cr-back">Vissza</button></div>`);
    $('cr-back').onclick = () => this.render();
  }
  memorial() {
    this.frame(`<div class="cr-recruit"><img src="${person('general')}" alt="" class="cr-big"><div><h1>Hősi halált halt</h1>
      <p>${RANKS[this.s.rank || 0]} ${this.s.name} „${this.s.callsign}” – ${this.s.sorties} bevetés, ${this.s.kills} légi győzelem.</p>
      <p class="hint">${(this.s.awards || []).join(' · ') || ''}</p><p>„Nem katapultált. A szolgálatát sosem felejtjük el.”</p>
      <div class="buttons"><button type="button" class="primary" id="cr-new">Új karrier</button></div></div></div>`, 'Karrier vége');
    $('cr-new').onclick = () => { this.s = null; this.war = null; this.roster = null; localStorage.removeItem(KEY); localStorage.removeItem(ROSTER_KEY); this.render(); };
  }
  // ------------------------------------------------------------------ the stages
  play() {
    const id = this.s.stage;
    if (id === 'gear') { this.root.hidden = true; gearUp((ok) => { if (ok) { this.next(); this.award('Repülőorvosi alkalmasság (7 G)'); } this.root.hidden = false; this.render(); }, null, { portrait: portraitUrl({ nation: this.s.nation || 'us', portrait: this.s.portrait || 0 }), fitter: person('instructor') }); return; }
    if (id.startsWith('class')) { this.classroom(this.stage); return; }
    if (id === 'backseat') { this.backSeat(); return; }
    if (id === 't6') { this.course('t6', 't6'); return; }
    if (id === 'branch') { this.branch(); return; }
    if (id === 'adv') { this.course(this.s.branch === 'navy' ? 't45' : 't38', this.s.branch === 'navy' ? 't45' : 't38'); return; }
    if (id === 'bfm') { this.fly({ kind: 'bfm', role: 'lead', wingman: false, playerType: this.fleetJet(), red: [{ type: this.fleetJet(), n: 1, power: 'us' }], skill: 'easy', title: 'Légiharc-gyakorlat', bearing: 0 }, null, (r) => { if (r.won) { this.next(); this.award('BFM-vizsga'); } this.debrief(r); }); return; }
    if (id === 'wings') { this.wings(); return; }
    if (id === 'qra' || id === 'qralead') { this.qra(id === 'qralead' ? 'lead' : 'wing'); return; }
    if (id === 'ww3') { this.warStart(); return; }
  }
  fleetJet() { return this.s.jet || (this.s.branch === 'navy' ? 'fa18' : 'f16'); }
  // ---- the classroom: the instructor explains the calls, then a test (type or say them)
  classroom(stage) {
    const calls = CALLS.filter((c) => stage.lessons.includes(c.lesson));
    const navy = this.s.branch === 'navy';
    this.frame(`<div class="cr-recruit"><img src="${person(navy ? 'navy_instructor' : 'instructor')}" alt="" class="cr-big"><div>
      <h1>${stage.name}</h1><p>„A rádión röviden, pontosan, angolul beszélünk – mindenki ugyanazt a pár szót használja, így a zajban, rakéták között is értjük egymást.
      Először a hívójel (kinek szólsz), aztán a sajátod, aztán az üzenet. Ezeket kell tudnod:”</p></div></div>
      <div class="cr-calls">${calls.map((c) => `<div><b>${c.say}</b> <span>${c.hu}</span> <i>${c.alt.slice(0, 3).join(' · ')}</i></div>`).join('')}</div>
      <div class="buttons"><button type="button" class="primary" id="cr-test">Vizsga ▶</button><button type="button" id="cr-back">Vissza</button></div>`, 'Karrier · rádióóra');
    $('cr-back').onclick = () => this.render();
    $('cr-test').onclick = () => this.quiz(stage, calls);
  }
  quiz(stage, calls) {
    const qs = calls.filter((c) => QUIZ[c.id]).sort(() => Math.random() - 0.5).slice(0, 6);
    let i = 0, good = 0;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const ask = () => {
      if (i >= qs.length) {
        const pass = good >= Math.ceil(qs.length * 0.7);
        this.frame(`<h2>${pass ? 'Sikeres vizsga!' : 'Ez most nem sikerült'}</h2><p>${good} / ${qs.length} helyes válasz.</p>
          <div class="buttons"><button type="button" class="primary" id="cr-ok">${pass ? 'Tovább ▶' : 'Újra'}</button></div>`, 'Karrier · rádióvizsga');
        $('cr-ok').onclick = () => {
          if (pass) { for (const l of stage.lessons) if (!this.s.lessons.includes(l)) this.s.lessons.push(l); this.next(); this.render(); }
          else this.quiz(stage, calls);
        };
        return;
      }
      const q = qs[i];
      this.frame(`<h2>${i + 1}. kérdés / ${qs.length}</h2><p class="cr-q">${QUIZ[q.id]}</p><p class="hint">Mit mondasz a rádióba? Írd be angolul${SR ? ', vagy nyomd a 🎙 gombot és mondd ki' : ''}.</p>
        <div class="row"><input id="cr-ans" type="text" autocomplete="off" style="flex:1;text-transform:uppercase"> ${SR ? '<button type="button" class="small" id="cr-mic">🎙</button>' : ''}
        <button type="button" class="primary" id="cr-send">Küld</button></div><p id="cr-fb" class="hint"></p>`, 'Karrier · rádióvizsga');
      const check = (text) => {
        const c = recognise(text, CALLS);
        const ok = c && c.id === q.id;
        if (ok) good++;
        $('cr-fb').innerHTML = ok ? '✓ <b>Helyes!</b>' : `✗ A helyes: <b>${q.say}</b> (${q.hu})`;
        $('cr-send').disabled = true;
        setTimeout(() => { i++; ask(); }, ok ? 900 : 2600);
      };
      const box = $('cr-ans');
      box.focus();
      box.onkeydown = (e) => { e.stopPropagation(); if (e.key === 'Enter') check(box.value); };
      $('cr-send').onclick = () => check(box.value);
      if (SR) $('cr-mic').onclick = () => {
        const r = new SR(); r.lang = 'en-US'; r.maxAlternatives = 5;
        r.onresult = (e) => { const alts = [...e.results[0]].map((a) => a.transcript); box.value = alts.find((a) => recognise(a, CALLS)) || alts[0]; check(box.value); };
        r.onerror = () => { $('cr-fb').textContent = 'A mikrofon nem elérhető – írd be.'; };
        try { r.start(); $('cr-fb').textContent = '🎙 Beszélj…'; } catch (e) { /* ignore */ }
      };
    };
    ask();
  }
  // ---- the back seat: the instructor flies the T-6 round the circuit; you make the tower calls on time
  async backSeat() {
    const steps = [
      { phase: 'hold', call: 'request_taxi', say: 'Rendben, kérj gurulási engedélyt a toronytól.' },
      { phase: 'hold', call: 'ready_takeoff', say: 'A pálya elején vagyunk. Mondd, hogy készen állunk a felszállásra.', then: (ap) => setTimeout(() => ap.release(), 2500) },
      { phase: 'climb', call: 'airborne', say: 'Fent vagyunk – jelentsd, hogy a levegőben vagyunk.' },
      { phase: 'downwind', call: 'inbound', say: 'Hátszélben vagyunk, hamarosan leszállunk. Jelentkezz be leszállásra.' },
      { phase: 'base', call: 'gear_down', say: 'Futómű kint, három zöld. Jelentsd a toronynak.', when: (ap) => ap.ac.fm.gearPos > 0.97 },
      { phase: 'stopped', call: 'clear_runway', say: 'Megálltunk. Szólj, hogy elhagytuk a pályát.' },
    ];
    const game = await this.go({ callsign: 'TEXAN 2-1', aircraft: 't6', airStart: false, scenario: 'waves', tutorial: false, wingman: 0, activity: (g) => new BackSeat(g, steps, this.unlockedSet(), (res) => this.afterBackSeat(res)) }, null);
    if (!game) this.render();
  }
  afterBackSeat(res) {
    this.s.radio.push(res.score); this.radioAvg();
    if (res.done) this.next();
    this.debrief({ won: res.done, radio: res.score, title: 'Hátsó ülés – T-6A', text: res.done ? 'Az oktató elégedett: „Szép munka a rádión! Legközelebb te repülsz.”' : 'Megszakadt a repülés.' });
  }
  async course(key) {
    const done = (k, res = {}) => {
      if (res.radio !== undefined) { this.s.radio.push(res.radio); this.radioAvg(); }
      this.next(); this.award(k === 't6' ? 'Alapképzés (T-6A)' : k === 't45' ? 'Haladó képzés + hordozós minősítés (T-45C)' : 'Haladó képzés (T-38C)');
      this.debrief({ won: true, radio: res.radio, title: { t6: 'T-6A Texan II', t38: 'T-38C Talon', t45: 'T-45C Goshawk' }[k] || k, text: 'A tanfolyam kész! Az oktató aláírta a repülési naplódat.' });
    };
    await this.go({ aircraft: key, airStart: false, scenario: 'waves', tutorial: false, wingman: 0, activity: (g) => new School(g, key, done, { radio: true }) }, null);
  }
  branch() {
    this.frame(`<h1>Air Force vagy Navy?</h1><p>Az alapképzés közös. Innen a két fegyvernem útja elválik.</p>
      <div class="cr-branch"><button type="button" class="cr-pick" id="cr-af"><b>US Air Force</b><span>T-38C Talon (szuperszonikus) → F-16C Viper vagy F-35A. Szárazföldi bázisok.</span></button>
      <button type="button" class="cr-pick" id="cr-navy"><b>US Navy</b><span>T-45C Goshawk, leszállás anyahajóra → F/A-18E Super Hornet. Katapult, fékezőkötél.</span></button></div>`, 'Karrier · fegyvernem');
    $('cr-af').onclick = () => { this.s.branch = 'af'; this.s.jet = 'f16'; this.next(); this.render(); };
    $('cr-navy').onclick = () => { this.s.branch = 'navy'; this.s.jet = 'fa18'; this.next(); this.render(); };
  }
  wings() {
    const af = this.s.branch !== 'navy';
    this.frame(`<div class="cr-recruit"><img src="${person('general')}" alt="" class="cr-big"><div><h1>Szárnyavatás</h1>
      <p>„${this.s.name}, a mai naptól ${af ? 'az Egyesült Államok Légierejének' : 'az Egyesült Államok Haditengerészetének'} pilótája vagy. Gratulálok, <b>hadnagy</b>!”</p>
      ${af ? '<p>Melyik gépre kérsz beosztást?</p><div class="cr-branch"><button type="button" class="cr-pick" data-jet="f16"><b>F-16C Viper</b><span>fürge, sokoldalú, a világ legtöbbet gyártott vadásza</span></button><button type="button" class="cr-pick" data-jet="f35"><b>F-35A Lightning II</b><span>lopakodó, a legjobb érzékelők – a jövő gépe</span></button><button type="button" class="cr-pick" data-jet="f15"><b>F-15EX Eagle II</b><span>nagy, gyors, sok rakéta</span></button></div>' : '<div class="buttons"><button type="button" class="primary" data-jet="fa18">Irány a század (F/A-18E) ▶</button></div>'}</div></div>`, 'Karrier · szárnyak');
    for (const b of this.root.querySelectorAll('[data-jet]')) b.onclick = () => { this.s.jet = b.dataset.jet; this.s.wings = true; this.s.rank = 0; this.award('Pilótajelvény (Wings)'); this.next(); this.render(); };
  }
  qra(role) {
    const n = role === 'wing' ? 3 : 2, done = this.s.qra || 0;
    this.ensureRoster();
    const m = { kind: 'intercept', role, playerType: this.fleetJet(), red: [{ type: Math.random() < 0.5 ? 'su35' : 'mig31', n: 1, power: 'ru' }], title: `Légtérrendészet ${done + 1}. / ${n}`, bearing: 70 * Math.PI / 180,
      callsign: `${this.s.callsign} 1-${role === 'wing' ? 2 : 1}`, scramble: true, tod: 'day' };
    const flight = this.autoFlight(role);
    this.applyFlight(m, flight);
    this.fly(m, { lat: 57.6, lon: 24.6, name: 'Baltikum (Észtország)' }, (r) => {
      this.s.sorties++; this.s.radio.push(r.radio); this.radioAvg();
      const fl = this.flightFates(flight, r);
      if (r.won) { this.s.qra = done + 1; if (this.s.qra >= n) { this.s.qra = 0; this.next(); if (role === 'wing') { this.s.rank = 1; this.award('Előléptetés: főhadnagy'); } } }
      if (r.why === 'shot_intruder') { this.s.court = (this.s.court || 0) + 1; }
      this.debrief({ ...r, title: m.title, extra: fl });
    });
  }
  // ---- the people you fly with: pilots of the roster (portrait, call sign, skills)
  ensureRoster() { if (!this.roster) this.roster = makeRoster('us', 240, Math.floor(Math.random() * 1e6)); this.save(); }
  pilot(id) { return (this.roster || []).find((p) => p.id === id); }
  // the squadron assigns them: a good pilot to lead you, a steady one to follow you
  autoFlight(role, n = 1) {
    const ready = (this.roster || []).filter((p) => p.status === 'ready').sort(() => Math.random() - 0.5);
    if (role === 'wing') return { leadId: (ready.sort((a, b) => b.rank - a.rank || rating(b) - rating(a))[0] || {}).id, wingIds: [] };
    return { leadId: null, wingIds: ready.slice(0, n).map((p) => p.id) };
  }
  applyFlight(m, fl) {
    m.flight = fl; m.portraits = {};
    const lead = this.pilot(fl.leadId), wings = (fl.wingIds || []).map((id) => this.pilot(id)).filter(Boolean);
    if (lead) { m.leadName = `${lead.callsign}`; m.leadType = lead.type; m.portraits.lead = portraitUrl(lead); }
    if (wings[0]) { m.wingName = wings[0].callsign; m.wingType = wings[0].type; m.portraits.wing = portraitUrl(wings[0]); m.allySkill = this.skillOf(wings); }
    m.blue = (m.blue || []).filter((b) => !b.pilotId);
    wings.slice(1).forEach((p) => m.blue.push({ type: p.type, n: 1, power: 'us', label: p.callsign, pilotId: p.id }));
    if (!wings.length && !lead) m.wingman = false;
  }
  skillOf(pilots) { const a = pilots.reduce((x, p) => x + rating(p), 0) / Math.max(1, pilots.length); return a > 78 ? 'ace' : a > 66 ? 'hard' : 'normal'; }
  // after the sortie: experience and fate of the pilots who flew with you
  flightFates(fl, r) {
    const ids = [fl.leadId, ...(fl.wingIds || [])].filter(Boolean), out = [];
    const lost = Math.max(0, (r.blueLost || []).length - (r.status === 'ok' ? 0 : 1));
    const others = Math.max(0, (r.redLost || []).length - (r.kills || 0));
    ids.forEach((id, i) => {
      const p = this.pilot(id); if (!p) return;
      const fate = afterSortie(p, { kills: i < others ? 1 : 0, shotDown: i < lost, overEnemy: r.overEnemy });
      const txt = { ok: 'épségben hazatért', kia: '<b>HŐSI HALOTT</b>', pow: 'hadifogságba esett', rescued: 'katapultált, kimentették (sebesült)' }[fate];
      out.push(`<div class="cr-pilot"><img src="${portraitUrl(p)}" alt=""><div><b>${RANKS[p.rank]} ${p.name} „${p.callsign}”</b><span>${txt}</span></div></div>`);
    });
    this.save();
    return out.length ? `<h3>A köteléked</h3><div class="cr-roster">${out.join('')}</div>` : '';
  }
  // ---- launching a flight and the debriefing after it
  async fly(m, place, after) {
    await this.go({ callsign: m.callsign || `${this.s.callsign} 1-1`, aircraft: m.playerType, airStart: false, scenario: 'waves', tutorial: false, wingman: 0, tod: m.tod || 'day',
      portraits: m.portraits || {},
      activity: (g) => new Sortie(g, { ...m, permadeath: this.s.permadeath }, (r) => { this.handleFate(r); this.saveLog(m, r); after(r); }) }, place);
  }
  // the hand written log goes into the pilot's log book
  saveLog(m, r) {
    if (!r.log) return;
    (this.s.logbook = this.s.logbook || []).unshift({ n: this.s.sorties + 1, day: this.war && this.war.started ? this.war.day : null, title: m.title, won: !!r.won, kills: r.kills || 0, status: r.status, scramble: !!r.scramble, text: r.log });
    this.s.logbook = this.s.logbook.slice(0, 200);
    this.save();
  }
  logbookScreen(back) {
    const L = this.s.logbook || [];
    this.frame(`<h2>Repülési napló</h2><p class="hint">A saját kezű jelentéseid, a legutóbbi elöl.</p>
      ${L.length ? L.map((e) => `<div class="logrow"><b>${e.n}. bevetés – ${e.title}</b><span>${e.day ? `${e.day}. nap · ` : ''}${e.scramble ? 'riadó · ' : ''}${e.won ? 'siker' : 'nem sikerült'} · lelövés: ${e.kills}${e.status && e.status !== 'ok' ? ` · ${e.status === 'ejected' ? 'katapultált' : 'lelőtték'}` : ''}</span><p>${String(e.text).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))}</p></div>`).join('') : '<p>Még üres: minden bevetés után be kell adnod a jelentésed.</p>'}
      <div class="buttons"><button type="button" id="cr-back">Vissza</button></div>`, 'Karrier · napló');
    $('cr-back').onclick = () => (back ? back() : this.render());
  }
  handleFate(r) {
    if (r.status === 'shot_down' && this.s.permadeath) { this.s.alive = false; }
    if (r.status === 'shot_down' && !this.s.permadeath) { this.s.hospital = 2; this.award('Purple Heart'); }
    if (r.status === 'ejected') { this.s.ejections = (this.s.ejections || 0) + 1; if (r.overEnemy && Math.random() < 0.4) { this.s.pow = 3; this.award('POW Medal'); } }
    this.s.kills += r.kills || 0;
    this.save();
  }
  radioAvg() { const a = this.s.radio.filter((x) => x !== undefined); this.s.radioAvg = a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : null; this.save(); }
  award(name) { if (!this.s.awards.includes(name)) { this.s.awards.push(name); this.save(); } }
  debrief(r) {
    this.stopFlight();
    $('menu').hidden = true; this.root.hidden = false;
    const fate = !this.s.alive ? '<p><b>Nem katapultáltál – hősi halált haltál.</b></p>'
      : r.status === 'ejected' ? `<p>Katapultáltál – életben vagy, a gép elveszett.${this.s.pow ? ' Ellenséges terület felett értél földet: <b>hadifogságba estél</b> (3 bevetésből kimaradsz).' : ' A mentőhelikopter kimentett.'}</p>`
        : r.status === 'shot_down' ? '<p>Lelőttek – kórházba kerültél (2 bevetésből kimaradsz).</p>' : '';
    this.frame(`<h1>${r.title || 'Jelentés'}: ${r.won ? 'SIKER' : 'nem sikerült'}</h1>${fate}${r.text ? `<p>${r.text}</p>` : ''}
      <div class="stats"><div class="stat"><b>${r.kills || 0}</b><span>lelövés</span></div><div class="stat"><b>${r.radio ?? '-'}%</b><span>rádiófegyelem</span></div>
      <div class="stat"><b>${(r.blueLost || []).length}</b><span>saját veszteség</span></div><div class="stat"><b>${(r.redLost || []).length}</b><span>ellenséges veszteség</span></div></div>
      ${r.extra || ''}<div class="buttons"><button type="button" class="primary" id="cr-cont">Tovább ▶</button></div>`, 'Karrier · jelentés');
    $('cr-cont').onclick = () => this.render();
  }
  // ------------------------------------------------------------------ World War 3
  warStart() {
    if (!this.war) this.war = newWar('us');
    if (!this.roster) this.roster = makeRoster('us', 240, Math.floor(Math.random() * 1e6));
    this.war.started = true;
    this.save();
    this.frame(`<div class="cr-recruit"><img src="${person('general')}" alt="" class="cr-big"><div><h1>Kitört a háború</h1>
      <p>„Hajnalban minden megváltozott. Nincsenek szövetségek: Oroszország, Kína és mi is mindenki mindenki ellen áll. Csak Európa légiereje harcol együtt.
      A bizalmat ki kell érdemelni – ha segítünk nekik, talán mellénk állnak.”</p>
      <p>„Minden nagyhatalomnak megvan a gépszáma. A miénket pontosan ismerjük, a többiekét csak becsüljük. Az nyer, akinek a végén még van légiereje.
      Te most a frontra mész – ${RANKS[this.s.rank || 0]}ként még parancsot kapsz. Ha előléptetnek, te döntesz: hova, kivel, mikor.”</p>
      <div class="buttons"><button type="button" class="primary" id="cr-war">A hadműveleti központba ▶</button></div></div></div>`, 'Karrier · 3. világháború');
    $('cr-war').onclick = () => this.warRoom();
  }
  warRoom() {
    const w = this.war, me = w.player, rank = this.s.rank || 0;
    if (w.over) { this.warEnd(); return; }
    const fleetRow = (id) => {
      const { fleet, exact } = seenFleet(w, id), t = totalFleet(fleet), start = w.powers[id].start;
      return `<div class="cr-power" style="--c:${POWERS[id].colour}"><b>${POWERS[id].name}${w.powers[id].out ? ' – KIESETT' : ''}</b>
        <span>${exact ? '' : '≈'}${t} vadászgép ${exact ? '' : '(becslés)'} · ${Math.round(t / start * 100)}%</span>
        <div class="bar"><i style="width:${Math.min(100, t / start * 100)}%"></i></div>
        <small>${Object.entries(fleet).map(([k, v]) => `${k.toUpperCase()} ${exact ? '' : '~'}${v}`).join(' · ')}</small>
        ${id !== me ? `<small>bizalom: ${Math.round(trustOf(w, me, id))} · ${alliedWith(w, me, id) ? '<b>SZÖVETSÉGES</b>' : atWar(w, me, id) ? 'háborúban' : 'tűzszünet'}</small>` : ''}</div>`;
    };
    const fronts = FRONTS.filter((f) => f.sides.includes(me) && frontEnemies(w, f.id).length);
    const assigned = this.s.assigned && fronts.find((f) => f.id === this.s.assigned) ? this.s.assigned : (fronts[Math.floor(w.day / 3) % Math.max(1, fronts.length)] || {}).id;
    this.s.assigned = assigned;
    const canChoose = rank >= 3, canCommand = rank >= 4, canPolitics = rank >= 5;
    const away = this.s.hospital || this.s.pow;
    const frontBtns = fronts.map((f) => `<button type="button" class="cr-front${f.id === assigned ? ' sel' : ''}" data-front="${f.id}" ${!canChoose && f.id !== assigned ? 'disabled' : ''}>
      <b>${f.name}</b><span>${f.why}</span><small>ellenség: ${frontEnemies(w, f.id).map((x) => POWERS[x].short).join(', ')} · hevesség ${Math.round(w.fronts[f.id].heat * 100)}%</small></button>`).join('');
    this.frame(`<div class="cr-war">
      <div><h2>${w.day}. nap · ${RANKS[rank]} ${this.s.name}</h2>
        <div class="hint">${canChoose ? 'Őrnagyként te választod a frontot.' : `A parancs: ${(FRONTS.find((f) => f.id === assigned) || {}).name}. (Őrnagytól te választhatsz.)`}</div>
        <div class="cr-fronts">${frontBtns}</div>
        <div class="buttons">${away ? `<button type="button" class="primary" id="cr-wait">${this.s.pow ? 'Hadifogságban…' : 'Kórházban…'} (még ${away}) – teljen az idő ▶</button>`
          : `<button type="button" class="primary" id="cr-fly">📋 Parancs és eligazítás: ${(FRONTS.find((f) => f.id === assigned) || {}).name}</button>`}
          <button type="button" id="cr-log">Napló (${(this.s.logbook || []).length})</button>
          ${canCommand ? '<button type="button" id="cr-roster">Pilóták (kiküldés)</button>' : ''}
          ${canPolitics ? '<button type="button" id="cr-politics">Politika</button>' : ''}
          <button type="button" class="small" id="cr-skip">Egy nap telik (pihenő)</button></div>
        <h3>Napló</h3><div class="cr-log">${w.log.slice(0, 12).map((l) => `<div><b>${l.day}.</b> ${l.text}</div>`).join('') || '<div class="hint">még üres</div>'}</div>
      </div>
      <div><h3>Légierők</h3>${Object.keys(POWERS).map(fleetRow).join('')}
        <p class="hint">A saját (és a szövetséges) számokat pontosan látod, a többiekét a hírszerzés becsüli – a felderítő bevetések pontosítják.</p></div>
    </div>`, 'Karrier · hadműveleti központ');
    for (const b of this.root.querySelectorAll('[data-front]')) b.onclick = () => { if (canChoose) { this.s.assigned = b.dataset.front; this.s.order = null; this.save(); this.warRoom(); } };
    if ($('cr-fly')) $('cr-fly').onclick = () => this.briefing(assigned);
    if ($('cr-log')) $('cr-log').onclick = () => this.logbookScreen(() => this.warRoom());
    if ($('cr-wait')) $('cr-wait').onclick = () => { this.passDays(DAYS); if (this.s.hospital) this.s.hospital--; if (this.s.pow) this.s.pow--; this.save(); this.warRoom(); };
    $('cr-skip').onclick = () => { this.passDays(1); this.warRoom(); };
    if ($('cr-roster')) $('cr-roster').onclick = () => this.rosterScreen(assigned);
    if ($('cr-politics')) $('cr-politics').onclick = () => this.politics();
  }
  passDays(n) { for (let i = 0; i < n; i++) { simulateDay(this.war); if (this.war.day % 4 === 0) aiDiplomacy(this.war); if (this.roster) restDay(this.roster); } this.save(); }
  // the order of the day: the front, the enemies there by their real fleets, your flight and help, sized by rank.
  // You do not choose it: it is given to you.  From captain you choose your wingmen, from major the front, the
  // kind of mission, the time of day and the jet - except when the klaxon sounds (an alert is not planned).
  makeOrder(frontId, over = {}) {
    const w = this.war, f = FRONTS.find((x) => x.id === frontId), enemies = frontEnemies(w, frontId), rank = this.s.rank || 0;
    this.ensureRoster();
    const foe = enemies[Math.floor(Math.random() * enemies.length)];
    const big = Math.random() < 0.35 + rank * 0.05;
    const nRed = big ? 4 + Math.floor(Math.random() * 7) : 2 + Math.floor(Math.random() * 2);
    const red = pickTypes(w.powers[foe].fleet, nRed).map((t) => ({ type: t, n: 1, power: foe }));
    const blue = [], nBlue = Math.max(0, nRed - 2 + (rank >= 2 ? 0 : 1));
    for (const t of pickTypes(w.powers.us.fleet, nBlue)) blue.push({ type: t === 'f22' && Math.random() < 0.5 ? 'f15' : t, n: 1, power: 'us', label: 'USAF' });
    for (const id of Object.keys(POWERS)) if (id !== 'us' && alliedWith(w, 'us', id) && f.sides.includes(id)) for (const t of pickTypes(w.powers[id].fleet, 2)) blue.push({ type: t, n: 1, power: id, label: POWERS[id].short });
    const role = rank < 1 ? 'wing' : 'lead';
    return { front: frontId, foe, role, red, blue, rank, skill: ['normal', 'normal', 'hard', 'hard', 'ace', 'ace', 'ace'][rank], minutes: 8, bearing: Math.random() * Math.PI * 2,
      kind: over.kind || (Math.random() < 0.3 ? 'cap' : 'sweep'), jet: over.jet || this.fleetJet(), tod: over.tod || 'day',
      scramble: over.scramble !== undefined ? over.scramble : Math.random() < 0.3, flight: this.autoFlight(role, 1) };
  }
  order(frontId) {
    if (!this.s.order || this.s.order.front !== frontId) { this.s.order = this.makeOrder(frontId); this.save(); }
    return this.s.order;
  }
  missionOf(o) {
    const f = FRONTS.find((x) => x.id === o.front);
    const m = { kind: o.kind, role: o.role, playerType: o.jet, red: o.red, blue: o.blue.map((b) => ({ ...b })), skill: o.skill, minutes: o.minutes, bearing: o.bearing, front: o.front,
      title: `${f.name}: ${o.red.length} ${POWERS[o.foe].short} gép`, callsign: `${this.s.callsign} 1-${o.role === 'wing' ? 2 : 1}`, scramble: o.scramble, tod: o.tod };
    this.applyFlight(m, o.flight);
    return m;
  }
  crewHtml(o) {
    const row = (p, label) => p ? `<div class="cr-pilot"><img src="${portraitUrl(p)}" alt=""><div><b>${label}: ${RANKS[p.rank]} ${p.name} „${p.callsign}”</b><span>${p.type.toUpperCase()} · közelharc ${p.dogfight} · rakétás ${p.bvr} · idegek ${p.nerve}</span></div></div>` : '';
    return row(this.pilot(o.flight.leadId), 'Vezér') + (o.flight.wingIds || []).map((id) => row(this.pilot(id), 'Kísérő')).join('');
  }
  briefing(frontId) {
    const o = this.order(frontId), w = this.war, f = FRONTS.find((x) => x.id === o.front), rank = this.s.rank || 0;
    const jetName = (k) => k.toUpperCase();
    const redTxt = [...new Set(o.red.map((r) => r.type))].map((t) => t.toUpperCase()).join(', ');
    const canWing = rank >= 2 && !o.scramble, canPlan = rank >= 3 && !o.scramble;
    this.frame(`<div class="cr-recruit"><img src="${person('general')}" alt="" class="cr-big"><div>
      <h1>${o.scramble ? '🚨 RIADÓ!' : 'Parancs'}</h1>
      <p><b>${f.name}</b> – ${f.why}</p>
      ${o.scramble ? '<p>„Nincs idő a részletekre! Az ellenség már úton van. <b>Fuss a gépedhez</b>, a kifutó mellett áll, járatva. Indulj, a többit rádión kapod.”</p>'
        : `<p>Feladat: <b>${KINDS[o.kind]}</b> · ellenség: <b>${o.red.length} gép</b> (${o.foe ? POWERS[o.foe].short : ''}: ~${redTxt}) · ${TODS.find((t) => t[0] === o.tod)[1]}</p>
           <p>A gépeden (<b>${jetName(o.jet)}</b>) előbb fel kell venned a felszerelést, át kell vizsgálnod a kabinban mindent, engedélyt kérsz a toronytól, és csak aztán szállsz fel. Hazafelé le kell szállnod, és a bevetés végén kézzel írt jelentést adsz le.</p>`}
      ${this.crewHtml(o)}
      <div class="buttons"><button type="button" class="primary" id="cr-go2">${o.scramble ? '🚨 Futás a géphez' : '▶ Indulás a felszereléshez'}</button>
        ${canWing ? '<button type="button" id="cr-wingmen">Kísérők kiválasztása</button>' : ''}
        ${canPlan ? '<button type="button" id="cr-plan">Tervezés: hely, idő, gép</button>' : ''}
        <button type="button" class="small" id="cr-back">Vissza</button></div>
      ${rank < 2 ? '<p class="hint">Századostól te választhatod a kísérőidet, őrnagytól a helyet, az időpontot és a gépet is.</p>' : ''}</div></div>`, 'Karrier · eligazítás');
    $('cr-go2').onclick = () => this.startOrder(o);
    $('cr-back').onclick = () => this.warRoom();
    if ($('cr-wingmen')) $('cr-wingmen').onclick = () => this.wingScreen(o);
    if ($('cr-plan')) $('cr-plan').onclick = () => this.planScreen(o);
    void w;
  }
  startOrder(o) {
    const f = FRONTS.find((x) => x.id === o.front), m = this.missionOf(o);
    this.fly(m, { lat: f.lat, lon: f.lon, name: f.name }, (r) => { this.s.order = null; this.afterWarMission(m, o.foe, r, o.flight); });
  }
  // rank 2+: pick the pilots who fly with you
  wingScreen(o) {
    const R = this.roster, kind = o.kind === 'cap' ? 'cap' : 'sweep', max = 3;
    this.pickedW = this.pickedW || new Set(o.flight.wingIds || []);
    const ready = R.filter((p) => p.status === 'ready').sort((a, b) => rating(b, kind) - rating(a, kind));
    const row = (p) => `<label class="cr-pilot${this.pickedW.has(p.id) ? ' sel' : ''}"><input type="checkbox" data-wid="${p.id}" ${this.pickedW.has(p.id) ? 'checked' : ''}>
      <img src="${portraitUrl(p)}" alt=""><div><b>${RANKS[p.rank]} ${p.name} „${p.callsign}”</b><span>${NATION_NAMES[p.nation]} · ${p.type.toUpperCase()} · ${p.sorties} bevetés · ${p.kills} győzelem</span>
      <span>közelharc ${p.dogfight} · rakétás ${p.bvr} · idegek ${p.nerve} · fáradtság ${Math.round(p.fatigue * 100)}% · <b>${rating(p, kind)}</b></span></div></label>`;
    this.frame(`<h2>Kísérők kiválasztása</h2><p class="hint">Legfeljebb ${max} pilóta repül veled. A legjobb választás a feladattól függ (légtérfölényhez a közelharcosok, járőrhöz a higgadtak). ${this.pickedW.size} kiválasztva.</p>
      <div class="buttons"><button type="button" class="primary" id="cr-ok">Kész ▶</button><button type="button" id="cr-best">A legjobb ${max}</button></div>
      <div class="cr-roster">${ready.slice(0, 60).map(row).join('')}</div>`, 'Karrier · kísérők');
    for (const c of this.root.querySelectorAll('[data-wid]')) c.onchange = () => {
      const id = Number(c.dataset.wid);
      if (c.checked) { if (this.pickedW.size >= max) { c.checked = false; return; } this.pickedW.add(id); } else this.pickedW.delete(id);
      this.wingScreen(o);
    };
    $('cr-best').onclick = () => { this.pickedW = new Set(ready.slice(0, max).map((p) => p.id)); this.wingScreen(o); };
    $('cr-ok').onclick = () => { o.flight = { leadId: null, wingIds: [...this.pickedW] }; this.pickedW = null; this.save(); this.briefing(o.front); };
  }
  // rank 3+: where, what kind, when, with what
  planScreen(o) {
    const w = this.war, me = w.player;
    const fronts = FRONTS.filter((f) => f.sides.includes(me) && frontEnemies(w, f.id).length);
    const jets = ['f16', 'f35', 'fa18', 'f15', 'f22'].filter((k) => (w.powers.us.fleet[k] || 0) > 0);
    const opt = (name, val, cur, text) => `<label class="cr-chip"><input type="radio" name="${name}" value="${val}" ${cur === val ? 'checked' : ''}><span>${text}</span></label>`;
    this.frame(`<h2>Tervezés</h2><p class="hint">Őrnagyként te döntesz: hova, milyen feladatra, mikor és mivel megyünk.</p>
      <h3>Hova</h3><div class="cr-chips">${fronts.map((f) => opt('front', f.id, o.front, `${f.name} <small>(hevesség ${Math.round(w.fronts[f.id].heat * 100)}%)</small>`)).join('')}</div>
      <h3>Feladat</h3><div class="cr-chips">${Object.entries(KINDS).map(([k, t]) => opt('kind', k, o.kind, t)).join('')}</div>
      <h3>Mikor</h3><div class="cr-chips">${TODS.map(([k, t]) => opt('tod', k, o.tod, t)).join('')}</div>
      <h3>Mivel</h3><div class="cr-chips">${jets.map((k) => opt('jet', k, o.jet, `${k.toUpperCase()} <small>(raktáron: ${w.powers.us.fleet[k]})</small>`)).join('')}</div>
      <div class="buttons"><button type="button" class="primary" id="cr-ok">Jóváhagyom ▶</button><button type="button" id="cr-back">Mégse</button></div>`, 'Karrier · tervezés');
    const val = (n) => (this.root.querySelector(`input[name=${n}]:checked`) || {}).value;
    $('cr-back').onclick = () => this.briefing(o.front);
    $('cr-ok').onclick = () => {
      const front = val('front') || o.front;
      const n = front === o.front ? o : this.makeOrder(front, { scramble: false });
      n.kind = val('kind') || o.kind; n.tod = val('tod') || o.tod; n.jet = val('jet') || o.jet; n.scramble = false;
      if (front !== o.front) { n.flight = o.flight; this.s.assigned = front; }
      this.s.order = n; this.save(); this.briefing(front);
    };
  }
  afterWarMission(m, foe, r, flight) {
    const w = this.war;
    const losses = { [foe]: {}, us: {} };
    for (const t of r.redLost) losses[foe][t] = (losses[foe][t] || 0) + 1;
    for (const t of r.blueLost) losses.us[t] = (losses.us[t] || 0) + 1;
    const trust = {};
    for (const b of m.blue) if (b.power !== 'us') trust[b.power] = (trust[b.power] || 0) + (r.won ? 4 : 1);
    if (!m.blue.some((b) => b.power === 'eu') && FRONTS.find((f) => f.id === m.front).sides.includes('eu') && r.won) trust.eu = 3;   // you helped Europe's front
    applyMission(w, { losses, front: m.front, won: r.won, trust, trustWhy: 'közös harc a fronton', intel: 0.02 });
    this.passDays(DAYS);
    this.s.sorties++; this.s.radio.push(r.radio); this.radioAvg();
    // awards and promotions
    const extra = [];
    if (r.kills >= 3) { this.award('Silver Star'); extra.push('Silver Star – 3 légi győzelem egy bevetésen'); }
    if (r.kills >= 5) { this.award('Medal of Honor'); extra.push('Medal of Honor – 5 győzelem egy bevetésen!'); }
    if (this.s.kills >= 5 && !this.s.awards.includes('ÁSZ')) { this.award('ÁSZ'); extra.push('ÁSZ – 5 légi győzelem'); }
    if (this.s.sorties % 5 === 0) { this.award(`Air Medal (${this.s.sorties} bevetés)`); }
    if (r.won && m.red.length >= 8) { this.award('Distinguished Flying Cross'); extra.push('Distinguished Flying Cross – győzelem túlerő ellen'); }
    const promoteAt = [0, 3, 8, 14, 22, 32, 45];
    const score = this.s.sorties + this.s.kills * 2;
    while ((this.s.rank || 0) < 6 && score >= promoteAt[(this.s.rank || 0) + 1]) { this.s.rank = (this.s.rank || 0) + 1; extra.push(`ELŐLÉPTETÉS: ${RANKS[this.s.rank]}${this.s.rank === 2 ? ' – mostantól te választod a kísérőidet' : this.s.rank === 3 ? ' – mostantól te választod a helyet, az időpontot és a gépet' : this.s.rank === 4 ? ' – pilótákat küldhetsz ki' : this.s.rank === 5 ? ' – politikai döntések' : ''}`); }
    this.save();
    if (r.scramble && r.scrambleSec != null) extra.push(r.scrambleSec <= 150 ? `Riadó → felszállás: ${r.scrambleSec} s – gyors reakció!` : `Riadó → felszállás: ${r.scrambleSec} s – lassú volt.`);
    this.debrief({ ...r, title: m.title, extra: extra.map((e) => `<p class="cr-award">🎖 ${e}</p>`).join('') + (flight ? this.flightFates(flight, r) : '') });
  }
  // ---- the pilots: pick who flies a mission you do not fly yourself
  rosterScreen(frontId) {
    const R = this.roster, kind = 'sweep';
    const ready = R.filter((p) => p.status === 'ready').sort((a, b) => rating(b, kind) - rating(a, kind));
    this.picked = this.picked || new Set();
    const row = (p) => `<label class="cr-pilot${this.picked.has(p.id) ? ' sel' : ''}"><input type="checkbox" data-pid="${p.id}" ${this.picked.has(p.id) ? 'checked' : ''}>
      <img src="${portraitUrl(p)}" alt=""><div><b>${RANKS[p.rank]} ${p.name} „${p.callsign}”</b><span>${NATION_NAMES[p.nation]} · ${p.type.toUpperCase()} · ${p.sorties} bevetés · ${p.kills} győzelem</span>
      <span>közelharc ${p.dogfight} · rakétás ${p.bvr} · idegek ${p.nerve} · fáradtság ${Math.round(p.fatigue * 100)}% · <b>${rating(p, kind)}</b></span></div></label>`;
    const lost = R.filter((p) => p.status !== 'ready');
    this.frame(`<h2>Pilóták – kiküldés: ${(FRONTS.find((f) => f.id === frontId) || {}).name}</h2>
      <p class="hint">Válassz ki 2–8 pilótát. A pontszám a légtérfölény-bevetéshez való alkalmasságuk (a fáradtság rontja). ${this.picked.size} kiválasztva.</p>
      <div class="buttons"><button type="button" class="primary" id="cr-send" ${this.picked.size < 2 ? 'disabled' : ''}>Kiküldöm őket ▶</button><button type="button" id="cr-best">A 4 legjobb</button><button type="button" id="cr-back">Vissza</button></div>
      <div class="cr-roster">${ready.slice(0, 60).map(row).join('')}</div>
      <p class="hint">Nem bevethető: ${lost.length} (${['wounded', 'pow', 'kia'].map((s) => `${STATUS_HU[s]}: ${lost.filter((p) => p.status === s).length}`).join(', ')})</p>`, 'Karrier · pilóták');
    for (const c of this.root.querySelectorAll('[data-pid]')) c.onchange = () => { const id = Number(c.dataset.pid); if (c.checked) this.picked.add(id); else this.picked.delete(id); this.rosterScreen(frontId); };
    $('cr-best').onclick = () => { this.picked = new Set(ready.slice(0, 4).map((p) => p.id)); this.rosterScreen(frontId); };
    $('cr-back').onclick = () => this.warRoom();
    $('cr-send').onclick = () => this.sendFlight(frontId, R.filter((p) => this.picked.has(p.id)));
  }
  // a mission flown by the AI pilots: their ratings against the enemy's quality decide it
  sendFlight(frontId, pilots) {
    const w = this.war, enemies = frontEnemies(w, frontId), foe = enemies[Math.floor(Math.random() * enemies.length)];
    const nRed = Math.max(2, pilots.length + Math.floor(Math.random() * 3) - 1);
    const reds = pickTypes(w.powers[foe].fleet, nRed);
    const ours = pilots.reduce((s, p) => s + rating(p) * (QUALITY[p.type] || 6), 0);
    const theirs = reds.reduce((s, t) => s + (QUALITY[t] || 6) * 55 * POWERS[foe].skill, 0);
    const p = ours / (ours + theirs), out = [];
    let redLost = 0, blueLost = 0;
    const losses = { [foe]: {}, us: {} };
    for (const t of reds) if (Math.random() < p * 0.75) { redLost++; losses[foe][t] = (losses[foe][t] || 0) + 1; }
    for (const pl of pilots) {
      const kills = redLost > 0 && Math.random() < p ? 1 : 0;
      const shotDown = Math.random() < (1 - p) * 0.45;
      if (shotDown) { blueLost++; losses.us[pl.type] = (losses.us[pl.type] || 0) + 1; }
      const fate = afterSortie(pl, { kills, shotDown, overEnemy: Math.random() < 0.5 });
      out.push(`<div class="cr-pilot"><img src="${portraitUrl(pl)}" alt=""><div><b>${pl.name} „${pl.callsign}”</b><span>${kills ? `${kills} győzelem · ` : ''}${{ ok: 'épségben hazatért', kia: 'HŐSI HALOTT', pow: 'hadifogságba esett', rescued: 'katapultált, kimentették (sebesült)' }[fate]}</span></div></div>`);
    }
    applyMission(w, { losses, front: frontId, won: redLost > blueLost });
    this.passDays(DAYS);
    this.picked = new Set();
    this.save();
    this.frame(`<h2>Jelentés – ${(FRONTS.find((f) => f.id === frontId) || {}).name}</h2>
      <p>${pilots.length} gépünk ${reds.length} ${POWERS[foe].short} vadász ellen: <b>${redLost}</b> ellenséges és <b>${blueLost}</b> saját gép veszett oda.</p>
      <div class="cr-roster">${out.join('')}</div><div class="buttons"><button type="button" class="primary" id="cr-back">Vissza a központba</button></div>`, 'Karrier · jelentés');
    $('cr-back').onclick = () => this.warRoom();
  }
  // ---- politics (colonel and above): alliances, ceasefires, strikes on the factories
  politics() {
    const w = this.war, me = w.player;
    const others = Object.keys(POWERS).filter((id) => id !== me && !w.powers[id].out);
    this.frame(`<h2>Politika és stratégia</h2><p class="hint">Ezredesként már te is ott ülsz, ahol a döntések születnek. A szövetséghez legalább 60-as bizalom kell.</p>
      ${others.map((id) => `<div class="cr-power" style="--c:${POWERS[id].colour}"><b>${POWERS[id].name}</b><small>bizalom: ${Math.round(trustOf(w, me, id))} · ${alliedWith(w, me, id) ? 'SZÖVETSÉGES' : atWar(w, me, id) ? 'háborúban' : 'tűzszünet'}</small>
        <div class="buttons">${!alliedWith(w, me, id) ? `<button type="button" class="small" data-ally="${id}">Szövetség ajánlása</button>` : ''}
        ${atWar(w, me, id) ? `<button type="button" class="small" data-cease="${id}">Tűzszünet</button><button type="button" class="small" data-strike="${id}">Csapás a repülőgépgyárakra</button>` : ''}
        ${!atWar(w, me, id) && !alliedWith(w, me, id) ? `<button type="button" class="small" data-aid="${id}">Segítség küldése (+bizalom)</button>` : ''}</div></div>`).join('')}
      <p id="cr-pmsg" class="cr-award"></p><div class="buttons"><button type="button" id="cr-back">Vissza</button></div>`, 'Karrier · politika');
    const msg = (t) => { $('cr-pmsg').textContent = t; this.save(); };
    for (const b of this.root.querySelectorAll('[data-ally]')) b.onclick = () => { msg(proposeAlliance(w, me, b.dataset.ally).text); setTimeout(() => this.politics(), 1600); };
    for (const b of this.root.querySelectorAll('[data-cease]')) b.onclick = () => { msg(proposeCeasefire(w, me, b.dataset.cease).text); setTimeout(() => this.politics(), 1600); };
    for (const b of this.root.querySelectorAll('[data-aid]')) b.onclick = () => { changeTrust(w, me, b.dataset.aid, 8, 'segítséget küldtünk'); w.powers[me].fleet.f16 = Math.max(0, (w.powers[me].fleet.f16 || 0) - 6); msg('6 F-16-ot átadtunk – nő a bizalom.'); setTimeout(() => this.politics(), 1600); };
    for (const b of this.root.querySelectorAll('[data-strike]')) b.onclick = () => {
      const id = b.dataset.strike, cost = 4 + Math.floor(Math.random() * 6);
      w.powers[me].fleet.f15 = Math.max(0, (w.powers[me].fleet.f15 || 0) - Math.min(cost, 2)); w.powers[me].fleet.f16 = Math.max(0, (w.powers[me].fleet.f16 || 0) - cost);
      applyMission(w, { strike: id, losses: {} }); msg(`A csapás sikerült: ${POWERS[id].name} gyártása visszaesett – ${cost} gépünk nem tért vissza.`); setTimeout(() => this.politics(), 1800);
    };
    $('cr-back').onclick = () => this.warRoom();
  }
  warEnd() {
    const w = this.war, won = w.over.player;
    if (won) this.award('Győzelem a 3. világháborúban');
    this.frame(`<div class="cr-recruit"><img src="${person('general')}" alt="" class="cr-big"><div><h1>${won ? 'GYŐZELEM' : 'VERESÉG'}</h1>
      <p>${w.over.day}. nap. ${won ? 'Az ellenség légiereje megsemmisült. Vége a háborúnak.' : 'A légierőnk elfogyott. A háború a mi vereségünkkel ért véget.'}</p>
      <p>${RANKS[this.s.rank || 0]} ${this.s.name}: ${this.s.sorties} bevetés, ${this.s.kills} légi győzelem.</p><p class="hint">${this.s.awards.join(' · ')}</p>
      <div class="buttons"><button type="button" class="primary" id="cr-new">Új háború</button></div></div></div>`, 'Karrier · a háború vége');
    $('cr-new').onclick = () => { this.war = newWar('us'); this.war.started = true; this.save(); this.warRoom(); };
  }
}
const DAYS = 2;

// ------------------------------------------------------------------ the back seat flight
class BackSeat {
  constructor(game, steps, unlocked, onEnd) {
    this.g = game; this.steps = steps; this.i = 0; this.onEnd = onEnd; this.wait = 0; this.made = 0; this.late = 0; this.hinted = false;
    game.radio.unlocked = unlocked; game.radio.callsign = 'TEXAN 2-1';
    const p = game.player;
    this.ap = new InstructorPilot(p, game.terrain.airfield, { onPhase: () => this.prompt() });
    p.autopilot = this.ap;
    game.cam.cockpit = true;
    this.off = game.radio.onCall((call) => this.heard(call));
    this.panel = document.getElementById('tutorial'); this.panel.hidden = false;
    this.prompt();
  }
  get step() { return this.steps[this.i]; }
  prompt() {
    const s = this.step;
    if (!s || this.ap.phase !== s.phase || this.asked === this.i || (s.when && !s.when(this.ap))) return;
    this.asked = this.i; this.wait = 0; this.hinted = false;
    this.g.radio.say('instructor', s.say, 600, false);
    this.render();
  }
  heard(call) {
    const s = this.step;
    if (!s) return;
    if (call.id === s.call && this.ap.phase === s.phase) {
      this.made++;
      if (s.then) s.then(this.ap);
      this.i++;
      if (this.i >= this.steps.length) { setTimeout(() => this.end(true), 3000); this.render(); return; }
      this.prompt();
      this.render();
    } else if (this.ap.phase === s.phase) this.g.radio.say('instructor', 'Nem ezt kell most mondani – gondold át!', 300, false);
  }
  update(dt) {
    if (!this.step) return;
    if (this.ap.phase !== this.step.phase) return;
    this.prompt();
    if (this.asked !== this.i) return;          // the instructor has not asked yet
    this.wait += dt;
    if (this.wait > 25 && !this.hinted) {
      this.hinted = true; this.late++;
      const c = CALLS.find((x) => x.id === this.step.call);
      this.g.radio.say('instructor', `Segítek: azt mondd, hogy „${c.say}”. (I gomb)`, 0, false);
    }
    if (this.step.phase === 'hold' && this.wait > 60 && this.step.call === 'ready_takeoff') { this.heard({ id: 'ready_takeoff' }); }
  }
  onEvent() {}
  enter() {}
  respawn() { this.end(false); }
  end(done) {
    if (this.ended) return;
    this.ended = true;
    if (this.off) this.off();
    this.panel.hidden = true;
    this.g.player.autopilot = null; this.g.tutorial = null;
    const score = Math.round(100 * this.made / Math.max(1, this.made + this.late));
    this.onEnd({ done, score });
  }
  render() {
    const s = this.step;
    this.panel.innerHTML = `<div class="tut-head"><span>Hátsó ülés · ${Math.min(this.i + 1, this.steps.length)} / ${this.steps.length}</span></div>
      <h3>Te rádiózol, az oktató repül</h3><p>Hallgasd az oktatót, és amikor kéri, szólj a toronynak: <kbd>I</kbd> röviden = lista / beírás, nyomva tartva = mondd ki.</p>
      <div class="tut-task ${s ? '' : 'done'}"><b>${s ? 'FELADAT' : 'KÉSZ'}</b>${s ? `Várj az oktató kérésére (most: ${{ hold: 'a földön', climb: 'emelkedés', downwind: 'hátszél', base: 'bázisforduló', stopped: 'megállva' }[s.phase] || s.phase})` : 'Szép munka!'}</div>`;
  }
}
