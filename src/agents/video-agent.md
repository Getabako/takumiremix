# Video Agent - スライドベース動画生成

## 役割
ブログ記事から高品質なスライド解説動画を自動生成するエージェント。
Gemini TTS音声とRemotionを統合し、視聴者に価値を届ける動画を作成します。

## 重要: 処理フロー（この順序で必ず実行）

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: スライド生成                                       │
│  ├── 記事からスライド構成を生成（Gemini 3 Pro）             │
│  │   - タイトルスライド                                     │
│  │   - コンテンツスライド（3-4枚）                         │
│  │   - エンディングスライド                                │
│  └── 各スライドの画像を生成（Gemini 2.5 Flash image）       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: 音声生成（スライド内容を元に）                     │
│  ├── スライド内容からナレーションスクリプトを生成           │
│  │   - 各スライドの要点を自然な話し言葉で解説               │
│  │   - 約120文字（30秒分）                                 │
│  └── Gemini 2.5 Flash TTSで音声生成（WAV形式）             │
│      - PCM → WAV変換（24kHz, 16bit, mono）                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: ファイル配置（フォールバック用）                   │
│  ├── スライド画像をpublic/slides/にコピー                   │
│  │   - slide_01.png, slide_02.png, ...                     │
│  └── 音声ファイルをpublic/narration.wavに保存              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: 動画レンダリング（Remotion）v2.7.0                 │
│  ├── 【重要】Base64データURL変換（DailyInstagram方式）      │
│  │   - 画像: PNG → data:image/png;base64,...               │
│  │   - 音声: WAV → data:audio/wav;base64,...               │
│  │   - file://プロトコル問題を回避                         │
│  ├── propsをJSONファイルに保存                              │
│  │   - slides: スライドデータ                              │
│  │   - slideImages: Base64画像配列（優先）                 │
│  │   - audioDataUrl: Base64音声（優先）                    │
│  │   - audioUrl: ファイルパス（フォールバック）             │
│  │   - slideDuration: 5秒/スライド                         │
│  ├── node render.mjs SlideVideo を実行                     │
│  └── MP4動画を出力（1920x1080）                            │
└─────────────────────────────────────────────────────────────┘
```

## 動画仕様

### スライドベース動画（30秒以内）
| 項目 | 値 |
|------|------|
| 解像度 | 1920x1080 |
| フレームレート | 30fps |
| 長さ | **最大30秒**（6スライド x 5秒） |
| 形式 | MP4 (H.264 + AAC) |
| 用途 | YouTube、ブログ埋め込み |
| 音声 | Gemini 2.5 Flash TTS ナレーション（WAV） |
| **品質評価** | **なし（記事のみ評価）** |

## 音声生成詳細

### TTS音声タイプ（トピック別）
| トピック | 音声ID | Gemini Voice | 特徴 |
|---------|--------|--------------|------|
| psychology | default | Kore | 落ち着いた声 |
| education | default | Kore | 落ち着いた声 |
| startup | bright | Puck | 明るい声 |
| investment | default | Kore | 落ち着いた声 |
| ai_tools | bright | Puck | 明るい声 |
| inclusive_education | calm | Charon | 静かな声 |
| weekly_summary | warm | Aoede | 温かみのある声 |

### ナレーション生成プロセス
1. スライド構成を分析（heading, points, type）
2. 各スライドの内容を要約
3. 自然な話し言葉でスクリプト生成
4. Gemini 2.5 Flash TTSで音声合成
5. PCM→WAV形式に変換（24kHz, 16bit, mono）

### 音声データの検証（3段階・緩和済み v2.6.3）
1. **PCMデータ検証** (`gemini_client.py`)
   - 最低100バイト以上のPCMデータ（以前は5KB）
   - WAV変換後のサイズを検証
2. **WAVファイル検証** (`generate_slide_video.py` Step 3)
   - WAVヘッダー（RIFF/WAVE）の確認のみ
   - サイズ制限なし（以前は10KB以上）
   - 小さい音声も有効として扱う
3. **Remotion前検証** (`render.mjs`)
   - ファイルの存在確認
   - WAVヘッダーの確認（サイズ制限なし）
   - ヘッダー無効でもファイルサイズ > 44バイトなら使用を試行

### TTS API呼び出し
```python
# src/lib/gemini_client.py
config = types.GenerateContentConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Kore"  # or Puck, Charon, Aoede
            )
        )
    )
)
```

## スライドデータの正規化（重要）

Remotionに渡す前にスライドデータを正規化します:

### typeフィールドの正規化
- **スライド1**: 必ず `type: "title"` に設定
- **中間スライド**: 必ず `type: "content"` に設定
- **最終スライド**: 必ず `type: "ending"` に設定

### SlideVideo.tsxが期待するデータ形式
```typescript
interface SlideData {
  heading: string;      // 必須: 見出し
  subheading?: string;  // オプション: サブ見出し
  points?: string[];    // オプション: 箇条書きポイント
  type: "title" | "content" | "ending";  // 必須: 3種類のみ
  imageUrl?: string;    // 自動生成されるため不要
  narrationText?: string;  // オプション
}
```

### 画像パスの自動設定
- `imageUrl`はRemotionが自動生成: `slides/slide_01.png`, `slides/slide_02.png`...
- 画像は`remotion/public/slides/`ディレクトリに配置

## 動画生成ポリシー

### 重要: 品質評価なし
動画生成では品質評価をスキップします。品質評価は**記事のみ**に適用されます。
動画は生成成功後、即座にパスします。

### 制約事項
- 30秒以内（6スライド x 5秒 = 30秒）
- リトライなし（1回の試行のみ）
- 音声生成失敗時も動画は生成される（無音）

### 必須要件
- [ ] スライド構成が正しい（タイトル、コンテンツ、エンディング）
- [ ] スライドタイプが正規化されている（title/content/ending）
- [ ] 解像度 1920x1080
- [ ] MP4形式で出力

## 使用するモデル・ツール

| 用途 | モデル/ツール |
|------|-------------|
| スライド構成 | `gemini-3-pro-preview` |
| スライド画像 | `gemini-2.5-flash-image` |
| ナレーション | `gemini-2.5-flash-preview-tts` |
| 動画レンダリング | Remotion 4.0 |

## トピック別カラースキーム

| トピック | Primary | Secondary | 背景 |
|---------|---------|-----------|------|
| psychology | #00b4d8 | #90e0ef | #1a1a2e |
| education | #10b981 | #6ee7b7 | #1a1a2e |
| startup | #f59e0b | #fcd34d | #1a1a2e |
| investment | #14b8a6 | #5eead4 | #1a1a2e |
| ai_tools | #3b82f6 | #93c5fd | #1a1a2e |
| inclusive_education | #06b6d4 | #67e8f9 | #1a1a2e |
| weekly_summary | #0ea5e9 | #7dd3fc | #1a1a2e |

## エラーハンドリング

### 音声生成失敗時
- 動画は無音で生成される
- ログに警告を出力
- 結果JSONに `has_audio: false` を設定

### スライド生成失敗時
- エラーを返して終了
- リトライは行わない

### レンダリング失敗時
- エラーを返して終了
- 詳細なエラーログを出力

## 出力結果の例

```json
{
  "status": "success",
  "topic": "education",
  "video": {
    "status": "success",
    "path": "output/videos/slide_video_20260107_education.mp4",
    "resolution": "1920x1080",
    "duration": 30,
    "has_audio": true,
    "slide_count": 6
  },
  "narration": {
    "status": "success",
    "script": "教育の最新トレンドについてお話しします...",
    "audio_size_bytes": 720000,
    "voice": "Kore"
  },
  "slides": {
    "status": "success",
    "slide_count": 6,
    "slides": [
      {"type": "title", "heading": "教育の最新動向2026"},
      {"type": "content", "heading": "AIを活用した学習", "points": ["..."]},
      ...
    ]
  }
}
```

## API呼び出しパターン

### メイン処理（generate_slide_video）
```python
from scripts.generate_slide_video import generate_slide_video

result = await generate_slide_video(
    article={
        "title": "記事タイトル",
        "content": "記事本文...",
        "topic_id": "education"
    },
    target_slides=6,      # 最大6枚（30秒制限）
    slide_duration=5      # 各スライド5秒
)
```

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/scripts/generate_slide_video.py` | メイン処理（Step 1-4統合） |
| `src/scripts/generate_slides.py` | スライド生成（Step 1） |
| `src/lib/gemini_client.py` | TTS音声生成（Step 2） |
| `remotion/src/compositions/SlideVideo.tsx` | Remotionコンポーネント |
| `remotion/render.mjs` | レンダリングスクリプト |

## 依存関係

### Python
```
google-genai>=1.56.0  # TTS対応
```

### remotion/package.json
```json
{
  "dependencies": {
    "@remotion/cli": "4.0.0",
    "@remotion/player": "4.0.0",
    "remotion": "4.0.0"
  }
}
```

### システム要件
- Node.js 20+
- ffmpeg（Remotionに同梱）
- Chrome依存ライブラリ（CI環境）

## ドキュメント更新義務

このエージェントで機能追加・修正・エラー対応を行った場合、**必ずこのファイルを最新仕様に更新すること**。
