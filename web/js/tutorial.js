// Tutorial: an optional guided flight (main menu -> Oktatás).  Every lesson explains WHAT a system does, HOW to
// use it and WHEN it is worth it, then gives one small task that the game checks by itself.  Target drones do
// not shoot back, and the player's jet cannot be hurt by weapons here (only the ground is dangerous).
import { V, add, sub, mul, norm, len, clamp, DEG, rng } from './util.js';
import { Aircraft } from './sim.js';
import { BANDITS, BANDIT_MISSILES } from './specs.js';
import { steerTowards } from './ai.js';
import { Missile } from './weapons.js';

const $ = (id) => document.getElementById(id);
const k = (key) => `<kbd>${key}</kbd>`;

// a target that just flies: straight, or weaving gently; radar off so the RWR stays quiet
class DronePilot {
  constructor(ac, heading, weave = 0, throttle = 0.9) {
    this.ac = ac; this.heading = heading; this.weave = weave; this.throttle = throttle; this.t = 0; this.alt = ac.pos.z;
    if (ac.radar.on) ac.radar.togglePower();
    ac.pilot = this;
  }
  think() {}
  fly(dt) {
    const ac = this.ac;
    this.t += dt;
    const h = this.heading + Math.sin(this.t * 0.3) * this.weave;
    const climb = clamp((this.alt - ac.pos.z) / 1500, -0.25, 0.25);
    steerTowards(ac.fm, norm(V(Math.sin(h), Math.cos(h), climb)), ac.controls, 0.45, 0.8);
    ac.controls.throttle = this.throttle;
  }
}

function lessons(spec) {
  const f16 = spec.id === 'f16', gun = spec.gun;
  const list = [
    {
      title: 'Üdvözlünk a pilótafülkében!',
      read: true,
      html: `<p>Ez az oktatás lépésről lépésre végigvezet a játékon. Minden lépésnél leírjuk, <b>mit</b> csinál egy
        funkció, <b>hogyan</b> használod és <b>mikor</b> érdemes, utána jön egy kis feladat – a játék magától
        észreveszi, ha megcsináltad.</p>
        <p>A gép közben magától repül. Gyakorlás alatt a lövések nem sebeznek meg, csak a földbe csapódás veszélyes.</p>
        <h4>A képernyő</h4>
        <ul>
          <li><b>Bal oldalt:</b> IAS = sebesség (km/h), M = Mach, G = terhelés, AoA = állásszög,
            THR = gázkar, MOT = hajtómű.</li>
          <li><b>Jobb oldalt:</b> ALT = magasság, AGL = föld feletti magasság, VS = emelkedés, HDG = irány,
            FUEL = üzemanyag, HP = épség.</li>
          <li><b>Középen:</b> a zöld kereszt a gép orra, a szárnyas zöld kör a valódi repülési irány,
            a fehér kör az, ahová célzol.</li>
          <li><b>Bal lent</b> az RWR (ki figyel rád radarral), <b>jobb lent</b> a radar.</li>
        </ul>`,
      task: `Nyomd meg az ${k('Enter')}-t, ha elolvastad.`,
    },
    {
      title: 'Repülés az egérrel',
      html: `<p><b>Mit:</b> külső nézetben az egér a fehér kört mozgatja, a gép pedig az orrát oda fordítja. A
        bedöntést és a húzást egy robotpilóta (instruktor) intézi helyetted.</p>
        <p><b>Hogyan:</b> mozgasd az egeret. Kicsi elmozdulás = finom korrekció, a kép széléig = éles forduló.
        Kézzel is repülhetsz: ${k('S')} orr fel, ${k('W')} orr le, ${k('A')} / ${k('D')} orsózás,
        ${k('Q')} / ${k('E')} oldalkormány – amíg nyomod, az instruktor elengedi a gépet.</p>
        <p><b>Mikor:</b> célzáshoz és üldözéshez az egér a legjobb; kézzel akkor, ha egy manővert pontosan
        akarsz, például teljes erejű húzást az ${k('S')}-sel.</p>`,
      task: 'Fordulj legalább 90°-ot (bármelyik irányba).',
      setup: (t) => { t.flags.turned = 0; t.flags.lastHdg = null; },
      check: (t) => {
        const f = t.player.forward, h = Math.atan2(f.x, f.y);
        if (t.flags.lastHdg !== null) {
          let d = h - t.flags.lastHdg;
          d = Math.atan2(Math.sin(d), Math.cos(d));
          t.flags.turned += d;
        }
        t.flags.lastHdg = h;
        return Math.abs(t.flags.turned) >= 90 * DEG;
      },
      status: (t) => `Eddig: ${Math.round(Math.abs(t.flags.turned) / DEG)}°`,
    },
    {
      title: 'Gáz és utánégető',
      html: `<p><b>Mit:</b> ${k('Shift')} növeli, ${k('Z')} (vagy ${k('Ctrl')}) csökkenti a gázt. 100% a katonai
        teljesítmény (MIL). E fölött jön az utánégető (AB): sokkal több tolóerő, de 4–5-ször annyi üzemanyag
        (F-16: 1,6 → 7,3 kg/s; Super Hornet: 2,8 → 10,3 kg/s).</p>
        <p><b>Hogyan:</b> tartsd nyomva a ${k('Shift')}-et – 100%-nál megáll. Engedd el, és nyomd meg még egyszer:
        ez az AB. Lefelé az első ${k('Z')} kikapcsolja az AB-t. A HUD-on a THR a kar állása, a MOT a hajtómű,
        ami pár másodperc alatt pörög fel.</p>
        <p><b>Mikor:</b> AB-t felszálláskor, ha lelassultál, és éles forduló közben. Utazáshoz MIL vagy kevesebb,
        így tovább bírja az üzemanyag. Hőkövető rakéta ellen kapcsold ki az AB-t, mert kevesebb hőt adsz le.</p>`,
      task: 'Kapcsold be az utánégetőt, aztán vedd vissza 100%-ra.',
      setup: (t) => { t.flags.ab = false; },
      check: (t) => {
        const thr = t.player.controls.throttle;
        if (thr > 1.001) t.flags.ab = true;
        return t.flags.ab && thr <= 1.001;
      },
      status: (t) => (t.flags.ab ? 'Utánégető megvolt – most vissza 100%-ra (Z)' : `Gáz most: ${Math.round(Math.min(t.player.controls.throttle, 1) * 100)}%`),
    },
    {
      title: 'Forduló, G és energia',
      html: `<p><b>Mit:</b> a G a terhelés: vízszintes repülésben 1 G, a gép határa ${spec.gMax} G. Minél nagyobb
        a G, annál élesebben fordulsz – de annál gyorsabban fogy a sebességed. A sebesség az „energiád”:
        ha elfogy, nem tudsz fordulni, és könnyű célpont leszel.</p>
        <p><b>Hogyan:</b> vidd az egeret messze oldalra és felfelé, vagy nyomd az ${k('S')}-t. Közben figyeld a
        bal oldali G és IAS értéket.</p>
        <p><b>Mikor:</b> a legélesebb forduló kb. 650–850 km/h-n megy (ez a sarok-sebesség). Lassabban a gép nem
        tud nagy G-t húzni, gyorsabban túl nagy a fordulókör. Ha elfogyott a sebesség: AB és enyhe süllyedés.
        8 G fölött tartósan elszürkül a kép.</p>`,
      task: 'Húzz legalább 6 G-t.',
      setup: (t) => { t.flags.g = 1; },
      check: (t) => { t.flags.g = Math.max(t.flags.g, t.player.fm.gLoad); return t.flags.g >= 6; },
      status: (t) => `Legnagyobb eddig: ${t.flags.g.toFixed(1)} G`,
    },
    {
      title: 'Kabin és kijelzők',
      html: `<p><b>Mit:</b> a ${k('V')} a kabinnézet. Itt az egér maga a botkormány: előre tolva orr le, magad
        felé húzva orr fel, oldalra orsózás. A bot ott marad, ahová teszed – középre te viszed vissza
        (a bal oldali kis kijelzőn a zöld pont jelzi a semleges állást).</p>
        <p><b>Hogyan:</b> ${k('N')} = lenézel a kijelzőkre (ráközelít, így olvashatók), újra ${k('N')} = vissza.
        ${k('J')} / ${k('K')} / ${k('L')} = a bal / jobb / középső kijelző lapozása.</p>
        <ul>
          <li><b>RDR</b> – radar: a célok, a lockolt cél adatai és típusa, hatótáv-csík</li>
          <li><b>SA</b> – térkép: ellenség, rakéták, harci zóna, bázis</li>
          <li><b>SMS</b> – fegyverzet, lőszer, flare / chaff</li>
          <li><b>ENG</b> – hajtómű, tolóerő, üzemanyag, mennyi kell hazáig (BINGO)</li>
          <li><b>RWR</b> – ki figyel rád, és a rád tartó rakéták</li>
        </ul>
        <p><b>Mikor:</b> a kabinnézet akkor jó, ha a cél előtted van. A kijelzőkre utazás közben vagy lock előtt
        nézz le – csak röviden, mert közben nem látod a HUD-ot.</p>`,
      task: `Válts kabinnézetbe (${k('V')}), nézd meg a kijelzőket (${k('N')}), majd ${k('N')}-nel nézz vissza előre.`,
      setup: (t) => { t.flags.panel = false; },
      check: (t) => {
        const c = t.game.cam;
        if (c.cockpit && c.panelLook) t.flags.panel = true;
        return t.flags.panel && c.cockpit && !c.panelLook;
      },
      status: (t) => (t.flags.panel ? 'Most N-nel nézz vissza előre' : t.game.cam.cockpit ? 'Most nyomd meg az N-t' : 'Nyomd meg a V-t'),
    },
    {
      title: 'Radar lock és AIM-120 – távoli cél',
      html: `<p>Egy céldrón repül feléd kb. 22 km-ről (nem lő vissza). A piros háromszög jelöli, alatta a távolság km-ben.</p>
        <p><b>Mit:</b> az AIM-120A AMRAAM radarvezérlésű rakéta („Fox 3”), 5–35 km-ről lőhető. Kilövés után
        a te radarod vezeti, majd kb. 11–16 km-re a céltól bekapcsolja a saját radarját (PITBULL) – onnan
        magától megy.</p>
        <p><b>Hogyan:</b></p>
        <ol>
          <li>Nyomd meg a ${k('2')}-t: kiválasztod az AIM-120A-t.</li>
          <li>Fordulj a cél felé (vagy nézz rá ${k('C')}-vel), és nyomd meg a ${k('T')}-t: fél másodperc alatt
            lockol, a célon zöld négyzet jelenik meg.</li>
          <li>A jobb oldali DLZ-csík mutatja, elér-e a rakéta. Ha a négyzet piros lesz és villog a
            <b>LŐHETSZ!</b>, nyomd meg a ${k('Space')}-t.</li>
          <li>Tartsd az orrod a cél felé (±60°), amíg meg nem jelenik a PITBULL üzenet.</li>
        </ol>
        <p><b>Mikor:</b> szemből messzebbről is elér, mert a cél feléd repül; hátulról csak közelebbről. Ha a lock
        elvész (a cél 90°-ra fordul – ez a notch), nyomd meg újra a ${k('T')}-t.</p>`,
      task: 'Lődd le a drónt AIM-120-szal.',
      setup: (t) => { t.drone({ dist: 22000, heading: 'toward' }); },
      check: (t) => t.killed(),
      status: (t) => t.droneStatus(),
    },
    {
      title: 'AIM-9 – hőkövető rakéta közelről',
      html: `<p>Egy drón repül előtted kb. 3 km-re, teljes gázzal – jó meleg cél.</p>
        <p><b>Mit:</b> az AIM-9M Sidewinder a gép hőjét követi („Fox 2”). Nem kell hozzá radar, de rövid a
        hatótáva: hátulról 1–8 km, szemből csak 3–4 km. Kilövés után teljesen magától megy.</p>
        <p><b>Hogyan:</b></p>
        <ol>
          <li>Nyomd meg az ${k('1')}-et. Megjelenik egy nagy kör – a rakéta keresője –, és halk morgást hallasz.</li>
          <li>Vidd a célt a körbe: ha hőt lát, magától lockol (dupla kör, magas sípolás). Az ${k('F')}
            azonnal lockol bármelyik ellenségre az orrod előtt ±30°-on belül.</li>
          <li>${k('Space')} = indítás.</li>
        </ol>
        <p><b>Mikor:</b> a cél mögül, főleg ha utánégetővel repül. Ha a cél flare-t szór, várj egy pillanatot
        és lockolj újra. 400 m-en belül már túl közel van – oda az ágyú való.</p>`,
      task: 'Lődd le a drónt AIM-9-cel.',
      setup: (t) => { t.drone({ dist: 3000, heading: 'away', throttle: 0.85, speed: 190, maxDist: 10000 }); },
      check: (t) => t.killed(),
      status: (t) => t.droneStatus(),
    },
    {
      title: 'Gépágyú',
      html: `<p>Most egy lassabb, kicsit kanyargó drón van előtted kb. 900 m-re.</p>
        <p><b>Mit:</b> a 20 mm-es ${gun.name} gépágyú 1 km-en belül hatásos, 6000 lövés/perc, ${gun.ammo}
        lőszer (kb. ${Math.round(gun.ammo / 100)} másodpercnyi tűz).</p>
        <p><b>Hogyan:</b></p>
        <ol>
          <li>Lockold a célt radarral (${k('T')}). Ekkor megjelenik az előretartás-jelző: fehér kör ponttal –
            ide érnek a golyók.</li>
          <li>Tedd a fehér célzókört erre a jelre, és tüzelj a <b>bal egérgombbal</b>, rövid sorozatokkal.</li>
        </ol>
        <p><b>Mikor:</b> ha a cél közel van és előtted, vagy ha elfogytak a rakéták. 1,5 km-nél messzebbről ne
        lőj – a golyók lelassulnak és szétszóródnak.</p>`,
      task: 'Lődd le a drónt.',
      setup: (t) => { t.drone({ dist: 900, heading: 'away', speed: 170, throttle: 0.7, weave: 0.2, maxDist: 6000, hp: 40 }); },
      check: (t) => t.killed(),
      status: (t) => t.droneStatus(),
    },
    {
      title: 'Védekezés: rád lőttek!',
      html: `<p>Pár másodperc múlva egy ellenség rakétát indít rád kb. 9 km-ről, oldalról. A gyakorlásban nem
        sebez, de jelezzük, ha eltalált volna.</p>
        <p><b>Mit jelez a gép:</b> az RWR-en (bal lent) piros villogó jel, gyorsuló sípolás, középen
        <b>MISSILE!</b>, a rakétán piros rombusz a távolsággal és a becsapódásig hátralévő idővel.</p>
        <p><b>Hogyan védekezz:</b></p>
        <ol>
          <li>Fordulj úgy, hogy a rakéta oldalt (3 vagy 9 órában) legyen – ez a <b>notch</b>: a radar nem lát
            jól, ha nem közeledsz felé és nem is távolodsz tőle.</li>
          <li>Közben tartsd nyomva az ${k('X')}-et: chaff (radar ellen) és flare (hőkövető ellen).</li>
          <li>Az utolsó 2–3 másodpercben húzz egy éles fordulót – a rakéta nem tud ilyen élesen fordulni.</li>
          <li>Hőkövető ellen vedd vissza az utánégetőt.</li>
        </ol>
        <p><b>Mikor:</b> azonnal, amint megjelenik a MISSILE!. Egyenesen előre ne menekülj – a rakéta gyorsabb.</p>`,
      task: 'Éld túl a rakétát (ne találjon el).',
      setup: (t) => { t.flags.fireIn = 3; t.flags.missile = null; t.flags.hit = false; t.flags.tries = 0; },
      check: (t, dt) => t.missileDrill(dt),
      status: (t) => t.missileStatus(),
    },
  ];
  if (spec.id === 'f22') {
    list.push({
      title: 'A Raptor: lopakodás és belső fegyvertér',
      html: `<p><b>Lopakodó:</b> az F-22 radarkeresztmetszete apró, ezért az ellenség radarja csak kb. 10–15 km-ről
        lát meg (téged akár 100 km-ről is). Az APG-77 radarod „csendes” (LPI): amíg csak keresel vele, az ellenfél
        RWR-je nem jelez, csak amikor lockolsz.</p>
        <p><b>Belső fegyvertér:</b> 6 AIM-120 a hasban, 1–1 AIM-9 az oldalsó terekben. ${k('Space')}-re előbb kinyílik
        az ajtó, a kar kitolja a rakétát, az leold vagy lerepül a sínről, aztán minden visszacsukódik – kb. 0,7 s
        késéssel indul a rakéta. Amíg az ajtó nyitva van, a géped jól látszik a radaron (a HUD-on: FEGYVERTÉR NYITVA).</p>
        <p><b>Tolóerő-vektorálás:</b> mindig be van kapcsolva (nem kell Tab), 35°-os állásszög, a gép max 8 G-t húz.</p>
        <p><b>Mikor:</b> lőj messziről, amíg nem látnak; rakéta után fordulj el, hogy ne maradj sokáig nyitott
        ajtóval a közelükben. Külső nézetben (${k('V')}) megnézheted, ahogy a rakéta kijön a hasból.</p>`,
      task: `Indíts egy rakétát (${k('Space')}), és nézd meg, ahogy kinyílik a fegyvertér.`,
      setup: (t) => { t.flags.launched = false; },
      check: (t) => t.player.stations.some((st) => st.launch && st.launch.t > 1.0) || t.flags.launched,
      status: (t) => (t.player.bayOpenAny > 0.05 ? 'Fegyvertér nyitva!' : `Fegyver: ${t.player.selected || '-'}`),
    });
  } else if (f16) {
    list.push({
      title: 'Extrém mód: tolóerő-vektorálás és Cobra (F-16)',
      html: `<p>Csak az F-16-on van (mint a kísérleti F-16 MATV-n): a fúvócső ±20°-ot fordul.</p>
        <p><b>Mit ad:</b> 9 G-s fordulók (az egeres instruktor is kihúzza), 32°-os állásszög, gyorsabb orsózás,
        több tolóerő, kis sebességen is irányítható. Cserébe többet fogyaszt.</p>
        <p><b>Cobra:</b> teljes húzásra a gép felágaskodik (80° állásszögig), és egy pillanat alatt rengeteg
        sebességet veszít. Ha egy rakéta <b>3–4 másodpercen belül</b> van tőled, amikor ezt csinálod, nagy eséllyel
        elveszít és elrepül melletted. Ha túl korán csinálod, a rakéta újracéloz, te pedig lelassultál.</p>
        <p><b>Hogyan:</b> ${k('Tab')} = extrém mód be / ki. Cobra: 600 km/h alatt tartsd nyomva az ${k('S')}-t
        (kabinban: bot teljesen hátra) kb. 1 másodpercig, engedd el, adj AB-t, és engedd le az orrot.</p>
        <p><b>Mikor:</b> közelharcban, hogy az ellenfél mögé kerülj, és végső védekezésként rakéta ellen, amikor a
        piros rombusz 3–4 másodpercet mutat.</p>`,
      task: `Kapcsold be az extrém módot (${k('Tab')}), és csinálj egy Cobrát (állásszög 50° fölött).`,
      check: (t) => t.player.extreme && t.player.fm.alpha > 50 * DEG,
      status: (t) => (t.player.extreme ? `Extrém mód BE · ${Math.round(t.player.fm.ias * 3.6)} km/h · AoA ${Math.round(t.player.fm.alpha / DEG)}°`
        : 'Nyomd meg a Tab-ot'),
    });
  } else {
    list.push({
      title: 'A Super Hornet erőssége: nagy állásszög',
      html: `<p><b>Mit:</b> a Hornet nagy szárnya és a törzs melletti LEX miatt 40°-os állásszögig is irányítható:
        lassan is oda tudja fordítani az orrát, ahová kell – ezzel lehet lövéshez jutni közelharcban.</p>
        <p><b>Hogyan:</b> lassíts 450 km/h alá, aztán húzz teljes erővel (${k('S')} vagy egér messze felfelé).</p>
        <p><b>Mikor:</b> csak röviden! Nagy állásszögben gyorsan fogy a sebesség, és a Hornet lassabban gyorsul
        vissza, mint az F-16. Energiaharcban (hosszú, gyors fordulók) az F-16 az erősebb.</p>`,
      task: 'Érj el 30° fölötti állásszöget.',
      check: (t) => t.player.fm.alpha > 30 * DEG,
      status: (t) => `${Math.round(t.player.fm.ias * 3.6)} km/h · AoA ${Math.round(t.player.fm.alpha / DEG)}°`,
    });
  }
  list.push({
    title: 'Harci zóna, bázis, leszállás',
    read: true,
    html: `<p>A játékban a harc a térkép túloldalán, a <b>harci zónában</b> van: a HUD-on borostyán rombusz
      mutatja az irányt és a távolságot, a kabin térképén piros kör. A bázis körüli 14 km-es körben senki nem
      támad – ott nyugodtan fel- és leszállhatsz.</p>
      <p><b>Hullámok:</b> felszállás után kb. 25 másodperccel jön az első hullám a zónába, minden hullám eggyel
      több ellenséget hoz. Az ellenség csak közelről lő (normál nehézségen AIM-120-szal legfeljebb 8 km-ről),
      te sokkal messzebbről lockolhatsz és lőhetsz.</p>
      <p><b>Leszállás:</b> futómű ki (${k('G')}), kb. 270 km/h, lassú süllyedés (4 m/s alatt), vízszintes
      szárnyak; a földön ${k('B')} fékez. A bázis betonján lelassulva újratölt, tankol és javít.
      Arkád módban a rakéták 10 másodperc alatt maguktól visszatöltődnek, realisztikusban csak leszálláskor.</p>
      <p><b>Tipp:</b> messziről AIM-120 (${k('T')} + ${k('Space')}), közelről AIM-9 vagy ágyú, és mindig figyeld
      az RWR-t. Jó repülést!</p>`,
    task: `${k('Enter')} = az oktatás vége, vissza a főmenübe.`,
  });
  return list;
}

export class Tutorial {
  constructor(game) {
    this.game = game; this.panel = $('tutorial'); this.spawned = []; this.deadTime = 0;
    this.steps = lessons(game.player.spec);
    this.panel.hidden = false;
    this.start(0);
  }
  get player() { return this.game.player; }
  get step() { return this.steps[this.i]; }

  start(i) {
    const w = this.game.world;
    w.aircraft = w.aircraft.filter((a) => !this.spawned.includes(a));
    w.missiles = w.missiles.filter((m) => !this.spawned.includes(m.shooter));
    this.spawned = [];
    this.i = i; this.done = false; this.doneTime = 0; this.flags = {};
    const p = this.player;
    p.invulnerable = true;
    // the lessons need both missile types on the jet
    if (!p.stations.some((s) => s.key === 'AIM-9M') || !p.stations.some((s) => s.key === 'AIM-120A')) {
      p.loadout = 'default'; p.rearm();
    }
    if (this.step.setup) this.step.setup(this);
    this.render();
  }
  next() { if (this.i + 1 < this.steps.length) this.start(this.i + 1); else this.finish(); }
  enter() { this.next(); }                     // Enter: read steps go on, task steps can be skipped
  finish() {
    const w = this.game.world;
    w.aircraft = w.aircraft.filter((a) => !this.spawned.includes(a));
    this.panel.hidden = true;
    this.player.invulnerable = false;
    this.game.tutorial = null;
    if (this.game.onTutorialEnd) this.game.onTutorialEnd();
  }

  // ------------------------------------------------------------------ helpers
  drone({ dist, heading = 'away', speed = 220, throttle = 0.9, weave = 0, side = 0, maxDist = 45000, hp = null }) {
    const p = this.player, g = this.game;
    const fwd = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0)), right = V(fwd.y, -fwd.x, 0);
    const pos = add(add(p.pos, mul(fwd, dist)), mul(right, side));
    pos.z = Math.max(p.pos.z, g.terrain.height(pos.x, pos.y) + 1200);
    const hdgP = Math.atan2(fwd.x, fwd.y), h = heading === 'toward' ? hdgP + Math.PI : hdgP;
    const spec = BANDITS[g.opts.enemyType === 'fa18' ? 'fa18' : 'f16'];
    const ac = new Aircraft(spec, 'Céldrón', 'red', pos, h / DEG, speed, { missiles: BANDIT_MISSILES, rnd: rng(7) });
    ac.stations.forEach((s) => { s.loaded = false; }); ac.updateStores();
    if (hp) ac.hp = hp;                          // the gun lesson's drone goes down after a few good bursts
    new DronePilot(ac, h, weave, throttle);
    g.world.addAircraft(ac);
    this.spawned.push(ac);
    this.flags.drone = ac; this.flags.maxDist = maxDist;
    return ac;
  }
  killed() {
    const d = this.flags.drone;
    if (d && !d.alive && d.lastAttacker === this.player) this.flags.kill = true;
    if (this.flags.kill) return true;
    // flew away, or went down without your shot (a hill): a new one
    if (d && (len(sub(d.pos, this.player.pos)) > this.flags.maxDist || !d.alive)) {
      this.game.world.aircraft = this.game.world.aircraft.filter((a) => a !== d);
      this.game.hud.message('A drón elment – itt egy új előtted', 'info', 3);
      this.step.setup(this);
    }
    return false;
  }
  droneStatus() {
    const d = this.flags.drone;
    if (!d || !d.alive) return 'Találat!';
    const dist = len(sub(d.pos, this.player.pos)) / 1000;
    const r = this.player.radar, locked = r.locked === d;
    return `Drón: ${dist.toFixed(1)} km · ${locked ? 'radar lock OK' : 'nincs radar lock'} · fegyver: ${this.player.selected || '-'}`;
  }
  missileDrill(dt) {
    const f = this.flags, p = this.player, g = this.game;
    if (!f.missile) {
      f.fireIn -= dt;
      if (f.fireIn > 0) return false;
      // a bandit appears 7 km out behind on the right and fires one (weak) AIM-120 at once, aimed ahead of you
      const ac = this.drone({ dist: -5000, side: 5000, heading: 'away', speed: 260 });
      const rel = sub(p.pos, ac.pos);
      const m = new Missile(BANDIT_MISSILES['AIM-120A'], ac, ac.pos, ac.vel, norm(rel), ac.rnd, p);
      m.estVel = p.vel.clone();
      g.world.addMissile(m);
      f.missile = m; f.hit = false; f.tries++;
      return false;
    }
    const m = f.missile;
    if (m.alive) {
      // gone past you and flying away, or lost you: that counts as beaten
      const rel = sub(p.pos, m.pos), closing = (m.vel.x * rel.x + m.vel.y * rel.y + m.vel.z * rel.z) / Math.max(len(rel), 1) - 0;
      if ((closing < 0 && len(rel) > 1500) || m.defeated) m.alive = false; else return false;
    }
    if (f.hit) {                               // it would have hit: one more try
      g.hud.message('ELTALÁLT VOLNA – próbáld újra: fordulj oldalra, X, és az utolsó pillanatban éles forduló', 'warn', 5);
      f.missile = null; f.fireIn = 4;
      return false;
    }
    return true;
  }
  missileStatus() {
    const f = this.flags;
    if (!f.missile) return f.tries ? 'Új rakéta jön...' : `Rakéta indul ${Math.max(0, Math.ceil(f.fireIn))} s múlva`;
    const d = len(sub(f.missile.pos, this.player.pos)) / 1000;
    return `RAKÉTA: ${d.toFixed(1)} km · ${f.missile.status}`;
  }

  // ------------------------------------------------------------------ frame
  update(dt) {
    const p = this.player;
    if (!p.alive) {                             // crashed: back in the air, same lesson again
      this.deadTime += dt;
      if (this.deadTime > 2) {
        this.deadTime = 0;
        this.game.state.banner = this.game.state.subBanner = '';
        this.game.spawnPlayer();
        this.start(this.i);
      }
      return;
    }
    const s = this.step;
    if (!this.done && s.check && s.check(this, dt)) { this.done = true; this.render(); }
    if (this.done) { this.doneTime += dt; if (this.doneTime > 2.5) { this.next(); return; } }
    this.renderTime = (this.renderTime || 0) + dt;
    if (this.renderTime > 0.25) { this.renderTime = 0; this.renderStatus(); }
  }
  onEvent(kind, d) {
    if (kind === 'shielded' && d.target === this.player) this.flags.hit = true;
    if (kind === 'kill' && d.killer === this.player && d.victim === this.flags.drone) this.flags.kill = d.weapon;
  }

  render() {
    const s = this.step, n = this.steps.length;
    this.panel.innerHTML = `
      <div class="tut-head"><span>OKTATÁS · ${this.i + 1} / ${n}</span><span class="tut-bar"><i style="width:${(this.i + 1) / n * 100}%"></i></span></div>
      <h3>${s.title}</h3>
      <div class="tut-body">${s.html}</div>
      <div class="tut-task ${this.done ? 'done' : ''}">
        <b>${this.done ? '✓ KÉSZ' : 'FELADAT'}</b> ${this.done ? 'Szép volt! Megyünk tovább…' : s.task}
        <div class="tut-status" id="tut-status"></div>
      </div>
      <div class="tut-foot">${s.read ? `${k('Enter')} = tovább` : `${k('Enter')} = lépés kihagyása`} · ${k('Esc')} = menü (kilépés az oktatásból)</div>`;
    this.renderStatus();
  }
  renderStatus() {
    const el = $('tut-status'), s = this.step;
    if (!el) return;
    try { el.textContent = !this.done && s.status ? s.status(this) : ''; } catch (e) { el.textContent = ''; }
  }
}
