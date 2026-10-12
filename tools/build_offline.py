"""Builds web/dogfight-offline.html: the whole browser game in ONE file that runs from disk
(double click, no internet, no server).

Browsers refuse ES modules and fetch() on file:// pages, so the modules are bundled into one
classic script with esbuild and every asset is embedded as a data: URI.

    python tools/build_offline.py          (needs Node.js; esbuild is fetched by npx)
"""

import base64
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(WEB, "dogfight-offline.html")
ESBUILD = "esbuild@0.24.0"
MIME = {".json": "application/json", ".jpg": "image/jpeg", ".png": "image/png"}


def bundle():
    cmd = ["npx", "--yes", ESBUILD, os.path.join(WEB, "js", "game.js"), "--bundle", "--format=iife",
           "--minify", "--target=es2020", "--charset=utf8"]
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def data_uri(name):
    path = os.path.join(WEB, "assets", name)
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (MIME[os.path.splitext(name)[1]], base64.b64encode(f.read()).decode("ascii"))


def inline_script(code):
    return "<script>\n" + code.replace("</script", "<\\/script") + "\n</script>"


def main():
    with open(os.path.join(WEB, "index.html"), encoding="utf-8") as f:
        page = f.read()
    with open(os.path.join(WEB, "js", "three.min.js"), encoding="utf-8") as f:
        three = f.read()
    assets = sorted(n for n in os.listdir(os.path.join(WEB, "assets")) if os.path.splitext(n)[1] in MIME)
    table = ",\n".join('"%s": "%s"' % (n, data_uri(n)) for n in assets)
    tags = ('<script src="js/three.min.js"></script>', '<script type="module" src="js/game.js"></script>')
    for tag in tags:
        if tag not in page:
            sys.exit("index.html changed: missing %s" % tag)
    page = page.replace(tags[0], inline_script(three))
    page = page.replace(tags[1], inline_script("window.DOGFIGHT_ASSETS = {\n%s\n};" % table) + "\n"
                        + inline_script(bundle()))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
