"""Laravel (routes, controllers, simple Eloquent, Blade) -> FastAPI/MFastAPI-compatible Python.

What is translated (anything else keeps the original PHP in a TODO comment and answers 501):
  routes      Route::get/post/put/patch/delete, ->name(), ->middleware(),
              Route::prefix()/middleware()/name()/controller() chains ending in ->group(function () {...}),
              Route::group(['prefix' => .., 'middleware' => .., 'as' => ..], function () {...}),
              Route::resource / Route::apiResource (->only / ->except)
  handlers    closures, [Controller::class, 'm'], 'Controller@m', 'm' inside Route::controller()->group
  bodies      `$v = EXPR;` lines, `abort(N)`, ending in `return EXPR;`
  EXPR        strings ('..', ".. $param .." / "{$param}"), numbers, true/false/null, `.` concatenation,
              arrays [k => v] / [a, b], compact('a'), $request->all()/input()/query(),
              Model::all()/find()/findOrFail()/where(..)->get()/first()/create(..),
              $model->attr, view('name', [...]), response()->json(X[, status])
  Blade       resources/views/**/*.blade.php -> templates/**/*.html (Jinja2): {{ }}, {!! !!}, {{-- --}},
              @if/@elseif/@else/@endif, @foreach, @forelse/@empty, @extends/@section/@yield, @include
  Eloquent    SQLAlchemy Core; columns from database/migrations Schema::create(...)
Middleware is NOT converted: routes using it answer 501 until a function is put in MIDDLEWARE (safe default).
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------- small PHP scanners

def _body(src: str, start: int, open_c: str = "{", close_c: str = "}") -> Tuple[str, int]:
    """Text up to the bracket matching an already-consumed opener at `start`."""
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
        elif c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return src[start:i], i + 1
        i += 1
    return src[start:], len(src)


def _split(s: str, sep: str) -> Optional[List[str]]:
    """Split on `sep` at nesting depth 0, outside quotes. None if a quote is unbalanced."""
    out, cur, q, depth, i = [], "", None, 0, 0
    while i < len(s):
        c = s[i]
        if q:
            cur += c
            if c == "\\" and i + 1 < len(s):
                cur += s[i + 1]
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in "'\"":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if depth == 0 and s.startswith(sep, i) and not (sep == "." and s.startswith("..", i)):
            out.append(cur)
            cur = ""
            i += len(sep)
            continue
        cur += c
        i += 1
    if q:
        return None
    out.append(cur)
    return out


def _php_str(tok: str) -> Optional[str]:
    """Plain (non-interpolating) PHP string literal -> its value."""
    tok = tok.strip()
    if len(tok) >= 2 and tok[0] == tok[-1] == "'":
        inner = tok[1:-1]
        if "'" in inner.replace("\\'", ""):
            return None
        return inner.replace("\\'", "'").replace("\\\\", "\\")
    if len(tok) >= 2 and tok[0] == tok[-1] == '"' and "$" not in tok:
        inner = tok[1:-1]
        if '"' in inner.replace('\\"', ""):
            return None
        return inner.replace('\\"', '"')
    return None


def _singular(w: str) -> str:
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("ses", "xes", "zes", "ches", "shes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _plural_snake(name: str) -> str:
    s = re.sub(r"(?<!^)([A-Z])", r"_\1", name).lower()
    if s.endswith("y") and s[-2:-1] not in "aeiou":
        return s[:-1] + "ies"
    if s.endswith(("s", "x", "z", "ch", "sh")):
        return s + "es"
    return s + "s"


# ---------------------------------------------------------------- project scan

class Project:
    def __init__(self, root: Optional[str]):
        self.root = root
        self.controllers: Dict[Tuple[str, str], Tuple[str, str]] = {}
        self.tables: Dict[str, List[Tuple[str, str]]] = {}   # table -> [(column, sqlalchemy type)]
        self.model_tables: Dict[str, str] = {}               # Model -> table (from app/Models $table)
        self.views: Dict[str, str] = {}                      # 'a.b' -> jinja source
        self.view_warnings: Dict[str, List[str]] = {}
        if root:
            self._scan()

    def _php_files(self, *parts: str):
        base = os.path.join(self.root, *parts)
        for dp, _dn, fns in os.walk(base):
            for fn in sorted(fns):
                if fn.endswith(".php"):
                    p = os.path.join(dp, fn)
                    with open(p, encoding="utf-8") as fh:
                        yield p, fh.read()

    def _scan(self) -> None:
        for _p, src in self._php_files("app", "Http", "Controllers"):
            cm = re.search(r"class\s+(\w+)", src)
            if not cm:
                continue
            for mm in re.finditer(r"public\s+function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*[\w\\|?]+\s*)?\{", src):
                body, _ = _body(src, mm.end())
                self.controllers[(cm.group(1), mm.group(1))] = (mm.group(2), body)
        for _p, src in self._php_files("app", "Models"):
            cm = re.search(r"class\s+(\w+)", src)
            tm = re.search(r"\$table\s*=\s*['\"](\w+)['\"]", src)
            if cm and tm:
                self.model_tables[cm.group(1)] = tm.group(1)
        for _p, src in self._php_files("database", "migrations"):
            for sm in re.finditer(r"Schema::create\s*\(\s*['\"](\w+)['\"]\s*,\s*function\s*\([^)]*\)\s*\{", src):
                body, _ = _body(src, sm.end())
                cols: List[Tuple[str, str]] = []
                for cm in re.finditer(r"\$table->(\w+)\(\s*(?:['\"](\w+)['\"])?", body):
                    kind, col = cm.group(1), cm.group(2)
                    if kind in ("id", "bigIncrements", "increments"):
                        cols.append((col or "id", "pk"))
                    elif kind == "timestamps":
                        cols += [("created_at", "DateTime"), ("updated_at", "DateTime")]
                    elif kind == "softDeletes":
                        cols.append(("deleted_at", "DateTime"))
                    elif col:
                        t = {"string": "String", "char": "String", "text": "Text", "longText": "Text",
                             "mediumText": "Text", "integer": "Integer", "bigInteger": "Integer",
                             "unsignedBigInteger": "Integer", "unsignedInteger": "Integer", "foreignId": "Integer",
                             "tinyInteger": "Integer", "smallInteger": "Integer", "boolean": "Boolean",
                             "float": "Float", "double": "Float", "decimal": "Float", "date": "Date",
                             "dateTime": "DateTime", "timestamp": "DateTime", "json": "JSON"}.get(kind, "String")
                        cols.append((col, t))
                self.tables[sm.group(1)] = cols
        vroot = os.path.join(self.root, "resources", "views")
        for dp, _dn, fns in os.walk(vroot):
            for fn in sorted(fns):
                if fn.endswith(".blade.php"):
                    full = os.path.join(dp, fn)
                    rel = os.path.relpath(full, vroot)[: -len(".blade.php")].replace(os.sep, ".")
                    with open(full, encoding="utf-8") as fh:
                        src, warns = blade_to_jinja(fh.read())
                    self.views[rel] = src
                    if warns:
                        self.view_warnings[rel] = warns

    def table_of(self, model: str) -> str:
        return self.model_tables.get(model) or _plural_snake(model)


# ---------------------------------------------------------------- Blade -> Jinja2

def _blade_expr(e: str) -> str:
    e = e.strip()
    e = re.sub(r"count\(\s*(\$[\w>\-\[\]'\"]+)\s*\)", r"(\1)|length", e)
    e = e.replace("===", "==").replace("!==", "!=")
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    e = re.sub(r"->(\w+)", r".\1", e)
    e = re.sub(r"\$(\w+)", r"\1", e)
    parts = _split(e, ".")  # PHP concatenation `a . b` -> Jinja `a ~ b` (only spaced dots)
    if parts is not None and " . " in e:
        e = " ~ ".join(p.strip() for p in _split(e, " . ") or [e])
    e = e.replace("null", "none").replace("true", "true")
    return re.sub(r"\s+", " ", e).strip()


def blade_to_jinja(src: str) -> Tuple[str, List[str]]:
    """Convert a simple Blade template to Jinja2. Returns (jinja source, warnings)."""
    warns: List[str] = []
    out = re.sub(r"\{\{--(.*?)--\}\}", lambda m: "{#" + m.group(1) + "#}", src, flags=re.S)
    out = re.sub(r"\{!!(.*?)!!\}", lambda m: "{{ (" + _blade_expr(m.group(1)) + ")|safe }}", out, flags=re.S)
    out = re.sub(r"(?<!@)\{\{(?!#)(.*?)\}\}", lambda m: "{{ " + _blade_expr(m.group(1)) + " }}", out, flags=re.S)
    forelse: List[str] = []

    def directive(m: "re.Match[str]") -> str:
        name = m.group(1)
        arg = None
        rest_end = m.end()
        if rest_end < len(out_src[0]) and out_src[0][rest_end] == "(":
            arg, end = _body(out_src[0], rest_end + 1, "(", ")")
            consumed[0] = end
        else:
            consumed[0] = rest_end
        if name == "if":
            return "{%% if %s %%}" % _blade_expr(arg or "")
        if name == "elseif":
            return "{%% elif %s %%}" % _blade_expr(arg or "")
        if name == "else":
            return "{% else %}"
        if name in ("endif", "endunless"):
            return "{% endif %}"
        if name == "unless":
            return "{%% if not (%s) %%}" % _blade_expr(arg or "")
        if name in ("foreach", "forelse"):
            fm = re.fullmatch(r"\s*(.+?)\s+as\s+\$(\w+)(?:\s*=>\s*\$(\w+))?\s*", arg or "")
            if not fm:
                warns.append("@%s(%s) not converted" % (name, arg))
                return m.group(0)
            seq = _blade_expr(fm.group(1))
            if name == "forelse":
                forelse.append("x")
            if fm.group(3):
                return "{%% for %s, %s in (%s).items() %%}" % (fm.group(2), fm.group(3), seq)
            return "{%% for %s in %s %%}" % (fm.group(2), seq)
        if name == "empty" and forelse:
            return "{% else %}"
        if name in ("endforeach", "endforelse"):
            if name == "endforelse" and forelse:
                forelse.pop()
            return "{% endfor %}"
        if name == "extends":
            return '{%% extends "%s.html" %%}' % _php_str(arg or "''").replace(".", "/")
        if name == "include":
            return '{%% include "%s.html" %%}' % (_php_str((_split(arg or "''", ",") or ["''"])[0]) or "").replace(".", "/")
        if name == "yield":
            return "{%% block %s %%}{%% endblock %%}" % _php_str((_split(arg or "''", ",") or ["''"])[0])
        if name == "section":
            parts = _split(arg or "", ",") or []
            if len(parts) == 2:
                return "{%% block %s %%}{{ %s }}{%% endblock %%}" % (_php_str(parts[0]), _blade_expr(parts[1]))
            return "{%% block %s %%}" % _php_str(parts[0])
        if name in ("endsection", "show", "stop"):
            return "{% endblock %}"
        if name == "csrf":
            warns.append("@csrf dropped (no CSRF token in the converted app)")
            return "{# @csrf not converted #}"
        warns.append("@%s not converted" % name)
        return m.group(0)

    res, pos = [], 0
    out_src = [out]
    consumed = [0]
    dm = re.compile(r"(?<![\w@{])@(\w+)")
    while True:
        m = dm.search(out, pos)
        if not m:
            res.append(out[pos:])
            break
        res.append(out[pos:m.start()])
        res.append(directive(m))
        pos = consumed[0]
    text = "".join(res)
    if warns:
        text = "{# 2mfastapi: " + "; ".join(warns) + " #}\n" + text
    return text, warns


# ---------------------------------------------------------------- PHP expression -> Python

class Ctx:
    def __init__(self, proj: Project, params: List[str]):
        self.proj = proj
        self.params = params
        self.vars: Dict[str, str] = {p: "str" for p in params}   # name -> kind
        self.request_var: Optional[str] = None
        self.uses_body = False
        self.uses_request = False
        self.uses_db = False
        self.uses_view = False


def _interp(inner: str, ctx: Ctx) -> Optional[Tuple[str, str]]:
    parts, pos = [], 0
    for m in re.finditer(r"\{\$(\w+)\}|\$(\w+)", inner):
        var = m.group(1) or m.group(2)
        if var not in ctx.vars:
            return None
        if m.start() > pos:
            parts.append(repr(inner[pos:m.start()]))
        parts.append("str(%s)" % var)
        pos = m.end()
    if pos < len(inner):
        parts.append(repr(inner[pos:]))
    return " + ".join(parts), "str"


_DB = re.compile(r"\\?(?:App\\Models\\)?([A-Z]\w*)::(\w+)\((.*)\)$", re.S)


def _args(s: str, ctx: Ctx) -> Optional[List[Tuple[str, str]]]:
    if not s.strip():
        return []
    items = _split(s, ",")
    if items is None:
        return None
    out = []
    for it in items:
        x = _expr(it, ctx)
        if x is None:
            return None
        out.append(x)
    return out


def _db_expr(e: str, ctx: Ctx) -> Optional[Tuple[str, str]]:
    # Model::where(..)[->where(..)]->get()/first()
    m = re.match(r"\\?(?:App\\Models\\)?([A-Z]\w*)::where\(", e)
    if m:
        table, rest, conds = ctx.proj.table_of(m.group(1)), e[m.end() - 1:], []
        while rest.startswith("("):
            inner, end = _body(rest, 1, "(", ")")
            a = _args(inner, ctx)
            if a is None or len(a) not in (2, 3):
                return None
            if len(a) == 2:
                conds.append("(%s, '=', %s)" % (a[0][0], a[1][0]))
            else:
                conds.append("(%s, %s, %s)" % (a[0][0], a[1][0], a[2][0]))
            rest = rest[end:].strip()
            if rest.startswith("->where("):
                rest = rest[len("->where"):]
        fn = {"->get()": "_db_where", "->first()": "_db_first"}.get(rest.replace(" ", ""))
        if not fn:
            return None
        ctx.uses_db = True
        return "%s(%r, [%s])" % (fn, table, ", ".join(conds)), "json"
    m = _DB.fullmatch(e)
    if not m or m.group(1) in ("Route", "Str", "Arr", "Auth", "DB", "Request"):
        return None
    model, meth, raw = m.group(1), m.group(2), m.group(3)
    a = _args(raw, ctx)
    if a is None:
        return None
    table = ctx.proj.table_of(model)
    fn = {"all": ("_db_all", 0), "find": ("_db_find", 1), "findOrFail": ("_db_find_or_404", 1),
          "create": ("_db_create", 1)}.get(meth)
    if not fn or len(a) != fn[1]:
        return None
    ctx.uses_db = True
    return "%s(%r%s)" % (fn[0], table, "".join(", " + x[0] for x in a)), "json"


def _expr(e: str, ctx: Ctx) -> Optional[Tuple[str, str]]:
    """PHP expression -> (python expression, kind) with kind in str/num/json/html/any/resp."""
    e = e.strip()
    if not e:
        return None
    if e.startswith("(") and e.endswith(")") and _body(e, 1, "(", ")")[1] == len(e):
        return _expr(e[1:-1], ctx)
    if re.fullmatch(r"-?\d+(\.\d+)?", e):
        return e, "num"
    low = e.lower()
    if low in ("true", "false", "null"):
        return {"true": "True", "false": "False", "null": "None"}[low], "json"
    if e.startswith("[") and e.endswith("]") and _body(e, 1, "[", "]")[1] == len(e):
        items = [x for x in (_split(e[1:-1], ",") or [None]) if x is None or x.strip()]
        if None in items:
            return None
        if items and all("=>" in (_split(x, "=>") and x) and len(_split(x, "=>") or []) == 2 for x in items):
            pairs = []
            for it in items:
                k, v = _split(it, "=>")
                kk, vv = _expr(k, ctx), _expr(v, ctx)
                if kk is None or vv is None:
                    return None
                pairs.append("%s: %s" % (kk[0], vv[0]))
            return "{" + ", ".join(pairs) + "}", "json"
        if any("=>" in x for x in items):
            return None
        vals = _args(e[1:-1], ctx)
        return (None if vals is None else ("[" + ", ".join(v[0] for v in vals) + "]", "json"))
    parts = _split(e, ".")
    if parts is None:
        return None
    if len(parts) > 1:
        conv = []
        for p in parts:
            x = _expr(p, ctx)
            if x is None or x[1] in ("json", "html", "resp"):
                return None
            conv.append(x[0] if x[1] == "str" else "str(%s)" % x[0])
        return " + ".join(conv), "str"
    if e[0] in "'\"":
        if e[0] == '"' and e[-1] == '"' and "$" in e:
            inner = e[1:-1]
            if '"' in inner.replace('\\"', ""):
                return None
            return _interp(inner.replace('\\"', '"'), ctx)
        s = _php_str(e)
        return None if s is None else (repr(s), "str")
    # $request->...
    rq = ctx.request_var
    if rq:
        m = re.fullmatch(r"\$%s->all\(\)" % rq, e)
        if m:
            ctx.uses_body = True
            return "_body", "json"
        m = re.fullmatch(r"\$%s->(input|query)\((.*)\)" % rq, e, re.S)
        if m:
            a = _args(m.group(2), ctx)
            if a is None or len(a) not in (1, 2):
                return None
            if m.group(1) == "input":
                ctx.uses_body = True
                return "_body.get(%s)" % ", ".join(x[0] for x in a), "any"
            ctx.uses_request = True
            return "request.query_params.get(%s)" % ", ".join(x[0] for x in a), "any"
    m = re.fullmatch(r"\$(\w+)", e)
    if m:
        v = m.group(1)
        return (v, ctx.vars[v]) if v in ctx.vars else None
    m = re.fullmatch(r"\$(\w+)->(\w+)", e)
    if m and m.group(1) in ctx.vars:
        return "%s[%r]" % (m.group(1), m.group(2)), "any"
    m = re.fullmatch(r"compact\((.*)\)", e, re.S)
    if m:
        names = [_php_str(x) for x in (_split(m.group(1), ",") or [])]
        if not names or None in names or any(n not in ctx.vars for n in names):
            return None
        return "{" + ", ".join("%r: %s" % (n, n) for n in names) + "}", "json"
    m = re.fullmatch(r"view\((.*)\)", e, re.S)
    if m:
        a = _split(m.group(1), ",") or []
        name = _php_str(a[0]) if a else None
        if not name or name not in ctx.proj.views or len(a) > 2:
            return None
        data = _expr(a[1], ctx) if len(a) == 2 else ("{}", "json")
        if data is None or not data[0].startswith("{"):
            return None
        ctx.uses_view = True
        return "_render(%r, %s)" % (name, data[0]), "html"
    m = re.fullmatch(r"response\(\)->json\((.*)\)", e, re.S)
    if m:
        a = _args(m.group(1), ctx)
        if a is None or len(a) not in (1, 2):
            return None
        st = (", status_code=%s" % a[1][0]) if len(a) == 2 else ""
        return "JSONResponse(jsonable_encoder(%s)%s)" % (a[0][0], st), "resp"
    return _db_expr(e, ctx)


def _statements(body: str, ctx: Ctx) -> Optional[List[str]]:
    """Translate a handler body into python lines, or None."""
    stmts = [s.strip() for s in (_split(body, ";") or [None]) if s is None or s.strip()]
    if not stmts or None in stmts:
        return None
    lines: List[str] = []
    for i, st in enumerate(stmts):
        last = i == len(stmts) - 1
        if st.startswith("//") or st.startswith("#"):
            return None
        m = re.fullmatch(r"abort\((\d+)(?:\s*,\s*(.+))?\)", st, re.S)
        if m:
            msg = _expr(m.group(2), ctx) if m.group(2) else None
            lines.append("raise HTTPException(status_code=%s%s)" % (m.group(1), (", detail=" + msg[0]) if msg else ""))
            continue
        m = re.fullmatch(r"\$(\w+)\s*=\s*(.+)", st, re.S)
        if m and not last and not m.group(2).startswith("="):
            x = _expr(m.group(2), ctx)
            if x is None or x[1] == "resp":
                return None
            ctx.vars[m.group(1)] = x[1]
            lines.append("%s = %s" % (m.group(1), x[0]))
            continue
        m = re.fullmatch(r"return\s+(.+)", st, re.S)
        if m and last:
            x = _expr(m.group(1), ctx)
            if x is None:
                return None
            code, kind = x
            if kind == "resp":
                lines.append("return " + code)
            elif kind == "html":
                lines.append("return HTMLResponse(%s)" % code)
            elif kind == "str":
                lines.append("return PlainTextResponse(%s)" % code)
            else:
                lines.append("return JSONResponse(jsonable_encoder(%s))" % code)
            return lines
        return None
    return None


# ---------------------------------------------------------------- routes

_VERB = re.compile(r"Route::(get|post|put|patch|delete|any)\s*\(\s*(['\"])(.*?)\2\s*,\s*", re.S)
_GROUP_CHAIN = re.compile(r"Route::((?:(?:prefix|middleware|name|as|controller|namespace|domain)\s*\((?:[^()]|\([^()]*\))*\)\s*->\s*)+)group\s*\(\s*function\s*\(\s*\)\s*(?:use\s*\([^)]*\)\s*)?\{", re.S)
_GROUP_ARR = re.compile(r"Route::group\s*\(\s*\[", re.S)
_RESOURCE = re.compile(r"Route::(resource|apiResource)\s*\(\s*(['\"])(.*?)\2\s*,\s*\\?([\w\\]+)::class\s*\)", re.S)
_CLOSURE = re.compile(r"(?:static\s+)?function\s*\(([^)]*)\)\s*(?:use\s*\([^)]*\)\s*)?(?::\s*[\w\\|?]+\s*)?\{", re.S)
_ARROW = re.compile(r"(?:static\s+)?fn\s*\(([^)]*)\)\s*=>\s*", re.S)
_CTRL_ARR = re.compile(r"\[\s*\\?([\w\\]+)::class\s*,\s*(['\"])(\w+)\2\s*\]", re.S)
_CTRL_AT = re.compile(r"(['\"])([\w\\]+)@(\w+)\1", re.S)
_CTRL_NAME = re.compile(r"(['\"])(\w+)\1", re.S)
_TAIL = re.compile(r"\s*->\s*(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", re.S)

_RESOURCE_ACTIONS = [("index", "get", ""), ("create", "get", "/create"), ("store", "post", ""),
                     ("show", "get", "/{%s}"), ("edit", "get", "/{%s}/edit"),
                     ("update", "put_patch", "/{%s}"), ("destroy", "delete", "/{%s}")]


def _str_list(arg: str) -> List[str]:
    arg = arg.strip()
    if arg.startswith("[") and arg.endswith("]"):
        arg = arg[1:-1]
    return [s for s in (_php_str(x) for x in (_split(arg, ",") or [])) if s]


class Scope:
    def __init__(self, prefix="", name="", middleware=None, controller=None):
        self.prefix, self.name, self.controller = prefix, name, controller
        self.middleware = list(middleware or [])

    def child(self, prefix="", name="", middleware=None, controller=None):
        return Scope(self.prefix + ("/" + prefix.strip("/") if prefix.strip("/") else ""),
                     self.name + name, self.middleware + list(middleware or []), controller or self.controller)


class Route:
    def __init__(self, verbs, path, args, body, origin, scope, name=None, middleware=None, arrow=False):
        self.verbs, self.path, self.args, self.body, self.origin = verbs, path, args, body, origin
        self.name = (scope.name + name) if name else None
        self.middleware = scope.middleware + list(middleware or [])
        self.arrow = arrow


def _handler(proj: Project, ctrl: Optional[str], meth: str):
    short = ctrl.split("\\")[-1] if ctrl else ""
    origin = "%s@%s" % (short, meth)
    hit = proj.controllers.get((short, meth))
    if hit:
        return hit[0], hit[1], origin
    return "", "// controller method not found: " + origin, origin


def _routes(php: str, scope: Scope, proj: Project, out: List[Route]) -> None:
    pos = 0
    while True:
        cands = [(m.start(), k, m) for k, m in (("chain", _GROUP_CHAIN.search(php, pos)), ("arr", _GROUP_ARR.search(php, pos)),
                                                 ("res", _RESOURCE.search(php, pos)), ("verb", _VERB.search(php, pos))) if m]
        if not cands:
            return
        _s, kind, m = min(cands, key=lambda c: c[0])
        if kind == "chain":
            kw = {"prefix": "", "name": "", "middleware": [], "controller": None}
            for cm in re.finditer(r"(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", m.group(1)):
                k, a = cm.group(1), cm.group(2)
                if k == "prefix":
                    kw["prefix"] = _php_str(a) or ""
                elif k in ("name", "as"):
                    kw["name"] = _php_str(a) or ""
                elif k == "middleware":
                    kw["middleware"] += _str_list(a)
                elif k == "controller":
                    cc = re.match(r"\s*\\?([\w\\]+)::class", a)
                    kw["controller"] = cc.group(1) if cc else None
            inner, pos = _body(php, m.end())
            _routes(inner, scope.child(**kw), proj, out)
            continue
        if kind == "arr":
            opts, end = _body(php, m.end(), "[", "]")
            cm = re.match(r"\s*,\s*function\s*\(\s*\)\s*(?:use\s*\([^)]*\)\s*)?\{", php[end:])
            if not cm:
                pos = end
                continue
            kw = {"prefix": "", "name": "", "middleware": [], "controller": None}
            for it in _split(opts, ",") or []:
                kv = _split(it, "=>")
                if not kv or len(kv) != 2:
                    continue
                k = _php_str(kv[0]) or ""
                if k == "prefix":
                    kw["prefix"] = _php_str(kv[1]) or ""
                elif k == "as":
                    kw["name"] = _php_str(kv[1]) or ""
                elif k == "middleware":
                    kw["middleware"] += _str_list(kv[1])
            inner, pos = _body(php, end + cm.end())
            _routes(inner, scope.child(**kw), proj, out)
            continue
        if kind == "res":
            res_name, ctrl, pos = m.group(3), m.group(4), m.end()
            only = except_ = None
            mws: List[str] = []
            while True:
                t = _TAIL.match(php, pos)
                if not t:
                    break
                if t.group(1) == "only":
                    only = _str_list(t.group(2))
                elif t.group(1) == "except":
                    except_ = _str_list(t.group(2))
                elif t.group(1) == "middleware":
                    mws += _str_list(t.group(2))
                pos = t.end()
            last = res_name.split(".")[-1]
            param = _singular(last).replace("-", "_")
            base = "/" + res_name.replace(".", "/").strip("/")
            for act, verb, suffix in _RESOURCE_ACTIONS:
                if m.group(1) == "apiResource" and act in ("create", "edit"):
                    continue
                if (only is not None and act not in only) or (except_ and act in except_):
                    continue
                args, body, origin = _handler(proj, ctrl, act)
                verbs = ["put", "patch"] if verb == "put_patch" else [verb]
                path = scope.prefix + base + (suffix % param if "%s" in suffix else suffix)
                out.append(Route(verbs, path, args, body, origin, scope, name="%s.%s" % (last, act), middleware=mws))
            continue
        # plain verb route
        verb, path = m.group(1), scope.prefix + "/" + m.group(3).strip("/")
        rest_at = m.end()
        rest = php[rest_at:]
        c, ar = _CLOSURE.match(rest), _ARROW.match(rest)
        a, b = _CTRL_ARR.match(rest), _CTRL_AT.match(rest)
        n = _CTRL_NAME.match(rest) if scope.controller else None
        arrow = False
        if c:
            body, end = _body(rest, c.end())
            args, origin = c.group(1), None
        elif ar:
            # fn (...) => EXPR  -> body is "return EXPR"
            j = ar.end()
            depth, q, k = 0, None, j
            while k < len(rest):
                ch = rest[k]
                if q:
                    if ch == "\\":
                        k += 1
                    elif ch == q:
                        q = None
                elif ch in "'\"":
                    q = ch
                elif ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                k += 1
            body, end, args, origin, arrow = "return " + rest[j:k].strip() + ";", k, ar.group(1), None, True
        elif a or b:
            ctrl, meth = (a.group(1), a.group(3)) if a else (b.group(2), b.group(3))
            args, body, origin = _handler(proj, ctrl, meth)
            end = (a or b).end()
        elif n:
            args, body, origin = _handler(proj, scope.controller, n.group(2))
            end = n.end()
        else:
            args, body, origin, end = "", "// unsupported route handler", None, 0
        pos = rest_at + end
        close = re.match(r"\s*\)", php[pos:])
        if close:
            pos += close.end()
        rname, mws = None, []
        while True:
            t = _TAIL.match(php, pos)
            if not t:
                break
            if t.group(1) == "name":
                rname = _php_str(t.group(2))
            elif t.group(1) == "middleware":
                mws += _str_list(t.group(2))
            pos = t.end()
        verbs = ["get", "post", "put", "patch", "delete"] if verb == "any" else [verb]
        out.append(Route(verbs, path, args, body, origin, scope, name=rname, middleware=mws, arrow=arrow))


# ---------------------------------------------------------------- code generation

_SKIP_MW = ("web", "api")

_HEADER = '''# generated by 2mfastapi laravel: FastAPI / MFastAPI compatible
import inspect
import os
from urllib.parse import parse_qsl

import mfastapi
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

app = FastAPI()

# Laravel middleware is not converted. A route that used middleware answers 501 until you put
# a function here, e.g. MIDDLEWARE["auth"] = check_login (raise HTTPException to refuse).
MIDDLEWARE = {}


def _mw(name):
    async def dep(request: Request):
        fn = MIDDLEWARE.get(name)
        if fn is None:
            raise HTTPException(status_code=501, detail="Laravel middleware '%s' is not converted" % name)
        r = fn(request)
        if inspect.isawaitable(r):
            await r
    return dep


async def _read_body(request):
    """Like Laravel $request->all(): query string merged with a JSON or form body."""
    data = dict(request.query_params)
    raw = await request.body()
    ctype = request.headers.get("content-type", "")
    if raw and "json" in ctype:
        import json
        try:
            v = json.loads(raw)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid JSON body")
        if isinstance(v, dict):
            data.update(v)
    elif raw and "x-www-form-urlencoded" in ctype:
        data.update(parse_qsl(raw.decode("utf-8", "replace")))
    return data
'''

_DB_CODE = '''

# ---- Eloquent -> SQLAlchemy Core (tables from database/migrations; DATABASE_URL, default sqlite file)
import datetime as _dt
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text,
                        create_engine, insert, select)

_engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///laravel.db"))
_meta = MetaData()
%(tables)s
_meta.create_all(_engine)  # like `php artisan migrate` for tables that do not exist yet


def _t(name):
    if name not in _meta.tables:
        Table(name, _meta, autoload_with=_engine)  # a table that has no migration: read it from the database
    return _meta.tables[name]


def _rows(stmt):
    with _engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(stmt)]


def _db_all(name):
    return _rows(select(_t(name)))


def _db_find(name, key):
    t = _t(name)
    pk = list(t.primary_key.columns)[0]
    r = _rows(select(t).where(pk == key))
    return r[0] if r else None


def _db_find_or_404(name, key):
    r = _db_find(name, key)
    if r is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return r


_OPS = {"=": "__eq__", "==": "__eq__", "!=": "__ne__", "<>": "__ne__", "<": "__lt__", ">": "__gt__",
        "<=": "__le__", ">=": "__ge__"}


def _db_where(name, conds):
    t = _t(name)
    stmt = select(t)
    for col, op, val in conds:
        stmt = stmt.where(getattr(t.c[col], _OPS[op])(val))
    return _rows(stmt)


def _db_first(name, conds):
    r = _db_where(name, conds)
    return r[0] if r else None


def _db_create(name, data):
    t = _t(name)
    vals = {k: v for k, v in dict(data).items() if k in t.c and not t.c[k].primary_key}
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    for k in ("created_at", "updated_at"):
        if k in t.c and k not in vals:
            vals[k] = now
    with _engine.begin() as c:
        res = c.execute(insert(t).values(**vals))
        key = res.inserted_primary_key[0] if res.inserted_primary_key else None
    return _db_find(name, key) if key is not None else vals
'''

_VIEW_CODE = '''

# ---- Blade -> Jinja2 (templates/ next to this file)
from jinja2 import Environment, FileSystemLoader, select_autoescape

_jinja = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")),
                     autoescape=select_autoescape(["html"]))


def _render(name, data):
    return _jinja.get_template(name.replace(".", "/") + ".html").render(**data)
'''


def _arg_info(args: str, proj: Project):
    """-> (route arg names in order, request var, {var: model}) or None for unsupported args."""
    names, req, models = [], None, {}
    for x in [x.strip() for x in args.split(",") if x.strip()]:
        x = x.split("=")[0].strip()
        t = x.split()
        if len(t) == 1:
            names.append(t[0].lstrip("$&"))
        elif len(t) == 2:
            typ, var = t[0].lstrip("?\\").split("\\")[-1], t[1].lstrip("$&")
            if typ == "Request" or typ.endswith("Request"):
                req = var
            elif typ in ("string", "int", "float", "bool"):
                names.append(var)
            elif typ[:1].isupper():
                names.append(var)
                models[var] = typ
            else:
                return None
        else:
            return None
    return names, req, models


def _route_code(r: Route, n: int, proj: Project) -> Tuple[List[str], bool]:
    url = re.sub(r"\{(\w+)\?\}", r"{\1}", "/" + "/".join(x for x in r.path.split("/") if x))
    params = re.findall(r"\{(\w+)\}", url)
    deco_kw = []
    if r.name:
        deco_kw.append("name=%r" % r.name)
    mws = [m for m in r.middleware if m.split(":")[0] not in _SKIP_MW]
    if mws:
        deco_kw.append("dependencies=[%s]" % ", ".join("Depends(_mw(%r))" % m for m in mws))
    kw = (", " + ", ".join(deco_kw)) if deco_kw else ""
    if len(r.verbs) == 1:
        deco = '@app.%s("%s"%s)' % (r.verbs[0], url, kw)
    else:
        deco = '@app.api_route("%s", methods=[%s]%s)' % (url, ", ".join('"%s"' % v.upper() for v in r.verbs), kw)
    body_lines = None
    info = _arg_info(r.args, proj)
    ctx = Ctx(proj, params)
    pre: List[str] = []
    if info is not None and len(info[0]) <= len(params):
        names, req, models = info
        ctx.request_var = req
        body = r.body
        # Laravel binds route segments to handler arguments by position
        for a, p in zip(names, params):
            body = re.sub(r"\$%s\b" % re.escape(a), "$" + p, body)
            if a in models:
                ctx.uses_db = True
                ctx.vars[p] = "json"
                pre.append("%s = _db_find_or_404(%r, %s)  # implicit model binding: %s $%s" % (p, proj.table_of(models[a]), p, models[a], a))
        if req:
            body = re.sub(r"\$%s\b" % re.escape(req), "$" + req, body)
        body_lines = _statements(body, ctx)
    lines = [deco]
    sig = ["%s: str" % p for p in params]
    is_async = False
    if body_lines is not None:
        if ctx.uses_body or ctx.uses_request:
            sig.append("request: Request")
        if ctx.uses_body:
            is_async = True
            pre.insert(0, "_body = await _read_body(request)")
    lines.append("%sdef route_%d(%s):" % ("async " if is_async else "", n, ", ".join(sig)))
    if r.origin:
        lines.append("    # from controller %s" % r.origin)
    if r.middleware:
        lines.append("    # Laravel middleware: %s" % ", ".join(r.middleware))
    if body_lines is not None:
        lines += ["    " + l for l in pre + body_lines]
    else:
        lines.append("    # TODO(2mfastapi): not translated automatically. Original PHP:")
        for l in r.body.strip().splitlines():
            lines.append("    #   " + l.rstrip())
        lines.append('    return JSONResponse({"detail": "Not Implemented (converted from Laravel)"}, status_code=501)')
    lines.append("")
    return lines, body_lines is not None


def _tables_code(proj: Project) -> str:
    out = []
    for t, cols in proj.tables.items():
        cs = []
        for c, typ in cols:
            if typ == "pk":
                cs.append("Column(%r, Integer, primary_key=True, autoincrement=True)" % c)
            else:
                cs.append("Column(%r, %s, nullable=True)" % (c, typ))
        out.append("Table(%r, _meta, %s)" % (t, ", ".join(cs)))
    return "\n".join(out)


def translate(php: str, root: Optional[str] = None, sources: Optional[List[Tuple[str, str]]] = None,
              project: Optional[Project] = None) -> Tuple[str, int, int]:
    """Return (python source, translated count, TODO count).

    `sources` is a list of (php, url prefix); when omitted, `php` is used with no prefix.
    `root` is the Laravel project root (controllers, models, migrations, views)."""
    proj = project or Project(root)
    routes: List[Route] = []
    for src, pre in (sources if sources is not None else [(php, "")]):
        _routes(src, Scope(prefix=pre), proj, routes)
    body: List[str] = []
    ok = todo = 0
    uses_db = bool(proj.tables)
    for n, r in enumerate(routes, 1):
        lines, good = _route_code(r, n, proj)
        body += lines
        ok, todo = ok + good, todo + (not good)
        uses_db = uses_db or any("_db_" in l for l in lines)
    code = _HEADER
    if uses_db:
        code += _DB_CODE % {"tables": _tables_code(proj)}
    if any("_render(" in l for l in body):
        code += _VIEW_CODE
    code += "\n\n" + "\n".join(body)
    code += ("\n# MFastAPI: speed up route lookup (Rust/Mojo/C core when available; otherwise it changes nothing).\n"
             "# Must run after every route is registered. Set MFASTAPI_DISABLE=1 to turn it off.\n"
             "mfastapi.accelerate(app)\n")
    return code, ok, todo


def convert_laravel(root: str, out_dir: str) -> Tuple[int, int]:
    """Translate routes/web.php and routes/api.php (api.php routes get the /api prefix, as in Laravel),
    resolving controllers, Eloquent models (via migrations) and Blade views. Writes main.py and templates/."""
    os.makedirs(out_dir, exist_ok=True)
    proj = Project(root)
    srcs = []
    for fn, prefix in (("web.php", ""), ("api.php", "/api")):
        p = os.path.join(root, "routes", fn)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                srcs.append((fh.read(), prefix))
    code, ok, todo = translate("", sources=srcs, project=proj)
    with open(os.path.join(out_dir, "main.py"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(code)
    for name, src in proj.views.items():
        p = os.path.join(out_dir, "templates", *name.split(".")) + ".html"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src)
    return ok, todo
