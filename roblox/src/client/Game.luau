--!nonstrict
-- The game on the client: the port of the Game class of web/js/game.js.  The match (shared/game/Match.luau) runs here, on the player's
-- own machine, with the same flight model, weapons and AI as the browser game; this module feeds it the controls (Controls.luau),
-- steers the camera (Camera.luau), draws the match (View.luau) and the HUD (GuiCanvas + Hud.luau) and handles the pause, the
-- ejection, the missile / kill camera and the keys that are not flying.  The server only keeps the save (coins, skins) and the rooms.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local IslandData = require(Shared.IslandData)
local JetInfo = require(Shared.JetInfo)
local SimTerrain = require(Shared.sim.SimTerrain)
local SimMath = require(Shared.sim.SimMath)
local Specs = require(Shared.sim.Specs)
local Match = require(Shared.game.Match)
local Career = require(Shared.game.Career)
local Camera = require(Shared.game.Camera)
local Controls = require(Shared.game.Controls)
local HudLogic = require(Shared.game.Hud)

local GuiCanvas = require(script.Parent.GuiCanvas)
local DeviceInput = require(script.Parent.DeviceInput)
local View = require(script.Parent.View)
local Env = require(script.Parent.Env)
local Sounds = require(script.Parent.Sounds)
local MfdView = require(script.Parent.MfdView)
local TutorialUi = require(script.Parent.TutorialUi)
local RadioUi = require(script.Parent.RadioUi)
local State = require(script.Parent.State)
local Net = require(Shared.game.Net)

local V, norm, copy, sub, len = SimMath.V, SimMath.norm, SimMath.copy, SimMath.sub, SimMath.len

local Game = {}
Game.active = false
Game.paused = false
Game.onEnd = nil                     -- called when the match is left for the menu
Game.settings = { aim = 60, stick = 60, invert = false, fov = 70, tod = "day" }

local player = Players.LocalPlayer
local remotes, profile
local terrain, terrainReady = nil, false
local career
local canvas, input
local match, cam, view, hud
local conn
local pendingEarn, earnTimer, saveTimer = 0, 0, 0
local missileCam, followM, followEnd, followLast = false, nil, 0, nil
local bt = nil
local pauseGui
local session, netQueue, netConn, netTimer
local tutUi
local sounds
local mfdView
local radioUi

function Game.init(r)
	remotes = r
end

function Game.setProfile(p)
	profile = p
	if not career then career = Career.new(p and p.career or nil, function(data)
		if remotes and remotes.SaveCareer then remotes.SaveCareer:FireServer(data) end
	end) end
end

-- the island's height grid takes a moment to decode: do it while the menu is open
function Game.preload()
	if terrain or terrainReady then return end
	task.spawn(function()
		terrain = SimTerrain.new(IslandData.load())
		terrainReady = true
	end)
end
function Game.ready() return terrainReady end

local function makeHangar()
	return {
		pilotSkin = profile and profile.pilotOn or nil,
		skin = profile and profile.airOn or nil,
		modOn = function() return false end,
		upgraded = function(_, spec) return spec end,
		earn = function(_, n) pendingEarn += n end,
		credits = function() return (profile and profile.coins or 0) + pendingEarn end,
	}
end

-- ------------------------------------------------------------------ pause screen
local function buildPauseGui()
	local gui = Instance.new("ScreenGui")
	gui.Name = "PauseGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 20
	gui.Enabled = false
	gui.Parent = player:WaitForChild("PlayerGui")
	local back = Instance.new("Frame")
	back.Size = UDim2.fromScale(1, 1)
	back.BackgroundColor3 = Color3.fromRGB(4, 10, 14)
	back.BackgroundTransparency = 0.45
	back.BorderSizePixel = 0
	back.Parent = gui
	local box = Instance.new("Frame")
	box.AnchorPoint = Vector2.new(0.5, 0.5)
	box.Position = UDim2.fromScale(0.5, 0.5)
	box.Size = UDim2.fromOffset(460, 330)
	box.BackgroundColor3 = Color3.fromRGB(18, 26, 30)
	box.BorderSizePixel = 0
	box.Parent = back
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, 10)
	c.Parent = box
	local title = Instance.new("TextLabel")
	title.BackgroundTransparency = 1
	title.Size = UDim2.new(1, 0, 0, 50)
	title.Position = UDim2.fromOffset(0, 10)
	title.Font = Enum.Font.Oswald
	title.Text = "SZÜNET"
	title.TextColor3 = Color3.fromRGB(255, 200, 64)
	title.TextSize = 36
	title.Parent = box
	local stats = Instance.new("TextLabel")
	stats.Name = "Stats"
	stats.BackgroundTransparency = 1
	stats.Size = UDim2.new(1, -40, 0, 40)
	stats.Position = UDim2.fromOffset(20, 62)
	stats.Font = Enum.Font.RobotoMono
	stats.TextSize = 15
	stats.TextColor3 = Color3.fromRGB(210, 225, 215)
	stats.TextWrapped = true
	stats.Text = ""
	stats.Parent = box
	local function button(text, y, fn)
		local b = Instance.new("TextButton")
		b.Size = UDim2.new(1, -60, 0, 44)
		b.Position = UDim2.fromOffset(30, y)
		b.BackgroundColor3 = Color3.fromRGB(255, 200, 64)
		b.TextColor3 = Color3.fromRGB(16, 22, 20)
		b.Font = Enum.Font.GothamBold
		b.TextSize = 18
		b.Text = text
		b.AutoButtonColor = true
		b.Parent = box
		local cc = Instance.new("UICorner")
		cc.CornerRadius = UDim.new(0, 6)
		cc.Parent = b
		b.Activated:Connect(fn)
		return b
	end
	button("Folytatás (P)", 112, function() Game.resume() end)
	button("Súgó (H)", 166, function() Game.toggleHelp() end)
	button("Főmenü – vége a játéknak", 220, function() Game.stop() end)
	local hint = Instance.new("TextLabel")
	hint.BackgroundTransparency = 1
	hint.Size = UDim2.new(1, -40, 0, 40)
	hint.Position = UDim2.fromOffset(20, 276)
	hint.Font = Enum.Font.Gotham
	hint.TextSize = 13
	hint.TextColor3 = Color3.fromRGB(150, 170, 160)
	hint.Text = "Az Esc a Roblox menüjét is megnyitja – ugyanúgy folytathatod."
	hint.Parent = box
	return gui
end

local HELP = {
	"IRÁNYÍTÁS",
	"Egér: célkör – a gép orra oda áll  ·  kabinnézetben (V) az egér a botkormány",
	"W/S: orr le/fel  ·  A/D: bedöntés  ·  Q/E: oldalkormány  ·  Shift/Z: gáz (Shift másodszor: utánégető)",
	"Bal egérgomb: gépágyú  ·  Space: rakéta  ·  X: flare/chaff  ·  B: fékszárny  ·  G: futómű",
	"T: radar lock  ·  Y: következő cél  ·  F: hőkereső lock  ·  R: radar  ·  1/2: AIM-9M / AIM-120A  ·  görgő: fegyverváltás",
	"C vagy jobb egérgomb: körülnézés  ·  V: kabin  ·  N: kijelzők  ·  U: rakétakamera  ·  M: jelölők  ·  középső gomb: zoom",
	"Tab: extrém mód (F-16, F-15 ACTIVE)  ·  Ctrl+E kétszer: katapult  ·  Enter: újraéledés  ·  P: szünet",
	"Kontroller: bal kar = repülés, jobb kar = célkör, R2/L2 = gáz, R1 = ágyú, A = rakéta, L1 = flare",
}
local helpGui
local function buildHelp()
	local gui = Instance.new("ScreenGui")
	gui.Name = "HelpGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 25
	gui.Enabled = false
	gui.Parent = player:WaitForChild("PlayerGui")
	local box = Instance.new("TextLabel")
	box.AnchorPoint = Vector2.new(0.5, 0.5)
	box.Position = UDim2.fromScale(0.5, 0.5)
	box.Size = UDim2.fromOffset(900, 360)
	box.BackgroundColor3 = Color3.fromRGB(10, 18, 22)
	box.BackgroundTransparency = 0.1
	box.TextColor3 = Color3.fromRGB(215, 230, 220)
	box.Font = Enum.Font.RobotoMono
	box.TextSize = 15
	box.TextWrapped = true
	box.TextXAlignment = Enum.TextXAlignment.Left
	box.TextYAlignment = Enum.TextYAlignment.Top
	box.Text = table.concat(HELP, "\n\n")
	box.Parent = gui
	local pad = Instance.new("UIPadding")
	pad.PaddingTop, pad.PaddingLeft, pad.PaddingRight = UDim.new(0, 20), UDim.new(0, 24), UDim.new(0, 24)
	pad.Parent = box
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, 10)
	c.Parent = box
	return gui
end

function Game.toggleHelp()
	if not helpGui then helpGui = buildHelp() end
	helpGui.Enabled = not helpGui.Enabled
	if helpGui.Enabled and not Game.paused then Game.pause(true) end
end

-- ------------------------------------------------------------------ pause / resume
function Game.pause(silent)
	if not match or Game.paused then return end
	Game.paused = true
	match.state.paused = true
	input:setEnabled(false)
	if not pauseGui then pauseGui = buildPauseGui() end
	local st = match.state
	pauseGui.Frame.Frame.Stats.Text = string.format("%d. hullám · %d pont · lelőve %d · halál %d%s", st.wave, st.score, st.kills, st.deaths, st.streak > 1 and (" · sorozat " .. st.streak) or "")
	pauseGui.Enabled = not silent
end
function Game.resume()
	if not match then return end
	Game.paused = false
	match.state.paused = false
	if pauseGui then pauseGui.Enabled = false end
	if helpGui then helpGui.Enabled = false end
	input:setEnabled(true)
	input:takeDelta()
end

-- ------------------------------------------------------------------ keys
local function onKey(k)
	if not match then return end
	if k == "Escape" then
		if Game.paused then Game.resume() else Game.pause() end
		return
	end
	if k == "p" then
		if Game.paused then Game.resume() else Game.pause() end
		return
	end
	if k == "h" or k == "F1" then Game.toggleHelp(); return end
	if Game.paused then return end
	local p = match.player
	if k == "Enter" then
		if match.tutorial then match.tutorial:enter() else match:respawn(); if cam then cam:reset(match.player) end end
		return
	end
	if k == "i" then if radioUi then radioUi:toggle() end; return end
	if k == "m" then hud.markers = not hud.markers; return end
	if k == "eject" then match:ejectHandle(); return end
	if k == "u" then
		missileCam, followM = not missileCam, nil
		hud:message(missileCam and "RAKÉTAKAMERA BE - a kilőtt rakétát követi (U = ki)" or "RAKÉTAKAMERA KI", "info", 2, "mcam")
		return
	end
	if k == "j" or k == "k" or k == "l" then
		local page = mfdView and mfdView:cycle(({ j = "left", k = "right", l = "center" })[k])
		if page then hud:message("KIJELZŐ: " .. page, "info", 1, "mfd") end
		return
	end
	if k == "v" then cam.cockpit = not cam.cockpit; cam.panelLook = false; return end
	if k == "n" then
		if not cam.cockpit then cam.cockpit, cam.panelLook = true, true else cam.panelLook = not cam.panelLook end
		return
	end
	if k == "__zoom" then cam.zoom = (cam.zoom + 1) % 3; return end
	if k == "o" and match:canAct() then
		hud:message("Bullet time: a Hangárban vehető meg (mod)", "info", 2, "bt")
		return
	end
	if k == "t" then
		-- lock the enemy closest to where you are looking (mouse aim, or free look)
		local fwd = SimMath.fwdOf(cam.orientation)
		match:onKey("t", fwd)
		return
	end
	match:onKey(k)
end

-- ------------------------------------------------------------------ the missile camera and the kill camera
local function updateFollow(dt)
	local p = match.player
	cam.follow, cam.followLabel = nil, ""
	if not p then return end
	if not p.alive then
		local k = match.killCam
		if k and k.t > 0 and k.killer and not k.killer.crashed then
			k.t -= dt
			cam.follow = { pos = copy(k.killer.pos), dir = norm(k.killer.vel, k.killer.forward), dist = 40, height = 8 }
			cam.followLabel = "LELŐTT: " .. k.killer.name
		end
		return
	end
	if not missileCam then followM = nil; return end
	local now = os.clock()
	local m = followM
	if m and not m.alive and now - followEnd > 1.5 then m = nil; followM = nil end
	if not m then
		local mine = nil
		for _, x in ipairs(match.world.missiles) do
			if x.shooter == p and x.alive then mine = x end
		end
		m = mine
		followM = mine
	end
	if not m then return end
	if m.alive then
		followEnd = now
		followLast = { pos = copy(m.pos), dir = copy(m.dir) }
		local tg = m.guidedTarget or m.intended
		cam.follow = { pos = m.pos, dir = m.dir, dist = 8, height = 1.6 }
		cam.followLabel = string.format("RAKÉTAKAMERA · %s · %s%s  (U = ki)", m.spec.name, m.status,
			(tg and tg.alive) and string.format(" · %.1f km", len(sub(tg.pos, m.pos)) / 1000) or "")
	else
		cam.follow = { pos = followLast.pos, dir = followLast.dir, dist = 70, height = 12 }
		cam.followLabel = "RAKÉTAKAMERA · becsapódás"
	end
end

-- ------------------------------------------------------------------ the frame
local function frame(dt)
	dt = math.clamp(dt, 0, 0.1)
	local st = match.state
	local p = match.player
	local dx, dy = 0, 0
	if not Game.paused then
		dx, dy = input:takeDelta()
		if p.alive and not p.ejected then
			Controls.apply(match, cam, input:snapshot(dx, dy), dt)
		end
	end
	local events = match:update(dt)
	if session then
		session:step(dt)
		session:onEvents(events)
		netTimer -= dt
		if #netQueue > 0 and netTimer <= 0 then
			netTimer = 1 / 20
			remotes.Net:FireServer(netQueue)
			netQueue = {}
		end
	end
	for _, e in ipairs(events) do
		local kind, d = e[1], e[2]
		view:handleEvent(kind, d)
		hud:handleEvent(kind, d, match.player)
		sounds:handleEvent(kind, d, match.player)
		if kind == "explosion" then
			local dd = len(sub(d.pos, match.player.pos))
			if dd < 2500 then
				local k = 1 - dd / 2500
				cam.kick = math.max(cam.kick or 0, k * k)
			end
		end
	end
	updateFollow(Game.paused and 0 or dt)
	cam:update(Game.paused and 0 or dt, match.player)
	view.world = match.world
	view:setCamera(cam, cam.follow and cam.follow.pos or match.player.pos)
	local inside = cam.cockpit and match.player.alive and not cam.follow
	view:update(Game.paused and 0 or dt, match.player, inside)
	if inside ~= Game.wasInside then
		Game.wasInside = inside
		if Game.onCockpit then Game.onCockpit(inside) end
	end

	sounds:update(match.player, Game.paused, match.world, cam.position, dt)

	-- the HUD
	local w, h = canvas:size()
	local showMfd = inside == true and not Game.paused
	if mfdView then mfdView:update(dt, match.player, match.world, match.nav, showMfd, w, h, cam.panelLook) end
	hud.hideScopes = showMfd
	canvas:begin()
	if match.race or match:scenario() == "free" then hud.nav = nil else hud.nav = match.nav end
	hud.tutorial = match.tutorial ~= nil
	if match.tutorial then
		tutUi = tutUi or TutorialUi.new()
		tutUi:update(match.tutorial:view())
	elseif tutUi then
		tutUi:destroy()
		tutUi = nil
	end
	if radioUi then radioUi:update(match.radio, Game.paused) end
	st.raceTarget = match.race and match.race.target and match.race.target.c or nil
	local meatball = nil
	hud:update(dt, match.player, match.world, { position = cam.position, orientation = cam.orientation, fov = cam.fov }, cam, st, w, h)
	canvas:finish()

	-- the save: coins now and then, the career now and then
	earnTimer += dt
	if earnTimer >= 3 and pendingEarn > 0 then
		earnTimer = 0
		if remotes and remotes.Earn then remotes.Earn:FireServer(pendingEarn) end
		if profile then profile.coins = (profile.coins or 0) + pendingEarn end
		pendingEarn = 0
	end
end

-- ------------------------------------------------------------------ start / stop
-- opts: as the menu of the browser game builds them (scenario, difficulty, enemies, enemyTypes, aircraft, loadout, mode, wingman, airStart)
function Game.start(opts)
	if Game.active or not terrainReady then return false end
	Game.active = true
	Game.paused = false
	opts = opts or {}
	cam = Camera.new(terrain)
	local s = Game.settings
	cam.sensitivity, cam.stickSens, cam.invertY, cam.baseFov = Camera.SENS_BASE * s.aim / 100, s.stick / 100, s.invert, s.fov
	cam.fov = s.fov
	if not canvas then canvas = GuiCanvas.new(player) end
	canvas:setEnabled(true)
	hud = HudLogic.new(canvas)
	input = input or DeviceInput.new()
	input.listening = true
	radioUi = RadioUi.new(input)
	input.onPress = onKey
	input.onWheel = function(dir) if match and not Game.paused then match:cycleWeapon(dir) end end
	local hangar = makeHangar()
	sounds = Sounds.new(0.7)
	local env = {
		terrain = terrain,
		career = career or Career.new(nil, nil),
		hangar = hangar, hud = hud, cam = cam,
		onTutorialEnd = function() task.defer(Game.stop) end,
		onKick = function(k) if cam then cam.kick = math.max(cam.kick or 0, k) end end,
		onCatapultTow = function() if cam and match then cam:reset(match.player) end end,
		onCatapultOff = function()
			if cam and match then
				local f = norm(V(match.player.forward.x, match.player.forward.y, 0), V(0, 1, 0))
				cam.aim = SimMath.qlook(norm(V(f.x, f.y, 0.21)))
			end
		end,
		sounds = sounds,
		best = profile and profile.best or {},
		onRecord = function(kind, t, lap)
			if remotes and remotes.SaveBest then remotes.SaveBest:FireServer(kind, t, lap) end
			if profile then
				profile.best = profile.best or {}
				profile.best[kind] = t
				if kind == "tube" then profile.best.tubeLap = lap end
			end
		end,
		onSpawn = function(ac, spec)
			if ac.isPlayer then
				local info = JetInfo[spec.model] or JetInfo.f16
				cam.eye = V(info.eye[1], info.eye[2], info.eye[3])
				cam.panel = V(info.panel[1], info.panel[2], info.panel[3])
				cam.panelFov = info.panelFov
				cam:reset(ac)
				if mfdView then mfdView:destroy() end
				mfdView = MfdView.new(spec)
			end
		end,
	}
	-- in a room: the others fly in the same sky (Net.luau)
	local room = State.room
	local myId = player.UserId
	local inRoom = room ~= nil and #room.members > 0
	if inRoom then
		local team, slot = "A", 0
		for i, m in ipairs(room.members) do
			if m.userId == myId then team, slot = m.team, i - 1 end
		end
		local pvp = room.mode == "pvp"
		opts.scenario = pvp and "pvp" or "waves"
		opts.netGuest = (not pvp) and room.host ~= myId
		opts.wingman = 0
		env.netTeam = pvp and (team == "A" and "blue" or "red") or "blue"
		env.netSlot = slot
	end
	match = Match.new(opts, env)
	if inRoom then
		netQueue, netTimer = {}, 0
		local bus = {
			userId = myId, name = player.DisplayName, team = env.netTeam, clock = os.clock,
			isHost = function() return State.room == nil or State.room.host == myId end,
			send = function(m) table.insert(netQueue, m) end,
		}
		session = Net.new(match, bus)
		env.teamScore = function() return session.score end
		netConn = remotes.Net.OnClientEvent:Connect(function(from, batch)
			if not session or typeof(batch) ~= "table" then return end
			for _, m in batch do
				if typeof(m) == "table" then session:onMessage(from, m) end
			end
		end)
	end
	view = View.new(match.world)
	view:buildCarrier(match.carrier)
	view.quality = Game.settings.quality or "high"
	Env.set(Game.settings.tod)
	match.env.onRestart = function() view:setWorld(match.world) end
	missileCam, followM = false, nil
	input:setEnabled(true)
	match.state.paused = false
	conn = RunService:BindToRenderStep("DogfightFrame", Enum.RenderPriority.Camera.Value + 1, frame)
	return true
end

function Game.stop()
	if not Game.active then return end
	Game.active = false
	pcall(function() RunService:UnbindFromRenderStep("DogfightFrame") end)
	if pendingEarn > 0 and remotes and remotes.Earn then remotes.Earn:FireServer(pendingEarn) end
	if profile then profile.coins = (profile.coins or 0) + pendingEarn end
	pendingEarn = 0
	if career then career:save() end
	if input then input:setEnabled(false) end
	if canvas then canvas:setEnabled(false) end
	if pauseGui then pauseGui.Enabled = false end
	if helpGui then helpGui.Enabled = false end
	if Game.wasInside and Game.onCockpit then Game.onCockpit(false) end
	Game.wasInside = false
	if view then view:destroy() end
	if session then
		session:leave()
		if #netQueue > 0 then remotes.Net:FireServer(netQueue) end
		session, netQueue = nil, nil
	end
	if netConn then netConn:Disconnect(); netConn = nil end
	if sounds then sounds:stopAll(); sounds:destroy(); sounds = nil end
	if mfdView then mfdView:destroy(); mfdView = nil end
	if tutUi then tutUi:destroy(); tutUi = nil end
	if radioUi then radioUi:destroy(); radioUi = nil end
	match, view, hud, cam = nil, nil, nil, nil
	local c = workspace.CurrentCamera
	c.CameraType = Enum.CameraType.Scriptable
	if Game.onEnd then Game.onEnd() end
end

function Game.player() return match and match.player or nil end
function Game.match() return match end

return Game
