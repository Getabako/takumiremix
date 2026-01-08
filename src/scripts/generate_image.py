#!/usr/bin/env python3
"""
画像生成スクリプト - Gemini 2.5 Flash Image Edition（スマートプロンプト対応）

ブログ記事用の画像をGemini 2.5 Flash imageモデルで生成します。
記事タイトルを分析して、内容に合った具体的で多様な画像を生成します。

使用方法:
    python generate_image.py --title "記事タイトル" --summary "記事概要" --topic ai_tools
"""
import asyncio
import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.gemini_client import GeminiClient, ImageGenerationResult
from lib.timezone import get_timestamp_jst

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlogImageGenerator:
    """ブログ用画像生成クラス（スマートプロンプト対応）"""

    def __init__(self):
        self.client = GeminiClient()
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_hero_image(
        self,
        title: str,
        summary: str,
        topic_id: Optional[str] = None,
        style: str = "modern, minimalist, professional, tech-inspired",
        use_smart_prompt: bool = True
    ) -> Dict:
        """
        ヒーロー画像を生成（スマートプロンプト対応）

        Args:
            title: 記事タイトル
            summary: 記事概要
            topic_id: トピックID（カラースキーム決定用）
            style: 画像スタイル
            use_smart_prompt: スマートプロンプト生成を使用するか

        Returns:
            生成結果の辞書
        """
        logger.info(f"Generating hero image for: {title}")
        logger.info(f"Using smart prompt: {use_smart_prompt}, Topic: {topic_id}")

        result = await self.client.generate_blog_image(
            title=title,
            summary=summary,
            style=style,
            image_type="hero",
            topic_id=topic_id,
            use_smart_prompt=use_smart_prompt
        )

        return await self._save_images(result, "hero", title)

    async def generate_section_images(
        self,
        title: str,
        sections: List[Dict[str, str]],
        topic_id: Optional[str] = None,
        style: str = "clean, illustrative, informative",
        use_smart_prompt: bool = True
    ) -> List[Dict]:
        """
        セクション用画像を生成（スマートプロンプト対応）

        Args:
            title: 記事タイトル
            sections: セクション情報のリスト
            topic_id: トピックID（カラースキーム決定用）
            style: 画像スタイル
            use_smart_prompt: スマートプロンプト生成を使用するか

        Returns:
            生成結果のリスト
        """
        results = []
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Section {i+1}")
            section_content = section.get("content", "")

            logger.info(f"Generating section image {i+1}: {section_title}")

            result = await self.client.generate_blog_image(
                title=f"{title} - {section_title}",
                summary=section_content[:200],
                style=style,
                image_type="section",
                topic_id=topic_id,
                use_smart_prompt=use_smart_prompt
            )

            saved = await self._save_images(result, f"section_{i+1}", section_title)
            results.append(saved)

        return results

    async def _save_images(
        self,
        result: ImageGenerationResult,
        prefix: str,
        title: str
    ) -> Dict:
        """画像をファイルに保存（日本時間）"""
        timestamp = get_timestamp_jst()  # JST timestamp
        saved_files = []

        for i, image_data in enumerate(result.images):
            filename = f"{prefix}_{timestamp}_{i}.png"
            filepath = self.output_dir / filename

            with open(filepath, "wb") as f:
                f.write(image_data)

            logger.info(f"Saved image: {filepath}")
            saved_files.append({
                "file_path": str(filepath),
                "filename": filename,
                "size_bytes": len(image_data)
            })

        return {
            "type": prefix,
            "title": title,
            "prompt": result.prompt,
            "model": result.model,
            "images": saved_files,
            "text_response": result.text_response,
            "generated_at": timestamp
        }


async def generate_images(
    article: Dict,
    topic_id: Optional[str] = None,
    use_smart_prompt: bool = True
) -> Dict:
    """
    記事用の画像を生成（メインエントリーポイント・スマートプロンプト対応）

    Args:
        article: 記事データ
            - title: 記事タイトル
            - summary/description: 記事概要
            - sections: セクション情報（オプション）
            - topic_id: トピックID（オプション）
        topic_id: トピックID（カラースキーム決定用、articleから取得可能）
        use_smart_prompt: スマートプロンプト生成を使用するか

    Returns:
        生成結果
    """
    generator = BlogImageGenerator()

    title = article.get("title", "Untitled Article")
    summary = article.get("summary") or article.get("description", "")
    sections = article.get("sections", [])

    # topic_idは引数またはarticleから取得
    effective_topic_id = topic_id or article.get("topic_id") or article.get("topic")

    results = {
        "status": "success",
        "hero": None,
        "sections": [],
        "total_images": 0,
        "topic_id": effective_topic_id,
        "smart_prompt_used": use_smart_prompt
    }

    try:
        # ヒーロー画像生成（スマートプロンプト使用）
        hero_result = await generator.generate_hero_image(
            title=title,
            summary=summary,
            topic_id=effective_topic_id,
            use_smart_prompt=use_smart_prompt
        )
        results["hero"] = hero_result
        results["total_images"] += len(hero_result.get("images", []))

        # セクション画像生成（セクションがある場合）
        if sections:
            section_results = await generator.generate_section_images(
                title=title,
                sections=sections[:3],  # 最大3セクション
                topic_id=effective_topic_id,
                use_smart_prompt=use_smart_prompt
            )
            results["sections"] = section_results
            for sr in section_results:
                results["total_images"] += len(sr.get("images", []))

        logger.info(f"Total images generated: {results['total_images']}")
        logger.info(f"Smart prompt used: {use_smart_prompt}")

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        results["status"] = "error"
        results["error"] = str(e)

    return results


def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Generate blog images with Gemini 2.5 Flash (Smart Prompt)"
    )
    parser.add_argument("--title", "-t", required=True, help="Article title")
    parser.add_argument("--summary", "-s", required=True, help="Article summary")
    parser.add_argument("--topic", type=str, help="Topic ID for color scheme (e.g., ai_tools, psychology)")
    parser.add_argument("--sections", "-sec", type=str, help="JSON string of sections")
    parser.add_argument("--output", "-o", type=str, help="Output directory")
    parser.add_argument("--no-smart-prompt", action="store_true",
                        help="Disable smart prompt generation (use simple prompt)")

    args = parser.parse_args()

    article = {
        "title": args.title,
        "summary": args.summary,
        "topic_id": args.topic
    }

    if args.sections:
        try:
            article["sections"] = json.loads(args.sections)
        except json.JSONDecodeError:
            logger.warning("Invalid sections JSON, ignoring")

    result = asyncio.run(generate_images(
        article=article,
        topic_id=args.topic,
        use_smart_prompt=not args.no_smart_prompt
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
