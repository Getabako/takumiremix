#!/usr/bin/env python3
"""
Video Workflow - Blog to Video with gTTS + Remotion

StockWorkFlowのgTTS音声生成とRemotionを統合した動画生成ワークフロー

ワークフロー:
1. ブログ記事からセクション抽出
2. Marpスライド生成
3. PDF → PNG変換
4. ナレーションスクリプト生成
5. gTTSで音声生成
6. タイミング情報生成（字幕用）
7. Remotionで動画レンダリング

依存関係:
- gTTS: pip install gTTS
- pydub: pip install pydub
- pdf2image: pip install pdf2image
- Marp CLI: npm install -g @marp-team/marp-cli
- Remotion: npm install (in remotion directory)
"""

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

class VideoConfig:
    """Video configuration"""
    WIDTH = 1920
    HEIGHT = 1080
    FPS = 30
    AUDIO_SPEED = 1.2  # 音声速度倍率

# ============================================================================
# gTTS Audio Generator (from StockWorkFlow)
# ============================================================================

class GTTSAudioGenerator:
    """gTTSを使った音声生成"""

    def __init__(self, speed_factor: float = 1.2):
        self.speed_factor = speed_factor

    def generate(self, text: str, output_path: Path) -> float:
        """音声を生成し、長さ（秒）を返す"""
        try:
            from gtts import gTTS
            from pydub import AudioSegment

            if not text or not text.strip():
                # 無音を生成
                silence = AudioSegment.silent(duration=2000)
                silence.export(str(output_path), format="mp3")
                return 2.0

            # gTTSで音声生成
            temp_file = output_path.with_suffix('.temp.mp3')
            tts = gTTS(text=text, lang='ja', slow=False)
            tts.save(str(temp_file))

            # pydubで速度調整
            audio = AudioSegment.from_mp3(str(temp_file))
            faster_audio = audio._spawn(audio.raw_data, overrides={
                "frame_rate": int(audio.frame_rate * self.speed_factor)
            })
            faster_audio = faster_audio.set_frame_rate(audio.frame_rate)
            faster_audio.export(str(output_path), format="mp3")

            # 一時ファイル削除
            temp_file.unlink()

            # 長さを取得
            return len(faster_audio) / 1000.0

        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            return 5.0

    def get_duration(self, audio_path: Path) -> float:
        """音声ファイルの長さを取得"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
        except:
            return 5.0

# ============================================================================
# Section Extractor
# ============================================================================

class SectionExtractor:
    """ブログ記事からセクション抽出"""

    def extract(self, content: str) -> List[Dict[str, str]]:
        """h2セクションを抽出"""
        sections = []

        # YAMLフロントマターを除去（---で囲まれた部分）
        content = self._remove_frontmatter(content)

        # タイトル（# で始まる行）を取得して除去
        title_match = re.search(r'^#\s+(.+?)$', content, flags=re.MULTILINE)
        if title_match:
            content = content[title_match.end():].strip()

        # ## で分割
        pattern = r'^##\s+(.+?)$'
        parts = re.split(pattern, content, flags=re.MULTILINE)

        # イントロ（最初の##の前）- 実際の内容がある場合のみ
        intro = self._clean_content(parts[0])
        if intro and len(intro) > 30:  # 30文字以上の実質的な内容がある場合
            sections.append({
                "title": "はじめに",
                "content": intro[:500]
            })

        # セクション
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                section_title = parts[i].strip()
                section_content = self._clean_content(parts[i + 1])
                if section_content and len(section_content) > 20:  # 内容がある場合のみ追加
                    sections.append({
                        "title": section_title,
                        "content": section_content[:500]
                    })

        # セクションが少ない場合は段落で分割
        if len(sections) < 3:
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
            for i, para in enumerate(paragraphs[:6]):
                if para not in [s['content'] for s in sections]:
                    sections.append({
                        "title": f"ポイント {i+1}",
                        "content": self._clean_content(para)[:500]
                    })

        return sections[:8]  # 最大8セクション

    def _remove_frontmatter(self, content: str) -> str:
        """YAMLフロントマターを除去"""
        # ---で始まり---で終わるフロントマターを除去
        pattern = r'^---[\s\S]*?---\s*\n?'
        content = re.sub(pattern, '', content)
        return content.strip()

    def _clean_content(self, text: str) -> str:
        """マークダウン記法を除去して読みやすいテキストに"""
        if not text:
            return ""

        # リンク [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # 強調 **text** → text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)

        # イタリック *text* → text
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # 見出し ### text → text
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        # リスト - item → item
        text = re.sub(r'^[-*+]\s+', '・', text, flags=re.MULTILINE)

        # 番号付きリスト 1. item → item
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

        # 画像 ![alt](url) → 除去
        text = re.sub(r'!\[.*?\]\([^)]*\)', '', text)

        # コードブロック ```code``` → 除去
        text = re.sub(r'```[\s\S]*?```', '', text)

        # インラインコード `code` → code
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 引用 > text → text
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

        # 余分な空白と改行
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)

        return text.strip()


# ============================================================================
# Slide Image Generator (using Gemini 2.5 Flash image)
# ============================================================================

class SlideImageGenerator:
    """Gemini 2.5 Flash imageでスライド用画像を生成"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")

    async def generate_slide_image(
        self,
        title: str,
        content: str,
        output_path: Path,
        index: int = 0
    ) -> Optional[Path]:
        """スライド用の画像を生成"""
        try:
            from google import genai
            from google.genai import types

            if not self.api_key:
                logger.warning("GOOGLE_AI_API_KEY not set, skipping image generation")
                return None

            client = genai.Client(api_key=self.api_key)

            # プロンプトを作成
            prompt = f"""Generate a simple, clean illustration for a presentation slide.

Topic: {title}
Content summary: {content[:200]}

Requirements:
- Simple, professional illustration style
- 16:9 landscape format (1920x1080)
- Clean lines, minimal detail
- Soft colors matching professional theme
- NO text, NO words, NO letters in the image
- Abstract or symbolic representation of the topic
- Modern, minimalist design suitable for tech/education presentation

Generate a 16:9 LANDSCAPE illustration."""

            logger.info(f"  Generating image for slide {index}: {title[:30]}...")

            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"]
                )
            )

            # 画像を保存
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    output_path.write_bytes(image_data)
                    logger.info(f"    Saved: {output_path.name}")
                    return output_path

            logger.warning(f"    No image generated for slide {index}")
            return None

        except Exception as e:
            logger.error(f"  Image generation error: {e}")
            return None

    async def generate_all_images(
        self,
        sections: List[Dict],
        output_dir: Path
    ) -> List[Optional[Path]]:
        """全スライドの画像を生成"""
        output_dir.mkdir(parents=True, exist_ok=True)
        images = []

        for i, section in enumerate(sections):
            image_path = output_dir / f"slide_image_{i:02d}.png"
            result = await self.generate_slide_image(
                title=section.get("title", f"Slide {i}"),
                content=section.get("content", ""),
                output_path=image_path,
                index=i
            )
            images.append(result)

            # レート制限対策
            if result:
                await asyncio.sleep(2)

        return images

# ============================================================================
# Marp Slide Generator
# ============================================================================

class MarpSlideGenerator:
    """Marpスライド生成（画像挿入対応）"""

    def generate(
        self,
        title: str,
        sections: List[Dict],
        output_path: Path,
        images: Optional[List[Optional[Path]]] = None
    ) -> str:
        """Marpマークダウンを生成（画像付き）"""
        slides = []

        # タイトルスライド
        slides.append(f"""---
marp: true
theme: default
paginate: true
backgroundColor: #1a1a2e
color: #ffffff
style: |
  section {{
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 40px 60px;
  }}
  h1 {{
    color: #00d4ff;
    font-size: 2.5em;
    text-align: center;
    margin-top: 120px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
  }}
  h2 {{
    color: #00d4ff;
    border-bottom: 3px solid #00d4ff;
    padding-bottom: 15px;
    font-size: 1.6em;
    margin-bottom: 30px;
  }}
  p, li {{
    font-size: 1.3em;
    line-height: 1.8;
    color: #e0e0e0;
  }}
  ul {{
    margin-left: 20px;
  }}
  li {{
    margin-bottom: 15px;
  }}
  img {{
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
  }}
---

# {title}

""")

        # コンテンツスライド
        for i, section in enumerate(sections):
            # ポイントを抽出
            points = self._extract_points(section["content"])
            points_md = "\n".join([f"- {p}" for p in points])

            # 画像がある場合は右側に配置
            image_md = ""
            if images and i < len(images) and images[i]:
                image_path = images[i]
                # 相対パスを使用
                image_md = f"\n![bg right:35%]({image_path.name})\n"

            slides.append(f"""---
{image_md}
## {section["title"]}

{points_md}

""")

        # エンディングスライド
        slides.append("""---

# ご視聴ありがとうございました

**if(塾) Blog**

チャンネル登録・高評価お願いします

詳しくはブログ記事をご覧ください

""")

        markdown = "\n".join(slides)
        output_path.write_text(markdown, encoding='utf-8')
        return markdown

    def _extract_points(self, content: str) -> List[str]:
        """コンテンツからポイントを抽出（より詳細に）"""
        if not content:
            return ["詳しい内容はブログ記事をご覧ください"]

        # 箇条書きがあればそれを使用
        bullet_points = re.findall(r'・(.+?)(?=・|\n\n|$)', content)
        if len(bullet_points) >= 2:
            return [p.strip() for p in bullet_points[:4] if len(p.strip()) > 5]

        # 文を分割
        sentences = re.split(r'[。！？]', content)
        points = []

        for s in sentences:
            s = s.strip()
            # 適切な長さの文を選択
            if 10 < len(s) < 100:
                # 先頭の記号を除去
                s = re.sub(r'^[・\-\*\d\.]+\s*', '', s)
                if s and len(s) > 10:
                    points.append(s)

        # ポイントが少ない場合
        if len(points) < 2:
            # コンテンツを複数行に分割
            lines = [l.strip() for l in content.split('\n') if len(l.strip()) > 15]
            for line in lines[:4]:
                if line not in points:
                    points.append(line[:80])

        # 最終的なポイントを返す
        result = points[:4] if points else [content[:100]]
        return [p for p in result if p]  # 空文字を除外

# ============================================================================
# Slide Renderer
# ============================================================================

class SlideRenderer:
    """スライドをPDF/PNGにレンダリング"""

    def render_to_pdf(self, marp_path: Path, output_path: Path) -> bool:
        """Marp → PDF"""
        try:
            cmd = ["marp", str(marp_path), "--pdf", "--allow-local-files", "-o", str(output_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return output_path.exists()
        except Exception as e:
            logger.error(f"PDF render error: {e}")
            return False

    def pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """PDF → PNG (1920x1080 for video)"""
        try:
            from pdf2image import convert_from_path
            from PIL import Image

            # 高解像度で変換（16:9アスペクト比用）
            images = convert_from_path(str(pdf_path), dpi=200)
            paths = []
            for i, img in enumerate(images):
                out = output_dir / f"slide_{i:02d}.png"

                # 1920x1080にリサイズ（アスペクト比を維持しながらフィット）
                target_size = (1920, 1080)
                img_ratio = img.width / img.height
                target_ratio = 1920 / 1080

                if img_ratio > target_ratio:
                    # 横長 - 幅に合わせる
                    new_width = 1920
                    new_height = int(1920 / img_ratio)
                else:
                    # 縦長 - 高さに合わせる
                    new_height = 1080
                    new_width = int(1080 * img_ratio)

                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # 1920x1080のキャンバスに中央配置
                canvas = Image.new('RGB', target_size, (26, 26, 46))  # #1a1a2e
                x = (1920 - new_width) // 2
                y = (1080 - new_height) // 2
                canvas.paste(img_resized, (x, y))
                canvas.save(str(out), "PNG", quality=95)
                paths.append(out)
                logger.info(f"  Slide {i}: {out.name} (1920x1080)")

            return paths
        except Exception as e:
            logger.error(f"PDF to image error: {e}")
            import traceback
            traceback.print_exc()
            return []

# ============================================================================
# Narration Generator
# ============================================================================

class NarrationGenerator:
    """ナレーションスクリプト生成"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")

    async def generate(self, title: str, sections: List[Dict]) -> List[str]:
        """各スライド用のナレーションを生成"""
        scripts = []

        # イントロ
        scripts.append(f"こんにちは。今回は「{title}」についてお話しします。")

        # セクションごと
        for section in sections:
            content = section["content"][:200]
            script = f"{section['title']}について説明します。{content}"
            # 100文字以内に収める
            if len(script) > 100:
                script = script[:97] + "..."
            scripts.append(script)

        # アウトロ
        scripts.append("以上、ご視聴ありがとうございました。詳しくはブログ記事をご覧ください。")

        return scripts

# ============================================================================
# Timing Generator (from StockWorkFlow)
# ============================================================================

class TimingGenerator:
    """字幕タイミング生成"""

    def __init__(self, fps: int = 30):
        self.fps = fps

    def generate(self, audio_files: List[Dict]) -> Dict:
        """音声ファイルからタイミング情報を生成"""
        slides_data = []
        current_time = 0

        for audio_info in audio_files:
            duration = audio_info["duration"]
            script = audio_info["script"]

            # 字幕セグメント生成
            subtitles = self._generate_subtitles(script, current_time, duration)

            slides_data.append({
                "index": audio_info["index"],
                "audioFile": audio_info["audio_file"],
                "duration": duration,
                "durationFrames": int(duration * self.fps),
                "startTime": current_time,
                "endTime": current_time + duration,
                "startFrame": int(current_time * self.fps),
                "endFrame": int((current_time + duration) * self.fps),
                "subtitles": subtitles,
                "fullScript": script
            })

            current_time += duration

        return {
            "fps": self.fps,
            "totalDuration": current_time,
            "totalFrames": int(current_time * self.fps),
            "slides": slides_data
        }

    def _generate_subtitles(self, script: str, start_time: float, duration: float) -> List[Dict]:
        """字幕セグメントを生成"""
        subtitles = []
        max_chars = 30

        # 句読点で分割
        sentences = []
        current = ""
        for char in script:
            current += char
            if char in ['。', '！', '？', '、']:
                if current.strip():
                    sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())

        # セグメント化
        segments = []
        for sentence in sentences:
            if len(sentence) <= max_chars:
                segments.append(sentence)
            else:
                # 長い文は分割
                for i in range(0, len(sentence), max_chars):
                    segments.append(sentence[i:i+max_chars])

        if not segments:
            return []

        # タイミング計算
        total_chars = sum(len(s) for s in segments)
        seg_start = start_time

        for seg in segments:
            char_ratio = len(seg) / total_chars if total_chars > 0 else 1.0 / len(segments)
            seg_duration = duration * char_ratio

            subtitles.append({
                "text": seg,
                "start": seg_start,
                "end": seg_start + seg_duration,
                "startFrame": int(seg_start * self.fps),
                "endFrame": int((seg_start + seg_duration) * self.fps)
            })

            seg_start += seg_duration

        return subtitles

# ============================================================================
# Video Renderer
# ============================================================================

class RemotionRenderer:
    """Remotionで動画レンダリング"""

    def __init__(self):
        self.remotion_dir = Path(__file__).parent.parent.parent / "remotion"

    def render(self, timings: Dict, slide_images: List[Path], output_path: Path) -> bool:
        """Remotionで動画をレンダリング"""
        try:
            # タイミングデータを保存
            timings_file = self.remotion_dir / "timings.json"
            with open(timings_file, 'w', encoding='utf-8') as f:
                json.dump(timings, f, ensure_ascii=False, indent=2)

            # スライド画像をpublicディレクトリにコピー
            slides_dir = self.remotion_dir / "public" / "slides"
            slides_dir.mkdir(parents=True, exist_ok=True)

            for i, img_path in enumerate(slide_images):
                dest = slides_dir / f"slide_{i:02d}.png"
                shutil.copy(img_path, dest)

            # 音声ファイルをpublicディレクトリにコピー
            audio_dir = self.remotion_dir / "public" / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)

            for slide in timings["slides"]:
                audio_src = Path(slide["audioFile"])
                if audio_src.exists():
                    audio_dest = audio_dir / audio_src.name
                    shutil.copy(audio_src, audio_dest)
                    # パスを更新
                    slide["audioFile"] = f"audio/{audio_src.name}"

            # 更新したタイミングデータを保存
            with open(timings_file, 'w', encoding='utf-8') as f:
                json.dump(timings, f, ensure_ascii=False, indent=2)

            # npm install
            subprocess.run(["npm", "install"], cwd=self.remotion_dir, capture_output=True)

            # レンダリング
            total_frames = timings["totalFrames"]
            cmd = [
                "npx", "remotion", "render",
                "SlideVideoV3",
                str(output_path),
                f"--props={json.dumps({'timingsFile': 'timings.json'})}",
                f"--frames=0-{total_frames}"
            ]

            result = subprocess.run(cmd, cwd=self.remotion_dir, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Remotion render error: {result.stderr}")
                return False

            return output_path.exists()

        except Exception as e:
            logger.error(f"Render error: {e}")
            return False

# ============================================================================
# Main Workflow
# ============================================================================

class VideoWorkflow:
    """統合動画生成ワークフロー（画像生成対応）"""

    def __init__(self):
        self.section_extractor = SectionExtractor()
        self.slide_image_generator = SlideImageGenerator()
        self.marp_generator = MarpSlideGenerator()
        self.slide_renderer = SlideRenderer()
        self.narration_generator = NarrationGenerator()
        self.audio_generator = GTTSAudioGenerator()
        self.timing_generator = TimingGenerator()
        self.remotion_renderer = RemotionRenderer()

    async def generate(self, blog_content: str, title: str, topic: str) -> Dict:
        """ブログ記事から動画を生成（画像生成付き）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent.parent / "output" / "videos" / f"{timestamp}_{topic}"
        output_dir.mkdir(parents=True, exist_ok=True)

        slides_dir = output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        try:
            # Step 1: セクション抽出
            logger.info("Step 1: Extracting sections...")
            sections = self.section_extractor.extract(blog_content)
            logger.info(f"Extracted {len(sections)} sections")

            # デバッグ: 抽出されたセクションを表示
            for i, sec in enumerate(sections):
                logger.info(f"  Section {i}: {sec['title'][:30]}... ({len(sec['content'])} chars)")

            # Step 2: スライド用画像生成（Gemini 2.5 Flash image）
            logger.info("Step 2: Generating slide images with Gemini 2.5 Flash...")
            slide_images_gen = await self.slide_image_generator.generate_all_images(
                sections, images_dir
            )
            # 生成された画像をslidesディレクトリにコピー
            slide_images_for_marp = []
            for i, img_path in enumerate(slide_images_gen):
                if img_path and img_path.exists():
                    dest_path = slides_dir / img_path.name
                    shutil.copy(img_path, dest_path)
                    slide_images_for_marp.append(dest_path)
                    logger.info(f"  Copied image {i}: {dest_path.name}")
                else:
                    slide_images_for_marp.append(None)
            logger.info(f"Generated {sum(1 for x in slide_images_for_marp if x)} slide images")

            # Step 3: Marpスライド生成（画像付き）
            logger.info("Step 3: Generating Marp slides with images...")
            marp_path = slides_dir / "slides.md"
            self.marp_generator.generate(title, sections, marp_path, slide_images_for_marp)

            # Step 4: PDF → PNG変換
            logger.info("Step 4: Rendering slides to images...")
            pdf_path = slides_dir / "slides.pdf"
            if not self.slide_renderer.render_to_pdf(marp_path, pdf_path):
                return {"status": "error", "error": "PDF rendering failed"}

            slide_images = self.slide_renderer.pdf_to_images(pdf_path, slides_dir)
            if not slide_images:
                return {"status": "error", "error": "PDF to image conversion failed"}
            logger.info(f"Created {len(slide_images)} slide images")

            # Step 5: ナレーションスクリプト生成
            logger.info("Step 5: Generating narration scripts...")
            scripts = await self.narration_generator.generate(title, sections)

            # Step 6: gTTSで音声生成
            logger.info("Step 6: Generating audio with gTTS...")
            audio_files = []
            for i, script in enumerate(scripts):
                audio_path = audio_dir / f"slide_{i:02d}.mp3"
                duration = self.audio_generator.generate(script, audio_path)
                audio_files.append({
                    "index": i,
                    "audio_file": str(audio_path),
                    "duration": duration,
                    "script": script
                })
                logger.info(f"  Slide {i}: {duration:.1f}s")
                time.sleep(1)  # レート制限対策

            # Step 7: タイミング情報生成
            logger.info("Step 7: Generating timing information...")
            timings = self.timing_generator.generate(audio_files)

            # Step 8: ffmpegで動画レンダリング
            logger.info("Step 8: Rendering video with ffmpeg...")
            video_path = output_dir / f"video_{topic}.mp4"

            if not self.remotion_renderer.render(timings, slide_images, video_path):
                # Remotionが失敗した場合はffmpegでシンプルな動画を作成
                logger.warning("Remotion failed, falling back to ffmpeg...")
                video_path = self._fallback_render(slide_images, audio_files, output_dir, topic)

            if video_path and video_path.exists():
                logger.info(f"Video generated: {video_path}")
                return {
                    "status": "success",
                    "video_path": str(video_path),
                    "duration": timings["totalDuration"],
                    "slides_count": len(slide_images),
                    "title": title
                }
            else:
                return {"status": "error", "error": "Video rendering failed"}

        except Exception as e:
            logger.error(f"Workflow error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    def _fallback_render(self, slide_images: List[Path], audio_files: List[Dict],
                        output_dir: Path, topic: str) -> Optional[Path]:
        """ffmpegを使ったシンプルなフォールバックレンダリング"""
        try:
            # ffmpegの存在確認
            ffmpeg_check = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
            if ffmpeg_check.returncode != 0:
                logger.error("ffmpeg not found in PATH")
                return None
            logger.info(f"ffmpeg found: {ffmpeg_check.stdout.strip()}")

            video_path = output_dir / f"video_{topic}.mp4"
            concat_file = output_dir / "concat.txt"

            # 各スライドを動画に変換して結合
            temp_videos = []
            logger.info(f"Creating {len(slide_images)} slide videos...")

            for i, (img, audio_info) in enumerate(zip(slide_images, audio_files)):
                temp_video = output_dir / f"temp_{i:02d}.mp4"
                duration = audio_info["duration"]
                audio_path = audio_info["audio_file"]

                logger.info(f"  Processing slide {i}: {img.name}, audio: {audio_path}, duration: {duration:.1f}s")

                # 画像を1920x1080にリサイズしてエンコード
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-framerate", "30",
                    "-i", str(img),
                    "-i", str(audio_path),
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-ar", "44100",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-t", str(duration),
                    str(temp_video)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"  ffmpeg error for slide {i}: {result.stderr[:500]}")
                    continue

                if temp_video.exists():
                    temp_videos.append(temp_video)
                    logger.info(f"  Created: {temp_video.name}")
                else:
                    logger.error(f"  Temp video not created: {temp_video}")

            if not temp_videos:
                logger.error("No temp videos were created")
                return None

            # concat.txtを作成
            with open(concat_file, 'w') as f:
                for tv in temp_videos:
                    f.write(f"file '{tv.name}'\n")
            logger.info(f"Created concat file with {len(temp_videos)} videos")

            # 結合
            logger.info("Concatenating videos...")
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(video_path)
            ]
            result = subprocess.run(concat_cmd, capture_output=True, text=True, cwd=str(output_dir))

            if result.returncode != 0:
                logger.error(f"Concat error: {result.stderr[:500]}")

            # 一時ファイル削除
            for tv in temp_videos:
                if tv.exists():
                    tv.unlink()
            if concat_file.exists():
                concat_file.unlink()

            if video_path.exists():
                file_size = video_path.stat().st_size / (1024 * 1024)
                logger.info(f"Video created: {video_path} ({file_size:.1f} MB)")
                return video_path
            else:
                logger.error("Final video file not created")
                return None

        except Exception as e:
            logger.error(f"Fallback render error: {e}")
            import traceback
            traceback.print_exc()
            return None

# ============================================================================
# Entry Point
# ============================================================================

async def generate_video(blog_content: str, title: str, topic: str) -> Dict:
    """動画生成のエントリーポイント"""
    workflow = VideoWorkflow()
    return await workflow.generate(blog_content, title, topic)


if __name__ == "__main__":
    # テスト
    test_content = """
# 2026年最新AIツール動向

## AIチャットボットの進化

ChatGPTやGeminiなどのAIチャットボットが急速に進化しています。
特に2026年は「エージェント型AI」の年と言われています。

## マルチモーダルAIの台頭

テキストだけでなく、画像、音声、動画を統合的に処理できるAI。

## 今後の展望

AIツールは今後さらに身近になっていくでしょう。
"""

    result = asyncio.run(generate_video(test_content, "2026年最新AIツール動向", "ai_tools"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
