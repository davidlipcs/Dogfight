--!nonstrict
-- The flight display: speed, altitude, throttle, hull, weapons, enemy markers, the missile lock box, warnings,
-- the toasts, a key help - and the on-screen controls on a phone / tablet.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Ui = require(script.Parent.Ui)

local Hud = {}

local camera = workspace.CurrentCamera
local gui
local f = {}              -- the elements
local server = { hp = 100, maxHp = 100, missiles = 0, flares = 0, wave = 0, enemies = 0 }
local profile = { coins = 0, kills = 0 }
local alertOn = false
local markers = {}
local toastBusy = 0

local function text(parent, name, props)
	local l = Ui.label(parent, "", props)
	l.Name = name
	l.Font = Enum.Font.Code
	l.TextStrokeTransparency = 0.6
	f[name] = l
	return l
end

function Hud.init(remotes, flight)
	gui = Ui.make("ScreenGui", { Name = "DogfightHud", ResetOnSpawn = false, IgnoreGuiInset = true, Enabled = false, DisplayOrder = 5, Parent = Players.LocalPlayer:WaitForChild("PlayerGui") })

	-- left bottom: speed, altitude, throttle
	local left = Ui.make("Frame", { BackgroundTransparency = 1, Position = UDim2.new(0, 16, 1, -150), Size = UDim2.new(0, 230, 0, 140), Parent = gui })
	text(left, "speed", { Position = UDim2.new(0, 0, 0, 0), TextSize = 20, TextColor3 = Ui.Green })
	text(left, "alt", { Position = UDim2.new(0, 0, 0, 26), TextSize = 20, TextColor3 = Ui.Green })
	text(left, "thr", { Position = UDim2.new(0, 0, 0, 52), TextSize = 16, TextColor3 = Ui.Green })
	local bar = Ui.make("Frame", { BackgroundColor3 = Color3.fromRGB(20, 40, 30), BorderSizePixel = 0, Position = UDim2.new(0, 0, 0, 78), Size = UDim2.new(1, -20, 0, 10), Parent = left }, { Ui.corner(4) })
	f.thrFill = Ui.make("Frame", { BackgroundColor3 = Ui.Green, BorderSizePixel = 0, Size = UDim2.new(0.7, 0, 1, 0), Parent = bar }, { Ui.corner(4) })

	-- right bottom: hull and weapons
	local right = Ui.make("Frame", { BackgroundTransparency = 1, Position = UDim2.new(1, -250, 1, -150), Size = UDim2.new(0, 234, 0, 140), Parent = gui })
	text(right, "hp", { Position = UDim2.new(0, 0, 0, 0), TextSize = 18, TextColor3 = Ui.Green, TextXAlignment = Enum.TextXAlignment.Right })
	local hbar = Ui.make("Frame", { BackgroundColor3 = Color3.fromRGB(40, 20, 20), BorderSizePixel = 0, Position = UDim2.new(0, 0, 0, 26), Size = UDim2.new(1, 0, 0, 10), Parent = right }, { Ui.corner(4) })
	f.hpFill = Ui.make("Frame", { BackgroundColor3 = Ui.Green, BorderSizePixel = 0, Size = UDim2.new(1, 0, 1, 0), Parent = hbar }, { Ui.corner(4) })
	text(right, "wpn", { Position = UDim2.new(0, 0, 0, 46), TextSize = 18, TextColor3 = Ui.Amber, TextXAlignment = Enum.TextXAlignment.Right })
	text(right, "gun", { Position = UDim2.new(0, 0, 0, 72), TextSize = 14, TextColor3 = Color3.fromRGB(170, 200, 190), TextXAlignment = Enum.TextXAlignment.Right })

	-- top: coins / wave
	local top = Ui.make("Frame", { BackgroundTransparency = 1, Position = UDim2.new(0, 16, 0, 12), Size = UDim2.new(0, 300, 0, 60), Parent = gui })
	text(top, "coins", { Position = UDim2.new(0, 0, 0, 0), TextSize = 22, TextColor3 = Ui.Amber })
	text(top, "kills", { Position = UDim2.new(0, 0, 0, 26), TextSize = 16, TextColor3 = Color3.fromRGB(200, 215, 210) })
	text(gui, "wave", { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 12), Size = UDim2.new(0, 400, 0, 26), TextSize = 20, TextColor3 = Color3.fromRGB(235, 245, 240), TextXAlignment = Enum.TextXAlignment.Center })

	-- warnings and toasts
	text(gui, "alert", { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0.17, 0), Size = UDim2.new(0, 500, 0, 34), TextSize = 30, TextColor3 = Ui.Red, TextXAlignment = Enum.TextXAlignment.Center, Visible = false })
	text(gui, "warn", { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0.23, 0), Size = UDim2.new(0, 500, 0, 26), TextSize = 22, TextColor3 = Ui.Amber, TextXAlignment = Enum.TextXAlignment.Center })
	text(gui, "toast", { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0.3, 0), Size = UDim2.new(0, 560, 0, 30), TextSize = 22, TextColor3 = Color3.new(1, 1, 1), TextXAlignment = Enum.TextXAlignment.Center, TextTransparency = 1 })

	-- the aim point and the steering dot, the lock box
	f.aim = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Size = UDim2.new(0, 26, 0, 26), BackgroundTransparency = 1, Parent = gui }, { Ui.make("UIStroke", { Color = Ui.Green, Thickness = 2 }), Ui.corner(13) })
	f.dot = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Size = UDim2.new(0, 8, 0, 8), BackgroundColor3 = Ui.Amber, BorderSizePixel = 0, Parent = gui }, { Ui.corner(4) })
	f.lock = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Size = UDim2.new(0, 64, 0, 64), BackgroundTransparency = 1, Visible = false, Parent = gui }, { Ui.make("UIStroke", { Color = Ui.Red, Thickness = 3 }) })
	text(f.lock, "lockText", { Position = UDim2.new(0, 0, 1, 2), Size = UDim2.new(1, 0, 0, 18), TextSize = 14, TextColor3 = Ui.Red, TextXAlignment = Enum.TextXAlignment.Center })

	-- the key help (H)
	f.help = Ui.make("TextLabel", {
		BackgroundColor3 = Ui.Panel, BackgroundTransparency = 0.2, Position = UDim2.new(0, 16, 0, 90), Size = UDim2.new(0, 330, 0, 210), Visible = false,
		TextColor3 = Color3.fromRGB(220, 235, 230), Font = Enum.Font.Code, TextSize = 15, TextXAlignment = Enum.TextXAlignment.Left, TextYAlignment = Enum.TextYAlignment.Top, Parent = gui,
		Text = "Egér: a kurzor irányít (M: ki/be)\nW / S: orr le / fel · A / D: bedöntés\nQ / E: oldalkormány\nShift / Ctrl: gáz · (R / F is)\nSzóköz vagy bal klikk: gépágyú\nX vagy jobb klikk: rakéta (előbb célozz)\nG: flare (rakéta ellen!)\nV: pilótafülke · I: fordított orr\nH: ez a súgó\n\nKontroller: bal pálca, A tűz, X rakéta,\nB flare, Y nézet, R2/L2 gáz",
	}, { Ui.corner(6), Ui.padding(10) })

	UserInputService.InputBegan:Connect(function(input, processed)
		if processed then return end
		if input.KeyCode == Enum.KeyCode.H then f.help.Visible = not f.help.Visible end
	end)

	remotes.Hud.OnClientEvent:Connect(function(d) server = d end)
	remotes.Profile.OnClientEvent:Connect(function(p) profile = p end)
	remotes.MissileAlert.OnClientEvent:Connect(function(on) alertOn = on end)
	remotes.Toast.OnClientEvent:Connect(function(msg, kind) Hud.toast(msg, kind) end)
	remotes.Tracer.OnClientEvent:Connect(function(a, b, c) flight.beam(a, b, c) end)

	if UserInputService.TouchEnabled then Hud.touchControls(flight) end
end

function Hud.setProfile(p) profile = p end

function Hud.show(v: boolean)
	gui.Enabled = v
	alertOn = false
end

function Hud.toast(msg: string, kind: string?)
	local c = kind == "good" and Ui.Green or kind == "warn" and Ui.Amber or kind == "bad" and Ui.Red or Color3.new(1, 1, 1)
	f.toast.Text = msg
	f.toast.TextColor3 = c
	f.toast.TextTransparency = 0
	toastBusy += 1
	local mine = toastBusy
	task.delay(2.6, function()
		if mine == toastBusy then TweenService:Create(f.toast, TweenInfo.new(0.6), { TextTransparency = 1 }):Play() end
	end)
end

-- on a phone: a stick on the left half, buttons on the right
function Hud.touchControls(flight)
	local zone = Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(0.5, 0, 1, 0), Parent = gui })
	local base = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Size = UDim2.new(0, 120, 0, 120), BackgroundColor3 = Color3.new(1, 1, 1), BackgroundTransparency = 0.8, Visible = false, Parent = gui }, { Ui.corner(60) })
	local knob = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0.5, 0), Size = UDim2.new(0, 50, 0, 50), BackgroundColor3 = Ui.Green, BackgroundTransparency = 0.3, Parent = base }, { Ui.corner(25) })
	local origin, id = nil, nil
	zone.InputBegan:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.Touch and not id then
			id = input
			origin = Vector2.new(input.Position.X, input.Position.Y)
			base.Position = UDim2.new(0, origin.X, 0, origin.Y)
			base.Visible = true
			input.Changed:Connect(function()
				if input.UserInputState == Enum.UserInputState.End then
					id = nil
					base.Visible = false
					flight.touch.roll, flight.touch.pitch = 0, 0
				elseif id == input then
					local d = (Vector2.new(input.Position.X, input.Position.Y) - origin) / 60
					if d.Magnitude > 1 then d = d.Unit end
					knob.Position = UDim2.new(0.5, d.X * 60, 0.5, d.Y * 60)
					flight.touch.roll = d.X
					flight.touch.pitch = -d.Y
				end
			end)
		end
	end)
	local function btn(label, anchor, pos, color, down, up)
		local b = Ui.button(gui, label, { AnchorPoint = anchor, Position = pos, Size = UDim2.new(0, 84, 0, 84), BackgroundColor3 = color, TextSize = 18, BackgroundTransparency = 0.25 })
		Ui.corner(42).Parent = b
		b.InputBegan:Connect(function(i) if i.UserInputType == Enum.UserInputType.Touch then down() end end)
		b.InputEnded:Connect(function(i) if i.UserInputType == Enum.UserInputType.Touch and up then up() end end)
		return b
	end
	btn("TŰZ", Vector2.new(1, 1), UDim2.new(1, -20, 1, -20), Ui.Red, function() flight.setFiring(true) end, function() flight.setFiring(false) end)
	btn("RAKÉTA", Vector2.new(1, 1), UDim2.new(1, -116, 1, -60), Ui.Amber, function() flight.fireMissile() end)
	btn("FLARE", Vector2.new(1, 1), UDim2.new(1, -20, 1, -116), Color3.fromRGB(120, 200, 255), function() flight.flare() end)
	btn("GÁZ +", Vector2.new(0, 1), UDim2.new(0, 260, 1, -20), Ui.Green, function() flight.touch.throttle = 1 end, function() flight.touch.throttle = 0 end)
	btn("GÁZ -", Vector2.new(0, 1), UDim2.new(0, 260, 1, -112), Color3.fromRGB(170, 200, 190), function() flight.touch.throttle = -1 end, function() flight.touch.throttle = 0 end)
end

local function screenPoint(world: Vector3)
	local v, on = camera:WorldToViewportPoint(world)
	return Vector2.new(v.X, v.Y), on and v.Z > 0, v.Z
end

function Hud.update(dt: number, fs)
	if not gui or not gui.Enabled then return end
	camera = workspace.CurrentCamera
	local size = camera.ViewportSize
	-- the numbers
	f.speed.Text = string.format("SEB  %d km/h", math.floor((fs.speed or 0) * 0.28 * 3.6))
	f.alt.Text = string.format("MAG  %d m", math.floor((fs.alt or 0) * 0.28))
	f.thr.Text = string.format("GÁZ  %d%%%s", math.floor((fs.throttle or 0) * 100), fs.ab and "  UTÁNÉGETŐ" or "")
	f.thrFill.Size = UDim2.new(fs.throttle or 0, 0, 1, 0)
	f.thrFill.BackgroundColor3 = fs.ab and Ui.Amber or Ui.Green
	local hp, maxHp = server.hp or 100, server.maxHp or 100
	f.hp.Text = string.format("ÉLETERŐ  %d", math.max(0, math.floor(hp)))
	f.hpFill.Size = UDim2.new(math.clamp(hp / maxHp, 0, 1), 0, 1, 0)
	f.hpFill.BackgroundColor3 = hp / maxHp < 0.35 and Ui.Red or Ui.Green
	f.wpn.Text = string.format("RAKÉTA ×%d   FLARE ×%d", server.missiles or 0, server.flares or 0)
	f.gun.Text = "ÁGYÚ ∞"
	f.coins.Text = string.format("%d érme", profile.coins or 0)
	f.kills.Text = string.format("lelőtt: %d", profile.kills or 0)
	f.wave.Text = (server.wave or 0) > 0 and string.format("%d. HULLÁM · ellenség: %d", server.wave, server.enemies or 0) or "Hamarosan jönnek…"

	-- warnings
	f.alert.Visible = alertOn
	if alertOn then
		f.alert.Text = "⚠ RAKÉTA! – G: flare, és fordulj keményen"
		f.alert.TextTransparency = (math.floor(os.clock() * 5) % 2 == 0) and 0 or 0.5
	end
	f.warn.Text = fs.stall and "ELTÖRÉS! – több gázt, süllyeszd az orrot" or fs.edge and "A harcteret elhagyod – visszafordulsz" or ""

	-- the aim point (700 studs ahead of the nose) and the cursor steering dot
	if fs.pos then
		local p, on = screenPoint(fs.pos + fs.look * 700)
		f.aim.Visible = on
		if on then f.aim.Position = UDim2.new(0, p.X, 0, p.Y) end
	end
	f.dot.Visible = fs.mouse == true
	if fs.mouse then
		local m = UserInputService:GetMouseLocation()
		f.dot.Position = UDim2.new(0, m.X, 0, m.Y)
	end

	-- enemy markers and the lock box
	local list = {}
	for _, m in workspace.Enemies:GetChildren() do
		if m:IsA("Model") then table.insert(list, m) end
	end
	for i, m in list do
		local mk = markers[i]
		if not mk then
			mk = Ui.make("TextLabel", { AnchorPoint = Vector2.new(0.5, 0.5), Size = UDim2.new(0, 70, 0, 20), BackgroundTransparency = 1, Font = Enum.Font.Code, TextSize = 14, TextColor3 = Ui.Red, TextStrokeTransparency = 0.5, Parent = gui })
			markers[i] = mk
		end
		local wp = m:GetPivot().Position
		local d = fs.pos and (wp - fs.pos).Magnitude or 0
		local p, on, z = screenPoint(wp)
		local label = string.format("%s%.1f", on and "▼ " or "◆ ", d / 1000)
		if not on then
			-- off screen: on the edge of the screen, towards the enemy
			local dir = p - size / 2
			if z < 0 then dir = -dir end
			if dir.Magnitude < 1 then dir = Vector2.new(0, -1) end
			dir = dir.Unit
			local k = math.min((size.X / 2 - 40) / math.max(math.abs(dir.X), 1e-3), (size.Y / 2 - 40) / math.max(math.abs(dir.Y), 1e-3))
			p = size / 2 + dir * k
		end
		mk.Text = label
		mk.Position = UDim2.new(0, p.X, 0, p.Y)
		mk.Visible = true
	end
	for i = #list + 1, #markers do markers[i].Visible = false end

	local lock = fs.lock
	if lock and lock.Parent then
		local p, on = screenPoint(lock:GetPivot().Position)
		f.lock.Visible = on
		if on then
			f.lock.Position = UDim2.new(0, p.X, 0, p.Y)
			f.lockText.Text = (server.missiles or 0) > 0 and "ZÁR · X" or "NINCS RAKÉTA"
		end
	else
		f.lock.Visible = false
	end
end

return Hud
