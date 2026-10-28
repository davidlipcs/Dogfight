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
    local Net = require("Net")
    local terrain = T.new(TERRAIN_DATA)
    local function run(mode, seconds)
        local clockT = 0
        local inbox = { A = {}, B = {} }
        local function mk(name, uid, other, team, host, opts, seed)
            local msgsSeen = {}
            local env = { terrain = terrain, seed = seed, netTeam = team, hud = { message = function(_, t) msgsSeen[#msgsSeen + 1] = t end, popup = function(_, t) msgsSeen[#msgsSeen + 1] = "POPUP " .. t end, showMedal = function() end },
                clock = function() return clockT end }
            local me = { name = name }
            local match = G.new(opts, env)
            me.match = match
            local bus = { userId = uid, name = name, team = team, clock = function() return clockT end, isHost = function() return host end,
                send = function(m) table.insert(inbox[other], { from = uid, msg = m, at = clockT + 0.05 }) end }
            env.teamScore = function() return me.session.score end
            me.session = Net.new(match, bus)
            AI.newAIPilot(match.player, "hard", nil)
            me.seen = msgsSeen
            return me
        end
        local optsA = { scenario = mode == "pvp" and "pvp" or "waves", enemies = 2, difficulty = "normal", airStart = true, enemyTypes = { "f16" } }
        local optsB = { scenario = mode == "pvp" and "pvp" or "waves", enemies = 2, difficulty = "normal", airStart = true, enemyTypes = { "f16" }, netGuest = mode ~= "pvp" }
        local A = mk("Anna", 1, "B", "blue", true, optsA, 5)
        local B = mk("Bela", 2, "A", mode == "pvp" and "red" or "blue", mode == "pvp", optsB, 6)
        local dt = 1 / 60
        local out = { ghostsA = 0, ghostsB = 0, enemyGhostsB = 0, ghostSamples = 0 }
        for i = 1, math.floor(seconds / dt) do
            clockT = clockT + dt
            for _, me in ipairs({ A, B }) do
                local key = me == A and "A" or "B"
                local q = inbox[key]
                local keep = {}
                for _, e in ipairs(q) do
                    if e.at <= clockT then me.session:onMessage(e.from, e.msg) else keep[#keep + 1] = e end
                end
                inbox[key] = keep
                me.match:update(dt)
                me.session:step(dt)
                me.session:onEvents(me.match.events)
            end
            if i % 600 == 0 then
                local n = 0 for _ in pairs(B.session.humans) do n = n + 1 end
                local ne = 0 for _ in pairs(B.session.enemies) do ne = ne + 1 end
                out.ghostsB = n; out.enemyGhostsB = ne; out.ghostSamples = out.ghostSamples + 1
            end
        end
        out.A = { kills = A.match.state.kills, deaths = A.match.state.deaths, score = A.match.state.score, wave = A.match.state.wave, alive = A.match.player.alive }
        out.B = { kills = B.match.state.kills, deaths = B.match.state.deaths, score = B.match.state.score, wave = B.match.state.wave, alive = B.match.player.alive, mode = B.match.state.modeLine }
        out.scoreA = A.session.score.blue .. ":" .. A.session.score.red
        out.scoreB = B.session.score.blue .. ":" .. B.session.score.red
        out.nA = #A.match.world.aircraft; out.nB = #B.match.world.aircraft
        out.msgB = #B.seen
        return out
    end
    
    -- the gun path: A shoots at B's ghost, B's jet has to lose hit points
    local clockT = 0
    local inbox = { A = {}, B = {} }
    local function mk(name, uid, other, team, host, seed)
        local env = { terrain = terrain, seed = seed, netTeam = team, clock = function() return clockT end }
        local match = G.new({ scenario = "pvp", airStart = true, aircraft = "f16" }, env)
        local bus = { userId = uid, name = name, team = team, clock = function() return clockT end, isHost = function() return false end,
            send = function(m) table.insert(inbox[other], { from = uid, msg = m, at = clockT + 0.03 }) end }
        local sess = Net.new(match, bus)
        return { match = match, session = sess }
    end
    local A, B = mk("A", 1, "B", "blue", false, 1), mk("B", 2, "A", "red", false, 2)
    -- B right ahead of A, same heading, slightly faster so that A keeps it in the gun sight
    local pa = A.match.player
    local pb = B.match.player
    pb.fm.pos.x, pb.fm.pos.y, pb.fm.pos.z = pa.pos.x + 250, pa.pos.y, pa.pos.z
    pa.fm.vel.x, pa.fm.vel.y, pa.fm.vel.z = 250, 0, 0
    pb.fm.vel.x, pb.fm.vel.y, pb.fm.vel.z = 250, 0, 0
    local q = require("SimMath").qheading(90, 0)
    pa.fm.quat = q:clone(); pb.fm.quat = q:clone()
    pa.controls.throttle, pb.controls.throttle = 0.9, 0.9
    A.match.pilot.aim = require("SimMath").V(1, 0, 0)
    local hp0 = pb.hp
    for i = 1, 600 do
        clockT = clockT + 1 / 60
        for _, me in ipairs({ A, B }) do
            local key = me == A and "A" or "B"
            local keep = {}
            for _, e in ipairs(inbox[key]) do if e.at <= clockT then me.session:onMessage(e.from, e.msg) else keep[#keep + 1] = e end end
            inbox[key] = keep
            me.match:update(1 / 60)
            me.session:step(1 / 60)
            me.session:onEvents(me.match.events)
        end
        pa.trigger = i > 120
        pb.fm.pos.z = pa.pos.z; pb.fm.pos.y = pa.pos.y
        pa.pilot.aim = require("SimMath").norm(require("SimMath").sub(pb.pos, pa.pos))
        pa.fm.engine = 1; pb.fm.engine = 1
    end
    return { hpB0 = hp0, hpB = pb.hp, aliveB = pb.alive, ammoA = pa.gun.ammo, deathsB = B.match.state.deaths, killsA = A.match.state.kills }

''')
import pprint
pprint.pprint(to_py(res))
print('seconds', round(time.time() - t0, 1))
