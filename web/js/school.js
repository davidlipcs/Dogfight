// Career: the road of a US military pilot, as the real one goes (sources: AETC / CNATRA):
//   1. kit and centrifuge - G-suit, harness, helmet, oxygen mask; then +7 G for 15 s with the anti-G straining
//      manoeuvre (AGSM), the NATO standard (AAMedP-1.13 / STANAG 3827)
//   2. primary training on the T-6 Texan II - the same for Air Force and Navy students
//   3. the choice: Air Force or Navy
//   4. advanced: Air Force on the T-38C Talon (supersonic), Navy on the T-45C Goshawk with carrier qualification
//   5. wings - and the fleet jet: F-16C Viper (Air Force) or F/A-18E Super Hornet (Navy)
//   6. World War 3 (ww3.js)
import { V, add, sub, mul, len, norm, qheading, qlook, DEG } from './util.js';
import { Race } from './race.js';

const $ = (id) => document.getElementById(id);
const KEY = 'dogfight-path';
const k = (t) => `<kbd>${t}</kbd>`;

export function loadPath() {
  const p = { gear: false, t6: false, branch: null, adv: false, wings: false, ww3: 0 };
  try { Object.assign(p, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* private mode */ }
  return p;
}
export function savePath(p) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* private mode */ } }

// ------------------------------------------------------------------ lessons
const takeoff = (extra = '') => ({
  title: 'Felszállás',
  text: `<p>A gép a kifutó elején áll. Tartsd a ${k('Shift')}-et (teljes gáz)${extra}, és amikor a sebesség eléri a felemelkedési
    sebességet, emeld az egeret (vagy ${k('S')}). 150 m felett húzd be a futóművet: ${k('G')}.</p>`,
  task: 'Szállj fel, és húzd be a futóművet',
  check: (s) => !s.p.onGround && s.agl > 150 && s.p.fm.gearPos < 0.1,
});
const rings = (n, text) => ({
  title: `Útvonal: ${n} gyűrű`, text: `<p>${text} A következő gyűrűt a borostyán kör mutatja a HUD-on.</p>`,
  task: `Repülj át mind a ${n} gyűrűn`, setup: (s) => s.startRings(n), check: (s) => s.race && s.race.finished,
  status: (s) => (s.race ? `${s.race.next} / ${n} gyűrű` : ''),
});
const gturn = (g, secs) => ({
  title: `${g} G-s forduló`,
  text: `<p>Dönts be 60–80°-ra, és húzd az egeret magad felé (vagy ${k('S')}). Tartsd a terhelést ${g} G felett ${secs} másodpercig –
    a G-ruha közben felfújódik a lábadon. Figyeld a HUD-on a ${k('G')} értéket.</p>`,
  task: `Tarts ${g} G-t ${secs} másodpercig`,
  check: (s, dt) => { s.flags.g = s.p.fm.gLoad >= g ? (s.flags.g || 0) + dt : Math.max(0, (s.flags.g || 0) - dt * 2); return s.flags.g >= secs; },
  status: (s) => `G ${s.p.fm.gLoad.toFixed(1)} · ${Math.min(secs, s.flags.g || 0).toFixed(1)} / ${secs} s`,
});
const land = {
  title: 'Leszállás a bázison',
  text: `<p>Repülj vissza a bázisra (cián négyzet a HUD-on). ${k('G')} = futómű ki, ~270 km/h, lassú süllyedés (4 m/s alatt), egyenes
    szárnyak. A földön ${k('B')} = fék.</p>`,
  task: 'Szállj le, és állj meg a betonon',
  check: (s) => s.p.onGround && s.p.speed < 4 && s.g.terrain.airfield.onPaved(s.p.pos.x, s.p.pos.y) && !s.g.carrier.onDeck(s.p.pos.x, s.p.pos.y),
};
const COURSES = {
  t6: {
    name: 'Alapképzés – T-6A Texan II', short: 'T-6A',
    intro: `A T-6A Texan II légcsavaros gyakorlógép: ezen tanul repülni az Air Force és a Navy minden pilótanövendéke. 1100 lóerős
      turbólégcsavaros hajtómű, ~520 km/h, +7 G. Lassú és kezes – itt tanulod meg az alapokat.`,
    steps: [takeoff(), rings(6, 'Egy rövid útvonal a bázis körül.'), gturn(4, 4), land],
  },
  t38: {
    name: 'Haladó képzés (Air Force) – T-38C Talon', short: 'T-38C',
    intro: `A T-38C Talon az Air Force szuperszonikus gyakorló sugárhajtású gépe: két J85-ös hajtómű utánégetővel, Mach 1,08,
      720°/s-os orsózás. Ezzel készülsz fel a vadászgépekre (most érkezik az utódja, a T-7A Red Hawk).`,
    steps: [takeoff(' – a 100% után még egy Shift = utánégető'), rings(8, 'Alacsony útvonal a dombok között.'),
      { title: 'Hangsebesség', text: `<p>Emelkedj 6–8 km-re, kapcsold be az utánégetőt, és enyhe zuhanásban gyorsíts át 1,0 Mach fölé. A HUD-on az ${k('M')} sor
        mutatja. Ez az első szuperszonikus repülésed!</p>`, task: 'Érd el a Mach 1,0-t', check: (s) => s.p.fm.mach >= 1.0,
        status: (s) => `M ${s.p.fm.mach.toFixed(2)}` },
      gturn(5, 5), land],
  },
  t45: {
    name: 'Haladó képzés (Navy) – T-45C Goshawk', short: 'T-45C',
    intro: `A T-45C Goshawk a Navy hordozóképes gyakorlógépe (a brit Hawk alapján): megerősített futómű, fékezőhorog. A képzés
      csúcsa a hordozós minősítés (Carrier Qualification): leszállás a fékezőkötélre és katapultos felszállás.`,
    steps: [takeoff(), rings(8, 'Útvonal a tenger felé.'), gturn(5, 5),
      { title: 'Hordozós leszállás (CQ)', spawn: (s) => s.approach(),
        text: `<p>A hordozó mögött vagy, 6 km-re. A <b>MEATBALL</b> jelző (jobbra) mutatja a siklópályát: a sárga gömb a zöld vonal
          felett = túl magasan, alatta = túl alacsonyan. „BALRA / JOBBRA” = igazodj a ferde leszállófedélzethez (351°).</p>
          <p>Futómű kint, ~250 km/h, egyenletes süllyedés. A fedélzeten a fékezőhorog beakad a kötélbe (a 3. a legjobb). Ha nem
          akad be (BOLTER): teljes gáz és újra!</p>`,
        task: 'Szállj le a hordozóra fékezőkötéllel', setup: (s) => s.approach(), check: (s) => s.flags.trap },
      { title: 'Katapultos felszállás', text: `<p>A fedélzeti személyzet a katapulthoz vontatott. Adj teljes gázt (${k('Shift')} tartva),
          és a katapult 2,5 másodperc alatt kilő. Utána húzd fel az orrot, és ${k('G')} = futómű be.</p>`,
        task: 'Indulj el a katapultról', check: (s) => s.flags.cat },
    ],
  },
};

// career (radio: true): before the take-off the tower has to clear you, and before the landing too
const clearance = {
  title: 'Engedély a toronytól',
  text: `<p>Mielőtt egy métert is gurulnál, a toronnyal beszélsz. Nyomd meg röviden az ${k('I')}-t (lista, beírás – vagy a szám),
    vagy tartsd nyomva, és mondd ki angolul:</p><ol><li><b>REQUEST TAXI</b> – gurulási engedély</li><li><b>READY FOR TAKEOFF</b> – a pálya elején, felszállási engedély</li></ol>
    <p>A torony válaszát a bal felső sarokban olvasod és hallod. Engedély nélkül felszállni szabálysértés!</p>`,
  task: 'Kérj gurulást, majd felszállási engedélyt',
  check: (s) => s.rf.taxi && s.rf.takeoff,
  status: (s) => `gurulás ${s.rf.taxi ? '✓' : '·'} · felszállás ${s.rf.takeoff ? '✓' : '·'}`,
};
const landRadio = {
  ...land,
  text: `${land.text}<p><b>Rádió:</b> a bázis felé jövet <b>INBOUND FOR LANDING</b>, a végső egyenesen futóművel <b>GEAR DOWN</b>
    (a torony így ad leszállási engedélyt), a földön megállva <b>CLEAR OF RUNWAY</b>.</p>`,
  task: 'Kérj leszállást, szállj le, állj meg, és jelentsd: CLEAR OF RUNWAY',
  check: (s) => land.check(s) && s.rf.clear,
  status: (s) => `INBOUND ${s.rf.inbound ? '✓' : '·'} · GEAR DOWN ${s.rf.land ? '✓' : '·'} · CLEAR ${s.rf.clear ? '✓' : '·'}`,
};

export class School {
  constructor(game, course, onDone, { radio = false } = {}) {
    this.g = game; this.key = course; this.onDone = onDone;
    const c = COURSES[course];
    // the radio course: the tower clearance first, the landing with the calls; the jets start on the runway
    this.course = radio ? { ...c, steps: [clearance, ...c.steps.map((st) => (st === land ? landRadio : st))] } : c;
    this.takeoffIdx = radio ? 1 : 0;
    this.rf = { taxi: false, takeoff: false, inbound: false, land: false, clear: false, made: 0, bad: 0 };
    if (radio) {
      this.off = game.radio.onCall((call) => {
        const p = this.p;
        if (call.id === 'request_taxi') this.rf.taxi = true;
        else if (call.id === 'ready_takeoff') { if (this.rf.taxi) this.rf.takeoff = true; else { this.rf.bad++; return; } }
        else if (call.id === 'inbound') this.rf.inbound = true;
        else if (call.id === 'gear_down' && p.fm.gearPos > 0.9) this.rf.land = true;
        else if (call.id === 'clear_runway' && p.onGround && p.speed < 8) this.rf.clear = true;
        else return;
        this.rf.made++;
      });
    }
    this.panel = $('tutorial'); this.panel.hidden = false;
    this.race = null; this.flags = {}; this.deadTime = 0;
    game.onTrap = () => { this.flags.trap = true; };
    game.onCatapult = () => { this.flags.cat = true; };
    this.start(0);
  }
  get p() { return this.g.player; }
  get agl() { return this.p.pos.z - this.g.terrain.height(this.p.pos.x, this.p.pos.y); }
  get step() { return this.course.steps[this.i]; }
  start(i) {
    this.i = i; this.done = false; this.doneTime = 0; this.flags = {};
    if (this.race) { this.race.dispose(); this.race = null; }
    // after the take-off lesson every restart is in the air near the base
    if (i > this.takeoffIdx) this.g.opts.airStart = true;
    if (this.step.setup) this.step.setup(this);
    this.render();
  }
  // a ring course from where the jet is now, the way it is heading
  startRings(n) {
    const p = this.p, f = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0)), field = this.g.terrain.airfield;
    const start = add(p.pos, mul(f, 800));
    const goal = this.key === 't45' ? V(this.g.carrier.x, this.g.carrier.y + 6000, 0) : V(field.x - 9000, field.y + 9000, 0);
    this.race = new Race(this.g.terrain, this.g.view.scene, start, Math.atan2(f.x, f.y), { rings: n, goal, record: false });
  }
  // 6 km behind the carrier on its landing line, 400 m high, gear down, on speed
  approach() {
    const cv = this.g.carrier, p = this.p, h = cv.landingHeading * DEG;
    const back = V(-Math.sin(h), -Math.cos(h), 0), l = cv.landStart, d = cv.landDir;
    const td = cv.world(l[0] + d[0] * 60, l[1] + d[1] * 60, 0);
    const pos = add(V(td.x, td.y, 0), mul(back, 6000)); pos.z = 19.5 + Math.tan(3.5 * DEG) * 6000 + 15;
    const fm = p.fm;
    fm.onGround = false; fm.pos = pos; fm.quat = qheading(cv.landingHeading, 0); fm.vel = mul(V(Math.sin(h), Math.cos(h), 0), 72);
    fm.gearDown = true; fm.gearPos = 1; fm.groundZ = undefined; fm.arrest = 0; fm.catapultAcc = 0; fm.parkBrake = false;
    p.controls.throttle = 0.62; fm.engine = 0.62;
    this.g.cam.reset(p);
  }
  // the game asks after a crash: back to the start of this lesson
  respawn() {
    const g = this.g;
    g.state.banner = g.state.subBanner = '';
    g.spawnPlayer();
    this.start(this.i);
    if (this.step.spawn) this.step.spawn(this);
  }
  update(dt) {
    const s = this.step;
    if (!this.p.alive) {                       // crashed: a few seconds, then this lesson again
      this.deadTime += dt;
      if (this.deadTime > 3) { this.deadTime = 0; this.respawn(); }
      return;
    }
    // taking off without clearance: the tower is not amused
    if (this.rf && this.off && !this.rf.takeoff && !this.p.onGround && !this.rf.warned) {
      this.rf.warned = true; this.rf.bad++;
      this.g.radio.say('tower', `${this.g.radio.callsign}, you departed without a clearance! Call me next time.`, 300);
    }
    if (this.race) this.raceStep(dt);
    if (!this.done && s.check && s.check(this, dt)) {
      this.done = true; this.g.sounds.play('splash', 0.6); this.g.hud.message('FELADAT TELJESÍTVE', 'good', 2.5, 'school');
      this.render();
    }
    if (this.done) {
      this.doneTime += dt;
      if (this.doneTime > 2.2) this.next();
    } else if (s.status) {
      const el = this.panel.querySelector('.tut-status');
      if (el) el.textContent = s.status(this);
    }
  }
  raceStep(dt) {
    const prev = this.prevPos || this.p.pos.clone();
    this.prevPos = this.p.pos.clone();
    const ev = this.race.update(dt, this.p, prev);
    if (ev === 'ring' || ev === 'finish') this.g.sounds.play('splash', 0.35);
    else if (ev === 'miss') this.g.hud.message('MELLÉ! Fordulj vissza a gyűrűhöz', 'warn', 2, 'race');
  }
  next() {
    if (this.i + 1 < this.course.steps.length) {
      // the carrier lessons follow each other on the deck; the others go on where the jet is
      this.start(this.i + 1);
      if (this.step.spawn && !this.flags.trap) this.step.spawn(this);
    } else this.finish();
  }
  enter() {}                                 // Enter does not skip: these are exams
  finish() {
    if (this.finished) return;
    this.finished = true;
    if (this.race) { this.race.dispose(); this.race = null; }
    if (this.off) this.off();
    this.panel.hidden = true;
    this.g.school = null; this.g.tutorial = null; this.g.onTrap = null; this.g.onCatapult = null;
    const radio = this.off ? Math.round(100 * this.rf.made / Math.max(1, this.rf.made + this.rf.bad + (this.rf.inbound ? 0 : 1))) : undefined;
    if (this.onDone) this.onDone(this.key, { radio });
  }
  render() {
    const s = this.step, n = this.course.steps.length;
    this.panel.innerHTML = `
      <div class="tut-head"><span>${this.course.short} · ${this.i + 1} / ${n}</span><span class="tut-bar"><i style="width:${(this.i + (this.done ? 1 : 0)) / n * 100}%"></i></span></div>
      <h3>${s.title}</h3>${this.i === 0 ? `<p><i>${this.course.intro}</i></p>` : ''}${s.text}
      <div class="tut-task ${this.done ? 'done' : ''}"><b>${this.done ? 'KÉSZ' : 'FELADAT'}</b>${s.task}</div>
      <div class="tut-status"></div>
      <div class="tut-foot">${this.course.name} · Esc = menü (a képzés innen folytatható)</div>`;
  }
}

// ------------------------------------------------------- kit and centrifuge
const KIT = [
  ['suit', 'Repülőoverál', 'Tűzálló Nomex anyag – ez van rajtad a pilótafülkében.'],
  ['gsuit', 'G-ruha (anti-G nadrág)', 'Felfújható kamrák a hason és a lábakon. Nagy G-nél levegőt kapnak, és nem hagyják a vért a lábakba szorulni – így nem sötétül el a kép. Kb. 1 G-vel többet bírsz vele.'],
  ['harness', 'Ejtőernyő-hám', 'Ezzel kapcsolódsz a katapultüléshez és az ejtőernyőhöz. Szorosra húzva!'],
  ['helmet', 'Sisak (HMD)', 'Védi a fejed, a sisakkijelzőn pedig ott vannak a célpontok – oda nézel, oda céloz a rakéta.'],
  ['mask', 'Oxigénmaszk', 'Nagy magasságban és nagy G-nél ezen át lélegzel; a G-ruhával együtt a nyomásos légzést is segíti.'],
];
export function gearUp(onDone, onMedal, { portrait = null, fitter = null } = {}) {
  const box = $('gearup');
  const on = { suit: true };
  // the picture: the life support technician hands out the kit; dressed, it is you in full gear
  const figure = () => {
    const all = KIT.every(([id]) => on[id]);
    const n = KIT.filter(([id]) => on[id]).length;
    const src = all || !fitter ? portrait : fitter;
    return src ? `<img class="pilot-img" src="${src}" alt="" style="filter:${all ? 'none' : `saturate(${0.4 + n * 0.12})`}">
      <p class="hint">${all ? 'Kész: így ülsz be a gépbe.' : 'A repülő-felszerelés szakember sorban adja a holmit.'}</p>` : '';
  };
  const render = () => {
    const all = KIT.every(([id]) => on[id]);
    box.innerHTML = `<div class="card wide"><div class="eyebrow">Karrier · 1. lépés · Felszerelés</div><h1 style="font-size:38px">Öltözz be!</h1>
      <div class="gear-grid"><div>${figure()}</div><div class="kit">${KIT.map(([id, name, d]) => `<div class="kit-item${on[id] ? ' on' : ''}"><b>${name}</b><span>${d}</span>
        ${on[id] ? '<em>✓ rajtad</em>' : `<button type="button" class="small primary" data-kit="${id}">Felveszem</button>`}</div>`).join('')}</div></div>
      <div class="buttons"><button type="button" class="primary" id="to-fuge" ${all ? '' : 'disabled'}>Irány a centrifuga ▶</button><button type="button" id="gear-back">Vissza</button></div></div>`;
    for (const b of box.querySelectorAll('[data-kit]')) b.onclick = () => { on[b.dataset.kit] = true; render(); };
    $('to-fuge').onclick = () => centrifuge(box, () => { box.hidden = true; if (onMedal) onMedal('gsuit'); onDone(true); }, render);
    $('gear-back').onclick = () => { box.hidden = true; onDone(false); };
  };
  box.hidden = false;
  render();
}
// +1 G to +7 G in 10 s, then 15 s at 7 G.  Every 2.5 s the instructor calls the straining cycle: press SPACE
// (or the button) inside the window - tense the legs and belly, quick breath.  Miss it and the picture greys.
function centrifuge(box, onPass, back) {
  box.innerHTML = `<div class="card wide"><div class="eyebrow">Karrier · 1. lépés · Centrifuga</div><h1 style="font-size:38px">Centrifuga: 7 G, 15 mp</h1>
    <p>A centrifuga felpörget 7 G-ig, és 15 másodpercig ott tart (NATO szabvány). A G-ruha magától felfújódik. Neked az <b>AGSM</b> a dolgod
    (anti-G feszítő manőver): amikor megjelenik a <b>FESZÍTS!</b> jel, nyomd meg a ${k('Szóköz')}-t vagy a gombot – megfeszíted a lábad és a hasad,
    és gyorsan levegőt veszel. Ha lemaradsz, beszűkül a látásod; ha teljesen elsötétül: G-LOC (eszméletvesztés).</p>
    <canvas id="fuge" width="640" height="300"></canvas>
    <div class="buttons"><button type="button" class="primary" id="agsm">FESZÍTÉS + LÉGZÉS (Szóköz)</button><button type="button" id="fuge-back">Vissza</button></div></div>`;
  const cv = $('fuge'), g = cv.getContext('2d');
  let t = 0, vision = 1, cue = null, nextCue = 2.0, last = performance.now(), done = false, msg = '', msgT = 0, raf = 0;
  const press = () => {
    if (done) return;
    if (cue && cue.t < 1.2) { vision = Math.min(1, vision + 0.22); msg = 'JÓ!'; cue = null; nextCue = t + 2.5; }
    else { vision -= 0.04; msg = 'Túl korán'; }
    msgT = 0.8;
  };
  const key = (e) => { if (e.code === 'Space') { e.preventDefault(); press(); } };
  addEventListener('keydown', key);
  const stop = () => { cancelAnimationFrame(raf); removeEventListener('keydown', key); };
  $('agsm').onclick = press;
  $('fuge-back').onclick = () => { stop(); back(); };
  const frame = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    t += dt;
    const G = t < 10 ? 1 + 0.6 * t : t < 25 ? 7 : Math.max(1, 7 - (t - 25) * 2);
    if (t >= nextCue && !cue && t < 25) cue = { t: 0 };
    if (cue) { cue.t += dt; if (cue.t > 1.2) { vision -= 0.2; cue = null; nextCue = t + 2.5; msg = 'LEMARADTÁL!'; msgT = 0.8; } }
    vision -= Math.max(0, G - 4.5) * 0.045 * dt;
    msgT -= dt;
    // draw: the arm of the centrifuge from above, the G meter, the G-suit bladders, the vision tunnel
    const W = cv.width, H = cv.height;
    g.fillStyle = '#0b1016'; g.fillRect(0, 0, W, H);
    const ang = t * (0.6 + G * 0.35);
    g.save(); g.translate(150, 150); g.rotate(ang);
    g.strokeStyle = '#93a1ab'; g.lineWidth = 10; g.beginPath(); g.moveTo(0, 0); g.lineTo(110, 0); g.stroke();
    g.fillStyle = '#ffc840'; g.beginPath(); g.arc(118, 0, 18, 0, Math.PI * 2); g.fill(); g.restore();
    g.fillStyle = '#3a4652'; g.beginPath(); g.arc(150, 150, 14, 0, Math.PI * 2); g.fill();
    g.font = '600 46px Oswald, sans-serif'; g.fillStyle = G > 6 ? '#ff4d40' : '#6bff85'; g.textAlign = 'left';
    g.fillText(`${G.toFixed(1)} G`, 320, 70);
    g.font = '14px "JetBrains Mono", monospace'; g.fillStyle = '#93a1ab';
    g.fillText(t < 10 ? 'felpörgés' : t < 25 ? `7 G: még ${Math.max(0, 25 - t).toFixed(1)} s` : 'lassítás', 320, 94);
    g.fillText('G-ruha', 320, 130);
    for (let i = 0; i < 3; i++) { g.strokeStyle = '#556b4a'; g.strokeRect(320 + i * 40, 140, 30, 60); g.fillStyle = '#6bff85'; const f = Math.min(1, Math.max(0, (G - 1.5) / 5)); g.fillRect(320 + i * 40, 200 - 60 * f, 30, 60 * f); }
    g.fillText('látás', 460, 130); g.strokeStyle = '#93a1ab'; g.strokeRect(460, 140, 150, 18);
    g.fillStyle = vision > 0.5 ? '#6bff85' : vision > 0.25 ? '#ffc840' : '#ff4d40'; g.fillRect(460, 140, 150 * Math.max(0, vision), 18);
    if (cue) { g.font = '600 40px Oswald, sans-serif'; g.fillStyle = '#ffc840'; g.fillText('FESZÍTS!', 460, 215); }
    if (msgT > 0) { g.font = '600 22px Oswald, sans-serif'; g.fillStyle = '#dfe6ea'; g.fillText(msg, 460, 250); }
    // tunnel vision: the edge darkens as vision falls
    const v = Math.max(0, vision), grd = g.createRadialGradient(W / 2, H / 2, W * 0.1 + W * 0.5 * v, W / 2, H / 2, W * 0.75);
    grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(1, `rgba(0,0,0,${Math.min(0.97, 1.1 - v)})`);
    g.fillStyle = grd; g.fillRect(0, 0, W, H);
    if (vision <= 0) {
      done = true; stop();
      g.fillStyle = 'rgba(0,0,0,0.9)'; g.fillRect(0, 0, W, H);
      g.font = '600 34px Oswald, sans-serif'; g.fillStyle = '#ff4d40'; g.textAlign = 'center';
      g.fillText('G-LOC – elájultál', W / 2, H / 2 - 10);
      g.font = '15px Barlow, sans-serif'; g.fillStyle = '#dfe6ea'; g.fillText('Nyomd időben a Szóközt, amikor kiírja: FESZÍTS!', W / 2, H / 2 + 22);
      $('agsm').textContent = 'Újra'; $('agsm').onclick = () => centrifuge(box, onPass, back);
      return;
    }
    if (t >= 28) {
      done = true; stop();
      g.fillStyle = 'rgba(6,20,10,0.88)'; g.fillRect(0, 0, W, H);
      g.font = '600 34px Oswald, sans-serif'; g.fillStyle = '#6bff85'; g.textAlign = 'center';
      g.fillText('ÁTMENT – 7 G, 15 mp', W / 2, H / 2 - 10);
      g.font = '15px Barlow, sans-serif'; g.fillStyle = '#dfe6ea'; g.fillText('A repülőorvos aláírta: mehetsz repülni!', W / 2, H / 2 + 22);
      $('agsm').textContent = 'Tovább ▶'; $('agsm').onclick = onPass;
      return;
    }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);
}

// ------------------------------------------------------------- the career screen
export const STAGES = [
  ['gear', 'Felvétel: felszerelés és centrifuga'],
  ['t6', 'Alapképzés – T-6A Texan II (Navy és Air Force közös)'],
  ['branch', 'Fegyvernem: Air Force vagy Navy'],
  ['adv', 'Haladó képzés – T-38C Talon (Air Force) / T-45C Goshawk (Navy)'],
  ['wings', 'Szárnyak: F-16C Viper / F/A-18E Super Hornet'],
  ['ww3', '3. világháború – 5 bevetés'],
];
export function nextStage(p) {
  if (!p.gear) return 'gear';
  if (!p.t6) return 't6';
  if (!p.branch) return 'branch';
  if (!p.adv) return 'adv';
  if (!p.wings) return 'wings';
  return 'ww3';
}
export function rank(p) {
  if (p.ww3 >= 5) return p.branch === 'navy' ? 'Korvettkapitány' : 'Őrnagy';
  if (p.wings) return p.branch === 'navy' ? 'Hadnagy (Naval Aviator)' : 'Hadnagy (pilóta)';
  if (p.t6) return 'Pilótanövendék (haladó)';
  return 'Pilótanövendék';
}
