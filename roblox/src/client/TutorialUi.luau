--!nonstrict
-- The card of the tutorial (shared/game/Tutorial.luau): the lesson's text, the task and what the game sees of it.
local Players = game:GetService("Players")

local TutorialUi = {}
TutorialUi.__index = TutorialUi

function TutorialUi.new()
	local self = setmetatable({}, TutorialUi)
	local gui = Instance.new("ScreenGui")
	gui.Name = "TutorialGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 6
	gui.Enabled = false
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	self.gui = gui
	local card = Instance.new("Frame")
	card.AnchorPoint = Vector2.new(1, 0.5)
	card.Position = UDim2.new(1, -16, 0.5, 0)
	card.Size = UDim2.new(0, 400, 0.78, 0)
	card.BackgroundColor3 = Color3.fromRGB(10, 18, 22)
	card.BackgroundTransparency = 0.12
	card.BorderSizePixel = 0
	card.Parent = gui
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, 8)
	c.Parent = card
	local function label(name, y, h, size, color, font)
		local l = Instance.new("TextLabel")
		l.Name = name
		l.BackgroundTransparency = 1
		l.Position = UDim2.new(0, 14, 0, y)
		l.Size = UDim2.new(1, -28, 0, h)
		l.TextXAlignment = Enum.TextXAlignment.Left
		l.TextYAlignment = Enum.TextYAlignment.Top
		l.TextWrapped = true
		l.RichText = true
		l.TextSize = size
		l.TextColor3 = color
		l.Font = font or Enum.Font.Gotham
		l.Text = ""
		l.Parent = card
		return l
	end
	self.head = label("Head", 8, 18, 12, Color3.fromRGB(107, 255, 133), Enum.Font.RobotoMono)
	self.title = label("Title", 28, 30, 22, Color3.fromRGB(255, 200, 64), Enum.Font.Oswald)
	local scroll = Instance.new("ScrollingFrame")
	scroll.Name = "Body"
	scroll.BackgroundTransparency = 1
	scroll.BorderSizePixel = 0
	scroll.Position = UDim2.new(0, 10, 0, 62)
	scroll.Size = UDim2.new(1, -20, 1, -178)
	scroll.ScrollBarThickness = 6
	scroll.CanvasSize = UDim2.new(0, 0, 0, 0)
	scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
	scroll.Parent = card
	local body = Instance.new("TextLabel")
	body.BackgroundTransparency = 1
	body.Size = UDim2.new(1, -8, 0, 0)
	body.AutomaticSize = Enum.AutomaticSize.Y
	body.TextXAlignment = Enum.TextXAlignment.Left
	body.TextYAlignment = Enum.TextYAlignment.Top
	body.TextWrapped = true
	body.RichText = true
	body.TextSize = 14
	body.Font = Enum.Font.Gotham
	body.TextColor3 = Color3.fromRGB(215, 228, 220)
	body.Parent = scroll
	self.body = body
	local task = Instance.new("Frame")
	task.Name = "Task"
	task.AnchorPoint = Vector2.new(0, 1)
	task.Position = UDim2.new(0, 10, 1, -34)
	task.Size = UDim2.new(1, -20, 0, 100)
	task.BackgroundColor3 = Color3.fromRGB(24, 40, 34)
	task.BorderSizePixel = 0
	task.Parent = card
	local tc = Instance.new("UICorner")
	tc.CornerRadius = UDim.new(0, 6)
	tc.Parent = task
	self.task = task
	local tt = Instance.new("TextLabel")
	tt.BackgroundTransparency = 1
	tt.Position = UDim2.new(0, 10, 0, 6)
	tt.Size = UDim2.new(1, -20, 0, 60)
	tt.TextXAlignment = Enum.TextXAlignment.Left
	tt.TextYAlignment = Enum.TextYAlignment.Top
	tt.TextWrapped = true
	tt.RichText = true
	tt.TextSize = 14
	tt.Font = Enum.Font.GothamMedium
	tt.TextColor3 = Color3.fromRGB(235, 245, 235)
	tt.Parent = task
	self.taskText = tt
	local st = Instance.new("TextLabel")
	st.BackgroundTransparency = 1
	st.Position = UDim2.new(0, 10, 1, -28)
	st.Size = UDim2.new(1, -20, 0, 22)
	st.TextXAlignment = Enum.TextXAlignment.Left
	st.TextSize = 13
	st.Font = Enum.Font.RobotoMono
	st.TextColor3 = Color3.fromRGB(107, 255, 133)
	st.Text = ""
	st.Parent = task
	self.status = st
	self.foot = label("Foot", 0, 24, 12, Color3.fromRGB(140, 160, 150), Enum.Font.Gotham)
	self.foot.AnchorPoint = Vector2.new(0, 1)
	self.foot.Position = UDim2.new(0, 14, 1, -8)
	self.version = -1
	return self
end

function TutorialUi:update(v)
	if not v then self.gui.Enabled = false; return end
	self.gui.Enabled = true
	self.head.Text = string.format("OKTATÁS · %d / %d", v.i, v.n)
	if v.version ~= self.version then
		self.version = v.version
		self.title.Text = v.title
		self.body.Text = v.body
		self.body.Parent.CanvasPosition = Vector2.new(0, 0)
		self.foot.Text = (v.read and "<font color=\"#ffc840\"><b>[Enter]</b></font> = tovább" or "<font color=\"#ffc840\"><b>[Enter]</b></font> = lépés kihagyása") .. " · Esc = menü"
	end
	self.taskText.Text = (v.done and "<font color=\"#6bff85\"><b>✓ KÉSZ</b></font> Szép volt! Megyünk tovább…" or ("<b>FELADAT</b> " .. v.task))
	self.status.Text = v.status or ""
end

function TutorialUi:destroy() self.gui:Destroy() end

return TutorialUi
