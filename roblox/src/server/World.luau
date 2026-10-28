--!nonstrict
-- The playing field: a green island with hills and a runway in a wide sea, the sky and the light.
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)
local IslandMath = require(ReplicatedStorage:WaitForChild("Shared").IslandMath)

local World = {}

-- the air base (the game's own place, on the island's plateau): runway, taxiway, apron, hangars, tower
local function airBase(box, field: Vector3)
	local y = field.Y + 0.6
	local len, wid = 300, 4.5                                        -- 3000 m x 45 m at 1:10
	box("Runway", Vector3.new(wid * 2.4, 1, len), Vector3.new(field.X, y, field.Z), Color3.fromRGB(58, 62, 68))
	for i = -6, 6 do box("RunwayMark", Vector3.new(0.8, 0.2, 10), Vector3.new(field.X, y + 0.6, field.Z + i * 22), Color3.fromRGB(235, 235, 235)) end
	box("Taxiway", Vector3.new(2.6, 1, len), Vector3.new(field.X + 19, y, field.Z), Color3.fromRGB(70, 74, 80))
	box("Apron", Vector3.new(26, 1, 70), Vector3.new(field.X + 39, y, field.Z), Color3.fromRGB(78, 82, 88))
	for i = -1, 1 do box("Hangar", Vector3.new(14, 7, 12), Vector3.new(field.X + 56, y + 3.5, field.Z + i * 24), Color3.fromRGB(122, 128, 134)) end
	box("Tower", Vector3.new(3, 14, 3), Vector3.new(field.X + 30, y + 7, field.Z - 34), Color3.fromRGB(190, 196, 202))
end

function World.build()
	local W = Config.World
	local terrain = workspace.Terrain
	local function box(name, size, pos, col)
		local p = Instance.new("Part")
		p.Name = name
		p.Anchored = true
		p.Size = size
		p.Position = pos
		p.Color = col
		p.Material = Enum.Material.Concrete
		p.Parent = workspace
		return p
	end

	local island = workspace:GetAttribute("IslandBuilt") == true
	if island then
		-- the game's own island is already in the place (IslandBuilder, built once in Studio)
		airBase(box, IslandMath.airfield())
	else
		warn("Dogfight Plus: the real island is not built yet (see roblox/README.md, 'A sziget'). A simple island is used meanwhile.")
		terrain:Clear()
		terrain:FillCylinder(CFrame.new(0, -6, 0), 32, 1500, Enum.Material.Grass)
		local rng = Random.new(7)
		local mats = { Enum.Material.Grass, Enum.Material.Grass, Enum.Material.Ground, Enum.Material.Rock }
		for i = 1, 26 do
			local a, r = rng:NextNumber(0, math.pi * 2), rng:NextNumber(650, 1300)
			terrain:FillBall(Vector3.new(math.cos(a) * r, rng:NextNumber(-20, 40), math.sin(a) * r), rng:NextNumber(110, 320), mats[rng:NextInteger(1, #mats)])
		end
		terrain:FillCylinder(CFrame.new(0, -14, 0), 16, 1590, Enum.Material.Sand)
		terrain:FillCylinder(CFrame.new(0, -6, 0), 32, 1470, Enum.Material.Grass)
		airBase(box, Vector3.new(0, 10, 0))
	end

	-- the sea (a big part: cheaper than terrain water at this size)
	local sea = Instance.new("Part")
	sea.Name = "Sea"
	sea.Anchored = true
	sea.CanCollide = false
	sea.Size = Vector3.new(W.Half * 2 + 8000, 1, W.Half * 2 + 8000)
	sea.Position = Vector3.new(0, -1.6, 0)
	sea.Color = Color3.fromRGB(28, 96, 150)
	sea.Material = Enum.Material.SmoothPlastic
	sea.Transparency = 0.12
	sea.Reflectance = 0.15
	sea.Parent = workspace

	Lighting.ClockTime = 14
	Lighting.Brightness = 3
	Lighting.OutdoorAmbient = Color3.fromRGB(120, 130, 150)
	local atm = Lighting:FindFirstChildOfClass("Atmosphere") or Instance.new("Atmosphere")
	atm.Density = 0.22
	atm.Offset = 0.2
	atm.Color = Color3.fromRGB(190, 205, 225)
	atm.Decay = Color3.fromRGB(150, 170, 200)
	atm.Glare = 0.1
	atm.Haze = 1.2
	atm.Parent = Lighting
end

-- where a player's jet starts: over the air base (the two teams of a team fight on its two sides)
function World.spawnPoint(team: string?, pvp: boolean?, rng)
	local field = IslandMath.airfield()
	local W = Config.World
	local a
	if pvp then a = (team == "A" and math.pi or 0) + rng:NextNumber(-0.5, 0.5) else a = rng:NextNumber(0, math.pi * 2) end
	local pos = Vector3.new(field.X + math.cos(a) * W.SpawnRadius, field.Y + W.SpawnHeight + rng:NextNumber(-60, 60), field.Z + math.sin(a) * W.SpawnRadius)
	local look = Vector3.new(field.X - pos.X, 0, field.Z - pos.Z).Unit
	return pos, look
end

return World
