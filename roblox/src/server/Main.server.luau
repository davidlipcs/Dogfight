--!nonstrict
-- Dogfight Plus for Roblox: the server's entry point.  The match itself runs on the player's own machine (the same simulation as the
-- browser game, shared/game/Match.luau); the server keeps what must not be the client's word: the save (coins, skins, career, records),
-- the shop and the Robux purchases, and the rooms.
-- Only one copy of the game's server may run (an update file left in the Workspace has a copy of this script, too)
if workspace:GetAttribute("DogfightServerRunning") == true or not script:IsDescendantOf(game:GetService("ServerScriptService")) then
	warn("Dogfight Plus: a second copy of the server script was not started (" .. script:GetFullName() .. "). Delete leftovers such as 'DogfightCodeUpdate' from the Workspace.")
	return
end
workspace:SetAttribute("DogfightServerRunning", true)

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Remotes = require(Shared.Remotes)

local Data = require(script.Parent.Data)
local Shop = require(script.Parent.Shop)
local World = require(script.Parent.World)
local Rooms = require(script.Parent.Rooms)
local Daily = require(script.Parent.Daily)
local Tools = require(script.Parent.Tools)

Players.CharacterAutoLoads = false          -- there is no avatar: the player is the jet
local remotes = Remotes.init()

World.build()
Tools.adoptJets()                           -- imported jets still lying in the Workspace go where the game looks for them
Data.init(remotes)
Data.start()
Shop.start(remotes)
Rooms.init(remotes)
Daily.init(remotes)

Players.PlayerAdded:Connect(function(player)
	if Data.load(player) then Shop.onLoaded(player) end
end)
for _, player in Players:GetPlayers() do
	task.spawn(function()
		if Data.load(player) then Shop.onLoaded(player) end
	end)
end

remotes.Earn.OnServerEvent:Connect(function(player, n) Data.earn(player, n) end)
remotes.SaveCareer.OnServerEvent:Connect(function(player, t)
	Data.saveCareer(player, t)
	local p = Data.get(player)
	if p and p.career then Daily.reportScore(player, p.career.bestScore) end
end)
remotes.SaveBest.OnServerEvent:Connect(function(player, kind, time, lap) Data.saveBest(player, kind, time, lap) end)
-- the war career is saved at most every 0.3 s, but the newest state is never dropped (a later one replaces a waiting one)
local warSaved, warPending, warWaiting = {}, {}, {}
local function flushWar(player)
	local t = warPending[player]
	warPending[player] = nil
	warWaiting[player] = nil
	warSaved[player] = os.clock()
	if t then Data.saveWar(player, t) end
end
remotes.SaveWar.OnServerEvent:Connect(function(player, t)
	warPending[player] = t
	local wait = 0.3 - (os.clock() - (warSaved[player] or -1))
	if wait <= 0 then
		flushWar(player)
	elseif not warWaiting[player] then
		warWaiting[player] = true
		task.delay(wait, function() flushWar(player) end)
	end
end)

-- the match of a room: every message of a player goes to the others of the same room (the server only relays; each player is the
-- authority of their own jet, the room's host of the enemies)
local netBudget = {}
remotes.Net.OnServerEvent:Connect(function(player, batch)
	if typeof(batch) ~= "table" or #batch == 0 or #batch > 40 then return end
	local room = Rooms.get(player)
	if not room then return end
	local now = os.clock()
	local b = netBudget[player]
	if not b then b = { tokens = 60, t = now }; netBudget[player] = b end
	b.tokens = math.min(60, b.tokens + (now - b.t) * 40)
	b.t = now
	if b.tokens < 1 then return end
	b.tokens -= 1
	for _, m in batch do
		if typeof(m) ~= "table" or typeof(m.t) ~= "string" then return end
	end
	for p in room.members do
		if p ~= player then remotes.Net:FireClient(p, player.UserId, batch) end
	end
end)
Players.PlayerRemoving:Connect(function(player) netBudget[player] = nil; warSaved[player] = nil; warPending[player] = nil; warWaiting[player] = nil end)

game:GetService("RunService").Heartbeat:Connect(function(dt) Rooms.step(dt) end)

print("Dogfight Plus server ready")
