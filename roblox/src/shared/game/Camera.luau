--!nonstrict
-- The flight camera: the port of FlightCamera of web/js/game.js (without the three.js camera object).  The mouse moves an aim
-- point on the sphere round the jet (the instructor flies the nose there); with C / right mouse held the head looks round
-- freely; in the cockpit the head turns about the neck and the eyes lean past the seat; V = cockpit, N = look down at the displays.
-- Everything is in the simulation's frame (metres; x east, y north, z up; the view looks along +Y of its orientation).  After
-- update(): self.position (a vector), self.orientation (a quaternion, with the shake), self.fov (vertical, degrees), self.shift.
-- Common subset of Lua 5.4 and Luau.
local M = require(script.Parent.Parent.sim.SimMath)
local V, add, sub, mul, dot, cross, norm, clamp, DEG = M.V, M.add, M.sub, M.mul, M.dot, M.cross, M.norm, M.clamp, M.DEG
local qaxis, qmul, qlook, fwdOf, upOf, xform = M.qaxis, M.qmul, M.qlook, M.fwdOf, M.upOf, M.xform
local atan2, sin, cos, exp, abs, min, max = M.atan2, math.sin, math.cos, math.exp, math.abs, math.min, math.max

local C = {}
C.CHASE_DISTANCE, C.CHASE_HEIGHT = 26, 5.5
C.HEAD_YAW = 160 * DEG                                   -- a pilot turns the head at most 160 degrees each way
C.SENS_BASE = 0.09                                       -- "100 %" on the sensitivity sliders
C.STICK_GAIN, C.STICK_DEADZONE = 0.045, 0.07
local NECK, EYE_FROM_NECK, LEAN_SIDE, LEAN_FWD = V(0, -0.09, -0.06), V(0, 0.09, 0.06), 0.18, 0.12
C.COCKPIT_SHIFT = 0.13

local function ease(t) t = clamp(t, 0, 1); return t * t * (3 - 2 * t) end

local Cam = {}
Cam.__index = Cam
function C.new(terrain)
	local self = setmetatable({}, Cam)
	self.terrain, self.eye = terrain, V(0, 2.4, 1.1)
	self.sensitivity, self.stickSens, self.invertY = C.SENS_BASE * 0.6, 0.6, false
	self.aim, self.look = M.Q(), M.Q()
	self.freeLook, self.cockpit, self.position, self.fov, self.phase, self.zoom = false, false, V(), 70, 0, 0
	self.headYaw, self.headPitch, self.headG = 0, 0, 0
	self.panelLook, self.panel, self.panelFov = false, nil, 30
	self.baseFov = 70
	self.follow, self.followLabel = nil, ""
	self.orientation, self.shift, self.kick = M.Q(), 0, 0
	self.rand = function() return math.random() end
	return self
end
function Cam:reset(ac)
	self.aim = qlook(ac.forward)
	self.look = self.aim:clone()
end
function Cam:aimDirection() return fwdOf(self.aim) end
function Cam:setFreeLook(on)
	if on and not self.freeLook and not self.cockpit then self.look = self.aim:clone() end
	if on then self.panelLook = false end
	self.freeLook = on
end
function Cam:rotate(yawDeg, pitchDeg)
	if self.cockpit and self.freeLook then                   -- turning the head inside the cockpit
		self.headYaw = clamp(self.headYaw + yawDeg * DEG, -C.HEAD_YAW, C.HEAD_YAW)
		self.headPitch = clamp(self.headPitch + pitchDeg * DEG, -0.9, 1.4)
		return
	end
	local q = self.freeLook and self.look or self.aim
	q = qmul(qaxis(V(0, 0, 1), yawDeg * DEG), q)             -- yaw around world up
	q = qmul(q, qaxis(V(1, 0, 0), pitchDeg * DEG)):normalize() -- pitch around local right
	if self.freeLook then self.look = q else self.aim = q end
end
function Cam:mouseDelta(dx, dy)
	self:rotate(-dx * self.sensitivity, -dy * self.sensitivity * (self.invertY and -1 or 1))
end
-- rolls the view back upright (the aim point never stays tilted)
function C.level(q, dt, rate)
	rate = rate or 1.6
	local fwd = fwdOf(q)
	if abs(fwd.z) > 0.96 then return q end
	local up = upOf(q)
	local want = norm(sub(V(0, 0, 1), mul(fwd, fwd.z)))
	local ang = atan2(dot(cross(up, want), fwd), dot(up, want))
	local step
	if abs(ang) < 2.5 then step = clamp(ang, -rate * dt, rate * dt) else step = ang * min(1, rate * 0.6 * dt) end
	return qmul(q, qaxis(V(0, 1, 0), step))
end

function Cam:update(dt, ac)
	self.aim = C.level(self.aim, dt)
	if self.freeLook then self.look = C.level(self.look, dt) end
	if not ac then return end
	local view = self.freeLook and self.look or self.aim
	local f = self.follow
	local terrain = self.terrain
	if f then
		-- missile cam / kill cam: behind the followed object, looking where it goes
		view = qlook(f.dir)
		self.position = add(sub(f.pos, mul(f.dir, f.dist)), mul(upOf(view), f.height))
		local ground = terrain:height(self.position.x, self.position.y)
		if self.position.z < ground + 3 then self.position.z = ground + 3 end
	elseif self.cockpit and ac.alive then
		-- the pilot's head is part of the jet: the view rolls, pitches and yaws with it.  Under G the head sags or lifts a few cm.
		if not self.freeLook then
			-- the head comes back to the front, or with N turns down to the instrument panel
			local k = exp(-6 * dt)
			local p = (self.panelLook and self.panel) and atan2(self.panel.z - self.eye.z, self.panel.y - self.eye.y) or 0
			self.headYaw = self.headYaw * k
			self.headPitch = p + (self.headPitch - p) * k
		end
		local sag = clamp(-(ac.fm.gLoad - 1) * 0.012, -0.06, 0.09)
		self.headG = self.headG + (sag - self.headG) * min(1, dt * 6)
		local head = qmul(qaxis(V(0, 0, 1), self.headYaw), qaxis(V(1, 0, 0), self.headPitch))
		view = qmul(ac.quat, head)
		local lean = ease((abs(self.headYaw) - 40 * DEG) / (100 * DEG))
		local body = V(-M.sign(self.headYaw) * LEAN_SIDE * lean, LEAN_FWD * lean, self.headG)
		local eye = add(add(self.eye, NECK), add(xform(head, EYE_FROM_NECK), body))
		self.position = add(ac.pos, xform(ac.quat, eye))
	else
		local dist = ac.alive and C.CHASE_DISTANCE or 70
		self.position = add(sub(ac.pos, mul(fwdOf(view), dist)), mul(upOf(view), C.CHASE_HEIGHT))
		local ground = terrain:height(self.position.x, self.position.y)
		if self.position.z < ground + 3 then self.position.z = ground + 3 end
	end
	self.phase = self.phase + dt
	local shake = 0
	if ac.alive and ac.gun.firing then shake = shake + 0.07 end
	if ac.alive and ac.fm.gLoad > 6 then shake = shake + (ac.fm.gLoad - 6) * 0.03 end
	if self.kick > 0 then
		shake = shake + self.kick * 0.6
		self.kick = max(0, self.kick - dt * 1.6)                       -- a blast nearby
	end
	local q = view
	if shake > 0 then
		q = qmul(q, qmul(qaxis(V(1, 0, 0), sin(self.phase * 53) * shake * DEG), qaxis(V(0, 0, 1), sin(self.phase * 71) * shake * DEG)))
	end
	self.orientation = q
	local panel = self.cockpit and self.panelLook and ac.alive and not f
	local b = self.baseFov
	local target
	if panel then target = self.panelFov
	elseif f then target = b
	else target = ({ self.cockpit and b + 5 or b, b * 0.64, b * 0.4 })[self.zoom + 1] end
	self.fov = self.fov + (target - self.fov) * min(1, dt * 8)
	-- cockpit: the picture is shifted so the HUD sits above the screen centre (a lens shift in the browser)
	local shift = (self.cockpit and ac.alive and not panel and not f) and C.COCKPIT_SHIFT or 0
	self.shift = self.shift + (shift - self.shift) * min(1, dt * 8)
end

return C
