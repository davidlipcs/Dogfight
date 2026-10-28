--!nonstrict
-- Several rooms share one sky, but you only see your own: the jets, enemies and missiles of the other rooms are
-- made invisible here (on this client only).
local State = require(script.Parent.State)

local Visibility = {}

local function apply(model: Instance)
	local hidden = State.roomId ~= nil and model:GetAttribute("RoomId") ~= State.roomId
	local function one(d: Instance)
		if d:IsA("BasePart") then d.LocalTransparencyModifier = hidden and 1 or 0
		elseif d:IsA("Trail") or d:IsA("PointLight") then d.Enabled = not hidden end
	end
	one(model)
	for _, d in model:GetDescendants() do one(d) end
end

function Visibility.init()
	for _, name in { "Jets", "Enemies", "Missiles" } do
		local f = workspace:WaitForChild(name)
		f.ChildAdded:Connect(function(c) task.defer(apply, c) end)
		for _, c in f:GetChildren() do apply(c) end
	end
	State.onChange(function()
		for _, name in { "Jets", "Enemies", "Missiles" } do
			for _, c in workspace[name]:GetChildren() do apply(c) end
		end
	end)
	-- a sweep now and then (the seat parts of a jet appear later)
	task.spawn(function()
		while true do
			task.wait(1)
			for _, name in { "Jets", "Enemies", "Missiles" } do
				for _, c in workspace[name]:GetChildren() do apply(c) end
			end
		end
	end)
end

return Visibility
