import json
from luarun import runtime, to_py, compare
lua = runtime()
ref = json.load(open('ref_util.json'))
res = lua.execute(r'''
    local M = require("SimMath")
    local V, Q = M.V, M.Q
    local out = {}
    local function q(a) return { a.x, a.y, a.z, a.w } end
    local function v(a) return { a.x, a.y, a.z } end
    local q1, q2, q3 = M.qheading(37, 12), M.qlook(V(0.3, 0.8, 0.2)), M.qlook(V(0, 0.1, 0.99))
    out.q = { q(q1), q(q2), q(q3), q(M.qmul(q1, q2)) }
    local vv = V(1, 2, 3)
    out.x = { v(M.xform(q1, vv)), v(M.toLocal(q1, vv)), v(M.fwdOf(q1)), v(M.upOf(q2)), v(M.rightOf(q3)) }
    local r = M.rng(12345)
    out.rng = { r(), r(), r(), r.uniform(5, 9), r.gauss(0, 1), r.gauss(2, 3) }
    local r2 = M.rng(0xdeadbeef)
    out.rng2 = { r2(), r2(), r2(), r2(), r2() }
    out.rot = { v(M.rotateTowards(V(1, 0, 0), V(0, 1, 0.2), 0.3)), v(M.norm(V(3, 4, 12))) }
    local d, t = M.closestApproach(V(100, 50, 20), V(-30, -5, 1), 2)
    out.ca = { d, t }
    out.interp = { M.interp({ { 0, 1 }, { 1, 3 }, { 2, 4 } }, 1.5), M.smoothstep(0, 4, 1.2), M.angleBetween(V(1, 0, 0), V(1, 1, 0)), M.headingDeg(V(-1, 1, 0)), M.bankAngle(q1) }
    return out
''')
res = to_py(res)
diff = compare(ref, res, '', 1e-9)
print('util parity:', 'OK' if not diff else diff[:20])
