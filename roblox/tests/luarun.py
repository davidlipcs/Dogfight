"""Runs the Luau sim modules of roblox/src/shared/sim under Lua 5.4 (lupa), with Roblox's require / script / bit32 shimmed."""
import json
import os
import sys
from lupa import LuaRuntime

_here = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_here, 'root.txt')):                      # written by prepare.sh
    ROOT = open(os.path.join(_here, 'root.txt')).read().strip()
else:
    ROOT = os.path.dirname(os.path.dirname(_here))
SIM = os.path.join(ROOT, 'roblox/src/shared/sim')
SHARED = os.path.join(ROOT, 'roblox/src/shared')
GAME = os.path.join(ROOT, 'roblox/src/shared/game')


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        local function mk(name) return setmetatable({ __n = name }, { __index = function(_, k) return mk(k) end }) end
        script = { Parent = mk("Parent") }
        __loaded = {}
        __paths = {}
        function require(name)
            if type(name) == "table" then name = rawget(name, "__n") end
            if __loaded[name] ~= nil then return __loaded[name] end
            local path = __paths[name]
            if not path then error("module not found: " .. tostring(name)) end
            local f = assert(io.open(path, "r"))
            local src = f:read("a")
            f:close()
            local chunk = assert(load(src, "@" .. name, "t"))
            local r = chunk()
            __loaded[name] = r
            return r
        end
    ''')
    paths = lua.eval('__paths')
    for d in (SIM, SHARED, GAME):
        for f in os.listdir(d):
            if f.endswith('.luau'):
                paths[f[:-5]] = os.path.join(d, f)
    return lua


def to_py(o):
    from lupa import lua_type
    if lua_type(o) == 'table':
        keys = list(o.keys())
        if keys and all(isinstance(k, int) for k in keys):
            return [to_py(o[k]) for k in sorted(keys)]
        return {str(k): to_py(o[k]) for k in keys}
    return o


def compare(a, b, path='', tol=1e-9, out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in b:
                compare(a[k], b[k], path + '.' + k, tol, out)
            else:
                out.append(f'{path}.{k}: missing in lua')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'{path}: length {len(a)} vs {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f'{path}[{i}]', tol, out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if abs(a - b) > tol * max(1.0, abs(a)):
            out.append(f'{path}: js {a!r} lua {b!r}')
    elif a != b:
        out.append(f'{path}: js {a!r} lua {b!r}')
    return out
