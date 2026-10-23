// Touch controls for phones and tablets: a virtual stick on the left moves the aim circle (like the mouse or
// the right stick of a pad), a throttle lever on the left edge, and buttons on the right.  Every control
// follows its own finger (pointer id), so firing while steering works.
const CSS = `
#touch { position: fixed; inset: 0; pointer-events: none; z-index: 5; user-select: none; -webkit-user-select: none; }
#touch * { box-sizing: border-box; }
#touch .tc { pointer-events: auto; touch-action: none; position: absolute; }
#touch .t-stick { left: calc(env(safe-area-inset-left) + 13vmin); bottom: 5vmin; width: 34vmin; height: 34vmin; border-radius: 50%;
  border: 2px solid rgba(107,255,133,.45); background: rgba(10,16,20,.12); }
#touch .t-knob { position: absolute; left: 50%; top: 50%; width: 13vmin; height: 13vmin; margin: -6.5vmin 0 0 -6.5vmin; border-radius: 50%;
  background: rgba(107,255,133,.35); border: 2px solid rgba(107,255,133,.8); }
#touch .t-thr { left: calc(env(safe-area-inset-left) + 2vmin); bottom: 5vmin; width: 9vmin; height: 52vmin; border-radius: 1.5vmin;
  border: 2px solid rgba(255,200,64,.5); background: rgba(10,16,20,.15); overflow: hidden; }
#touch .t-thr i { position: absolute; left: 0; right: 0; bottom: 0; background: rgba(107,255,133,.35); }
#touch .t-thr i.ab { background: rgba(255,140,40,.55); }
#touch .t-thr b { position: absolute; left: 0; right: 0; top: 8%; border-top: 2px dashed rgba(255,200,64,.7); }
#touch .t-thr span { position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%) rotate(-90deg);
  font: 600 2.6vmin "JetBrains Mono", monospace; color: #dfe6ea; text-align: center; white-space: nowrap; }
#touch .t-btn { border-radius: 50%; border: 2px solid rgba(223,230,234,.55); background: rgba(10,16,20,.16); color: #dfe6ea; text-shadow: 0 1px 2px #000;
  font: 600 2.7vmin "Oswald", "Arial Narrow", sans-serif; letter-spacing: .04em; display: grid; place-items: center; text-align: center; line-height: 1.05; }
#touch .t-btn.on { background: rgba(255,200,64,.45); border-color: #ffc840; }
#touch .t-gun { right: calc(env(safe-area-inset-right) + 4vmin); bottom: 6vmin; width: 22vmin; height: 22vmin; border-color: rgba(255,90,70,.8); font-size: 3.6vmin; }
#touch .t-fire { right: calc(env(safe-area-inset-right) + 28vmin); bottom: 4vmin; width: 17vmin; height: 17vmin; border-color: rgba(255,200,64,.85); }
#touch .t-lock { right: calc(env(safe-area-inset-right) + 27vmin); bottom: 23vmin; width: 14vmin; height: 14vmin; border-color: rgba(107,255,133,.85); }
#touch .t-flare { right: calc(env(safe-area-inset-right) + 6vmin); bottom: 30vmin; width: 15vmin; height: 15vmin; }
#touch .t-wpn { right: calc(env(safe-area-inset-right) + 43vmin); bottom: 18vmin; width: 12vmin; height: 12vmin; }
#touch .t-brake { right: calc(env(safe-area-inset-right) + 46vmin); bottom: 4vmin; width: 12vmin; height: 12vmin; }
#touch .t-top { top: calc(env(safe-area-inset-top) + 9vmin); width: 11vmin; height: 8vmin; border-radius: 1.2vmin; font-size: 2.4vmin; }
#touch .t-pause { right: calc(env(safe-area-inset-right) + 2vmin); }
#touch .t-view { right: calc(env(safe-area-inset-right) + 14vmin); }
#touch .t-gear { right: calc(env(safe-area-inset-right) + 26vmin); }
#touch .t-ir { right: calc(env(safe-area-inset-right) + 38vmin); }
#touch .t-tvc { right: calc(env(safe-area-inset-right) + 50vmin); }
#rotate-hint { position: fixed; inset: 0; z-index: 20; display: none; place-items: center; background: rgba(5,9,12,.92); color: #dfe6ea;
  font: 600 20px "Oswald", sans-serif; text-align: center; padding: 24px; }
@media (orientation: portrait) { body.touch-play #rotate-hint { display: grid; } }
`;

const BUTTONS = [
  ['t-gun', 'ÁGYÚ', 'hold', 'gun'], ['t-fire', 'RAKÉTA', 'tap', 'Space'], ['t-lock', 'LOCK', 'tap', 't'],
  ['t-flare', 'FLARE', 'hold', 'flare'], ['t-wpn', 'FEGY-<br>VER', 'tap', 'weapon'], ['t-brake', 'FÉK', 'hold', 'brake'],
  ['t-top t-pause', '❚❚', 'tap', 'pause'], ['t-top t-view', 'NÉZET', 'tap', 'v'], ['t-top t-gear', 'FUTÓMŰ', 'tap', 'g'],
  ['t-top t-ir', 'IR LOCK', 'tap', 'f'], ['t-top t-tvc', 'TVC', 'tap', 'Tab'],
];

export class TouchControls {
  constructor(onTap) {
    this.onTap = onTap;
    this.stick = { x: 0, y: 0 }; this.hold = { gun: false, flare: false, brake: false }; this.throttle = null;
    this.active = false;
    const style = document.createElement('style'); style.textContent = CSS; document.head.appendChild(style);
    const root = this.root = document.createElement('div');
    root.id = 'touch'; root.hidden = true;
    root.innerHTML = `<div class="tc t-thr"><i></i><b></b><span>GÁZ</span></div><div class="tc t-stick"><div class="t-knob"></div></div>` +
      BUTTONS.map(([cls, label, , act]) => `<div class="tc t-btn ${cls}" data-act="${act}">${label}</div>`).join('');
    document.body.appendChild(root);
    const hint = document.createElement('div');
    hint.id = 'rotate-hint'; hint.textContent = 'Fordítsd el a telefont fekvő helyzetbe ↻';
    document.body.appendChild(hint);
    this.bindStick(root.querySelector('.t-stick'));
    this.bindThrottle(root.querySelector('.t-thr'));
    for (const el of root.querySelectorAll('.t-btn')) {
      const [, , kind, act] = BUTTONS.find((b) => b[3] === el.dataset.act);
      el.addEventListener('pointerdown', (e) => {
        e.preventDefault(); try { el.setPointerCapture(e.pointerId); } catch (err) { /* synthetic pointer */ } el.classList.add('on');
        if (kind === 'hold') this.hold[act] = true; else this.onTap(act);
      });
      const up = () => { el.classList.remove('on'); if (kind === 'hold') this.hold[act] = false; };
      el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up); el.addEventListener('lostpointercapture', up);
    }
  }
  bindStick(el) {
    const knob = el.querySelector('.t-knob');
    let id = null;
    const move = (e) => {
      const r = el.getBoundingClientRect(), rad = r.width / 2;
      let x = (e.clientX - r.left - rad) / rad, y = (e.clientY - r.top - rad) / rad;
      const l = Math.hypot(x, y);
      if (l > 1) { x /= l; y /= l; }
      this.stick.x = x; this.stick.y = y;
      knob.style.transform = `translate(${x * rad * 0.7}px, ${y * rad * 0.7}px)`;
    };
    el.addEventListener('pointerdown', (e) => { e.preventDefault(); id = e.pointerId; try { el.setPointerCapture(id); } catch (err) { /* ignore */ } move(e); });
    el.addEventListener('pointermove', (e) => { if (e.pointerId === id) move(e); });
    const end = (e) => { if (e.pointerId !== id) return; id = null; this.stick.x = 0; this.stick.y = 0; knob.style.transform = ''; };
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }
  // the top 8 % of the lever is the afterburner
  bindThrottle(el) {
    let id = null;
    const set = (e) => {
      const r = el.getBoundingClientRect(), k = 1 - (e.clientY - r.top) / r.height;
      this.throttle = k > 0.92 ? 1.1 : Math.max(0, Math.min(1, k / 0.92));
    };
    el.addEventListener('pointerdown', (e) => { e.preventDefault(); id = e.pointerId; try { el.setPointerCapture(id); } catch (err) { /* ignore */ } set(e); });
    el.addEventListener('pointermove', (e) => { if (e.pointerId === id) set(e); });
    const end = (e) => { if (e.pointerId === id) id = null; };
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }
  // shown while flying; the lever follows the real throttle (keys, pad) when it is not being touched
  update(visible, player) {
    if (this.root.hidden === visible) this.root.hidden = !visible;
    document.body.classList.toggle('touch-play', visible);
    if (!visible) { this.stick.x = this.stick.y = 0; for (const k in this.hold) this.hold[k] = false; return; }
    const thr = player ? player.controls.throttle : 0, fill = this.root.querySelector('.t-thr i');
    fill.style.height = `${(thr > 1 ? 1 : thr * 0.92) * 100}%`;
    fill.classList.toggle('ab', thr > 1);
    const tvc = this.root.querySelector('.t-tvc');
    tvc.hidden = !(player && player.spec.tvc && !player.spec.tvcAlways);
    tvc.classList.toggle('on', !!(player && player.extreme && !player.spec.tvcAlways));
  }
  takeThrottle() { const t = this.throttle; this.throttle = null; return t; }
}

export const touchDevice = () => (window.matchMedia && matchMedia('(pointer: coarse)').matches) || navigator.maxTouchPoints > 0 && !matchMedia('(pointer: fine)').matches;
