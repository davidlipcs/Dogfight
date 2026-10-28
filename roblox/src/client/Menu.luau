--!nonstrict
-- The match options of the browser game's main menu (web/index.html #menu): mission, own plane, weapons, enemy types, mode, difficulty,
-- wingman, enemy count, mouse sensitivity, time of day.  build() makes the panel (a scrolling list of rows); opts() turns the choices
-- into the options table of Game.start.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Specs = require(Shared.sim.Specs)
local Ui = require(script.Parent.Ui)

local Menu = {}

local ALL = {}
for k, v in pairs(Specs.AIRCRAFT) do ALL[k] = v end
for k, v in pairs(Specs.TRAINERS) do ALL[k] = v end

Menu.state = {
	scen = "waves", plane = "f16", arms = {}, foes = { f16 = true }, mode = "arcade", diff = "normal", wing = 0, enemies = 2,
	aim = 60, stick = 60, invert = false, fov = 70, tod = "day", quality = "high",
}
local S = Menu.state

local SCENS = {
	{ "waves", "Hullámok" }, { "duel", "Párbaj 1v1" }, { "survival", "Túlélés" }, { "race", "Gyűrűverseny" }, { "canyon", "Kanyonfutam" },
	{ "tube", "Alagútfutam" }, { "free", "Közös repülés" },
}
local SCEN_HINT = {
	waves = "egyre nagyobb hullámok, a bázison újratölthetsz", duel = "1 ellenfél szemből - minden kör tele géppel, a levegőben indul",
	survival = "egy életed van, a hullámok gyorsan jönnek - meddig bírod?", race = "gyűrűk a völgyekben, idő ellen",
	canyon = "alacsony repülés a völgyben, célpont a végén, meredek kihúzás a gerincen át – 2:15 alatt",
	tube = "üvegrács-alagút úttal, 3 kör, a körök és a legjobb idő mérve", free = "szabad repülés ellenség nélkül",
}
local DIFF = { { "easy", "Könnyű" }, { "normal", "Normál" }, { "hard", "Nehéz" }, { "ace", "Ász" } }
local DIFF_HINT = { easy = "pont ×0,6", normal = "pont ×1", hard = "pont ×1,5", ace = "teljes erejű ellenfél · pont ×2" }
local TODS = { { "day", "Nappal" }, { "sunset", "Naplemente" }, { "overcast", "Borult" }, { "night", "Éjszaka" } }
local QUALITY = { { "low", "Gyors" }, { "medium", "Közepes" }, { "high", "Szép" } }

local refreshers = {}              -- functions that repaint the rows after a change
local function refresh() for _, f in ipairs(refreshers) do f() end end

local function row(parent, label, order)
	local r = Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(1, -8, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, LayoutOrder = order, Parent = parent })
	Ui.label(r, label, { Size = UDim2.new(0, 96, 0, 30), TextSize = 14, TextColor3 = Color3.fromRGB(150, 170, 165), Font = Enum.Font.GothamBold })
	local body = Ui.make("Frame", { BackgroundTransparency = 1, Position = UDim2.new(0, 100, 0, 0), Size = UDim2.new(1, -100, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, Parent = r },
		{ Ui.make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Wraps = true, Padding = UDim.new(0, 5), SortOrder = Enum.SortOrder.LayoutOrder }) })
	local hint = Ui.label(r, "", { Position = UDim2.new(0, 100, 0, 0), Size = UDim2.new(1, -100, 0, 18), TextSize = 12, TextColor3 = Color3.fromRGB(130, 150, 145), TextWrapped = true, Visible = false })
	return body, hint
end

-- a group of option buttons; get/set read and write the choice; multi: a set of choices
local function choice(parent, items, get, set, w)
	local btns = {}
	for i, it in ipairs(items) do
		local b = Ui.button(parent, it[2], { Size = UDim2.new(0, w or 96, 0, 28), TextSize = 13, LayoutOrder = i })
		btns[it[1]] = b
		b.Activated:Connect(function() set(it[1]); refresh() end)
	end
	table.insert(refreshers, function()
		for id, b in pairs(btns) do
			local on = get(id)
			b.BackgroundColor3 = on and Ui.Amber or Color3.fromRGB(46, 62, 68)
			b.TextColor3 = on and Color3.fromRGB(16, 22, 20) or Color3.fromRGB(225, 235, 230)
		end
	end)
end

local function stepper(parent, get, set, lo, hi, step, fmt, order)
	local box = Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(0, 190, 0, 28), LayoutOrder = order or 0, Parent = parent })
	local val = Ui.label(box, "", { Position = UDim2.new(0, 34, 0, 0), Size = UDim2.new(0, 120, 0, 28), TextXAlignment = Enum.TextXAlignment.Center, TextSize = 14 })
	Ui.button(box, "−", { Position = UDim2.new(0, 0, 0, 0), Size = UDim2.new(0, 30, 0, 28), TextSize = 18, BackgroundColor3 = Color3.fromRGB(46, 62, 68), TextColor3 = Color3.new(1, 1, 1) }, function()
		set(math.max(lo, get() - step)); refresh()
	end)
	Ui.button(box, "+", { Position = UDim2.new(0, 158, 0, 0), Size = UDim2.new(0, 30, 0, 28), TextSize = 18, BackgroundColor3 = Color3.fromRGB(46, 62, 68), TextColor3 = Color3.new(1, 1, 1) }, function()
		set(math.min(hi, get() + step)); refresh()
	end)
	table.insert(refreshers, function() val.Text = fmt(get()) end)
	return box
end

-- the loadout: how many AIM-9M and AIM-120A (the stations are filled like the real jet would carry them)
local function plane() return ALL[S.plane] or ALL.f16 end
local function defaults(spec)
	local n9, n120 = 0, 0
	for _, k in pairs(spec.loadouts.default) do
		if k == "AIM-9M" then n9 += 1 elseif k == "AIM-120A" then n120 += 1 end
	end
	S.arms = { ["AIM-9M"] = n9, ["AIM-120A"] = n120 }
end
local function fitArms()
	local spec = plane()
	local lim = Specs.loadoutLimits(spec)
	for _, key in { "AIM-9M", "AIM-120A" } do
		local other = key == "AIM-9M" and "AIM-120A" or "AIM-9M"
		S.arms[key] = math.clamp(S.arms[key] or 0, 0, math.min(lim[key], lim.total - (S.arms[other] or 0)))
	end
	local r = Specs.buildLoadout(spec, S.arms["AIM-9M"], S.arms["AIM-120A"])
	local guard = 0
	while (r.left["AIM-9M"] > 0 or r.left["AIM-120A"] > 0) and guard < 20 do
		S.arms["AIM-9M"] -= r.left["AIM-9M"]
		S.arms["AIM-120A"] -= r.left["AIM-120A"]
		r = Specs.buildLoadout(spec, S.arms["AIM-9M"], S.arms["AIM-120A"])
		guard += 1
	end
	return r.layout
end

function Menu.build(parent)
	local list = Ui.make("ScrollingFrame", {
		BackgroundTransparency = 1, BorderSizePixel = 0, ScrollBarThickness = 8, CanvasSize = UDim2.new(0, 0, 0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y,
		Size = UDim2.new(1, 0, 1, 0), Parent = parent,
	}, { Ui.make("UIListLayout", { Padding = UDim.new(0, 10), SortOrder = Enum.SortOrder.LayoutOrder }) })
	local order = 0
	local function nextRow(label)
		order += 1
		return row(list, label, order)
	end

	local body, hint = nextRow("Küldetés")
	choice(body, SCENS, function(id) return S.scen == id end, function(id) S.scen = id end, 104)
	table.insert(refreshers, function() hint.Visible = true; hint.Text = SCEN_HINT[S.scen]; hint.Position = UDim2.new(0, 100, 1, 2) end)

	body = nextRow("Saját gép")
	for gi, g in ipairs(Specs.PLANE_GROUPS) do
		local items = {}
		for _, k in ipairs(g[2]) do if ALL[k] then items[#items + 1] = { k, ALL[k].short } end end
		if #items > 0 then
			Ui.label(body, g[1], { Size = UDim2.new(0, 110, 0, 28), TextSize = 12, TextColor3 = Color3.fromRGB(130, 150, 145), LayoutOrder = gi * 100 })
			for i, it in ipairs(items) do
				local b = Ui.button(body, it[2], { Size = UDim2.new(0, 84, 0, 28), TextSize = 12, LayoutOrder = gi * 100 + i })
				b.Activated:Connect(function()
					S.plane = it[1]
					defaults(ALL[it[1]])
					fitArms()
					refresh()
					if Menu.onPlane then Menu.onPlane() end
				end)
				table.insert(refreshers, function()
					local on = S.plane == it[1]
					b.BackgroundColor3 = on and Ui.Amber or Color3.fromRGB(46, 62, 68)
					b.TextColor3 = on and Color3.fromRGB(16, 22, 20) or Color3.fromRGB(225, 235, 230)
				end)
			end
		end
	end

	body, hint = nextRow("Fegyverzet")
	local function armStepper(key, order)
		Ui.label(body, key, { Size = UDim2.new(0, 70, 0, 28), TextSize = 13, LayoutOrder = order })
		stepper(body, function() return S.arms[key] or 0 end, function(v) S.arms[key] = v; fitArms() end, 0, 12, 1, function(v) return tostring(v) end, order + 1)
	end
	armStepper("AIM-9M", 1)
	armStepper("AIM-120A", 3)
	Ui.button(body, "Alap", { Size = UDim2.new(0, 64, 0, 28), TextSize = 13, LayoutOrder = 5, BackgroundColor3 = Color3.fromRGB(46, 62, 68), TextColor3 = Color3.new(1, 1, 1) }, function()
		defaults(plane()); fitArms(); refresh()
	end)
	table.insert(refreshers, function()
		local layout = fitArms()
		local mass, n = 0, 0
		for _, k in pairs(layout) do
			n += 1
			mass += k == "AIM-9M" and 86 or 152
		end
		hint.Visible = true
		hint.Text = string.format("%d rakéta · %d kg · %s", n, mass, plane().name or "")
		hint.Position = UDim2.new(0, 100, 1, 2)
	end)

	body, hint = nextRow("Ellenfél")
	for gi, g in ipairs(Specs.PLANE_GROUPS) do
		if g[1] ~= "Gyakorlógépek" then
			Ui.label(body, g[1], { Size = UDim2.new(0, 110, 0, 28), TextSize = 12, TextColor3 = Color3.fromRGB(130, 150, 145), LayoutOrder = gi * 100 })
			for i, k in ipairs(g[2]) do
				if Specs.BANDITS[k] then
					local b = Ui.button(body, ALL[k] and ALL[k].short or k, { Size = UDim2.new(0, 84, 0, 28), TextSize = 12, LayoutOrder = gi * 100 + i })
					b.Activated:Connect(function()
						S.foes[k] = (not S.foes[k]) or nil
						refresh()
					end)
					table.insert(refreshers, function()
						local on = S.foes[k] == true
						b.BackgroundColor3 = on and Color3.fromRGB(255, 120, 100) or Color3.fromRGB(46, 62, 68)
						b.TextColor3 = on and Color3.fromRGB(16, 22, 20) or Color3.fromRGB(225, 235, 230)
					end)
				end
			end
		end
	end
	table.insert(refreshers, function()
		local n = 0
		for _ in pairs(S.foes) do n += 1 end
		hint.Visible = true
		hint.Text = n > 0 and (n .. " típus · kattints újra a kivételhez") or "jelölj ki legalább egyet (különben F-16C jön)"
		hint.Position = UDim2.new(0, 100, 1, 2)
	end)

	body, hint = nextRow("Játékmód")
	choice(body, { { "arcade", "Arkád" }, { "realistic", "Realisztikus" } }, function(id) return S.mode == id end, function(id) S.mode = id end, 120)
	table.insert(refreshers, function() hint.Visible = true; hint.Text = S.mode == "arcade" and "rakéták 10 s alatt újratöltődnek" or "újratöltés csak leszállás után"; hint.Position = UDim2.new(0, 100, 1, 2) end)

	body, hint = nextRow("Nehézség")
	choice(body, DIFF, function(id) return S.diff == id end, function(id) S.diff = id end, 90)
	table.insert(refreshers, function() hint.Visible = true; hint.Text = DIFF_HINT[S.diff]; hint.Position = UDim2.new(0, 100, 1, 2) end)

	body = nextRow("Kísérő")
	choice(body, { { 0, "Nincs" }, { 1, "1 kísérőgép" } }, function(id) return S.wing == id end, function(id) S.wing = id end, 120)

	body = nextRow("Ellenség")
	stepper(body, function() return S.enemies end, function(v) S.enemies = v end, 1, 4, 1, function(v) return v .. " az első hullámban" end)

	body = nextRow("Egér célzás")
	stepper(body, function() return S.aim end, function(v) S.aim = v end, 5, 200, 5, function(v) return v .. "%" end)
	Ui.button(body, "fordított Y", { Size = UDim2.new(0, 110, 0, 28), TextSize = 13, LayoutOrder = 2 }, function() S.invert = not S.invert; refresh() end)
	table.insert(refreshers, function() end)
	body = nextRow("Botkormány")
	stepper(body, function() return S.stick end, function(v) S.stick = v end, 5, 200, 5, function(v) return v .. "%" end)

	body = nextRow("Látótér")
	stepper(body, function() return S.fov end, function(v) S.fov = v end, 50, 110, 5, function(v) return v .. "°" end)
	body = nextRow("Napszak")
	choice(body, TODS, function(id) return S.tod == id end, function(id) S.tod = id end, 110)
	body = nextRow("Grafika")
	choice(body, QUALITY, function(id) return S.quality == id end, function(id) S.quality = id end, 110)

	-- the first plane's weapons
	defaults(plane())
	refresh()
	return list
end

-- the options of Game.start, and the settings (Game.settings)
function Menu.opts(airStart)
	local spec = plane()
	local layout = Specs.buildLoadout(spec, S.arms["AIM-9M"] or 0, S.arms["AIM-120A"] or 0).layout
	local foes = {}
	for k in pairs(S.foes) do foes[#foes + 1] = k end
	table.sort(foes)
	if #foes == 0 then foes = { "f16" } end
	return {
		airStart = airStart == true, carrierStart = airStart == "carrier", difficulty = S.diff, enemies = S.enemies, mode = S.mode, aircraft = S.plane, enemyTypes = foes, loadout = layout,
		tutorial = false, scenario = S.scen, wingman = S.wing,
	}
end
function Menu.settings()
	return { aim = S.aim, stick = S.stick, invert = S.invert, fov = S.fov, tod = S.tod, quality = S.quality }
end

return Menu
