#!/usr/bin/env python3
"""
SEO最適化スクリプト - Gemini 3 Flash Preview Edition

Gemini 3 Flash Preview（思考モードオフ）を使用した高速SEO最適化。
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SEOOptimizer:
    """SEO最適化クラス"""

    def __init__(self):
        self.client = GeminiClient()
        self.model = GeminiClient.MODEL_FLASH_3  # gemini-3-flash-preview

    async def optimize(self, article: Dict) -> Dict:
        """
        記事のSEO最適化を実行

        Args:
            article: 記事データ（content, topic, title等）

        Returns:
            最適化された記事データ
        """
        content = article.get('content', '')
        topic = article.get('topic', '')

        logger.info(f"Starting SEO optimization with {self.model}")

        prompt = f"""
あなたはSEO専門家です。以下のブログ記事をSEO観点で分析し、最適化してください。

【記事】
{content}

【最適化要件】
1. **タイトル最適化**
   - 60文字以内
   - 主要キーワードを前方に配置
   - クリックしたくなる魅力的な表現

2. **メタディスクリプション**
   - 120文字以内
   - 記事の価値を明確に伝える
   - 行動喚起を含める

3. **見出し構造（H2/H3）**
   - 論理的な階層構造
   - キーワードを自然に含める
   - スキャンしやすい構成

4. **本文最適化**
   - キーワード密度: 1.5-3%
   - 読みやすい段落分け（3-4文）
   - 内部リンク・外部リンクの示唆

5. **構造化データ**
   - FAQ形式のセクションがあれば追加
   - リスト形式の活用

【出力形式】
以下のJSON形式で出力してください：
```json
{{
  "title": "最適化されたタイトル",
  "description": "最適化されたメタディスクリプション",
  "content": "最適化された記事本文（Markdown形式）",
  "seo_score": 85,
  "keywords": ["キーワード1", "キーワード2"],
  "improvements": ["改善点1", "改善点2"]
}}
```
"""

        result = await self.client.generate_content(
            prompt=prompt,
            model=self.model,
            thinking_mode=False,  # 思考モードオフで高速応答
            temperature=0.5  # SEOは正確性重視で低め
        )

        # レスポンスをパース
        try:
            # JSON部分を抽出
            response_text = result.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                optimized = json.loads(json_str)
            else:
                # JSONが見つからない場合は元のコンテンツを返す
                optimized = {
                    "title": article.get('title', ''),
                    "description": article.get('description', ''),
                    "content": result.text,
                    "seo_score": 70,
                    "keywords": [],
                    "improvements": []
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse SEO response as JSON, using raw text")
            optimized = {
                "title": article.get('title', ''),
                "description": article.get('description', ''),
                "content": result.text,
                "seo_score": 70,
                "keywords": [],
                "improvements": []
            }

        logger.info(f"SEO optimization completed. Score: {optimized.get('seo_score', 'N/A')}")

        return {
            "topic": topic,
            "title": optimized.get('title', article.get('title', '')),
            "description": optimized.get('description', ''),
            "content": optimized.get('content', content),
            "seo_score": optimized.get('seo_score', 70),
            "keywords": optimized.get('keywords', []),
            "improvements": optimized.get('improvements', []),
            "categories": article.get('categories', []),  # カテゴリを保持
            "tags": article.get('tags', []),  # タグを保持
            "optimized": True,
            "model_used": self.model
        }


async def optimize_seo(article: Dict) -> Dict:
    """
    記事のSEO最適化（メインエントリーポイント）

    Args:
        article: 記事データ

    Returns:
        最適化された記事データ
    """
    optimizer = SEOOptimizer()
    return await optimizer.optimize(article)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SEO Optimize with Gemini 3 Flash Preview")
    parser.add_argument('--content', '-c', type=str, help='Article content')
    parser.add_argument('--file', '-f', type=str, help='Article file path')
    args = parser.parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding='utf-8')
    else:
        content = args.content or "Test content for SEO optimization"

    result = asyncio.run(optimize_seo({"content": content}))
    print(json.dumps(result, ensure_ascii=False, indent=2))
