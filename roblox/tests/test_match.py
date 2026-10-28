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
    local Cam = require("Camera")
    local Hud = require("Hud")
    local Ctl = require("Controls")
    local Mfd = require("Mfd")
    local calls = 0
    local canvas = setmetatable({}, { __index = function(_, k)
        if k == "measure" then return function(_, s, size) calls = calls + 1; return #s * size * 0.6 end end
        return function() calls = calls + 1 end end })
    local function run(name, opts, seconds, seed, autoplay)
        local env, msgs = mkenv(seed)
        local m = G.new(opts, env)
        local cam = Cam.new(terrain)
        cam:reset(m.player)
        local hud = Hud.new(canvas)
        local mfd = Mfd.new(m.player.spec)
        for _, d in ipairs(mfd.list) do d.g = canvas end
        hud.nav = m.nav
        local held = {}
        local input = { dx = 3, dy = -1, held = function(k) return held[k] == true end, mouse = { [0] = false, [1] = false, [2] = false } }
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
            cam.cockpit = (i // 1200) % 2 == 1
            if i % 7 == 0 and not autoplay and m.player.alive then held.shift = (i % 14 == 0); Ctl.apply(m, cam, input, dt * 7) end
            cam:update(dt, m.player)
            if i % 3 == 0 then
                for _, e in ipairs(m.events) do hud:handleEvent(e[1], e[2], m.player) end
                mfd:update(dt * 3, m.player, m.world, m.nav)
                if i % 600 == 0 then mfd:cycle("left"); mfd:cycle("right"); mfd:cycle("center") end
                hud:update(dt * 3, m.player, m.world, { position = cam.position, orientation = cam.orientation, fov = cam.fov }, cam, m.state, 1280, 720)
            end
        end
        local st = m.state
        return { name = name, t = m.world.time, wave = st.wave, kills = st.kills, deaths = st.deaths, score = st.score, alive = m.player.alive,
            nac = #m.world.aircraft, msgs = #msgs, calls = calls, last = msgs[#msgs] or "", mode = st.modeLine, race = m.race and m.race.next or -1, banner = st.banner }
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
