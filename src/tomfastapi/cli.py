"""2mfastapi scan DIR | convert PATH -o OUT | auto DIR [-o OUT]"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .convert import convert
from .scan import scan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="2mfastapi", description="Convert Flask / Django / FastAPI projects to MFastAPI.")
    ap.add_argument("--version", action="version", version="2mfastapi " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="list the projects found below a directory")
    s.add_argument("path")
    s.add_argument("--json", action="store_true")
    c = sub.add_parser("convert", help="convert the project at PATH")
    c.add_argument("path")
    c.add_argument("-o", "--output", required=True)
    a = sub.add_parser("auto", help="convert every project found below a directory")
    a.add_argument("path")
    a.add_argument("-o", "--output", help="destination root (default: <path>-mfastapi)")
    lv = sub.add_parser("laravel", help="convert Laravel routes/web.php and routes/api.php")
    lv.add_argument("path")
    lv.add_argument("-o", "--output", required=True)
    ns = ap.parse_args(argv)
    if ns.cmd == "laravel":
        from .laravel import convert_laravel
        ok, todo = convert_laravel(ns.path, ns.output)
        print("wrote %s (%d routes translated, %d TODO -> 501)" % (os.path.join(ns.output, "main.py"), ok, todo), file=sys.stderr)
        return 0
    if ns.cmd == "scan":
        ps = scan(ns.path)
        if ns.json:
            print(json.dumps([p.to_dict() for p in ps], ensure_ascii=False))
        else:
            for i, p in enumerate(ps, 1):
                print("[%d] %s  %s  routes~%d  %s%s" % (i, p.kind, p.name, p.routes, p.path, ("  libs: " + ", ".join(p.libs)) if p.libs else ""))
            if not ps:
                print("No Flask, Django or FastAPI project found. / プロジェクトは見つかりませんでした。")
        return 0
    if ns.cmd == "convert":
        ps = [p for p in scan(ns.path) if os.path.abspath(p.path) == os.path.abspath(ns.path)] or scan(ns.path)
        if not ps:
            print("no project found", file=sys.stderr)
            return 1
        routes, warns = convert(ps[0], ns.output)
        print("wrote %s (%d routes)" % (ns.output, routes), file=sys.stderr)
        for w in warns:
            print("warning: %s" % w, file=sys.stderr)
        return 0
    dest = ns.output or (os.path.abspath(ns.path).rstrip("/\\") + "-mfastapi")
    for p in scan(ns.path):
        routes, warns = convert(p, os.path.join(dest, p.name))
        print("%s %s -> %s (%d routes)" % (p.kind, p.name, os.path.join(dest, p.name), routes))
        for w in warns:
            print("  warning: %s" % w)
    return 0
