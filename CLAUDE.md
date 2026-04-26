# Broad Listening Book Wiki

書籍「選挙を変えたブロードリスニング 生成AIが実現する民意の可視化と分析」に登場する概念・人物・技術・組織・事例のWiki。

## ディレクトリ構成

- `raw/` — 書籍の原稿（読み取り専用、変更不可）
- `wiki/` — Wikiページ（LLMが生成・更新する）
- `wiki/index.md` — Wikiページの一覧とカテゴリ別索引（Quartzサイトのトップ）
- `content/` — `wiki/` から自動生成される（Quartzのビルド入力）。**直接編集しない**
- `scripts/resolve-links.py` — `wiki/` → `content/` 変換と `[[wikilink]]` 解決
- `.github/workflows/deploy.yml` — GitHub Pages への自動デプロイ
- `log.md` — 作業ログ（時系列）

## デプロイ

`main` に push すると GitHub Actions が `wiki/` をビルドして `https://nishio.github.io/broad-listening-book-wiki/` に公開する。
ローカルプレビューは `pnpm serve`（または `python3 scripts/resolve-links.py && npx quartz build --serve`）。

## Wikiページの規約

### ファイル名
- 日本語の概念名をそのまま使う（例: `ブロードリスニング.md`）
- 英語名がある場合は英語をファイル名にする（例: `Talk_to_the_City.md`）
- 人名は姓名で（例: `安野貴博.md`, `Audrey_Tang.md`）
- スペースはアンダースコアに置き換える

### ページ構成
```markdown
# ページタイトル

概要（1〜3文で簡潔に）

## 詳細

本文。書籍での記述に基づく。

## 関連項目

- [[関連ページ名]]
```

### 相互リンク
- `[[ページ名]]` 形式でWikiリンクを記述（Obsidian互換）
- 関連項目セクションに主要な関連ページを列挙
- 本文中でも初出時にリンクする

### カテゴリ
ページは以下のカテゴリに分類する：
- **概念** — ブロードリスニング、デジタル民主主義、熟議民主主義など
- **技術** — Talk to the City、Polis、Sentence-BERTなど
- **人物** — 安野貴博、オードリー・タンなど
- **組織** — DD2030、チームみらい、g0vなど
- **事例** — 2024年東京都知事選、シン東京2050、vTaiwanなど
- **分析手法** — クラスタリング、次元削減、ベクトル化など

## 運用ルール

- 原稿（raw/）の内容に基づいて記述する
- 新しいページを作成したら `wiki/index.md` を更新する
- 作業内容は log.md に記録する
