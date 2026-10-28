--!nonstrict
-- Point-mass aerodynamics + fly-by-wire (G command with AoA limiter) + landing gear: the port of web/js/flight.js.
-- Everything that differs between the aircraft comes from the spec (Specs).
local M = require(script.Parent.SimMath)
local G, DEG, V = M.G, M.DEG, M.V
local add, sub, mul, dot, cross, len, norm, clamp, interp = M.add, M.sub, M.mul, M.dot, M.cross, M.len, M.norm, M.clamp, M.interp
local qaxis, qmul, fwdOf, upOf, rightOf, qheading = M.qaxis, M.qmul, M.fwdOf, M.upOf, M.rightOf, M.qheading
local sin, cos, sqrt, asin, atan2 = math.sin, math.cos, math.sqrt, math.asin, M.atan2

local R_AIR, GAMMA = 287.05, 1.4
local RHO0 = 1.225
local RHO_TROPOPAUSE = 0.36392

local F = {}
F.RHO0 = RHO0

-- the standard atmosphere: returns density, speed of sound
function F.isa(alt)
	local h = clamp(alt, 0, 32000)
	local temp, p
	if h < 11000 then
		temp = 288.15 - 0.0065 * h
		p = 101325 * (temp / 288.15) ^ 5.25588
	elseif h < 20000 then
		temp = 216.65
		p = 22632.1 * math.exp(-G * (h - 11000) / (R_AIR * temp))
	else
		temp = 216.65 + 0.001 * (h - 20000)
		p = 5474.89 * (temp / 216.65) ^ (-G / (R_AIR * 0.001))
	end
	return p / (R_AIR * temp), sqrt(GAMMA * R_AIR * temp)
end
local isa = F.isa

local CLA_MACH = { { 0, 1 }, { 0.8, 1.08 }, { 0.95, 1.12 }, { 1.1, 0.95 }, { 1.5, 0.8 }, { 2.2, 0.62 } }
local K_ALPHA, K_BETA, TAU_PITCH, TAU_ROLL, TAU_YAW = 6, 3, 0.06, 0.09, 0.12
F.MAX_AB = 1.1
local MAX_AB = F.MAX_AB
local G_ONSET = 10
local SPOOL_UP_CORE, SPOOL_DOWN_CORE, SPOOL_UP_AB, SPOOL_DOWN_AB = 0.30, 0.40, 0.07, 0.25
F.GEAR_HEIGHT = 2.05
local GEAR_HEIGHT = F.GEAR_HEIGHT
local GEAR_TIME, GEAR_CD, FLAP_CL, FLAP_CD = 4, 0.022, 0.22, 0.012
local MU_PAVED, MU_GRASS, MU_BRAKE, MAX_SINK, MAX_BANK = 0.02, 0.07, 0.45, 4.2, 12
local NWS_RATE = 0.45

-- ------------------------------------------------------------------ the controls
function F.newControls(throttle)
	return {
		pitch = 0, roll = 0, yaw = 0, throttle = throttle or 0.85, airbrake = false, brakes = false,
		postStall = false,               -- extreme mode + full aft stick: the AoA limiter lets go (Cobra)
	}
end

-- ------------------------------------------------------------------ the flight model
local FM = {}
local getters = {
	tvc = function(t) if t.extreme and t.spec.tvc then return t.spec.tvc end return nil end,
	mass = function(t) return t.spec.emptyMass + t.fuel + t.storeMass end,
	speed = function(t) return len(t.vel) end,
	forward = function(t) return fwdOf(t.quat) end,
	up = function(t) return upOf(t.quat) end,
	right = function(t) return rightOf(t.quat) end,
	afterburner = function(t) return t.engine > 1.001 and t.fuel > 0 end,
}
FM.__index = function(t, k)
	local m = FM[k]
	if m ~= nil then return m end
	local g = getters[k]
	if g then return g(t) end
	return nil
end

function F.new(spec, pos, vel, quat, fuel)
	local self = setmetatable({}, FM)
	self.spec = spec
	self.pos = pos:clone()
	self.vel = vel:clone()
	self.quat = quat:clone()
	self.omega = V()                       -- x pitch, y roll, z yaw-left (local)
	self.fuel = fuel or spec.internalFuel
	self.storeMass, self.storeCd = 0, 0
	self.engine, self.nzCmd = 0.85, 1
	self.alpha, self.beta, self.mach, self.ias, self.rho, self.qbar = 0, 0, 0, len(vel), RHO0, 0
	self.gLoad, self.thrust, self.accel = 1, 0, V()
	self.gearDown, self.gearPos, self.onGround, self.groundPitch = false, 0, false, 0
	self.contactEvent, self.crashReason, self.sinkRate, self.flaps = nil, "", 0, 0
	self.gearHeight = spec.gearHeight or GEAR_HEIGHT
	self.drag, self.fuelFlow = 0, 0
	self.extreme, self.vectorAngle = false, 0        -- F-16 extreme mode: thrust vectoring on
	return self
end

function FM:placeOnGround(x, y, groundZ, headingDeg)
	self.pos = V(x, y, groundZ + self.gearHeight)
	self.vel = V()
	self.quat = qheading(headingDeg, 0)
	self.omega = V()
	self.gearDown, self.gearPos, self.onGround, self.groundPitch, self.engine, self.nzCmd = true, 1, true, 0, 0, 1
	self.groundZ, self.arrest, self.catapultAcc = groundZ, 0, 0
end

function FM:setGear(down)
	if not down and self.onGround then return false end
	self.gearDown = down
	return true
end

function FM:liftCoefficient(alpha, mach)
	local s = self.spec
	local cla = s.clAlpha * interp(CLA_MACH, mach)
	local a = math.abs(alpha)
	local stall = s.alphaStall * DEG
	local tvc = self.tvc
	local clMax = tvc and tvc.clMax or s.clMax
	local cl
	if a <= stall then
		cl = math.min(cla * a, clMax)
	else
		local peak = math.min(cla * stall, clMax)
		local t = clamp((a - stall) / (15 * DEG), 0, 1)
		cl = peak * (1 - t) + 0.95 * sin(2 * math.min(a, math.pi - a)) * t
	end
	return M.sign(alpha ~= 0 and alpha or 1) * cl
end

function FM:thrustAt(setting, rho, mach)
	local s = self.spec
	if self.fuel <= 0 then return 0 end
	local lapse
	if rho >= RHO_TROPOPAUSE then lapse = (rho / RHO0) ^ 0.75
	else lapse = (RHO_TROPOPAUSE / RHO0) ^ 0.75 * (rho / RHO_TROPOPAUSE) ^ 1.25 end
	local dry = s.thrustDry * (0.04 + 0.96 * math.min(setting, 1) ^ 1.6) * lapse * (1 + 0.02 * mach)
	if setting <= 1 then return dry end
	local ab = clamp((setting - 1) / (MAX_AB - 1), 0, 1)
	return dry + (s.thrustAb * lapse * (1 + 0.3 * mach) - dry) * ab
end

function FM:spool(target, dt)
	local e = self.engine
	if target > e then
		if e < 1 then e = math.min(e + SPOOL_UP_CORE * (0.45 + 0.55 * e) * dt, math.min(target, 1))
		elseif self.fuel > 0 then e = math.min(e + SPOOL_UP_AB * dt, target) end
	elseif target < e then
		e = math.max(e - (e > 1 and SPOOL_DOWN_AB or SPOOL_DOWN_CORE) * dt, target)
	end
	self.engine = e
end

function FM:step(dt, c, terrain)
	local s = self.spec
	local fwd, up, right = self.forward, self.up, self.right
	local rho, aSound = isa(self.pos.z)
	local speed = self.speed
	local vhat = speed > 1 and mul(self.vel, 1 / speed) or fwd:clone()
	local alpha = speed > 1 and atan2(-dot(self.vel, up), dot(self.vel, fwd)) or 0
	local beta = asin(clamp(dot(self.vel, right) / math.max(speed, 1), -1, 1))
	local mach = speed / aSound
	local qbar = 0.5 * rho * speed * speed
	local mass = self.mass

	self:spool(clamp(c.throttle, 0, s.noAB and 1 or MAX_AB), dt)       -- turboprop / plain turbofan trainers: no afterburner
	local tv = self.tvc
	local thrust = self:thrustAt(self.engine, rho, mach) * (tv and tv.thrustScale or 1)
	self.thrust = thrust
	local sfc = self.engine <= 1 and s.fuelFlowDry / s.thrustDry or s.fuelFlowAb / s.thrustAb
	self.fuelFlow = thrust * sfc
	self.fuel = math.max(0, self.fuel - self.fuelFlow * dt)

	local cl = self:liftCoefficient(alpha, mach)
	local flaps = self.gearPos * clamp((125 - speed * sqrt(rho / RHO0)) / 25, 0, 1)
	self.flaps = flaps
	if flaps > 0 and alpha > -0.05 then cl = cl + FLAP_CL * flaps end
	local liftDir = norm(cross(right, vhat), up)
	local sideDir = cross(vhat, liftDir)
	local cd = s.cd0 + (s.pylonCd or 0) + interp(s.waveDrag, mach) + s.kInduced * (tv and tv.kScale or 1) * cl * cl + self.storeCd + 0.8 * sin(alpha) ^ 2
	if c.airbrake then cd = cd + s.airbrakeCd end
	cd = cd + GEAR_CD * self.gearPos + FLAP_CD * flaps
	local area = s.wingArea
	self.drag = qbar * area * cd
	-- thrust vectoring: the nozzle turns with the pitch stick, part of the thrust pushes the tail down (nose up)
	local vec = (tv and not self.onGround) and clamp(c.pitch, -1, 1) * tv.vector * DEG or 0
	self.vectorAngle = self.vectorAngle + (vec - self.vectorAngle) * math.min(1, dt * 8)
	local force = add(add(add(mul(liftDir, qbar * area * cl), mul(sideDir, -qbar * area * 1.1 * beta)),
		mul(vhat, -qbar * area * cd)), add(mul(fwd, thrust * cos(self.vectorAngle)), mul(up, thrust * sin(self.vectorAngle))))
	local acc = add(mul(force, 1 / mass), V(0, 0, -G))

	-- landing gear
	local target = self.gearDown and 1 or 0
	self.gearPos = self.gearPos + clamp(target - self.gearPos, -dt / GEAR_TIME, dt / GEAR_TIME)
	self.contactEvent = nil
	if terrain then
		local groundZ = terrain:height(self.pos.x, self.pos.y)
		local tele = { force = force, mass = mass, alpha = alpha, mach = mach, rho = rho, qbar = qbar, speed = speed }
		if self.onGround then self:groundStep(dt, c, acc, terrain, tele) return end
		if self.pos.z - groundZ <= self.gearHeight then
			if self:touchdown(groundZ, terrain) then self:groundStep(dt, c, acc, terrain, tele) end
			return
		end
	end

	-- FLCS pitch: G command with AoA limiter and onset limit
	local stick = clamp(c.pitch, -1, 1)
	local nz = stick >= 0 and 1 + stick * (s.gMax - 1) or 1 + stick * (1 - s.gMin)
	self.nzCmd = self.nzCmd + clamp(nz - self.nzCmd, -G_ONSET * dt, G_ONSET * dt)
	nz = self.nzCmd
	local claEff = s.clAlpha * interp(CLA_MACH, mach)
	-- AoA limit: normal, or in extreme mode 30 degrees (the mouse instructor) / 80 with full aft stick (Cobra)
	local alphaLim = (tv and (c.postStall and tv.alphaPostStall or tv.alphaNormal) or s.alphaLimit) * DEG
	local alphaReq
	if qbar > 1 then alphaReq = nz * mass * G / (qbar * area * claEff) else alphaReq = alphaLim * (nz > 0 and 1 or -1) end
	alphaReq = clamp(alphaReq, -10 * DEG, alphaLim)
	-- Cobra: below ~600 km/h a full pull with vectored thrust throws the nose straight up to the limit
	if tv and c.postStall and speed < 170 then alphaReq = alphaLim end
	local vSafe = math.max(speed, 30)
	local pathPitch = dot(acc, liftDir) / vSafe
	local pathLat = dot(acc, sideDir) / vSafe
	-- the vectored nozzle keeps pitch and roll authority even when the air is too slow for the tail
	local authority = clamp(qbar / 9000 + (tv and tv.lowSpeedAuthority or 0), 0.12, 1)
	local qMax = tv and tv.pitchRate or 0.9
	local qCmd = clamp(pathPitch + K_ALPHA * (alphaReq - alpha) * authority, -qMax, qMax)
	local rollEff = clamp(qbar / 9000 + (tv and tv.lowSpeedAuthority * 0.5 or 0), 0.15, 1) * (1 - 0.5 * clamp(alpha / alphaLim, 0, 1))
	local pCmd = clamp(c.roll, -1, 1) * (tv and tv.rollRate or s.rollRate) * DEG * rollEff
	local betaCmd = -clamp(c.yaw, -1, 1) * s.yawBeta * DEG
	local rCmd = pathLat + K_BETA * (beta - betaCmd) * authority
	self.omega.x = self.omega.x + (qCmd - self.omega.x) * math.min(1, dt / TAU_PITCH)
	self.omega.y = self.omega.y + (pCmd - self.omega.y) * math.min(1, dt / TAU_ROLL)
	self.omega.z = self.omega.z + (-rCmd - self.omega.z) * math.min(1, dt / TAU_YAW)

	self.vel:addScaled(acc, dt)
	self.pos:addScaled(self.vel, dt)
	local rot = mul(self.omega, dt)
	local ang = len(rot)
	if ang > 1e-9 then
		self.quat = qmul(self.quat, qaxis(rot, ang))
		self.quat:normalize()
	end

	self.alpha, self.beta, self.mach, self.rho, self.qbar = alpha, beta, mach, rho, qbar
	self.ias = speed * sqrt(rho / RHO0)
	self.accel = acc
	self.gLoad = dot(mul(force, 1 / mass), up) / G
end

function FM:touchdown(groundZ, terrain)
	local fwd, s = self.forward, self.spec
	local pitch = asin(clamp(fwd.z, -1, 1)) / DEG
	local r = self.right
	local bank = atan2(-r.z, self.up.z) / DEG
	self.sinkRate = math.max(0, -self.vel.z)
	local reason = ""
	local tail = s.tailStrike or 13
	if self.gearPos < 0.98 then
		reason = self.gearPos < 0.1 and "futómű nélkül értél földet" or "a futómű nem volt kint"
	elseif self.sinkRate > MAX_SINK then reason = string.format("túl kemény földetérés (%.1f m/s)", self.sinkRate)
	elseif math.abs(bank) > MAX_BANK then reason = "szárnyvéggel értél földet"
	elseif pitch < -3 then reason = "orral értél földet"
	elseif pitch > tail + 7 then reason = "farokkal értél földet"
	elseif terrain:slope(self.pos.x, self.pos.y) > 6 * DEG then reason = "egyenetlen terep"
	elseif terrain.isWater and terrain.isWater(self.pos.x, self.pos.y) then reason = "a tengerbe csapódtál" end
	if reason ~= "" then
		self.contactEvent, self.crashReason = "crash", reason
		self.pos.z = groundZ + 1
		return false
	end
	self.onGround = true
	self.contactEvent = pitch > tail + 2 and "tailstrike" or "touchdown"
	self.groundPitch = math.max(0, pitch) * DEG
	self.omega = V()
	self.nzCmd = 1
	self.pos.z = groundZ + self.gearHeight
	self.vel.z = 0
	self.groundZ = groundZ
	return true
end

function FM:groundStep(dt, c, acc, terrain, t)
	local fwd = self.forward
	local heading = atan2(fwd.x, fwd.y)
	local hDir = V(sin(heading), cos(heading), 0)
	local hRight = V(hDir.y, -hDir.x, 0)
	local normal = 0
	if acc.z < 0 then normal = -acc.z; acc.z = 0 end
	local paved = true
	if terrain.airfield then paved = terrain.airfield:onPaved(self.pos.x, self.pos.y) end
	local mu = (paved and MU_PAVED or MU_GRASS) + ((c.brakes or self.parkBrake) and MU_BRAKE or 0)
	local u, w = dot(self.vel, hDir), dot(self.vel, hRight)
	if math.abs(u) > 1e-3 then
		local decel = math.min(mu * normal, math.abs(u) / dt)
		acc:addScaled(hDir, -M.sign(u) * decel)
	elseif normal > 0 then
		local along, hold = dot(acc, hDir), mu * normal
		acc:addScaled(hDir, -(math.abs(along) <= hold and along or M.sign(along) * hold))
	end
	-- carrier: the catapult shuttle pulls forward, the arresting wire holds back (set by the game)
	if self.catapultAcc and self.catapultAcc ~= 0 then acc:addScaled(hDir, self.catapultAcc) end
	if self.arrest and self.arrest ~= 0 then
		if u > 1.2 then acc:addScaled(hDir, -math.min(self.arrest, u / dt)) else self.arrest = 0 end
	end
	local grip = 0.8 * normal
	acc:addScaled(hRight, -clamp(w / math.max(dt, 0.02), -grip, grip))

	local gs = math.max(math.abs(u), 0.1)
	local nws = self.groundPitch < 2 * DEG and NWS_RATE * math.min(1, 8 / gs) or 0
	local yawRate = clamp(c.yaw, -1, 1) * (nws + 0.03 * math.min(gs / 60, 1)) * (gs > 0.3 and 1 or 0)
	local ias = t.speed * sqrt(t.rho / RHO0)
	local rotateIas = self.spec.rotateIas or 60
	local auth = clamp((ias - rotateIas) / 12, 0, 1)
	local tailStrike = self.spec.tailStrike or 13
	local stick = clamp(c.pitch, -1, 1)
	local pitchRate = stick > 0 and stick * 7 * DEG * auth or 0
	if pitchRate <= 0 then pitchRate = -3.5 * DEG end
	if self.catapultAcc and self.catapultAcc ~= 0 and ias > rotateIas - 4 then pitchRate = math.max(pitchRate, 9 * DEG) end   -- catapult: hands-off rotation
	self.groundPitch = clamp(self.groundPitch + pitchRate * dt, 0, tailStrike * DEG)

	self.vel:addScaled(acc, dt)
	self.pos:addScaled(self.vel, dt)
	heading = heading + yawRate * dt
	self.quat = qheading(heading / DEG, self.groundPitch / DEG)
	self.omega = V(self.groundPitch > 0 and pitchRate or 0, 0, 0)
	local ng = terrain:height(self.pos.x, self.pos.y)
	if self.groundZ ~= nil and self.groundZ - ng > 3 then
		-- rolled off an edge (the carrier's deck): from here it flies - or falls
		self.onGround, self.groundZ, self.catapultAcc = false, nil, 0
		self.alpha, self.mach, self.rho, self.qbar, self.ias, self.accel = t.alpha, t.mach, t.rho, t.qbar, ias, acc
		return
	end
	self.groundZ = ng
	if normal == 0 and self.vel.z > 0 then
		if self.pos.z > ng + self.gearHeight + 0.3 then self.onGround = false; self.groundZ = nil end
	else
		self.pos.z = ng + self.gearHeight
		self.vel.z = 0
	end
	self.alpha, self.beta, self.mach, self.rho, self.qbar = t.alpha, 0, t.mach, t.rho, t.qbar
	self.ias, self.accel = ias, acc
	self.gLoad = dot(mul(t.force, 1 / t.mass), self.up) / G + normal / G
end

return F
