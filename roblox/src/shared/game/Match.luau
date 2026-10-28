--!nonstrict
-- A match: the game flow of web/js/game.js without the pictures, the input devices and the menus - spawning the player,
-- the enemy waves, the wingman, duel, survival, ring races, scoring and medals, the throttle lever, the ejection.
-- The client (client/Game.luau) feeds it the player's controls and draws what happens.
-- Written in the common subset of Lua 5.4 and Luau, so it is tested outside of Roblox (roblox/tests).
local M = require(script.Parent.Parent.sim.SimMath)
local Sim = require(script.Parent.Parent.sim.Sim)
local AI = require(script.Parent.Parent.sim.AI)
local Specs = require(script.Parent.Parent.sim.Specs)
local Race = require(script.Parent.Race)
local Career = require(script.Parent.Career)
local Tutorial = require(script.Parent.Tutorial)
local CarrierLib = require(script.Parent.Carrier)
local V, add, sub, mul, len, norm, copy, clamp, DEG = M.V, M.add, M.sub, M.mul, M.len, M.norm, M.copy, M.clamp, M.DEG
local atan2, rng = M.atan2, M.rng
local abs = math.abs
local IR = Specs.IR
local AIRCRAFT, TRAINERS, BANDITS = Specs.AIRCRAFT, Specs.TRAINERS, Specs.BANDITS
local WEAPON_CLASS = Specs.WEAPON_CLASS

local G = {}

-- the matches that can be played with a friend, and how far apart the two start (m)
G.NET_SCENS = { race = true, canyon = true, tube = true, free = true }
G.NET_SIDE = { race = 40, canyon = 25, tube = 35, free = 90 }

-- The fight happens on the far side of the map: the enemies live in the combat zone and never attack anyone near the home
-- base (safe area), so taking off and landing is quiet.  An air start puts the player on the way there, just outside the zone.
local ZONE, ENGAGE_MARGIN, SAFE_RADIUS = { x = -14000, y = 16000, r = 16000 }, 12000, 14000
G.ZONE, G.SAFE_RADIUS = ZONE, SAFE_RADIUS
local CAT_HINT = "KATAPULT: adj teljes gázt (Shift tartva, 100%), és a katapult kilő az orr felé  ·  utána húzd az orrot (S), G = futómű"
local TAKEOFF_HINT_NOAB = "FELSZÁLLÁS: Shift tartva = gáz 100%-ig  ·  felemelkedési sebességnél emeld az egeret (vagy S)  ·  G = futómű"
local TAKEOFF_HINT = "FELSZÁLLÁS: Shift tartva = gáz 100%-ig, újra Shift = utánégető  ·  ~280 km/h-nál emeld az egeret (vagy S)  ·  G = futómű"
local SPLASH = { "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten" }
local WAVE_DELAY, FIRST_WAVE_DELAY, RELOAD_TIME, MAX_ENEMIES, MAX_ACTIVE, REINFORCE_GAP = 5, 25, 10, 6, 4, 70
local THROTTLE_RATE, MAX_AB = 0.4, 1.1
G.TAKEOFF_HINT, G.TAKEOFF_HINT_NOAB = TAKEOFF_HINT, TAKEOFF_HINT_NOAB

local function noop() end

local Match = {}
Match.__index = Match

function G.freshState()
	return { wave = 0, kills = 0, deaths = 0, banner = "", subBanner = "", paused = false, waveTimer = FIRST_WAVE_DELAY, waveActive = false,
		score = 0, streak = 0, reserve = 0, reserveT = 0, spawned = 0, duelWins = 0, duelLosses = 0, duelStreak = 0, over = false, modeLine = "", credits = 0 }
end

-- opts: scenario (waves, survival, duel, race, canyon, tube, free), enemies, difficulty, enemyTypes, aircraft, loadout, airStart,
--       wingman, mode ("arcade")
-- env:  terrain, seed, career (Career), hangar { pilotSkin, skin, modOn(id), upgraded(spec), earn(n) }, hud { message, popup, showMedal },
--       sounds { play }, radio { say }, onSpawn(ac, spec), clock() (seconds), best { race, canyon, tube, tubeLap }, onRecord(kind, ...)
function G.new(opts, env)
	local self = setmetatable({}, Match)
	self.opts, self.env = opts or {}, env
	self.terrain = env.terrain
	self.world = Sim.newWorld(self.terrain, env.seed or math.floor(os.clock() * 1e6) % 1000000000)
	self.rnd = self.world.rnd
	self.career = env.career or Career.new(nil, nil)
	self.hangar = env.hangar or { pilotSkin = nil, skin = nil, modOn = function() return false end, upgraded = function(_, s) return s end, earn = noop }
	self.hud = env.hud or { message = noop, popup = noop, showMedal = noop }
	self.sounds = env.sounds or { play = noop }
	self.radio = env.radio or { say = noop, event = noop }
	self.clock = env.clock or os.clock
	self.state = G.freshState()
	self.threats, self.hitBy = {}, {}
	self.bt = { charge = 1, active = 0 }
	self.player, self.pilot, self.wingman, self.killCam, self.race = nil, nil, nil, nil, nil
	self.stick = { x = 0, y = 0, idle = 0 }
	self.nav = { zone = { x = ZONE.x, y = ZONE.y, r = ZONE.r, engage = ZONE.r + ENGAGE_MARGIN },
		base = { x = self.terrain.airfield.x, y = self.terrain.airfield.y, r = SAFE_RADIUS }, wave = 0, enemies = 0 }
	self.prevPos, self.myFin, self.ejectArm, self.thrPress = nil, nil, 0, -1e9
	self.events = {}                                    -- the world's events of the last frame, for the view
	self.guest = self.opts.netGuest == true
	-- the carrier, 21 km east and 42 km south of the island's middle (its deck is ground for the flight model)
	self.carrier = self.terrain.carrier or CarrierLib.new(self.terrain, 21000, -42000, 0)
	self.nav.carrier = { x = self.carrier.x, y = self.carrier.y }
	self.wasOnDeck, self.catState, self.trapped, self.towTimer = false, nil, false, 0
	self:spawnPlayer()
	if self.opts.tutorial then self.tutorial = Tutorial.new(self, env.cam) end
	return self
end

function Match:scenario()
	if self.opts.tutorial then return "waves" end
	return self.opts.scenario or "waves"
end
-- the host of a co-op room runs the enemies; the guests only see them (Net.luau)
function Match:setGuest(on) self.guest = on == true end
function Match:wantWingman()
	local sc = self:scenario()
	return self.opts.wingman and not self.opts.tutorial and not self.guest and sc ~= "pvp" and sc ~= "duel" and sc ~= "race" and sc ~= "canyon" and sc ~= "tube" and sc ~= "free" and not self.opts.benchmark
end
function Match:enemiesAlive()
	local out = {}
	for _, a in ipairs(self.world.aircraft) do
		if a.team ~= "blue" and a.alive then out[#out + 1] = a end
	end
	return out
end

-- ---------------------------------------------------------------- spawning
function Match:spawnPlayer()
	local w, terrain = self.world, self.terrain
	if self.player then
		local keep = {}
		for _, a in ipairs(w.aircraft) do if a ~= self.player then keep[#keep + 1] = a end end
		w.aircraft = keep
	end
	local sc = self:scenario()
	local duel, canyon, tube, free = sc == "duel", sc == "canyon", sc == "tube", sc == "free"
	local pvp = sc == "pvp"
	local race = sc == "race" or canyon or tube
	local air = self.opts.airStart or duel or race or free or pvp
	local field = terrain.airfield
	local pos, heading, speed = nil, 0, 0
	local st = self.state
	if race then
		-- ring race: 3 km north of the base, heading north, the first ring ahead
		local start = V(field.x, field.y + 3000, 0)
		if not self.race then
			local env = self.env
			local onRecord = env.onRecord or noop
			local best = env.best or {}
			if canyon then self.race = Race.Canyon.new(terrain, { best = best.canyon, onRecord = function(t) onRecord("canyon", t) end })
			elseif tube then self.race = Race.Tube.new(terrain, V(field.x, field.y + 3500, 0), { best = best.tube, bestLap = best.tubeLap, onRecord = function(t, lap) onRecord("tube", t, lap) end })
			else self.race = Race.Race.new(terrain, start, 0, { best = best.race, onRecord = function(t) onRecord("race", t) end }) end
		end
		self.race:reset()
		if tube then
			local pose = self.race:startPose()
			pos, heading, speed = pose.pos, pose.heading, 230
		else
			local r0 = self.race.rings[1]
			pos = add(r0.c, mul(r0.n, -1800))
			if canyon then pos.z = math.max(r0.c.z, terrain:height(pos.x, pos.y) + 90)
			else pos.z = math.max(r0.c.z + 60, terrain:height(pos.x, pos.y) + 250) end
			speed = canyon and 270 or 220
			heading = atan2(r0.n.x, r0.n.y) / DEG
		end
		self.prevPos, self.myFin = nil, nil
	elseif duel then
		-- duel: in the combat zone, heading north; the opponent comes head-on (spawnDuel)
		pos = V(ZONE.x, ZONE.y - 7000, 5000)
		pos.z = math.max(pos.z, terrain:height(pos.x, pos.y) + 1500)
		speed = 250
		local keep = {}
		for _, a in ipairs(w.aircraft) do
			if a.team ~= "blue" and a.alive then a.alive = false end
		end
		for _, a in ipairs(w.aircraft) do if a.team == "blue" then keep[#keep + 1] = a end end
		w.aircraft = keep
		st.waveActive, st.waveTimer = false, 3
	elseif pvp then
		-- team fight: the two teams start on the two sides of the combat zone, facing each other
		local red = self.env.netTeam == "red"
		local slot = (self.env.netSlot or 0) % 8
		pos = V(ZONE.x + (red and 7000 or -7000), ZONE.y + (slot - 3.5) * 700, 4500 + (slot % 3) * 350)
		pos.z = math.max(pos.z, terrain:height(pos.x, pos.y) + 1500)
		speed, heading = 250, red and 270 or 90
	elseif free then
		-- free flight: over the base, heading north
		pos = V(field.x, field.y + 2500, 0)
		pos.z = math.max(1800, terrain:height(pos.x, pos.y) + 900)
		speed = 230
	elseif air then
		-- between the base and the combat zone, heading for the zone
		local k = 0.45
		pos = V(field.x + (ZONE.x - field.x) * k, field.y + (ZONE.y - field.y) * k, 4500)
		pos.z = math.max(pos.z, terrain:height(pos.x, pos.y) + 1500)
		speed = 250
		heading = atan2(ZONE.x - pos.x, ZONE.y - pos.y) / DEG
	elseif self.opts.carrierStart and self.carrier.active then
		local cx, cy, ch = self.carrier:catapult(0)            -- on catapult 1, facing the bow
		pos, heading = V(cx, cy, 0), ch
	else
		local p = field:startPosition()
		pos, heading = V(p[1], p[2], 0), 0
	end
	if self.env.netSide and G.NET_SCENS[sc] then              -- two players: side by side, not on top of each other
		local side, h = self.env.netSide, heading * DEG
		pos = copy(pos)
		pos.x = pos.x + math.cos(h) * side * G.NET_SIDE[sc]
		pos.y = pos.y - math.sin(h) * side * G.NET_SIDE[sc]
	end
	-- the hangar: engine-room upgrades, the paint scheme and the mods ride on the player's jet
	local hg = self.hangar
	local base = AIRCRAFT[self.opts.aircraft] or TRAINERS[self.opts.aircraft] or AIRCRAFT.f16
	local spec = self.opts.benchmark and base or hg:upgraded(base)
	local ac = Sim.newAircraft(spec, "Te (" .. spec.callsign .. " 1)", self.env.netTeam or "blue", pos, heading, speed, { isPlayer = true, livery = "viper", lockAssist = true,
		missiles = Specs.missilesFor(spec, false), loadout = spec.trainer and "default" or self.opts.loadout or "default", rnd = rng(math.floor(self.rnd() * 1e9)),
		outfit = hg.pilotSkin, skin = hg.skin, blastMult = hg:modOn("bigboom") and 1.6 or 1,
		tracerColor = hg:modOn("tracer") and { 0.85, 0.4, 1, 0.45, 0.1, 0.7 } or nil })
	ac.specKey = AIRCRAFT[self.opts.aircraft] and self.opts.aircraft or TRAINERS[self.opts.aircraft] and self.opts.aircraft or "f16"
	if air then
		ac.controls.throttle = 0.95
	else
		ac.fm:placeOnGround(pos.x, pos.y, terrain:height(pos.x, pos.y), heading)
		ac.controls.throttle = 0
		st.subBanner = (self.opts.carrierStart and self.carrier.active) and CAT_HINT or (spec.noAB and TAKEOFF_HINT_NOAB or TAKEOFF_HINT)
	end
	w:addAircraft(ac)
	self.player, self.pilot = ac, AI.newPlayerPilot(ac)
	self.killCam, self.followM = nil, nil
	self.threats, self.hitBy = {}, {}
	if self.env.onSpawn then self.env.onSpawn(ac, spec) end
	if self.wingman and self.wingman.alive then self.wingman.pilot.lead = ac
	elseif air and self:wantWingman() then self:spawnWingman() end
	if sc == "survival" and st.wave == 0 then st.waveTimer = air and 12 or FIRST_WAVE_DELAY end
end

-- the wingman joins behind and to the right of the player (same type, the weaker AI airframe and missiles)
function Match:spawnWingman()
	local p = self.player
	local spec = BANDITS[p.spec.id] or BANDITS[p.spec.model] or BANDITS.f16
	local fwd = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0))
	local right = V(fwd.y, -fwd.x, 0)
	local pos = add(add(p.pos, mul(fwd, -260)), mul(right, 170))
	pos.z = math.max(p.pos.z + 20, self.terrain:height(pos.x, pos.y) + 300)
	local loadout = spec.id == "f16" and "default" or Specs.buildLoadout(spec, 2, 4).layout
	local ac = Sim.newAircraft(spec, spec.callsign .. " 2 (kísérő)", "blue", pos, atan2(fwd.x, fwd.y) / DEG, math.max(200, p.speed),
		{ livery = "viper", missiles = Specs.missilesFor(spec, true), loadout = loadout, rnd = rng(math.floor(self.rnd() * 1e9)) })
	AI.newWingmanPilot(ac, p)
	self.world:addAircraft(ac)
	self.wingman = ac
	self.hud:message("KÍSÉRŐ CSATLAKOZOTT - " .. ac.name, "good", 3)
	if self.env.onSpawn then self.env.onSpawn(ac, spec) end
end

-- a wave appears in the combat zone, on its far side from the player, facing the player's way in
function Match:spawnWave()
	local st, p = self.state, self.player
	if self:scenario() == "duel" then self:spawnDuel(); return end
	st.wave = st.wave + 1
	if self:wantWingman() and (not self.wingman or not self.wingman.alive) then self:spawnWingman() end
	self.career:best("bestWave", st.wave)
	if st.wave >= 5 then self:medal("wave5") end
	if self:scenario() == "survival" then
		self.career:best("bestSurvival", st.wave)
		if st.wave >= 4 then self:medal("survivor") end
	end
	local count = math.min((self.opts.enemies or 2) + st.wave - 1, MAX_ENEMIES)
	local now = math.min(count, MAX_ACTIVE)
	st.reserve, st.reserveT, st.spawned = count - now, 0, 0
	self:spawnEnemies(now, 0)
	st.waveActive = true
	local toZone = math.max(0, math.sqrt((ZONE.x - p.pos.x) ^ 2 + (ZONE.y - p.pos.y) ^ 2) - ZONE.r)
	local extra = st.reserve > 0 and (" (egyszerre " .. now .. ", a többi erősítésként jön)") or ""
	local far = toZone > 1000 and (" (" .. string.format("%.0f", toZone / 1000) .. " km)") or ""
	self.hud:message(st.wave .. ". HULLÁM - " .. count .. " ellenség" .. extra .. " a harci zónában" .. far, "warn", 5)
end

function Match:enemyType(r)
	local list = {}
	local src = self.opts.enemyTypes or { self.opts.enemyType or "f16" }
	for _, k in ipairs(src) do if BANDITS[k] then list[#list + 1] = k end end
	if #list == 0 then return "f16" end
	return list[math.floor(r() * #list) + 1]
end

-- n enemies in a line across the combat zone (back: metres further away, for reinforcements)
function Match:spawnEnemies(n, back)
	local st, p, r = self.state, self.player, self.rnd
	local from = norm(V(ZONE.x - p.pos.x, ZONE.y - p.pos.y, 0), V(0, 1, 0))
	local center = add(V(ZONE.x, ZONE.y, 0), mul(from, ZONE.r * 0.35 + back))
	local side = V(from.y, -from.x, 0)
	local area = { x = self.nav.zone.x, y = self.nav.zone.y, r = self.nav.zone.r, engage = self.nav.zone.engage, safe = self.nav.base }
	for i = 0, n - 1 do
		local pos = add(center, mul(side, (i - (n - 1) / 2) * 3500 + r.uniform(-800, 800)))
		pos.z = math.max(r.uniform(3000, 7500), self.terrain:height(pos.x, pos.y) + 1500)
		local heading = atan2(-from.x, -from.y) / DEG + r.uniform(-20, 20)
		local typ = self:enemyType(r)
		local spec = BANDITS[typ]
		local loadout = (typ == "f16" or spec.proc) and "default" or Specs.buildLoadout(spec, 2, 4).layout
		st.spawned = st.spawned + 1
		local ac = Sim.newAircraft(spec, "Bandita " .. st.spawned .. " (" .. spec.short .. ")", "red", pos, heading, 240,
			{ livery = "viper", missiles = Specs.missilesFor(spec, true), loadout = loadout, rnd = rng(math.floor(r() * 1e9)) })
		AI.newAIPilot(ac, self.opts.difficulty or "normal", area)
		ac.specKey = typ
		self.world:addAircraft(ac)
		if self.env.onSpawn then self.env.onSpawn(ac, spec) end
	end
end

-- duel: one opponent 9 km ahead, head-on, same height; every round starts with a full jet
function Match:spawnDuel()
	local st, p, r = self.state, self.player, self.rnd
	st.wave = st.wave + 1
	p:rearm()
	p.hp, p.burning = p.spec.hp, false
	p.fm.fuel = p.spec.internalFuel
	for _, s in ipairs(p.stations) do s.reload = nil end
	local fwd = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0))
	local pos = add(p.pos, mul(fwd, 9000))
	pos.x, pos.y = clamp(pos.x, -38000, 38000), clamp(pos.y, -38000, 38000)
	pos.z = clamp(p.pos.z + r.uniform(-400, 400), self.terrain:height(pos.x, pos.y) + 1500, 9000)
	local typ = self:enemyType(r)
	local spec = BANDITS[typ]
	local loadout = (typ == "f16" or spec.proc) and "default" or Specs.buildLoadout(spec, 2, 4).layout
	local ac = Sim.newAircraft(spec, "Ellenfél (" .. spec.short .. ")", "red", pos, atan2(p.pos.x - pos.x, p.pos.y - pos.y) / DEG, 240,
		{ livery = "viper", missiles = Specs.missilesFor(spec, true), loadout = loadout, rnd = rng(math.floor(r() * 1e9)) })
	AI.newAIPilot(ac, self.opts.difficulty or "normal", nil)
	ac.specKey = typ
	self.world:addAircraft(ac)
	if self.env.onSpawn then self.env.onSpawn(ac, spec) end
	st.waveActive = true
	self.hud:message(st.wave .. ". PÁRBAJ - " .. spec.short .. " szemből, 9 km", "warn", 4)
end

-- ------------------------------------------------------------------ the player's controls
function Match:canAct() return not self.state.paused and self.player ~= nil and self.player.alive end

-- Throttle like a real lever with a MIL detent: a tap moves it 5 %, holding slews it 40 %/s.  Going up it stops at 100 %
-- (MIL); the afterburner needs a new press of Shift there.  Down from AB goes straight to MIL.
function Match:throttleStep(dir)
	local c = self.player.controls
	self.thrPress = self.clock()
	if dir > 0 then
		if c.throttle >= 0.999 then
			if c.throttle < MAX_AB and not self.player.spec.noAB then
				c.throttle = MAX_AB
				self.hud:message("UTÁNÉGETŐ BE", "warn", 1.2, "thr")
			end
		else
			c.throttle = math.min(1, math.floor(c.throttle * 20 + 1e-6) / 20 + 0.05)
		end
	elseif c.throttle > 1.001 then
		c.throttle = 1
		self.hud:message("UTÁNÉGETŐ KI", "info", 1.2, "thr")
	else
		c.throttle = math.max(0, math.ceil(c.throttle * 20 - 1e-6) / 20 - 0.05)
	end
end
function Match:throttleInput(dt, up, down)
	local c = self.player.controls
	local dir = (up and not down) and 1 or (down and not up) and -1 or 0
	if dir == 0 or self.clock() - self.thrPress < 0.3 then return end
	if dir > 0 and c.throttle < 1 then c.throttle = math.min(1, c.throttle + THROTTLE_RATE * dt)
	elseif dir < 0 then c.throttle = c.throttle > 1 and 1 or math.max(0, c.throttle - THROTTLE_RATE * dt) end
end

-- inp: { aim (direction, sim frame), pitch, roll, yaw (-1..1 or nil), throttleUp, throttleDown, brake, trigger, flare, camPos (the camera's forward for the T key) }
function Match:applyInput(dt, inp)
	local p, c = self.player, self.player.controls
	self.pilot.aim = inp.aim or self.pilot.aim
	self.pilot.pitch, self.pilot.roll, self.pilot.yaw = inp.pitch, inp.roll, inp.yaw
	if inp.throttleSet then c.throttle = inp.throttleSet end
	self:throttleInput(dt, inp.throttleUp, inp.throttleDown)
	c.airbrake = inp.brake == true
	c.brakes = inp.brake == true and p.onGround
	p.trigger = inp.trigger == true
	p.cmHold = inp.flare == true
end

-- the keys that are not held (a press): k as in the browser game
function Match:onKey(k, camForward)
	if not self:canAct() then return end
	local p = self.player
	local function msg(t, l, d) self.hud:message(t, l or "info", d or 1.5) end
	if k == "shift" then self:throttleStep(1); return end
	if k == "z" or k == "control" then self:throttleStep(-1); return end
	if k == "Space" then
		local m = p:fireMissile(self.world)
		if m then
			local fox = m.spec.guidance == IR and "FOX 2" or "FOX 3"
			msg(m.pending and (fox .. " - fegyvertér nyílik") or fox)
		end
	elseif k == "f" then
		if not p.selectedSpec or p.selectedSpec.guidance ~= IR then p:select("AIM-9M") end
		if p.irSeeker.locked then
			p:toggleIrLock(self.world)
			msg("KERESŐ ELENGEDVE", "info", 1.2)
		elseif p:toggleIrLock(self.world) then
			msg("SEEKER LOCK - Space: indítás", "good")
		else
			msg("Nincs ellenség az orr előtt (±30°)", "warn")
		end
	elseif k == "t" then
		-- lock the enemy closest to where you are looking (mouse aim, or free look)
		local res = p.radar:quickLock(self.world, camForward or p.forward)
		local t = ({ unlocked = { "UNLOCK", "info" }, locking = { "LOCKOLÁS...", "info" }, keep = { "Nincs másik cél", "info" },
			none = { "Nincs cél a nézési irányban - fordulj felé", "warn" } })[res]
		if t then msg(t[1], t[2], 1.6) end
	elseif k == "y" then p.radar:cycleTarget()
	elseif k == "r" then
		p.radar:togglePower()
		msg("RADAR " .. (p.radar.on and "BE" or "KI"), "info", 1.2)
	elseif k == "1" then if p:select("AIM-9M") then msg("AIM-9M", "info", 1) end
	elseif k == "2" then if p:select("AIM-120A") then msg("AIM-120A", "info", 1) end
	elseif k == "Tab" then
		if p:toggleExtreme() then
			msg(p.extreme and "EXTRÉM MÓD BE - tolóerő-vektorálás, 9 G, teljes húzás = Cobra" or "EXTRÉM MÓD KI", p.extreme and "warn" or "info", 2.5)
		elseif p.spec.tvcAlways then msg("F-22: a tolóerő-vektorálás mindig be van kapcsolva", "info")
		else msg("Ezen a gépen nincs tolóerő-vektorálás (F-16 és F-15 ACTIVE)", "warn") end
	elseif k == "g" then
		if p:toggleGear() then msg("FUTÓMŰ " .. (p.fm.gearDown and "KI" or "BE"))
		else msg("A földön nem húzható be a futómű", "warn") end
	end
end

function Match:cycleWeapon(dir)
	if not self:canAct() then return end
	local p = self.player
	local keys = p:weaponKeys()
	local loaded = {}
	for _, k in ipairs(keys) do if p:missileCount(k) > 0 then loaded[#loaded + 1] = k end end
	local list = #loaded > 0 and loaded or keys
	if #list == 0 then return end
	local idx = 0
	for i, k in ipairs(list) do if k == p.selected then idx = i end end
	local n
	if idx == 0 then n = 1 else n = ((idx - 1 + (dir > 0 and 1 or -1)) % #list) + 1 end
	local nextKey = list[n]
	if nextKey ~= p.selected and p:select(nextKey) then
		self.hud:message(nextKey .. "  (" .. p:missileCount(nextKey) .. ")", "info", 1)
	end
end

-- Ctrl+E twice (like the real handle: a deliberate pull): the seat fires, the pilot comes down under the parachute and lives;
-- the jet flies on with nobody at the controls and is lost
function Match:ejectHandle()
	local p, now = self.player, self.clock()
	if not p or not p.alive or p.ejected then return end
	if p.onGround and p.speed < 30 then
		self.hud:message("A földön állva nem katapultálunk – szállj ki rendesen", "info", 2, "eject")
		return
	end
	if self.ejectArm == 0 or now - self.ejectArm > 2.5 then
		self.ejectArm = now
		self.hud:message("KATAPULTÁLÁS: Ctrl+E még egyszer!", "warn", 1.5, "eject")
		return
	end
	self.ejectArm = 0
	p.ejected = true
	p.pilot = { think = noop, fly = function() p.controls.pitch = 0.05; p.controls.roll = 0; p.controls.yaw = 0 end }
	p.trigger = false
	local st = self.state
	st.banner = "KATAPULTÁLTÁL!"
	st.subBanner = "A pilóta életben van – a " .. p.spec.short .. " elveszett  ·  Enter: új gép"
	self.sounds:play("eject")
	self.radio:say("you", (self.opts.callsign or "VIPER 1-1") .. ", EJECTING, EJECTING!")
	self.career.data.ejections = (self.career.data.ejections or 0) + 1
	if self.env.onEject then self.env.onEject(p) end
end

function Match:respawn()
	if self.player and self.player.ejected then
		self.state.banner, self.state.subBanner = "", ""
		if self.env.onRespawn then self.env.onRespawn() end
		self:spawnPlayer()
		return
	end
	if self.race and self.race.finished then
		self.state.banner, self.state.subBanner = "", ""
		self:spawnPlayer()
		return
	end
	if self.state.over then
		self.career.data.matches = self.career.data.matches + 1
		self:restart()
		return
	end
	if self.player and not self.player.alive then
		self.state.banner, self.state.subBanner = "", ""
		self:spawnPlayer()
	end
end
-- a new match with the same options (survival: after the end)
function Match:restart()
	local w = Sim.newWorld(self.terrain, math.floor(self.rnd() * 1e9))
	self.world, self.rnd = w, w.rnd
	self.state = G.freshState()
	self.player, self.wingman, self.killCam, self.race = nil, nil, nil, nil
	self.bt = { charge = 1, active = 0 }
	if self.env.onRestart then self.env.onRestart() end
	self:spawnPlayer()
end

-- ------------------------------------------------------------------ the frame
-- dt: seconds of the frame.  Returns the world's events (also kept in self.events), after the scoring has seen them.
function Match:update(dt)
	local st = self.state
	if not st.paused then
		local bt = self.bt
		if bt.active > 0 then bt.active = math.max(0, bt.active - dt) else bt.charge = math.min(1, bt.charge + dt / 20) end
		local wdt = bt.active > 0 and dt * 0.35 or dt
		self.world:update(wdt)
		if self.race and self.player.alive then self:raceStep(wdt) end
		if self.player.alive and not self.player.ejected and self.carrier.active then self:carrierStep(dt) end
		if self.player.alive and not self.player.onGround then self.career:tick(dt) end
		for _, m in ipairs(self.player.rwr.incoming) do self.threats[m.missile] = true end
		if self.tutorial then self.tutorial:update(dt) end
		self:gameFlow(dt)
	end
	local events = self.world:drainEvents()
	for _, e in ipairs(events) do
		self:onEvent(e[1], e[2])
		self:extraEvent(e[1], e[2])
		if self.tutorial then self.tutorial:onEvent(e[1], e[2]) end
	end
	self.events = events
	local nav = self.nav
	nav.wave, nav.enemies = st.wave, #self:enemiesAlive()
	st.modeLine = self:modeLine()
	st.meatball = self:meatball()
	st.credits = self.hangar.credits and self.hangar:credits() or 0
	return events
end

-- carrier: arresting wires on touchdown, bolters, the catapult; the deck counts as paved for rearming
function Match:carrierStep(dt)
	local p, cv, st = self.player, self.carrier, self.state
	local fm = p.fm
	local on = p.onGround and cv:onDeck(p.pos.x, p.pos.y)
	if on and not self.wasOnDeck and p.speed > 22 then
		if fm.gearDown and cv:inWires(p.pos.x, p.pos.y) then
			fm.arrest, self.catState, self.trapped = 30, nil, true
			local n = cv:wireNumber(p.pos.x, p.pos.y)
			self.hud:message("BEAKADT - " .. n .. ". fékezőkötél" .. (n == 3 and " (tökéletes!)" or ""), "good", 4, "trap")
			if not self.opts.tutorial and not self.opts.benchmark then self:medal("trap") end
			if self.env.onTrap then self.env.onTrap(n) end
		else
			self.hud:message("BOLTER! Teljes gáz, és emelkedj újra", "warn", 3, "trap")
		end
	end
	self.wasOnDeck = on
	if self.trapped and p.speed < 3 then               -- the wire stopped the jet: throttle back, brakes on
		self.trapped, p.controls.throttle, fm.parkBrake, self.towTimer = false, 0, true, 2.5
		self.hud:message("ELKAPVA! A fedélzeti személyzet a katapulthoz vontat...", "good", 3, "trap")
	end
	if self.towTimer > 0 and on then
		self.towTimer = self.towTimer - dt
		if self.towTimer <= 0 then                      -- towed to catapult 1 (rearmed and refuelled by the deck crew)
			local x, y, h = cv:catapult(0)
			fm:placeOnGround(x, y, CarrierLib.DECK_Z, h)
			p.controls.throttle = 0
			p:rearm()
			p.hp, p.burning = p.spec.hp, false
			fm.fuel = p.spec.internalFuel
			if self.env.onCatapultTow then self.env.onCatapultTow() end
			self.hud:message("A KATAPULTON - teljes gáz = kilövés", "info", 4, "trap")
		end
	end
	if fm.parkBrake and ((not on) or p.controls.throttle >= 0.99) then fm.parkBrake = false end
	-- catapult: stopped on the track at full throttle -> 1 s run-up, then the shuttle fires
	local cat = self.catState
	if on and cv:onCatapult(p.pos.x, p.pos.y) and fm.gearDown and p.speed < 3 and p.controls.throttle >= 0.99 and not cat then
		self.catState = { t = 0, fired = false }
		cat = self.catState
		self.hud:message("KATAPULT ÉLESÍTVE...", "warn", 1.5, "cat")
	end
	if cat then
		cat.t = cat.t + dt
		if not cat.fired and cat.t > 1.0 then
			cat.fired, fm.catapultAcc = true, 30
			self.hud:message("KATAPULT!", "good", 2, "cat")
			if self.env.onKick then self.env.onKick(0.8) end
		end
		if cat.fired and ((not p.onGround) or p.speed > 88) then
			fm.catapultAcc, self.catState = 0, nil
			-- off the bow: the aim point goes 12 degrees up so the jet climbs away from the sea
			if self.env.onCatapultOff then self.env.onCatapultOff() end
		end
		if not cat.fired and (p.controls.throttle < 0.99 or not on) then self.catState = nil end
	end
	if st.subBanner == CAT_HINT and not p.onGround then st.subBanner = "" end
end
-- optical landing system: shown while flying an approach to the carrier (behind it, gear down, within 4 km)
function Match:meatball()
	local p = self.player
	if not p or not p.alive or p.onGround or not p.fm.gearDown then return nil end
	local g = self.carrier:glide(p.pos.x, p.pos.y, p.pos.z)
	if not g.behind or g.dist > 4500 or abs(g.off) > 700 then return nil end
	return g
end

function Match:addScore(n)
	self.state.score = self.state.score + n
	if not self.opts.tutorial and not self.opts.benchmark then self.hangar:earn(n) end
end
function Match:medal(id)
	if self.opts.benchmark then return end
	local a = self.career:award(id)
	if not a then return end
	self.hud:showMedal(a)
	self.sounds:play("medal", 0.7)
end

function Match:onEvent(kind, d)
	-- the wingman's own radio calls
	if self.wingman then
		if kind == "launch" and d.missile and d.missile.shooter == self.wingman then self.radio:event("wing_fox") end
		if kind == "kill" and d.killer == self.wingman then self.radio:event("wing_splash") end
	end
	if kind ~= "kill" then return end
	local st, p, scen = self.state, self.player, self:scenario()
	if d.victim == p and p.ejected then
		self.hud:message("Az elhagyott gép lezuhant – a pilóta életben van", "info", 3, "eject")
		return
	end
	if d.victim == p then
		st.deaths, st.streak = st.deaths + 1, 0
		if not self.opts.tutorial then self.career.data.deaths = self.career.data.deaths + 1 end
		if d.killer and d.killer ~= p and d.killer.alive then self.killCam = { killer = d.killer, t = 4 } end
		st.banner = d.weapon ~= "crash" and "LELŐTTEK!" or "LEZUHANTÁL!"
		local again = "Enter: újraéledés"
		st.subBanner = self.opts.tutorial and "Pár másodperc, és újra a levegőben vagy – a lecke elölről indul"
			or (again .. "  ·  Esc: menü (főmenü, új játék)")
		if scen == "duel" and not self.opts.tutorial then
			st.duelLosses, st.duelStreak = st.duelLosses + 1, 0
			st.subBanner = "Párbaj elvesztve  ·  " .. again .. " (új kör)"
		end
		if scen == "survival" then
			local rec = st.score > (self.career.data.bestScore or 0)
			self.career:best("bestScore", st.score)
			self.career:best("bestSurvival", st.wave)
			self.career:save()
			st.over, st.banner = true, "VÉGE"
			st.subBanner = "Túlélés: " .. st.wave .. ". hullám · " .. st.score .. " pont" .. (rec and " · ÚJ REKORD!" or "") .. "  ·  Enter: új játék"
		end
		self.career:save()
	elseif d.killer == p then
		st.kills = st.kills + 1
		local weapon = WEAPON_CLASS[d.weapon] or d.weapon
		if self.opts.tutorial or self.opts.benchmark then return end
		st.streak = st.streak + 1
		local pts = Career.killPoints(weapon, self.opts.difficulty or "normal", st.streak)
		self:addScore(pts)
		self.hud:popup("+" .. pts .. " " .. Career.weaponLabel(weapon) .. (st.streak > 1 and (" ×" .. st.streak) or ""))
		local c = self.career.data
		c.kills = c.kills + 1
		if weapon == "crash" then c.crashKills = c.crashKills + 1
		elseif weapon == "AIM-9M" then c.irKills = c.irKills + 1
		elseif weapon == "AIM-120A" then c.arhKills = c.arhKills + 1
		else c.gunKills = c.gunKills + 1 end
		c.perPlane[p.spec.id] = (c.perPlane[p.spec.id] or 0) + 1
		self.career:best("bestStreak", st.streak)
		self.career:best("bestScore", st.score)
		self.sounds:play("splash", 0.6)
		self:medal("first")
		if weapon == "crash" then self:medal("maneuver") elseif weapon == "AIM-9M" then self:medal("fox2")
		elseif weapon == "AIM-120A" then self:medal("fox3") elseif Career.isGun(weapon) then self:medal("guns") end
		if st.streak >= 5 then self:medal("ace") end
		if d.victim.spec.id == "f22" then self:medal("stealth") end
		c.victims = c.victims or {}
		c.victims[d.victim.spec.id] = (c.victims[d.victim.spec.id] or 0) + 1
		if self.opts.difficulty == "hard" or self.opts.difficulty == "ace" then self:medal("veteran") end
		if st.score >= 5000 then self:medal("score5k") end
		self.career:save()
	elseif d.killer and d.killer == self.wingman and d.victim.team ~= "blue" then
		self:addScore(50)
		self.hud:popup("+50 KÍSÉRŐ", "rgba(115,217,255,0.95)")
		self:medal("team")
	end
end

-- the extra effects of events: medals that do not come from kills
function Match:extraEvent(kind, d)
	local p = self.player
	if not p then return end
	if kind == "hit" and d.target == p then
		if d.missile then self.hitBy[d.missile] = true end
	elseif kind == "launch" and d.shooter == p then
		if not self.opts.tutorial then self.career.data.missilesFired = self.career.data.missilesFired + 1 end
	elseif kind == "missile_end" then
		local m = d.missile
		if self.threats[m] and not self.hitBy[m] and p.alive and not self.opts.tutorial then
			self:addScore(50)
			self.hud:popup("+50 KICSELEZVE", "rgba(115,217,255,0.95)")
			self:medal("evade")
		end
		self.threats[m], self.hitBy[m] = nil, nil
	elseif kind == "cobra" and d.target == p and not self.opts.tutorial then
		self:medal("cobra")
	end
end

-- ring race: passing rings, the finish, a ring missed
function Match:raceStep(dt)
	local p, r, st = self.player, self.race, self.state
	local prev = self.prevPos or copy(p.pos)
	self.prevPos = copy(p.pos)
	local ev = r:update(dt, p, prev)
	local sc = self:scenario()
	local fmt = Race.fmtTime
	if ev == "finish" then self.myFin = (sc == "tube") and r.finalTime or r.time end
	if sc == "tube" and ev == "lap" then
		self:addScore(60)
		self.hud:popup((r.lap - 1) .. ". KÖR  " .. fmt(r.lastLap), "rgba(255,200,64,0.95)")
		self.sounds:play("medal", 0.4)
	elseif sc == "tube" and ev == "out" then
		self.hud:message("KILÓGTÁL A CSŐBŐL – az idő duplán számít", "warn", 2, "race")
	elseif ev == "ring" and sc == "tube" then
		self:addScore(5)
	elseif ev == "ring" then
		self:addScore(20)
		self.hud:popup((sc == "canyon" and "KAPU" or "GYŰRŰ") .. " " .. r.next .. "/" .. #r.rings, "rgba(255,200,64,0.95)")
		self.sounds:play("splash", 0.4)
	elseif ev == "miss" and sc ~= "tube" then
		self.hud:message("MELLÉ! Fordulj vissza a gyűrűhöz", "warn", 2, "race")
	elseif ev == "target" then
		self.world:emit("explosion", { pos = r.targetPos, size = 3, ground = true })
		self:addScore(150)
		self.hud:popup("CÉLPONT MEGSEMMISÍTVE", "rgba(255,90,60,0.95)")
		self.sounds:play("medal", 0.5)
		self.hud:message("CÉLPONT TALÁLVA – most húzd fel meredeken a gerincen át!", "good", 5, "race")
	elseif ev == "radar" then
		self.hud:message("RADARKONTAKT! +5 s – repülj alacsonyabban (350 m alatt)", "warn", 3, "race")
	elseif ev == "finish" and sc == "tube" then
		local reward = 400 + (r.record and 250 or 0)
		self:addScore(reward)
		st.banner = "CÉL!  " .. fmt(r.finalTime) .. "  (" .. r.laps .. " kör)"
		st.subBanner = (r.record and "ÚJ REKORD! · " or ("rekord: " .. fmt(r.best) .. " · ")) .. "legjobb kör " .. fmt(r.bestLap)
			.. (r.penalty > 0.5 and (" · csőből kilógás +" .. string.format("%.1f", r.penalty) .. " s") or "") .. " · +" .. reward .. " kredit  ·  Enter: újra"
		self.sounds:play("medal", 0.7)
		self.career:save()
	elseif ev == "finish" and sc == "canyon" then
		local reward = r.success and (500 + (r.record and 250 or 0)) or 100
		self:addScore(reward)
		st.banner = r.success and ("KÜLDETÉS TELJESÍTVE  " .. fmt(r.time)) or ("TÚL LASSÚ  " .. fmt(r.time))
		st.subBanner = (r.success and (r.record and "ÚJ REKORD! · " or ("rekord: " .. fmt(r.best) .. " · ")) or ("a határidő " .. fmt(Race.CANYON_LIMIT) .. " volt · "))
			.. "+" .. reward .. " kredit  ·  Enter: újra"
		self.sounds:play(r.success and "medal" or "splash", 0.7)
		self.career:save()
	elseif ev == "finish" then
		local reward = 300 + (r.record and 200 or 0)
		self:addScore(reward)
		st.banner = "CÉL!  " .. fmt(r.time)
		st.subBanner = (r.record and "ÚJ REKORD! · " or ("rekord: " .. fmt(r.best) .. " · ")) .. "+" .. reward .. " kredit  ·  Enter: újra"
		self.sounds:play("medal", 0.7)
		self.career:best("bestScore", st.score)
		self.career:save()
	end
	return ev
end

function Match:modeLine()
	local st, sc = self.state, self:scenario()
	if self.opts.tutorial then return "" end
	local fmt = Race.fmtTime
	local friend = self.env.friendLine and self.env.friendLine() or ""
	if sc == "race" and self.race then
		local r = self.race
		return "GYŰRŰVERSENY · " .. math.min(r.next, #r.rings) .. "/" .. #r.rings .. " · " .. fmt(r.time) .. " · rekord " .. fmt(r.best) .. friend
	end
	if sc == "tube" and self.race then
		local r = self.race
		return "ALAGÚTFUTAM · kör " .. r.lap .. "/" .. r.laps .. " · " .. fmt(r.clock) .. (r.lastLap and (" · utolsó " .. fmt(r.lastLap)) or "")
			.. (r.bestLap and (" · legjobb " .. fmt(r.bestLap)) or "") .. (r.outside and " · KILÓGSZ A CSŐBŐL" or "") .. friend
	end
	if sc == "pvp" then
		local sc2 = self.env.teamScore and self.env.teamScore() or { blue = 0, red = 0 }
		return "CSAPATHARC · KÉK " .. sc2.blue .. " : " .. sc2.red .. " PIROS · te: " .. (self.env.netTeam == "red" and "PIROS" or "KÉK")
	end
	if sc == "free" then return "KÖZÖS REPÜLÉS" .. (self.env.friendLine and " · a barátoddal" or " · egyedül") end
	if sc == "canyon" and self.race then
		local r = self.race
		local t = r.time + r.penalty
		local left = Race.CANYON_LIMIT - t
		return "KANYONFUTÁS · " .. (r.hit and "célpont találva · húzz fel!" or "cél: a völgy végén") .. " · " .. fmt(t) .. " / " .. fmt(Race.CANYON_LIMIT)
			.. (left < 0 and " · LEJÁRT" or "") .. (r.penalty > 0 and (" · radar +" .. r.penalty .. " s") or "") .. " · rekord " .. fmt(r.best) .. friend
	end
	if sc == "duel" then
		return "PÁRBAJ · győzelem " .. st.duelWins .. " · vereség " .. st.duelLosses .. (st.duelStreak > 1 and (" · " .. st.duelStreak .. " egymás után") or "")
	end
	if sc == "survival" then return "TÚLÉLÉS · egy életed van · rekord: " .. (self.career.data.bestSurvival or 0) .. ". hullám" end
	if self.guest then return "KÖZÖS HARC · " .. (st.wave or 0) .. ". hullám (a szoba nyitója vezeti)" end
	if self.wingman then
		return "KÍSÉRŐ: " .. (self.wingman.alive and "a levegőben" or "lelőtték, a következő hullámmal visszajön")
	end
	return ""
end

function Match:gameFlow(dt)
	local st, p = self.state, self.player
	if not p.alive then return end
	local terrain = self.terrain
	local field = terrain.airfield
	local airborne = (not p.onGround) and p.pos.z - terrain:height(p.pos.x, p.pos.y) > 150
	if (st.subBanner == TAKEOFF_HINT or st.subBanner == TAKEOFF_HINT_NOAB) and airborne then
		st.subBanner = ""
		self.hud:message("SIKERES FELSZÁLLÁS - húzd be a futóművet (G)", "good", 4)
	end
	local sc = self:scenario()
	if sc == "race" or sc == "canyon" or sc == "tube" or sc == "free" or sc == "pvp" then return end
	local runsWaves = not self.guest                        -- the host's machine runs the enemies
	-- reinforcements: the rest of a big wave comes in groups, when the first ones are thinned out (or after a while)
	if runsWaves and not self.opts.tutorial and st.waveActive and st.reserve > 0 then
		st.reserveT = st.reserveT + dt
		if #self:enemiesAlive() <= 1 or st.reserveT > REINFORCE_GAP then
			local n = math.min(st.reserve, 3)
			self:spawnEnemies(n, 6000)
			st.reserve, st.reserveT = st.reserve - n, 0
			self.hud:message("ERŐSÍTÉS: még " .. n .. " ellenség érkezik" .. (st.reserve > 0 and (" (utána még " .. st.reserve .. ")") or ""), "warn", 4, "reinf")
		end
	end
	if runsWaves and not self.opts.tutorial and st.waveActive and not (st.reserve > 0) and #self:enemiesAlive() == 0 then
		st.waveActive, st.waveTimer = false, WAVE_DELAY
		if sc == "duel" then
			st.duelWins, st.duelStreak = st.duelWins + 1, st.duelStreak + 1
			self:addScore(300)
			self.career.data.duelWins = self.career.data.duelWins + 1
			self.hud:popup("+300 PÁRBAJ", "rgba(255,200,64,0.95)")
			self.hud:message("PÁRBAJ MEGNYERVE - a következő ellenfél pár másodperc múlva jön", "good", 4)
			if st.duelStreak >= 3 then self:medal("duel3") end
			st.waveTimer = 4
		else
			local bonus = 100 * st.wave
			self:addScore(bonus)
			self.hud:popup("+" .. bonus .. " HULLÁM", "rgba(255,200,64,0.95)")
			if sc == "survival" then
				st.waveTimer = 4
				self.hud:message("HULLÁM TELJESÍTVE - a következő mindjárt jön", "good", 4)
			else
				self.hud:message("HULLÁM TELJESÍTVE - leszállhatsz a bázison újrafegyverezni", "good", 5)
			end
		end
		self.career:best("bestScore", st.score)
		self.career:save()
	end
	if runsWaves and not self.opts.tutorial and self:wantWingman() and not self.wingman and airborne then self:spawnWingman() end
	if runsWaves and not self.opts.tutorial and not st.waveActive and airborne then
		st.waveTimer = st.waveTimer - dt
		if st.waveTimer <= 0 then self:spawnWave() end
	end
	-- arcade: every fired missile comes back on its rail RELOAD_TIME seconds later
	if self.opts.mode == "arcade" then
		for _, s in ipairs(p.stations) do
			if s.loaded then
				s.reload = nil
			else
				s.reload = (s.reload or RELOAD_TIME) - dt
				if s.reload <= 0 then
					s.loaded, s.reload = true, nil
					p:updateStores()
					if not p.selected or p:missileCount(p.selected) == 0 then p:select(s.key) end
					self.hud:message(s.key .. " ÚJRATÖLTVE", "good", 1.5, "reload")
				end
			end
		end
		-- the gun and the flare / chaff dispensers refill too (full in 10 s, after a 2 s pause)
		self.gunIdle = p.gun.firing and 0 or (self.gunIdle or 0) + dt
		self.cmIdle = p.cmHold and 0 or (self.cmIdle or 0) + dt
		local function refill(have, max, idle, key)
			if have >= max or idle < 2 then self[key] = 0; return have end
			self[key] = (self[key] or 0) + max / RELOAD_TIME * dt
			local n = math.floor(self[key])
			self[key] = self[key] - n
			return math.min(max, have + n)
		end
		p.gun.ammo = refill(p.gun.ammo, p.spec.gun.ammo, self.gunIdle, "ammoAcc")
		p.flares = refill(p.flares, p.spec.cm.flares, self.cmIdle, "flareAcc")
		p.chaff = refill(p.chaff, p.spec.cm.chaff, self.cmIdle, "chaffAcc")
	end
	if self.hangar:modOn("infcm") and not self.opts.benchmark then p.flares, p.chaff = p.spec.cm.flares, p.spec.cm.chaff end
	-- landing on the base (on the concrete, slowed down) rearms, refuels and repairs at once
	local needs = p.hp < p.spec.hp or p.fm.fuel < p.spec.internalFuel * 0.95 or p.gun.ammo < p.spec.gun.ammo or p.flares < p.spec.cm.flares
	if not needs then
		for _, s in ipairs(p.stations) do if not s.loaded then needs = true end end
	end
	if p.onGround and p.speed < 25 and needs and field:onPaved(p.pos.x, p.pos.y) then
		p:rearm()
		p.hp, p.burning = p.spec.hp, false
		p.fm.fuel = p.spec.internalFuel
		for _, s in ipairs(p.stations) do s.reload = nil end
		self.hud:message("ÚJRAFEGYVERZÉS, TANKOLÁS, JAVÍTÁS KÉSZ", "good", 4, "service")
		if not self.opts.tutorial then self:medal("home") end
	end
end

G.SPLASH = SPLASH
return G
