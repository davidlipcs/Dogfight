--!nonstrict
-- Builds a fighter out of plain parts (no meshes, so nothing to upload): the same model flies in the game,
-- sits in the hangar preview and carries the bought paint scheme and the pilot's outfit.
-- The nose points to -Z (LookVector), like every Roblox model.
local Catalog = require(script.Parent.Catalog)

local JetBuilder = {}

local function color(n: number): Color3
	return Color3.fromRGB(bit32.band(bit32.rshift(n, 16), 255), bit32.band(bit32.rshift(n, 8), 255), bit32.band(n, 255))
end
JetBuilder.color = color

local DEFAULT = { color = 0x8d949c, emissive = 0x000000, pcolor = 0x4b5258 }
local ENEMY = { color = 0x4a3a3a, emissive = 0x000000, pattern = "splinter", pcolor = 0x2a1f1f, rough = 0.8 }
JetBuilder.EnemySkin = ENEMY

-- a small seeded generator: a scheme always gets the same pattern
local function seeded(id: string)
	local h = 2166136261
	for i = 1, #id do
		h = bit32.bxor(h, string.byte(id, i))
		h = (h * 16777619) % 4294967296
	end
	local a = h
	return function()
		a = (a * 1664525 + 1013904223) % 4294967296
		return a / 4294967296
	end
end

local function newPart(parent: Instance, name: string, size: Vector3, cf: CFrame, col: Color3, material: Enum.Material?, shape: Enum.PartType?): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.Color = col
	p.Material = material or Enum.Material.SmoothPlastic
	if shape then p.Shape = shape end
	p.Anchored = false
	p.CanCollide = false
	p.CanTouch = false
	p.Massless = true
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.CFrame = cf
	p.Parent = parent
	return p
end

local function weld(body: BasePart, p: BasePart)
	local w = Instance.new("WeldConstraint")
	w.Part0 = body
	w.Part1 = p
	w.Parent = p
end

-- the pattern of a paint scheme: thin coloured parts laid over the wings and the fuselage
local function decorate(model: Model, body: Part, skin, mat: Enum.Material)
	local kind = skin.pattern
	if not kind then return end
	local r = seeded(skin.id or "x")
	local col = color(skin.pcolor or 0xffffff)
	local rainbow = { 0xff3b3b, 0xff9a2a, 0xffe83a, 0x3bd86a, 0x3ba8ff, 0x8a4aff }
	local count = 0
	local function add(name: string, size: Vector3, cf: CFrame, c: Color3?, shape: Enum.PartType?)
		if count >= 36 then return end
		count += 1
		local p = newPart(model, name, size, cf, c or col, mat, shape)
		weld(body, p)
	end
	-- a spot on the top of a wing: u along the span (-3.5..3.5), v along the chord (-1.7..1.7); the part follows the sweep
	local function wingTop(side: number, u: number, v: number): CFrame
		local sx = 0.906 * u - 0.423 * v
		local sz = 0.423 * u + 0.906 * v
		return CFrame.new(side * (5.2 + sx), 0.27, 2 + sz) * CFrame.Angles(0, side * math.rad(-25), 0)
	end
	local function onTube(z: number): CFrame
		return CFrame.new(0, 1.3, z)
	end
	if kind == "camo" or kind == "splinter" or kind == "digital" then
		for i = 1, 24 do
			local side = (i % 2 == 0) and 1 or -1
			local u, v = (r() * 2 - 1) * 3.2, (r() * 2 - 1) * 1.4
			if i % 4 == 0 then
				add("Camo", Vector3.new(0.5 + r() * 0.9, 0.1, 0.8 + r() * 1.6), onTube(-6 + r() * 11) * CFrame.Angles(0, (r() - 0.5) * 0.8, 0))
			elseif kind == "camo" then
				add("Camo", Vector3.new(1.0 + r() * 1.6, 0.1, 0.8 + r() * 1.0), wingTop(side, u, v) * CFrame.Angles(0, (r() - 0.5) * 1.2, 0))
			elseif kind == "splinter" then
				add("Camo", Vector3.new(0.5 + r() * 0.8, 0.1, 1.2 + r() * 1.8), wingTop(side, u, v) * CFrame.Angles(0, (r() - 0.5) * 2.4, 0))
			else
				add("Camo", Vector3.new(0.7, 0.1, 0.7), wingTop(side, math.floor(u / 0.7) * 0.7, math.floor(v / 0.7) * 0.7))
			end
		end
	elseif kind == "dots" or kind == "hex" then
		for i = 0, 4 do
			for j = 0, 1 do
				local u, v = -3 + i * 1.5, -0.9 + j * 1.8
				add("Dot", Vector3.new(0.8, 0.1, 0.8), wingTop(1, u, v), nil, nil)
				add("Dot", Vector3.new(0.8, 0.1, 0.8), wingTop(-1, u, v), nil, nil)
			end
		end
		for k = 0, 3 do add("Dot", Vector3.new(0.8, 0.1, 0.8), onTube(-5 + k * 3)) end
	elseif kind == "checker" then
		for i = 0, 3 do
			for j = 0, 2 do
				if (i + j) % 2 == 0 then
					add("Check", Vector3.new(1.3, 0.1, 1.3), wingTop(1, -2.4 + i * 1.6, -1.3 + j * 1.3))
					add("Check", Vector3.new(1.3, 0.1, 1.3), wingTop(-1, -2.4 + i * 1.6, -1.3 + j * 1.3))
				end
			end
		end
		for k = 0, 4 do if k % 2 == 0 then add("Check", Vector3.new(1.1, 0.1, 1.1), onTube(-6 + k * 2.6)) end end
	elseif kind == "flame" then
		for i = 1, 8 do
			add("Flame", Vector3.new(0.6 + r() * 0.5, 0.1, 2.4 + r() * 3.2), onTube(2 + i * 0.7 + r()) * CFrame.new(((i % 2 == 0) and 1 or -1) * (0.2 + r() * 0.6), 0, 0) * CFrame.Angles(0, (r() - 0.5) * 0.3, 0))
		end
		for i = 1, 6 do add("Flame", Vector3.new(0.9, 0.1, 1.2 + r() * 1.4), wingTop((i % 2 == 0) and 1 or -1, -3 + i * 1.0, 0.5 + r() * 0.6)) end
	else -- stripes, tiger, wave, rainbow: bands across the wings and rings round the fuselage
		for k = 0, 3 do
			local c = (kind == "rainbow") and color(rainbow[(k % #rainbow) + 1]) or col
			local u = -2.6 + k * 1.75
			add("Band", Vector3.new(0.8, 0.1, 3.7), wingTop(1, u, 0), c)
			add("Band", Vector3.new(0.8, 0.1, 3.7), wingTop(-1, u, 0), c)
		end
		for k = 0, 4 do
			local c = (kind == "rainbow") and color(rainbow[((k + 2) % #rainbow) + 1]) or col
			add("Ring", Vector3.new(0.7, 2.68, 2.68), CFrame.new(0, 0, -5 + k * 2.6) * CFrame.Angles(0, math.rad(90), 0), c, Enum.PartType.Cylinder)
		end
	end
end

-- a Model with PrimaryPart "Body".  air: a Catalog.Air id (nil = the factory grey), pilot: a Catalog.Pilot id (nil = plain),
-- enemy: true builds the dark hostile scheme (smaller part count)
function JetBuilder.build(airId: string?, pilotId: string?, enemy: boolean?): Model
	local skin = enemy and ENEMY or (airId and Catalog.AirById[airId]) or DEFAULT
	local model = Instance.new("Model")
	model.Name = enemy and "Enemy" or "Jet"

	local paint = color(skin.color)
	local accent = color(skin.pcolor or 0x4b5258)
	local dark = Color3.fromRGB(34, 38, 44)
	local metal = skin.metal or 0
	local material = metal >= 0.6 and Enum.Material.Metal or Enum.Material.SmoothPlastic
	local reflect = skin.metal and math.clamp(skin.metal * 0.35, 0, 0.4) or 0
	local glow = skin.emissive and skin.emissive > 0x222222

	local body = newPart(model, "Body", Vector3.new(2.6, 2.6, 15), CFrame.new(0, 0, 0), paint, material, Enum.PartType.Block)
	body.Transparency = 1                                         -- the root of the model; the round Tube is what you see
	body.Reflectance = reflect
	model.PrimaryPart = body

	local function piece(name, size, cf, col, mat, shape)
		local p = newPart(model, name, size, cf, col, mat or material, shape)
		p.Reflectance = reflect
		weld(body, p)
		return p
	end
	-- fuselage: a round tube along Z, a nose cone, the engine
	piece("Tube", Vector3.new(15, 2.6, 2.6), CFrame.Angles(0, math.rad(90), 0), paint, material, Enum.PartType.Cylinder)
	piece("Nose1", Vector3.new(4, 2.0, 2.0), CFrame.new(0, 0, -9.2) * CFrame.Angles(0, math.rad(90), 0), paint, material, Enum.PartType.Cylinder)
	piece("Nose2", Vector3.new(3, 1.2, 1.2), CFrame.new(0, 0, -11.6) * CFrame.Angles(0, math.rad(90), 0), dark, Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	-- wings, tailplanes, fins
	piece("WingL", Vector3.new(8, 0.35, 4.2), CFrame.new(-5.2, -0.1, 2) * CFrame.Angles(0, math.rad(25), 0), paint)
	piece("WingR", Vector3.new(8, 0.35, 4.2), CFrame.new(5.2, -0.1, 2) * CFrame.Angles(0, math.rad(-25), 0), paint)
	piece("TailL", Vector3.new(3.4, 0.3, 2), CFrame.new(-2.7, 0, 7.4) * CFrame.Angles(0, math.rad(20), 0), paint)
	piece("TailR", Vector3.new(3.4, 0.3, 2), CFrame.new(2.7, 0, 7.4) * CFrame.Angles(0, math.rad(-20), 0), paint)
	piece("FinL", Vector3.new(0.3, 3.4, 3), CFrame.new(-1.0, 2.5, 6.6) * CFrame.Angles(0, 0, math.rad(10)), paint)
	piece("FinR", Vector3.new(0.3, 3.4, 3), CFrame.new(1.0, 2.5, 6.6) * CFrame.Angles(0, 0, math.rad(-10)), paint)
	piece("Intake", Vector3.new(1.8, 1.3, 4), CFrame.new(0, -1.6, -2.5), dark, Enum.Material.SmoothPlastic)
	-- the glass
	local canopy = piece("Canopy", Vector3.new(4.2, 1.9, 1.9), CFrame.new(0, 1.4, -3.0) * CFrame.Angles(0, math.rad(90), 0), Color3.fromRGB(110, 170, 220), Enum.Material.Glass, Enum.PartType.Ball)
	canopy.Transparency = 0.45
	canopy.Reflectance = 0.15
	-- the engine: a dark nozzle and the afterburner flame (the client turns it up with the throttle)
	piece("Nozzle", Vector3.new(1.6, 2.2, 2.2), CFrame.new(0, 0, 8.4) * CFrame.Angles(0, math.rad(90), 0), dark, Enum.Material.Metal, Enum.PartType.Cylinder)
	local flame = piece("Flame", Vector3.new(5, 1.5, 1.5), CFrame.new(0, 0, 11.4) * CFrame.Angles(0, math.rad(90), 0), Color3.fromRGB(255, 150, 40), Enum.Material.Neon, Enum.PartType.Cylinder)
	flame.Transparency = 0.6
	-- a glow trim (a neon paint scheme): thin strips along the wing edges
	if glow and not enemy then
		local g = color(skin.color)
		for _, s in { -1, 1 } do
			local p = piece("Glow", Vector3.new(0.3, 0.45, 7), CFrame.new(s * 5.2, -0.05, 4) * CFrame.Angles(0, s * math.rad(-25), 0), g, Enum.Material.Neon)
			p.Reflectance = 0
		end
	end
	-- missiles under the wings
	if not enemy then
		for _, s in { -1, 1 } do
			piece("Missile", Vector3.new(2.6, 0.5, 0.5), CFrame.new(s * 3.6, -0.7, 1.4) * CFrame.Angles(0, math.rad(90), 0), Color3.fromRGB(220, 222, 226), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
		end
		-- the pilot in the cockpit: helmet with visor, oxygen mask and hose, shoulders, harness, arms on the stick
		-- (the bought outfit gives the colours)
		local outfit = pilotId and Catalog.PilotById[pilotId]
		local helmet = outfit and color(outfit.helmet) or Color3.fromRGB(205, 205, 200)
		local visor = outfit and color(outfit.visor) or Color3.fromRGB(34, 36, 42)
		local suit = outfit and color(outfit.suit) or Color3.fromRGB(86, 96, 70)
		local acc = outfit and color(outfit.accent) or Color3.fromRGB(220, 200, 60)
		local skinTone = Color3.fromRGB(199, 154, 118)
		local webbing = Color3.fromRGB(38, 41, 45)
		local rubber = Color3.fromRGB(40, 46, 42)
		local sunVisor = (visor.R * 0.299 + visor.G * 0.587 + visor.B * 0.114) < 0.27
		local px, pz = 0, -2.75                                 -- the pilot's place in the cockpit (the seat)
		piece("Seat", Vector3.new(1.7, 0.3, 1.5), CFrame.new(px, 0.45, pz + 0.15), Color3.fromRGB(52, 56, 60), Enum.Material.SmoothPlastic)
		piece("SeatBack", Vector3.new(1.5, 1.9, 0.3), CFrame.new(px, 1.35, pz + 0.85), Color3.fromRGB(48, 52, 56), Enum.Material.SmoothPlastic)
		piece("PilotTorso", Vector3.new(1.0, 1.15, 0.78), CFrame.new(px, 0.95, pz) * CFrame.Angles(0, 0, math.rad(90)), suit, Enum.Material.Fabric, Enum.PartType.Cylinder)
		piece("PilotShoulders", Vector3.new(1.55, 0.62, 0.72), CFrame.new(px, 1.36, pz), suit, Enum.Material.Fabric, Enum.PartType.Ball)
		piece("PilotNeck", Vector3.new(0.4, 0.36, 0.36), CFrame.new(px, 1.62, pz - 0.05) * CFrame.Angles(0, 0, math.rad(90)), skinTone, Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
		piece("PilotHelmet", Vector3.new(0.86, 0.94, 0.98), CFrame.new(px, 1.95, pz - 0.08), helmet, Enum.Material.SmoothPlastic, Enum.PartType.Ball).Reflectance = 0.12
		if not sunVisor then
			piece("PilotFace", Vector3.new(0.58, 0.42, 0.4), CFrame.new(px, 1.9, pz - 0.5), skinTone, Enum.Material.SmoothPlastic, Enum.PartType.Ball)
		end
		local lens = piece("PilotVisor", Vector3.new(0.78, 0.5, 0.52), CFrame.new(px, 1.95, pz - 0.42), visor, sunVisor and Enum.Material.Glass or Enum.Material.SmoothPlastic, Enum.PartType.Ball)
		lens.Transparency = sunVisor and 0 or 0.45
		lens.Reflectance = 0.25
		piece("PilotMask", Vector3.new(0.46, 0.34, 0.34), CFrame.new(px, 1.76, pz - 0.58), rubber, Enum.Material.SmoothPlastic, Enum.PartType.Ball)
		piece("PilotHose", Vector3.new(0.1, 0.1, 1.0), CFrame.new(px - 0.28, 1.4, pz - 0.5) * CFrame.Angles(math.rad(-48), math.rad(14), 0), rubber, Enum.Material.SmoothPlastic)
		for _, s in { -1, 1 } do
			piece("PilotEar", Vector3.new(0.14, 0.4, 0.4), CFrame.new(px + s * 0.43, 1.92, pz - 0.05), Color3.fromRGB(44, 48, 54), Enum.Material.Metal, Enum.PartType.Cylinder)
			piece("PilotStrap", Vector3.new(0.22, 1.0, 0.05), CFrame.new(px + s * 0.34, 1.05, pz - 0.38) * CFrame.Angles(0, 0, s * math.rad(-10)), webbing, Enum.Material.Fabric)
			piece("PilotArm", Vector3.new(0.3, 0.3, 1.05), CFrame.new(px + s * 0.72, 0.95, pz - 0.5) * CFrame.Angles(math.rad(-25), s * math.rad(-8), 0), suit, Enum.Material.Fabric)
			piece("PilotGlove", Vector3.new(0.34, 0.34, 0.34), CFrame.new(px + s * 0.66, 0.78, pz - 1.0), Color3.fromRGB(30, 31, 34), Enum.Material.SmoothPlastic, Enum.PartType.Ball)
		end
		piece("PilotBuckle", Vector3.new(0.26, 0.2, 0.06), CFrame.new(px, 1.0, pz - 0.4), Color3.fromRGB(176, 182, 190), Enum.Material.Metal)
		piece("PilotChestStrap", Vector3.new(0.9, 0.1, 0.05), CFrame.new(px, 1.0, pz - 0.39), webbing, Enum.Material.Fabric)
		piece("PilotPatch", Vector3.new(0.3, 0.14, 0.05), CFrame.new(px - 0.42, 1.18, pz - 0.38), acc, Enum.Material.SmoothPlastic)
		piece("PilotStripe", Vector3.new(0.12, 0.05, 0.85), CFrame.new(px, 2.42, pz - 0.08), acc, Enum.Material.SmoothPlastic)
	end
	-- the pattern of the paint scheme
	if not enemy then
		decorate(model, body, skin, material)
	end
	-- a generous invisible hit box (the guns and missiles test against it)
	local hit = newPart(model, "Hitbox", Vector3.new(9, 3.5, 18), CFrame.new(0, 0, 0), Color3.new(1, 1, 1), Enum.Material.SmoothPlastic)
	hit.Transparency = 1
	hit.CanQuery = true
	weld(body, hit)
	return model
end

-- turns the afterburner flame up or down (0..1)
function JetBuilder.setFlame(model: Model, level: number)
	local f = model:FindFirstChild("Flame")
	if f then
		f.Transparency = 1 - math.clamp(level, 0, 1) * 0.85
	end
end

return JetBuilder
