--!nonstrict
-- Reasons to come back: the daily reward (a streak), three daily missions and a top list.  The missions are measured on the server from the
-- career counters the client saves (they only ever go up), against what they were when the day's missions were given out.
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)
local Data = require(script.Parent.Data)

local Daily = {}

local board = nil
pcall(function() board = DataStoreService:GetOrderedDataStore(Config.DataStoreName .. "_best") end)
local boardCache, boardAt = {}, 0
local lastBoardWrite = {}

local function today(): number
	return math.floor(os.time() / 86400)
end

-- three missions a day, always the same three for the same player on the same day
local function pick(userId: number, day: number)
	local rng = Random.new(userId * 7919 + day)
	local pool, out = table.clone(Config.Missions), {}
	for _ = 1, 3 do
		local i = rng:NextInteger(1, #pool)
		table.insert(out, pool[i])
		table.remove(pool, i)
	end
	return out
end

local function stat(p, key: string): number
	local c = p.career
	return c and tonumber(c[key]) or 0
end

local function missionsOf(player: Player)
	local p = Data.get(player)
	if not p then return nil end
	local day = today()
	local m = p.missions
	if not m or m.day ~= day then
		m = { day = day, base = {}, claimed = {} }
		for _, d in Config.Missions do m.base[d.stat] = stat(p, d.stat) end
		p.missions = m
	end
	return m
end

function Daily.missions(player: Player)
	local p, m = Data.get(player), missionsOf(player)
	if not p then return {} end
	local out = {}
	for _, d in pick(player.UserId, m.day) do
		local progress = math.max(0, stat(p, d.stat) - (m.base[d.stat] or 0))
		table.insert(out, { id = d.id, text = d.text, target = d.target, progress = math.min(progress, d.target), reward = d.reward, claimed = m.claimed[d.id] == true, done = progress >= d.target })
	end
	return out
end

function Daily.claimMission(player: Player, id: any)
	local p, m = Data.get(player), missionsOf(player)
	if not p or typeof(id) ~= "string" then return false, "Hiba" end
	for _, e in Daily.missions(player) do
		if e.id == id then
			if e.claimed then return false, "Már átvetted" end
			if not e.done then return false, "Ez még nincs kész" end
			m.claimed[id] = true
			p.coins += e.reward
			Data.push(player)
			task.spawn(Data.save, player)
			return true, "+" .. e.reward .. " érme"
		end
	end
	return false, "Nincs ilyen feladat"
end

-- the daily reward: once per day; the streak goes on when yesterday was claimed
function Daily.claimDaily(player: Player)
	local p = Data.get(player)
	if not p then return false, "Hiba" end
	local day = today()
	local d = p.daily or { last = 0, streak = 0 }
	if d.last == day then return false, "Ma már átvetted – gyere vissza holnap!" end
	d.streak = (d.last == day - 1) and (d.streak % #Config.Daily + 1) or 1
	d.last = day
	p.daily = d
	local n = Config.Daily[d.streak]
	p.coins += n
	Data.push(player)
	task.spawn(Data.save, player)
	return true, "+" .. n .. " érme (" .. d.streak .. ". nap)", d.streak
end

function Daily.dailyState(player: Player)
	local p = Data.get(player)
	local d = p and p.daily or { last = 0, streak = 0 }
	local day = today()
	return { available = d.last ~= day, streak = d.last >= day - 1 and d.streak or 0, rewards = Config.Daily }
end

-- the top list: the best score of the players, kept in an ordered DataStore (written at most once a minute per player)
function Daily.reportScore(player: Player, score: number)
	if not board or typeof(score) ~= "number" or score ~= score or score <= 0 or score > 1e9 then return end
	local now = os.clock()
	if now - (lastBoardWrite[player] or -1e9) < 60 then return end
	local p = Data.get(player)
	if p and p.reportedBest and score <= p.reportedBest then return end
	lastBoardWrite[player] = now
	if p then p.reportedBest = score end
	task.spawn(function()
		pcall(function() board:UpdateAsync(tostring(player.UserId), function(old) return math.max(old or 0, math.floor(score)) end) end)
	end)
end

function Daily.leaderboard()
	if os.clock() - boardAt < 60 and #boardCache > 0 then return boardCache end
	boardAt = os.clock()
	local out = {}
	if board then
		local ok, pages = pcall(function() return board:GetSortedAsync(false, 10) end)
		if ok then
			for rank, e in pages:GetCurrentPage() do
				local name = "Pilóta"
				pcall(function() name = Players:GetNameFromUserIdAsync(tonumber(e.key)) end)
				table.insert(out, { rank = rank, name = name, score = e.value })
			end
		end
	end
	boardCache = out
	return out
end

function Daily.init(remotes)
	remotes.ClaimDaily.OnServerInvoke = function(player) return Daily.claimDaily(player) end
	remotes.GetMissions.OnServerInvoke = function(player) return { missions = Daily.missions(player), daily = Daily.dailyState(player) } end
	remotes.ClaimMission.OnServerInvoke = function(player, id) return Daily.claimMission(player, id) end
	remotes.GetLeaderboard.OnServerInvoke = function() return Daily.leaderboard() end
	Players.PlayerRemoving:Connect(function(player) lastBoardWrite[player] = nil end)
end

return Daily
