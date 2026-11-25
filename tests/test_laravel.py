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
    assert (ok, todo) == (3, 2)


def test_routes(tmp_path):
    _, _, c = _app(tmp_path)
    assert c.get("/").text == "Hello from Laravel"
    assert c.get("/hello/Taro").text == "Hello, Taro!"
    assert c.get("/api/users/7").json() == {"id": "7", "role": "member"}
    assert c.get("/dashboard").status_code == 501
    assert c.post("/api/orders").status_code == 501


def test_todo_comment_and_interpolation():
    code, ok, todo = translate("Route::get('/x/{a}', function ($a) { return \"hi $a\"; });")
    assert (ok, todo) == (0, 1)
    assert "TODO(2mfastapi)" in code and 'return "hi $a";' in code


def test_cli(tmp_path):
    assert main(["laravel", EX, "-o", str(tmp_path)]) == 0
    assert (tmp_path / "main.py").exists()
