# Luau ↔ JavaScript parity tests

The flight model, weapons, AI, scenarios and race courses of the Roblox version (`roblox/src/shared/sim`, `roblox/src/shared/game`) are
ports of `web/js`. These tests run the Luau modules under Lua 5.4 (lupa, with Roblox's `require` shimmed) next to the original
JavaScript and compare the numbers.

```sh
pip install lupa
sh roblox/tests/prepare.sh /tmp/dfparity && cd /tmp/dfparity
for t in util flight sim race; do node ref_$t.mjs > ref_$t.json; python3 test_$t.py; done
python3 test_island.py     # the full-resolution island data equals terrain.json
python3 test_match.py      # smoke test of the game flow (waves, survival, duel, race, canyon, tube, free)
```
