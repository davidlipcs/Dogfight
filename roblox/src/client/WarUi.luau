--!nonstrict
-- The war career on the screen: the operations room (the air forces of the four powers, the fronts, the log), the briefing of the
-- mission, the report after it, the politics and the end of the war.  The game logic is shared/game/Campaign.luau (the port of
-- web/js/campaign.js); the sortie itself is a Match of scenario "mission" (shared/game/Mission.luau).  The war and the pilot are saved on
-- the server (SaveWar) and come back with the profile.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Campaign = require(Shared.game.Campaign)
local Specs = require(Shared.sim.Specs)
local Ui = require(script.Parent.Ui)

local C = Campaign
local POWERS, FRONTS = C.POWERS, C.FRONTS

local WarUi = {}

local gui, body, eyebrow
local remotes, hooks
local S = { war = nil, pilot = nil }            -- the war and the pilot (the saved state)
local open = false
local note = ""                                  -- a line of feedback under the buttons

local TODS = { { "day", "nappal" }, { "overcast", "borult" }, { "sunset", "naplemente" }, { "night", "éjszaka" } }
local JETS = { "f16", "fa18", "f35", "f15", "f22" }

local function colour(id) local c = POWERS[id].colour return Color3.fromRGB(c[1], c[2], c[3]) end

local function persist()
	if not S.war or not S.pilot then return end
	while #S.war.log > 40 do table.remove(S.war.log) end
	if remotes and remotes.SaveWar then remotes.SaveWar:FireServer({ war = S.war, pilot = S.pilot }) end
end

-- ------------------------------------------------------------------ building blocks
local function clear()
	for _, c in body:GetChildren() do
		if c:IsA("GuiObject") then c:Destroy() end
	end
end

local order = 0
local function nextOrder() order += 1 return order end

local function heading(text, size)
	return Ui.label(body, text, { Size = UDim2.new(1, 0, 0, (size or 24) + 8), TextSize = size or 24, Font = Enum.Font.GothamBold, TextColor3 = Ui.Green, LayoutOrder = nextOrder() })
end

local function para(text, props)
	local l = Ui.label(body, text, { Size = UDim2.new(1, 0, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, TextWrapped = true, RichText = true, TextSize = 15,
		TextYAlignment = Enum.TextYAlignment.Top, LayoutOrder = nextOrder() })
	for k, v in props or {} do l[k] = v end
	return l
end

local function row()
	local r = Ui.make("Frame", { Size = UDim2.new(1, 0, 0, 36), BackgroundTransparency = 1, LayoutOrder = nextOrder(), Parent = body },
		{ Ui.make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 8), SortOrder = Enum.SortOrder.LayoutOrder, VerticalAlignment = Enum.VerticalAlignment.Center }) })
	return r
end

local function button(parent, text, onClick, props)
	local b = Ui.button(parent, text, { Size = UDim2.new(0, 190, 0, 34), TextSize = 14 })
	for k, v in props or {} do b[k] = v end
	b.AutomaticSize = Enum.AutomaticSize.X
	local pad = Ui.make("UIPadding", { PaddingLeft = UDim.new(0, 12), PaddingRight = UDim.new(0, 12) })
	pad.Parent = b
	if onClick then b.Activated:Connect(onClick) end
	return b
end

local function chips(parent, items, current, set)
	for _, it in ipairs(items) do
		local on = it[1] == current
		button(parent, it[2], function() set(it[1]) end, {
			BackgroundColor3 = on and Ui.Amber or Color3.fromRGB(46, 62, 68), TextColor3 = on and Color3.fromRGB(16, 22, 20) or Color3.fromRGB(225, 235, 230) })
	end
end

local function bar(parent, frac, color)
	local back = Ui.make("Frame", { Size = UDim2.new(1, 0, 0, 8), BackgroundColor3 = Color3.fromRGB(34, 44, 48), BorderSizePixel = 0, Parent = parent }, { Ui.corner(4) })
	Ui.make("Frame", { Size = UDim2.new(math.clamp(frac, 0, 1), 0, 1, 0), BackgroundColor3 = color, BorderSizePixel = 0, Parent = back }, { Ui.corner(4) })
	return back
end

local function frame(eyebrowText)
	clear()
	order = 0
	eyebrow.Text = eyebrowText or "Karrier"
end

local function noteLine()
	if note ~= "" then para(note, { TextColor3 = Ui.Amber }) end
end

local screens = {}

-- ------------------------------------------------------------------ the war room
local function fleetBox(parent, id)
	local w, me = S.war, S.war.player
	local seen = C.seenFleet(w, id)
	local fleet, exact = seen.fleet, seen.exact
	local total, start = C.totalFleet(fleet), w.powers[id].start
	local box = Ui.make("Frame", { Size = UDim2.new(1, 0, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, BackgroundColor3 = Ui.Panel, BorderSizePixel = 0, LayoutOrder = nextOrder(), Parent = parent },
		{ Ui.corner(8), Ui.padding(8), Ui.make("UIListLayout", { Padding = UDim.new(0, 3), SortOrder = Enum.SortOrder.LayoutOrder }),
			Ui.make("UIStroke", { Color = colour(id), Thickness = 2 }) })
	local n = 0
	local function line(text, props)
		n += 1
		local l = Ui.label(box, text, { Size = UDim2.new(1, 0, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, TextWrapped = true, RichText = true, TextSize = 13, LayoutOrder = n })
		for k, v in props or {} do l[k] = v end
		return l
	end
	line(POWERS[id].name .. (w.powers[id].out and " – KIESETT" or ""), { TextSize = 16, Font = Enum.Font.GothamBold, TextColor3 = colour(id) })
	line((exact and "" or "≈") .. total .. " vadászgép" .. (exact and "" or " (becslés)") .. " · " .. math.floor(total / start * 100 + 0.5) .. "%")
	n += 1
	local b = bar(box, total / start, colour(id))
	b.LayoutOrder = n
	if id == me then
		local bu = C.budgetOf(w, id)
		line(string.format("💰 költségvetés: <b>%d M$</b> · +%s M$/nap · a pénz havi ~<b>%s</b> új gépre elég (a gyárak legfeljebb %s-ot tudnának)", bu.money, tostring(bu.income), tostring(bu.perMonth), tostring(bu.capacity)),
			{ TextColor3 = Color3.fromRGB(190, 205, 198) })
	end
	local parts = {}
	for _, k in ipairs(C.sortedKeys(fleet)) do parts[#parts + 1] = string.upper(k) .. " " .. (exact and "" or "~") .. fleet[k] end
	line(table.concat(parts, " · "), { TextColor3 = Color3.fromRGB(160, 180, 172) })
	if id ~= me then
		local st = C.alliedWith(w, me, id) and "<b>SZÖVETSÉGES</b>" or (C.atWar(w, me, id) and "háborúban" or "tűzszünet")
		line(string.format("bizalom: %d · %s", math.floor(C.trustOf(w, me, id) + 0.5), st), { TextColor3 = Color3.fromRGB(160, 180, 172) })
	end
end

function screens.warRoom()
	local w, p = S.war, S.pilot
	if w.over then screens.warEnd() return end
	local me = w.player
	local rank = p.rank or 0
	local fronts = {}
	for _, f in ipairs(FRONTS) do
		local onIt = false
		for _, s in ipairs(f.sides) do if s == me then onIt = true end end
		if onIt and #C.frontEnemies(w, f.id) > 0 then fronts[#fronts + 1] = f end
	end
	local assigned = p.assigned
	local found = false
	for _, f in ipairs(fronts) do if f.id == assigned then found = true end end
	if not found then assigned = fronts[1] and fronts[(math.floor(w.day / 3) % math.max(1, #fronts)) + 1].id or nil end
	p.assigned = assigned
	local canChoose = rank >= 3

	frame("Karrier · hadműveleti központ")
	heading(string.format("%d. nap · %s %s „%s”", w.day, C.RANKS[rank + 1], p.name, p.callsign))
	para(string.format("Bevetések: %d · lelövések: %d · kitüntetések: %d%s", p.sorties, p.kills, #p.awards, #p.awards > 0 and (" (" .. table.concat(p.awards, ", ") .. ")") or ""),
		{ TextColor3 = Color3.fromRGB(170, 190, 185), TextSize = 13 })
	para(canChoose and "Őrnagyként te választod a frontot." or "A parancs: " .. (assigned and C.front(assigned).name or "-") .. ". (Őrnagytól te választhatsz.)", { TextColor3 = Color3.fromRGB(170, 190, 185), TextSize = 13 })
	for _, f in ipairs(fronts) do
		local r = row()
		r.Size = UDim2.new(1, 0, 0, 46)
		local names = {}
		for _, e in ipairs(C.frontEnemies(w, f.id)) do names[#names + 1] = POWERS[e].short end
		local sel = f.id == assigned
		button(r, string.format("%s  –  ellenség: %s · hevesség %d%%", f.name, table.concat(names, ", "), math.floor(w.fronts[f.id].heat * 100 + 0.5)), function()
			if canChoose then p.assigned, p.order = f.id, nil; persist(); screens.warRoom() end
		end, { Size = UDim2.new(1, 0, 0, 42), AutomaticSize = Enum.AutomaticSize.None, TextSize = 14, TextXAlignment = Enum.TextXAlignment.Left,
			BackgroundColor3 = sel and Ui.Amber or Color3.fromRGB(46, 62, 68), TextColor3 = sel and Color3.fromRGB(16, 22, 20) or Color3.fromRGB(225, 235, 230), Active = canChoose or sel })
	end
	local r = row()
	if assigned then button(r, "📋 Parancs és eligazítás", function() screens.briefing(assigned) end, { BackgroundColor3 = Ui.Green }) end
	if rank >= 4 and assigned then button(r, "MI-kötelék kiküldése", function() screens.quick(assigned) end) end
	if rank >= 5 then button(r, "Politika", function() screens.politics() end) end
	button(r, "Egy nap pihenő", function() C.passDays(w, 1); persist(); note = ""; screens.warRoom() end, { BackgroundColor3 = Color3.fromRGB(70, 86, 92), TextColor3 = Color3.new(1, 1, 1) })
	noteLine()
	heading("Légierők", 18)
	for _, id in ipairs(C.POWER_IDS) do fleetBox(body, id) end
	heading("Napló", 18)
	if #w.log == 0 then para("még üres", { TextColor3 = Color3.fromRGB(150, 170, 165) }) end
	for i = 1, math.min(12, #w.log) do para(string.format("<b>%d.</b> %s", w.log[i].day, w.log[i].text), { TextSize = 13 }) end
	local r2 = row()
	button(r2, "Új karrier", function() S.war, S.pilot = nil, nil; persist(); screens.start() end, { BackgroundColor3 = Color3.fromRGB(200, 120, 110) })
end

-- ------------------------------------------------------------------ briefing
function screens.briefing(frontId)
	local w, p = S.war, S.pilot
	local rank = p.rank or 0
	if not p.order or p.order.front ~= frontId then p.order = C.makeOrder(w, p, frontId); persist() end
	local o = p.order
	local f = C.front(frontId)
	local redTypes, seen = {}, {}
	for _, r in ipairs(o.red) do
		if not seen[r.type] then seen[r.type] = true; redTypes[#redTypes + 1] = string.upper(r.type) end
	end
	frame("Karrier · eligazítás")
	heading("Parancs")
	para(string.format("<b>%s</b> – %s", f.name, f.why))
	local todName = "nappal"
	for _, t in ipairs(TODS) do if t[1] == o.tod then todName = t[2] end end
	para(string.format("Feladat: <b>%s</b> · ellenség: <b>%d gép</b> (%s: ~%s) · %s · saját oldal: %d szövetséges gép · te: <b>%s</b>", C.KINDS[o.kind], #o.red, POWERS[o.foe].short,
		table.concat(redTypes, ", "), todName, #o.blue, o.role == "wing" and "a vezér 2-ese" or "kötelékvezető (MI-kísérővel)"))
	para("Rádió: <b>I</b> billentyű. A bevetés a levegőben kezdődik, úton a harci zóna felé; ha vége, Enter = jelentés.", { TextColor3 = Color3.fromRGB(170, 190, 185), TextSize = 13 })
	if rank >= 2 then
		para("Feladat:", { TextSize = 14 })
		local r = row()
		local kinds = {}
		for _, k in ipairs({ "sweep", "cap" }) do kinds[#kinds + 1] = { k, C.KINDS[k] } end
		chips(r, kinds, o.kind, function(v) o.kind = v; persist(); screens.briefing(frontId) end)
		para("Időpont:", { TextSize = 14 })
		local r2 = row()
		chips(r2, TODS, o.tod, function(v) o.tod = v; persist(); screens.briefing(frontId) end)
	end
	if rank >= 3 then
		para("Gép:", { TextSize = 14 })
		local r3 = row()
		local jets = {}
		for _, k in ipairs(JETS) do
			if (w.powers[w.player].fleet[k] or 0) > 0 and Specs.AIRCRAFT[k] then jets[#jets + 1] = { k, string.upper(k) .. " (" .. w.powers[w.player].fleet[k] .. ")" } end
		end
		chips(r3, jets, o.jet, function(v) o.jet = v; p.jet = v; persist(); screens.briefing(frontId) end)
	else
		para("Géped: <b>" .. string.upper(o.jet) .. "</b>. Századostól választhatod a feladatot és az időpontot, őrnagytól a frontot és a gépet.", { TextColor3 = Color3.fromRGB(170, 190, 185), TextSize = 13 })
	end
	local r4 = row()
	button(r4, "▶ Indulás a bevetésre", function() screens.fly(o) end, { BackgroundColor3 = Ui.Green })
	button(r4, "Vissza", function() screens.warRoom() end, { BackgroundColor3 = Color3.fromRGB(70, 86, 92), TextColor3 = Color3.new(1, 1, 1) })
end

function screens.fly(o)
	local w, p = S.war, S.pilot
	local m = C.missionOf(w, p, o)
	S.flying = m
	local spec = Specs.AIRCRAFT[o.jet] or Specs.AIRCRAFT.f16
	local layout = Specs.buildLoadout(spec, 2, 4).layout
	if hooks and hooks.onFly then
		hooks.onFly({ mission = m, scenario = "mission", airStart = true, aircraft = o.jet, wingman = o.role == "lead" and 1 or 0, difficulty = o.skill, enemies = 0,
			mode = "arcade", tod = o.tod, loadout = layout, enemyTypes = { "f16" }, callsign = m.callsign })
	end
end

-- ------------------------------------------------------------------ after the mission
-- r: the result of Mission.luau, m: the mission table.  Called by Main.client when the sortie is over
function WarUi.afterMission(r, m)
	if not S.war or not S.pilot or not m then return end
	local w, p = S.war, S.pilot
	S.flying = nil
	p.order = nil
	local res = C.afterMission(w, p, m, r)
	persist()
	open = true
	gui.Enabled = true
	frame("Karrier · jelentés")
	heading(r.won and "KÜLDETÉS TELJESÍTVE" or (r.status == "ejected" and "Katapultáltál" or r.status == "shot_down" and "Lelőttek" or "Küldetés vége"))
	para(string.format("<b>%s</b>\nlelövéseid: <b>%d</b> · ellenséges gép elveszett: <b>%d</b> · saját gép elveszett: <b>%d</b> · idő: %d:%02d", m.title, r.kills or 0, #(r.redLost or {}),
		#(r.blueLost or {}), math.floor(r.time / 60), math.floor(r.time % 60)))
	for _, l in ipairs(res.lines) do para("🎖 " .. l, { TextColor3 = Ui.Amber }) end
	para(string.format("A háború a %d. napnál tart.", w.day), { TextColor3 = Color3.fromRGB(170, 190, 185), TextSize = 13 })
	local row1 = row()
	button(row1, "Vissza a központba", function() screens.warRoom() end, { BackgroundColor3 = Ui.Green })
	if hooks and hooks.onShown then hooks.onShown() end
end

-- a flight of AI pilots (rank 4+)
function screens.quick(frontId)
	local w = S.war
	frame("Karrier · MI-kötelék")
	heading("MI-kötelék kiküldése: " .. C.front(frontId).name)
	para("A kötelék magától repül: a gépek száma és az ellenség minősége dönt. Minél több gépet küldesz, annál nagyobb a siker – és a veszteség.")
	local r = row()
	for _, n in ipairs({ 2, 4, 6, 8 }) do
		button(r, n .. " gép", function()
			local res = C.sendFlight(w, frontId, n)
			persist()
			frame("Karrier · jelentés")
			heading("Jelentés – " .. C.front(frontId).name)
			para(string.format("%d gépünk %d %s vadász ellen: <b>%d</b> ellenséges és <b>%d</b> saját gép veszett oda. %s", res.mine, res.reds, POWERS[res.foe].short, res.redLost, res.blueLost,
				res.won and "Győzelem." or "Nem sikerült."))
			local r2 = row()
			button(r2, "Vissza a központba", function() screens.warRoom() end, { BackgroundColor3 = Ui.Green })
		end)
	end
	local r3 = row()
	button(r3, "Vissza", function() screens.warRoom() end, { BackgroundColor3 = Color3.fromRGB(70, 86, 92), TextColor3 = Color3.new(1, 1, 1) })
end

-- ------------------------------------------------------------------ politics (colonel and above)
function screens.politics()
	local w = S.war
	local me = w.player
	frame("Karrier · politika")
	heading("Politika és stratégia")
	para("Ezredesként már te is ott ülsz, ahol a döntések születnek. A szövetséghez legalább 60-as bizalom kell. Az országok a bizalom szerint döntenek: szövetséget bontanak, tűzszünetet mondanak fel, gyárat bombáznak, segítenek egymásnak.",
		{ TextColor3 = Color3.fromRGB(170, 190, 185), TextSize = 13 })
	noteLine()
	local function done(text) note = text; persist(); screens.politics() end
	if #w.offers > 0 then
		heading("Ajánlatok", 18)
		for i, o in ipairs(w.offers) do
			local r = row()
			Ui.label(r, string.format("%s: %s (%d. napja · bizalom %d)", POWERS[o.from].name, o.type == "alliance" and "szövetséget ajánl" or "tűzszünetet ajánl", w.day - o.day, math.floor(C.trustOf(w, me, o.from) + 0.5)),
				{ Size = UDim2.new(0, 360, 0, 30), TextSize = 14, TextWrapped = true })
			button(r, "Elfogadom", function() done(C.answerOffer(w, i, true).text) end, { BackgroundColor3 = Ui.Green })
			button(r, "Elutasítom", function() done(C.answerOffer(w, i, false).text) end)
		end
	end
	for _, id in ipairs(C.POWER_IDS) do
		if id ~= me and not w.powers[id].out then
			local st = C.alliedWith(w, me, id) and "SZÖVETSÉGES" or (C.atWar(w, me, id) and "háborúban" or "tűzszünet")
			para(string.format("<b>%s</b> – bizalom: %d · %s", POWERS[id].name, math.floor(C.trustOf(w, me, id) + 0.5), st), { TextColor3 = colour(id) })
			local r = row()
			if not C.alliedWith(w, me, id) then button(r, "Szövetség ajánlása", function() done(C.proposeAlliance(w, me, id).text) end) end
			if C.atWar(w, me, id) then
				button(r, "Tűzszünet", function() done(C.proposeCeasefire(w, me, id).text) end)
				button(r, "Csapás a repülőgépgyárakra", function()
					local cost = 4 + math.random(0, 5)
					local f = w.powers[me].fleet
					f.f15 = math.max(0, (f.f15 or 0) - math.min(cost, 2))
					f.f16 = math.max(0, (f.f16 or 0) - cost)
					C.applyMission(w, { strike = id, losses = {} })
					done(string.format("A csapás sikerült: %s gyártása visszaesett – %d gépünk nem tért vissza.", POWERS[id].name, cost))
				end)
			elseif not C.alliedWith(w, me, id) then
				button(r, "Segítség küldése (+bizalom)", function()
					C.changeTrust(w, me, id, 8, "segítséget küldtünk")
					w.powers[me].fleet.f16 = math.max(0, (w.powers[me].fleet.f16 or 0) - 6)
					done("6 F-16-ot átadtunk – nő a bizalom.")
				end)
			end
		end
	end
	heading("Gyártás és költségvetés", 18)
	local cur = w.policy.production and w.policy.production[me]
	para("A gyárak csak annyit építenek, amennyit a keret kifizet. Melyik gyártósor kapja a pénzt először? Most: <b>" .. (cur and string.upper(cur) or "egyenlően") .. "</b>", { TextSize = 13 })
	local r = row()
	for _, k in ipairs(C.sortedKeys(POWERS[me].production)) do
		button(r, string.format("%s · %d M$/db · max %s/hó", string.upper(k), C.COST[k], tostring(POWERS[me].production[k])), function()
			w.policy.production = w.policy.production or {}
			w.policy.production[me] = k
			done("")
		end)
	end
	local r2 = row()
	button(r2, "Vissza", function() note = ""; screens.warRoom() end, { BackgroundColor3 = Color3.fromRGB(70, 86, 92), TextColor3 = Color3.new(1, 1, 1) })
end

function screens.warEnd()
	local w, p = S.war, S.pilot
	local won = w.over.player
	if won then C.award(p, "Győzelem a 3. világháborúban") end
	frame("Karrier · a háború vége")
	heading(won and "GYŐZELEM" or "VERESÉG", 34)
	para(string.format("%d. nap. %s", w.over.day, won and "Az ellenség légiereje megsemmisült. Vége a háborúnak." or "A légierőnk elfogyott. A háború a mi vereségünkkel ért véget."))
	para(string.format("%s %s: %d bevetés, %d légi győzelem.", C.RANKS[(p.rank or 0) + 1], p.name, p.sorties, p.kills))
	if #p.awards > 0 then para(table.concat(p.awards, " · "), { TextColor3 = Ui.Amber, TextSize = 13 }) end
	local r = row()
	button(r, "Új háború", function()
		S.war = C.newWar("us", os.time())
		S.war.started = true
		persist()
		screens.warRoom()
	end, { BackgroundColor3 = Ui.Green })
	persist()
end

-- ------------------------------------------------------------------ the beginning
function screens.start()
	frame("Karrier · toborzóiroda")
	heading("Jelentkezés a háborúba")
	para("Kitört a harmadik világháború. Nincsenek szövetségek: az Egyesült Államok, Európa, Oroszország és Kína mind mindenki ellen áll – csak az európai légierők harcolnak együtt. A bizalmat ki kell érdemelni: ha közösen harcoltok, vagy segítesz, valaki talán mellénk áll.")
	para("Az nyer, akinek a végén még van légiereje. A saját gépszámodat pontosan látod, a többiekét csak becsüljük. Hadnagyként parancsot kapsz; ahogy emelkedsz a ranglétrán, egyre többről döntesz: feladat, front, gép, MI-kötelékek, végül a politika.")
	local r = row()
	Ui.label(r, "Neved:", { Size = UDim2.new(0, 70, 0, 30), TextSize = 15 })
	local nameBox = Ui.make("TextBox", { Size = UDim2.new(0, 220, 0, 30), BackgroundColor3 = Color3.fromRGB(26, 40, 46), TextColor3 = Color3.new(1, 1, 1), Text = Players.LocalPlayer.DisplayName,
		TextSize = 16, Font = Enum.Font.GothamMedium, ClearTextOnFocus = false, Parent = r }, { Ui.corner(6) })
	local r2 = row()
	Ui.label(r2, "Hívójel:", { Size = UDim2.new(0, 70, 0, 30), TextSize = 15 })
	local csBox = Ui.make("TextBox", { Size = UDim2.new(0, 220, 0, 30), BackgroundColor3 = Color3.fromRGB(26, 40, 46), TextColor3 = Color3.new(1, 1, 1), Text = "VIPER", TextSize = 16,
		Font = Enum.Font.GothamMedium, ClearTextOnFocus = false, Parent = r2 }, { Ui.corner(6) })
	local r3 = row()
	button(r3, "Aláírom ▶", function()
		local name = string.sub(nameBox.Text ~= "" and nameBox.Text or "Pilóta", 1, 24)
		local cs = string.upper(string.sub(csBox.Text ~= "" and csBox.Text or "VIPER", 1, 12))
		S.pilot = C.newPilot(name, cs)
		S.war = C.newWar("us", os.time())
		S.war.started = true
		persist()
		screens.warRoom()
	end, { BackgroundColor3 = Ui.Green })
end

-- ------------------------------------------------------------------ the module
function WarUi.init(r, h)
	remotes, hooks = r, h
	gui = Ui.make("ScreenGui", { Name = "DogfightWar", ResetOnSpawn = false, IgnoreGuiInset = true, DisplayOrder = 21, Enabled = false, Parent = Players.LocalPlayer:WaitForChild("PlayerGui") })
	local panel = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0.5, 0), Size = UDim2.new(0, 860, 0.92, 0), BackgroundColor3 = Color3.fromRGB(14, 20, 24), Parent = gui },
		{ Ui.corner(10), Ui.padding(14) })
	eyebrow = Ui.label(panel, "Karrier", { Size = UDim2.new(1, -120, 0, 22), TextSize = 14, TextColor3 = Color3.fromRGB(150, 170, 165) })
	Ui.button(panel, "✕ Bezár", { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, 0), Size = UDim2.new(0, 100, 0, 28), TextSize = 14 }, function() WarUi.show(false) end)
	body = Ui.make("ScrollingFrame", { Position = UDim2.new(0, 0, 0, 30), Size = UDim2.new(1, 0, 1, -30), BackgroundTransparency = 1, BorderSizePixel = 0, ScrollBarThickness = 8,
		CanvasSize = UDim2.new(0, 0, 0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y, Parent = panel },
		{ Ui.make("UIListLayout", { Padding = UDim.new(0, 8), SortOrder = Enum.SortOrder.LayoutOrder }) })
end

-- the saved state from the profile (profile.warSave = { war, pilot })
function WarUi.setProfile(p)
	local save = p and p.warSave
	if S.war then return end                     -- (what this machine has is newer than the server's copy)
	if typeof(save) == "table" and typeof(save.war) == "table" and typeof(save.pilot) == "table" then
		S.war, S.pilot = save.war, save.pilot
	end
end

function WarUi.show(v)
	open = v
	if not gui then return end
	gui.Enabled = v
	if v then
		note = ""
		S.flying = nil
		if S.war and S.pilot then screens.warRoom() else screens.start() end
	end
end

WarUi.screens = screens                      -- (the tests open every screen)

function WarUi.toggle() WarUi.show(not open) end

return WarUi
