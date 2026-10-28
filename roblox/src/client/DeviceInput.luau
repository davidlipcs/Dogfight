--!nonstrict
-- Keyboard, mouse and gamepad as the browser game sees them (web/js/game.js Input, Pad): keys have the browser game's names
-- ("w", "Space", "shift", "control", "Tab" ...), the mouse is locked to the middle and gives its travel, a gamepad gives the
-- left stick and the buttons.  Presses are handed to onPress(name); wheel notches to onWheel(direction).
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")

local KeyCode = Enum.KeyCode
local NAMES = {
	[KeyCode.Space] = "Space", [KeyCode.Tab] = "Tab", [KeyCode.LeftShift] = "shift", [KeyCode.RightShift] = "shift",
	[KeyCode.LeftControl] = "control", [KeyCode.RightControl] = "control", [KeyCode.Return] = "Enter", [KeyCode.KeypadEnter] = "Enter",
	[KeyCode.Escape] = "Escape", [KeyCode.F1] = "F1",
	[KeyCode.One] = "1", [KeyCode.Two] = "2", [KeyCode.Three] = "3", [KeyCode.Four] = "4", [KeyCode.Five] = "5",
	[KeyCode.Up] = "ArrowUp", [KeyCode.Down] = "ArrowDown", [KeyCode.Left] = "ArrowLeft", [KeyCode.Right] = "ArrowRight",
}
for _, name in { "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z" } do
	NAMES[KeyCode[name]] = string.lower(name)
end

local PAD = {
	[KeyCode.ButtonA] = "Space", [KeyCode.ButtonX] = "t", [KeyCode.ButtonB] = "f", [KeyCode.ButtonY] = "__weapon", [KeyCode.DPadUp] = "g",
	[KeyCode.DPadLeft] = "v", [KeyCode.DPadRight] = "__zoom", [KeyCode.ButtonR3] = "m", [KeyCode.ButtonStart] = "Escape", [KeyCode.ButtonSelect] = "h",
}

local DeviceInput = {}
DeviceInput.__index = DeviceInput

function DeviceInput.new()
	local self = setmetatable({}, DeviceInput)
	self.keys = {}                     -- by the browser's names
	self.mouse = { [0] = false, [1] = false, [2] = false }
	self.padButtons = {}
	self.pad = { lx = 0, ly = 0, rx = 0, ry = 0, rt = false, lt = false, rb = false, lb = false, down = false, l3 = false }
	self.padConnected = false
	self.onPress, self.onRelease, self.onWheel, self.onPadAction = nil, nil, nil, nil
	self.enabled = false               -- the mouse is locked and the flying keys work
	self.listening = true
	self.conns = {}

	local function press(name)
		if not self.keys[name] and self.onPress then self.onPress(name) end
		self.keys[name] = true
	end
	table.insert(self.conns, UserInputService.InputBegan:Connect(function(input, processed)
		if not self.listening then return end
		local t = input.UserInputType
		if t == Enum.UserInputType.Keyboard then
			local name = NAMES[input.KeyCode]
			if not name then return end
			-- paused: only the keys that bring the pause screen and the help up / down
			if not self.enabled and name ~= "Escape" and name ~= "p" and name ~= "h" and name ~= "F1" then return end
			if name == "e" and (self.keys.control) then
				if self.onPress then self.onPress("eject") end
				return
			end
			press(name)
		elseif not self.enabled then return
		elseif t == Enum.UserInputType.MouseButton1 then self.mouse[0] = true
		elseif t == Enum.UserInputType.MouseButton3 then
			self.mouse[1] = true
			if self.onPress then self.onPress("__zoom") end
		elseif t == Enum.UserInputType.MouseButton2 then self.mouse[2] = true
		elseif t == Enum.UserInputType.Gamepad1 then
			self.padConnected = true
			local k = input.KeyCode
			self.padButtons[k] = true
			if k == KeyCode.ButtonR2 then
				self.pad.rt = true
				if self.onPress then self.onPress("shift") end
			elseif k == KeyCode.ButtonL2 then
				self.pad.lt = true
				if self.onPress then self.onPress("z") end
			elseif k == KeyCode.ButtonR1 then self.pad.rb = true
			elseif k == KeyCode.ButtonL1 then self.pad.lb = true
			elseif k == KeyCode.DPadDown then self.pad.down = true
			elseif k == KeyCode.ButtonL3 then self.pad.l3 = true
			elseif PAD[k] then
				local n = PAD[k]
				if n == "__weapon" then
					if self.onWheel then self.onWheel(1) end
				elseif self.onPress then self.onPress(n) end
			end
		end
	end))
	table.insert(self.conns, UserInputService.InputEnded:Connect(function(input)
		local t = input.UserInputType
		if t == Enum.UserInputType.Keyboard then
			local name = NAMES[input.KeyCode]
			if name then
				self.keys[name] = nil
				if self.onRelease then self.onRelease(name) end
			end
		elseif t == Enum.UserInputType.MouseButton1 then self.mouse[0] = false
		elseif t == Enum.UserInputType.MouseButton3 then self.mouse[1] = false
		elseif t == Enum.UserInputType.MouseButton2 then self.mouse[2] = false
		elseif t == Enum.UserInputType.Gamepad1 then
			local k = input.KeyCode
			self.padButtons[k] = nil
			if k == KeyCode.ButtonR2 then self.pad.rt = false
			elseif k == KeyCode.ButtonL2 then self.pad.lt = false
			elseif k == KeyCode.ButtonR1 then self.pad.rb = false
			elseif k == KeyCode.ButtonL1 then self.pad.lb = false
			elseif k == KeyCode.DPadDown then self.pad.down = false
			elseif k == KeyCode.ButtonL3 then self.pad.l3 = false end
		end
	end))
	table.insert(self.conns, UserInputService.InputChanged:Connect(function(input)
		if not self.enabled then return end
		if input.UserInputType == Enum.UserInputType.MouseWheel then
			-- one weapon step per notch
			if self.onWheel then self.onWheel(input.Position.Z > 0 and 1 or -1) end
		elseif input.UserInputType == Enum.UserInputType.Gamepad1 then
			local k = input.KeyCode
			if k == KeyCode.Thumbstick1 then
				local function dz(v) local a = math.abs(v); if a < 0.12 then return 0 end return (v < 0 and -1 or 1) * ((a - 0.12) / 0.88) ^ 1.5 end
				self.pad.lx, self.pad.ly = dz(input.Position.X), dz(-input.Position.Y)
			elseif k == KeyCode.Thumbstick2 then
				local function dz(v) local a = math.abs(v); if a < 0.12 then return 0 end return (v < 0 and -1 or 1) * ((a - 0.12) / 0.88) ^ 1.5 end
				self.pad.rx, self.pad.ry = dz(input.Position.X), dz(-input.Position.Y)
			end
		end
	end))
	table.insert(self.conns, UserInputService.WindowFocusReleased:Connect(function() self:releaseAll() end))
	table.insert(self.conns, UserInputService.GamepadConnected:Connect(function() self.padConnected = true end))
	table.insert(self.conns, UserInputService.GamepadDisconnected:Connect(function() self.padConnected = false end))
	return self
end

function DeviceInput:releaseAll()
	self.keys = {}
	self.mouse = { [0] = false, [1] = false, [2] = false }
	local p = self.pad
	p.lx, p.ly, p.rx, p.ry, p.rt, p.lt, p.rb, p.lb, p.down, p.l3 = 0, 0, 0, 0, false, false, false, false, false, false
end

-- on: the mouse is locked to the middle and hidden (flying); off: free (menus)
function DeviceInput:setEnabled(on)
	self.enabled = on
	if on then
		UserInputService.MouseBehavior = Enum.MouseBehavior.LockCenter
		UserInputService.MouseIconEnabled = false
	else
		UserInputService.MouseBehavior = Enum.MouseBehavior.Default
		UserInputService.MouseIconEnabled = true
		self:releaseAll()
	end
end

-- the mouse travel since the last call, in pixels
function DeviceInput:takeDelta()
	if not self.enabled then return 0, 0 end
	local d = UserInputService:GetMouseDelta()
	return d.X, d.Y
end

-- the table game/Controls.luau wants
function DeviceInput:snapshot(dx, dy)
	local keys = self.keys
	return {
		dx = dx, dy = dy, held = function(name) return keys[name] == true end, mouse = self.mouse,
		pad = self.padConnected and self.pad or nil,
	}
end

function DeviceInput:destroy()
	for _, c in self.conns do c:Disconnect() end
	self.conns = {}
	self:setEnabled(false)
end

return DeviceInput
