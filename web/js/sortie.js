// A sortie of the career, from the ready room to the paperwork:
//   kit        walk to the equipment container (helmet, G suit, harness)
//   walk       walk to your jet
//   preflight  in the cockpit: check the controls, the engine, the airbrake, the displays, the weapons, the radio
//   taxi       ask the tower for taxi and take-off clearance (the ground crew tows you to the runway)
//   takeoff    take off
//   fight      the mission itself (mission.js)
//   rtb        come home and land; the jet stops on the concrete
//   shutdown   engine off, climb out
//   walkback   walk to the operations building
//   log        write the flight log by hand - the sortie is not over until it is handed in
// An alert (scramble) sortie skips the kit, the walk across the apron and the checks: the klaxon sounds, you run
// the few metres to the jet that waits on the runway, hot, and go.
import { V, len, sub, DEG } from './util.js';
import { Mission } from './mission.js';
import { SPOTS } from './base.js';

const $ = (id) => document.getElementById(id);
const esc = (t) => String(t).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

export class Sortie {
  constructor(game, m, onEnd) {
    this.g = game; this.m = m; this.onEnd = onEnd; this.t = 0; this.phaseT = 0; this.result = null; this.mission = null;
    this.scramble = !!m.scramble; this.flags = {}; this.done = {}; this.ended = false;
    const b = this.b = game.base, p = game.player;
    b.build();
    b.jetsOnGround = [];
    this.radioOff = game.radio.onCall((c) => this.heard(c));
    this.panel = $('tutorial'); this.panel.hidden = false;
    game.state.subBanner = ''; game.state.banner = '';
    game.cam.cockpit = false;
    const w = b.walker;
    if (this.scramble) {
      b.park(p, SPOTS.alertJet, 0, true);
      w.kit = true;
      w.enter([SPOTS.alertHut[0] + 4, SPOTS.alertHut[1] + 24], 270);
      game.radio.cleared.takeoff = game.radio.cleared.taxi = true;
      this.setPhase('walk');
      this.siren();
    } else {
      b.park(p, SPOTS.jet, SPOTS.jetHeading);
      b.jetsOnGround = [[b.field.x + SPOTS.jet[0], b.field.y + SPOTS.jet[1], SPOTS.jetHeading]];
      w.kit = false;
      w.enter([SPOTS.door[0] + 2, SPOTS.door[1] - 6], 270);
      this.setPhase('kit');
    }
    w.info = () => this.infoLine();
  }
  get p() { return this.g.player; }
  // ------------------------------------------------------------------ phases
  setPhase(ph) {
    this.phase = ph; this.phaseT = 0;
    const b = this.b, w = b.walker, spec = this.p.spec;
    const jetRel = this.scramble ? SPOTS.alertJet : SPOTS.jet;
    if (ph === 'kit') {
      b.setPoints([
        { id: 'locker', x: SPOTS.locker[0], y: SPOTS.locker[1] - 3, r: 5, beacon: true, name: 'FELSZERELÉS', color: 0xffc840, enabled: () => !w.kit,
          label: 'Felszerelés felvétele: overál, G-ruha, hám, sisak', action: () => this.dress() },
      ]);
    } else if (ph === 'walk') {
      b.setPoints([
        { id: 'jet', x: jetRel[0], y: jetRel[1], r: 9, beacon: true, name: spec.short.toUpperCase(), color: 0x6bff85,
          label: () => (w.kit ? `Beszállás: <b>${spec.name}</b>` : 'Előbb vedd fel a felszerelést!'), action: () => (w.kit ? this.board() : this.g.hud.message('Előbb a felszerelés (sárga jelzés)!', 'warn', 2.5, 'kit')) },
        ...(w.kit ? [] : [{ id: 'locker', x: SPOTS.locker[0], y: SPOTS.locker[1] - 3, r: 5, beacon: true, name: 'FELSZERELÉS', color: 0xffc840, label: 'Felszerelés felvétele', action: () => this.dress() }]),
      ]);
    } else if (ph === 'walkback') {
      b.setPoints([{ id: 'door', x: SPOTS.door[0], y: SPOTS.door[1] - 3, r: 5, beacon: true, name: 'MŰVELETI ÉPÜLET', color: 0xffc840, label: 'Belépés: jelentés és napló', action: () => this.enterOps() }]);
    } else b.setPoints([]);
    this.render();
  }
  dress() {
    const w = this.b.walker;
    w.kit = true;
    this.g.hud.message('Felszerelés: overál, G-ruha, hám, sisak – felvéve', 'good', 3, 'kit');
    this.g.sounds && this.g.sounds.play && this.g.sounds.play('splash', 0.3);
    this.setPhase('walk');
  }
  board() {
    const g = this.g, w = this.b.walker;
    w.leave(); this.b.setPoints([]);
    g.cam.cockpit = true; g.cam.panelLook = false;
    this.p.fm.parkBrake = true;
    if (this.scramble) {
      this.boardT = this.t;
      this.p.fm.parkBrake = false; this.p.controls.throttle = 0.3;
      g.hud.message('GÁZT RÁ, FELSZÁLLÁS!', 'warn', 3, 'sc');
      this.setPhase('takeoff'); this.startMission();
    } else {
      this.pre = this.checklist();
      g.hud.message('Beültél. Ellenőrizd a gépet, mielőtt gurulásra kérsz engedélyt.', 'info', 4, 'pre');
      this.setPhase('preflight');
    }
  }
  // the checks in the cockpit, each of them something you do
  checklist() {
    const p = this.p, sel0 = p.selected, armed = p.weaponKeys().length > 0;
    const f = this.flags;
    const list = [
      { id: 'controls', text: 'Kormányfelületek: mozgasd a botot minden irányba (egér a kabinban, vagy W / S / A / D)', ok: () => f.pu && f.pd && f.rl && f.rr },
      { id: 'engine', text: 'Hajtómű: Shift = gáz 70% fölé, aztán Z = vissza alapjáratra', ok: () => f.thr && p.controls.throttle < 0.15 },
      { id: 'brake', text: 'Légfék és fék: tartsd lenyomva a B-t', ok: () => f.brk },
      { id: 'panel', text: 'Műszerek: nézz le a kijelzőkre (N)', ok: () => f.panelT > 1.2 },
    ];
    if (armed) list.push({ id: 'weapons', text: 'Fegyverzet: válassz fegyvert (1 vagy 2, vagy az egérgörgő)', ok: () => f.wpn || p.selected !== sel0 });
    list.push({ id: 'radio', text: 'Rádió: mondd, hogy RADIO CHECK (I gomb)', ok: () => f.radio });
    return list;
  }
  heard(call) {
    const f = this.flags;
    if (call.id === 'radio_check') f.radio = true;
    if (this.phase === 'preflight' || this.phase === 'taxi') {
      if (call.id === 'request_taxi') { if (this.phase === 'preflight' && this.pre.every((c) => c.ok())) this.setPhase('taxi'); }
      else if (call.id === 'ready_takeoff' && this.phase === 'taxi' && this.g.radio.cleared.taxi) this.tow();
    }
    if (this.phase === 'rtb' && call.id === 'clear_runway') f.clear = true;
  }
  onKey(k) {
    const f = this.flags;
    if (this.phase === 'preflight' && (k === '1' || k === '2')) f.wpn = true;
    if (this.phase === 'shutdown' && k === 'e') { this.climbOut(); return true; }
    return false;
  }
  // after the checks and the clearances: the ground crew tows the jet to the runway, engine running
  tow() {
    const g = this.g, fade = $('fade');
    if (fade) fade.classList.add('on');
    setTimeout(() => {
      this.b.park(this.p, SPOTS.alertJet, 0, true);
      this.p.fm.parkBrake = false; this.p.controls.throttle = 0.3;
      g.cam.reset(this.p);
      if (fade) fade.classList.remove('on');
      g.hud.message('A földi személyzet a pálya elejére vontatott. FELSZÁLLÁS!', 'good', 4, 'tow');
      g.state.subBanner = '';
      this.setPhase('takeoff'); this.startMission();
    }, 1300);
    this.setPhase('towing');
  }
  // the mission (and with it the flight standing next to you) exists from the start of the take-off
  startMission() {
    if (this.mission) return;
    this.mission = new Mission(this.g, { ...this.m, groundStart: true, embedded: true }, (r) => this.fightOver(r));
    this.mission.quiet = true;
  }
  startFight() {
    const g = this.g;
    this.airT = this.t;
    this.startMission();
    this.mission.quiet = false; this.mission.render();
    this.setPhase('fight');
  }
  fightOver(r) {
    this.result = { ...r, scrambleSec: this.scramble && this.airT ? Math.round(this.airT - (this.boardT || 0)) : null };
    const g = this.g, p = this.p;
    // the enemies are gone, the sky quietens
    g.world.aircraft = g.world.aircraft.filter((a) => a === p || a.team === 'blue' && a.alive);
    g.world.missiles = [];
    if (!p.alive || p.ejected) { this.setPhase('log'); this.openLog(); return; }
    g.radio.say('awacs', `${g.radio.callsign}, vector ${g.radio.homeBearing()} for home, runway three six, report inbound.`, 1200);
    this.setPhase('rtb');
  }
  landed() {
    const p = this.p, f = this.b.field;
    return p.onGround && p.speed < 2.5 && f.onPaved(p.pos.x, p.pos.y) && !this.g.carrier.onDeck(p.pos.x, p.pos.y);
  }
  climbOut() {
    const g = this.g, b = this.b, p = this.p;
    // the engine winds down, a tow truck takes the jet to its place, you climb out
    g.world.aircraft = g.world.aircraft.filter((a) => a === p); g.wingman = null;
    b.park(p, SPOTS.jet, SPOTS.jetHeading);
    b.jetsOnGround = [[b.field.x + SPOTS.jet[0], b.field.y + SPOTS.jet[1], SPOTS.jetHeading]];
    p.controls.throttle = 0;
    g.cam.cockpit = false; g.cam.panelLook = false;
    g.state.subBanner = '';
    b.walker.enter([SPOTS.jet[0] + 11, SPOTS.jet[1] - 3], 90);
    g.hud.message('Kiszálltál. Menj a műveleti épületbe jelenteni.', 'info', 4, 'out');
    this.setPhase('walkback');
  }
  enterOps() {
    this.b.walker.leave(); this.b.setPoints([]);
    this.setPhase('log');
    this.openLog();
  }
  // ------------------------------------------------------------------ the loop
  update(dt) {
    this.t += dt; this.phaseT += dt;
    const g = this.g, p = this.p, f = this.flags;
    if (this.phase === 'fight') { this.mission.update(dt); return; }
    if (this.phase === 'takeoff' && this.mission) this.mission.update(dt);
    if (this.phase === 'preflight' || this.phase === 'taxi') {
      const pl = g.pilot;
      if (pl && pl.pitch !== null) { if (pl.pitch > 0.6) f.pu = true; if (pl.pitch < -0.6) f.pd = true; }
      if (pl && pl.roll !== null) { if (pl.roll > 0.6) f.rr = true; if (pl.roll < -0.6) f.rl = true; }
      if (p.controls.throttle > 0.7) f.thr = true;
      if (p.controls.airbrake || p.controls.brakes) f.brk = true;
      f.panelT = g.cam.panelLook ? (f.panelT || 0) + dt : f.panelT || 0;
      p.fm.parkBrake = true;
      if (this.phase === 'preflight' && this.pre.every((c) => c.ok()) && !f.allDone) {
        f.allDone = true; g.hud.message('Minden rendben. Kérj gurulási engedélyt: REQUEST TAXI (I)', 'good', 5, 'pre');
        g.radio.say('tower', `${g.radio.callsign}, tower, ready when you are.`, 800);
      }
      if (this.phaseT % 0.5 < dt) this.render();
    } else if (this.phase === 'takeoff') {
      const agl = p.pos.z - g.terrain.height(p.pos.x, p.pos.y);
      if (!p.onGround && agl > 30 && p.alive) this.startFight();
      if (!p.alive || p.ejected) { this.setPhase('log'); this.result = { won: false, why: 'crash', status: p.ejected ? 'ejected' : 'shot_down', kills: 0, blueLost: [this.m.playerType], redLost: [], radio: 0 }; this.openLog(); }
      if (this.phaseT % 1 < dt) this.render();
    } else if (this.phase === 'rtb') {
      if (this.landed()) { this.setPhase('shutdown'); g.hud.message('Megálltál. E = hajtómű leállítása, kiszállás', 'good', 6, 'sd'); }
      else if (!p.alive) { this.setPhase('log'); this.result.status = 'shot_down'; this.openLog(); }
      if (this.phaseT % 1 < dt) this.render();
    } else if (this.phase === 'kit' || this.phase === 'walk' || this.phase === 'walkback') {
      if (this.phaseT % 0.5 < dt) this.render();
    }
  }
  onEvent(kind, d) { if ((this.phase === 'fight' || this.phase === 'takeoff') && this.mission) this.mission.onEvent(kind, d); }
  enter() { if (this.phase === 'fight' && this.mission) this.mission.enter(); }
  respawn() {}
  infoLine() {
    const m = this.m, name = esc(m.title || 'Bevetés');
    return `${name} · WASD = séta · Shift = futás · E = használ · I = rádió`;
  }
  // ------------------------------------------------------------------ the briefing panel
  render() {
    const m = this.m, ph = this.phase, spec = this.p.spec;
    const steps = this.scramble
      ? [['walk', 'Fuss a géphez!'], ['takeoff', 'Felszállás'], ['fight', 'Bevetés'], ['rtb', 'Leszállás'], ['shutdown', 'Kiszállás'], ['walkback', 'Jelentés'], ['log', 'Napló']]
      : [['kit', 'Felszerelés'], ['walk', 'Séta a géphez'], ['preflight', 'Ellenőrzés a kabinban'], ['taxi', 'Engedélyek'], ['takeoff', 'Felszállás'], ['fight', 'Bevetés'], ['rtb', 'Leszállás'], ['shutdown', 'Kiszállás'], ['walkback', 'Jelentés'], ['log', 'Napló']];
    const order = steps.map((s) => s[0]);
    const cur = ph === 'towing' ? order.indexOf('taxi') : order.indexOf(ph);
    const list = steps.map(([id, t], i) => `<li class="${i < cur ? 'done' : i === cur ? 'now' : ''}">${i < cur ? '✓' : i === cur ? '▶' : '·'} ${t}</li>`).join('');
    let body = '';
    if (ph === 'kit') body = '<p>Menj a <b>felszerelés-konténerhez</b> (sárga jelzés), és vedd fel a holmidat. Kitartott <kbd>Shift</kbd> = futás.</p>';
    else if (ph === 'walk') body = this.scramble
      ? `<p><b>RIADÓ!</b> Fuss a gépedhez (zöld jelzés)! Eltelt: ${Math.round(this.t)} s</p>`
      : `<p>Sétálj a gépedhez (zöld jelzés): <b>${spec.name}</b>.${this.b.walker.kit ? '' : ' <b>De előbb a felszerelés!</b>'}</p>`;
    else if (ph === 'preflight' || ph === 'taxi') {
      body = '<p>Ellenőrzés a pilótafülkéből:</p><ul class="pre">' + this.pre.map((c) => `<li class="${c.ok() ? 'ok' : ''}">${c.ok() ? '☑' : '☐'} ${c.text}</li>`).join('') + '</ul>';
      body += ph === 'taxi' ? '<p class="tut-task"><b>RÁDIÓ</b>mondd: <b>READY FOR TAKEOFF</b></p>'
        : this.flags.allDone ? '<p class="tut-task"><b>RÁDIÓ</b>mondd: <b>REQUEST TAXI</b> (I)</p>' : '';
    } else if (ph === 'towing') body = '<p>A földi személyzet a kifutóhoz vontat…</p>';
    else if (ph === 'takeoff') body = `<p>Teljes gáz (<kbd>Shift</kbd>), emeld az orrod felemelkedési sebességnél, futómű be (<kbd>G</kbd>).${this.scramble ? ` Eltelt: ${Math.round(this.t)} s` : ''}</p>`;
    else if (ph === 'rtb') body = '<p>A feladat kész. <b>Térj vissza a bázisra és szállj le</b> – a kifutó a HUD-on a cián négyzet. Rádió: INBOUND FOR LANDING, GEAR DOWN, CLEAR OF RUNWAY.</p>';
    else if (ph === 'shutdown') body = '<p>Megálltál a betonon. <kbd>E</kbd> = hajtómű leállítása és kiszállás.</p>';
    else if (ph === 'walkback') body = '<p>Sétálj a <b>műveleti épülethez</b> (sárga jelzés), és add le a jelentést.</p>';
    else if (ph === 'log') body = '<p>Töltsd ki a naplót.</p>';
    this.panel.innerHTML = `<div class="tut-head"><span>${esc(m.title || 'Bevetés')}</span></div><h3>${this.scramble ? 'Riasztás – QRA' : 'Bevetés'}</h3>
      <ol class="cr-stages-mini">${list}</ol>${body}`;
    if (ph === 'fight') this.panel.hidden = false;
  }
  // ------------------------------------------------------------------ the handwritten flight log
  openLog() {
    const g = this.g, r = this.result || { won: false, status: 'abort', kills: 0, blueLost: [], redLost: [], radio: 0 }, m = this.m;
    this.panel.hidden = true;
    g.state.paused = true; g.lockWanted = false;
    if (document.pointerLockElement) document.exitPointerLock();
    g.base.walker.leave();
    const box = $('logbook');
    const outcome = r.status === 'ejected' ? 'katapultáltál' : r.status === 'shot_down' ? 'lelőttek' : r.won ? 'teljesítve' : 'nem teljesítve';
    const accident = r.status === 'ejected' || r.status === 'shot_down';
    box.innerHTML = `<div class="paper"><h2>${accident ? 'Baleseti jelentés' : 'Repülési napló'}</h2>
      <div class="hdr">${esc(m.title || 'Bevetés')} · ${esc(g.radio.callsign)} · ${esc(this.p.spec.name)}<br>
      Eredmény: ${outcome} · lelövés: ${r.kills || 0} · saját veszteség: ${(r.blueLost || []).length}${this.scramble && r.scrambleSec != null ? ` · riadó → felszállás: ${r.scrambleSec} s` : ''}</div>
      <p class="tips">Saját kezűleg, a saját szavaiddal: mi volt a feladat, mit láttál, mit csináltál jól, mit rontottál el, mit javasolsz legközelebb. Legalább pár mondat.</p>
      <textarea id="log-text" spellcheck="false" placeholder="Kezdd el írni…" maxlength="1500"></textarea>
      <div class="need" id="log-need"></div>
      <div class="row-btn"><span class="hint" style="color:#6c6652">A napló a pilótanaplóba kerül.</span><button type="button" id="log-ok" disabled>Beadom ▶</button></div></div>`;
    box.hidden = false;
    const ta = $('log-text'), ok = $('log-ok'), need = $('log-need');
    const stop = (e) => e.stopPropagation();
    ta.addEventListener('keydown', stop); ta.addEventListener('keyup', stop); ta.addEventListener('keypress', stop);
    const check = () => {
      const t = ta.value.trim(), words = t.split(/\s+/).filter((w) => w.length > 1), uniq = new Set(words.map((w) => w.toLowerCase())).size;
      const good = t.length >= 60 && words.length >= 10 && uniq >= 7;
      ok.disabled = !good;
      need.textContent = good ? '' : `Még kell: ${Math.max(0, 60 - t.length)} karakter, ${Math.max(0, 10 - words.length)} szó.`;
    };
    ta.addEventListener('input', check); check();
    setTimeout(() => ta.focus(), 50);
    ok.onclick = () => {
      if (ok.disabled) return;
      box.hidden = true;
      this.end(ta.value.trim());
    };
  }
  end(text) {
    if (this.ended) return;
    this.ended = true;
    if (this.radioOff) this.radioOff();
    const g = this.g;
    this.b.walker.leave(); this.b.setPoints([]);
    this.panel.hidden = true;
    g.tutorial = null;
    g.state.subBanner = ''; g.state.banner = '';
    const r = this.result || { won: false, status: 'abort', kills: 0, blueLost: [], redLost: [], radio: 0 };
    this.onEnd({ ...r, log: text, scramble: this.scramble });
  }
  // an air raid siren: three rising sweeps
  siren() {
    const s = this.g.sounds, ctx = s && s.ctx;
    if (!ctx) return;
    try {
      s.resume();
      const o = ctx.createOscillator(), gn = ctx.createGain(), t0 = ctx.currentTime;
      o.type = 'sawtooth'; gn.gain.value = 0.0;
      o.connect(gn); gn.connect(s.master || ctx.destination);
      for (let k = 0; k < 3; k++) { o.frequency.setValueAtTime(420, t0 + k * 1.1); o.frequency.linearRampToValueAtTime(900, t0 + k * 1.1 + 0.9); }
      gn.gain.setValueAtTime(0.0, t0); gn.gain.linearRampToValueAtTime(0.25, t0 + 0.1); gn.gain.setValueAtTime(0.25, t0 + 3.2); gn.gain.linearRampToValueAtTime(0, t0 + 3.5);
      o.start(t0); o.stop(t0 + 3.6);
    } catch (e) { /* no audio */ }
  }
}
void V; void len; void sub; void DEG;
