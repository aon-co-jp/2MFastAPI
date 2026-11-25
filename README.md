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
