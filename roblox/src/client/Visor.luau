--!nonstrict
-- The visor is real glass: from the cockpit view everything is seen through its tint (darker and coloured, with a
-- dark rim).  Clear visors change nothing.  Never darker than 25% so that the game stays playable.
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Catalog = require(Shared.Catalog)
local JetBuilder = require(Shared.JetBuilder)
local Ui = require(script.Parent.Ui)

local Visor = {}
local cc, gui
local edges = {}

function Visor.init()
	cc = Instance.new("ColorCorrectionEffect")
	cc.Name = "DogfightVisor"
	cc.Enabled = false
	cc.Parent = Lighting
	gui = Ui.make("ScreenGui", { Name = "DogfightVisor", ResetOnSpawn = false, IgnoreGuiInset = true, DisplayOrder = 1, Enabled = false, Parent = Players.LocalPlayer:WaitForChild("PlayerGui") })
	-- the dark rim of the visor: four strips fading towards the middle
	local function edge(pos, size, rot)
		local f = Ui.make("Frame", { BackgroundColor3 = Color3.new(0, 0, 0), BorderSizePixel = 0, Position = pos, Size = size, BackgroundTransparency = 0.6, Parent = gui })
		local g = Instance.new("UIGradient")
		g.Rotation = rot
		g.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(1, 1) })
		g.Parent = f
		table.insert(edges, f)
	end
	edge(UDim2.new(0, 0, 0, 0), UDim2.new(1, 0, 0.16, 0), 90)
	edge(UDim2.new(0, 0, 0.84, 0), UDim2.new(1, 0, 0.16, 0), -90)
	edge(UDim2.new(0, 0, 0, 0), UDim2.new(0.12, 0, 1, 0), 0)
	edge(UDim2.new(0.88, 0, 0, 0), UDim2.new(0.12, 0, 1, 0), 180)
end

-- outfitId: the worn pilot outfit (or nil), on: the cockpit view is on
function Visor.set(outfitId: string?, on: boolean)
	local o = outfitId and Catalog.PilotById[outfitId]
	if not on or not o or (o.visorT or 1) >= 0.95 then
		cc.Enabled = false
		gui.Enabled = false
		return
	end
	local T = math.max(0.25, o.visorT)
	local k = 1 - T
	cc.TintColor = Color3.new(1, 1, 1):Lerp(JetBuilder.color(o.visor), math.min(0.85, k * 0.95))
	cc.Brightness = -k * 0.22
	cc.Contrast = 0.04 + k * 0.1
	cc.Saturation = -k * 0.1
	cc.Enabled = true
	for _, e in edges do e.BackgroundTransparency = 1 - math.min(0.55, 0.12 + k * 0.5) end
	gui.Enabled = true
end

return Visor
