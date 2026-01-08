# Marp Video Generator

Marpスライドベースの動画自動生成ワークフロー

## 概要

ブログ記事からMarp形式のスライドを生成し、音声付きの解説動画を自動作成します。
画像生成AIを使わず、Marpによるスライドをそのまま画像として使用するため、
テキストの可読性が高く、情報量の多い動画を生成できます。

## ワークフロー

```
ブログ記事
    │
    ▼
[Step 1] コンテンツ生成 (Gemini)
    │   ├── Marp Markdown生成
    │   └── ナレーションスクリプト生成
    │
    ▼
[Step 2] スライドレンダリング (Marp CLI)
    │   └── Markdown → PDF変換
    │
    ▼
[Step 3] 画像変換 (pdf2image)
    │   └── PDF → PNG (1920x1080)
    │
    ▼
[Step 4] 音声合成 (Gemini TTS)
    │   ├── スクリプト → WAV変換
    │   └── 音声長を正確に取得
    │
    ▼
[Step 5] 動画生成 (MoviePy)
    │   ├── 画像+音声を結合
    │   └── 音声長に合わせた完璧な同期
    │
    ▼
解説動画 (MP4)
```

## 必要条件

### Python パッケージ

```bash
pip install -r requirements.txt
```

### 外部ツール

| ツール | インストール方法 |
|--------|------------------|
| Node.js | https://nodejs.org/ |
| Marp CLI | `npm install -g @marp-team/marp-cli` |
| Poppler | `apt-get install poppler-utils` (Ubuntu) |
| FFmpeg | `apt-get install ffmpeg` (Ubuntu) |

### 日本語フォント（Linux）

```bash
sudo apt-get install fonts-noto-cjk
```

## 使用方法

### 環境チェック

```bash
python workflow_check.py
```

### 動画生成

```bash
# テキストから直接
python main.py --input "ブログ記事テキスト..."

# ファイルから
python main.py --file article.txt

# URLから
python main.py --url "https://example.com/article"
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--input`, `-i` | ブログテキスト | - |
| `--file`, `-f` | テキストファイル | - |
| `--url`, `-u` | 記事URL | - |
| `--output`, `-o` | 出力ファイル名 | 自動生成 |
| `--slides`, `-s` | スライド枚数 | 6 |
| `--theme`, `-t` | Marpテーマ | gaia |
| `--voice`, `-v` | 音声タイプ | default |

### Marpテーマ

| テーマ | 説明 |
|--------|------|
| `gaia` | クリーンなデザイン（デフォルト） |
| `default` | シンプルな標準テーマ |
| `uncover` | モダンなプレゼン向け |

### 音声タイプ

| タイプ | 説明 |
|--------|------|
| `default` | 落ち着いた声 |
| `bright` | 明るい声 |
| `calm` | 穏やかな声 |
| `warm` | 温かみのある声 |

## 出力ファイル

```
output/
├── work/            # 一時ファイル
│   ├── slides.md    # Marp Markdown
│   └── slides.pdf   # 変換後PDF
├── images/          # スライド画像
│   ├── slide_01.png
│   └── ...
├── audio/           # 音声ファイル
│   ├── voice_01.wav
│   └── ...
└── videos/          # 最終動画
    └── video_YYYYMMDD_HHMMSS.mp4
```

## 従来方式との違い

| 項目 | 従来方式 | Marp方式 |
|------|---------|----------|
| 画像生成 | AI画像生成 | Marpスライド |
| テキスト可読性 | 低い（画像に埋め込み） | 高い（スライド形式） |
| 情報量 | 少ない（アート重視） | 多い（テキスト重視） |
| 音声同期 | ずれる場合あり | 正確に同期 |
| 生成速度 | 遅い（画像生成） | 速い（PDFレンダリング） |

## GitHub Actions対応

`.github/workflows/daily-blog-generation.yml`に以下が追加されています：

```yaml
- name: Install Marp CLI
  run: |
    npm install -g @marp-team/marp-cli

- name: Install poppler
  run: |
    sudo apt-get install -y poppler-utils ffmpeg fonts-noto-cjk
```

## トラブルシューティング

### Marp CLIが見つからない

```
RuntimeError: Marp CLI not found
```

→ `npm install -g @marp-team/marp-cli` を実行

### PDF変換エラー

```
RuntimeError: PDF to image conversion failed
```

→ `poppler-utils`がインストールされているか確認

### 文字化け（豆腐）

→ 日本語フォントをインストール: `apt-get install fonts-noto-cjk`

### 音声が生成されない

→ `GOOGLE_AI_API_KEY`環境変数が設定されているか確認

## ライセンス

MIT License
