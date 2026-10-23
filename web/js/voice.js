// Spoken callouts with the browser's own speech synthesis: the warning voice of a fighter ("Pull up",
// "Missile") and the pilot's radio calls ("Fox two", "Splash one").  English on purpose, like the real ones.
// Works offline with the voices of the operating system; silently does nothing without them.
export class Voice {
  constructor() {
    this.synth = window.speechSynthesis || null;
    this.enabled = true; this.volume = 0.8; this.last = {}; this.voice = null;
    if (!this.synth) return;
    const pick = () => {
      const vs = this.synth.getVoices();
      // a female English voice sounds most like the real warning system; any English voice will do
      this.voice = vs.find((v) => /en[-_]US/i.test(v.lang) && /female|zira|samantha|jenny|aria|google us english/i.test(v.name))
        || vs.find((v) => /^en/i.test(v.lang)) || null;
    };
    pick();
    if ('onvoiceschanged' in this.synth) this.synth.onvoiceschanged = pick;
  }
  // key: the kind of callout; minGap: seconds before the same kind may be said again; urgent: cut the queue
  say(key, text, minGap = 4, urgent = false) {
    if (!this.synth || !this.enabled || this.volume <= 0) return;
    const now = performance.now() / 1000;
    if (now - (this.last[key] || -1e9) < minGap) return;
    this.last[key] = now;
    try {
      if (urgent) this.synth.cancel();
      else if (this.synth.speaking && this.synth.pending) return;      // never pile up a backlog
      const u = new SpeechSynthesisUtterance(text);
      if (this.voice) u.voice = this.voice;
      u.lang = this.voice ? this.voice.lang : 'en-US';
      u.rate = urgent ? 1.25 : 1.1; u.pitch = 1.05; u.volume = this.volume;
      this.synth.speak(u);
    } catch (e) { /* some browsers throw without a user gesture */ }
  }
  stop() { try { if (this.synth) this.synth.cancel(); } catch (e) { /* ignore */ } }
}
