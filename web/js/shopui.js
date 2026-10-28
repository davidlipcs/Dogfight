// The hangar screen: jets, paint, engine-room upgrades, mods, intel on the enemy types and the save file.
import { SKINS, PILOT_SKINS, UPGRADES, MODS, PLANES, exportSave, importSave } from './hangar.js';
import { RARITY } from './skins.js';
import { swatch, pilotSvg } from './skinart.js';
import { AIRCRAFT, BANDITS, TRAINERS, PLANE_GROUPS } from './specs.js';

const $ = (id) => document.getElementById(id);
const hex = (c) => '#' + c.toString(16).padStart(6, '0');
const TABS = [['planes', 'Gépek'], ['skins', 'Festések'], ['pilots', 'Pilóta'], ['upgrades', 'Fejlesztések'], ['mods', 'Módok'], ['intel', 'Hírszerzés'], ['save', 'Mentés']];

// what to know about each enemy type, worked out from its numbers (the "reverse engineering" of the intel cards)
const TIPS = {
  f16: 'Könnyű és fürge, de kevés rakétát visz. Szemből a radarja hamar észrevesz – oldalról, alacsonyan közelíts.',
  fa18: 'Nagy állásszögben veszélyes, lassan jól fordul. Tartsd gyorsan a harcot: hamar elveszti az energiáját.',
  f15: 'Nagy tolóerő, sok rakéta, messzire lát. A nagy radarjele miatt messziről lockolható – lőj elsőként.',
  f22: 'Lopakodó: a radar csak közelről látja. Hőkövetővel és gépágyúval kapd el; fegyvertér-nyitáskor jól látszik.',
  su35: 'Tolóerő-vektoros, nagy állásszögű vadász, sok rakétával. Ne fordulj vele lassan: tartsd az energiádat, és lőj messziről.',
  su57: 'Lopakodó, belső fegyvertérrel – a radar csak közelről látja. Hőkövetővel és ágyúval vadászd.',
  mig29: 'Fürge közelharcos, de kevés üzemanyaggal és rövid radar-hatótávval. Messziről lőj AIM-120-szal.',
  mig31: 'Nagyon gyors elfogó (Mach 2,8), de csak 5 G-t bír: fordulóharcban könnyű préda.',
  gripen: 'Kicsi, könnyű és fürge, kicsi a radarjele. Közelről, hőkövetővel a legjobb.',
  typhoon: 'Erős hajtóművek, kiváló gyorsulás és fordulás – az egyik legveszélyesebb ellenfél.',
  rafale: 'Sokoldalú kacsaszárnyas delta, jól fordul alacsony sebességen is. Tartsd a távolságot.',
  f35: 'Lopakodó, belső fegyvertérrel, kiváló érzékelőkkel – messziről lát és lő. Közelharcban nehezebb, mint egy F-16: kényszerítsd fordulóharcra.',
  j20: 'Nagy, lopakodó elfogó, hosszú hatótávú rakétákkal. Közelről, hőkövetővel kapd el.',
  generic: (s) => `${s.short}: ${s.gMax} G, ${s.rollRate}°/s orsózás.`,
};

export class HangarUI {
  constructor(hangar, career, onChange) {
    this.h = hangar; this.career = career; this.onChange = onChange; this.tab = 'planes'; this.flt = { skins: 'all', pilots: 'all' }; this.own = { skins: false, pilots: false };
    $('hangar-close').addEventListener('click', () => this.close());
    $('hangar').addEventListener('keydown', (e) => { if (e.key === 'Escape') this.close(); });
    hangar.onChange(() => this.render());
  }
  open(tab) { if (tab) this.tab = tab; $('menu').hidden = true; $('hangar').hidden = false; this.render(); $('hangar-close').focus(); }
  close() { $('hangar').hidden = true; $('menu').hidden = false; if (this.onChange) this.onChange(); }
  render() {
    const d = this.h.data;
    $('hangar-credits').textContent = `${d.credits.toLocaleString('hu-HU')} kredit`;
    $('hangar-tabs').innerHTML = TABS.map(([id, name]) => `<button type="button" class="tab${id === this.tab ? ' on' : ''}" data-tab="${id}">${name}</button>`).join('');
    for (const b of $('hangar-tabs').querySelectorAll('button')) b.onclick = () => { this.tab = b.dataset.tab; this.render(); };
    const body = $('hangar-body');
    body.innerHTML = this[this.tab]();
    for (const b of body.querySelectorAll('[data-act]')) b.onclick = () => this.act(b.dataset.act, b.dataset.id);
    if (this.tab === 'save') {
      $('save-import').onchange = async (e) => {
        const f = e.target.files[0]; if (!f) return;
        const err = await importSave(f);
        $('save-msg').textContent = err || 'Betöltve! Az oldal újraindul…';
        if (!err) setTimeout(() => location.reload(), 900);
      };
    }
  }
  act(kind, id) {
    const h = this.h, fail = () => { $('hangar-msg').textContent = 'Nincs elég kredit – szerezz többet a levegőben!'; };
    $('hangar-msg').textContent = '';
    if (kind === 'buy-skin') { if (!h.buySkin(id)) fail(); }
    else if (kind === 'equip-skin') h.equipSkin(id);
    else if (kind === 'buy-pilot') { if (!h.buyPilot(id)) fail(); }
    else if (kind === 'equip-pilot') h.equipPilot(id === '-' ? null : id);
    else if (kind === 'flt') { const [t, v] = id.split(':'); this.flt[t] = v; }
    else if (kind === 'own') { this.own[id] = !this.own[id]; }
    else if (kind === 'buy-up') { if (!h.buyUpgrade(id)) fail(); }
    else if (kind === 'buy-mod') { if (!h.buyMod(id)) fail(); }
    else if (kind === 'toggle-mod') h.toggleMod(id);
    else if (kind === 'buy-plane') { if (!h.buyPlane(id)) fail(); }
    else if (kind === 'export') exportSave();
    this.render();
  }
  price(n, owned) { return owned ? '<span class="owned">megvan</span>' : `<span class="price">${n.toLocaleString('hu-HU')} kr</span>`; }
  planes() {
    const all = { ...AIRCRAFT, ...TRAINERS };
    return '<p class="hint">Minden gép ingyenes – a főmenüben, a „Saját gép” sorban választod ki. Itt az adataik.</p><div class="grid">' +
      PLANE_GROUPS.map(([g, keys]) => keys.map((k) => { const s = all[k];
        return `<div class="item"><b>${s.name}</b><span>${g} · ${s.engines} hajtómű, ${Math.round(s.thrustAb / 1000)} kN · ${s.gMax} G · ${Math.round(s.emptyMass).toLocaleString('hu-HU')} kg</span>${this.price(0, true)}</div>`; }).join('')).join('') + '</div>';
  }
  // the filter row of the skins and pilot outfits: by rarity, and "only what I own"
  filters(tab, list, owned) {
    const total = list.length, have = list.filter((x) => owned[x.id]).length;
    const chip = (v, label) => `<button type="button" class="small${this.flt[tab] === v ? ' primary' : ''}" data-act="flt" data-id="${tab}:${v}">${label}</button>`;
    return `<div class="buttons" style="margin:6px 0">${chip('all', `Mind (${total})`)}${Object.keys(RARITY).map((k) => chip(k, `${RARITY[k]} (${list.filter((x) => x.rarity === k).length})`)).join('')}`
      + `<button type="button" class="small${this.own[tab] ? ' primary' : ''}" data-act="own" data-id="${tab}">Megvan: ${have}</button></div>`;
  }
  skins() {
    const d = this.h.data, list = SKINS.filter((s) => (this.flt.skins === 'all' || s.rarity === this.flt.skins) && (!this.own.skins || d.skins[s.id]));
    return `<p class="hint">A festés a te gépedre kerül (minden típusra). Az ellenség marad gyári szürke. ${SKINS.length} festés van.</p>` + this.filters('skins', SKINS, d.skins) + '<div class="grid">' + list.map((s) => {
      const own = !!d.skins[s.id], on = d.skin === s.id;
      const sw = `<img class="swatch" alt="" src="${swatch(s)}" style="width:56px;height:56px;border-radius:6px;object-fit:cover">`;
      const btn = on ? '<em>felszerelve</em>' : own ? `<button type="button" class="small" data-act="equip-skin" data-id="${s.id}">Felszerelem</button>`
        : `<button type="button" class="small primary" data-act="buy-skin" data-id="${s.id}">Megveszem</button>`;
      return `<div class="item${on ? ' sel' : ''}">${sw}<b>${s.name}</b>${s.rarity ? `<span class="rar rar-${s.rarity}">${RARITY[s.rarity]}</span>` : ''}${this.price(s.price, own)}${btn}</div>`;
    }).join('') + '</div>';
  }
  pilots() {
    const d = this.h.data, list = PILOT_SKINS.filter((s) => (this.flt.pilots === 'all' || s.rarity === this.flt.pilots) && (!this.own.pilots || d.pilots[s.id]));
    const none = `<div class="item${d.pilot ? '' : ' sel'}"><b>Alap egyenruha</b>${d.pilot ? '<button type="button" class="small" data-act="equip-pilot" data-id="-">Felszerelem</button>' : '<em>felszerelve</em>'}</div>`;
    return `<p class="hint">A pilótád: sisak, ruha, napellenző. A rádió portréján és a katapultált pilótán látszik. ${PILOT_SKINS.length} öltözet van.</p>` + this.filters('pilots', PILOT_SKINS, d.pilots) + '<div class="grid">' + none + list.map((s) => {
      const own = !!d.pilots[s.id], on = d.pilot === s.id;
      const btn = on ? '<em>felszerelve</em>' : own ? `<button type="button" class="small" data-act="equip-pilot" data-id="${s.id}">Felszerelem</button>`
        : `<button type="button" class="small primary" data-act="buy-pilot" data-id="${s.id}">Megveszem</button>`;
      return `<div class="item${on ? ' sel' : ''}"><img alt="" src="${pilotSvg(s)}" style="width:64px;height:75px;border-radius:6px"><b>${s.name}</b><span class="rar rar-${s.rarity}">${RARITY[s.rarity]}</span>${this.price(s.price, own)}${btn}</div>`;
    }).join('') + '</div>';
  }
  upgrades() {
    return '<div class="grid">' + UPGRADES.map((u) => {
      const lv = this.h.level(u.id), max = lv >= u.prices.length;
      const pips = u.prices.map((_, i) => `<i class="pip${i < lv ? ' on' : ''}"></i>`).join('');
      return `<div class="item"><b>${u.name}</b><span>${u.desc}</span><span class="pips">${pips}</span>` +
        (max ? '<em>maximum szint</em>' : `${this.price(u.prices[lv], false)}<button type="button" class="small primary" data-act="buy-up" data-id="${u.id}">${lv + 1}. szint</button>`) + '</div>';
    }).join('') + '</div><p class="hint">A fejlesztések a te gépedre hatnak, minden módban (az oktatás és a teljesítményteszt kivétel).</p>';
  }
  mods() {
    return '<div class="grid">' + MODS.map((m) => {
      const own = !!this.h.data.mods[m.id], on = this.h.modOn(m.id);
      const btn = own ? `<button type="button" class="small${on ? ' primary' : ''}" data-act="toggle-mod" data-id="${m.id}">${on ? 'BE' : 'KI'}</button>`
        : `<button type="button" class="small primary" data-act="buy-mod" data-id="${m.id}">Megveszem</button>`;
      return `<div class="item"><b>${m.name}</b><span>${m.desc}</span>${this.price(m.price, own)}${btn}</div>`;
    }).join('') + '</div>';
  }
  intel() {
    const v = this.career.data.victims || {};
    return '<p class="hint">Minden ellenségtípus adatlapja az első lelövéskor nyílik meg (a roncsból fejtjük vissza).</p><div class="grid">' +
      Object.keys(BANDITS).map((k) => {
        const s = BANDITS[k], n = v[k] || 0;
        if (!n) return `<div class="item locked"><b>??? – ${s.short}</b><span>Lőj le egyet, hogy megfejtsd az adatait.</span></div>`;
        const mass = s.emptyMass + s.internalFuel * 0.5 + 700, tw = s.thrustAb / (mass * 9.81);
        const rows = [['Tolóerő (utánégető)', `${Math.round(s.thrustAb / 1000)} kN`], ['Harci tömeg', `${Math.round(mass).toLocaleString('hu-HU')} kg`],
          ['Tolóerő/tömeg', tw.toFixed(2)], ['Max terhelés', `${s.gMax} G`], ['Orsózás', `${s.rollRate}°/s`], ['Max állásszög', `${s.alphaLimit}°`],
          ['Radar keresés / lock', `${Math.round(s.radar.searchRange / 1000)} / ${Math.round(s.radar.lockRange / 1000)} km`],
          ['Radarjel szemből', `${s.rcsFront} m²`], ['Gépágyú', `${s.gun.name}, ${s.gun.ammo} lőszer`], ['Lelőtted', `${n}×`]];
        return `<div class="item big"><b>${s.short} – adatlap</b><dl>${rows.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join('')}</dl><span class="tipp">${TIPS[k] || TIPS.generic(s)}</span></div>`;
      }).join('') + '</div>';
  }
  save() {
    const d = this.h.data;
    return `<p>Az egész előrehaladásod (kreditek, vásárlások, karrier, kitüntetések, beállítások) egy fájlban. Mentsd el, és egy másik gépen vagy böngészőben töltsd vissza – mint egy memóriakártya.</p>
      <div class="buttons"><button type="button" class="primary" data-act="export">⤓ Mentés letöltése</button>
      <label class="filebtn">⤒ Mentés betöltése<input type="file" id="save-import" accept=".json,application/json" hidden></label></div>
      <p class="hint" id="save-msg"></p>
      <p class="hint">Eddig összesen ${d.earned.toLocaleString('hu-HU')} kreditet szereztél. Betöltéskor a mostani állás biztonsági másolatba kerül.</p>`;
  }
}
