# Gemini Research Skill - 7日以内最新情報限定版

## 概要
Multi-Search（3回検索、メイン）とDeep Research（週1回）を使用した情報収集スキル。
**必ず7日以内の最新情報のみを収集**します。

## 設計方針

| 曜日 | リサーチ方法 | 検索回数 | 処理時間 |
|-----|-------------|----------|---------|
| **月〜土** | Multi-Search (3回検索) | 3回 | 約10秒 |
| **日曜日** | Deep Research API | 1回 | 約5分 |
| **手動指定** | 選択可能 | - | - |
| **フォールバック** | Multi-Search | 3回 | 約10秒 |

**理由**: Deep ResearchはRPM 1/分の厳しいレート制限があるため、
週1回（日曜日）のみ使用し、通常はMulti-Search（3回検索）でDeep Research簡易版として動作します。

## Multi-Search（3回検索）パターン

3つの異なる視点から検索を行い、情報を統合します：

| 検索 | 視点 | 目的 |
|------|------|------|
| 1回目 | 最新ニュース・動向 | 直近の発表・ニュースを収集 |
| 2回目 | 専門家の見解・研究 | 専門家意見・研究成果を収集 |
| 3回目 | 事例・統計・トレンド | 具体的データ・事例を収集 |

## 重要: 課金要件

**Deep Research APIは有料プラン専用です。**

| 項目 | 要件 |
|------|------|
| 課金設定 | [Google AI Studio](https://aistudio.google.com/) で Billing 有効化が必須 |
| 料金体系 | Gemini 3 Pro レート |
| 無料枠 | 使用不可 → 自動的にGoogle Search Toolにフォールバック |
| 必須パラメータ | `background=True`（storeはデフォルトTrue） |

## レート制限（重要）

| Tier | RPM | 備考 |
|------|-----|------|
| Free | 0 | 使用不可 |
| Tier 1 | **1** | 1リクエスト/分の厳しい制限 |
| Tier 2 | 1 | 同上 |

**注意**: レート制限超過時は400エラーが返されます。自動的にGoogle Searchにフォールバックします。

## 必須ライブラリバージョン

**重要**: Interactions API (Deep Research) を使用するには以下が必要です：
```
google-genai>=1.56.0
```

古いバージョン（0.5.0等）では400エラーが発生し、自動的にGoogle Searchにフォールバックします。

## 重要な制約条件

### 7日以内限定ルール（必須遵守）
```python
from lib.timezone import now_jst, format_date
from datetime import timedelta

MAX_AGE_DAYS = 7

# 日付範囲を計算（JST基準）
today = now_jst()
start_date = (today - timedelta(days=MAX_AGE_DAYS)).strftime("%Y年%m月%d日")
end_date = today.strftime("%Y年%m月%d日")

# クエリに日付制約を必ず含める
query = f"""
【重要】本日は{end_date}です。
必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。
7日より古い情報は絶対に含めないでください。
"""
```

## API設定

### Deep Research（7日以内限定クエリ）
```python
from lib.timezone import now_jst, format_date
from datetime import timedelta

# 日付範囲を計算
today = now_jst()
start_date = (today - timedelta(days=7)).strftime("%Y年%m月%d日")
end_date = today.strftime("%Y年%m月%d日")

# 日付制約付きクエリを構築
research_query = f"""
【重要】本日は{end_date}です。
必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。

【調査トピック】{topic}

【調査要件】
- 7日より古い情報は絶対に含めない
- 各情報に日付を明記（YYYY年MM月DD日形式）
- ソースURLを必ず含める（https://完全URL）
- 最低5つ以上の信頼できるソースを使用
"""

# 公式ドキュメント準拠: 同期クライアントを使用
# https://ai.google.dev/gemini-api/docs/deep-research
interaction = client.interactions.create(
    input=research_query,
    agent="deep-research-pro-preview-12-2025",
    background=True
)

# ポーリングで完了を待機
while True:
    interaction = client.interactions.get(interaction.id)
    if interaction.status == "completed":
        print(interaction.outputs[-1].text)
        break
    elif interaction.status == "failed":
        print(f"Research failed: {interaction.error}")
        break
    time.sleep(10)
```

### Multi-Search（メイン・月〜土曜日）
```python
from lib.timezone import format_date
from lib.gemini_client import GeminiClient

client = GeminiClient()

# Multi-Search（3回検索）でDeep Research簡易版
result = await client.multi_search_research(
    topic=topic_info['name'],
    topic_info=topic_info,
    date_range={"start": start_date, "end": end_date},
    search_count=3  # デフォルト: 3回
)

# 結果
content = result.content  # 統合されたリサーチ結果
sources = result.sources  # 全ソースURL一覧
search_count = result.search_count  # 実行した検索回数
```

### 単発Google Search（参考）
```python
# 1回のみの検索＆生成
result = await client.search_and_generate(
    query=f"{topic} 最新 {today_jst} 過去7日間",
    generation_prompt=research_query
)
content = result.text
sources = result.grounding_sources
```

## リサーチクエリテンプレート

### トレンド調査（7日以内限定）
```
【重要】本日は{today}です。
必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。

【調査依頼】{topic}に関する最新動向

調査期間: {start_date}〜{end_date}（7日間）
優先言語: 日本語、英語

必要な情報:
1. 最新ニュース・発表（日付必須）
2. 業界動向・市場分析（日付必須）
3. 専門家の見解（発表日付必須）
4. 統計データ（調査日付必須）
5. 今後の予測

出力要件:
- 各情報のソースURL必須（https://完全URL）
- 日付情報を「YYYY年MM月DD日」形式で明記
- 7日より古い情報は含めない
- 最低5つ以上の信頼できるソースを使用
```

## ソース収集の必須要件

### URLの記載形式
```markdown
- [ソースタイトル](https://example.com/full/url/path)
- [記事タイトル2](https://another-source.com/article)
```

### 必須チェックリスト
- [ ] 7日以内の情報のみか
- [ ] 各情報に日付が明記されているか
- [ ] ソースURLが完全形式か（https://で始まる）
- [ ] 最低5つ以上のソースがあるか
- [ ] 信頼できるソースを優先しているか

## エラーハンドリング・フォールバック
```python
async def run_research(topic_id: str, use_deep_research: bool = False) -> dict:
    """
    Deep Research失敗時は自動的にMulti-Searchにフォールバック
    """
    if use_deep_research:
        try:
            result = await client.deep_research(query)
            return result
        except Exception as e:
            # フォールバック: Multi-Search（3回検索）
            logger.error(f"Deep Research failed: {e}")
            logger.info("Falling back to Multi-Search...")
            use_deep_research = False

    # Multi-Search（デフォルト）
    result = await client.multi_search_research(
        topic=topic_info['name'],
        topic_info=topic_info,
        date_range=date_range,
        search_count=3
    )
    return result
```

## 関連スキル
- `timezone.md`: JST日時処理
- `gemini-content.md`: 記事生成（引用元付き）
