# 作業ログ

## [2026-04-20] 初期構築
- プロジェクト構造を作成（CLAUDE.md, index.md, log.md, wiki/）
- 書籍原稿をraw/にクローン（broad-listening-book リポジトリ）
- 全45章＋10コラムから概念・人物・技術・組織・事例を抽出
- 62ページのWikiを作成（カテゴリ別内訳は以下）

### 概念（12ページ）
ブロードリスニング、デジタル民主主義、熟議民主主義、拡張熟議、Plurality、Connective Action、ノイジーマイノリティ、サイレントマジョリティ、エコーチェンバー、安全な共感、ダブルダイヤモンドモデル、就職氷河期世代

### 技術・ツール（16ページ）
広聴AI、Talk to the City、Polis、大規模言語モデル、Sentence-BERT、UMAP、主成分分析、クラスタリング、いどばた、しゃべれるマニフェスト、声が届くマニフェスト、倍速会議、Sensemaker、Remesh、Recogra、Decidim

### 人物（11ページ）
安野貴博、オードリー・タン、西尾泰和、鈴木健、Colin Megill、伊藤孝恵、青山柊太朗、高木俊輔、関治之、いでい良輔、ユルゲン・ハーバーマス

### 組織（11ページ）
Digital Democracy 2030、チームみらい、国民民主党、日本維新の会、公明党、g0v、AI Objectives Institute、構想日本、多元現実、Code for Japan、JAPAN CHOICE

### 事例（8ページ）
2024年東京都知事選挙、シン東京2050、vTaiwan、ひまわり学生運動、ボーリンググリーン、自分ごと化会議、ミニ・パブリックス、パブリックコメント

### メディア・企業（4ページ）
朝日新聞、日本テレビ、アルティウスリンク、サイボウズ

## [2026-04-20] 原稿精読によるingest（第2回）
- 全45章＋10コラムを精読し、Wikiページを充実化
- 新規13ページを追加（合計75ページ）
- 既存ページ（ブロードリスニング、広聴AI、Talk to the City、Digital Democracy 2030、パブリックコメント）に原稿からの具体的事実を追記

### 新規追加ページ
- 概念: 正統性の空白、論点地図、デジタル公共財、ソブリンAI
- 技術: AIインタビュワー
- 人物: tokoroten、尾花山和哉、小野たいすけ、有賀啓介、田中魁
- 組織: GovTech東京、Democracy X、広島AIラボ、富士通

## [2026-04-26] Quartz + GitHub Pages セットアップ
- `quartz-github-pages-setup.md` のガイドに従って Quartz 4.5.2 を導入
- `wiki/` を編集ソース、`content/` を Quartz 入力として分離
- `scripts/resolve-links.py` で `[[ページ名]]` を Quartz 用パスに変換
- `.github/workflows/deploy.yml` で main push → 自動デプロイ
- `quartz.config.ts`: `baseUrl` を `nishio.github.io/broad-listening-book-wiki`、`locale` を `ja-JP` に
- `index.md` を `wiki/index.md` に移動（サイトのトップページに）
- `raw/`（書籍原稿、366MB）と `.claude/settings.local.json` を `.gitignore` で除外
- 公開URL: https://nishio.github.io/broad-listening-book-wiki/
- 初回 push で workflow が `npm ci` で失敗 → `pnpm install --frozen-lockfile` に修正して再 push

## 2026-09-15 未検証の効果主張を仮説として明示

韓国日報の取材回答を書く過程で、西尾が「設計意図・期待を検証済みの効果として断定しない」という修正を入れた。同じ観点で wiki を見直し、2ページを修正。

- `wiki/安全な共感.md` — 「開かれた共感を実現する」→ 書籍コラムが提示する**未検証の仮説**であると明示。コラム自身が「考えている」と書いており、心理実験・利用者調査による検証はない。あわせてコラムが置いている「ノイジーマイノリティ」留保（クラスタの大きさは件数であって支持率ではない）を本文に復元
- `wiki/倍速会議.md` — 「熟議の質をどの会場でも一定水準以上に引き上げる『スケールアウト』を実現する」→ **スケールアウトは掲げている目標であって達成の報告ではない**と明示。出典コラム「1万件の声を集めて気づいたこと」は「〜という状態を作る」という定義文。導入事例はあるが、ファシリテーター依存の会議との比較データは確認できていない

帰属の注意: `安全な共感` を当初「西尾の仮説」と書きかけたが、`broad-listening-book` repo の `column/安全な共感.md` は commit がすべて @tokoroten であり、西尾が書いた証拠がない。人物ではなく出典文書に帰属させた。

## 2026-10-01 AIあんのの回答数に内訳を追記

wiki森の横断照合（2026-09-30）で、本 wiki の「合計8,600回」と plurality-llm-wiki の「約7,400件」（Plurality 本の脚注）が食い違いとして挙がった。安野のインタビュー（[SlowNews](https://slownews.com/n/nc57874a0ad07)「YouTube7400件、電話1200件で計8600件」）で、7,400 は YouTube 分、8,600 は電話込みの合計と分かった。

- `wiki/安野貴博.md`、`wiki/2024年東京都知事選挙.md` — 内訳を付記。後者は「YouTube Live上で…合計8,600回」と書いていたので、YouTube と電話の両方に直した
- `content/` を `scripts/resolve-links.py` で再生成（2026-09-15 の修正分の未反映も同時に反映）
- 書籍原稿の中でも数字が揃っていない（06_01「8,600回」、序文「1万件弱」、コラム「YouTube約6,200件・電話830件以上」）。原稿の扱いは著者の判断なので wiki では触れない
