--!nonstrict
-- Builds a fighter out of plain parts (no meshes, so nothing to upload): the same model flies in the game,
-- sits in the hangar preview and carries the bought paint scheme and the pilot's outfit.
-- The nose points to -Z (LookVector), like every Roblox model.
local JetInfo = require(script.Parent.JetInfo)
local Catalog = require(script.Parent.Catalog)
local Config = require(script.Parent.Config)
local ReplicatedStorage = game:GetService("ReplicatedStorage")

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
	elseif kind == "tricolor" then
		-- the livery bands of the display-team jets: two colours (and a white line) across the wings and round the fuselage
		local col2 = color(skin.pcolor2 or 0xffffff)
		for k = 0, 3 do
			local c = (k % 2 == 0) and col or col2
			local u = -2.6 + k * 1.75
			add("Band", Vector3.new(0.9, 0.1, 3.7), wingTop(1, u, 0), c)
			add("Band", Vector3.new(0.9, 0.1, 3.7), wingTop(-1, u, 0), c)
		end
		for k = 0, 4 do
			local c = (k % 2 == 0) and col or col2
			add("Ring", Vector3.new(0.7, 2.68, 2.68), CFrame.new(0, 0, -5 + k * 2.6) * CFrame.Angles(0, math.rad(90), 0), c, Enum.PartType.Cylinder)
		end
		for _, side in { -1, 1 } do add("Fin", Vector3.new(0.34, 2.6, 0.7), CFrame.new(side * 1.0, 2.5, 6.6) * CFrame.Angles(0, 0, side * math.rad(-10)), col) end
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

-- a pilot in a seat (1 = front, 2 = rear of a two-seat jet): helmet with visor, oxygen mask and hose, shoulders,
-- harness, arms on the stick.  Everything sits inside the canopy and the fuselage tube: nobody sticks out of the jet.
-- The parts live in a Folder "Seat<n>" (removeSeat deletes it).
function JetBuilder.addPilot(model: Model, outfitId: string?, seat: number, twoSeat: boolean?)
	local body = model.PrimaryPart
	local old = model:FindFirstChild("Seat" .. seat)
	if old then old:Destroy() end
	local folder = Instance.new("Folder")
	folder.Name = "Seat" .. seat
	folder.Parent = model
	local outfit = outfitId and Catalog.PilotById[outfitId]
	local helmet = outfit and color(outfit.helmet) or Color3.fromRGB(205, 205, 200)
	local visor = outfit and color(outfit.visor) or Color3.fromRGB(34, 36, 42)
	local suit = outfit and color(outfit.suit) or Color3.fromRGB(86, 96, 70)
	local acc = outfit and color(outfit.accent) or Color3.fromRGB(220, 200, 60)
	local skinTone = Color3.fromRGB(199, 154, 118)
	local webbing = Color3.fromRGB(38, 41, 45)
	local rubber = Color3.fromRGB(40, 46, 42)
	-- the visor is real glass: how much light it lets through (visorT) decides how opaque it looks and, from the
	-- cockpit view, how dark the world is (Visor.luau); mirror = a reflective coating
	local T = outfit and outfit.visorT or 0.97
	local sunVisor = T <= 0.5
	local mirror = outfit and outfit.mirror == true
	local pressure = outfit and outfit.pressure == true
	local helmet2 = outfit and color(outfit.helmet2) or helmet
	local suit2 = outfit and color(outfit.suit2) or suit
	local glove = outfit and color(outfit.glove) or Color3.fromRGB(30, 31, 34)
	local px = 0
	local pz = not twoSeat and -2.75 or (seat == 1 and -3.85 or -0.95)       -- the seat
	local function piece(name: string, size: Vector3, cf: CFrame, col: Color3, mat: Enum.Material, shape: Enum.PartType?)
		local p = newPart(folder, name, size, body.CFrame * cf, col, mat, shape)      -- (the jet may already be flying somewhere)
		weld(body, p)
		return p
	end
	piece("Seat", Vector3.new(1.7, 0.3, 1.5), CFrame.new(px, 0.45, pz + 0.15), Color3.fromRGB(52, 56, 60), Enum.Material.SmoothPlastic)
	piece("SeatBack", Vector3.new(1.5, 1.9, 0.3), CFrame.new(px, 1.35, pz + 0.85), Color3.fromRGB(48, 52, 56), Enum.Material.SmoothPlastic)
	piece("PilotTorso", Vector3.new(1.0, 1.15, 0.78), CFrame.new(px, 0.95, pz) * CFrame.Angles(0, 0, math.rad(90)), suit, Enum.Material.Fabric, Enum.PartType.Cylinder)
	piece("PilotShoulders", Vector3.new(1.45, 0.62, 0.7), CFrame.new(px, 1.34, pz), suit, Enum.Material.Fabric, Enum.PartType.Ball)
	piece("PilotNeck", Vector3.new(0.4, 0.36, 0.36), CFrame.new(px, 1.6, pz - 0.05) * CFrame.Angles(0, 0, math.rad(90)), skinTone, Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	local hs = pressure and 1.18 or 1
	piece("PilotHelmet", Vector3.new(0.86 * hs, 0.94 * hs, 0.98 * hs), CFrame.new(px, 1.93, pz - 0.08), helmet, Enum.Material.SmoothPlastic, Enum.PartType.Ball).Reflectance = 0.12
	if pressure then
		local ring = piece("PilotNeckRing", Vector3.new(0.14, 0.78, 0.78), CFrame.new(px, 1.6, pz - 0.05) * CFrame.Angles(0, 0, math.rad(90)), Color3.fromRGB(170, 178, 186), Enum.Material.Metal, Enum.PartType.Cylinder)
		ring.Reflectance = 0.3
	end
	-- the helmet's livery: thin parts over the shell in the second colour
	local pat = outfit and outfit.pattern
	local top = 2.42 * (pressure and 1.04 or 1)
	if pat == "stripes" or pat == "tricolor" or pat == "trim" or pat == "wolf" then
		piece("LiveryStripe", Vector3.new(0.14, 0.05, 0.86 * hs), CFrame.new(px, top, pz - 0.08), pat == "tricolor" and Color3.fromRGB(205, 42, 62) or helmet2, Enum.Material.SmoothPlastic)
		if pat == "tricolor" then
			piece("LiveryStripe", Vector3.new(0.14, 0.05, 0.86), CFrame.new(px + 0.14, top - 0.02, pz - 0.08), Color3.fromRGB(46, 138, 74), Enum.Material.SmoothPlastic)
			piece("LiveryStripe", Vector3.new(0.14, 0.05, 0.86), CFrame.new(px - 0.14, top - 0.02, pz - 0.08), Color3.fromRGB(244, 244, 240), Enum.Material.SmoothPlastic)
		elseif pat == "wolf" then
			for _, s in { -1, 1 } do piece("LiveryStripe", Vector3.new(0.1, 0.05, 0.8), CFrame.new(px + s * 0.2, top - 0.05, pz - 0.08) * CFrame.Angles(0, 0, s * math.rad(-14)), helmet2, Enum.Material.SmoothPlastic) end
		end
	elseif pat == "chevron" then
		for k = 0, 2 do
			for _, s in { -1, 1 } do piece("LiveryV", Vector3.new(0.5, 0.05, 0.1), CFrame.new(px + s * 0.22, top - 0.07 - k * 0.0, pz - 0.38 + k * 0.22) * CFrame.Angles(0, s * math.rad(35), 0), helmet2, Enum.Material.SmoothPlastic) end
		end
	elseif pat == "camo" or pat == "circuit" then
		local rnd = Random.new(7)
		for _ = 1, 7 do
			piece("LiveryBlot", Vector3.new(0.18 + rnd:NextNumber() * 0.2, 0.05, 0.18 + rnd:NextNumber() * 0.2), CFrame.new(px + rnd:NextNumber(-0.3, 0.3), top - 0.06, pz - 0.08 + rnd:NextNumber(-0.35, 0.35)) * CFrame.Angles(0, rnd:NextNumber() * 3, 0), helmet2, pat == "circuit" and Enum.Material.Neon or Enum.Material.SmoothPlastic)
		end
	end
	if not sunVisor then
		piece("PilotFace", Vector3.new(0.58, 0.42, 0.4), CFrame.new(px, 1.88, pz - 0.5), skinTone, Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	end
	local lens = piece("PilotVisor", Vector3.new(0.78 * hs, 0.5 * hs, 0.52 * hs), CFrame.new(px, 1.93, pz - 0.42 * hs), visor, Enum.Material.Glass, Enum.PartType.Ball)
	lens.Transparency = math.clamp(T - 0.05, 0, 0.9)               -- clear glass: see-through, dark glass: opaque
	lens.Reflectance = mirror and 0.65 or 0.2
	piece("PilotMask", Vector3.new(0.46, 0.34, 0.34), CFrame.new(px, 1.74, pz - 0.58), rubber, Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	piece("PilotHose", Vector3.new(0.1, 0.1, 1.0), CFrame.new(px - 0.28, 1.38, pz - 0.5) * CFrame.Angles(math.rad(-48), math.rad(14), 0), rubber, Enum.Material.SmoothPlastic)
	for _, s in { -1, 1 } do
		piece("PilotEar", Vector3.new(0.14, 0.4, 0.4), CFrame.new(px + s * 0.43, 1.9, pz - 0.05), Color3.fromRGB(44, 48, 54), Enum.Material.Metal, Enum.PartType.Cylinder)
		piece("PilotYoke", Vector3.new(0.42, 0.1, 0.5), CFrame.new(px + s * 0.4, 1.3, pz) * CFrame.Angles(0, 0, s * math.rad(-25)), suit2, Enum.Material.Fabric)
		piece("PilotStrap", Vector3.new(0.22, 1.0, 0.05), CFrame.new(px + s * 0.34, 1.05, pz - 0.38) * CFrame.Angles(0, 0, s * math.rad(-10)), webbing, Enum.Material.Fabric)
		piece("PilotArm", Vector3.new(0.3, 0.3, 1.05), CFrame.new(px + s * 0.6, 0.85, pz - 0.5) * CFrame.Angles(math.rad(-25), s * math.rad(-6), 0), suit, Enum.Material.Fabric)
		piece("PilotGlove", Vector3.new(0.34, 0.34, 0.34), CFrame.new(px + s * 0.56, 0.7, pz - 1.0), glove, Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	end
	piece("PilotBuckle", Vector3.new(0.26, 0.2, 0.06), CFrame.new(px, 1.0, pz - 0.4), Color3.fromRGB(176, 182, 190), Enum.Material.Metal)
	piece("PilotChestStrap", Vector3.new(0.9, 0.1, 0.05), CFrame.new(px, 1.0, pz - 0.39), webbing, Enum.Material.Fabric)
	piece("PilotPatch", Vector3.new(0.3, 0.14, 0.05), CFrame.new(px - 0.42, 1.18, pz - 0.38), acc, Enum.Material.SmoothPlastic)
	piece("PilotStripe", Vector3.new(0.12, 0.05, 0.85), CFrame.new(px, 2.4, pz - 0.08), acc, Enum.Material.SmoothPlastic)
end

function JetBuilder.removeSeat(model: Model, seat: number)
	local f = model:FindFirstChild("Seat" .. seat)
	if f then f:Destroy() end
end

-- An imported jet (the game's own .glb model, imported into Studio and put in ReplicatedStorage.JetModels): scaled to the
-- real length, turned nose-to--Z, centred, every part welded to the invisible root "Body".  The paint scheme's tint goes
-- on the painted parts; the patterns are only drawn on the jets built from parts.
local function fromImported(src: Instance, key: string, skin, enemy: boolean?): Model?
	local model: Model = src:Clone()
	model.Name = enemy and "Enemy" or "Jet"
	local parts = {}
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then table.insert(parts, d)
		elseif d:IsA("Weld") or d:IsA("WeldConstraint") or d:IsA("Motor6D") or d:IsA("Script") or d:IsA("LocalScript") then d:Destroy() end
	end
	if #parts == 0 then model:Destroy() return nil end
	local length = 15
	for _, j in Config.JetModels do if j.key == key then length = j.length end end

	model:PivotTo(CFrame.new())
	local _, size = model:GetBoundingBox()
	if size.X > size.Z then model:PivotTo(CFrame.Angles(0, math.rad(90), 0) * model:GetPivot()) end   -- the long axis along Z
	local _, size2 = model:GetBoundingBox()
	-- the game's reference points (nozzles, missile stations, lamps, the eye ...) are in the jet frame of JetInfo: the model is put so that its
	-- box fills the same box there (the same length, the same middle), or the flames and the missiles would hang next to it
	local info = JetInfo[key]
	local want = length
	if info and info.bbox then want = info.bbox.max[2] - info.bbox.min[2] end
	model:ScaleTo(want / math.max(size2.X, size2.Z))
	local bb = model:GetBoundingBox()
	model:PivotTo(CFrame.new(-bb.Position) * model:GetPivot())                                        -- centred

	-- the nose points to -Z: the rear of a jet (engines, tail) is heavier than its nose
	local flip = Config.JetModelFlip[key]
	if flip == nil then
		local front, rear = 0, 0
		for _, p in parts do
			local v = p.Size.X * p.Size.Y * p.Size.Z
			if p.Position.Z < -length * 0.3 then front += v elseif p.Position.Z > length * 0.3 then rear += v end
		end
		flip = front > rear
	end
	if flip then model:PivotTo(CFrame.Angles(0, math.rad(180), 0) * model:GetPivot()) end
	if info and info.bbox then
		local b = info.bbox
		-- jet frame (x right, y forward, z up) -> model frame (x right, y up, -z forward)
		local middle = Vector3.new((b.min[1] + b.max[1]) / 2, (b.min[3] + b.max[3]) / 2, -(b.min[2] + b.max[2]) / 2)
		model:PivotTo(CFrame.new(middle) * model:GetPivot())
	end

	local body = Instance.new("Part")
	body.Name = "Body"
	body.Size = Vector3.new(1, 1, 1)
	body.Transparency = 1
	body.CanCollide = false
	body.CanTouch = false
	body.Massless = true
	body.Anchored = false
	body.CFrame = CFrame.new()
	body.Parent = model
	model.PrimaryPart = body

	local tint = enemy and Color3.fromRGB(95, 80, 80) or (skin and skin.color and color(skin.color)) or nil
	for _, p in parts do
		p.Anchored = false
		p.CanCollide = false
		p.CanTouch = false
		p.Massless = true
		weld(body, p)
		local isGlass = p.Transparency > 0.05 or string.find(string.lower(p.Name), "glass") ~= nil
		-- the paint scheme tints the painted parts only (the ones with a colour texture); the dark intakes, nozzles, screens, lamps and the
		-- landing gear keep the colours of the model
		local sa = p:FindFirstChildOfClass("SurfaceAppearance")
		local painted = sa ~= nil and sa.ColorMap ~= ""
		if tint and not isGlass and p:IsA("MeshPart") and painted then
			p.Color = tint
			pcall(function() sa.Color = tint end)
		end
		-- the landing gear and its doors are only shown with the gear down (View.luau)
		local lname = string.lower(p.Name)
		if string.sub(lname, 1, 5) == "gear_" or string.sub(lname, 1, 5) == "door_" then p:SetAttribute("Gear", true) end
	end
	-- the afterburner flame and a generous hit box
	local k = length / 15
	local flame = newPart(model, "Flame", Vector3.new(5 * k, 1.5 * k, 1.5 * k), CFrame.new(0, 0, length / 2 + 2 * k) * CFrame.Angles(0, math.rad(90), 0), Color3.fromRGB(255, 150, 40), Enum.Material.Neon, Enum.PartType.Cylinder)
	flame.Transparency = 0.6
	weld(body, flame)
	local hit = newPart(model, "Hitbox", Vector3.new(9 * k, 3.5 * k, length * 1.2), CFrame.new(), Color3.new(1, 1, 1), Enum.Material.SmoothPlastic)
	hit.Transparency = 1
	hit.CanQuery = true
	weld(body, hit)
	return model
end

-- a real livery is only worn on the jets it exists on
local function applicable(skin, modelKey: string?)
	if skin and skin.jets and modelKey and not table.find(skin.jets, modelKey) then return nil end
	return skin
end

-- a Model with PrimaryPart "Body".  air: a Catalog.Air id (nil = the factory grey), pilot: a Catalog.Pilot id (nil = plain),
-- enemy: true builds the dark hostile scheme (smaller part count); twoSeat: a longer canopy with a rear seat (wsoId: the
-- outfit of whoever sits there; addPilot puts a pilot in a seat later, removeSeat takes him out)
function JetBuilder.build(airId: string?, pilotId: string?, enemy: boolean?, twoSeat: boolean?, wsoId: string?, modelKey: string?): Model
	local skin = enemy and ENEMY or applicable(airId and Catalog.AirById[airId], modelKey) or DEFAULT
	-- the game's own model when it is imported (a two-seater uses the built one: there is no rear seat in the single-seat models)
	if modelKey and not twoSeat then
		local folder = ReplicatedStorage:FindFirstChild("JetModels")
		local src = folder and folder:FindFirstChild(modelKey)
		if src then
			local m = fromImported(src, modelKey, applicable(airId and Catalog.AirById[airId], modelKey), enemy)
			if m then return m end
			warn("Dogfight Plus: the imported jet '" .. modelKey .. "' has no parts (it is not a mesh model); the part-built stand-in is used")
		elseif not JetBuilder.warned then
			JetBuilder.warned = true
			warn("Dogfight Plus: the jet model '" .. modelKey .. "' is not in ReplicatedStorage.JetModels; part-built stand-ins are used (import the jets: roblox/README.md, step 2)")
		end
	end
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
	local canopy
	if twoSeat then
		canopy = piece("Canopy", Vector3.new(7.4, 2.3, 2.1), CFrame.new(0, 1.45, -2.3) * CFrame.Angles(0, math.rad(90), 0), Color3.fromRGB(110, 170, 220), Enum.Material.Glass, Enum.PartType.Ball)
	else
		canopy = piece("Canopy", Vector3.new(4.4, 2.3, 2.1), CFrame.new(0, 1.45, -3.0) * CFrame.Angles(0, math.rad(90), 0), Color3.fromRGB(110, 170, 220), Enum.Material.Glass, Enum.PartType.Ball)
	end
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
		JetBuilder.addPilot(model, pilotId, 1, twoSeat)
		if twoSeat and wsoId ~= nil then JetBuilder.addPilot(model, wsoId, 2, true) end
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
