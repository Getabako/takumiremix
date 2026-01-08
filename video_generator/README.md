# Gemini Video Generator

ブログ記事から高品質な解説動画を自動生成するワークフロー

## Features

- **Gemini 3.0 Pro Preview**: シーン構成・脚本の自動生成
- **Gemini 2.5 Flash image**: 高品質16:9画像の生成
- **Gemini TTS**: 自然な日本語音声合成
- **Ken Burns Effect**: 静止画に動きを与える演出
- **完璧な音声同期**: 音声長に基づく自動タイミング調整
- **テロップ自動生成**: 読みやすいオーバーレイテキスト

## Quick Start

### 1. 依存関係インストール

```bash
cd video_generator
pip install -r requirements.txt
```

### 2. APIキー設定

プロジェクトルートに`.env`ファイルを作成:

```
GOOGLE_AI_API_KEY=your_api_key_here
```

### 3. 動画生成

```bash
# テキストから直接
python main.py --input "AIについてのブログ記事テキスト..."

# ファイルから
python main.py --file article.txt

# URLから
python main.py --url "https://example.com/blog/article"
```

## コマンドラインオプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--input`, `-i` | ブログテキスト（直接入力） | - |
| `--url`, `-u` | ブログ記事のURL | - |
| `--file`, `-f` | テキストファイルパス | - |
| `--output`, `-o` | 出力ファイル名（拡張子なし） | 自動生成 |
| `--scenes`, `-s` | シーン数 | 6 |
| `--voice`, `-v` | 音声タイプ | default |
| `--output-dir` | 出力ディレクトリ | output |

## 音声タイプ

| タイプ | 説明 |
|--------|------|
| `default` | 標準的な落ち着いた声 |
| `bright` | 明るくエネルギッシュな声 |
| `calm` | 静かで穏やかな声 |
| `warm` | 温かみのある声 |
| `energetic` | 活発で元気な声 |
| `friendly` | 親しみやすい声 |

## 出力ファイル構成

```
output/
├── images/          # 生成された画像
│   ├── scene_01.png
│   ├── scene_02.png
│   └── ...
├── audio/           # 生成された音声
│   ├── scene_01.wav
│   ├── scene_02.wav
│   └── ...
└── videos/          # 最終動画
    └── video_YYYYMMDD_HHMMSS.mp4
```

## ワークフロー

```
ブログ記事入力
    │
    ▼
[Step 1] 脚本生成 (Gemini 3.0 Pro)
    │   ├── シーン分割
    │   ├── ナレーション原稿
    │   ├── 画像プロンプト
    │   └── テロップ文
    │
    ▼
[Step 2] 音声生成 (Gemini TTS)
    │   ├── 各シーンのナレーション音声
    │   └── 正確な秒数を取得
    │
    ▼
[Step 3] 画像生成 (Gemini 2.5 Flash)
    │   ├── 16:9 高解像度画像
    │   └── 1920x1080 リサイズ
    │
    ▼
[Step 4] 動画編集 (MoviePy)
    │   ├── Ken Burns Effect
    │   ├── テロップ合成
    │   ├── 音声同期
    │   └── MP4出力
    │
    ▼
最終動画 (MP4)
```

## Ken Burns Effect

静止画を動画として見せるための重要な演出技法:

- **ズームイン**: 1.0倍 → 1.1倍（設定可能）
- **スムーズな動き**: 線形補間による滑らかなズーム
- **視聴維持率向上**: 動きのある映像で視聴者を引き付ける

## 既存システムとの統合

`integrate.py`を使用して既存のブログ自動生成システムと連携:

```python
from video_generator.integrate import generate_blog_video

result = await generate_blog_video(
    article={
        "title": "記事タイトル",
        "content": "記事本文...",
        "topic_id": "ai_tools"
    },
    num_scenes=6
)
```

## トラブルシューティング

### APIキーエラー

```
ValueError: API key required
```

→ `.env`ファイルに`GOOGLE_AI_API_KEY`を設定

### 画像生成エラー

```
Image generation error: safety filter
```

→ プロンプトを調整、またはプレースホルダー画像が自動生成される

### 音声生成エラー

```
No audio data in response
```

→ テキストが短すぎる、または不適切な内容の可能性

### MoviePyエラー

```
ImageMagick not found
```

→ ImageMagickをインストール、またはテキスト描画がPILにフォールバック

## 技術仕様

| 項目 | 値 |
|------|-----|
| 出力解像度 | 1920x1080 (16:9) |
| フレームレート | 30 fps |
| 音声サンプルレート | 24000 Hz |
| 音声形式 | WAV (16bit mono) |
| 動画コーデック | H.264 |
| 音声コーデック | AAC |

## ライセンス

MIT License
