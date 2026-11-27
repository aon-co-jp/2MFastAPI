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
        self.models: List[str] = []
        self.relations: Dict[Tuple[str, str], Tuple[str, str, Optional[str]]] = {}  # (Model, rel) -> (kind, Target, fk)
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
            if cm:
                self.models.append(cm.group(1))
                for rm in re.finditer(r"function\s+(\w+)\s*\(\s*\)\s*(?::\s*[\w\\]+\s*)?\{\s*return\s+\$this->(hasMany|hasOne|belongsToMany|belongsTo)"
                                      r"\(\s*\\?([\w\\]+)::class\s*(?:,\s*['\"](\w+)['\"])?(?:,\s*['\"](\w+)['\"])?(?:,\s*['\"](\w+)['\"])?", src):
                    kind, target = rm.group(2), rm.group(3).split("\\")[-1]
                    if kind == "belongsToMany":
                        snake = lambda n: re.sub(r"(?<!^)([A-Z])", r"_\1", n).lower()
                        pivot = rm.group(4) or "_".join(sorted([snake(cm.group(1)), snake(target)]))
                        fk = rm.group(5) or snake(cm.group(1)) + "_id"
                        rfk = rm.group(6) or snake(target) + "_id"
                        self.relations[(cm.group(1), rm.group(1))] = (kind, target, "%s|%s|%s" % (pivot, fk, rfk))
                    else:
                        self.relations[(cm.group(1), rm.group(1))] = (kind, target, rm.group(4))
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

_LOOP = {"index": "loop.index0", "iteration": "loop.index", "first": "loop.first", "last": "loop.last",
         "count": "loop.length", "remaining": "loop.revindex0", "depth": "loop.depth",
         "even": "(loop.index is even)", "odd": "(loop.index is odd)"}


def _camel(name: str) -> str:
    return re.sub(r"-(\w)", lambda m: m.group(1).upper(), name)


def _components(src: str, warns: List[str]) -> str:
    """<x-alert type="e" :msg="$m">slot</x-alert> -> Jinja include of components/alert.html with those variables."""
    attr_re = re.compile(r'(:?)([\w\-:.]+)(?:\s*=\s*"([^"]*)")?')

    slot_re = re.compile(r"@@SLOT\[([\w\-]+)\]@@(.*?)@@/SLOT@@", re.S)

    def call(name: str, attrs: str, slot: str) -> str:
        sets = []
        for sn, sb in slot_re.findall(slot):          # <x-slot:title>..</x-slot> -> a variable `title`
            sets.append("{%% set %s %%}%s{%% endset %%}" % (_camel(sn), sb))
        slot = slot_re.sub("", slot)
        for am in attr_re.finditer(attrs):
            bind, key, val = am.group(1), _camel(am.group(2)), am.group(3)
            if not re.fullmatch(r"\w+", key):
                warns.append("component attribute %s not converted" % am.group(2))
                continue
            if val is None:
                sets.append("{%% set %s = true %%}" % key)
            elif bind:
                sets.append("{%% set %s = %s %%}" % (key, _blade_expr(val)))
            else:
                sets.append("{%% set %s = %r %%}" % (key, val))
        tpl = "components/" + name.replace(".", "/") + ".html"
        return "{%% with %%}{%% set slot %%}%s{%% endset %%}%s{%% include %r %%}{%% endwith %%}" % (slot, "".join(sets), tpl)

    src = re.sub(r"<x-slot(?::|\s+name=\")([\w\-]+)\"?\s*>(.*?)</x-slot>", lambda m: "@@SLOT[%s]@@%s@@/SLOT@@" % (m.group(1), m.group(2)), src, flags=re.S)
    tag = r"<x-([\w.\-]+)((?:\s+:?[\w\-:.]+(?:\s*=\s*\"[^\"]*\")?)*)\s*"
    prev = None
    while prev != src:
        prev = src
        src = re.sub(tag + r"/>", lambda m: call(m.group(1), m.group(2), ""), src)
        src = re.sub(tag + r">((?:(?!<x-).)*?)</x-\1>", lambda m: call(m.group(1), m.group(2), m.group(3)), src, flags=re.S)
    return src


def _blade_expr(e: str) -> str:
    e = e.strip()
    e = re.sub(r"\$loop->(\w+)", lambda m: _LOOP.get(m.group(1), "loop." + m.group(1)), e)
    e = re.sub(r"count\(\s*(\$[\w>\-\[\]'\"]+)\s*\)", r"(\1)|length", e)
    e = e.replace("===", "==").replace("!==", "!=")
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    e = re.sub(r"->(\w+)", r".\1", e)
    e = re.sub(r"\$(\w+)", r"\1", e)
    parts = _split(e, ".")  # PHP concatenation `a . b` -> Jinja `a ~ b` (only spaced dots)
    if parts is not None and " . " in e:
        e = " ~ ".join(p.strip() for p in _split(e, " . ") or [e])
    e = re.sub(r"null", "none", e)
    if "??" in e:  # PHP null coalescing: a ?? b
        parts = [x.strip() for x in (_split(e, "??") or [e])]
        if len(parts) == 2 and re.fullmatch(r"[\w.\[\]'\"]+", parts[0]):
            e = "(%s if %s is defined and %s is not none else %s)" % (parts[0], parts[0], parts[0], parts[1])
    return re.sub(r"\s+", " ", e).strip()


def blade_to_jinja(src: str) -> Tuple[str, List[str]]:
    """Convert a simple Blade template to Jinja2. Returns (jinja source, warnings)."""
    warns: List[str] = []
    for lm in re.finditer(r"\$loop->(\w+)", src):
        if lm.group(1) not in _LOOP:
            warns.append("$loop->%s not converted" % lm.group(1))
    src = _components(src, warns)
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
        if name == "props":
            sets = []
            for it in [x for x in (_split((arg or "").strip()[1:-1], ",") or []) if x.strip()]:
                kv = _split(it, "=>")
                if kv and len(kv) == 2:
                    k = _php_str(kv[0])
                    sets.append("{%% if %s is not defined %%}{%% set %s = %s %%}{%% endif %%}" % (k, k, _blade_expr(kv[1])))
            return "".join(sets)
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
        self.var_model: Dict[str, str] = {}   # variable -> Eloquent model (for relations / update / delete)
        self.last_table: Optional[str] = None


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


_VALID_RULES = ("required", "nullable", "sometimes", "string", "integer", "numeric", "boolean", "email",
                "min", "max", "in", "bail")


def _rules(e: str) -> Optional[str]:
    """['f' => 'required|max:5', 'g' => ['nullable', 'email']] -> python dict of rule lists, or None."""
    e = e.strip()
    if not (e.startswith("[") and e.endswith("]")):
        return None
    out = []
    for it in [x for x in (_split(e[1:-1], ",") or []) if x.strip()]:
        kv = _split(it, "=>")
        if not kv or len(kv) != 2 or _php_str(kv[0]) is None:
            return None
        v = kv[1].strip()
        if v.startswith("["):
            rs = [_php_str(x) for x in (_split(v[1:-1], ",") or []) if x.strip()]
        else:
            s = _php_str(v)
            rs = s.split("|") if s is not None else [None]
        if not rs or None in rs or any(r.split(":")[0] not in _VALID_RULES for r in rs):
            return None
        out.append("%r: %r" % (_php_str(kv[0]), rs))
    return "{" + ", ".join(out) + "}"


def _calls(s: str) -> Optional[List[Tuple[str, str]]]:
    """'a(x)->b()->c(1, 2)' -> [('a','x'), ('b',''), ('c','1, 2')]."""
    out, pos = [], 0
    while pos < len(s):
        m = re.match(r"\s*(\w+)\s*\(", s[pos:])
        if not m:
            return None
        inner, end = _body(s, pos + m.end(), "(", ")")
        out.append((m.group(1), inner))
        pos = end
        t = re.match(r"\s*->\s*", s[pos:])
        if t:
            pos += t.end()
        elif s[pos:].strip():
            return None
        else:
            break
    return out


def _model_of_table(proj: "Project", table: str) -> Optional[str]:
    for mdl in proj.models:
        if proj.table_of(mdl) == table:
            return mdl
    return None


def _db_expr(e: str, ctx: "Ctx") -> Optional[Tuple[str, str]]:
    """`with(..)` (eager loading) wraps the result of the chain in `_with(...)`."""
    ctx.withs = []
    r = _db_expr_core(e, ctx)
    if r is None or not ctx.withs:
        return r
    code, kind = r
    if not code.startswith(("_db_get(", "_db_first(", "_db_find(", "_db_find_or_404(")):
        return None
    return "_with(%s, [%s])" % (code, ", ".join(ctx.withs)), kind


def _db_expr_core(e: str, ctx: "Ctx") -> Optional[Tuple[str, str]]:
    """Eloquent `Model::...` and `DB::table(..)->...` / `DB::select(..)` chains."""
    ctx.last_table = None
    m = re.match(r"\\?(?:App\\Models\\|Illuminate\\Support\\Facades\\)?([A-Z]\w*)::", e)
    if not m or m.group(1) in ("Route", "Str", "Arr", "Auth", "Request", "Hash", "Log", "Cache", "Validator"):
        return None
    calls = _calls(e[m.end():])
    if not calls:
        return None
    if m.group(1) == "DB":
        name, raw = calls[0]
        if name == "select" and len(calls) == 1:
            a = _args(raw, ctx)
            if a is None or len(a) not in (1, 2) or a[0][1] != "str":
                return None
            ctx.uses_db = True
            return "_db_raw(%s%s)" % (a[0][0], (", " + a[1][0]) if len(a) == 2 else ""), "json"
        if name != "table" or _php_str(raw) is None:
            return None
        table, calls = _php_str(raw), calls[1:]
    else:
        table = ctx.proj.table_of(m.group(1))
    where, order, limit, joins = [], [], "None", []
    for i, (name, raw) in enumerate(calls):
        last = i == len(calls) - 1
        if name == "with" and m.group(1) != "DB" and not last:
            for path in re.findall(r"""['"]([A-Za-z_][\w.]*)['"]""", raw):
                spec = _with_spec(ctx, m.group(1), path.split("."))
                if spec is None:
                    return None
                ctx.withs.append(spec)
            continue
        a = _args(raw, ctx)
        if a is None:
            return None
        q = "_Q(%r, [%s], [%s], %s%s)" % (table, ", ".join(where), ", ".join(order), limit, (", [%s]" % ", ".join(joins)) if joins else "")
        if name in ("where", "orWhere") and len(a) in (2, 3):
            conj = ", 'or'" if name == "orWhere" else ""
            where.append("(%s, '=', %s%s)" % (a[0][0], a[1][0], conj) if len(a) == 2 else "(%s, %s, %s%s)" % (a[0][0], a[1][0], a[2][0], conj))
        elif name in ("join", "leftJoin") and len(a) in (3, 4):
            kind = "'left'" if name == "leftJoin" else "'inner'"
            joins.append("(%s, %s, %s, %s, %s)" % (kind, a[0][0], a[1][0], a[2][0] if len(a) == 4 else "'='", a[-1][0]))
        elif name in ("whereIn", "whereNotIn", "orWhereIn") and len(a) == 2:
            op = "'not in'" if name == "whereNotIn" else "'in'"
            where.append("(%s, %s, %s%s)" % (a[0][0], op, a[1][0], ", 'or'" if name == "orWhereIn" else ""))
        elif name in ("whereNull", "whereNotNull") and len(a) == 1:
            where.append("(%s, %s, None)" % (a[0][0], "'null'" if name == "whereNull" else "'notnull'"))
        elif name == "orderBy" and len(a) in (1, 2):
            order.append("(%s, %s)" % (a[0][0], a[1][0] if len(a) == 2 else "'asc'"))
        elif name in ("latest", "oldest") and len(a) <= 1:
            order.append("(%s, %r)" % (a[0][0] if a else "'created_at'", "desc" if name == "latest" else "asc"))
        elif name in ("limit", "take") and len(a) == 1:
            limit = a[0][0]
        elif not last:
            return None
        elif name in ("get", "all") and not a:
            ctx.uses_db = True
            return "_db_get(%s)" % q, "json"
        elif name == "first" and not a:
            ctx.uses_db, ctx.last_table = True, table
            return "_db_first(%s)" % q, "json"
        elif name == "count" and not a:
            ctx.uses_db = True
            return "_db_count(%s)" % q, "num"
        elif name == "exists" and not a:
            ctx.uses_db = True
            return "(_db_count(%s) > 0)" % q, "json"
        elif name == "pluck" and len(a) == 1:
            ctx.uses_db = True
            return "[r[%s] for r in _db_get(%s)]" % (a[0][0], q), "json"
        elif name in ("find", "findOrFail") and len(a) == 1 and not where:
            ctx.uses_db, ctx.last_table = True, table
            return "%s(%r, %s)" % ("_db_find" if name == "find" else "_db_find_or_404", table, a[0][0]), "json"
        elif name == "create" and len(a) == 1 and not where:
            ctx.uses_db, ctx.last_table = True, table
            return "_db_create(%r, %s)" % (table, a[0][0]), "json"
        elif name == "insert" and len(a) == 1 and not where:
            ctx.uses_db = True
            return "_db_insert(%r, %s)" % (table, a[0][0]), "json"
        elif name == "update" and len(a) == 1:
            ctx.uses_db = True
            return "_db_update_q(%s, %s)" % (q, a[0][0]), "num"
        elif name == "delete" and not a:
            ctx.uses_db = True
            return "_db_delete_q(%s)" % q, "num"
        elif name == "destroy" and len(a) == 1 and not where:
            ctx.uses_db = True
            return "_db_destroy(%r, %s)" % (table, a[0][0]), "num"
        else:
            return None
    return None


def _session_call(name: str, raw: str, ctx: "Ctx") -> Optional[Tuple[str, str]]:
    a = _args(raw, ctx)
    if a is None:
        return None
    n = len(a)
    ctx.uses_request = True
    k = a[0][0] if a else ""
    if name == "get" and n in (1, 2):
        return "_sess_get(request, %s)" % ", ".join(x[0] for x in a), "any"
    if name == "has" and n == 1:
        return "(_sess_get(request, %s) is not None)" % k, "json"
    if name == "pull" and n in (1, 2):
        return "_sess_pull(request, %s)" % ", ".join(x[0] for x in a), "any"
    if name == "all" and n == 0:
        return "_sess_all(request)", "json"
    if name in ("put", "flash") and n == 2:
        return "_sess_%s(request, %s, %s)" % (name, k, a[1][0]), "json"
    if name in ("forget", "remove") and n == 1:
        return "_sess_forget(request, %s)" % k, "json"
    if name == "token" and n == 0:
        return "_sess_token(request)", "any"
    if name in ("increment", "decrement") and n in (1, 2):
        return "_sess_inc(request, %s, %s)" % (k, ("-(%s)" % a[1][0]) if name == "decrement" and n == 2 else (a[1][0] if n == 2 else "-1" if name == "decrement" else "1")), "any"
    if name in ("invalidate", "flush", "regenerate", "regenerateToken", "migrate") and n in (0, 1):
        return "_sess_%s(request)" % ("flush" if name in ("invalidate", "flush") else "keep"), "json"
    return None


def _with_spec(ctx, model, path):
    """eager-load spec (rel, kind, table, fk, sub-specs) for 'a.b.c' paths."""
    rel = path[0]
    hit = ctx.proj.relations.get((model, rel))
    if not hit:
        return None
    kind, target, fk = hit
    if kind == "belongsToMany":
        pass
    elif kind != "belongsTo":
        fk = fk or re.sub(r"(?<!^)([A-Z])", r"_", model).lower() + "_id"
    else:
        fk = fk or rel + "_id"
    sub = []
    if len(path) > 1:
        t = _with_spec(ctx, target, path[1:])
        if t is None:
            return None
        sub.append(t)
    return "(%r, %r, %r, %r, [%s])" % (rel, kind, ctx.proj.table_of(target), fk, ", ".join(sub))


def _relation(var: str, rel: str, ctx: "Ctx") -> Optional[Tuple[str, str]]:
    mdl = ctx.var_model.get(var)
    hit = ctx.proj.relations.get((mdl, rel)) if mdl else None
    if not hit:
        return None
    kind, target, fk = hit
    ctx.uses_db = True
    tt = ctx.proj.table_of(target)
    if kind == "belongsTo":
        return "_db_find(%r, %s[%r])" % (tt, var, fk or rel + "_id"), "json"
    if kind == "belongsToMany":
        pv, f1, f2 = fk.split("|")
        return "_db_many(%r, %r, %r, %r, %s['id'])" % (tt, pv, f1, f2, var), "json"
    fk = fk or re.sub(r"(?<!^)([A-Z])", r"_\1", mdl).lower() + "_id"
    q = "_Q(%r, [(%r, '=', %s['id'])], [], None)" % (tt, fk, var)
    return ("_db_get(%s)" if kind == "hasMany" else "_db_first(%s)") % q, "json"


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
    # session('k') / session(['k' => v]) / $request->session()->get|put|flash|forget|has|pull|all(..)
    sm = re.fullmatch(r"session\((.*)\)", e, re.S)
    if sm:
        raw = sm.group(1).strip()
        if raw.startswith("["):
            a = _args(raw, ctx)
            if a is None or len(a) != 1:
                return None
            ctx.uses_request = True
            return "_sess_put_many(request, %s)" % a[0][0], "json"
        return _session_call("get", raw, ctx)
    bm = re.fullmatch(r"(?:back\(\)|redirect\(\)->back\(\))(->withInput\(\))?", e)
    if bm:
        ctx.uses_request = True
        if bm.group(1):
            ctx.uses_body = True
        return "_sess_back(request, %s)" % ("_body" if bm.group(1) else "None"), "resp"
    om = re.fullmatch(r"old\((.*)\)", e, re.S)
    if om:
        a = _args(om.group(1), ctx) if om.group(1).strip() else []
        if a is None or len(a) not in (1, 2):
            return None
        ctx.uses_request = True
        return "_sess_old(request, %s)" % ", ".join(x[0] for x in a), "any"
    rq = ctx.request_var
    if rq and re.fullmatch(r"\$%s->(flash|flashOnly|flashExcept)\(\)" % rq, e):
        ctx.uses_body = True
        ctx.uses_request = True
        return "_sess_flash_input(request, _body)", "json"
    if rq:
        sm = re.fullmatch(r"\$%s->session\(\)->(\w+)\((.*)\)" % rq, e, re.S)
        if sm:
            return _session_call(sm.group(1), sm.group(2), ctx)
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
    if rq:
        m = re.fullmatch(r"\$%s->validate\((.*)\)" % rq, e, re.S)
        if m:
            rules = _rules(m.group(1))
            if rules is None:
                return None
            ctx.uses_body = True
            return "_validate(_body, %s)" % rules, "json"
    m = re.fullmatch(r"\$(\w+)->(\w+)\(\)->withPivot\((.*?)\)((?:->wherePivot\([^()]*\))*)->get\(\)", e, re.S)
    if m and m.group(1) in ctx.vars:
        hit = ctx.proj.relations.get((ctx.var_model.get(m.group(1)), m.group(2)))
        cols = re.findall(r"""['"](\w+)['"]""", m.group(3))
        if hit and hit[0] == "belongsToMany" and cols:
            ctx.uses_db = True
            pv, f1, f2 = hit[2].split("|")
            wh = []
            for w in re.findall(r"->wherePivot\(([^()]*)\)", m.group(4)):
                wa = _args(w, ctx)
                if wa is None or len(wa) != 2:
                    return None
                wh.append("(%s, %s)" % (wa[0][0], wa[1][0]))
            return "_db_many_pivot(%r, %r, %r, %r, %s['id'], %r, [%s])" % (ctx.proj.table_of(hit[1]), pv, f1, f2, m.group(1), cols, ", ".join(wh)), "json"
    m = re.fullmatch(r"\$(\w+)->(\w+)\(\)->(attach|detach|sync)\((.*)\)", e, re.S)
    if m and m.group(1) in ctx.vars:
        hit = ctx.proj.relations.get((ctx.var_model.get(m.group(1)), m.group(2)))
        if hit and hit[0] == "belongsToMany":
            a = _args(m.group(4), ctx) if m.group(4).strip() else []
            if a is not None and (len(a) <= 1 or (len(a) == 2 and m.group(3) == "attach")) and (a or m.group(3) == "detach"):
                ctx.uses_db = True
                pv, f1, f2 = hit[2].split("|")
                return "_db_pivot(%r, %r, %r, %s['id'], %r, %s)" % (pv, f1, f2, m.group(1), m.group(3), a[0][0] if a else "None") if len(a) < 2 else "_db_pivot(%r, %r, %r, %s['id'], 'attach', %s, %s)" % (pv, f1, f2, m.group(1), a[0][0], a[1][0]), "json"
    m = re.fullmatch(r"\$(\w+)->(\w+)", e)
    if m and m.group(1) in ctx.vars and (m.group(1), m.group(2)) and _relation(m.group(1), m.group(2), ctx):
        return _relation(m.group(1), m.group(2), ctx)
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
        m = re.fullmatch(r"\$(\w+)->(update|delete|save)\((.*)\)", st, re.S)
        if m and m.group(1) in ctx.var_model and not last:
            v, op = m.group(1), m.group(2)
            t = ctx.proj.table_of(ctx.var_model[v])
            if op == "update":
                x = _expr(m.group(3), ctx)
                if x is None:
                    return None
                lines.append("%s = _db_update_row(%r, %s, %s)" % (v, t, v, x[0]))
            elif op == "delete" and not m.group(3).strip():
                lines.append("_db_delete_row(%r, %s)" % (t, v))
            elif op == "save" and not m.group(3).strip():
                lines.append("%s = _db_save(%r, %s)" % (v, t, v))
            else:
                return None
            continue
        m = re.fullmatch(r"\$(\w+)->(\w+)\s*=\s*(.+)", st, re.S)
        if m and m.group(1) in ctx.var_model and not last and not m.group(3).startswith("="):
            x = _expr(m.group(3), ctx)
            if x is None:
                return None
            lines.append("%s[%r] = %s" % (m.group(1), m.group(2), x[0]))
            continue
        m = re.fullmatch(r"\$(\w+)\s*=\s*(.+)", st, re.S)
        if m and not last and not m.group(2).startswith("="):
            x = _expr(m.group(2), ctx)
            if x is None or x[1] == "resp":
                return None
            ctx.vars[m.group(1)] = x[1]
            mdl = _model_of_table(ctx.proj, ctx.last_table) if ctx.last_table else None
            if mdl:
                ctx.var_model[m.group(1)] = mdl
            else:
                ctx.var_model.pop(m.group(1), None)
            lines.append("%s = %s" % (m.group(1), x[0]))
            continue
        if not last and not st.startswith("return"):
            x = _expr(st, ctx)  # statement used for its effect: $request->validate(..), DB::table(..)->insert(..)
            if x is not None and x[1] != "resp" and ("_validate(" in x[0] or "_db_" in x[0] or "_sess_" in x[0]):
                lines.append(x[0])
                continue
            return None
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


class _ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors


@app.exception_handler(_ValidationError)
async def _validation_error(request, exc):
    msgs = [m for ms in exc.errors.values() for m in ms]
    extra = len(msgs) - 1
    message = msgs[0] + ((" (and %d more error%s)" % (extra, "s" if extra > 1 else "")) if extra else "")
    return JSONResponse({"message": message, "errors": exc.errors}, status_code=422)


def _validate(data, rules):
    """Laravel $request->validate(): 422 {"message", "errors"} on failure, validated fields on success."""
    import re as _re
    errors, out = {}, {}
    for field, rs in rules.items():
        label = field.replace("_", " ")
        names = [r.split(":")[0] for r in rs]
        v = data.get(field)
        if v is None or v == "":
            if "required" in names:
                errors.setdefault(field, []).append("The %s field is required." % label)
            elif field in data and "nullable" in names:
                out[field] = None
            continue
        numeric = "integer" in names or "numeric" in names
        err = []
        for r in rs:
            n, _, arg = r.partition(":")
            s = str(v)
            if n == "string" and not isinstance(v, str):
                err.append("The %s field must be a string." % label)
            elif n == "integer" and (isinstance(v, bool) or not _re.fullmatch(r"-?\\d+", s)):
                err.append("The %s field must be an integer." % label)
            elif n == "numeric" and (isinstance(v, bool) or not _re.fullmatch(r"-?\\d+(\\.\\d+)?", s)):
                err.append("The %s field must be a number." % label)
            elif n == "boolean" and v not in (True, False, 0, 1, "0", "1"):
                err.append("The %s field must be true or false." % label)
            elif n == "email" and not _re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", s):
                err.append("The %s field must be a valid email address." % label)
            elif n == "in" and s not in arg.split(","):
                err.append("The selected %s is invalid." % label)
            elif n in ("min", "max"):
                try:
                    size = float(s) if numeric else len(v) if isinstance(v, (str, list, dict)) else float(s)
                except ValueError:
                    continue
                lim = float(arg)
                unit = "" if numeric or not isinstance(v, str) else " characters"
                if n == "min" and size < lim:
                    err.append("The %s field must be at least %s%s." % (label, arg, unit))
                if n == "max" and size > lim:
                    err.append("The %s field must not be greater than %s%s." % (label, arg, unit))
        if err:
            errors[field] = err
        else:
            out[field] = v
    if errors:
        raise _ValidationError(errors)
    return out
'''

_DB_CODE = '''

# ---- Eloquent -> SQLAlchemy Core (tables from database/migrations; DATABASE_URL, default sqlite file)
import datetime as _dt
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select, update)

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


def _db_many(target_table, pivot, fk, rfk, key):
    tt, pv = _t(target_table), _t(pivot)
    return _rows(select(tt).select_from(tt.join(pv, pv.c[rfk] == tt.c["id"])).where(pv.c[fk] == key))


def _db_many_pivot(target_table, pivot, fk, rfk, key, cols, where=()):
    tt, pv = _t(target_table), _t(pivot)
    q = select(tt, *[pv.c[k].label("_pv_" + k) for k in cols if k in pv.c]).select_from(tt.join(pv, pv.c[rfk] == tt.c["id"])).where(pv.c[fk] == key, *[pv.c[k] == v for k, v in where])
    out = []
    for r in _rows(q):
        out.append({**{k: v for k, v in r.items() if not k.startswith("_pv_")},
                    "pivot": {k[4:]: v for k, v in r.items() if k.startswith("_pv_")}})
    return out


def _with(res, specs):
    rows = [res] if isinstance(res, dict) else (res or [])
    for rel, kind, table, fk, *sub in specs:
        for r in rows:
            if kind == "belongsTo":
                r[rel] = _db_find(table, r.get(fk))
            elif kind == "belongsToMany":
                pv, f1, f2 = fk.split("|")
                r[rel] = _db_many(table, pv, f1, f2, r["id"])
            else:
                kids = _db_get(_Q(table, [(fk, "=", r["id"])], [], None))
                r[rel] = kids if kind == "hasMany" else (kids[0] if kids else None)
            if sub and sub[0] and r.get(rel):
                _with(r[rel], sub[0])
    return res


def _db_find_or_404(name, key):
    r = _db_find(name, key)
    if r is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return r


_OPS = {"=": "__eq__", "==": "__eq__", "!=": "__ne__", "<>": "__ne__", "<": "__lt__", ">": "__gt__",
        "<=": "__le__", ">=": "__ge__", "like": "like"}


def _Q(name, where, order, limit, joins=()):
    return {"t": name, "where": where, "order": order, "limit": limit, "joins": list(joins)}


def _col(q, name):
    if "." in name:
        tb, cn = name.split(".", 1)
        return _t(tb).c[cn]
    return _t(q["t"]).c[name]


def _from(q):
    src = _t(q["t"])
    for kind, tb, a, op, b in q.get("joins", []):
        src = src.join(_t(tb), getattr(_col(q, a), _OPS[str(op).lower()])(_col(q, b)), isouter=(kind == "left"))
    return src


def _apply(q, stmt):
    t = _t(q["t"])
    from sqlalchemy import and_, or_
    cond = None
    for w in q["where"]:
        col, op, val = w[0], str(w[1]).lower(), w[2]
        c = _col(q, col)
        if op == "in":
            e = c.in_(list(val))
        elif op == "not in":
            e = c.not_in(list(val))
        elif op == "null":
            e = c.is_(None)
        elif op == "notnull":
            e = c.is_not(None)
        else:
            e = getattr(c, _OPS[op])(val)
        if cond is None:
            cond = e
        elif len(w) > 3 and w[3] == "or":
            cond = or_(cond, e)
        else:
            cond = and_(cond, e)
    return stmt if cond is None else stmt.where(cond)


def _db_get(q):
    t = _t(q["t"])
    joined = bool(q.get("joins"))
    cols = list(t.c) + [c for jt in q.get("joins", []) for c in _t(jt[1]).c]
    stmt = _apply(q, select(*cols).select_from(_from(q)) if joined else select(t))
    for col, d in q["order"]:
        cc = _col(q, col)
        stmt = stmt.order_by(cc.desc() if str(d).lower() == "desc" else cc.asc())
    if q["limit"] is not None:
        stmt = stmt.limit(int(q["limit"]))
    if not joined:
        return _rows(stmt)
    with _engine.connect() as c:                      # 列名が重なるときは後ろの表が勝つ(Laravel/PDO と同じ)
        return [{k.name: v for k, v in zip(cols, r)} for r in c.execute(stmt)]


def _db_first(q):
    r = _db_get(dict(q, limit=1))
    return r[0] if r else None


def _db_count(q):
    from sqlalchemy import func
    with _engine.connect() as c:
        return c.execute(_apply(q, select(func.count()).select_from(_from(q)))).scalar()


def _cols(t, data, now_cols=("updated_at",)):
    vals = {k: v for k, v in dict(data).items() if k in t.c and not t.c[k].primary_key}
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    for k in now_cols:
        if k in t.c and k not in vals:
            vals[k] = now
    return vals


def _db_insert(name, data):
    rows = data if isinstance(data, list) else [data]
    t = _t(name)
    with _engine.begin() as c:
        for r in rows:
            c.execute(insert(t).values(**{k: v for k, v in dict(r).items() if k in t.c}))
    return True


def _db_pivot(pivot, f1, f2, key, mode, ids, extra=None):
    t = _t(pivot)
    per = {}
    if isinstance(ids, dict):                                  # sync([1 => ['col' => v]]): keys are ids, values are pivot columns
        per = {(int(k) if isinstance(k, str) and k.lstrip('-').isdigit() else k): v for k, v in ids.items()}
        ids = list(per)
    ids = [] if ids is None else (list(ids) if isinstance(ids, (list, tuple)) else [ids])
    ids = [int(i) if isinstance(i, str) and i.lstrip('-').isdigit() else i for i in ids]   # path parameters arrive as strings
    with _engine.begin() as c:
        have = {r[0] for r in c.execute(select(t.c[f2]).where(t.c[f1] == key))}
        if mode == "sync":
            gone = have - set(ids)
            if gone:
                c.execute(delete(t).where(t.c[f1] == key, t.c[f2].in_(gone)))
        if mode == "detach":
            c.execute(delete(t).where(t.c[f1] == key, *([t.c[f2].in_(ids)] if ids else [])))
        else:
            for i in ids:
                ex = {k: v for k, v in {**(extra or {}), **(per.get(i) or {})}.items() if k in t.c}
                if i not in have:
                    c.execute(insert(t).values(**{**ex, f1: key, f2: i}))
                elif ex and per:
                    c.execute(update(t).where(t.c[f1] == key, t.c[f2] == i).values(**ex))
    return True


def _db_update_q(q, data):
    t = _t(q["t"])
    with _engine.begin() as c:
        return c.execute(_apply(q, update(t)).values(**_cols(t, data))).rowcount


def _db_delete_q(q):
    with _engine.begin() as c:
        return c.execute(_apply(q, delete(_t(q["t"])))).rowcount


def _pk(name):
    return list(_t(name).primary_key.columns)[0].name


def _db_destroy(name, keys):
    keys = keys if isinstance(keys, list) else [keys]
    return sum(_db_delete_q(_Q(name, [(_pk(name), "=", k)], [], None)) for k in keys)


def _db_update_row(name, row, data):
    _db_update_q(_Q(name, [(_pk(name), "=", row[_pk(name)])], [], None), data)
    return _db_find(name, row[_pk(name)])


def _db_save(name, row):
    return _db_update_row(name, row, {k: v for k, v in row.items() if k != "updated_at"})  # like Eloquent: touch updated_at


def _db_delete_row(name, row):
    return _db_delete_q(_Q(name, [(_pk(name), "=", row[_pk(name)])], [], None))


def _db_raw(sql, bindings=()):
    """DB::select('... where a = ? and b = ?', [x, y]) -- positional ? bindings only."""
    from sqlalchemy import text
    params, parts = {}, sql.split("?")
    if len(parts) - 1 != len(bindings):
        raise HTTPException(status_code=500, detail="DB::select binding count mismatch")
    out = parts[0]
    for i, b in enumerate(bindings):
        params["p%d" % i] = b
        out += ":p%d" % i + parts[i + 1]
    with _engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(out), params)]


def _db_create(name, data):
    t = _t(name)
    vals = _cols(t, data, ("created_at", "updated_at"))
    with _engine.begin() as c:
        res = c.execute(insert(t).values(**vals))
        key = res.inserted_primary_key[0] if res.inserted_primary_key else None
    return _db_find(name, key) if key is not None else vals
'''

_SESSION_CODE = '''

# ---- session (Laravel session()/$request->session()) on Starlette's signed-cookie session ----
# Set APP_KEY in the environment; without it a random key is used and sessions end when the server restarts.
import os as _os
import secrets as _secrets
from starlette.middleware.sessions import SessionMiddleware


@app.middleware("http")
async def _flash_age(request, call_next):          # flash data lives for the next request only, as in Laravel
    s = request.session
    s["_flash_old"] = s.pop("_flash_new", {})
    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=_os.environ.get("APP_KEY") or _secrets.token_hex(32), same_site="lax")


def _sess_get(request, key, default=None):
    s = request.session
    if key in s:
        return s[key]
    return s.get("_flash_old", {}).get(key, default)


def _sess_flash_input(request, data):
    request.session.setdefault("_flash_new", {})["_input"] = dict(data or {})
    return True



def _sess_back(request, data=None):
    if data is not None:
        _sess_flash_input(request, data)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(request.headers.get("referer") or "/", status_code=302)

def _sess_old(request, key, default=None):
    return (_sess_get(request, "_input", None) or {}).get(key, default)


def _sess_put(request, key, value):
    request.session[key] = value


def _sess_put_many(request, data):
    request.session.update(data)


def _sess_flash(request, key, value):
    request.session.setdefault("_flash_new", {})[key] = value


def _sess_forget(request, key):
    request.session.pop(key, None)


def _sess_pull(request, key, default=None):
    v = _sess_get(request, key, default)
    request.session.pop(key, None)
    return v


def _sess_flush(request):
    request.session.clear()


def _sess_keep(request):             # regenerate(): the signed cookie holds the data, so the id has nothing to rotate
    return None


def _sess_token(request):
    if "_token" not in request.session:
        request.session["_token"] = _secrets.token_hex(20)
    return request.session["_token"]


def _sess_inc(request, key, by):
    v = (request.session.get(key) or 0) + by
    request.session[key] = v
    return v


def _sess_all(request):
    return {k: v for k, v in request.session.items() if not k.startswith("_flash") and k != "_token"}
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
                ctx.var_model[p] = models[a]
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
        code += _DB_CODE.replace("%(tables)s", _tables_code(proj))
    if any("_render(" in l for l in body):
        code += _VIEW_CODE
    if any("_sess_" in l for l in body):
        code += _SESSION_CODE
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
