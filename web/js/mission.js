// A sortie of the career: the jets of both sides over a real place, the flight lead (or your wingman), the
// radio, and the result for the war (campaign.js).
//  kinds:
//   'intercept' - peacetime air policing (Baltic QRA): a foreign jet near the border; get close, identify it
//                 (fly alongside under 600 m for 8 s), escort it out.  Weapons hold - shooting it ends the career.
//   'sweep'     - war: clear the sky of enemy fighters
//   'cap'       - war: hold the area for the time given (combat air patrol)
//   'bfm'       - fighter school: one against one, guns and IR missiles
//  role: 'wing' (an AI lead, you are number two) or 'lead' (you lead, an AI wingman follows your orders)
import { V, add, sub, mul, len, norm, dot, clamp, DEG, rng, qheading } from './util.js';
import { Aircraft } from './sim.js';
import { AIPilot, WingmanPilot, steerTowards } from './ai.js';
import { BANDITS, AIRCRAFT, buildLoadout, missilesFor } from './specs.js';

const $ = (id) => document.getElementById(id);

// an AI pilot that keeps its weapons quiet (peacetime): it flies its route, and only defends itself
class TransitPilot extends AIPilot {
  constructor(ac, route) { super(ac, 'normal', null); this.route = route; this.leg = 0; this.waved = false; }
  think(world) { this.ac.trigger = false; const t = this.findThreat(world); if (t) { this.threat = t; this.state = 'defend'; this.defendTimer = 2; } else if ((this.defendTimer -= 0.1) <= 0) this.state = 'transit'; }
  fly(dt, world) {
    if (this.state === 'defend' && this.threat && this.threat.alive) { const [d, th, g] = this.defend(world); steerTowards(this.ac.fm, d, this.ac.controls, g, 0.8); this.ac.controls.throttle = th; return; }
    const tgt = this.route[Math.min(this.leg, this.route.length - 1)];
    if (len(V(tgt.x - this.ac.pos.x, tgt.y - this.ac.pos.y, 0)) < 2500 && this.leg < this.route.length - 1) this.leg++;
    steerTowards(this.ac.fm, norm(sub(tgt, this.ac.pos)), this.ac.controls, 0.4, 0.7);
    this.ac.controls.throttle = 0.78;
  }
}
// the AI flight lead: flies to the fight with you on its wing, fights, comes home
class LeadPilot extends AIPilot {
  constructor(ac, skill, area) { super(ac, skill, area); }
}

export class Mission {
  // m: { kind, role, place, playerType, blue: [{type, n}], red: [{type, n, power}], skill, minutes, title, front, power, permadeath }
  constructor(game, m, onEnd) {
    this.g = game; this.m = m; this.onEnd = onEnd; this.t = 0; this.over = false; this.result = null;
    this.calls = { expected: 0, made: 0, late: 0 }; this.pending = null; this.idTime = 0; this.escortTime = 0; this.phase = 'ingress';
    this.kills = []; this.blueLost = []; this.redLost = [];
    const g = game, f = g.terrain.airfield, r = this.rnd = rng(Math.floor(Math.random() * 1e9));
    // the fight: 25 km from the base, on the enemy's side of it
    const dir = norm(V(Math.sin(m.bearing ?? 60 * DEG), Math.cos(m.bearing ?? 60 * DEG), 0));
    const lim = g.terrain.half - 12000;
    const P = this.P = V(clamp(f.x + dir.x * 24000, -lim, lim), clamp(f.y + dir.y * 24000, -lim, lim), 0);
    this.dir = norm(sub(P, V(f.x, f.y, 0)), dir);
    this.area = { x: P.x, y: P.y, r: 20000, engage: 36000 };
    g.nav.zone = { ...this.area }; g.state.missionLine = (m.title || 'BEVETÉS').toUpperCase();   // the HUD's zone mark: the fight
    const p = g.player, start = add(P, mul(this.dir, -16000));
    const z = Math.max(5000, g.terrain.height(start.x, start.y) + 1800);
    const hdg = Math.atan2(this.dir.x, this.dir.y);
    if (m.kind !== 'scramble') {                        // air start: on the way to the fight
      const fm = p.fm;
      fm.onGround = false; fm.pos = V(start.x, start.y, z); fm.vel = mul(V(Math.sin(hdg), Math.cos(hdg), 0), 230);
      fm.quat = qheading(hdg / DEG, 0); fm.gearDown = false; fm.gearPos = 0; fm.groundZ = undefined;
      p.controls.throttle = 0.9; fm.engine = 0.9;
      g.cam.reset(p);
    }
    g.radio.callsign = m.callsign || 'VIPER 1-1';
    // your flight: the AI lead (you on its wing) or your AI wingman
    const side = V(this.dir.y, -this.dir.x, 0);
    const blueSpec = (t) => BANDITS[t] || BANDITS.f16;
    const mk = (spec, team, pos, heading, name) => {
      const loadout = spec.internal || spec.id === 'f16' ? 'default' : buildLoadout(spec, 2, 4).layout;
      const ac = new Aircraft(spec, name, team, pos, heading / DEG, 230, { livery: 'viper', missiles: missilesFor(spec, true), loadout, rnd: rng(Math.floor(r() * 1e9)) });
      g.world.addAircraft(ac);
      return ac;
    };
    this.blue = [];
    if (m.role === 'wing') {
      const lead = this.lead = mk(blueSpec(m.leadType || m.playerType), 'blue', add(p.pos, add(mul(this.dir, 260), mul(side, -180))), hdg, `${(m.callsign || 'VIPER 1-1').replace(/-\d$/, '-1')} (vezér)`);
      lead.pos.z = p.pos.z + 20;
      new LeadPilot(lead, 'wing', m.kind === 'intercept' ? null : this.area);
      lead.isLead = true; this.blue.push(lead);
      g.radio.callsign = (m.callsign || 'VIPER 1-1').replace(/-\d$/, '-2');
    } else if (m.wingman !== false) {
      const w = mk(blueSpec(m.playerType), 'blue', add(p.pos, add(mul(this.dir, -260), mul(side, 170))), hdg, `${m.wingName || 'Kísérő'} (2-es)`);
      new WingmanPilot(w, p); g.wingman = w; this.blue.push(w);
    }
    // more friendly flights (allies), on both sides of yours
    let k = 0;
    for (const grp of m.blue || []) for (let i = 0; i < grp.n; i++, k++) {
      const pos = add(add(p.pos, mul(side, (k % 2 ? 1 : -1) * (2500 + 1200 * Math.floor(k / 2)))), mul(this.dir, -800 * Math.floor(k / 2)));
      const ac = mk(blueSpec(grp.type), 'blue', pos, hdg, `${grp.label || 'Szövetséges'} ${k + 1} (${blueSpec(grp.type).short})`);
      ac.power = grp.power;
      new AIPilot(ac, m.allySkill || 'normal', this.area); this.blue.push(ac);
    }
    // the other side
    this.red = [];
    k = 0;
    for (const grp of m.red || []) for (let i = 0; i < grp.n; i++, k++) {
      const spec = BANDITS[grp.type] || BANDITS.su35;
      const pos = add(add(P, mul(this.dir, 14000 + r() * 5000)), mul(side, (k - 2) * 2600));
      pos.z = Math.max(r() * 3000 + 4000, g.terrain.height(pos.x, pos.y) + 1500);
      const ac = mk(spec, 'red', pos, hdg + Math.PI, `${spec.short} ${k + 1}`);
      ac.power = grp.power;
      if (m.kind === 'intercept') {
        const route = [add(P, mul(side, -30000)), add(P, mul(side, -60000))].map((q) => V(q.x, q.y, pos.z));
        ac.fm.pos = add(add(P, mul(side, 22000)), mul(this.dir, 3000)); ac.fm.pos.z = 7000;
        new TransitPilot(ac, route);
        ac.passive = true;
      } else new AIPilot(ac, m.skill || 'normal', this.area);
      this.red.push(ac);
    }
    this.radioOff = g.radio.onCall((call) => this.heard(call));
    this.panel = $('tutorial'); this.panel.hidden = false;
    this.say('lead', this.briefLine());
    if (m.role === 'wing') this.expect('ack', 10);
    this.render();
  }
  briefLine() {
    const m = this.m, cs = this.g.radio.callsign;
    if (m.kind === 'intercept') return `${cs}, Magic: unknown aircraft approaching the border, intercept and identify. Weapons hold!`;
    if (m.kind === 'bfm') return `${cs}, fight's on in thirty seconds. Guns and heaters only.`;
    return `${cs}, Magic: ${this.red.length} hostile${this.red.length > 1 ? 's' : ''}, bullseye ${String(Math.round(((Math.atan2(this.P.x, this.P.y) / DEG) + 360) % 360)).padStart(3, '0')}. ${m.kind === 'cap' ? 'Hold the CAP.' : 'Clear the sky.'} Fence in.`;
  }
  say(who, text, delay = 400) { this.g.radio.say(this.m.role === 'wing' && who === 'lead' ? 'lead' : who === 'lead' ? 'awacs' : who, text, delay); }
  // the lead asked something: the right answer within `secs` counts for radio discipline
  expect(id, secs) { this.pending = { id, t: secs }; this.calls.expected++; }
  heard(call) {
    if (this.pending && (call.id === this.pending.id || (this.pending.id === 'ack' && call.id === 'ack'))) { this.calls.made++; this.pending = null; }
    if (call.id === 'tally' && this.m.kind === 'intercept') this.tally = true;
  }
  get p() { return this.g.player; }
  onEvent(kind, d) {
    if (kind !== 'kill') return;
    const v = d.victim;
    if (v.team === 'red') {
      this.redLost.push(v.spec.id || v.spec.model);
      if (d.killer === this.p) this.kills.push(v.spec.short);
      if (this.m.kind === 'intercept') { this.failNote = 'Lelőtted a polgári/idegen gépet békeidőben – hadbíróság!'; this.finish(false, 'shot_intruder'); return; }
      if (this.lead && this.lead.alive && d.killer === this.lead) this.say('lead', 'Splash one!', 200);
    } else if (v.team === 'blue') {
      if (v !== this.p) this.blueLost.push(v.spec.id || v.spec.model);
      if (v === this.lead) this.say('awacs', `${this.g.radio.callsign}, your lead is down! You have the flight.`, 600);
    }
  }
  update(dt) {
    if (this.over) return;
    this.t += dt;
    const p = this.p, m = this.m;
    if (this.pending && (this.pending.t -= dt) <= 0) { this.calls.late++; this.pending = null; this.g.hud.message('A vezér választ várt a rádión (I)!', 'warn', 2.5, 'radio'); }
    // the lead's radio calls: tally, engage
    const reds = this.red.filter((a) => a.alive);
    const near = reds.length ? Math.min(...reds.map((a) => len(sub(a.pos, p.pos)))) : 1e9;
    if (this.phase === 'ingress' && near < 32000) {
      this.phase = 'merge';
      if (m.kind === 'intercept') { this.say('awacs', `${this.g.radio.callsign}, target bearing ${this.bearingTo(reds[0])}, ${Math.round(near / 1852)} miles. Call tally.`); this.expect('tally', 40); }
      else if (m.role === 'wing') { this.say('lead', `${this.g.radio.callsign.replace(/-\d$/, '-1')}, tally ${reds.length}, engage! Two, cover me.`); this.expect('ack', 8); }
      else this.say('awacs', `${this.g.radio.callsign}, ${reds.length} hostiles, ${Math.round(near / 1852)} miles, hot. Cleared to engage.`);
    }
    if (m.kind === 'intercept' && reds[0]) {
      const d = len(sub(reds[0].pos, p.pos));
      if (this.phase !== 'escort' && this.phase !== 'done') {
        this.idTime = d < 600 ? this.idTime + dt : Math.max(0, this.idTime - dt * 0.5);
        if (this.idTime > 8) { this.phase = 'escort'; this.say('you', `${this.g.radio.callsign}: identified, ${reds[0].spec.short}, no weapons visible.`); this.say('awacs', 'Copy ID. Escort it away from the border.', 1500); reds[0].pilot.leg = 1; }
      } else if (this.phase === 'escort') {
        this.escortTime = d < 3500 ? this.escortTime + dt : this.escortTime;
        if (this.escortTime > 40) { this.phase = 'done'; this.say('awacs', `${this.g.radio.callsign}, good work, target left the area. RTB.`); this.finish(true); return; }
      }
    }
    if (m.kind !== 'intercept' && !reds.length && this.red.length) { this.say('awacs', `${this.g.radio.callsign}, picture clean. Good work, RTB.`); this.finish(true); return; }
    if (m.kind === 'cap' && this.t > (m.minutes || 8) * 60) { this.say('awacs', 'CAP time complete, RTB.'); this.finish(true); return; }
    if (this.t > (m.minutes || 12) * 60 + 300) { this.finish(m.kind === 'cap'); return; }
    if (!p.alive && !this.over) this.finish(false, 'killed');
    if (p.ejected && this.g.chute && this.g.chute.landed && !this.over) this.finish(false, 'ejected');
    if (this.t % 1 < dt) this.render();
  }
  bearingTo(a) { return String(Math.round(((Math.atan2(a.pos.x - this.p.pos.x, a.pos.y - this.p.pos.y) / DEG) + 360) % 360)).padStart(3, '0'); }
  finish(won, why = null) {
    if (this.over) return;
    this.over = true;
    const p = this.p, f = this.g.terrain.airfield;
    const overEnemy = dot(sub(p.pos, V(f.x, f.y, 0)), this.dir) > 20000;
    const status = p.ejected ? 'ejected' : !p.alive ? 'shot_down' : 'ok';
    const lostOwn = p.ejected || !p.alive;
    this.result = {
      won, why, status, overEnemy, kills: this.kills.length, killTypes: this.kills, playerType: this.m.playerType,
      blueLost: this.blueLost.concat(lostOwn ? [this.m.playerType] : []), redLost: this.redLost,
      radio: this.calls.expected ? Math.round(100 * this.calls.made / this.calls.expected) : 100, time: this.t,
    };
    this.g.hud.message(won ? 'KÜLDETÉS TELJESÍTVE – Enter: jelentés' : 'KÜLDETÉS VÉGE – Enter: jelentés', won ? 'good' : 'warn', 6, 'mission');
    this.g.state.subBanner = 'Enter: jelentés (debriefing)';
    this.render();
  }
  enter() { if (this.over) this.leave(); }
  respawn() { if (this.over || !this.p.alive) { if (!this.over) this.finish(false, 'killed'); this.leave(); } }
  leave() {
    if (this.left) return;
    this.left = true;
    if (this.radioOff) this.radioOff();
    this.panel.hidden = true;
    this.g.tutorial = null;
    this.g.state.banner = this.g.state.subBanner = '';
    if (this.onEnd) this.onEnd(this.result || { won: false, status: 'abort', kills: 0, blueLost: [], redLost: [], radio: 0 });
  }
  render() {
    const m = this.m, reds = this.red.filter((a) => a.alive).length;
    let task = '';
    if (m.kind === 'intercept') task = this.phase === 'escort' ? `Kísérd ki: ${Math.round(this.escortTime)} / 40 s (3,5 km-en belül)` : `Repülj mellé 600 m-re és azonosítsd: ${this.idTime.toFixed(1)} / 8 s · FEGYVER TILOS`;
    else if (m.kind === 'cap') task = `Tartsd a légteret: ${Math.max(0, Math.round((m.minutes || 8) * 60 - this.t))} s · ellenség: ${reds}`;
    else task = `Ellenséges gépek: ${reds} / ${this.red.length} · a te lelövéseid: ${this.kills.length}`;
    this.panel.innerHTML = `<div class="tut-head"><span>${m.title || 'Bevetés'}</span></div>
      <h3>${m.kind === 'intercept' ? 'Légtérrendészet (QRA)' : m.kind === 'cap' ? 'Légtérvédelmi járőr (CAP)' : m.kind === 'bfm' ? 'Légiharc-gyakorlat (BFM)' : 'Légtérfölény (sweep)'}</h3>
      <p>${m.role === 'wing' ? 'Te vagy a <b>2-es</b>: tartsd a vezér mellett a helyed, és válaszolj a rádión (<kbd>I</kbd>).' : 'Te vezeted a köteléket: a kísérődnek rádión adhatsz parancsot (<kbd>I</kbd>).'}</p>
      <div class="tut-task ${this.over ? 'done' : ''}"><b>${this.over ? (this.result && this.result.won ? 'KÉSZ' : 'VÉGE') : 'FELADAT'}</b>${task}</div>
      <div class="tut-foot">Rádiófegyelem: ${this.calls.made} / ${this.calls.expected} · Katapultálás: Ctrl+E kétszer</div>`;
  }
}
