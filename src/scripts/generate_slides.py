#!/usr/bin/env python3
"""
スライド生成スクリプト - Marp + Gemini Edition

ブログ記事からプレゼンテーションスライドを自動生成:
1. Gemini 3 Pro Preview でスライド構成生成
2. Gemini 2.5 Flash image で各スライド用画像生成
3. Marp CLI で PDF エクスポート
4. PDF を個別 PNG 画像に変換

使用方法:
    python generate_slides.py --title "記事タイトル" --content "記事本文"
"""
import asyncio
import argparse
import json
import logging
import subprocess
import shutil
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.timezone import get_timestamp_jst, format_date
from lib.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlideGenerationError(Exception):
    """スライド生成エラー"""
    pass


# トピック別カラースキーム（紫禁止）
TOPIC_COLORS = {
    "psychology": {
        "primary": "#00b4d8",
        "secondary": "#90e0ef",
        "bg": "#1a1a2e",
        "bg_secondary": "#16213e",
        "name": "心理学・メンタルヘルス"
    },
    "education": {
        "primary": "#10b981",
        "secondary": "#6ee7b7",
        "bg": "#1a1a2e",
        "bg_secondary": "#0d1f22",
        "name": "教育・学習科学"
    },
    "startup": {
        "primary": "#f59e0b",
        "secondary": "#fcd34d",
        "bg": "#1a1a2e",
        "bg_secondary": "#1f1a0d",
        "name": "起業家育成"
    },
    "investment": {
        "primary": "#14b8a6",
        "secondary": "#5eead4",
        "bg": "#1a1a2e",
        "bg_secondary": "#0d1f1d",
        "name": "投資教育"
    },
    "ai_tools": {
        "primary": "#3b82f6",
        "secondary": "#93c5fd",
        "bg": "#1a1a2e",
        "bg_secondary": "#0d1528",
        "name": "AIツール"
    },
    "inclusive_education": {
        "primary": "#06b6d4",
        "secondary": "#67e8f9",
        "bg": "#1a1a2e",
        "bg_secondary": "#0d1f22",
        "name": "インクルーシブ教育"
    },
    "weekly_summary": {
        "primary": "#0ea5e9",
        "secondary": "#7dd3fc",
        "bg": "#1a1a2e",
        "bg_secondary": "#0d1825",
        "name": "週間総括"
    }
}

# キャラクター多様性設定
CHARACTER_GENDERS = ["male", "female"]
CHARACTER_AGES = [
    "child (8-12 years old)",
    "teenager (13-17 years old)",
    "young adult (18-25 years old)",
    "adult (26-40 years old)",
    "middle-aged (41-55 years old)"
]


class SlideGenerator:
    """スライド自動生成クラス"""

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "slides"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.gemini_client = None

    def _get_gemini_client(self) -> GeminiClient:
        """GeminiClientを取得"""
        if self.gemini_client is None:
            self.gemini_client = GeminiClient()
        return self.gemini_client

    def _check_dependencies(self) -> Dict[str, bool]:
        """依存関係をチェック"""
        deps = {
            "marp_cli": False,
            "poppler": False,
            "pdf2image": False
        }

        # Marp CLI チェック
        try:
            result = subprocess.run(
                ["npx", "@marp-team/marp-cli", "--version"],
                capture_output=True, text=True, timeout=30
            )
            deps["marp_cli"] = result.returncode == 0
        except Exception:
            pass

        # pdf2image チェック
        try:
            from pdf2image import convert_from_path
            deps["pdf2image"] = True
        except ImportError:
            pass

        # Poppler チェック (pdftoppm)
        try:
            result = subprocess.run(
                ["pdftoppm", "-v"],
                capture_output=True, text=True, timeout=10
            )
            deps["poppler"] = True
        except Exception:
            pass

        return deps

    async def _generate_slide_structure(
        self,
        title: str,
        content: str,
        topic: str,
        target_slides: int = 12
    ) -> List[Dict]:
        """
        Gemini 3 Pro でスライド構成を生成

        Returns:
            スライドデータのリスト
        """
        client = self._get_gemini_client()
        colors = TOPIC_COLORS.get(topic, TOPIC_COLORS["ai_tools"])

        prompt = f"""あなたはプレゼンテーションの専門家です。
以下のブログ記事から、{target_slides}枚程度のスライド構成を作成してください。

## 記事タイトル
{title}

## 記事本文
{content[:8000]}

## 出力要件

1. **スライド枚数**: 10-15枚（目標: {target_slides}枚）
2. **構成**:
   - スライド1: タイトル（記事タイトル + サブタイトル）
   - スライド2: 導入・問題提起
   - スライド3-8: 本論（各ポイント1枚ずつ、箇条書き3-5項目）
   - スライド9-10: 実践アドバイス
   - スライド11-12: まとめ・結論
   - 最終スライド: CTA・エンディング

3. **各スライドのテキスト**: 最大100文字（簡潔に）
4. **箇条書き**: 1スライドあたり3-5項目

## 出力形式（JSON配列）
必ず以下のJSON形式で出力してください:
```json
[
  {{
    "slide_number": 1,
    "type": "title",
    "heading": "メインタイトル",
    "subheading": "サブタイトル",
    "points": [],
    "image_description": "タイトルにふさわしいイメージの説明"
  }},
  {{
    "slide_number": 2,
    "type": "content",
    "heading": "見出し",
    "subheading": "",
    "points": ["ポイント1", "ポイント2", "ポイント3"],
    "image_description": "このスライドを表現するイメージの説明"
  }}
]
```

JSONのみを出力してください。"""

        try:
            response = await client.generate_content(
                prompt=prompt,
                model="gemini-3-pro-preview"
            )

            # GenerationResultはdataclass、.textでテキストを取得
            response_text = response.text if hasattr(response, 'text') else str(response)

            # JSON抽出
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                slides = json.loads(json_match.group())
                logger.info(f"Generated {len(slides)} slide structures")
                return slides
            else:
                raise SlideGenerationError("JSON形式のスライド構成が見つかりません")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise SlideGenerationError(f"スライド構成のパースに失敗: {e}")

    async def _generate_slide_image(
        self,
        slide: Dict,
        slide_index: int,
        topic: str,
        output_dir: Path
    ) -> Optional[str]:
        """
        各スライド用のアニメ風画像を生成

        Returns:
            生成された画像のパス
        """
        client = self._get_gemini_client()
        colors = TOPIC_COLORS.get(topic, TOPIC_COLORS["ai_tools"])

        # キャラクター多様性
        gender = random.choice(CHARACTER_GENDERS)
        age = random.choice(CHARACTER_AGES)

        image_desc = slide.get("image_description", slide.get("heading", ""))
        slide_type = slide.get("type", "content")

        prompt = f"""Generate a WIDESCREEN 16:9 LANDSCAPE illustration in MODERN JAPANESE ANIME STYLE.

=== MANDATORY IMAGE DIMENSIONS ===
OUTPUT FORMAT: 16:9 WIDESCREEN ONLY (1920x1080, 1280x720)
- Width MUST be much greater than height
- DO NOT create square or portrait images

=== SLIDE CONTEXT ===
Slide Type: {slide_type}
Topic: {colors['name']}
Description: {image_desc}

=== CHARACTER REQUIREMENTS ===
Main Character: A {gender} character, {age}
- Engaging with the topic's theme
- Modern, relatable anime design
- NOT chibi, NOT overly cartoonish

=== STYLE ===
- Modern Japanese anime art
- Primary color: {colors['primary']}
- Clean, professional appearance
- No text or letters in the image
- Suitable for presentation slide

Generate a visually engaging 16:9 anime illustration for this presentation slide."""

        try:
            result = await client.generate_image(prompt)

            # ImageGenerationResultはdataclass、.imagesで画像リストを取得
            images = result.images if hasattr(result, 'images') else []
            if images:
                image_data = images[0]
                image_path = output_dir / f"slide_{slide_index:02d}.png"

                if isinstance(image_data, bytes):
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                elif isinstance(image_data, dict) and "data" in image_data:
                    import base64
                    data = image_data["data"]
                    if isinstance(data, str):
                        data = base64.b64decode(data)
                    with open(image_path, "wb") as f:
                        f.write(data)

                logger.info(f"Generated image for slide {slide_index}: {image_path}")
                return str(image_path)
            else:
                logger.warning(f"No images generated for slide {slide_index}")

        except Exception as e:
            logger.error(f"Image generation error for slide {slide_index}: {e}")

        return None

    def _generate_marp_markdown(
        self,
        slides: List[Dict],
        topic: str,
        title: str,
        author: str,
        date: str,
        image_dir: Path
    ) -> str:
        """
        Marp互換のマークダウンを生成
        """
        colors = TOPIC_COLORS.get(topic, TOPIC_COLORS["ai_tools"])

        # ヘッダー
        header = f"""---
marp: true
theme: default
paginate: true
backgroundColor: {colors['bg']}
color: #ffffff
style: |
  section {{
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    background: linear-gradient(135deg, {colors['bg']} 0%, {colors['bg_secondary']} 100%);
  }}
  h1 {{
    color: {colors['primary']};
    font-size: 56px;
    font-weight: 800;
    text-shadow: 0 2px 10px rgba(0,0,0,0.3);
  }}
  h2 {{
    color: {colors['secondary']};
    font-size: 40px;
    font-weight: 600;
  }}
  ul {{
    font-size: 28px;
    line-height: 1.8;
  }}
  li {{
    margin-bottom: 12px;
  }}
  p {{
    font-size: 24px;
    line-height: 1.6;
  }}
  .lead h1 {{
    font-size: 64px;
  }}
---

"""
        # スライド生成
        slide_contents = []

        for i, slide in enumerate(slides):
            slide_md = ""
            slide_type = slide.get("type", "content")
            heading = slide.get("heading", "")
            subheading = slide.get("subheading", "")
            points = slide.get("points", [])

            # 画像パス
            image_path = image_dir / f"slide_{i+1:02d}.png"
            image_ref = f"./images/slide_{i+1:02d}.png"

            if slide_type == "title":
                slide_md = f"""<!-- _class: lead -->

# {heading}

## {subheading}

![bg right:45% contain]({image_ref})

**{author}** | {date}
"""
            elif slide_type == "ending":
                slide_md = f"""<!-- _class: lead -->

# {heading}

{subheading}

![bg opacity:0.4]({image_ref})

**ブログで詳しく読む**
"""
            else:
                # 通常のコンテンツスライド
                points_md = "\n".join([f"- {p}" for p in points[:5]]) if points else ""

                # 画像位置を交互に
                if i % 2 == 0:
                    img_position = "bg left:40%"
                else:
                    img_position = "bg right:40%"

                slide_md = f"""# {heading}

![{img_position}]({image_ref})

{points_md}
"""
                if subheading:
                    slide_md = f"""# {heading}

## {subheading}

![{img_position}]({image_ref})

{points_md}
"""

            slide_contents.append(slide_md)

        # スライドを結合
        full_content = header + "\n---\n\n".join(slide_contents)
        return full_content

    async def _export_to_pdf(
        self,
        markdown_path: Path,
        output_path: Path
    ) -> bool:
        """Marp CLIでPDFエクスポート"""
        try:
            cmd = [
                "npx", "@marp-team/marp-cli",
                str(markdown_path),
                "--pdf",
                "--allow-local-files",
                "-o", str(output_path)
            ]

            logger.info(f"Running Marp CLI: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(markdown_path.parent)
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"PDF exported: {output_path}")
                return True
            else:
                logger.error(f"Marp CLI error: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"PDF export error: {e}")
            return False

    def _pdf_to_images(
        self,
        pdf_path: Path,
        output_dir: Path,
        dpi: int = 150
    ) -> List[str]:
        """PDFを個別PNG画像に変換"""
        try:
            from pdf2image import convert_from_path

            output_dir.mkdir(parents=True, exist_ok=True)

            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                fmt="png"
            )

            image_paths = []
            for i, image in enumerate(images):
                path = output_dir / f"slide_{i+1:02d}.png"
                image.save(str(path), "PNG")
                image_paths.append(str(path))
                logger.info(f"Converted slide {i+1}: {path}")

            return image_paths

        except ImportError:
            logger.error("pdf2image not installed. Run: pip install pdf2image")
            return []
        except Exception as e:
            logger.error(f"PDF to image conversion error: {e}")
            return []

    def _validate_slides(self, slides: List[Dict], image_paths: List[str]) -> Dict:
        """スライド品質を検証（3倍厳格）"""
        score = 100
        issues = []

        # スライド枚数チェック（10-15枚）
        if len(slides) < 10:
            score -= 20
            issues.append(f"スライド枚数不足: {len(slides)}枚（最低10枚必要）")
        elif len(slides) > 15:
            score -= 10
            issues.append(f"スライド枚数過多: {len(slides)}枚（最大15枚）")

        # 画像数チェック
        if len(image_paths) < len(slides):
            missing = len(slides) - len(image_paths)
            score -= missing * 5
            issues.append(f"画像不足: {missing}枚の画像がありません")

        # 各スライドのテキスト量チェック
        for i, slide in enumerate(slides):
            heading = slide.get("heading", "")
            points = slide.get("points", [])
            total_text = heading + " ".join(points)

            if len(total_text) > 200:
                score -= 3
                issues.append(f"スライド{i+1}: テキスト過多 ({len(total_text)}文字)")

            # ポイント数チェック
            if len(points) > 5:
                score -= 2
                issues.append(f"スライド{i+1}: ポイント過多 ({len(points)}項目)")

        # 構成チェック
        if slides:
            first_type = slides[0].get("type", "")
            if first_type != "title":
                score -= 10
                issues.append("最初のスライドがタイトルではありません")

        # 画像サイズチェック
        for path in image_paths:
            try:
                size = Path(path).stat().st_size
                if size < 10 * 1024:  # 10KB未満
                    score -= 5
                    issues.append(f"画像サイズ不足: {Path(path).name} ({size} bytes)")
            except Exception:
                pass

        return {
            "score": max(0, score),
            "passed": score >= 95,
            "issues": issues
        }

    async def generate_slides(
        self,
        title: str,
        content: str,
        topic: str = "ai_tools",
        author: str = "if(塾) Blog",
        target_slides: int = 12
    ) -> Dict:
        """
        メインのスライド生成処理

        Returns:
            生成結果
        """
        timestamp = get_timestamp_jst()
        date = format_date(fmt='%Y年%m月%d日')

        # 出力ディレクトリ設定
        slides_dir = self.output_dir / f"{timestamp}_{topic}"
        slides_dir.mkdir(parents=True, exist_ok=True)
        images_dir = slides_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "status": "in_progress",
            "topic": topic,
            "generated_at": timestamp
        }

        try:
            # 依存関係チェック
            deps = self._check_dependencies()
            logger.info(f"Dependencies: {deps}")

            # Step 1: スライド構成生成
            logger.info("Step 1: Generating slide structure...")
            slides = await self._generate_slide_structure(
                title=title,
                content=content,
                topic=topic,
                target_slides=target_slides
            )
            result["slide_count"] = len(slides)
            result["slides"] = slides

            # Step 2: 各スライドの画像生成
            logger.info("Step 2: Generating slide images...")
            generated_images = []
            for i, slide in enumerate(slides):
                image_path = await self._generate_slide_image(
                    slide=slide,
                    slide_index=i + 1,
                    topic=topic,
                    output_dir=images_dir
                )
                if image_path:
                    generated_images.append(image_path)
                await asyncio.sleep(0.5)  # レート制限対策

            result["generated_images"] = generated_images

            # Step 3: Marpマークダウン生成
            logger.info("Step 3: Generating Marp markdown...")
            markdown_content = self._generate_marp_markdown(
                slides=slides,
                topic=topic,
                title=title,
                author=author,
                date=date,
                image_dir=images_dir
            )

            markdown_path = slides_dir / "slides.md"
            markdown_path.write_text(markdown_content, encoding="utf-8")
            result["markdown_path"] = str(markdown_path)
            logger.info(f"Markdown saved: {markdown_path}")

            # Step 4: PDFエクスポート
            if deps.get("marp_cli"):
                logger.info("Step 4: Exporting to PDF...")
                pdf_path = slides_dir / "slides.pdf"
                pdf_success = await self._export_to_pdf(markdown_path, pdf_path)

                if pdf_success:
                    result["pdf_path"] = str(pdf_path)

                    # Step 5: PDF→画像変換
                    if deps.get("pdf2image") or deps.get("poppler"):
                        logger.info("Step 5: Converting PDF to images...")
                        final_images_dir = slides_dir / "final_images"
                        slide_images = self._pdf_to_images(pdf_path, final_images_dir)
                        result["slide_images"] = slide_images
                    else:
                        logger.warning("pdf2image/poppler not available, skipping PDF to image conversion")
                        result["slide_images"] = generated_images
                else:
                    logger.warning("PDF export failed, using generated images")
                    result["slide_images"] = generated_images
            else:
                logger.warning("Marp CLI not available, skipping PDF generation")
                result["slide_images"] = generated_images

            # 品質検証
            validation = self._validate_slides(slides, result.get("slide_images", []))
            result["quality"] = validation

            if validation["passed"]:
                result["status"] = "success"
                logger.info(f"Slides generated successfully! Score: {validation['score']}")
            else:
                result["status"] = "warning"
                logger.warning(f"Quality issues: {validation['issues']}")

        except Exception as e:
            logger.error(f"Slide generation error: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result


async def generate_slides(
    article: Dict,
    target_slides: int = 12
) -> Dict:
    """
    記事データからスライドを生成（メインエントリーポイント）

    Args:
        article: 記事データ
            - title: 記事タイトル
            - content: 記事本文
            - topic_id/topic: トピックID
        target_slides: 目標スライド枚数

    Returns:
        生成結果
    """
    generator = SlideGenerator()

    title = article.get("title", "Untitled")
    content = article.get("content", "")
    topic = article.get("topic_id") or article.get("topic", "ai_tools")

    return await generator.generate_slides(
        title=title,
        content=content,
        topic=topic,
        target_slides=target_slides
    )


def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(description="Generate presentation slides from blog article")
    parser.add_argument("--title", "-t", required=True, help="Article title")
    parser.add_argument("--content", "-c", type=str, help="Article content")
    parser.add_argument("--content-file", "-f", type=str, help="Path to content file")
    parser.add_argument("--topic", type=str, default="ai_tools", help="Topic ID")
    parser.add_argument("--slides", "-n", type=int, default=12, help="Target slide count")
    parser.add_argument("--output", "-o", type=str, help="Output directory")

    args = parser.parse_args()

    # コンテンツ読み込み
    content = args.content or ""
    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")

    if not content:
        print("Error: --content or --content-file required")
        sys.exit(1)

    article = {
        "title": args.title,
        "content": content,
        "topic_id": args.topic
    }

    result = asyncio.run(generate_slides(article, args.slides))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
