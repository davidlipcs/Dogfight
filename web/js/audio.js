// Procedural WebAudio sounds (port of dogfight/audio.py): engine, afterburner, gun, Sidewinder growl /
// lock tone, RWR tones, launch, hits and explosions.  Created on the first click (browser autoplay rules).
import { IR } from './specs.js';
import { len, sub } from './util.js';

const RATE = 22050;

function buffer(ctx, seconds, fn) {
  const n = Math.floor(RATE * seconds), b = ctx.createBuffer(1, n, RATE), d = b.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = Math.max(-1, Math.min(1, fn(i / RATE, i)));
  return b;
}

export class Sounds {
  constructor(volume = 0.7) {
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = AC ? new AC({ sampleRate: 44100 }) : null;
    this.loops = {};
    if (!this.ctx) return;
    const c = this.ctx;
    this.master = c.createGain(); this.master.gain.value = volume; this.master.connect(c.destination);
    let seed = 1;
    const noise = () => { seed = (seed * 16807) % 2147483647; return seed / 1073741823.5 - 1; };
    // low-passed noise for engine / wind
    let lp = 0, lp2 = 0;
    const rumble = buffer(c, 2, () => { lp += (noise() - lp) * 0.08; return lp * 3.2; });
    const roar = buffer(c, 2, () => { lp2 += (noise() - lp2) * 0.35; return lp2 * 1.6; });
    const whine = buffer(c, 1, (t) => 0.18 * Math.sin(2 * Math.PI * 900 * t) + 0.08 * Math.sin(2 * Math.PI * 1830 * t) + 0.05 * noise());
    const gun = buffer(c, 0.5, (t) => { const ph = (t * 100) % 1; return (ph < 0.45 ? 1 : 0.35) * noise() * 0.9; });
    const growl = buffer(c, 1, (t) => 0.35 * (0.55 + 0.45 * Math.sin(2 * Math.PI * 20 * t)) *
      (Math.sin(2 * Math.PI * 400 * t) + 0.5 * Math.sin(2 * Math.PI * 800 * t) + 0.25 * Math.sin(2 * Math.PI * 1200 * t)));
    const lockTone = buffer(c, 1, (t) => 0.4 * Math.sin(2 * Math.PI * 1600 * t));
    const beeps = (f, hz, duty) => buffer(c, 1, (t) => ((t * hz) % 1 < duty ? 0.4 * Math.sin(2 * Math.PI * f * t) : 0));
    const warble = buffer(c, 1, (t) => 0.4 * Math.sin(2 * Math.PI * ((t * 12) % 1 < 0.5 ? 1100 : 1500) * t));
    this.buffers = {
      engine: rumble, afterburner: roar, whine, gun, growl, lock_tone: lockTone,
      rwr_lock: beeps(1000, 4, 0.5), rwr_launch: warble,
      rwr_new: buffer(c, 0.35, (t) => ((t * 10) % 1 < 0.5 ? 0.4 * Math.sin(2 * Math.PI * 1200 * t) : 0)),
      launch: buffer(c, 1.6, (t) => { lp2 += (noise() - lp2) * 0.25; return lp2 * 2.2 * Math.exp(-t * 1.6) * Math.min(1, t * 30); }),
      hit: buffer(c, 0.25, (t) => noise() * Math.exp(-t * 18)),
      explosion: buffer(c, 2.5, (t) => { lp += (noise() - lp) * 0.05; return lp * 6 * Math.exp(-t * 1.5) * Math.min(1, t * 80); }),
    };
  }
  resume() { if (this.ctx && this.ctx.state !== 'running') this.ctx.resume(); }
  play(name, volume = 1, rate = 1) {
    if (!this.ctx) return;
    const s = this.ctx.createBufferSource(), g = this.ctx.createGain();
    s.buffer = this.buffers[name]; s.playbackRate.value = rate; g.gain.value = volume;
    s.connect(g).connect(this.master); s.start();
  }
  loop(name, on, volume = 1, rate = 1) {
    if (!this.ctx) return;
    let l = this.loops[name];
    if (!l && !on) return;
    if (!l) {
      const s = this.ctx.createBufferSource(), g = this.ctx.createGain();
      s.buffer = this.buffers[name]; s.loop = true; g.gain.value = 0;
      s.connect(g).connect(this.master); s.start();
      l = this.loops[name] = { s, g };
    }
    const t = this.ctx.currentTime;
    l.g.gain.setTargetAtTime(on ? volume : 0, t, 0.05);
    if (on) l.s.playbackRate.setTargetAtTime(rate, t, 0.1);
  }
  stopAll() { for (const k of Object.keys(this.loops)) this.loop(k, false); }
  handleEvent(kind, d, player) {
    if (!this.ctx || !player) return;
    if (kind === 'launch' && d.shooter === player) this.play('launch', 0.8);
    else if (kind === 'explosion') {
      const dist = len(sub(d.pos, player.pos));
      if (dist < 12000) this.play('explosion', Math.max(0.15, 1 - dist / 12000), 0.8 + 0.3 * Math.random());
    } else if (kind === 'hit' && (d.target === player || d.shooter === player)) this.play('hit', 0.7);
  }
  update(player, paused) {
    if (!this.ctx) return;
    if (!player || !player.alive || paused) { this.stopAll(); return; }
    const e = player.fm.engine, e1 = Math.min(e, 1);
    this.loop('engine', true, 0.35 + 0.35 * e1, 0.6 + 0.6 * e1);
    this.loop('whine', true, 0.05 + 0.12 * e1, 0.7 + 0.45 * e1);
    this.loop('afterburner', e > 1.0, 0.55);
    this.loop('gun', player.gun.firing, 0.8);
    const sp = player.selectedSpec, tone = sp && sp.guidance === IR ? player.irSeeker.tone() : 'none';
    this.loop('growl', tone === 'growl', 0.22);
    this.loop('lock_tone', tone === 'lock', 0.25);
    const level = player.rwr.maxLevel;
    // missile warning: the warble speeds up as the nearest missile closes in
    const near = player.rwr.incoming.length ? player.rwr.incoming[0].dist : 1e9;
    this.loop('rwr_launch', level >= 3, 0.45, 1 + 0.8 * Math.max(0, Math.min(1, (8000 - near) / 8000)));
    this.loop('rwr_lock', level === 2, 0.3);
    if (player.rwr.newSearch && !this.prevNew) this.play('rwr_new', 0.3);
    this.prevNew = player.rwr.newSearch;
  }
}
