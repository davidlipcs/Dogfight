#!/bin/sh
# Builds the work folder of the Luau-vs-JavaScript parity tests:  sh roblox/tests/prepare.sh /tmp/dfparity
# Then, from that folder:  node ref_util.mjs > ref_util.json  (also ref_flight, ref_sim, ref_race)  and  python3 test_util.py  (flight, sim, race, island, match).
# Needs node, python3 with lupa (pip install lupa).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
OUT=${1:-/tmp/dfparity}
mkdir -p "$OUT/js"
cp "$ROOT"/web/js/*.js "$OUT/js/"
echo '{"type":"module"}' > "$OUT/js/package.json"
cp "$ROOT/web/js/three.min.js" "$OUT/three.cjs"
cp "$ROOT/web/assets/terrain.json" "$OUT/terrain.json"
cp "$HERE"/*.py "$HERE"/*.mjs "$OUT/"
echo "$ROOT" > "$OUT/root.txt"
echo "ready: cd $OUT"
