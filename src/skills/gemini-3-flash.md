# Gemini 3 Flash Preview Skill

## 概要
Gemini 3 Flash Preview（思考モードオフ）を使用した高速コンテンツ処理スキル

## モデル情報
- **モデル名**: `gemini-3-flash-preview`
- **特徴**: 高速応答、バランスの取れた性能
- **用途**: SEO最適化、品質レビュー、軽量タスク
- **思考モード**: オフ（高速応答優先）

## API設定

### 基本的な使用方法
```python
from lib.gemini_client import GeminiClient

client = GeminiClient()

# 思考モードオフで高速応答
result = await client.generate_content(
    prompt=your_prompt,
    model=GeminiClient.MODEL_FLASH_3,  # gemini-3-flash-preview
    thinking_mode=False,  # 思考モードオフ
    temperature=0.5
)
```

### SEO最適化での使用
```python
result = await client.generate_content(
    prompt=seo_prompt,
    model=GeminiClient.MODEL_FLASH_3,
    thinking_mode=False,
    temperature=0.5  # 正確性重視
)
```

### 品質レビューでの使用
```python
result = await client.generate_content(
    prompt=review_prompt,
    model=GeminiClient.MODEL_FLASH_3,
    thinking_mode=False,
    enable_search=True,  # ファクトチェック用
    temperature=0.3      # 一貫性重視
)
```

## 思考モード設定

### 思考モードオフ（推奨）
```python
config = {
    "thinking_config": {"thinking_budget": 0}
}
```
- 応答時間: 3-5秒
- 用途: SEO、レビュー、構造化出力

### 思考モードオン
```python
config = {
    "thinking_config": {"thinking_budget": 1024}
}
```
- 応答時間: 10-30秒
- 用途: 複雑な分析、創造的タスク

## モデル比較

| モデル | 速度 | 精度 | 用途 |
|--------|------|------|------|
| gemini-3-pro-preview | 遅い | 最高 | コンテンツ生成 |
| gemini-3-flash-preview | 速い | 高い | SEO/レビュー |
| gemini-2.0-flash | 最速 | 中 | 簡単なタスク |

## 推奨パラメータ

### SEO最適化
```json
{
  "model": "gemini-3-flash-preview",
  "thinking_mode": false,
  "temperature": 0.5,
  "max_tokens": 8192
}
```

### 品質レビュー
```json
{
  "model": "gemini-3-flash-preview",
  "thinking_mode": false,
  "enable_search": true,
  "temperature": 0.3,
  "max_tokens": 8192
}
```

### 構造化出力（JSON）
```json
{
  "model": "gemini-3-flash-preview",
  "thinking_mode": false,
  "temperature": 0.2,
  "max_tokens": 4096
}
```

## プロンプト設計のベストプラクティス

### 1. 明確な出力形式を指定
```
【出力形式】
以下のJSON形式で出力してください：
```json
{
  "key": "value"
}
```
```

### 2. 評価基準を数値化
```
【評価基準】
1. 項目A（0-25点）
2. 項目B（0-25点）
```

### 3. ステップバイステップの指示
```
【処理手順】
Step 1: ...
Step 2: ...
Step 3: ...
```

## エラーハンドリング

```python
try:
    result = await client.generate_content(
        prompt=prompt,
        model=GeminiClient.MODEL_FLASH_3,
        thinking_mode=False
    )
except Exception as e:
    logger.error(f"Gemini 3 Flash error: {e}")
    # フォールバック処理
```

## レート制限
- RPM（1分あたりリクエスト数）: 60
- TPM（1分あたりトークン数）: 100,000
- 推奨: 連続呼び出し間に1秒の間隔

## 関連エージェント
- `seo-agent.md`: SEO最適化
- `review-agent.md`: 品質レビュー

## パフォーマンス指標
| タスク | 応答時間 | 精度 |
|--------|----------|------|
| SEO最適化 | 3-5秒 | 85%+ |
| 品質レビュー | 5-8秒 | 90%+ |
| JSON生成 | 2-4秒 | 95%+ |
