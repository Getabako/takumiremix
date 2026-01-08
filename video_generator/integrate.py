#!/usr/bin/env python3
"""
既存ブログシステムとの統合モジュール

if-blog-auto システムと新しい動画生成ワークフローを接続します。

使用方法:
    from video_generator.integrate import generate_blog_video

    result = await generate_blog_video(
        article=article_data,
        output_dir=Path("output/videos")
    )
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 相対インポート対応
import sys
sys.path.insert(0, str(Path(__file__).parent))

from main import VideoGeneratorWorkflow, VideoConfig

logger = logging.getLogger(__name__)


@dataclass
class BlogVideoResult:
    """ブログ動画生成結果"""
    status: str  # "success", "partial", "error"
    video_path: Optional[str] = None
    duration: float = 0.0
    scenes_count: int = 0
    has_audio: bool = False
    error: Optional[str] = None


async def generate_blog_video(
    article: Dict[str, Any],
    output_dir: Path = None,
    num_scenes: int = 6,
    voice: str = "default"
) -> BlogVideoResult:
    """
    ブログ記事から動画を生成（既存システム互換）

    Args:
        article: 記事データ
            - title: 記事タイトル
            - content: 記事本文
            - summary: 記事要約（オプション）
            - topic_id: トピックID（オプション）
        output_dir: 出力ディレクトリ
        num_scenes: シーン数
        voice: 音声タイプ

    Returns:
        BlogVideoResult: 生成結果
    """
    try:
        # 出力ディレクトリ設定
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "output"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 記事データを取得
        title = article.get("title", "Untitled")
        content = article.get("content", "")
        summary = article.get("summary", "")
        topic_id = article.get("topic_id", "general")

        if not content:
            return BlogVideoResult(
                status="error",
                error="No content provided"
            )

        # ブログコンテンツを構築
        blog_content = f"""# {title}

{summary}

{content}
"""

        # 音声タイプをトピックに基づいて選択
        voice_map = {
            "psychology": "calm",
            "education": "default",
            "startup": "energetic",
            "investment": "warm",
            "ai_tools": "default",
            "inclusive_education": "warm",
            "weekly_summary": "default"
        }
        selected_voice = voice_map.get(topic_id, voice)

        # ワークフロー実行
        logger.info(f"Generating video for: {title}")
        logger.info(f"Topic: {topic_id}, Voice: {selected_voice}, Scenes: {num_scenes}")

        workflow = VideoGeneratorWorkflow(str(output_dir))

        # 出力名を生成
        import re
        from datetime import datetime
        safe_title = re.sub(r'[^\w\s-]', '', title)[:30]
        output_name = f"{datetime.now().strftime('%Y%m%d')}_{safe_title}"

        video_path = await workflow.generate_from_text(
            blog_content,
            output_name,
            num_scenes,
            selected_voice
        )

        # 結果を返す
        return BlogVideoResult(
            status="success",
            video_path=video_path,
            duration=num_scenes * 12.0,  # 概算
            scenes_count=num_scenes,
            has_audio=True
        )

    except Exception as e:
        logger.error(f"Video generation error: {e}")
        return BlogVideoResult(
            status="error",
            error=str(e)
        )


async def generate_slide_video_enhanced(
    article: Dict[str, Any],
    slides: list = None,
    output_dir: Path = None
) -> BlogVideoResult:
    """
    既存のスライド動画生成を拡張

    スライドデータがあれば使用、なければ記事から生成

    Args:
        article: 記事データ
        slides: スライドデータ（オプション）
        output_dir: 出力ディレクトリ

    Returns:
        BlogVideoResult: 生成結果
    """
    try:
        if slides and len(slides) > 0:
            # 既存スライドを使用
            logger.info(f"Using {len(slides)} existing slides")
            num_scenes = len(slides)
        else:
            # スライドなし、記事から生成
            num_scenes = 6

        return await generate_blog_video(
            article=article,
            output_dir=output_dir,
            num_scenes=num_scenes
        )

    except Exception as e:
        logger.error(f"Enhanced video generation error: {e}")
        return BlogVideoResult(
            status="error",
            error=str(e)
        )


# =============================================================================
# 既存システムとの互換レイヤー
# =============================================================================

def convert_to_legacy_format(result: BlogVideoResult) -> Dict[str, Any]:
    """
    BlogVideoResultを既存システムの形式に変換

    Args:
        result: BlogVideoResult

    Returns:
        既存システム互換の辞書形式
    """
    return {
        "status": result.status,
        "videos": {
            "standard": {
                "path": result.video_path,
                "duration": result.duration,
                "has_audio": result.has_audio,
                "width": 1920,
                "height": 1080
            }
        },
        "error": result.error
    }


# =============================================================================
# CLI テスト
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test video integration")
    parser.add_argument("--title", default="テスト記事", help="記事タイトル")
    parser.add_argument("--content", default="これはテスト記事です。AIについて説明します。", help="記事内容")
    args = parser.parse_args()

    async def test():
        result = await generate_blog_video(
            article={
                "title": args.title,
                "content": args.content,
                "topic_id": "ai_tools"
            },
            num_scenes=4
        )
        print(f"Result: {result}")
        return result

    asyncio.run(test())
