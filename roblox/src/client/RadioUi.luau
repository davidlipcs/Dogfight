--!nonstrict
-- The radio on the screen (shared/game/Radio.luau): the log of the last calls (subtitles, with who speaks) at the bottom left,
-- and - with the I key (or the RÁDIÓ button on a phone) - the panel: type a call or pick one from the numbered list.
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")

local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Radio = require(Shared.game.Radio)

local RadioUi = {}
RadioUi.__index = RadioUi

local COLORS = {
	you = Color3.fromRGB(150, 220, 255), tower = Color3.fromRGB(255, 200, 64), awacs = Color3.fromRGB(190, 160, 255),
	wing = Color3.fromRGB(107, 255, 133), lead = Color3.fromRGB(107, 255, 133), instructor = Color3.fromRGB(255, 160, 90),
}
local FADE_AFTER = 9

local function corner(o, r)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, r)
	c.Parent = o
end

-- input: the DeviceInput of the game (it is muted while the panel is open)
function RadioUi.new(input)
	local self = setmetatable({}, RadioUi)
	self.input = input
	self.open = false
	self.radio = nil
	self.seen, self.lastChange = -1, -1e9
	local gui = Instance.new("ScreenGui")
	gui.Name = "RadioGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 7
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	self.gui = gui

	local log = Instance.new("TextLabel")
	log.Name = "Log"
	log.AnchorPoint = Vector2.new(0, 1)
	log.Position = UDim2.new(0, 16, 1, -150)
	log.Size = UDim2.new(0, 460, 0, 110)
	log.BackgroundTransparency = 1
	log.TextXAlignment = Enum.TextXAlignment.Left
	log.TextYAlignment = Enum.TextYAlignment.Bottom
	log.TextWrapped = true
	log.RichText = true
	log.TextSize = 15
	log.Font = Enum.Font.GothamMedium
	log.TextColor3 = Color3.new(1, 1, 1)
	log.TextStrokeTransparency = 0.4
	log.Text = ""
	log.Parent = gui
	self.logLabel = log

	local panel = Instance.new("Frame")
	panel.Name = "Panel"
	panel.AnchorPoint = Vector2.new(0.5, 1)
	panel.Position = UDim2.new(0.5, 0, 1, -24)
	panel.Size = UDim2.new(0, 560, 0, 400)
	panel.BackgroundColor3 = Color3.fromRGB(10, 18, 22)
	panel.BackgroundTransparency = 0.06
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 8)
	self.panel = panel
	local title = Instance.new("TextLabel")
	title.BackgroundTransparency = 1
	title.Position = UDim2.new(0, 14, 0, 8)
	title.Size = UDim2.new(1, -28, 0, 22)
	title.TextXAlignment = Enum.TextXAlignment.Left
	title.TextSize = 15
	title.Font = Enum.Font.GothamBold
	title.TextColor3 = Color3.fromRGB(255, 200, 64)
	title.Text = "RÁDIÓ – írd be angolul (pl. FOX TWO), vagy kattints / nyomj számot"
	title.Parent = panel
	local box = Instance.new("TextBox")
	box.Name = "Input"
	box.Position = UDim2.new(0, 12, 0, 36)
	box.Size = UDim2.new(1, -24, 0, 34)
	box.BackgroundColor3 = Color3.fromRGB(26, 40, 46)
	box.BorderSizePixel = 0
	box.ClearTextOnFocus = false
	box.PlaceholderText = "ide írj, Enter = adás · Esc = mégsem"
	box.Text = ""
	box.TextColor3 = Color3.new(1, 1, 1)
	box.TextSize = 17
	box.Font = Enum.Font.RobotoMono
	box.TextXAlignment = Enum.TextXAlignment.Left
	box.Parent = panel
	corner(box, 6)
	self.box = box
	local list = Instance.new("Frame")
	list.Name = "List"
	list.BackgroundTransparency = 1
	list.Position = UDim2.new(0, 12, 0, 78)
	list.Size = UDim2.new(1, -24, 1, -86)
	list.Parent = panel
	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 3)
	layout.Parent = list
	self.list = list
	self.menu = {}

	box:GetPropertyChangedSignal("Text"):Connect(function()
		-- a digit in the empty box picks that call
		if self.open and os.clock() - (self.openedAt or 0) < 0.25 and string.lower(box.Text) == "i" then
			box.Text = ""                                   -- the key that opened the panel
		elseif self.open and string.match(box.Text, "^%d$") then
			local d = tonumber(box.Text)
			box.Text = ""
			self:pick(d)
		end
	end)
	box.FocusLost:Connect(function(enter)
		if not self.open then return end
		local text = box.Text
		self:close()
		if enter and self.radio then self.radio:transmit(text, "type") end
	end)

	if UserInputService.TouchEnabled then
		local b = Instance.new("TextButton")
		b.Name = "RadioButton"
		b.AnchorPoint = Vector2.new(0, 1)
		b.Position = UDim2.new(0, 16, 1, -100)
		b.Size = UDim2.new(0, 86, 0, 36)
		b.Text = "RÁDIÓ"
		b.TextSize = 14
		b.Font = Enum.Font.GothamBold
		b.TextColor3 = Color3.fromRGB(16, 22, 20)
		b.BackgroundColor3 = Color3.fromRGB(255, 200, 64)
		b.BackgroundTransparency = 0.25
		b.Parent = gui
		corner(b, 6)
		b.Activated:Connect(function() self:toggle() end)
	end
	return self
end

function RadioUi:pick(digit)
	local i = (digit + 7) % 10 + 1                      -- the keys 3..9, 0, 1, 2 are the entries 1..10
	local c = self.menu[i]
	if not c then return end
	self:close()
	if self.radio then self.radio:transmit(c.say, "menu") end
end

local function setMouse(free)
	UserInputService.MouseBehavior = free and Enum.MouseBehavior.Default or Enum.MouseBehavior.LockCenter
	UserInputService.MouseIconEnabled = free
end

function RadioUi:show()
	if self.open or not self.radio then return end
	self.open = true
	self.input.listening = false
	self.input:releaseAll()
	setMouse(true)
	local calls = self.radio:available()
	self.menu = {}
	for _, c in self.list:GetChildren() do
		if c:IsA("GuiObject") then c:Destroy() end
	end
	for i = 1, math.min(10, #calls) do
		local c = calls[i]
		self.menu[i] = c
		local b = Instance.new("TextButton")
		b.Size = UDim2.new(1, 0, 0, 26)
		b.BackgroundColor3 = Color3.fromRGB(24, 38, 44)
		b.BorderSizePixel = 0
		b.AutoButtonColor = true
		b.TextXAlignment = Enum.TextXAlignment.Left
		b.RichText = true
		b.TextSize = 14
		b.Font = Enum.Font.Gotham
		b.TextColor3 = Color3.fromRGB(215, 228, 220)
		b.Text = string.format("  <font color=\"#ffc840\"><b>%d</b></font>  <b>%s</b>  <font color=\"#9fb0a8\">%s</font>", (i + 2) % 10, c.say, c.hu)
		b.Parent = self.list
		corner(b, 4)
		b.Activated:Connect(function()
			self:close()
			self.radio:transmit(c.say, "menu")
		end)
	end
	if #calls > 10 then
		local more = Instance.new("TextLabel")
		more.BackgroundTransparency = 1
		more.Size = UDim2.new(1, 0, 0, 20)
		more.TextXAlignment = Enum.TextXAlignment.Left
		more.TextSize = 13
		more.Font = Enum.Font.Gotham
		more.TextColor3 = Color3.fromRGB(150, 170, 165)
		more.Text = string.format("  …és még %d: írd be", #calls - 10)
		more.Parent = self.list
	end
	self.box.Text = ""
	self.panel.Visible = true
	self.openedAt = os.clock()
	task.defer(function()
		if self.open then self.box:CaptureFocus() end
	end)
end

function RadioUi:close()
	if not self.open then return end
	self.open = false
	self.panel.Visible = false
	self.box.Text = ""
	pcall(function() self.box:ReleaseFocus() end)
	self.input.listening = true
	setMouse(false)
end

function RadioUi:toggle()
	if self.open then self:close() else self:show() end
end

-- every frame: the radio of the running match
function RadioUi:update(radio, paused)
	self.radio = radio
	if paused and self.open then self:close() end
	if not radio then self.logLabel.Text = ""; return end
	local now = os.clock()
	if radio.version ~= self.seen then
		self.seen = radio.version
		self.lastChange = now
		local lines = {}
		for _, l in ipairs(radio.log) do
			local c = COLORS[l.who] or Color3.new(1, 1, 1)
			local hex = string.format("#%02x%02x%02x", math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5))
			local text = string.gsub(l.text, "&", "&amp;")
			text = string.gsub(text, "<", "&lt;")
			table.insert(lines, string.format("<font color=\"%s\"><b>%s</b></font> %s", hex, Radio.NAMES[l.who] or l.who, text))
		end
		self.logLabel.Text = table.concat(lines, "\n")
	end
	self.logLabel.TextTransparency = (now - self.lastChange > FADE_AFTER and not self.open) and 0.6 or 0
end

function RadioUi:destroy()
	self:close()
	self.gui:Destroy()
end

return RadioUi
