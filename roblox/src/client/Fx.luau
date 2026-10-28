--!nonstrict
-- Smoke, fire, flashes and tracer lines: the particles of web/js/render.js (Particles.spawn(pos, vel, life, size, colour, drag, rise)) made
-- of ParticleEmitters.  An emitter makes particles where its part is when Emit is called, so every spawn takes the next part of a pool,
-- moves it there, sets the emitter up (size / colour / speed ...) and emits one particle.  Sizes are metres of the game, drawn at the
-- model scale (Config.ModelScale) so that the effects match the jets.  All positions are in the simulation's frame (metres).
local Config = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared").Config)
local Coords = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared").Coords)

local Fx = {}
Fx.__index = Fx

local TEXTURE = "rbxasset://textures/particles/smoke_main.dds"
local POOL = 120

local function makePool(folder, additive)
	local pool = { parts = {}, emitters = {}, i = 0 }
	for i = 1, POOL do
		local p = Instance.new("Part")
		p.Name = "Fx"
		p.Anchored = true
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.Transparency = 1
		p.Size = Vector3.new(0.2, 0.2, 0.2)
		p.CFrame = CFrame.new(0, -5000, 0)
		local e = Instance.new("ParticleEmitter")
		e.Enabled = false
		e.Rate = 0
		e.Texture = TEXTURE
		e.LightEmission = additive and 1 or 0
		e.LightInfluence = additive and 0 or 0.6
		e.EmissionDirection = Enum.NormalId.Front
		e.SpreadAngle = Vector2.new(0, 0)
		e.Rotation = NumberRange.new(0, 360)
		e.RotSpeed = NumberRange.new(-30, 30)
		e.LockedToPart = false
		e.Orientation = Enum.ParticleOrientation.FacingCamera
		e.ZOffset = additive and 0.5 or 0
		e.Parent = p
		p.Parent = folder
		pool.parts[i] = p
		pool.emitters[i] = e
	end
	return pool
end

function Fx.new(rnd)
	local self = setmetatable({}, Fx)
	local folder = Instance.new("Folder")
	folder.Name = "Effects"
	folder.Parent = workspace
	self.folder = folder
	self.smoke = makePool(folder, false)
	self.fire = makePool(folder, true)
	self.k = Config.Island.StudsPerMeter * Config.ModelScale          -- studs per metre of an effect's size
	self.s = Config.Island.StudsPerMeter                               -- studs per metre of a position
	self.rnd = rnd
	self.budget = 0
	-- tracers
	self.tracers = {}
	for i = 1, 90 do
		local t = Instance.new("Part")
		t.Name = "Tracer"
		t.Anchored = true
		t.CanCollide = false
		t.CanQuery = false
		t.CanTouch = false
		t.Material = Enum.Material.Neon
		t.Size = Vector3.new(0.16, 0.16, 1)
		t.CFrame = CFrame.new(0, -5000, 0)
		t.Parent = folder
		self.tracers[i] = t
	end
	return self
end

local function seq(a0, a1, f)
	return NumberSequence.new({ NumberSequenceKeypoint.new(0, f(a0)), NumberSequenceKeypoint.new(1, f(a1)) })
end

-- pos (a sim vector), vel (a sim vector or nil), life (s), size {start, end} (m), colour {{r,g,b,a},{r,g,b,a}} (0..1), drag (1/s), rise (m/s^2)
local function spawn(self, pool, pos, vel, life, size, color, drag, rise)
	if self.budget <= 0 then return end
	self.budget -= 1
	pool.i = pool.i % POOL + 1
	local part, e = pool.parts[pool.i], pool.emitters[pool.i]
	local p = Coords.pos(pos)
	if vel and (vel.x ~= 0 or vel.y ~= 0 or vel.z ~= 0) then
		local v = Coords.vec(vel)
		part.CFrame = CFrame.lookAt(p, p + v)
		e.Speed = NumberRange.new(v.Magnitude)
	else
		part.CFrame = CFrame.new(p)
		e.Speed = NumberRange.new(0)
	end
	e.Lifetime = NumberRange.new(life)
	local k = self.k
	e.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, math.max(0.05, size[1] * k)), NumberSequenceKeypoint.new(1, math.max(0.05, size[2] * k)) })
	local c0, c1 = color[1], color[2]
	e.Color = ColorSequence.new(Color3.new(c0[1], c0[2], c0[3]), Color3.new(c1[1], c1[2], c1[3]))
	e.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, math.clamp(1 - c0[4], 0, 1)), NumberSequenceKeypoint.new(1, math.clamp(1 - c1[4], 0, 1)) })
	e.Drag = drag or 0
	e.Acceleration = Vector3.new(0, (rise or 0) * self.s, 0)
	e:Emit(1)
end

function Fx:smokeAt(pos, vel, life, size, color, drag, rise) spawn(self, self.smoke, pos, vel, life, size, color, drag, rise) end
function Fx:fireAt(pos, vel, life, size, color, drag, rise) spawn(self, self.fire, pos, vel, life, size, color, drag, rise) end
-- how many particles may be made in one frame
function Fx:frame(budget) self.budget = budget end

-- tracer lines of the bullets (world.bullets), at most as many as there are parts
function Fx:setTracers(bullets)
	local n = 0
	local s = self.s
	for _, b in ipairs(bullets) do
		if b.tracer then
			n += 1
			local t = self.tracers[n]
			if not t then break end
			local a = Coords.pos(b.pos)
			local tail = Coords.posXYZ(b.pos.x - b.vel.x * 0.014, b.pos.y - b.vel.y * 0.014, b.pos.z - b.vel.z * 0.014)
			local len = (a - tail).Magnitude
			t.Size = Vector3.new(0.18, 0.18, math.max(len, 0.5) * 1.5)
			t.CFrame = CFrame.lookAt((a + tail) / 2, a)
			local tc = b.owner and b.owner.tracerColor
			t.Color = tc and Color3.new(tc[1], tc[2], tc[3]) or Color3.new(1, 0.85, 0.35)
			t.Transparency = 0
		end
	end
	for i = n + 1, #self.tracers do
		local t = self.tracers[i]
		if t.Transparency < 1 then t.Transparency = 1 end
	end
end

function Fx:destroy() self.folder:Destroy() end

return Fx
