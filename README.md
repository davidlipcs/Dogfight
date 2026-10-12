# Dogfight – F-16C légiharc (War Thunder stílusban)

3D légiharc-játék **Pythonban**, a [Panda3D](https://www.panda3d.org/) motorral (nem HTML/böngészős).
Első lépésként csak az **F-16C Block 50** van benne, a War Thunderből ismert fegyverekkel és
lockolási mechanikával:

| Fegyver | Típus | Mit tud |
|---|---|---|
| **M61A1 Vulcan** 20 mm | gépágyú | 6000 lövés/perc, 511 lőszer, nyomjelzők, előretartás-jelző radar lockkal |
| **AIM-9M Sidewinder** | hőkövető („Fox 2”) | 2,5°-os keresőmező, 40°-os kardán, IRCCM (flare-szűrés), all-aspect, ~Mach 2,5 |
| **AIM-120A AMRAAM** | aktív radaros („Fox 3”) | datalink + inerciális középszakasz, 16 km-en „PITBULL”, lofting, ~Mach 4 |
| **ALE-47** | önvédelem | 30 flare + 30 chaff |

Alap fegyverzet: 4× AIM-9M + 2× AIM-120A (`--loadout amraam` = 4× AIM-120A + 2× AIM-9M, `--loadout fox2` = 6× AIM-9M).

Az ellenfelek is F-16-osok („aggressor” homokszínű festéssel), AI pilótával: radarral lockolnak,
rakétát és ágyút használnak, notcholnak, flare-t és chaffot szórnak.

## Telepítés és indítás

Python 3.9+ kell (Panda3D + numpy).

```bash
pip install -r requirements.txt
python main.py
```

Hasznos kapcsolók (`python main.py --help`):

```bash
python main.py --difficulty hard --enemies 3     # nehezebb AI, több ellenség
python main.py --fullscreen --size 1920x1080
python main.py --loadout amraam                  # 4 AMRAAM
python main.py --sensitivity 0.06 --invert-y     # egér beállítások
python main.py --clouds 20 --no-aa               # gyengébb gépre
```

## Irányítás

| Billentyű | Funkció |
|---|---|
| **Egér** | War Thunder-féle egeres célzás: a gép a fehér kör felé repül |
| W / S, A / D, Q / E | magassági, csűrő, oldalkormány kézi felülbírálása |
| Shift / Ctrl | gáz fel / le (100% felett **utánégető**) |
| B (tartva) | légfék |
| C vagy jobb egérgomb (tartva) | szabad körülnézés |
| Z (tartva) | zoom |
| V | kabin (HUD) / külső nézet |
| **Bal egérgomb** | gépágyú |
| **Space** | rakéta indítása |
| 1 / 2 | AIM-9M / AIM-120A kiválasztása |
| X (tartva) | flare + chaff |
| R | radar be / ki |
| Y | következő radarcél kijelölése |
| **T** | radar **lock** / unlock (ha nincs kijelölt cél → ACM mód) |
| **F** | AIM-9M kereső **lock** / elengedés |
| M | célpont-jelölők ki/be |
| H vagy F1 | súgó (szünetelteti a játékot) |
| P | szünet, Esc: kilépés (szünetben) |
| Enter | újraéledés, ha lelőttek |

## Hogyan működik a lockolás? (mint a War Thunderben)

### AIM-9M Sidewinder (hőkövető)
1. Válaszd ki: **1**. A HUD-on megjelenik egy kör – ez a rakéta **keresőfeje**. Közben hallod a
   halk „morgást” (growl).
2. Vidd a célpontot a körbe. Ha a kereső hőforrást lát, a hang **magas, folyamatos sípolásra**
   vált, a kör villog.
3. Nyomd meg az **F**-et: a kereső rááll a célra (LOCK), és innentől magától követi – a fejjel akár
   40°-ra is elnézhet az orrtól.
4. **Space** = indítás. Repülés közben a rakéta saját keresővel, arányos rávezetéssel megy a célra.

Tippek: a hátsó félgömbből és utánégetős (AB) célra sokkal messzebbről lockol (≈9–13 km),
szemből csak ≈3–4 km-ről. Ha van radar lockod, a kereső automatikusan a radarcélra fordul és lockol.
A célpont flare-jei elcsalhatják a rakétát; az AIM-9M IRCCM-je ~65% eséllyel kiszűri őket.

### AIM-120A AMRAAM (aktív radaros)
1. A radar **SRCH** módban pásztáz (±60°). A jobb alsó **B-scope** kijelzőn látod a célokat
   (vízszintesen az irány, függőlegesen a távolság). **Y**-nal válthatsz célt.
2. **T** = lock. Kb. fél másodperc után **STT** lesz: zöld négyzet a célon, távolság és közeledési
   sebesség (Vc).
3. Közelharcban, ha nincs kijelölt cél, a **T** az **ACM** módot kapcsolja: ami az orrod elé kerül
   (szűk függőleges ablak, 16 km-ig), azt automatikusan lockolja.
4. A HUD jobb oldalán a **DLZ** csík mutatja a hatótávot: `Rmax` (még elér), `NO ESC` (nem tud
   kitérni), `MIN` (túl közel). **Space** = indítás.
5. Indítás után a rakéta **datalinken** kapja a célpont helyzetét, amíg tartod a lockot. Kb. 16 km-re
   a céltól aktiválja a saját radarját: **PITBULL** – innentől elengedheted a lockot.
   Ha előtte elveszted a lockot, a rakéta az utolsó ismert pozíció felé repül és ott keres.
6. Lock nélkül is kilőheted („maddog”): ilyenkor azonnal aktív, és ami a keresőjébe kerül, arra megy.

### Védekezés
* **RWR** (bal lent): `16` = ellenséges F-16 radar. Zöld = pásztáz, sárga = **lockolt rád**,
  piros villogó = **rakétát indítottak rád**.
* **Notch**: fordulj 90°-ra a radaros fenyegetéshez képest. A pulzus-Doppler radar kiszűri a
  közel nulla radiális sebességű célokat – kiesel a lockból. Közben szórj **chaffot** (X).
* Hőkövető ellen: **flare** (X), vedd vissza a gázt az utánégetőről, és fordulj élesen.

## Térkép

![Térkép](docs/map.png)

102 × 102 km-es sziget, 100 m-es felbontású domborzattal (az első indításkor ~10 s alatt generálódik,
utána a gyorsítótárból azonnal betölt):

* **észak:** hosszú, havas hegylánc, 3000–4400 m-es csúcsokkal
* **kelet:** nagy, különálló hegytömb (~3200 m)
* **nyugat és közép:** közepes, erdős hegyek (1000–2000 m), völgyek, egy tó
* **dél:** dombok és kisebb hegyek (200–900 m) – itt indulsz, észak felé
* körben tagolt partvonal, a szigeten túl nyílt tenger

![Hegyek](docs/screenshot_mountains.png)

## Repülésmodell

Az F-16C Block 50 (F110-GE-129, 4× AIM-9M + 2× AIM-120A) mért értékei a modellben:

| | Modell | Valódi F-16C |
|---|---|---|
| Végsebesség tengerszinten (utánégető) | 1455 km/h, M1,19 | ~M1,2 |
| Végsebesség 11 km-en | 2007 km/h, M1,89 | M1,8–2,0 (rakétákkal) |
| Katonai teljesítmény, 9 km | M1,0 | nem tud szuperszonikusan cirkálni |
| Gyorsulás 300→600 csomó, tengerszint | 16 s | |
| Emelkedés 10 km-re | ~80 s | ~1,5 perc |
| Plafon | ~16 km | 15,2 km (50 000 ft) |
| Tartós forduló alacsonyan | 9 G, ~21°/s | 18–21°/s |
| G-felépülés 1→8,5 G | ~1 s | ~9 G/s |
| Hajtómű: alapjárat → katonai | ~4 s | ~4 s |
| Utánégető begyújtás → max | ~1,5 s | 1–2 s |

* **Légkör:** ISA 0–32 km (sűrűség, hangsebesség) – fent kevesebb a felhajtóerő és a tolóerő,
  11 km felett a tolóerő gyorsabban csökken, ezért kb. 16 km a plafon.
* **Hajtómű:** valósághű, késleltetett felpörgés (alapjáraton lassú), magasság- és Mach-függő tolóerő,
  üzemanyag-fogyasztás (utánégetővel ~8 kg/s!).
* **Fly-by-wire (FLCS):** a botkormány **G-t** kér (semleges = 1 G, max **9 G**, min −3 G),
  a G-felépülés ~10 G/s-ra korlátozott, **25°-os AoA-limiter**, ~270°/s orsózás.
  A nagy G-s forduló **energiát (sebességet) emészt**, lassan nem tudsz 9 G-t húzni (sarok-sebesség ~750 km/h).
* **Aerodinamika:** Mach-függő felhajtóerő, transzonikus ellenállás-növekedés M0,88-tól, indukált ellenállás.
* **Egeres irányítás:** az "instruktor" a **repülési pályát** (sebességvektort) viszi a fehér körre,
  gravitáció-kompenzációval: vízszintes célnál tartja a magasságot, oldalra mutatva koordinált,
  helyesen bedöntött fordulót repül, mögötted lévő célnál vízszintes fordulót választ.

Minden adat egy helyen van: `dogfight/sim/specs.py` – itt lehet hangolni.

## Projekt felépítése

```
main.py                 indítás, parancssori kapcsolók
dogfight/
  game.py               Panda3D alkalmazás, játékmenet (hullámok, újraéledés)
  camera.py             War Thunder-féle egeres kamera, kabin nézet
  controls.py           bemenet, játékos "instruktora"
  audio.py              kódból generált hangok (growl, lock-hang, RWR, ágyú, hajtómű)
  sim/                  szimuláció (megjelenítés nélkül, tesztelhető)
    specs.py            F-16C, AIM-9M, AIM-120A, M61A1, APG-68 adatai
    flight_model.py     aerodinamika + FLCS
    missile.py          rakéták, arányos rávezetés, datalink, pitbull, DLZ
    radar.py            SRCH / ACM / STT, Doppler-notch, chaff
    ir_seeker.py        IR keresőfej, flare-ek, IRCCM
    rwr.py              radar figyelmeztető vevő
    guns.py             gépágyú, ballisztika, találat-doboz, előretartás
    aircraft.py, world.py, terrain.py, signatures.py, countermeasures.py
  ai/                   AI pilóta + közös "instruktor" (irány -> kormánymozdulatok)
  render/               procedurális F-16 és rakéta modellek, terep (LOD), ég, felhők, effektek
  ui/                   HUD, radar B-scope, RWR, súgó
tests/                  pytest tesztek a szimulációhoz
```

Tesztek futtatása: `pip install pytest && python -m pytest`
