--!nonstrict
-- Dogfight Plus for Roblox: the client's entry point (lobby -> flight or rear seat -> lobby).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Remotes = require(Shared.Remotes)

local Flight = require(script.Parent.Flight)
local Hud = require(script.Parent.Hud)
local Lobby = require(script.Parent.Lobby)
local RoomsUi = require(script.Parent.RoomsUi)
local State = require(script.Parent.State)
local Visibility = require(script.Parent.Visibility)
local Wso = require(script.Parent.Wso)
local Visor = require(script.Parent.Visor)

local player = Players.LocalPlayer
local remotes = Remotes.get()
local profile = nil
local state = "lobby"          -- lobby, launching, flying (pilot), wso (rear seat), dead

local function goLobby()
	state = "lobby"
	Flight.stop()
	Wso.stop()
	Hud.show(false)
	Lobby.show(true)
end

local function crashed()
	state = "dead"
	Hud.toast("Lezuhantál!", "bad")
	task.delay(2.4, function() if state == "dead" then goLobby() end end)
end

local function play(gear)
	if state ~= "lobby" then return end
	state = "launching"
	remotes.Launch:FireServer(gear)
	local jets = workspace:WaitForChild("Jets")
	local jet = jets:WaitForChild("Jet_" .. player.Name, 8)
	if not jet then
		state = "lobby"
		return
	end
	jet:WaitForChild("Body")
	RoomsUi.show(false)
	Lobby.show(false)
	Hud.show(true)
	state = "flying"
	Flight.start(jet, crashed)
	Hud.toast(gear == "twoseat" and "Kétüléses gép: a csapattársak beülhetnek hátulra · Szóköz: tűz · X: rakéta · G: flare" or "Vadássz! Szóköz: tűz · X: rakéta · G: flare · H: súgó", "info")
end

-- you sit in the rear seat of somebody's jet (the server tells us which): the pilot flies, you work the weapons
local function onSeat(jet)
	if jet then
		if state ~= "lobby" then return end
		RoomsUi.show(false)
		Lobby.show(false)
		Hud.show(true)
		state = "wso"
		Wso.start(jet)
		Hud.toast("Hátsó ülés: X rakéta · G flare · T jelölés · Z kiszállás", "info")
	elseif state == "wso" then
		goLobby()
	end
end

Hud.init(remotes, Flight)
Flight.init(remotes)
Wso.init(remotes, function()
	remotes.LeaveSeat:InvokeServer()
end)
Lobby.init(remotes, { onPlay = play, onRooms = function() RoomsUi.toggle() end })
RoomsUi.init(remotes, { onSeat = function() end })
Visibility.init()
Visor.init()
Flight.onCockpit = function(on) Visor.set(profile and profile.pilotOn, on) end

remotes.Seat.OnClientEvent:Connect(onSeat)
remotes.RoomState.OnClientEvent:Connect(function(room)
	State.set(room)
	Lobby.setRoom(room)
end)
remotes.Hud.OnClientEvent:Connect(function(d) Flight.markUid = d.markUid or 0 end)
remotes.Profile.OnClientEvent:Connect(function(p)
	profile = p
	Hud.setProfile(p)
	Lobby.setProfile(p)
end)
remotes.Died.OnClientEvent:Connect(function(reason)
	if state ~= "flying" and state ~= "wso" then return end        -- a crash was already handled by crashed()
	Flight.stop()
	Wso.stop()
	state = "dead"
	Hud.toast("Vége: " .. tostring(reason), "bad")
	task.delay(2.4, function() if state == "dead" then goLobby() end end)
end)

-- the profile (coins, skins): asked until the server has it
task.spawn(function()
	local p
	repeat
		p = remotes.GetProfile:InvokeServer()
		if not p then task.wait(0.5) end
	until p
	profile = p
	Hud.setProfile(p)
	Lobby.setProfile(p)
end)

goLobby()
Lobby.setRoom(nil)

RunService.RenderStepped:Connect(function(dt)
	if state == "flying" then Hud.update(dt, Flight.state)
	elseif state == "wso" then Hud.update(dt, Wso.state) end
end)
