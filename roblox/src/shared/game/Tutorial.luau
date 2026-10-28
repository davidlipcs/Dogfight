--!nonstrict
-- The tutorial (Oktatás): the port of web/js/tutorial.js.  An optional guided flight: every lesson explains what a system does, how to use
-- it and when it is worth it, then gives one small task that the game checks by itself.  Target drones do not shoot back, and the player's
-- jet cannot be hurt by weapons here.  The texts are Roblox rich text (<b>, <font>).  Common subset of Lua 5.4 and Luau.
local M = require(script.Parent.Parent.sim.SimMath)
local Sim = require(script.Parent.Parent.sim.Sim)
local AI = require(script.Parent.Parent.sim.AI)
local Specs = require(script.Parent.Parent.sim.Specs)
local Weapons = require(script.Parent.Parent.sim.Weapons)
local V, add, sub, mul, norm, len, clamp, copy, DEG = M.V, M.add, M.sub, M.mul, M.norm, M.len, M.clamp, M.copy, M.DEG
local atan2, sin, cos, abs, max, min = M.atan2, math.sin, math.cos, math.abs, math.max, math.min

local T = {}

local function k(key) return '<font color="#ffc840"><b>[' .. key .. ']</b></font>' end

-- a target that just flies: straight, or weaving gently; radar off so the RWR stays quiet
local Drone = {}
Drone.__index = Drone
local function newDrone(ac, heading, weave, throttle)
	local self = setmetatable({}, Drone)
	self.ac, self.heading, self.weave, self.throttle, self.t, self.alt = ac, heading, weave or 0, throttle or 0.9, 0, ac.pos.z
	if ac.radar.on then ac.radar:togglePower() end
	ac.pilot = self
	return self
end
function Drone:think() end
function Drone:fly(dt)
	local ac = self.ac
	self.t = self.t + dt
	local h = self.heading + sin(self.t * 0.3) * self.weave
	local climb = clamp((self.alt - ac.pos.z) / 1500, -0.25, 0.25)
	AI.steerTowards(ac.fm, norm(V(sin(h), cos(h), climb)), ac.controls, 0.45, 0.8)
	ac.controls.throttle = self.throttle
end

local function fixs(x, n) return string.format("%." .. (n or 1) .. "f", x) end

-- the lessons: { title, read, paras (list of rich text lines), task, setup(t), check(t, dt), status(t) }
local function lessons(spec)
	local f16, gun = spec.id == "f16", spec.gun
	local L = {}
	local function add_(l) L[#L + 1] = l end
	add_({ title = "Üdvözlünk a pilótafülkében!", read = true, paras = {
		"Ez az oktatás lépésről lépésre végigvezet a játékon. Minden lépésnél leírjuk, <b>mit</b> csinál egy funkció, <b>hogyan</b> használod és <b>mikor</b> érdemes, utána jön egy kis feladat – a játék magától észreveszi, ha megcsináltad.",
		"A gép közben magától repül. Gyakorlás alatt a lövések nem sebeznek meg, csak a földbe csapódás veszélyes.",
		"<b>A képernyő</b>",
		"• <b>Bal oldalt:</b> IAS = sebesség (km/h), M = Mach, G = terhelés, AoA = állásszög, THR = gázkar, MOT = hajtómű.",
		"• <b>Jobb oldalt:</b> ALT = magasság, AGL = föld feletti magasság, VS = emelkedés, HDG = irány, FUEL = üzemanyag, HP = épség.",
		"• <b>Középen:</b> a zöld kereszt a gép orra, a szárnyas zöld kör a valódi repülési irány, a fehér kör az, ahová célzol.",
		"• <b>Bal lent</b> az RWR (ki figyel rád radarral), <b>jobb lent</b> a radar.",
	}, task = "Nyomd meg az " .. k("Enter") .. "-t, ha elolvastad." })
	add_({ title = "Repülés az egérrel", paras = {
		"<b>Mit:</b> külső nézetben az egér a fehér kört mozgatja, a gép pedig az orrát oda fordítja. A bedöntést és a húzást egy robotpilóta (instruktor) intézi helyetted.",
		"<b>Hogyan:</b> mozgasd az egeret. Kicsi elmozdulás = finom korrekció, nagy = éles forduló. Kézzel is repülhetsz: " .. k("S") .. " orr fel, " .. k("W") .. " orr le, " .. k("A") .. " / " .. k("D") .. " orsózás, " .. k("Q") .. " / " .. k("E") .. " oldalkormány – amíg nyomod, az instruktor elengedi a gépet.",
		"<b>Mikor:</b> célzáshoz és üldözéshez az egér a legjobb; kézzel akkor, ha egy manővert pontosan akarsz.",
	}, task = "Fordulj legalább 90°-ot (bármelyik irányba).",
		setup = function(t) t.flags.turned, t.flags.lastHdg = 0, nil end,
		check = function(t)
			local f = t.player.forward
			local h = atan2(f.x, f.y)
			if t.flags.lastHdg ~= nil then
				local d = h - t.flags.lastHdg
				d = atan2(sin(d), cos(d))
				t.flags.turned = t.flags.turned + d
			end
			t.flags.lastHdg = h
			return abs(t.flags.turned) >= 90 * DEG
		end,
		status = function(t) return "Eddig: " .. math.floor(abs(t.flags.turned) / DEG + 0.5) .. "°" end })
	add_({ title = "Gáz és utánégető", paras = {
		"<b>Mit:</b> " .. k("Shift") .. " növeli, " .. k("Z") .. " (vagy " .. k("Ctrl") .. ") csökkenti a gázt. 100% a katonai teljesítmény (MIL). E fölött jön az utánégető (AB): sokkal több tolóerő, de 4–5-ször annyi üzemanyag.",
		"<b>Hogyan:</b> tartsd nyomva a " .. k("Shift") .. "-et – 100%-nál megáll. Engedd el, és nyomd meg még egyszer: ez az AB. Lefelé az első " .. k("Z") .. " kikapcsolja az AB-t. A HUD-on a THR a kar állása, a MOT a hajtómű, ami pár másodperc alatt pörög fel.",
		"<b>Mikor:</b> AB-t felszálláskor, ha lelassultál, és éles forduló közben. Utazáshoz MIL vagy kevesebb, így tovább bírja az üzemanyag. Hőkövető rakéta ellen kapcsold ki az AB-t.",
	}, task = "Kapcsold be az utánégetőt, aztán vedd vissza 100%-ra.",
		setup = function(t) t.flags.ab = false end,
		check = function(t)
			local thr = t.player.controls.throttle
			if thr > 1.001 then t.flags.ab = true end
			return t.flags.ab and thr <= 1.001
		end,
		status = function(t) return t.flags.ab and "Utánégető megvolt – most vissza 100%-ra (Z)" or ("Gáz most: " .. math.floor(min(t.player.controls.throttle, 1) * 100 + 0.5) .. "%") end })
	add_({ title = "Forduló, G és energia", paras = {
		"<b>Mit:</b> a G a terhelés: vízszintes repülésben 1 G, a gép határa " .. spec.gMax .. " G. Minél nagyobb a G, annál élesebben fordulsz – de annál gyorsabban fogy a sebességed. A sebesség az „energiád”: ha elfogy, nem tudsz fordulni, és könnyű célpont leszel.",
		"<b>Hogyan:</b> vidd az egeret messze oldalra és felfelé, vagy nyomd az " .. k("S") .. "-t. Közben figyeld a bal oldali G és IAS értéket.",
		"<b>Mikor:</b> a legélesebb forduló kb. 650–850 km/h-n megy (ez a sarok-sebesség). Ha elfogyott a sebesség: AB és enyhe süllyedés. 8 G fölött tartósan elszürkül a kép.",
	}, task = "Húzz legalább 6 G-t.",
		setup = function(t) t.flags.g = 1 end,
		check = function(t) t.flags.g = max(t.flags.g, t.player.fm.gLoad); return t.flags.g >= 6 end,
		status = function(t) return "Legnagyobb eddig: " .. fixs(t.flags.g) .. " G" end })
	add_({ title = "Kabin és kijelzők", paras = {
		"<b>Mit:</b> a " .. k("V") .. " a kabinnézet. Itt az egér maga a botkormány: előre tolva orr le, magad felé húzva orr fel, oldalra orsózás. A bot ott marad, ahová teszed – középre te viszed vissza (a bal oldali kis kijelzőn a zöld pont jelzi a semleges állást).",
		"<b>Hogyan:</b> " .. k("N") .. " = nagyobb kijelzők, újra " .. k("N") .. " = vissza. " .. k("J") .. " / " .. k("K") .. " / " .. k("L") .. " = a bal / jobb / középső kijelző lapozása.",
		"• <b>RDR</b> – radar: a célok, a lockolt cél adatai, hatótáv-csík  • <b>SA</b> – térkép: ellenség, rakéták, harci zóna, bázis  • <b>SMS</b> – fegyverzet, lőszer  • <b>ENG</b> – hajtómű, üzemanyag, mennyi kell hazáig (BINGO)  • <b>RWR</b> – ki figyel rád",
		"<b>Mikor:</b> a kabinnézet akkor jó, ha a cél előtted van. A kijelzőkre utazás közben vagy lock előtt nézz – csak röviden.",
	}, task = "Válts kabinnézetbe (" .. k("V") .. "), nagyítsd fel a kijelzőket (" .. k("N") .. "), majd " .. k("N") .. "-nel vissza.",
		setup = function(t) t.flags.panel = false end,
		check = function(t)
			local c = t.cam
			if c.cockpit and c.panelLook then t.flags.panel = true end
			return t.flags.panel and c.cockpit and not c.panelLook
		end,
		status = function(t) return t.flags.panel and "Most N-nel vissza" or (t.cam.cockpit and "Most nyomd meg az N-t" or "Nyomd meg a V-t") end })
	add_({ title = "Radar lock és AIM-120 – távoli cél", paras = {
		"Egy céldrón repül feléd kb. 22 km-ről (nem lő vissza). A piros háromszög jelöli, alatta a távolság km-ben.",
		"<b>Mit:</b> az AIM-120A AMRAAM radarvezérlésű rakéta („Fox 3”), 5–35 km-ről lőhető. Kilövés után a te radarod vezeti, majd kb. 11–16 km-re a céltól bekapcsolja a saját radarját (PITBULL) – onnan magától megy.",
		"<b>Hogyan:</b>  1. Nyomd meg a " .. k("2") .. "-t: kiválasztod az AIM-120A-t.  2. Fordulj a cél felé, és nyomd meg a " .. k("T") .. "-t: fél másodperc alatt lockol, a célon zöld négyzet jelenik meg.  3. A jobb oldali DLZ-csík mutatja, elér-e a rakéta. Ha a négyzet piros lesz és villog a <b>LŐHETSZ!</b>, nyomd meg a " .. k("Space") .. "-t.  4. Tartsd az orrod a cél felé, amíg meg nem jelenik a PITBULL üzenet.",
		"<b>Mikor:</b> szemből messzebbről is elér; hátulról csak közelebbről. Ha a lock elvész (a cél 90°-ra fordul – ez a notch), nyomd meg újra a " .. k("T") .. "-t.",
	}, task = "Lődd le a drónt AIM-120-szal.",
		setup = function(t) t:drone({ dist = 22000, heading = "toward" }) end,
		check = function(t) return t:killed() end, status = function(t) return t:droneStatus() end })
	add_({ title = "AIM-9 – hőkövető rakéta közelről", paras = {
		"Egy drón repül előtted kb. 3 km-re, teljes gázzal – jó meleg cél.",
		"<b>Mit:</b> az AIM-9M Sidewinder a gép hőjét követi („Fox 2”). Nem kell hozzá radar, de rövid a hatótávja: hátulról 1–8 km, szemből csak 3–4 km.",
		"<b>Hogyan:</b>  1. Nyomd meg az " .. k("1") .. "-et. Megjelenik egy nagy kör – a rakéta keresője.  2. Vidd a célt a körbe: ha hőt lát, magától lockol. Az " .. k("F") .. " azonnal lockol bármelyik ellenségre az orrod előtt ±30°-on belül.  3. " .. k("Space") .. " = indítás.",
		"<b>Mikor:</b> a cél mögül, főleg ha utánégetővel repül. Ha a cél flare-t szór, várj egy pillanatot és lockolj újra. 400 m-en belül már túl közel van – oda az ágyú való.",
	}, task = "Lődd le a drónt AIM-9-cel.",
		setup = function(t) t:drone({ dist = 3000, heading = "away", throttle = 0.85, speed = 190, maxDist = 10000 }) end,
		check = function(t) return t:killed() end, status = function(t) return t:droneStatus() end })
	add_({ title = "Gépágyú", paras = {
		"Most egy lassabb, kicsit kanyargó drón van előtted kb. 900 m-re.",
		"<b>Mit:</b> a " .. gun.name .. " gépágyú 1 km-en belül hatásos, " .. gun.ammo .. " lőszerrel (kb. " .. math.floor(gun.ammo / 100 + 0.5) .. " másodpercnyi tűz).",
		"<b>Hogyan:</b>  1. Lockold a célt radarral (" .. k("T") .. "). Megjelenik az előretartás-jelző: fehér kör ponttal – ide érnek a golyók.  2. Tedd a fehér célzókört erre a jelre, és tüzelj a <b>bal egérgombbal</b>, rövid sorozatokkal.",
		"<b>Mikor:</b> ha a cél közel van és előtted, vagy ha elfogytak a rakéták. 1,5 km-nél messzebbről ne lőj.",
	}, task = "Lődd le a drónt.",
		setup = function(t) t:drone({ dist = 900, heading = "away", speed = 170, throttle = 0.7, weave = 0.2, maxDist = 6000, hp = 40 }) end,
		check = function(t) return t:killed() end, status = function(t) return t:droneStatus() end })
	add_({ title = "Védekezés: rád lőttek!", paras = {
		"Pár másodperc múlva egy ellenség rakétát indít rád kb. 9 km-ről, oldalról. A gyakorlásban nem sebez, de jelezzük, ha eltalált volna.",
		"<b>Mit jelez a gép:</b> az RWR-en (bal lent) piros villogó jel, gyorsuló sípolás, középen <b>MISSILE!</b>, a rakétán piros rombusz a távolsággal és a becsapódásig hátralévő idővel.",
		"<b>Hogyan védekezz:</b>  1. Fordulj úgy, hogy a rakéta oldalt (3 vagy 9 órában) legyen – ez a <b>notch</b>: a radar nem lát jól.  2. Közben tartsd nyomva az " .. k("X") .. "-et: chaff (radar ellen) és flare (hőkövető ellen).  3. Az utolsó 2–3 másodpercben húzz egy éles fordulót – a rakéta nem tud ilyen élesen fordulni.  4. Hőkövető ellen vedd vissza az utánégetőt.",
		"<b>Mikor:</b> azonnal, amint megjelenik a MISSILE!. Egyenesen előre ne menekülj – a rakéta gyorsabb.",
	}, task = "Éld túl a rakétát (ne találjon el).",
		setup = function(t) t.flags.fireIn, t.flags.missile, t.flags.hit, t.flags.tries = 3, nil, false, 0 end,
		check = function(t, dt) return t:missileDrill(dt) end, status = function(t) return t:missileStatus() end })
	if spec.id == "f22" then
		add_({ title = "A Raptor: lopakodás és belső fegyvertér", paras = {
			"<b>Lopakodó:</b> az F-22 radarkeresztmetszete apró, ezért az ellenség radarja csak kb. 10–15 km-ről lát meg (téged akár 100 km-ről is). Az APG-77 radarod „csendes” (LPI).",
			"<b>Belső fegyvertér:</b> 6 AIM-120 a hasban, 1–1 AIM-9 az oldalsó terekben. " .. k("Space") .. "-re előbb kinyílik az ajtó, a kar kitolja a rakétát, aztán minden visszacsukódik – kb. 0,7 s késéssel indul a rakéta. Amíg az ajtó nyitva van, a géped jól látszik a radaron.",
			"<b>Tolóerő-vektorálás:</b> mindig be van kapcsolva (nem kell Tab), a gép max 8 G-t húz.",
		}, task = "Indíts egy rakétát (" .. k("Space") .. "), és nézd meg, ahogy kinyílik a fegyvertér.",
			setup = function(t) t.flags.launched = false end,
			check = function(t)
				for _, st in ipairs(t.player.stations) do if st.launch and st.launch.t > 1.0 then return true end end
				return t.flags.launched
			end,
			status = function(t) return t.player.bayOpenAny > 0.05 and "Fegyvertér nyitva!" or ("Fegyver: " .. (t.player.selected or "-")) end })
	elseif spec.id == "f15" then
		add_({ title = "Az Eagle erőssége: tolóerő és 9 G", paras = {
			"<b>Mit:</b> az F-15EX-ben két F110 hajtómű van, és nagy szárnya: nagy tolóerővel és 9 G-vel fordul. Akár 12 rakétát is vihet (a menüben).",
			"<b>Hogyan:</b> tartsd az utánégetőt és a 650–850 km/h-s sebességet, és húzz élesen. A nagy tolóerő miatt sokáig bírja a nagy G-t – ez az energiaharc.",
			"<b>Mikor:</b> hosszú fordulós harcban a gyengébb ellenfeleket is kifordítod. A nagy légfék (" .. k("B") .. ") gyorsan lelassít, ha túlrepülnéd a célt.",
		}, task = "Húzz legalább 8 G-t.",
			setup = function(t) t.flags.g = 1 end,
			check = function(t) t.flags.g = max(t.flags.g, t.player.fm.gLoad); return t.flags.g >= 8 end,
			status = function(t) return "Legnagyobb eddig: " .. fixs(t.flags.g) .. " G · " .. math.floor(t.player.fm.ias * 3.6 + 0.5) .. " km/h" end })
	elseif f16 then
		add_({ title = "Extrém mód: tolóerő-vektorálás és Cobra (F-16)", paras = {
			"Csak az F-16-on van (mint a kísérleti F-16 MATV-n): a fúvócső ±20°-ot fordul.",
			"<b>Mit ad:</b> 9 G-s fordulók, 32°-os állásszög, gyorsabb orsózás, kis sebességen is irányítható. Cserébe többet fogyaszt.",
			"<b>Cobra:</b> teljes húzásra a gép felágaskodik (80° állásszögig), és egy pillanat alatt rengeteg sebességet veszít. Ha egy rakéta <b>3–4 másodpercen belül</b> van tőled, amikor ezt csinálod, nagy eséllyel elveszít és elrepül melletted.",
			"<b>Hogyan:</b> " .. k("Tab") .. " = extrém mód be / ki. Cobra: 600 km/h alatt tartsd nyomva az " .. k("S") .. "-t (kabinban: bot teljesen hátra) kb. 1 másodpercig, engedd el, adj AB-t, és engedd le az orrot.",
		}, task = "Kapcsold be az extrém módot (" .. k("Tab") .. "), és csinálj egy Cobrát (állásszög 50° fölött).",
			check = function(t) return t.player.extreme and t.player.fm.alpha > 50 * DEG end,
			status = function(t) return t.player.extreme and ("Extrém mód BE · " .. math.floor(t.player.fm.ias * 3.6 + 0.5) .. " km/h · AoA " .. math.floor(t.player.fm.alpha / DEG + 0.5) .. "°") or "Nyomd meg a Tab-ot" end })
	else
		add_({ title = "A Super Hornet erőssége: nagy állásszög", paras = {
			"<b>Mit:</b> a Hornet nagy szárnya és a törzs melletti LEX miatt 40°-os állásszögig is irányítható: lassan is oda tudja fordítani az orrát, ahová kell.",
			"<b>Hogyan:</b> lassíts 450 km/h alá, aztán húzz teljes erővel (" .. k("S") .. " vagy egér messze felfelé).",
			"<b>Mikor:</b> csak röviden! Nagy állásszögben gyorsan fogy a sebesség.",
		}, task = "Érj el 30° fölötti állásszöget.",
			check = function(t) return t.player.fm.alpha > 30 * DEG end,
			status = function(t) return math.floor(t.player.fm.ias * 3.6 + 0.5) .. " km/h · AoA " .. math.floor(t.player.fm.alpha / DEG + 0.5) .. "°" end })
	end
	add_({ title = "Harci zóna, bázis, leszállás", read = true, paras = {
		"A játékban a harc a térkép túloldalán, a <b>harci zónában</b> van: a HUD-on borostyán rombusz mutatja az irányt és a távolságot. A bázis körüli 14 km-es körben senki nem támad – ott nyugodtan fel- és leszállhatsz.",
		"<b>Hullámok:</b> felszállás után kb. 25 másodperccel jön az első hullám a zónába, minden hullám eggyel több ellenséget hoz. Az ellenség csak közelről lő, te sokkal messzebbről lockolhatsz és lőhetsz.",
		"<b>Leszállás:</b> futómű ki (" .. k("G") .. "), kb. 270 km/h, lassú süllyedés (4 m/s alatt), vízszintes szárnyak; a földön " .. k("B") .. " fékez. A bázis betonján lelassulva újratölt, tankol és javít. Arkád módban a rakéták 10 másodperc alatt maguktól visszatöltődnek.",
		"<b>Tipp:</b> messziről AIM-120 (" .. k("T") .. " + " .. k("Space") .. "), közelről AIM-9 vagy ágyú, és mindig figyeld az RWR-t. Jó repülést!",
	}, task = k("Enter") .. " = az oktatás vége, vissza a főmenübe." })
	return L
end

local Tut = {}
Tut.__index = Tut
-- match: the Match (player, world, terrain, hud, opts); cam: a table with .cockpit and .panelLook that the game keeps up to date
function T.new(match, cam)
	local self = setmetatable({}, Tut)
	self.match, self.cam = match, cam or { cockpit = false, panelLook = false }
	self.spawned, self.deadTime, self.renderTime = {}, 0, 0
	self.steps = lessons(match.player.spec)
	self.statusText = ""
	self.version = 0                  -- changes whenever the card must be redrawn
	self:start(1)
	return self
end
function Tut:playerNow() return self.match.player end
-- (the lessons read t.player)
setmetatable(Tut, { __index = nil })
Tut.__index = function(t, key)
	if key == "player" then return t.match.player end
	if key == "step" then return t.steps[t.i] end
	return Tut[key]
end

function Tut:start(i)
	local w = self.match.world
	local keep = {}
	for _, a in ipairs(w.aircraft) do
		local drop = false
		for _, s in ipairs(self.spawned) do if s == a then drop = true end end
		if not drop then keep[#keep + 1] = a end
	end
	w.aircraft = keep
	local mk = {}
	for _, m in ipairs(w.missiles) do
		local drop = false
		for _, s in ipairs(self.spawned) do if s == m.shooter then drop = true end end
		if not drop then mk[#mk + 1] = m end
	end
	w.missiles = mk
	self.spawned = {}
	self.i, self.done, self.doneTime, self.flags = i, false, 0, {}
	local p = self.player
	p.invulnerable = true
	-- the lessons need both missile types on the jet
	local has9, has120 = false, false
	for _, s in ipairs(p.stations) do
		if s.key == "AIM-9M" then has9 = true end
		if s.key == "AIM-120A" then has120 = true end
	end
	if not has9 or not has120 then
		p.loadout = "default"
		p:rearm()
	end
	local st = self.steps[i]
	if st.setup then st.setup(self) end
	self.version = self.version + 1
end
function Tut:next()
	if self.i < #self.steps then self:start(self.i + 1) else self:finish() end
end
function Tut:enter() self:next() end
function Tut:finish()
	local w = self.match.world
	local keep = {}
	for _, a in ipairs(w.aircraft) do
		local drop = false
		for _, s in ipairs(self.spawned) do if s == a then drop = true end end
		if not drop then keep[#keep + 1] = a end
	end
	w.aircraft = keep
	self.player.invulnerable = false
	self.finished = true
	self.match.tutorial = nil
	if self.match.env.onTutorialEnd then self.match.env.onTutorialEnd() end
end

-- ------------------------------------------------------------------ helpers
function Tut:drone(o)
	local dist, heading, speed, throttle, weave, side, maxDist, hp = o.dist, o.heading or "away", o.speed or 220, o.throttle or 0.9, o.weave or 0, o.side or 0, o.maxDist or 45000, o.hp
	local p, m = self.player, self.match
	local fwd = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0))
	local right = V(fwd.y, -fwd.x, 0)
	local pos = add(add(p.pos, mul(fwd, dist)), mul(right, side))
	pos.z = max(p.pos.z, m.terrain:height(pos.x, pos.y) + 1200)
	local hdgP = atan2(fwd.x, fwd.y)
	local h = heading == "toward" and hdgP + math.pi or hdgP
	local spec = Specs.BANDITS[(m.opts.enemyType == "fa18") and "fa18" or "f16"]
	local ac = Sim.newAircraft(spec, "Céldrón", "red", pos, h / DEG, speed, { missiles = Specs.BANDIT_MISSILES, rnd = M.rng(7) })
	for _, s in ipairs(ac.stations) do s.loaded = false end
	ac:updateStores()
	if hp then ac.hp = hp end
	newDrone(ac, h, weave, throttle)
	m.world:addAircraft(ac)
	self.spawned[#self.spawned + 1] = ac
	self.flags.drone, self.flags.maxDist = ac, maxDist
	return ac
end
function Tut:killed()
	local d = self.flags.drone
	if d and not d.alive and d.lastAttacker == self.player then self.flags.kill = true end
	if self.flags.kill then return true end
	-- flew away, or went down without your shot (a hill): a new one
	if d and (len(sub(d.pos, self.player.pos)) > self.flags.maxDist or not d.alive) then
		local keep = {}
		for _, a in ipairs(self.match.world.aircraft) do if a ~= d then keep[#keep + 1] = a end end
		self.match.world.aircraft = keep
		self.match.hud:message("A drón elment – itt egy új előtted", "info", 3)
		self.steps[self.i].setup(self)
	end
	return false
end
function Tut:droneStatus()
	local d = self.flags.drone
	if not d or not d.alive then return "Találat!" end
	local dist = len(sub(d.pos, self.player.pos)) / 1000
	local locked = self.player.radar.locked == d
	return "Drón: " .. fixs(dist) .. " km · " .. (locked and "radar lock OK" or "nincs radar lock") .. " · fegyver: " .. (self.player.selected or "-")
end
function Tut:missileDrill(dt)
	local f, p, m = self.flags, self.player, self.match
	if not f.missile then
		f.fireIn = f.fireIn - dt
		if f.fireIn > 0 then return false end
		-- a bandit appears 7 km out behind on the right and fires one (weak) AIM-120 at once, aimed ahead of you
		local ac = self:drone({ dist = -5000, side = 5000, heading = "away", speed = 260 })
		local rel = sub(p.pos, ac.pos)
		local mis = Weapons.newMissile(Specs.BANDIT_MISSILES["AIM-120A"], ac, ac.pos, ac.vel, norm(rel), ac.rnd, p)
		mis.estVel = copy(p.vel)
		m.world:addMissile(mis)
		f.missile, f.hit = mis, false
		f.tries = f.tries + 1
		return false
	end
	local mis = f.missile
	if mis.alive then
		-- gone past you and flying away, or lost you: that counts as beaten
		local rel = sub(p.pos, mis.pos)
		local closing = (mis.vel.x * rel.x + mis.vel.y * rel.y + mis.vel.z * rel.z) / max(len(rel), 1)
		if (closing < 0 and len(rel) > 1500) or mis.defeated then mis.alive = false else return false end
	end
	if f.hit then                                   -- it would have hit: one more try
		m.hud:message("ELTALÁLT VOLNA – próbáld újra: fordulj oldalra, X, és az utolsó pillanatban éles forduló", "warn", 5)
		f.missile, f.fireIn = nil, 4
		return false
	end
	return true
end
function Tut:missileStatus()
	local f = self.flags
	if not f.missile then return f.tries > 0 and "Új rakéta jön..." or ("Rakéta indul " .. max(0, math.ceil(f.fireIn)) .. " s múlva") end
	local d = len(sub(f.missile.pos, self.player.pos)) / 1000
	return "RAKÉTA: " .. fixs(d) .. " km · " .. tostring(f.missile.status)
end

-- ------------------------------------------------------------------ frame
function Tut:update(dt)
	local p = self.player
	if not p.alive then                              -- crashed: back in the air, same lesson again
		self.deadTime = self.deadTime + dt
		if self.deadTime > 2 then
			self.deadTime = 0
			self.match.state.banner, self.match.state.subBanner = "", ""
			self.match:spawnPlayer()
			self:start(self.i)
		end
		return
	end
	local s = self.steps[self.i]
	if not self.done and s.check and s.check(self, dt) then
		self.done = true
		self.version = self.version + 1
	end
	if self.done then
		self.doneTime = self.doneTime + dt
		if self.doneTime > 2.5 then self:next(); return end
	end
	self.renderTime = self.renderTime + dt
	if self.renderTime > 0.25 then
		self.renderTime = 0
		local ok, txt = pcall(function() return (not self.done and s.status) and s.status(self) or "" end)
		self.statusText = ok and txt or ""
	end
end
function Tut:onEvent(kind, d)
	if kind == "shielded" and d.target == self.player then self.flags.hit = true end
	if kind == "kill" and d.killer == self.player and d.victim == self.flags.drone then self.flags.kill = d.weapon end
end

-- what the card shows
function Tut:view()
	local s = self.steps[self.i]
	return { i = self.i, n = #self.steps, title = s.title, body = table.concat(s.paras, "\n\n"), task = s.task, done = self.done, status = self.statusText,
		read = s.read == true, version = self.version }
end

return T
