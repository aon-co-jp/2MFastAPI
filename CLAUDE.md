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
