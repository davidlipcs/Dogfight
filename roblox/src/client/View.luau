--!nonstrict
-- What the match looks like: the aircraft (the game's own .glb jets when imported, otherwise built from parts), the missiles, the effects
-- and the camera.  The port of SceneView.update / visualFor / handleEvent / aircraftEffects of web/js/render.js.  The simulation's frame is
-- metres (x east, y north, z up); the Roblox world is Config.Island.StudsPerMeter studs per metre, and what is drawn is Config.ModelScale
-- times bigger (see Fx.luau for the effects).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Coords = require(Shared.Coords)
local JetBuilder = require(Shared.JetBuilder)
local JetInfo = require(Shared.JetInfo)
local SimMath = require(Shared.sim.SimMath)
local Fx = require(script.Parent.Fx)

local V, add, mul, xform, DEG = SimMath.V, SimMath.add, SimMath.mul, SimMath.xform, SimMath.DEG

local View = {}
View.__index = View

local K = Config.Island.StudsPerMeter * Config.ModelScale                -- studs per metre of a model
local FAR = 14000                                                          -- beyond this a jet is a dot: not drawn (m)

local function vec3(b) return Vector3.new(b[1], b[3], -b[2]) end            -- a body-frame point { x, y, z } -> model offset in metres

function View.new(world)
	local self = setmetatable({}, View)
	self.world = world
	self.fx = Fx.new(world.rnd)
	self.visuals, self.missileVis = {}, {}
	self.time = 0
	self.quality = "high"
	local folder = Instance.new("Folder")
	folder.Name = "Visuals"
	folder.Parent = workspace
	self.folder = folder
	local cam = workspace.CurrentCamera
	self.camera = cam
	cam.CameraType = Enum.CameraType.Scriptable
	return self
end

-- a flat triangle of two wedges (the standard way of drawing a triangle with parts)
local function triangle(parent, a, b, c, color, name)
	local ab, ac, bc = b - a, c - a, c - b
	local abd, acd, bcd = ab:Dot(ab), ac:Dot(ac), bc:Dot(bc)
	if abd > acd and abd > bcd then c, a = a, c
	elseif acd > bcd and acd > abd then a, b = b, a end
	ab, ac, bc = b - a, c - a, c - b
	local right = ac:Cross(ab).Unit
	local up = bc:Cross(right).Unit
	local back = bc.Unit
	local height = math.abs(ab:Dot(up))
	local function wedge()
		local w = Instance.new("WedgePart")
		w.Name = name or "Tri"
		w.Anchored, w.CanCollide, w.CanQuery, w.CanTouch, w.Massless, w.CastShadow = true, false, false, false, true, false
		w.Color = color
		w.Material = Enum.Material.Concrete
		w.TopSurface, w.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
		w.Parent = parent
		return w
	end
	local w1, w2 = wedge(), wedge()
	w1.Size = Vector3.new(0.1, height, math.abs(ab:Dot(back)))
	w1.CFrame = CFrame.fromMatrix((a + b) / 2, right, up, back)
	w2.Size = Vector3.new(0.1, height, math.abs(ac:Dot(back)))
	w2.CFrame = CFrame.fromMatrix((a + c) / 2, -right, up, -back)
end

-- the carrier (shared/game/Carrier.luau) from parts, at the island's scale: a hull, the angled flight deck, the island with its mast
function View:buildCarrier(carrier)
	local Carrier = require(Shared.game.Carrier)
	local S = Config.Island.StudsPerMeter
	local folder = Instance.new("Folder")
	folder.Name = "Carrier"
	folder.Parent = self.folder
	local function at(lx, ly, z) return Coords.pos(carrier:world(lx, ly, z)) end
	local function block(name, cx, cy, cz, w, l, h, color, material)
		local p = Instance.new("Part")
		p.Name = name
		p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Massless = true, false, false, false, true
		p.Size = Vector3.new(w * S, h * S, l * S)
		p.CFrame = CFrame.new(at(cx, cy, cz)) * CFrame.Angles(0, -math.rad(carrier.heading), 0)
		p.Color = color
		p.Material = material or Enum.Material.Metal
		p.Parent = folder
		return p
	end
	local grey, dark = Color3.fromRGB(124, 132, 140), Color3.fromRGB(65, 70, 76)
	local secs = { { 166, 2 }, { 150, 12 }, { 120, 18 }, { 60, 20.5 }, { -100, 20.5 }, { -150, 19 }, { -162, 17 } }
	local zTop = Carrier.DECK_Z - 1.2
	for i = 1, #secs - 1 do
		local y0, w0, y1, w1 = secs[i][1], secs[i][2], secs[i + 1][1], secs[i + 1][2]
		block("Hull", 0, (y0 + y1) / 2, (zTop - 6) / 2, (w0 + w1) * 0.9, y0 - y1, zTop + 6, grey)
	end
	block("Boot", 0, 0, 0.4, 38, 300, 2.2, Color3.fromRGB(106, 42, 36))
	-- the deck: the outline as triangles (fan from the first corner)
	local o = Carrier.OUTLINE
	for i = 2, #o - 1 do
		triangle(folder, at(o[1][1], o[1][2], Carrier.DECK_Z), at(o[i][1], o[i][2], Carrier.DECK_Z), at(o[i + 1][1], o[i + 1][2], Carrier.DECK_Z), dark, "Deck")
	end
	-- the island, the mast and the radar
	block("Island", 19, 6, Carrier.DECK_Z + 7, 9, 34, 14, grey)
	block("Bridge", 18.7, 8, Carrier.DECK_Z + 17, 8, 26, 6, grey)
	block("Mast", 19, 10, Carrier.DECK_Z + 33, 1.2, 1.2, 16, grey)
	-- the landing line and the wires, painted on the deck
	local lx, ly = carrier.landStart[1], carrier.landStart[2]
	local dx, dy = carrier.landDir[1], carrier.landDir[2]
	for _, w in ipairs(Carrier.WIRES) do
		local px, py = lx + dx * w, ly + dy * w
		local p = block("Wire", px, py, Carrier.DECK_Z + 0.2, 24, 0.8, 0.2, Color3.fromRGB(190, 190, 190), Enum.Material.SmoothPlastic)
		p.CFrame = CFrame.new(at(px, py, Carrier.DECK_Z + 0.3)) * CFrame.Angles(0, SimMath.atan2(dx, dy), 0)
	end
	for _, c in ipairs(Carrier.CATS) do
		block("Cat", c[1], (c[2] + c[3]) / 2, Carrier.DECK_Z + 0.2, 1.5, c[3] - c[2], 0.2, Color3.fromRGB(30, 33, 36), Enum.Material.SmoothPlastic)
	end
end

function View:setWorld(world)
	self.world = world
	self.fx.rnd = world.rnd
end

local function anchorAll(model)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.Massless = true
		elseif d:IsA("WeldConstraint") or d:IsA("Weld") then d:Destroy() end
	end
end

local function ball(parent, name, color, size)
	local p = Instance.new("Part")
	p.Name = name
	p.Shape = Enum.PartType.Ball
	p.Material = Enum.Material.Neon
	p.Color = color
	p.Size = Vector3.new(size, size, size)
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Massless = true, false, false, false, true
	p.CastShadow = false
	p.Parent = parent
	return p
end

-- a missile model (metres * K): body, nose, four fins, in its own frame (nose toward -Z), PrimaryPart "Body"
local function missileModel(spec)
	local m = Instance.new("Model")
	m.Name = "Missile"
	local len, d = spec.length, math.max(spec.diameter * 2.5, 0.26)
	local ir = spec.guidance == "IR"
	local white, dark = Color3.fromRGB(226, 228, 230), Color3.fromRGB(70, 74, 80)
	local function part(name, size, cf, color, shape, material)
		local p = Instance.new("Part")
		p.Name = name
		p.Size = size * K
		p.CFrame = cf
		p.Color = color
		p.Material = material or Enum.Material.SmoothPlastic
		if shape then p.Shape = shape end
		p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Massless = true, false, false, false, true
		p.CastShadow = false
		p.Parent = m
		return p
	end
	local body = part("Body", Vector3.new(len * 0.82, d, d), CFrame.Angles(0, math.rad(90), 0), white, Enum.PartType.Cylinder)
	m.WorldPivot = CFrame.new()                                      -- the pivot is the model's own origin (not the cylinder's turned body part)
	part("Nose", Vector3.new(d * 1.4, d, d), CFrame.new(0, 0, -len * 0.45 * K) * CFrame.Angles(0, math.rad(90), 0), ir and dark or white, Enum.PartType.Cylinder)
	for i = 0, 3 do
		local a = i * math.pi / 2 + math.pi / 4
		local fin = part("Fin", Vector3.new(0.05, d * 1.8, len * 0.16), CFrame.new(math.cos(a) * d * 0.5 * K, math.sin(a) * d * 0.5 * K, len * 0.36 * K) * CFrame.Angles(0, 0, a - math.pi / 2), dark)
		fin.Size = Vector3.new(0.05 * K, d * 1.4 * K, len * 0.16 * K)
	end
	return m
end

local function jetModel(ac)
	local info = JetInfo[ac.spec.model] or JetInfo.f16
	local enemy = ac.team == "red" and not ac.human
	local model = JetBuilder.build((not enemy) and ac.skin or nil, (not enemy) and ac.outfit or nil, enemy, false, nil, ac.spec.model)
	for _, d in model:GetChildren() do
		if d.Name == "Flame" or d.Name == "Missile" then d:Destroy() end          -- the flames and the missiles are drawn here
	end
	anchorAll(model)
	model:ScaleTo(K)
	return model, info
end

function View:visualFor(ac)
	local v = self.visuals[ac]
	if v then return v end
	local model, info = jetModel(ac)
	model.Parent = self.folder
	v = { model = model, info = info, trail = 0, phase = math.random() * 1.2, flames = {}, strobes = {}, stores = {}, shown = true }
	-- the missiles on the stations
	for _, st in ipairs(ac.stations) do
		local mm = missileModel(st.spec)
		local ref = info.refs["store_" .. st.number]
		local at = ref and vec3(ref) or vec3({ st.mount.x, st.mount.y, st.mount.z })
		mm:PivotTo(CFrame.new(at * K))
		mm.Parent = model
		v.stores[st.number] = { model = mm, loaded = true }
	end
	-- lamps and strobes
	for _, n in ipairs(info.nav) do
		ball(model, "Lamp", JetBuilder.color(n.color), 0.55 * K).CFrame = CFrame.new(vec3(n.pos) * K)
	end
	for _, s in ipairs(info.strobes) do
		local b = ball(model, "Strobe", Color3.new(1, 1, 1), 0.9 * K)
		b.CFrame = CFrame.new(vec3(s) * K)
		table.insert(v.strobes, b)
	end
	-- the afterburner: a long glowing drop behind every nozzle (outer orange, inner white)
	for _, n in ipairs(info.nozzles) do
		local outer, core = Instance.new("Part"), Instance.new("Part")
		for i, p in { outer, core } do
			p.Name = i == 1 and "Flame" or "FlameCore"
			p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Massless, p.CastShadow = true, false, false, false, true, false
			p.Material = Enum.Material.Neon
			p.Color = i == 1 and Color3.fromRGB(255, 138, 60) or Color3.fromRGB(255, 240, 200)
			p.Transparency = 1
			p.Size = Vector3.new(0.5, 0.5, 0.5)
			local m = Instance.new("SpecialMesh")
			m.MeshType = Enum.MeshType.Sphere
			m.Parent = p
			p.Parent = self.folder
		end
		table.insert(v.flames, { outer = outer, core = core, at = vec3(n) })
	end
	self.visuals[ac] = v
	return v
end

local function setShown(self, v, on)
	if v.shown == on then return end
	v.shown = on
	v.model.Parent = on and self.folder or nil
	if not on then for _, f in ipairs(v.flames) do f.outer.Transparency, f.core.Transparency = 1, 1 end end
end

function View:handleEvent(kind, d)
	local fx, rnd = self.fx, self.world.rnd
	local function rand3(s) return V(rnd.uniform(-s, s), rnd.uniform(-s, s), rnd.uniform(-s, s)) end
	if kind == "explosion" then self:explosion(d.pos, d.size or 1, d.ground)
	elseif kind == "hit" then
		for _ = 1, 3 do fx:fireAt(d.pos, rand3(20), 0.18, { 1.5, 3.5 }, { { 1, 0.85, 0.5, 1 }, { 1, 0.4, 0.1, 0 } }) end
		fx:smokeAt(d.pos, nil, 1.2, { 2, 6 }, { { 0.3, 0.3, 0.3, 0.6 }, { 0.4, 0.4, 0.4, 0 } })
	elseif kind == "impact" then fx:smokeAt(d.pos, V(0, 0, 6), 1.5, { 3, 9 }, { { 0.55, 0.48, 0.38, 0.7 }, { 0.6, 0.55, 0.45, 0 } })
	elseif kind == "chaff" then
		for _ = 1, 3 do fx:smokeAt(d.chaff.pos, add(mul(d.chaff.vel, 0.2), rand3(4)), d.chaff.life, { 2, 12 }, { { 0.75, 0.78, 0.82, 0.35 }, { 0.8, 0.82, 0.85, 0 } }, 1.5) end
	elseif kind == "launch" then
		for _ = 1, 4 do fx:smokeAt(d.missile.pos, add(mul(d.missile.vel, 0.9), rand3(6)), 1.6, { 2, 8 }, { { 0.85, 0.85, 0.85, 0.6 }, { 0.9, 0.9, 0.9, 0 } }, 2) end
	end
end

function View:explosion(pos, size, ground)
	local fx, r = self.fx, self.world.rnd
	local function rand3(s) return V(r.uniform(-s, s), r.uniform(-s, s), r.uniform(-s, s)) end
	fx:fireAt(pos, nil, 0.2, { 60 * size, 150 * size }, { { 1, 0.93, 0.78, 0.95 }, { 1, 0.55, 0.2, 0 } })           -- the flash
	for _ = 1, math.floor(8 * size + 4) do
		fx:fireAt(add(pos, rand3(3 * size)), rand3(25 * size), 0.5 + 0.5 * r(), { 4 * size, 22 * size }, { { 1, 0.75, 0.35, 1 }, { 0.9, 0.25, 0.05, 0 } }, 2.5)
	end
	local sc = ground and { 0.35, 0.3, 0.25, 0.85 } or { 0.25, 0.23, 0.21, 0.75 }
	for _ = 1, math.floor(10 * size + 4) do
		fx:smokeAt(add(pos, rand3(4 * size)), rand3(12 * size), 4 + 3 * r(), { 8 * size, 40 * size }, { sc, { 0.45, 0.43, 0.42, 0 } }, 0.8, ground and 2 or 0.5)
	end
end

-- the burning / smoking wreck, contrails, the vapour cone at Mach 1, vapour from the wings, the muzzle flash
function View:aircraftEffects(ac, v, dt)
	if ac.crashed then return end
	local fx, q = self.fx, ac.quat
	local info = v.info
	if ac.burning or ac.damaged then
		v.trail -= dt
		if v.trail <= 0 then
			v.trail = 0.04
			local tail = add(ac.pos, xform(q, V(info.tail[1], info.tail[2], info.tail[3])))
			if ac.burning then
				fx:fireAt(tail, mul(ac.vel, 0.7), 0.35, { 4, 8 }, { { 1, 0.6, 0.2, 0.9 }, { 0.8, 0.2, 0.05, 0 } }, 3)
				fx:smokeAt(tail, mul(ac.vel, 0.5), 7, { 4, 22 }, { { 0.12, 0.11, 0.1, 0.8 }, { 0.3, 0.3, 0.3, 0 } }, 2)
			else
				fx:smokeAt(tail, mul(ac.vel, 0.5), 3.5, { 2, 10 }, { { 0.45, 0.45, 0.45, 0.5 }, { 0.6, 0.6, 0.6, 0 } }, 2)
			end
		end
	end
	if not ac.alive then return end
	-- contrails high up, from every engine
	if self.quality ~= "low" and ac.pos.z > 7200 and ac.speed > 140 then
		v.contrail = (v.contrail or 0) - dt
		if v.contrail <= 0 then
			v.contrail = 0.07
			local k = math.min(1, (ac.pos.z - 7200) / 1500) * 0.5
			for _, n in ipairs(info.nozzles) do
				fx:smokeAt(add(ac.pos, xform(q, V(n[1], n[2] - 5, n[3]))), mul(ac.vel, 0.05), 7, { 1.4, 8 }, { { 1, 1, 1, k }, { 1, 1, 1, 0 } })
			end
		end
	end
	-- vapour cone right at the speed of sound in denser air
	local mach = ac.fm.mach
	if mach > 0.965 and mach < 1.035 and ac.pos.z < 9000 then
		local a = 0.4 * (1 - math.abs(mach - 1) / 0.035)
		local mid = add(ac.pos, mul(ac.forward, -1.5))
		for _ = 1, 4 do
			local ang = self.world.rnd() * math.pi * 2
			local pp = add(mid, add(mul(ac.fm.right, math.cos(ang) * 3.4), mul(ac.fm.up, math.sin(ang) * 2.6)))
			fx:smokeAt(pp, mul(ac.vel, 0.97), 0.16, { 2.4, 4.2 }, { { 1, 1, 1, a }, { 1, 1, 1, 0 } })
		end
	end
	local alpha = ac.fm.alpha / DEG
	if alpha > 13 and ac.speed > 70 then
		local a = 0.38 * math.min(1, (alpha - 13) / 9)
		for _, s in ipairs(info.vapor) do
			fx:smokeAt(add(ac.pos, xform(q, V(s[1], s[2], s[3]))), mul(ac.vel, 0.9), 0.45, { 0.7, 2.8 }, { { 1, 1, 1, a }, { 1, 1, 1, 0 } }, 1.5)
		end
	end
	if ac.fm.gLoad > 5.5 and ac.speed > 120 then
		local a = math.min(0.45, (ac.fm.gLoad - 5.5) * 0.12)
		for _, t in ipairs(info.wingtips) do
			fx:smokeAt(add(ac.pos, xform(q, V(t[1], t[2], t[3]))), mul(ac.vel, 0.85), 0.7, { 0.5, 1.4 }, { { 1, 1, 1, a }, { 1, 1, 1, 0 } }, 2)
		end
	end
	if ac.gun.firing then
		fx:fireAt(add(ac.pos, xform(q, V(info.gun[1], info.gun[2] + 0.6, info.gun[3]))), ac.vel, 0.04, { 1.2, 2.2 }, { { 1, 0.85, 0.5, 1 }, { 1, 0.5, 0.1, 0 } })
	end
end

-- player: the Aircraft the camera follows; cockpit: the view is from inside (its own jet is not drawn)
function View:update(dt, player, cockpit)
	self.time += dt
	local w = self.world
	local fx = self.fx
	fx:frame(70)
	local camPos = self.camPos
	local present = {}
	for _, ac in ipairs(w.aircraft) do
		present[ac] = true
		local v = self:visualFor(ac)
		local show = not ac.crashed
		if show and ac ~= player and camPos then
			local d = math.sqrt((ac.pos.x - camPos.x) ^ 2 + (ac.pos.y - camPos.y) ^ 2 + (ac.pos.z - camPos.z) ^ 2)
			if d > FAR then show = false end
		end
		if show and ac == player and cockpit and ac.alive then show = false end
		setShown(self, v, show)
		if show then
			local cf = Coords.cframe(ac.pos, ac.quat)
			v.model:PivotTo(cf)
			for n, s in pairs(v.stores) do
				local st
				for _, x in ipairs(ac.stations) do if x.number == n then st = x end end
				local loaded = st and st.loaded
				if s.loaded ~= loaded then
					s.loaded = loaded
					for _, d in s.model:GetDescendants() do if d:IsA("BasePart") then d.Transparency = loaded and 0 or 1 end end
				end
			end
			local e = ac.engineSetting
			for k, f in ipairs(v.flames) do
				if ac.alive and e > 1 and not ac.spec.noAB then
					local ab = (e - 1) / 0.1
					local fl = 1 + 0.08 * math.sin(self.time * 61 + k * 2.1) + 0.05 * math.sin(self.time * 23 + k)
					local r = (0.78 + 0.14 * ab) * v.info.flameScale
					local length = (2 + 3.2 * ab) * fl * v.info.flameScale
					local d = 0.92 * r
					f.outer.Size = Vector3.new(d * K, d * K, length * K)
					f.outer.CFrame = cf * CFrame.new(f.at * K + Vector3.new(0, 0, length * K / 2))
					f.core.Size = Vector3.new(d * 0.6 * K, d * 0.6 * K, length * 0.55 * K)
					f.core.CFrame = cf * CFrame.new(f.at * K + Vector3.new(0, 0, length * 0.55 * K / 2))
					f.outer.Transparency, f.core.Transparency = 0.45, 0.15
				else
					f.outer.Transparency, f.core.Transparency = 1, 1
				end
			end
			if ac.alive then
				local ph = (self.time + v.phase) % 1.2
				local on = ph < 0.06 or (ph > 0.18 and ph < 0.24)
				for _, s in ipairs(v.strobes) do s.Transparency = on and 0 or 1 end
			else
				for _, s in ipairs(v.strobes) do s.Transparency = 1 end
			end
			self:aircraftEffects(ac, v, dt)
		end
	end
	for ac, v in pairs(self.visuals) do
		if not present[ac] then
			v.model:Destroy()
			for _, f in ipairs(v.flames) do f.outer:Destroy(); f.core:Destroy() end
			self.visuals[ac] = nil
		end
	end

	local mp = {}
	for _, m in ipairs(w.missiles) do
		mp[m] = true
		local mv = self.missileVis[m]
		if not mv then
			mv = { model = missileModel(m.spec), last = SimMath.copy(m.pos) }
			mv.model.Parent = self.folder
			self.missileVis[m] = mv
		end
		local p = Coords.pos(m.pos)
		mv.model:PivotTo(CFrame.lookAt(p, p + Coords.dir(m.dir)))
		if m.burning then
			local tail = add(m.pos, mul(m.dir, -m.spec.length / 2))
			fx:fireAt(tail, m.vel, 0.05, { 1.6, 1 }, { { 1, 0.8, 0.5, 1 }, { 1, 0.5, 0.2, 0 } })
			local step = SimMath.len(SimMath.sub(m.pos, mv.last))
			if step > 7 then
				local n = math.min(math.floor(step / 7), 12)
				for k = 1, n do
					local t = k / n
					local pp = V(mv.last.x + (tail.x - mv.last.x) * t, mv.last.y + (tail.y - mv.last.y) * t, mv.last.z + (tail.z - mv.last.z) * t)
					fx:smokeAt(pp, V(w.rnd.uniform(-1.5, 1.5), w.rnd.uniform(-1.5, 1.5), w.rnd.uniform(-1.5, 1.5)), 5, { 1.5, 7 },
						{ { 0.92, 0.92, 0.92, 0.75 * m.spec.smoke }, { 0.95, 0.95, 0.95, 0 } })
				end
				mv.last = SimMath.copy(tail)
			end
		end
	end
	for m, mv in pairs(self.missileVis) do
		if not mp[m] then
			mv.model:Destroy()
			self.missileVis[m] = nil
		end
	end

	for _, f in ipairs(w.flares) do
		local k = f.intensity / f.peak
		fx:fireAt(f.pos, nil, 0.06, { 5 * k + 1, 4 * k + 1 }, { { 1, 0.95, 0.8, 1 }, { 1, 0.7, 0.4, 0.6 } })
		if w.rnd() < 0.5 then fx:smokeAt(f.pos, nil, 2, { 1, 4 }, { { 0.95, 0.95, 0.95, 0.35 }, { 1, 1, 1, 0 } }) end
	end
	fx:setTracers(w.bullets)
end

-- the camera: cam is the flight camera of shared/game/Camera.luau; anchor: the point (sim frame) it is placed round (the player's jet, or
-- what the missile / kill camera follows).  The jets are drawn Config.ModelScale times bigger than the island's scale, so the camera's
-- distance from the anchor (the chase distance, the eye in the cockpit) is scaled the same way - or it would sit inside the jet.
function View:setCamera(cam, anchor)
	self.camPos = cam.position
	local c = self.camera
	c.CameraType = Enum.CameraType.Scriptable
	anchor = anchor or cam.position
	local p = Coords.pos(anchor) + Coords.vec(SimMath.sub(cam.position, anchor)) * Config.ModelScale
	c.CFrame = Coords.cframe(SimMath.V(0, 0, 0), cam.orientation).Rotation + p
	c.FieldOfView = cam.fov
end

function View:destroy()
	for _, v in pairs(self.visuals) do
		v.model:Destroy()
		for _, f in ipairs(v.flames) do f.outer:Destroy(); f.core:Destroy() end
	end
	for _, mv in pairs(self.missileVis) do mv.model:Destroy() end
	self.visuals, self.missileVis = {}, {}
	self.fx:destroy()
	self.folder:Destroy()
end

return View
