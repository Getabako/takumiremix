# Image Agent

## 役割
ブログ記事に適した**アニメ風イラスト**をGemini 2.5 Flash imageモデルで生成する。
**スマートプロンプト機能**により、記事タイトルを分析して内容に合った具体的で多様な**人物入り画像**を生成します。

## アニメスタイル仕様（重要）
- **アスペクト比**: 16:9 横長（ワイドスクリーン）必須 - 外枠含め完全な16:9
- **必須**: 各画像にアニメ風の人物キャラクターを含める
- **スタイル**: モダンな日本のアニメスタイル（クリーンな線、表情豊か）
- **キャラクター**: 多様性あり（下記参照）
- **禁止**: ちびキャラ、過度にカートゥーン風なスタイル、正方形画像、縦長画像

## キャラクター多様性（必須）

毎回ランダムに異なるキャラクターを生成して多様性を確保：

### 性別（ランダム選択）
- male（男性）
- female（女性）

### 年齢（ランダム選択）
- child（8-12歳）
- teenager（13-17歳）
- young adult（18-25歳）
- adult（26-40歳）
- middle-aged（41-55歳）
- senior（56歳以上）

### 外見（ランダム選択）
- with short hair
- with long hair
- with glasses
- with a friendly smile
- with a thoughtful expression
- with casual clothing
- with business casual attire
- with professional attire

**重要**: 毎回異なる組み合わせを使用し、特定のタイプに偏らないようにする

## 使用API
- **Primary**: Gemini 2.5 Flash image (`gemini-2.5-flash-image`)
- **Analysis**: Gemini 2.0 Flash（記事分析・プロンプト最適化用）

## 重要な設定（必須遵守）

### response_modalities の指定
画像を生成するには、必ず `response_modalities=["IMAGE"]` を設定する必要があります。
この設定がないと、テキストのみが返され画像が生成されません。

```python
from google.genai import types

config = types.GenerateContentConfig(
    response_modalities=["IMAGE"],  # 必須
    temperature=1.0,
    top_p=0.95,
    top_k=40
)
```

### 画像検証ルール
- 最低サイズ: 10KB以上（10KB未満は破損と判断）
- PNGヘッダー検証: `\x89PNG\r\n\x1a\n`

## スマートプロンプト機能（重要）

記事タイトルを分析して、内容に合った**アニメ風キャラクター入り**の画像を生成します。

### 分析内容
Gemini 2.0 Flashで記事タイトルを分析し、以下を自動生成：
- **main_character**: アニメ風キャラクターの外見・服装・表情
- **character_action**: キャラクターの動作やポーズ
- **visual_metaphor**: 記事の核心を表す視覚的メタファー（キャラクターと統合）
- **mood**: 感情的トーン（明るい、落ち着いた、ダイナミックなど）
- **key_elements**: キャラクター周辺に含める具体的な視覚要素（3-4個）
- **background_style**: 背景スタイル
- **lighting**: ライティングスタイル

### 構図バリエーション
毎回ランダムに異なる構図を選択：
- centered focal point（中央配置）
- dynamic diagonal composition（対角線構図）
- layered depth（奥行きのある構図）
- radial arrangement（放射状配置）
- asymmetric balance（非対称バランス）
- grid-based structured layout（グリッド構造）
- organic flowing shapes（有機的な流れ）
- geometric abstract pattern（幾何学抽象）

## 処理フロー
```
1. 記事情報を受け取る
2. 【スマートプロンプト】Gemini Flashで記事タイトルを分析
3. 分析結果から具体的な視覚要素を抽出
4. トピック別カラースキームを適用
5. ランダムな構図スタイルを選択
6. 最適化されたプロンプトを構築
7. response_modalities=["IMAGE"] を設定
8. Gemini 2.5 Flash imageで画像生成
9. 画像データを検証（サイズ・ヘッダー）
10. 有効な画像のみを保存
11. 生成結果を返却
```

## 入力
```json
{
  "article_title": "記事タイトル",
  "article_summary": "記事概要",
  "image_prompts": {
    "hero": "ヒーロー画像プロンプト",
    "sections": ["セクション画像プロンプト1"]
  },
  "style_guide": {
    "color_scheme": "professional_blue",
    "style": "clean_minimal"
  }
}
```

## デザインガイドライン（必須遵守）

### 禁止カラー
- **紫色系の禁止**: purple, violet, lavender, magenta は使用しない
- **派手な色の禁止**: ネオンカラー、蛍光色は避ける

### 推奨カラー
```
Primary: Deep Navy (#1a1a2e) - 信頼性・知性
Accent: Professional Blue (#0f3460) - 落ち着き
Background: White/Light Gray (#f7fafc) - クリーンさ
Text: Dark Gray (#2d3748) - 読みやすさ
```

### トピック別カラースキーム（自動適用）

| トピックID | カラー | 名前 |
|-----------|--------|------|
| `psychology` | #2b6cb0 / #4299e1 | calming blue |
| `education` | #2f855a / #48bb78 | growth green |
| `startup` | #c05621 / #ed8936 | energetic orange |
| `investment` | #744210 / #d69e2e | trustworthy gold-brown |
| `ai_tools` | #1a365d / #3182ce | tech navy blue |
| `inclusive_education` | #285e61 / #38b2ac | supportive teal |
| `weekly_summary` | #553c9a / #805ad5 | insightful indigo |

### 画像スタイル
- **アニメ風イラスト**: モダンな日本のアニメスタイル
- **キャラクター中心**: 親しみやすい人物キャラクターを必ず含める
- **プロフェッショナル**: ビジネスに適した雰囲気を維持
- **明るく読みやすい**: テキストが映える余白を確保

### キャラクター設定
1. **若いプロフェッショナル/学生**: 記事のターゲット層を反映
2. **表情豊か**: 記事の雰囲気に合わせた表情
3. **現代的な服装**: カジュアルビジネス or カジュアル
4. **アクション/ポーズ**: 記事内容に関連した動作

### 避けるべき要素
1. 派手なグラデーション背景
2. 紫系の配色
3. 過度な装飾やアイコン
4. ちびキャラ・デフォルメが強すぎるスタイル
5. テキストを含む画像
6. 著作物・ブランドロゴ

## 出力
```json
{
  "status": "success",
  "hero": {
    "type": "hero",
    "title": "記事タイトル",
    "prompt": "生成に使用したプロンプト",
    "model": "gemini-2.5-flash-image",
    "images": [
      {
        "file_path": "/output/images/hero_20251229_123456_0.png",
        "filename": "hero_20251229_123456_0.png",
        "size_bytes": 123456
      }
    ],
    "generated_at": "20251229_123456"
  },
  "sections": [],
  "total_images": 1
}
```

## 画像仕様
| 用途 | サイズ | アスペクト比 | 形式 |
|------|--------|--------------|------|
| ヒーロー画像 | 1200x630 | 1.91:1 | PNG |
| OGP画像 | 1200x630 | 1.91:1 | PNG |
| 本文画像 | 800x450 | 16:9 | PNG/WebP |

## プロンプトテンプレート

### ヒーロー画像（アニメ風・16:9横長）
```
Create a hero illustration in MODERN JAPANESE ANIME STYLE for a blog article about [TOPIC].

IMAGE FORMAT (CRITICAL):
- Aspect ratio: 16:9 WIDESCREEN (landscape orientation, like 1920x1080)
- MUST be horizontally wide, NOT square, NOT portrait

CHARACTER (REQUIRED):
Main Character: [young professional/student with friendly expression]
Action/Pose: [engaged with topic - reading, working, explaining]

Style Requirements:
- WIDESCREEN 16:9 aspect ratio
- Modern Japanese anime art style (clean lines, expressive eyes)
- Professional and polished appearance
- Character should be the focal point

Colors: [CATEGORY_COLOR] as accent, warm skin tones, clean background
Composition: Character slightly off-center with space for text overlay
Avoid: purple colors, chibi style, text in image, overly cartoonish, square format
```

### セクション画像（アニメ風）
```
Create a section illustration in ANIME STYLE representing [CONCEPT].

CHARACTER (REQUIRED):
- Anime-style character interacting with the concept
- Relatable and approachable appearance

Style: clean anime art, soft colors, educational mood
Colors: [CATEGORY_COLOR], light background
Avoid: purple colors, complex patterns, text, chibi style
```

## API呼び出しパターン
```python
from lib.gemini_client import GeminiClient

client = GeminiClient()

# スマートプロンプトでブログ用画像生成（推奨）
result = await client.generate_blog_image(
    title="AIツールの最新動向2025",
    summary="2025年のAIツールトレンドを詳しく解説",
    style="clean, minimal, professional",
    image_type="hero",
    topic_id="ai_tools",  # カラースキーム自動適用
    use_smart_prompt=True  # 記事分析を有効化（デフォルト）
)

# シンプルプロンプトで画像生成（従来方式）
result = await client.generate_blog_image(
    title="記事タイトル",
    summary="記事概要",
    use_smart_prompt=False  # 分析をスキップ
)
```

### スクリプトからの使用
```python
from scripts.generate_image import generate_images

result = await generate_images(
    article={
        "title": "記事タイトル",
        "summary": "記事概要",
        "topic_id": "ai_tools"
    },
    use_smart_prompt=True
)
```

## 品質チェックリスト
- [ ] 紫色系が含まれていないか
- [ ] 派手すぎないか
- [ ] プロフェッショナルな雰囲気か
- [ ] テキストが映える背景か
- [ ] 記事内容と関連しているか

## ドキュメント更新義務（必須遵守）

このエージェントで機能追加・修正・エラー対応を行った場合、**必ずREADME.mdを最新仕様に更新すること**。

### 更新すべき内容
1. **最新アップデート**: 変更内容を記載
2. **トラブルシューティング**: 画像生成エラーと解決策を追加
3. **内部動作フロー**: 画像生成処理の説明

### 内部動作フロー図
```
┌────────────────────────────────────┐
│ generate_images(article)           │
└─────────────────┬──────────────────┘
                  │
        ┌─────────▼─────────────────┐
        │ response_modalities=      │
        │ ["IMAGE"] を設定（必須）  │
        └─────────┬─────────────────┘
                  │
        ┌─────────▼─────────────────┐
        │ Gemini 2.5 Flash image    │
        │ で画像生成                │
        └─────────┬─────────────────┘
                  │
        ┌─────────▼─────────────────┐
        │ 画像サイズ検証            │
        │ (最低1KB以上)             │
        └─────────┬─────────────────┘
                  │
          有効？ ─┴─ 無効？
          │           │
          │    ┌──────▼──────────────┐
          │    │ 警告ログ出力        │
          │    │ "Image too small"   │
          │    └──────┬──────────────┘
          │           │
    ┌─────▼───────────▼─────────────┐
    │ output/images/ に保存         │
    └─────────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │ publish時にPNGヘッダー検証 │
        │ (最低10KB以上)            │
        └─────────────┬─────────────┘
                      │
    ┌─────────────────▼─────────────┐
    │ docs/assets/images/ にコピー  │
    └───────────────────────────────┘
```
