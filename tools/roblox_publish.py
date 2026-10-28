#!/usr/bin/env python3
"""Publishes the built place file to a Roblox experience with Open Cloud (Place Publishing API).

Needs three environment variables - never paste the key in a chat or commit it:
  ROBLOX_API_KEY       an Open Cloud API key (Creator Hub > Open Cloud > API Keys) with the permission
                       "universe-places: write" for your experience
  ROBLOX_UNIVERSE_ID   the experience's Universe ID (Creator Hub > the experience > ... > Copy Universe ID)
  ROBLOX_PLACE_ID      the Place ID of its start place
Run:  python3 tools/build_rbxlx.py && python3 tools/roblox_publish.py            (shows what it would do)
      python3 tools/roblox_publish.py --publish                                 (uploads and publishes)
      python3 tools/roblox_publish.py --publish --save-only                     (uploads as a saved version, not live)
"""
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, "roblox", "build", "DogfightPlus.rbxlx")


def main():
    args = sys.argv[1:]
    key, uid, pid = (os.environ.get(k, "") for k in ("ROBLOX_API_KEY", "ROBLOX_UNIVERSE_ID", "ROBLOX_PLACE_ID"))
    missing = [n for n, v in (("ROBLOX_API_KEY", key), ("ROBLOX_UNIVERSE_ID", uid), ("ROBLOX_PLACE_ID", pid)) if not v]
    if missing:
        sys.exit("Missing environment variables: " + ", ".join(missing))
    if not os.path.exists(FILE):
        sys.exit("Build the place first: python3 tools/build_rbxlx.py")
    kind = "Saved" if "--save-only" in args else "Published"
    url = "https://apis.roblox.com/universes/v1/%s/places/%s/versions?versionType=%s" % (uid, pid, kind)
    data = open(FILE, "rb").read()
    print("place file: %s (%d KB)\ntarget: universe %s, place %s, version type %s" % (FILE, len(data) // 1024, uid, pid, kind))
    if "--publish" not in args:
        print("Dry run (add --publish to upload).")
        return
    req = urllib.request.Request(url, data=data, method="POST", headers={"x-api-key": key, "Content-Type": "application/xml"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            print("OK", r.status, json.loads(r.read().decode() or "{}"))
    except urllib.error.HTTPError as e:
        sys.exit("Roblox answered %s: %s" % (e.code, e.read().decode(errors="replace")[:500]))


if __name__ == "__main__":
    main()
