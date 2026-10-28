--!nonstrict
-- The cockpit displays on the screen: in the cockpit view (V) the radar, map, stores and engine pages of shared/game/Mfd.luau are drawn
-- on panels along the bottom of the screen (the browser game shows them on the 3D instrument panel).  J / K / L turn their pages; N makes
-- them bigger.  Each panel is a GuiCanvas of its own pixel size inside a clipping frame that scales it.
local Players = game:GetService("Players")

local GuiCanvas = require(script.Parent.GuiCanvas)
local Mfd = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared").game.Mfd)

local MfdView = {}
MfdView.__index = MfdView

function MfdView.new(spec)
	local self = setmetatable({}, MfdView)
	local player = Players.LocalPlayer
	local gui = Instance.new("ScreenGui")
	gui.Name = "MfdGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 4
	gui.Enabled = false
	gui.Parent = player:WaitForChild("PlayerGui")
	self.gui = gui
	self.mfd = Mfd.new(spec)
	self.panels = {}
	for _, d in ipairs(self.mfd.list) do
		local frame = Instance.new("Frame")
		frame.Name = d.name
		frame.BackgroundColor3 = Color3.fromRGB(2, 8, 5)
		frame.BorderSizePixel = 0
		frame.ClipsDescendants = true
		frame.Size = UDim2.fromOffset(d.w, d.h)
		frame.Parent = gui
		local stroke = Instance.new("UIStroke")
		stroke.Color = Color3.fromRGB(60, 70, 66)
		stroke.Thickness = 3
		stroke.Parent = frame
		local scale = Instance.new("UIScale")
		scale.Parent = frame
		local canvas = GuiCanvas.new(player, { container = frame, size = Vector2.new(d.w, d.h) })
		d.g = canvas
		self.panels[#self.panels + 1] = { d = d, frame = frame, scale = scale, canvas = canvas }
	end
	return self
end

-- the places: the pages with a key go to the bottom left (J), bottom right (K) and the middle (L); the data strip and the mini RWR above them
function MfdView:layout(w, h, big)
	local base = math.min(h * (big and 0.44 or 0.27), w * 0.2)
	local side = { J = 0, K = 0, L = 0 }
	for _, p in ipairs(self.panels) do
		local d = p.d
		local k = base / 512
		if d.pages[1] == "ded" then k = base * 1.5 / 512 elseif d.pages[1] == "rwrmini" then k = base * 0.5 / 256 end
		p.scale.Scale = k
		local pw, ph = d.w * k, d.h * k
		if d.key == "J" then p.frame.Position = UDim2.fromOffset(12, h - ph - 12)
		elseif d.key == "K" then p.frame.Position = UDim2.fromOffset(w - pw - 12, h - ph - 12)
		elseif d.key == "L" then p.frame.Position = UDim2.fromOffset(w / 2 - pw / 2, h - ph - 12)
		elseif d.pages[1] == "ded" then p.frame.Position = UDim2.fromOffset(w / 2 - pw / 2, h - ph - 12 - (self.hasCentre and base * 1.02 or 0))
		elseif d.pages[1] == "rwrmini" then p.frame.Position = UDim2.fromOffset(12 + base + 14, h - ph - 12)
		else p.frame.Position = UDim2.fromOffset(w / 2 - pw / 2 + base * 0.6, h - ph - 12) end
	end
end

function MfdView:cycle(side) return self.mfd:cycle(side) end

-- visible: draw the displays (and show them); info = the match's nav table
function MfdView:update(dt, ac, world, info, visible, w, h, big)
	self.gui.Enabled = visible
	if not visible then return end
	if not self.hasCentre then
		for _, d in ipairs(self.mfd.list) do if d.key == "L" then self.hasCentre = true end end
	end
	self:layout(w, h, big)
	for _, p in ipairs(self.panels) do p.canvas:begin() end
	self.mfd:update(dt, ac, world, info)
	for _, p in ipairs(self.panels) do p.canvas:finish() end
end

function MfdView:destroy() self.gui:Destroy() end

return MfdView
