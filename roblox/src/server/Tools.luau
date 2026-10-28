--!nonstrict
-- Helpers for the Command Bar of Roblox Studio (View > Command Bar), run in edit mode.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)

local Tools = {}

-- Moves the imported jet models (the .glb files imported with File > Import 3D, named f16, fa18, ...) from the
-- Workspace into ReplicatedStorage.JetModels, where the game looks for them.   require(game.ServerScriptService.Server.Tools).adoptJets()
function Tools.adoptJets()
	local folder = ReplicatedStorage:FindFirstChild("JetModels")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "JetModels"
		folder.Parent = ReplicatedStorage
	end
	local n = 0
	for _, j in Config.JetModels do
		for _, c in workspace:GetChildren() do
			if c.Name == j.key and (c:IsA("Model") or c:IsA("MeshPart") or c:IsA("Folder")) then
				if c:IsA("MeshPart") then
					local m = Instance.new("Model")
					m.Name = j.key
					c.Parent = m
					c = m
				end
				c.Parent = folder
				n += 1
			end
		end
	end
	print(string.format("Dogfight Plus: %d jet model(s) moved to ReplicatedStorage.JetModels (now: %d). Save the place.", n, #folder:GetChildren()))
end

-- Lists which jets are imported.
function Tools.listJets()
	local folder = ReplicatedStorage:FindFirstChild("JetModels")
	for _, j in Config.JetModels do
		print(j.key, folder and folder:FindFirstChild(j.key) and "imported" or "-")
	end
end

return Tools
