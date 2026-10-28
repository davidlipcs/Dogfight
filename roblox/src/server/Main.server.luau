--!nonstrict
-- Dogfight Plus for Roblox: the server's entry point.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Remotes = require(Shared.Remotes)

local Data = require(script.Parent.Data)
local Shop = require(script.Parent.Shop)
local World = require(script.Parent.World)
local Combat = require(script.Parent.Combat)
local Enemies = require(script.Parent.Enemies)

Players.CharacterAutoLoads = false          -- there is no avatar: the player is the jet
local remotes = Remotes.init()

World.build()
Data.init(remotes)
Data.start()
Shop.start(remotes)
Combat.init(remotes)
Enemies.init(remotes)

Players.PlayerAdded:Connect(function(player)
	Data.load(player)
	Shop.onLoaded(player)
end)
for _, player in Players:GetPlayers() do
	task.spawn(function()
		Data.load(player)
		Shop.onLoaded(player)
	end)
end

local lastLaunch = {}
remotes.Launch.OnServerEvent:Connect(function(player)
	if not Data.isLoaded(player) then return end
	local now = os.clock()
	if now - (lastLaunch[player] or 0) < 2 then return end
	lastLaunch[player] = now
	Combat.spawnPlayerJet(player)
end)
Players.PlayerRemoving:Connect(function(player) lastLaunch[player] = nil end)

local hudTimer, coinTimer = 0, 0
RunService.Heartbeat:Connect(function(dt)
	Combat.step(dt)
	Enemies.step(dt)

	hudTimer += dt
	if hudTimer >= 0.25 then
		hudTimer = 0
		for _, player in Players:GetPlayers() do
			local jet = Combat.jetOf(player)
			if jet then
				remotes.Hud:FireClient(player, {
					wave = Enemies.wave(), enemies = Enemies.count(),
					hp = jet:GetAttribute("Health"), maxHp = jet:GetAttribute("MaxHealth"),
					missiles = jet:GetAttribute("Missiles"), flares = jet:GetAttribute("Flares"),
				})
			end
		end
	end

	-- a trickle of coins for time in the air
	coinTimer += dt
	if coinTimer >= 1 then
		coinTimer = 0
		for _, player in Players:GetPlayers() do
			if Combat.jetOf(player) then Data.addCoins(player, Config.Coins.Survive) end
		end
	end
end)

print("Dogfight Plus server ready")
