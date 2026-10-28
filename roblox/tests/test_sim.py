import json, array, base64, sys
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
    local Sim = require("Sim")
    local AI = require("AI")
    local S = require("Specs")
    local terrain = T.new(TERRAIN_DATA)
    local function scenario(seed, setup, Tend)
        local w = Sim.newWorld(terrain, seed)
        local acs = setup(w)
        local out, counts = {}, {}
        local dt = 1 / 60
        for i = 0, math.floor(Tend / dt + 1e-9) do
            w:update(dt)
            for _, e in ipairs(w:drainEvents()) do counts[e[1]] = (counts[e[1]] or 0) + 1 end
            if i % 300 == 0 then
                local rec = { t = w.time, acs = {}, nm = #w.missiles, nf = #w.flares, counts = {} }
                for k, v in pairs(counts) do rec.counts[k] = v end
                for j, a in ipairs(acs) do
                    rec.acs[j] = { pos = { a.pos.x, a.pos.y, a.pos.z }, vel = { a.vel.x, a.vel.y, a.vel.z }, hp = a.hp, alive = a.alive, flares = a.flares, ammo = a.gun.ammo,
                        m9 = a:missileCount("AIM-9M"), m120 = a:missileCount("AIM-120A"), state = a.pilot and a.pilot.state or "" }
                end
                out[#out + 1] = rec
            end
        end
        return out
    end
    local function mk(spec, name, team, x, y, z, hdg, spd, seed, missiles, skill)
        local a = Sim.newAircraft(spec, name, team, V(x, y, z), hdg, spd, { rnd = M.rng(seed), missiles = missiles })
        AI.newAIPilot(a, skill, nil)
        return a
    end
    local out = {}
    out.duel = scenario(5, function(w)
        local a = mk(S.AIRCRAFT.f16, "A", "blue", 0, 0, 6000, 90, 250, 11, S.PLAYER_MISSILES, "normal")
        local b = mk(S.BANDITS.su35, "B", "red", 14000, 0, 6200, 270, 250, 22, S.missilesFor(S.BANDITS.su35, true), "ace")
        w:addAircraft(a); w:addAircraft(b); return { a, b }
    end, 150)
    out.merge = scenario(9, function(w)
        local a = mk(S.AIRCRAFT.fa18, "A", "blue", 0, 0, 5000, 0, 280, 31, S.PLAYER_MISSILES, "hard")
        local b = mk(S.BANDITS.mig29, "B", "red", 2500, 9000, 5100, 200, 260, 32, S.missilesFor(S.BANDITS.mig29, true), "hard")
        local c = mk(S.BANDITS.f16, "C", "red", -3000, 12000, 4800, 180, 250, 33, S.BANDIT_MISSILES, "normal")
        w:addAircraft(a); w:addAircraft(b); w:addAircraft(c); return { a, b, c }
    end, 150)
    out.stealth = scenario(3, function(w)
        local a = mk(S.AIRCRAFT.f22, "A", "blue", 20000, -10000, 8000, 45, 300, 41, S.PLAYER_MISSILES, "ace")
        local b = mk(S.BANDITS.typhoon, "B", "red", 30000, 2000, 8100, 250, 260, 42, S.missilesFor(S.BANDITS.typhoon, true), "ace")
        w:addAircraft(a); w:addAircraft(b); return { a, b }
    end, 150)
    return out
''')
res = to_py(res)
ref = json.load(open('ref_sim.json'))
tol = float(sys.argv[1]) if len(sys.argv) > 1 else 1e-5
for k in ref:
    diff = compare(ref[k], res[k], k, tol)
    print(k, 'OK' if not diff else (len(diff), diff[:8]))
