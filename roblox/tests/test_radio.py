"""The radio (shared/game/Radio.luau) understands the same phrases as web/js/radio.js, and the other side answers."""
import json, subprocess, array, base64
from luarun import runtime, to_py
PHRASES = ["Fox 2!", "fox two", "FOX THREE, VIPER 1-1", "tower, request taxi", "Viper one one ready for take-off", "splash one", "SPLASH", "bingo fuel",
           "two engage", "check six", "Cover me!", "request picture", "magic checking in", "gear down and locked", "mayday mayday", "wheels up", "nonsense words",
           "tally ho", "no joy", "guns guns", "winchester", "rtb", "heading home", "form up", "break right", "radio check", "copy", "ROGER WILCO", "inbound", "clear of the runway"]
ref = json.loads(subprocess.run(['node', 'ref_radio.mjs', json.dumps(PHRASES)], capture_output=True, text=True, check=True).stdout)
lua = runtime()
d = json.load(open('terrain.json'))
raw = array.array('h'); raw.frombytes(base64.b64decode(d['heights']))
heights = lua.table_from([v * d['scale'] for v in raw])
lua.globals().TERRAIN_DATA = lua.table(size=d['size'], res=d['res'], heights=heights, airfield=lua.table(x=d['airfield']['x'], y=d['airfield']['y'], elevation=d['airfield']['elevation']))
lua.globals().PHRASES = lua.table_from(PHRASES)
res = lua.execute(r'''
    local R = require("Radio")
    local out = {}
    local allowed = R.CALLS
    for i = 1, #PHRASES do
        local c = R.recognise(PHRASES[i], allowed)
        out[i] = { R.normalise(PHRASES[i]), c and c.id or false }
    end
    return out
''')
got = to_py(res)
bad = 0
for p, r, g in zip(PHRASES, ref, got):
    gid = g[1] if g[1] else None
    if r[0] != g[0] or r[1] != gid:
        bad += 1
        print('DIFF', repr(p), 'js', r, 'lua', g)
print('phrases', len(PHRASES), 'different', bad)
assert bad == 0

# a match: the answers, the wingman's orders, the picture
res = lua.execute(r'''
    local M = require("SimMath")
    local T = require("SimTerrain")
    local G = require("Match")
    local terrain = T.new(TERRAIN_DATA)
    local msgs = {}
    local env = { terrain = terrain, seed = 5, hud = { message = function(_, t) msgs[#msgs + 1] = t end, popup = function() end, showMedal = function() end } }
    local m = G.new({ scenario = "waves", wingman = 1, airStart = true, aircraft = "f16", enemies = 3 }, env)
    local r = m.radio
    local out = {}
    for i = 1, 60 * 40 do m:update(1 / 60) end
    assert(r:transmit("tower radio check", "type"))
    assert(r:transmit("magic request picture", "type"))
    assert(r:transmit("two cover me", "type"))
    assert(not r:transmit("blah blah", "type"))
    for i = 1, 60 * 3 do m:update(1 / 60) end
    for _, l in ipairs(r.log) do out[#out + 1] = l.who .. ": " .. l.text end
    out[#out + 1] = "order=" .. tostring(m.wingman and m.wingman.pilot.order)
    return out
''')
for l in to_py(res).values() if hasattr(to_py(res), 'values') else to_py(res): print(l)
print('radio ok')
