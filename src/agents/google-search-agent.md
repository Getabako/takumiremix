# Google Search Agent

## 役割
Multi-Search（3回検索）を使用して、**7日以内の最新情報のみ**を高品質に収集する

## 使用タイミング（メイン）

| 実行タイミング | リサーチ方法 | 検索回数 |
|--------------|-------------|----------|
| **月〜土曜日（デフォルト）** | Multi-Search | 3回 |
| **手動指定時** | Multi-Search | 選択可 |
| **Deep Research失敗時** | Multi-Search（フォールバック） | 3回 |

**設計方針**: Multi-Search（3回検索）をDeep Research簡易版として日常的なリサーチのメインとして使用します。
3つの異なる視点から検索を行い、情報を統合することで高品質な情報収集を実現します。

## Multi-Search（3回検索）パターン

3つの異なる視点から検索を実行し、情報を統合します：

| 検索 | 視点 | 目的 |
|------|------|------|
| 1回目 | 最新ニュース・公式発表 | 直近の重要なニュースや発表を収集 |
| 2回目 | 専門家の見解・研究データ | 学術的知見やエビデンスを収集 |
| 3回目 | 実践事例・統計情報 | 具体的な事例と数値データを収集 |

### トピック別専門クエリ（自動生成）

各トピックに最適化された検索クエリを使用します：

| トピック | クエリ例 |
|----------|---------|
| psychology | `心理学 メンタルヘルス 最新研究 論文発表` |
| education | `教育改革 学習指導要領 文部科学省 発表` |
| startup | `スタートアップ 資金調達 IPO M&A ニュース` |
| investment | `新NISA iDeCo 制度変更 金融庁 発表` |
| ai_tools | `生成AI ChatGPT Claude Gemini 新機能 アップデート` |
| inclusive_education | `不登校 支援制度 フリースクール 教育機会確保法` |
| weekly_summary | `週間ニュース 注目トピック AI 教育 経済` |

## 特徴

| 項目 | Multi-Search (3回) | Deep Research |
|------|-------------------|---------------|
| 処理時間 | **約10秒** | 約5分 |
| レート制限 | 緩やか | RPM 1/分（厳しい） |
| 課金 | 無料枠あり | 有料のみ |
| 情報深度 | **高品質（複合視点）** | 包括的・深層 |
| 推奨用途 | 日常リサーチ（メイン） | 週1回の深層調査 |

## 使用モデル
- **Primary**: `gemini-3-pro-preview` + Google Search Tool (3回検索)

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

## 入力
```json
{
  "topic": "調査トピック",
  "focus_areas": ["焦点領域1", "焦点領域2"],
  "date_range": "過去7日間（自動計算）",
  "language": "ja"
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

### Step 2: Multi-Search実行（3回検索）
```python
from src.lib.gemini_client import GeminiClient

client = GeminiClient()
result = await client.multi_search_research(
    topic=topic_info['name'],
    topic_info=topic_info,
    date_range={"start": start_date, "end": end_date},
    search_count=3  # デフォルト: 3回
)
# 3つの視点から検索してDeep Research簡易版として高品質情報収集
```

### Step 3: 結果の統合
3回の検索結果を統合し、重複を除去して構造化されたレポートを生成

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
  "content": "統合されたリサーチ結果（マークダウン形式）",
  "sources": [
    {
      "title": "ソースタイトル",
      "url": "https://example.com/article",
      "research_date_range": "2025年12月22日〜2025年12月29日"
    }
  ],
  "method": "multi_search",
  "search_count": 3,
  "fallback_reason": null
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

## クエリテンプレート
```
【重要】本日は{today_jst}です。必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。

【調査トピック】{topic_name}

【調査要件 - 必須遵守】
1. 期間制限: {start_date}〜{end_date}の7日以内の情報のみ
2. 各情報には必ず具体的な日付（YYYY年MM月DD日）を明記

【ソース・引用元の記載 - 必須】
- 各情報の引用元URL（ソースURL）を必ず含めてください
- 最低5つ以上の異なるソースを使用してください
- URLは完全な形式で記載してください（https://で始まる完全URL）
```

## 関連エージェント
- `deep-research-agent.md`: 週1回（日曜日）の深層調査

## 関連スキル
- `gemini-research.md`: リサーチ実行
- `timezone.md`: JST日時処理
