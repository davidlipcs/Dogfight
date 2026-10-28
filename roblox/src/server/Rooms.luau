--!nonstrict
-- The hangar groups ("rooms"): a player opens a room, says how many more may come in (20 in all at most), and the
-- others join from the list (or with the code of a private room).  Everybody moves themselves between the two
-- teams of a team-fight room, in any split.  A room is a group inside the server: what happens in it (enemy waves,
-- the fight between the teams, the missiles) only concerns its members.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TextService = game:GetService("TextService")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)
local R = Config.Rooms

local Rooms = {}
Rooms.hooks = {}          -- left(player, room), closed(room)

local rooms = {}          -- [id] = room
local roomOf = {}         -- [Player] = room
local nextId = 1
local remotes = nil
local rng = Random.new()

function Rooms.get(player: Player)
	return roomOf[player]
end
function Rooms.byId(id)
	return rooms[id]
end

function Rooms.count(room): number
	local n = 0
	for _ in room.members do n += 1 end
	return n
end

function Rooms.players(room): { Player }
	local out = {}
	for p in room.members do table.insert(out, p) end
	return out
end

-- a text a player typed that others will read goes through Roblox's filter
local function filtered(text: string, player: Player): string
	text = string.sub(text or "", 1, R.NameMax)
	local ok, result = pcall(function()
		local f = TextService:FilterStringAsync(text, player.UserId)
		return f:GetNonChatStringForBroadcastAsync()
	end)
	if ok and typeof(result) == "string" and result ~= "" then return result end
	return player.DisplayName .. " szobája"
end

local function newCode(): string
	for _ = 1, 50 do
		local c = string.format("%04d", rng:NextInteger(0, 9999))
		local free = true
		for _, r in rooms do
			if r.code == c then free = false break end
		end
		if free then return c end
	end
	return string.format("%04d", rng:NextInteger(0, 9999))
end

local function smallerTeam(room): string
	local a, b = 0, 0
	for _, t in room.team do
		if t == "A" then a += 1 else b += 1 end
	end
	return a <= b and "A" or "B"
end

-- what the members see
function Rooms.view(room, forPlayer: Player?)
	local members = {}
	for p in room.members do
		table.insert(members, { userId = p.UserId, name = p.DisplayName, team = room.team[p] or "A", host = (p == room.host) })
	end
	table.sort(members, function(a, b) return a.name < b.name end)
	local seats = {}
	local jets = workspace:FindFirstChild("Jets")
	if jets then
		for _, j in jets:GetChildren() do
			if j:GetAttribute("RoomId") == room.id and j:GetAttribute("Seats") == 2 and j:GetAttribute("WsoId") == 0 and j:GetAttribute("SeatOpen") then
				local pilot = Players:GetPlayerByUserId(j:GetAttribute("OwnerId") or 0)
				if pilot then table.insert(seats, { userId = pilot.UserId, name = pilot.DisplayName, team = j:GetAttribute("Team") }) end
			end
		end
	end
	return {
		id = room.id, name = room.name, mode = room.mode, max = room.max, private = room.private,
		code = (forPlayer and room.members[forPlayer]) and room.private and room.code or nil,
		host = room.host and room.host.UserId or 0, members = members, seats = seats, score = room.score,
	}
end

function Rooms.push(room)
	for p in room.members do
		remotes.RoomState:FireClient(p, Rooms.view(room, p))
	end
end

local function pushNone(player: Player)
	remotes.RoomState:FireClient(player, nil)
end

function Rooms.leave(player: Player)
	local room = roomOf[player]
	if not room then return end
	roomOf[player] = nil
	room.members[player] = nil
	room.team[player] = nil
	if Rooms.hooks.left then Rooms.hooks.left(player, room) end
	if next(room.members) == nil then
		rooms[room.id] = nil
		if Rooms.hooks.closed then Rooms.hooks.closed(room) end
	else
		if room.host == player then
			for p in room.members do room.host = p break end
		end
		Rooms.push(room)
	end
	if player.Parent then pushNone(player) end
end

local function enter(player: Player, room)
	Rooms.leave(player)
	room.members[player] = true
	room.team[player] = room.mode == "pvp" and smallerTeam(room) or "A"
	roomOf[player] = room
	Rooms.push(room)
end

-- a new room: name, mode ("coop" against the AI waves, "pvp" two teams), how many more may come in, private?
function Rooms.create(player: Player, name: string, mode: string, extra: number, private: boolean)
	if typeof(name) ~= "string" then name = "" end
	extra = math.clamp(math.floor(tonumber(extra) or 3), 0, R.MaxPlayers - 1)
	local room = {
		id = nextId, name = filtered(name ~= "" and name or (player.DisplayName .. " szobája"), player), host = player,
		mode = mode == "pvp" and "pvp" or "coop", max = 1 + extra, private = private == true, code = nil,
		members = {}, team = {}, score = { A = 0, B = 0 }, created = os.time(),
	}
	nextId += 1
	if room.private then room.code = newCode() end
	rooms[room.id] = room
	enter(player, room)
	return true, room.id
end

function Rooms.list()
	local out = {}
	for _, r in rooms do
		if not r.private then
			table.insert(out, { id = r.id, name = r.name, mode = r.mode, count = Rooms.count(r), max = r.max, host = r.host and r.host.DisplayName or "" })
		end
	end
	table.sort(out, function(a, b) return a.id < b.id end)
	return out
end

-- by room id, or by the 4-digit code of a private room
function Rooms.join(player: Player, ref)
	local room = nil
	if typeof(ref) == "number" then
		room = rooms[ref]
		if room and room.private then room = nil end
	elseif typeof(ref) == "string" then
		local code = string.gsub(ref, "%s", "")
		for _, r in rooms do
			if r.private and r.code == code then room = r end
		end
	end
	if not room then return false, "Nincs ilyen szoba" end
	if roomOf[player] == room then return true, "Már itt vagy" end
	if Rooms.count(room) >= room.max then return false, "A szoba megtelt" end
	enter(player, room)
	return true, room.name
end

function Rooms.quickPlay(player: Player)
	local best = nil
	for _, r in rooms do
		if not r.private and r.mode == "coop" and Rooms.count(r) < r.max then
			if not best or Rooms.count(r) > Rooms.count(best) then best = r end
		end
	end
	if best then return Rooms.join(player, best.id) end
	return Rooms.create(player, "", "coop", 7, false)
end

-- everybody moves themselves ("A" or "B"), in any split
function Rooms.setTeam(player: Player, team)
	local room = roomOf[player]
	if not room or room.mode ~= "pvp" then return false, "Ez a szoba nem csapatharc" end
	if team ~= "A" and team ~= "B" then return false end
	if player and room.team[player] == team then return true end
	if Rooms.hooks.canSwitch and not Rooms.hooks.canSwitch(player, room) then return false, "Repülés közben nem lehet csapatot váltani" end
	room.team[player] = team
	Rooms.push(room)
	return true
end

function Rooms.setSlots(player: Player, extra)
	local room = roomOf[player]
	if not room or room.host ~= player then return false, "Csak a szoba nyitója állíthatja" end
	extra = math.clamp(math.floor(tonumber(extra) or 0), 0, R.MaxPlayers - 1)
	room.max = math.max(Rooms.count(room), 1 + extra)
	Rooms.push(room)
	return true, room.max
end

function Rooms.score(room, team: string)
	room.score[team] = (room.score[team] or 0) + 1
end

function Rooms.init(r)
	remotes = r
	remotes.ListRooms.OnServerInvoke = function() return Rooms.list() end
	remotes.CreateRoom.OnServerInvoke = function(player, name, mode, extra, private) return Rooms.create(player, name, mode, extra, private) end
	remotes.JoinRoom.OnServerInvoke = function(player, ref) return Rooms.join(player, ref) end
	remotes.LeaveRoom.OnServerInvoke = function(player) Rooms.leave(player) return true end
	remotes.QuickPlay.OnServerInvoke = function(player) return Rooms.quickPlay(player) end
	remotes.SetTeam.OnServerInvoke = function(player, team) return Rooms.setTeam(player, team) end
	remotes.SetSlots.OnServerInvoke = function(player, extra) return Rooms.setSlots(player, extra) end
	Players.PlayerRemoving:Connect(function(player) Rooms.leave(player) end)
end

-- the open rear seats change: now and then everybody gets the fresh state
function Rooms.step(dt: number)
	Rooms._t = (Rooms._t or 0) + dt
	if Rooms._t < 1.5 then return end
	Rooms._t = 0
	for _, room in rooms do Rooms.push(room) end
end

return Rooms
