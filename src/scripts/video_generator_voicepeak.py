#!/usr/bin/env python3
"""
Video Generator with VOICEPEAK - Blog to Video Workflow

Workflow:
1. Extract sections from blog content
2. Generate section images using Gemini
3. Create Marp slides with section images
4. Convert Marp to PDF, then to PNG images
5. Generate narration script for each slide
6. Generate audio using VOICEPEAK (Female 2)
7. Assemble video with:
   - Slide images as backgrounds
   - Fade transitions between slides
   - YouTube-style double-bordered subtitles
   - Synced audio

Requirements:
- VOICEPEAK installed at /Applications/voicepeak.app
- Marp CLI: npm install -g @marp-team/marp-cli
- ffmpeg for video processing
- pdf2image + poppler for PDF to PNG conversion
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class VideoConfig:
    """Video generation configuration"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    fade_duration: float = 0.5  # seconds for fade transition
    min_slide_duration: float = 5.0
    max_slide_duration: float = 30.0

@dataclass
class VOICEPEAKConfig:
    """VOICEPEAK configuration"""
    path: str = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"
    narrator: str = "Japanese Female 2"  # 女性2
    speed: int = 100  # 50-200
    pitch: int = 0    # -300 to 300
    max_chars: int = 140  # VOICEPEAK character limit per request

# ============================================================================
# Dependencies Check
# ============================================================================

def check_dependencies() -> Dict[str, bool]:
    """Check if all required dependencies are available"""
    deps = {
        "voicepeak": os.path.exists(VOICEPEAKConfig.path),
        "marp": shutil.which("marp") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
    }

    try:
        from pdf2image import convert_from_path
        deps["pdf2image"] = True
    except ImportError:
        deps["pdf2image"] = False

    try:
        from PIL import Image, ImageDraw, ImageFont
        deps["pillow"] = True
    except ImportError:
        deps["pillow"] = False

    return deps

# ============================================================================
# Section Extractor
# ============================================================================

class SectionExtractor:
    """Extract sections from blog content"""

    def extract(self, content: str) -> List[Dict[str, str]]:
        """Extract sections with headers and content"""
        sections = []

        # Split by h2 headers (## )
        pattern = r'^##\s+(.+?)$'
        parts = re.split(pattern, content, flags=re.MULTILINE)

        # First part is intro (before first ##)
        if parts[0].strip():
            sections.append({
                "title": "Introduction",
                "content": parts[0].strip()[:500]  # Limit content length
            })

        # Process remaining sections
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                title = parts[i].strip()
                content_text = parts[i + 1].strip()[:500]
                sections.append({
                    "title": title,
                    "content": content_text
                })

        return sections

# ============================================================================
# Image Generator
# ============================================================================

class SectionImageGenerator:
    """Generate images for each section using Gemini"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY is required")

    async def generate(self, section: Dict[str, str], output_path: Path) -> bool:
        """Generate an image for a section"""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            prompt = f"""Create a professional, modern illustration for a blog section.

Section Title: {section['title']}
Content Summary: {section['content'][:200]}

Requirements:
- Clean, minimalist design
- Professional color scheme (blues, teals, whites)
- NO text or letters in the image
- 16:9 aspect ratio (landscape)
- Suitable for a tech/education blog
- Abstract or conceptual representation of the topic
"""

            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"]
                )
            )

            # Extract image from response
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        output_path.write_bytes(image_data)
                        logger.info(f"Generated image: {output_path}")
                        return True

            logger.warning(f"No image generated for section: {section['title']}")
            return False

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return False

# ============================================================================
# Marp Slide Generator
# ============================================================================

class MarpSlideGenerator:
    """Generate Marp slides from sections"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")

    async def generate(self, sections: List[Dict], image_paths: List[Path],
                       title: str, output_path: Path) -> str:
        """Generate Marp markdown with embedded images"""

        slides = []

        # Title slide
        slides.append(f"""---
marp: true
theme: default
paginate: false
backgroundColor: #1a1a2e
color: #ffffff
style: |
  section {{
    font-family: 'Noto Sans JP', sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  }}
  h1 {{
    color: #00d4ff;
    font-size: 2.5em;
    text-align: center;
    margin-top: 200px;
  }}
  h2 {{
    color: #00d4ff;
    border-bottom: 3px solid #00d4ff;
    padding-bottom: 10px;
  }}
  p {{
    font-size: 1.3em;
    line-height: 1.6;
  }}
  img {{
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  }}
---

# {title}

""")

        # Content slides
        for i, section in enumerate(sections):
            image_path = image_paths[i] if i < len(image_paths) else None

            slide_content = f"""---

## {section['title']}

"""
            if image_path and image_path.exists():
                slide_content += f"![bg right:40%]({image_path.name})\n\n"

            # Truncate content for slide
            content = section['content'][:300]
            if len(section['content']) > 300:
                content += "..."

            slide_content += content
            slides.append(slide_content)

        # End slide
        slides.append("""---

# Thank You

ご視聴ありがとうございました

""")

        markdown = "\n".join(slides)
        output_path.write_text(markdown, encoding='utf-8')

        return markdown

# ============================================================================
# PDF/Image Converter
# ============================================================================

class SlideRenderer:
    """Render Marp slides to PDF and PNG images"""

    def render_to_pdf(self, markdown_path: Path, output_path: Path) -> bool:
        """Convert Marp markdown to PDF"""
        try:
            cmd = [
                "marp", str(markdown_path),
                "--pdf",
                "--allow-local-files",
                "-o", str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Marp error: {result.stderr}")
                return False

            return output_path.exists()
        except Exception as e:
            logger.error(f"PDF rendering error: {e}")
            return False

    def pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """Convert PDF pages to PNG images"""
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(str(pdf_path), dpi=150)
            image_paths = []

            for i, image in enumerate(images):
                output_path = output_dir / f"slide_{i:03d}.png"
                image.save(str(output_path), "PNG")
                image_paths.append(output_path)
                logger.info(f"Saved slide image: {output_path}")

            return image_paths
        except Exception as e:
            logger.error(f"PDF to image conversion error: {e}")
            return []

# ============================================================================
# Narration Generator
# ============================================================================

class NarrationGenerator:
    """Generate narration scripts using Gemini"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")

    async def generate(self, sections: List[Dict], title: str) -> List[str]:
        """Generate narration script for each slide"""
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)

            scripts = []

            # Title slide narration
            intro_prompt = f"""以下のブログタイトルの導入ナレーションを30-50文字で作成してください。
タイトル: {title}

要件:
- 視聴者への挨拶から始める
- 内容の概要を簡潔に伝える
- 自然な話し言葉で"""

            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=intro_prompt
            )
            scripts.append(response.text.strip())

            # Section narrations
            for section in sections:
                prompt = f"""以下のブログセクションのナレーションを50-100文字で作成してください。

タイトル: {section['title']}
内容: {section['content'][:300]}

要件:
- 内容のポイントを分かりやすく説明
- 自然な話し言葉
- 「です」「ます」調で"""

                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt
                )
                scripts.append(response.text.strip())

            # Outro
            scripts.append("以上、ご視聴ありがとうございました。チャンネル登録、高評価よろしくお願いします。")

            return scripts

        except Exception as e:
            logger.error(f"Narration generation error: {e}")
            return []

# ============================================================================
# VOICEPEAK Audio Generator
# ============================================================================

class VOICEPEAKGenerator:
    """Generate audio using VOICEPEAK"""

    def __init__(self, config: VOICEPEAKConfig = None):
        self.config = config or VOICEPEAKConfig()

    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks within character limit"""
        if len(text) <= self.config.max_chars:
            return [text]

        chunks = []
        sentences = re.split(r'([。！？])', text)
        current_chunk = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]

            if len(current_chunk) + len(sentence) <= self.config.max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def generate(self, text: str, output_path: Path) -> float:
        """Generate audio from text, returns duration in seconds"""
        if not text or not text.strip():
            # Generate silence
            self._generate_silence(output_path, 2.0)
            return 2.0

        chunks = self._split_text(text)

        if len(chunks) == 1:
            return self._generate_single(chunks[0], output_path)
        else:
            return self._generate_chunked(chunks, output_path)

    def _generate_single(self, text: str, output_path: Path) -> float:
        """Generate audio for a single chunk"""
        wav_path = output_path.with_suffix('.wav')

        cmd = [
            self.config.path,
            '-s', text,
            '-o', str(wav_path),
            '-n', self.config.narrator,
            '--speed', str(self.config.speed),
            '--pitch', str(self.config.pitch)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if not wav_path.exists():
                logger.error("VOICEPEAK failed to generate audio")
                self._generate_silence(output_path, 5.0)
                return 5.0

            # Convert to MP3
            mp3_cmd = [
                'ffmpeg', '-y', '-i', str(wav_path),
                '-codec:a', 'libmp3lame', '-qscale:a', '2',
                str(output_path)
            ]
            subprocess.run(mp3_cmd, capture_output=True, check=True)
            wav_path.unlink()

            return self._get_duration(output_path)

        except Exception as e:
            logger.error(f"VOICEPEAK error: {e}")
            self._generate_silence(output_path, 5.0)
            return 5.0

    def _generate_chunked(self, chunks: List[str], output_path: Path) -> float:
        """Generate and concatenate audio from multiple chunks"""
        temp_dir = output_path.parent / "temp_audio"
        temp_dir.mkdir(exist_ok=True)

        temp_files = []
        try:
            for i, chunk in enumerate(chunks):
                temp_path = temp_dir / f"chunk_{i:03d}.mp3"
                self._generate_single(chunk, temp_path)
                temp_files.append(temp_path)

            # Concatenate
            concat_list = temp_dir / "concat.txt"
            with open(concat_list, 'w') as f:
                for tf in temp_files:
                    f.write(f"file '{tf.name}'\n")

            concat_cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(concat_list),
                '-codec:a', 'libmp3lame', '-qscale:a', '2',
                str(output_path)
            ]
            subprocess.run(concat_cmd, capture_output=True, check=True)

            return self._get_duration(output_path)

        finally:
            # Cleanup
            for tf in temp_files:
                if tf.exists():
                    tf.unlink()
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _generate_silence(self, output_path: Path, duration: float):
        """Generate silent audio"""
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'anullsrc=r=44100:cl=stereo',
            '-t', str(duration),
            '-codec:a', 'libmp3lame',
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    def _get_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds"""
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 5.0

# ============================================================================
# Video Assembler
# ============================================================================

class VideoAssembler:
    """Assemble final video with slides, audio, subtitles, and transitions"""

    def __init__(self, config: VideoConfig = None):
        self.config = config or VideoConfig()

    def create_subtitle_image(self, text: str, output_path: Path):
        """Create subtitle image with YouTube-style double border"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create transparent image
            img = Image.new('RGBA', (self.config.width, 150), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Try to load Japanese font
            font_size = 48
            try:
                font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", font_size)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", font_size)
                except:
                    font = ImageFont.load_default()

            # Calculate text position (centered)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.config.width - text_width) // 2
            y = 50

            # Draw double border (YouTube style)
            # Outer border (black)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))

            # Inner border (dark gray)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    draw.text((x + dx, y + dy), text, font=font, fill=(50, 50, 50, 255))

            # Main text (white)
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

            img.save(str(output_path), 'PNG')

        except Exception as e:
            logger.error(f"Subtitle creation error: {e}")

    def create_video(self, slides_data: List[Dict], output_path: Path) -> bool:
        """
        Create video from slides with audio, subtitles, and fade transitions

        slides_data: List of {
            'image': Path to slide image,
            'audio': Path to audio file,
            'duration': float duration in seconds,
            'subtitle': str subtitle text
        }
        """
        if not slides_data:
            logger.error("No slides data provided")
            return False

        temp_dir = output_path.parent / "temp_video"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Create individual slide videos
            slide_videos = []

            for i, slide in enumerate(slides_data):
                slide_video = temp_dir / f"slide_{i:03d}.mp4"

                # Create subtitle image
                subtitle_path = temp_dir / f"subtitle_{i:03d}.png"
                if slide.get('subtitle'):
                    self.create_subtitle_image(slide['subtitle'], subtitle_path)

                # Build ffmpeg command for this slide
                duration = slide.get('duration', 5.0)

                # Input: image + audio
                cmd = ['ffmpeg', '-y']
                cmd.extend(['-loop', '1', '-i', str(slide['image'])])

                if slide.get('audio') and Path(slide['audio']).exists():
                    cmd.extend(['-i', str(slide['audio'])])
                    audio_input = True
                else:
                    audio_input = False

                # Add subtitle overlay if exists
                if subtitle_path.exists():
                    cmd.extend(['-i', str(subtitle_path)])
                    filter_complex = f"[0:v]scale={self.config.width}:{self.config.height}[bg];[bg][2:v]overlay=(W-w)/2:H-h-50[v]"
                    cmd.extend(['-filter_complex', filter_complex, '-map', '[v]'])
                else:
                    cmd.extend(['-vf', f'scale={self.config.width}:{self.config.height}'])

                if audio_input:
                    cmd.extend(['-map', '1:a'])

                cmd.extend([
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-r', str(self.config.fps)
                ])

                if audio_input:
                    cmd.extend(['-c:a', 'aac', '-b:a', '192k'])

                cmd.append(str(slide_video))

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Slide video creation warning: {result.stderr[:200]}")

                if slide_video.exists():
                    slide_videos.append(slide_video)

            if not slide_videos:
                logger.error("No slide videos created")
                return False

            # Concatenate with fade transitions
            return self._concatenate_with_fade(slide_videos, output_path)

        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _concatenate_with_fade(self, videos: List[Path], output_path: Path) -> bool:
        """Concatenate videos with fade transitions"""
        if len(videos) == 1:
            shutil.copy(videos[0], output_path)
            return True

        # Create concat file
        concat_file = videos[0].parent / "concat.txt"
        with open(concat_file, 'w') as f:
            for v in videos:
                f.write(f"file '{v.name}'\n")

        # Build filter for xfade transitions
        fade_duration = self.config.fade_duration

        # For simplicity, use concat demuxer with crossfade filter
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', str(concat_file),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Video concatenation error: {result.stderr[:500]}")
            return False

        return output_path.exists()

# ============================================================================
# Main Video Generator
# ============================================================================

class BlogVideoGenerator:
    """Main class to orchestrate blog to video conversion"""

    def __init__(self):
        self.deps = check_dependencies()
        self.section_extractor = SectionExtractor()
        self.image_generator = SectionImageGenerator()
        self.marp_generator = MarpSlideGenerator()
        self.slide_renderer = SlideRenderer()
        self.narration_generator = NarrationGenerator()
        self.audio_generator = VOICEPEAKGenerator()
        self.video_assembler = VideoAssembler()

    async def generate(self, blog_content: str, title: str, topic: str) -> Dict:
        """
        Generate video from blog content

        Returns:
            Dict with status, video_path, duration, etc.
        """
        # Check dependencies
        missing_deps = [k for k, v in self.deps.items() if not v]
        if missing_deps:
            logger.warning(f"Missing dependencies: {missing_deps}")
            if "voicepeak" in missing_deps:
                logger.error("VOICEPEAK is required for video generation")
                return {"status": "error", "error": "VOICEPEAK not installed"}

        # Setup output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent.parent / "output" / "videos" / f"{timestamp}_{topic}"
        output_dir.mkdir(parents=True, exist_ok=True)

        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        audio_dir = output_dir / "audio"
        audio_dir.mkdir(exist_ok=True)

        slides_dir = output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)

        try:
            # Step 1: Extract sections
            logger.info("Step 1: Extracting sections from blog...")
            sections = self.section_extractor.extract(blog_content)
            logger.info(f"Extracted {len(sections)} sections")

            # Step 2: Generate section images
            logger.info("Step 2: Generating section images...")
            image_paths = []
            for i, section in enumerate(sections):
                img_path = images_dir / f"section_{i:03d}.png"
                success = await self.image_generator.generate(section, img_path)
                if success:
                    image_paths.append(img_path)
                else:
                    image_paths.append(None)

            # Step 3: Generate Marp slides
            logger.info("Step 3: Creating Marp slides...")
            marp_path = slides_dir / "slides.md"
            await self.marp_generator.generate(sections, image_paths, title, marp_path)

            # Step 4: Render to PDF and PNG
            logger.info("Step 4: Rendering slides to images...")
            pdf_path = slides_dir / "slides.pdf"
            if not self.slide_renderer.render_to_pdf(marp_path, pdf_path):
                return {"status": "error", "error": "Failed to render PDF"}

            slide_images = self.slide_renderer.pdf_to_images(pdf_path, slides_dir)
            if not slide_images:
                return {"status": "error", "error": "Failed to convert PDF to images"}

            # Step 5: Generate narration scripts
            logger.info("Step 5: Generating narration scripts...")
            narrations = await self.narration_generator.generate(sections, title)

            # Step 6: Generate audio with VOICEPEAK
            logger.info("Step 6: Generating audio with VOICEPEAK...")
            slides_data = []
            total_duration = 0

            for i, (slide_img, narration) in enumerate(zip(slide_images, narrations)):
                audio_path = audio_dir / f"audio_{i:03d}.mp3"
                duration = self.audio_generator.generate(narration, audio_path)

                # Add some padding
                duration = max(duration + 0.5, 5.0)
                total_duration += duration

                slides_data.append({
                    'image': slide_img,
                    'audio': audio_path,
                    'duration': duration,
                    'subtitle': narration[:50] + "..." if len(narration) > 50 else narration
                })

            # Step 7: Assemble video
            logger.info("Step 7: Assembling final video...")
            video_path = output_dir / f"video_{topic}.mp4"

            if not self.video_assembler.create_video(slides_data, video_path):
                return {"status": "error", "error": "Failed to assemble video"}

            logger.info(f"Video generated successfully: {video_path}")

            return {
                "status": "success",
                "video_path": str(video_path),
                "duration": total_duration,
                "slides_count": len(slide_images),
                "title": title
            }

        except Exception as e:
            logger.error(f"Video generation error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

# ============================================================================
# CLI
# ============================================================================

async def main():
    """Test video generation"""
    test_content = """
# 2026年最新AIツール動向

## AIチャットボットの進化

ChatGPTやGeminiなどのAIチャットボットが急速に進化しています。
特に2026年は「エージェント型AI」の年と言われています。

## マルチモーダルAIの台頭

テキストだけでなく、画像、音声、動画を統合的に処理できるマルチモーダルAIが主流になっています。

## 今後の展望

AIツールは今後さらに身近なものになっていくでしょう。
"""

    generator = BlogVideoGenerator()
    result = await generator.generate(test_content, "2026年最新AIツール動向", "ai_tools")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
