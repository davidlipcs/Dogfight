// Two players, no server: a WebRTC data channel that is set up by copying one short code each way (over
// Messenger, Discord, anything).  The host makes an offer code, the friend pastes it and gets an answer code back,
// the host pastes that and the link opens.  After that the two games exchange their jets' positions ~20 times
// a second and each one draws the other as a "ghost" aircraft (NetPilot) - nothing else is shared, so every
// player flies their own physics and the races compare times.
import { THREE } from './util.js';
const ICE = [{ urls: ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302'] }];
const b64 = (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64 = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));
const pipe = async (bytes, stream) => new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer());

// the session description as a short text: deflated JSON when the browser can, plain otherwise
export async function pack(desc) {
  const raw = new TextEncoder().encode(JSON.stringify({ t: desc.type, s: desc.sdp }));
  if (typeof CompressionStream === 'function') return 'DF1-' + b64(await pipe(raw, new CompressionStream('deflate-raw')));
  return 'DF0-' + b64(raw);
}
export async function unpack(code) {
  code = String(code || '').replace(/\s+/g, '');
  const m = /^DF([01])-([\w-]+)$/.exec(code);
  if (!m) throw new Error('ez nem egy játékkód');
  let bytes = unb64(m[2]);
  if (m[1] === '1') bytes = await pipe(bytes, new DecompressionStream('deflate-raw'));
  const o = JSON.parse(new TextDecoder().decode(bytes));
  return { type: o.t, sdp: o.s };
}

class Link {
  constructor() { this.reset(); this.handlers = {}; this.onstatus = null; }
  reset() { this.pc = null; this.state = null; this.role = null; this.status = 'idle'; this.fast = null; this.safe = null; this.peer = null; }
  get open() { return this.status === 'open'; }
  on(type, fn) { this.handlers[type] = fn; }
  setStatus(s) { this.status = s; if (this.onstatus) this.onstatus(s); }
  make(role) {
    this.close();
    this.role = role;
    const pc = this.pc = new RTCPeerConnection({ iceServers: ICE });
    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;
      if (s === 'failed' || s === 'closed' || s === 'disconnected') { if (this.status !== 'idle') this.setStatus('closed'); }
    };
    return pc;
  }
  wire(dc) {
    dc.onmessage = (e) => { let m; try { m = JSON.parse(e.data); } catch (x) { return; } const h = this.handlers[m.t]; if (h) h(m); };
    if (dc.label === 'fast') { this.fast = dc; return; }
    this.safe = dc;
    dc.onopen = () => this.setStatus('open');
    dc.onclose = () => { if (this.status === 'open') this.setStatus('closed'); };
  }
  gathered(pc) {
    return new Promise((res) => {
      if (pc.iceGatheringState === 'complete') { res(); return; }
      const done = () => { pc.removeEventListener('icegatheringstatechange', chk); res(); };
      const chk = () => { if (pc.iceGatheringState === 'complete') done(); };
      pc.addEventListener('icegatheringstatechange', chk);
      setTimeout(done, 6000);
    });
  }
  // host: the offer code for the friend
  async host() {
    const pc = this.make('host');
    this.wire(pc.createDataChannel('safe'));
    this.wire(pc.createDataChannel('fast', { ordered: false, maxRetransmits: 0 }));
    await pc.setLocalDescription(await pc.createOffer());
    await this.gathered(pc);
    this.setStatus('wait');
    return pack(pc.localDescription);
  }
  // friend: paste the offer, get the answer code
  async join(offerCode) {
    const desc = await unpack(offerCode);
    if (desc.type !== 'offer') throw new Error('ez a válaszkód, nem a meghívó');
    const pc = this.make('guest');
    pc.ondatachannel = (e) => this.wire(e.channel);
    await pc.setRemoteDescription(desc);
    await pc.setLocalDescription(await pc.createAnswer());
    await this.gathered(pc);
    this.setStatus('wait');
    return pack(pc.localDescription);
  }
  // host: paste the answer, the link opens
  async accept(answerCode) {
    const desc = await unpack(answerCode);
    if (desc.type !== 'answer') throw new Error('ez a meghívó, nem a válaszkód');
    await this.pc.setRemoteDescription(desc);
  }
  // reliable (start, results, hello) and unreliable-fast (the jet's state) messages
  send(o) { if (this.safe && this.safe.readyState === 'open') this.safe.send(JSON.stringify(o)); }
  sendFast(o) { const c = this.fast && this.fast.readyState === 'open' ? this.fast : this.safe; if (c && c.readyState === 'open') c.send(JSON.stringify(o)); }
  close() {
    const pc = this.pc;
    this.pc = null; this.fast = this.safe = null; this.status = 'idle'; this.peer = null;
    if (pc) { try { pc.close(); } catch (e) { /* already closed */ } }
  }
}
export const link = new Link();

// The friend's jet as seen here: an aircraft whose position comes from the link (dead reckoning plus smoothing).
// sim.js leaves it alone (aircraft.ghost): no physics, no sensors, no damage.
export class NetPilot {
  constructor(ac) { this.ac = ac; ac.pilot = this; ac.ghost = true; this.snap = null; this.fresh = true; this.target = new THREE.Quaternion(); }
  receive(s) {
    this.target.set(s.q[0], s.q[1], s.q[2], s.q[3]);
    this.snap = { p: s.p, v: s.v, c: s.c, e: s.e, g: s.g, at: performance.now() };
  }
  get seen() { return !!this.snap; }
  think() { /* nothing */ }
  fly(dt) {
    const s = this.snap, ac = this.ac, fm = ac.fm;
    if (!s) return;
    const age = Math.min((performance.now() - s.at) / 1000, 0.4);
    const tx = s.p[0] + s.v[0] * age, ty = s.p[1] + s.v[1] * age, tz = s.p[2] + s.v[2] * age;
    const far = Math.hypot(tx - fm.pos.x, ty - fm.pos.y, tz - fm.pos.z) > 300;
    const k = this.fresh || far ? 1 : 1 - Math.exp(-dt * 12);
    fm.pos.x += (tx - fm.pos.x) * k; fm.pos.y += (ty - fm.pos.y) * k; fm.pos.z += (tz - fm.pos.z) * k;
    fm.quat.slerp(this.target, k);
    fm.quat.normalize();
    fm.vel.set(s.v[0], s.v[1], s.v[2]);
    fm.engine = s.e; ac.controls.pitch = s.c[0]; ac.controls.roll = s.c[1]; ac.controls.yaw = s.c[2]; ac.controls.throttle = s.e;
    fm.gearDown = !!s.g; fm.gearPos = s.g ? 1 : 0; fm.onGround = false;
    this.fresh = false;
  }
}

const r3 = (n) => Math.round(n * 1000) / 1000;
// the jet's state as a packet (positions to the decimetre, the rest rounded)
export function snapshot(ac) {
  const p = ac.pos, v = ac.vel, q = ac.quat, c = ac.controls;
  return { t: 's', p: [Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10, Math.round(p.z * 10) / 10], v: [Math.round(v.x), Math.round(v.y), Math.round(v.z)],
    q: [r3(q.x), r3(q.y), r3(q.z), r3(q.w)], c: [r3(c.pitch), r3(c.roll), r3(c.yaw)], e: r3(ac.fm.engine), g: ac.fm.gearDown ? 1 : 0 };
}
