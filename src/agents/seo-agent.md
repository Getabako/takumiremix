# SEO Agent

## 役割
Gemini 3 Flash Preview（思考モードオフ）を使用してブログ記事のSEO最適化を高速に行う

## 使用モデル
- **Primary**: `gemini-3-flash-preview`（思考モードオフ）
- **特徴**: 高速応答、SEO分析に最適化

## 処理フロー

```
入力: 記事データ（content, title, topic）
        ↓
   タイトル最適化
   - 60文字以内
   - キーワード前方配置
   - クリック誘導表現
        ↓
   メタディスクリプション生成
   - 120文字以内
   - 価値提案を明確に
        ↓
   見出し構造最適化
   - H2/H3の論理構造
   - キーワード自然配置
        ↓
   本文最適化
   - キーワード密度調整
   - 段落分け改善
        ↓
出力: 最適化された記事 + SEOスコア
```

## API呼び出し
```python
from lib.gemini_client import GeminiClient

client = GeminiClient()
result = await client.generate_content(
    prompt=seo_prompt,
    model=GeminiClient.MODEL_FLASH_3,  # gemini-3-flash-preview
    thinking_mode=False,  # 思考モードオフ
    temperature=0.5       # 正確性重視
)
```

## 入力
```json
{
  "content": "記事本文（Markdown）",
  "title": "元のタイトル",
  "topic": "トピックID"
}
```

## 出力
```json
{
  "title": "最適化されたタイトル",
  "description": "メタディスクリプション",
  "content": "最適化された記事本文",
  "seo_score": 85,
  "keywords": ["キーワード1", "キーワード2"],
  "improvements": ["改善点1", "改善点2"],
  "optimized": true,
  "model_used": "gemini-3-flash-preview"
}
```

## SEOチェックリスト
- [x] タイトル60文字以内
- [x] メタディスクリプション120文字以内
- [x] H1タグは1つのみ
- [x] 主要キーワードがタイトル前半に
- [x] キーワード密度1.5-3%
- [x] 画像全てにalt属性
- [x] 内部リンク・外部リンク提案

## 設定
```json
{
  "model": "gemini-3-flash-preview",
  "thinking_mode": false,
  "temperature": 0.5,
  "max_tokens": 8192
}
```

## デザインガイドライン準拠チェック

### 最適化時に確認する項目
1. **絵文字チェック**: タイトル、メタディスクリプションに絵文字がないか
2. **表現チェック**: AIっぽい陳腐な表現がないか
3. **タイトル長**: 60文字以内か
4. **ディスクリプション長**: 120文字以内か

### 修正が必要な表現（自動置換）
- 「革新的」→ 具体的な表現に
- 「画期的」→ 具体的なメリットに
- 「驚くべき」→ 削除または具体化
- 絵文字 → 削除

## 関連スキル
- `gemini-3-flash.md`: Gemini 3 Flash Preview操作

## パフォーマンス
- 応答時間: 約3-5秒（思考モードオフ）
- 精度: SEOスコア平均80点以上
