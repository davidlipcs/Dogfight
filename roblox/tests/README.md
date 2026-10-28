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

## The Roblox side (menu, HUD, view, sounds, displays, rooms)

`python3 roblox/tests/test_client.py` runs the server and client scripts headless under Lua with a mock of the Roblox API
(`mockrbx.lua`; the Luau syntax is translated by `luau2lua.py`): the lobby and every button, a ground start, an air start, every scenario,
the carrier catapult, the tutorial, the cockpit displays, a room with a second player's packets. It finds Lua errors; it cannot find what
only the real Roblox shows (the mock only logs properties it does not know, and it does not draw anything).
