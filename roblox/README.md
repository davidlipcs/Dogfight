# Dogfight Plus – Roblox változat

A böngészős játék Roblox-os változata. A repülési modell, a fegyverek, az MI, a küldetések (hullámok, párbaj, túlélés, gyűrű-, kanyon- és
alagútfutam, közös repülés), a HUD, a kamera és a kabin-kijelzők a böngészős játék kódjából vannak átírva Luau-ba (`src/shared/sim`,
`src/shared/game`), és **a játékos saját gépén futnak**, ugyanúgy, mint a böngészőben. A szerver csak a mentést (érme, festések, karrier,
rekordok), a boltot és a szobákat kezeli. Az átírt számítások számról számra egyeznek a JavaScript-tel (`roblox/tests`).

**Fontos:** a Roblox-oldalt (menü, kamera, HUD, jelenet, hang) nem lehetett Roblox Studióban futtatni ott, ahol készült; az Output ablak kiírja,
ha valami elromlik – azt kell elküldeni a javításhoz.

## Hova mi kerül (lépésről lépésre)

### 1. A sziget (egyszer)
1. Nyisd meg a `DogfightPlus.rbxlx` fájlt Studióban (ne indíts játékot).
2. **View → Command Bar**, ide másold be és Enter: `require(game.ServerScriptService.Server.IslandBuilder).build()`
3. Pár percig dolgozik (az Output ablakban a végén: „the island is built”). Utána **File → Save**.

### 2. A gépek (egyszer; nélkülük kockákból épített gépek repülnek)
A `roblox/models` mappában 16 `.glb` fájl van, a böngészős játék gépei Roblox-barát (≤ 15 000 háromszögű darabokra csökkentett) változatban.
1. Studióban: **View → Asset Manager** (ha nem látszik, a View menüben kapcsold be) → fent a **Bulk Import** gomb.
2. A megnyíló fájlválasztóban jelöld ki az összes `.glb` fájlt a `roblox/models` mappából (Ctrl+A), **Open**.
3. A Studio megmutatja az importálandókat – **Import**. Várd meg, amíg mind átkerül (néhány perc). Minden gép egy `Model` lesz a Workspace-ben, a fájl nevével (`f16`, `fa18` …).
4. **View → Command Bar**, ide: `require(game.ServerScriptService.Server.Tools).adoptJets()` – ez a modelleket a `ReplicatedStorage.JetModels` mappába teszi, onnan veszi a játék.
5. **File → Save.** (A `Tools.listJets()` kiírja, melyik gép van meg.)
Ha egy gép hátrafelé repül: `Config.JetModelFlip = { f16 = true }`.
Az újragenerálás: `python3 tools/make_roblox_models.py` (kell hozzá: `pip install trimesh fast-simplification scipy numpy pillow`).

### 3. A hangok (egyszer)
A böngésző a hangokat képletekből készíti; Roblox csak feltöltött hangfájlt játszik. A `roblox/audio/dogfight_sounds.wav` **egyetlen fájl**, benne az
összes hang (motor, utánégető, ágyú, rakéta, robbanás, figyelmeztetések …); a `src/shared/SoundMap.luau` tudja, melyik hang hol van benne.
1. Menj a **create.roblox.com** oldalra, jelentkezz be.
2. Bal oldalt **Creations** (Alkotások) → fent **Development Items** (Fejlesztői elemek) → **Audio** (Hang) → **Upload** (Feltöltés).
   (A Studióban is megy: **View → Asset Manager → Audio → Import**; az Asset Manager a sima fájlt is feltölti.)
3. Válaszd ki a `dogfight_sounds.wav` fájlt, add neki a nevét (pl. „Dogfight hangok”), **Upload**. A Roblox pár percig ellenőrzi.
4. Ha kész, nyisd meg a hang oldalát: az **Asset ID** egy hosszú szám (a címsorban is ott van: `.../audio/1234567890`). Másold ki.
5. Studióban: Explorer → kattints a **ReplicatedStorage**-ra → Properties → lent az **Attributes** → **Add Attribute** → név: `SoundAssetId`, típus: **String**, érték: az Asset ID. (Vagy írd be a `src/shared/Config.luau` fájlban a `Config.SoundId = ` után.)
6. **File → Save.** Ha az ID nincs beállítva, a játék néma.

### 4. Indítás
Studióban nyomj **Play**-t (vagy a Roblox-ra feltöltve a **Play** gomb). A lobbiban az **INDULÁS A PÁLYÁRÓL** felszállással kezd, az **INDULÁS A LEVEGŐBEN** a levegőből. A **Játék** fülön ugyanazok a beállítások vannak, mint a böngészős főmenüben.

## A méretarány (miért nem lehet a gép „igazi méretű”)

A játék **valódi méterekben** számol: a sziget 102 kilométer széles, a gép 15 méter hosszú. A Roblox mértékegysége a *stud*. Ha 1 méter = 1 stud lenne, a sziget
102 000 stud széles volna – ekkora terepet a Roblox nem tud felépíteni (a legkisebb terep-kocka 4 stud, ez 650 millió kocka lenne). Ezért a **szigetet kicsinyítjük**:
1 méter = 0,1 stud, így a sziget 10 240 stud, és kiépíthető. Csakhogy ekkor a 15 méteres gép 1,5 stud lenne – akkora, mint egy kicsi ládika, a kamera pedig
nem is tud ilyen közel látni. Ezért a **gépeket, a rakétákat és a füstöt nagyítva rajzoljuk** (`Config.ModelScale = 8`: a gép ~12 stud), a kamera távolságát is ugyanennyivel
nagyítva. A repülés, a sebesség és minden számítás közben a valódi méterekben történik, a HUD is méterben és km-ben mutat. A látvány különbsége: más gépek távolról nagyobbnak látszanak, mint a böngészőben.

## Szobák, csapatok, kétüléses gép

* **Hangár-csoportok (szobák):** a lobbiban a *Szobák / Csapat* gombbal. Aki szobát nyit, megadja a nevét, a módját, és hogy **hányan jöhetnek még be** (összesen legfeljebb **20** fő, `Config.Rooms.MaxPlayers`); lehet **privát** is (4 jegyű kóddal lehet belépni, a listán nem látszik). A szobák egy szerveren belül élnek: mindenki csak a saját szobája gépeit, ellenségeit és rakétáit látja, és csak azok hatnak rá.
* **Két mód:** *Együtt (AI)*: a szoba saját ellenség-hullámai ellen, közösen; *Csapatharc*: kék és piros csapat egymás ellen. A csapatot **mindenki maga váltja** (az „Átlépek ide” gombbal, repülés közben nem), **bármilyen eloszlásban** (akár 15 a 3 ellen). A pontot a kilőtt ellenfelek adják.
* **Kétüléses F/A-18F:** a lobbiban az *Indulás* előtt válaszd a *Kétüléses* gépet. A csapattársak a szobák képernyőn a *Beülök* gombbal beülnek a **hátsó ülésre**: ott nem repülnek, hanem a gép rakétáit lövik (széles szögben), flare-t dobnak, és a **T**-vel jelölik a célpontot a pilótának (a pilóta zárása a jelöltet választja). A gép tulajdonosa repül és a gépágyút kezeli; a lelövésből a hátsó ülés fele annyi érmét kap. Ha a gépet lelövik, mindketten kiesnek. A két pilóta a saját öltözetét viseli, és a fülkében marad (senki sem lóg ki a gépből).
* **Készség a Roblox oldalán:** a szerver játékos-létszámát (Max Players) a Creator Dashboardon állítsd 20-nál nagyobbra, ha több szoba is menjen egyszerre; a Roblox saját privát szerverei (VIP) is használhatók.

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

* A szobák, csapatok és a kétüléses gép leírása fent a régi, szerver-oldali változatra vonatkozik: az új, kliens-oldali játékban ezek még nincsenek átírva (a játék egyelőre egyjátékos).
* Hiányzik: hordozó, karrier-mód, oktatás, rádió, a kabin 3D-s műszerfala (a kijelzők a képernyő alján vannak).
* A pilóta kockákból épül (sisak, napellenző, oxigénmaszk, tömlő, hám, kesztyű), a pilótafülkében ülő pilótán és a hangár-előnézeten látszik (nincs avatar a repülés alatt).
* PvP kikapcsolva (`Config.PvP`); a barátok együtt lőnek az ellenségre.
