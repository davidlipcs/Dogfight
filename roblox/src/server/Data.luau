--!nonstrict
-- The save: coins, the bought skins and what is worn, kills.  A DataStore keeps it between visits; when the
-- DataStore is not available (Studio without API access) the game still runs, the save lives for the session.
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)

local Data = {}

local store = nil
pcall(function() store = DataStoreService:GetDataStore(Config.DataStoreName) end)

local profiles = {}   -- [Player] = table
local loaded = {}     -- [Player] = true once the data is in
local remotes = nil

local function fresh()
	return {
		coins = Config.Coins.Start, kills = 0, best = 0, flown = 0,
		air = {}, pilot = {},            -- owned: [id] = true
		airOn = nil, pilotOn = nil,      -- worn (nil = the factory paint / the plain flight suit)
		receipts = {},
		version = 1,
	}
end

local function key(player: Player): string
	return "u_" .. tostring(player.UserId)
end

function Data.init(r)
	remotes = r
end

function Data.get(player: Player)
	return profiles[player]
end

function Data.isLoaded(player: Player): boolean
	return loaded[player] == true
end

-- what the client needs to draw the shop and the HUD
function Data.view(player: Player)
	local p = profiles[player]
	if not p then return nil end
	return { coins = p.coins, kills = p.kills, best = p.best, air = p.air, pilot = p.pilot, airOn = p.airOn, pilotOn = p.pilotOn, double = p.double == true }
end

function Data.push(player: Player)
	if remotes and profiles[player] then remotes.Profile:FireClient(player, Data.view(player)) end
end

function Data.load(player: Player)
	local p = fresh()
	if store then
		local ok, saved = pcall(function() return store:GetAsync(key(player)) end)
		if ok and typeof(saved) == "table" then
			for k, v in saved do p[k] = v end
		elseif not ok then
			warn("DataStore load failed: ", saved)
		end
	end
	p.air = p.air or {}
	p.pilot = p.pilot or {}
	p.receipts = p.receipts or {}
	profiles[player] = p
	loaded[player] = true
	Data.push(player)
	return p
end

function Data.save(player: Player)
	local p = profiles[player]
	if not p or not store then return end
	local copy = {}
	for k, v in p do if k ~= "double" then copy[k] = v end end
	for attempt = 1, 3 do
		local ok, err = pcall(function() store:SetAsync(key(player), copy) end)
		if ok then return end
		warn("DataStore save failed (" .. attempt .. "): ", err)
		task.wait(2 * attempt)
	end
end

function Data.addCoins(player: Player, n: number)
	local p = profiles[player]
	if not p or n == 0 then return end
	if n > 0 and p.double then n = n * 2 end
	p.coins = math.max(0, p.coins + n)
	Data.push(player)
end

function Data.spend(player: Player, price: number): boolean
	local p = profiles[player]
	if not p or p.coins < price then return false end
	p.coins -= price
	return true
end

function Data.addKill(player: Player)
	local p = profiles[player]
	if not p then return end
	p.kills += 1
end

function Data.start()
	Players.PlayerRemoving:Connect(function(player)
		Data.save(player)
		profiles[player] = nil
		loaded[player] = nil
	end)
	-- autosave every minute
	task.spawn(function()
		while true do
			task.wait(60)
			for _, player in Players:GetPlayers() do
				if loaded[player] then task.spawn(Data.save, player) end
			end
		end
	end)
	game:BindToClose(function()
		for _, player in Players:GetPlayers() do
			if loaded[player] then task.spawn(Data.save, player) end
		end
		task.wait(3)
	end)
end

return Data
