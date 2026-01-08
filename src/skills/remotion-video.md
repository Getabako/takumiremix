# Remotion Video Skill

## 概要
Remotionフレームワークを使用したスライドベース動画生成スキル。
ブログ記事からスライドを生成し、**TTS音声ナレーション**を統合して動画を作成します。

### 重要な制約
- **動画長**: 最大30秒（6スライド x 5秒）
- **品質評価**: なし（動画生成は品質評価をスキップ）
- **リトライ**: なし（1回の試行のみ）

## 処理フロー（この順序で実行）

```
STEP 1: スライド生成
    ↓
STEP 2: 音声生成（スライド内容を元に）
    ↓
STEP 3: ファイル配置（public/に配置）
    ↓
STEP 4: Remotionレンダリング（音声統合）
```

## 使用技術
- **Framework**: Remotion 4.0
- **Language**: TypeScript/React
- **TTS**: Gemini 2.5 Flash TTS (gemini-2.5-flash-preview-tts)
- **Output**: MP4 (H.264 + AAC)
- **Audio Format**: WAV (24kHz, 16bit, mono)

## Remotion概要
Remotionは、Reactコンポーネントを使ってプログラマティックに動画を作成できるフレームワークです。

### 主要概念
- **Composition**: 動画の定義（サイズ、長さ、fps）
- **Sequence**: タイムライン上のシーン配置
- **useCurrentFrame**: 現在のフレーム番号を取得
- **interpolate**: 値をアニメーション
- **spring**: 物理ベースのアニメーション
- **Audio**: 音声トラックの統合

## コンポジション設定

### BlogVideo（標準版）- メイン
```typescript
<Composition
  id="BlogVideo"
  component={BlogVideo}
  durationInFrames={900}  // 30秒 @ 30fps
  fps={30}
  width={1920}
  height={1080}
  defaultProps={blogData}
/>
```

### BlogVideoShort（ショート版）- 将来拡張用
```typescript
<Composition
  id="BlogVideoShort"
  component={BlogVideo}
  durationInFrames={450}  // 15秒 @ 30fps
  fps={30}
  width={1080}
  height={1920}  // 縦型
  defaultProps={{...blogData, isShort: true}}
/>
```

## Props インターフェース

### BlogVideoProps
```typescript
interface BlogVideoProps {
  title: string;           // 記事タイトル
  summary: string;         // 記事要約
  points: string[];        // 主要ポイント（配列）
  topic: string;           // トピックID
  date: string;            // 日付
  authorName?: string;     // 著者名（デフォルト: "if(塾) Blog"）
  isShort?: boolean;       // ショート動画フラグ
  heroImageUrl?: string;   // ヒーロー画像URL
  audioUrl?: string;       // ナレーション音声URL
}
```

### SlideVideoProps（スライドベース動画用）
```typescript
interface SlideVideoProps {
  title: string;           // 動画タイトル
  slides: SlideData[];     // スライドデータ配列
  topic: string;           // トピックID
  authorName?: string;     // 著者名
  audioUrl?: string | null; // ナレーション音声（public/内のパス）
  slideImagePrefix?: string; // 画像プレフィックス（デフォルト: "slide_"）
  slideDuration?: number;   // 各スライドの表示時間（秒、デフォルト: 5）
}

interface SlideData {
  heading: string;         // 見出し（必須）
  subheading?: string;     // サブ見出し
  points?: string[];       // 箇条書きポイント
  type: "title" | "content" | "ending";  // スライドタイプ（必須）
  imageUrl?: string;       // 画像URL（自動生成されるため省略可）
  narrationText?: string;  // ナレーションテキスト
}
```

### スライドタイプの正規化（重要）
Pythonから渡す前にスライドデータを正規化する必要があります:
- **スライド1**: `type: "title"` に強制
- **中間スライド**: `type: "content"` に強制
- **最終スライド**: `type: "ending"` に強制

**注意**: generate_slide_video.pyの`_normalize_slides_for_remotion()`メソッドで自動正規化されます。

## TTS音声統合

### Pythonでの音声生成
```python
from lib.gemini_client import GeminiClient

client = GeminiClient()

# ナレーション生成
narration = await client.generate_video_narration(
    title=article["title"],
    summary=article["summary"],
    points=article["points"],
    duration_seconds=30,
    voice="default"  # トピック別に選択
)

# 音声ファイル保存
audio_path = output_dir / "narration.wav"
with open(audio_path, "wb") as f:
    f.write(narration["audio_data"])
```

### Remotionでの音声組み込み
```typescript
import { Audio, staticFile } from 'remotion';

export const BlogVideo: React.FC<BlogVideoProps> = (props) => {
  return (
    <AbsoluteFill>
      {/* 音声トラック */}
      {props.audioUrl && (
        <Audio src={props.audioUrl} />
      )}

      {/* ビジュアルシーン */}
      <Sequence from={0} durationInFrames={180}>
        <TitleScene {...props} />
      </Sequence>

      {/* 画像シーン */}
      {props.heroImageUrl && (
        <Sequence from={180} durationInFrames={90}>
          <HeroImageScene imageUrl={props.heroImageUrl} />
        </Sequence>
      )}

      {/* 続くシーン... */}
    </AbsoluteFill>
  );
};
```

## トピック別設定

### カラースキーム
```typescript
const TOPIC_COLORS = {
  psychology: { primary: "#2b6cb0", accent: "#4299e1", name: "心理学" },
  education: { primary: "#2f855a", accent: "#48bb78", name: "教育" },
  startup: { primary: "#c05621", accent: "#ed8936", name: "スタートアップ" },
  investment: { primary: "#744210", accent: "#d69e2e", name: "投資" },
  ai_tools: { primary: "#1a365d", accent: "#3182ce", name: "AIツール" },
  inclusive_education: { primary: "#285e61", accent: "#38b2ac", name: "インクルーシブ教育" },
  weekly_summary: { primary: "#553c9a", accent: "#805ad5", name: "週間総括" }
};
```

### 推奨TTS音声
```typescript
const TOPIC_VOICES = {
  psychology: "default",     // Kore - 落ち着いた声
  education: "default",
  startup: "bright",         // Puck - 明るい声
  investment: "default",
  ai_tools: "bright",
  inclusive_education: "calm", // Charon - 静かな声
  weekly_summary: "warm"       // Aoede - 温かみのある声
};
```

## アニメーション技法

### Spring アニメーション
```typescript
const slideIn = spring({
  frame,
  fps,
  config: { damping: 100, stiffness: 200, mass: 0.5 }
});
```

### Interpolate
```typescript
const opacity = interpolate(frame, [0, 20], [0, 1], {
  extrapolateRight: "clamp"
});

const translateY = interpolate(slideIn, [0, 1], [50, 0]);
```

### 画像フェード効果
```typescript
const HeroImageScene: React.FC<{ imageUrl: string }> = ({ imageUrl }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = interpolate(frame, [0, 30], [1.1, 1], {
    extrapolateRight: "clamp"
  });

  const opacity = interpolate(frame, [0, 15, 75, 90], [0, 1, 1, 0]);

  return (
    <AbsoluteFill style={{ opacity }}>
      <Img
        src={imageUrl}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale})`
        }}
      />
    </AbsoluteFill>
  );
};
```

## シーン構成（音声同期版）

### TitleScene
- グラデーション背景（トピックカラー）
- トピックラベル（スケールアニメーション）
- メインタイトル（フェードイン + スライドアップ）
- **音声**: 「今日は〇〇についてお話しします」

### HeroImageScene（NEW）
- ヒーロー画像を全画面表示（Ken Burnsエフェクト）
- オーバーレイでタイトル再表示
- **音声**: 「最新動向を見ていきましょう」

### SummaryScene
- ダークグレー背景
- カラーアクセントバー
- 要約テキスト（フェードイン）
- **音声**: 要約の読み上げ

### PointScene
- ライトグレー背景
- 番号バッジ（スケールアニメーション）
- ポイントテキスト（スライドイン）
- **音声**: 各ポイントの説明

### EndingScene
- グラデーション背景（トピックカラー）
- 著者名/ブログ名（スケールアニメーション）
- 日付（フェードイン）
- CTA「ブログで詳しく読む」
- **音声**: 「詳しくはブログをご覧ください」

## レンダリング

### CLIでのレンダリング
```bash
# 標準動画のみ（推奨）
npx remotion render BlogVideo out/video.mp4

# カスタムprops（音声・画像付き）
npx remotion render BlogVideo out/video.mp4 --props='{"title":"タイトル","audioUrl":"file:///path/to/audio.wav","heroImageUrl":"file:///path/to/image.png"}'
```

### プログラマティックレンダリング（音声付き）
```javascript
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import fs from "fs";
import path from "path";

// 音声ファイルをpublic/に配置
const audioPath = path.join(__dirname, "public", "narration.wav");
fs.copyFileSync(sourceAudioPath, audioPath);

const bundled = await bundle({
  entryPoint: "./src/index.tsx",
  webpackOverride: (config) => config,
  publicDir: "./public",  // 音声・画像ファイル配置先
});

const blogData = {
  ...articleData,
  audioUrl: staticFile("narration.wav"),
  heroImageUrl: staticFile("hero.png")
};

const composition = await selectComposition({
  serveUrl: bundled,
  id: "BlogVideo",
  inputProps: blogData,
});

await renderMedia({
  composition,
  serveUrl: bundled,
  codec: "h264",
  outputLocation: "out/video.mp4",
  inputProps: blogData,
});
```

## Pythonからの完全フロー
```python
import subprocess
import json
import os
from pathlib import Path
from lib.gemini_client import GeminiClient

async def render_video_with_audio(article: dict, output_path: str):
    """音声・画像付きRemotionレンダリング"""

    client = GeminiClient()
    remotion_dir = Path(__file__).parent.parent / "remotion"
    public_dir = remotion_dir / "public"
    public_dir.mkdir(exist_ok=True)

    # 1. TTS音声生成
    topic = article.get("topic", "ai_tools")
    voice = TOPIC_VOICES.get(topic, "default")

    narration = await client.generate_video_narration(
        title=article["title"],
        summary=article["summary"],
        points=article["points"],
        duration_seconds=30,
        voice=voice
    )

    # 2. 音声ファイル保存
    audio_path = public_dir / "narration.wav"
    with open(audio_path, "wb") as f:
        f.write(narration["audio_data"])

    # 3. ヒーロー画像をコピー
    if article.get("hero_image_path"):
        hero_dest = public_dir / "hero.png"
        shutil.copy(article["hero_image_path"], hero_dest)

    # 4. propsをJSONに保存
    props_data = {
        **article,
        "audioUrl": "narration.wav",  # staticFile参照
        "heroImageUrl": "hero.png" if article.get("hero_image_path") else None
    }

    props_file = remotion_dir / "props.json"
    with open(props_file, "w", encoding="utf-8") as f:
        json.dump(props_data, f, ensure_ascii=False)

    # 5. Remotionレンダリング
    result = subprocess.run(
        ["node", "render.mjs", "BlogVideo", output_path, str(props_file)],
        cwd=str(remotion_dir),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Render failed: {result.stderr}")

    return {
        "video_path": output_path,
        "narration_script": narration["script"],
        "has_audio": True
    }
```

## プロジェクト構成
```
remotion/
├── package.json
├── remotion.config.ts
├── render.mjs              # レンダリングスクリプト
├── tsconfig.json
├── public/                 # 静的ファイル（音声・画像）
│   ├── narration.wav       # TTS音声（動的生成）
│   └── hero.png            # ヒーロー画像（動的コピー）
└── src/
    ├── index.tsx           # エントリーポイント
    ├── Root.tsx            # コンポジション定義
    └── compositions/
        ├── BlogVideo.tsx   # メイン動画コンポーネント
        └── scenes/
            ├── TitleScene.tsx
            ├── HeroImageScene.tsx  # NEW
            ├── SummaryScene.tsx
            ├── PointScene.tsx
            └── EndingScene.tsx
```

## 依存関係インストール
```bash
cd remotion
npm install
```

## 開発プレビュー
```bash
npm start
# ブラウザで http://localhost:3000 を開く
```

## エラーハンドリング

### 音声生成エラー
```python
try:
    narration = await client.generate_video_narration(...)
except Exception as e:
    logger.warning(f"TTS failed: {e}")
    # フォールバック: 音声なしで続行
    narration = {"audio_data": None, "script": None}
```

### レンダリングエラー
```python
class VideoRenderError(Exception):
    """動画レンダリングエラー"""
    pass

try:
    output = await render_video_with_audio(article, "out/video.mp4")
except subprocess.CalledProcessError as e:
    # エラー解析
    if "Target closed" in str(e.stderr):
        raise VideoRenderError("Chromium crashed - check dependencies")
    elif "libasound" in str(e.stderr):
        raise VideoRenderError("Audio library missing - install libasound2t64")
    raise VideoRenderError(f"Remotion render failed: {e.stderr}")
```

## 出力ディレクトリ
```
output/
└── videos/
    ├── blog_video_20251230_ai_tools.mp4       # 音声付き標準版
    └── blog_video_short_20251230_ai_tools.mp4 # ショート版（将来拡張用）
```

## CI環境設定

### GitHub Actions
```yaml
- name: Install Chrome dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y \
      libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
      libxdamage1 libxfixes3 libxrandr2 libgbm1 \
      libasound2t64 libpango-1.0-0 libpangocairo-1.0-0 \
      libcairo2 libatspi2.0-0 libgtk-3-0 libgdk-pixbuf-2.0-0 \
      libx11-xcb1 libxcb-dri3-0 libxshmfence1 \
      fonts-liberation fonts-noto-cjk xvfb \
      libegl1 libgl1-mesa-dri libglx-mesa0 mesa-utils

- name: Start Xvfb
  run: |
    Xvfb :99 -screen 0 1920x1080x24 &
    echo "DISPLAY=:99" >> $GITHUB_ENV
```

### render.mjs CI設定
```javascript
const isCI = process.env.CI === 'true';

const chromiumOptions = {
  gl: isCI ? 'swangle' : 'angle',
  enableMultiProcessOnLinux: true,
  headless: true,
};
```

## 注意事項
- Node.js 20+ が必要
- 初回実行時は依存関係のインストールが必要
- レンダリングは重い処理のため、CI/CDでのタイムアウトに注意（45分推奨）
- 日本語フォント（fonts-noto-cjk）が必要
- TTS音声はWAV形式で保存し、Remotionで読み込む
