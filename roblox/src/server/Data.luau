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
		jetOn = nil,                     -- the jet model (Config.JetModels key; nil = the one built from parts)
		career = nil,                    -- the career table of the match (shared/game/Career.luau)
		best = {},                       -- race records: race, canyon, tube, tubeLap (seconds)
		warSave = nil,                   -- the war career: { war, pilot } (shared/game/Campaign.luau)
		daily = nil, missions = nil,     -- the daily reward streak and the day's missions (server/Daily.luau)
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
	return { coins = p.coins, kills = p.kills, best = p.best, air = p.air, pilot = p.pilot, airOn = p.airOn, pilotOn = p.pilotOn, jetOn = p.jetOn, double = p.double == true, career = p.career, best = p.best, warSave = p.warSave }
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
	p.best = p.best or {}
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

-- coins earned in the match (the client plays the match, so the rate is limited: at most ~40 coins a second on average, 4000 at once)
local earnBudget = {}      -- [Player] = { tokens, t }
function Data.earn(player: Player, n: any)
	local p = profiles[player]
	if not p or typeof(n) ~= "number" or n ~= n or n <= 0 then return end
	local now = os.clock()
	local b = earnBudget[player]
	if not b then b = { tokens = 4000, t = now }; earnBudget[player] = b end
	b.tokens = math.min(4000, b.tokens + (now - b.t) * 40)
	b.t = now
	if player.MembershipType == Enum.MembershipType.Premium then n = n * (1 + Config.PremiumBonus) end
	n = math.min(math.floor(n), b.tokens)
	if n <= 0 then return end
	b.tokens -= n
	Data.addCoins(player, n)
end

local CAREER_KEYS = { "matches", "kills", "deaths", "gunKills", "irKills", "arhKills", "crashKills", "missilesFired", "flightTime", "bestScore", "bestWave",
	"bestStreak", "bestSurvival", "duelWins", "ejections" }
-- the career table, checked: numbers for the counters, a table of ids and times for the medals, a table of counts per plane / victim
function Data.saveCareer(player: Player, t: any)
	local p = profiles[player]
	if not p or typeof(t) ~= "table" then return end
	local c = {}
	for _, k in CAREER_KEYS do
		local v = t[k]
		if typeof(v) == "number" and v == v and v >= 0 and v < 1e9 then c[k] = v end
	end
	for _, k in { "medals", "perPlane", "victims" } do
		local src, dst = t[k], {}
		if typeof(src) == "table" then
			local n = 0
			for id, v in src do
				n += 1
				if n > 80 then break end
				if typeof(id) == "string" and #id < 24 and typeof(v) == "number" and v == v then dst[id] = v end
			end
		end
		c[k] = dst
	end
	-- the counters only ever go up (a smaller number is a stale or a forged packet)
	local old = p.career
	if old then
		for _, k in CAREER_KEYS do
			if (old[k] or 0) > (c[k] or 0) then c[k] = old[k] end
		end
	end
	p.career = c
	p.kills = c.kills or p.kills
	p.best = p.best or {}
end

-- the war career (a table the size of a few KB): kept if it looks like one
function Data.saveWar(player: Player, t: any)
	local p = profiles[player]
	if not p or typeof(t) ~= "table" or typeof(t.war) ~= "table" or typeof(t.pilot) ~= "table" then return end
	local w, pl = t.war, t.pilot
	if typeof(w.day) ~= "number" or typeof(w.powers) ~= "table" or typeof(pl.rank) ~= "number" or pl.rank < 0 or pl.rank > 6 then return end
	local ok, json = pcall(function() return game:GetService("HttpService"):JSONEncode(t) end)
	if not ok or #json > 60000 then return end
	-- the pilot's counters only go up inside a war (a smaller number is a stale or forged packet), unless it is a fresh war
	local old = p.warSave
	if old and old.war and old.war.day and w.day >= old.war.day and typeof(old.pilot) == "table" then
		if (pl.sorties or 0) < (old.pilot.sorties or 0) or (pl.kills or 0) < (old.pilot.kills or 0) or pl.rank < (old.pilot.rank or 0) then return end
	end
	p.warSave = t
end

function Data.saveBest(player: Player, kind: any, time: any, lap: any)
	local p = profiles[player]
	if not p or typeof(time) ~= "number" or time ~= time or time <= 3 or time > 36000 then return end
	if kind ~= "race" and kind ~= "canyon" and kind ~= "tube" then return end
	p.best = p.best or {}
	if p.best[kind] == nil or time < p.best[kind] then p.best[kind] = time end
	if kind == "tube" and typeof(lap) == "number" and lap > 3 and lap < 36000 then
		if p.best.tubeLap == nil or lap < p.best.tubeLap then p.best.tubeLap = lap end
	end
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
		earnBudget[player] = nil
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
