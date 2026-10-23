// In-game music: four tracks written as code (a small step sequencer on WebAudio: bass, pads, arpeggio,
// lead and drums), or the player's own music file.  No audio files are shipped.
const NOTE = (n) => 440 * Math.pow(2, (n - 69) / 12);          // MIDI note -> Hz

// a track: tempo, chord roots (MIDI) per bar, a scale for the arpeggio, patterns of 16 steps per bar
export const TRACKS = [
  { id: 'patrol', name: 'Hajnali járőr', bpm: 92, chords: [50, 46, 43, 45], minor: true, arp: [0, 7, 12, 15, 12, 7, 3, 7],
    kick: 'x...x...x...x...', snare: '....x.......x...', hat: '..x...x...x...x.', bass: 'x..x..x.x..x..x.', lead: null, wave: 'triangle' },
  { id: 'burner', name: 'Utánégető', bpm: 128, chords: [45, 41, 48, 43], minor: true, arp: [0, 12, 7, 12, 3, 12, 7, 15],
    kick: 'x...x...x...x...', snare: '....x.......x..x', hat: 'xxxxxxxxxxxxxxxx', bass: 'x.xxx.xxx.xxx.xx', lead: [12, 15, 19, 17, 15, 12, 10, 12], wave: 'sawtooth' },
  { id: 'cobra', name: 'Kobra', bpm: 140, chords: [40, 40, 43, 38], minor: true, arp: [0, 3, 7, 10, 12, 10, 7, 3],
    kick: 'x..x..x.x..x..x.', snare: '....x.......x...', hat: 'x.xxx.xxx.xxx.xx', bass: 'xx.xxx.xxx.xxx.x', lead: [24, 22, 19, 22, 24, 27, 26, 22], wave: 'square' },
  { id: 'night', name: 'Éjszakai bevetés', bpm: 104, chords: [48, 44, 41, 43], minor: false, arp: [0, 4, 7, 11, 14, 11, 7, 4],
    kick: 'x.......x.......', snare: '....x.......x...', hat: '..x...x...x...xx', bass: 'x...x.x.x...x.x.', lead: null, wave: 'triangle' },
];

export class Music {
  constructor() {
    this.ctx = null; this.track = null; this.volume = 0.5; this.timer = null; this.audioEl = null; this.ownUrl = null; this.ownName = '';
  }
  ensure() {
    if (this.ctx) return true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    this.ctx = new AC();
    this.out = this.ctx.createGain(); this.out.gain.value = this.volume * 0.5;
    // a little echo makes the synths sound like music instead of beeps
    const delay = this.ctx.createDelay(), fb = this.ctx.createGain(), wet = this.ctx.createGain();
    delay.delayTime.value = 0.28; fb.gain.value = 0.28; wet.gain.value = 0.22;
    this.fx = this.ctx.createGain();
    this.fx.connect(this.out); this.fx.connect(delay); delay.connect(fb).connect(delay); delay.connect(wet).connect(this.out);
    this.out.connect(this.ctx.destination);
    const n = this.ctx.sampleRate * 0.4, b = this.ctx.createBuffer(1, n, this.ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    this.noise = b;
    return true;
  }
  setVolume(v) {
    this.volume = v;
    if (this.out) this.out.gain.setTargetAtTime(v * 0.5, this.ctx.currentTime, 0.05);
    if (this.audioEl) this.audioEl.volume = Math.min(1, v);
  }
  // id: a track id, 'own' (the loaded file) or 'off'
  play(id) {
    this.stop();
    if (id === 'off' || !id) return;
    if (id === 'own') {
      if (!this.ownUrl) return;
      this.audioEl = new Audio(this.ownUrl); this.audioEl.loop = true; this.audioEl.volume = Math.min(1, this.volume);
      this.audioEl.play().catch(() => {});
      this.track = 'own';
      return;
    }
    const t = TRACKS.find((x) => x.id === id);
    if (!t || !this.ensure()) return;
    if (this.ctx.state !== 'running') this.ctx.resume();
    this.track = id; this.def = t; this.step = 0; this.next = this.ctx.currentTime + 0.1;
    this.timer = setInterval(() => this.schedule(), 50);
  }
  stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null; this.track = null;
    if (this.audioEl) { this.audioEl.pause(); this.audioEl = null; }
  }
  pause(on) {
    if (this.audioEl) { if (on) this.audioEl.pause(); else this.audioEl.play().catch(() => {}); }
    if (this.ctx) { if (on) this.ctx.suspend(); else this.ctx.resume(); }
  }
  loadOwn(file) {
    if (this.ownUrl) URL.revokeObjectURL(this.ownUrl);
    this.ownUrl = URL.createObjectURL(file); this.ownName = file.name;
  }
  // look-ahead scheduler: the notes of the next 0.2 s are queued on the audio clock
  schedule() {
    const t = this.def, spb = 60 / t.bpm / 4;                 // seconds per 16th
    while (this.next < this.ctx.currentTime + 0.2) {
      const s = this.step % 16, bar = Math.floor(this.step / 16) % t.chords.length, root = t.chords[bar], at = this.next;
      if (t.kick[s] === 'x') this.kick(at);
      if (t.snare[s] === 'x') this.hit(at, 0.25, 1800, 0.18);
      if (t.hat[s] === 'x') this.hit(at, 0.05, 7000, 0.06);
      if (t.bass[s] === 'x') this.tone(at, NOTE(root - 12), spb * 1.6, 'sawtooth', 0.16, 600);
      if (s % 2 === 0) this.tone(at, NOTE(root + 12 + t.arp[(s / 2) % t.arp.length]), spb * 1.4, t.wave, 0.05, 3000);
      if (s === 0) for (const iv of t.minor ? [0, 3, 7] : [0, 4, 7]) this.tone(at, NOTE(root + iv), spb * 15, 'triangle', 0.035, 1500, true);
      if (t.lead && Math.floor(this.step / 64) % 2 === 1 && s % 4 === 0) this.tone(at, NOTE(root + t.lead[(s / 4 + bar * 4) % t.lead.length]), spb * 3.5, 'square', 0.04, 2400);
      this.next += spb; this.step++;
    }
  }
  tone(at, f, dur, type, vol, cutoff, pad = false) {
    const c = this.ctx, o = c.createOscillator(), g = c.createGain(), lp = c.createBiquadFilter();
    o.type = type; o.frequency.value = f; lp.type = 'lowpass'; lp.frequency.value = cutoff;
    const a = pad ? dur * 0.3 : 0.005;
    g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(vol, at + a); g.gain.exponentialRampToValueAtTime(0.0005, at + dur);
    o.connect(lp).connect(g).connect(this.fx); o.start(at); o.stop(at + dur + 0.05);
  }
  kick(at) {
    const c = this.ctx, o = c.createOscillator(), g = c.createGain();
    o.frequency.setValueAtTime(140, at); o.frequency.exponentialRampToValueAtTime(42, at + 0.12);
    g.gain.setValueAtTime(0.5, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.25);
    o.connect(g).connect(this.out); o.start(at); o.stop(at + 0.3);
  }
  hit(at, dur, f, vol) {
    const c = this.ctx, s = c.createBufferSource(), g = c.createGain(), hp = c.createBiquadFilter();
    s.buffer = this.noise; hp.type = 'highpass'; hp.frequency.value = f;
    g.gain.setValueAtTime(vol, at); g.gain.exponentialRampToValueAtTime(0.001, at + dur);
    s.connect(hp).connect(g).connect(this.out); s.start(at); s.stop(at + dur + 0.02);
  }
}
