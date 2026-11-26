import os

from fastapi.testclient import TestClient

from tomfastapi.cli import main
from tomfastapi.laravel import convert_laravel, translate

EX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "laravel_app")


def _app(out):
    ok, todo = convert_laravel(EX, str(out))
    ns = {}
    exec(compile(open(os.path.join(str(out), "main.py"), encoding="utf-8").read(), "main.py", "exec"), ns)
    return ok, todo, TestClient(ns["app"])


def test_counts(tmp_path):
    ok, todo, _ = _app(tmp_path)
    assert (ok, todo) == (8, 3)


def test_routes(tmp_path):
    _, _, c = _app(tmp_path)
    assert c.get("/").text == "Hello from Laravel"
    assert c.get("/hello/Taro").text == "Hello, Taro!"
    assert c.get("/api/users/7").json() == {"id": "7", "role": "member"}
    assert c.get("/dashboard").status_code == 501
    assert c.post("/api/orders").status_code == 501
    assert c.post("/api/users").status_code == 501  # controller store() uses Request: TODO


def test_controllers_groups_interpolation(tmp_path):
    _, _, c = _app(tmp_path)
    assert c.get("/users").json() == {"users": "all"}          # [UserController::class, 'index']
    assert c.get("/users/5").text == "User 5"                   # 'UserController@show' + "User $id"
    assert c.get("/greet/Hana").text == "Hi Hana, welcome!"    # "Hi {$name}, welcome!"
    assert c.get("/admin/stats").json() == {"ok": 1}            # Route::prefix('admin')->group(...)
    assert c.get("/admin/v/ping").text == "pong"                # nested prefix groups


def test_generated_calls_accelerate(tmp_path):
    convert_laravel(EX, str(tmp_path))
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


def test_cli(tmp_path):
    assert main(["laravel", EX, "-o", str(tmp_path)]) == 0
    assert (tmp_path / "main.py").exists()
