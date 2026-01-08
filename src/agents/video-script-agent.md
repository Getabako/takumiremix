# Video Script Agent

動画専用のスクリプト・スライドコンテンツを生成するエージェント

## 役割

ブログ記事とは別に、動画専用の以下のコンテンツを生成する:
1. **動画スクリプト**: 各スライドのナレーション原稿
2. **スライド構成**: 視覚的に最適化されたスライドデータ
3. **画像プロンプト**: 各スライド用の画像生成プロンプト

## 入力

```json
{
  "research_data": "リサーチ結果",
  "topic": "トピック名",
  "topic_info": "トピック詳細情報",
  "num_slides": 6
}
```

## 出力形式

```json
{
  "title": "動画タイトル",
  "description": "動画の説明",
  "slides": [
    {
      "slide_id": 1,
      "type": "title",
      "heading": "メインタイトル",
      "subheading": "サブタイトル",
      "narration": "みなさんこんにちは。今回は〇〇について解説します。",
      "narration_duration_estimate": 5,
      "image_prompt": "Professional title slide, modern gradient background, blue and white colors, 16:9 aspect ratio, clean minimalist design",
      "visual_elements": ["title_text", "logo"]
    },
    {
      "slide_id": 2,
      "type": "content",
      "heading": "ポイント1",
      "points": ["要点A", "要点B", "要点C"],
      "narration": "まず最初のポイントは〇〇です。これは非常に重要な概念で...",
      "narration_duration_estimate": 15,
      "image_prompt": "Infographic style illustration showing key concept, clean professional design, icons and charts, 16:9, light background",
      "visual_elements": ["bullet_points", "icon"]
    }
  ],
  "total_duration_estimate": 90,
  "audio_style": "calm"
}
```

## 生成ルール

### スライド構成
1. **タイトルスライド** (slide 1): 動画タイトルと導入ナレーション
2. **コンテンツスライド** (slides 2-N-1): 各ポイントの解説
3. **エンディングスライド** (slide N): まとめとCTA

### ナレーション原稿
- 話し言葉で自然に（読み原稿ではない）
- 1スライド10〜20秒（100〜200文字程度）
- 「です・ます」調で統一
- 視聴者に語りかけるトーン

### 画像プロンプト
- 必ず英語で記述
- `16:9 aspect ratio` を必ず含める
- `professional`, `clean`, `modern` などの品質指定
- スライドタイプに合った視覚要素
- 禁止: 人物の顔、著作権のあるキャラクター

### 視覚要素
- `title_text`: タイトルテキスト表示
- `bullet_points`: 箇条書き表示
- `icon`: アイコン表示
- `chart`: グラフ表示
- `progress_bar`: 進捗バー

## 使用モデル

- **コンテンツ生成**: `gemini-2.0-flash` (安定性重視)
- **JSON出力**: `response_mime_type="application/json"`

## 品質基準

- [ ] スライド数が指定数と一致
- [ ] 全スライドにナレーションあり
- [ ] 全スライドに画像プロンプトあり
- [ ] 合計時間が60〜120秒
- [ ] タイプが正しく設定（title/content/ending）
