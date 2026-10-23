// Key remapping.  Every action has a default key (the one the game code listens for); a remapped key is
// translated to that default before the game sees it (Input.tr), so nothing else in the game changes.
export const ACTIONS = [
  ['Space', 'Rakéta indítása'], ['t', 'Radar lock'], ['f', 'AIM-9 lock'], ['x', 'Flare + chaff'], ['y', 'Következő radarcél'],
  ['1', 'AIM-9M választás'], ['2', 'AIM-120A választás'], ['r', 'Radar be / ki'], ['s', 'Orr fel'], ['w', 'Orr le'],
  ['a', 'Orsózás balra'], ['d', 'Orsózás jobbra'], ['q', 'Oldalkormány balra'], ['e', 'Oldalkormány jobbra'],
  ['shift', 'Gáz fel / utánégető'], ['z', 'Gáz le'], ['b', 'Fék / légfék'], ['g', 'Futómű'], ['c', 'Körülnézés'],
  ['v', 'Kabin / külső nézet'], ['i', 'Rádió (tartsd: beszéd · nyomd: lista / írás)'], ['u', 'Rakétakamera'], ['o', 'Bullet time (mod)'], ['m', 'Jelölők'], ['Tab', 'TVC (F-16, F-15 ACTIVE)'],
];
const NAMES = { Space: 'Szóköz', shift: 'Shift', Tab: 'Tab', Enter: 'Enter', ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→' };
export const keyLabel = (k) => NAMES[k] || (k.length === 1 ? k.toUpperCase() : k.replace(/^Key|^Numpad/, ''));
const RESERVED = ['Escape', 'h', 'F1', 'p', 'Enter', 'NumpadEnter', 'control'];

// the key each action has now (custom or default)
const current = (custom, def) => custom[def] || def;

// translation table for Input: pressed key -> the default key of its action ('__none' = does nothing)
export function buildMap(custom) {
  const map = {}, taken = new Set(ACTIONS.map(([d]) => current(custom, d)));
  for (const [d] of ACTIONS) {
    const k = current(custom, d);
    if (k !== d) map[k] = d;
    if (!taken.has(d) && !(d in map)) map[d] = '__none';
  }
  return map;
}

// the list in the settings: click a row, press the new key; a key that is in use swaps with it
export function keyEditor(root, custom, onChange) {
  let waiting = null;
  const render = () => {
    root.innerHTML = ACTIONS.map(([d, name]) => `<button type="button" class="keyrow${waiting === d ? ' wait' : ''}" data-d="${d}"><span>${name}</span><kbd>${waiting === d ? 'nyomj egy gombot…' : keyLabel(current(custom, d))}</kbd></button>`).join('') +
      '<button type="button" class="small" id="keys-reset">Alaphelyzet</button>';
    for (const b of root.querySelectorAll('.keyrow')) b.onclick = (e) => { e.stopPropagation(); waiting = b.dataset.d; render(); };
    root.querySelector('#keys-reset').onclick = (e) => { e.stopPropagation(); for (const k of Object.keys(custom)) delete custom[k]; waiting = null; render(); onChange(); };
  };
  addEventListener('keydown', (e) => {
    if (!waiting) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (e.key === 'Escape') { waiting = null; render(); return; }
    let k = e.code === 'ShiftLeft' || e.code === 'ShiftRight' ? 'shift' : e.code && e.code.startsWith('Digit') ? e.code.slice(5)
      : e.key && e.key.length === 1 && /[a-z]/i.test(e.key) ? e.key.toLowerCase() : e.code;
    if (RESERVED.includes(k)) { waiting = null; render(); return; }
    const other = ACTIONS.find(([d]) => d !== waiting && current(custom, d) === k);
    if (other) custom[other[0]] = current(custom, waiting);         // swap
    custom[waiting] = k;
    for (const [d] of ACTIONS) if (custom[d] === d) delete custom[d];
    waiting = null; render(); onChange();
  }, true);
  render();
}
