#!/usr/bin/env python3
"""Builds roblox/build/DogfightPlugin.rbxmx: a Roblox Studio PLUGIN (put it into the Plugins folder, Studio > Plugins > Plugins Folder) that adds
three buttons to the Plugins tab, so nothing has to be typed into the Command Bar:
  - "Kód telepítése"  puts the game's code into the open place (replaces ReplicatedStorage.Shared, ServerScriptService.Server, StarterPlayerScripts.Client)
  - "Sziget építése"  builds the island (IslandBuilder.build(), once; takes a few minutes)
  - "Gépek átemelése" moves the imported jet models into ReplicatedStorage.JetModels (Tools.adoptJets())
The code itself is inside the plugin file, so a new version = a new plugin file."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_rbxlx as B

PLUGIN = r'''-- Dogfight Plus: the plugin (see tools/build_plugin.py)
local ChangeHistoryService = game:GetService("ChangeHistoryService")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")
local SP = game:GetService("StarterPlayer"):WaitForChild("StarterPlayerScripts")

local toolbar = plugin:CreateToolbar("Dogfight Plus")
local bInstall = toolbar:CreateButton("DogfightInstall", "A játék kódjának telepítése ebbe a pályába (a sziget és a gépek megmaradnak)", "", "Kód telepítése")
local bIsland = toolbar:CreateButton("DogfightIsland", "A sziget felépítése (csak egyszer; pár percig tart)", "", "Sziget építése")
local bJets = toolbar:CreateButton("DogfightJets", "A beimportált gépek áttétele a helyükre", "", "Gépek átemelése")
for _, b in { bInstall, bIsland, bJets } do b.ClickableWhenViewportHidden = true end

local function enableScripts(root)
	for _, d in root:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") then d.Disabled = false end
	end
end

local function swap(parent, name)
	local old = parent:FindFirstChild(name)
	if old then old:Destroy() end
	local new = script[name]:Clone()
	new.Parent = parent
	enableScripts(new)
end

-- leftovers of older versions (a second copy of the scripts runs a second menu / game on top of the first one): removed
local KNOWN = { Main = true, Lobby = true, Game = true, Hud = true, Flight = true, Wso = true, Visibility = true, Combat = true, Enemies = true, Shop = true, Data = true,
	Rooms = true, World = true, Tools = true, Daily = true, IslandBuilder = true, Menu = true, View = true, RoomsUi = true, Ui = true, State = true, Visor = true,
	Config = true, Catalog = true, Remotes = true, JetBuilder = true, DeviceInput = true, GuiCanvas = true, Env = true, Fx = true, Sounds = true, WarUi = true, RadioUi = true }
local FOLDERS = { Client = true, Server = true, Shared = true, DogfightCodeUpdate = true }
local function cleanup()
	local keep = { RS:FindFirstChild("Shared"), SSS:FindFirstChild("Server"), SP:FindFirstChild("Client") }
	local function kept(inst)
		for _, k in keep do
			if k and (inst == k or inst:IsDescendantOf(k)) then return true end
		end
		return false
	end
	local roots = { workspace, game:GetService("StarterGui"), game:GetService("StarterPack"), game:GetService("ReplicatedFirst"), game:GetService("ServerStorage"),
		SSS, game:GetService("StarterPlayer"), RS, game:GetService("Lighting") }
	local removed = {}
	for _, root in roots do
		for _, d in root:GetDescendants() do
			if not kept(d) and d.Parent and ((d:IsA("LuaSourceContainer") and KNOWN[d.Name]) or (d:IsA("Folder") and FOLDERS[d.Name]) or (d:IsA("Model") and d.Name == "DogfightCodeUpdate")) then
				table.insert(removed, d:GetFullName())
				d:Destroy()
			end
		end
	end
	if #removed > 0 then
		print("Dogfight Plus: leftovers of older versions removed: " .. table.concat(removed, ", "))
	end
end

bInstall.Click:Connect(function()
	bInstall:SetActive(false)
	ChangeHistoryService:SetWaypoint("Dogfight Plus: before the code")
	swap(RS, "Shared")
	swap(SSS, "Server")
	swap(SP, "Client")
	cleanup()
	game:GetService("Players").CharacterAutoLoads = false
	ChangeHistoryService:SetWaypoint("Dogfight Plus: the code")
	print("Dogfight Plus: the code is installed. Now File > Save, then Play.")
end)

bIsland.Click:Connect(function()
	bIsland:SetActive(false)
	local server = SSS:FindFirstChild("Server")
	local builder = server and server:FindFirstChild("IslandBuilder")
	if not builder then warn("Dogfight Plus: install the code first (the button 'Kód telepítése')") return end
	print("Dogfight Plus: building the island... (a few minutes; do not press Play)")
	local ok, err = pcall(function() require(builder).build() end)
	if not ok then warn("Dogfight Plus: the island could not be built: ", err) else print("Dogfight Plus: now File > Save.") end
end)

bJets.Click:Connect(function()
	bJets:SetActive(false)
	local server = SSS:FindFirstChild("Server")
	local tools = server and server:FindFirstChild("Tools")
	if not tools then warn("Dogfight Plus: install the code first (the button 'Kód telepítése')") return end
	local ok, err = pcall(function() require(tools).adoptJets() end)
	if not ok then warn("Dogfight Plus: ", err) else print("Dogfight Plus: now File > Save.") end
end)

print("Dogfight Plus plugin ready: the Plugins tab has the buttons.")
'''


def main():
    out = os.path.join(B.ROOT, "roblox", "build", "DogfightPlugin.rbxmx")
    orig = B.script_item

    def disabled(path, fname):
        s = orig(path, fname)
        if re.match(r'<Item class="(Script|LocalScript)"', s):
            s = s.replace("<Properties>", '<Properties><bool name="Disabled">true</bool>', 1)
        return s
    B.script_item = disabled
    kids = B.folder_item("Shared", os.path.join(B.SRC, "shared")) + B.folder_item("Server", os.path.join(B.SRC, "server")) + B.folder_item("Client", os.path.join(B.SRC, "client"))
    body = PLUGIN.replace("]]>", "]]]]><![CDATA[>")
    plugin = B.item("Script", "DogfightPlus", '<ProtectedString name="Source"><![CDATA[%s]]></ProtectedString>' % body, kids)
    xml = ('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">\n%s</roblox>\n') % plugin
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print("wrote %s (%d KB)" % (out, len(xml) // 1024))


if __name__ == "__main__":
    main()
