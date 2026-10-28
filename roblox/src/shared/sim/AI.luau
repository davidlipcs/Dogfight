--!nonstrict
-- Mouse-aim instructor, player pilot and enemy AI: the port of web/js/ai.js.
local M = require(script.Parent.SimMath)
local Specs = require(script.Parent.Specs)
local Weapons = require(script.Parent.Weapons)
local Sim = require(script.Parent.Sim)
local G, DEG, V = M.G, M.DEG, M.V
local add, sub, mul, dot, cross, len, norm, clamp, smoothstep, angleBetween, bankAngle, wrap = M.add, M.sub, M.mul, M.dot, M.cross, M.len, M.norm, M.clamp, M.smoothstep, M.angleBetween, M.bankAngle, M.wrap
local ARH = Specs.ARH
local STT, gunLead, launchZone = Weapons.STT, Weapons.gunLead, Weapons.launchZone
local AI_DT = Sim.AI_DT
local acos, atan2, abs, cos, sin = math.acos, M.atan2, math.abs, math.cos, math.sin

local A = {}

-- Mouse-aim "instructor" (War Thunder style): swings the flight path - or with `nose` the nose itself - towards `direction`.
function A.steerTowards(fm, direction, c, maxGFrac, precision, nose)
	maxGFrac, precision, nose = maxGFrac or 1, precision or 1, nose or false
	local s, q, right, up, fwd = fm.spec, fm.quat, fm.right, fm.up, fm.forward
	local path = (nose or fm.speed <= 30) and fwd or norm(fm.vel, fwd)
	local lift = norm(cross(right, path), up)
	local side = cross(path, lift)
	local d = norm(direction)
	local off = acos(clamp(dot(d, path), -1, 1))
	local speed = math.max(fm.speed, 60)
	local perp = sub(d, mul(path, dot(d, path)))
	if len(perp) > 1e-6 then perp = norm(perp) end
	local behind = smoothstep(120 * DEG, 170 * DEG, off)
	if behind > 0 or len(perp) < 0.5 then
		local flat = cross(path, V(0, 0, 1))
		if len(flat) < 1e-3 then flat = right:clone() end
		flat = norm(flat)
		local sign = dot(perp, flat)
		if abs(sign) < 0.15 then sign = bankAngle(q) >= 0 and 1 or -1 end
		flat = mul(flat, sign >= 0 and 1 or -1)
		perp = norm(add(mul(perp, 1 - behind), mul(flat, math.max(behind, 0.01))), flat)
	end
	-- turn rate demand (PD: a path already swinging towards the target eases off)
	local closingRate = dot(fm.accel, perp) / speed
	local rate = clamp(off * 0.9 * precision - 0.5 * closingRate * (1 - behind), 0, 1.0)
	local acc = add(mul(perp, rate * speed), V(0, 0, G))
	acc:addScaled(path, -dot(acc, path))
	local aG = len(acc) / G
	local rollPull = atan2(dot(acc, side), dot(acc, lift))
	local rollPush = wrap(rollPull + math.pi)
	-- pull (lift towards the target) or push (lift away, negative G)?
	local pushOk = behind == 0 and (off < 40 * DEG or (aG <= -s.gMin * 0.85 and off < 60 * DEG))
	local costPull, costPush = abs(rollPull), abs(rollPush) + 25 * DEG
	local push = (fm.steerPush and true or false) and pushOk
	if pushOk then
		local flip
		if push then flip = costPull + 20 * DEG < costPush else flip = costPush + 20 * DEG < costPull end
		if flip then push = not push end
	end
	fm.steerPush = push
	local rollErr = push and rollPush or rollPull
	-- small corrections: keep the bank small (the rudder below does the rest)
	if off < 45 * DEG and behind == 0 then
		local cur = bankAngle(q)
		local lim = (20 + 160 * smoothstep((nose and 2 or 4) * DEG, (nose and 22 or 40) * DEG, off)) * DEG
		local base = (push and abs(cur) > math.pi / 2) and math.pi or 0        -- inverted flight: limit around 180
		local want = wrap(cur + rollErr - base)
		rollErr = wrap(clamp(want, -lim, lim) + base - cur)
	end
	-- load factor along the lift direction we are rolling to, applied as the roll gets there
	local target = add(mul(lift, cos(rollErr)), mul(side, sin(rollErr)))
	local nz = dot(acc, target) / G
	nz = 1 + (nz - 1) * math.max(0, cos(clamp(rollErr, -math.pi / 2, math.pi / 2)))
	nz = clamp(nz, s.gMin * 0.85, s.gMax * maxGFrac)
	c.roll = clamp(rollErr * 1.8 - fm.omega.y * 0.3, -1, 1)
	c.pitch = clamp(nz >= 1 and (nz - 1) / (s.gMax - 1) or (nz - 1) / (1 - s.gMin), -1, 1)
	local fine = 1 - smoothstep((nose and 6 or 3) * DEG, (nose and 20 or 12) * DEG, off)
	c.yaw = clamp(atan2(dot(d, side), dot(d, path)) * 4 * precision, -1, 1) * fine
	if fm.onGround then
		local he = wrap(atan2(d.x, d.y) - atan2(fwd.x, fwd.y))
		c.roll = 0
		c.yaw = clamp(he * 3, -1, 1)
		c.pitch = clamp(math.asin(clamp(d.z, -1, 1)) * 4, 0, 1)
	end
	return off
end
local steerTowards = A.steerTowards

local PLAYER_G = 0.85

local PlayerPilot = {}
PlayerPilot.__index = function(t, k)
	if k == "manual" then return t.pitch ~= nil or t.roll ~= nil end
	return PlayerPilot[k]
end
function A.newPlayerPilot(ac)
	local p = setmetatable({}, PlayerPilot)
	p.ac, p.aim, p.pitch, p.roll, p.yaw = ac, ac.forward:clone(), nil, nil, nil
	ac.pilot = p
	return p
end
function PlayerPilot:think() end
function PlayerPilot:fly()
	local c, fm = self.ac.controls, self.ac.fm
	if self.manual then
		-- keyboard flying: the instructor lets go, the jet does exactly what the keys say; an axis without a key holds its attitude
		c.pitch = self.pitch ~= nil and self.pitch or 0
		c.roll = self.roll ~= nil and self.roll or clamp(-fm.omega.y * 0.5, -1, 1)
		c.yaw = self.yaw ~= nil and self.yaw or 0
		-- extreme mode: a full pull lets the jet go past the AoA limit (Cobra)
		c.postStall = fm.extreme and c.pitch >= 0.95
		return
	end
	c.postStall = false
	steerTowards(fm, self.aim, c, fm.extreme and 1 or PLAYER_G, fm.extreme and 1.5 or 1.3, true)
	if self.yaw ~= nil then c.yaw = self.yaw end
end

-- The AI flies the same jets as the player (with a weaker airframe); its pilot is a little weaker too.
local SKILLS = {
	easy = { g = 0.6, precision = 0.65, missileCd = 36, cm = 0.3, aware = 0.2, gunCone = 0.7, arh = false, zone = 0.5, maxIr = 3500, maxArh = 0, evade = 0.08 },
	normal = { g = 0.8, precision = 0.85, missileCd = 24, cm = 0.6, aware = 0.45, gunCone = 1.0, arh = true, zone = 0.7, maxIr = 4500, maxArh = 8000, evade = 0.15 },
	hard = { g = 0.92, precision = 0.95, missileCd = 15, cm = 0.9, aware = 0.75, gunCone = 1.4, arh = true, zone = 0.8, maxIr = 5500, maxArh = 10000, evade = 0.24 },
	ace = { g = 1.0, precision = 1.0, missileCd = 11, cm = 1.0, aware = 0.95, gunCone = 1.8, arh = true, zone = 0.88, maxIr = 6500, maxArh = 13000, evade = 0.35 },
	wing = { g = 0.95, precision = 0.95, missileCd = 14, cm = 0.9, aware = 0.8, gunCone = 1.4, arh = true, zone = 0.8, maxIr = 5500, maxArh = 11000, evade = 0.2 },
}
A.SKILLS = SKILLS
local MIN_AGL = 450

local AIPilot = {}
AIPilot.__index = AIPilot
local function initAI(self, ac, skill, area)
	self.ac, self.skill, self.rnd, self.area = ac, SKILLS[skill or "normal"], ac.rnd, area
	self.state, self.target, self.threat, self.aware, self.defendTimer = "patrol", nil, nil, {}, 0
	self.missileTimer = self.rnd.uniform(6, 14)
	self.patrolAlt = ac.pos.z
	self.waypoint = self:patrolPoint()
	ac.pilot = self
end
function A.newAIPilot(ac, skill, area)
	local p = setmetatable({}, AIPilot)
	initAI(p, ac, skill, area)
	return p
end
function AIPilot:patrolPoint()
	local a, r = self.area, self.rnd
	if not a then return V(r.uniform(-20000, 20000), r.uniform(-20000, 20000), self.patrolAlt) end
	local ang = r.uniform(0, 2 * math.pi)
	local d = a.r * 0.8 * math.sqrt(r())
	return V(a.x + sin(ang) * d, a.y + cos(ang) * d, self.patrolAlt)
end
-- may this enemy be attacked?  inside the combat zone (+ margin) and not in the base's safe area
function AIPilot:fair(t)
	local a = self.area
	if not a then return true end
	if a.safe and math.sqrt((t.pos.x - a.safe.x) ^ 2 + (t.pos.y - a.safe.y) ^ 2) < a.safe.r then return false end
	return math.sqrt((t.pos.x - a.x) ^ 2 + (t.pos.y - a.y) ^ 2) < a.engage
end
function AIPilot:think(world)
	local ac = self.ac
	self.missileTimer = self.missileTimer - AI_DT
	ac.trigger = false
	local target = nil
	for _, e in ipairs(world:enemiesOf(ac)) do
		if self:fair(e) then
			if not target or len(sub(e.pos, ac.pos)) < len(sub(target.pos, ac.pos)) then target = e end
		end
	end
	self.target = target
	local threat = self:findThreat(world)
	if threat then
		self.threat, self.state, self.defendTimer = threat, "defend", 2.5
	elseif self.defendTimer > 0 then
		self.defendTimer = self.defendTimer - AI_DT
		if self.threat and not self.threat.alive then self.defendTimer = math.min(self.defendTimer, 0.5) end
	else
		self.threat = nil
		self.state = self.target and "engage" or "patrol"
	end
	local t = self.target
	if not t then return end
	local d, r = len(sub(t.pos, ac.pos)), ac.radar
	if not r.on then r:togglePower() end
	if r.locked ~= t and r.pending ~= t and d < r.spec.lockRange then r:tryLock(t) end
	if self.state == "engage" then self:weapons(world, t, d) end
end
function AIPilot:findThreat(world)
	local ac = self.ac
	local best, bd = nil, 1e9
	for _, m in ipairs(world.missiles) do
		if m.alive and m.shooter and m.shooter.team ~= ac.team and (m.guidedTarget == ac or m.intended == ac) then
			local d = len(sub(m.pos, ac.pos))
			local known = self.aware[m.id]
			if not known then
				local warned = false
				if m.spec.guidance == ARH then
					for _, t in ipairs(ac.rwr.threats) do
						if t.level == "launch" and (t.source == m or t.source == m.shooter) then warned = true; break end
					end
				end
				local spotted = d < 4500 and self.rnd() < self.skill.aware * 0.5
				if warned or spotted then self.aware[m.id] = true; known = true end
			end
			if known and d < bd then best, bd = m, d end
		end
	end
	return best
end
function AIPilot:gunSolution(t)
	local dir = gunLead(self.ac.pos, self.ac.vel, t.pos, t.vel, self.ac.spec.gun, 2)
	return dir
end
function AIPilot:weapons(world, t, d)
	local ac = self.ac
	if self.holdFire then return end                  -- peacetime: weapons hold (air policing)
	if d < 1100 and angleBetween(ac.forward, self:gunSolution(t)) < self.skill.gunCone * DEG then ac.trigger = true end
	if self.missileTimer > 0 then return end
	local fired = nil
	local closingT = -dot(t.vel, norm(sub(t.pos, ac.pos)))
	local function zone(key)
		local z = launchZone(ac:missileSpec(key), ac.speed, ac.pos.z, closingT)
		return z * self.skill.zone
	end
	if ac:missileCount("AIM-9M") > 0 and d > 900 and d < math.min(self.skill.maxIr, zone("AIM-9M")) then
		if ac.selected ~= "AIM-9M" then ac:select("AIM-9M")
		elseif ac.irSeeker.candidate == t or ac.irSeeker.target == t then
			if not ac.irSeeker.locked then ac.irSeeker:lock() end
			if ac.irSeeker.target == t then fired = ac:fireMissile(world) end
		end
	elseif ac:missileCount("AIM-120A") > 0 and self.skill.arh and ac.radar.mode == STT and ac.radar.locked == t then
		if d > 2500 and d < math.min(self.skill.maxArh, zone("AIM-120A")) then
			if ac.selected ~= "AIM-120A" then ac:select("AIM-120A") end
			fired = ac:fireMissile(world)
		end
	end
	if fired then self.missileTimer = self.skill.missileCd * self.rnd.uniform(0.8, 1.3) end
end
function AIPilot:fly(dt, world)
	local ac, terr = self.ac, world.terrain
	local desired, throttle, maxG = nil, 1, self.skill.g
	if self.state == "defend" and self.threat and self.threat.alive then desired, throttle, maxG = self:defend(world)
	elseif self.state == "engage" and self.target then desired, throttle = self:pursue(self.target)
	else desired, throttle = self:patrol() end
	local agl = ac.pos.z - terr:height(ac.pos.x, ac.pos.y)
	local ahead = add(ac.pos, mul(ac.vel, 4))
	local aglAhead = ahead.z - terr:height(ahead.x, ahead.y)
	if aglAhead < MIN_AGL or agl < MIN_AGL * 0.7 then
		desired = norm(add(norm(V(ac.vel.x, ac.vel.y, 0)), V(0, 0, 0.9)))
		maxG = 1
	elseif agl < 1800 and desired.z < -0.15 then
		desired = norm(V(desired.x, desired.y, -0.15))
	end
	if abs(ac.pos.x) > 42000 or abs(ac.pos.y) > 42000 then desired = norm(add(norm(V(-ac.pos.x, -ac.pos.y, 0)), mul(desired, 0.3))) end
	local a = self.area
	if a and math.sqrt((ac.pos.x - a.x) ^ 2 + (ac.pos.y - a.y) ^ 2) > a.engage + 4000 then
		desired = norm(add(norm(V(a.x - ac.pos.x, a.y - ac.pos.y, 0)), mul(desired, 0.3)))
	end
	steerTowards(ac.fm, desired, ac.controls, maxG, self.skill.precision)
	ac.controls.throttle = throttle
end
function AIPilot:pursue(t)
	local ac = self.ac
	local rel = sub(t.pos, ac.pos)
	local d = len(rel)
	local desired
	if d < 2500 then desired = self:gunSolution(t) else desired = norm(add(rel, mul(t.vel, math.min(d / 600, 6) * 0.5))) end
	local throttle = 1
	if d > 5000 or ac.speed < 190 then throttle = 1.1
	elseif d < 900 and -dot(sub(t.vel, ac.vel), norm(rel)) > 80 then throttle = 0.6 end
	return desired, throttle
end
function AIPilot:defend(world)
	local ac, m = self.ac, self.threat
	local los = sub(m.pos, ac.pos)
	local d = len(los)
	local flat = norm(V(los.x, los.y, 0))
	local perp = V(-flat.y, flat.x, 0)
	if dot(perp, ac.vel) < 0 then perp = mul(perp, -1) end
	local agl = ac.pos.z - world.terrain:height(ac.pos.x, ac.pos.y)
	local useCm = self.rnd() < self.skill.cm * 0.25
	if m.spec.guidance == ARH then
		if d < 14000 and useCm then ac:dispense(world) end
		return norm(add(perp, V(0, 0, agl > 2500 and -0.25 or 0))), 1, self.skill.g
	end
	if d < 3500 then
		if useCm or d < 1500 then ac:dispense(world) end
		return norm(add(sub(perp, mul(flat, 0.3)), V(0, 0, -0.1))), 0.65, 1
	end
	return norm(add(mul(flat, -1), V(0, 0, -0.05))), 1.1, self.skill.g
end
function AIPilot:patrol()
	local ac = self.ac
	local to = sub(self.waypoint, ac.pos)
	if len(V(to.x, to.y, 0)) < 3000 then self.waypoint = self:patrolPoint() end
	local climb = clamp((self.patrolAlt - ac.pos.z) / 3000, -0.3, 0.3)
	return norm(add(norm(V(to.x, to.y, 0)), V(0, 0, climb))), 0.95
end

-- The player's wingman: flies in formation (behind and to the right) until an enemy comes within reach of the lead,
-- then fights it like any AI pilot, and comes back to the formation when the sky is clear.
local WING_REACH = 26000
local Wingman = setmetatable({}, { __index = AIPilot })
Wingman.__index = Wingman
function A.newWingmanPilot(ac, lead)
	local p = setmetatable({}, Wingman)
	initAI(p, ac, "wing", nil)
	p.lead, p.order = lead, "free"
	return p
end
function Wingman:fair(t)
	local l = self.lead
	if not l or not l.alive then return true end
	if self.order == "rejoin" then return false end
	if self.order == "engage" then return true end
	return len(sub(t.pos, l.pos)) < (self.order == "cover" and 6000 or WING_REACH)
end
function Wingman:think(world)
	AIPilot.think(self, world)
	local l = self.lead
	if self.order == "engage" and l and l.radar and l.radar.locked and l.radar.locked.alive and self.state ~= "defend" then self.target = l.radar.locked end
end
function Wingman:patrol()
	local l, ac = self.lead, self.ac
	if not l or not l.alive or l.onGround then return AIPilot.patrol(self) end
	local fwd = norm(V(l.forward.x, l.forward.y, 0), V(0, 1, 0))
	local right = V(fwd.y, -fwd.x, 0)
	local slot = add(add(l.pos, mul(fwd, -140)), mul(right, 110))
	slot.z = slot.z + 15
	local to = sub(add(slot, mul(l.vel, 1.2)), ac.pos)
	local d = len(to)
	local desired = d > 60 and norm(add(to, mul(l.vel, 1.5))) or norm(l.vel)
	local along = dot(sub(slot, ac.pos), norm(l.vel))
	local throttle = clamp(math.min(1, l.controls.throttle) + along * 0.004 + (l.speed - ac.speed) * 0.02, 0.25, 1.1)
	if d > 3000 then throttle = 1.1 end
	return desired, throttle
end

return A
