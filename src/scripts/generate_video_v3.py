#!/usr/bin/env python3
"""
Video Generation V3 - Marp Slides to Video (MoviePy Edition)

WorkFlow:
1. Marp Markdown Slide Generation (Gemini)
2. Slide Image Generation & Insertion (Gemini Image)
3. Marp CLI -> PDF Rendering
4. PDF -> PNG Conversion (pdf2image)
5. Narration Script Generation (Gemini)
6. TTS Audio Generation (Gemini TTS)
7. Video Assembly (MoviePy)
   - Image Background
   - Audio Sync
   - Subtitles (Burn-in)

Usage:
    from generate_video_v3 import VideoGeneratorV3
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
import wave
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

# Third-party imports
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-generativeai not installed")
    sys.exit(1)

try:
    from pdf2image import convert_from_path
except ImportError:
    print("Error: pdf2image not installed")
    sys.exit(1)

MOVIEPY_AVAILABLE = False
try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
    )
    # 警告抑制
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    MOVIEPY_AVAILABLE = True
except ImportError:
    print("Warning: moviepy not installed, video generation will be skipped")
    ImageClip = None
    AudioFileClip = None
    CompositeVideoClip = None
    concatenate_videoclips = None

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    print("Error: Pillow or numpy not installed")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import image generator
sys.path.insert(0, str(Path(__file__).parent))
try:
    from generate_image import BlogImageGenerator
except ImportError:
    logger.warning("generate_image module not found, image generation may fail")

# =============================================================================
# Configuration
# =============================================================================

@dataclass
class VideoConfig:
    """動画設定"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    default_slide_duration: float = 5.0
    min_slide_duration: float = 3.0
    max_slide_duration: float = 30.0
    audio_padding: float = 0.5
    subtitle_font_size: int = 50
    subtitle_bg_color: Tuple[int, int, int, int] = (0, 0, 0, 180)
    subtitle_text_color: Tuple[int, int, int] = (255, 255, 255)
    subtitle_bottom_margin: int = 100

# トピック別カラースキーム
TOPIC_COLORS = {
    "psychology": {"primary": "#00b4d8", "secondary": "#90e0ef", "bg": "#1a1a2e", "bg_secondary": "#16213e", "name": "心理学"},
    "education": {"primary": "#10b981", "secondary": "#6ee7b7", "bg": "#1a1a2e", "bg_secondary": "#0d1f22", "name": "教育"},
    "startup": {"primary": "#f59e0b", "secondary": "#fcd34d", "bg": "#1a1a2e", "bg_secondary": "#1f1a0d", "name": "起業"},
    "investment": {"primary": "#14b8a6", "secondary": "#5eead4", "bg": "#1a1a2e", "bg_secondary": "#0d1f1d", "name": "投資"},
    "ai_tools": {"primary": "#3b82f6", "secondary": "#93c5fd", "bg": "#1a1a2e", "bg_secondary": "#0d1528", "name": "AIツール"},
    "weekly_summary": {"primary": "#0ea5e9", "secondary": "#7dd3fc", "bg": "#1a1a2e", "bg_secondary": "#0d1825", "name": "週間総括"}
}

# =============================================================================
# Helper Classes
# =============================================================================

class MarpSlideGenerator:
    """Marp Markdown生成"""
    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate(self, research_data: str, topic: str, topic_info: Dict, num_slides: int) -> Dict[str, Any]:
        """Markdown生成"""
        colors = TOPIC_COLORS.get(topic, TOPIC_COLORS["ai_tools"])
        topic_name = topic_info.get("name", colors.get("name", topic))
        
        prompt = f"""あなたはMarpプレゼンテーション作成の専門家です。
以下のリサーチデータから、{num_slides}枚のスライドを作成してください。

【リサーチデータ】
{research_data[:5000]}

【トピック】{topic_name}

【出力形式】
以下のMarp形式のみを出力してください。
画像URLはまだ入れないでください（後で自動挿入します）。

```markdown
---
marp: true
theme: default
paginate: true
backgroundColor: {colors['bg']}
color: #ffffff
style: |
  section {{
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  }}
  h1 {{ color: {colors['primary']}; font-size: 64px; }}
  h2 {{ color: {colors['secondary']}; font-size: 48px; }}
  ul {{ font-size: 36px; }}
---

<!-- _class: lead -->

# タイトル

## サブタイトル

---

# スライド2

- ポイント1
- ポイント2

---
(以下続く)
```
"""
        try:
            config = types.GenerateContentConfig(temperature=0.7, max_output_tokens=4096)
            response = await asyncio.to_thread(self.client.models.generate_content, model=self.MODEL, contents=prompt, config=config)
            markdown = response.text.strip()
            if "```markdown" in markdown:
                markdown = markdown.split("```markdown")[1].split("```")[0]
            elif "```" in markdown:
                markdown = markdown.split("```")[1].split("```")[0]
            
            return {"markdown": markdown, "slide_count": markdown.count("---") - 1, "topic": topic, "title": topic_name}
        except Exception as e:
            logger.error(f"Marp generation failed: {e}")
            raise

class SlideImageInjector:
    """スライドごとの画像生成と挿入"""
    def __init__(self):
        self.generator = BlogImageGenerator()

    async def process(self, markdown: str, topic_id: str, output_dir: Path) -> str:
        """Markdownを解析し、各スライドに背景画像を生成・挿入"""
        slides = markdown.split("\n---")
        # Header is slides[0] if starts with ---, otherwise check
        
        # Marp header handling
        if markdown.strip().startswith("---"):
            header = slides[0]
            body_slides = slides[1:]
        else:
            # Maybe no header? Should not happen with prompt
            header = ""
            body_slides = slides
            
        new_slides = [header]
        images_dir = output_dir / "bg_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for i, slide_content in enumerate(body_slides):
            if not slide_content.strip():
                new_slides.append(slide_content)
                continue
                
            # スライド内容からプロンプト用テキスト抽出
            slide_text = re.sub(r'<!--.*?-->', '', slide_content, flags=re.DOTALL)
            slide_text = re.sub(r'[#\-\*\n]', ' ', slide_text).strip()[:300]
            
            # 画像生成
            logger.info(f"Generating image for slide {i+1}...")
            result = await self.generator.generate_hero_image(
                title=f"Slide {i+1}",
                summary=slide_text,
                topic_id=topic_id,
                style="abstract, cinematic, futuristic background, darkness, minimal, high quality, 8k, technological",
                use_smart_prompt=True
            )
            
            if result.get("images"):
                img_data = result["images"][0]
                # data is dict {'file_path': ...}
                src_path = img_data.get("file_path")
                if src_path:
                    # Copy to local work dir
                    dst_name = f"bg_{i+1:02d}.png"
                    dst_path = images_dir / dst_name
                    shutil.copy2(src_path, dst_path)
                    
                    # Add background syntax to slide
                    # ![bg brightness:0.3](image.png)
                    bg_syntax = f"\n![bg opacity:0.2 brightness:0.5]({dst_path.absolute()})\n"
                    
                    # Insert after first line (which might be empty or ID)
                    lines = slide_content.split('\n')
                    # Find insertion point (after directive or at top)
                    inserted = False
                    for idx, line in enumerate(lines):
                        if not line.strip().startswith("<!--"):
                            lines.insert(idx, bg_syntax)
                            inserted = True
                            break
                    if not inserted:
                        lines.append(bg_syntax)
                        
                    slide_content = "\n".join(lines)
            
            new_slides.append(slide_content)
            
        return "\n---".join(new_slides)

class MarpRenderer:
    """Marp -> PDF -> Images"""
    def __init__(self):
        pass
        
    def render(self, markdown_path: Path, output_dir: Path) -> List[Path]:
        """PDF経由で画像に変換"""
        pdf_path = output_dir / "slides.pdf"
        
        # Marp CLI
        cmd = ["npx", "@marp-team/marp-cli", str(markdown_path), "--pdf", "--allow-local-files", "-o", str(pdf_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Try global marp
            try:
                cmd[0] = "marp"
                subprocess.run(cmd[1:], check=True, capture_output=True)
            except:
                logger.error(f"Marp failed: {e.stderr if hasattr(e, 'stderr') else e}")
                raise RuntimeError("Marp rendering failed")
        
        if not pdf_path.exists():
            raise RuntimeError("PDF not created")
            
        # PDF -> Images
        images_dir = output_dir / "final_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Converting PDF to images...")
        images = convert_from_path(str(pdf_path), dpi=150) # 1920x1080 approx at this DPI/aspect
        
        image_paths = []
        for i, img in enumerate(images):
            # Resize to exactly 1920x1080
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            p = images_dir / f"slide_{i+1:02d}.png"
            img.save(p, "PNG")
            image_paths.append(p)
            
        return image_paths

class NarrationGenerator:
    """ナレーション生成"""
    MODEL = "gemini-2.0-flash"
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate(self, markdown: str, count: int) -> List[str]:
        prompt = f"""Marpスライドの内容から、各スライドの読み上げ原稿（ナレーション）を作成してください。
スライド数: {count}
内容:
{markdown}

出力形式: JSON配列 ["slide1 text", "slide2 text", ...]
各ナレーションは読点で区切られた自然な日本語で、1スライドあたり10-15秒程度（50-80文字）にしてください。
"""
        config = types.GenerateContentConfig(response_mime_type="application/json")
        response = await asyncio.to_thread(self.client.models.generate_content, model=self.MODEL, contents=prompt, config=config)
        return json.loads(response.text)

class AudioGenerator:
    """TTS"""
    MODEL = "gemini-2.5-flash-preview-tts"
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        
    async def generate(self, text: str, path: Path) -> float:
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                )
            )
        )
        response = await asyncio.to_thread(self.client.models.generate_content, model=self.MODEL, contents=text, config=config)
        
        pcm = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                pcm = base64.b64decode(part.inline_data.data)
                break
        
        if not pcm:
            raise RuntimeError("No audio data")
            
        # PCM -> WAV (24kHz, 1ch, 16bit)
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)
            
        return len(pcm) / (24000 * 2)

class VideoAssembler:
    """MoviePy Video Assembly"""
    def __init__(self, config: VideoConfig):
        self.config = config
        # Font path check (MacOS/Linux)
        self.font_path = "/System/Library/Fonts/Hiragino Sans GB.ttc"
        if not Path(self.font_path).exists():
             # Fallback for Linux (GitHub Actions)
            self.font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
            
    def create_video(self, slides: List[Dict], output_path: Path):
        clips = []
        for slide in slides:
            img_path = str(slide["image"])
            audio_path = str(slide["audio"])
            duration = slide["duration"] + self.config.audio_padding
            text = slide["text"]
            
            # Base Image Clip
            img_clip = ImageClip(img_path).set_duration(duration)
            
            # Audio
            audio_clip = AudioFileClip(audio_path)
            img_clip = img_clip.set_audio(audio_clip)
            
            # Subtitle (Burn-in with Pillow)
            subtitle_clip = self._create_subtitle_clip(text, duration, (self.config.width, self.config.height))
            
            # Composite
            final_slide = CompositeVideoClip([img_clip, subtitle_clip])
            clips.append(final_slide)
            
        final_video = concatenate_videoclips(clips)
        final_video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium"
        )
        
    def _create_subtitle_clip(self, text: str, duration: float, size: Tuple[int, int]) -> ImageClip:
        """Create a transparent ImageClip with text drawn on it"""
        W, H = size
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Font loading
        try:
            font = ImageFont.truetype(self.font_path, self.config.subtitle_font_size)
        except:
             font = ImageFont.load_default()
        
        # Wrap text
        max_width = W - 100
        lines = []
        # Simple wrapping
        current_line = ""
        for char in text:
            if draw.textlength(current_line + char, font=font) < max_width:
                current_line += char
            else:
                lines.append(current_line)
                current_line = char
        lines.append(current_line)
        
        # Draw background and text
        text_height = len(lines) * (self.config.subtitle_font_size + 10)
        y_start = H - self.config.subtitle_bottom_margin - text_height
        
        # Semi-transparent bg for text area
        draw.rectangle(
            [(50, y_start - 10), (W - 50, H - self.config.subtitle_bottom_margin + 10)],
            fill=self.config.subtitle_bg_color
        )
        
        y = y_start
        for line in lines:
            # Center text
            w = draw.textlength(line, font=font)
            x = (W - w) / 2
            draw.text((x, y), line, font=font, fill=self.config.subtitle_text_color)
            y += self.config.subtitle_font_size + 10
            
        return ImageClip(np.array(img)).set_duration(duration)

# =============================================================================
# Main Class
# =============================================================================

class VideoGeneratorV3:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key missing")
            
        self.marp_gen = MarpSlideGenerator(self.api_key)
        self.injector = SlideImageInjector()
        self.renderer = MarpRenderer()
        self.narrator = NarrationGenerator(self.api_key)
        self.audio_gen = AudioGenerator(self.api_key)
        self.assembler = VideoAssembler(VideoConfig())

    async def generate(self, research_data: str, topic: str, topic_info: Dict, num_slides: int = 6) -> Dict:
        # Check if moviepy is available
        if not MOVIEPY_AVAILABLE:
            logger.warning("moviepy not available, skipping video generation")
            return {
                "status": "skipped",
                "error": "moviepy not installed",
                "video_path": None,
                "duration": 0,
                "slides_count": 0,
                "title": ""
            }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent.parent / "output" / "videos" / f"{timestamp}_{topic}"
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Step 1: Marp Generation")
        marp_res = await self.marp_gen.generate(research_data, topic, topic_info, num_slides)
        raw_md = marp_res["markdown"]
        
        logger.info("Step 2: Image Injection")
        injected_md = await self.injector.process(raw_md, topic, output_dir)
        md_path = output_dir / "slides.md"
        md_path.write_text(injected_md, encoding="utf-8")
        
        logger.info("Step 3 & 4: Rendering to Images")
        image_paths = self.renderer.render(md_path, output_dir)
        
        logger.info("Step 5 & 6: Narration & Audio")
        narrations = await self.narrator.generate(injected_md, len(image_paths))
        
        slides_data = []
        for i, (img, text) in enumerate(zip(image_paths, narrations)):
            wav_path = output_dir / f"audio_{i:02d}.wav"
            duration = await self.audio_gen.generate(text, wav_path)
            slides_data.append({
                "image": img,
                "audio": wav_path,
                "text": text,
                "duration": duration
            })
            
        logger.info("Step 7: Assembly")
        video_path = output_dir / f"video_{topic}.mp4"
        self.assembler.create_video(slides_data, video_path)
        
        return {
            "status": "success",
            "video_path": str(video_path),
            "duration": sum(s["duration"] for s in slides_data),
            "slides_count": len(slides_data),
            "title": marp_res["title"]
        }

if __name__ == "__main__":
    # Test run
    test_research = "AI tools are evolving rapidly. ChatGPT 5 is coming. Agents are the future."
    gen = VideoGeneratorV3()
    asyncio.run(gen.generate(test_research, "ai_tools", {"name": "Test"}, 3))
