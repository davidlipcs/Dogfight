// the JavaScript radio's idea of what was said, for the phrases of test_radio.py
import './shim.mjs';
const { CALLS, normalise, recognise } = await import('./js/radio.js');
const phrases = JSON.parse(process.argv[2] || '[]');
const allowed = CALLS.filter((c) => c.to !== 'target' && c.id !== 'weapons_free_req');
const out = phrases.map((p) => { const c = recognise(p, allowed); return [normalise(p), c ? c.id : null]; });
console.log(JSON.stringify(out));
