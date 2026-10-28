import json, array, base64
from luarun import runtime, to_py
lua = runtime()
res = lua.execute(r'''
    local D = require("IslandData")
    local T = require("SimTerrain")
    local data = D.load()
    local terrain = T.new(data)
    local a = data.airfield
    return { #data.heights, terrain:height(a.x, a.y), terrain:height(0, 0), terrain.maxHeight, D.material(data, 512, 512), D.material(data, 100, 900) }
''')
res = to_py(res)
d = json.load(open('terrain.json'))
raw = array.array('h'); raw.frombytes(base64.b64decode(d['heights']))
n = d['res'] + 1
print('lua', res)
print('ref count', len(raw), 'airfield elevation', d['airfield']['elevation'], 'max', max(raw) * d['scale'])
# a spot check of the heights
import random
random.seed(1)
ok = True
lua2 = lua.execute('return require("IslandData").load().heights')
for _ in range(2000):
    k = random.randrange(len(raw))
    if abs(lua2[k + 1] - raw[k] * d['scale']) > 1e-6: ok = False; print('mismatch', k); break
print('heights identical:', ok)
