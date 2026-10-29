#!/usr/bin/env python3
"""Builds roblox/build/DogfightPlus.rbxlx (a Roblox place file) from roblox/src without Rojo.
Open it in Roblox Studio, or publish it with tools/roblox_publish.py.  (With Rojo: `rojo build roblox -o DogfightPlus.rbxlx`.)

Layout (the same as roblox/default.project.json):
  ReplicatedStorage/Shared                        <- src/shared   (ModuleScripts)
  ServerScriptService/Server                      <- src/server   (Main.server.luau = Script, the rest ModuleScripts)
  StarterPlayer/StarterPlayerScripts/Client       <- src/client   (Main.client.luau = LocalScript, the rest ModuleScripts)
"""
import os
import sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "roblox", "src")
OUT = os.path.join(ROOT, "roblox", "build", "DogfightPlus.rbxlx")

_ref = [0]


def ref():
    _ref[0] += 1
    return "RBX%d" % _ref[0]


def item(cls, name, props="", children=""):
    return '<Item class="%s" referent="%s"><Properties><string name="Name">%s</string>%s</Properties>%s</Item>\n' % (
        cls, ref(), escape(name), props, children)


def version():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip() + "+" + subprocess.check_output(["date", "+%d.%H%M"]).decode().strip()
    except Exception:
        return "dev"


def script_item(path, fname):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if fname == "Config.luau":
        src = src.replace('Config.Version = "dev"', 'Config.Version = "%s"' % version(), 1)
    if fname.endswith(".server.luau"):
        cls, name = "Script", fname[: -len(".server.luau")]
    elif fname.endswith(".client.luau"):
        cls, name = "LocalScript", fname[: -len(".client.luau")]
    else:
        cls, name = "ModuleScript", fname[: -len(".luau")]
    body = src.replace("]]>", "]]]]><![CDATA[>")                 # a CDATA section cannot contain ]]>
    props = '<ProtectedString name="Source"><![CDATA[%s]]></ProtectedString>' % body
    return item(cls, name, props)


def folder_item(name, directory):
    kids = ""
    for fname in sorted(os.listdir(directory)):
        full = os.path.join(directory, fname)
        if fname.endswith(".luau"):
            kids += script_item(full, fname)
        elif os.path.isdir(full):
            kids += folder_item(fname, full)               # sim/, game/ ...
    return item("Folder", name, "", kids)


def main():
    parts = []
    parts.append(item("Workspace", "Workspace", '<float name="Gravity">196.2</float>'))
    parts.append(item("ReplicatedStorage", "ReplicatedStorage", "", folder_item("Shared", os.path.join(SRC, "shared"))))
    parts.append(item("ServerScriptService", "ServerScriptService", "", folder_item("Server", os.path.join(SRC, "server"))))
    parts.append(item("StarterPlayer", "StarterPlayer", "", item("StarterPlayerScripts", "StarterPlayerScripts", "", folder_item("Client", os.path.join(SRC, "client")))))
    parts.append(item("Players", "Players", '<bool name="CharacterAutoLoads">false</bool>'))
    parts.append(item("Lighting", "Lighting", '<double name="ClockTime">14</double>'))
    xml = ('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">\n<Meta name="ExplicitAutoJoints">true</Meta>\n%s</roblox>\n') % "".join(parts)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(xml)
    print("wrote %s (%d KB, %d scripts)" % (OUT, len(xml) // 1024, xml.count("<ProtectedString")))


if __name__ == "__main__":
    sys.exit(main())
