import json, array, base64, time
from luarun import runtime, to_py
lua = runtime()
d = json.load(open('terrain.json'))
raw = array.array('h'); raw.frombytes(base64.b64decode(d['heights']))
heights = lua.table_from([v * d['scale'] for v in raw])
lua.globals().TERRAIN_DATA = lua.table(size=d['size'], res=d['res'], heights=heights, airfield=lua.table(x=d['airfield']['x'], y=d['airfield']['y'], elevation=d['airfield']['elevation']))
res = lua.execute(r'''
    local M = require("SimMath")
    local T = require("SimTerrain")
    local G = require("Match")
    local AI = require("AI")
    local terrain = T.new(TERRAIN_DATA)
    local out = {}
    for _, key in ipairs({ "f16", "fa18", "f22", "f15", "t38" }) do
        local ended = false
        local cam = { cockpit = false, panelLook = false }
        local env = { terrain = terrain, seed = 3, cam = cam, onTutorialEnd = function() ended = true end,
            hud = { message = function() end, popup = function() end, showMedal = function() end } }
        local m = G.new({ tutorial = true, airStart = true, aircraft = key, mode = "arcade" }, env)
        local steps, views = 0, 0
        local dt = 1 / 60
        for i = 1, 60 * 160 do
            -- the pilot: flown by the instructor towards a slowly turning aim; every 5 s a lesson is skipped, a few are really played
            local p = m.player
            if i % 5 == 0 and m.tutorial then
                local v = m.tutorial:view(); views = views + 1
                assert(v.title and v.body and v.task)
            end
            m.pilot.aim = M.V(math.sin(i / 400), math.cos(i / 400), 0.05)
            if m.tutorial and i % 300 == 0 then m.tutorial:enter(); steps = steps + 1 end
            m:update(dt)
            if ended then break end
        end
        out[key] = { ended = ended, steps = steps, views = views, alive = m.player.alive, lessons = m.tutorial and #m.tutorial.steps or -1 }
    end
    return out
''')
import pprint; pprint.pprint(to_py(res))
