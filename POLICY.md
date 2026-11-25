# POLICY.md

## 2026-11-25 同時開発の方針 / Policy: develop together

**日本語**: 方針(2026-11-25、ユーザー指示): 未了は確認なしで完成まで自動で進める。需要が少ない・1からの大規模な開発が必要でも、別の方式で済ませず真摯に作り直す。特に COBOL_to・Java_to・MFastAPI・2MFastAPI(他の言語・フレームワークから MFastAPI 互換へ変換。Node.js・TypeScript は例外的に選択可で、選ばない選択も可)・RMojo・RPoRea・2RPoRea(他の言語から RPoRea=RPoem+Reaxt へ変換。Reaxt は React・Next.js・Nuxt.js・Nest.js 相当)・Reaxt を同時に開発する。2RPoRea は 2026-11-25 に新設(検出 scan のみ、変換は未着手)。

**English**: Policy (2026-11-25, user instruction): carry unfinished work through to completion without asking. Even when demand is low or a large from-scratch rewrite is needed, do the real work instead of substituting another approach. Developed together: COBOL_to, Java_to, MFastAPI, 2MFastAPI (converts other languages and frameworks to MFastAPI-compatible code; Node.js and TypeScript are an optional exception and choosing neither is allowed), RMojo, RPoRea, 2RPoRea (converts other languages to RPoRea = RPoem + Reaxt; Reaxt is the Rust equivalent of React, Next.js, Nuxt.js and Nest.js) and Reaxt. 2RPoRea was created on 2026-11-25 (detection `scan` only; conversion not started).

<!-- directive-20261125-1130 -->
## 2026-11-25 指示(11:30 まで確認不要) / Directive (no confirmation until 11:30)
**日本語**: 2026-11-25 11:30 まで、未了は確認なしで完成まで自動で進める。需要が少ない・必要性が低いと判断される、あるいは1から大規模に作り直す必要があっても、別の方式で済ませず、正面から作り直す。同時に開発する対象: COBOL_to・Java_to・MFastAPI・2MFastAPI(他の言語・フレームワークから MFastAPI 互換へ。Node.js・TypeScript は例外的に選べ、選ばない選択も可能)・RMojo・RPoRea(RPoem と Reaxt の統合)・2RPoRea(他の言語・フレームワークから RPoRea へ)・Reaxt(React+Next.js+Nuxt.js+Nest.js の統合)。1つ変えたら他を確認し、README・CLAUDE・PORTING・POLICY を日英で同じ日に更新する。
**English**: Until 2026-11-25 11:30, carry unfinished work through to completion automatically without asking. Even if demand looks low or a large from-scratch rewrite is needed, do not substitute another approach; do the real work. Developed together: COBOL_to, Java_to, MFastAPI, 2MFastAPI (converts other languages and frameworks to MFastAPI-compatible code; Node.js and TypeScript are an optional exception and choosing neither is allowed), RMojo, RPoRea (RPoem and Reaxt integrated), 2RPoRea (converts other languages and frameworks to RPoRea) and Reaxt (React + Next.js + Nuxt.js + Nest.js integrated). When one changes, check the others and update README, CLAUDE, PORTING and POLICY in Japanese and English the same day.
