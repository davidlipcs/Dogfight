#!/usr/bin/env python3
"""Builds roblox/build/DogfightCode.rbxmx: only the CODE of the game (the three script folders) with a one-line installer, to put into a place
that already has the island built and the jets imported - so a new version never means building the island again.
In Studio: drag the file into the 3D view (or right click Workspace > Insert from File), then in the Command Bar:
    require(workspace.DogfightCodeUpdate.Install)()
then File > Save."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_rbxlx as B

INSTALL = '''-- Replaces the game's code in this place (ReplicatedStorage.Shared, ServerScriptService.Server, StarterPlayerScripts.Client) with the new one.
-- The island, the imported jets and everything else in the place stay as they are.
return function()
	local RS = game:GetService("ReplicatedStorage")
	local SSS = game:GetService("ServerScriptService")
	local SP = game:GetService("StarterPlayer"):WaitForChild("StarterPlayerScripts")
	local pack = script.Parent
	local function swap(parent, name)
		local old = parent:FindFirstChild(name)
		if old then old:Destroy() end
		pack[name].Parent = parent
	end
	swap(RS, "Shared")
	swap(SSS, "Server")
	swap(SP, "Client")
	game:GetService("Players").CharacterAutoLoads = false
	pack:Destroy()
	print("Dogfight Plus: the code is updated. File > Save, then Play.")
end
'''


def main():
    out = os.path.join(B.ROOT, "roblox", "build", "DogfightCode.rbxmx")
    kids = B.folder_item("Shared", os.path.join(B.SRC, "shared")) + B.folder_item("Server", os.path.join(B.SRC, "server")) + B.folder_item("Client", os.path.join(B.SRC, "client"))
    body = INSTALL.replace("]]>", "]]]]><![CDATA[>")
    kids += B.item("ModuleScript", "Install", '<ProtectedString name="Source"><![CDATA[%s]]></ProtectedString>' % body)
    model = B.item("Model", "DogfightCodeUpdate", "", kids)
    xml = ('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">\n%s</roblox>\n') % model
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print("wrote %s (%d KB)" % (out, len(xml) // 1024))


if __name__ == "__main__":
    main()
