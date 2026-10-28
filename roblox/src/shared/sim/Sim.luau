--!nonstrict
-- Aircraft + World: the port of web/js/sim.js.  The simulation steps at 100 Hz (PHYS_DT), the sensors at 30 Hz, the AI at 10 Hz.
local M = require(script.Parent.SimMath)
local Flight = require(script.Parent.Flight)
local Specs = require(script.Parent.Specs)
local Weapons = require(script.Parent.Weapons)
local V, add, sub, mul, len, copy, norm, qheading, xform, DEG = M.V, M.add, M.sub, M.mul, M.len, M.copy, M.norm, M.qheading, M.xform, M.DEG
local IR, ARH, MISSILES = Specs.IR, Specs.ARH, Specs.MISSILES
local STT = Weapons.STT

local S = {}
local STORE_DRAG_AREA = 0.031                       -- m^2 of drag area per missile with its launcher
local ASSIST_IR_FOV, ASSIST_IR_CONE = 10, 30        -- player lock assist: seeker search cone / F-key cone (deg)
S.PHYS_DT, S.SENSOR_DT, S.AI_DT = 1 / 100, 1 / 30, 1 / 10
local PHYS_DT, SENSOR_DT, AI_DT = S.PHYS_DT, S.SENSOR_DT, S.AI_DT

-- ------------------------------------------------------------------ the aircraft
local Aircraft = {}
local getters = {
	pos = function(t) return t.fm.pos end,
	vel = function(t) return t.fm.vel end,
	quat = function(t) return t.fm.quat end,
	forward = function(t) return t.fm.forward end,
	speed = function(t) return t.fm.speed end,
	mach = function(t) return t.fm.mach end,
	engineSetting = function(t) return t.alive and t.fm.engine or 0 end,
	damaged = function(t) return t.hp < t.spec.hp * 0.5 end,
	onGround = function(t) return t.fm.onGround end,
	selectedSpec = function(t) return t.selected and t:missileSpec(t.selected) or nil end,
	extreme = function(t) return t.fm.extreme end,
	bayOpenAny = function(t)
		if not t.spec.bays then return 0 end
		return math.max(t:bayOpen("main"), t:bayOpen("side_L"), t:bayOpen("side_R"))
	end,
}
Aircraft.__index = function(t, k)
	local m = Aircraft[k]
	if m ~= nil then return m end
	local g = getters[k]
	if g then return g(t) end
	return nil
end

-- opts: isPlayer, livery, rnd, loadout (a name or { station = weapon }), missiles, lockAssist, blastMult, ...
function S.newAircraft(spec, name, team, pos, headingDeg, speed, opts)
	opts = opts or {}
	local self = setmetatable({}, Aircraft)
	self.spec, self.name, self.team = spec, name, team
	self.isPlayer = opts.isPlayer == true
	self.livery = opts.livery or "viper"
	self.rnd = opts.rnd or M.rng(math.floor(os.clock() * 1e6) % 1000000000)
	local q = qheading(headingDeg, 0)
	self.fm = Flight.new(spec, pos, mul(xform(q, V(0, 1, 0)), speed), q)
	self.fm.engine = 0.9
	self.controls = Flight.newControls(0.9)
	self.trigger = false
	self.gun = Weapons.newGun(spec.gun, self.rnd)
	self.loadout = opts.loadout or "default"
	self.stations, self.selected = {}, nil
	self.radar = Weapons.newRadar(spec.radar, self, self.rnd)
	self.missiles = opts.missiles or MISSILES          -- the player's and the enemies' missiles differ
	self.irSeeker = Weapons.newIRSeeker(self.missiles["AIM-9M"] or MISSILES["AIM-9M"], self.rnd)
	self.rwr = Weapons.newRWR(self)
	self.flares, self.chaff, self.cmHold, self.cmTimer = spec.cm.flares, spec.cm.chaff, false, 0
	self.hp, self.alive, self.burning, self.crashed, self.deathTime = spec.hp, true, false, false, nil
	self.kills, self.lastAttacker, self.lastHitTime, self.pilot = 0, nil, -1e9, nil
	self.lockAssist, self.irAutoHold = opts.lockAssist == true, 0
	self.outfit = opts.outfit
	self.skin, self.blastMult, self.tracerColor = opts.skin, opts.blastMult or 1, opts.tracerColor
	self.fm.extreme = spec.tvcAlways == true             -- the F-22's thrust vectoring is always on
	self:rearm()
	return self
end

function Aircraft:rearm()
	-- a loadout is a name from spec.loadouts or a { station = weapon } table (the menu's loadout editor)
	local layout = self.loadout
	if type(layout) ~= "table" then layout = self.spec.loadouts[layout] or self.spec.loadouts.default end
	local nums = {}
	for n in pairs(layout) do
		local ok = self.spec.stations[n] and (not self.spec.pylons[n])
		if self.spec.stations[n] and self.spec.pylons[n] then
			for _, k in ipairs(self.spec.pylons[n]) do if k == layout[n] then ok = true end end
		end
		if ok then nums[#nums + 1] = n end
	end
	table.sort(nums)
	self.stations = {}
	for _, n in ipairs(nums) do
		local m = self.spec.stations[n]
		self.stations[#self.stations + 1] = { number = n, key = layout[n], spec = self:missileSpec(layout[n]), mount = V(m[1], m[2], m[3]), loaded = true, launch = nil }
	end
	self.gun:reload()
	self.flares, self.chaff = self.spec.cm.flares, self.spec.cm.chaff
	if not self.selected or self:missileCount(self.selected) == 0 then self.selected = self.stations[1] and self.stations[1].key or nil end
	self:updateStores()
end

function Aircraft:updateStores()
	local mass, n = 0, 0
	for _, s in ipairs(self.stations) do
		if s.loaded then mass = mass + s.spec.mass; n = n + 1 end
	end
	self.fm.storeMass = mass
	self.fm.storeCd = self.spec.bays and 0 or STORE_DRAG_AREA * n / self.spec.wingArea       -- F-22: all inside
end
function Aircraft:missileCount(key)
	local n = 0
	for _, s in ipairs(self.stations) do if s.loaded and not s.launch and s.key == key then n = n + 1 end end
	return n
end
function Aircraft:weaponKeys()
	local out, seen = {}, {}
	for _, s in ipairs(self.stations) do
		if not seen[s.key] then seen[s.key] = true; out[#out + 1] = s.key end
	end
	return out
end
function Aircraft:missileSpec(key) return self.missiles[key] or MISSILES[key] end
function Aircraft:select(key)
	local has = false
	for _, k in ipairs(self:weaponKeys()) do if k == key then has = true end end
	if not has then return false end
	self.selected = key
	self.irSeeker:reset()
	return true
end
function Aircraft:toggleGear() return self.fm:setGear(not self.fm.gearDown) end
-- F-16 extreme mode (thrust vectoring); false when the jet has none
function Aircraft:toggleExtreme()
	if not self.spec.tvc or self.spec.tvcAlways then return false end
	self.fm.extreme = not self.fm.extreme
	return true
end

function Aircraft:physicsStep(dt, world)
	if self.crashed or self.ghost then return end
	if self.alive then
		self.fm:step(dt, self.controls, world.terrain)
		local ev = self.fm.contactEvent
		if ev == "crash" then self:crash(world, self.fm.crashReason); return end
		if ev == "tailstrike" then
			world:emit("message", { to = self, text = "FAROKÜTÉS!", level = "bad" })
			self:takeDamage(30, nil, "tailstrike", world)
		elseif ev == "touchdown" and self.fm.sinkRate > 3 then
			world:emit("message", { to = self, text = "KEMÉNY LANDOLÁS", level = "warn" })
		end
		self.gun:update(dt, self, self.trigger, world)
		if self.spec.bays then self:updateLaunches(dt, world) end
		self.cmTimer = self.cmTimer - dt
		if self.cmHold then self:dispense(world) end
	else
		local wreck = Flight.newControls(0)
		wreck.pitch, wreck.roll = -0.3, 0.9
		self.fm:step(dt, wreck, nil)
		self.gun.firing = false
		if self.pos.z <= world.terrain:height(self.pos.x, self.pos.y) + 1.5 then self:crash(world) end
	end
end

function Aircraft:sensorStep(dt, world)
	if not self.alive or (self.ghost and not self.slave) then return end          -- (the rear seat's copy of the pilot's jet looks round too)
	local r = self.radar
	r:update(dt, world)
	local msgs = { locked = { "RADAR LOCK", "good" }, lost = { "LOCK LOST", "warn" }, decoyed = { "LOCK LOST - CHAFF", "warn" } }
	local msg = r.lastEvent and msgs[r.lastEvent]
	if msg then world:emit("message", { to = self, text = msg[1], level = msg[2] }) end
	local sp = self.selectedSpec
	if sp and sp.guidance == IR then
		if self.irSeeker.spec ~= sp then self.irSeeker = Weapons.newIRSeeker(sp, self.rnd) end
		self.irSeeker.acqFov = self.lockAssist and ASSIST_IR_FOV or nil
		local slave = (r.mode == STT and r.trackPos) and norm(sub(r.trackPos, self.pos)) or nil
		local res = self.irSeeker:update(dt, self.pos, self.forward, world:heatSources(), world.terrain, slave, self)
		if res == "lost" then world:emit("message", { to = self, text = "SEEKER LOST", level = "warn" })
		elseif res == "decoyed" then world:emit("message", { to = self, text = "SEEKER ON FLARE", level = "warn" }) end
		if slave and not self.irSeeker.locked and self.irSeeker.candidate == r.locked then self.irSeeker:lock() end
		-- lock assist: the seeker locks by itself onto an enemy in its (wide) search cone
		self.irAutoHold = self.irAutoHold - dt
		local c = self.irSeeker.candidate
		if self.lockAssist and self.irAutoHold <= 0 and not self.irSeeker.locked and c and not c.isFlare and c.team ~= self.team then
			self.irSeeker:lock()
			world:emit("message", { to = self, text = "SEEKER LOCK - Space: indítás", level = "good" })
		end
	end
	self.rwr:update(world)
end

function Aircraft:toggleIrLock(world)
	local sp = self.selectedSpec
	if not sp or sp.guidance ~= IR then return false end
	if self.irSeeker.locked then
		self.irSeeker:unlock()
		self.irAutoHold = 3
		return false
	end
	if self.lockAssist and world and not self.irSeeker.candidate then
		-- nothing in the seeker: look for the hottest enemy within a wide cone around the nose
		local s = self.irSeeker:bestInCone(self.pos, self.forward, world:heatSources(), ASSIST_IR_CONE * DEG, world.terrain, self)
		if s and not s.isFlare and s.team ~= self.team then self.irSeeker.candidate = s end
	end
	return self.irSeeker:lock()
end

function Aircraft:fireMissile(world)
	if not self.alive or not self.selected then return nil end
	local byNum = {}
	for _, s in ipairs(self.stations) do byNum[s.number] = s end
	local st = nil
	for _, n in ipairs(self.spec.firingOrder) do
		local s = byNum[n]
		if s and s.loaded and not s.launch and s.key == self.selected then st = s; break end
	end
	if not st then
		world:emit("message", { to = self, text = "NINCS TÖBB " .. self.selected, level = "warn" })
		return nil
	end
	local sp = st.spec
	local target, axis = nil, nil
	if sp.guidance == IR then
		target = self.irSeeker.target
		axis = self.irSeeker.axis and self.irSeeker.axis:clone() or nil
	else
		target = self.radar.mode == STT and self.radar.locked or nil
	end
	if self.spec.bays then
		-- internal bay: the door opens and the launcher swings the missile out first (updateLaunches)
		st.launch = { t = 0, target = target, axis = axis, released = false, timing = self.spec.launch[st.key] }
		if sp.guidance == IR then self.irSeeker:reset() end
		self:afterLaunch()
		return { spec = sp, pending = true }
	end
	local m = self:release(st, target, axis, world, math.abs(st.mount.x) > 4.5 and 0 or 4)
	if sp.guidance == IR then self.irSeeker:reset() end
	self:afterLaunch()
	return m
end
-- the rear seat shoots: a missile of the given kind at the given target, whatever the radar of the jet says (nil: not launched)
function Aircraft:fireFrom(world, key, target)
	if not self.alive or self.ejected then return nil end
	local byNum = {}
	for _, s in ipairs(self.stations) do byNum[s.number] = s end
	local st = nil
	for _, n in ipairs(self.spec.firingOrder) do
		local s = byNum[n]
		if s and s.loaded and not s.launch and s.key == key then st = s; break end
	end
	if not st then return nil end
	if target and (not target.alive or target.team == self.team) then target = nil end
	local sp = st.spec
	local axis = nil
	if sp.guidance == IR and target then axis = norm(sub(target.pos, self.pos)) end
	if self.spec.bays then
		st.launch = { t = 0, target = target, axis = axis, released = false, timing = self.spec.launch[st.key] }
		self:afterLaunch()
		return { spec = sp, pending = true }
	end
	local m = self:release(st, target, axis, world, math.abs(st.mount.x) > 4.5 and 0 or 4)
	self:afterLaunch()
	return m
end
function Aircraft:release(st, target, axis, world, eject)
	local q = self.quat
	local pos = add(self.pos, xform(q, st.mount))
	local vel = sub(self.vel, mul(self.fm.up, eject))
	local m = Weapons.newMissile(st.spec, self, pos, vel, self.forward, self.rnd, target, axis)
	st.loaded = false
	self:updateStores()
	world:addMissile(m)
	return m
end
function Aircraft:afterLaunch()
	if self:missileCount(self.selected) == 0 then
		for _, k in ipairs(self:weaponKeys()) do
			if self:missileCount(k) > 0 then self:select(k); break end
		end
	end
end
-- F-22 launch sequences: door open -> launcher out -> release -> launcher back -> door closed
function Aircraft:updateLaunches(dt, world)
	for _, st in ipairs(self.stations) do
		local L = st.launch
		if L then
			L.t = L.t + dt
			local T = L.timing
			if not L.released and L.t >= T.release then
				L.released = true
				local target = L.target
				if st.spec.guidance == IR and self.irSeeker.locked then target = self.irSeeker.target end
				if st.spec.guidance == ARH then target = (self.radar.mode == STT) and self.radar.locked or L.target end
				self:release(st, (target and target.alive ~= false) and target or nil, L.axis, world, T.eject)
			end
			if L.t >= T.close[2] then st.launch = nil end
		end
	end
end
-- 0..1: how far the launcher of station st is out; how open the doors of a bay group are
function Aircraft:rackOut(st)
	local L = st.launch
	if not L then return 0 end
	local T = L.timing
	local function ramp(a, b) return math.min(1, math.max(0, (L.t - a) / (b - a))) end
	if L.t < T.back[1] then return ramp(T.out[1], T.out[2]) end
	return 1 - ramp(T.back[1], T.back[2])
end
function Aircraft:bayOpen(group)
	local open = 0
	for _, st in ipairs(self.stations) do
		local L = st.launch
		if L and self.spec.bays[st.number] == group then
			local T = L.timing
			local o
			if L.t < T.close[1] then o = math.min(1, L.t / T.open)
			else o = 1 - math.min(1, (L.t - T.close[1]) / (T.close[2] - T.close[1])) end
			open = math.max(open, o)
		end
	end
	return open
end

function Aircraft:dispense(world)
	if self.cmTimer > 0 or (self.flares <= 0 and self.chaff <= 0) then return end
	self.cmTimer = self.spec.cm.interval
	local down = mul(self.fm.up, -1)
	if self.flares > 0 then
		self.flares = self.flares - 1
		local side = mul(self.fm.right, self.rnd.uniform(-12, 12))
		world:addFlare(Weapons.newFlare(add(self.pos, mul(down, 1.5)), add(add(mul(self.vel, 0.96), mul(down, 22)), side), self.spec.cm))
	end
	if self.chaff > 0 then
		self.chaff = self.chaff - 1
		world:addChaff(Weapons.newChaff(add(self.pos, mul(down, 1.5)), self.vel, self.spec.cm))
	end
end

function Aircraft:takeDamage(amount, source, weapon, world)
	if not self.alive then return end
	if self.invulnerable then world:emit("shielded", { target = self, source = source, weapon = weapon }); return end     -- tutorial
	self.hp = self.hp - amount
	self.lastAttacker, self.lastHitTime = source, world.time
	if self.hp < self.spec.hp * 0.3 then self.burning = true end
	if self.hp <= 0 then self:kill(world, source, weapon) end
end
function Aircraft:kill(world, killer, weapon)
	if not self.alive then return end
	self.alive, self.burning, self.hp, self.trigger, self.cmHold = false, true, 0, false, false
	self.deathTime = world.time
	if self.radar.on then self.radar:togglePower() end
	if killer and killer ~= self then killer.kills = killer.kills + 1 end
	world:emit("kill", { victim = self, killer = killer, weapon = weapon })
end
function Aircraft:crash(world, reason)
	if self.crashed then return end
	if self.alive then
		local recent = (world.time - self.lastHitTime < 30) and self.lastAttacker or nil
		if reason and reason ~= "" then world:emit("message", { to = self, text = "BALESET: " .. reason, level = "bad" }) end
		self:kill(world, recent, "crash")
	end
	self.crashed = true
	self.fm.vel = V()
	world:emit("explosion", { pos = copy(self.pos), size = 2.5, ground = true })
end

-- ------------------------------------------------------------------ the world
local World = {}
World.__index = World
function S.newWorld(terrain, seed)
	local w = setmetatable({}, World)
	w.terrain, w.rnd = terrain, M.rng(seed or 1)
	w.aircraft, w.missiles, w.bullets, w.flares, w.chaff, w.events = {}, {}, {}, {}, {}, {}
	w.time, w.acc, w.sensorAcc, w.aiAcc = 0, 0, 0, 0
	return w
end
function World:emit(kind, data) self.events[#self.events + 1] = { kind, data } end
function World:drainEvents()
	local e = self.events
	self.events = {}
	return e
end
function World:addAircraft(a) self.aircraft[#self.aircraft + 1] = a; return a end
function World:addMissile(m)
	self.missiles[#self.missiles + 1] = m
	self:emit("launch", { missile = m, shooter = m.shooter })
end
function World:addFlare(f) self.flares[#self.flares + 1] = f; self:emit("flare", { flare = f }) end
function World:addChaff(c) self.chaff[#self.chaff + 1] = c; self:emit("chaff", { chaff = c }) end
function World:heatSources()
	local out = {}
	for _, a in ipairs(self.aircraft) do
		if a.alive or (a.burning and not a.crashed) then out[#out + 1] = a end
	end
	for _, f in ipairs(self.flares) do out[#out + 1] = f end
	return out
end
function World:enemiesOf(a)
	local out = {}
	for _, o in ipairs(self.aircraft) do
		if o.team ~= a.team and o.alive then out[#out + 1] = o end
	end
	return out
end
local function filterAlive(list)
	local out = {}
	for _, x in ipairs(list) do if x.alive then out[#out + 1] = x end end
	return out
end
function World:update(frameDt)
	frameDt = math.min(frameDt, 0.1)
	self.acc = self.acc + frameDt
	local steps = 0
	while self.acc >= PHYS_DT do
		self:physics(PHYS_DT)
		self.acc = self.acc - PHYS_DT
		steps = steps + 1
		if steps >= 12 then self.acc = 0; break end
	end
	Weapons.updateBullets(self, frameDt)
	self.missiles = filterAlive(self.missiles)
	self.flares = filterAlive(self.flares)
	self.chaff = filterAlive(self.chaff)
	local keep = {}
	for _, a in ipairs(self.aircraft) do
		if a.isPlayer or not a.crashed or self.time - a.deathTime < 8 then keep[#keep + 1] = a end
	end
	self.aircraft = keep
end
function World:physics(dt)
	self.time = self.time + dt
	for _, a in ipairs(self.aircraft) do if a.pilot and a.alive then a.pilot:fly(dt, self) end end
	for _, a in ipairs(self.aircraft) do a:physicsStep(dt, self) end
	for _, m in ipairs(self.missiles) do m:update(dt, self) end
	for _, f in ipairs(self.flares) do f:update(dt) end
	for _, c in ipairs(self.chaff) do c:update(dt) end
	self.sensorAcc = self.sensorAcc + dt
	if self.sensorAcc >= SENSOR_DT then
		for _, a in ipairs(self.aircraft) do a:sensorStep(self.sensorAcc, self) end
		self.sensorAcc = 0
	end
	self.aiAcc = self.aiAcc + dt
	if self.aiAcc >= AI_DT then
		for _, a in ipairs(self.aircraft) do if a.pilot and a.alive then a.pilot:think(self) end end
		self.aiAcc = 0
	end
end
function World:detonate(m, pos, ground, selfDestruct)
	if not m.alive then return end
	m.alive = false
	local sp = m.spec
	local k = (m.shooter and m.shooter.blastMult) or 1          -- hangar mod: bigger blast
	local rLethal, rDamage = sp.lethalRadius * k, sp.damageRadius * k
	for _, ac in ipairs(self.aircraft) do
		if ac.alive then
			local d = len(sub(ac.pos, pos))
			if d < rDamage then
				local dmg = d <= rLethal and sp.damage or sp.damage * (1 - (d - rLethal) / (rDamage - rLethal))
				self:emit("hit", { target = ac, pos = copy(ac.pos), shooter = m.shooter, missile = m })
				ac:takeDamage(dmg, m.shooter, sp.name, self)
			end
		end
	end
	self:emit("explosion", { pos = copy(pos), size = (selfDestruct and 0.8 or (sp.damage >= 150 and 1.6 or 1.2)) * (k > 1 and 1.5 or 1), ground = ground or false })
	self:emit("missile_end", { missile = m })
end

return S
