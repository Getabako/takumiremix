# Deep Research Agent

## 役割
Gemini Deep Research APIを使用して、**7日以内の最新情報のみ**を包括的に調査する。
**日曜日は6トピックを横断した「週間トレンド総括」記事を生成**する。

## 使用タイミング（重要）

| 実行タイミング | リサーチ方法 | 内容 |
|--------------|-------------|------|
| **日曜日（自動）** | Deep Research API | **週間総括**（6トピック横断） |
| **手動指定時** | Deep Research API | 単一トピック調査 |
| **それ以外の曜日** | Multi-Search 3回検索（別エージェント） | 単一トピック調査 |

**設計方針**: Deep Researchは週1回（日曜日）のみ使用し、6トピックを横断した週間総括を生成。
通常はMulti-Search（3回検索）を使用します。これはRPM 1/分の厳しいレート制限と処理時間（約5分）を考慮した設計です。

## 週間総括（日曜日専用）

日曜日は `weekly_summary` トピックとして、6つの分野を横断した週間総括記事を生成します：

| 分野 | 曜日 | キーワード |
|------|------|-----------|
| 心理学・メンタルヘルス | 月 | 心理学、カウンセリング、ストレス |
| 教育・学習科学 | 火 | 教育、EdTech、学習法 |
| 起業・スタートアップ | 水 | 起業、ビジネスモデル、資金調達 |
| 投資・金融リテラシー | 木 | 投資、NISA、資産形成 |
| AIツール・技術動向 | 金 | AI、ChatGPT、Gemini |
| インクルーシブ教育・多様な学び | 土 | 不登校、発達障害、フリースクール |

### 週間総括の構成
1. 今週のハイライト（全体要約）
2. 各分野の注目ニュース（分野ごとに1〜2件）
3. 分野横断的なトレンド分析
4. 来週の注目ポイント

## 重要: 課金要件

**Deep Research APIは有料プラン専用です。**

| 項目 | 要件 |
|------|------|
| 課金設定 | [Google AI Studio](https://aistudio.google.com/) で Billing 有効化が必須 |
| 料金体系 | Gemini 3 Pro レート（入力$1.25/100万トークン、出力$5.00/100万トークン） |
| 無料枠 | 使用不可 → 自動的にGoogle Search Toolにフォールバック |
| 必須パラメータ | `background=True`（storeはデフォルトTrue） |

## レート制限（重要）

| Tier | RPM (Requests Per Minute) | TPM (Tokens Per Minute) |
|------|---------------------------|-------------------------|
| Free | 使用不可 | - |
| Tier 1 | **1** | 32,000 |
| Tier 2 | 1 | 32,000 |

**注意**: Deep ResearchのRPMは**1リクエスト/分**と非常に厳しい制限があります。
レート制限に達すると400エラー「Request contains an invalid argument」が返されます。
この場合は自動的にGoogle Search Toolにフォールバックします。

## 必須ライブラリバージョン

**重要**: Interactions APIを使用するには以下のバージョンが必要です：
```
google-genai>=1.56.0
```

v0.5.0などの古いバージョンでは `client.interactions.create()` メソッドが存在せず、400エラーが発生します。

## 重要な制約条件

### 7日以内限定ルール（必須遵守）
- **調査対象期間**: 現在日（JST）から過去7日間のみ
- 7日より古い情報は絶対に含めない
- すべての情報に具体的な日付（YYYY年MM月DD日）を明記
- 日時処理はすべて日本標準時（JST = UTC+9）を使用

### 日付範囲の計算
```python
from lib.timezone import now_jst
from datetime import timedelta

today = now_jst()
start_date = today - timedelta(days=7)
# 例: 2025年12月22日〜2025年12月29日
```

## 使用モデル
- **Primary**: `deep-research-pro-preview-12-2025`
- **Fallback**: `gemini-3-pro-preview` with Google Search Tool

## 入力
```json
{
  "topic": "調査トピック",
  "focus_areas": ["焦点領域1", "焦点領域2"],
  "date_range": "過去7日間（自動計算）",
  "language": "ja",
  "depth": "comprehensive"
}
```

## 処理フロー

### Step 1: 日付範囲の確定（JST基準）
```python
from lib.timezone import now_jst, format_date
from datetime import timedelta

today = now_jst()
start_date = (today - timedelta(days=7)).strftime("%Y年%m月%d日")
end_date = today.strftime("%Y年%m月%d日")
```

### Step 2: リサーチクエリの構築
日付制約を明示的に含めたクエリを構築

### Step 3: Deep Research実行
```python
from src.lib.gemini_client import GeminiClient

client = GeminiClient()
result = await client.deep_research(
    query=research_query,  # 日付制約付き
    timeout_seconds=1800   # 30分（Deep Researchは時間がかかる）
)
# 内部で同期クライアントをasyncio.to_thread()でラップして実行
# 公式ドキュメント準拠: client.interactions.create() を使用
# background=True でバックグラウンド実行、ポーリングで完了を待機
```

### Step 4: 結果の構造化とソース整理
調査結果をJSON形式で構造化し、ソース情報を整理する

## 出力形式
```json
{
  "topic": "トピック名",
  "research_date": "2025年12月29日",
  "date_range": {
    "start": "2025年12月22日",
    "end": "2025年12月29日",
    "max_age_days": 7
  },
  "summary": "調査結果の要約",
  "key_findings": [
    {
      "finding": "発見内容",
      "date": "2025年12月28日",
      "source_url": "https://example.com/article"
    }
  ],
  "statistics": [],
  "expert_opinions": [],
  "trends": [],
  "sources": [
    {
      "title": "ソースタイトル",
      "url": "https://example.com/article",
      "type": "academic|news|official|blog",
      "reliability": "high|medium|low",
      "published_date": "2025年12月27日"
    }
  ]
}
```

## ソース収集のガイドライン（必須遵守）

### 必須要件
- **最低5つ以上**の信頼できるソースを収集
- 各ソースには必ず**完全なURL**を含める（https://で始まる）
- **7日以内に公開された情報のみ**を採用
- URLはマークダウンリンク形式 `[タイトル](URL)` で記載

### 優先順位
1. 公的機関（政府、国際機関）
2. 学術論文・研究機関
3. 専門メディア・業界誌
4. 大手ニュースメディア
5. 専門家ブログ・個人サイト

### 除外対象
- 7日より古い情報
- リンク切れのURL
- 信頼性の低いソース
- 日付が不明な情報

## クエリテンプレート
```
【重要】本日は{today_jst}です。必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。

【調査トピック】{topic_name}

【調査要件 - 必須遵守】
1. 期間制限: {start_date}〜{end_date}の7日以内の情報のみ
   - 7日より古い情報は絶対に含めないでください
   - 各情報には必ず具体的な日付（YYYY年MM月DD日）を明記してください

【ソース・引用元の記載 - 必須】
- 各情報の引用元URL（ソースURL）を必ず含めてください
- 最低5つ以上の異なるソースを使用してください
- URLは完全な形式で記載してください（https://で始まる完全URL）
```

## エラーハンドリング
- **Deep Research失敗時**: 自動的にMulti-Search（3回検索）にフォールバック
- **レート制限エラー（400）**: RPM 1/1を超過 → Multi-Searchにフォールバック
- タイムアウト: Multi-Searchにフォールバック
- API制限: 指数バックオフで再試行（最大3回）
- ライブラリバージョンエラー: 400 Bad Request → フォールバック実行

### フォールバックフロー
```python
try:
    result = await client.deep_research(query)
except Exception as e:
    # 自動的にMulti-Search（3回検索）にフォールバック
    result = await client.multi_search_research(topic, topic_info, date_range)
```

## 関連スキル
- `gemini-research.md`: Deep Research実行
- `timezone.md`: JST日時処理

## ドキュメント更新義務（必須遵守）

このエージェントで機能追加・修正・エラー対応を行った場合、**必ずREADME.mdを最新仕様に更新すること**。

### 更新すべき内容
1. **最新アップデート**: 変更内容を記載
2. **トラブルシューティング**: 新しいエラーと解決策を追加
3. **内部動作フロー**: フォールバック処理等の説明

### エラー通知フロー
```
Deep Research 失敗時のログ出力:
============================================================
【重要】Deep Research APIが失敗しました
エラー内容: {エラーメッセージ}
フォールバック: Google Search Tool (gemini-3-pro-preview) を使用します
============================================================
```

### 内部動作フロー図
```
┌──────────────────────────────────────┐
│ run_research(topic, use_deep=True)  │
│ topic=weekly_summary → 週間総括      │
└─────────────────┬────────────────────┘
                  │
        ┌─────────▼─────────┐
        │ Deep Research API │
        │ 呼び出し          │
        │ (週間総括: 6分野  │
        │  横断クエリ生成)  │
        └─────────┬─────────┘
                  │
          成功？ ─┴─ 失敗？
          │           │
          │    ┌──────▼──────────────┐
          │    │ エラーログ出力      │
          │    │ "【重要】Deep      │
          │    │  Research失敗"     │
          │    └──────┬──────────────┘
          │           │
          │    ┌──────▼──────────────┐
          │    │ Multi-Search       │
          │    │ (3回検索)          │
          │    └──────┬──────────────┘
          │           │
    ┌─────▼───────────▼─────┐
    │ 結果返却               │
    │ method: deep_research │
    │  or multi_search      │
    │ fallback_reason: ...  │
    └───────────────────────┘
```
