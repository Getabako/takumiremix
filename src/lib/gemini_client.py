#!/usr/bin/env python3
"""
Gemini API クライアントライブラリ

Gemini 3 Pro Preview, Deep Research, Google Search Toolを
統合的に扱うためのラッパークラス
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Deep Research結果のデータクラス"""
    interaction_id: str
    status: str
    content: str
    sources: List[Dict[str, str]]
    error: Optional[str] = None
    method: str = "deep_research"  # deep_research, multi_search, single_search


@dataclass
class MultiSearchResult:
    """複数回検索結果のデータクラス"""
    status: str
    content: str
    sources: List[Dict[str, str]]
    search_count: int
    combined_findings: List[str]
    error: Optional[str] = None


@dataclass
class GenerationResult:
    """コンテンツ生成結果のデータクラス"""
    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    grounding_sources: Optional[List[Dict]] = None


@dataclass
class ImageGenerationResult:
    """画像生成結果のデータクラス"""
    images: List[bytes]
    model: str
    prompt: str
    text_response: Optional[str] = None


@dataclass
class AudioGenerationResult:
    """音声生成結果のデータクラス"""
    audio_data: bytes
    model: str
    text: str
    duration_seconds: Optional[float] = None


class GeminiClient:
    """Gemini API統合クライアント"""

    # モデル定数
    MODEL_PRO = "gemini-3-pro-preview"
    MODEL_FLASH = "gemini-3-flash-preview"  # Updated: Gemini 3 Flash (thinking off)
    MODEL_FLASH_3 = "gemini-3-flash-preview"  # SEO/Review用 (alias)
    MODEL_IMAGE = "gemini-2.5-flash-image"
    MODEL_TTS = "gemini-2.5-flash-preview-tts"  # TTS用
    AGENT_DEEP_RESEARCH = "deep-research-pro-preview-12-2025"

    # TTS音声オプション（日本語対応音声）
    TTS_VOICES = {
        "default": "Kore",      # 落ち着いた声
        "bright": "Puck",       # 明るい声
        "calm": "Charon",       # 静かな声
        "warm": "Aoede",        # 温かみのある声
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Google AI API Key（省略時は環境変数から取得）
        """
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY is required")

        self.client = genai.Client(api_key=self.api_key)
        # 注意: self.client.aio（非同期クライアント）は使用しない
        # Deep Researchは公式ドキュメント通り同期クライアントを使用
        logger.info("GeminiClient initialized")

    def _extract_urls_from_text(self, text: str) -> List[str]:
        """
        テキストからURLを抽出する

        Args:
            text: 検索結果テキスト

        Returns:
            抽出されたURLのリスト
        """
        import re

        # URLパターン（https/httpで始まるURL）
        url_pattern = r'https?://[^\s\)\]\}\"\'<>]+'

        urls = re.findall(url_pattern, text)

        # URLのクリーンアップ
        cleaned_urls = []
        for url in urls:
            # 末尾の句読点を除去
            url = url.rstrip('.,;:!?')
            # 末尾の括弧を除去
            url = url.rstrip(')')
            # 有効なURLかチェック
            if url.startswith('http') and '.' in url and len(url) > 10:
                cleaned_urls.append(url)

        # 重複を除去して返す
        return list(dict.fromkeys(cleaned_urls))

    async def generate_content(
        self,
        prompt: str,
        model: str = MODEL_PRO,
        enable_search: bool = False,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        thinking_mode: bool = False
    ) -> GenerationResult:
        """
        コンテンツを生成する

        Args:
            prompt: プロンプト
            model: 使用モデル
            enable_search: Google Search Toolを有効化
            system_instruction: システム指示
            temperature: 生成温度
            max_tokens: 最大トークン数
            thinking_mode: 思考モード（False=オフ、高速応答）

        Returns:
            GenerationResult: 生成結果
        """
        config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        # 思考モードの設定（Gemini 3 Flash Preview用）
        if not thinking_mode and "flash" in model.lower():
            # 思考モードをオフにして高速応答
            config["thinking_config"] = {"thinking_budget": 0}

        # Google Search Tool有効化
        tools = []
        if enable_search:
            tools.append({"google_search": {}})
            config["tools"] = tools

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config)
            )

            # Grounding情報の抽出（複数の場所をチェック）
            grounding_sources = None

            # 方法1: response.grounding_metadata（直接）
            if hasattr(response, 'grounding_metadata') and response.grounding_metadata:
                grounding_sources = response.grounding_metadata
                logger.debug("Found grounding_metadata in response")

            # 方法2: response.candidates[0].grounding_metadata
            if not grounding_sources and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding_sources = candidate.grounding_metadata
                    logger.debug("Found grounding_metadata in candidate")

            # デバッグ: grounding情報の構造をログ出力
            if grounding_sources:
                logger.debug(f"Grounding sources type: {type(grounding_sources)}")
                if hasattr(grounding_sources, 'grounding_chunks'):
                    chunks = grounding_sources.grounding_chunks
                    logger.debug(f"Found {len(chunks) if chunks else 0} grounding chunks")
                if hasattr(grounding_sources, 'web_search_queries'):
                    queries = grounding_sources.web_search_queries
                    logger.debug(f"Web search queries: {queries}")

            return GenerationResult(
                text=response.text,
                model=model,
                usage=getattr(response, 'usage_metadata', None),
                grounding_sources=grounding_sources
            )

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise

    def _sync_deep_research(
        self,
        query: str,
        timeout_seconds: int,
        poll_interval: int
    ) -> ResearchResult:
        """
        Deep Research APIを同期的に実行（公式ドキュメント準拠）

        公式コード: https://ai.google.dev/gemini-api/docs/deep-research
        """
        import time

        logger.info(f"Starting Deep Research (sync): {query[:50]}...")

        # 公式ドキュメント通りの同期呼び出し
        interaction = self.client.interactions.create(
            input=query,
            agent=self.AGENT_DEEP_RESEARCH,
            background=True
        )

        interaction_id = interaction.id
        logger.info(f"Research started: {interaction_id}")

        # ポーリングで完了を待機（公式コード準拠）
        elapsed = 0
        while elapsed < timeout_seconds:
            interaction = self.client.interactions.get(interaction_id)

            if interaction.status == "completed":
                content = interaction.outputs[-1].text if interaction.outputs else ""
                sources = self._extract_sources(interaction)

                logger.info(f"Research completed: {interaction_id}")
                return ResearchResult(
                    interaction_id=interaction_id,
                    status="completed",
                    content=content,
                    sources=sources
                )

            elif interaction.status == "failed":
                logger.error(f"Research failed: {interaction.error}")
                return ResearchResult(
                    interaction_id=interaction_id,
                    status="failed",
                    content="",
                    sources=[],
                    error=str(interaction.error)
                )

            time.sleep(poll_interval)
            elapsed += poll_interval
            logger.debug(f"Research in progress... ({elapsed}s)")

        # タイムアウト
        return ResearchResult(
            interaction_id=interaction_id,
            status="timeout",
            content="",
            sources=[],
            error=f"Research timed out after {timeout_seconds} seconds"
        )

    async def deep_research(
        self,
        query: str,
        timeout_seconds: int = 1800,  # 30分（Deep Researchは時間がかかる）
        poll_interval: int = 10
    ) -> ResearchResult:
        """
        Deep Research APIで深層調査を実行

        公式ドキュメント準拠: 同期クライアントをasyncio.to_thread()でラップ
        https://ai.google.dev/gemini-api/docs/deep-research

        Args:
            query: 調査クエリ
            timeout_seconds: タイムアウト秒数（デフォルト30分）
            poll_interval: ポーリング間隔秒数

        Returns:
            ResearchResult: 調査結果
        """
        try:
            # 同期メソッドをasyncio.to_thread()で非同期実行
            return await asyncio.to_thread(
                self._sync_deep_research,
                query,
                timeout_seconds,
                poll_interval
            )
        except Exception as e:
            logger.error(f"Deep Research error: {e}")
            # 詳細なエラー情報をログ出力
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response}")
            if hasattr(e, 'status_code'):
                logger.error(f"Status code: {e.status_code}")
            raise

    def _extract_sources(self, result) -> List[Dict[str, str]]:
        """リサーチ結果からソース情報を抽出"""
        sources = []
        if hasattr(result, 'grounding_metadata') and result.grounding_metadata:
            for source in result.grounding_metadata.get('sources', []):
                sources.append({
                    "title": source.get("title", ""),
                    "url": source.get("uri", ""),
                    "snippet": source.get("snippet", "")
                })
        return sources

    async def search_and_generate(
        self,
        query: str,
        generation_prompt: str,
        model: str = MODEL_PRO
    ) -> GenerationResult:
        """
        Google Searchで検索してから生成する

        Args:
            query: 検索クエリ
            generation_prompt: 生成プロンプト（{search_results}プレースホルダー使用可）
            model: 使用モデル

        Returns:
            GenerationResult: 生成結果
        """
        # 検索を有効にして生成
        combined_prompt = f"""
以下のトピックについて最新情報を検索し、その情報を基に回答してください。

検索トピック: {query}

指示: {generation_prompt}
"""

        return await self.generate_content(
            prompt=combined_prompt,
            model=model,
            enable_search=True
        )

    def _generate_topic_specific_queries(
        self,
        topic_id: str,
        topic_name: str,
        topic_info: Dict[str, Any],
        date_range: Dict[str, str]
    ) -> List[str]:
        """
        トピック別に最適化された検索クエリを生成

        各トピックの特性に合わせた具体的で効果的な検索クエリを生成します。
        """
        keywords = topic_info.get('keywords', [])
        focus_areas = topic_info.get('research_focus', [])
        year = "2025"

        # トピック別の専門的な検索クエリパターン
        topic_query_patterns = {
            "psychology": [
                f"心理学 メンタルヘルス 最新研究 論文発表 {date_range['end']}",
                f"認知行動療法 マインドフルネス 効果 エビデンス 学会 {year}",
                f"ストレス対策 うつ病予防 カウンセリング 新手法 臨床心理"
            ],
            "education": [
                f"教育改革 学習指導要領 文部科学省 発表 {date_range['end']}",
                f"EdTech オンライン学習 AI教育 導入事例 効果測定 {year}",
                f"学習科学 アクティブラーニング 教育効果 研究 実証実験"
            ],
            "startup": [
                f"スタートアップ 資金調達 IPO M&A ニュース {date_range['end']}",
                f"起業家 成功事例 ユニコーン企業 ビジネスモデル {year} 日本",
                f"ベンチャーキャピタル 投資動向 注目スタートアップ テック企業"
            ],
            "investment": [
                f"新NISA iDeCo 制度変更 金融庁 発表 {date_range['end']}",
                f"投資信託 資産形成 ポートフォリオ 運用戦略 {year}",
                f"株式市場 経済動向 金融リテラシー 投資教育 初心者向け"
            ],
            "ai_tools": [
                f"生成AI ChatGPT Claude Gemini 新機能 アップデート {date_range['end']}",
                f"AIツール 業務効率化 活用事例 企業導入 {year}",
                f"機械学習 大規模言語モデル LLM 技術動向 開発者向け"
            ],
            "inclusive_education": [
                f"不登校 支援制度 フリースクール 教育機会確保法 {date_range['end']}",
                f"発達障害 ADHD ASD 合理的配慮 学校支援 {year}",
                f"ニューロダイバーシティ インクルーシブ教育 成功事例 専門家"
            ],
            "weekly_summary": [
                f"週間ニュース 注目トピック AI 教育 経済 {date_range['end']}",
                f"心理学 スタートアップ 投資 トレンド まとめ {year}",
                f"インクルーシブ教育 メンタルヘルス テクノロジー 最新動向"
            ]
        }

        # トピック別クエリがあればそれを使用、なければ汎用クエリを生成
        if topic_id in topic_query_patterns:
            return topic_query_patterns[topic_id]

        # フォールバック: 汎用的だが詳細なクエリを生成
        keyword_str = ' '.join(keywords[:3]) if keywords else topic_name
        focus_str = ' '.join(focus_areas[:2]) if focus_areas else ""

        return [
            f"{keyword_str} 最新ニュース 公式発表 {date_range['end']}",
            f"{topic_name} 専門家 研究 調査報告 論文 {year}",
            f"{topic_name} {focus_str} 事例 統計データ 分析レポート"
        ]

    async def multi_search_research(
        self,
        topic: str,
        topic_info: Dict[str, Any],
        date_range: Dict[str, str],
        search_count: int = 3,
        model: str = MODEL_PRO
    ) -> MultiSearchResult:
        """
        Google Searchを複数回実行してDeep Research簡易版として情報収集

        3つの異なる視点から検索を行い、情報を統合します：
        1. 最新ニュース・動向（公式発表、重要ニュース）
        2. 専門家の見解・研究（学術的知見、エビデンス）
        3. 具体的な事例・統計データ（実践例、数値データ）

        Args:
            topic: トピック名
            topic_info: トピック設定情報
            date_range: 日付範囲 {"start": "...", "end": "..."}
            search_count: 検索回数（デフォルト: 3）
            model: 使用モデル

        Returns:
            MultiSearchResult: 複数回検索の統合結果
        """
        logger.info(f"Starting Multi-Search Research ({search_count} searches): {topic}")

        # トピックIDを取得（topic_infoまたはtopicから）
        topic_id = topic_info.get('id', '')
        topic_name = topic_info.get('name', topic)

        # トピック別に最適化された検索クエリを生成
        search_queries = self._generate_topic_specific_queries(
            topic_id=topic_id,
            topic_name=topic_name,
            topic_info=topic_info,
            date_range=date_range
        )

        all_sources = []
        all_findings = []
        errors = []

        # 検索視点のラベル
        search_perspectives = [
            "最新ニュース・公式発表",
            "専門家の見解・研究データ",
            "実践事例・統計情報"
        ]

        for i, query in enumerate(search_queries[:search_count], 1):
            perspective = search_perspectives[i-1] if i <= len(search_perspectives) else f"視点{i}"
            logger.info(f"Search {i}/{search_count} ({perspective}): {query[:50]}...")

            search_prompt = f"""
【重要な前提条件】
- 本日は{date_range['end']}です
- 必ず過去7日以内（{date_range['start']}〜{date_range['end']}）の最新情報のみを検索・報告してください
- 7日より古い情報は絶対に含めないでください

【検索視点】{perspective}
【検索クエリ】{query}

【詳細な出力要件】

あなたはプロのリサーチャーです。以下の形式で、**読者に価値を提供できる具体的で詳細な情報**を収集してください。

## 発見した重要情報（最低3件、できれば5件以上）

各情報について以下を必ず記載：
- **日付**: YYYY年MM月DD日形式
- **情報の種類**: ニュース/研究発表/政策発表/企業発表/調査結果
- **要約**: 50-100字で具体的に（数値データがあれば必ず含める）
- **重要度**: 高/中（なぜ重要かを一言で）
- **ソースURL**: 完全なURLを記載

## 具体的な数値・データ（見つかった場合）

- 統計データ、調査結果の数値
- 前年比、増減率などの変化
- 市場規模、利用者数などの具体値

## 専門家の意見・分析（見つかった場合）

- 専門家名（または機関名）
- 発言・分析の要約
- 出典

## ソース一覧（必須 - 最低5件）

**重要**: 以下の形式で必ずソースURLを記載してください。これは記事の引用元として使用されます。

各ソースについて：
- タイトル: [記事タイトル]
- URL: https://で始まる完全URL（必須）
- 信頼度: 高/中（公的機関、大手メディア、専門誌は「高」）
- 公開日: [YYYY年MM月DD日]

例:
- タイトル: 教育改革の最新動向2025
- URL: https://www.mext.go.jp/example
- 信頼度: 高
- 公開日: 2025年12月28日

【品質基準】
- 曖昧な情報より具体的なデータを優先
- 「〜らしい」「〜と思われる」などの推測は含めない
- 一次ソース（政府発表、研究機関、企業公式）を優先
- 読者がすぐに活用できる実践的な情報を重視
"""

            try:
                result = await self.generate_content(
                    prompt=search_prompt,
                    model=model,
                    enable_search=True,
                    temperature=0.5
                )

                if result.text:
                    all_findings.append(f"【検索{i}の結果】\n{result.text}")

                    # テキストからURLを抽出（フォールバック）
                    extracted_urls = self._extract_urls_from_text(result.text)
                    for url in extracted_urls:
                        if not any(s.get('url') == url for s in all_sources):
                            all_sources.append({
                                "title": "",
                                "url": url,
                                "snippet": "",
                                "extracted_from": "text"
                            })

                # Grounding sourcesを収集（複数の構造に対応）
                sources_found = 0
                logger.debug(f"Checking grounding_sources: {result.grounding_sources is not None}")
                if result.grounding_sources:
                    logger.debug(f"grounding_sources type: {type(result.grounding_sources)}")
                    logger.debug(f"grounding_sources attrs: {dir(result.grounding_sources)}")
                    # 方法1: grounding_chunks
                    if hasattr(result.grounding_sources, 'grounding_chunks') and result.grounding_sources.grounding_chunks:
                        for chunk in result.grounding_sources.grounding_chunks:
                            if hasattr(chunk, 'web') and chunk.web:
                                url = getattr(chunk.web, 'uri', '') or getattr(chunk.web, 'url', '')
                                title = getattr(chunk.web, 'title', '')
                                if url and not any(s.get('url') == url for s in all_sources):
                                    all_sources.append({
                                        "title": title,
                                        "url": url,
                                        "snippet": ""
                                    })
                                    sources_found += 1

                    # 方法2: search_entry_point (代替構造)
                    if hasattr(result.grounding_sources, 'search_entry_point'):
                        sep = result.grounding_sources.search_entry_point
                        if hasattr(sep, 'rendered_content'):
                            logger.debug(f"Search entry point found")

                    # 方法3: grounding_supports
                    if hasattr(result.grounding_sources, 'grounding_supports') and result.grounding_sources.grounding_supports:
                        for support in result.grounding_sources.grounding_supports:
                            if hasattr(support, 'grounding_chunk_indices'):
                                logger.debug(f"Grounding support indices: {support.grounding_chunk_indices}")

                logger.info(f"Search {i} completed, found {len(all_findings)} findings, {sources_found} new sources from grounding, total sources: {len(all_sources)}")

                # API制限を避けるため少し待機
                if i < search_count:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Search {i} failed: {e}")
                errors.append(str(e))
                continue

        if not all_findings:
            return MultiSearchResult(
                status="failed",
                content="",
                sources=[],
                search_count=0,
                combined_findings=[],
                error="; ".join(errors) if errors else "No search results"
            )

        # 収集した情報を統合
        combined_content = "\n\n".join(all_findings)

        # 統合プロンプトで情報を整理（高品質版）
        target_audience = topic_info.get('target_audience', '一般読者')

        synthesis_prompt = f"""
あなたは{topic_name}分野の専門ライターです。
以下の検索結果を統合して、**読者が価値を感じる高品質なリサーチレポート**を作成してください。

【対象読者】{target_audience}
【調査期間】{date_range['start']}〜{date_range['end']}（7日以内の情報のみ）

【収集した情報（3つの視点から検索）】
{combined_content}

【レポート作成ガイドライン】

## 1. エグゼクティブサマリー（重要度: 最高）
- この1週間で最も重要な3つのポイントを箇条書きで
- 読者が「これだけは知っておくべき」という情報
- 具体的な数値やファクトを含める

## 2. 今週の重要ニュース
各ニュースについて：
- **[日付] タイトル**
- 内容の要約（50-100字）
- なぜ重要か（読者への影響）
- ソース情報

## 3. 注目トレンド・動向分析
- 今週見られた傾向や変化
- 前週や前年との比較（データがあれば）
- 業界・分野への影響予測

## 4. 専門家の見解・研究知見
- 専門家の発言や分析を引用
- 研究機関からの新しい知見
- エビデンスに基づいた洞察

## 5. 実践的な数値・データ
- 具体的な統計データ
- 調査結果の数値
- 市場データ、利用状況など

## 6. 読者へのアクションポイント
- この情報を踏まえて読者が取るべき行動
- 注意すべき点、チェックすべきこと
- 次のステップとして推奨すること

## 7. 来週の注目ポイント（予告）
- 来週発表予定の情報や動向
- フォローすべきトピック

【品質チェックリスト】
- [ ] すべての情報に日付を明記したか
- [ ] 具体的な数値・データを含めたか
- [ ] 読者にとっての価値を明確にしたか
- [ ] 根拠のない推測を排除したか
- [ ] 7日より古い情報を除外したか
- [ ] ソース情報を記載したか

【文体・トーン】
- 専門的だが親しみやすい
- 押し付けがましくない
- 絵文字は使用しない
- 「革新的」「画期的」などの陳腐な表現を避ける
"""

        try:
            synthesis_result = await self.generate_content(
                prompt=synthesis_prompt,
                model=model,
                enable_search=False,  # 既に収集した情報を使用
                temperature=0.3
            )

            final_content = synthesis_result.text

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            final_content = combined_content  # フォールバック: 生の結果を使用

        # ソースが少ない場合、結合コンテンツからも抽出を試みる
        if len(all_sources) < 3:
            logger.info(f"Sources count ({len(all_sources)}) is low, extracting from combined content...")
            additional_urls = self._extract_urls_from_text(combined_content)
            for url in additional_urls:
                if not any(s.get('url') == url for s in all_sources):
                    all_sources.append({
                        "title": "",
                        "url": url,
                        "snippet": "",
                        "extracted_from": "combined_content"
                    })
            logger.info(f"After extraction from combined content: {len(all_sources)} sources")

        # 最終コンテンツからもURLを抽出
        if len(all_sources) < 3:
            logger.info(f"Still low ({len(all_sources)}), extracting from final content...")
            final_urls = self._extract_urls_from_text(final_content)
            for url in final_urls:
                if not any(s.get('url') == url for s in all_sources):
                    all_sources.append({
                        "title": "",
                        "url": url,
                        "snippet": "",
                        "extracted_from": "final_content"
                    })
            logger.info(f"After extraction from final content: {len(all_sources)} sources")

        logger.info(f"Multi-Search Research completed: {len(all_sources)} sources, {search_count} searches")

        return MultiSearchResult(
            status="completed",
            content=final_content,
            sources=all_sources,
            search_count=search_count,
            combined_findings=all_findings,
            error=None
        )

    async def generate_image(
        self,
        prompt: str,
        model: str = MODEL_IMAGE,
        num_images: int = 1,
        aspect_ratio: str = "16:9"
    ) -> ImageGenerationResult:
        """
        Gemini 2.5 Flash imageで画像を生成する

        Args:
            prompt: 画像生成プロンプト
            model: 使用モデル（デフォルト: gemini-2.5-flash-image）
            num_images: 生成画像数
            aspect_ratio: アスペクト比（デフォルト: "16:9" YouTubeサムネイル向け）

        Returns:
            ImageGenerationResult: 生成結果（画像バイナリデータのリスト）
        """
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        logger.info(f"Aspect ratio: {aspect_ratio}")

        try:
            # 画像生成用の設定（response_modalitiesとimage_configが必須）
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                temperature=1.0,
                top_p=0.95,
                top_k=40,
                # 16:9アスペクト比を強制（YouTubeサムネイル/ブログヒーロー画像向け）
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio
                )
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=prompt,
                config=config
            )

            images = []
            text_response = None

            # レスポンスからの画像データ抽出
            if response.candidates and len(response.candidates) > 0:
                parts = response.candidates[0].content.parts
                for part in parts:
                    # テキストレスポンスの場合
                    if hasattr(part, 'text') and part.text:
                        text_response = part.text
                    # 画像データの場合（inlineData）
                    elif hasattr(part, 'inline_data') and part.inline_data:
                        # inline_data.dataはbytes型の場合とbase64文字列の場合がある
                        data = part.inline_data.data
                        if isinstance(data, str):
                            import base64
                            image_data = base64.b64decode(data)
                        else:
                            image_data = data

                        # 画像サイズの検証（最低1KB以上）
                        if len(image_data) > 1024:
                            images.append(image_data)
                            logger.info(f"Image extracted: {len(image_data)} bytes")
                        else:
                            logger.warning(f"Image data too small: {len(image_data)} bytes, skipping")

            if not images:
                logger.warning("No valid images generated, response may contain only text")
                if text_response:
                    logger.info(f"Text response: {text_response[:200]}...")

            logger.info(f"Generated {len(images)} valid image(s)")

            return ImageGenerationResult(
                images=images,
                model=model,
                prompt=prompt,
                text_response=text_response
            )

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise

    # トピック別カラースキーム
    TOPIC_COLORS = {
        "psychology": {"primary": "#2b6cb0", "accent": "#4299e1", "name": "calming blue"},
        "education": {"primary": "#2f855a", "accent": "#48bb78", "name": "growth green"},
        "startup": {"primary": "#c05621", "accent": "#ed8936", "name": "energetic orange"},
        "investment": {"primary": "#744210", "accent": "#d69e2e", "name": "trustworthy gold-brown"},
        "ai_tools": {"primary": "#1a365d", "accent": "#3182ce", "name": "tech navy blue"},
        "inclusive_education": {"primary": "#285e61", "accent": "#38b2ac", "name": "supportive teal"},
        "weekly_summary": {"primary": "#553c9a", "accent": "#805ad5", "name": "insightful indigo"},
        "default": {"primary": "#1a1a2e", "accent": "#0f3460", "name": "professional navy"}
    }

    # 視覚的構図バリエーション
    COMPOSITION_STYLES = [
        "centered focal point with clean negative space",
        "dynamic diagonal composition with flowing elements",
        "layered depth with foreground and background elements",
        "radial arrangement emanating from center",
        "asymmetric balance with visual tension",
        "grid-based structured layout",
        "organic flowing shapes and curves",
        "geometric abstract pattern"
    ]

    # キャラクター多様性設定（ランダム選択用）
    CHARACTER_GENDERS = ["male", "female"]
    CHARACTER_AGES = [
        "child (8-12 years old)",
        "teenager (13-17 years old)",
        "young adult (18-25 years old)",
        "adult (26-40 years old)",
        "middle-aged (41-55 years old)",
        "senior (56+ years old)"
    ]
    CHARACTER_APPEARANCES = [
        "with short hair",
        "with long hair",
        "with glasses",
        "with a friendly smile",
        "with a thoughtful expression",
        "with casual clothing",
        "with business casual attire",
        "with professional attire"
    ]

    async def analyze_for_image_prompt(
        self,
        title: str,
        summary: str,
        topic_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        記事タイトルと概要を分析して、最適な画像プロンプト要素を生成

        Args:
            title: 記事タイトル
            summary: 記事概要
            topic_id: トピックID（カラースキーム決定用）

        Returns:
            画像生成用の要素を含む辞書
        """
        # ランダムな性別・年齢を選択（多様性のため）
        import random
        random_gender = random.choice(self.CHARACTER_GENDERS)
        random_age = random.choice(self.CHARACTER_AGES)
        random_appearance = random.choice(self.CHARACTER_APPEARANCES)

        analysis_prompt = f"""Analyze this blog article title and summary, then suggest specific visual elements for an ANIME-STYLE illustration with PEOPLE/CHARACTERS.

Title: {title}
Summary: {summary}

IMPORTANT CHARACTER DIVERSITY REQUIREMENT:
- The main character MUST be: {random_gender}, {random_age}, {random_appearance}
- Do NOT always use young women - vary gender and age each time

Provide a JSON response with:
1. "main_character": Describe an anime-style {random_gender} character, {random_age}, {random_appearance}, that represents the article's theme. Be specific about their appearance, clothing style, and expression.
2. "character_action": What the character is doing (e.g., "typing on a laptop with determination", "explaining concepts with hand gestures", "studying with focused concentration")
3. "visual_metaphor": A creative visual metaphor that represents the article's core message, integrated with the character
4. "mood": The emotional tone (e.g., "hopeful and bright", "calm and reflective", "dynamic and energetic")
5. "key_elements": List of 3-4 specific visual elements to include around the character (be concrete)
6. "background_style": Describe the background (e.g., "modern office with soft lighting", "cozy study room with bookshelves", "futuristic cityscape")
7. "lighting": Describe the lighting style (e.g., "warm golden hour glow", "soft studio lighting", "dramatic backlight")

Important:
- Character MUST be {random_gender}, {random_age}
- Use modern Japanese anime art style (clean lines, expressive eyes, stylized features)
- Be specific about character appearance, clothing, and pose
- Each image should tell a story related to the article content

Respond ONLY with valid JSON, no other text."""

        try:
            result = await self.generate_content(
                prompt=analysis_prompt,
                model=self.MODEL_FLASH,
                temperature=0.8  # 多様性を高めるため
            )

            # JSONをパース
            import json
            import re

            # JSONブロックを抽出
            text = result.text.strip()
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")

            # トピック別カラーを追加
            colors = self.TOPIC_COLORS.get(topic_id, self.TOPIC_COLORS["default"])
            analysis["color_scheme"] = colors

            # ランダムな構図スタイルを追加
            import random
            analysis["composition"] = random.choice(self.COMPOSITION_STYLES)

            return analysis

        except Exception as e:
            logger.warning(f"Image analysis failed, using fallback: {e}")
            # フォールバック: ランダムな多様性を持つキャラクター
            import random
            colors = self.TOPIC_COLORS.get(topic_id, self.TOPIC_COLORS["default"])
            fallback_gender = random.choice(self.CHARACTER_GENDERS)
            fallback_age = random.choice(self.CHARACTER_AGES)
            fallback_appearance = random.choice(self.CHARACTER_APPEARANCES)
            return {
                "main_character": f"a {fallback_gender} {fallback_age} {fallback_appearance}, wearing appropriate attire for their age",
                "character_action": "looking thoughtfully at the viewer while gesturing toward floating information displays",
                "visual_metaphor": "knowledge and discovery represented by glowing light particles",
                "mood": "optimistic and engaging",
                "key_elements": ["laptop or tablet", "floating data visualizations", "warm ambient lighting"],
                "background_style": "modern minimalist workspace with soft gradients",
                "lighting": "soft studio lighting with warm accents",
                "color_scheme": colors,
                "composition": "character slightly off-center with visual elements balanced around them"
            }

    async def generate_blog_image(
        self,
        title: str,
        summary: str,
        style: str = "modern, minimalist, professional",
        image_type: str = "hero",
        topic_id: Optional[str] = None,
        use_smart_prompt: bool = True
    ) -> ImageGenerationResult:
        """
        ブログ記事用の画像を生成する（スマートプロンプト対応）

        Args:
            title: 記事タイトル
            summary: 記事概要
            style: 画像スタイル
            image_type: 画像タイプ（hero, section, thumbnail）
            topic_id: トピックID（カラースキーム決定用）
            use_smart_prompt: スマートプロンプト生成を使用するか

        Returns:
            ImageGenerationResult: 生成結果
        """
        if use_smart_prompt:
            # 記事を分析してアニメ風キャラクター入りのスマートプロンプトを生成
            analysis = await self.analyze_for_image_prompt(title, summary, topic_id)

            colors = analysis.get("color_scheme", self.TOPIC_COLORS["default"])

            prompt = f"""Generate a WIDESCREEN 16:9 LANDSCAPE illustration in MODERN JAPANESE ANIME STYLE.

=== MANDATORY IMAGE DIMENSIONS ===
OUTPUT FORMAT: 16:9 WIDESCREEN ONLY
- The image MUST be wide and horizontal (landscape)
- Width MUST be much greater than height (ratio 16:9, like a movie screen)
- DO NOT create square images
- DO NOT create portrait/vertical images
- Example dimensions: 1920x1080, 1280x720, 1600x900

=== CHARACTER (REQUIRED) ===
Main Character: {analysis.get('main_character', 'a young professional with a friendly expression')}
Action/Pose: {analysis.get('character_action', 'looking thoughtfully at floating information')}

=== VISUAL CONCEPT ===
Visual Metaphor: {analysis.get('visual_metaphor', 'knowledge and discovery')}

=== ENVIRONMENT & ELEMENTS ===
{chr(10).join([f"- {elem}" for elem in analysis.get('key_elements', ['modern workspace', 'digital elements'])])}

=== STYLE & MOOD ===
- Art Style: Modern Japanese anime (clean lines, expressive features, stylized but relatable)
- Mood: {analysis.get('mood', 'optimistic and engaging')}
- Composition: {analysis.get('composition', 'character-focused with balanced visual elements')} - use the WIDE canvas
- Background: {analysis.get('background_style', 'soft gradient with subtle details')}
- Lighting: {analysis.get('lighting', 'soft studio lighting')}

=== COLOR PALETTE ===
- Primary color: {colors['primary']} ({colors['name']})
- Accent color: {colors['accent']}
- Skin tones: Natural and warm

=== TECHNICAL REQUIREMENTS ===
- MANDATORY: 16:9 widescreen horizontal landscape format
- High resolution, crisp details
- No text, words, or letters in the image
- Character positioned to utilize the wide format
- Clean, professional anime art style (NOT chibi, NOT overly cartoonish)
- Leave negative space on sides for text overlay

Generate a 16:9 WIDESCREEN anime illustration for: "{title[:100]}" """

        else:
            # シンプルなアニメ風プロンプト（16:9横長）+ キャラクター多様性
            # ランダムな性別・年齢を選択（多様性のため）
            random_gender = random.choice(self.CHARACTER_GENDERS)
            random_age = random.choice(self.CHARACTER_AGES)
            random_appearance = random.choice(self.CHARACTER_APPEARANCES)

            prompt = f"""Generate a WIDESCREEN 16:9 LANDSCAPE illustration in MODERN JAPANESE ANIME STYLE.

=== MANDATORY IMAGE DIMENSIONS ===
OUTPUT FORMAT: 16:9 WIDESCREEN ONLY
- The image MUST be wide and horizontal (landscape orientation)
- Width MUST be much greater than height (ratio 16:9, like a movie screen)
- DO NOT create square images
- DO NOT create portrait/vertical images
- Example dimensions: 1920x1080, 1280x720, 1600x900
- The ENTIRE image frame must be 16:9 horizontal

=== ARTICLE INFORMATION ===
Title: {title}
Summary: {summary}

=== CHARACTER REQUIREMENTS (MANDATORY) ===
Main Character: A {random_gender} character, {random_age}, {random_appearance}
- Character should be engaging with the topic (reading, working, thinking, explaining)
- Modern, relatable anime character design
- NOT chibi style, NOT overly cartoonish
- Natural proportions, expressive face

=== STYLE REQUIREMENTS ===
- Modern Japanese anime art style (clean lines, expressive eyes)
- {style}
- Professional and polished appearance
- High quality, detailed illustration
- No text, words, or letters in the image
- Leave some space on sides for text overlay

Generate a visually engaging 16:9 WIDESCREEN anime illustration that captures the essence of this article."""

        logger.info(f"Generating image with {'smart' if use_smart_prompt else 'simple'} prompt for: {title[:50]}...")

        return await self.generate_image(prompt)

    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        PCM（生の音声データ）をWAV形式に変換する

        Args:
            pcm_data: PCMバイナリデータ
            sample_rate: サンプルレート（デフォルト: 24000 Hz）
            channels: チャンネル数（デフォルト: 1 = モノラル）
            sample_width: サンプル幅（デフォルト: 2 = 16ビット）

        Returns:
            WAV形式のバイナリデータ
        """
        import io
        import wave

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

        wav_buffer.seek(0)
        return wav_buffer.read()

    async def generate_audio(
        self,
        text: str,
        voice: str = "default",
        model: str = None
    ) -> AudioGenerationResult:
        """
        Gemini 2.5 Flash TTSで音声を生成する

        Args:
            text: 読み上げるテキスト
            voice: 音声タイプ（default, bright, calm, warm）
            model: 使用モデル（デフォルト: gemini-2.5-flash-preview-tts）

        Returns:
            AudioGenerationResult: 生成結果（WAV形式の音声バイナリデータ）
        """
        model = model or self.MODEL_TTS
        voice_name = self.TTS_VOICES.get(voice, self.TTS_VOICES["default"])

        logger.info(f"Generating audio with voice '{voice_name}': {text[:50]}...")

        try:
            # TTS用の設定（公式ドキュメントに準拠）
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=text,
                config=config
            )

            # レスポンスから音声データを抽出（PCM形式）
            pcm_data = None
            if response.candidates and len(response.candidates) > 0:
                parts = response.candidates[0].content.parts
                for part in parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        data = part.inline_data.data
                        if isinstance(data, str):
                            import base64
                            pcm_data = base64.b64decode(data)
                        else:
                            pcm_data = data
                        break

            if not pcm_data:
                raise ValueError("No audio data in response")

            # PCMデータサイズの検証（WAVヘッダー分より大きければOK）
            # 以前は5KB以上を要求していたが、短いテキストの場合もあるため緩和
            MIN_PCM_SIZE = 100  # 最低100バイト（ほぼ無条件で通す）
            if len(pcm_data) < MIN_PCM_SIZE:
                raise ValueError(f"PCM data too small: {len(pcm_data)} bytes (minimum: {MIN_PCM_SIZE})")

            logger.info(f"PCM audio data received: {len(pcm_data)} bytes")

            # PCMデータをWAV形式に変換（24000Hz, 16bit, mono）
            wav_data = self._pcm_to_wav(pcm_data, sample_rate=24000, channels=1, sample_width=2)
            logger.info(f"WAV audio generated: {len(wav_data)} bytes")

            # WAVデータの検証（ヘッダー + PCMデータ = 44 + PCMサイズ）
            expected_wav_size = 44 + len(pcm_data)  # WAVヘッダー44バイト
            if len(wav_data) < expected_wav_size - 10:  # 多少の誤差を許容
                raise ValueError(f"WAV conversion failed: expected ~{expected_wav_size} bytes, got {len(wav_data)}")

            # 音声の長さを計算（概算）
            duration_seconds = len(pcm_data) / (24000 * 2)  # 24000Hz, 16bit
            logger.info(f"Audio duration: ~{duration_seconds:.1f} seconds")

            return AudioGenerationResult(
                audio_data=wav_data,
                model=model,
                text=text,
                duration_seconds=duration_seconds
            )

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise

    async def analyze_article_for_video(
        self,
        title: str,
        content: str,
        summary: str = ""
    ) -> Dict[str, Any]:
        """
        ブログ記事全体を分析して動画用の要素を抽出

        Args:
            title: 記事タイトル
            content: 記事本文（マークダウン）
            summary: 記事概要（オプション）

        Returns:
            動画用に構造化された記事分析結果
        """
        # 記事が長い場合は最初の部分を使用（API制限対策）
        content_for_analysis = content[:8000] if len(content) > 8000 else content

        prompt = f"""以下のブログ記事を分析して、動画用のコンテンツを抽出してください。

【記事タイトル】
{title}

【記事概要】
{summary}

【記事本文】
{content_for_analysis}

【抽出内容】以下のJSON形式で出力してください:
{{
    "main_theme": "記事の主要テーマ（1文で）",
    "key_message": "読者に伝えたい最も重要なメッセージ（1文で）",
    "sections": [
        {{
            "title": "セクションタイトル",
            "key_point": "そのセクションの要点（1-2文）",
            "stat_or_fact": "印象的な数値やファクト（あれば）"
        }}
    ],
    "statistics": ["記事内の重要な数値データ（最大5つ）"],
    "expert_quotes": ["専門家の引用や研究結果（最大3つ）"],
    "action_items": ["読者が実践できるアクション（最大3つ）"],
    "narrative_arc": {{
        "hook": "冒頭で注意を引くポイント",
        "problem": "提起される問題や課題",
        "solution": "提示される解決策",
        "conclusion": "結論・まとめ"
    }},
    "video_points": ["動画で強調すべきポイント（最大5つ、各20文字以内）"]
}}

【注意事項】
- 記事の本質的な内容を抽出する
- 具体的で視聴者に価値のある情報を優先
- 抽象的・一般的な内容は避ける
- JSON形式のみを出力、余計な説明は不要"""

        try:
            result = await self.generate_content(
                prompt=prompt,
                model=self.MODEL_FLASH,
                temperature=0.3  # 一貫性のため低めに
            )

            # JSONをパース
            import json
            import re
            text = result.text.strip()
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                analysis = json.loads(json_match.group())
                logger.info(f"Article analysis completed: {len(analysis.get('sections', []))} sections found")
                return analysis
            else:
                raise ValueError("No valid JSON found")

        except Exception as e:
            logger.warning(f"Article analysis failed, using fallback: {e}")
            # フォールバック
            return {
                "main_theme": title,
                "key_message": summary[:100] if summary else title,
                "sections": [],
                "statistics": [],
                "expert_quotes": [],
                "action_items": [],
                "narrative_arc": {
                    "hook": title,
                    "problem": "",
                    "solution": "",
                    "conclusion": ""
                },
                "video_points": []
            }

    async def generate_narration_script(
        self,
        title: str,
        summary: str,
        points: List[str],
        duration_seconds: int = 30,
        full_content: str = "",
        article_analysis: Dict = None
    ) -> str:
        """
        ブログ動画用のナレーションスクリプトを生成（記事全体を考慮）

        Args:
            title: 記事タイトル
            summary: 記事概要
            points: 主要ポイントのリスト
            duration_seconds: 動画の長さ（秒）
            full_content: 記事全文（オプション）
            article_analysis: 記事分析結果（オプション）

        Returns:
            ナレーションスクリプト（読み上げ用テキスト）
        """
        points_text = "\n".join([f"- {p}" for p in points])

        # 文字数の目安: 日本語で約4文字/秒
        target_chars = duration_seconds * 4

        # 記事分析結果がある場合は追加情報として使用
        analysis_context = ""
        if article_analysis:
            stats = article_analysis.get("statistics", [])
            quotes = article_analysis.get("expert_quotes", [])
            arc = article_analysis.get("narrative_arc", {})

            if stats:
                analysis_context += f"\n【重要な数値データ】\n" + "\n".join([f"- {s}" for s in stats[:3]])
            if quotes:
                analysis_context += f"\n【専門家の知見】\n" + "\n".join([f"- {q}" for q in quotes[:2]])
            if arc.get("hook"):
                analysis_context += f"\n【ストーリーの流れ】\n- 導入: {arc.get('hook', '')}\n- 問題提起: {arc.get('problem', '')}\n- 解決策: {arc.get('solution', '')}\n- 結論: {arc.get('conclusion', '')}"

        # 記事本文から抜粋（分析結果がない場合のフォールバック）
        content_excerpt = ""
        if full_content and not article_analysis:
            content_excerpt = f"\n【記事本文（抜粋）】\n{full_content[:1500]}"

        prompt = f"""以下のブログ記事情報から、{duration_seconds}秒間のナレーション用スクリプトを作成してください。
記事全体の内容を考慮し、視聴者に価値のある情報を凝縮して伝えてください。

【記事タイトル】
{title}

【記事概要】
{summary}

【主要ポイント】
{points_text}
{analysis_context}
{content_excerpt}

【スクリプト作成ルール】
1. 約{target_chars}文字程度（{duration_seconds}秒で読み上げる量）
2. 自然な話し言葉で、聞きやすいリズム
3. 以下の構成で作成:
   - 冒頭（5秒）: 視聴者の興味を引く導入
   - 本文（20秒）: 記事の核心部分と具体的な情報
   - 締め（5秒）: 視聴者へのメッセージ
4. 記事全体の価値を凝縮して伝える
5. 具体的な数値やファクトを含める（あれば）
6. 絵文字や記号は使用しない
7. 押し付けがましい表現は避け、専門的だが親しみやすいトーンで

【出力形式】
ナレーションスクリプトのみを出力してください。余計な説明は不要です。"""

        try:
            result = await self.generate_content(
                prompt=prompt,
                model=self.MODEL_FLASH,
                temperature=0.7
            )
            return result.text.strip()
        except Exception as e:
            logger.error(f"Narration script generation failed: {e}")
            # フォールバック: シンプルなスクリプト
            return f"{title}。{summary[:100]}"

    async def generate_video_narration(
        self,
        title: str,
        summary: str,
        points: List[str],
        duration_seconds: int = 30,
        voice: str = "default",
        full_content: str = "",
        analyze_content: bool = True
    ) -> Dict[str, Any]:
        """
        ブログ動画用のナレーション音声を一括生成（記事全体を分析）

        Args:
            title: 記事タイトル
            summary: 記事概要
            points: 主要ポイントのリスト
            duration_seconds: 動画の長さ（秒）
            voice: 音声タイプ
            full_content: 記事全文（オプション）
            analyze_content: 記事を分析してより良いナレーションを生成するか

        Returns:
            ナレーション結果（スクリプト、音声データ、記事分析）
        """
        logger.info(f"Generating video narration for: {title[:50]}...")
        logger.info(f"Full content provided: {len(full_content)} chars, analyze: {analyze_content}")

        article_analysis = None

        try:
            # 1. 記事全体を分析（コンテンツがある場合）
            if full_content and analyze_content:
                logger.info("Analyzing full article content for video...")
                article_analysis = await self.analyze_article_for_video(
                    title=title,
                    content=full_content,
                    summary=summary
                )

                # 分析結果からポイントを補完
                video_points = article_analysis.get("video_points", [])
                if video_points:
                    # 既存のポイントに分析結果を追加
                    points = list(set(points + video_points))[:5]
                    logger.info(f"Enhanced points with analysis: {len(points)} points")

            # 2. ナレーションスクリプトを生成（記事分析を活用）
            script = await self.generate_narration_script(
                title=title,
                summary=summary,
                points=points,
                duration_seconds=duration_seconds,
                full_content=full_content,
                article_analysis=article_analysis
            )
            logger.info(f"Narration script generated: {len(script)} chars")

            # 3. TTSで音声を生成
            audio_result = await self.generate_audio(
                text=script,
                voice=voice
            )

            return {
                "status": "success",
                "script": script,
                "audio_data": audio_result.audio_data,
                "audio_size_bytes": len(audio_result.audio_data),
                "voice": voice,
                "article_analysis": article_analysis,
                "enhanced_points": points
            }

        except Exception as e:
            logger.error(f"Video narration generation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "script": None,
                "audio_data": None,
                "article_analysis": article_analysis
            }

    async def generate_slide_narration(
        self,
        slides: List[Dict[str, Any]],
        title: str,
        topic: str = "ai_tools",
        voice: str = "default",
        slide_duration: int = 5
    ) -> Dict[str, Any]:
        """
        スライドベースのナレーション音声を生成

        Args:
            slides: スライドデータのリスト（heading, points, type）
            title: 記事タイトル
            topic: トピックID
            voice: 音声タイプ
            slide_duration: 各スライドの表示時間（秒）

        Returns:
            各スライドのナレーションスクリプトと統合音声データ
        """
        logger.info(f"Generating slide narration for {len(slides)} slides...")

        try:
            # 1. スライド全体のナレーションスクリプトを生成
            slides_info = "\n".join([
                f"スライド{i+1} ({s.get('type', 'content')}): {s.get('heading', '')} - {', '.join(s.get('points', []))}"
                for i, s in enumerate(slides)
            ])

            total_duration = len(slides) * slide_duration
            target_chars = total_duration * 4  # 1秒あたり約4文字

            prompt = f"""以下のプレゼンテーションスライドを解説するナレーションスクリプトを作成してください。

【タイトル】
{title}

【スライド構成】
{slides_info}

【スクリプト作成ルール】
1. 合計{total_duration}秒（約{target_chars}文字）で、各スライドを{slide_duration}秒程度で解説
2. 自然な話し言葉で、プレゼンテーション解説者のように
3. 構成:
   - タイトルスライド: 導入と期待感を醸成
   - コンテンツスライド: 各ポイントを簡潔に説明
   - エンディング: まとめと次のアクションを促す
4. スライド間の接続詞を適切に使用
5. 絵文字や記号は使用しない
6. 専門的だが親しみやすいトーンで

【出力形式】
ナレーションスクリプト全文のみを出力してください。"""

            result = await self.generate_content(
                prompt=prompt,
                model=self.MODEL_FLASH,
                temperature=0.7
            )
            script = result.text.strip()
            logger.info(f"Slide narration script generated: {len(script)} chars")

            # 2. TTSで音声を生成
            audio_result = await self.generate_audio(
                text=script,
                voice=voice
            )

            return {
                "status": "success",
                "script": script,
                "audio_data": audio_result.audio_data,
                "audio_size_bytes": len(audio_result.audio_data),
                "voice": voice,
                "slide_count": len(slides),
                "total_duration": total_duration
            }

        except Exception as e:
            logger.error(f"Slide narration generation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "script": None,
                "audio_data": None
            }
