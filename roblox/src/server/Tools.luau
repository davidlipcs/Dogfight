--!nonstrict
-- Helpers for the Command Bar of Roblox Studio (View > Command Bar), run in edit mode.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)

local Tools = {}

-- the jet key an imported instance belongs to: the name without ".glb", a "(1)" suffix or case ("F16.glb" -> f16)
local function keyOf(name: string): string?
	local n = string.lower(name)
	n = string.gsub(n, "%.glb$", "")
	n = string.gsub(n, "%s*%(%d+%)$", "")
	n = string.gsub(n, "[%s_%-]+$", "")
	for _, j in Config.JetModels do
		if j.key == n then return j.key end
	end
	return nil
end

local function containsParts(inst: Instance): boolean
	if inst:IsA("BasePart") then return true end
	for _, d in inst:GetDescendants() do
		if d:IsA("BasePart") then return true end
	end
	return false
end

-- Moves the imported jet models (the .glb files imported with Bulk Import, named f16, fa18, ...) from the Workspace (also
-- from inside folders / the Import group) into ReplicatedStorage.JetModels, where the game looks for them.  It runs by
-- itself when the server starts (so a forgotten step costs nothing); by hand:
--   require(game.ServerScriptService.Server.Tools).adoptJets()
function Tools.adoptJets()
	local folder = ReplicatedStorage:FindFirstChild("JetModels")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "JetModels"
		folder.Parent = ReplicatedStorage
	end
	local n = 0
	local found, keys = {}, {}
	for _, c in workspace:GetDescendants() do
		if c:IsA("Model") or c:IsA("MeshPart") or c:IsA("Folder") then
			local key = keyOf(c.Name)
			if key and containsParts(c) then
				table.insert(found, c)
				table.insert(keys, key)
			end
		end
	end
	for i, c in ipairs(found) do
		local key = keys[i]
		if not folder:FindFirstChild(key) and c.Parent then
			if c:IsA("MeshPart") then
				local m = Instance.new("Model")
				m.Name = key
				m.Parent = folder
				c.Parent = m
			else
				c.Name = key
				c.Parent = folder
			end
			n += 1
		end
	end
	local have = 0
	for _, j in Config.JetModels do
		if folder:FindFirstChild(j.key) then have += 1 end
	end
	print(string.format("Dogfight Plus: %d jet model(s) moved to ReplicatedStorage.JetModels (now %d of %d).%s", n, have, #Config.JetModels,
		RunService:IsStudio() and not RunService:IsRunning() and " Save the place (File > Save)." or ""))
	return have
end

-- Lists which jets are imported.
function Tools.listJets()
	local folder = ReplicatedStorage:FindFirstChild("JetModels")
	for _, j in Config.JetModels do
		print(j.key, folder and folder:FindFirstChild(j.key) and "imported" or "-")
	end
end

return Tools
