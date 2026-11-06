#!/usr/bin/env python3
"""Builds roblox/build/DogfightPlugin.rbxmx: a Roblox Studio PLUGIN (put it into the Plugins folder, Studio > Plugins > Plugins Folder) that adds
three buttons to the Plugins tab, so nothing has to be typed into the Command Bar - and, when a place is opened in Studio, does by itself
what is missing (installs the code into an empty place or updates an older copy, builds the island once, moves imported jets where the
game looks for them) and shows how far it is in a small window:
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

-- ============ the steps (the buttons and the automatic setup use the same ones)
local function hasCode()
	local server = SSS:FindFirstChild("Server")
	return server ~= nil and server:FindFirstChild("Main") ~= nil and RS:FindFirstChild("Shared") ~= nil and SP:FindFirstChild("Client") ~= nil
end

local function versionOf(shared)
	local cfg = shared and shared:FindFirstChild("Config")
	if not cfg then return nil end
	local ok, c = pcall(require, cfg)
	return ok and type(c) == "table" and tostring(c.Version) or nil
end

local function install()
	ChangeHistoryService:SetWaypoint("Dogfight Plus: before the code")
	swap(RS, "Shared")
	swap(SSS, "Server")
	swap(SP, "Client")
	cleanup()
	game:GetService("Players").CharacterAutoLoads = false
	workspace:SetAttribute("DogfightServerRunning", nil)
	ChangeHistoryService:SetWaypoint("Dogfight Plus: the code")
	print("Dogfight Plus: the code (" .. tostring(versionOf(script.Shared)) .. ") is installed.")
end

local status = { code = "?", island = "?", jets = "?" }
local widget, label
local function show()
	if not label then return end
	local need = {}
	if status.code ~= "ok" then table.insert(need, "a kód") end
	if status.island ~= "ok" then table.insert(need, "a sziget") end
	local lines = {
		"<b>DOGFIGHT PLUS – beállítás</b>",
		"",
		"Kód: " .. (status.code == "ok" and "✔ telepítve" or status.code),
		"Sziget: " .. (status.island == "ok" and "✔ kész" or status.island),
		"Gépek: " .. status.jets,
		"",
	}
	if status.busy then
		table.insert(lines, "<font color='#ffc840'>Dolgozom… ne nyomd meg a Play-t, amíg ez tart.</font>")
	elseif #need == 0 then
		table.insert(lines, "<font color='#6bff85'><b>Minden kész.</b> Mentsd el: File → Save (Ctrl+S), és utána mehet a Play.</font>")
	else
		table.insert(lines, "<font color='#ff9a8a'>Hiányzik: " .. table.concat(need, ", ") .. ".</font>")
	end
	label.Text = table.concat(lines, "\n")
end

local function buildIsland()
	local server = SSS:FindFirstChild("Server")
	local builder = server and server:FindFirstChild("IslandBuilder")
	if not builder then warn("Dogfight Plus: install the code first") return end
	status.busy = true
	status.island = "épül… 0%"
	show()
	print("Dogfight Plus: building the island... (a few minutes; do not press Play)")
	local ok, err = pcall(function()
		require(builder).build(function(f) status.island = string.format("épül… %d%%", math.floor(f * 100)); show() end)
	end)
	status.busy = false
	if ok then
		status.island = "ok"
		print("Dogfight Plus: the island is built. Now File > Save.")
	else
		status.island = "nem sikerült: " .. tostring(err)
		warn("Dogfight Plus: the island could not be built: ", err)
	end
	show()
end

local function adoptJets(quiet)
	local server = SSS:FindFirstChild("Server")
	local tools = server and server:FindFirstChild("Tools")
	if not tools then return end
	local ok, have = pcall(function() return require(tools).adoptJets() end)
	if ok then
		local total = 16
		status.jets = (type(have) == "number" and have >= total) and "✔ mind a 16 megvan" or
			string.format("%s / 16 – a hiányzókat: Import 3D (a gépek zipjéből), ide magától átkerülnek", tostring(have or 0))
	elseif not quiet then
		warn("Dogfight Plus: ", have)
	end
	show()
end

bInstall.Click:Connect(function()
	bInstall:SetActive(false)
	install()
	status.code = "ok"
	show()
	print("Dogfight Plus: now File > Save, then Play.")
end)

bIsland.Click:Connect(function()
	bIsland:SetActive(false)
	task.spawn(buildIsland)
end)

bJets.Click:Connect(function()
	bJets:SetActive(false)
	adoptJets(false)
end)

-- ============ automatic setup: when a place is opened in Studio (not in a Play test), the plugin does what is missing by itself
local RunService = game:GetService("RunService")
if RunService:IsEdit() then
	local ok = pcall(function()
		widget = plugin:CreateDockWidgetPluginGui("DogfightSetup", DockWidgetPluginGuiInfo.new(Enum.InitialDockState.Float, true, false, 420, 230, 320, 180))
		widget.Title = "Dogfight Plus"
		label = Instance.new("TextLabel")
		label.Size = UDim2.fromScale(1, 1)
		label.BackgroundColor3 = Color3.fromRGB(18, 24, 28)
		label.TextColor3 = Color3.fromRGB(225, 232, 228)
		label.Font = Enum.Font.GothamMedium
		label.TextSize = 15
		label.RichText = true
		label.TextWrapped = true
		label.TextXAlignment = Enum.TextXAlignment.Left
		label.TextYAlignment = Enum.TextYAlignment.Top
		local pad = Instance.new("UIPadding")
		pad.PaddingLeft, pad.PaddingTop, pad.PaddingRight = UDim.new(0, 12), UDim.new(0, 10), UDim.new(0, 12)
		pad.Parent = label
		label.Parent = widget
	end)
	if not ok then widget, label = nil, nil end

	task.spawn(function()
		task.wait(1)
		-- the code: installed into an empty place, updated in a place that has an older version; another game's place is left alone
		local function otherScripts()
			local n = 0
			for _, root in { SSS, SP, workspace, game:GetService("StarterGui"), game:GetService("ReplicatedFirst") } do
				for _, d in root:GetDescendants() do
					if d:IsA("LuaSourceContainer") and not KNOWN[d.Name] then
						local inOurs = false
						for _, k in { RS:FindFirstChild("Shared"), SSS:FindFirstChild("Server"), SP:FindFirstChild("Client") } do
							if k and d:IsDescendantOf(k) then inOurs = true end
						end
						if not inOurs then n += 1 end
					end
				end
			end
			return n
		end
		local mine, placed = versionOf(script.Shared), versionOf(RS:FindFirstChild("Shared"))
		if not hasCode() then
			if otherScripts() == 0 then
				install()
				status.code = "ok"
			else
				status.code = "nincs telepítve (ebben a pályán más szkriptek is vannak) – Plugins fül → Kód telepítése"
			end
		elseif placed ~= mine then
			print(string.format("Dogfight Plus: the place has the code %s, the plugin %s: updating.", tostring(placed), tostring(mine)))
			install()
			status.code = "ok"
		else
			status.code = "ok"
		end
		show()
		if status.code ~= "ok" then return end
		-- the jets: the imported ones are moved where the game looks for them, now and whenever new ones are imported
		adoptJets(true)
		local pending = false
		workspace.ChildAdded:Connect(function(child)
			if pending or not (child:IsA("Model") or child:IsA("BasePart")) then return end
			pending = true
			task.delay(2, function() pending = false; adoptJets(true) end)
		end)
		-- the island: built once (the place keeps it after File > Save)
		if workspace:GetAttribute("IslandBuilt") == true then
			status.island = "ok"
			show()
		else
			buildIsland()
		end
	end)
end

print("Dogfight Plus plugin ready: it sets the place up by itself (the window 'Dogfight Plus' shows how far); the Plugins tab has the buttons too.")
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
