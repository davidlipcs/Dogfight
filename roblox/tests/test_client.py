"""Runs the Roblox-side code (server Main, client Main, the menu, a match with its HUD, view, effects, displays, sounds, tutorial and a room)
headless under lupa with the mock of the Roblox API (mockrbx.lua).  It finds Lua errors (typos, nils, missing methods); it cannot find
what only the real Roblox shows (a property that does not exist is logged as a warning, but the list is incomplete).
  python3 roblox/tests/test_client.py"""
import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'roblox', 'src')
sys.path.insert(0, HERE)
from lupa import LuaRuntime  # noqa: E402
import luau2lua  # noqa: E402

lua = LuaRuntime(unpack_returned_tuples=True)
M = lua.execute(open(os.path.join(HERE, 'mockrbx.lua')).read())
cache = {}


def translate(path):
    if path not in cache:
        cache[path] = luau2lua.translate(open(path, encoding='utf-8').read())
    return cache[path]


M.translate = translate


def build(directory, name):
    folder = M.instOf('Folder', name)
    for entry in sorted(os.listdir(directory)):
        full = os.path.join(directory, entry)
        if os.path.isdir(full):
            c = build(full, entry)
            c.Parent = folder
        elif entry.endswith('.server.luau'):
            s = M.instOf('Script', entry[:-12]); s.__file = full; s.Parent = folder
        elif entry.endswith('.client.luau'):
            s = M.instOf('LocalScript', entry[:-12]); s.__file = full; s.Parent = folder
        elif entry.endswith('.luau'):
            m = M.moduleInstance(entry[:-5], full); m.Parent = folder
    return folder


def mount(service, folder):
    folder.Parent = M.service(service)


mount('ReplicatedStorage', build(os.path.join(SRC, 'shared'), 'Shared'))
mount('ServerScriptService', build(os.path.join(SRC, 'server'), 'Server'))
sps = M.instOf('StarterPlayerScripts', 'StarterPlayerScripts')
sps.Parent = M.service('StarterPlayer')
build(os.path.join(SRC, 'client'), 'Client').Parent = sps
lua.globals().M = M
lua.execute('M.log = M.log or {}')


def run(chunk, label):
    try:
        return lua.execute(chunk)
    except Exception as e:  # noqa: BLE001
        print('FAILED:', label)
        print(str(e)[:1500])
        print('\n'.join(list(M.log)[-5:]))
        raise SystemExit(1)


t0 = time.time()
run('''
    local server = M.service("ServerScriptService").Server
    M.runScript(server.Main)
    local client = M.service("StarterPlayer").StarterPlayerScripts.Client
    M.runScript(client.Main)
''', 'start server and client')
print('started in', round(time.time() - t0, 1), 's')

HELPERS = r'''
    local function find(o, pred) for _, d in ipairs(o:GetDescendants()) do if pred(d) then return d end end end
    local function press(kc, down)
        local uis = M.service("UserInputService")
        local ev = down and uis.InputBegan or uis.InputEnded
        ev:Fire({ UserInputType = Enum.UserInputType.Keyboard, KeyCode = Enum.KeyCode[kc] }, false)
    end
    local function frames(n, dt)
        local f = M.renderSteps.DogfightFrame
        assert(f, "the game loop is not bound")
        for i = 1, n do f(dt or 1 / 60); M.pump(dt or 1 / 60) end
    end
    local function clickText(txt)
        local b = find(M.localPlayer.PlayerGui, function(d) return d.__p.Text and string.find(d.__p.Text, txt, 1, true) and d.__sig.Activated end)
        assert(b, "no button: " .. txt)
        b.__sig.Activated:Fire()
    end
'''
run(HELPERS + '''
    clickText("INDULÁS A PÁLYÁRÓL")
    frames(180)
    press("W", true); frames(60); press("W", false)
    press("Space", true); press("Space", false)
    press("T", true); press("T", false); press("One", true); press("One", false)
    frames(120)
''', 'ground start, a few seconds of flying')
print('ground start ok')

run(HELPERS + '''
    local Game = require(M.service("StarterPlayer").StarterPlayerScripts.Client.Game)
    local m = Game.match()
    assert(m, "no match")
    press("V", true); press("V", false)
    frames(120)                     -- cockpit view with the displays
    press("J", true); press("J", false); press("K", true); press("K", false)
    press("N", true); press("N", false)
    frames(60)
    press("N", true); press("N", false); press("V", true); press("V", false)
    press("U", true); press("U", false)
    frames(60)
    press("P", true); press("P", false)   -- pause
    frames(10)
    press("P", true); press("P", false)
    frames(10)
    Game.stop()
''', 'cockpit, displays, pause, stop')
print('cockpit / pause ok')

run(HELPERS + '''
    clickText("INDULÁS A LEVEGŐBEN")
    frames(600)
    local Game = require(M.service("StarterPlayer").StarterPlayerScripts.Client.Game)
    -- the AI of the match plays for the player: fire things
    local m = Game.match()
    for i = 1, 6 do
        press("Space", true); press("Space", false)
        press("X", true); frames(30); press("X", false)
    end
    frames(600)
    Game.stop()
    clickText("OKTATÁS")
    frames(300)
    press("Enter", true); press("Enter", false)
    frames(300)
    Game.stop()
''', 'air start, weapons, tutorial')
print('air start + tutorial ok')
run(HELPERS + """
    -- every button of the lobby and the menu once
    local gui = M.localPlayer.PlayerGui
    local n = 0
    for _, d in ipairs(gui:GetDescendants()) do
        if d.__sig.Activated and d.__p.Text and not string.find(d.__p.Text, "INDUL", 1, true) and not string.find(d.__p.Text, "OKTAT", 1, true) then
            n = n + 1
            d.__sig.Activated:Fire()
        end
    end
    print("buttons pressed", n)
    local Menu = require(M.service("StarterPlayer").StarterPlayerScripts.Client.Menu)
    local Game = require(M.service("StarterPlayer").StarterPlayerScripts.Client.Game)
    for _, sc in ipairs({ "duel", "survival", "race", "canyon", "tube", "free" }) do
        Menu.state.scen = sc
        clickText("INDULÁS A LEVEGŐBEN")
        frames(400)
        press("V", true); press("V", false); frames(30); press("V", false)
        Game.stop()
    end
    Menu.state.scen = "waves"
    clickText("HORDOZÓRÓL")
    frames(600)
    local m = Game.match()
    local p = m.player
    print("carrier start: z", p.pos.z, "onGround", p.onGround, "onDeck", m.carrier:onDeck(p.pos.x, p.pos.y), "onCat", m.carrier:onCatapult(p.pos.x, p.pos.y), "gear", p.fm.gearDown)
    for i = 1, 25 do press("LeftShift", true); press("LeftShift", false) end     -- throttle up in 5 % steps to 100 %
    print("throttle", p.controls.throttle)
    frames(300)
    print("after 5 s: speed", p.speed, "z", p.pos.z, "onGround", p.onGround, "catState", m.catState and m.catState.t, "banner", m.state.subBanner)
    frames(900)
    print("after 20 s: speed", p.speed, "z", p.pos.z, "onGround", p.onGround, "alive", p.alive)
    Game.stop()
""", "all buttons, every scenario, carrier start")
print("scenarios ok")

run(HELPERS + """
    -- a room: the host (us) in a co-op room with a second player, packets from the other machine
    local C = M.service("StarterPlayer").StarterPlayerScripts.Client
    local State = require(C.State)
    local Game = require(C.Game)
    State.set({ id = 1, name = "t", mode = "coop", max = 4, host = 4242, members = { { userId = 4242, name = "Teszt", team = "A", host = true }, { userId = 77, name = "Másik", team = "A" } }, seats = {} })
    clickText("INDULÁS A LEVEGŐBEN")
    frames(120)
    local net = M.service("ReplicatedStorage").Remotes.Net
    local snap = { t = "s", p = { 100, 100, 4000 }, v = { 200, 0, 0 }, q = { 0, 0, 0, 1 }, c = { 0, 0, 0 }, e = 0.9, g = 0, hp = 100, al = 1, bn = 0, cr = 0, gn = 0, ej = 0 }
    for i = 1, 40 do
        net.__sig.OnClientEvent:Fire(77, { { t = "hello", n = "Másik", a = "fa18", tm = "blue" }, snap })
        frames(6)
    end
    net.__sig.OnClientEvent:Fire(77, { { t = "bye" } })
    frames(30)
    State.set({ id = 2, name = "p", mode = "pvp", max = 4, host = 77, members = { { userId = 4242, name = "Teszt", team = "B", host = false }, { userId = 77, name = "Másik", team = "A", host = true } }, seats = {} })
    Game.stop()
    clickText("INDULÁS A LEVEGŐBEN")
    for i = 1, 20 do net.__sig.OnClientEvent:Fire(77, { { t = "hello", n = "Másik", a = "f16", tm = "blue" }, snap }); frames(10) end
    Game.stop()
    State.set(nil)
""", "rooms")
print("rooms ok")
run(HELPERS + """
    clickText("Napi")
    local before = require(M.service("ServerScriptService").Server.Data).get(M.localPlayer).coins
    clickText("Átveszem")
    local after = require(M.service("ServerScriptService").Server.Data).get(M.localPlayer).coins
    print("daily reward: coins", before, "->", after)
    assert(after > before, "the daily reward did not pay")
    clickText("Ma már átvetted")
""", "daily reward")
print("daily ok")
run(HELPERS + """
    -- the radio: the I key opens the panel, a typed call goes out, the wingman answers
    local Game = require(M.service("StarterPlayer").StarterPlayerScripts.Client.Game)
    clickText("INDULÁS A LEVEGŐBEN")
    frames(200)
    local m = Game.match()
    local gui = M.localPlayer.PlayerGui.RadioGui
    assert(not gui.Panel.Visible)
    press("I", true); press("I", false)
    frames(5)
    assert(gui.Panel.Visible, "the radio panel did not open")
    assert(gui.Panel.Input.__focused, "the box has no focus")
    gui.Panel.Input.Text = "tower, radio check"
    gui.Panel.Input.__sig.FocusLost:Fire(true)
    assert(not gui.Panel.Visible)
    frames(240)
    local text = gui.Log.Text
    assert(string.find(text, "loud and clear", 1, true), "no answer in the log: " .. text)
    -- a digit picks from the list
    press("I", true); press("I", false); frames(3)
    assert(gui.Panel.Visible, "the panel did not open the second time")
    gui.Panel.Input.Text = "3"
    assert(not gui.Panel.Visible, "the digit did not pick a call")
    frames(240)
    print(gui.Log.Text)
    Game.stop()
""", "radio")
print("radio ok")
run(HELPERS + """
    -- the rear seat of a team mate's jet, then our own two-seat jet with the seat open
    local C = M.service("StarterPlayer").StarterPlayerScripts.Client
    local State = require(C.State)
    local Game = require(C.Game)
    local Menu = require(C.Menu)
    local Rooms = require(M.service("ServerScriptService").Server.Rooms)
    State.set({ id = 1, name = "t", mode = "coop", max = 4, host = 77, members = { { userId = 4242, name = "Teszt", team = "A" }, { userId = 77, name = "Pilóta", team = "A", host = true } }, seats = {} })
    assert(Game.start({ wsoOf = 77, aircraft = "fa18", loadout = "default", scenario = "waves", enemies = 0, wingman = 0, airStart = true, mode = "arcade", difficulty = "normal", enemyTypes = { "f16" } }))
    local net = M.service("ReplicatedStorage").Remotes.Net
    local snap = { t = "s", p = { 100, 100, 4000 }, v = { 200, 0, 0 }, q = { 0, 0, 0, 1 }, c = { 0, 0, 0 }, e = 0.9, g = 0, hp = 100, al = 1, bn = 0, cr = 0, gn = 0, ej = 0, fl = 30, ld = "111111" }
    for i = 1, 30 do net.__sig.OnClientEvent:Fire(77, { snap }); frames(6) end
    local m = Game.match()
    assert(m.wso and m.player.slave)
    press("T", true); press("T", false); press("Space", true); press("Space", false); press("X", true); press("X", false)
    press("One", true); press("One", false); press("Y", true); press("Y", false)
    frames(60)
    Game.stop()
    State.set(nil)
    -- the pilot side
    State.set({ id = 2, name = "t", mode = "coop", max = 4, host = 4242, members = { { userId = 4242, name = "Teszt", team = "A", host = true } }, seats = {} })
    Menu.state.two = true
    clickText("INDULÁS A LEVEGŐBEN")
    frames(120)
    net.__sig.OnClientEvent:Fire(77, { { t = "wsohello", to = 4242, n = "Hátsó" } })
    frames(30)
    net.__sig.OnClientEvent:Fire(77, { { t = "wso", to = 4242, a = "flare" } })
    frames(120)
    Game.stop()
    State.set(nil)
    Menu.state.two = false
""", "two-seat")
print("two-seat ok")
print('seconds', round(time.time() - t0, 1))
w = dict(M.warnings.items()) if hasattr(M.warnings, 'items') else {}
if w:
    print('WARNINGS (check them against the Roblox API):')
    for k, v in sorted(w.items()):
        print('  ', v, 'x', k)
