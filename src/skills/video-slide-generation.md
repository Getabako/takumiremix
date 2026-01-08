# Video Slide Generation Skill

動画用スライド画像を確実に生成するスキル

## 概要

各スライドの画像を生成し、**必ず全スライドに画像が存在する**ことを保証する。
画像生成に失敗した場合は、フォールバック画像を生成する。

## 入力

```json
{
  "slides": [
    {
      "slide_id": 1,
      "type": "title",
      "heading": "タイトル",
      "image_prompt": "English image prompt..."
    }
  ],
  "topic_id": "ai_tools",
  "output_dir": "output/videos/{timestamp}"
}
```

## 出力

```json
{
  "status": "success",
  "slides": [
    {
      "slide_id": 1,
      "image_path": "/path/to/slide_01.png",
      "image_base64": "data:image/png;base64,...",
      "generation_method": "gemini" | "fallback"
    }
  ],
  "total_images": 6,
  "successful_generations": 6,
  "fallback_count": 0
}
```

## 処理フロー

```
入力スライドリスト
    │
    ▼
[For each slide]
    ├── 1. Gemini画像生成を試行
    │       └── 成功 → 画像保存
    │       └── 失敗 → フォールバックへ
    │
    ├── 2. フォールバック画像生成
    │       └── グラデーション背景 + テキスト
    │
    └── 3. Base64エンコード
            └── data:image/png;base64,...
    │
    ▼
全スライドに画像が存在することを検証
    │
    ▼
結果を返却（slides.length === images.length 保証）
```

## 画像生成ルール

### Gemini画像生成
- モデル: `gemini-2.5-flash-preview-05-20`
- 設定: `response_modalities=["IMAGE"]`
- リサイズ: 1920x1080 (16:9)
- 形式: PNG

### フォールバック画像
画像生成に失敗した場合、以下のフォールバック画像を生成:

```python
def create_fallback_image(slide, topic_id):
    """フォールバック画像を生成"""
    # トピック別カラースキーム
    colors = {
        "psychology": ("#2b6cb0", "#4299e1"),
        "education": ("#2f855a", "#48bb78"),
        "startup": ("#c05621", "#ed8936"),
        "investment": ("#744210", "#d69e2e"),
        "ai_tools": ("#1a365d", "#3182ce"),
        "inclusive_education": ("#285e61", "#38b2ac"),
    }

    primary, accent = colors.get(topic_id, ("#1a1a2e", "#4a4a6e"))

    # グラデーション背景 + タイトルテキスト
    img = create_gradient_image(1920, 1080, primary, accent)
    draw_text(img, slide["heading"], center=True)

    return img
```

## 重要な保証

1. **スライド数 = 画像数**: 必ず一致させる
2. **全画像が有効**: Base64エンコード前に検証
3. **最低サイズ保証**: 1920x1080
4. **形式統一**: PNG形式

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| Gemini API エラー | フォールバック画像を生成 |
| レート制限 | 1秒待機後リトライ（最大3回） |
| 画像サイズ不正 | リサイズして修正 |
| Base64変換失敗 | フォールバック画像で再試行 |

## 使用例

```python
from skills.video_slide_generation import generate_slide_images

result = await generate_slide_images(
    slides=video_script["slides"],
    topic_id="ai_tools",
    output_dir=Path("output/videos/20260108")
)

# 結果検証
assert len(result["slides"]) == len(video_script["slides"])
for slide in result["slides"]:
    assert slide["image_base64"].startswith("data:image/png;base64,")
```
