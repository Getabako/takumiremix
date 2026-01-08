# Quality Evaluation Skill

## 概要
ブログ記事、スライド、動画の品質を厳格に評価するスキル。
95%以上の合格ラインを維持するために使用。

## 評価基準（3倍厳格）

### 合格ライン
- **総合**: 95%以上
- **各カテゴリ**: 95%以上（推奨）

### 減点方式
従来の約3倍の減点幅を適用:

```python
# 例: 文字数チェック
if word_count >= 10000:
    score += 8  # 満点
elif word_count >= 8000:
    score += 5.6  # 70%（従来なら90%相当）
elif word_count >= 5000:
    score += 3.2  # 40%（従来なら70%相当）
else:
    score += 0  # 0点
```

## API

```python
from scripts.quality_evaluator import QualityEvaluator, evaluate_workflow

# 同期的な評価
evaluator = QualityEvaluator()
result = evaluator.evaluate_all(article, slides_data, video_data)

# 非同期評価
result = await evaluate_workflow(article, slides_data, video_data)
```

## 評価関数

### evaluate_article(article) → QualityResult
```python
result = evaluator.evaluate_article({
    "title": "記事タイトル",
    "content": "記事本文...",
    "word_count": 10000,
    "seo_score": 85,
    "sources": [{"title": "Source", "url": "https://..."}]
})
```

### evaluate_slides(slides_data) → QualityResult
```python
result = evaluator.evaluate_slides({
    "slides": [...],
    "slide_images": ["path/to/slide_01.png", ...],
    "markdown_path": "path/to/slides.md",
    "pdf_path": "path/to/slides.pdf"
})
```

### evaluate_video(video_data) → QualityResult
```python
result = evaluator.evaluate_video({
    "videos": {
        "standard": {
            "path": "path/to/video.mp4",
            "resolution": "1920x1080",
            "duration": 60,
            "size_bytes": 15000000,
            "has_audio": True
        }
    },
    "narration": {
        "script": "ナレーションテキスト...",
        "audio_size_bytes": 250000
    }
})
```

## 品質向上のための推奨事項

### ブログ記事
- 10,000文字以上を目標に
- 見出し（##）を5つ以上使用
- 箇条書きを適切に使用
- 絵文字は絶対に使用しない

### スライド
- 10-15枚の範囲に収める
- 1スライド100文字以内
- 全スライドに画像を配置
- タイトル→内容→エンディングの構成

### 動画
- 1920x1080の解像度
- TTS音声を必ず含める
- 2MB-100MBのファイルサイズ
- エラーなく生成完了

## 再試行パターン

```python
MAX_RETRIES = 3
PASS_THRESHOLD = 0.95

for attempt in range(MAX_RETRIES):
    result = generate_content()
    quality = evaluator.evaluate_all(result)

    if quality["overall"]["passed"]:
        break  # 合格

    # 問題点に基づいて調整
    if "文字数" in str(quality["all_issues"]):
        # 記事を拡充
        pass
    if "スライド枚数" in str(quality["all_issues"]):
        # スライドを追加
        target_slides += 2
```

## ログ出力

```python
logger.info(f"Quality score: {result['overall']['percentage']}%")
logger.info(f"Passed: {result['overall']['passed']}")

for issue in result['all_issues']:
    logger.warning(f"Issue: {issue}")
```
