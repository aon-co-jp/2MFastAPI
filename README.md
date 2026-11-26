> Latest translations / 翻訳の最新版: [0-LATEST-TRANSLATIONS.md](0-LATEST-TRANSLATIONS.md)

# 2MFastAPI

**日本語**: Flask・Django(DRF を含む)・FastAPI で組まれたプロジェクトを、使っているライブラリの組み合わせ(SQLAlchemy・marshmallow・JWT・DRF・Flask-Login など)ごと **MFastAPI**(FastAPI 互換・Rust 高速化、`mfastapi.accelerate(app)`)へ自動変換するツール。Flask / Django の変換は [2FastAPI](https://github.com/aon-co-jp/2FastAPI) を土台にし、FastAPI のプロジェクトはコードを変えずに `run_mfastapi.py`(MFastAPI が無ければ素の FastAPI として動く)を足します。
**English**: Converts Flask, Django (incl. DRF) and FastAPI projects, in many library combinations (SQLAlchemy, marshmallow, JWT, DRF, Flask-Login ...), to **MFastAPI** (FastAPI-compatible, Rust-accelerated, `mfastapi.accelerate(app)`). Flask / Django conversion builds on [2FastAPI](https://github.com/aon-co-jp/2FastAPI); FastAPI projects keep their code and get a `run_mfastapi.py` launcher (plain FastAPI behaviour when MFastAPI is absent).

- 紹介・ダウンロード: https://easy-web.tokyo/2MFastAPI ・ デモ: https://easy-web.tokyo/2MFastAPI/demo/
- ライセンス / License: MIT

## 使い方 / Usage
```bash
pip install "tofastapi @ git+https://github.com/aon-co-jp/2FastAPI.git" .
2mfastapi scan  ./my-projects                  # Flask / Django / FastAPI を探す(ライブラリも表示) / list projects and libraries
2mfastapi convert ./proj -o ./proj-mfastapi    # 1つ変換 / convert one
2mfastapi auto  ./my-projects -o ./out         # 見つかった全部を変換 / convert everything found
uvicorn run_mfastapi:app --reload              # 変換後 / after conversion
```
MFastAPI は GitHub リリースのホイールで配布(PyPI 未公開): https://github.com/aon-co-jp/MFastAPI/releases 。未導入でも変換後のアプリは素の FastAPI として動きます。
MFastAPI ships as GitHub release wheels (not on PyPI). The converted app also runs as plain FastAPI without it.

## 対応する組み合わせ / Supported combinations (差分試験あり / differentially tested)
| 元 / Source | 変換 / Conversion |
|---|---|
| FastAPI + SQLAlchemy + Pydantic(+ JWT/passlib 等) | コードは無変更、`run_mfastapi.py` を追加。応答が元と一致することを試験 / unchanged code + launcher; responses verified identical |
| Flask + Flask-SQLAlchemy + marshmallow + Flask-JWT-Extended | 2FastAPI の互換層で変換(Flask が発行したトークンを変換後が受理) / via 2FastAPI shims |
| Django REST framework(`ModelViewSet`・`ModelSerializer`・`ViewSet`・router) | SQLAlchemy + pydantic の CRUD に変換 / converted to SQLAlchemy + pydantic CRUD |
| Flask(Login・Session・Blueprint ほか)、Django(View・TemplateView・render) | 2FastAPI の全機能 / everything 2FastAPI converts |

## 毎晩の自動バージョンアップ / Nightly auto-update
**日本語**: GitHub Actions が毎晩 02:47 JST に、最新の 2FastAPI(main)・MFastAPI(最新ホイール)・上流(Python / Flask / Django / FastAPI / Starlette)で全試験を実行します。失敗したら日付つきの issue を1件起こします。通って、かつ 2FastAPI か MFastAPI に新しいリリースが出ていれば、パッチ版を上げてリリースします(`upstream.json` に前回の版を記録、`scripts/nightly_bump.py`)。また `version-control` が本リポジトリのクローンの鮮度を見張り、easy-web.tokyo の紹介ページは `refresh_versions.py`(1時間ごと)で最新版を表示します。
**English**: GitHub Actions runs the full suite every night (02:47 JST) against the latest 2FastAPI (main), MFastAPI (latest wheel) and upstream (Python / Flask / Django / FastAPI / Starlette), opening one dated issue on failure. When it passes and 2FastAPI or MFastAPI has a new release, it bumps the patch version and publishes a release (`upstream.json`, `scripts/nightly_bump.py`). `version-control` watches the clone's freshness and the easy-web.tokyo page shows the latest versions via `refresh_versions.py` (hourly).

## 開発 / Development
WSL: `bash run-tests.sh`(`2FastAPI` を隣に置く / keep 2FastAPI checked out next to this repo)。Windows ネイティブでは libcst が無いためテストは WSL / Linux CI。

## 2026-11-25 同時開発の方針 / Policy: develop together

**日本語**: 方針(2026-11-25、ユーザー指示): 未了は確認なしで完成まで自動で進める。需要が少ない・1からの大規模な開発が必要でも、別の方式で済ませず真摯に作り直す。特に COBOL_to・Java_to・MFastAPI・2MFastAPI(他の言語・フレームワークから MFastAPI 互換へ変換。Node.js・TypeScript は例外的に選択可で、選ばない選択も可)・RMojo・RPoRea・2RPoRea(他の言語から RPoRea=RPoem+Reaxt へ変換。Reaxt は React・Next.js・Nuxt.js・Nest.js 相当)・Reaxt を同時に開発する。2RPoRea は 2026-11-25 に新設(検出 scan のみ、変換は未着手)。

**English**: Policy (2026-11-25, user instruction): carry unfinished work through to completion without asking. Even when demand is low or a large from-scratch rewrite is needed, do the real work instead of substituting another approach. Developed together: COBOL_to, Java_to, MFastAPI, 2MFastAPI (converts other languages and frameworks to MFastAPI-compatible code; Node.js and TypeScript are an optional exception and choosing neither is allowed), RMojo, RPoRea, 2RPoRea (converts other languages to RPoRea = RPoem + Reaxt; Reaxt is the Rust equivalent of React, Next.js, Nuxt.js and Nest.js) and Reaxt. 2RPoRea was created on 2026-11-25 (detection `scan` only; conversion not started).

<!-- directive-20261125-1130 -->
## 2026-11-25 指示(11:30 まで確認不要) / Directive (no confirmation until 11:30)
**日本語**: 2026-11-25 11:30 まで、未了は確認なしで完成まで自動で進める。需要が少ない・必要性が低いと判断される、あるいは1から大規模に作り直す必要があっても、別の方式で済ませず、正面から作り直す。同時に開発する対象: COBOL_to・Java_to・MFastAPI・2MFastAPI(他の言語・フレームワークから MFastAPI 互換へ。Node.js・TypeScript は例外的に選べ、選ばない選択も可能)・RMojo・RPoRea(RPoem と Reaxt の統合)・2RPoRea(他の言語・フレームワークから RPoRea へ)・Reaxt(React+Next.js+Nuxt.js+Nest.js の統合)。1つ変えたら他を確認し、README・CLAUDE・PORTING・POLICY を日英で同じ日に更新する。
**English**: Until 2026-11-25 11:30, carry unfinished work through to completion automatically without asking. Even if demand looks low or a large from-scratch rewrite is needed, do not substitute another approach; do the real work. Developed together: COBOL_to, Java_to, MFastAPI, 2MFastAPI (converts other languages and frameworks to MFastAPI-compatible code; Node.js and TypeScript are an optional exception and choosing neither is allowed), RMojo, RPoRea (RPoem and Reaxt integrated), 2RPoRea (converts other languages and frameworks to RPoRea) and Reaxt (React + Next.js + Nuxt.js + Nest.js integrated). When one changes, check the others and update README, CLAUDE, PORTING and POLICY in Japanese and English the same day.

<!-- directive-20261125-mojo -->
## 2026-11-25 追記: MFastAPI は Mojo から使えること / Addendum: MFastAPI must be usable from Mojo
**日本語**: MFastAPI は **Mojo から使用できる仕様**を保つ(Python 構文・Rust 実装・Mojo 対応、Windows では RMojo の `compat/wsl-bridge` 経由で WSL 上の Mojo を使う)。2MFastAPI の変換結果も Mojo から使えること。現状: `mojo/` は参照実装で、段階B・Cのサーバーは実験的。Mojo からの呼び出しの実機確認は、確認済みの範囲だけを「確認済み」と書く。11:30 まで確認なしで自動で進める。
**English**: MFastAPI keeps the **specification of being usable from Mojo** (Python syntax, Rust core, Mojo support; on Windows the real Mojo in WSL is driven through RMojo's `compat/wsl-bridge`). Output of 2MFastAPI must be usable from Mojo too. Current state: `mojo/` is a reference implementation and its stage B/C servers are experimental. Only what was actually run is called "verified". Continue automatically without asking until 11:30.

## 2026-11-25 Laravel のルート(PHP)→ MFastAPI / FastAPI / Laravel routes (PHP)
**日本語**: `2mfastapi laravel <Laravelのフォルダー> -o <出力先>` で `routes/web.php`・`routes/api.php`(api は `/api` 付き)を FastAPI / MFastAPI 互換の `main.py` に変換します。訳すのは単純なクロージャ(`return '文字列'`、ルート引数との `.` 連結、`['キー' => 値]` の配列→dict)だけで、それ以外は元の PHP を TODO コメントに残し 501 を返します。確認済み: 試験4件成功(全体9件)、サンプル `examples/laravel_app` を変換して uvicorn(素の FastAPI。`mfastapi.accelerate` は未適用)で起動し、curl で 200×3・501×2 を確認。コントローラー・Eloquent・Blade・ミドルウェア・`"$var"` の展開は未対応。
**English**: `2mfastapi laravel <laravel dir> -o <out>` turns `routes/web.php` and `routes/api.php` (with the `/api` prefix) into a FastAPI/MFastAPI-compatible `main.py`. Only simple closures are translated (`return 'text'`, `.` concatenation with route params, `['key' => value]` arrays to dicts); everything else keeps the original PHP in a TODO comment and returns 501. Verified: 4 new tests pass (9 in total); the sample `examples/laravel_app` was converted, started with uvicorn (plain FastAPI; `mfastapi.accelerate` not applied) and checked with curl (three 200s, two 501s). Controllers, Eloquent, Blade, middleware and `"$var"` interpolation are not supported.

## 2026-11-26 Laravel 変換: MFastAPI の加速・コントローラー・prefix グループ・文字列展開 / Laravel: MFastAPI acceleration, controllers, prefix groups, interpolation
**日本語**: `2mfastapi laravel` の出力は `import mfastapi` を含み、全ルートを登録した後に `mfastapi.accelerate(app)` を呼びます(拡張が無い環境では何も変えず、`MFASTAPI_DISABLE=1` で無効)。新しく次に対応しました: コントローラーのルート `[UserController::class, 'index']` と `'UserController@show'`(`app/Http/Controllers` からメソッドを探し、`return` 1行だけの本体を翻訳。`Request $request` などを受け取るメソッドは TODO・501)、`Route::prefix('admin')->group(function () {...})`(入れ子も可)、ルート引数の文字列展開 `"Hello $name"`・`"Hi {$name}!"`(ルート引数以外の変数は推測せず TODO)。**確認済み**: 試験12件成功。WSL の uvicorn でサンプルを起動し curl で 200×8(`/users`・`/users/5`・`/greet/Hana`・`/admin/stats`・`/admin/v/ping` など)、501×3、未定義 404 を確認。そのとき `mfastapi.backend()` は `"rust"`(mfastapi 0.2.6)、ルーターは加速済みのクラスに差し替わっていました(ルート15本で、加速が働く下限8本以上)。**正直な注意**: リクエストごとに Rust の照合経路を通ったことを計測したわけではなく、速度も測っていません。
**English**: `2mfastapi laravel` output now has `import mfastapi` and calls `mfastapi.accelerate(app)` after every route is registered (it changes nothing when no extension is available; `MFASTAPI_DISABLE=1` turns it off). Newly supported: controller routes `[UserController::class, 'index']` and `'UserController@show'` (methods are looked up in `app/Http/Controllers` and single-`return` bodies are translated; methods taking `Request $request` and the like become TODO/501), `Route::prefix('admin')->group(function () {...})` (nested too), and route-parameter interpolation `"Hello $name"` / `"Hi {$name}!"` (other variables are not guessed and stay TODO). **Verified**: 12 tests pass. The sample was started with uvicorn in WSL and checked with curl: eight 200s (`/users`, `/users/5`, `/greet/Hana`, `/admin/stats`, `/admin/v/ping` and more), three 501s, 404 for an unknown path. At that time `mfastapi.backend()` returned `"rust"` (mfastapi 0.2.6) and the router had been swapped to the accelerated class (15 routes, above the 8-route threshold). **Honest note**: we did not measure that each request actually went through the Rust matching path, and we did not measure speed.

## 2026-11-26 Laravel 変換: middleware・name・controller グループ・resource・Request・Eloquent・Blade / Laravel: middleware, names, controller groups, resources, Request, Eloquent, Blade
**日本語**: `2mfastapi laravel` が次も変換するようになりました。
- ルート: `->name()`(グループの `name('admin.')` と連結し、FastAPI の `name=` に。`app.url_path_for` で引ける)、`Route::middleware()`/`prefix()`/`name()`/`controller()` を `->` でつないだ `->group(function(){...})`、`Route::group([...], function(){...})`、`Route::controller(X::class)->group` 内の `'メソッド名'`、`Route::resource`/`apiResource`(`only`/`except`、update は PUT と PATCH)、`fn () => ...` の短い関数。
- **ミドルウェアは変換しません**。使っているルートは、出力の `MIDDLEWARE["auth"] = 関数` を入れるまで 501 を返します(認証が外れたまま公開されないための安全側の既定)。`web`・`api` は無視します。
- 本体: `$v = 式;` を並べて最後に `return`、`abort(404)`、`$request->all()`/`input('k'[, 既定値])`(クエリと JSON/フォームの本文をまとめたもの)/`query('k')`、`response()->json(x, 201)`、`compact()`、`$model->列`、型付き引数 `User $user` の暗黙のモデル結合(見つからなければ 404)。
- Eloquent → SQLAlchemy Core: `Model::all()`・`find()`・`findOrFail()`・`where(列, 値)`/`where(列, 演算子, 値)` の連結 `->get()`/`->first()`・`create()`。表と列は `database/migrations` の `Schema::create` から作り、無い表は起動時に作成(`DATABASE_URL`、既定は SQLite)。`create` は表にある列だけを入れます。
- Blade → Jinja2: `resources/views/**/*.blade.php` を `templates/**/*.html` に変換(`{{ }}` は Blade と同じくエスケープ、`{!! !!}`、`{{-- --}}`、`@if/@elseif/@else/@unless`、`@foreach`、`@forelse/@empty`、`@extends/@section/@yield`、`@include`、`count()`)。`@csrf` など未対応の書き方は、テンプレート先頭のコメントに書き残します。
**確認済み**: 試験17件成功。WSL の uvicorn でサンプルを起動し、curl で確認しました: ミドルウェア付き 501、`POST /photos`(JSON)201、`POST /api/users`(フォーム)200、一覧・暗黙結合 200、存在しない ID 404、`PATCH` 501(未翻訳の本体)、注文の作成・`where`・`first`・`findOrFail` 404、`/search?q=tea`、Blade のレイアウト付き画面。`mfastapi.backend()` は `"rust"`、ルーターは加速済み(31本)。
**未対応**: `$request->validate()`、Eloquent のリレーション・更新・削除・`DB::` クエリビルダー、Blade のコンポーネント・`$loop`、`Route::where`/`bind`、ミドルウェアの中身。
**English**: `2mfastapi laravel` now also converts:
- Routes: `->name()` (joined with a group `name('admin.')`, emitted as FastAPI `name=`, usable with `app.url_path_for`), `Route::middleware()/prefix()/name()/controller()` chains ending in `->group(function(){...})`, `Route::group([...], function(){...})`, bare `'method'` handlers inside `Route::controller(X::class)->group`, `Route::resource`/`apiResource` (`only`/`except`; update = PUT and PATCH), and `fn () => ...` arrow functions.
- **Middleware is not converted.** Routes that use it answer 501 until you set `MIDDLEWARE["auth"] = function` in the output (a safe default, so auth never silently disappears). `web` and `api` are ignored.
- Bodies: `$v = expr;` lines ending in `return`, `abort(404)`, `$request->all()`/`input('k'[, default])` (query plus JSON or form body)/`query('k')`, `response()->json(x, 201)`, `compact()`, `$model->column`, and implicit model binding for typed arguments like `User $user` (404 when missing).
- Eloquent to SQLAlchemy Core: `Model::all()`, `find()`, `findOrFail()`, chained `where(col, val)`/`where(col, op, val)` with `->get()`/`->first()`, and `create()`. Tables and columns come from `Schema::create` in `database/migrations`; missing tables are created at startup (`DATABASE_URL`, SQLite by default). `create` keeps only the table's columns.
- Blade to Jinja2: `resources/views/**/*.blade.php` becomes `templates/**/*.html` (`{{ }}` escapes like Blade, `{!! !!}`, `{{-- --}}`, `@if/@elseif/@else/@unless`, `@foreach`, `@forelse/@empty`, `@extends/@section/@yield`, `@include`, `count()`). Unsupported directives such as `@csrf` are listed in a comment at the top of the template.
**Verified**: 17 tests pass. The sample ran under uvicorn in WSL and was checked with curl: 501 with middleware, `POST /photos` (JSON) 201, `POST /api/users` (form) 200, listing and implicit binding 200, unknown ID 404, `PATCH` 501 (untranslated body), order create, `where`, `first`, `findOrFail` 404, `/search?q=tea`, and a Blade page with a layout. `mfastapi.backend()` returned `"rust"` and the router was accelerated (31 routes).
**Not supported**: `$request->validate()`, Eloquent relations, update and delete, the `DB::` query builder, Blade components and `$loop`, `Route::where`/`bind`, and what middleware actually does.
