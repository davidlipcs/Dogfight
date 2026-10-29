# Dogfight Plus – Roblox változat

A böngészős játék Roblox-os változata. A repülési modell, a fegyverek, az MI, a küldetések (hullámok, párbaj, túlélés, gyűrű-, kanyon- és
alagútfutam, közös repülés), a HUD, a kamera és a kabin-kijelzők a böngészős játék kódjából vannak átírva Luau-ba (`src/shared/sim`,
`src/shared/game`), és **a játékos saját gépén futnak**, ugyanúgy, mint a böngészőben. A szerver csak a mentést (érme, festések, karrier,
rekordok), a boltot és a szobákat kezeli. Az átírt számítások számról számra egyeznek a JavaScript-tel (`roblox/tests`).

**Fontos:** a Roblox-oldalt (menü, kamera, HUD, jelenet, hang) nem lehetett Roblox Studióban futtatni ott, ahol készült; az Output ablak kiírja,
ha valami elromlik – azt kell elküldeni a javításhoz.

## Hova mi kerül (lépésről lépésre)

### 0. Frissítés (ha már van felépített szigeted és importált gépeid)
**Ne a `DogfightPlus.rbxlx`-et nyisd meg újra** – az üres, abban nincs sziget és nincsenek gépek. Helyette a **`DogfightCode.rbxmx`** csak a játék kódját cseréli ki a *te* pályádban:
1. Nyisd meg a saját, már elmentett pályádat (ahol a sziget és a gépek vannak).
2. Húzd be a `DogfightCode.rbxmx` fájlt a Studio 3D ablakába (vagy jobb klikk a Workspace-en → *Insert from File…*).
3. **Window → Command Bar**, ide: `require(workspace.DogfightCodeUpdate.Install)()` → Enter. (Az Output kiírja: „the code is updated”.)
4. **File → Save**, majd **Play**.
A lobbi bal felső részén látszik: *Sziget: kész/NINCS* és *Gépek: X/16*. Ha valami hiányzik, a játék nem indul el, hanem megmondja, mit pótolj.


### 1. A sziget (egyszer)
1. Nyisd meg a `DogfightPlus.rbxlx` fájlt Studióban (ne indíts játékot).
2. **Window → Command Bar** (régebbi Studióban View → Command Bar), ide másold be és Enter: `require(game.ServerScriptService.Server.IslandBuilder).build()`
3. Pár percig dolgozik (a **Window → Output** ablakban a végén: „the island is built”). Utána **File → Save**.

### 2. A gépek (egyszer; nélkülük kockákból épített gépek repülnek)
A `roblox/models` mappában 16 `.glb` fájl van, a böngészős játék gépei Roblox-barát (≤ 15 000 háromszögű darabokra csökkentett) változatban.
0. Ha a játék teszt módban fut (Client / Server fülek), előbb **Test → Stop**.
1. Studióban: **Window → Asset Manager** (régebbi Studióban View → Asset Manager; vagy a Home fülön az Asset Manager gomb) → fent a **Bulk Import** gomb.
2. A megnyíló fájlválasztóban jelöld ki az összes `.glb` fájlt a `roblox/models` mappából (Ctrl+A), **Open**.
3. A Studio megmutatja az importálandókat – **Import**. Várd meg, amíg mind átkerül (néhány perc). Minden gép egy `Model` lesz a Workspace-ben, a fájl nevével (`f16`, `fa18` …).
4. **File → Save.** (Ha korábban már importáltál gépeket, az új import felülírja a régieket – az indításkori átrakás a frissen importált modellt veszi.) Ennyi: a játék **induláskor magától** átteszi a Workspace-ben talált gépeket a `ReplicatedStorage.JetModels` mappába (a Window → Output kiírja: „N jet model(s) moved … (now X of 16)”). Ha kézzel akarod: **Window → Command Bar**, ide: `require(game.ServerScriptService.Server.Tools).adoptJets()`, majd Save. (A `Tools.listJets()` kiírja, melyik gép van meg.)
5. A játékban a **Hangár → Gép** fülön látszik, melyik gép van importálva; a menüben a választott géphez tartozó modell repül.
Ha egy gép hátrafelé repül: `Config.JetModelFlip = { f16 = true }`.
Az újragenerálás: `python3 tools/make_roblox_models.py` (kell hozzá: `pip install trimesh fast-simplification scipy numpy pillow`).

### 3. A hangok (egyszer)
A böngésző a hangokat képletekből készíti; Roblox csak feltöltött hangfájlt játszik. A `roblox/audio/dogfight_sounds.wav` **egyetlen fájl**, benne az
összes hang (motor, utánégető, ágyú, rakéta, robbanás, figyelmeztetések …); a `src/shared/SoundMap.luau` tudja, melyik hang hol van benne.
1. Menj a **create.roblox.com** oldalra, jelentkezz be.
2. Bal oldalt **Creations** (Alkotások) → fent **Development Items** (Fejlesztői elemek) → **Audio** (Hang) → **Upload** (Feltöltés).
   (A Studióban is megy: **Window → Asset Manager → Audio → Import**.)
3. Válaszd ki a `dogfight_sounds.wav` fájlt, add neki a nevét (pl. „Dogfight hangok”), **Upload**. A Roblox pár percig ellenőrzi.
4. Ha kész, nyisd meg a hang oldalát: az **Asset ID** egy hosszú szám (a címsorban is ott van: `.../audio/1234567890`). Másold ki.
5. Studióban: Explorer → kattints a **ReplicatedStorage**-ra → Properties → lent az **Attributes** → **Add Attribute** → név: `SoundAssetId`, típus: **String**, érték: az Asset ID. (Vagy írd be a `src/shared/Config.luau` fájlban a `Config.SoundId = ` után.)
6. **File → Save.** Ha az ID nincs beállítva, a játék néma.

### 4. Indítás
Studióban nyomj **Play**-t (vagy a Roblox-ra feltöltve a **Play** gomb). A lobbiban az **INDULÁS A PÁLYÁRÓL** felszállással kezd, az **INDULÁS A LEVEGŐBEN** a levegőből. A **Játék** fülön ugyanazok a beállítások vannak, mint a böngészős főmenüben.

**A betöltés:** az indítás gomb után a játék egy betöltőképernyőt mutat, és csak akkor indul, amikor a sziget, a kifutó, a gépek és a gépek hálói mind megvannak (legfeljebb 25 másodpercig vár, utána akkor is indul).

## A méretarány (miért nem lehet a gép „igazi méretű”)

A játék **valódi méterekben** számol: a sziget 102 kilométer széles, a gép 15 méter hosszú. A Roblox mértékegysége a *stud*. Ha 1 méter = 1 stud lenne, a sziget
102 000 stud széles volna – ekkora terepet a Roblox nem tud felépíteni (a legkisebb terep-kocka 4 stud, ez 650 millió kocka lenne). Ezért a **szigetet kicsinyítjük**:
1 méter = 0,1 stud, így a sziget 10 240 stud, és kiépíthető. Csakhogy ekkor a 15 méteres gép 1,5 stud lenne – akkora, mint egy kicsi ládika, a kamera pedig
nem is tud ilyen közel látni. Ezért a **gépeket, a rakétákat és a füstöt nagyítva rajzoljuk** (`Config.ModelScale = 8`: a gép ~12 stud), a kamera távolságát is ugyanennyivel
nagyítva. A repülés, a sebesség és minden számítás közben a valódi méterekben történik, a HUD is méterben és km-ben mutat. A látvány különbsége: más gépek távolról nagyobbnak látszanak, mint a böngészőben.

## Szobák, csapatok, kétüléses gép, rádió

* **Hangár-csoportok (szobák):** a lobbiban a *Szobák / Csapat* gombbal. Szobát nyitva megadod a nevét, a módját és hogy hányan jöhetnek még (összesen legfeljebb **20** fő); lehet **privát** is (4 jegyű kód). Mindenki a saját gépén repül, a többieket "szellemként" látja; a szoba nyitója futtatja az ellenséget.
* **Két mód:** *Együtt (AI)* és *Csapatharc* (kék/piros, bármilyen eloszlásban; a csapatot mindenki maga váltja).
* **Kétüléses gép:** a menüben az *Ülések* sorban válaszd a *Kétüléses (szobában)* lehetőséget, és indulj szobából. A csapattársak a Szobák képernyőn a *Beülök* gombbal ülnek a **hátsó ülésre**: nem repülnek, hanem **T** = célpont jelölése (a pilótának is látszik, az ő T-je előbb a jelöltre zár), **Y** = következő ellenség, **Space** = rakétaindítás a pilóta gépéről (széles szögben, zár nélkül), **X** = flare, **1/2** = fegyverválasztás, egérrel körülnéz. A hátsó ülés fele annyi érmét kap a lelövésért. A pilóta és a hátsó ülés is kiléphet; ha a pilótát lelövik, a hátsó ülés véget ér. *Nincs* külön hátsó-ülés modell az importált gépeken (a pilóta nem látja a hátsó ülésen ülőt).
* **Rádió:** **I** = megnyílik a rádió-panel: írd be angolul a hívást (pl. `FOX TWO`, `SPLASH`, `BINGO`, `REQUEST PICTURE`, `COVER ME`), vagy kattints / nyomd meg a számot a listán. A másik oldal (torony, kísérő, AWACS) feliratban válaszol, a kísérő végrehajtja a parancsokat. Beszédfelismerés és beszédhang nincs (a Roblox nem tud).

## Háborús karrier (HÁBORÚ gomb a lobbiban)

A böngészős karrier 3. világháborús része, a `campaign.js` számról számra egyező átirata (150 napnyi háború ugyanazt adja, mint a JavaScript): négy nagyhatalom (USA, Európa, Oroszország, Kína) valódi vadászgép-számokkal, havi gyártással és költségvetéssel, 12 front valódi helyeken, bizalom, szövetségek, tűzszünetek, gyárbombázás, a többiek légierejéről csak becslés (hírszerzés). Te hadnagyként kezded: kapsz egy parancsot (front, feladat, ellenség a front valódi gépeiből), **bevetésre indulsz a levegőben** (légtérfölény vagy légtérvédelmi járőr, AI vezér vagy AI kísérő, szövetséges és ellenséges gépek, erősítés), és ami a bevetésben történt (lelőtt és elveszett gépek, bizalom), hat a háborúra. Előléptetésekkel nő a döntési jogod: százados = feladat és időpont, őrnagy = front és gép, alezredes = MI-kötelékek kiküldése, ezredes = politika (szövetség, tűzszünet, gyárbombázás, gyártási sorrend). A háború és a pilóta a szerveren mentődik. Nincs benne (a böngészősben van): a pilótaiskola (rádióórák, T-6, T-38/T-45, BFM), a légtérrendészeti bevetések, a gyalogos bázis, a pilótalista (roster) és a világtérkép.

## Kabin: 3D műszerfal

Kabinnézetben (V) a kijelzők (radar, térkép, fegyverek, hajtómű, DED, RWR) valódi képernyők egy műszerfalon a pilóta előtt (`MfdView.luau`, SurfaceGui). **J/K/L** lapoz, **N** a kijelzők felé néz. A modellek belső terét a játék nem rajzolja ki (a sajátgép kabinnézetben rejtett), ezért a műszerfal lebegő képernyőkből áll. Ha rosszul néz ki, a menüben a *Kabin kijelzők* sorban átkapcsolható „A képernyő alján" változatra.

## A napellenző üvege

A pilóta-öltözetek napellenzője valódi üveg (`visorT` = fényáteresztés, `visor` = árnyalat, `mirror` = tükörbevonat). Pilótafülke-nézetben (V) a `Visor.luau` a színével és sötétségével befolyásolja a képet (színkorrekció + sötét perem); a tiszta üveg nem változtat semmin, a legsötétebb is csak 75%-ig sötétít.

## Irányítás

PC: egér (a kurzor irányít, M: ki/be) vagy W/S/A/D · Q/E oldalkormány · Shift/Ctrl gáz · Szóköz / bal klikk tűz · X / jobb klikk rakéta (előbb tartsd az ellenséget az orr előtt: piros doboz jelzi a zárat) · G flare · V pilótafülke · H súgó.
Kontroller és telefon (érintő-joystick + gombok) is van.

## Pénz (Robux) és érmék

* Érmét kapsz lelövésért (100), hullám-bónuszért és a levegőben töltött időért; a shopban skinekre költhető (600 / 1500 / 3500 / 8000 érme a ritkaság szerint).
* **Robux-ár (valódi pénz):** minden skin a ritkasága szerint kapható Robuxért is: 15 / 35 / 65 / **110 R$** (gyakori / ritka / epikus / legendás). A legdrágább skin így ≈ **500 Ft** (a `Config.Money.HufPerRobux = 4.5` árfolyammal számolva; **nézd meg a mostani árfolyamot a Roblox boltban, és írd át**, a program a 500 Ft-os plafont ehhez igazítja). Technikailag négy Developer Product kell (egy a ritkaságonként, a fenti Robux-áron), az azonosítókat a `Config.SkinProducts` tartalmazza; a választott skint a szerver megjegyzi, és a vásárlás visszaigazolásakor adja át.
* **Robux-bevétel (érmecsomagok):** a Creator Dashboardon hozz létre *Developer Product*okat (érmecsomagok), és írd az azonosítójukat a `Config.Products` listába (0 = még nincs, a gomb rejtve marad). A `Config.DoubleCoinsPass` egy *Game Pass* azonosítója (dupla érme). A vásárlás-kezelés (`ProcessReceipt`, dupla-jóváírás elleni védelem) kész.
* A vásárolt érmét nem duplázza a pass.

## Feltöltés a Robloxra (Open Cloud)

1. Creator Hubon hozz létre egy *Experience*-t (ennek lesz Universe ID-ja és egy Place ID-ja).
2. Creator Hub → Open Cloud → API Keys: új kulcs, jogosultság **universe-places: write** erre az experience-re. **A kulcsot ne írd be sehova chatbe, és ne commitold** – környezeti változóként add meg: `ROBLOX_API_KEY`, `ROBLOX_UNIVERSE_ID`, `ROBLOX_PLACE_ID`.
3. `python3 tools/build_rbxlx.py && python3 tools/roblox_publish.py` (próbafutás), majd `--publish` a valódi feltöltéshez (`--save-only`: csak mentett verzió, nem éles).
4. A felhő-környezetben az `apis.roblox.com` hostot engedélyezni kell a hálózati beállításokban (Network access → Allowed domains), különben a feltöltés nem éri el a Robloxot.

## Ismert korlátok

* A Roblox-oldalt (menü, kamera, HUD, hang, részecskék, műszerfal) nem lehetett valódi Studióban kipróbálni, csak egy utánzott Roblox-környezetben; az Output ablak kiírja a hibákat.
* A karrierből hiányzik a pilótaiskola, a légtérrendészet, a gyalogos bázis, a pilótalista és a világtérkép (lásd fent).
* A pilóta kockákból épül, a pilótafülkében ülő pilótán és a hangár-előnézeten látszik.
