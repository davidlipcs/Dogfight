import json, array, base64, sys, time
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
    local terrain = T.new(TERRAIN_DATA)
    local log = {}
    local function mkenv(seed)
        local msgs = {}
        local env = { terrain = terrain, seed = seed,
            hud = { message = function(_, t) msgs[#msgs + 1] = t end, popup = function(_, t) msgs[#msgs + 1] = "POPUP " .. t end, showMedal = function(_, a) msgs[#msgs + 1] = "MEDAL " .. a.name end },
            clock = function() return os.clock() end }
        return env, msgs
    end
    local function run(name, opts, seconds, seed, autoplay)
        local env, msgs = mkenv(seed)
        local m = G.new(opts, env)
        if autoplay then
            local ai = AI.newAIPilot(m.player, "hard", nil)      -- the player's jet flown by an AI pilot
        end
        local dt = 1 / 60
        local n = math.floor(seconds / dt)
        for i = 1, n do
            if m.race and m.player.alive then
                -- fly at the next ring
                local tg = m.race.target
                if tg then
                    m.pilot.aim = M.norm(M.sub(tg.c, m.player.pos))
                end
            end
            m:update(dt)
        end
        local st = m.state
        return { name = name, t = m.world.time, wave = st.wave, kills = st.kills, deaths = st.deaths, score = st.score, alive = m.player.alive,
            nac = #m.world.aircraft, msgs = #msgs, last = msgs[#msgs] or "", mode = st.modeLine, race = m.race and m.race.next or -1, banner = st.banner }
    end
    log[#log + 1] = run("waves-air", { scenario = "waves", enemies = 2, difficulty = "normal", airStart = true, enemyTypes = { "f16", "su35" } }, 240, 7, true)
    log[#log + 1] = run("survival", { scenario = "survival", enemies = 3, difficulty = "hard", airStart = true, wingman = true }, 240, 8, true)
    log[#log + 1] = run("duel", { scenario = "duel", enemies = 1, difficulty = "ace", enemyTypes = { "su57" } }, 200, 9, true)
    log[#log + 1] = run("ground", { scenario = "waves", enemies = 2, difficulty = "easy" }, 30, 10, false)
    log[#log + 1] = run("race", { scenario = "race" }, 200, 11, false)
    log[#log + 1] = run("canyon", { scenario = "canyon" }, 150, 12, false)
    log[#log + 1] = run("tube", { scenario = "tube" }, 150, 13, false)
    log[#log + 1] = run("free", { scenario = "free" }, 30, 14, false)
    return log
''')
for r in to_py(res):
    print(r)
print('seconds', round(time.time() - t0, 1))
