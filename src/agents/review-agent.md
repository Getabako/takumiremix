# Review Agent

## 役割
Gemini 3 Flash Preview（思考モードオフ）を使用して生成コンテンツの品質チェックを高速に実行する

## 使用モデル
- **Primary**: `gemini-3-flash-preview`（思考モードオフ）
- **Fact-check**: Google Search Tool有効

## 処理フロー

```
入力: 記事データ
        ↓
   情報の正確性チェック
   - Google Search でファクトチェック
   - 誤解を招く表現の検出
        ↓
   読みやすさ評価
   - 論理的な流れ
   - 段落構成
   - 専門用語の説明
        ↓
   オリジナリティ評価
   - 独自の視点
   - 実用的な価値
        ↓
   品質スコアリング
   - 4項目×25点 = 100点満点
        ↓
   必要に応じて修正適用
        ↓
出力: レビュー済み記事 + 品質スコア
```

## API呼び出し
```python
from lib.gemini_client import GeminiClient

client = GeminiClient()
result = await client.generate_content(
    prompt=review_prompt,
    model=GeminiClient.MODEL_FLASH_3,  # gemini-3-flash-preview
    thinking_mode=False,  # 思考モードオフ
    enable_search=True,   # ファクトチェック用
    temperature=0.3       # 一貫性重視
)
```

## 入力
```json
{
  "content": "記事本文",
  "title": "記事タイトル",
  "topic": "トピックID"
}
```

## 出力
```json
{
  "content": "レビュー・修正済み記事",
  "quality_score": 85,
  "scores": {
    "accuracy": 22,
    "readability": 21,
    "originality": 20,
    "seo_quality": 22
  },
  "issues": [
    {
      "type": "warning",
      "location": "第2段落",
      "description": "問題の説明",
      "suggestion": "修正提案"
    }
  ],
  "strengths": ["強み1", "強み2"],
  "status": "approved",
  "reviewed": true,
  "model_used": "gemini-3-flash-preview"
}
```

## 品質基準

| スコア | 判定 | アクション |
|--------|------|-----------|
| 90-100 | 優秀 | 即時公開可 |
| 75-89 | 良好 | 公開可（軽微な修正推奨） |
| 60-74 | 要改善 | 修正後再レビュー |
| 0-59 | 不合格 | 大幅な書き直し必要 |

## ステータス
- `approved`: 公開可能
- `needs_revision`: 要修正
- `rejected`: 却下

## 評価項目詳細

### 1. 情報の正確性 (25点)
- 事実に基づいているか
- 誤解を招く表現がないか
- 出典が明確か

### 2. 読みやすさ・構成 (25点)
- 論理的な流れ
- 適切な段落分け
- 専門用語の説明

### 3. オリジナリティ・価値 (25点)
- 独自の視点や洞察
- 読者にとっての実用性
- 具体的な事例やデータ

### 4. SEO・技術品質 (25点)
- タイトルの魅力
- 見出し構造
- メタデータの適切さ

## 設定
```json
{
  "model": "gemini-3-flash-preview",
  "thinking_mode": false,
  "enable_search": true,
  "temperature": 0.3,
  "max_tokens": 8192
}
```

## 引用元・参考文献チェック（必須）

### チェック項目
1. **参考文献セクションの有無**: 記事末尾に「参考文献・引用元」セクションがあるか
2. **ソースの数**: 最低3つ以上の引用元が記載されているか
3. **リンク形式**: URLがマークダウンリンク形式 `[タイトル](URL)` で記載されているか
4. **sources-section**: `<div class="sources-section">` タグで囲まれているか
5. **免責事項**: 「この記事はAIによって生成されました。」の記載があるか

### 自動修正対象
- 参考文献セクションがない場合 → ソースデータから自動生成
- リンク形式が不正な場合 → 正しい形式に変換
- sources-sectionタグがない場合 → 追加

### 不合格条件
- 参考文献セクションが完全に欠落している場合
- 有効なソースが1つもない場合

## デザインガイドライン準拠チェック

### チェック項目
1. **絵文字の使用**: タイトル、見出し、本文に絵文字がないか
2. **AIっぽい表現**: 「革新的」「画期的」「驚くべき」などの陳腐な表現がないか
3. **トーン**: 押し付けがましい表現がないか
4. **見出し構造**: 適切なH2/H3構造になっているか

### 自動修正対象
- 絵文字 → 削除
- 「さあ、始めましょう」 → 削除
- 過度な感嘆符 → 句点に変更
- 「革新的な」 → 具体的な表現に置換

### 不合格条件
- 絵文字が3つ以上含まれる場合
- AIっぽい表現が5箇所以上ある場合
- 見出し構造が不適切な場合

## 関連スキル
- `gemini-3-flash.md`: Gemini 3 Flash Preview操作

## パフォーマンス
- 応答時間: 約5-8秒（検索込み、思考モードオフ）
- 精度: 品質スコア判定の一貫性95%以上
