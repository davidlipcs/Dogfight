--!nonstrict
-- Sensors and weapons: IR seeker, radar, RWR, missiles, gun, decoys - the port of web/js/weapons.js.
local M = require(script.Parent.SimMath)
local Flight = require(script.Parent.Flight)
local Specs = require(script.Parent.Specs)
local G, DEG, V = M.G, M.DEG, M.V
local add, sub, mul, dot, cross, len, norm, copy, clamp = M.add, M.sub, M.mul, M.dot, M.cross, M.len, M.norm, M.copy, M.clamp
local smoothstep, angleBetween, interp, rotateTowards, closestApproach, toLocal, xform = M.smoothstep, M.angleBetween, M.interp, M.rotateTowards, M.closestApproach, M.toLocal, M.xform
local isa = Flight.isa
local IR, ARH = Specs.IR, Specs.ARH
local sqrt, exp, atan2 = math.sqrt, math.exp, M.atan2

local W = {}

-- ------------------------------------------------------------------ signatures
local function irIntensityRaw(src, obs)
	if not src.alive and not src.burning then return 0 end
	local toObs = norm(sub(obs, src.pos))
	local rear = -dot(src.forward, toObs)
	local nozzle = 0.15 + 0.85 * smoothstep(-0.35, 0.95, rear)
	local e = src.engineSetting
	local heat, plume = 0, 0
	if e > 1 then
		heat = 2.0 + 0.4 * (e - 1) / 0.1
		plume = 0.35
	else
		heat = 0.25 + 0.75 * clamp(e, 0, 1) ^ 1.5
	end
	return heat * nozzle + plume + 0.06 * src.mach * src.mach + (src.burning and 1.5 or 0)
end
function W.irIntensity(src, obs)
	if src.isFlare then return src.intensity end
	local scale = 1
	if src.spec and src.spec.irScale then scale = src.spec.irScale end     -- F-22: cooler, shielded exhaust
	return irIntensityRaw(src, obs) * scale
end
local irIntensity = W.irIntensity
function W.irLockRange(base, I)
	if I <= 0 then return 0 end
	return math.min(base * sqrt(I), base * 1.5)
end
local irLockRange = W.irLockRange
function W.rcs(tgt, obs)
	local toObs = norm(sub(obs, tgt.pos))
	local side = 1 - math.abs(dot(tgt.forward, toObs))
	local r = tgt.spec.rcsFront + (tgt.spec.rcsSide - tgt.spec.rcsFront) * side
	-- F-22 with a weapons bay door open: the cavity and the missile shine on radar for a moment
	if tgt.spec.rcsBay and tgt.bayOpenAny > 0.2 then return math.max(r, tgt.spec.rcsBay * tgt.bayOpenAny) end
	return r
end
local rcs = W.rcs
function W.radarRange(base, r) return base * (math.max(r, 1e-5) / 5) ^ 0.25 end       -- no floor: stealth works
local radarRange = W.radarRange
function W.radialSpeed(vel, obs, pos) return dot(vel, norm(sub(pos, obs))) end
local radialSpeed = W.radialSpeed

-- ------------------------------------------------------------- countermeasures
local ids = 1
local Flare = {}
Flare.__index = function(t, k)
	if k == "intensity" then
		if t.age < 0.15 then return t.peak * t.age / 0.15 end
		return t.peak * math.max(0, 1 - (t.age - 0.15) / (t.life - 0.15)) ^ 0.7
	end
	return Flare[k]
end
function W.newFlare(pos, vel, cm)
	local f = setmetatable({}, Flare)
	f.id = ids
	ids = ids + 1
	f.isFlare, f.alive = true, true
	f.pos, f.vel, f.age, f.life, f.peak = copy(pos), copy(vel), 0, cm.flareLife, cm.flareIntensity
	return f
end
function Flare:update(dt)
	self.age = self.age + dt
	local s = len(self.vel)
	self.vel:scale(1 - math.min(1, 0.0025 * s * dt))
	self.vel.z = self.vel.z - G * dt
	self.pos:addScaled(self.vel, dt)
	if self.age >= self.life then self.alive = false end
end

local Chaff = {}
Chaff.__index = Chaff
function W.newChaff(pos, vel, cm)
	local c = setmetatable({}, Chaff)
	c.id = ids
	ids = ids + 1
	c.isChaff, c.alive = true, true
	c.pos, c.vel, c.age, c.life = copy(pos), mul(vel, 0.3), 0, cm.chaffLife
	return c
end
function Chaff:update(dt)
	self.age = self.age + dt
	self.vel:scale(1 - math.min(1, 3 * dt))
	self.vel.z = self.vel.z - 1.5 * dt
	self.pos:addScaled(self.vel, dt)
	if self.age >= self.life then self.alive = false end
end

-- --------------------------------------------------------------------- IR seeker
local IRSeeker = {}
IRSeeker.__index = function(t, k)
	if k == "locked" then return t.target ~= nil end
	return IRSeeker[k]
end
function W.newIRSeeker(spec, rnd)
	local s = setmetatable({}, IRSeeker)
	s.spec, s.rnd, s.axis, s.target, s.candidate, s.judged = spec, rnd, nil, nil, nil, {}
	s.acqFov = nil              -- wider search cone (deg) for the player's lock assist; nil = real seeker FOV
	s.snap = false
	return s
end
function IRSeeker:reset() self.target, self.candidate, self.judged = nil, nil, {} end
function IRSeeker:visible(src, origin, terrain)
	if not src.alive then return false end
	local d = len(sub(src.pos, origin))
	if d > irLockRange(self.spec.seekerRange, irIntensity(src, origin)) then return false end
	return (not terrain) or terrain:lineOfSight(origin, src.pos)
end
function IRSeeker:bestInCone(origin, axis, sources, half, terrain, exclude)
	local best, bestScore = nil, 0
	for _, s in ipairs(sources) do
		if s ~= exclude and s.alive then
			local to = sub(s.pos, origin)
			local d = len(to)
			if d >= 1 then
				local off = angleBetween(axis, to)
				if off <= half then
					local I = irIntensity(s, origin)
					if d <= irLockRange(self.spec.seekerRange, I) then
						local score = I / (d * d) * (1 - 0.5 * off / half)
						if score > bestScore and ((not terrain) or terrain:lineOfSight(origin, s.pos)) then best, bestScore = s, score end
					end
				end
			end
		end
	end
	return best
end
function IRSeeker:update(dt, origin, boresight, sources, terrain, slaveDir, exclude)
	local sp = self.spec
	local fov = sp.seekerFov * DEG
	if not self.axis then self.axis = norm(boresight) end
	if not self.target then
		local want = slaveDir or boresight
		if angleBetween(boresight, want) > sp.gimbal * DEG then want = boresight end
		self.axis = norm(want)
		self.candidate = self:bestInCone(origin, self.axis, sources, (self.acqFov or sp.seekerFov) * DEG, terrain, exclude)
		return nil
	end
	local tgt = self.target
	local desired = norm(sub(tgt.pos, origin))
	if self.snap then self.axis = desired; self.snap = false end       -- seeker head jumps onto what it locked
	self.axis = rotateTowards(self.axis, desired, sp.trackRate * DEG * dt)
	self.candidate = tgt
	if (not self:visible(tgt, origin, terrain)) or angleBetween(self.axis, desired) > fov * 1.6
		or angleBetween(boresight, self.axis) > sp.gimbal * DEG then
		self.target, self.candidate = nil, nil
		return "lost"
	end
	local heat = irIntensity(tgt, origin)
	for _, s in ipairs(sources) do
		if s.isFlare and s ~= tgt and not self.judged[s.id] then
			if angleBetween(self.axis, sub(s.pos, origin)) <= fov * 2 and s.intensity >= 0.6 * heat then
				self.judged[s.id] = true
				if self.rnd() > sp.ccm then self.target = s; return "decoyed" end
			end
		end
	end
	return nil
end
function IRSeeker:lock()
	if self.candidate then
		self.target = self.candidate
		self.snap = true
		return true
	end
	return false
end
function IRSeeker:unlock() self.target = nil end
function IRSeeker:tone() return (self.target or self.candidate) and "lock" or "growl" end

-- ------------------------------------------------------------------------ radar
local OFF, SEARCH, ACM, STT = "OFF", "SRCH", "ACM", "STT"
W.OFF, W.SEARCH, W.ACM, W.STT = OFF, SEARCH, ACM, STT
local Radar = {}
Radar.__index = function(t, k)
	if k == "on" then return t.mode ~= OFF end
	return Radar[k]
end
function W.newRadar(spec, owner, rnd)
	local r = setmetatable({}, Radar)
	r.spec, r.owner, r.rnd = spec, owner, rnd
	r.mode, r.beamAz, r.beamDir = SEARCH, -spec.scanAz * DEG, 1
	r.contacts, r.selected, r.locked, r.pending, r.pendingTime = {}, nil, nil, nil, 0
	r.lostTime, r.trackPos, r.trackVel, r.notched, r.judged, r.lastEvent = 0, nil, nil, false, {}, nil
	return r
end
local function count(t) local n = 0; for _ in pairs(t) do n = n + 1 end return n end
function Radar:anglesTo(pos)
	local rel = sub(pos, self.owner.pos)
	local l = toLocal(self.owner.quat, rel)
	return atan2(l.x, l.y), atan2(l.z, math.sqrt(l.x * l.x + l.y * l.y)), len(rel)
end
function Radar:inNotch(t) return math.abs(radialSpeed(t.vel, self.owner.pos, t.pos)) < self.spec.notchSpeed end
function Radar:canDetect(t, world, maxRange)
	if t == self.owner or not t.alive then return false end
	local d = len(sub(t.pos, self.owner.pos))
	if d > maxRange or d > radarRange(self.spec.searchRange, rcs(t, self.owner.pos)) or self:inNotch(t) then return false end
	return world.terrain:lineOfSight(self.owner.pos, t.pos)
end
function Radar:togglePower()
	if self.mode == OFF then self.mode = SEARCH
	else self:dropLock(); self.mode = OFF; self.contacts = {} end
end
function Radar:setAcm() self:dropLock(); self.mode = ACM; self.pending = nil end
function Radar:setSearch() self:dropLock(); self.mode = SEARCH end
function Radar:tryLock(t)
	if self.mode == OFF or not t or not t.alive then return false end
	local az, el, d = self:anglesTo(t.pos)
	local gim = self.spec.sttGimbal * DEG
	if math.abs(az) > gim or math.abs(el) > gim or d > self.spec.lockRange then return false end
	self.pending, self.pendingTime = t, 0
	return true
end
function Radar:lockButton()
	if self.mode == OFF then self.mode = SEARCH; return "on" end
	if self.mode == STT then self:setSearch(); return "unlocked" end
	if self.mode == SEARCH and self.selected and self.contacts[self.selected] and self:tryLock(self.selected) then return "locking" end
	if self.mode == SEARCH then self:setAcm(); return "acm" end
	self:setSearch()
	return "search"
end
-- lock assist: lock the enemy closest to `dir` (where the player looks); pressed again it moves on to the next one, or unlocks
function Radar:quickLock(world, dir, coneDeg)
	coneDeg = coneDeg or 30
	if self.mode == OFF then self.mode = SEARCH end
	local gim, own = self.spec.sttGimbal * DEG, self.owner
	local cands = {}
	for _, t in ipairs(world.aircraft) do
		if t ~= own and t.alive and t.team ~= own.team then
			local rel = sub(t.pos, own.pos)
			local off = angleBetween(dir, rel)
			local az, el, d = self:anglesTo(t.pos)
			if not (off > coneDeg * DEG or d > self.spec.lockRange or math.abs(az) > gim or math.abs(el) > gim)
				and world.terrain:lineOfSight(own.pos, t.pos) then
				cands[#cands + 1] = { t = t, off = off }
			end
		end
	end
	table.sort(cands, function(a, b) return a.off < b.off end)
	local current = self.locked or self.pending
	if #cands == 0 then return current and "keep" or "none" end
	local pick = cands[1].t
	local idx = nil
	for i, c in ipairs(cands) do if c.t == current then idx = i end end
	if idx then
		pick = cands[(idx % #cands) + 1].t
		if pick == current then self:setSearch(); return "unlocked" end
	end
	self:dropLock()
	self.mode = SEARCH
	if not self:tryLock(pick) then return "none" end
	self.pendingTime = self.spec.lockTime * 0.5
	self.selected = pick
	return "locking"
end
function Radar:cycleTarget()
	local order = {}
	for _, c in pairs(self.contacts) do order[#order + 1] = c end
	if #order == 0 then self.selected = nil; return end
	table.sort(order, function(a, b) return (math.abs(a.az) + math.abs(a.el)) < (math.abs(b.az) + math.abs(b.el)) end)
	local idx = nil
	for i, c in ipairs(order) do if c.target == self.selected then idx = i end end
	if idx then self.selected = order[(idx % #order) + 1].target else self.selected = order[1].target end
end
function Radar:dropLock()
	self.locked, self.pending, self.trackPos, self.trackVel, self.notched, self.lostTime = nil, nil, nil, nil, false, 0
end
function Radar:update(dt, world)
	self.lastEvent = nil
	local sp = self.spec
	if self.mode == OFF then return end
	if self.mode == SEARCH then self:search(dt, world)
	elseif self.mode == ACM then self:acm(world) end
	if self.mode == STT then self:track(dt, world) end
	if self.pending and self.mode ~= STT then self:acquire(dt, world) end
	local frame = 2 * (2 * sp.scanAz / sp.scanRate)
	local dead = {}
	for t, c in pairs(self.contacts) do
		if world.time - c.time > frame * 1.3 or not t.alive then dead[#dead + 1] = t end
	end
	for _, t in ipairs(dead) do self.contacts[t] = nil end
	if self.selected and not self.contacts[self.selected] and self.selected ~= self.locked then self.selected = nil end
end
function Radar:search(dt, world)
	local sp = self.spec
	local lim, old = sp.scanAz * DEG, self.beamAz
	self.beamAz = self.beamAz + self.beamDir * sp.scanRate * DEG * dt
	if self.beamAz > lim or self.beamAz < -lim then
		self.beamAz = clamp(self.beamAz, -lim, lim)
		self.beamDir = -self.beamDir
	end
	local lo, hi = math.min(old, self.beamAz) - 2 * DEG, math.max(old, self.beamAz) + 2 * DEG
	for _, t in ipairs(world.aircraft) do
		if t ~= self.owner and t.alive then
			local az, el, d = self:anglesTo(t.pos)
			if not (az < lo or az > hi or math.abs(el) > sp.scanEl * DEG) then
				if self:canDetect(t, world, sp.searchRange * 1.3) then
					self.contacts[t] = { target = t, pos = copy(t.pos), vel = copy(t.vel), time = world.time, range = d, az = az, el = el }
				end
			end
		end
	end
	if not self.selected and next(self.contacts) ~= nil then self:cycleTarget() end
end
function Radar:acm(world)
	local sp = self.spec
	local best, bestD = nil, sp.acmRange
	for _, t in ipairs(world.aircraft) do
		if t ~= self.owner and t.alive then
			local az, el, d = self:anglesTo(t.pos)
			if not (math.abs(az) > sp.acmAz * DEG or el < sp.acmElLow * DEG or el > sp.acmElHigh * DEG) then
				if d < bestD and self:canDetect(t, world, sp.acmRange) then best, bestD = t, d end
			end
		end
	end
	if best and not self.pending then
		self.pending = best
		self.pendingTime = sp.lockTime * 0.4
	end
end
function Radar:acquire(dt, world)
	local t = self.pending
	local az, el, d = self:anglesTo(t.pos)
	local gim = self.spec.sttGimbal * DEG
	if math.abs(az) > gim or math.abs(el) > gim or d > self.spec.lockRange or not self:canDetect(t, world, self.spec.lockRange) then
		self.pending = nil
		return
	end
	self.pendingTime = self.pendingTime + dt
	if self.pendingTime >= self.spec.lockTime then
		self.locked, self.selected, self.pending, self.mode, self.lostTime = t, t, nil, STT, 0
		self.trackPos, self.trackVel = copy(t.pos), copy(t.vel)
		self.judged = {}
		self.lastEvent = "locked"
	end
end
function Radar:track(dt, world)
	local t, sp = self.locked, self.spec
	local valid = t and t.alive
	self.notched = false
	local az, el, d = 0, 0, 0
	if valid then
		az, el, d = self:anglesTo(t.pos)
		local gim = sp.sttGimbal * DEG
		self.notched = self:inNotch(t)
		valid = math.abs(az) <= gim and math.abs(el) <= gim and d <= sp.lockRange * 1.25 and not self.notched
			and d <= radarRange(sp.searchRange, rcs(t, self.owner.pos)) * 1.2 and world.terrain:lineOfSight(self.owner.pos, t.pos)
	end
	if valid and self:chaffDecoyed(t, world) then
		self.lastEvent = "decoyed"
		self:dropLock()
		self.mode = SEARCH
		return
	end
	if valid then
		self.lostTime = 0
		self.trackPos, self.trackVel = copy(t.pos), copy(t.vel)
		self.contacts[t] = { target = t, pos = copy(t.pos), vel = copy(t.vel), time = world.time, range = d, az = az, el = el }
		return
	end
	self.lostTime = self.lostTime + dt
	if self.trackPos then self.trackPos:addScaled(self.trackVel, dt) end
	if self.lostTime > sp.trackMemory then
		self.lastEvent = "lost"
		self:dropLock()
		self.mode = SEARCH
	end
end
function Radar:chaffDecoyed(t, world)
	if #world.chaff == 0 then return false end
	local los = sub(t.pos, self.owner.pos)
	local d = len(los)
	local vr = math.abs(radialSpeed(t.vel, self.owner.pos, t.pos))
	local eff = 0.55 * (1 - smoothstep(self.spec.notchSpeed, 6 * self.spec.notchSpeed, vr))
	for _, ch in ipairs(world.chaff) do
		if not (self.judged[ch.id] or ch.age < 0.3) then
			local rel = sub(ch.pos, self.owner.pos)
			if not (math.abs(len(rel) - d) > 600 or angleBetween(rel, los) > 4 * DEG) then
				self.judged[ch.id] = true
				if self.rnd() < eff then return true end
			end
		end
	end
	return false
end
function Radar:isPainting(t)
	if self.mode == STT and self.locked == t then return "lock" end
	if (self.mode == SEARCH or self.mode == ACM) and self.contacts[t] then return "search" end
	if self.pending == t then return "lock" end
	return nil
end

-- -------------------------------------------------------------------------- RWR
local LEVELS = { search = 1, lock = 2, launch = 3 }
local RWR = {}
RWR.__index = function(t, k)
	if k == "maxLevel" then
		local m = 0
		for _, th in ipairs(t.threats) do m = math.max(m, LEVELS[th.level]) end
		return m
	end
	return RWR[k]
end
function W.newRWR(owner)
	local r = setmetatable({}, RWR)
	r.owner, r.threats, r.incoming, r.newSearch, r.known = owner, {}, {}, false, {}
	return r
end
function RWR:bearing(pos)
	local l = toLocal(self.owner.quat, sub(pos, self.owner.pos))
	return atan2(l.x, l.y)
end
function RWR:update(world)
	local o = self.owner
	local found, order = {}, {}
	local function put(k, v)
		if not found[k] then order[#order + 1] = k end
		found[k] = v
	end
	for _, ac in ipairs(world.aircraft) do
		if ac ~= o and ac.alive and ac.radar.on then
			local lvl = ac.radar:isPainting(o)
			if not (lvl == "search" and ac.spec.radar.lpi) then        -- LPI radar (F-22): not heard while searching
				if lvl then put(ac, { source = ac, symbol = ac.spec.radar.rwrSymbol, level = lvl, bearing = self:bearing(ac.pos) }) end
			end
		end
	end
	for _, m in ipairs(world.missiles) do
		if m.alive and m.spec.guidance == ARH and m.guidedTarget == o then
			if m.active then put(m, { source = m, symbol = "M", level = "launch", bearing = self:bearing(m.pos) })
			elseif m.datalink and found[m.shooter] then found[m.shooter].level = "launch" end
		end
	end
	-- missile approach warning (player only): every missile flying at us, IR ones included
	self.incoming = {}
	if o.isPlayer then
		for _, m in ipairs(world.missiles) do
			if m.alive and m.shooter and m.shooter.team ~= o.team and (m.guidedTarget == o or m.intended == o) then
				local d = len(sub(m.pos, o.pos))
				if d <= 15000 then
					self.incoming[#self.incoming + 1] = { missile = m, dist = d }
					if not found[m] then put(m, { source = m, symbol = "M", level = "launch", bearing = self:bearing(m.pos) }) end
				end
			end
		end
		table.sort(self.incoming, function(a, b) return a.dist < b.dist end)
	end
	local list = {}
	for i, k in ipairs(order) do list[i] = found[k] end
	-- a stable sort by level (highest first)
	local idx = {}
	for i = 1, #list do idx[i] = i end
	table.sort(idx, function(a, b)
		local la, lb = LEVELS[list[a].level], LEVELS[list[b].level]
		if la ~= lb then return la > lb end
		return a < b
	end)
	self.threats = {}
	for i, k in ipairs(idx) do self.threats[i] = list[k] end
	local keys = {}
	local fresh = false
	for _, k in ipairs(order) do
		keys[k] = true
		if not self.known[k] then fresh = true end
	end
	self.newSearch = fresh
	self.known = keys
end

-- --------------------------------------------------------------------- missiles
local mids = 1
local Missile = {}
Missile.__index = function(t, k)
	if k == "guidedTarget" then
		if t.spec.guidance == IR then return t.seeker and t.seeker.target or nil end
		if t.active then return t.arhTarget end
		if t.datalink then return t.intended end
		return nil
	elseif k == "burning" then
		return t.age < t.spec.burnTime
	end
	return Missile[k]
end
function W.newMissile(spec, shooter, pos, vel, dir, rnd, target, irAxis)
	local m = setmetatable({}, Missile)
	m.id = mids
	mids = mids + 1
	m.spec, m.shooter, m.rnd = spec, shooter, rnd
	m.pos, m.vel, m.dir, m.mass = copy(pos), copy(vel), norm(dir), spec.mass
	m.age, m.alive, m.thrust, m.status = 0, true, 0, "LAUNCH"
	m.seeker = nil
	if spec.guidance == IR then
		m.seeker = W.newIRSeeker(spec, rnd)
		m.seeker.axis = irAxis and copy(irAxis) or copy(m.dir)
		m.seeker.target = target
	end
	m.intended, m.active, m.datalink, m.arhTarget = target, false, false, nil
	m.estPos = target and copy(target.pos) or nil
	m.estVel = target and copy(target.vel) or nil
	m.judged = {}
	if spec.guidance == ARH and not target then
		m.estPos = add(m.pos, mul(m.dir, spec.seekerRange * 0.8))
		m.estVel = V()
		m.active = true
	end
	return m
end
function Missile:motorThrust()
	local t = self.age
	for _, p in ipairs(self.spec.motor) do
		if t < p[1] then return p[2] end
		t = t - p[1]
	end
	return 0
end
function Missile:update(dt, world)
	if not self.alive then return end
	local sp = self.spec
	self.age = self.age + dt
	local rho, aS = isa(self.pos.z)
	local speed = math.max(len(self.vel), 1)
	local vhat = mul(self.vel, 1 / speed)
	local mach = speed / aS
	local qbar = 0.5 * rho * speed * speed
	self.thrust = self:motorThrust()
	if self.thrust > 0 then self.mass = self.mass - sp.propellant / sp.burnTime * dt end
	local acmd = V()
	if not self.defeated then self:checkCobra(world) end
	if not self.defeated then self:checkEvade(world) end
	if self.age >= math.max(sp.guidanceDelay, sp.railTime) and not self.defeated then
		local aimPos, aimVel = self:guidance(dt, world)
		if aimPos then
			acmd = self:proNav(aimPos, aimVel)
			acmd.z = acmd.z + G
		end
	elseif self.defeated then
		self.status = "MISSED"
	end
	acmd:addScaled(vhat, -dot(acmd, vhat))
	-- fins, plus thrust vectoring while the motor burns (spec.tvc: share of the thrust that can push sideways)
	local tvc = (sp.tvc and self.thrust > 0) and self.thrust * sp.tvc / self.mass or 0
	local aMax = math.min(sp.maxG * G, qbar * sp.refArea * sp.cnMax / self.mass + tvc)
	local aLen = len(acmd)
	if aLen > aMax then
		acmd:scale(aMax / aLen)
		aLen = aMax
	end
	local drag = qbar * sp.refArea * interp(sp.cd, mach) + aLen * self.mass * sp.inducedDrag
	local acc = add(add(mul(vhat, (self.thrust - drag) / self.mass), acmd), V(0, 0, -G))
	local newVel = add(self.vel, mul(acc, dt))
	if self.age > sp.armTime then
		local avg = mul(add(self.vel, newVel), 0.5)
		for _, ac in ipairs(world.aircraft) do
			if ac.alive and ac ~= self.shooter then          -- the fuse never triggers on the launching jet
				local rel = sub(ac.pos, self.pos)
				if len(rel) <= 400 then
					local d, t = closestApproach(rel, sub(ac.vel, avg), dt)
					if d <= sp.fuseRadius * ((self.shooter and self.shooter.blastMult) or 1) then
						self.pos:addScaled(avg, t)
						world:detonate(self, self.pos)
						return
					end
				end
			end
		end
	end
	self.vel = newVel
	self.pos:addScaled(self.vel, dt)
	if len(self.vel) > 1 then self.dir = norm(self.vel) end
	if self.pos.z <= world.terrain:height(self.pos.x, self.pos.y) then world:detonate(self, self.pos, true)
	elseif self.age > sp.guidanceTime then world:detonate(self, self.pos, false, true)
	elseif (not self.burning) and speed < 160 and self.age > 3 then
		self.status = "SLOW"
		if speed < 110 then world:detonate(self, self.pos, false, true) end
	end
end
-- A target that suddenly stands on its tail (Cobra, AoA > 40 degrees) when the missile is 4 s or less away loses most of its
-- speed in a moment: the missile cannot turn that hard and its seeker loses the target in the clutter - it overshoots.
function Missile:checkCobra(world)
	local t = self.guidedTarget or self.intended
	if not t or not t.fm or not t.alive or t.fm.alpha < 40 * DEG then return end
	local rel = sub(t.pos, self.pos)
	local d = len(rel)
	local closing = -dot(sub(t.vel, self.vel), norm(rel))
	local ttg = closing > 1 and d / closing or 99
	if ttg > 4 or self.cobraJudged then return end
	self.cobraJudged = true
	if self.rnd() < (t.isPlayer and 0.9 or 0.6) then
		self.defeated = true
		world:emit("message", { to = t, text = "COBRA - A RAKÉTA ELVESZTETT!", level = "good" })
		world:emit("cobra", { target = t, missile = self })
	end
end
-- An AI pilot sees the missile at the last moment and breaks hard with flares: once per missile, a chance set by its skill
function Missile:checkEvade(world)
	local t = self.guidedTarget or self.intended
	if self.evadeJudged or not t or not t.fm or not t.alive or t.isPlayer or not t.pilot or not t.pilot.skill then return end
	local rel = sub(t.pos, self.pos)
	local d = len(rel)
	local closing = -dot(sub(t.vel, self.vel), norm(rel))
	if d / math.max(closing, 1) > 1.6 then return end
	self.evadeJudged = true
	-- the base chance (difficulty) is scaled by what the pilot could actually do
	local p = t.pilot.skill.evade or 0
	if t.pilot.state ~= "defend" then p = p * 0.25 end
	if t.flares + t.chaff <= 0 then p = p * 0.3 end
	if closing > 450 then p = p * 0.7 elseif self.age > 14 then p = p * 1.25 end
	if self.rnd() < math.min(p, 0.6) then
		self.defeated = true
		self.status = "MISSED"
		t:dispense(world)
		world:emit("evaded", { target = t, missile = self })
		if self.shooter then world:emit("message", { to = self.shooter, text = t.name .. ": KICSELEZTE A RAKÉTÁT!", level = "warn" }) end
	end
end
function Missile:proNav(aimPos, aimVel)
	local r = sub(aimPos, self.pos)
	local d2 = math.max(dot(r, r), 1)
	local vRel = sub(aimVel, self.vel)
	local omega = mul(cross(r, vRel), 1 / d2)
	local rHat = mul(r, 1 / sqrt(d2))
	local vc = math.max(-dot(vRel, rHat), 0.6 * len(self.vel), 150)
	return mul(cross(omega, rHat), self.spec.navGain * vc)
end
function Missile:guidance(dt, world)
	if self.spec.guidance == IR then return self:guidanceIR(dt, world) end
	return self:guidanceARH(dt, world)
end
function Missile:guidanceIR(dt, world)
	local s = self.seeker
	s:update(dt, self.pos, self.dir, world:heatSources(), world.terrain, nil, self.shooter)
	if not s.locked then s:lock() end
	if not s.locked then self.status = "LOST"; return nil end
	self.status = s.target.isFlare and "FLARE" or "TRACK"
	return s.target.pos, s.target.vel
end
function Missile:guidanceARH(dt, world)
	local sp = self.spec
	if not self.active then
		local sh = self.shooter
		local radar = (sh and sh.alive) and sh.radar or nil
		if sp.datalink and radar and radar.mode == STT and radar.locked == self.intended and radar.trackPos then
			self.estPos, self.estVel, self.datalink, self.status = copy(radar.trackPos), copy(radar.trackVel), true, "DATALINK"
		else
			self.datalink = false
			if not self.estPos then return nil end
			self.estPos:addScaled(self.estVel, dt)
			self.status = "INERTIAL"
		end
		if len(sub(self.estPos, self.pos)) <= sp.seekerRange then
			self.active, self.datalink = true, false
			world:emit("pitbull", { missile = self })
		end
	end
	if self.active then return self:activeSeeker(dt, world) end
	return self:loft(self.estPos), self.estVel
end
function Missile:loft(aim)
	if not self.spec.loft then return aim end
	local d = len(sub(aim, self.pos))
	local ang = 22 * DEG * smoothstep(12000, 40000, d)
	return V(aim.x, aim.y, aim.z + math.tan(ang) * d * 0.5)
end
function Missile:seekerOk(t, world)
	local sp = self.spec
	local rel = sub(t.pos, self.pos)
	local d = len(rel)
	if angleBetween(self.dir, rel) > sp.gimbal * DEG then return false end
	if t.isChaff then return d < sp.seekerRange and t.alive end
	if not t.alive or d > radarRange(sp.seekerRange, rcs(t, self.pos)) then return false end
	if math.abs(radialSpeed(t.vel, self.pos, t.pos)) < (sp.notch or 22) then return false end        -- beaming: Doppler notch
	return world.terrain:lineOfSight(self.pos, t.pos)
end
function Missile:activeSeeker(dt, world)
	local sp = self.spec
	local t = self.arhTarget
	if t and not self:seekerOk(t, world) then
		t = nil
		self.arhTarget = nil
	end
	if t and not t.isChaff then
		local vr = math.abs(radialSpeed(t.vel, self.pos, t.pos))
		local p = (1 - sp.ccm) * (1 - smoothstep(25, 150, vr))
		local los = sub(t.pos, self.pos)
		for _, ch in ipairs(world.chaff) do
			if not (self.judged[ch.id] or ch.age < 0.2 or angleBetween(sub(ch.pos, self.pos), los) > 5 * DEG) then
				self.judged[ch.id] = true
				if self.rnd() < p then
					t = ch
					self.arhTarget = ch
					break
				end
			end
		end
	end
	if not t then
		local axis = self.estPos and sub(self.estPos, self.pos) or self.dir
		local best, bestScore = nil, 1e18
		for _, ac in ipairs(world.aircraft) do
			if ac ~= self.shooter and ac.alive then
				local rel = sub(ac.pos, self.pos)
				if not (angleBetween(axis, rel) > sp.seekerFov * DEG or not self:seekerOk(ac, world)) then
					local score = len(rel) + (ac ~= self.intended and 2000 or 0)
					if self.estPos then score = score + len(sub(ac.pos, self.estPos)) end
					if score < bestScore then best, bestScore = ac, score end
				end
			end
		end
		t = best
		self.arhTarget = best
	end
	if not t then
		self.status = "SEARCH"
		if not self.estPos then return nil end
		if self.estVel then self.estPos:addScaled(self.estVel, dt) end
		return self.estPos, self.estVel
	end
	self.status = t.isChaff and "CHAFF" or "ACTIVE"
	if not t.isChaff then self.estPos, self.estVel = copy(t.pos), copy(t.vel) end
	return t.pos, t.vel
end

function W.timeToImpact(m)
	local t = m.guidedTarget
	if not t then return nil end
	local rel = sub(t.pos, m.pos)
	local closing = -dot(sub(t.vel, m.vel), norm(rel))
	if closing > 1 then return len(rel) / closing end
	return nil
end

function W.launchZone(spec, launchSpeed, altitude, closing)
	local function fly(closure)
		local mass, v, x, t = spec.mass, launchSpeed, 0, 0
		local dt = 0.25
		while t < spec.guidanceTime do
			local rho, aS = isa(altitude + (spec.loft and 2500 * math.min(t / 20, 1) or 0))
			local thrust, tt = 0, t
			for _, p in ipairs(spec.motor) do
				if tt < p[1] then thrust = p[2]; break end
				tt = tt - p[1]
			end
			if t < spec.burnTime then mass = mass - spec.propellant / spec.burnTime * dt end
			local drag = 0.5 * rho * v * v * spec.refArea * interp(spec.cd, v / aS) * 1.15
			v = v + (thrust - drag) / mass * dt
			x = x + v * dt
			t = t + dt
			if v < 450 and t > spec.burnTime then break end       -- too slow to still out-turn a target
		end
		return math.max(0, x + closure * t)
	end
	return fly(closing), fly(-300)
end

function W.flyoutTime(spec, launchSpeed, altitude, range)
	local mass, v, x, t = spec.mass, launchSpeed, 0, 0
	local dt = 0.1
	local path = range * (spec.loft and 1.08 or 1.0)
	while t < spec.guidanceTime do
		local rho, aS = isa(altitude + (spec.loft and 2500 * math.min(t / 20, 1) or 0))
		local thrust, tt = 0, t
		for _, p in ipairs(spec.motor) do
			if tt < p[1] then thrust = p[2]; break end
			tt = tt - p[1]
		end
		if t < spec.burnTime then mass = mass - spec.propellant / spec.burnTime * dt end
		local drag = 0.5 * rho * v * v * spec.refArea * interp(spec.cd, v / aS) * 1.15
		v = v + (thrust - drag) / mass * dt
		x = x + v * dt
		t = t + dt
		if x >= path then return t end
		if v < 250 and t > spec.burnTime then return nil end
	end
	return nil
end

-- -------------------------------------------------------------------------- gun
W.GUN_OFFSET = V(-0.70, 3.95, -0.20)       -- the gun port in the left strake
local Gun = {}
Gun.__index = Gun
function W.newGun(spec, rnd)
	return setmetatable({ spec = spec, ammo = spec.ammo, rnd = rnd, firing = false, acc = 0, count = 0 }, Gun)
end
function Gun:reload() self.ammo = self.spec.ammo end
function Gun:update(dt, shooter, trigger, world)
	local sp = self.spec
	self.firing = trigger and self.ammo > 0 and shooter.alive
	if not self.firing then self.acc = 0; return end
	self.acc = self.acc + dt * sp.rateRpm / 60
	local n = math.min(math.floor(self.acc), self.ammo)
	self.acc = self.acc - n
	if n <= 0 then return end
	local q, fwd, right, up = shooter.quat, shooter.forward, shooter.fm.right, shooter.fm.up
	local gp = shooter.spec.gunPos
	local muzzle = add(shooter.pos, xform(q, gp and V(gp[1], gp[2], gp[3]) or W.GUN_OFFSET))
	local sig = sp.dispersionMrad * 1e-3
	for i = 0, n - 1 do
		self.ammo = self.ammo - 1
		self.count = self.count + 1
		local dir = norm(add(add(fwd, mul(right, self.rnd.gauss(0, sig))), mul(up, self.rnd.gauss(0, sig))))
		local vel = add(shooter.vel, mul(dir, sp.muzzle))
		world.bullets[#world.bullets + 1] = { pos = add(muzzle, mul(vel, dt * i / n)), vel = vel, age = 0, owner = shooter, alive = true, tracer = self.count % 2 == 0, spec = sp }
	end
end

function W.gunLead(sPos, sVel, tPos, tVel, spec, iterations)
	iterations = iterations or 4
	local rel, dv = sub(tPos, sPos), sub(tVel, sVel)
	local k, v0 = spec.dragK, spec.muzzle
	local tof, aim = len(rel) / v0, copy(rel)
	for _ = 1, iterations do
		aim = add(add(rel, mul(dv, tof)), V(0, 0, 0.5 * G * tof * tof))
		tof = (exp(math.min(k * len(aim), 6)) - 1) / (k * v0)
	end
	return norm(aim), tof
end

local function segHitsBox(p0, p1, c, h)
	local t0, t1 = 0, 1
	local a, b = { p0.x, p0.y, p0.z }, { p1.x, p1.y, p1.z }
	for i = 1, 3 do
		local s, d = a[i] - c[i], b[i] - a[i]
		if math.abs(d) < 1e-9 then
			if math.abs(s) > h[i] then return false end
		else
			local u0, u1 = (-h[i] - s) / d, (h[i] - s) / d
			if u0 > u1 then u0, u1 = u1, u0 end
			t0 = math.max(t0, u0)
			t1 = math.min(t1, u1)
			if t0 > t1 then return false end
		end
	end
	return true
end

function W.updateBullets(world, dt)
	local targets, keep = {}, {}
	for _, a in ipairs(world.aircraft) do if a.alive then targets[#targets + 1] = a end end
	for _, b in ipairs(world.bullets) do
		local old = copy(b.pos)
		local sp = len(b.vel)
		b.vel:scale(1 - b.spec.dragK * sp * dt)
		b.vel.z = b.vel.z - G * dt
		b.pos:addScaled(b.vel, dt)
		b.age = b.age + dt
		local step = len(sub(b.pos, old))
		for _, ac in ipairs(targets) do
			if not (ac == b.owner or (b.owner and ac.team == b.owner.team)) then        -- no friendly fire with the gun
				local relEnd = sub(b.pos, ac.pos)
				if len(relEnd) <= step + 12 then
					local relStart = sub(old, sub(ac.pos, mul(ac.vel, dt)))
					local p0, p1 = toLocal(ac.quat, relStart), toLocal(ac.quat, relEnd)
					local hit = false
					for _, hb in ipairs(ac.spec.hitboxes) do
						if segHitsBox(p0, p1, hb[1], hb[2]) then hit = true; break end
					end
					if hit then
						b.alive = false
						world:emit("hit", { target = ac, pos = copy(b.pos), shooter = b.owner })
						ac:takeDamage(b.spec.damage, b.owner, b.spec.name, world)
						break
					end
				end
			end
		end
		if b.alive then
			if b.pos.z < world.terrain:height(b.pos.x, b.pos.y) then
				if b.tracer then world:emit("impact", { pos = copy(b.pos) }) end
			elseif b.age < b.spec.life then
				keep[#keep + 1] = b
			end
		end
	end
	world.bullets = keep
end

return W
