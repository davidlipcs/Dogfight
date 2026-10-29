--!nonstrict
-- Dogfight Plus for Roblox: the client's entry point.  The menu (hangar, shop, rooms, match options) -> a match on this machine
-- (Game.luau) -> back to the menu.
-- Only one copy of the game's client may run (two would show two menus on top of each other)
local LocalPlayer = game:GetService("Players").LocalPlayer
if LocalPlayer:GetAttribute("DogfightClientRunning") == true then
	warn("Dogfight Plus: a second copy of the client script was not started (" .. script:GetFullName() .. ").")
	return
end
LocalPlayer:SetAttribute("DogfightClientRunning", true)

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local StarterGui = game:GetService("StarterGui")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Remotes = require(Shared.Remotes)

local Game = require(script.Parent.Game)
local Lobby = require(script.Parent.Lobby)
local Menu = require(script.Parent.Menu)
local RoomsUi = require(script.Parent.RoomsUi)
local State = require(script.Parent.State)
local Visor = require(script.Parent.Visor)
local WarUi = require(script.Parent.WarUi)
local LoadingUi = require(script.Parent.LoadingUi)

pcall(function()
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)      -- Tab is a flying key
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, false)
end)

local remotes = Remotes.get()
local profile = nil
local inMatch = false

Game.init(remotes)
Game.onCockpit = function(on) Visor.set(profile and profile.pilotOn, on) end
Game.preload()

local function goLobby()
	inMatch = false
	local done = Game.lastMission
	Game.lastMission = nil
	if done then
		-- a sortie of the war career is over: the report
		WarUi.afterMission(done.result, done.mission)
		return
	end
	Lobby.show(true)
end
Game.onEnd = goLobby

-- the island's data is decoded while the menu is open; a start waits for it with a big message on the screen (and tells if it fails)
local function prepare(back)
	LoadingUi.show("Indítás… a sziget adatainak betöltése", 0.05)
	local t0 = os.clock()
	while not Game.ready() and not Game.preloadError and os.clock() - t0 < 120 do
		task.wait(0.2)
		LoadingUi.set(nil, math.min(0.4, 0.05 + (os.clock() - t0) / 150))
	end
	if Game.ready() then return true end
	LoadingUi.fail("A sziget adatai nem töltődtek be",
		Game.preloadError and ("Hiba: " .. Game.preloadError .. "\n\nPróbáld újra a kód telepítésével (Plugins fül → Kód telepítése), majd File → Save.") or "Túl sokáig tart. Várj egy kicsit, és próbáld újra.",
		function() LoadingUi.hide(); back() end)
	return false
end

local function play(airStart, tutorial)
	if inMatch then return end
	inMatch = true
	if not prepare(function() inMatch = false; Lobby.show(true) end) then return end
	local s = Menu.settings()
	for k, v in pairs(s) do Game.settings[k] = v end
	if profile then Game.setProfile(profile) end
	RoomsUi.show(false)
	Lobby.show(false)
	local opts = Menu.opts(airStart)
	if tutorial then
		opts.tutorial, opts.scenario, opts.enemies, opts.wingman, opts.mode, opts.airStart = true, "waves", 0, 0, "arcade", true
		if profile then profile.pilotOn = profile.pilotOn end
	end
	local ok, started = pcall(Game.start, opts)
	if not ok then
		warn("Dogfight Plus: the match could not be started: ", started)
		Game.stop()
		LoadingUi.fail("A játék nem tudott elindulni", "Hiba: " .. tostring(started) .. "\n\nMásold ki ezt a szöveget (és az Output ablak piros sorait), és küldd el.", function() LoadingUi.hide(); inMatch = false; Lobby.show(true) end)
	elseif not started then
		inMatch = false
		LoadingUi.hide()
		Lobby.show(true)
	end
end

-- a sortie of the war career (WarUi): a match of scenario "mission"
local function playMission(opts)
	if inMatch then return end
	inMatch = true
	if not prepare(function() inMatch = false; WarUi.show(true) end) then return end
	local s = Menu.settings()
	for k, v in pairs(s) do Game.settings[k] = v end
	if profile then Game.setProfile(profile) end
	WarUi.show(false)
	RoomsUi.show(false)
	Lobby.show(false)
	local ok, started = pcall(Game.start, opts)
	if not ok then
		warn("Dogfight Plus: the sortie could not be started: ", started)
		Game.stop()
		LoadingUi.fail("A bevetés nem tudott elindulni", "Hiba: " .. tostring(started), function() LoadingUi.hide(); inMatch = false; WarUi.show(true) end)
	elseif not started then
		inMatch = false
		LoadingUi.hide()
		WarUi.show(true)
	end
end

Lobby.init(remotes, { onPlay = play, onRooms = function() RoomsUi.toggle() end, onWar = function() WarUi.show(true) end })
WarUi.init(remotes, { onFly = playMission })
RoomsUi.init(remotes, { onSeat = function(seat, pilotId)
	-- the rear seat of a team mate's jet: a match in which only the weapons are yours
	if inMatch or typeof(seat) ~= "table" then return end
	local layout = {}
	for _, pair in ipairs(seat.lo or {}) do layout[pair[1]] = pair[2] end
	local s = Menu.settings()
	for k, v in pairs(s) do Game.settings[k] = v end
	if profile then Game.setProfile(profile) end
	RoomsUi.show(false)
	Lobby.show(false)
	inMatch = true
	if not Game.start({ wsoOf = pilotId, aircraft = seat.a, loadout = next(layout) and layout or "default", scenario = "waves", enemies = 0, wingman = 0, airStart = true, mode = "arcade", difficulty = "normal", enemyTypes = { "f16" } }) then
		inMatch = false
		Lobby.show(true)
		remotes.LeaveSeat:InvokeServer()
	end
end })
Visor.init()

remotes.RoomState.OnClientEvent:Connect(function(room)
	State.set(room)
	Lobby.setRoom(room)
end)
remotes.Toast.OnClientEvent:Connect(function(text, kind)
	local m = Game.match()
	if m then m.hud:message(text, kind or "info", 3) else Lobby.say(text, kind == "good") end
end)
remotes.Profile.OnClientEvent:Connect(function(p)
	profile = p
	Game.setProfile(p)
	Lobby.setProfile(p)
	WarUi.setProfile(p)
end)

-- the profile (coins, skins): asked until the server has it
task.spawn(function()
	local p
	repeat
		p = remotes.GetProfile:InvokeServer()
		if not p then task.wait(0.5) end
	until p
	profile = p
	Game.setProfile(p)
	Lobby.setProfile(p)
	WarUi.setProfile(p)
end)

-- while a match runs the menu is never shown (whatever happened, it is put away)
game:GetService("RunService").Heartbeat:Connect(function()
	if Game.active and Lobby.isVisible() then Lobby.show(false) end
end)
print("Dogfight Plus client " .. tostring(require(Shared.Config).Version) .. " runs from " .. script:GetFullName())

goLobby()
Lobby.setRoom(nil)
