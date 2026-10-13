# Dogfight – F-16C Viper: teljes dokumentáció

Ez a dokumentum mindent leír, ami a projektben elkészült: hol és hogyan lehet játszani, mit tud a játék,
hogyan épül fel a kód, hogyan kell karbantartani, és milyen lépésekben készült (fejlesztési napló).
A rövidebb, játékosoknak szóló leírás a [README](../README.md)-ben van.

---

## 1. Áttekintés

War Thunder-szerű légiharc-játék egyetlen géppel, az **F-16C Block 50 Viperrel**. A repülés, a radar,
a rakéták és a lockolás valódi adatokra épülnek (War Thunder- és valós F-16 értékek). Két, egymással
egyenértékű változat van:

| Változat | Hol fut | Mire jó |
|---|---|---|
| **Böngészős** (`web/`, Three.js) | Chrome, telepítés nélkül; GitHub Pages-ről vagy egyetlen letöltött fájlból | ezzel játszik a legtöbb ember, iskolában is |
| **Python** (`dogfight/`, Panda3D) | saját gépen, `python main.py` | az „eredeti”, ebből készülnek a böngészős változat modelljei és a terep |

A két változat ugyanazt a szimulációt használja (a JavaScript a Python sorról sorra átírt változata),
ugyanazokkal a számokkal.

---

## 2. Hol és hogyan lehet játszani

| Mód | Link / parancs | Megjegyzés |
|---|---|---|
| **GitHub Pages** | https://davidlipcs.github.io/Dogfight/ | bárki megnyithatja; a gyökér átirányít a `web/` oldalra; a `main` ágra pusholás után ~1 perc alatt frissül |
| **Letöltött fájl** | https://davidlipcs.github.io/Dogfight/web/dogfight-offline.html | `Dogfight-F16.html`, ~14 MB, dupla kattintással indul, internet sem kell; a menüben „Letöltés egy fájlban” link is van |
| **claude.ai artifact** | https://claude.ai/artifact/KAfUJ7Wu7RVBsrRqSdVNGE | privát (csak a tulajdonos látja, a Share menüből osztható); itt nincs letöltés link |
| **Python** | `pip install -r requirements.txt` → `python main.py` | Python 3.9+, Panda3D, numpy |

Az iskolai hálózatokra figyelve a böngészős változat **nem tölt semmit külső szerverről** (a three.js a
repóban van). Csak a Google-betűtípusok jönnek kívülről; ha le vannak tiltva, a játék rendszerbetűkkel megy.
Ha egy hálózat a `github.io` címeket is tiltja, a letöltött egyfájlos változat működik.

---

## 3. Irányítás

### Egér és billentyűzet

| Gomb | Funkció |
|---|---|
| Egér | War Thunder-féle egeres célzás: a gép a fehér kör felé repül |
| S / W | orr fel / le kézzel – amíg nyomod, a segítő elengedi a gépet, a célzókör az orron marad |
| A / D, Q / E | orsózás, oldalkormány |
| Shift / Z vagy Ctrl | gáz fel / le: koppintás 5%, tartva 40%/s; 100%-nál (MIL) megáll, újabb Shift = utánégető; lefelé az első nyomás kikapcsolja |
| G | futómű |
| B (tartva) | földön kerékfék, levegőben légfék |
| C / jobb egérgomb (tartva) | körülnézés (kabinban a fejet fordítja) |
| V | kabin / külső nézet |
| Görgő / középső egérgomb | fegyverváltás / zoom (böngésző) |
| Bal egérgomb / Space | gépágyú / rakéta |
| 1 / 2 | AIM-9M / AIM-120A |
| X (tartva) | flare + chaff |
| T / F / Y / R | radar lock / hőkövető lock / következő radarcél / radar be-ki |
| M, H, P, Enter, Esc | jelölők, súgó, szünet, újraéledés, egér elengedése |

A Python változatban a zoom a **Z** (tartva), a gáz le a **Ctrl**.

### Kontroller (Xbox / PlayStation)

Bal kar = közvetlen irányítás (hátra = orr fel) · jobb kar = célzókör · RT / LT = gáz · RB = ágyú ·
A = rakéta · LB = flare · X / B = radar / hőkövető lock · Y = fegyverváltás · D-pad: futómű / fék / nézet /
zoom · L3 tartva = körülnézés · R3 = jelölők · Start = szünet · Back = súgó. A menüben A = felszállás,
X = indulás a levegőben. (Böngésző: Gamepad API; Python: Panda3D input devices.)

---

## 4. Játékmenet

* **Kezdés:** a Viper Base légibázis 36-os pályájának elején (vagy `Indulás a levegőben` / `--air-start`).
* **Hullámok:** az első ellenséges hullám 25 s-mal a felszállás után érkezik 32–40 km-ről; minden hullám
  eggyel több ellenséget hoz (legfeljebb 6). Hullám után 5 s szünet.
* **Játékmódok** (menü / `--mode`):
  * **Arkád** – minden kilőtt rakéta 10 s múlva visszakerül a sínre; a lőszer és a flare/chaff 2 s
    szünet után 10 s alatt feltölt.
  * **Realisztikus** – újratöltés csak leszálláskor.
* **Kiszolgálás:** mindkét módban, ha a bázis betonján 25 m/s alá lassulsz: azonnal újrafegyverzés,
  tankolás, javítás.
* **Nehézség:** könnyű / normál / nehéz (az AI pilóta tudását állítja, lásd 5.6).
* **Halál / baleset:** „LELŐTTEK!” / „LEZUHANTÁL!”, Enter (kontrolleren A) = újraéledés a kifutón.

---

## 5. A rendszerek részletesen

### 5.1 Repülésmodell (`sim/flight_model.py`, `web/js/flight.js`)

* ISA légkör 0–32 km; magasság- és Mach-függő tolóerő (F110-GE-129), késleltetett hajtómű-felpörgés,
  utánégető (~1,5 s), üzemanyag-fogyasztás.
* FLCS (fly-by-wire): a bot G-t kér (−3 … +9 G), G-felépülés 10 G/s, 25°-os AoA-limiter, ~270°/s orsózás.
* Transzonikus ellenállás M0,88-tól, indukált ellenállás, külső terhek ellenállása.
* Futómű és földi fizika: gördülés, kerékfék, orrkerék-kormányzás, farokütés, kemény / ferde / futómű
  nélküli földet érés = baleset, fékszárnyak a futóművel.
* Mért értékek (lásd README táblázat): M1,19 tengerszinten, M1,89 11 km-en, plafon ~16 km, 9 G-s forduló
  ~21°/s, felszállás utánégetővel ~450 m.
* Fix lépésköz: fizika 100 Hz, szenzorok 30 Hz, AI 10 Hz.

### 5.2 Egeres „instruktor” (`ai/steering.py`, `web/js/ai.js` – `steerTowards`)

A War Thunder egeres irányításához hasonló robotpilóta; a játékos és az AI ugyanazt használja.

* A **repülési pályát** viszi a cél felé, gravitáció-kompenzációval.
* Kért fordulási sebesség = 0,9 × szöghiba (max 1 rad/s), a pálya már meglévő fordulásával csillapítva.
* Kis korrekció (< ~40°): a bedöntés korlátozott (20°-tól nő), a maradékot oldalkormány végzi.
* Kicsit lejjebb lévő cél (< 40°): negatív G-s nyomás vízszintes szárnyakkal, nem fordul hátára.
  A húzás / nyomás döntésnek 20°-os hiszterézise van, így nem billeg oda-vissza.
* A játékosnál a segítő 0,85 × 9 G-nél (~7,6 G) megáll; az S-sel kihúzható a teljes 9 G.
* Kézi irányítás (W/S/A/D vagy bal kar): a segítő elenged, a nem nyomott tengely tartja a helyzetét,
  a célzókör az orron marad (elengedéskor nem rántja vissza a gépet).

### 5.3 Gázkar

Koppintás = 5%, tartva 0,3 s után 40%/s. Felfelé 100%-nál (MIL) megáll, az utánégetőhöz új nyomás kell;
lefelé az első nyomás az utánégetőből egyből 100%-ra vált. A HUD `THR` a gázkar, `MOT` a hajtómű valós
állása (a hajtómű pár másodperc alatt éri utol). A billentyűzet-állapotot minden egér- és billentyű-esemény
Shift / Ctrl jelzőjéből újraszinkronizálja (elveszett Shift-felengedés ellen, pl. Windows „Beragadó
billentyűk”). Böngészőben a Ctrl+W előtt a lap rákérdez a kilépésre.

### 5.4 Fegyverek és lockolás

| Fegyver | Adatok |
|---|---|
| M61A1 | 6000 lövés/perc, 511 lőszer, 1050 m/s, nyomjelzők, előretartás-jelző radar lockkal |
| AIM-9M | IR kereső 2,5° FOV, 40° kardán, IRCCM 0,65 (flare-szűrés), ~M2,5, 9 km keresőhatótáv (hőtől függ) |
| AIM-120A | datalink + inerciális középszakasz, 16 km-en PITBULL (aktív), lofting, ~M4, maddog indítás |
| ALE-47 | 30 flare + 30 chaff |

**Lock segítő (csak a játékosnál):**
* AIM-9M: a kereső 10°-os körben keres, és **magától lockol**, ha ellenség van benne. Az F azonnal lockol
  bármelyik ellenségre ±30°-on belül, vagy elengedi a lockot (utána 3 s-ig nem lockol magától).
* Radar: a **T** a nézési irányhoz legközelebbi ellenséget fogja be (±30°, 55 km-ig) ~0,25 s alatt;
  újra T = következő cél, ha nincs más, unlock. Radar lockkal a hőkövető is ráfordul.

**Lock kijelzés:** vastag négyzet a célon (a gép méretéhez igazodik), „LOCK” + fegyver, távolság, Vc;
pirosan villogó „LŐHETSZ! (Space)” hatótávon belül; „még messze” / „túl közel” / „messze van – válts
AIM-120-ra (2)”. Szaggatott vonal a várható találati pontig (⊗, a DLZ fly-out modellből számolt idővel),
pöttyözött vonal a cél várható pályájáról, a saját rakéták rombusz-jelölője becsapódásig hátralévő idővel.

**DLZ** (`launch_zone` / `launchZone`): 1D fly-out modell; Rmax ott ér véget, ahol a rakéta 450 m/s alá
lassul (onnan már nem tud fordulni). Példa 5 km-en szemből: AIM-120 ~37 km, AIM-9 ~21 km.

### 5.5 Szenzorok és figyelmeztetés

* **APG-68 radar:** SRCH (±60° pásztázás, B-scope), ACM, STT; pulzus-Doppler notch (25 m/s), chaff a notch
  közelében hat.
* **RWR:** keresés (zöld), lock (sárga), indítás (piros) – radaros fenyegetések.
* **Rakétaközelítés-jelző (MAWS, csak játékos):** minden rád kilőtt rakéta 15 km-en belül, a hőkövetők is:
  gyorsuló sípolás, „MISSILE!”, piros jel a rakétán távolsággal és becsapódási idővel, kép szélén nyíl,
  RWR-en `M`.
* Ellenség-jelölők 80 km-ig.

### 5.6 AI (`ai/pilot.py`, `web/js/ai.js`)

Az ellenség **pontosan ugyanolyan F-16** (gép, festés, fegyverzet), csak a pilóta kicsit gyengébb:

| Nehézség | max G | pontosság | rakéta-szünet | flare-esély | észlelés | DLZ-hányad, ahonnan lő |
|---|---|---|---|---|---|---|
| könnyű | 0,60 | 0,65 | 36 s | 0,30 | 0,20 | 0,5 (csak AIM-9) |
| normál | 0,80 | 0,85 | 24 s | 0,60 | 0,45 | 0,7 |
| nehéz | 0,92 | 0,95 | 15 s | 0,90 | 0,75 | 0,8 |

Viselkedés: járőrözés, célkövetés (rakéta, ágyú), védekezés (notch, flare/chaff, kitérés), terep- és
pályahatár-kerülés. A játékos a teljes DLZ-t kihasználhatja, így mindig messzebbről lőhet.

### 5.7 Kabin és nézetek

* Kabin-kád a törzsbe vágva, magas buborék-kabintető kerettel és tükrökkel, 30°-ban döntött ACES II ülés,
  oldalkonzolok, oldalsó bot és gázkar, műszerfal két világító MFD-vel, DED, ICP, tartalék műszerek,
  takaróernyő és HUD. Pilóta szándékosan nincs. A textúra: `dogfight/render/cockpit.png`
  (`tools/make_cockpit_texture.py` rajzolja).
* A kabinnézet a géphez rögzített (együtt orsózik, bólint), C / jobb gomb / L3 = fejfordítás; G alatt a
  fej lesüllyed; 7,5 G felett elsötétülés, −1,8 G alatt bevörösödés.
* A saját gép kabinnézetben külön, közeli (3 cm-es near plane) renderelési menetben rajzolódik
  (Three.js layer 1, Panda3D camera mask + display region), így a műszerfal nem vágódik le.
* Külső nézet: War Thunder-féle követő kamera, a horizontra visszabillenő célzással.

### 5.8 Grafika és hang

* F-16 kódból épített modell: Catmull-Rom törzs, LERX, NACA profilok, csuklós kormányfelületek, háromszínű
  szürke festés textúra-atlasszal, fények, páracsóva, szárnyvég-örvények, utánégető-láng.
* 102 × 102 km-es sziget LOD-terepen, légibázis (pálya, gurulóút, fedezékek, torony, fények), felhők,
  tenger, részecske-effektek (füst, robbanás, flare), nyomjelzők.
* Minden shader az első képkockán lefordul (nincs akadás az első utánégetőnél / rakétánál).
* Hangok kódból generálva (WebAudio / Panda3D): hajtómű, utánégető, ágyú, growl, lock-hang, RWR, MAWS,
  indítás, találat, robbanás.

---

## 6. A kód felépítése

### 6.1 Megfeleltetés a két változat között

| Python (`dogfight/`) | Böngésző (`web/js/`) | Tartalom |
|---|---|---|
| `sim/specs.py` | `specs.js` | F-16C, AIM-9M, AIM-120A, M61A1, APG-68, ALE-47 adatai |
| `sim/atmosphere.py`, `sim/flight_model.py` | `flight.js` | légkör, aerodinamika, FLCS, hajtómű, futómű |
| `sim/terrain.py`, `sim/airfield.py` | `terrain.js` | magasságmező, reptér |
| `sim/ir_seeker.py`, `radar.py`, `rwr.py`, `missile.py`, `guns.py`, `signatures.py`, `countermeasures.py` | `weapons.js` | szenzorok, rakéták, ágyú, DLZ, flare/chaff |
| `sim/aircraft.py`, `sim/world.py` | `sim.js` | repülőgép, világ, fix lépésköz, események |
| `ai/steering.py`, `ai/pilot.py`, `controls.py` | `ai.js` | instruktor, AI pilóta, játékos pilóta |
| `controls.py` | `game.js` (Input, Pad) | billentyű, egér, kontroller, gázkar |
| `camera.py` | `game.js` (FlightCamera) | követő és kabin kamera |
| `game.py` | `game.js` (Game) | játékmenet, módok, hullámok, kiszolgálás |
| `render/*` | `render.js` | modellek, terep, reptér, effektek, kabin-menet |
| `ui/hud.py`, `ui/scopes.py`, `ui/help.py` | `hud.js`, `index.html` | HUD, radar, RWR, G-hatások, súgó |
| `audio.py` | `audio.js` | hangok |

### 6.2 Eszközök (`tools/`)

| Parancs | Mit csinál |
|---|---|
| `python tools/export_web_assets.py` | a Python modellből / terepből előállítja a `web/assets/*` fájlokat (f16.json, festések, terep, kabin-textúra) |
| `python tools/make_cockpit_texture.py` | megrajzolja a kabin-textúrát (`dogfight/render/cockpit.png`, Pillow kell) |
| `python tools/build_offline.py` | elkészíti a `web/dogfight-offline.html` egyfájlos változatot (Node.js kell; az esbuild-et npx tölti le) |

Ha a modell vagy a terep változik: `make_cockpit_texture.py` (ha a kabin változott) →
`export_web_assets.py` → `build_offline.py`.

### 6.3 Tesztek

`python -m pytest` – 50 teszt: repülésmodell (végsebesség, plafon, G, orsózás, hajtómű), földi fizika
(felszállás, leszállás, balesetek), rakéták (sebesség, rávezetés, flare, notch, pitbull), szenzorok
(radar, IR, lock segítő, MAWS), instruktor (kis korrekció, nyomás, G-határ), gázkar (koppintás, MIL-ütköző,
utánégető), világ (hullámok, találatok).

### 6.4 Közzététel

* **GitHub Pages:** a repó beállítása „Deploy from branch: main / (root)” (Jekyll). A gyökér `index.html`
  átirányít a `web/`-re. Pusholás után a „pages build and deployment” workflow ~1 perc alatt frissít.
* **claude.ai artifact:** a `web/index.html` belső része (doctype / html / head / body nélkül, letöltés-link
  nélkül) a `web/js/*` és `web/assets/*` fájlokkal publikálva.
* **Offline fájl:** `tools/build_offline.py` után a `web/dogfight-offline.html` commitolva (a Pages-ről
  tölthető le).

---

## 7. Fejlesztési napló

| # | Kérés | Ami elkészült | Commit |
|---|---|---|---|
| 1 | War Thunder-szerű játék, először csak F-16, rakéták, lockolás | Python + Panda3D játék: F-16C, AIM-9M, AIM-120A, gépágyú, radar, RWR, AI, HUD | `cadf9c6` |
| 2 | Térkép kisebb-nagyobb hegyekkel | 102 km-es sziget, LOD-terep, gyorsítótár | `3de7ea1` |
| 3 | Realisztikus mozgás, gyorsulás, magasság | ISA légkör, hajtómű-késleltetés, G-felépülés, plafon, instruktor | `b7f5160` |
| 4 | Felszállópálya, több realizmus | Viper Base, felszállás / leszállás fizika, kiszolgálás | `724ecd3` |
| 5 | Sokkal részletesebb, szebb F-16 | kódból épített részletes modell, rakéták, festés | `0204790` |
| 6 | Még szebb F-16 | mozgó kormányfelületek, háromszínű festés, fények, páracsóva | `41e7aca` |
| 7 | Kipróbálás Chrome-ban, telepítés nélkül | teljes böngészős port (Three.js), claude.ai artifact | `318cb0e` |
| 8 | Kevésbé gyerekes modell, részletes kabin, pilóta nélkül | kabin-kád, ülés, műszerfal MFD-kkel, HUD; pilóta törölve; kabin-menet | `ede5940` |
| 9 | Fegyverváltás görgővel, S fel / W le | görgő = fegyverváltás, zoom a középső gombon, S/W csere | `714b24a` |
| 10 | Könnyebb lockolás | lock segítő: önálló IR-lock, T a nézési irányba | `ae256b2` |
| 11 | Elérés GitHubról, iskolában | GitHub Pages, three.js a repóban, gyökér-átirányítás | `b9f79c6` |
| 12 | Egyértelmű lock: négyzet, hova megy | lock-négyzet, LŐHETSZ, találati pont, rakéta-pályák | `8b140a4` |
| 13 | Letöltés | egyfájlos offline változat | `73ee2d0` |
| 14 | Beakad az utánégető | Shift-újraszinkron, Z = AB ki, shader-előfordítás | `4bfc908` |
| 15 | Kabin forogjon a géppel, realisztikusabb forduló, figyelmeztetés minden rakétára; Arkád / Realisztikus mód; precíz gázkar | rögzített kabin, G-hatások, MAWS, gázkar MIL-ütközővel, játékmódok | `021dca0` |
| 16 | Furcsa fordulás, forog W/S-nél – legyen War Thunder-szerű | új instruktor (arányos, nyom, hiszterézis), kézi irányítás átvétele | `b62b4a1` |
| 17 | Kontroller, flare és lőszer újratöltés | Gamepad (böngésző + Python), arkád lőszer / flare töltés | `2bc5829` |
| 18 | AI ugyanolyan gép, kicsit gyengébb; én is lőhessek messziről | azonos F-16, gyengébb AI, DLZ alapú AI-lövés, 80 km-es jelölők | `b8c41ae` |
| 19 | Dokumentáció | ez a dokumentum, README frissítés, új képek | – |

---

## 8. Ismert korlátok és tesztelési megjegyzések

* A böngészős változatot csak **fej nélküli Chrome-ban, szoftveres rendereléssel** teszteltük (1–18 FPS).
  Valódi videokártyán a sebességet nem mértük; gyenge iskolai gépen kisebb ablak segíthet.
* **Kontroller:** a böngészőben szimulált kontrollerrel teszteltük; a Python változat kontrolleres része
  valódi eszköz nélkül nem volt kipróbálható.
* Böngészőben a Ctrl lenyomva tartása közben a böngésző saját gyorsbillentyűi (pl. Ctrl+1 lapváltás)
  továbbra is működnek – a Z biztonságosabb gáz le gomb.
* A claude.ai artifact privát; másnak a Share menüből kell megosztani. Ott a letöltés link nem működik.
* Ha egy hálózat a `github.io`-t is tiltja, csak a letöltött egyfájlos változat működik.
* Az offline fájl pillanatkép: változtatás után újra kell építeni (`build_offline.py`) és újra letölteni.
* Az „aggressor” sivatagi festés még benne van a kódban, de jelenleg nem használja semmi.

## 9. Ötletek a folytatáshoz

* **Valódi 3D modell:** egy jó licencű F-16 `.glb` / `.blend` fájl beépítése (a mozgó kormányfelületek a
  meglévő csuklópont-rendszerre köthetők). Blenderrel (pl. Blender MCP a Claude asztali alkalmazásában)
  a modellezés vizuálisan ellenőrizhető lenne.
* Több repülőgép (pl. MiG-29, Su-27) saját adatokkal.
* Beállítások mentése (egér-érzékenység, mód, nehézség) a böngészőben.
* Többjátékos mód.
* Pontosabb rakéta-fly-out (2D, manőverező céllal) a DLZ-hez.
