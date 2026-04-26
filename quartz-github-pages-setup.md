# Quartz + GitHub Pages で Wiki を公開する手順（移植ガイド）

「Markdown を書いて push すれば GitHub Pages に自動公開される」構成を作るためのガイド。dd2030-wiki で実際に動いているセットアップを、他のリポジトリにそのまま移植できる形でまとめた。**このファイル 1 つを読めば再現できる**ようにスクリプトと設定の中身も全て記載してある。

## 何ができるようになるか

- `wiki/` 配下の Markdown を編集して push するだけで、GitHub Pages に静的サイトが自動デプロイされる
- リンクは `[[ページ名]]` とシンプルに書ける（パスは自動解決）
- ローカルで `--serve` でプレビューできる
- LLM が Wiki を編集しやすい構造（フロントマター + 短い wikilink）を保ったまま、Quartz の機能（検索・グラフ・バックリンク等）が使える

## 全体像

```
wiki/                   ← 人間/LLM が編集する場所（[[ページ名]] でリンク）
  ↓ python3 scripts/resolve-links.py（prebuild で自動実行）
content/                ← Quartz が読む場所（自動生成、直接編集しない）
  ↓ npx quartz build
public/                 ← 生成された HTML
  ↓ GitHub Actions
GitHub Pages
```

ポイント:
- **Quartz は `content/` を読む前提**で、wiki ファイルを直接置くと「リンクのパス指定が面倒」「ファイル移動でリンクが壊れる」などの問題が出る
- そこで `wiki/` を「編集用」、`content/` を「ビルド入力用」として分離し、`resolve-links.py` で `[[ページ名]]` を `[[相対パス|ページ名]]` に自動変換する
- `package.json` の `prebuild` に仕込んであるので `npx quartz build` の前に必ず走る（CI では明示 step として呼ぶ）

## 前提

- Node.js 22+
- Python 3.10+
- 公開先となる GitHub リポジトリ（Public か、Pages を有効にできる Pro/Org Private）

## 構築手順

### ステップ 1: Quartz を fork してクローン

[Quartz 本家](https://github.com/jackyzha0/quartz) を fork するのが楽。

```bash
git clone https://github.com/jackyzha0/quartz.git my-wiki
cd my-wiki
git remote set-url origin https://github.com/<your-username>/my-wiki.git
```

Quartz 本体は `quartz/` ディレクトリと `package.json`, `quartz.config.ts`, `quartz.layout.ts`, `tsconfig.json`, `globals.d.ts`, `index.d.ts` などから成る。これらはそのまま使えばよい。

### ステップ 2: ディレクトリ構成を整える

```bash
mkdir -p wiki scripts .github/workflows
# Quartz が初期で持っている content/ の中身は wiki/ に移す
mv content/* wiki/ 2>/dev/null || true
```

### ステップ 3: `quartz.config.ts` の `baseUrl` を変更

```ts
configuration: {
  pageTitle: "My Wiki",
  baseUrl: "<your-username>.github.io/<repo-name>",
  locale: "ja-JP",  // 日本語 wiki なら
  ...
}
```

`baseUrl` は **末尾スラッシュなし**、**プロトコルなし** で書く。これを間違うと CSS や内部リンクが 404 になる。

### ステップ 4: wikilink 解決スクリプトを置く

`scripts/resolve-links.py` を以下の内容で作成する。

<details>
<summary>scripts/resolve-links.py の全文（クリックで展開）</summary>

```python
#!/usr/bin/env python3
"""
wiki/ → content/ へコピーしつつ、[[wikilink]] を Quartz が解決できるパスに変換する。

処理:
1. wiki/ 配下の全 .md ファイルをスキャンし、title と aliases から名前→パスの対応表を構築
2. 全ファイルを content/ にコピーしつつ、[[リンク名]] を [[相対パス|リンク名]] に変換
3. 対応するページが存在しないリンクはそのまま残す（プレーンテキスト化）

wiki/ のファイルはシンプルな [[ページ名]] で書けばよく、
パス解決はこのスクリプトが自動で行う。
"""

import os
import re
import shutil
import yaml

WIKI_DIR = os.path.join(os.path.dirname(__file__), '..', 'wiki')
CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content')

WIKI_DIR = os.path.abspath(WIKI_DIR)
CONTENT_DIR = os.path.abspath(CONTENT_DIR)


def extract_frontmatter(filepath):
    """ファイルからYAMLフロントマターを抽出"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if not content.startswith('---'):
        return {}, content
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, content


def build_link_map(wiki_dir):
    """
    名前 → 相対パス（拡張子なし）の対応表を構築。

    以下の名前でマッチする:
    - ファイル名（拡張子なし）: e.g. "kouchou-ai" → "entities/kouchou-ai"
    - title: e.g. "広聴AI" → "entities/kouchou-ai"
    - aliases の各エントリ: e.g. "広聴AI" → "entities/kouchou-ai"
    """
    link_map = {}

    for root, dirs, files in os.walk(wiki_dir):
        for fname in files:
            if not fname.endswith('.md'):
                continue

            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, wiki_dir)
            # 拡張子を除去し、パス区切りを / に統一
            slug = rel_path.replace(os.sep, '/').removesuffix('.md')

            # ファイル名（拡張子なし）
            basename = fname.removesuffix('.md')
            link_map[basename] = slug

            # フロントマターから title と aliases を取得
            fm, _ = extract_frontmatter(filepath)

            if fm.get('title'):
                link_map[fm['title']] = slug

            for alias in (fm.get('aliases') or []):
                link_map[alias] = slug

    return link_map


def resolve_wikilinks(content, link_map, current_slug):
    """
    [[リンク名]] → [[解決済みパス|リンク名]] に変換。
    [[パス|表示名]] 形式は既に解決済みとしてスキップ。
    """
    def replace_link(match):
        inner = match.group(1)

        # 既に [[path|display]] 形式の場合
        if '|' in inner:
            path_part, display = inner.split('|', 1)
            # path_part がlink_mapにある場合はパスに変換
            if path_part in link_map:
                resolved = link_map[path_part]
                return f'[[{resolved}|{display}]]'
            # path_part が既にパスっぽい場合はそのまま
            return match.group(0)

        # [[リンク名]] 形式
        link_name = inner.strip()

        if link_name in link_map:
            resolved = link_map[link_name]
            # 自分自身へのリンクはそのまま
            if resolved == current_slug:
                return f'**{link_name}**'
            # 表示名がファイル名と同じならパスだけでOK
            if link_name == resolved.split('/')[-1]:
                return f'[[{resolved}]]'
            return f'[[{resolved}|{link_name}]]'

        # 対応するページがない場合はプレーンテキストに
        return link_name

    return re.sub(r'\[\[([^\]]+)\]\]', replace_link, content)


def main():
    # link_map を構築
    link_map = build_link_map(WIKI_DIR)

    print(f"Link map ({len(link_map)} entries):")
    for name, slug in sorted(link_map.items()):
        print(f"  {name} → {slug}")
    print()

    # content/ をクリーンアップ
    if os.path.exists(CONTENT_DIR):
        shutil.rmtree(CONTENT_DIR)
    os.makedirs(CONTENT_DIR, exist_ok=True)

    # wiki/ → content/ にコピーしつつリンク解決
    file_count = 0

    for root, dirs, files in os.walk(WIKI_DIR):
        for fname in files:
            src = os.path.join(root, fname)
            rel = os.path.relpath(src, WIKI_DIR)
            dst = os.path.join(CONTENT_DIR, rel)

            os.makedirs(os.path.dirname(dst), exist_ok=True)

            if fname.endswith('.md'):
                with open(src, 'r', encoding='utf-8') as f:
                    content = f.read()

                slug = rel.replace(os.sep, '/').removesuffix('.md')
                new_content = resolve_wikilinks(content, link_map, slug)

                with open(dst, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                file_count += 1
            else:
                shutil.copy2(src, dst)

    print(f"Processed {file_count} markdown files")
    print(f"Output: {CONTENT_DIR}")

    # 検証: content/ 内の未解決リンク（対応するファイルが存在しないもの）を報告
    print("\nValidation - checking for broken links:")
    broken = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            filepath = os.path.join(root, fname)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            for m in re.finditer(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text):
                link_target = m.group(1)
                target_path = os.path.join(CONTENT_DIR, link_target + '.md')
                if not os.path.exists(target_path):
                    rel_file = os.path.relpath(filepath, CONTENT_DIR)
                    broken.append((rel_file, link_target))

    if broken:
        print(f"  WARNING: {len(broken)} broken link(s) found:")
        for src_file, target in broken:
            print(f"    {src_file} → [[{target}]]")
    else:
        print("  All links valid!")


if __name__ == '__main__':
    main()
```

</details>

スクリプトのおおまかな流れ:

- フロントマターの `title` と `aliases` から「名前 → パス」の対応表を構築
- `[[ページ名]]` を `[[entities/foo|ページ名]]` のような Quartz が解決できる形式に変換
- 自分自身へのリンクは `**ページ名**` （太字）に変換
- 対応するページがないリンクはプレーンテキスト化（赤リンクを残さない）
- 最後に「broken link 一覧」を出力して検証

`WIKI_DIR` と `CONTENT_DIR` は `scripts/` の親ディレクトリ基準なので、`scripts/resolve-links.py` という配置ならそのまま動く。

### ステップ 5: GitHub Actions ワークフローを置く

`.github/workflows/deploy.yml` を以下の内容で作成する。

```yaml
name: Deploy Quartz to GitHub Pages

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0   # CreatedModifiedDate プラグインが git 履歴を読むため

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Python dependencies
        run: pip install pyyaml

      - name: Resolve wikilinks (wiki/ → content/)
        run: python3 scripts/resolve-links.py

      - name: Install Node dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: npx quartz build

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: public

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

ハマりポイント:
- `fetch-depth: 0` は必須。Quartz の `CreatedModifiedDate` プラグインが git log で更新日を取るため、shallow clone だと「全ページ同じ日付」になる
- pnpm を使うなら `pnpm-lock.yaml` をコミットしておく。npm でいいなら `npm ci && npx quartz build` に置き換えてよい
- `pip install pyyaml` は resolve-links.py の依存。それ以外の追加 Python パッケージは要らない

### ステップ 6: `package.json` の `prebuild` フックを追加

```json
"scripts": {
  "prebuild": "python3 scripts/resolve-links.py",
  ...
}
```

これがあると `pnpm build` 系の前に自動でリンク解決が走る。CI で `npx quartz build` を直接呼ぶ場合は `prebuild` が発火しないので、ワークフロー側でも明示 step として `python3 scripts/resolve-links.py` を呼んでおく（前ステップの deploy.yml にはすでに入れてある）。両方仕込んでおくとローカル/CI 両方で安全。

### ステップ 7: `.gitignore`

```
node_modules/
public/
.quartz-cache/
.obsidian/
.DS_Store
```

`content/` は **gitignore しない**運用が dd2030-wiki の選択。リンク解決後の状態をコミットしておくと、ローカルで `python3 scripts/resolve-links.py` を走らせる前でも GitHub 上で見られる（PR レビュー時は自動生成物として差分を無視する）。
gitignore する選択肢もあり。CI では毎回再生成するので、どちらでも動く。

### ステップ 8: ローカルで動作確認

```bash
corepack enable
pnpm install
pip install pyyaml

python3 scripts/resolve-links.py
npx quartz build --serve
# → http://localhost:8080 で確認
```

### ステップ 9: GitHub Pages を有効化

1. GitHub の **Settings → Pages** を開く
2. **Build and deployment → Source** を **GitHub Actions** に設定（"Deploy from a branch" ではない）
3. main に push する → Actions タブでワークフローが走る → 完了すると `https://<user>.github.io/<repo>/` で公開される

## Wiki ページの規約（推奨）

`wiki/` 配下のページにはフロントマターを付ける:

```markdown
---
title: 広聴AI
aliases: [kouchou-ai, 広聴]
tags: [product]
created: 2025-04-18
updated: 2026-04-26
---

[[overview]] からリンクされる。関連: [[Polimoney]]
```

- `title` と `aliases` の両方が `resolve-links.py` の対応表に入るので、`[[広聴AI]]` でも `[[kouchou-ai]]` でも同じページにリンクされる
- リンク先のファイルが `wiki/entities/kouchou-ai.md` なら、編集者はパスを意識しなくていい
- `created`, `updated` は Quartz が表示に使う

カテゴリ別ディレクトリ（例）:

```
wiki/
├── index.md            # 目次
├── overview.md         # プロジェクト概要
├── entities/           # 人物・組織・プロダクトのページ
├── concepts/           # 概念・用語の説明
├── events/             # イベント・会議
├── topics/             # テーマ別の横断整理
├── timeline/           # 時系列の活動まとめ
└── sources/            # 元資料の要約
```

これは LLM が Wiki を維持しやすくするための分類例。プロジェクトに合わせて変えてよい。

## カスタマイズしたくなる箇所

| やりたいこと | 触る場所 |
|-------------|---------|
| サイトタイトル/言語 | `quartz.config.ts` の `pageTitle`, `locale` |
| 配色・フォント | `quartz.config.ts` の `theme` |
| サイドバー/ヘッダーの構成 | `quartz.layout.ts` |
| フッターのリンク | `quartz.layout.ts` の `Component.Footer` |
| 公開対象から除外するファイル | `quartz.config.ts` の `ignorePatterns` |
| プラグイン追加（数式、Mermaid等） | `quartz.config.ts` の `plugins.transformers` |

## トラブルシューティング

**CSS が読み込まれない / リンクが 404**
→ `baseUrl` の設定ミス。`<user>.github.io/<repo>` 形式（プロトコルなし、末尾スラッシュなし）になっているか確認。

**全ページの「最終更新日」が同じになる**
→ `actions/checkout@v4` の `fetch-depth: 0` が抜けている。

**`[[ページ名]]` がリンクにならず生のテキストで出る**
→ resolve-links.py が走っていないか、対応するファイルが存在しない。CI ログで `Link map (N entries):` と broken link の警告を確認。

**`prebuild` が CI で実行されない**
→ CI が `npx quartz build` を直接呼ぶ場合 `prebuild` フックは発火しない。ワークフロー側で明示的に `python3 scripts/resolve-links.py` を呼ぶ step を入れる（このガイドの deploy.yml にはすでに入れてある）。

**Quartz をアップデートしたら壊れた**
→ Quartz 本体は破壊的変更が入ることがある。`pnpm-lock.yaml` をコミットしておけば再現可能。アップデートは別ブランチで動作確認してからマージ。

## 参考

- [Quartz 本家ドキュメント](https://quartz.jzhao.xyz/)
- [LLM Wiki パターン（karpathy）](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
