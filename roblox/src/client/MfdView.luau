--!nonstrict
-- The cockpit displays on the screen: in the cockpit view (V) the radar, map, stores and engine pages of shared/game/Mfd.luau are drawn
-- on panels along the bottom of the screen (the browser game shows them on the 3D instrument panel).  J / K / L turn their pages; N makes
-- them bigger.  Each panel is a GuiCanvas of its own pixel size inside a clipping frame that scales it.
local Players = game:GetService("Players")

local GuiCanvas = require(script.Parent.GuiCanvas)
local Config = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared").Config)
local Coords = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared").Coords)

local K = Config.Island.StudsPerMeter * Config.ModelScale                  -- studs per metre of a model (the jets are drawn this big)
local METRES_PER_PIXEL = 0.17 / 512                                         -- a 512 pixel display is 17 cm wide
local Mfd = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared").game.Mfd)

local MfdView = {}
MfdView.__index = MfdView

-- use3d: the displays are real screens on a dashboard in front of the pilot (SurfaceGuis on parts, placed round the jet); else they
-- are drawn on panels along the bottom of the screen
function MfdView.new(spec, use3d)
	local self = setmetatable({}, MfdView)
	self.use3d = use3d == true
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
	if self.use3d then
		local folder = Instance.new("Folder")
		folder.Name = "CockpitPanel"
		self.folder = folder
		local plate = Instance.new("Part")
		plate.Name = "Plate"
		plate.Anchored, plate.CanCollide, plate.CanQuery, plate.CanTouch, plate.CastShadow = true, false, false, false, false
		plate.Color = Color3.fromRGB(20, 22, 24)
		plate.Material = Enum.Material.SmoothPlastic
		plate.Parent = folder
		self.plate = plate
	end
	for _, d in ipairs(self.mfd.list) do
		local frame = Instance.new("Frame")
		frame.Name = d.name
		frame.BackgroundColor3 = Color3.fromRGB(2, 8, 5)
		frame.BorderSizePixel = 0
		frame.ClipsDescendants = true
		frame.Size = UDim2.fromOffset(d.w, d.h)
		local part, scale = nil, nil
		if self.use3d then
			part = Instance.new("Part")
			part.Name = d.name
			part.Anchored, part.CanCollide, part.CanQuery, part.CanTouch, part.CastShadow = true, false, false, false, false
			part.Color = Color3.fromRGB(2, 8, 5)
			part.Material = Enum.Material.SmoothPlastic
			part.Size = Vector3.new(d.w * METRES_PER_PIXEL * K, d.h * METRES_PER_PIXEL * K, 0.004)
			local sg = Instance.new("SurfaceGui")
			sg.Face = Enum.NormalId.Front
			sg.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
			sg.CanvasSize = Vector2.new(d.w, d.h)
			sg.LightInfluence = 0
			sg.Brightness = 1.6
			sg.AlwaysOnTop = false
			sg.Parent = part
			frame.Parent = sg
			part.Parent = self.folder
		else
			frame.Parent = gui
			local stroke = Instance.new("UIStroke")
			stroke.Color = Color3.fromRGB(60, 70, 66)
			stroke.Thickness = 3
			stroke.Parent = frame
			scale = Instance.new("UIScale")
			scale.Parent = frame
		end
		local canvas = GuiCanvas.new(player, { container = frame, size = Vector2.new(d.w, d.h) })
		d.g = canvas
		self.panels[#self.panels + 1] = { d = d, frame = frame, scale = scale, canvas = canvas, part = part }
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
-- the dashboard in front of the pilot: ac = the player's jet, eye / panel = where the pilot's eye and the middle of the displays are (jet frame, metres)
function MfdView:place3d(ac, eye, panelAt)
	local cf = Coords.cframe(ac.pos, ac.quat)
	local function local3(b) return Vector3.new(b.x, b.z, -b.y) * K end
	local eyeAt, centre = local3(eye), local3(panelAt)
	local face = CFrame.lookAt(centre, eyeAt)                                  -- the screens look at the pilot's eyes
	local n = 0
	for _, p in ipairs(self.panels) do
		if p.d.key == "L" then n += 1 end
	end
	local hasCentre = n > 0
	for _, p in ipairs(self.panels) do
		local d = p.d
		local x, y = 0, 0
		if d.key == "J" then x = -0.19
		elseif d.key == "K" then x = 0.19
		elseif d.key == "L" then x, y = 0, -0.015
		elseif d.pages[1] == "ded" then y = hasCentre and 0.165 or 0.12
		else x, y = -0.38, 0 end
		local off = CFrame.new(x * K, y * K, 0)
		p.part.CFrame = cf * face * off
	end
	self.plate.Size = Vector3.new(1.0 * K, 0.5 * K, 0.004)
	self.plate.CFrame = cf * face * CFrame.new(0, 0.02 * K, 0.004 * K + 0.003)
end

function MfdView:update(dt, ac, world, info, visible, w, h, big, eye, panelAt)
	self.gui.Enabled = visible and not self.use3d
	if self.use3d then
		self.folder.Parent = visible and workspace or nil
	end
	if not visible then return end
	if not self.hasCentre then
		for _, d in ipairs(self.mfd.list) do if d.key == "L" then self.hasCentre = true end end
	end
	if self.use3d then
		if eye and panelAt then self:place3d(ac, eye, panelAt) end
	else
		self:layout(w, h, big)
	end
	for _, p in ipairs(self.panels) do p.canvas:begin() end
	self.mfd:update(dt, ac, world, info)
	for _, p in ipairs(self.panels) do p.canvas:finish() end
end

function MfdView:destroy()
	self.gui:Destroy()
	if self.folder then self.folder:Destroy() end
end

return MfdView
