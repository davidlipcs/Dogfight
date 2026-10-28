--!nonstrict
-- Dogfight Plus for Roblox: the client's entry point (lobby -> flight -> lobby).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Remotes = require(Shared.Remotes)

local Flight = require(script.Parent.Flight)
local Hud = require(script.Parent.Hud)
local Lobby = require(script.Parent.Lobby)

local player = Players.LocalPlayer
local remotes = Remotes.get()
local state = "lobby"

local function goLobby()

RunService.RenderStepped:Connect(function(dt)
	if state == "flying" then Hud.update(dt, Flight.state) end
end)
	state = "lobby"
	Flight.stop()
	Hud.show(false)
	Lobby.show(true)
end

local function crashed()
	state = "dead"
	Hud.toast("Lezuhantál!", "bad")
	task.delay(2.4, function() if state == "dead" then goLobby() end end)
end

local function play()
	if state ~= "lobby" then return end
	state = "launching"
	remotes.Launch:FireServer()
	local jets = workspace:WaitForChild("Jets")
	local jet = jets:WaitForChild("Jet_" .. player.Name, 8)
	if not jet then
		state = "lobby"
		return
	end
	jet:WaitForChild("Body")
	Lobby.show(false)
	Hud.show(true)
	state = "flying"
	Flight.start(jet, crashed)
	Hud.toast("Vadássz! Szóköz: tűz · X: rakéta · G: flare · H: súgó", "info")
end

Hud.init(remotes, Flight)
Flight.init(remotes)
Lobby.init(remotes, { onPlay = play })

remotes.Profile.OnClientEvent:Connect(function(p)
	Hud.setProfile(p)
	Lobby.setProfile(p)
end)
remotes.Died.OnClientEvent:Connect(function(reason)
	if state ~= "flying" then return end        -- a crash was already handled by crashed()
	Flight.stop()
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
	Hud.setProfile(p)
	Lobby.setProfile(p)
end)

goLobby()

RunService.RenderStepped:Connect(function(dt)
	if state == "flying" then Hud.update(dt, Flight.state) end
end)
