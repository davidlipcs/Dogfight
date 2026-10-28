--!nonstrict
-- The loading screen: a full screen cover with what is being loaded and a bar.  The match starts only when everything is there
-- (the island, the runway, the aircraft and their meshes), so nothing pops in while you fly.
local Players = game:GetService("Players")

local LoadingUi = {}

local gui, status, fill

local function build()
	gui = Instance.new("ScreenGui")
	gui.Name = "DogfightLoading"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 100
	gui.Enabled = false
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	local back = Instance.new("Frame")
	back.Size = UDim2.fromScale(1, 1)
	back.BackgroundColor3 = Color3.fromRGB(6, 12, 16)
	back.BorderSizePixel = 0
	back.Active = true
	back.Parent = gui
	local title = Instance.new("TextLabel")
	title.AnchorPoint = Vector2.new(0.5, 0.5)
	title.Position = UDim2.fromScale(0.5, 0.4)
	title.Size = UDim2.fromOffset(600, 60)
	title.BackgroundTransparency = 1
	title.Font = Enum.Font.GothamBlack
	title.TextSize = 44
	title.TextColor3 = Color3.fromRGB(107, 255, 133)
	title.Text = "DOGFIGHT PLUS"
	title.Parent = back
	status = Instance.new("TextLabel")
	status.AnchorPoint = Vector2.new(0.5, 0.5)
	status.Position = UDim2.fromScale(0.5, 0.52)
	status.Size = UDim2.fromOffset(700, 28)
	status.BackgroundTransparency = 1
	status.Font = Enum.Font.GothamMedium
	status.TextSize = 18
	status.TextColor3 = Color3.fromRGB(215, 228, 220)
	status.Text = "Betöltés…"
	status.Parent = back
	local track = Instance.new("Frame")
	track.AnchorPoint = Vector2.new(0.5, 0.5)
	track.Position = UDim2.fromScale(0.5, 0.58)
	track.Size = UDim2.fromOffset(420, 10)
	track.BackgroundColor3 = Color3.fromRGB(34, 44, 48)
	track.BorderSizePixel = 0
	track.Parent = back
	local c1 = Instance.new("UICorner")
	c1.CornerRadius = UDim.new(0, 5)
	c1.Parent = track
	fill = Instance.new("Frame")
	fill.Size = UDim2.new(0, 0, 1, 0)
	fill.BackgroundColor3 = Color3.fromRGB(255, 200, 64)
	fill.BorderSizePixel = 0
	fill.Parent = track
	local c2 = Instance.new("UICorner")
	c2.CornerRadius = UDim.new(0, 5)
	c2.Parent = fill
end

function LoadingUi.show(text, frac)
	if not gui then build() end
	gui.Enabled = true
	LoadingUi.set(text, frac)
end

function LoadingUi.set(text, frac)
	if not gui then return end
	if text then status.Text = text end
	if frac then fill.Size = UDim2.new(math.clamp(frac, 0, 1), 0, 1, 0) end
end

function LoadingUi.hide()
	if gui then gui.Enabled = false end
end

return LoadingUi
