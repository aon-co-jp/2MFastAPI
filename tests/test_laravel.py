import os
import sys

from fastapi.testclient import TestClient

from tomfastapi.cli import main
from tomfastapi.laravel import blade_to_jinja, convert_laravel, translate

EX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "laravel_app")


def _app(out, monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setenv("DATABASE_URL", "sqlite:///" + os.path.join(str(out), "t.db"))
    ok, todo = convert_laravel(EX, str(out))
    path = os.path.join(str(out), "main.py")
    ns = {"__file__": path, "__name__": "lv_main"}
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), ns)
    return ok, todo, TestClient(ns["app"]), ns


def test_counts(tmp_path, monkeypatch):
    ok, todo, _, _ = _app(tmp_path, monkeypatch)
    assert (ok, todo) == (22, 5)


def test_routes(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    assert c.get("/").text == "Hello from Laravel"
    assert c.get("/hello/Taro").text == "Hello, Taro!"
    assert c.get("/api/users/7").json() == {"id": "7", "role": "member"}
    assert c.post("/api/legacy").status_code == 501          # $request->validate(...) is not translated


def test_controllers_groups_interpolation(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    assert c.get("/users").json() == {"users": "all"}          # [UserController::class, 'index']
    assert c.get("/users/5").text == "User 5"                   # 'UserController@show' + "User $id"
    assert c.get("/greet/Hana").text == "Hi Hana, welcome!"    # "Hi {$name}, welcome!"
    assert c.get("/admin/stats").json() == {"ok": 1}            # Route::prefix('admin')->group(...)
    assert c.get("/admin/v/ping").text == "pong"                # nested prefix groups
    assert c.get("/ctl/list").json() == {"users": "all"}        # Route::controller()->prefix()->group()
    assert c.get("/ctl/show/9").text == "User 9"


def test_names_and_middleware(tmp_path, monkeypatch):
    _, _, c, ns = _app(tmp_path, monkeypatch)
    app = ns["app"]
    assert app.url_path_for("home") == "/"
    assert app.url_path_for("admin.stats") == "/admin/stats"    # group name prefix + ->name()
    assert app.url_path_for("photos.show", photo="3") == "/photos/3"
    r = c.get("/secret")                                         # middleware is not converted: safe 501
    assert r.status_code == 501 and "auth" in r.json()["detail"]
    ns["MIDDLEWARE"]["auth"] = lambda request: None              # plug in a real check -> route runs
    assert c.get("/secret").text == "secret"


def test_eloquent_request_resource(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    assert c.get("/photos").json() == []                        # resource index -> User::all()
    r = c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    assert r.status_code == 201 and r.json()["name"] == "Aoi" and r.json()["id"] == 1
    r = c.post("/api/users", data={"name": "Ren", "email": "r@example.test", "bogus": "x"})  # form body
    assert r.status_code == 200 and r.json()["name"] == "Ren" and "bogus" not in r.json()
    assert [u["name"] for u in c.get("/photos").json()] == ["Aoi", "Ren"]
    assert c.get("/photos/2").json()["email"] == "r@example.test"   # implicit model binding
    assert c.get("/photos/99").status_code == 404
    assert c.get("/photos/create").status_code == 501           # method missing in the controller
    assert c.put("/photos/1").status_code == 501 and c.patch("/photos/1").status_code == 501
    assert c.post("/api/orders", json={"user_id": 1, "amount": 150, "status": "paid"}).json()["amount"] == 150
    c.post("/api/orders", json={"user_id": 1, "amount": 20, "status": "new"})
    assert [o["amount"] for o in c.get("/api/orders/status/new").json()] == [20]
    assert c.get("/api/orders/big").json()["amount"] == 150
    assert c.get("/api/orders/2").json()["status"] == "new"
    assert c.get("/api/orders/50").status_code == 404           # findOrFail
    assert c.get("/search?q=tea").json() == {"q": "tea"}        # $request->query('q', '')
    assert c.get("/search").json() == {"q": ""}


def test_blade_views(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    html = c.get("/dashboard").text
    assert "<title>Dashboard</title>" in html and "<li>none</li>" in html and "<p><b>Team</b></p>" in html
    c.post("/photos", json={"name": "<x>", "email": "e@example.test"})
    html = c.get("/dashboard").text
    assert "Users (1)" in html and "&lt;x&gt;" in html and "<x>" not in html  # {{ }} escapes like Blade
    assert c.get("/page/Mio").text.strip() == "<p>Hello, Mio!</p>"   # fn () => view(...)


def test_blade_to_jinja_unit():
    src, warns = blade_to_jinja("@unless($a)x @endunless @csrf @foo {{ $a . 'b' }}")
    assert "{% if not (a) %}x {% endif %}" in src
    assert "{{ a ~ 'b' }}" in src
    assert any("@foo" in w for w in warns) and any("csrf" in w for w in warns)


def test_generated_calls_accelerate(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch)
    code = (tmp_path / "main.py").read_text(encoding="utf-8")
    assert "import mfastapi" in code
    assert code.rstrip().endswith("mfastapi.accelerate(app)")


def test_todo_comment_and_interpolation():
    code, ok, todo = translate("Route::get('/x/{a}', function ($a) { return \"hi $a\"; });")
    assert (ok, todo) == (1, 0) and "'hi ' + str(a)" in code
    # a variable that is not a route parameter is not guessed
    code, ok, todo = translate("Route::get('/x', function () { return \"hi $user\"; });")
    assert (ok, todo) == (0, 1)
    assert "TODO(2mfastapi)" in code and 'return "hi $user";' in code


def test_missing_controller_is_todo():
    code, ok, todo = translate("Route::get('/m', 'NopeController@x');")
    assert (ok, todo) == (0, 1) and "controller method not found: NopeController@x" in code


def test_group_array_and_api_resource():
    code, ok, todo = translate("Route::group(['prefix' => 'p', 'as' => 'p.', 'middleware' => ['auth']], function () {"
                               " Route::get('/a', function () { return 'a'; })->name('a'); });"
                               " Route::apiResource('tags', TagController::class)->except(['destroy']);")
    assert '@app.get("/p/a", name=\'p.a\', dependencies=[Depends(_mw(\'auth\'))])' in code
    assert "/tags/create" not in code and "tags.destroy" not in code and "tags.update" in code


def test_cli(tmp_path):
    assert main(["laravel", EX, "-o", str(tmp_path)]) == 0
    assert (tmp_path / "main.py").exists() and (tmp_path / "templates" / "layouts" / "app.html").exists()
