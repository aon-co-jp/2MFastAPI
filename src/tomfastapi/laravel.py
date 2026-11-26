"""Laravel routes (routes/web.php, routes/api.php) -> FastAPI/MFastAPI-compatible Python.

Only simple closures are translated:
  return 'text';  /  return 'Hello ' . $name;  /  return ['k' => 'v', 'id' => $id];
Anything else becomes a route that answers 501 with a TODO comment holding the original PHP.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

def _body(src: str, start: int) -> Tuple[str, int]:
    depth, i, q = 1, start, None
    while i < len(src):
        c = src[i]
        if q:
            if c == "\\":
                i += 1
            elif c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:i], i + 1
        i += 1
    return src[start:], len(src)


def _str(tok: str, params: Optional[List[str]] = None) -> Optional[str]:
    tok = tok.strip()
    if len(tok) >= 2 and tok[0] == tok[-1] == "'":
        inner = tok[1:-1]
        if "'" in inner.replace("\\'", ""):
            return None
        return repr(inner.replace("\\'", "'").replace("\\\\", "\\"))
    if len(tok) >= 2 and tok[0] == tok[-1] == '"':
        inner = tok[1:-1]
        if '"' in inner.replace('\\"', ""):
            return None
        inner = inner.replace('\\"', '"')
        if "$" in inner:
            return _interp(inner, params or [])
        return repr(inner)
    return None


def _interp(inner: str, params: List[str]) -> Optional[str]:
    """PHP interpolation "Hello $name" / "Hi {$name}!" -> 'Hello ' + str(name). Only route parameters."""
    parts, pos = [], 0
    for m in re.finditer(r"\{\$(\w+)\}|\$(\w+)", inner):
        var = m.group(1) or m.group(2)
        if var not in params:
            return None
        if m.start() > pos:
            parts.append(repr(inner[pos:m.start()]))
        parts.append("str(%s)" % var)
        pos = m.end()
    if pos < len(inner):
        parts.append(repr(inner[pos:]))
    return " + ".join(parts)


def _split(s: str, sep: str) -> Optional[List[str]]:
    out, cur, q, depth = [], "", None, 0
    for c in s:
        if q:
            cur += c
            if c == q:
                q = None
            continue
        if c in "'\"":
            q = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if c == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
    if q:
        return None
    out.append(cur)
    return out


def _expr(e: str, params: List[str]) -> Optional[str]:
    e = e.strip()
    if e.startswith("[") and e.endswith("]"):
        items = _split(e[1:-1], ",")
        if items is None:
            return None
        pairs = []
        for it in items:
            if not it.strip():
                continue
            kv = it.split("=>", 1)
            if len(kv) != 2:
                return None
            k, v = _str(kv[0]), _expr(kv[1], params)
            if k is None or v is None:
                return None
            pairs.append("%s: %s" % (k, v))
        return "{" + ", ".join(pairs) + "}"
    parts = _split(e, ".")
    if parts is None:
        return None
    if len(parts) > 1:
        conv = []
        for p in parts:
            x = _expr(p, params)
            if x is None or x.startswith("{"):
                return None
            conv.append(x if x[0] in "'\"" or x.startswith("str(") else "str(%s)" % x)
        return " + ".join(conv)
    m = re.fullmatch(r"\$(\w+)", e)
    if m:
        return m.group(1) if m.group(1) in params else None
    if re.fullmatch(r"-?\d+(\.\d+)?", e):
        return e
    return _str(e, params)


_VERB = re.compile(r"Route::(get|post|put|patch|delete)\s*\(\s*(['\"])(.*?)\2\s*,\s*", re.S)
_GROUP = re.compile(r"Route::prefix\s*\(\s*(['\"])(.*?)\1\s*\)\s*->\s*group\s*\(\s*function\s*\(\s*\)\s*(?:use\s*\([^)]*\)\s*)?\{", re.S)
_CLOSURE = re.compile(r"function\s*\(([^)]*)\)\s*(?:use\s*\([^)]*\)\s*)?\{", re.S)
_CTRL_ARR = re.compile(r"\[\s*\\?([\w\\]+)::class\s*,\s*(['\"])(\w+)\2\s*\]", re.S)
_CTRL_AT = re.compile(r"(['\"])([\w\\]+)@(\w+)\1", re.S)
_SCALAR = ("string", "int", "float", "?string", "?int", "?float")


def _controllers(root: Optional[str]) -> dict:
    """Map (ShortClassName, method) -> (args, body) for app/Http/Controllers/**/*.php."""
    found: dict = {}
    if not root:
        return found
    base = os.path.join(root, "app", "Http", "Controllers")
    for dp, _dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith(".php"):
                continue
            with open(os.path.join(dp, fn), encoding="utf-8") as fh:
                src = fh.read()
            cm = re.search(r"class\s+(\w+)", src)
            if not cm:
                continue
            for mm in re.finditer(r"public\s+function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*[\w\\|?]+\s*)?\{", src):
                body, _ = _body(src, mm.end())
                found[(cm.group(1), mm.group(1))] = (mm.group(2), body)
    return found


def _routes(php: str, prefix: str, ctrls: dict, out: list) -> None:
    """Collect (verb, path, args, body, origin) in source order, expanding Route::prefix()->group()."""
    pos = 0
    while True:
        g, v = _GROUP.search(php, pos), _VERB.search(php, pos)
        if g and (not v or g.start() < v.start()):
            inner, pos = _body(php, g.end())
            _routes(inner, prefix + "/" + g.group(2).strip("/"), ctrls, out)
            continue
        if not v:
            return
        verb, path = v.group(1), prefix + "/" + v.group(3).strip("/")
        rest = php[v.end():]
        c = _CLOSURE.match(rest)
        a = _CTRL_ARR.match(rest)
        b = None if a else _CTRL_AT.match(rest)
        if c:
            body, end = _body(rest, c.end())
            out.append((verb, path, c.group(1), body, None))
            pos = v.end() + end
        elif a or b:
            cls, meth = (a.group(1), a.group(3)) if a else (b.group(2), b.group(3))
            short = cls.split("\\")[-1]
            origin = "%s@%s" % (short, meth)
            hit = ctrls.get((short, meth))
            if hit:
                out.append((verb, path, hit[0], hit[1], origin))
            else:
                out.append((verb, path, "", "// controller method not found: " + origin, origin))
            pos = v.end() + (a or b).end()
        else:
            out.append((verb, path, "", "// unsupported route handler", None))
            pos = v.end()


def translate(php: str, root: Optional[str] = None, sources: Optional[List[Tuple[str, str]]] = None) -> Tuple[str, int, int]:
    """Return (python source, translated count, TODO count).

    `sources` is a list of (php, url prefix); when omitted, `php` is used with no prefix.
    `root` is the Laravel project root, used to resolve controller routes."""
    lines = ["# generated by 2mfastapi laravel: FastAPI / MFastAPI compatible",
             "import mfastapi",
             "from fastapi import FastAPI",
             "from fastapi.responses import JSONResponse, PlainTextResponse", "",
             "app = FastAPI()", ""]
    ctrls = _controllers(root)
    routes: list = []
    for src, pre in (sources if sources is not None else [(php, "")]):
        _routes(src, pre, ctrls, routes)
    ok = todo = 0
    for n, (verb, path, args, body, origin) in enumerate(routes, 1):
        url = re.sub(r"\{(\w+)\?\}", r"{\1}", "/" + "/".join(x for x in path.split("/") if x))
        params = re.findall(r"\{(\w+)\}", url)
        raw_args = [x.strip() for x in args.split(",") if x.strip()]
        arg_names = []
        for x in raw_args:
            t = x.split("=")[0].split()
            if len(t) == 1 or (len(t) == 2 and t[0] in _SCALAR):
                arg_names.append(t[-1].lstrip("$"))
        py_body = None
        rm = re.fullmatch(r"\s*return\s+(.*?);\s*", body, re.S)
        # only plain route arguments (no injected objects such as `Request $request`)
        if rm and len(arg_names) == len(raw_args) and len(arg_names) <= len(params):
            expr = rm.group(1)
            # Laravel binds route segments to handler arguments by position
            for a, p in zip(arg_names, params):
                expr = re.sub(r"\$%s\b" % re.escape(a), "$" + p, expr)
            py = _expr(expr, params)
            if py is not None:
                kind = "JSONResponse" if py.startswith("{") else "PlainTextResponse"
                py_body = "    return %s(%s)" % (kind, py)
        lines.append('@app.%s("%s")' % (verb, url))
        lines.append("def route_%d(%s):" % (n, ", ".join("%s: str" % p for p in params)))
        if origin:
            lines.append("    # from controller %s" % origin)
        if py_body:
            ok += 1
            lines.append(py_body)
        else:
            todo += 1
            lines.append("    # TODO(2mfastapi): not translated automatically. Original PHP:")
            for l in body.strip().splitlines():
                lines.append("    #   " + l.rstrip())
            lines.append('    return JSONResponse({"detail": "Not Implemented (converted from Laravel)"}, status_code=501)')
        lines.append("")
    lines.append("# MFastAPI: speed up route lookup (Rust/Mojo/C core when available; otherwise it changes nothing).")
    lines.append("# Must run after every route is registered. Set MFASTAPI_DISABLE=1 to turn it off.")
    lines.append("mfastapi.accelerate(app)")
    lines.append("")
    return "\n".join(lines), ok, todo


def convert_laravel(root: str, out_dir: str) -> Tuple[int, int]:
    """Translate routes/web.php and routes/api.php (api.php routes get the /api prefix, as in Laravel).
    Controller routes are resolved from app/Http/Controllers."""
    os.makedirs(out_dir, exist_ok=True)
    srcs = []
    for fn, prefix in (("web.php", ""), ("api.php", "/api")):
        p = os.path.join(root, "routes", fn)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                srcs.append((fh.read(), prefix))
    code, ok, todo = translate("", root=root, sources=srcs)
    with open(os.path.join(out_dir, "main.py"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(code)
    return ok, todo
