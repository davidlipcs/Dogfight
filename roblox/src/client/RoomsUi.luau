--!nonstrict
-- The rooms screen: your room (members, teams, slots, the open rear seats), a quick start, a new room and the list.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)
local Ui = require(script.Parent.Ui)
local State = require(script.Parent.State)

local RoomsUi = {}

local remotes, gui, body, msg
local open = false
local form = { name = "", mode = "coop", extra = 3, private = false }
local list = {}
local listTimer = 0
local codeText = ""
local onSeat = nil          -- called after a rear seat is taken
local MAX = Config.Rooms.MaxPlayers

local function say(text: string?, good: boolean?)
	if msg then
		msg.Text = text or ""
		msg.TextColor3 = good and Ui.Green or Ui.Amber
	end
end

local function section(title: string)
	local f = Ui.make("Frame", { BackgroundColor3 = Color3.fromRGB(24, 34, 40), BorderSizePixel = 0, Size = UDim2.new(1, -12, 0, 10), AutomaticSize = Enum.AutomaticSize.Y, Parent = body }, {
		Ui.corner(8), Ui.padding(10), Ui.make("UIListLayout", { Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder }),
	})
	Ui.label(f, title, { Size = UDim2.new(1, 0, 0, 22), TextSize = 18, Font = Enum.Font.GothamBold, TextColor3 = Ui.Amber })
	return f
end

local function row(parent: Instance, height: number?)
	return Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, height or 34), Parent = parent }, {
		Ui.make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 8), VerticalAlignment = Enum.VerticalAlignment.Center }),
	})
end

local function modeName(mode: string): string
	return mode == "pvp" and "Csapatharc (két csapat egymás ellen)" or "Együtt az ellenség ellen"
end

local render

local function myRoomSection()
	local r = State.room
	local s = section(r and ("A szobád: " .. r.name) or "Nem vagy szobában")
	if not r then
		Ui.label(s, "Nyiss egy szobát, vagy lépj be egybe – vagy nyomj a Gyors játékra.", { Size = UDim2.new(1, 0, 0, 20), TextSize = 14, TextWrapped = true })
		return
	end
	local me = Players.LocalPlayer.UserId
	local isHost = r.host == me
	Ui.label(s, string.format("%s · %d/%d fő%s", modeName(r.mode), #r.members, r.max, r.private and " · privát" or ""), { Size = UDim2.new(1, 0, 0, 20), TextSize = 14 })
	if r.private and r.code then
		Ui.label(s, "Belépési kód: " .. r.code .. "  (ezt add meg a barátaidnak)", { Size = UDim2.new(1, 0, 0, 22), TextSize = 18, TextColor3 = Ui.Green, Font = Enum.Font.GothamBold })
	end
	-- the slots: only the room's opener changes them
	if isHost then
		local rw = row(s)
		Ui.label(rw, "Még ennyien jöhetnek be:", { Size = UDim2.new(0, 190, 0, 28), TextSize = 14 })
		Ui.button(rw, "−", { Size = UDim2.new(0, 34, 0, 28), TextSize = 20 }, function() remotes.SetSlots:InvokeServer(r.max - 2) end)
		Ui.label(rw, tostring(r.max - 1), { Size = UDim2.new(0, 30, 0, 28), TextSize = 18, TextXAlignment = Enum.TextXAlignment.Center, Font = Enum.Font.GothamBold })
		Ui.button(rw, "+", { Size = UDim2.new(0, 34, 0, 28), TextSize = 20 }, function() remotes.SetSlots:InvokeServer(r.max) end)
		Ui.label(rw, "(összesen legfeljebb " .. MAX .. " fő)", { Size = UDim2.new(0, 190, 0, 28), TextSize = 12, TextColor3 = Color3.fromRGB(150, 170, 165) })
	end
	-- the members, by team in a team fight
	if r.mode == "pvp" then
		local cols = row(s, 10)
		cols.AutomaticSize = Enum.AutomaticSize.Y
		cols.Size = UDim2.new(1, 0, 0, 10)
		cols:FindFirstChildOfClass("UIListLayout").VerticalAlignment = Enum.VerticalAlignment.Top
		for _, t in { "A", "B" } do
			local c = Ui.make("Frame", { BackgroundColor3 = t == "A" and Color3.fromRGB(20, 40, 70) or Color3.fromRGB(70, 28, 28), BorderSizePixel = 0, Size = UDim2.new(0.5, -6, 0, 10), AutomaticSize = Enum.AutomaticSize.Y, Parent = cols }, {
				Ui.corner(6), Ui.padding(8), Ui.make("UIListLayout", { Padding = UDim.new(0, 3) }),
			})
			local n = 0
			for _, m in r.members do if m.team == t then n += 1 end end
			Ui.label(c, (t == "A" and "KÉK" or "PIROS") .. " csapat · " .. n .. " fő · pont: " .. (r.score[t] or 0), { Size = UDim2.new(1, 0, 0, 20), TextSize = 15, Font = Enum.Font.GothamBold })
			for _, m in r.members do
				if m.team == t then Ui.label(c, (m.host and "★ " or "") .. m.name .. (m.userId == me and "  (te)" or ""), { Size = UDim2.new(1, 0, 0, 18), TextSize = 14 }) end
			end
			if State.team ~= t then
				Ui.button(c, "Átlépek ide", { Size = UDim2.new(1, 0, 0, 28), TextSize = 14, BackgroundColor3 = Ui.Green }, function()
					local ok, m2 = remotes.SetTeam:InvokeServer(t)
					if not ok then say(m2 or "Nem sikerült", false) end
				end)
			else
				Ui.label(c, "← itt vagy", { Size = UDim2.new(1, 0, 0, 22), TextSize = 13, TextColor3 = Ui.Green })
			end
		end
	else
		for _, m in r.members do
			Ui.label(s, (m.host and "★ " or "• ") .. m.name .. (m.userId == me and "  (te)" or ""), { Size = UDim2.new(1, 0, 0, 18), TextSize = 14 })
		end
	end
	-- the open rear seats of two-seat jets of my team
	for _, st in r.seats do
		if st.userId ~= me and st.team == State.team then
			local rw = row(s)
			Ui.label(rw, st.name .. " kétüléses gépének hátsó ülése szabad", { Size = UDim2.new(0, 330, 0, 28), TextSize = 14 })
			Ui.button(rw, "Beülök", { Size = UDim2.new(0, 110, 0, 28), TextSize = 14, BackgroundColor3 = Ui.Green }, function()
				local ok, m2 = remotes.JoinSeat:InvokeServer(st.userId)
				say(m2, ok)
				if ok and onSeat then onSeat() end
			end)
		end
	end
	Ui.button(s, "Kilépek a szobából", { Size = UDim2.new(0, 190, 0, 30), TextSize = 14, BackgroundColor3 = Color3.fromRGB(200, 120, 110) }, function()
		remotes.LeaveRoom:InvokeServer()
	end)
end

local function createSection()
	local s = section("Új szoba nyitása")
	local rw = row(s)
	Ui.label(rw, "Név:", { Size = UDim2.new(0, 50, 0, 30), TextSize = 14 })
	local box = Ui.make("TextBox", { Size = UDim2.new(0, 260, 0, 30), BackgroundColor3 = Color3.fromRGB(38, 50, 56), TextColor3 = Color3.new(1, 1, 1), Font = Enum.Font.Gotham, TextSize = 15,
		PlaceholderText = "pl. A mi hangárunk", Text = form.name, ClearTextOnFocus = false, Parent = rw }, { Ui.corner(5) })
	box.FocusLost:Connect(function() form.name = string.sub(box.Text, 1, Config.Rooms.NameMax) end)
	local m = row(s)
	Ui.label(m, "Mód:", { Size = UDim2.new(0, 50, 0, 30), TextSize = 14 })
	for _, md in { "coop", "pvp" } do
		Ui.button(m, md == "pvp" and "Csapatharc" or "Együtt (AI)", { Size = UDim2.new(0, 130, 0, 30), TextSize = 14,
			BackgroundColor3 = form.mode == md and Ui.Amber or Color3.fromRGB(70, 86, 92), TextColor3 = form.mode == md and Color3.fromRGB(16, 22, 20) or Color3.new(1, 1, 1) }, function() form.mode = md; render() end)
	end
	local x = row(s)
	Ui.label(x, "Még ennyien jöhetnek be:", { Size = UDim2.new(0, 190, 0, 30), TextSize = 14 })
	Ui.button(x, "−", { Size = UDim2.new(0, 34, 0, 30), TextSize = 20 }, function() form.extra = math.max(0, form.extra - 1); render() end)
	Ui.label(x, tostring(form.extra), { Size = UDim2.new(0, 34, 0, 30), TextSize = 18, TextXAlignment = Enum.TextXAlignment.Center, Font = Enum.Font.GothamBold })
	Ui.button(x, "+", { Size = UDim2.new(0, 34, 0, 30), TextSize = 20 }, function() form.extra = math.min(MAX - 1, form.extra + 1); render() end)
	Ui.label(x, "(összesen " .. (form.extra + 1) .. ", legfeljebb " .. MAX .. ")", { Size = UDim2.new(0, 190, 0, 30), TextSize = 12, TextColor3 = Color3.fromRGB(150, 170, 165) })
	local p = row(s)
	Ui.button(p, form.private and "☑ Privát (kóddal lehet belépni)" or "☐ Privát (kóddal lehet belépni)", { Size = UDim2.new(0, 300, 0, 30), TextSize = 14,
		BackgroundColor3 = form.private and Ui.Green or Color3.fromRGB(70, 86, 92), TextColor3 = form.private and Color3.fromRGB(16, 22, 20) or Color3.new(1, 1, 1) }, function() form.private = not form.private; render() end)
	Ui.button(s, "Szoba megnyitása", { Size = UDim2.new(0, 220, 0, 38), TextSize = 16, BackgroundColor3 = Ui.Green }, function()
		local ok, id = remotes.CreateRoom:InvokeServer(form.name, form.mode, form.extra, form.private)
		say(ok and "Szoba megnyitva" or "Nem sikerült", ok)
	end)
end

local function joinSection()
	local s = section("Csatlakozás")
	Ui.button(s, "⚡ Gyors játék (együtt, bárkivel)", { Size = UDim2.new(0, 300, 0, 38), TextSize = 16 }, function()
		local ok, m = remotes.QuickPlay:InvokeServer()
		say(ok and "Bent vagy" or tostring(m), ok)
	end)
	local rw = row(s)
	Ui.label(rw, "Privát szoba kódja:", { Size = UDim2.new(0, 160, 0, 30), TextSize = 14 })
	local box = Ui.make("TextBox", { Size = UDim2.new(0, 90, 0, 30), BackgroundColor3 = Color3.fromRGB(38, 50, 56), TextColor3 = Color3.new(1, 1, 1), Font = Enum.Font.Code, TextSize = 18,
		PlaceholderText = "0000", Text = codeText, ClearTextOnFocus = false, Parent = rw }, { Ui.corner(5) })
	box.FocusLost:Connect(function() codeText = box.Text end)
	Ui.button(rw, "Belépek", { Size = UDim2.new(0, 100, 0, 30), TextSize = 14 }, function()
		local ok, m = remotes.JoinRoom:InvokeServer(box.Text)
		say(m, ok)
	end)
	Ui.label(s, "Nyilvános szobák:", { Size = UDim2.new(1, 0, 0, 20), TextSize = 14, TextColor3 = Ui.Amber })
	if #list == 0 then
		Ui.label(s, "Most nincs nyitott szoba.", { Size = UDim2.new(1, 0, 0, 20), TextSize = 14, TextColor3 = Color3.fromRGB(150, 170, 165) })
	end
	for _, r in list do
		local line = row(s)
		Ui.label(line, string.format("%s · %s · %d/%d", r.name, r.mode == "pvp" and "csapatharc" or "együtt", r.count, r.max), { Size = UDim2.new(0, 360, 0, 28), TextSize = 14 })
		Ui.button(line, r.count >= r.max and "Tele" or "Belépek", { Size = UDim2.new(0, 100, 0, 28), TextSize = 14 }, function()
			local ok, m = remotes.JoinRoom:InvokeServer(r.id)
			say(m, ok)
		end)
	end
end

render = function()
	if not body then return end
	for _, c in body:GetChildren() do
		if c:IsA("GuiObject") then c:Destroy() end
	end
	myRoomSection()
	joinSection()
	createSection()
end

local function refreshList()
	local ok, l = pcall(function() return remotes.ListRooms:InvokeServer() end)
	if ok and typeof(l) == "table" then list = l end
	if open then render() end
end

function RoomsUi.init(r, hooks)
	remotes = r
	onSeat = hooks and hooks.onSeat
	gui = Ui.make("ScreenGui", { Name = "DogfightRooms", ResetOnSpawn = false, IgnoreGuiInset = true, DisplayOrder = 20, Enabled = false, Parent = Players.LocalPlayer:WaitForChild("PlayerGui") })
	local panel = Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0.5, 0), Size = UDim2.new(0, 700, 0.9, 0), BackgroundColor3 = Color3.fromRGB(14, 20, 24), Parent = gui }, { Ui.corner(10), Ui.padding(12) })
	Ui.label(panel, "Hangár-csoportok (szobák)", { Size = UDim2.new(1, -120, 0, 30), TextSize = 22, Font = Enum.Font.GothamBold, TextColor3 = Ui.Green })
	Ui.button(panel, "Bezár", { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, 0), Size = UDim2.new(0, 90, 0, 30), TextSize = 14 }, function() RoomsUi.show(false) end)
	msg = Ui.label(panel, "", { Position = UDim2.new(0, 0, 0, 34), Size = UDim2.new(1, 0, 0, 20), TextSize = 15 })
	body = Ui.make("ScrollingFrame", { Position = UDim2.new(0, 0, 0, 58), Size = UDim2.new(1, 0, 1, -58), BackgroundTransparency = 1, BorderSizePixel = 0, ScrollBarThickness = 8,
		CanvasSize = UDim2.new(0, 0, 0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y, Parent = panel }, { Ui.make("UIListLayout", { Padding = UDim.new(0, 8), SortOrder = Enum.SortOrder.LayoutOrder }) })
	State.onChange(function() if open then render() end end)
	task.spawn(function()
		while true do
			task.wait(3)
			if open then refreshList() end
		end
	end)
end

function RoomsUi.show(v: boolean)
	open = v
	gui.Enabled = v
	if v then
		say("")
		task.spawn(refreshList)
		render()
	end
end

function RoomsUi.toggle() RoomsUi.show(not open) end

return RoomsUi
