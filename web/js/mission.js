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
import { InstructorPilot } from './autopilot.js';
import { BANDITS, AIRCRAFT, buildLoadout, missilesFor } from './specs.js';

const $ = (id) => document.getElementById(id);

// an AI pilot that keeps its weapons quiet (peacetime): it flies its route, and only defends itself
class TransitPilot extends AIPilot {
  constructor(ac, route, thr = 0.78) { super(ac, 'normal', null); this.route = route; this.leg = 0; this.waved = false; this.thr = thr; }
  think(world) { this.ac.trigger = false; const t = this.findThreat(world); if (t) { this.threat = t; this.state = 'defend'; this.defendTimer = 2; } else if ((this.defendTimer -= 0.1) <= 0) this.state = 'transit'; }
  fly(dt, world) {
    if (this.state === 'defend' && this.threat && this.threat.alive) { const [d, th, g] = this.defend(world); steerTowards(this.ac.fm, d, this.ac.controls, g, 0.8); this.ac.controls.throttle = th; return; }
    const tgt = this.route[Math.min(this.leg, this.route.length - 1)];
    if (len(V(tgt.x - this.ac.pos.x, tgt.y - this.ac.pos.y, 0)) < 2500 && this.leg < this.route.length - 1) this.leg++;
    steerTowards(this.ac.fm, norm(sub(tgt, this.ac.pos)), this.ac.controls, 0.4, 0.7);
    this.ac.controls.throttle = this.thr;
  }
}
// an airliner brought home.  Its own simple control law (a bank angle for the heading, the stick for the flight
// path angle): a gentle descent to a point 22 km out on the extended centre line of the runway, a straight-in
// approach on a 3 degree glide path, the flare, the landing roll and the brakes.
class LinerPilot {
  constructor(ac, field) { this.ac = ac; this.f = field; this.phase = 'iaf'; this.t = 0; ac.pilot = this; }
  think() {}
  fly(dt) {
    const ac = this.ac, fm = ac.fm, c = ac.controls, f = this.f, pos = ac.pos, y0 = f.y - 1500 + 250, G = Math.tan(3 * DEG);
    this.t += dt; c.airbrake = false; c.brakes = false; c.yaw = 0;
    const bank = Math.asin(clamp(-fm.right.z, -1, 1)), hdg = Math.atan2(ac.forward.x, ac.forward.y);
    const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
    const turnTo = (want, maxBank = 22 * DEG) => { const phi = clamp(wrap(want - hdg) * 1.6, -maxBank, maxBank); c.roll = clamp((phi - bank) * 2.5, -1, 1); };
    const path = (gam) => { const g0 = Math.asin(clamp(fm.vel.z / Math.max(fm.speed, 30), -1, 1)); c.pitch = clamp((gam - g0) * 10, -1, 1); };
    const speed = (want) => { c.throttle = clamp(0.5 + (want - fm.ias) * 0.03, 0.04, 1); };
    if (this.phase === 'iaf') {
      const dx = f.x - pos.x, dy = (y0 - 22000) - pos.y, d = Math.hypot(dx, dy);
      const zWant = Math.min(pos.z, f.elevation + 1400 + Math.max(0, d - 4000) * 0.03);
      turnTo(Math.atan2(dx, dy)); path(clamp((zWant - pos.z) / Math.max(d, 3000), -0.07, 0.03)); speed(150);
      if (d < 3000) this.phase = 'intercept';
    } else if (this.phase === 'intercept') {
      const lat = f.x - pos.x, zWant = f.elevation + (y0 - pos.y) * G + 60;
      turnTo(Math.atan2(clamp(lat / 2500, -1, 1) * 0.8, 1)); path(clamp((zWant - pos.z) / 2500, -0.07, 0.03)); speed(125);
      if (y0 - pos.y < 9000 && Math.abs(lat) < 900) { this.phase = 'final'; if (!fm.gearDown) ac.toggleGear(); }
    } else if (this.phase === 'final') {
      const lat = f.x - pos.x, zWant = f.elevation + Math.max(0, y0 - pos.y) * G, vApp = (ac.spec.rotateIas || 78) * 1.45;
      turnTo(Math.atan2(clamp(lat / 1800, -0.3, 0.3), 1), 12 * DEG);
      path(-G + clamp((zWant - (pos.z - fm.gearHeight)) / 400, -0.04, 0.03)); speed(vApp);
      if (!fm.gearDown) ac.toggleGear();
      if (pos.z - f.elevation < fm.gearHeight + 14) this.phase = 'flare';
    } else if (this.phase === 'flare') {
      const h = pos.z - f.elevation - fm.gearHeight, sink = clamp(0.9 + h * 0.14, 0.9, 3);
      turnTo(Math.atan2(clamp((f.x - pos.x) / 1800, -0.1, 0.1), 1), 6 * DEG); path(-sink / Math.max(fm.speed, 40));
      c.throttle = clamp(0.2 + ((ac.spec.rotateIas || 78) * 1.3 - fm.ias) * 0.04, 0, 0.7);
      if (fm.onGround) { this.phase = 'rollout'; this.t = 0; }
    } else {
      c.throttle = 0; c.pitch = 0; c.roll = clamp(-bank * 2, -1, 1); c.brakes = this.t > 2;
      c.yaw = clamp(wrap(0 - hdg) * 4 - (pos.x - f.x) * 0.02, -1, 1);
    }
  }
}
// the AI flight lead: flies to the fight with you on its wing, fights, comes home
class LeadPilot extends AIPilot {
  constructor(ac, skill, area) { super(ac, skill, area); }
}

const MAX_ACTIVE_RED = 4, REINFORCE_GAP = 90;

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
    if (m.kind !== 'scramble' && !m.groundStart) {      // air start: on the way to the fight
      const fm = p.fm;
      fm.onGround = false; fm.pos = V(start.x, start.y, z); fm.vel = mul(V(Math.sin(hdg), Math.cos(hdg), 0), 230);
      fm.quat = qheading(hdg / DEG, 0); fm.gearDown = false; fm.gearPos = 0; fm.groundZ = undefined;
      p.controls.throttle = 0.9; fm.engine = 0.9;
      g.cam.reset(p);
    }
    g.radio.callsign = m.callsign || 'VIPER 1-1';
    // your flight: the AI lead (you on its wing) or your AI wingman
    const side = V(this.dir.y, -this.dir.x, 0);
    // after a take-off the rest of the flight is already up ahead, on the way to the fight
    const ref = m.groundStart ? V(p.pos.x + this.dir.x * 3500, p.pos.y + this.dir.y * 3500, p.pos.z + 1600) : p.pos;
    const blueSpec = (t) => BANDITS[t] || BANDITS.f16;
    const mk = (spec, team, pos, heading, name) => {
      const loadout = spec.internal || spec.id === 'f16' ? 'default' : buildLoadout(spec, 2, 4).layout;
      const ac = new Aircraft(spec, name, team, pos, heading / DEG, 230, { livery: 'viper', missiles: missilesFor(spec, true), loadout, rnd: rng(Math.floor(r() * 1e9)) });
      g.world.addAircraft(ac);
      return ac;
    };
    this.blue = [];
    if (m.role === 'wing') {
      const lead = this.lead = mk(blueSpec(m.leadType || m.playerType), 'blue', add(ref, add(mul(this.dir, 260), mul(side, -180))), hdg, `${m.leadName || (m.callsign || 'VIPER 1-1').replace(/-\d$/, '-1')} (vezér)`);
      lead.pos.z = ref.z + 20;
      new LeadPilot(lead, 'wing', m.kind === 'intercept' ? null : this.area);
      lead.isLead = true; this.blue.push(lead);
      g.radio.callsign = (m.callsign || 'VIPER 1-1').replace(/-\d$/, '-2');
    } else if (m.wingman !== false) {
      const w = mk(blueSpec(m.wingType || m.playerType), 'blue', add(ref, add(mul(this.dir, -260), mul(side, 170))), hdg, `${m.wingName || 'Kísérő'} (2-es)`);
      new WingmanPilot(w, p); g.wingman = w; this.blue.push(w);
    }
    // more friendly flights (allies), on both sides of yours
    let k = 0;
    for (const grp of m.blue || []) for (let i = 0; i < grp.n; i++, k++) {
      const pos = add(add(ref, mul(side, (k % 2 ? 1 : -1) * (2500 + 1200 * Math.floor(k / 2)))), mul(this.dir, -800 * Math.floor(k / 2)));
      const ac = mk(blueSpec(grp.type), 'blue', pos, hdg, `${grp.label || 'Szövetséges'} ${k + 1} (${blueSpec(grp.type).short})`);
      ac.power = grp.power;
      new AIPilot(ac, m.allySkill || 'normal', this.area); this.blue.push(ac);
    }
    // air policing: weapons hold for everybody on your side, the lead and the wingman as well
    if (m.kind === 'intercept') for (const a of this.blue) if (a.pilot) a.pilot.holdFire = true;
    // the other side
    this.scn = m.scenario || 'ident';                    // air policing: 'ident' (a foreign fighter), 'liner' (an airliner in trouble), 'hostile' (it attacks)
    this.weaponsFree = false; this.hostileAct = false; this.answered = false;
    this.red = [];
    // the enemy comes in groups: at most 4 at once, the rest as reinforcements once the first group is thinned out
    const queue = [];
    for (const grp of m.red || []) for (let i = 0; i < grp.n; i++) queue.push(grp);
    this.reserveRed = queue.slice(MAX_ACTIVE_RED); this.reinfT = 0; this.redK = 0;
    this.spawnRed = (grp, back = 0) => {
      const k = this.redK++;
      const spec = BANDITS[grp.type] || BANDITS.su35;
      const pos = add(add(P, mul(this.dir, 14000 + back + r() * 5000)), mul(side, ((k % 5) - 2) * 2600));
      pos.z = Math.max(r() * 3000 + 4000, g.terrain.height(pos.x, pos.y) + 1500);
      const ac = mk(spec, 'red', pos, hdg + Math.PI, `${spec.short} ${k + 1}`);
      ac.power = grp.power;
      if (m.kind === 'intercept') {
        const lim2 = g.terrain.half - 6000, route = [add(P, mul(side, -30000)), add(P, mul(side, -60000))].map((q) => V(clamp(q.x, -lim2, lim2), clamp(q.y, -lim2, lim2), pos.z));
        ac.fm.pos = add(add(P, mul(side, 22000)), mul(this.dir, 3000)); ac.fm.pos.z = this.scn === 'liner' ? 3600 : 7000;
        new TransitPilot(ac, route, this.scn === 'liner' ? 0.55 : 0.78);
        ac.passive = true;
      } else new AIPilot(ac, m.skill || 'normal', this.area);
      this.red.push(ac);
      return ac;
    };
    for (const grp of queue.slice(0, MAX_ACTIVE_RED)) this.spawnRed(grp);
    this.radioOff = g.radio.onCall((call) => this.heard(call));
    this.panel = $('tutorial'); this.panel.hidden = false;
    this.embedded = !!m.embedded;                        // a Sortie (sortie.js) runs the rest: take-off, landing, the log
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
    if (this.m.kind !== 'intercept' || this.over) return;
    const t = this.red[0], cs = this.g.radio.callsign;
    if (call.id === 'interrogate' && this.phase === 'contact' && !this.answered) { this.answered = true; this.interrogated(t); }
    else if (call.id === 'follow_me' && this.phase === 'signal') this.followMe(t);
    else if (call.id === 'weapons_free_req') {
      if (this.hostileAct) this.say('awacs', `${cs}, weapons free, weapons free!`, 900);
      else this.say('awacs', `${cs}, negative. Hold your fire: he has not committed a hostile act.`, 900);
    }
  }
  // the intruder answers the interrogation, as the scenario says
  interrogated(t) {
    const cs = this.g.radio.callsign;
    if (this.scn === 'liner') {
      this.say('intruder', 'Fighter, this is flight AB two one four: we have lost our navigation and half of our instruments. One hundred forty two passengers, fuel is low. Please help us!', 1500);
      this.say('awacs', `${cs}, copy. Take him home: tell him to follow you. Runway three six is clear for him.`, 6500);
      this.phase = 'signal'; this.expect('follow_me', 60);
    } else if (this.scn === 'hostile') {
      this.say('awacs', `${cs}, no reply. Stay with him, weapons hold.`, 1500);
      this.phase = 'wait_hostile'; this.hostileT = this.t + 7;
    } else if (this.rnd() < 0.6) {
      this.say('intruder', 'Fighter, this is Russian military flight four four one two: navigation error, turning back to the east.', 1500);
      this.beginEscort(t);
    } else {
      this.say('awacs', `${cs}, no answer. Show him the way out: tell him to follow you.`, 1500);
      this.phase = 'signal'; this.expect('follow_me', 45);
    }
  }
  followMe(t) {
    const cs = this.g.radio.callsign;
    if (this.scn === 'liner') {
      this.say('intruder', 'Roger, following you. Thank God.', 1200);
      t.pilot = new LinerPilot(t, this.g.terrain.airfield);
      this.phase = 'land'; this.landT0 = this.t;
      this.say('awacs', `${cs}, tower has him: stay with him until he is down.`, 3000);
    } else { this.say('intruder', 'Wilco, turning.', 1200); this.beginEscort(t); }
  }
  beginEscort(t) { this.phase = 'escort'; this.escortTime = 0; if (t.pilot) t.pilot.leg = 1; }
  // the hostile one turns on you
  turnHostile(t) {
    t.pilot = new AIPilot(t, 'normal', this.area); t.passive = false; this.phase = 'hostile';
    this.say('awacs', `${this.g.radio.callsign}, he is turning on you! Defend yourself. Weapons hold until he fires.`, 400);
  }
  // he fired: a hostile act, weapons free for everybody
  hostileActNow() {
    if (this.hostileAct) return;
    this.hostileAct = this.weaponsFree = true;
    for (const a of this.blue) if (a.pilot) a.pilot.holdFire = false;
    this.say('awacs', `${this.g.radio.callsign}, missile in the air! Weapons free, weapons free!`, 200);
    this.g.hud.message('HOSTILE ACT – FEGYVER SZABAD', 'warn', 4, 'wf');
  }
  get p() { return this.g.player; }
  onEvent(kind, d) {
    if (kind === 'launch' && this.m.kind === 'intercept' && d.missile && d.missile.shooter && d.missile.shooter.team === 'red') this.hostileActNow();
    if (kind !== 'kill') return;
    const v = d.victim;
    if (v.team === 'red') {
      this.redLost.push(v.spec.id || v.spec.model);
      if (d.killer === this.p) this.kills.push(v.spec.short);
      if (this.m.kind === 'intercept') {
        // only a shot from your own side is a crime; if the intruder simply crashed, the job is lost, nobody is to blame
        if (d.killer && d.killer.team === 'blue') {
          if (this.weaponsFree) { this.say('awacs', `${this.g.radio.callsign}, splash. He started it. RTB.`, 600); this.finish(true, 'neutralised'); }
          else { this.failNote = 'Lelőtted a polgári/idegen gépet békeidőben – hadbíróság!'; this.finish(false, 'shot_intruder'); }
        }
        else { this.say('awacs', `${this.g.radio.callsign}, the target is down on its own. Mission over, RTB.`); this.finish(false, 'intruder_lost'); }
        return;
      }
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
      const t = reds[0], d = len(sub(t.pos, p.pos)), cs = this.g.radio.callsign;
      this.g.radio.talkOk = d < 10000 && !this.over;                // the radio calls to the other aircraft work in range
      if (this.phase === 'ingress' || this.phase === 'merge') {
        this.idTime = d < 600 ? this.idTime + dt : Math.max(0, this.idTime - dt * 0.5);
        if (this.idTime > 8) {
          this.phase = 'contact'; this.contactT0 = this.t;
          this.say('you', `${cs}: identified, ${this.scn === 'liner' ? 'civil airliner, narrow body, no weapons' : `${t.spec.short}, no weapons visible`}.`);
          this.say('awacs', this.scn === 'liner' ? 'Civil airliner, no flight plan, no radio on guard. Interrogate him on guard frequency.' : 'Copy ID. He does not answer on guard. Interrogate him: ask who he is.', 1500);
          this.expect('interrogate', 60);
        }
      } else if (this.phase === 'contact' && this.scn === 'hostile' && this.t - this.contactT0 > 40) this.interrogated(t);
      else if (this.phase === 'wait_hostile' && this.t > this.hostileT) this.turnHostile(t);
      else if (this.phase === 'hostile' && !this.hostileAct) {
        // hostile intent without a shot: a radar lock on you, his guns firing, or half a minute of attack manoeuvres
        this.hostileT2 = (this.hostileT2 || 0) + dt;
        if ((p.rwr && p.rwr.maxLevel >= 2) || (t.gun && t.gun.firing) || this.hostileT2 > 30) this.hostileActNow();
      } else if (this.phase === 'escort') {
        this.escortTime = d < 3500 ? this.escortTime + dt : this.escortTime;
        if (this.escortTime > 40) { this.phase = 'done'; this.say('awacs', `${cs}, good work, target left the area. RTB.`); this.finish(true); return; }
      } else if (this.phase === 'land') {
        if (t.onGround && t.speed < 25) { this.phase = 'done'; this.say('awacs', `${cs}, he is down safely. Good work, RTB.`); this.say('intruder', 'We are down. Thank you, fighter!', 800); this.finish(true, 'landed'); return; }
        if (this.t - this.landT0 > 900) { this.finish(false, 'intruder_lost'); return; }
      }
    }
    // the intruder flew on out of our airspace before you got to it
    if (m.kind === 'intercept' && reds[0] && ['ingress', 'merge', 'contact', 'signal', 'wait_hostile'].includes(this.phase) && reds[0].pilot.route
      && reds[0].pilot.leg >= reds[0].pilot.route.length - 1 && len(V(reds[0].pos.x - reds[0].pilot.route[1].x, reds[0].pos.y - reds[0].pilot.route[1].y, 0)) < 3500) {
      this.say('awacs', `${this.g.radio.callsign}, the target has left our airspace. Mission over, RTB.`); reds[0].alive = false; this.finish(false, 'escaped'); return;
    }
    if (this.reserveRed.length && this.phase !== 'ingress') {
      this.reinfT += dt;
      if (reds.length <= 1 || this.reinfT > REINFORCE_GAP) {
        const n = Math.min(this.reserveRed.length, 3), grp = this.reserveRed.splice(0, n);
        for (const gr of grp) this.spawnRed(gr, 6000);
        this.reinfT = 0;
        this.say('awacs', `${this.g.radio.callsign}, reinforcements: ${n} more hostile${n > 1 ? 's' : ''} inbound, bearing ${this.bearingTo(this.red[this.red.length - 1])}.`);
      }
    }
    if (m.kind !== 'intercept' && !reds.length && this.red.length && !this.reserveRed.length) { this.say('awacs', `${this.g.radio.callsign}, picture clean. Good work, RTB.`); this.finish(true); return; }
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
    if (this.embedded) {
      this.g.hud.message(won ? 'KÜLDETÉS TELJESÍTVE – térj haza' : 'KÜLDETÉS VÉGE', won ? 'good' : 'warn', 6, 'mission');
      setTimeout(() => this.leave(), 800);
      return;
    }
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
    this.g.radio.talkOk = false;
    if (!this.embedded) { this.panel.hidden = true; this.g.tutorial = null; this.g.state.banner = this.g.state.subBanner = ''; }
    if (this.onEnd) this.onEnd(this.result || { won: false, status: 'abort', kills: 0, blueLost: [], redLost: [], radio: 0 });
  }
  render() {
    const m = this.m, reds = this.red.filter((a) => a.alive).length;
    let task = '';
    if (m.kind === 'intercept') {
      const tk = { contact: 'Kérdezd ki rádión (I): UNKNOWN AIRCRAFT IDENTIFY · FEGYVER TILOS', signal: 'Utasítsd rádión (I): FOLLOW ME', wait_hostile: 'Maradj mellette · FEGYVER TILOS', hostile: 'Védekezz! Tűzengedély csak ha lőnek rád (REQUEST WEAPONS FREE)',
        land: 'Kísérd le a bázisra, amíg le nem száll · NE LŐJ', escort: `Kísérd ki: ${Math.round(this.escortTime)} / 40 s (3,5 km-en belül)` }[this.phase];
      task = this.weaponsFree && this.phase === 'hostile' ? 'FEGYVER SZABAD – semlegesítsd a támadót' : tk || `Repülj mellé 600 m-re és azonosítsd: ${this.idTime.toFixed(1)} / 8 s · FEGYVER TILOS`;
    }
    else if (m.kind === 'cap') task = `Tartsd a légteret: ${Math.max(0, Math.round((m.minutes || 8) * 60 - this.t))} s · ellenség: ${reds}`;
    else task = `Ellenséges gépek: ${reds}${this.reserveRed.length ? ` + ${this.reserveRed.length} erősítés úton` : ''} / ${this.red.length + this.reserveRed.length} · a te lelövéseid: ${this.kills.length}`;
    this.panel.innerHTML = `<div class="tut-head"><span>${m.title || 'Bevetés'}</span></div>
      <h3>${m.kind === 'intercept' ? 'Légtérrendészet (QRA)' : m.kind === 'cap' ? 'Légtérvédelmi járőr (CAP)' : m.kind === 'bfm' ? 'Légiharc-gyakorlat (BFM)' : 'Légtérfölény (sweep)'}</h3>
      <p>${m.role === 'wing' ? 'Te vagy a <b>2-es</b>: tartsd a vezér mellett a helyed, és válaszolj a rádión (<kbd>I</kbd>).' : 'Te vezeted a köteléket: a kísérődnek rádión adhatsz parancsot (<kbd>I</kbd>).'}</p>
      <div class="tut-task ${this.over ? 'done' : ''}"><b>${this.over ? (this.result && this.result.won ? 'KÉSZ' : 'VÉGE') : 'FELADAT'}</b>${task}</div>
      <div class="tut-foot">Rádiófegyelem: ${this.calls.made} / ${this.calls.expected} · Katapultálás: Ctrl+E kétszer</div>`;
  }
}
