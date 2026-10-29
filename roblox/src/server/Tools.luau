--!nonstrict
-- Helpers for the Command Bar of Roblox Studio (View > Command Bar), run in edit mode.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)

local Tools = {}

-- the jet key an imported instance belongs to: its name without ".glb", "(1)" and the like, case and punctuation ignored, so that
-- "F16.glb", "f-16", "F16C Viper", "Su-35" and "MiG29 (1)" all find their jet
local function keyOf(name: string): string?
	local n = string.lower(name)
	n = string.gsub(n, "%.glb$", "")
	n = string.gsub(n, "[^%w]", "")
	for _, j in Config.JetModels do
		if j.key == n then return j.key end
	end
	-- a longer name that starts with the key ("f16cviper", "typhoonfgr4"); the longest key wins ("t6" must not take "t60...")
	local best = nil
	for _, j in Config.JetModels do
		if string.sub(n, 1, #j.key) == j.key and (not best or #j.key > #best) then best = j.key end
	end
	return best
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
	local places = { workspace, game:GetService("ServerStorage"), game:GetService("Lighting"), game:GetService("ReplicatedFirst") }
	local scan = {}
	for _, root in ipairs(places) do
		for _, d in root:GetDescendants() do table.insert(scan, d) end
	end
	for _, c in scan do
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
		if c.Parent and not c:IsDescendantOf(folder) and not (found[i - 1] and c:IsDescendantOf(found[i - 1])) then
			local old = folder:FindFirstChild(key)
			if old then old:Destroy() end                                   -- a fresh import replaces the old model of the same jet
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
	-- what is lying in the Workspace that looks like a model but was not taken (the names help to find out why)
	local others = {}
	for _, c in workspace:GetChildren() do
		if (c:IsA("Model") or c:IsA("Folder") or c:IsA("MeshPart")) and c.Name ~= "Visuals" and c.Name ~= "Preview" and c.Name ~= "Camera" and containsParts(c) and not keyOf(c.Name) then
			table.insert(others, c.Name)
		end
	end
	if #others > 0 then
		warn("Dogfight Plus: models in the Workspace whose name is not a jet key (rename them to f16, fa18, f15, f22, f35, gripen, typhoon, rafale, su35, su57, mig29, mig31, j20, t38, t45, t6): " .. table.concat(others, ", "))
	end
	local names = {}
	for _, c in folder:GetChildren() do table.insert(names, c.Name) end
	table.sort(names)
	print("Dogfight Plus: in ReplicatedStorage.JetModels: " .. (#names > 0 and table.concat(names, ", ") or "(nothing)"))
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
