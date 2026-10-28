"""A mission of the war career from the order to the report: both roles, both kinds, flown by an AI pilot on the player's jet."""
import json, array, base64, time
from luarun import runtime, to_py
lua = runtime()
d = json.load(open('terrain.json'))
raw = array.array('h'); raw.frombytes(base64.b64decode(d['heights']))
heights = lua.table_from([v * d['scale'] for v in raw])
lua.globals().TERRAIN_DATA = lua.table(size=d['size'], res=d['res'], heights=heights, airfield=lua.table(x=d['airfield']['x'], y=d['airfield']['y'], elevation=d['airfield']['elevation']))
t0 = time.time()
res = lua.execute(r'''
    local M = require("SimMath")
    local T = require("SimTerrain")
    local G = require("Match")
    local AI = require("AI")
    local C = require("Campaign")
    local terrain = T.new(TERRAIN_DATA)
    local out = {}
    local w = C.newWar("us", 99)
    w.started = true
    local function fly(rank, kind, frontId)
        local pilot = C.newPilot("Teszt", "VIPER")
        pilot.rank = rank
        local o = C.makeOrder(w, pilot, frontId, { kind = kind, jet = rank >= 3 and "f22" or "f16" })
        local m = C.missionOf(w, pilot, o)
        local ended = nil
        local msgs = {}
        local env = { terrain = terrain, seed = 5 + rank, hud = { message = function(_, t) msgs[#msgs + 1] = t end, popup = function() end, showMedal = function() end },
            onMissionEnd = function(r, mm) ended = r end, onTeleport = function() end }
        local match = G.new({ scenario = "mission", mission = m, airStart = true, aircraft = o.jet, wingman = o.role == "lead" and 1 or 0, difficulty = o.skill, enemies = 0 }, env)
        AI.newAIPilot(match.player, "hard", nil)
        local dt = 1 / 30
        local line = match.state.modeLine
        for i = 1, math.floor(60 * 40 / dt) do
            match:update(dt)
            if match.mission.over then break end
        end
        local overBefore = match.mission.over
        match:respawn()                                   -- Enter
        assert(ended, "no result after Enter")
        local before = C.totalFleet(w.powers[o.foe].fleet)
        local after = C.afterMission(w, pilot, m, ended)
        return { rank = rank, kind = kind, role = o.role, nred = #o.red, nblue = #o.blue, over = overBefore, won = ended.won, why = ended.why, kills = ended.kills,
            redLost = #ended.redLost, blueLost = #ended.blueLost, time = math.floor(ended.time), foeFleetBefore = before, foeFleetAfter = C.totalFleet(w.powers[o.foe].fleet),
            lines = #after.lines, rankNow = pilot.rank, sorties = pilot.sorties, day = w.day, mode = line }
    end
    out[#out + 1] = fly(0, "sweep", "baltic")
    out[#out + 1] = fly(2, "cap", "taiwan")
    out[#out + 1] = fly(3, "sweep", "hungary")
    -- flights of AI pilots, a hundred days, the end of the war
    local r = C.sendFlight(w, "baltic", 4)
    out[#out + 1] = { flight = r.redLost .. ":" .. r.blueLost .. " " .. tostring(r.won) }
    for i = 1, 300 do
        C.passDays(w, 2)
        if w.over then break end
    end
    out[#out + 1] = { warDay = w.day, over = w.over and (w.over.player and "won" or "lost") or "running" }
    return out
''')
for r in to_py(res):
    print(r)
print('mission ok', round(time.time() - t0, 1), 's')
