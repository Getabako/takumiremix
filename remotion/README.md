# Remotion Video Generator v2.0.0

ブログ記事から動画を自動生成するRemotionプロジェクト。

## 技術スタック

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Remotion | 4.0.0 | 動画レンダリングフレームワーク |
| React | 18.2.0 | UIコンポーネント |
| TypeScript | 5.3.0+ | 型安全な開発 |
| Node.js | 20+ | 実行環境 |

## コンポジション一覧

| ID | 説明 | 解像度 | 長さ | 用途 |
|----|------|--------|------|------|
| `BlogVideo` | ブログ概要動画 | 1920x1080 | 30秒 | YouTube/Web埋め込み |
| `BlogVideoShort` | ショート動画 | 1080x1920 | 15秒 | Shorts/Reels/TikTok |
| `SlideVideo` | スライドベース動画 | 1920x1080 | 可変長 | 解説動画 |
| `SlideVideoShort` | スライドショート | 1080x1920 | 可変長 | ショート解説 |

## セットアップ

```bash
cd remotion
npm install
```

## 使用方法

### プレビュー（Remotion Studio）

```bash
npm start
# または
npm run preview
```

### レンダリング

```bash
# BlogVideo（デフォルト）
npm run render

# BlogVideo
npm run render:blog

# SlideVideo
npm run render:slide

# ショート動画
npm run build:short

# カスタムprops付き
node render.mjs SlideVideo output/video.mp4 props.json

# CI環境
CI=true node render.mjs SlideVideo output/video.mp4 props.json
```

### その他のコマンド

```bash
# 型チェック
npm run typecheck

# Remotionアップグレード
npm run upgrade
```

## Props形式

### BlogVideo

```json
{
  "title": "記事タイトル",
  "summary": "記事概要（2-3文）",
  "points": ["ポイント1", "ポイント2", "ポイント3"],
  "topic": "ai_tools",
  "date": "2025年1月6日",
  "authorName": "if(塾) Blog",
  "isShort": false,
  "audioUrl": "narration.wav",
  "heroImageUrl": "hero.png"
}
```

| プロパティ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `title` | string | Yes | 記事タイトル |
| `summary` | string | Yes | 記事概要 |
| `points` | string[] | Yes | 要点リスト（最大3つ表示） |
| `topic` | string | Yes | トピックID（カラースキーム選択） |
| `date` | string | Yes | 公開日 |
| `authorName` | string | No | 著者名（デフォルト: if(塾) Blog） |
| `isShort` | boolean | No | ショート版フラグ |
| `audioUrl` | string | No | TTS音声ファイルパス |
| `heroImageUrl` | string | No | ヒーロー画像パス |

### SlideVideo

```json
{
  "title": "プレゼンタイトル",
  "slides": [
    {
      "type": "title",
      "heading": "メインタイトル",
      "subheading": "サブタイトル",
      "imageUrl": "slides/slide_01.png"
    },
    {
      "type": "content",
      "heading": "見出し",
      "points": ["ポイント1", "ポイント2", "ポイント3"],
      "imageUrl": "slides/slide_02.png",
      "narrationText": "このスライドのナレーション"
    },
    {
      "type": "ending",
      "heading": "if(塾) Blog",
      "subheading": "詳しくはブログで"
    }
  ],
  "topic": "ai_tools",
  "authorName": "if(塾) Blog",
  "slideDuration": 5,
  "audioUrl": "narration.wav",
  "slideImagePrefix": "slide_"
}
```

| プロパティ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `title` | string | Yes | プレゼンタイトル |
| `slides` | SlideData[] | Yes | スライドデータ配列 |
| `topic` | string | Yes | トピックID |
| `authorName` | string | No | 著者名 |
| `slideDuration` | number | No | 各スライドの表示時間（秒、デフォルト: 5） |
| `audioUrl` | string | No | TTS音声ファイルパス |
| `slideImagePrefix` | string | No | スライド画像のプレフィックス |

#### SlideData型

| プロパティ | 型 | 説明 |
|-----------|-----|------|
| `type` | "title" \| "content" \| "ending" | スライドタイプ |
| `heading` | string | 見出し |
| `subheading` | string? | サブ見出し |
| `points` | string[]? | 箇条書きポイント |
| `imageUrl` | string? | 背景画像パス |
| `narrationText` | string? | ナレーションテキスト |

### 動的な動画長（calculateMetadata）

SlideVideoは`calculateMetadata`を使用して動的に長さを計算:

```
動画長（フレーム） = スライド数 × slideDuration × fps
例: 12スライド × 5秒 × 30fps = 1800フレーム（60秒）
```

## トピック別カラースキーム

### BlogVideo カラー

| トピック | Primary | Accent | 日本語名 |
|----------|---------|--------|---------|
| psychology | #2b6cb0 | #4299e1 | 心理学 |
| education | #2f855a | #48bb78 | 教育 |
| startup | #c05621 | #ed8936 | スタートアップ |
| investment | #744210 | #d69e2e | 投資 |
| ai_tools | #1a365d | #3182ce | AIツール |
| inclusive_education | #285e61 | #38b2ac | インクルーシブ教育 |
| weekly_summary | #553c9a | #805ad5 | 週間総括 |

### SlideVideo カラー

| トピック | Primary | Secondary | Background |
|----------|---------|-----------|------------|
| psychology | #00b4d8 | #90e0ef | #1a1a2e |
| education | #10b981 | #6ee7b7 | #1a1a2e |
| startup | #f59e0b | #fcd34d | #1a1a2e |
| investment | #14b8a6 | #5eead4 | #1a1a2e |
| ai_tools | #3b82f6 | #93c5fd | #1a1a2e |
| inclusive_education | #06b6d4 | #67e8f9 | #1a1a2e |
| weekly_summary | #0ea5e9 | #7dd3fc | #1a1a2e |

## アニメーション効果

### BlogVideo

| シーン | エフェクト |
|--------|-----------|
| タイトル | Spring + Fade In |
| ヒーロー画像 | Ken Burns（ズームアウト） |
| サマリー | Fade In |
| ポイント | Slide In + Spring |
| エンディング | Scale + Fade |

### SlideVideo

| エフェクト | 説明 |
|-----------|------|
| Ken Burns | ズーム + パンの組み合わせ |
| Fade | フェードイン/アウト |
| Slide Left/Right | 左右スライドイン |
| Stagger | ポイントの順次表示 |
| Progress Bar | 下部プログレスバー |

## ファイル構造

```
remotion/
├── src/
│   ├── index.tsx              # エントリーポイント（registerRoot）
│   ├── Root.tsx               # コンポジション定義
│   └── compositions/
│       ├── BlogVideo.tsx      # ブログ動画コンポーネント
│       │   ├── TitleScene     # タイトルシーン
│       │   ├── HeroImageScene # ヒーロー画像（Ken Burns）
│       │   ├── SummaryScene   # サマリーシーン
│       │   ├── PointScene     # ポイントシーン
│       │   └── EndingScene    # エンディングシーン
│       └── SlideVideo.tsx     # スライド動画コンポーネント
│           └── SlideScene     # 各スライドのシーン
├── public/                    # 静的ファイル（音声、画像）
│   ├── narration.wav          # TTS音声ファイル
│   ├── hero.png               # ヒーロー画像
│   └── slides/                # スライド画像
│       ├── slide_01.png
│       ├── slide_02.png
│       └── ...
├── out/                       # 出力ディレクトリ
├── render.mjs                 # プログラマティックレンダリング
├── remotion.config.ts         # Remotion設定
├── package.json               # 依存関係・スクリプト
├── tsconfig.json              # TypeScript設定
└── README.md                  # このファイル
```

## render.mjs の機能

### コマンドライン引数

```bash
node render.mjs [compositionId] [outputPath] [propsFile]
```

| 引数 | デフォルト | 説明 |
|------|-----------|------|
| `compositionId` | BlogVideo | レンダリングするコンポジション |
| `outputPath` | out/video.mp4 | 出力ファイルパス |
| `propsFile` | - | propsのJSONファイル |

### 機能

- **進捗ログ**: 10%ごとに進捗を出力
- **動的長さ計算**: SlideVideoのスライド数から自動計算
- **CI環境対応**: `CI=true`でソフトウェアレンダリング使用
- **エラー解析**: エラー時に原因と解決策を提案
- **ファイルサイズ検証**: 異常に小さいファイルをエラーとして検出

### CI環境設定

```javascript
const chromiumOptions = {
  gl: isCI ? 'swangle' : 'angle',
  enableMultiProcessOnLinux: true,
  headless: true
};
```

## remotion.config.ts 設定

```typescript
Config.setVideoImageFormat("jpeg");   // フレーム画像形式
Config.setOverwriteOutput(true);      // 上書き許可
Config.setJpegQuality(90);            // JPEG品質
Config.setConcurrency(4);             // 並列処理数
Config.setLevel("verbose");           // ログレベル
```

## CI/CD対応

### GitHub Actions

```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'

- name: Install dependencies
  run: |
    cd remotion
    npm ci

- name: Render video
  run: |
    cd remotion
    node render.mjs SlideVideo output/video.mp4 props.json
  env:
    CI: true
    DISPLAY: ':99'

- name: Upload artifact
  uses: actions/upload-artifact@v4
  with:
    name: video
    path: remotion/output/video.mp4
```

### Linux環境での依存関係

```bash
sudo apt-get update
sudo apt-get install -y \
  libnss3 \
  libatk-bridge2.0-0 \
  libdrm2 \
  libxkbcommon0 \
  libgbm1 \
  libasound2
```

## トラブルシューティング

### Target closed エラー

**原因**: Chromiumがクラッシュ

**解決策**:
1. Chrome依存関係をインストール
2. `gl: 'swiftshader'`を試す
3. メモリを増やす
4. `DISPLAY`環境変数を設定

### ENOENT エラー

**原因**: ファイルが見つからない

**解決策**:
1. `npm install`を実行
2. ソースファイルの存在を確認

### GPU/GL エラー

**原因**: グラフィックス関連

**解決策**:
1. `gl: 'swiftshader'`でソフトウェアレンダリング
2. Mesa/LLVMライブラリをインストール

## 統合ワークフロー

このRemotionプロジェクトは、ブログ自動生成システムの一部として動作します。

### 実行トリガー

| トリガー | 条件 |
|---------|------|
| **自動実行** | 毎日 JST 5:00（UTC 20:00） |
| **手動実行** | GitHub Actions > workflow_dispatch |

### 曜日別トピック・リサーチ方法

| 曜日 | トピック | リサーチ方法 |
|-----|---------|-------------|
| 月曜 | psychology（心理学） | Google Search 3回 |
| 火曜 | education（教育） | Google Search 3回 |
| 水曜 | startup（スタートアップ） | Google Search 3回 |
| 木曜 | investment（投資） | Google Search 3回 |
| 金曜 | ai_tools（AIツール） | Google Search 3回 |
| 土曜 | inclusive_education（インクルーシブ教育） | Google Search 3回 |
| **日曜** | **weekly_summary（週間総括）** | **Deep Research** |

### 7ステップ処理フロー

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions 開始                          │
│  ubuntu-latest / Python 3.11 / Node.js 20                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 情報収集                                                │
│  ├── 月〜土: Google Search 3回検索 (gemini-3-pro-preview)       │
│  └── 日曜: Deep Research API (週間総括)                         │
│  出力: research_data (sources, topic_info)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: ブログ記事生成                                          │
│  モデル: gemini-3-pro-preview                                   │
│  出力: article (title, content, word_count)                     │
│  目標: 4000〜5500文字                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 画像生成                                                │
│  モデル: gemini-2.5-flash-image                                 │
│  出力: hero.png (アイキャッチ画像)                              │
│  特徴: アニメスタイル、16:9、キャラクター多様性                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: スライド動画生成（推奨モード）                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4-1. スライド生成                                        │   │
│  │      Gemini 3 Pro → 12枚のスライド構成                   │   │
│  │      Gemini 2.5 Flash image → 各スライド画像             │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4-2. Marp PDF エクスポート                               │   │
│  │      Markdown → PDF → PNG画像                            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4-3. ナレーション生成                                    │   │
│  │      Gemini 2.5 Flash TTS → narration.wav                │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4-4. Remotion レンダリング                               │   │
│  │      SlideVideo → 1920x1080 MP4                          │   │
│  │      12スライド × 5秒 = 60秒動画                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: SEO最適化                                               │
│  モデル: gemini-3-flash-preview（思考オフ）                     │
│  出力: title, description, tags, categories                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 品質レビュー（最大3回リトライ）                         │
│  ├── 品質スコア80点以上まで修正                                │
│  ├── スライド動画: 95%以上で合格                               │
│  └── 不合格時: スライド数調整、テキスト量調整                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: GitHub Pages 投稿                                       │
│  ├── docs/_posts/ に記事保存                                   │
│  ├── docs/assets/images/ に画像保存                            │
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

### 生成される成果物

| 成果物 | パス | 説明 |
|-------|------|------|
| ブログ記事 | `docs/_posts/YYYY-MM-DD-title.md` | Markdown形式 |
| ヒーロー画像 | `docs/assets/images/YYYYMMDD_topic_hero.png` | アイキャッチ |
| スライド画像 | `output/slides/slide_XX.png` | 12枚程度 |
| 動画 | `output/videos/slide_video_*.mp4` | 60秒程度 |
| 音声 | `remotion/public/narration.wav` | TTS音声 |

### 品質評価基準（95%合格ライン）

| 項目 | 基準 | 重み |
|-----|------|------|
| 記事文字数 | 10,000文字以上 | 8 |
| スライド枚数 | 10〜15枚 | 5 |
| 動画+音声 | TTS音声あり | 5 |
| 画像品質 | 全スライド画像あり | 4 |
| SEOスコア | 80点以上 | 3 |

### 処理時間の目安

| ステップ | 時間 |
|---------|------|
| 情報収集（Google Search） | 約10秒 |
| 情報収集（Deep Research） | 約5分 |
| 記事生成 | 約30秒 |
| 画像生成 | 約1〜2分 |
| スライド動画生成 | 約5〜10分 |
| SEO+レビュー | 約30秒 |
| Git push + Jekyll | 約2分 |
| **合計** | **約10〜20分** |

### デフォルト設定

```python
--use-slide-video = True      # スライドベース動画（推奨）
--slide-count = 12            # 目標スライド枚数
--slide-duration = 5          # 各スライド5秒
--publish = True              # GitHub Pages投稿
```

### 関連スクリプト

| スクリプト | 説明 |
|-----------|------|
| `src/scripts/main.py` | メインエントリーポイント |
| `src/scripts/generate_slide_video.py` | スライド動画生成 |
| `src/scripts/generate_slides.py` | スライド生成 |
| `src/scripts/quality_evaluator.py` | 品質評価 |
| `remotion/render.mjs` | Remotionレンダリング |

## ライセンス

MIT License
