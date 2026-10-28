--!nonstrict
-- Dogfight Plus for Roblox: the client's entry point.  The menu (hangar, shop, rooms, match options) -> a match on this machine
-- (Game.luau) -> back to the menu.
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
	Lobby.show(true)
end
Game.onEnd = goLobby

local function play(airStart, tutorial)
	if inMatch then return end
	if not Game.ready() then
		Lobby.say("A sziget adatai még töltődnek…", false)
		return
	end
	local s = Menu.settings()
	for k, v in pairs(s) do Game.settings[k] = v end
	if profile then Game.setProfile(profile) end
	RoomsUi.show(false)
	Lobby.show(false)
	inMatch = true
	local opts = Menu.opts(airStart)
	if tutorial then
		opts.tutorial, opts.scenario, opts.enemies, opts.wingman, opts.mode, opts.airStart = true, "waves", 0, 0, "arcade", true
		if profile then profile.pilotOn = profile.pilotOn end
	end
	if not Game.start(opts) then
		inMatch = false
		Lobby.show(true)
	end
end

Lobby.init(remotes, { onPlay = play, onRooms = function() RoomsUi.toggle() end })
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
end)

goLobby()
Lobby.setRoom(nil)
