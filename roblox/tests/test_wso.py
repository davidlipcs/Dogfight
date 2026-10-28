"""Two-seat jet: the pilot (machine A, room host, with an AI enemy wave) and the rear seat (machine B) are connected by a loopback.
The rear seat sees the pilot's jet, marks a target, fires a missile and drops flares: all three must happen on the pilot's jet."""
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
    local V = M.V
    local T = require("SimTerrain")
    local G = require("Match")
    local AI = require("AI")
    local Net = require("Net")
    local Specs = require("Specs")
    local terrain = T.new(TERRAIN_DATA)
    local clockT = 0
    local inbox = { A = {}, B = {} }
    local msgs = { A = {}, B = {} }
    local function hudOf(key) return { message = function(_, t) msgs[key][#msgs[key] + 1] = t end, popup = function() end, showMedal = function() end } end
    local function mk(key, other, uid, name, opts, envx)
        local env = { terrain = terrain, seed = uid, netTeam = "blue", hud = hudOf(key), clock = function() return clockT end }
        for k, v in pairs(envx or {}) do env[k] = v end
        local match = G.new(opts, env)
        local bus = { userId = uid, name = name, team = "blue", clock = function() return clockT end, isHost = function() return key == "A" end,
            send = function(m) table.insert(inbox[other], { from = uid, msg = m, at = clockT + 0.04 }) end }
        local me = { match = match, env = env }
        me.session = Net.new(match, bus)
        env.wsoSend = function(a, k, tg) me.session:wsoSend(a, k, tg) end
        return me
    end
    local layout = Specs.buildLoadout(Specs.AIRCRAFT.fa18, 2, 4).layout
    local A = mk("A", "B", 1, "Pilóta", { scenario = "waves", enemies = 2, difficulty = "normal", airStart = true, aircraft = "fa18", twoSeat = true, enemyTypes = { "f16" }, loadout = layout })
    local B = mk("B", "A", 2, "Hátsó", { scenario = "waves", wsoOf = 1, aircraft = "fa18", netGuest = true, loadout = layout, enemies = 2 })
    assert(B.match.wso and B.match.player.slave and B.match.player.ghost)
    local pa = A.match.player
    local out = { }
    local stopB = false
    local function step(seconds, hook)
        local dt = 1 / 60
        for i = 1, math.floor(seconds / dt) do
            clockT = clockT + dt
            for _, me in ipairs(stopB and { A } or { A, B }) do
                local key = me == A and "A" or "B"
                local keep = {}
                for _, e in ipairs(inbox[key]) do if e.at <= clockT then me.session:onMessage(e.from, e.msg) else keep[#keep + 1] = e end end
                inbox[key] = keep
                me.match:update(dt)
                me.session:step(dt)
                me.session:onEvents(me.match.events)
            end
            if hook then hook(i) end
        end
    end
    -- the pilot flies straight; the enemies come
    local function fly() A.match:applyInput(1 / 60, { aim = V(0, 1, 0.02), throttleSet = 0.9 }) end
    step(46, fly)
    local pb = B.match.player
    out.followErr = M.len(M.sub(pa.pos, pb.pos))
    out.wsoKnown = A.session.wsoUser
    out.wsoName = A.match.wsoName
    out.stationsA, out.stationsB = #pa.stations, #pb.stations
    -- the enemy: nearest red in B's world
    local enemies = {}
    for _, a in ipairs(B.match.world.aircraft) do if a.team == "red" and a.alive then enemies[#enemies + 1] = a end end
    out.enemiesSeenByWso = #enemies
    -- mark
    local fwd = M.fwdOf(pb.quat)
    B.match:wsoKey("y", fwd)
    out.mark = B.match.wsoMark and B.match.wsoMark.name or "none"
    step(1)
    out.pilotMark = A.match.wsoMark and A.match.wsoMark.name or "none"
    out.pilotMsgs = #msgs.A
    -- fire
    local n120 = pa:missileCount("AIM-120A")
    pb:select("AIM-120A")
    B.match:wsoKey("Space", fwd)
    step(1)
    out.firedA = n120 - pa:missileCount("AIM-120A")
    out.maskB = pb:missileCount("AIM-120A")
    local copyOnB = 0
    for _, m in ipairs(B.match.world.missiles) do if m.replicated then copyOnB = copyOnB + 1 end end
    out.missileCopiesOnB = copyOnB
    -- flares
    local fl0 = pa.flares
    B.match:wsoKey("x", fwd)
    local seenHold = 0
    step(2, function(i) fly(); if pa.cmHold then seenHold = seenHold + 1 end end)
    out.seenHold = seenHold
    out.flaresUsed = fl0 - pa.flares
    out.flaresB = pb.flares
    out.cm = tostring(pa.cmHold) .. ' ' .. tostring(pa.cmTimer) .. ' ' .. tostring(A.match.wsoFlare)
    -- the pilot locks the marked one
    A.match.wsoMark = A.match.wsoMark
    A.match:onKey("t", M.fwdOf(pa.quat))
    -- the rear seat leaves: the pilot notices
    stopB = true
    step(8, fly)
    out.afterLeave = A.session.wsoUser
    -- the pilot is gone
    return out
''')
import pprint
pprint.pprint(to_py(res))
print('seconds', round(time.time() - t0, 1))
