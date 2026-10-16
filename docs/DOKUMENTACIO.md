# Dogfight – F-16C Viper és F/A-18E Super Hornet: teljes dokumentáció

Ez a dokumentum mindent leír, ami a projektben elkészült: hol és hogyan lehet játszani, mit tud a játék,
hogyan épülnek fel a gépek és a kód, hogyan kell karbantartani, és milyen lépésekben készült
(fejlesztési napló). A rövidebb, játékosoknak szóló leírás a [README](../README.md)-ben van.

**Tartalom:** 1. Áttekintés · 2. Hol lehet játszani · 3. Irányítás · 4. Főmenü és játékmenet ·
5. A két repülőgép · 6. A rendszerek részletesen · 7. A modellek (Blender) · 8. A kód felépítése ·
9. Karbantartás és közzététel · 10. Fejlesztési napló · 11. Ismert korlátok · 12. Ötletek

---

## 1. Áttekintés

War Thunder-szerű légiharc-játék két géppel: az **F-16C Block 50 Viperrel** és az **F/A-18E Super
Hornettel**. A repülés, a hajtóművek, a radar, a rakéták és a lockolás valós adatokra épülnek. Két változat van:

| Változat | Hol fut | Mit tud |
|---|---|---|
| **Böngészős** (`web/`, Three.js) | Chrome, telepítés nélkül; GitHub Pages-ről vagy egyetlen letöltött fájlból | **a teljes, aktuális játék**: két gép, Blender-modellek, élő kabinkijelzők, menü, fegyverzet-szerkesztő, harci zóna |
| **Python** (`dogfight/`, Panda3D) | saját gépen, `python main.py` | az „eredeti” változat, csak F-16-tal és a régi, kódból épített modellel; ebből készül a terep és a böngészős F-16 kabinmodellje |

A böngészős változat a Python-szimuláció JavaScriptre átírt és azóta továbbfejlesztett változata. A
későbbi fejlesztések (Super Hornet, kabinkijelzők, harci zóna, erősebb saját / gyengébb ellenséges rakéták,
orr-alapú célzás, egér-botkormány) **csak a böngészős változatban** vannak meg.

---

## 2. Hol és hogyan lehet játszani

| Mód | Link / parancs | Megjegyzés |
|---|---|---|
| **GitHub Pages** | https://davidlipcs.github.io/Dogfight/ | bárki megnyithatja; a gyökér átirányít a `web/` oldalra; a `main` ágra pusholás után ~1 perc alatt frissül |
| **Letöltött fájl** | https://davidlipcs.github.io/Dogfight/web/dogfight-offline.html | ~22 MB, dupla kattintással indul Chrome-ban, internet sem kell; a menüben „Letöltés egy fájlban” link is van |
| **Helyi szerver** | `web/` mappa kiszolgálása bármilyen statikus szerverrel, pl. `python -m http.server` a `web/` mappában | fejlesztéshez; `file://`-ból a moduláris változat nem fut, csak az offline fájl |
| **claude.ai artifact** | https://claude.ai/artifact/KAfUJ7Wu7RVBsrRqSdVNGE | régebbi, csak F-16-os állapot; privát (a Share menüből osztható) |
| **Python** | `pip install -r requirements.txt` → `python main.py` | Python 3.9+, Panda3D, numpy |

Az iskolai hálózatokra figyelve a böngészős változat **nem tölt semmit külső szerverről** (a three.js a
repóban van). Csak a Google-betűtípusok jönnek kívülről; ha le vannak tiltva, a játék rendszerbetűkkel megy.
Ha egy hálózat a `github.io` címeket is tiltja, a letöltött egyfájlos változat működik.

---

## 3. Irányítás

### Egér és billentyűzet (böngésző)

| Gomb | Funkció |
|---|---|
| **Egér – külső nézet** | egeres célzás: a gép **orra** áll a fehér körre (a zöld kör a valódi repülési irányt mutatja) |
| **Egér – kabinnézet** | az egér a **botkormány**: előre tolva orr le, magad felé húzva orr fel, oldalra orsózás. A bot **ott marad, ahová teszed**, semmi nem húzza vissza középre; középen 7%-os holtsáv, a bal oldali kis kijelzőn a pont zöld, ha semlegesben vagy |
| S / W | orr fel / le kézzel – amíg nyomod, a segítő elengedi a gépet, a célzókör az orron marad |
| A / D, Q / E | orsózás, oldalkormány |
| Shift / Z vagy Ctrl | gáz fel / le: koppintás 5%, tartva 40%/s; 100%-nál (MIL) megáll, újabb Shift = utánégető; lefelé az első nyomás kikapcsolja |
| G | futómű ki / be |
| B (tartva) | földön kerékfék, levegőben légfék |
| C / jobb egérgomb (tartva) | körülnézés (kabinban a fejet fordítja, ±160°) |
| V | kabin / külső nézet |
| **N** | kabinban: lenézés a **kijelzőkre** (ráközelít, olvasható); újra N = vissza. Külső nézetből egyből a kabinba és a kijelzőkre vált |
| **J / K / L** | a bal / jobb / középső kabinkijelző lapozása (RDR, SA, SMS, ENG, RWR) |
| **Tab** | F-16: EXTRÉM mód (tolóerő-vektorálás) be / ki – 9 G-s fordulók, teljes húzás 600 km/h alatt = Cobra |
| Görgő / középső egérgomb | fegyverváltás / zoom (3 fokozat) |
| Bal egérgomb / Space | gépágyú / rakéta |
| 1 / 2 | AIM-9M / AIM-120A |
| X (tartva) | flare + chaff |
| T / F / Y / R | radar lock / hőkövető lock / következő radarcél / radar be-ki |
| M | célpont-, zóna- és bázisjelölők ki / be |
| H vagy F1, P, Enter, Esc | súgó, szünet, újraéledés, menü (Folytatás / Főmenü / Súgó / Teljes képernyő) |

A Python változatban a zoom a **Z** (tartva), a gáz le a **Ctrl**; ott nincs N / J / K / L és egér-botkormány.

### Kontroller (Xbox / PlayStation)

Bal kar = közvetlen irányítás (hátra = orr fel) · jobb kar = célzókör · RT / LT = gáz · RB = ágyú ·
A = rakéta · LB = flare · X / B = radar / hőkövető lock · Y = fegyverváltás · D-pad: futómű / fék / nézet /
zoom · L3 tartva = körülnézés · R3 = jelölők · Start = szünet · Back = súgó. A menüben A = Folytatás vagy
felszállás, X = indulás a levegőben, B = új meccs a kifutóról. (Böngésző: Gamepad API; Python: Panda3D.)

---

## 4. Főmenü és játékmenet

### Főmenü (böngésző)

| Beállítás | Lehetőségek |
|---|---|
| **Saját gép** | F-16C Viper · F/A-18E Super Hornet (a cím is vált: „Dogfight Viper” / „Dogfight Rhino”) |
| **Fegyverzet** | AIM-9M és AIM-120A darabszám (− / +), „Alap” gomb; alatta a függesztési pontok sora mutatja, melyik állomásra mi kerül, mellette a rakéták száma és tömege |
| **Ellenfél** | F-16C · F/A-18E · Vegyes (hullámonként véletlenszerűen keverve) |
| **Játékmód** | Arkád · Realisztikus |
| **Nehézség** | Könnyű · Normál · Nehéz |
| **Ellenség** | 1–4 ellenség az első hullámban |
| **Egér** | érzékenység, fordított Y |
| Gombok | Folytatás (ha fut meccs) · Felszállás a kifutóról · Indulás a levegőben · **Oktatás** |

**Fegyverzet-kiosztás** (`buildLoadout` a `specs.js`-ben): minden fegyver először azokat az állomásokat
foglalja el, amelyeket csak ő használhat, utána a közöseket a saját sorrendjében – úgy, ahogy az igazi gépen:

| Gép | Állomások | AIM-9M | AIM-120A | Alap |
|---|---|---|---|---|
| F-16C | 1, 2, 3, 7, 8, 9 | mindegyikre (sorrend: 1, 9, 2, 8, 3, 7) | mindegyikre (3, 7, 1, 9, 2, 8) | 4× AIM-9M + 2× AIM-120A |
| F/A-18E | 1–5, 7–11 (6 = középső, üres) | 1, 11 (szárnyvég, csak AIM-9) + 2–4, 8–10 | 5, 7 (törzs, csak AIM-120) + 2–4, 8–10 | 4× AIM-9M + 6× AIM-120A |

Egy fegyverből legfeljebb annyi lehet, ahány állomás viszi, és a kettő együtt nem lehet több az állomások
számánál (F-16: 6, Hornet: 10). Az ellenséges Hornetek 2× AIM-9M + 4× AIM-120A, az ellenséges F-16-osok az
alap fegyverzettel repülnek.

A főmenü meccs közben is elérhető (Esc → Főmenü): onnan a **Folytatás** visszavisz, vagy új meccs indul
ugyanazon a jeleneten (a terep és a modellek nem töltődnek újra).

### Oktatás (`web/js/tutorial.js`)

Nem kötelező, vezetett repülés a menüben kiválasztott géppel, levegőben indulva, hullámok nélkül, arkád
módban. A jobb oldali kártya minden leckénél elmondja, **mit** csinál a funkció, **hogyan** kell használni és
**mikor** érdemes, alatta a feladat és élő állapot (pl. „Drón: 12,4 km · radar lock OK”). A feladatot a játék
ellenőrzi; sikerre 2,5 s múlva jön a következő lecke. Enter = olvasó leckénél tovább, feladatnál kihagyás;
Esc = menü. Közben a HUD jobb oszlopa a bal alá kerül, hogy a kártya ne takarja.

| # | Lecke | Feladat (amit a játék figyel) |
|---|---|---|
| 1 | Üdvözlés, a képernyő részei | Enter |
| 2 | Repülés az egérrel, kézi irányítás | 90° fordulás |
| 3 | Gáz, utánégető, fogyasztás | AB be, majd vissza 100%-ra |
| 4 | Forduló, G, energia, sarok-sebesség | 6 G |
| 5 | Kabin, egér-botkormány, kijelzők (N, J/K/L) | V → N → N |
| 6 | Radar lock és AIM-120 (céldrón 22 km-ről, szemből) | a drón lelövése |
| 7 | AIM-9 hőkövető (drón 3 km-re előtted) | a drón lelövése |
| 8 | Gépágyú, előretartás-jelző (drón 900 m-re) | a drón lelövése |
| 9 | Védekezés: RWR, MISSILE, notch, chaff / flare, éles forduló | egy hátulról-oldalról indított AIM-120 túlélése (ha eltalált volna, újra jön) |
| 10 | F-16: extrém mód és Cobra · Hornet: nagy állásszög | Tab + 50° fölötti AoA · Hornet: 30° fölötti AoA |
| 11 | Harci zóna, hullámok, leszállás, kiszolgálás | Enter → főmenü |

A drónok (`DronePilot`) egyenesen vagy enyhén kanyarogva repülnek, radar nélkül, fegyvertelenül; ha
elrepülnek vagy nem a te lövésedtől esnek le, új drón jön. A játékos gépe az oktatásban sebezhetetlen
(`invulnerable`: a találat csak jelzés), a földbe csapódás után a lecke elölről indul.

### Harci zóna és biztonsági kör

![Helyzetkép a Hornet középső kijelzőjén](fa18_cockpit_displays.jpg)

* A légibázis a térkép **délkeleti** részén van (x = 19 km, y = −26 km). A **harci zóna** a túloldalon:
  középpontja (−14 km, +16 km), sugara **16 km** – kb. 53 km-re a bázistól.
* A bázis körüli **14 km-es biztonsági körben** az ellenség senkit nem támad.
* Az AI csak azokra a célokra megy rá, amelyek a zóna középpontjától **28 km-en belül** vannak (zóna + 12 km),
  és nincsenek a biztonsági körben. A zónában járőrözik, és ha 32 km-nél messzebbre sodródik, visszafordul.
  A biztonsági kör széle ~39 km-re van a zóna középpontjától, így felszállás és leszállás közben nem lőnek rád.
* **Levegőben indulva** a bázis és a zóna között indulsz (a táv 45%-ánál, 4500 m-en, a zóna felé), kb.
  13 km-re a zóna szélétől. A kifutóról indulva ~37 km az út a zóna széléig.
* Jelölések: a HUD-on borostyán rombusz „HARCI ZÓNA xx km” (ha mögötted van, nyíl a kép szélén), ciánkék
  négyzet „BÁZIS xx km”; bal fent „HARCI ZÓNA” vagy „BIZTONSÁGI ZÓNA (bázis)” felirat, ha benne vagy. A
  kabin SA-térképén piros szaggatott kör a zóna, ciánkék a biztonsági kör; a DED / UFCD sorában irány és távolság.

### Hullámok, módok, kiszolgálás

* **Hullámok:** az első 25 s-mal azután jön, hogy a gép 150 m fölé emelkedett; mindig a zónában, annak a
  tőled távolabbi oldalán jelenik meg, feléd fordulva, 3000–7500 m-en. Minden hullám eggyel több ellenséget
  hoz (legfeljebb 6). Hullám után 5 s szünet.
* **Arkád** – minden kilőtt rakéta 10 s múlva visszakerül a sínre; a lőszer és a flare / chaff 2 s szünet
  után 10 s alatt feltölt. **Realisztikus** – újratöltés csak leszálláskor.
* **Kiszolgálás:** mindkét módban, ha a bázis betonján 25 m/s alá lassulsz: azonnal újrafegyverzés (a
  menüben beállított fegyverzettel), tankolás, javítás.
* **Halál / baleset:** „LELŐTTEK!” / „LEZUHANTÁL!”, Enter (kontrolleren A) = újraéledés ugyanazzal a géppel.

---

## 5. A két repülőgép

Mindkét gép ugyanazzal a repülésmodellel repül (`web/js/flight.js`); a különbség csak az adatokban van
(`web/js/specs.js`: `F16C`, `FA18E`). Az alábbi értékeket a játék saját modelljével mértük
(50% üzemanyag, alap fegyverzet):

| | F-16C Block 50 | F/A-18E Super Hornet |
|---|---|---|
| Hajtómű | 1× F110-GE-129: 76,3 / 131,6 kN | 2× F414-GE-400: 2× 57,8 / 2× 97,9 kN |
| Fogyasztás MIL / utánégető | 1,64 / 7,25 kg/s | 2,75 / 10,3 kg/s (két hajtómű) |
| Üres tömeg / belső üzemanyag | 8 900 / 3 200 kg | 14 552 / 6 530 kg |
| Szárnyfelület / fesztáv / hossz | 27,9 m² / 9,96 m / 15,06 m | 46,5 m² / 13,62 m / 18,31 m |
| cL,α / cL,max / cD0 / k | 4,1 / 1,8 / 0,0205 / 0,118 | 4,4 / 2,0 / 0,0235 (+0,0035 pilonok) / 0,105 |
| Max G / min G / AoA-limit / orsózás | 9 / −3 / 25° / 270°/s | 7,5 / −3 / 40° / 220°/s |
| Tolóerő/tömeg | 1,20 | 1,05 |
| Végsebesség tengerszinten / 11 km-en | M1,18 / M1,88 | M1,0 / ~M1,4 |
| Emelkedés tengerszinten | ~320 m/s | ~230 m/s |
| Tartós forduló 3 km, M0,6 | 5,3 G, 14,9°/s | 5,0 G, 14,1°/s |
| Pillanatnyi forduló 3 km, 600 km/h | 5,8 G, 19,2°/s | 6,3 G, 20,9°/s |
| Átesési sebesség tengerszinten | ~215 km/h | ~206 km/h |
| Utánégetővel bírja | ~7,4 perc | ~10,6 perc |
| Felszállás utánégetővel (álló helyzetből) | ~14 s | ~16 s |
| Gépágyú | M61A1, 511 lövés | M61A2 (orrban), 412 lövés |
| Radar | AN/APG-68(V)9: 74 km keresés, 55 km lock, 0,5 s | AN/APG-79 AESA: 90 km, 70 km, 0,35 s, gyorsabb pásztázás |
| Futómagasság / farokütés / elforgatás | 2,05 m / 13° / 60 m/s IAS-tól | 1,95 m / 12° / 64 m/s-tól |
| Találati pont, RCS szemből / oldalról | 100, 1,5 / 6 m² | 115, 1,0 / 8 m² |

**A különbség a játékban:** a Hornet nagyobb szárnnyal és a LEX-szel lassan jobban fordul és messzebbre
fordítja az orrát (40°-os állásszög), de nehezebb és nagyobb az ellenállása (a döntött pilonok is), ezért
lassabban gyorsul, és nagy állásszögnél gyorsan elveszti az energiáját – mint az igazi. A Viper több
tolóerővel és 9 G-vel az energiaharcban erősebb.

**Ellenséges változatok** (`BANDITS`): ugyanazok a gépek gyengébb sárkánnyal – F-16C: 7 G, 190°/s, 20° AoA;
F/A-18E: 6,3 G, 150°/s, 28° AoA.

**F-16 EXTRÉM mód** (`F16C.tvc`, Tab): tolóerő-vektorálás, mint a kísérleti F-16 MATV / VISTA-n. Bekapcsolva:

| | Normál | Extrém |
|---|---|---|
| Fúvócső-kitérés | – | ±20° a pitch bottal (a tolóerő egy része a gép „felfelé” tolja) |
| Tolóerő / indukált ellenállás | 100% / 100% | 120% / 75% |
| cL,max | 1,8 | 2,4 |
| AoA-limit | 25° | 32° (instruktor), 80° teljes kézi húzásnál 600 km/h alatt (Cobra) |
| Max pitch-sebesség / orsózás | 0,9 rad/s / 270°/s | 2,4 rad/s / 330°/s, kis sebességen is |
| Egeres instruktor G-határa | a max G 85%-a | a teljes 9 G |
| 9 G-ben tartva (3 km, 860 km/h-ról) | 2,6 s | 4,1 s |

**Cobra és rakéták** (`Missile.checkCobra`): ha a rakéta célpontja 40° fölötti állásszögben van, miközben a
rakéta 4 másodpercen belül érne oda, a rakéta egyszer „dönt”: a játékos ellen 90%, az AI ellen 60% eséllyel
elveszíti a célt és elrepül mellette (MISSED). Mérve (bandita AIM-120 / AIM-9 hátulról, 5 km): jó időzítéssel
8-ból 7 elvétette, túl korán (9 s) vagy semmit sem csinálva mind talált. A HUD bal oszlopában „TVC EXTRÉM”
(Cobra közben „COBRA”) jelzi a módot.

**Rakéták mindkét gépen:** AIM-9M és AIM-120A. Ellenállásuk a gépre 0,031 m² rakétánként (indítósínnel),
ezért nagyobb szárnyú gépen kisebb együtthatót ad (a valóságnak megfelelően).

---

## 6. A rendszerek részletesen

### 6.1 Repülésmodell (`web/js/flight.js`, Pythonban `sim/flight_model.py`)

* ISA légkör 0–32 km; magasság- és Mach-függő tolóerő, késleltetett hajtómű-felpörgés (alapjárat → MIL ~4 s),
  utánégető (~1,5 s), üzemanyag-fogyasztás a tolóerővel arányosan (TSFC a gép adataiból).
* Felhajtóerő: cL,α × Mach-tényező, cL,max-nál telítődik, átesés után fokozatosan csökken.
  Ellenállás: cD0 + pilonok + transzonikus hullám-ellenállás (gépenként külön görbe) + k·cL² + rakéták +
  0,8·sin²α (nagy állásszög) + légfék + futómű + fékszárny.
* Fly-by-wire: a bot G-t kér (gMin … gMax), G-felépülés 10 G/s, AoA-limiter (gépenként), orsózás a
  gép adatai szerint, nagy állásszögnél és kis sebességnél csökkenő kormányhatással.
* Futómű és földi fizika: gördülés (beton / fű), kerékfék, orrkerék-kormányzás, elforgatás csak elég
  légsebességnél, farokütés, kemény / ferde / futómű nélküli földet érés = baleset, fékszárnyak a futóművel.
  A futómagasság, a farokütési szög és az elforgatási sebesség gépenként más.
* Kijelzéshez számolt értékek: tolóerő, ellenállás, fogyasztás (a kabin ENG oldala ezeket mutatja).
* Fix lépésköz: fizika 100 Hz, szenzorok 30 Hz, AI 10 Hz.

### 6.2 Egeres „instruktor” (`web/js/ai.js` – `steerTowards`)

A War Thunder egeres irányításához hasonló robotpilóta; a játékos és az AI ugyanazt használja.

* Az AI a **repülési pályát** viszi a cél felé; a játékos gépénél az **orrot** állítja a kurzorra.
  Gravitáció-kompenzációval.
* Kért fordulási sebesség = 0,9 × szöghiba (max 1 rad/s), a pálya meglévő fordulásával csillapítva.
* Kis korrekció: a bedöntés korlátozott, a maradékot oldalkormány végzi. Kicsit lejjebb lévő cél:
  negatív G-s nyomás, nem fordul hátára; a húzás / nyomás döntésnek hiszterézise van.
* A játékosnál a segítő a gép max G-jének 85%-ánál megáll; az S-sel kihúzható a teljes G.
* Kézi irányítás (W/S/A/D, bal kar vagy kabinban az egér-botkormány): a segítő elenged, a nem nyomott
  tengely tartja a helyzetét.

### 6.3 Gázkar

Koppintás = 5%, tartva 0,3 s után 40%/s. Felfelé 100%-nál (MIL) megáll, az utánégetőhöz új nyomás kell;
lefelé az első nyomás az utánégetőből egyből 100%-ra vált. A HUD `THR` a gázkar, `MOT` a hajtómű valós
állása. A Shift / Ctrl állapotot minden esemény újraszinkronizálja (elveszett felengedés ellen).
Böngészőben a Ctrl+W előtt a lap rákérdez a kilépésre.

### 6.4 Fegyverek és lockolás

| Fegyver | Adatok |
|---|---|
| M61A1 / M61A2 | 6000 lövés/perc, 511 / 412 lőszer, 1050 m/s, nyomjelzők, előretartás-jelző radar lockkal |
| AIM-9M | IR kereső, IRCCM (flare-szűrés), ~M2,5 |
| AIM-120A | datalink + inerciális középszakasz, PITBULL (aktív), lofting, ~M4, maddog indítás |
| ALE-47 | 30 flare + 30 chaff |

**Saját és ellenséges rakéták (böngésző):** a játékos rakétái (`PLAYER_MISSILES`) sokkal erősebbek
(55 G, tolóerő-vektorálás, 0,1 s sínidő, széles kereső, szinte nem téveszthető meg, nagy gyújtó- és
hatósugár), az ellenségéi (`BANDIT_MISSILES`) gyengébbek (kis G, lassú követés, könnyen becsapható,
korán notcholható). Mérés kitérő, flare-t / chaffot szóró célra: saját AIM-9 közelről ~90–100%, AIM-120
~90%; az ellenség rakétái a kitérő gépet nem találták el.

**Lock segítő (csak a játékosnál):** AIM-9M: a kereső 10°-os körben keres és magától lockol; az F
azonnal lockol ±30°-on belül vagy elenged. Radar: a **T** a nézési irányhoz legközelebbi ellenséget fogja
be (±30°, a radar lock-hatótávján belül: F-16 55 km, Hornet 70 km); újra T = következő cél vagy unlock.

**Lock kijelzés:** négyzet a célon, „LOCK” + fegyver, távolság, Vc; „LŐHETSZ! (Space)” hatótávon belül;
szaggatott vonal a várható találati pontig; saját rakéták rombusz-jelölővel és becsapódási idővel.
**DLZ:** 1D fly-out modell, Rmax ott, ahol a rakéta 450 m/s alá lassul.

### 6.5 Szenzorok és figyelmeztetés

* **Radar:** SRCH (±60° pásztázás), ACM, STT; pulzus-Doppler notch, chaff a notch közelében hat.
  APG-68: 120°/s pásztázás, 25 m/s notch; APG-79: 260°/s, 20 m/s notch, gyorsabb lock.
* **RWR:** keresés (zöld), lock (sárga), indítás (piros); a jel a fenyegető gép típusa (`16` / `18`).
* **Rakétaközelítés-jelző (MAWS):** minden rád kilőtt rakéta 15 km-en belül, a hőkövetők is: sípolás,
  „MISSILE!”, piros jel a rakétán távolsággal és becsapódási idővel, kép szélén nyíl.
* **HUD-figyelmeztetések:** PULL UP, MISSILE!, RADAR LOCK, SPEED LOW (< 252 km/h), FUTÓMŰ!, GEAR SPEED
  (> 558 km/h kiengedett futóval), BINGO FUEL (a belső üzemanyag 12%-a alatt); G és AoA sárga a gép
  határának 85% / 80%-a felett.
* Ellenség-jelölők 80 km-ig, zóna- és bázisjelölő (lásd 4.).

### 6.6 AI (`web/js/ai.js`, Pythonban `ai/pilot.py`)

| Nehézség | max G | pontosság | rakéta-szünet | flare-esély | észlelés | DLZ-hányad, ahonnan lő |
|---|---|---|---|---|---|---|
| könnyű | 0,60 | 0,65 | 36 s | 0,30 | 0,20 | 0,5 (csak AIM-9) |
| normál | 0,80 | 0,85 | 24 s | 0,60 | 0,45 | 0,7 |
| nehéz | 0,92 | 0,95 | 15 s | 0,90 | 0,75 | 0,8 |

Viselkedés: járőrözés a harci zónában, célkövetés (rakéta, ágyú), védekezés (notch, flare / chaff,
kitérés), terep- és pályahatár-kerülés; csak „tisztességes” célra támad (zónában, nem a biztonsági körben).

**Legnagyobb lőtávolság** (a DLZ-hányadon felül), hogy senki ne kapjon rakétát „a semmiből”, amíg ő maga még
nem tud lockolni: könnyű – AIM-9 3,5 km, AIM-120 nincs; normál – 4,5 / 8 km; nehéz – 5,5 / 10 km. A játékos a
radarral 55 km-ről (F-16) / 70 km-ről (Hornet) lockolhat; ha egy ellenség lock-távolságon belül van és nincs
lock, a legközelebbi jelölője alatt „T = lock” felirat jelenik meg.

### 6.7 Kabin, kijelzők, nézetek

![F-16 kabin, a kijelzőkre nézve (N)](f16_cockpit_displays.jpg)

**Kabinok.** F-16: a régi, kódból épített kabinmodell (`web/assets/f16.json`): ACES II ülés, oldalsó bot,
két MFD, DED, ICP, RWR-szkóp, tartalék műszerek, HUD. F/A-18E: a Blender-modell része: NACES ülés,
keretes szélvédő, majdnem átlátszó HUD-üveg, két DDI, UFCD, AMPCD, középső bot, gázkarok, figyelmeztető lámpák.

**Élő kijelzők (`web/js/mfd.js`, `CockpitDisplays`).** Minden képernyő egy canvas-textúra; kabinnézetben
képkockánként a kijelzők fele rajzolódik újra (mindegyik ~30-szor másodpercenként), külső nézetben semmi.

| Oldal | Tartalom |
|---|---|
| **RDR** | B-scope: célok magassággal és irányvektorral, pásztázó nyaláb, ACM-doboz; lockolt cél: távolság, Vc, magasság, Mach, aspektus, **NCTR** (típus), notch / memória; jobb oldalt DLZ-csík (Rmax, no-escape, Rmin, SHOOT / NOESC) |
| **SA** | orr-felfelé térkép 20 / 40 / 80 km-es tartománnyal: ellenségek (radarcél tömött, datalink üres), saját és rád tartó rakéták, RWR-irányok a peremen, harci zóna, bázis és biztonsági kör, irány és távolság mindkettőhöz |
| **SMS** | gép-felülnézet az állomásokkal (töltött / üres, kiválasztott fehér, arkád újratöltés), darabszámok, lőszer, flare / chaff, a kiválasztott rakéta állapota |
| **ENG** | hajtóművenként fordulatszám-oszlop, fúvócső, EGT, fogyasztás, tolóerő, utánégető; tolóerő/tömeg, **Ps** (fajlagos többletteljesítmény), ellenállás, Mach, IAS, AoA / limit, G (min / max a felszállás óta), tömeg; üzemanyag-csík, hátralévő idő, **BINGO** (ennyi kell a hazaúthoz) |
| **RWR** | fenyegetések a szkópon, rád tartó rakéták listája távolsággal és idővel, flare / chaff |
| **DED / UFCD** | adatsor: zóna és bázis iránya / távolsága, üzemanyag és BINGO, fegyverek, hullám; a Hornet UFCD-jén magasság, Mach, G, hátralévő idő, fogyasztás, flare / chaff is |

| Gép | Bal (J) | Jobb (K) | Középső (L) | Fix |
|---|---|---|---|---|
| F-16C | MFD: RDR / SMS / ENG | MFD: SA / ENG / SMS | – | DED, RWR-szkóp |
| F/A-18E | DDI: ENG / SMS / RWR | DDI: RDR / SMS | AMPCD: SA / RWR | UFCD |

Az F-16 képernyői a régi modell négy képernyő-négyszögére kerülnek (0–1 UV-val szétválasztva), a Hornetéi a
`screen_*` objektumokra – ezekre a JS vetíti a UV-t (`Models.modelScreens`).

**Nézetek.**
* **N – kijelzők nézése:** a fej a műszerfal közepére fordul, a látószög 30° (F-16) / 40° (Hornet); a
  HUD-réteg ilyenkor csak a figyelmeztetéseket és üzeneteket rajzolja. C-vel körülnézve kilép belőle.
* Kabinnézetben a kép 13%-kal lejjebb van tolva (lencseeltolás, `setViewOffset`): a HUD a középpont fölé
  kerül, alul beférnek a kijelzők; a fegyver-sorok a kép tetejére, a botkormány-kijelző balra kerül; a HUD
  dőlésskálája csak ±16°-on belül látszik (mint az igazi HUD).
* **Egér-botkormány:** a bot ott marad, ahová teszed (nincs visszarugózás), 7%-os holtsáv; pointer lock
  nélkül a kurzor középtől mért eltérése a bot.
* A kabinnézet a géphez rögzített; a fej a nyak körül fordul (±160°), hátranézéskor előre-oldalra dől;
  G alatt a fej lesüllyed; 8,2 G felett lassan elszürkül a kép (egy tartott 9 G-s fordulónál ~6 s után), −1,8 G alatt bevörösödés.
* A saját gép kabinnézetben külön, közeli (3 cm-es near plane) renderelési menetben rajzolódik (layer 1).
* Külső nézet: War Thunder-féle követő kamera.

### 6.8 Grafika és hang

* **Külső nézet:** a Blenderben épített F-16 és Super Hornet (`.glb`), saját olvasóval (`web/js/glb.js`).
  Gépenként: mozgó kormányfelületek, behúzódó futómű ajtókkal, helyzetjelző fények, stroboszkóp (F-16:
  1 a vezérsíkon, Hornet: 2), utánégető-láng (Hornet: két kisebb), páracsóva a LEX / szárnytő-kiterjesztésből
  nagy állásszögnél, szárnyvég-örvények 5,5 G felett, torkolattűz a gépágyú helyén.
* **Hornet kormányfelületei:** csűrő orsózásra, fékszárny állásszög szerint (és kis sebességnél
  differenciálisan), orrsegédszárny 34°-ig, két oldalkormány; légféknél a kormányok kifelé, a csűrők fel,
  a LEX-spoilerek ki; a kifutón a kormányok befelé állnak (toe-in).
* A reptéren 2 F-16 és 2 Super Hornet parkol.
* 102 × 102 km-es sziget LOD-terepen, légibázis, felhők, tenger, füst, robbanás, flare, nyomjelzők.
* Minden shader az első képkockán lefordul (nincs akadás).
* Hangok kódból generálva (WebAudio): hajtómű, utánégető, ágyú, growl, lock-hang, RWR, MAWS, robbanás.

---

## 7. A modellek (Blender)

![F/A-18E elölről (Blender-render)](../models/fa18/previews/fa18_front.png)

Mindkét gép **Blender-szkriptből** épül, kézi modellezés nélkül; a szkriptek bármikor újrafuttathatók.

| Fájl | Tartalom |
|---|---|
| `tools/blender/aircraft_lib.py` | közös eszközök: mesh-darabok (`Part`), geometria (cső, doboz, szárnyprofil-felület, kerék, futóakna, futóajtó), anyagok (festés textúrával, matt / fém színnel, üveg, HUD-üveg, kijelző, lámpák), objektum-építés UV-val és csuklóval, renderképek, GLB-export |
| `build_f16.py`, `f16_shape.py`, `f16_paint.py` | F-16C: alak-táblázatok, építés, festés (USAF háromszínű szürke, panelvonalak) |
| `build_fa18.py`, `fa18_shape.py`, `fa18_paint.py` | F/A-18E: keresztmetszetek (törzs + gondolák + LEX + szárny sima összeolvasztással), szívócsatornák, kettős döntött vezérsík, kabin, futómű, festés (US Navy kétszínű szürke, NAVY / NG / 200 jelzések, sárga-fekete farokcsík) |

**Kimenet:** `models/<gép>/<gép>.glb` (teljes felbontású textúrák), `web/assets/<gép>.glb` (kisebb
textúrák, ezt tölti a játék), `models/<gép>/<gép>.blend`, a festés textúrái `models/<gép>/textures/`
(nincs a repóban, újragenerálható), renderképek `models/<gép>/previews/`. Az F-16 építése a rakéták
`.glb`-jét is kiírja (`aim9m.glb`, `aim120c.glb`).

**Konvenciók** (a játék ezekre épít):
* Tengelyek: +Y előre, +X jobbra, +Z fel, méter (a glTF-export +Y fel / −Z előre; a játék visszaforgatja).
* Mozgó részek origója a csuklón, a helyi X tengely a csuklóvonal; pozitív forgatás = kilépőél le /
  belépőél le / oldalkormány kilépőéle jobbra / légfék nyit. Nevek: `lef_*`, `flap_*`, `ail_*`, `stab_*`,
  `rudder` vagy `rudder_L` / `rudder_R`, `sb_up_*`, `sb_lo_*`.
* Futószárak és ajtók glTF-extrában: `retract` / `door` = ennyi fokkal kell a helyi X körül forgatni a
  behúzáshoz.
* Üres csomópontok: `store_N` (N. függesztési pont), `ref_nozzle*`, `ref_wingtip_L/R`, `ref_nav_L/R`,
  `ref_tail`, `ref_strobe*`, `ref_vapor_L/R`, `ref_gun`, `ref_eye`, `ref_gear_main_L/R`, `ref_gear_nose`,
  `ref_intake_light_L/R` (F-16).
* `screen_*` objektumok (Hornet): a kabin kijelzői, a játék ezekre rajzol.

**Futtatás Blenderben** (Scripting fül, vagy a blender-mcp kiegészítő 9876-os portján keresztül):

```python
path = r"...\tools\blender\build_fa18.py"
exec(compile(open(path, encoding="utf-8").read(), path, "exec"),
     {"__file__": path, "OPTS": dict(textures=False, export=True, save=True)})
```

`OPTS`: `build` (modell építése), `textures` (textúrák újrafestése), `export` (GLB-k kiírása), `save`
(`.blend` mentése), `previews` (mappa a renderképeknek), `views` (melyik nézetek). Egy jelenetben egyszerre
egy gép van: az építés törli a korábbi `F16` / `FA18` gyűjteményt.

---

## 8. A kód felépítése

### 8.1 Böngészős változat (`web/`)

| Fájl | Tartalom |
|---|---|
| `index.html` | menü (gép, fegyverzet, ellenfél, mód, nehézség, egér), szünet, súgó, betöltő |
| `js/specs.js` | `F16C`, `FA18E`, `BANDITS`, rakéták (`PLAYER_MISSILES`, `BANDIT_MISSILES`), gépágyúk, radarok, `buildLoadout`, `loadoutLimits` |
| `js/flight.js` | légkör, aerodinamika, fly-by-wire, hajtómű, futómű |
| `js/terrain.js` | magasságmező, reptér |
| `js/weapons.js` | IR kereső, radar, RWR, rakéták, gépágyú, DLZ, flare / chaff |
| `js/sim.js` | `Aircraft` (fegyverzet, kiszolgálás, szenzorok), `World` (fix lépésköz, események) |
| `js/ai.js` | instruktor, játékos pilóta, AI pilóta harci zónával |
| `js/render.js` | modellek (`Models.typeInfo`: gépenkénti pontok és effektek), kormányfelületek, terep, reptér, effektek, kabin-menet |
| `js/glb.js` | `.glb`-olvasó |
| `js/mfd.js` | élő kabinkijelzők |
| `js/hud.js` | HUD, radar, RWR, G-hatások, zóna- és bázisjelölők |
| `js/audio.js` | hangok |
| `js/game.js` | kamera, bemenet (egér-botkormány), játékmenet (zóna, hullámok, kiszolgálás), betöltés, menü |
| `js/tutorial.js` | az oktatás leckéi, céldrónok, rakéta-gyakorlat |

### 8.2 Megfeleltetés a Python változattal

| Python (`dogfight/`) | Böngésző (`web/js/`) |
|---|---|
| `sim/specs.py` | `specs.js` |
| `sim/atmosphere.py`, `sim/flight_model.py` | `flight.js` |
| `sim/terrain.py`, `sim/airfield.py` | `terrain.js` |
| `sim/ir_seeker.py`, `radar.py`, `rwr.py`, `missile.py`, `guns.py`, `signatures.py`, `countermeasures.py` | `weapons.js` |
| `sim/aircraft.py`, `sim/world.py` | `sim.js` |
| `ai/steering.py`, `ai/pilot.py`, `controls.py` | `ai.js`, `game.js` (Input, Pad) |
| `camera.py`, `game.py` | `game.js` |
| `render/*` | `render.js` (+ `glb.js`, `mfd.js`) |
| `ui/*` | `hud.js`, `index.html` |
| `audio.py` | `audio.js` |

### 8.3 Eszközök (`tools/`)

| Parancs | Mit csinál |
|---|---|
| `python tools/export_web_assets.py` | a Python modellből / terepből előállítja a `web/assets/*` fájlokat (f16.json, festések, terep, kabin-textúra) |
| `python tools/make_cockpit_texture.py` | megrajzolja az F-16 kabin-textúráját (Pillow kell) |
| `python tools/build_offline.py` | elkészíti a `web/dogfight-offline.html` egyfájlos változatot (Node.js nélkül a beépített csomagoló dolgozik; minden `web/assets` fájl data: URI-ként kerül bele) |
| `tools/blender/build_f16.py`, `build_fa18.py` | **Blenderben** futtatandó modell-építők (lásd 7.) |

### 8.4 Tesztek

`python -m pytest` – 50 teszt a **Python** változathoz: repülésmodell, földi fizika, rakéták, szenzorok,
instruktor, gázkar, világ. A böngészős változat új részeit (Hornet, kijelzők, zóna) Chrome-ban, a
játék saját függvényeivel mértük és próbáltuk ki (lásd 11.); automata JS-teszt nincs.

---

## 9. Karbantartás és közzététel

* **Új gépadat / hangolás:** `web/js/specs.js` → `python tools/build_offline.py`.
* **Blender-modell változott:** a gép építője Blenderben (`export=True`) → `build_offline.py`.
* **Python modell / terep változott:** `make_cockpit_texture.py` (ha a kabin változott) →
  `export_web_assets.py` → `build_offline.py`.
* **GitHub Pages:** „Deploy from branch: main / (root)”. A gyökér `index.html` átirányít a `web/`-re.
  Pusholás (`git push origin main`) után ~1 perc alatt frissül. Ezen a gépen a pusholáshoz a tulajdonos
  GitHub-bejelentkezése kell.
* **Offline fájl:** `build_offline.py` után a `web/dogfight-offline.html` commitolva (a Pages-ről tölthető le).

---

## 10. Fejlesztési napló

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
| 19 | Dokumentáció | ez a dokumentum, README frissítés, új képek | `f74219f` |
| 20 | High quality F-16 modell Blenderben, GLB-ben, bekötve a játékba | Blender-szkriptből épített modell és rakéták, saját `.glb`-olvasó, új külső nézet, Node nélküli offline építés | `32cf8f4` |
| 21 | Behúzható futómű aknákkal, kabin ne lógjon ki, orr kövesse a kurzort, fej 160°, erős saját / gyenge ellenséges rakéták, gyengébb ellenséges gép | futóműaknák és -ajtók, behúzás-animáció, ülés- és ernyőjavítás, orr-alapú instruktor, fejforgatás ±160°, `PLAYER_MISSILES` / `BANDIT_MISSILES`, `F16C_BANDIT`, tolóerő-vektorálás | `feefd29` |
| 22 | Kabinból joystickként irányítani, a kabinnézet ne takarjon, főmenü meccs közben / után | egér-botkormány kabinnézetben, nyak körüli fejforgatás előre-oldalra dőléssel, szünetmenü, főmenü Folytatással, új meccs ugyanazon a jeleneten | `a4f9287` |
| 23 | Kabin: több infó olvashatóan (az alapok maradnak); F/A-18E Super Hornet Blenderben saját kabinnal; valós aerodinamika és tolóerő mindkettőnél; gép- és ellenfélválasztás, fegyverzet; a harc a térkép túloldalán | `aircraft_lib.py` + `build_fa18.py` (Super Hornet GLB), élő kabinkijelzők (`mfd.js`), N = kijelzők nézése, lencseeltolás kabinban; `FA18E` adatok, rakéta-ellenállás felület szerint, gépenkénti futómagasság; menü: saját gép, ellenfél, fegyverzet-szerkesztő; harci zóna és biztonsági kör | `92dc6ab` |
| 24 | A kabin-botkormány ne álljon vissza magától középre | a bot ott marad, ahová teszed; 7%-os holtsáv, zöld pont a semlegesben | `4a9d873` |
| 25 | Dokumentálj mindent | a dokumentáció és a README teljes átírása a jelenlegi állapotra | `ad1f7ca` |
| 26 | Oktatás, ami tényleg elmagyaráz mindent (csak aki akarja); ne lőjenek rám 15 km-ről, amíg én nem tudok lockolni; az F-16 legyen jobb az F-18-nál, extrém mód tolóerő-vektorálással egy gombra, 9 G, Cobra rakéta ellen | `tutorial.js` (11 lecke, céldrónok, rakéta-gyakorlat, Oktatás gomb); AI lőtávolság-plafon (normál 8 / 4,5 km), „T = lock” jelzés; F-16 extrém mód (Tab): TVC, 9 G instruktor, cL,max 2,4, 80° Cobra, `Missile.checkCobra`; enyhébb G-sötétülés | – |

---

## 11. Ismert korlátok és tesztelési megjegyzések

* A böngészős változatot csak Chrome-ban, **szoftveres rendereléssel** próbáltuk ki (kb. 10–20 FPS);
  valódi videokártyán a sebességet nem mértük. Gyenge gépen kisebb ablak segíthet.
* **Mérve / kipróbálva (Chrome):** a táblázat repülési értékei (a játék saját függvényeivel), felszállás
  mindkét géppel, a zóna-logika (zónában támadnak, a bázis fölött nem), kevert ellenséges hullám hiba nélkül,
  a Hornet kormányfelületeinek iránya, a botkormány (2 s után is a helyén marad), az offline fájl betöltése.
* A Python tesztek ezen a gépen nem futottak (nincs numpy / Panda3D); a Python kód nem változott.
* **Kontroller:** szimulált kontrollerrel teszteltük.
* A Hornet 87 ezer, az F-16 70 ezer háromszög; sok egyszerre látszó gépnél gyenge videokártyán lassabb lehet.
* A kijelzők szövege normál kabinnézetben kicsi – olvasáshoz az **N** (ráközelítés) való.
* Az F-16 kabinnézete továbbra is a régi, kódból épített modell, ezért belülről a gép formája kicsit eltér
  a külsőtől. A Hornet kabinja a saját modellje.
* A claude.ai artifact és a Python változat a régi (csak F-16-os) állapotban maradt.
* Az „aggressor” F-16 festés elkészül, de a játék nem használja.
* Böngészőben a Ctrl lenyomva tartása közben a böngésző gyorsbillentyűi működnek – a Z biztonságosabb gáz le.
* Az offline fájl pillanatkép: változtatás után újra kell építeni és újra letölteni.

## 12. Ötletek a folytatáshoz

* Részletes Blender-kabin az F-16-ba is (a régi modell kikerülhetne).
* Hornet: középső póttartály (6. állomás), saját hajtómű-hangok; kijelzők lapozása a gombjaikra kattintva.
* Több repülőgép (pl. MiG-29, Su-27) saját adatokkal; aggressor festés az ellenfeleknek.
* Beállítások mentése (gép, fegyverzet, egér) a böngészőben.
* Többjátékos mód; pontosabb rakéta-fly-out (2D, manőverező céllal).
