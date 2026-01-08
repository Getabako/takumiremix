# if(塾) Blog Automation System v2.9.0

Gemini API を活用した、最新トレンド情報を自動収集して画像・**スライド動画**付き**高品質ブログ記事（20,000文字以上）**を生成・GitHub Pagesに自動投稿するシステム。

## 最新アップデート（2026年1月8日）

### v2.9.0: Gemini 3 Flash移行 & Remotionレンダリング修正
- **Gemini 3 Flash移行**: `gemini-2.0-flash` → `gemini-3-flash-preview`（思考モードオフ）
- **SlideVideoV3対応**: Marpスライド対応＆タイミング制御の新コンポジション
- **デフォルトコンポジション変更**: `BlogVideo` → `SlideVideoV3`（スライド動画がデフォルト）
- **render.mjs引数順序修正**: Python→Remotion間の引数順序不一致を修正
  - 修正前: `compositionId, propsPath, outputPath`（誤り）
  - 修正後: `compositionId, outputPath, propsPath`（正しい順序）
- **思考モード無効化**: `thinking_config=ThinkingConfig(thinking_level="minimal")`

### v2.8.0: 動画レンダリング修正 & セットアップ簡素化
- **青い画面問題修正**: 最後のスライドがフェードアウトしない（DailyInstagram方式）
- **SlideVideo.tsx完全書き直し**: シンプルで安定したレンダリングロジック
- **セットアップスクリプト追加**: `setup.py`で環境構築を自動化
- **テストスクリプト追加**: `test_full_pipeline.py`で動作確認
- **dotenv対応**: ローカル開発で`.env`ファイルを自動読み込み
- **デバッグログ強化**: 動画生成の各ステップを詳細にログ出力

### v2.7.0: Base64 Data URL方式 & VOICEPEAK TTS統合
- **Base64 Data URL方式**: DailyInstagram参考実装、file://プロトコル問題を完全解決
- **VOICEPEAK TTS統合**: 高品質日本語音声合成（商用可能 6ナレーターセット対応）
- **デュアルTTSシステム**: VOICEPEAK（ローカル優先）+ Gemini TTS（クラウドフォールバック）
- **トピック別ナレーター**: 各トピックに最適な声を自動選択
- **画像・音声のBase64変換**: Remotionへのデータ受け渡しを確実に
- **プロパティ拡張**: `slideImages[]`, `audioDataUrl` props追加

### v2.6.3: 音声検証の緩和
- **最小サイズ制限撤廃**: 短い音声でも有効として扱う
- **WAVヘッダーのみ検証**: サイズではなくフォーマットで判定

### v2.6.2: 音声生成の確実性向上
- **多層音声検証**: PCMデータ、WAVファイル、Remotion前の3段階で検証
- **最低サイズチェック**: PCM 5KB以上、WAV 10KB以上を要求
- **無効ファイル自動削除**: 検証失敗時は無効な音声ファイルを削除
- **render.mjs検証**: Remotion実行前に音声ファイルの存在と形式を確認

### v2.6.1: 動画生成バグ修正
- **スライドタイプ正規化**: Remotionに渡す前にスライドタイプを自動正規化（title/content/ending）
- **画像パス修正**: 複数ソースから画像を収集し、確実にpublic/slides/に配置
- **音声検証強化**: WAVヘッダーを検証して正しいフォーマットを保証
- **デバッグログ追加**: 各ステップの詳細ログで問題を特定しやすく

### v2.6: 動画生成フロー改善 & 安定性向上
- **動画生成フロー整理**: スライド → 音声生成 → 動画レンダリングの明確な4ステップ構成
- **TTS音声修正**: PCM → WAV変換（24kHz, 16bit, mono）で音声が正しく再生
- **30秒動画制限**: 6スライド × 5秒 = 30秒以内に最適化
- **画像アスペクト比**: 16:9（YouTubeサムネイル形式）に統一
- **品質評価97%**: 記事のみ品質評価、動画は評価スキップ
- **動画品質評価削除**: 動画生成時のリトライ・タイムアウトを防止

### v2.5: 2倍品質アップデート
- **記事ボリューム5倍**: 20,000文字以上の充実したコンテンツ（従来の5倍）
- **17セクション構成**: 導入から行動計画まで網羅的に解説
- **読者エンゲージメント強化**: ストーリーテリング、驚きの事実、Q&Aセクション

### v2.0: スライド動画対応
- **スライドベース動画生成**: 6枚のスライド + TTS音声で30秒の解説動画を自動生成
- **品質評価システム**: 97%以上の合格ラインで品質を担保（記事のみ）
- **Marp PDF連携**: スライドをPDF/画像に自動変換
- **Remotion v2.0**: SlideVideo/SlideVideoShortコンポジション追加

## 公開URL

**https://takubon0202.github.io/if-blog-auto/**

---

## 設計方針: Multi-Search（3回検索）メイン + Deep Research 週1回

| 曜日 | リサーチ方法 | 検索回数 | 処理時間 | 備考 |
|------|-------------|----------|---------|------|
| **月〜土** | Multi-Search | 3回 | 約10秒 | デフォルト・推奨 |
| **日曜日** | Deep Research API | 1回 | 約5分 | 週1回の深層調査 |
| **フォールバック** | Multi-Search | 3回 | 約10秒 | Deep Research失敗時 |
| **手動実行** | 選択可能 | - | - | GitHub Actionsで選択 |

**設計理由**:
- Deep ResearchはRPM 1/分の厳しいレート制限があるため、週1回（日曜日）のみ使用
- Multi-Search（3回検索）はDeep Research簡易版として、3つの視点から情報を収集し高品質なリサーチを実現
- Deep Research失敗時は自動的にMulti-Searchにフォールバック

---

## システムフロー（7ステップ）

### 予想実行時間

| ステップ | 処理内容 | 予想時間 |
|---------|---------|---------|
| Step 1 | 情報収集（Multi-Search） | 約10-30秒 |
| Step 1 | 情報収集（Deep Research・日曜のみ） | 約3-5分 |
| Step 2 | ブログ記事生成 | 約1-2分 |
| Step 3 | 画像生成（16:9） | 約30秒-1分 |
| Step 4 | スライド動画生成 | 約3-5分 |
| Step 5 | SEO最適化 | 約5-10秒 |
| Step 6 | 品質レビュー | 約10-20秒 |
| Step 7 | GitHub Pages投稿 | 約30秒-1分 |
| **合計** | **通常（月〜土）** | **約8-12分** |
| **合計** | **週間総括（日曜）** | **約12-18分** |

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions 開始                          │
│  ubuntu-latest / Python 3.11 / Node.js 20                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 情報収集                                    [約10-30秒] │
│  ├── 月〜土: Google Search 3回検索 (gemini-3-pro-preview)       │
│  └── 日曜: Deep Research API (週間総括)             [約3-5分]   │
│  出力: research_data (sources, topic_info)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: ブログ記事生成（5倍品質版）                  [約1-2分]  │
│  モデル: gemini-3-pro-preview                                   │
│  出力: article (title, content, word_count)                     │
│  目標: 20,000文字以上（17セクション構成）                       │
│  特徴: ストーリーテリング、驚きの事実、Q&A、行動計画            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 画像生成                                   [約30秒-1分] │
│  モデル: gemini-2.5-flash-image                                 │
│  出力: hero.png (アイキャッチ画像)                              │
│  特徴: アニメスタイル、**16:9アスペクト比**、キャラクター多様性 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: スライド動画生成（4サブステップ）           [約3-5分]   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4-1. スライド生成                           [約1-2分]    │   │
│  │      Gemini 3 Pro → 6枚のスライド構成                    │   │
│  │      Gemini 2.5 Flash image → 各スライド画像             │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4-2. 音声生成（スライド内容を元に）         [約30秒]     │   │
│  │      【ローカル】VOICEPEAK TTS → narration.wav（優先）   │   │
│  │      【クラウド】Gemini TTS（フォールバック）            │   │
│  │      形式: WAV (24kHz/44.1kHz, 16bit, mono)              │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4-3. ファイル配置                           [数秒]       │   │
│  │      スライド画像 → public/slides/                       │   │
│  │      音声ファイル → public/narration.wav                 │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4-4. Remotion レンダリング                  [約2-3分]    │   │
│  │      【v2.7.0】Base64 Data URL方式                       │   │
│  │      - 画像: PNG → data:image/png;base64,...             │   │
│  │      - 音声: WAV → data:audio/wav;base64,...             │   │
│  │      SlideVideo → 1920x1080 MP4                          │   │
│  │      6スライド × 5秒 = **30秒動画**（最大）              │   │
│  │      **品質評価なし** → 即座に成功                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: SEO最適化                                  [約5-10秒]   │
│  モデル: gemini-3-flash-preview（思考オフ）                     │
│  出力: title, description, tags, categories                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 品質レビュー（記事のみ・最大3回リトライ）  [約10-20秒]  │
│  ├── 品質スコア**97%以上**で合格                               │
│  ├── 動画は品質評価をスキップ                                  │
│  └── 不合格時: 記事の修正・再生成                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: GitHub Pages 投稿                         [約30秒-1分]  │
│  ├── docs/_posts/ に記事保存                                   │
│  ├── docs/assets/images/ に画像保存                            │
│  ├── docs/assets/videos/ に動画保存                            │
│  ├── Git commit & push                                         │
│  └── Jekyll ビルド → 公開                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    公開完了                                      │
│  URL: https://takubon0202.github.io/if-blog-auto/               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 使用AIモデル・ツール

| ステップ | モデル/ツール | 曜日/タイミング | 応答時間 |
|----------|--------------|----------------|----------|
| 情報収集（メイン） | `gemini-3-pro-preview` + Multi-Search 3回 | 月〜土 | 約10-30秒 |
| 情報収集（深層） | `deep-research-pro-preview-12-2025` | 日曜のみ | 約3-5分 |
| 記事生成 | `gemini-3-pro-preview` | 全曜日 | 約1-2分 |
| 画像生成 | `gemini-2.5-flash-image` (16:9) | 全曜日 | 約30秒-1分 |
| スライド生成 | `gemini-3-pro-preview` + `gemini-2.5-flash-image` | 全曜日 | 約1-2分 |
| ナレーション | VOICEPEAK（ローカル優先）/ Gemini TTS（フォールバック） | 全曜日 | 約30秒 |
| 動画レンダリング | Remotion 4.0 SlideVideoV3（デフォルト） | 全曜日 | 約2-3分 |
| SEO最適化 | `gemini-3-flash-preview`（思考オフ） | 全曜日 | 約5-10秒 |
| 品質レビュー | `gemini-3-flash-preview`（思考オフ） | 全曜日 | 約10-20秒 |

### 処理時間の目安（合計）

| モード | 処理時間 | 備考 |
|-------|----------|------|
| 通常（月〜土） | **約8〜12分** | Multi-Search使用 |
| 週間総括（日曜） | **約12〜18分** | Deep Research使用 |
| 動画スキップ時 | 約5〜8分 | `--skip-video`オプション |

### 重要な変更点（v2.6）

| 項目 | 旧仕様 | 新仕様 |
|------|--------|--------|
| 動画長 | 60秒（12スライド） | **30秒（6スライド）** |
| 画像比率 | 1:1（正方形） | **16:9（YouTubeサムネ）** |
| TTS形式 | PCM（生データ） | **WAV（24kHz, 16bit, mono）** |
| 品質評価 | 95%（動画含む） | **97%（記事のみ）** |
| 動画リトライ | 最大3回 | **なし（1回のみ）** |

---

## クイックスタート

### 前提条件
- Python 3.11以上
- Git
- Node.js 20以上（動画生成に必要）
- Google AI API Key（[Google AI Studio](https://aistudio.google.com/)から取得）
- VOICEPEAK（オプション：高品質音声用）

### 1. 簡単セットアップ（推奨）

```bash
# リポジトリをクローン
git clone https://github.com/takubon0202/if-blog-auto.git
cd if-blog-auto

# Python仮想環境を作成・有効化
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 依存関係をインストール
pip install -r requirements.txt

# 対話式セットアップを実行（推奨）
python setup.py
```

`setup.py`は以下を自動で行います:
- python-dotenvのインストール確認
- `.env`ファイルの作成（APIキー入力）
- VOICEPEAKの検出
- Node.js / Remotionの確認・インストール

### 2. 手動セットアップ（上級者向け）

```bash
# 環境変数を設定
copy .env.example .env         # Windows
# cp .env.example .env         # Mac/Linux
```

`.env`ファイルを編集してAPIキーを設定：
```
GOOGLE_AI_API_KEY=your_actual_api_key_here

# オプション: VOICEPEAKのパスを指定
VOICEPEAK_PATH=C:\Program Files\VOICEPEAK\voicepeak.exe
```

### 3. 動作確認テスト

```bash
# 環境確認テスト（動画生成なし）
python src/scripts/test_full_pipeline.py --skip-video

# 音声テスト付き
python src/scripts/test_full_pipeline.py --with-audio

# フルテスト（動画生成含む）
python src/scripts/test_full_pipeline.py --with-audio
```

テスト結果で各コンポーネントの状態を確認できます:
- `[OK]` = 正常
- `[NG]` = 要設定/要インストール
- `[SKIP]` = スキップ

### 4. 記事を生成

```bash
cd src/scripts

# AIツールの記事を生成して投稿（Google Search使用）
python main.py --topic ai_tools --publish

# Deep Researchを使用して生成
python main.py --topic psychology --use-deep-research --publish

# ドライラン（投稿せずにテスト）
python main.py --topic education --dry-run

# 画像生成をスキップ
python main.py --topic startup --skip-images --publish

# 動画生成をスキップ
python main.py --topic education --skip-video --publish
```

### 5. コマンドラインオプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--topic` | トピックID（必須） | - |
| `--use-deep-research` | Deep Research APIを使用 | False（Google Search） |
| `--use-slide-video` | スライドベース動画を生成（推奨） | True |
| `--slide-count` | 目標スライド枚数（**最大6**） | **6** |
| `--slide-duration` | 各スライドの表示時間（秒） | 5 |
| `--skip-images` | 画像生成をスキップ | False |
| `--skip-video` | 動画生成をスキップ | False |
| `--dry-run` | ドライラン（投稿なし） | False |
| `--publish` | GitHub Pagesに投稿 | True |

**注意**: `--slide-count`は最大6に制限されます（30秒動画制限のため）。

---

## GitHub Actions 自動実行

### 自動実行スケジュール

| 項目 | 設定 |
|------|------|
| 実行時刻 | 毎日 JST 5:00（UTC 20:00） |
| トピック選択 | 曜日別に自動選択 |
| リサーチ方法 | 日曜日のみDeep Research、他はGoogle Search |
| タイムゾーン | Asia/Tokyo（JST） |
| タイムアウト | 45分（動画生成対応） |

### 手動実行

1. GitHub > Actions > **Manual Blog Generation**
2. **Run workflow** をクリック
3. パラメータを選択：
   - **topic**: トピックを選択
   - **research_method**: `google_search` または `deep_research`
   - **skip_images**: 画像生成をスキップするか
   - **skip_video**: 動画生成をスキップするか

### GitHub Actionsでの動画生成

GitHub Actionsでは自動的に以下の処理が行われます：

1. **Node.js 20のセットアップ**
2. **Remotion依存関係のインストール** (`npm ci`)
3. **動画のレンダリング** (標準30秒 + ショート15秒)
4. **成果物のアップロード** (30日間保持)

---

## サブエージェント構成

| エージェント | 役割 | モデル/ツール | 使用タイミング |
|-------------|------|--------------|--------------|
| `google-search-agent` | Multi-Search情報収集（メイン） | Gemini 3 Pro + 3回検索 | 月〜土・フォールバック |
| `deep-research-agent` | 深層調査 | Deep Research API | 日曜のみ |
| `writing-agent` | 20,000文字以上の高品質記事執筆（v2.0） | Gemini 3 Pro | 全曜日 |
| `engagement-agent` | 読者エンゲージメント強化（NEW） | Gemini 3 Pro | 全曜日 |
| `image-agent` | アイキャッチ画像生成（スマートプロンプト） | Gemini 2.5 Flash image + 記事分析 | 全曜日 |
| `slide-agent` | スライド生成（12枚構成） | Gemini 3 Pro + 2.5 Flash image | 全曜日 |
| `video-agent` | スライド動画生成 | Remotion 4.0 SlideVideoV3（デフォルト） | 全曜日 |
| `quality-agent` | 品質評価（95%合格ライン・20,000文字チェック） | 独自評価システム | 全曜日 |
| `seo-agent` | SEOメタデータ最適化 | Gemini 3 Flash（思考オフ） | 全曜日 |
| `review-agent` | 品質チェック・ファクトチェック | Gemini 3 Flash（思考オフ） | 全曜日 |
| `site-builder-agent` | Jekyllサイト構造管理 | - | 必要時 |
| `blog-publisher-agent` | GitHub Pages投稿処理 | - | 全曜日 |

---

## スキル構成

| スキル | 目的 | 使用API/ツール |
|--------|------|---------------|
| `gemini-research` | 7日以内情報収集（Multi-Search 3回/Deep Research） | Gemini API |
| `gemini-content` | 20,000文字以上の引用元付きコンテンツ生成 | Gemini 3 Pro |
| `storytelling-skill` | ストーリーテリング技術（NEW） | Gemini 3 Pro |
| `gemini-3-flash` | SEO/レビュー高速処理（思考オフ） | Gemini 3 Flash |
| `image-generation` | ブログ用画像生成（スマートプロンプト対応） | Gemini 2.5 Flash image |
| `slide-generation` | スライド生成・PDF変換・画像変換 | Gemini + Marp CLI |
| `remotion-video` | スライド動画生成 | Remotion 4.0 SlideVideoV3（デフォルト） |
| `quality-evaluation` | 品質評価（95%合格ライン・20,000文字チェック） | 独自評価システム |
| `timezone` | JST日時処理 | Python datetime |
| `github-pages` | GitHub Pages操作 | Git API |
| `jekyll-content` | Jekyll形式コンテンツ生成 | - |
| `cms-integration` | CMS連携 | - |

---

## 対象トピック（6種類 + 週間総括）

| ID | トピック | 曜日 | リサーチ方法 | キーワード例 |
|----|----------|------|-------------|-------------|
| `psychology` | 心理学・メンタルヘルス | 月曜 | Multi-Search | 心理学、カウンセリング、ストレス |
| `education` | 教育・学習科学 | 火曜 | Multi-Search | 教育、EdTech、学習法 |
| `startup` | 起業家育成・スタートアップ | 水曜 | Multi-Search | 起業、スタートアップ、経営 |
| `investment` | 投資教育・金融リテラシー | 木曜 | Multi-Search | 投資、NISA、資産形成 |
| `ai_tools` | AIツール・技術動向 | 金曜 | Multi-Search | AI、ChatGPT、Gemini |
| `inclusive_education` | インクルーシブ教育・多様な学び | 土曜 | Multi-Search | 不登校、発達障害、フリースクール |
| `weekly_summary` | **週間トレンド総括** | **日曜** | **Deep Research** | 6分野横断、週間まとめ |

### 週間総括（日曜日）

日曜日は6つのトピックを横断した「週間トレンド総括」記事をDeep Researchで生成します：

1. **今週のハイライト** - 全体の要約（3〜5行）
2. **各分野の注目ニュース** - 分野ごとに1〜2件
3. **分野横断的なトレンド分析**
4. **来週の注目ポイント**

---

## 重要なルール・制約

### 7日以内最新情報限定ルール

本システムは**必ず7日以内の最新情報のみ**を使用します。

| 項目 | 設定 |
|------|------|
| 情報の鮮度 | 過去7日以内のみ |
| 日付形式 | YYYY年MM月DD日 |
| タイムゾーン | 日本標準時 (JST = UTC+9) |
| 最低ソース数 | 5つ以上 |

### 引用元・参考文献必須ルール

すべての記事末尾に**引用元・参考文献**を自動記載します。

```markdown
---

## 参考文献・引用元

<div class="sources-section">

この記事は以下の情報源を参考に作成されました：

- [ソースタイトル1](https://example.com/article1)
- [ソースタイトル2](https://example.com/article2)
- [ソースタイトル3](https://example.com/article3)

</div>

---

*この記事はAIによって生成されました。*
```

### デザインガイドライン

| 禁止事項 | 推奨事項 |
|---------|---------|
| 絵文字の使用 | クリーンでミニマルなデザイン |
| 紫色系の使用 | Deep Navy (#1a1a2e) 基調 |
| AIっぽい表現（「革新的」「画期的」等） | 専門的だが親しみやすいトーン |

### 画像生成（スマートプロンプト機能）

記事タイトルを分析して、内容に合った具体的で多様な画像を自動生成します。

| 分析項目 | 説明 |
|---------|------|
| main_subject | メインの視覚的対象（例: "glowing neural network"） |
| visual_metaphor | 記事の核心を表すメタファー |
| mood | 感情的トーン（明るい、落ち着いた等） |
| key_elements | 含めるべき具体的な視覚要素 |
| composition | ランダム選択される構図スタイル |

**トピック別カラースキーム（自動適用）**:
- `psychology`: calming blue (#2b6cb0)
- `education`: growth green (#2f855a)
- `startup`: energetic orange (#c05621)
- `investment`: trustworthy gold-brown (#744210)
- `ai_tools`: tech navy blue (#1a365d)
- `inclusive_education`: supportive teal (#285e61)
- `weekly_summary`: insightful indigo (#553c9a)

---

## プロジェクト構造

```
if-blog-auto/
├── .github/
│   └── workflows/
│       ├── daily-blog-generation.yml  # 日次自動生成
│       ├── manual-trigger.yml         # 手動実行
│       └── deploy-pages.yml           # ページデプロイ
│
├── docs/                    # GitHub Pages サイト (Jekyll)
│   ├── _config.yml          # Jekyll設定 (timezone: Asia/Tokyo)
│   ├── _layouts/            # レイアウトテンプレート
│   ├── _posts/              # ブログ記事（自動投稿先）
│   ├── assets/
│   │   ├── css/style.css
│   │   └── images/          # 記事画像
│   ├── index.md
│   ├── about.md
│   └── categories.md
│
├── remotion/                # 動画生成（Remotion v2.0）
│   ├── package.json         # Remotion依存関係
│   ├── remotion.config.ts   # Remotion設定
│   ├── render.mjs           # レンダリングスクリプト
│   ├── tsconfig.json        # TypeScript設定
│   ├── README.md            # Remotionドキュメント
│   └── src/
│       ├── index.tsx        # エントリーポイント
│       ├── Root.tsx         # コンポジション定義
│       └── compositions/
│           ├── BlogVideo.tsx      # ブログ動画コンポーネント
│           ├── SlideVideo.tsx     # スライド動画コンポーネント
│           └── SlideVideoV3.tsx   # Marp対応スライド動画（v2.9.0・デフォルト）
│
├── src/
│   ├── agents/              # サブエージェント定義（12種類）
│   │   ├── google-search-agent.md   # メイン（月〜土）
│   │   ├── deep-research-agent.md   # 日曜のみ
│   │   ├── writing-agent.md         # 記事執筆（v2.0：20,000文字対応）
│   │   ├── engagement-agent.md      # エンゲージメント強化（NEW v2.5）
│   │   ├── image-agent.md
│   │   ├── slide-agent.md           # スライド生成
│   │   ├── video-agent.md           # 動画生成
│   │   ├── quality-agent.md         # 品質評価（20,000文字チェック）
│   │   ├── seo-agent.md
│   │   ├── review-agent.md
│   │   ├── site-builder-agent.md
│   │   └── blog-publisher-agent.md
│   │
│   ├── skills/              # スキル定義（12種類）
│   │   ├── gemini-research.md
│   │   ├── gemini-content.md
│   │   ├── storytelling-skill.md    # ストーリーテリング（NEW v2.5）
│   │   ├── gemini-3-flash.md
│   │   ├── image-generation.md
│   │   ├── slide-generation.md      # スライド生成
│   │   ├── remotion-video.md        # 動画生成
│   │   ├── quality-evaluation.md    # 品質評価
│   │   ├── timezone.md
│   │   ├── github-pages.md
│   │   ├── jekyll-content.md
│   │   └── cms-integration.md
│   │
│   ├── config/
│   │   ├── topics.json      # トピック設定
│   │   └── settings.json    # システム設定
│   │
│   ├── lib/
│   │   ├── gemini_client.py   # Gemini APIクライアント
│   │   ├── voicepeak_client.py # VOICEPEAK TTSクライアント（v2.7.0）
│   │   └── timezone.py        # タイムゾーンユーティリティ (JST)
│   │
│   ├── scripts/
│   │   ├── main.py              # メインスクリプト
│   │   ├── research.py          # リサーチ実行
│   │   ├── generate_content.py  # 記事生成
│   │   ├── generate_image.py    # 画像生成
│   │   ├── generate_slides.py   # スライド生成（NEW）
│   │   ├── generate_slide_video.py  # スライド動画統合（NEW）
│   │   ├── generate_video.py    # 動画生成
│   │   ├── quality_evaluator.py # 品質評価（NEW）
│   │   ├── seo_optimize.py      # SEO最適化
│   │   ├── review.py            # 品質レビュー
│   │   └── publish.py           # GitHub Pages投稿
│   │
│   └── templates/
│       ├── blog-post.md
│       └── meta-template.json
│
├── output/                  # 生成された記事（ローカル保存）
│   ├── posts/               # Markdown記事
│   ├── images/              # 生成画像
│   ├── slides/              # スライド画像（NEW）
│   └── videos/              # 生成動画
│
├── CLAUDE.md                # プロジェクトルール
├── requirements.txt         # Python依存関係
└── package.json             # Node.js依存関係
```

---

## GeminiClient API リファレンス

### 主要メソッド

```python
from lib.gemini_client import GeminiClient

client = GeminiClient()

# コンテンツ生成
result = await client.generate_content(
    prompt="プロンプト",
    model="gemini-3-pro-preview",
    enable_search=False,
    thinking_mode=True
)

# Google Search + 生成
result = await client.search_and_generate(
    query="検索クエリ",
    generation_prompt="生成プロンプト"
)

# Multi-Search（3回検索、メイン）
result = await client.multi_search_research(
    topic="トピック名",
    topic_info=topic_info,
    date_range={"start": "2025年12月22日", "end": "2025年12月29日"},
    search_count=3  # デフォルト: 3回
)

# Deep Research（日曜日用）
result = await client.deep_research(
    query="調査クエリ",
    timeout_seconds=1800
)

# 画像生成（スマートプロンプト対応）
result = await client.generate_blog_image(
    title="記事タイトル",
    summary="記事概要",
    topic_id="ai_tools",  # トピック別カラースキーム自動適用
    use_smart_prompt=True  # 記事分析を有効化（デフォルト）
)
```

### モデル定数

```python
GeminiClient.MODEL_PRO = "gemini-3-pro-preview"
GeminiClient.MODEL_FLASH = "gemini-3-flash-preview"  # v2.9.0で更新（思考モードオフ）
GeminiClient.MODEL_FLASH_3 = "gemini-3-flash-preview"
GeminiClient.MODEL_IMAGE = "gemini-2.5-flash-image"
GeminiClient.AGENT_DEEP_RESEARCH = "deep-research-pro-preview-12-2025"
```

---

## タイムゾーンユーティリティ

```python
from lib.timezone import (
    now_jst,              # 現在の日本時間
    format_date,          # 日付フォーマット
    format_datetime_jst,  # Jekyll用日時
    get_weekday_name_jst  # 曜日名取得
)

# 使用例
today = now_jst()
date_str = format_date()  # "2025-12-29"
jekyll_date = format_datetime_jst()  # "2025-12-29 16:50:44 +0900"
weekday = get_weekday_name_jst()  # "sunday"
```

---

## トラブルシューティング

### Deep Research 400エラー

```
google.genai._interactions.BadRequestError: Error code: 400 - {'error': {'message': 'Request contains an invalid argument.'}}
```

**考えられる原因と解決策**:

1. **レート制限超過（最も多い原因）**
   - 原因: Deep ResearchのRPMは**1リクエスト/分**と非常に厳しい
   - 解決: 1分以上間隔を空けて再実行、または翌日に再試行
   - 注意: 月〜土はGoogle Searchを使用すれば回避可能

2. **課金設定がない**
   - 原因: Deep Research APIは**有料プラン専用**
   - 解決: [Google AI Studio](https://aistudio.google.com/) で Billing を有効化
   - 注意: 課金なしでも自動的にGoogle Searchにフォールバック

3. **ライブラリバージョンが古い**
   - 原因: `google-genai`が古いバージョン
   - 解決: `pip install google-genai>=1.56.0`

### 画像生成エラー

```
Error: Image generation failed
```

- **原因**: `response_modalities=["IMAGE"]`設定が不足
- **解決**: 最新のコードでは自動設定されています
- **回避**: `--skip-images`オプションで画像生成をスキップ

### 動画生成エラー（v2.8.0で修正）

#### 動画が途中で青くなる（v2.8.0修正）
```
Video turns blue mid-way through playback
```

- **原因**: 最後のスライドがフェードアウトして、背景色のみが表示されていた
- **解決**: v2.8.0で最後のスライドはフェードアウトしないように修正（DailyInstagram方式）
- **確認**: SlideVideo.tsxの`isLast`プロパティで最後のスライドを判定

#### 動画が途中で真っ暗になる
```
Video goes black after a few slides
```

- **原因**: スライド画像が正しくコピーされていない
- **解決**: v2.6.1で画像パス処理を改善。複数のソースから画像を収集
- **確認**: ログで「画像発見」「コピー」メッセージを確認

#### 動画がデフォルトコンテンツを表示
```
Video shows "AIツールの最新動向2025" instead of actual content
```

- **原因**: スライドデータ形式がRemotionの期待と不一致
- **解決**: v2.6.1でスライドタイプを自動正規化（title/content/ending）
- **確認**: ログで「スライドデータを正規化中」を確認

#### render.mjs引数エラー（v2.9.0で修正）
```
Video renders with wrong output path or props not loaded
```

- **原因**: Python側で引数順序が誤っていた（`propsPath, outputPath` の順番で渡していた）
- **解決**: v2.9.0で引数順序を修正
  - 正しい順序: `compositionId, outputPath, propsPath`
- **影響ファイル**: `generate_video_v2.py`, `generate_video_v3.py`
- **確認**: ログで「Rendering: node render.mjs SlideVideoV3 output.mp4 props.json」の順序を確認

#### 音声が再生されない
```
Video has no audio
```

- **原因**: WAVファイルが正しく生成/保存されていない、またはTTSが未設定
- **解決**: 以下のいずれかを設定
  1. `.env`に`GOOGLE_AI_API_KEY`を設定（Gemini TTS使用）
  2. VOICEPEAKをインストール（高品質日本語音声）
- **確認**: `python src/scripts/test_full_pipeline.py --with-audio`で音声生成をテスト
- **注意**: TTS未設定時は無音動画が生成される（正常動作）

### セットアップ関連エラー

#### test_full_pipeline.pyでAPI キー未設定
```
[NG] GOOGLE_AI_API_KEY: 未設定
```

- **解決**: `python setup.py`を実行してAPIキーを設定、または手動で`.env`ファイルを作成
- **取得方法**: [Google AI Studio](https://aistudio.google.com/app/apikey)からAPIキーを取得

#### VOICEPEAK未インストール
```
[NG] VOICEPEAK: 未インストール
```

- **解決**: VOICEPEAKダウンローダーを実行してインストール
- **場所**: `voicepeak_6nare_dl\VOICEPEAK...\Windows\voicepeak-downloader.exe`
- **代替**: Gemini TTSを使用（APIキー設定で自動的に使用）

#### Remotion未インストール
```
[NG] Remotion: 未インストール
```

- **解決**: `cd remotion && npm install`を実行
- **注意**: Node.js 20以上が必要

### フォールバック動作

Deep Research失敗時は自動的にMulti-Search（3回検索）にフォールバックします：

```
┌─────────────────────────┐
│ Deep Research API 呼び出し│
└────────────┬────────────┘
             │
      失敗？ ─┴─ 成功？
      │           │
   ┌──▼──────────┐  │
   │ エラーログ   │  └→ 深層調査結果を使用
   │ 出力        │
   └──┬──────────┘
      │
   ┌──▼──────────────────────┐
   │ Multi-Search（3回検索）  │
   │ にフォールバック        │
   │ ・最新ニュース検索      │
   │ ・専門家見解検索        │
   │ ・事例・統計検索        │
   └──────────────────────────┘
```

### Multi-Search（3回検索）の仕組み

3つの異なる視点から検索を行い、情報を統合します：

| 検索 | 視点 | 目的 |
|------|------|------|
| 1回目 | 最新ニュース・公式発表 | 直近の重要なニュースや発表を収集 |
| 2回目 | 専門家の見解・研究データ | 学術的知見やエビデンスを収集 |
| 3回目 | 実践事例・統計情報 | 具体的な事例と数値データを収集 |

#### トピック別専門クエリ（2025年12月30日改善）

各トピックに最適化された検索クエリを使用することで、より関連性の高い情報を収集します：

| トピック | 専門クエリ例 |
|----------|-------------|
| psychology | 心理学 メンタルヘルス 最新研究 論文発表 |
| education | 教育改革 学習指導要領 文部科学省 発表 |
| startup | スタートアップ 資金調達 IPO M&A ニュース |
| investment | 新NISA iDeCo 制度変更 金融庁 発表 |
| ai_tools | 生成AI ChatGPT Claude Gemini 新機能 アップデート |
| inclusive_education | 不登校 支援制度 フリースクール 教育機会確保法 |

これにより、Deep Research簡易版として高品質な情報収集を実現します。

### 高品質記事生成（2025年12月30日改善）

記事生成の品質向上のため、以下の機能を実装：

1. **トピック別ライティング指示**
   - 各トピックに最適化された執筆ガイドライン
   - 読者層に合わせた文体・トーンの調整

2. **読者価値最大化**
   - 問題解決型アプローチ
   - 具体的なデータ・事例の必須化
   - 実践可能なアクションポイントの提示

3. **品質チェックリスト（5倍品質版）**
   - 文字数: **20,000文字以上**（従来の5倍）
   - H2見出し: 12-18個、H3サブ見出し: 40個以上
   - 成功事例5つ以上、失敗事例3つ以上
   - 具体的数値・データ最低25箇所
   - 読者への問いかけ5箇所以上
   - 驚きの事実「知っていましたか?」3つ以上
   - Q&Aセクションに10個以上の質問と回答
   - 7日以内の情報のみ使用
   - 参考文献は必ず**ハイパーリンク形式**で10個以上記載

---

## 動画生成（Remotion v2.7.0）

ブログ記事の内容から自動でスライド解説動画を生成します。

### 重要: 動画生成フロー（v2.7.0更新）

**v2.7.0の主な改善点:**
- **Base64 Data URL方式**: ファイルパスではなくBase64エンコードでデータを渡す
- **VOICEPEAK TTS統合**: 高品質日本語音声（ローカル優先）
- **デュアルTTSシステム**: VOICEPEAK + Gemini TTSのフォールバック構成

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: スライド生成                           [約1-2分]  │
│  ├── 記事からスライド構成を生成（Gemini 3 Pro）           │
│  └── 各スライドの画像を生成（Gemini 2.5 Flash image）     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: 音声生成（スライド内容を元に）         [約30秒]   │
│  ├── スライド内容からナレーションスクリプトを生成         │
│  └── Gemini 2.5 Flash TTSで音声生成                        │
│      形式: WAV (24kHz, 16bit, mono)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: ファイル配置                           [数秒]     │
│  ├── スライド画像 → public/slides/                        │
│  └── 音声ファイル → public/narration.wav                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: 動画レンダリング（Remotion）           [約2-3分]  │
│  ├── スライド画像と音声を統合                             │
│  └── MP4動画を出力（1920x1080）                           │
│      **品質評価なし** → 即座に成功                        │
└─────────────────────────────────────────────────────────────┘
```

### コンポジション一覧

| ID | 説明 | 解像度 | 長さ | 用途 |
|----|------|--------|------|------|
| `SlideVideoV3` | **Marpスライド対応動画（デフォルト・推奨）** | 1920x1080 | 可変（タイミング制御） | YouTube、ブログ埋め込み |
| `SlideVideo` | スライドベース動画 | 1920x1080 | **30秒（最大）** | YouTube、ブログ埋め込み |
| `SlideVideoShort` | スライドショート | 1080x1920 | 15秒（可変） | Shorts/Reels |
| `BlogVideo` | 従来の概要動画 | 1920x1080 | 30秒 | ブログ埋め込み |
| `BlogVideoShort` | 従来のショート | 1080x1920 | 15秒 | TikTok |

**v2.9.0変更**: デフォルトのコンポジションが `BlogVideo` から `SlideVideoV3` に変更されました。

### スライド動画のシーン構成（v2.6更新）

```
6スライド × 5秒 = 30秒動画（最大）

Slide 1: タイトルスライド
  - メインタイトル + サブタイトル
  - Ken Burnsエフェクト（ズーム + パン）

Slide 2-5: コンテンツスライド
  - 見出し + 箇条書きポイント
  - 背景画像（Gemini 2.5 Flash image生成）
  - スタガー表示アニメーション
  - プログレスバー

Slide 6: エンディングスライド
  - ブログ名「if(塾) Blog」
  - CTA「ブログで詳しく読む」

+ TTS音声（デュアルTTSシステム）
  【ローカル優先】VOICEPEAK 商用可能 6ナレーターセット
  【クラウド】Gemini 2.5 Flash TTS（フォールバック）
  形式: WAV (44.1kHz/24kHz, 16bit, mono)
```

### VOICEPEAK TTS システム（v2.7.0新機能）

ローカル環境ではVOICEPEAKを優先使用し、高品質な日本語音声を生成します。

#### ナレーター設定

| ID | ナレーター名 | 特徴 |
|----|-------------|------|
| `female1` | Japanese Female 1 | 落ち着いた女性の声（デフォルト） |
| `female2` | Japanese Female 2 | 優しい女性の声 |
| `female3` | Japanese Female 3 | 明るい女性の声 |
| `male1` | Japanese Male 1 | エネルギッシュな男性の声 |
| `male2` | Japanese Male 2 | 信頼感のある男性の声 |
| `male3` | Japanese Male 3 | 落ち着いた男性の声 |

#### トピック別ナレーター自動選択

| トピック | 使用ナレーター | 理由 |
|---------|---------------|------|
| psychology | female1 | 落ち着いた声で安心感を演出 |
| education | female1 | 教育的な場面に適した声 |
| startup | male1 | エネルギッシュな雰囲気 |
| investment | male2 | 信頼感のある声 |
| ai_tools | male1 | テクノロジー系に適した声 |
| inclusive_education | female2 | 優しく寄り添う声 |
| weekly_summary | female1 | 落ち着いた解説向き |

#### VOICEPEAK インストールパス

```
# デフォルト検索パス（自動検出）
C:\Program Files\VOICEPEAK\voicepeak.exe
C:\Program Files (x86)\VOICEPEAK\voicepeak.exe
C:\Users\琢己の自作PC\Downloads\voicepeak_6nare_dl\VOICEPEAK 商用可能 6ナレーターセット ダウンロード版\voicepeak.exe

# 環境変数で設定（優先）
VOICEPEAK_PATH=C:\path\to\voicepeak.exe
```

#### フォールバック動作

```
┌─────────────────────────────────────────┐
│ VOICEPEAK で音声生成を試行              │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────▼─────────┐
        │   VOICEPEAKが     │
        │   利用可能？       │
        └─────────┬─────────┘
                  │
       ┌──────────┴──────────┐
       │                     │
   ┌───▼───┐            ┌────▼────┐
   │ 成功  │            │ 失敗/   │
   │       │            │ 未インストール │
   └───┬───┘            └────┬────┘
       │                     │
       │              ┌──────▼──────────────┐
       │              │ Gemini 2.5 Flash TTS│
       │              │ にフォールバック     │
       │              └──────┬──────────────┘
       │                     │
   ┌───▼─────────────────────▼───┐
   │      WAV音声を出力          │
   │  tts_source: "voicepeak"    │
   │  または "gemini_tts"        │
   └─────────────────────────────┘
```

### 従来動画のシーン構成

```
Scene 1: タイトルシーン（6秒）
  - トピックラベル表示（アニメーション付き）
  - メインタイトル（フェードイン + スライドアップ）

Scene 2: サマリーシーン（5秒）
  - 記事要約をシンプルに表示
  - カラーアクセント付き

Scene 3-5: ポイントシーン（各4秒 × 3ポイント = 12秒）
  - 番号アイコン（スケールアニメーション）
  - ポイントテキスト（スライドイン）

Scene 6: エンディング（5秒）
  - ブログ名/著者名
  - 日付
  - CTA「ブログで詳しく読む」
```

### トピック別カラースキーム（画像と統一）

動画も画像と同じカラースキームを使用：

| トピックID | Primary | Accent |
|-----------|---------|--------|
| `psychology` | #2b6cb0 | #4299e1 |
| `education` | #2f855a | #48bb78 |
| `startup` | #c05621 | #ed8936 |
| `investment` | #744210 | #d69e2e |
| `ai_tools` | #1a365d | #3182ce |
| `inclusive_education` | #285e61 | #38b2ac |
| `weekly_summary` | #553c9a | #805ad5 |

### 動画生成API

```python
from scripts.generate_video import generate_video

result = await generate_video(
    article={
        "title": "記事タイトル",
        "summary": "記事要約",
        "points": ["ポイント1", "ポイント2", "ポイント3"],
        "topic_id": "ai_tools"
    },
    generate_short=True  # ショート動画も生成
)
```

### 依存関係

動画生成にはNode.js 20+が必要です：

```bash
cd remotion
npm install
```

---

## 品質評価システム（97%合格ライン・記事のみ評価）

**記事のみ**の品質を自動評価し、97%以上で合格とします。
**動画は品質評価をスキップ**します（タイムアウト防止のため）。

### 評価基準（v2.6更新）

| 項目 | 基準 | 重み | 対象 |
|-----|------|------|------|
| 記事文字数 | **20,000文字以上** | 10 | 記事 |
| 記事構成 | 12セクション以上 | 10 | 記事 |
| 情報ソース | 10個以上 | 8 | 記事 |
| 読みやすさ | 見出し・箇条書き | 8 | 記事 |
| エンゲージメント | 問いかけ・驚き・ストーリー | 4 | 記事 |
| 絵文字禁止 | 絵文字なし | 4 | 記事 |
| SEOスコア | 80点以上 | 6 | 記事 |
| ~~スライド枚数~~ | ~~10〜15枚~~ | ~~5~~ | ~~廃止~~ |
| ~~動画+音声~~ | ~~TTS音声あり~~ | ~~5~~ | ~~廃止~~ |

### 重要な変更（v2.6）

- **品質評価は記事のみ**: 動画生成時の品質評価を削除
- **閾値引き上げ**: 95% → **97%**
- **動画リトライなし**: 動画生成は1回のみ実行（タイムアウト防止）

### 自動リトライ（記事のみ）

品質が97%未満の場合、最大3回まで記事の自動リトライを行います：

1. 文字数不足 → 記事を拡充して再生成
2. 構成不足 → セクションを追加して再生成
3. 情報ソース不足 → ソースを追加して再生成

### 使用方法

```python
from scripts.quality_evaluator import QualityEvaluator

evaluator = QualityEvaluator()
result = evaluator.evaluate_all(
    article=article_data,
    slides_data=slides_result,
    video_data=video_result
)

if result["overall"]["passed"]:
    print(f"Quality check PASSED: {result['overall']['percentage']}%")
else:
    print(f"Quality check FAILED: {result['all_issues']}")
```

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **AI モデル** | Gemini 3 Pro, Gemini 3 Flash, Deep Research, Gemini 2.5 Flash image |
| **音声合成（TTS）** | VOICEPEAK（ローカル優先）、Gemini 2.5 Flash TTS（フォールバック） |
| **動画生成** | Remotion 4.0 (SlideVideoV3/SlideVideo/BlogVideo) + Base64 Data URL方式 |
| **スライド生成** | Marp CLI (Markdown → PDF → PNG) |
| **言語** | Python 3.11+, JavaScript (Node.js 20+), TypeScript |
| **ライブラリ** | `google-genai>=1.56.0`, `pdf2image`, `python-pptx` |
| **検索** | Google Search Tool (Gemini Built-in) |
| **静的サイト** | Jekyll (GitHub Pages) |
| **CI/CD** | GitHub Actions |
| **品質管理** | 独自評価システム（97%合格ライン） |

---

## ライセンス

MIT License

---

## 関連リンク

- [GitHub Repository](https://github.com/takubon0202/if-blog-auto)
- [公開ブログ](https://takubon0202.github.io/if-blog-auto/)
- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API ドキュメント](https://ai.google.dev/gemini-api/docs)
