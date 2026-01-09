#!/usr/bin/env python3
"""
ブログ自動生成メインスクリプト - GitHub Pages Edition

システムフロー:
1. 情報収集（Google Search: 通常、Deep Research: 日曜のみ）
2. Gemini 3 Pro (ブログ生成)
3. Gemini 2.5 Flash (画像生成)
4. 動画生成（2つのモード）:
   - 従来モード: Remotion + TTS（30秒概要動画）
   - スライドモード（推奨）: スライド生成 → Marp PDF → Remotion動画
5. SEO最適化 & レビュー
6. 品質評価（95%合格ライン）
7. GitHub Pages投稿

設計方針:
- Google Search Tool: 日常的な情報収集（メイン・デフォルト）
- Deep Research: 週1回（日曜日）の深層調査
- スライドベース動画: 高品質な解説動画を自動生成（推奨）
"""
import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

# Load .env file for local development
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Main] Loaded environment from: {env_path}")
except ImportError:
    pass  # dotenv not installed, use environment variables directly

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.timezone import format_date

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description='Blog Auto Generator - GitHub Pages Edition')
    parser.add_argument('--topic', required=True, help='Topic ID')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no publish)')
    parser.add_argument('--use-deep-research', action='store_true', default=False,
                        help='Use Deep Research API (default: False, use Google Search)')
    parser.add_argument('--skip-images', action='store_true', help='Skip image generation')
    parser.add_argument('--skip-video', action='store_true', help='Skip video generation')
    parser.add_argument('--use-slide-video', action='store_true', default=True,
                        help='Use slide-based video generation (default: True, recommended)')
    parser.add_argument('--slide-count', type=int, default=6,
                        help='Target slide count for slide-based video (default: 6, max 6 for 30s video)')
    parser.add_argument('--slide-duration', type=int, default=5,
                        help='Duration per slide in seconds (default: 5)')
    parser.add_argument('--publish', action='store_true', default=True,
                        help='Publish to GitHub Pages (default: True)')
    args = parser.parse_args()

    logger.info(f"Starting blog generation for topic: {args.topic}")
    logger.info(f"Mode: {'Dry run' if args.dry_run else 'Production'}")

    # Import modules
    from research import run_research
    from generate_content import generate_article
    from generate_image import generate_images
    from seo_optimize import optimize_seo
    from review import review_article
    from publish import publish_to_github_pages
    from quality_evaluator import QualityEvaluator
    # Note: video_generator_voicepeak is imported dynamically in Step 4

    result = {
        "topic": args.topic,
        "status": "in_progress",
        "steps": {}
    }

    try:
        # Step 1: 情報収集（Google Search or Deep Research）
        logger.info("=" * 50)
        research_method = "Deep Research" if args.use_deep_research else "Google Search"
        logger.info(f"Step 1: Running {research_method}...")
        logger.info("=" * 50)
        research_data = await run_research(args.topic, args.use_deep_research)
        result["steps"]["research"] = {
            "status": "completed",
            "sources_count": len(research_data.get("sources", []))
        }
        logger.info(f"Research completed. Found {len(research_data.get('sources', []))} sources.")

        # Step 2: Gemini 3 Pro (ブログ生成)
        logger.info("=" * 50)
        logger.info("Step 2: Generating content with Gemini 3 Pro...")
        logger.info("=" * 50)
        article = await generate_article(args.topic, research_data)
        result["steps"]["content"] = {
            "status": "completed",
            "word_count": article.get("word_count", 0)
        }
        logger.info(f"Content generated. Word count: {article.get('word_count', 0)}")

        # Step 3: Gemini 2.5 Flash (画像生成 - ヒーロー + セクション)
        images = {"status": "skipped"}
        if not args.skip_images:
            logger.info("=" * 50)
            logger.info("Step 3: Generating images with Gemini 2.5 Flash...")
            logger.info("=" * 50)

            # セクションを抽出してarticleに追加
            content = article.get("content", "")
            sections = []
            import re
            pattern = r'^##\s+(.+?)$'
            parts = re.split(pattern, content, flags=re.MULTILINE)
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    sections.append({
                        "title": parts[i].strip(),
                        "content": parts[i + 1].strip()[:300]
                    })

            # セクション情報を追加
            article_with_sections = {**article, "sections": sections}
            logger.info(f"Extracted {len(sections)} sections for image generation")

            images = await generate_images(article_with_sections, topic_id=args.topic)
            result["steps"]["images"] = {
                "status": images.get("status", "error"),
                "total_images": images.get("total_images", 0),
                "section_images": len(images.get("sections", []))
            }
            logger.info(f"Images generated: {images.get('total_images', 0)} (hero + {len(images.get('sections', []))} sections)")
        else:
            logger.info("Step 3: Skipping image generation")
            result["steps"]["images"] = {"status": "skipped"}

        # Step 4: 動画生成（VOICEPEAK + Marp方式）
        videos = {"status": "skipped"}
        slides_data = None
        if not args.skip_video:
            logger.info("=" * 50)
            logger.info("Step 4: Generating video (VOICEPEAK + Marp)...")
            logger.info("=" * 50)

            try:
                # 新しいVOICEPEAK動画生成システム
                from video_generator_voicepeak import BlogVideoGenerator

                video_gen = BlogVideoGenerator()

                # ブログ記事の内容から動画を生成
                blog_content = article.get("content", "")
                blog_title = article.get("title", args.topic)

                video_result = await video_gen.generate(
                    blog_content=blog_content,
                    title=blog_title,
                    topic=args.topic
                )

                if video_result.get("status") == "success":
                    videos = {
                        "status": "success",
                        "videos": {"standard": {
                            "path": video_result.get("video_path"),
                            "duration": video_result.get("duration", 0)
                        }},
                        "title": video_result.get("title", "")
                    }
                    result["steps"]["videos"] = videos
                    result["steps"]["slides"] = {
                        "status": "completed",
                        "slide_count": video_result.get("slides_count", 0)
                    }
                    logger.info(f"Video generated! Duration: {video_result.get('duration', 0):.1f}s, Slides: {video_result.get('slides_count', 0)}")
                else:
                    videos = {"status": "error", "error": video_result.get("error", "Unknown")}
                    result["steps"]["videos"] = videos
                    logger.warning(f"Video generation failed: {video_result.get('error', 'Unknown')}")

            except ImportError as e:
                logger.warning(f"Video generator import error: {e}")
                videos = {"status": "skipped", "error": str(e)}
                result["steps"]["videos"] = videos
            except Exception as e:
                logger.warning(f"Video generation error: {e}")
                videos = {"status": "error", "error": str(e)}
                result["steps"]["videos"] = videos
        else:
            logger.info("Step 4: Skipping video generation")
            result["steps"]["videos"] = {"status": "skipped"}

        # Step 5: SEO最適化
        logger.info("=" * 50)
        logger.info("Step 5: SEO optimization...")
        logger.info("=" * 50)
        optimized = await optimize_seo(article)
        result["steps"]["seo"] = {"status": "completed"}
        logger.info("SEO optimization completed.")

        # Step 6: レビュー（品質保証ループ）
        logger.info("=" * 50)
        logger.info("Step 6: Quality review...")
        logger.info("=" * 50)

        # 品質スコアが80点以上になるまでリトライ（最大3回）
        MIN_QUALITY_SCORE = 80
        MAX_REVIEW_ATTEMPTS = 3
        final = optimized
        review_attempts = 0

        for attempt in range(MAX_REVIEW_ATTEMPTS):
            review_attempts += 1
            final = await review_article(final)
            quality_score = final.get("quality_score", 0)
            status = final.get("status", "")

            logger.info(f"Review attempt {review_attempts}: Score={quality_score}, Status={status}")

            if quality_score >= MIN_QUALITY_SCORE and status == "approved":
                logger.info(f"Quality threshold met! Final score: {quality_score}")
                break
            elif attempt < MAX_REVIEW_ATTEMPTS - 1:
                logger.warning(f"Quality score {quality_score} below threshold {MIN_QUALITY_SCORE}, retrying...")
            else:
                logger.warning(f"Max attempts reached. Final score: {quality_score}")

        result["steps"]["review"] = {
            "status": "completed",
            "quality_score": final.get("quality_score", 0),
            "review_attempts": review_attempts
        }
        logger.info(f"Review completed. Final quality score: {final.get('quality_score', 0)} (after {review_attempts} attempt(s))")

        # ローカル保存（日本時間）
        output_dir = Path(__file__).parent.parent.parent / "output" / "posts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{format_date(fmt='%Y%m%d')}_{args.topic}.md"  # JST date

        if not args.dry_run:
            output_file.write_text(final['content'], encoding='utf-8')
            logger.info(f"Saved locally: {output_file}")

        # Step 7: GitHub Pages投稿
        if args.publish and not args.dry_run:
            logger.info("=" * 50)
            logger.info("Step 7: Publishing to GitHub Pages...")
            logger.info("=" * 50)

            # 記事データを構築
            # 動画データの準備（成功時は生成した動画、それ以外は空でフォールバックを使用）
            video_data = {}
            video_status = videos.get("status", "skipped")
            if video_status == "success":
                video_data = videos.get("videos", {})
                logger.info(f"Using generated videos: {list(video_data.keys())}")
            elif video_status == "partial":
                # 部分的な成功の場合も動画を使用
                video_data = videos.get("videos", {})
                logger.info(f"Using partially generated videos: {list(video_data.keys())}")
            else:
                # 失敗やスキップの場合は空で渡し、publish.pyでフォールバック
                logger.info(f"Video status '{video_status}', will use fallback in publish")

            publish_data = {
                "title": final.get("title", article.get("title", "Untitled")),
                "content": final.get("content", ""),
                "description": final.get("description", "")[:120],
                "categories": final.get("categories", [research_data.get("topic_info", {}).get("name", "未分類")]),
                "tags": final.get("tags", []),
                "images": images,
                # videosは成功/部分成功時は生成した動画、それ以外はフォールバック
                "videos": video_data,
                # トピックID（動画フォールバック用）
                "topic": args.topic,
                "topic_id": args.topic
            }

            publish_result = await publish_to_github_pages(publish_data)
            result["steps"]["publish"] = {
                "status": publish_result.get("status"),
                "public_url": publish_result.get("public_url"),
                "message": publish_result.get("message")
            }

            if publish_result.get("status") == "success":
                logger.info(f"Published! URL: {publish_result.get('public_url')}")
            else:
                logger.error(f"Publish failed: {publish_result.get('message')}")
        else:
            logger.info("Step 7: Skipping publish (dry-run mode)")
            result["steps"]["publish"] = {"status": "skipped"}

        result["status"] = "completed"
        logger.info("=" * 50)
        logger.info("Blog generation completed successfully!")
        logger.info("=" * 50)

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()

        logger.error("=" * 50)
        logger.error("BLOG GENERATION FAILED")
        logger.error("=" * 50)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {e}")
        logger.error(f"Full traceback:\n{error_traceback}")

        # エラー解析
        error_str = str(e).lower()
        if "api" in error_str or "key" in error_str:
            logger.error("[Error Analysis] API関連のエラーです。APIキーが正しく設定されているか確認してください。")
        elif "timeout" in error_str:
            logger.error("[Error Analysis] タイムアウトエラーです。ネットワーク接続を確認してください。")
        elif "rate" in error_str or "limit" in error_str:
            logger.error("[Error Analysis] レート制限に達しました。しばらく待ってから再試行してください。")
        elif "video" in error_str or "remotion" in error_str:
            logger.error("[Error Analysis] 動画生成エラーです。Remotion依存関係を確認してください。")
        elif "image" in error_str:
            logger.error("[Error Analysis] 画像生成エラーです。")
        elif "git" in error_str or "push" in error_str:
            logger.error("[Error Analysis] Git操作エラーです。リポジトリの状態を確認してください。")

        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        result["traceback"] = error_traceback
        raise

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result, ensure_ascii=False, indent=2))
