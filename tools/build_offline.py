"""Builds web/dogfight-offline.html: the whole browser game in ONE file that runs from disk
(double click, no internet, no server).

Browsers refuse ES modules and fetch() on file:// pages, so the modules are bundled into one
classic script and every asset is embedded as a data: URI.

    python tools/build_offline.py

With Node.js installed the bundle is minified by esbuild (fetched by npx); without it a small bundler
written here is used instead (same result, just not minified).
"""

import base64
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(WEB, "dogfight-offline.html")
ESBUILD = "esbuild@0.24.0"
MIME = {".json": "application/json", ".jpg": "image/jpeg", ".png": "image/png", ".glb": "model/gltf-binary"}
IMPORT = re.compile(r"^import\s*\{([^}]*)\}\s*from\s*'\./([\w.]+)';[ \t]*\n", re.M)


def bundle():
    npx = shutil.which("npx")
    if npx is None:
        print("Node.js not found: using the built-in bundler")
        return bundle_plain()
    cmd = [npx, "--yes", ESBUILD, os.path.join(WEB, "js", "game.js"), "--bundle", "--format=iife",
           "--minify", "--target=es2020", "--charset=utf8"]
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def bundle_plain():
    """The modules only use named imports and plain `export const / function / class`, so each one can
    become a function scope that returns what the others import from it."""
    sources, order, wanted = {}, [], {}

    def visit(name):
        if name in sources:
            return
        with open(os.path.join(WEB, "js", name), encoding="utf-8") as f:
            sources[name] = f.read()
        for names, dep in IMPORT.findall(sources[name]):
            wanted.setdefault(dep, set()).update(n.split(" as ")[0].strip() for n in names.split(",") if n.strip())
            visit(dep)
        order.append(name)                               # dependencies first

    def destructure(m):
        names = ", ".join(n.strip().replace(" as ", ": ") for n in m.group(1).split(",") if n.strip())
        return "const { %s } = __modules['%s'];\n" % (names, m.group(2))
    visit("game.js")
    out = ["(() => {", '"use strict";', "const __modules = {};"]
    for name in order:
        src = IMPORT.sub(destructure, sources[name])
        src = re.sub(r"^export\s*\{[^}]*\};?[ \t]*\n", "", src, flags=re.M)
        src = re.sub(r"^export\s+(?=(?:async\s+)?(?:const|function|class)\b)", "", src, flags=re.M)
        if re.search(r"^\s*(import|export)\b", src, flags=re.M):
            sys.exit("%s: an import / export form the built-in bundler does not know" % name)
        exports = ", ".join(sorted(wanted.get(name, ())))
        out.append("__modules['%s'] = (() => {\n%s\nreturn { %s };\n})();" % (name, src, exports))
    out.append("})();")
    return "\n".join(out)


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
    # the installable-app links only work on a web server; the one-file copy runs from disk
    page = re.sub(r'<link rel="(manifest|icon|apple-touch-icon)"[^>]*>\n?', '', page)
    page = page.replace(tags[0], inline_script(three))
    page = page.replace(tags[1], inline_script("window.DOGFIGHT_ASSETS = {\n%s\n};" % table) + "\n"
                        + inline_script(bundle()))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
