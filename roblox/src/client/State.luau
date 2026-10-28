--!nonstrict
-- What the client knows about its room (filled from the server's RoomState events), shared by the screens.
local State = {
	room = nil,        -- the last RoomState table, or nil when not in a room
	roomId = nil,
	team = "A",
	mode = "coop",
	listeners = {},
}

function State.set(room)
	State.room = room
	State.roomId = room and room.id or nil
	State.mode = room and room.mode or "coop"
	State.team = "A"
	if room then
		for _, m in room.members do
			if m.userId == game:GetService("Players").LocalPlayer.UserId then State.team = m.team end
		end
	end
	for _, f in State.listeners do f(room) end
end

function State.onChange(f)
	table.insert(State.listeners, f)
end

-- is this jet / enemy model of my room?
function State.mine(model: Instance): boolean
	return State.roomId ~= nil and model:GetAttribute("RoomId") == State.roomId
end

-- hostile to me: the AI of my room, or (in a team fight) a jet of the other team
function State.hostile(model: Instance): boolean
	if not State.mine(model) then return false end
	if model.Parent == workspace:FindFirstChild("Enemies") then return true end
	if State.mode == "pvp" and model.Parent == workspace:FindFirstChild("Jets") then
		return model:GetAttribute("Team") ~= State.team and model:GetAttribute("OwnerId") ~= game:GetService("Players").LocalPlayer.UserId
	end
	return false
end

return State
