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
	for pilot, seat in room.seats do
		if seat.open and not seat.wso then
			table.insert(seats, { userId = pilot.UserId, name = pilot.DisplayName, team = room.team[pilot] or "A", a = seat.a, lo = seat.lo })
		end
	end
	table.sort(seats, function(x, y) return x.userId < y.userId end)
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
	room.seats[player] = nil
	for _, seat in room.seats do
		if seat.wso == player then seat.wso = nil end
	end
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
	extra = tonumber(extra) or 3
	if extra ~= extra then extra = 3 end
	extra = math.clamp(math.floor(extra), 0, R.MaxPlayers - 1)
	local room = {
		id = nextId, name = filtered(name ~= "" and name or (player.DisplayName .. " szobája"), player), host = player,
		mode = mode == "pvp" and "pvp" or "coop", max = 1 + extra, private = private == true, code = nil,
		members = {}, team = {}, seats = {}, score = { A = 0, B = 0 }, created = os.time(),
	}
	if player.Parent == nil then return false, "Kiléptél" end                -- (the name filter yields: the player may be gone)
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
	extra = tonumber(extra) or 0
	if extra ~= extra then extra = 0 end
	extra = math.clamp(math.floor(extra), 0, R.MaxPlayers - 1)
	room.max = math.max(Rooms.count(room), 1 + extra)
	Rooms.push(room)
	return true, room.max
end

-- the pilot of a two-seat jet opens / closes the rear seat: the aircraft key and the loadout (a list of { station, weapon }) of the jet
function Rooms.openSeat(player: Player, open, aircraft, loadout)
	local room = roomOf[player]
	if not room then return false, "Nem vagy szobában" end
	if open ~= true then
		room.seats[player] = nil
		Rooms.push(room)
		return true
	end
	if typeof(aircraft) ~= "string" or #aircraft > 12 then return false end
	local lo = {}
	if typeof(loadout) == "table" then
		for _, pair in loadout do
			if typeof(pair) == "table" and typeof(pair[1]) == "number" and typeof(pair[2]) == "string" and #lo < 16 and #pair[2] <= 12 then
				table.insert(lo, { pair[1], pair[2] })
			end
		end
	end
	local old = room.seats[player]
	room.seats[player] = { open = true, a = aircraft, lo = lo, wso = old and old.wso or nil }
	Rooms.push(room)
	return true
end

-- a team mate sits in the rear seat of the pilot's jet.  -> true, the seat ({ a, lo, team }) or false, why
function Rooms.joinSeat(player: Player, pilotUserId)
	local room = roomOf[player]
	if not room then return false, "Nem vagy szobában" end
	local pilot = nil
	for p in room.members do
		if p.UserId == pilotUserId then pilot = p end
	end
	local seat = pilot and room.seats[pilot]
	if not pilot or pilot == player or not seat or not seat.open then return false, "Ez az ülés nem szabad" end
	if seat.wso and seat.wso ~= player then return false, "Már ül valaki a hátsó ülésen" end
	if room.mode == "pvp" and room.team[pilot] ~= room.team[player] then return false, "Csak a saját csapatod gépébe ülhetsz be" end
	for _, other in room.seats do
		if other.wso == player then other.wso = nil end
	end
	seat.wso = player
	Rooms.push(room)
	return true, { a = seat.a, lo = seat.lo, team = room.team[pilot] or "A", pilot = pilot.UserId }
end

function Rooms.leaveSeat(player: Player)
	local room = roomOf[player]
	if not room then return true end
	for _, seat in room.seats do
		if seat.wso == player then seat.wso = nil end
	end
	Rooms.push(room)
	return true
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
	remotes.OpenSeat.OnServerInvoke = function(player, open, aircraft, loadout) return Rooms.openSeat(player, open, aircraft, loadout) end
	remotes.JoinSeat.OnServerInvoke = function(player, pilotUserId) return Rooms.joinSeat(player, pilotUserId) end
	remotes.LeaveSeat.OnServerInvoke = function(player) return Rooms.leaveSeat(player) end
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
