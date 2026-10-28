--!nonstrict
-- World War 3: the strategic game behind the career - the port of web/js/campaign.js.
--  * four powers that start at war with everybody - the USA, Europe (the European air forces fight together from the first day), Russia
--    and China.  Trust is earned (joint missions, help when somebody is attacked) and only then can two powers ally.
--  * every power has its real air force (fighters by type, public estimates 2025-26) and builds new jets every month at the real rate,
--    as far as its budget pays.  You see your own numbers exactly, the others only as intelligence estimates.
--  * the war is fought on fronts at real places; every day the fronts fight it out by the quality and number of the jets and pilots
--    sent there; your own missions add what you actually did.
--  * a power whose fighters are gone is out; the last power (or alliance) with an air force wins.
-- The state is a plain table (strings, numbers, booleans, tables), so it can be saved as it is.
-- Common subset of Lua 5.4 and Luau.
local C = {}

C.DAY_PER_MISSION = 2

-- air-to-air quality of each type (10 = best)
C.QUALITY = { f22 = 10, f35 = 8.6, su57 = 7.6, j20 = 8.0, f15 = 7.6, su35 = 7.4, typhoon = 7.6, rafale = 7.5, gripen = 6.7,
	f16 = 6.6, fa18 = 6.6, mig31 = 5.6, mig29 = 5.4, f15a = 7.2 }
-- what a new jet costs (million dollars, flyaway)
C.COST = { f22 = 150, f35 = 82, f15 = 90, f16 = 65, fa18 = 70, typhoon = 100, rafale = 95, gripen = 55, su35 = 85, su57 = 100, j20 = 110, mig31 = 60, mig29 = 30, f15a = 40 }
local QUALITY, COST = C.QUALITY, C.COST

C.POWER_IDS = { "us", "eu", "ru", "cn" }
local POWER_IDS = C.POWER_IDS
-- fleet: fighters by type; production: the most a line builds per month; income: million dollars a day for new jets
C.POWERS = {
	us = { name = "Egyesült Államok", short = "USA", colour = { 74, 127, 216 },
		fleet = { f22 = 180, f35 = 650, f15 = 30, f16 = 900, fa18 = 500 }, production = { f35 = 10, f15 = 2 }, income = 24, pilots = 3200, skill = 1.0 },
	eu = { name = "Európa", short = "EU", colour = { 60, 192, 160 },
		fleet = { typhoon = 370, rafale = 200, gripen = 104, f35 = 75, f16 = 48 }, production = { typhoon = 1, rafale = 1.5, gripen = 1, f35 = 2 }, income = 9, pilots = 1300, skill = 0.95 },
	ru = { name = "Oroszország", short = "RU", colour = { 216, 74, 74 },
		fleet = { su35 = 130, su57 = 28, mig31 = 120, mig29 = 90 }, production = { su35 = 1.5, su57 = 1 }, income = 5, pilots = 1100, skill = 0.85 },
	cn = { name = "Kína", short = "CN", colour = { 224, 176, 48 },
		fleet = { j20 = 300, su35 = 24 }, production = { j20 = 10 }, income = 20, pilots = 1500, skill = 0.85 },
}
local POWERS = C.POWERS

-- the fronts: real places and who meets whom
C.FRONTS = {
	{ id = "baltic", name = "Baltikum", sides = { "eu", "us", "ru" }, why = "Észtország, Lettország, Litvánia légtere" },
	{ id = "poland", name = "Lengyel–belarusz határ", sides = { "eu", "us", "ru" }, why = "a Suwałki-folyosó" },
	{ id = "blacksea", name = "Fekete-tenger", sides = { "eu", "us", "ru" }, why = "a Krím és a tengeri útvonalak" },
	{ id = "arctic", name = "Észak-Norvégia", sides = { "eu", "us", "ru" }, why = "a Kola-félsziget bázisai" },
	{ id = "hungary", name = "Magyarország", sides = { "eu", "ru" }, why = "Európa szíve – a magyar Gripenek otthona" },
	{ id = "alaska", name = "Alaszka – Bering-szoros", sides = { "us", "ru" }, why = "Amerika és Oroszország 80 km-re" },
	{ id = "taiwan", name = "Tajvani-szoros", sides = { "us", "cn" }, why = "a Csendes-óceán kulcsa" },
	{ id = "scs", name = "Dél-kínai-tenger", sides = { "us", "cn" }, why = "mesterséges szigetek, kifutópályákkal" },
	{ id = "japan", name = "Japán-tenger", sides = { "us", "cn", "ru" }, why = "három nagyhatalom találkozik" },
	{ id = "siberia", name = "Amur-folyó (orosz–kínai határ)", sides = { "ru", "cn" }, why = "a két szomszéd régi vitája" },
	{ id = "atlantic", name = "Izland – az Atlanti-óceán kapuja", sides = { "us", "eu" }, why = "Keflavík és a GIUK-rés: itt csak az európai légierővel kerülsz szembe" },
	{ id = "india", name = "Himalája – Ladakh", sides = { "cn", "us" }, why = "a világ teteje" },
}
local FRONTS = C.FRONTS
function C.front(id)
	for _, f in ipairs(FRONTS) do
		if f.id == id then return f end
	end
	return nil
end

local clamp = function(x, lo, hi) if x < lo then return lo elseif x > hi then return hi else return x end end
local floor = math.floor

local function sortedKeys(t)
	local out = {}
	for k in pairs(t) do out[#out + 1] = k end
	table.sort(out)
	return out
end
C.sortedKeys = sortedKeys

-- the order the browser's tables list their types in (the random draws walk through them in this order, so it decides who loses what)
C.FLEET_ORDER = { us = { "f22", "f35", "f15", "f16", "fa18" }, eu = { "typhoon", "rafale", "gripen", "f35", "f16" }, ru = { "su35", "su57", "mig31", "mig29" }, cn = { "j20", "su35" } }
C.PROD_ORDER = { us = { "f35", "f15" }, eu = { "typhoon", "rafale", "gripen", "f35" }, ru = { "su35", "su57" }, cn = { "j20" } }
local function ordered(t, list)
	local out, seen = {}, {}
	for _, k in ipairs(list or {}) do
		if t[k] ~= nil then out[#out + 1] = k; seen[k] = true end
	end
	local rest = {}
	for k in pairs(t) do
		if not seen[k] then rest[#rest + 1] = k end
	end
	table.sort(rest)
	for _, k in ipairs(rest) do out[#out + 1] = k end
	return out
end

local function pairKey(a, b)
	if a < b then return a .. "-" .. b end
	return b .. "-" .. a
end

function C.totalFleet(fleet)
	local s = 0
	for _, v in pairs(fleet) do s = s + v end
	return s
end
local totalFleet = C.totalFleet
function C.strength(fleet, skill)
	local s = 0
	for k, v in pairs(fleet) do s = s + v * (QUALITY[k] or 6) end
	return s * (skill or 1)
end
local strength = C.strength

local function log(w, text)
	table.insert(w.log, 1, { day = w.day, text = text })
	if #w.log > 80 then table.remove(w.log) end
end

local function copyFleet(f)
	local o = {}
	for k, v in pairs(f) do o[k] = v end
	return o
end

-- a fresh war: everybody against everybody, Europe together
function C.newWar(playerPower, seed)
	playerPower = playerPower or "us"
	local w = { version = 1, seed = seed or os.time(), day = 0, started = false, player = playerPower, powers = {}, trust = {}, allied = {}, war = {}, fronts = {},
		intel = {}, log = {}, offers = {}, over = false, missions = 0, policy = { production = {}, focus = false } }
	for _, id in ipairs(POWER_IDS) do
		local p = POWERS[id]
		w.powers[id] = { fleet = copyFleet(p.fleet), start = totalFleet(p.fleet), lost = {}, built = {}, out = false, pilots = p.pilots, money = p.income * 20, spent = 0, fleetFrac = {}, damage = 0 }
	end
	local T = { ["eu-us"] = 25, ["ru-us"] = -60, ["cn-us"] = -55, ["eu-ru"] = -55, ["cn-eu"] = -25, ["cn-ru"] = 5 }
	for k, v in pairs(T) do w.trust[k] = v; w.allied[k] = false; w.war[k] = true end
	for _, f in ipairs(FRONTS) do w.fronts[f.id] = { control = {}, heat = 0.5, lastBattle = false } end
	for _, id in ipairs(POWER_IDS) do
		if id ~= playerPower then w.intel[id] = 0.35 end                  -- estimate error (+-35 %)
	end
	return w
end

function C.trustOf(w, a, b) return w.trust[pairKey(a, b)] or 0 end
function C.alliedWith(w, a, b) return a == b or w.allied[pairKey(a, b)] == true end
function C.atWar(w, a, b) return a ~= b and not w.allied[pairKey(a, b)] and w.war[pairKey(a, b)] == true end
local trustOf, alliedWith, atWar = C.trustOf, C.alliedWith, C.atWar

function C.changeTrust(w, a, b, d, why)
	local k = pairKey(a, b)
	w.trust[k] = clamp((w.trust[k] or 0) + d, -100, 100)
	if why then log(w, string.format("%s–%s bizalom %s%d: %s", POWERS[a].short, POWERS[b].short, d > 0 and "+" or "", floor(d + (d < 0 and -0.5 or 0.5)), why)) end
end
local changeTrust = C.changeTrust

-- what the player sees of a power's air force: exact for your own and your allies', an estimate for the rest
function C.seenFleet(w, id)
	local real = w.powers[id].fleet
	if id == w.player or alliedWith(w, id, w.player) then return { fleet = copyFleet(real), exact = true } end
	local e = w.intel[id] or 0.35
	local out = {}
	for k, v in pairs(real) do
		local noise = math.sin((w.seed % 997) + #k * 7.3 + w.day * 0.13 + #id) * e          -- stable per day
		out[k] = math.max(0, floor(v * (1 + noise) / 5 + 0.5) * 5)
	end
	return { fleet = out, exact = false, error = e }
end

-- ---------------------------------------------------------------- diplomacy
function C.proposeAlliance(w, from, to)
	local t = trustOf(w, from, to)
	if alliedWith(w, from, to) then return { ok = false, text = "Már szövetségesek vagytok." } end
	if t < 60 then return { ok = false, text = string.format("%s nem bízik bennetek eléggé (bizalom: %d / 60).", POWERS[to].name, floor(t + 0.5)) } end
	w.allied[pairKey(from, to)] = true
	w.war[pairKey(from, to)] = false
	log(w, "SZÖVETSÉG: " .. POWERS[from].name .. " és " .. POWERS[to].name)
	return { ok = true, text = POWERS[to].name .. " elfogadta: szövetségesek vagytok!" }
end
function C.proposeCeasefire(w, from, to)
	local t = trustOf(w, from, to)
	local weak = totalFleet(w.powers[to].fleet) / w.powers[to].start
	if t > 0 or weak < 0.35 then
		w.war[pairKey(from, to)] = false
		log(w, "TŰZSZÜNET: " .. POWERS[from].name .. " és " .. POWERS[to].name)
		changeTrust(w, from, to, 10, "tűzszünet")
		return { ok = true, text = "Tűzszünet " .. POWERS[to].name .. " és köztetek." }
	end
	return { ok = false, text = POWERS[to].name .. " elutasította a tűzszünetet." }
end
function C.declareWar(w, from, to)
	w.allied[pairKey(from, to)] = false
	w.war[pairKey(from, to)] = true
	changeTrust(w, from, to, -40, "hadüzenet")
	for _, o in ipairs(POWER_IDS) do
		if o ~= from and o ~= to and alliedWith(w, o, to) then changeTrust(w, from, o, -20, "megtámadtátok a szövetségesét (" .. POWERS[to].short .. ")") end
	end
end

-- ---------------------------------------------------------------- the daily battles on the fronts
local function seeded(w)
	local s = (w.seed + w.day * 7919) % 2147483647
	return function()
		s = (s * 16807) % 2147483647
		return (s - 1) / 2147483646
	end
end

-- remove a fraction of a power's fleet (spread over the types; the better ones survive a little better)
function C.loseJets(w, id, frac)
	local P = w.powers[id]
	local total = 0
	for _, k in ipairs(ordered(P.fleet, C.FLEET_ORDER[id])) do
		local v = P.fleet[k]
		local q = QUALITY[k] or 6
		local f = frac * (1.25 - q / 20)
		local exact = v * f
		local n = floor(exact) + (math.random() < exact % 1 and 1 or 0)
		local lost = math.min(v, n)
		P.fleet[k] = v - lost
		P.lost[k] = (P.lost[k] or 0) + lost
		total = total + lost
	end
	return total
end

local function checkOut(w)
	for _, id in ipairs(POWER_IDS) do
		local P = w.powers[id]
		if not P.out and totalFleet(P.fleet) <= math.max(3, P.start * 0.02) then
			P.out = true
			log(w, POWERS[id].name .. " légiereje megsemmisült – kiesett a háborúból!")
		end
	end
	-- the end: everybody left is allied (or at peace) with everybody else
	local left = {}
	for _, id in ipairs(POWER_IDS) do
		if not w.powers[id].out then left[#left + 1] = id end
	end
	local fighting = false
	for _, a in ipairs(left) do
		for _, b in ipairs(left) do
			if a < b and atWar(w, a, b) then fighting = true end
		end
	end
	local playerLeft = false
	for _, id in ipairs(left) do
		if id == w.player then playerLeft = true end
	end
	if not fighting and not w.over then
		w.over = { day = w.day, winners = left, player = playerLeft }
		log(w, playerLeft and "A HÁBORÚ VÉGET ÉRT – GYŐZTETEK!" or "A HÁBORÚ VÉGET ÉRT – a te oldalad elvesztette a légierejét.")
	end
	if w.powers[w.player].out and not w.over then w.over = { day = w.day, winners = left, player = false } end
end

-- one day: production, then the battles.  skip: a front id that is not simulated (the player fights there himself)
function C.simulateDay(w, skip)
	local r = seeded(w)
	local report = {}
	w.day = w.day + 1
	for _, id in ipairs(POWER_IDS) do
		local P = w.powers[id]
		if not P.out then
			local dmg = (P.damage or 0) > 0 and 1 - P.damage or 1
			P.money = P.money + POWERS[id].income * dmg                                   -- the budget of the day
			P.money = math.min(P.money, POWERS[id].income * 60)                          -- no endless savings: two months at most
			P.fleetFrac = P.fleetFrac or {}
			local first = w.policy.production and w.policy.production[id]
			local order = ordered(POWERS[id].production, C.PROD_ORDER[id])
			if first then
				local rest = {}
				for _, k in ipairs(order) do
					if k ~= first then rest[#rest + 1] = k end
				end
				if POWERS[id].production[first] then table.insert(rest, 1, first) end
				order = rest
			end
			for _, k in ipairs(order) do
				local perMonth, cost = POWERS[id].production[k], COST[k] or 80
				P.fleetFrac[k] = math.min(1.5, (P.fleetFrac[k] or 0) + perMonth / 30 * dmg)
				while P.fleetFrac[k] >= 1 and P.money >= cost do
					P.fleetFrac[k] = P.fleetFrac[k] - 1
					P.money = P.money - cost
					P.spent = P.spent + cost
					P.fleet[k] = (P.fleet[k] or 0) + 1
					P.built[k] = (P.built[k] or 0) + 1
				end
			end
			if (P.damage or 0) > 0 then P.damage = math.max(0, P.damage - 0.01) end    -- repairs
		end
	end
	if not w.started then return report end
	for _, f in ipairs(FRONTS) do
		if skip ~= f.id then
			local sides = {}
			for _, s in ipairs(f.sides) do
				if not w.powers[s].out then sides[#sides + 1] = s end
			end
			for i = 1, #sides do
				for j = i + 1, #sides do
					local a, b = sides[i], sides[j]
					if atWar(w, a, b) then
						local heat = w.fronts[f.id].heat * (0.6 + 0.8 * r())
						local function commit(id)
							local n = 0
							for _, x in ipairs(FRONTS) do
								for _, s in ipairs(x.sides) do if s == id then n = n + 1 end end
							end
							return 0.06 * heat / math.max(1, n / 3)
						end
						local ca, cb = commit(a), commit(b)
						local sa, sb = strength(w.powers[a].fleet, POWERS[a].skill) * ca, strength(w.powers[b].fleet, POWERS[b].skill) * cb
						if sa >= 1 and sb >= 1 then
							local ka, kb = 0.05 * sb / (sa + sb), 0.05 * sa / (sa + sb)       -- fraction of the committed jets lost
							local la, lb = C.loseJets(w, a, ka * ca), C.loseJets(w, b, kb * cb)
							w.fronts[f.id].lastBattle = { day = w.day, a = a, b = b, la = la, lb = lb }
							changeTrust(w, a, b, -0.02)
							report[#report + 1] = { front = f.id, a = a, b = b, la = la, lb = lb }
						end
					end
				end
			end
		end
	end
	checkOut(w)
	return report
end

-- what really happened in the player's mission.  result: { losses = { power = { type = n } }, front, won, trust = { power = d }, trustWhy, intel, strike }
function C.applyMission(w, result)
	for power, byType in pairs(result.losses or {}) do
		local P = w.powers[power]
		if P then
			for k, n in pairs(byType) do
				local m = math.min(P.fleet[k] or 0, n)
				P.fleet[k] = (P.fleet[k] or 0) - m
				P.lost[k] = (P.lost[k] or 0) + m
			end
		end
	end
	if result.front and w.fronts[result.front] then
		w.fronts[result.front].heat = clamp(w.fronts[result.front].heat + (result.won and -0.05 or 0.08), 0.2, 1)
	end
	for other, d in pairs(result.trust or {}) do changeTrust(w, w.player, other, d, result.trustWhy) end
	if result.intel then
		for id in pairs(w.intel) do w.intel[id] = math.max(0.05, w.intel[id] - result.intel) end
	end
	if result.strike then
		local P = w.powers[result.strike]
		P.damage = clamp((P.damage or 0) + 0.25, 0, 0.8)
		log(w, "Gyárak bombázva: " .. POWERS[result.strike].name .. " gyártása -25 %")
	end
	w.missions = w.missions + 1
	checkOut(w)
end

-- the other powers' own decisions every few days (alliances fall apart or form, allies help each other, ceasefires, strikes on factories,
-- offers to the player)
function C.aiDiplomacy(w)
	local r = seeded(w)
	local function ratio(id) return totalFleet(w.powers[id].fleet) / math.max(1, w.powers[id].start) end
	local offers = {}
	for _, o in ipairs(w.offers or {}) do
		if w.day - o.day <= 10 and not w.powers[o.from].out then offers[#offers + 1] = o end
	end
	w.offers = offers
	local function hasOffer(from, type_)
		for _, o in ipairs(w.offers) do
			if o.from == from and o.type == type_ then return true end
		end
		return false
	end
	local function hit(id, by, d)
		local P = w.powers[id]
		P.damage = clamp((P.damage or 0) + d, 0, 0.8)
		log(w, string.format("%s bombázta %s gyárait (a gyártás −%d %%)", POWERS[by].name, id == w.player and "a te" or POWERS[id].name, floor(d * 100 + 0.5)))
	end
	for _, a in ipairs(POWER_IDS) do
		for _, b in ipairs(POWER_IDS) do
			if a < b and not w.powers[a].out and not w.powers[b].out then
				local pl = a == w.player or b == w.player
				local other = a == w.player and b or a
				if not pl then
					local common = 0
					for _, c in ipairs(POWER_IDS) do
						if c ~= a and c ~= b and atWar(w, a, c) and atWar(w, b, c) then common = common + 1 end
					end
					changeTrust(w, a, b, common * 0.6)
				end
				local t = trustOf(w, a, b)
				local skipRest = false
				-- an alliance dies of distrust (yours included)
				if alliedWith(w, a, b) and t < 20 then
					w.allied[pairKey(a, b)] = false
					w.war[pairKey(a, b)] = true
					log(w, string.format("SZÖVETSÉG FELBONTVA: %s és %s (bizalom %d)", POWERS[a].name, POWERS[b].name, floor(t + 0.5)))
					skipRest = true
				end
				-- a truce is called off when the trust is gone
				if not skipRest and not alliedWith(w, a, b) and not atWar(w, a, b) and t < -40 then
					C.declareWar(w, a, b)
					log(w, "TŰZSZÜNET FELMONDVA: " .. POWERS[a].name .. " és " .. POWERS[b].name)
					skipRest = true
				end
				if not skipRest and alliedWith(w, a, b) then
					-- the strong ally helps the weak one: two of its best jets
					local s, wk = a, b
					if ratio(b) > ratio(a) then s, wk = b, a end
					if ratio(wk) < 0.6 and ratio(s) > 0.8 and r() < 0.35 then
						local keys = sortedKeys(w.powers[s].fleet)
						table.sort(keys, function(x, y) return (QUALITY[x] or 6) > (QUALITY[y] or 6) end)
						local typ = nil
						for _, k in ipairs(keys) do
							if not typ and w.powers[s].fleet[k] > 10 then typ = k end
						end
						if typ then
							w.powers[s].fleet[typ] = w.powers[s].fleet[typ] - 2
							w.powers[wk].fleet[typ] = (w.powers[wk].fleet[typ] or 0) + 2
							changeTrust(w, a, b, 1)
							log(w, string.format("%s 2 %s-t küldött szövetségesének (%s)", POWERS[s].name, string.upper(typ), POWERS[wk].name))
						end
					end
					skipRest = true
				end
				if not skipRest and atWar(w, a, b) then
					local weak = math.min(ratio(a), ratio(b))
					if not pl and t >= 10 and weak < 0.55 then
						w.war[pairKey(a, b)] = false
						changeTrust(w, a, b, 10)
						log(w, "TŰZSZÜNET: " .. POWERS[a].name .. " és " .. POWERS[b].name .. " (a veszteségektől megfogyatkozva)")
						skipRest = true
					elseif t <= -60 and r() < 0.06 then
						local victim = w.player
						if not pl then victim = ratio(a) < ratio(b) and a or b end
						hit(victim, victim == a and b or a, 0.15)
					end
				end
				if not skipRest and not pl and not alliedWith(w, a, b) and t >= 70 then
					w.allied[pairKey(a, b)] = true
					w.war[pairKey(a, b)] = false
					log(w, "SZÖVETSÉG: " .. POWERS[a].name .. " és " .. POWERS[b].name)
					skipRest = true
				end
				if not skipRest and pl then
					if t >= 70 and not hasOffer(other, "alliance") then
						table.insert(w.offers, { from = other, type = "alliance", day = w.day })
						log(w, string.format("%s szövetséget ajánl neked (bizalom %d)", POWERS[other].name, floor(t + 0.5)))
					elseif atWar(w, a, b) and t >= 25 and (ratio(other) < 0.55 or ratio(w.player) < 0.5) and not hasOffer(other, "ceasefire") then
						table.insert(w.offers, { from = other, type = "ceasefire", day = w.day })
						log(w, string.format("%s tűzszünetet ajánl (bizalom %d)", POWERS[other].name, floor(t + 0.5)))
					end
				end
			end
		end
	end
end

-- the player answers an offer
function C.answerOffer(w, i, accept)
	local o = (w.offers or {})[i]
	if not o then return { ok = false, text = "" } end
	table.remove(w.offers, i)
	if not accept then
		changeTrust(w, w.player, o.from, -3, "elutasítottad az ajánlatukat")
		return { ok = true, text = "Elutasítottad." }
	end
	if o.type == "alliance" then return C.proposeAlliance(w, w.player, o.from) end
	return C.proposeCeasefire(w, w.player, o.from)
end

-- the enemies of the player at a front
function C.frontEnemies(w, frontId)
	local f = C.front(frontId)
	local out = {}
	for _, s in ipairs(f.sides) do
		if atWar(w, w.player, s) and not w.powers[s].out then out[#out + 1] = s end
	end
	return out
end

-- n jets drawn from a fleet by numbers
function C.pickTypes(fleet, n, rnd, power)
	rnd = rnd or math.random
	local keys = ordered(fleet, C.FLEET_ORDER[power])
	local sum = 0
	for _, k in ipairs(keys) do
		if fleet[k] > 0 then sum = sum + fleet[k] end
	end
	local out = {}
	for _ = 1, n do
		if sum > 0 then
			local x = rnd() * sum
			for _, k in ipairs(keys) do
				local v = fleet[k]
				if v > 0 then
					x = x - v
					if x <= 0 then out[#out + 1] = k break end
				end
			end
		end
	end
	return out
end

-- the budget as the player sees it: money, the daily income, and how many jets a month it really pays for
function C.budgetOf(w, id)
	local P = w.powers[id]
	local inc = POWERS[id].income * (1 - (P.damage or 0))
	local monthly, cost = 0, 0
	for k, perMonth in pairs(POWERS[id].production) do
		monthly = monthly + perMonth
		cost = cost + perMonth * (COST[k] or 80)
	end
	local afford = math.min(monthly, inc * 30 / (cost / monthly))
	return { money = floor((P.money or 0) + 0.5), income = floor(inc * 10 + 0.5) / 10, perMonth = floor(afford * 10 + 0.5) / 10, capacity = monthly }
end

-- ---------------------------------------------------------------- the career of the pilot in the war (ranks, awards)
C.RANKS = { "hadnagy", "főhadnagy", "százados", "őrnagy", "alezredes", "ezredes", "dandártábornok" }
C.PROMOTE_AT = { 0, 3, 8, 14, 22, 32, 45 }
C.KINDS = { sweep = "Légtérfölény (sweep)", cap = "Légtérvédelmi járőr (CAP)" }

-- the pilot: { name, callsign, rank, sorties, kills, awards = {}, order, assigned }
function C.newPilot(name, callsign)
	return { name = name or "Pilóta", callsign = callsign or "VIPER", rank = 0, sorties = 0, kills = 0, awards = {}, jet = "f16" }
end

local function award(pilot, name)
	for _, a in ipairs(pilot.awards) do
		if a == name then return false end
	end
	table.insert(pilot.awards, name)
	return true
end
C.award = award

-- the order of the day: the front, the enemies there by their real fleets, your flight and help, sized by rank.  over: { kind, jet, tod }
function C.makeOrder(w, pilot, frontId, over)
	over = over or {}
	local f = C.front(frontId)
	local enemies = C.frontEnemies(w, frontId)
	local rank = pilot.rank or 0
	local foe = enemies[math.random(#enemies)]
	local big = math.random() < 0.35 + rank * 0.05
	local nRed = big and 4 + math.random(0, 2) or 2 + math.random(0, 1)          -- at most 6; a mission sends them in groups of 4
	local red = {}
	for _, t in ipairs(C.pickTypes(w.powers[foe].fleet, nRed, nil, foe)) do red[#red + 1] = { type = t, n = 1, power = foe } end
	local blue = {}
	local nBlue = math.max(0, nRed - 2 + (rank >= 2 and 0 or 1))
	for _, t in ipairs(C.pickTypes(w.powers[w.player].fleet, nBlue, nil, w.player)) do
		blue[#blue + 1] = { type = (t == "f22" and math.random() < 0.5) and "f15" or t, n = 1, power = w.player, label = POWERS[w.player].short }
	end
	for _, id in ipairs(POWER_IDS) do
		if id ~= w.player and alliedWith(w, w.player, id) then
			local onFront = false
			for _, s in ipairs(f.sides) do if s == id then onFront = true end end
			if onFront then
				local t = trustOf(w, w.player, id)
				local n = t >= 85 and 4 or (t >= 70 and 3 or 2)
				for _, ty in ipairs(C.pickTypes(w.powers[id].fleet, n, nil, id)) do blue[#blue + 1] = { type = ty, n = 1, power = id, label = POWERS[id].short } end
			end
		end
	end
	return { front = frontId, foe = foe, role = rank < 1 and "wing" or "lead", red = red, blue = blue, rank = rank,
		skill = ({ "normal", "normal", "hard", "hard", "ace", "ace", "ace" })[rank + 1], minutes = 8, bearing = math.random() * math.pi * 2,
		kind = over.kind or (math.random() < 0.3 and "cap" or "sweep"), jet = over.jet or pilot.jet or "f16", tod = over.tod or "day" }
end

-- the mission table for Mission.luau from an order
function C.missionOf(w, pilot, o)
	local f = C.front(o.front)
	local blue = {}
	for _, b in ipairs(o.blue) do blue[#blue + 1] = { type = b.type, n = b.n, power = b.power, label = b.label } end
	return { kind = o.kind, role = o.role, playerType = o.jet, red = o.red, blue = blue, skill = o.skill, minutes = o.minutes, bearing = o.bearing,
		front = o.front, foe = o.foe, power = w.player, tod = o.tod,
		title = string.format("%s: %d %s gép", f.name, #o.red, POWERS[o.foe].short), callsign = pilot.callsign .. " 1-" .. (o.role == "wing" and 2 or 1) }
end

-- a mission has been flown: what it does to the war and the pilot.  r: the result of Mission.luau.  -> { lines = {...} }
function C.afterMission(w, pilot, m, r)
	local foe = m.foe
	local losses = {}
	losses[foe] = {}
	losses[w.player] = {}
	for _, e in ipairs(r.redLost or {}) do
		local p = e.power or foe
		losses[p] = losses[p] or {}
		losses[p][e.type] = (losses[p][e.type] or 0) + 1
	end
	for _, e in ipairs(r.blueLost or {}) do
		local p = e.power or w.player
		losses[p] = losses[p] or {}
		losses[p][e.type] = (losses[p][e.type] or 0) + 1
	end
	local trust = {}
	for _, b in ipairs(m.blue) do
		if b.power ~= w.player then trust[b.power] = (trust[b.power] or 0) + (r.won and 4 or 1) end
	end
	local f = C.front(m.front)
	local hasEu = false
	for _, b in ipairs(m.blue) do if b.power == "eu" then hasEu = true end end
	for _, s in ipairs(f.sides) do
		if s == "eu" and not hasEu and r.won and w.player ~= "eu" then trust.eu = 3 end            -- you helped Europe's front
	end
	C.applyMission(w, { losses = losses, front = m.front, won = r.won, trust = trust, trustWhy = "közös harc a fronton", intel = 0.02 })
	local lines = {}
	-- whoever you fight trusts you less: every enemy jet you shoot down costs trust with its country, and a little with its allies
	local b0 = trustOf(w, w.player, foe)
	local shot = #(r.redLost or {})
	local d = 3 + 1.2 * shot
	changeTrust(w, w.player, foe, -d, string.format("harcoltatok egymás ellen (%d lelőtt gép)", shot))
	for _, o in ipairs(POWER_IDS) do
		if o ~= w.player and o ~= foe and alliedWith(w, foe, o) then
			changeTrust(w, w.player, o, -d * 0.4, "megtámadtátok a szövetségesét (" .. POWERS[foe].short .. ")")
		end
	end
	lines[#lines + 1] = string.format("Bizalom %s: %d → %d (harc ellenük)", POWERS[foe].short, floor(b0 + 0.5), floor(trustOf(w, w.player, foe) + 0.5))
	C.passDays(w, C.DAY_PER_MISSION)
	pilot.sorties = pilot.sorties + 1
	pilot.kills = pilot.kills + (r.kills or 0)
	if (r.kills or 0) >= 3 and award(pilot, "Silver Star") then lines[#lines + 1] = "Silver Star – 3 légi győzelem egy bevetésen" end
	if (r.kills or 0) >= 5 and award(pilot, "Medal of Honor") then lines[#lines + 1] = "Medal of Honor – 5 győzelem egy bevetésen!" end
	if pilot.kills >= 5 and award(pilot, "ÁSZ") then lines[#lines + 1] = "ÁSZ – 5 légi győzelem" end
	if pilot.sorties % 5 == 0 and award(pilot, "Air Medal (" .. pilot.sorties .. " bevetés)") then lines[#lines + 1] = "Air Medal – " .. pilot.sorties .. " bevetés" end
	if r.won and #m.red >= 8 and award(pilot, "Distinguished Flying Cross") then lines[#lines + 1] = "Distinguished Flying Cross – győzelem túlerő ellen" end
	local score = pilot.sorties + pilot.kills * 2
	while (pilot.rank or 0) < 6 and score >= C.PROMOTE_AT[(pilot.rank or 0) + 2] do
		pilot.rank = (pilot.rank or 0) + 1
		local extra = ({ [2] = " – mostantól te választod a feladatot és az időpontot", [3] = " – mostantól te választod a frontot és a gépet",
			[4] = " – MI-kötelékeket küldhetsz ki", [5] = " – politikai döntések" })[pilot.rank] or ""
		lines[#lines + 1] = "ELŐLÉPTETÉS: " .. C.RANKS[pilot.rank + 1] .. extra
	end
	return { lines = lines }
end

-- days go by: the war goes on, the powers decide
function C.passDays(w, n)
	for _ = 1, n do
		C.simulateDay(w)
		if w.day % 4 == 0 then C.aiDiplomacy(w) end
	end
end

-- a flight of AI pilots flies a mission the player does not fly: the numbers decide.  n: how many jets (2-8).  -> { redLost, blueLost, won }
function C.sendFlight(w, frontId, n)
	local enemies = C.frontEnemies(w, frontId)
	local foe = enemies[math.random(#enemies)]
	local nRed = math.max(2, n + math.random(0, 2) - 1)
	local reds = C.pickTypes(w.powers[foe].fleet, nRed, nil, foe)
	local mine = C.pickTypes(w.powers[w.player].fleet, n, nil, w.player)
	local ours, theirs = 0, 0
	for _, t in ipairs(mine) do ours = ours + 62 * (QUALITY[t] or 6) end
	for _, t in ipairs(reds) do theirs = theirs + (QUALITY[t] or 6) * 55 * POWERS[foe].skill end
	local p = ours / (ours + theirs)
	local losses = {}
	losses[foe] = {}
	losses[w.player] = {}
	local redLost, blueLost = 0, 0
	for _, t in ipairs(reds) do
		if math.random() < p * 0.75 then redLost = redLost + 1; losses[foe][t] = (losses[foe][t] or 0) + 1 end
	end
	for _, t in ipairs(mine) do
		if math.random() < (1 - p) * 0.45 then blueLost = blueLost + 1; losses[w.player][t] = (losses[w.player][t] or 0) + 1 end
	end
	C.applyMission(w, { losses = losses, front = frontId, won = redLost > blueLost })
	C.passDays(w, C.DAY_PER_MISSION)
	return { foe = foe, redLost = redLost, blueLost = blueLost, reds = #reds, mine = #mine, won = redLost > blueLost }
end

return C
