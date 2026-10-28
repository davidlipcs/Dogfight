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
    local F = require("Flight")
    local S = require("Specs")
    local T = require("SimTerrain")
    local terrain = T.new(TERRAIN_DATA)
    local function run(spec, setup, ctl, Tend, extreme)
        local fm = setup(spec)
        fm.extreme = extreme or false
        local c = F.newControls(0.9)
        local dt = 0.01
        local out = {}
        for i = 0, math.floor(Tend / dt + 1e-9) do
            local t = i * dt
            ctl(c, t)
            fm:step(dt, c, terrain)
            if i % 500 == 0 then
                out[#out + 1] = { t = t, pos = { fm.pos.x, fm.pos.y, fm.pos.z }, vel = { fm.vel.x, fm.vel.y, fm.vel.z }, q = { fm.quat.x, fm.quat.y, fm.quat.z, fm.quat.w },
                    om = { fm.omega.x, fm.omega.y, fm.omega.z }, eng = fm.engine, fuel = fm.fuel, g = fm.gLoad, alpha = fm.alpha, gear = fm.gearPos, on = fm.onGround, ev = fm.contactEvent or false, ias = fm.ias }
            end
        end
        return out
    end
    local function air(alt, spd, hdg)
        return function(spec) return F.new(spec, V(0, 0, alt), M.mul(M.fwdOf(M.qheading(hdg, 0)), spd), M.qheading(hdg, 0)) end
    end
    local function ctlA(c, t)
        c.throttle = t < 6 and 1.1 or 0.7
        c.pitch = t < 3 and 0.4 or (t < 9 and (-0.2 + 0.1 * math.sin(t)) or 0.6)
        c.roll = (t > 4 and t < 7) and 1 or ((t > 10 and t < 12) and -1 or 0)
        c.yaw = t > 14 and 0.5 or 0
        c.airbrake = t > 18 and t < 20
        c.postStall = false
    end
    local function ctlB(c, t) c.throttle = 1.1; c.pitch = t < 2 and 0 or 1; c.roll = 0; c.yaw = 0; c.postStall = t > 3 end
    local f = terrain.airfield
    local function ground(spec)
        local fm = F.new(spec, V(), V(), M.qheading(0))
        fm:placeOnGround(f.x, f.y - 1400, terrain:height(f.x, f.y - 1400), 0)
        return fm
    end
    local function ctlG(c, t) c.throttle = t < 1 and 0.4 or 1.1; c.brakes = t < 1; c.pitch = t > 22 and 0.6 or 0; c.yaw = 0.05; c.roll = 0 end
    return {
        f16_air = run(S.AIRCRAFT.f16, air(5000, 250, 45), ctlA, 25),
        fa18_air = run(S.AIRCRAFT.fa18, air(3000, 200, 270), ctlA, 25),
        f16_tvc = run(S.AIRCRAFT.f16, air(6000, 120, 10), ctlB, 12, true),
        f22_air = run(S.AIRCRAFT.f22, air(8000, 300, 100), ctlA, 25),
        t6_air = run(S.TRAINERS.t6, air(2000, 110, 0), ctlA, 25),
        f16_takeoff = run(S.AIRCRAFT.f16, ground, ctlG, 60),
        su35_air = run(S.AIRCRAFT.su35, air(4000, 260, 0), ctlA, 20),
    }
''')
res = to_py(res)
ref = json.load(open('ref_flight.json'))
for k in ref:
    for r in ref[k]:
        if r['ev'] is None: r['ev'] = False
    diff = compare(ref[k], res[k], k, 1e-6)
    print(k, 'OK' if not diff else diff[:6])
