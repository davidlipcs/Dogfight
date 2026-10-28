// the JavaScript war: 150 days with a fixed random source, for test_campaign.py
import './shim.mjs';
const C = await import('./js/campaign.js');
let x = 987654321;
Math.random = () => { x = (x * 16807) % 2147483647; return (x - 1) / 2147483646; };
const w = C.newWar('us', 4242);
w.started = true;
const snaps = [];
for (let d = 1; d <= 150; d++) {
  C.simulateDay(w);
  if (w.day % 4 === 0) C.aiDiplomacy(w);
  if (d % 30 === 0) {
    snaps.push({ day: w.day, fleets: Object.fromEntries(Object.entries(w.powers).map(([k, p]) => [k, C.totalFleet(p.fleet)])),
      trust: { ...w.trust }, money: Object.fromEntries(Object.entries(w.powers).map(([k, p]) => [k, Math.round(p.money * 100) / 100])), over: !!w.over });
  }
}
const seen = C.seenFleet(w, 'ru');
const bud = C.budgetOf(w, 'us');
console.log(JSON.stringify({ snaps, seen: seen.fleet, bud, log: w.log.length }));
