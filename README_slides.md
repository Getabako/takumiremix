# if(塾) Blog Automation System - プレゼンテーション用スライド

**作成日**: 2025年12月30日
**NotebookLM用**: 15枚のスライド構成

---

## スライド 1: タイトルスライド

### if(塾) Blog Automation System

**Gemini AIで実現する完全自動ブログ運営**

- 最新トレンド情報を自動収集
- 画像付きブログ記事を自動生成
- GitHub Pagesに自動投稿

**公開URL**: https://takubon0202.github.io/if-blog-auto/

**作成日**: 2025年12月30日

---

## スライド 2: システム概要

### 何ができるシステムか？

**自動化される作業:**
1. 最新ニュース・トレンドの調査
2. SEO最適化されたブログ記事の執筆
3. アイキャッチ画像の生成
4. 品質チェック・ファクトチェック
5. GitHub Pagesへの投稿・公開

**特徴:**
- 毎日JST 5:00に自動実行
- 7日以内の最新情報のみ使用
- 6つのトピック + 週間総括を曜日別に生成

---

## スライド 3: リサーチ方法の選択

### Multi-Search vs Deep Research

| 曜日 | リサーチ方法 | 検索回数 | 処理時間 |
|------|-------------|----------|---------|
| 月〜土 | Multi-Search | 3回 | 約10秒 |
| 日曜日 | Deep Research | 1回 | 約5分 |

**設計理由:**
- Deep ResearchはRPM 1/分の厳しい制限
- Multi-Searchは3つの視点から高品質な情報収集
- 失敗時は自動でMulti-Searchにフォールバック

---

## スライド 4: システムフロー全体像

### 5ステップの自動処理

```
Step 1: 情報収集
    ↓ Multi-Search 3回検索 / Deep Research
Step 2: 記事生成
    ↓ Gemini 3 Pro で執筆
Step 3: 画像生成
    ↓ Gemini 2.5 Flash image
Step 4: SEO最適化 & 品質レビュー
    ↓ Gemini 3 Flash（高速処理）
Step 5: GitHub Pages 投稿
    → Jekyll → Git Push → 自動公開
```

---

## スライド 5: 使用AIモデル

### 用途別に最適化されたAIモデル

| 用途 | モデル | 特徴 |
|------|--------|------|
| 情報収集 | gemini-3-pro-preview + Multi-Search | 3回検索で網羅的 |
| 深層調査 | deep-research-pro-preview-12-2025 | 日曜のみ |
| 記事生成 | gemini-3-pro-preview | 高品質な文章生成 |
| 画像生成 | gemini-2.5-flash-image | スマートプロンプト対応 |
| SEO/レビュー | gemini-3-flash-preview | 思考オフで高速 |

---

## スライド 6: 対象トピック

### 6つのトピック + 週間総括

| 曜日 | トピック | キーワード例 |
|------|----------|-------------|
| 月曜 | 心理学・メンタルヘルス | 心理学、カウンセリング |
| 火曜 | 教育・学習科学 | EdTech、学習法 |
| 水曜 | 起業家育成・スタートアップ | 起業、経営 |
| 木曜 | 投資教育・金融リテラシー | NISA、資産形成 |
| 金曜 | AIツール・技術動向 | ChatGPT、Gemini |
| 土曜 | インクルーシブ教育 | 不登校、発達障害 |
| **日曜** | **週間トレンド総括** | 6分野横断 |

---

## スライド 7: Multi-Search（3回検索）の仕組み

### 3つの視点から情報を統合

| 検索 | 視点 | 目的 |
|------|------|------|
| 1回目 | 最新ニュース・公式発表 | 直近の重要ニュース |
| 2回目 | 専門家の見解・研究データ | 学術的知見・エビデンス |
| 3回目 | 実践事例・統計情報 | 具体的な事例と数値 |

**トピック別専門クエリ:**
- psychology: 心理学 メンタルヘルス 最新研究 論文発表
- ai_tools: 生成AI ChatGPT Claude Gemini 新機能

---

## スライド 8: サブエージェント構成

### 8つの専門エージェント

| エージェント | 役割 |
|-------------|------|
| google-search-agent | Multi-Search情報収集（メイン） |
| deep-research-agent | 深層調査（日曜のみ） |
| writing-agent | ブログ記事の執筆 |
| image-agent | アイキャッチ画像生成 |
| seo-agent | SEOメタデータ最適化 |
| review-agent | 品質チェック |
| site-builder-agent | Jekyllサイト構造管理 |
| blog-publisher-agent | GitHub Pages投稿 |

---

## スライド 9: スマートプロンプト画像生成

### 記事内容に合った画像を自動生成

**分析項目:**
- main_subject: メインの視覚的対象
- visual_metaphor: 記事の核心を表すメタファー
- mood: 感情的トーン
- key_elements: 具体的な視覚要素
- composition: ランダム選択される構図スタイル

**トピック別カラースキーム:**
- psychology: calming blue (#2b6cb0)
- education: growth green (#2f855a)
- ai_tools: tech navy blue (#1a365d)

---

## スライド 10: 高品質記事生成の仕組み

### 読者価値を最大化する記事

**品質チェックリスト:**
- 文字数: 4000-5500文字（充実した内容）
- 具体的数値・データ: 最低5箇所
- 各主張に根拠（ソース）を明記
- 7日以内の情報のみ使用
- 参考文献はハイパーリンク形式

**トピック別ライティング指示:**
- psychology: 温かみのある文体、セルフケア方法
- investment: 初心者向け、リスクも説明
- ai_tools: 具体的なツールと活用法

---

## スライド 11: 重要なルール・制約

### システムの品質を担保するルール

**7日以内最新情報限定:**
- 過去7日以内の情報のみ使用
- 日付形式: YYYY年MM月DD日
- タイムゾーン: JST (UTC+9)

**引用元・参考文献必須:**
- 最低5つ以上の信頼できるソース
- ハイパーリンク形式で記載

**デザインガイドライン:**
- 絵文字使用禁止
- AIっぽい表現禁止（「革新的」「画期的」等）

---

## スライド 12: GitHub Actions自動実行

### 完全自動化されたワークフロー

**自動実行スケジュール:**
- 実行時刻: 毎日 JST 5:00
- トピック選択: 曜日別に自動
- リサーチ方法: 日曜のみDeep Research

**手動実行も可能:**
1. GitHub > Actions > Manual Blog Generation
2. Run workflow をクリック
3. パラメータを選択（topic, research_method）

---

## スライド 13: プロジェクト構造

### 整理されたディレクトリ構成

```
if-blog-auto/
├── .github/workflows/    # GitHub Actions
├── docs/                 # Jekyll サイト
│   ├── _posts/           # ブログ記事
│   └── assets/images/    # 記事画像
├── src/
│   ├── agents/           # 8種類のエージェント
│   ├── skills/           # 8種類のスキル
│   ├── lib/              # Gemini API クライアント
│   └── scripts/          # 実行スクリプト
└── output/               # 生成記事（ローカル）
```

---

## スライド 14: 技術スタック

### 使用している技術

| カテゴリ | 技術 |
|---------|------|
| AIモデル | Gemini 3 Pro, Flash, Deep Research, 2.5 Flash image |
| 言語 | Python 3.11+, JavaScript (Node.js 20+) |
| ライブラリ | google-genai>=1.56.0 |
| 検索 | Google Search Tool (Gemini Built-in) |
| 静的サイト | Jekyll (GitHub Pages) |
| CI/CD | GitHub Actions |

---

## スライド 15: まとめと今後の展望

### if(塾) Blog Automation Systemの価値

**実現した自動化:**
- 情報収集から投稿まで完全自動
- 6トピック + 週間総括を毎日生成
- 高品質な画像付き記事

**主な特徴:**
- Multi-Search 3回検索で高品質リサーチ
- トピック別最適化（クエリ、文体、カラー）
- 7日以内の最新情報のみ使用

**公開URL:**
https://takubon0202.github.io/if-blog-auto/

---

*このスライドは2025年12月30日時点の情報に基づいて作成されました。*
