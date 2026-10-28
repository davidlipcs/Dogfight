import json, array, base64
from luarun import runtime, to_py, compare
lua = runtime()
d = json.load(open('terrain.json'))
raw = array.array('h'); raw.frombytes(base64.b64decode(d['heights']))
heights = lua.table_from([v * d['scale'] for v in raw])
lua.globals().TERRAIN_DATA = lua.table(size=d['size'], res=d['res'], heights=heights, airfield=lua.table(x=d['airfield']['x'], y=d['airfield']['y'], elevation=d['airfield']['elevation']))
res = lua.execute(r'''
    local M = require("SimMath")
    local V = M.V
    local T = require("SimTerrain")
    local R = require("Race")
    local terrain = T.new(TERRAIN_DATA)
    local field = terrain.airfield
    local function arr(v) return { v.x, v.y, v.z } end
    local function rings(r) local o = {} for i, x in ipairs(r.rings) do o[i] = { arr(x.c), arr(x.n) } end return o end
    local function fly(r, miss)
        local evs = {}
        for k = 0, #r.rings * 3 - 1 do
            if r.finished then break end
            local g = r.rings[(r.next % #r.rings) + 1]
            local off = (miss and k == 2) and 1.2 * r.R or 0
            local side = V(g.n.y, -g.n.x, 0)
            local a = V(g.c.x - g.n.x * 30 + side.x * off, g.c.y - g.n.y * 30 + side.y * off, g.c.z)
            local b = V(g.c.x + g.n.x * 30 + side.x * off, g.c.y + g.n.y * 30 + side.y * off, g.c.z)
            local ev = r:update(0.5, { pos = b }, a)
            evs[#evs + 1] = { ev or "null", r.next, r.time, r.penalty or 0 }
        end
        return evs
    end
    local out = {}
    local race = R.Race.new(terrain, V(field.x, field.y + 3000, 0), 0)
    out.race = { rings = rings(race), ev = fly(race, true), fin = race.finished, rec = race.record }
    local canyon = R.Canyon.new(terrain)
    out.canyon = { rings = rings(canyon), target = arr(canyon.targetPos), idx = canyon.targetIdx, ev = fly(canyon, false), success = canyon.success, time = canyon.time }
    local tube = R.Tube.new(terrain, V(field.x, field.y + 3500, 0))
    local pose = tube:startPose()
    out.tube = { rings = rings(tube), lap = tube.lapLength, pose = { arr(pose.pos), pose.heading }, off = tube:offAxis(V(field.x + 10, field.y + 3500, 900)), ev = fly(tube, false), fin = tube.finalTime, bestLap = tube.bestLap }
    return out
''')
lua_out = to_py(res)
ref = json.load(open('ref_race.json'))
# nulls: JS null -> "null"
def fix(o):
    if isinstance(o, list): return [fix(x) for x in o]
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    return 'null' if o is None else o
ref = fix(ref)
errs = compare(ref, lua_out, tol=1e-6)
print(len(errs), 'differences')
for e in errs[:30]: print(e)
for k in ('race', 'canyon', 'tube'): print(k, len(ref[k]['rings']), len(lua_out[k]['rings']), ref[k].get('fin'), lua_out[k].get('fin'))
