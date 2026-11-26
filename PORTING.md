# 2MFastAPI PORTING / 再開メモ

## 日本語
**状態(2026-11-18)**: v0.1.0 を新規作成。`2mfastapi scan/convert/auto`。FastAPI は無変更で `run_mfastapi.py` を追加、Flask/Django/DRF は 2FastAPI(v0.5.2 以降)に委譲。毎晩のCI(02:47 JST)で再試験・自動リリース。easy-web.tokyo の `/2MFastAPI` と `/2MFastAPI/demo/`(ダウンロード専用)を公開。
**未了**: PyPI公開(所有者の認証)。トップのバナーは配備済み(末尾の記録)。
**テスト**: `bash run-tests.sh`(WSL。`2FastAPI` を隣に置き、MFastAPI のホイールを入れると Rust 版で試験)。
**再開用メッセージ**: 「`F:\2MFastAPI\PORTING.md` を読んで、未了の続きを確認なしで開発・TEST・DEBUG・commit・pushして。チャットは日本語のみ。」

## English
**Status (2026-11-18)**: v0.1.0 created. `2mfastapi scan/convert/auto`. FastAPI projects are kept unchanged plus `run_mfastapi.py`; Flask/Django/DRF are delegated to 2FastAPI (v0.5.2+). Nightly CI (02:47 JST) re-tests and auto-releases. `/2MFastAPI` and `/2MFastAPI/demo/` (download-only) are live on easy-web.tokyo.
**Open**: PyPI (owner credentials). The top-page banner is deployed (see the record at the end).
**Tests**: `bash run-tests.sh` (WSL; keep `2FastAPI` next to this repo and install an MFastAPI wheel to test the Rust backend).
**Resume message**: "Read `F:\2MFastAPI\PORTING.md` and continue the open items without asking (develop, test, debug, commit, push). Chat in Japanese only."

## 記録 / Record (2026-11-18)
- 日本語: `aon-co-jp/2MFastAPI` 公開(v0.1.0、CI成功)。VPS: `/root/easy-web-intros/2MFastAPI/`(index・demo)、`domains.toml` に `/2MFastAPI` を追加(反映前のコピー `/root/domains.toml.before-2mfastapi-20261118`、`open-web-server` を再起動し既存ドメインの応答は前後で同一)、`/root/refresh_versions.py` に 2MFastAPI を追加(元は `.before-2mfastapi`)。version-control の走査対象 `/root/repository/` に `2MFastAPI`・`2FastAPI` をクローン。**トップページのバナーは `open-easy-web` `f205e8c`(intro_banners.rs)に追加済みだが、本番の open-easy-web サーバー(認証サーバー)の再ビルド・差し替えは未実施**。
- English: `aon-co-jp/2MFastAPI` published (v0.1.0, CI green). VPS: `/root/easy-web-intros/2MFastAPI/` (index, demo); `/2MFastAPI` added to `domains.toml` (pre-change copy `/root/domains.toml.before-2mfastapi-20261118`, `open-web-server` restarted, other domains answered the same before/after); `/root/refresh_versions.py` now lists 2MFastAPI (original kept as `.before-2mfastapi`). `2MFastAPI` and `2FastAPI` cloned under `/root/repository/` for version-control. **The top-page banner is in `open-easy-web` `f205e8c` (intro_banners.rs) but the production open-easy-web (auth) server has not been rebuilt and swapped.**
- 日本語: トップのバナーを配備(2026-11-18)。`cda9653`(本番と同時点)+バナー変更のみを WSL(Ubuntu-24.04、glibc 2.39)でビルド→VPS別ポートでカナリア→差し替え。旧バイナリ `/root/open-easy-web-server.before-2mfastapi-20261118`(戻すときは `target/release/open-easy-web-server` に戻して `systemctl restart open-easy-web`)。注意: main の `fcad6eb`(open-cpu同梱)は未配備のまま含めていない。`server/Cargo.lock` が最新の兄弟クレートと合わず `--locked` は不可だった。
- English: Top banner deployed (2026-11-18). Built `cda9653` (what production ran) + only the banner change in WSL Ubuntu-24.04 (glibc 2.39), canary on another port, then swapped. Old binary kept at `/root/open-easy-web-server.before-2mfastapi-20261118` (roll back by restoring it to `target/release/open-easy-web-server` and `systemctl restart open-easy-web`). `fcad6eb` (open-cpu bundle) was deliberately not included; `--locked` failed because `server/Cargo.lock` is out of sync with sibling crates.

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

## 2026-11-25 Laravel ルート変換 / Laravel route conversion
**日本語**: `src/tomfastapi/laravel.py` と `laravel` サブコマンドを追加。試験4件成功、サンプルを uvicorn(素の FastAPI)で起動し curl で確認済み。未了: コントローラー(`[Controller::class, 'm']`)、`Route::group`/`prefix`、`"$var"` 展開、MFastAPI の accelerate 適用での起動確認。
**English**: Added `src/tomfastapi/laravel.py` and the `laravel` subcommand. 4 tests pass; the sample ran under uvicorn (plain FastAPI) and was checked with curl. Open: controllers, `Route::group`/`prefix`, `"$var"` interpolation, a run with MFastAPI accelerate applied.

## 2026-11-26 Laravel 変換の拡張 / Laravel conversion extended
**日本語**: `laravel.py` を、ルートを一覧にしてから出力する形に作り直し、コントローラー(配列形式と `@` 形式)・`Route::prefix()->group()`(入れ子)・`"$var"`/`"{$var}"` 展開・出力末尾の `mfastapi.accelerate(app)` を追加。試験12件成功、WSL uvicorn+curl で確認、`mfastapi.backend()`=`rust`。未了: `Route::middleware`/`name`/`controller()->group`、`Route::resource`、`Request` を使う本体、Eloquent・Blade、リクエストごとの Rust 経路と速度の計測。
**English**: `laravel.py` now collects routes first and then emits them; added controllers (array and `@` forms), nested `Route::prefix()->group()`, `"$var"`/`"{$var}"` interpolation and a trailing `mfastapi.accelerate(app)`. 12 tests pass; checked with uvicorn + curl in WSL; `mfastapi.backend()` = `rust`. Open: `Route::middleware`/`name`/`controller()->group`, `Route::resource`, bodies using `Request`, Eloquent and Blade, measuring the per-request Rust path and speed.

## 2026-11-26 Laravel 変換の第2段 / Laravel conversion, round 2
**日本語**: `laravel.py` を「プロジェクト走査(コントローラー・モデル・マイグレーション・Blade)→ルート収集(スコープ付き)→本体翻訳(Ctx)→コード生成」に作り直し、middleware・name・controller グループ・`Route::group([...])`・resource/apiResource・`fn` 短関数・Request・Eloquent(SQLAlchemy Core)・Blade(Jinja2)・暗黙のモデル結合に対応。ミドルウェアは安全側で 501(`MIDDLEWARE` に関数を入れると動く)。試験17件、WSL uvicorn+curl、`mfastapi.backend()`=`rust`。注意: Blade と同じく `@` の直前が英数字だと命令として扱わない。未了: validate、リレーション・更新・削除、`DB::`、Blade コンポーネント、`$loop`。
**English**: `laravel.py` is now "scan the project (controllers, models, migrations, Blade) -> collect routes with scopes -> translate bodies (Ctx) -> generate code", adding middleware, names, controller groups, `Route::group([...])`, resource/apiResource, `fn` arrow functions, Request, Eloquent (SQLAlchemy Core), Blade (Jinja2) and implicit model binding. Middleware answers 501 by default (put a function in `MIDDLEWARE` to enable). 17 tests; WSL uvicorn + curl; `mfastapi.backend()` = `rust`. Note: as in Blade, `@` right after a letter or digit is not a directive. Open: validate, relations/update/delete, `DB::`, Blade components, `$loop`.
