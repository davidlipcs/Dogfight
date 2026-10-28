--!nonstrict
-- Dogfight Plus for Roblox: the server's entry point.  The match itself runs on the player's own machine (the same simulation as the
-- browser game, shared/game/Match.luau); the server keeps what must not be the client's word: the save (coins, skins, career, records),
-- the shop and the Robux purchases, and the rooms.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Remotes = require(Shared.Remotes)

local Data = require(script.Parent.Data)
local Shop = require(script.Parent.Shop)
local World = require(script.Parent.World)
local Rooms = require(script.Parent.Rooms)

Players.CharacterAutoLoads = false          -- there is no avatar: the player is the jet
local remotes = Remotes.init()

World.build()
Data.init(remotes)
Data.start()
Shop.start(remotes)
Rooms.init(remotes)

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

remotes.Earn.OnServerEvent:Connect(function(player, n) Data.earn(player, n) end)
remotes.SaveCareer.OnServerEvent:Connect(function(player, t) Data.saveCareer(player, t) end)
remotes.SaveBest.OnServerEvent:Connect(function(player, kind, time, lap) Data.saveBest(player, kind, time, lap) end)

game:GetService("RunService").Heartbeat:Connect(function(dt) Rooms.step(dt) end)

print("Dogfight Plus server ready")
