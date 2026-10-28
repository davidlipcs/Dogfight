--!nonstrict
-- The remote events and functions between the server and the players.  The server creates them (Remotes.init()),
-- the clients wait for them (Remotes.get()).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Remotes = {}

local EVENTS = {
	"Fire",           -- client -> server: the gun is firing
	"FireMissile",    -- client -> server: a missile at an enemy (the Model)
	"Flare",          -- client -> server: drop flares
	"Crashed",        -- client -> server: my jet hit the ground / the sea
	"Launch",         -- client -> server: take off (kind: "single" or "twoseat")
	"Mark",           -- client -> server: the rear seat marks an enemy (the Model) for the pilot
	"Seat",           -- server -> client: you sit in the rear seat of this jet (the Model), or nil: you left it
	"RoomState",      -- server -> client: the room you are in (members, teams, open rear seats)
	"Tracer",         -- server -> clients: a line of tracer fire (from, to, color)
	"Hud",            -- server -> client: { wave, enemies, missiles, flares, hp }
	"Toast",          -- server -> client: a short message (text, kind)
	"MissileAlert",   -- server -> client: true / false, a missile is coming at you
	"Died",           -- server -> client: the jet is gone (reason)
	"Profile",        -- server -> client: the coins, the owned and the equipped things
	"Earn",           -- client -> server: coins earned in the match (the server limits the rate)
	"SaveCareer",     -- client -> server: the career table (kills, medals ...)
	"Net",            -- both ways: a batch of messages of the match (shared/game/Net.luau); the server hands it to the others of the room
	"SaveBest",       -- client -> server: a race record (kind "race" / "canyon" / "tube", time, best lap)
}
local FUNCTIONS = {
	"BuyAir", "BuyPilot", "EquipAir", "EquipPilot", "EquipJet",    -- shop: (id) -> ok, message
	"BuyProduct", "BuyPass",                            -- Robux: (index) -> ok
	"GetProfile",
	"ClaimDaily", "GetMissions", "ClaimMission", "GetLeaderboard",   -- the daily reward, the daily missions, the top list
	"BuySkinRobux",                                     -- (kind "air"/"pilot", id): the Robux purchase of a skin
	"ListRooms", "CreateRoom", "JoinRoom", "LeaveRoom", "QuickPlay", "SetTeam", "SetSlots",   -- the hangar groups
	"OpenSeat", "JoinSeat", "LeaveSeat",                -- the rear seat of a two-seat jet: the pilot opens it (open, aircraft key, loadout pairs), a team mate takes / leaves it
}

function Remotes.init()
	local folder = Instance.new("Folder")
	folder.Name = "Remotes"
	for _, n in EVENTS do
		local e = Instance.new("RemoteEvent")
		e.Name = n
		e.Parent = folder
	end
	for _, n in FUNCTIONS do
		local f = Instance.new("RemoteFunction")
		f.Name = n
		f.Parent = folder
	end
	folder.Parent = ReplicatedStorage
	return folder
end

function Remotes.get()
	local folder = ReplicatedStorage:WaitForChild("Remotes")
	local t = {}
	for _, n in EVENTS do t[n] = folder:WaitForChild(n) end
	for _, n in FUNCTIONS do t[n] = folder:WaitForChild(n) end
	return t
end

return Remotes
