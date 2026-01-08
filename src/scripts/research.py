#!/usr/bin/env python3
"""
リサーチ実行スクリプト - 7日以内最新情報限定版

Google Search Tool 3回検索（デフォルト）またはDeep Research APIを使用して、
必ず7日以内の最新情報のみを収集します。
すべての日時処理は日本標準時(JST)を使用します。

設計方針:
- Multi-Search (3回検索): 日常的な情報収集（月〜土・デフォルト）
  → 3つの視点から検索してDeep Research簡易版として高品質な情報収集
- Deep Research: 週1回（日曜日）の深層調査
  → 失敗時は自動的にMulti-Searchにフォールバック
- 週間総括 (weekly_summary): 日曜日専用
  → Deep Researchで6トピックを横断的に分析
"""
import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gemini_client import GeminiClient
from lib.timezone import now_jst, format_date

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 最新情報の期間制限（日数）
MAX_AGE_DAYS = 7

# デフォルトの検索回数
DEFAULT_SEARCH_COUNT = 3


def get_date_range_jst() -> tuple[str, str]:
    """
    7日以内の日付範囲を取得（JST基準）

    Returns:
        tuple: (開始日, 終了日) の文字列タプル
    """
    today = now_jst()
    start_date = today - timedelta(days=MAX_AGE_DAYS)
    return (
        start_date.strftime("%Y年%m月%d日"),
        today.strftime("%Y年%m月%d日")
    )


async def run_research(
    topic_id: str,
    use_deep_research: bool = False,
    search_count: int = DEFAULT_SEARCH_COUNT
) -> dict:
    """
    リサーチを実行（7日以内の最新情報限定）

    Args:
        topic_id: トピックID
        use_deep_research: Deep Research APIを使用するか（デフォルト: False）
        search_count: Google Searchの検索回数（デフォルト: 3）

    Returns:
        dict: リサーチ結果（sources含む）

    Note:
        - デフォルトはMulti-Search（3回検索）でDeep Research簡易版として動作
        - Deep Researchは週1回（日曜日）または手動指定時のみ推奨
        - Deep Research失敗時は自動的にMulti-Searchにフォールバック
    """
    # トピック設定を読み込み
    config_path = Path(__file__).parent.parent / "config" / "topics.json"
    with open(config_path, encoding="utf-8") as f:
        topics_config = json.load(f)

    topic_info = next(
        (t for t in topics_config["topics"] if t["id"] == topic_id),
        None
    )

    if not topic_info:
        raise ValueError(f"Unknown topic: {topic_id}")

    client = GeminiClient()

    # 日付範囲を取得（JST基準）
    start_date, end_date = get_date_range_jst()
    today_jst = format_date(fmt="%Y年%m月%d日")
    date_range = {
        "start": start_date,
        "end": end_date,
        "max_age_days": MAX_AGE_DAYS
    }

    fallback_error = None

    # 週間総括トピックの特別処理
    is_weekly_summary = topic_info.get("is_summary", False)
    if is_weekly_summary:
        use_deep_research = True  # 週間総括は常にDeep Research
        logger.info("=" * 60)
        logger.info("【週間総括】6トピックを横断した週間総括記事を生成します")
        logger.info("=" * 60)

    # Deep Research使用時
    if use_deep_research:
        logger.info("=" * 60)
        logger.info("【Deep Research】深層調査を開始します...")
        logger.info("=" * 60)

        # 週間総括用のクエリを生成
        if is_weekly_summary:
            summary_topics = topic_info.get("summary_topics", [])
            # 全トピックの情報を取得
            all_topic_names = []
            all_keywords = []
            for tid in summary_topics:
                t = next((t for t in topics_config["topics"] if t["id"] == tid), None)
                if t:
                    all_topic_names.append(t["name"])
                    all_keywords.extend(t["keywords"][:3])

            research_query = f"""
【重要】本日は{today_jst}です。必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。

【週間総括レポート】
今週1週間の重要ニュースを、以下の6つの分野を横断して総括してください。

【対象分野】
{chr(10).join([f"- {name}" for name in all_topic_names])}

【調査要件 - 必須遵守】
1. 期間制限: {start_date}〜{end_date}の7日以内の情報のみ
   - 7日より古い情報は絶対に含めないでください
   - 各情報には必ず具体的な日付（YYYY年MM月DD日）を明記してください
2. 言語: 日本語優先（英語ソースも可）
3. 各分野から最低1〜2件の重要ニュースを抽出
4. 分野横断的なトレンドや関連性を分析
5. キーワード: {', '.join(set(all_keywords[:15]))}

【必要な構成】
1. 今週のハイライト（全体の要約・3〜5行）
2. 各分野の注目ニュース（分野ごとに1〜2件）
   - 心理学・メンタルヘルス
   - 教育・学習科学
   - 起業・スタートアップ
   - 投資・金融リテラシー
   - AIツール・技術動向
   - インクルーシブ教育・多様な学び
3. 分野横断的なトレンド分析
4. 来週の注目ポイント

【ソース・引用元の記載 - 必須】
- 各情報の引用元URL（ソースURL）を必ず含めてください
- 信頼できるソース（公的機関、学術論文、専門メディア）を優先してください
- 最低8つ以上の異なるソースを使用してください
- URLは完全な形式で記載してください（https://で始まる完全URL）

【出力形式】
- 日付は「YYYY年MM月DD日」形式で統一
- ソースURLは[タイトル](URL)のMarkdown形式で記載
"""
        else:
            research_query = f"""
【重要】本日は{today_jst}です。必ず過去7日以内（{start_date}〜{end_date}）の最新情報のみを調査してください。

【調査トピック】{topic_info['name']}

【調査要件 - 必須遵守】
1. 期間制限: {start_date}〜{end_date}の7日以内の情報のみ
   - 7日より古い情報は絶対に含めないでください
   - 各情報には必ず具体的な日付（YYYY年MM月DD日）を明記してください
2. 言語: 日本語優先（英語ソースも可）
3. 焦点: {', '.join(topic_info['research_focus'])}
4. キーワード: {', '.join(topic_info['keywords'])}

【必要な情報】
1. 最新ニュース・動向（具体的な日付必須）
2. 専門家の見解・研究結果（発表日付必須）
3. 統計データ・調査結果（調査日付必須）
4. 具体的な事例（発生日付必須）
5. 今後の展望

【ソース・引用元の記載 - 必須】
- 各情報の引用元URL（ソースURL）を必ず含めてください
- 信頼できるソース（公的機関、学術論文、専門メディア）を優先してください
- 最低5つ以上の異なるソースを使用してください
- URLは完全な形式で記載してください（https://で始まる完全URL）

【出力形式】
- 日付は「YYYY年MM月DD日」形式で統一
- ソースURLは[タイトル](URL)のMarkdown形式で記載
"""

        try:
            result = await client.deep_research(research_query)

            if result.status == "completed":
                # ソース情報を強化（日付範囲を追加）
                sources = result.sources or []
                enhanced_sources = []
                for source in sources:
                    enhanced_source = dict(source)
                    enhanced_source["research_date_range"] = f"{start_date}〜{end_date}"
                    enhanced_sources.append(enhanced_source)

                logger.info("【Deep Research】深層調査が完了しました")
                logger.info(f"ソース数: {len(enhanced_sources)}")

                return {
                    "topic": topic_id,
                    "topic_info": topic_info,
                    "content": result.content,
                    "sources": enhanced_sources,
                    "research_date": today_jst,
                    "date_range": date_range,
                    "method": "deep_research",
                    "search_count": 1
                }
            else:
                raise Exception(f"Deep Research failed: {result.error}")

        except Exception as e:
            # Deep Researchが失敗した場合、Multi-Searchにフォールバック
            logger.error("=" * 60)
            logger.error("【重要】Deep Research APIが失敗しました")
            logger.error(f"エラー内容: {e}")
            logger.error(f"フォールバック: Multi-Search（{search_count}回検索）を実行します")
            logger.error("=" * 60)

            fallback_error = str(e)
            use_deep_research = False  # フォールバック

    # Multi-Search（3回検索）を使用
    if not use_deep_research:
        logger.info("=" * 60)
        logger.info(f"【Multi-Search】{search_count}回検索でDeep Research簡易版を実行します...")
        logger.info("=" * 60)

        result = await client.multi_search_research(
            topic=topic_info['name'],
            topic_info=topic_info,
            date_range={"start": start_date, "end": end_date},
            search_count=search_count
        )

        if result.status == "completed":
            # ソース情報を整形
            enhanced_sources = []
            for source in result.sources:
                enhanced_source = dict(source)
                enhanced_source["research_date_range"] = f"{start_date}〜{end_date}"
                enhanced_sources.append(enhanced_source)

            logger.info("【Multi-Search】情報収集が完了しました")
            logger.info(f"検索回数: {result.search_count}")
            logger.info(f"ソース数: {len(enhanced_sources)}")

            return {
                "topic": topic_id,
                "topic_info": topic_info,
                "content": result.content,
                "sources": enhanced_sources,
                "research_date": today_jst,
                "date_range": date_range,
                "method": "multi_search",
                "search_count": result.search_count,
                "fallback_reason": fallback_error if fallback_error else None
            }
        else:
            logger.error(f"Multi-Search failed: {result.error}")
            raise Exception(f"Research failed: {result.error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="7日以内の最新情報を収集（デフォルト: 3回検索）"
    )
    parser.add_argument('--topic', required=True, help='トピックID')
    parser.add_argument('--use-deep-research', action='store_true', default=False,
                        help='Deep Research APIを使用（週1回の深層調査向け）')
    parser.add_argument('--search-count', type=int, default=DEFAULT_SEARCH_COUNT,
                        help=f'Google Searchの検索回数（デフォルト: {DEFAULT_SEARCH_COUNT}）')
    args = parser.parse_args()

    result = asyncio.run(run_research(
        args.topic,
        use_deep_research=args.use_deep_research,
        search_count=args.search_count
    ))

    # 結果を出力
    print(f"\n=== リサーチ結果 ({result['research_date']}) ===")
    print(f"方法: {result['method']}")
    print(f"検索回数: {result.get('search_count', 1)}")
    print(f"期間: {result['date_range']['start']} 〜 {result['date_range']['end']}")
    print(f"ソース数: {len(result['sources'])}")
    if result.get('fallback_reason'):
        print(f"フォールバック理由: {result['fallback_reason']}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
