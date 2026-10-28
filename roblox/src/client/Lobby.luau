--!nonstrict
-- The hangar screen: a turning preview of your jet and the shop (paint schemes and pilot outfits for coins,
-- coin packs for Robux).  Trying a skin puts it on the preview jet; buying it makes it yours.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Catalog = require(Shared.Catalog)
local JetBuilder = require(Shared.JetBuilder)
local Ui = require(script.Parent.Ui)

local Lobby = {}

local ORIGIN = Vector3.new(30000, 600, 0)
local camera = workspace.CurrentCamera
local remotes, hooks
local gui, shop, listFrame, coinsLabel, msgLabel
local profile = { coins = 0, air = {}, pilot = {} }
local tab, rarity, onlyOwned = "air", "all", false
local previewModel, previewFolder
local tryAir, tryPilot = nil, nil     -- what the preview shows while you look at a skin
local focus = "jet"                   -- "jet" or "pilot": where the camera looks
local angle = 0
local visible = false
local ready = false
local gear = "single"               -- "single" or "twoseat" (the F/A-18F with a rear seat for a team mate)
local gearButtons = {}
local roomLabel = nil
local State = require(script.Parent.State)

local function rebuildPreview()
	if previewModel then previewModel:Destroy() end
	local air = tryAir ~= nil and tryAir or profile.airOn
	local pilot = tryPilot ~= nil and tryPilot or profile.pilotOn
	if air == "" then air = nil end
	if pilot == "" then pilot = nil end
	previewModel = JetBuilder.build(air, pilot, false, gear == "twoseat", nil, profile.jetOn)
	previewModel.PrimaryPart.Anchored = true
	previewModel:PivotTo(CFrame.new(ORIGIN))
	JetBuilder.setFlame(previewModel, 0.4)
	previewModel.Parent = previewFolder
end

local function say(text: string, good: boolean?)
	msgLabel.Text = text
	msgLabel.TextColor3 = good and Ui.Green or Ui.Amber
end

local function swatchFor(skin, isPilot: boolean, parent: Instance)
	local box = Ui.make("Frame", { Size = UDim2.new(1, -12, 0, 56), Position = UDim2.new(0, 6, 0, 6), BackgroundColor3 = JetBuilder.color(isPilot and skin.suit or skin.color), BorderSizePixel = 0, ClipsDescendants = true, Parent = parent }, { Ui.corner(6) })
	if isPilot then
		Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0.4, 0), Size = UDim2.new(0, 34, 0, 34), BackgroundColor3 = JetBuilder.color(skin.helmet), BorderSizePixel = 0, Parent = box }, { Ui.corner(17) })
		Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0.45, 0), Size = UDim2.new(0, 26, 0, 12), BackgroundColor3 = JetBuilder.color(skin.visor), BorderSizePixel = 0, Parent = box }, { Ui.corner(6) })
		Ui.make("Frame", { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, 0), Size = UDim2.new(0, 10, 0.4, 0), BackgroundColor3 = JetBuilder.color(skin.accent), BorderSizePixel = 0, Parent = box })
	elseif skin.pattern then
		local pc = JetBuilder.color(skin.pcolor)
		for i = 0, 5 do
			Ui.make("Frame", { Position = UDim2.new(i / 6, 0, 0, 0), Size = UDim2.new(1 / 12, 0, 1, 0), BackgroundColor3 = pc, BackgroundTransparency = 0.2, BorderSizePixel = 0, Rotation = 0, Parent = box })
		end
	end
	if not isPilot and skin.metal and skin.metal > 0.6 then
		Ui.make("Frame", { Size = UDim2.new(1, 0, 0.4, 0), BackgroundColor3 = Color3.new(1, 1, 1), BackgroundTransparency = 0.7, BorderSizePixel = 0, Parent = box })
	end
end

local function owned(isPilot: boolean, id: string): boolean
	return (isPilot and profile.pilot or profile.air)[id] == true
end
local function worn(isPilot: boolean, id: string): boolean
	return (isPilot and profile.pilotOn or profile.airOn) == id
end

local function card(skin, isPilot: boolean)
	local id = skin.id
	local f = Ui.make("Frame", { BackgroundColor3 = Ui.Panel, BorderSizePixel = 0, Parent = listFrame }, { Ui.corner(8), Ui.make("UIStroke", { Color = Ui.RarityColor[skin.rarity], Thickness = worn(isPilot, id) and 3 or 1 }) })
	swatchFor(skin, isPilot, f)
	Ui.label(f, skin.name, { Position = UDim2.new(0, 8, 0, 68), Size = UDim2.new(1, -16, 0, 18), TextSize = 14, Font = Enum.Font.GothamBold })
	local extra = isPilot and string.format(" · üveg %d%%%s", math.floor((skin.visorT or 1) * 100), skin.mirror and " tükör" or "") or ""
	Ui.label(f, Catalog.Rarity[skin.rarity] .. extra, { Position = UDim2.new(0, 8, 0, 86), Size = UDim2.new(1, -16, 0, 14), TextSize = 12, TextColor3 = Ui.RarityColor[skin.rarity] })
	local isOwned = owned(isPilot, id)
	local label = worn(isPilot, id) and "Viseled" or isOwned and "Felszerel" or (tostring(skin.price) .. " érme")
	local b = Ui.button(f, label, { Position = UDim2.new(0, 8, 0, 106), Size = UDim2.new(1, -16, 0, 30), TextSize = 14,
		BackgroundColor3 = worn(isPilot, id) and Color3.fromRGB(60, 80, 70) or isOwned and Color3.fromRGB(140, 200, 255) or Ui.Amber })
	b.Activated:Connect(function()
		if worn(isPilot, id) then return end
		local ok, msg
		if isOwned then
			ok = (isPilot and remotes.EquipPilot or remotes.EquipAir):InvokeServer(id)
			msg = ok and "Felszerelve" or "Nem sikerült"
		else
			ok, msg = (isPilot and remotes.BuyPilot or remotes.BuyAir):InvokeServer(id)
		end
		say(msg or "", ok)
		if isPilot then tryPilot = nil else tryAir = nil end
	end)
	-- the same skin for Robux (real money, at most 500 Ft: Config.SkinRobux); hidden once it is yours
	if not isOwned then
		local rb = Config.SkinRobux[skin.rarity]
		local huf = math.floor(rb * Config.Money.HufPerRobux + 0.5)
		Ui.button(f, string.format("R$ %d (≈ %d Ft)", rb, huf), { Position = UDim2.new(0, 8, 0, 140), Size = UDim2.new(1, -16, 0, 30), TextSize = 13, BackgroundColor3 = Color3.fromRGB(120, 200, 255) }, function()
			local ok, m = remotes.BuySkinRobux:InvokeServer(isPilot and "pilot" or "air", id)
			say(m or "", ok)
		end)
	end
	-- looking at it: the preview jet wears it
	local look = Ui.make("TextButton", { Text = "", BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 100), ZIndex = 1, Parent = f })
	look.Activated:Connect(function()
		if isPilot then tryPilot, focus = id, "pilot" else tryAir, focus = id, "jet" end
		rebuildPreview()
	end)
end

local function render()
	if not ready then return end
	for _, c in listFrame:GetChildren() do
		if c:IsA("GuiObject") then c:Destroy() end
	end
	coinsLabel.Text = string.format("%d érme", profile.coins or 0)
	if tab == "jet" then
		local have = ReplicatedStorage:FindFirstChild("JetModels")
		local any = false
		for _, j in Config.JetModels do
			local ok = have ~= nil and have:FindFirstChild(j.key) ~= nil
			any = any or ok
			local f = Ui.make("Frame", { BackgroundColor3 = Ui.Panel, BorderSizePixel = 0, Parent = listFrame }, { Ui.corner(8), Ui.make("UIStroke", { Color = profile.jetOn == j.key and Ui.Green or Color3.fromRGB(60, 80, 86), Thickness = profile.jetOn == j.key and 3 or 1 }) })
			Ui.label(f, j.name, { Position = UDim2.new(0, 8, 0, 10), Size = UDim2.new(1, -16, 0, 40), TextSize = 15, Font = Enum.Font.GothamBold, TextWrapped = true })
			Ui.label(f, string.format("hossz %.1f m", j.length), { Position = UDim2.new(0, 8, 0, 56), Size = UDim2.new(1, -16, 0, 16), TextSize = 12, TextColor3 = Color3.fromRGB(150, 170, 165) })
			local label = profile.jetOn == j.key and "Ezzel repülsz" or ok and "Kiválasztom" or "nincs importálva"
			Ui.button(f, label, { Position = UDim2.new(0, 8, 0, 100), Size = UDim2.new(1, -16, 0, 30), TextSize = 13, BackgroundColor3 = ok and Ui.Amber or Color3.fromRGB(70, 80, 84) }, function()
				if ok then
					remotes.EquipJet:InvokeServer(j.key)
				else
					say("Ez a gép még nincs importálva a Studióba (lásd a README-t)", false)
				end
			end)
		end
		if not any then
			Ui.label(listFrame, "Még egy gép sincs importálva: a játék a kockákból épített gépet használja.", { Size = UDim2.new(0, 480, 0, 40), TextWrapped = true })
		end
		return
	end
	if tab == "coins" then
		local any = false
		for i, prod in Config.Products do
			if prod.id ~= 0 then
				any = true
				local f = Ui.make("Frame", { BackgroundColor3 = Ui.Panel, BorderSizePixel = 0, Parent = listFrame }, { Ui.corner(8) })
				Ui.label(f, prod.label, { Position = UDim2.new(0, 8, 0, 10), Size = UDim2.new(1, -16, 0, 22), TextSize = 17, Font = Enum.Font.GothamBold })
				Ui.label(f, prod.coins .. " érme", { Position = UDim2.new(0, 8, 0, 42), Size = UDim2.new(1, -16, 0, 30), TextSize = 24, TextColor3 = Ui.Amber, Font = Enum.Font.GothamBold })
				Ui.button(f, "Vásárlás (Robux)", { Position = UDim2.new(0, 8, 1, -42), Size = UDim2.new(1, -16, 0, 34), TextSize = 14 }, function() remotes.BuyProduct:InvokeServer(i) end)
			end
		end
		if Config.DoubleCoinsPass ~= 0 then
			any = true
			local f = Ui.make("Frame", { BackgroundColor3 = Ui.Panel, BorderSizePixel = 0, Parent = listFrame }, { Ui.corner(8), Ui.make("UIStroke", { Color = Ui.Amber, Thickness = 2 }) })
			Ui.label(f, "Dupla érme", { Position = UDim2.new(0, 8, 0, 10), Size = UDim2.new(1, -16, 0, 22), TextSize = 17, Font = Enum.Font.GothamBold })
			Ui.label(f, "mindent kétszer annyit érsz", { Position = UDim2.new(0, 8, 0, 40), Size = UDim2.new(1, -16, 0, 40), TextSize = 14, TextWrapped = true })
			Ui.button(f, profile.double and "Megvan" or "Vásárlás (Robux)", { Position = UDim2.new(0, 8, 1, -42), Size = UDim2.new(1, -16, 0, 34), TextSize = 14 }, function() if not profile.double then remotes.BuyPass:InvokeServer() end end)
		end
		if not any then
			Ui.label(listFrame, "A Robux-csomagok hamarosan itt lesznek.", { Size = UDim2.new(0, 300, 0, 40), TextWrapped = true })
		end
		return
	end
	local isPilot = tab == "pilot"
	local list = isPilot and Catalog.Pilot or Catalog.Air
	for _, skin in list do
		if (rarity == "all" or skin.rarity == rarity) and (not onlyOwned or owned(isPilot, skin.id)) then card(skin, isPilot) end
	end
end

function Lobby.paintGear()
	for id, b in gearButtons do
		b.BackgroundColor3 = id == gear and Ui.Amber or Color3.fromRGB(70, 86, 92)
		b.TextColor3 = id == gear and Color3.fromRGB(16, 22, 20) or Color3.new(1, 1, 1)
	end
end

-- the line under the coins: which room you are in
function Lobby.setRoom(room)
	if not roomLabel then return end
	if room then
		roomLabel.Text = string.format("Szoba: %s · %d/%d fő · %s", room.name, #room.members, room.max, room.mode == "pvp" and ("csapatharc, te: " .. (State.team == "A" and "KÉK" or "PIROS")) or "együtt az ellenség ellen")
	else
		roomLabel.Text = "Nem vagy szobában – az Indulás egy nyilvános szobába tesz."
	end
end

function Lobby.setProfile(p)
	profile = p
	if ready then
		tryAir, tryPilot = nil, nil
		rebuildPreview()
		render()
	end
end

function Lobby.init(r, h)
	remotes, hooks = r, h
	camera = workspace.CurrentCamera
	previewFolder = Ui.make("Folder", { Name = "Preview", Parent = workspace })
	gui = Ui.make("ScreenGui", { Name = "DogfightLobby", ResetOnSpawn = false, IgnoreGuiInset = true, DisplayOrder = 10, Parent = Players.LocalPlayer:WaitForChild("PlayerGui") })

	Ui.label(gui, "DOGFIGHT PLUS", { Position = UDim2.new(0, 28, 0, 22), Size = UDim2.new(0, 500, 0, 54), TextSize = 46, Font = Enum.Font.GothamBlack, TextColor3 = Ui.Green })
	Ui.label(gui, "Légiharc a barátaiddal – lődd le a hullámokat, gyűjts érméket, öltöztesd a gépedet és a pilótádat.", { Position = UDim2.new(0, 30, 0, 78), Size = UDim2.new(0, 520, 0, 40), TextSize = 16, TextWrapped = true, TextColor3 = Color3.fromRGB(200, 215, 210) })
	coinsLabel = Ui.label(gui, "", { Position = UDim2.new(0, 30, 0, 126), Size = UDim2.new(0, 300, 0, 30), TextSize = 24, TextColor3 = Ui.Amber, Font = Enum.Font.GothamBold })
	roomLabel = Ui.label(gui, "", { Position = UDim2.new(0, 30, 0, 156), Size = UDim2.new(0, 520, 0, 20), TextSize = 15, TextColor3 = Color3.fromRGB(190, 210, 205) })
	Ui.button(gui, "▶ INDULÁS", { Position = UDim2.new(0, 30, 0, 184), Size = UDim2.new(0, 220, 0, 56), TextSize = 24, BackgroundColor3 = Ui.Green }, function() hooks.onPlay(gear) end)
	local function gearBtn(id, label, x)
		local b = Ui.button(gui, label, { Position = UDim2.new(0, x, 0, 248), Size = UDim2.new(0, 150, 0, 34), TextSize = 14 })
		gearButtons[id] = b
		b.Activated:Connect(function() gear = id; Lobby.paintGear(); rebuildPreview() end)
	end
	gearBtn("single", "Együléses", 30)
	gearBtn("twoseat", "Kétüléses (F/A-18F)", 186)
	Lobby.paintGear()
	Ui.button(gui, "👥 Szobák / Csapat", { Position = UDim2.new(0, 30, 0, 290), Size = UDim2.new(0, 220, 0, 44), TextSize = 18, BackgroundColor3 = Color3.fromRGB(150, 210, 255) }, function() hooks.onRooms() end)
	local hang = Ui.button(gui, "🛒 Hangár / Shop", { Position = UDim2.new(0, 30, 0, 342), Size = UDim2.new(0, 220, 0, 44), TextSize = 18 }, function() shop.Visible = not shop.Visible end)
	hang.Name = "HangarButton"
	Ui.label(gui, "Irányítás: egér + W/S/A/D · Szóköz tűz · X rakéta · G flare · H súgó (repülés közben)", { Position = UDim2.new(0, 30, 1, -40), Size = UDim2.new(0, 700, 0, 24), TextSize = 14, TextColor3 = Color3.fromRGB(170, 190, 185) })

	-- the shop panel on the right
	shop = Ui.make("Frame", { AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, -20, 0.5, 0), Size = UDim2.new(0, 560, 0.88, 0), BackgroundColor3 = Color3.fromRGB(14, 20, 24), BackgroundTransparency = 0.08, Visible = true, Parent = gui }, { Ui.corner(10), Ui.padding(12) })
	local tabs = Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 38), Parent = shop }, { Ui.make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 8) }) })
	local function tabBtn(id, label)
		Ui.button(tabs, label, { Size = UDim2.new(0, 150, 0, 34), TextSize = 15, BackgroundColor3 = Color3.fromRGB(40, 56, 62), TextColor3 = Color3.new(1, 1, 1) }, function()
			tab = id
			tryAir, tryPilot = nil, nil
			focus = id == "pilot" and "pilot" or "jet"
			rebuildPreview()
			render()
		end)
	end
	tabBtn("air", "Gép festése (" .. #Catalog.Air .. ")")
	tabBtn("pilot", "Pilóta (" .. #Catalog.Pilot .. ")")
	tabBtn("jet", "Gép típusa")
	tabBtn("coins", "Érmék")
	local chips = Ui.make("Frame", { BackgroundTransparency = 1, Position = UDim2.new(0, 0, 0, 44), Size = UDim2.new(1, 0, 0, 30), Parent = shop }, { Ui.make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 6) }) })
	local function chip(id, label)
		Ui.button(chips, label, { Size = UDim2.new(0, 92, 0, 28), TextSize = 13, BackgroundColor3 = Ui.RarityColor[id] or Color3.fromRGB(200, 210, 215) }, function() rarity = id; render() end)
	end
	chip("all", "Mind"); chip("C", "Gyakori"); chip("R", "Ritka"); chip("E", "Epikus"); chip("L", "Legendás")
	Ui.button(chips, "Csak a megvettek", { Size = UDim2.new(0, 120, 0, 28), TextSize = 13, BackgroundColor3 = Color3.fromRGB(80, 96, 100), TextColor3 = Color3.new(1, 1, 1) }, function() onlyOwned = not onlyOwned; render() end)
	msgLabel = Ui.label(shop, "", { Position = UDim2.new(0, 0, 0, 78), Size = UDim2.new(1, 0, 0, 20), TextSize = 15 })
	listFrame = Ui.make("ScrollingFrame", {
		Position = UDim2.new(0, 0, 0, 102), Size = UDim2.new(1, 0, 1, -102), BackgroundTransparency = 1, BorderSizePixel = 0, ScrollBarThickness = 8,
		CanvasSize = UDim2.new(0, 0, 0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y, Parent = shop,
	}, { Ui.make("UIGridLayout", { CellSize = UDim2.new(0, 160, 0, 178), CellPadding = UDim2.new(0, 8, 0, 8), SortOrder = Enum.SortOrder.LayoutOrder }) })
	ready = true

	-- the camera circles the preview jet while the lobby is up
	RunService:BindToRenderStep("DogfightLobbyCam", Enum.RenderPriority.Camera.Value + 1, function(dt)
		if not visible then return end
		angle += dt * 0.35
		camera.CameraType = Enum.CameraType.Scriptable
		if focus == "pilot" then
			local c = ORIGIN + Vector3.new(0, 1.7, -2.8)
			local pos = c + Vector3.new(math.cos(angle) * 3.6, 0.9, math.sin(angle) * 3.6)
			camera.CFrame = CFrame.lookAt(pos, c)
			camera.FieldOfView = 55
		else
			local pos = ORIGIN + Vector3.new(math.cos(angle) * 46, 9 + math.sin(angle * 0.7) * 5, math.sin(angle) * 46)
			camera.CFrame = CFrame.lookAt(pos, ORIGIN)
			camera.FieldOfView = 55
		end
	end)
end

function Lobby.show(v: boolean)
	visible = v
	gui.Enabled = v
	if v then
		camera = workspace.CurrentCamera
		tryAir, tryPilot = nil, nil
		focus = "jet"
		rebuildPreview()
		render()
	end
end

return Lobby
