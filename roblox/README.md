# Dogfight Plus – Roblox változat

A böngészős játék Roblox-os testvére: **hullámokban támadó ellenséges vadászok**, gépágyú, rakéta, flare, **barátokkal közös égbolt**
(a Roblox saját szerverein, bárki csatlakozhat), érmék és egy **shop 100 gép-festéssel és 100 pilóta-öltözettel**.
A kód Luau, Rojo-kompatibilis. **Fontos:** ebben a környezetben nincs Roblox Studio, ezért a kódot itt nem lehetett lefuttatni, csak a
szintaxisát ellenőriztem; az első Studio-s próbán várhatók apróbb hibák (a Studio Output ablaka kiírja őket).

## Mi van benne

| Hely | Mit csinál |
|---|---|
| `src/shared/Catalog.luau` | a 100 + 100 skin (**generált**: `python3 tools/gen_skins.py`, forrása `tools/skins_data.py` – ugyanez hajtja a böngészős játékot is) |
| `src/shared/Config.luau` | minden hangolható szám: érmék, fegyverek, ellenség, Robux-csomagok |
| `src/shared/JetBuilder.luau` | a gép és a pilóta felépítése kockákból (nincs mit feltölteni), a festés mintájával |
| `src/server/` | `Main` (indítás), `World` (sziget), `Combat` (lövés, rakéta, flare, sebzés), `Enemies` (AI és hullámok), `Data` (mentés DataStore-ral), `Shop` (vásárlás, Robux) |
| `src/client/` | `Flight` (repülés), `Hud`, `Lobby` (hangár + shop), `Main` |

## Kipróbálás Studióban

**A) Rojo-val** (ajánlott): `rojo serve roblox` a repó gyökeréből, Studióban a Rojo plugin „Connect”.
**B) Rojo nélkül:** `python3 tools/build_rbxlx.py` → `roblox/build/DogfightPlus.rbxlx`, ezt nyisd meg Studióban, és nyomj Play-t.
Studióban az ellenőrzéshez kapcsold be: Game Settings → Security → *Enable Studio Access to API Services* (különben a mentés nem működik, de a játék fut).

## Szobák, csapatok, kétüléses gép

* **Hangár-csoportok (szobák):** a lobbiban a *Szobák / Csapat* gombbal. Aki szobát nyit, megadja a nevét, a módját, és hogy **hányan jöhetnek még be** (összesen legfeljebb **20** fő, `Config.Rooms.MaxPlayers`); lehet **privát** is (4 jegyű kóddal lehet belépni, a listán nem látszik). A szobák egy szerveren belül élnek: mindenki csak a saját szobája gépeit, ellenségeit és rakétáit látja, és csak azok hatnak rá.
* **Két mód:** *Együtt (AI)*: a szoba saját ellenség-hullámai ellen, közösen; *Csapatharc*: kék és piros csapat egymás ellen. A csapatot **mindenki maga váltja** (az „Átlépek ide” gombbal, repülés közben nem), **bármilyen eloszlásban** (akár 15 a 3 ellen). A pontot a kilőtt ellenfelek adják.
* **Kétüléses F/A-18F:** a lobbiban az *Indulás* előtt válaszd a *Kétüléses* gépet. A csapattársak a szobák képernyőn a *Beülök* gombbal beülnek a **hátsó ülésre**: ott nem repülnek, hanem a gép rakétáit lövik (széles szögben), flare-t dobnak, és a **T**-vel jelölik a célpontot a pilótának (a pilóta zárása a jelöltet választja). A gép tulajdonosa repül és a gépágyút kezeli; a lelövésből a hátsó ülés fele annyi érmét kap. Ha a gépet lelövik, mindketten kiesnek. A két pilóta a saját öltözetét viseli, és a fülkében marad (senki sem lóg ki a gépből).
* **Készség a Roblox oldalán:** a szerver játékos-létszámát (Max Players) a Creator Dashboardon állítsd 20-nál nagyobbra, ha több szoba is menjen egyszerre; a Roblox saját privát szerverei (VIP) is használhatók.

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

* Nincs felszállás / leszállás: a gép a levegőből indul, a talajnak ütközés lezuhanás.
* Nincs hang (nem akartam kitalált hangazonosítókat beírni). A `Hud`-ba és a `Combat`-ba egy-egy `Sound` könnyen beilleszthető.
* A pilóta kockákból épül (sisak, napellenző, oxigénmaszk, tömlő, hám, kesztyű), a pilótafülkében ülő pilótán és a hangár-előnézeten látszik (nincs avatar a repülés alatt).
* PvP kikapcsolva (`Config.PvP`); a barátok együtt lőnek az ellenségre.
