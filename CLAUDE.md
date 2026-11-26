# 2MFastAPI 開発方針 / Development notes

**日本語**: 共通ルールは [`open-raid-z/CLAUDE.md`](https://github.com/aon-co-jp/open-raid-z) と [`runo`](https://github.com/aon-co-jp/runo) の `CLAUDE.md` を参照。チャットは日本語のみ。確認なしで開発・TEST・DEBUG・commit・push。heredocでバックスラッシュ・三連引用符を含むコードを書かない(Writeツールを使う)。REST を新設しない方針は本ツールの変換結果には関係しない(変換先は元のアプリの API をそのまま保つ)。
**English**: shared rules live in `open-raid-z/CLAUDE.md` and `runo/CLAUDE.md`. Chat in Japanese only. Develop, test, debug, commit and push without asking. Do not write code with backslashes or triple quotes through bash heredocs (use the Write tool). The "no new REST" policy does not apply to converted output (the converted app keeps its original API).

## 状態 / Status
- 日本語: v0.1.0。Flask / Django / DRF は 2FastAPI(`tofastapi`)で変換し、FastAPI は無変更+`run_mfastapi.py`。差分試験5件(FastAPI+SQLAlchemy+Pydantic、Flask+SQLAlchemy+marshmallow+JWT、DRF ModelViewSet、CLI)を WSL(MFastAPI 0.2.6 の Rust 版を入れて)で確認。毎晩のCI(最新の2FastAPI/MFastAPI/上流で再試験、新版があればパッチ版を自動リリース)あり。
- English: v0.1.0. Flask / Django / DRF go through 2FastAPI (`tofastapi`); FastAPI projects are kept as-is plus `run_mfastapi.py`. 5 differential tests pass in WSL with the MFastAPI 0.2.6 Rust backend. Nightly CI re-tests against the latest 2FastAPI / MFastAPI / upstream and auto-releases a patch version when upstream has a new release.

## 構成 / Layout
`src/tomfastapi/{scan,convert,cli}.py`、`examples/`(試験用サンプル)、`scripts/nightly_bump.py`(毎晩の版上げ)・`scripts/make_pages.py`(紹介ページ生成)、`webpage/`(easy-web.tokyo の `/2MFastAPI` と `/demo`)、`upstream.json`。

## 未了 / Open
- 日本語: PyPI 公開(所有者の認証が必要。2FastAPI・MFastAPI も未公開のため依存は GitHub 参照)、FastAPI 側の「組み合わせ」ごとの個別変換(現状は無変更で動かす)、macOS/Windows の CI。
- English: PyPI publication (needs the owner's credentials; the dependency is a GitHub reference because 2FastAPI/MFastAPI are not on PyPI either), per-combination rewrites on the FastAPI side (today they run unchanged), macOS/Windows CI.

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

## Versionless API の方針 / Versionless API policy (2026-11-25)
**日本語**: このリポジトリのAPIは **Versionless**(URL・パッケージ名に `v1` 等を付けず、互換性を壊さず足すだけで進化させる)。欄は足すだけ・足す欄は省略可能・知らない欄は無視・名前変更は新名を足して旧を非推奨に(期限は既定で6か月以上、使用0を確認してから削除)・enumは未知の値を許容・安全上の緊急修正は例外。既存の `.v1` は呼び出し側を壊さないよう当面残し、版なしの別名を追加して段階的に畳む。詳細・出典は [`runo/API-POLICY.md`](https://github.com/aon-co-jp/runo/blob/main/API-POLICY.md) 末尾。適用はこれから順に行う。
**English**: This repository's APIs are **Versionless**: no `v1` in URLs or package names; evolve by adding only, without breaking compatibility. Only add fields, new fields are optional, ignore unknown fields, rename by adding the new name and deprecating the old (default deadline 6 months or more, remove only after confirming zero use), tolerate unknown enum values, emergency security fixes are the exception. Existing `.v1` names stay for now so callers do not break; a versionless alias is added and `.v1` is retired in stages. Details and sources: the end of [`runo/API-POLICY.md`](https://github.com/aon-co-jp/runo/blob/main/API-POLICY.md). Rollout is step by step.

## API 方針: REST 全廃・gRPC / Connect へ
**日本語**: このリポジトリでは **REST API を新規に作らない**。ブラウザ・`curl` から呼ぶ API は **Connect の単純呼び出し**(`POST /<パッケージ>.<Service>/<Method>`、`content-type: application/json`)、サービス間は **gRPC / gRPC-web**。GraphQL は読み取り専用。既存の REST は触るときに移し、移したら旧経路は消す。JSON は RS-JSON(`from_str_secure` / `parse_secure`)で読む。例外は相手の規格が形を決めるもの(ACME、OAuth/OIDC のコールバック、第三者の Webhook、ヘルスチェック、静的ファイル、OTLP)のみ。迷ったら Connect。正本は [`runo/API-POLICY.md`](https://github.com/aon-co-jp/runo/blob/main/API-POLICY.md)。
**English**: This repository **does not add new REST APIs**. APIs called from browsers or `curl` use **Connect unary calls** (`POST /<package>.<Service>/<Method>`, `content-type: application/json`); service-to-service calls use **gRPC / gRPC-web**. GraphQL is read-only. Existing REST is migrated when touched and the old route is removed. Read JSON with RS-JSON (`from_str_secure` / `parse_secure`). Exceptions are only shapes dictated by someone else's standard (ACME, OAuth/OIDC callbacks, third-party webhooks, health checks, static files, OTLP). When in doubt, use Connect. Source of truth: the link above.

## 2026-11-26 Laravel 変換(`src/tomfastapi/laravel.py`)の作業メモ / Working notes
**日本語**: 出力は必ず最後に `mfastapi.accelerate(app)` を呼ぶ(ルート登録の後)。訳せないものは推測せず、元の PHP を TODO コメントに残して 501。ミドルウェアは中身を訳さず 501 を既定にする(認証が黙って外れるのを防ぐ)。試験は `wsl -d Ubuntu -- bash /mnt/f/2MFastAPI/run-tests.sh`(17件)。実起動の確認は WSL の `~/2fa-venv` の uvicorn と curl で行い、`mfastapi.backend()` も記録する。サンプルは `examples/laravel_app`。
**English**: Output always ends with `mfastapi.accelerate(app)` (after route registration). Never guess: untranslatable code keeps the original PHP in a TODO comment and answers 501. Middleware bodies are not translated and default to 501 (so auth never silently disappears). Tests: `wsl -d Ubuntu -- bash /mnt/f/2MFastAPI/run-tests.sh` (17). Check real runs with uvicorn from `~/2fa-venv` in WSL plus curl, and record `mfastapi.backend()`. Sample: `examples/laravel_app`.
