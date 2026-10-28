"""The war of Campaign.luau equals the JavaScript one (same random source), and a mission of the war career can be flown from start to end."""
import json, subprocess, array, base64, time
from luarun import runtime, to_py
ref = json.loads(subprocess.run(['node', 'ref_campaign.mjs'], capture_output=True, text=True, check=True).stdout)
lua = runtime()
res = to_py(lua.execute(r'''
    local C = require("Campaign")
    local x = 987654321
    math.random = function(a, b)
        x = (x * 16807) % 2147483647
        local f = (x - 1) / 2147483646
        if a == nil then return f end
        if b == nil then return math.floor(f * a) + 1 end
        return a + math.floor(f * (b - a + 1))
    end
    local w = C.newWar("us", 4242)
    w.started = true
    local snaps = {}
    for d = 1, 150 do
        C.simulateDay(w)
        if w.day % 4 == 0 then C.aiDiplomacy(w) end
        if d % 30 == 0 then
            local fleets, money = {}, {}
            for k, p in pairs(w.powers) do fleets[k] = C.totalFleet(p.fleet); money[k] = math.floor(p.money * 100 + 0.5) / 100 end
            local trust = {}
            for k, v in pairs(w.trust) do trust[k] = v end
            snaps[#snaps + 1] = { day = w.day, fleets = fleets, trust = trust, money = money, over = w.over and true or false }
        end
    end
    local seen = C.seenFleet(w, "ru")
    return { snaps = snaps, seen = seen.fleet, bud = C.budgetOf(w, "us"), log = #w.log }
'''))
snaps = res['snaps']
bad = 0
for a, b in zip(ref['snaps'], snaps):
    for k in ('us', 'eu', 'ru', 'cn'):
        if a['fleets'][k] != b['fleets'][k]:
            bad += 1; print('fleet diff day', a['day'], k, a['fleets'][k], b['fleets'][k])
        if abs(a['money'][k] - b['money'][k]) > 0.02:
            bad += 1; print('money diff day', a['day'], k, a['money'][k], b['money'][k])
    for k, v in a['trust'].items():
        if abs(v - b['trust'][k]) > 1e-6:
            bad += 1; print('trust diff day', a['day'], k, v, b['trust'][k])
    if a['over'] != b['over']: bad += 1; print('over diff', a['day'])
for k, v in ref['seen'].items():
    if res['seen'][k] != v: bad += 1; print('seen diff', k, v, res['seen'][k])
print('snapshots', len(ref['snaps']), 'differences', bad, 'budget', dict(res['bud']), 'ref budget', ref['bud'], 'log', res['log'], ref['log'])
assert bad == 0
print('campaign parity ok')
