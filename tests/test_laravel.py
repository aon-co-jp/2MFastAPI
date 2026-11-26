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
    assert (ok, todo) == (55, 2)


def test_routes(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    assert c.get("/").text == "Hello from Laravel"
    assert c.get("/hello/Taro").text == "Hello, Taro!"
    assert c.get("/api/users/7").json() == {"id": "7", "role": "member"}
    r = c.post("/api/legacy")                                  # $request->validate([...]) -> Laravel-style 422
    assert r.status_code == 422 and r.json() == {"message": "The name field is required.",
                                                 "errors": {"name": ["The name field is required."]}}
    assert c.post("/api/legacy", json={"name": "a"}).text == "x"


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
    assert c.get("/photos/1/edit").status_code == 501           # $request->file(..) is not translated
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


def test_validate_update_delete(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    r = c.put("/photos/1", json={"name": "x" * 21, "email": "bad"})
    assert r.status_code == 422
    assert r.json()["errors"] == {"name": ["The name field must not be greater than 20 characters."],
                                  "email": ["The email field must be a valid email address."]}
    assert r.json()["message"] == "The name field must not be greater than 20 characters. (and 1 more error)"
    r = c.patch("/photos/1", json={"name": "Aoi2", "email": None, "id": 99})
    assert r.status_code == 200 and r.json()["name"] == "Aoi2" and r.json()["id"] == 1  # $photo->update($data)
    assert r.json()["email"] is None
    assert c.put("/photos/99", json={"name": "z"}).status_code == 404
    assert c.delete("/photos/1").json() == {"deleted": "1"}          # User::destroy($photo)
    assert c.get("/photos/1").status_code == 404


def test_relations_and_db_builder(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    for uid, amount, st in ((1, 150, "paid"), (1, 20, "new"), (2, 70, "paid")):
        c.post("/api/orders", json={"user_id": uid, "amount": amount, "status": st})
    assert [o["amount"] for o in c.get("/api/users/1/orders").json()] == [150, 20]   # hasMany
    assert c.get("/api/users/2/orders").json()[0]["amount"] == 70
    assert c.get("/api/orders/3/owner").json()["name"] == "Ren"                       # belongsTo
    assert c.get("/api/users/9/orders").status_code == 404
    before = c.get("/api/orders/2").json()["updated_at"]
    paid = c.post("/api/orders/2/pay").json()                                         # $m->col = ..; save()
    assert paid["status"] == "paid" and paid["updated_at"] > before
    rep = c.get("/api/report").json()
    assert rep["count"] == 3 and rep["top"] == [150, 70]
    assert rep["raw"] == [{"status": "paid", "n": 3}]                                  # DB::select with ? bindings
    c.post("/api/orders", json={"user_id": 2, "amount": 1, "status": "new"})
    assert c.post("/api/orders/close").json() == {"closed": 1}                       # where()->update()
    assert c.get("/api/orders/status/closed").json()[0]["amount"] == 1
    assert c.get("/api/orders/status/tiny").json()[0]["amount"] == 5                 # DB::table()->insert()
    assert c.delete("/api/orders/1").status_code == 204                               # $m->delete()
    assert c.get("/api/orders/1").status_code == 404


def test_blade_components_and_loop(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "<Aoi>", "email": "a@example.test"})
    for amount, st in ((150, "paid"), (20, "new")):
        c.post("/api/orders", json={"user_id": 1, "amount": amount, "status": st})
    html = c.get("/api/users/1/page").text
    assert '<div class="alert alert-warn"><b>&lt;Aoi&gt;</b> 2 orders</div>' in html     # <x-alert> + slot
    assert '<div class="alert alert-info"></div>' in html                                # @props default
    assert '<li data-i="0">1/2 paid</li>' in html and '<li data-i="1">2/2 new (last)</li>' in html  # $loop


def test_or_where_in_null(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    for uid, amount, st in ((1, 150, "paid"), (1, 20, "new"), (2, 70, "paid")):
        c.post("/api/orders", json={"user_id": uid, "amount": amount, "status": st})
    r = c.get("/api/report2").json()
    assert r["either"] == [1, 2]       # where(amount>100) OR status=new
    assert r["in"] == [3]               # whereIn
    assert r["notin"] == [2]            # whereNotIn
    assert r["notnull"] == 3            # whereNotNull


def test_joins(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    for uid, amount, st in ((1, 150, "paid"), (1, 20, "new"), (2, 70, "paid")):
        c.post("/api/orders", json={"user_id": uid, "amount": amount, "status": st})
    rows = c.get("/api/joined").json()
    assert [(r["name"], r["amount"]) for r in rows] == [("Aoi", 150), ("Ren", 70)]   # join + qualified where/orderBy
    assert c.get("/api/joined-count").json() == {"n": 3}                              # leftJoin + count


def test_with_eager_loading(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    for uid, amount, st in ((1, 150, "paid"), (1, 20, "new"), (2, 70, "paid")):
        c.post("/api/orders", json={"user_id": uid, "amount": amount, "status": st})
    users = c.get("/api/users-with-orders").json()
    assert [(u["name"], [o["amount"] for o in u["orders"]]) for u in users] == [("Aoi", [150, 20]), ("Ren", [70])]  # with() hasMany
    orders = c.get("/api/orders-with-owner").json()
    assert [o["user"]["name"] for o in orders] == ["Aoi", "Aoi", "Ren"]                                              # with() belongsTo
    nested = c.get("/api/users-orders-owner").json()
    assert [[o["user"]["name"] for o in u["orders"]] for u in nested] == [["Aoi", "Aoi"], ["Ren"]]                    # nested with('orders.user')


def test_belongs_to_many(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    assert c.post("/api/roles/seed").json() == {"ok": True}
    assert [r["name"] for r in c.get("/api/users/1/roles").json()] == ["admin", "editor"]   # $user->roles (pivot role_user)
    assert [r["name"] for r in c.get("/api/users/2/roles").json()] == ["editor"]
    users = c.get("/api/users-with-roles").json()                                              # with('roles')
    assert [(u["name"], [r["name"] for r in u["roles"]]) for u in users] == [("Aoi", ["admin", "editor"]), ("Ren", ["editor"])]


def test_named_slots(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    html = c.get("/api/slots").text
    assert '<div class="alert alert-ok"><b>Heads up</b> Body one</div>' in html      # <x-slot:title>
    assert '<div class="alert alert-info"><b>Second</b> Body two</div>' in html      # <x-slot name="title">


def test_session_and_flash(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    assert c.get("/api/cart").json() == {"cart": None, "status": None, "has": False}
    assert c.post("/api/cart/add", json={"item": "pen"}).json() == {"ok": True}      # put + flash
    assert c.get("/api/cart").json() == {"cart": "pen", "status": "added", "has": True}   # flash visible on the next request
    assert c.get("/api/cart").json() == {"cart": "pen", "status": None, "has": True}      # ...and gone after that
    assert c.post("/api/cart/clear").json() == {"cleared": True}                          # forget
    assert c.get("/api/cart").json()["cart"] is None
    c.post("/api/cart/add", json={"item": "pen"})
    assert c.post("/api/cart/reset").json() == {"reset": True}                            # put + invalidate
    assert c.get("/api/cart").json()["cart"] is None


def test_session_increment(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    assert c.get("/api/hits").json() == {"hits": 1}
    assert c.get("/api/hits").json() == {"hits": 2}


def test_session_token(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    a = c.get("/api/csrf").json()
    assert len(a["t1"]) == 40 and a["t1"] == a["t2"]
    assert c.get("/api/csrf").json()["t1"] == a["t1"]          # stable within one session


def test_attach_detach_sync(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    c.post("/api/roles/seed")
    names = lambda u: sorted(r["name"] for r in c.get("/api/users/%d/roles" % u).json())
    assert c.post("/api/users/2/roles/1/attach").json() == {"ok": True}
    assert names(2) == ["admin", "editor"]
    assert c.post("/api/users/2/roles/1/attach").json() == {"ok": True}      # attaching twice adds no duplicate
    assert names(2) == ["admin", "editor"]
    assert c.post("/api/users/2/roles/2/detach").json() == {"ok": True}
    assert names(2) == ["admin"]
    assert c.post("/api/users/1/roles-only-admin").json() == {"ok": True}    # sync([1]) drops editor
    assert names(1) == ["admin"]


def test_attach_with_pivot_columns(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    c.post("/api/roles/seed")
    assert c.post("/api/users/2/roles/1/grant").json() == {"ok": True}
    rows = [r for r in c.get("/api/pivot").json() if r["granted_by"]]
    assert [(r["user_id"], r["role_id"], r["granted_by"]) for r in rows] == [(2, 1, "admin")]   # extra pivot column written


def test_with_pivot(tmp_path, monkeypatch):
    _, _, c, _ = _app(tmp_path, monkeypatch)
    c.post("/photos", json={"name": "Aoi", "email": "a@example.test"})
    c.post("/photos", json={"name": "Ren", "email": "r@example.test"})
    c.post("/api/roles/seed")
    c.post("/api/users/2/roles/1/grant")
    rows = c.get("/api/users/2/roles-granted").json()
    assert sorted((r["name"], r["pivot"]["granted_by"]) for r in rows) == [("admin", "admin"), ("editor", None)]
    only = c.get("/api/users/2/roles-by-grant").json()                                         # wherePivot
    assert [r["name"] for r in only] == ["admin"]
