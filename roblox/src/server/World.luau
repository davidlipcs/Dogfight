--!nonstrict
-- The playing field: a green island with hills and a runway in a wide sea, the sky and the light.
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)

local World = {}

function World.build()
	local W = Config.World
	local terrain = workspace.Terrain
	terrain:Clear()

	-- the island: grass on top of a thin slab, hills of grass, rock and earth
	terrain:FillCylinder(CFrame.new(0, -6, 0), 32, W.IslandRadius, Enum.Material.Grass)
	local rng = Random.new(7)
	local mats = { Enum.Material.Grass, Enum.Material.Grass, Enum.Material.Ground, Enum.Material.Rock }
	for i = 1, 26 do
		local a, r = rng:NextNumber(0, math.pi * 2), rng:NextNumber(650, W.IslandRadius - 200)
		local radius = rng:NextNumber(110, 320)
		terrain:FillBall(Vector3.new(math.cos(a) * r, rng:NextNumber(-20, 40), math.sin(a) * r), radius, mats[rng:NextInteger(1, #mats)])
	end
	-- the beach: a ring of sand at the water line
	terrain:FillCylinder(CFrame.new(0, -14, 0), 16, W.IslandRadius + 90, Enum.Material.Sand)
	terrain:FillCylinder(CFrame.new(0, -6, 0), 32, W.IslandRadius - 30, Enum.Material.Grass)

	-- the sea (a big part: cheaper than terrain water at this size)
	local sea = Instance.new("Part")
	sea.Name = "Sea"
	sea.Anchored = true
	sea.CanCollide = false
	sea.Size = Vector3.new(W.Half * 2 + 4000, 2, W.Half * 2 + 4000)
	sea.Position = Vector3.new(0, -4, 0)
	sea.Color = Color3.fromRGB(28, 96, 150)
	sea.Material = Enum.Material.SmoothPlastic
	sea.Transparency = 0.12
	sea.Reflectance = 0.15
	sea.Parent = workspace

	-- the runway and a few buildings (decoration and a landmark to fly around)
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
	box("Runway", Vector3.new(90, 1, 1000), Vector3.new(0, 10.5, 0), Color3.fromRGB(58, 62, 68))
	for i = -4, 4 do
		box("RunwayMark", Vector3.new(3, 0.2, 40), Vector3.new(0, 11.1, i * 100), Color3.fromRGB(235, 235, 235))
	end
	for i = 1, 3 do
		box("Hangar", Vector3.new(60, 24, 50), Vector3.new(160, 22, -300 + i * 140), Color3.fromRGB(122, 128, 134))
	end
	box("Tower", Vector3.new(14, 60, 14), Vector3.new(120, 40, 260), Color3.fromRGB(190, 196, 202))

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

return World
