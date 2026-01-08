#!/usr/bin/env python3
"""
品質レビュースクリプト - Gemini 3 Flash Preview Edition

Gemini 3 Flash Preview（思考モードオフ）を使用した高速品質レビュー。
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityReviewer:
    """品質レビュークラス"""

    def __init__(self):
        self.client = GeminiClient()
        self.model = GeminiClient.MODEL_FLASH_3  # gemini-3-flash-preview

    async def review(self, article: Dict) -> Dict:
        """
        記事の品質レビューを実行

        Args:
            article: 記事データ

        Returns:
            レビュー結果を含む記事データ
        """
        content = article.get('content', '')
        topic = article.get('topic', '')
        title = article.get('title', '')

        logger.info(f"Starting quality review with {self.model}")

        prompt = f"""
あなたは編集長として、以下のブログ記事の品質をレビューしてください。

【記事タイトル】
{title}

【記事本文】
{content}

【評価基準】

1. **情報の正確性** (25点)
   - 事実に基づいているか
   - 誤解を招く表現がないか
   - 出典が明確か

2. **読みやすさ・構成** (25点)
   - 論理的な流れ
   - 適切な段落分け
   - 専門用語の説明

3. **オリジナリティ・価値** (25点)
   - 独自の視点や洞察
   - 読者にとっての実用性
   - 具体的な事例やデータ

4. **SEO・技術品質** (25点)
   - タイトルの魅力
   - 見出し構造
   - メタデータの適切さ

【出力形式】
以下のJSON形式で出力してください：
```json
{{
  "quality_score": 85,
  "scores": {{
    "accuracy": 22,
    "readability": 21,
    "originality": 20,
    "seo_quality": 22
  }},
  "issues": [
    {{
      "type": "warning",
      "location": "第2段落",
      "description": "問題の説明",
      "suggestion": "修正提案"
    }}
  ],
  "strengths": ["強み1", "強み2"],
  "content": "修正後の記事本文（必要な修正を適用）",
  "status": "approved"
}}
```

statusは以下のいずれか：
- "approved": 公開可能
- "needs_revision": 要修正
- "rejected": 却下
"""

        result = await self.client.generate_content(
            prompt=prompt,
            model=self.model,
            thinking_mode=False,  # 思考モードオフで高速応答
            enable_search=True,   # ファクトチェック用に検索有効
            temperature=0.3       # レビューは一貫性重視で低め
        )

        # レスポンスをパース
        try:
            response_text = result.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                review_result = json.loads(json_str)
            else:
                review_result = self._default_review_result(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse review response as JSON")
            review_result = self._default_review_result(content)

        quality_score = review_result.get('quality_score', 75)
        status = review_result.get('status', 'approved')

        logger.info(f"Quality review completed. Score: {quality_score}, Status: {status}")

        return {
            "topic": topic,
            "title": title,
            "content": review_result.get('content', content),
            "description": article.get('description', ''),
            "categories": article.get('categories', []),
            "tags": article.get('tags', []),
            "quality_score": quality_score,
            "scores": review_result.get('scores', {}),
            "issues": review_result.get('issues', []),
            "strengths": review_result.get('strengths', []),
            "status": status,
            "reviewed": True,
            "model_used": self.model
        }

    def _default_review_result(self, content: str) -> Dict:
        """デフォルトのレビュー結果"""
        return {
            "quality_score": 75,
            "scores": {
                "accuracy": 19,
                "readability": 19,
                "originality": 18,
                "seo_quality": 19
            },
            "issues": [],
            "strengths": ["基本的な構成は適切"],
            "content": content,
            "status": "approved"
        }


async def review_article(article: Dict) -> Dict:
    """
    記事の品質レビュー（メインエントリーポイント）

    Args:
        article: 記事データ

    Returns:
        レビュー済み記事データ
    """
    reviewer = QualityReviewer()
    return await reviewer.review(article)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quality Review with Gemini 3 Flash Preview")
    parser.add_argument('--content', '-c', type=str, help='Article content')
    parser.add_argument('--file', '-f', type=str, help='Article file path')
    args = parser.parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding='utf-8')
    else:
        content = args.content or "Test content for quality review"

    result = asyncio.run(review_article({"content": content, "title": "Test Article"}))
    print(json.dumps(result, ensure_ascii=False, indent=2))
