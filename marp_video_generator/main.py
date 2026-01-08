#!/usr/bin/env python3
"""
Marp Video Generator - スライドベース動画自動生成ワークフロー

ブログ記事からMarpスライドを生成し、音声付き動画を自動作成します。

Workflow:
1. Content Generation (Gemini) - Marp Markdown + 読み上げスクリプト生成
2. Slide Rendering (Marp CLI) - Markdown → PDF変換
3. Image Conversion (pdf2image) - PDF → PNG画像変換
4. Audio Synthesis (Gemini TTS) - スクリプト → 音声変換
5. Video Assembly (MoviePy) - 画像+音声を同期して動画生成

Usage:
    python main.py --input "ブログ記事テキスト"
    python main.py --file article.txt
    python main.py --url "https://example.com/article"
"""

import os
import sys
import json
import asyncio
import argparse
import base64
import wave
import tempfile
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
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
    print("Run: pip install google-generativeai")
    sys.exit(1)

try:
    from pdf2image import convert_from_path
except ImportError:
    print("Error: pdf2image not installed")
    print("Run: pip install pdf2image")
    sys.exit(1)

try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips, ColorClip
    )
except ImportError:
    print("Error: moviepy not installed")
    print("Run: pip install moviepy")
    sys.exit(1)

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Error: Pillow or numpy not installed")
    print("Run: pip install Pillow numpy")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kwargs: x

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SlideData:
    """スライドデータ"""
    page: int
    markdown: str
    script: str
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    audio_duration: float = 0.0


@dataclass
class VideoConfig:
    """動画設定"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    audio_padding: float = 0.5  # 音声後の余韻（秒）
    marp_theme: str = "gaia"  # Marpテーマ


# =============================================================================
# Step 1: Content Generation (Gemini)
# =============================================================================

class ContentGenerator:
    """Geminiを使用したスライドコンテンツ生成"""

    MODEL = "gemini-2.0-flash"  # 安定版モデル

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set GOOGLE_AI_API_KEY environment variable.")

        self.client = genai.Client(api_key=self.api_key)
        logger.info("ContentGenerator initialized")

    async def generate_slides(
        self,
        blog_content: str,
        num_slides: int = 6,
        theme: str = "gaia"
    ) -> List[SlideData]:
        """
        ブログ記事からMarpスライドとスクリプトを生成

        Args:
            blog_content: ブログ記事テキスト
            num_slides: スライド枚数
            theme: Marpテーマ

        Returns:
            SlideDataのリスト
        """
        logger.info(f"Generating {num_slides} slides with theme '{theme}'...")

        prompt = f"""あなたはプレゼンテーション作成のエキスパートです。
以下のブログ記事を分析し、{num_slides}枚のスライドとナレーションスクリプトをJSON形式で出力してください。

## ブログ記事:
{blog_content[:10000]}

## 出力形式（厳密にこのJSON形式で出力してください）:
```json
{{
  "theme": "{theme}",
  "slides": [
    {{
      "page": 1,
      "markdown": "# タイトル\\n\\nサブタイトル",
      "script": "みなさんこんにちは。今回は〇〇について解説します。"
    }},
    {{
      "page": 2,
      "markdown": "## 目次\\n\\n- ポイント1\\n- ポイント2\\n- ポイント3",
      "script": "本日のアジェンダです。まず〇〇について説明し、次に〇〇を見ていきます。"
    }}
  ]
}}
```

## 重要な指示:
1. page は 1 から {num_slides} までの連番
2. markdown は Marp記法（見出し、箇条書き、強調を活用）
3. script は自然な話し言葉（10〜20秒で読める長さ）
4. スライド1はタイトル・導入
5. スライド{num_slides}はまとめ・CTA
6. 文字ばかりにせず、箇条書きや強調で視認性を高める
7. JSONのみを出力（説明文不要）

## Markdown記法の例:
- 見出し: # 大見出し, ## 中見出し, ### 小見出し
- 箇条書き: - 項目, 1. 番号付き
- 強調: **太字**, *斜体*
- 改行: \\n
"""

        try:
            # JSON出力を指定
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.MODEL,
                contents=prompt,
                config=config
            )

            # JSONパース
            text = response.text.strip()

            # コードブロック除去（念のため）
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)

            # SlideDataに変換
            slides = []
            for slide_data in data.get("slides", []):
                slide = SlideData(
                    page=slide_data["page"],
                    markdown=slide_data["markdown"],
                    script=slide_data["script"]
                )
                slides.append(slide)

            logger.info(f"Generated {len(slides)} slides successfully")
            return slides

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response: {text[:500]}")
            raise
        except Exception as e:
            logger.error(f"Content generation error: {e}")
            raise


# =============================================================================
# Step 2: Slide Rendering (Marp CLI)
# =============================================================================

class SlideRenderer:
    """Marp CLIを使用したスライドレンダリング"""

    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SlideRenderer initialized: {self.work_dir}")

    def _find_marp_command(self) -> List[str]:
        """Marpコマンドを探す"""
        # npx経由
        try:
            result = subprocess.run(
                ["npx", "@marp-team/marp-cli", "--version"],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return ["npx", "@marp-team/marp-cli"]
        except:
            pass

        # グローバルインストール
        try:
            result = subprocess.run(
                ["marp", "--version"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return ["marp"]
        except:
            pass

        raise RuntimeError(
            "Marp CLI not found. Install with: npm install -g @marp-team/marp-cli"
        )

    def create_markdown_file(
        self,
        slides: List[SlideData],
        theme: str = "gaia"
    ) -> Path:
        """
        スライドデータからMarp Markdownファイルを作成

        Args:
            slides: スライドリスト
            theme: Marpテーマ

        Returns:
            作成したMarkdownファイルのパス
        """
        md_path = self.work_dir / "slides.md"

        # Marp frontmatter
        content = f"""---
marp: true
theme: {theme}
paginate: true
style: |
  section {{
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    font-size: 28px;
  }}
  h1 {{
    font-size: 48px;
    color: #333;
  }}
  h2 {{
    font-size: 36px;
    color: #444;
  }}
  ul, ol {{
    font-size: 24px;
  }}
---

"""
        # 各スライドを追加
        for i, slide in enumerate(slides):
            if i > 0:
                content += "\n---\n\n"
            content += slide.markdown + "\n"

        md_path.write_text(content, encoding="utf-8")
        logger.info(f"Markdown file created: {md_path}")

        return md_path

    def render_to_pdf(self, md_path: Path) -> Path:
        """
        MarkdownファイルをPDFに変換

        Args:
            md_path: Markdownファイルパス

        Returns:
            PDFファイルパス
        """
        pdf_path = self.work_dir / "slides.pdf"

        marp_cmd = self._find_marp_command()

        cmd = marp_cmd + [
            str(md_path),
            "--pdf",
            "--allow-local-files",
            "-o", str(pdf_path)
        ]

        logger.info(f"Running Marp: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.work_dir)
            )

            if result.returncode != 0:
                logger.error(f"Marp stderr: {result.stderr}")
                raise RuntimeError(f"Marp failed: {result.stderr}")

            if not pdf_path.exists():
                raise RuntimeError("PDF file was not created")

            logger.info(f"PDF created: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
            return pdf_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("Marp timed out")


# =============================================================================
# Step 3: Image Conversion (pdf2image)
# =============================================================================

class ImageConverter:
    """PDFから画像への変換"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ImageConverter initialized: {self.output_dir}")

    def convert_pdf_to_images(
        self,
        pdf_path: Path,
        dpi: int = 300
    ) -> List[Path]:
        """
        PDFを高解像度の画像に変換

        Args:
            pdf_path: PDFファイルパス
            dpi: 解像度

        Returns:
            画像ファイルパスのリスト
        """
        logger.info(f"Converting PDF to images (DPI: {dpi})...")

        try:
            # Windowsの場合、poppler_pathを設定する必要がある場合あり
            poppler_path = os.getenv("POPPLER_PATH")

            if poppler_path:
                images = convert_from_path(
                    str(pdf_path),
                    dpi=dpi,
                    poppler_path=poppler_path
                )
            else:
                images = convert_from_path(str(pdf_path), dpi=dpi)

        except Exception as e:
            logger.error(f"PDF conversion error: {e}")
            raise RuntimeError(
                f"PDF to image conversion failed: {e}\n"
                "Make sure poppler-utils is installed."
            )

        image_paths = []
        for i, image in enumerate(images, 1):
            # 16:9にリサイズ
            target_size = (1920, 1080)
            image = self._resize_to_fit(image, target_size)

            image_path = self.output_dir / f"slide_{i:02d}.png"
            image.save(str(image_path), "PNG", quality=95)
            image_paths.append(image_path)

            logger.info(f"Saved: {image_path}")

        logger.info(f"Converted {len(image_paths)} pages to images")
        return image_paths

    def _resize_to_fit(
        self,
        image: Image.Image,
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """
        アスペクト比を維持しながらリサイズし、余白を追加

        Args:
            image: 元画像
            target_size: (width, height)

        Returns:
            リサイズされた画像
        """
        target_w, target_h = target_size
        orig_w, orig_h = image.size

        # アスペクト比を計算
        target_ratio = target_w / target_h
        orig_ratio = orig_w / orig_h

        if orig_ratio > target_ratio:
            # 横長なので幅に合わせる
            new_w = target_w
            new_h = int(target_w / orig_ratio)
        else:
            # 縦長なので高さに合わせる
            new_h = target_h
            new_w = int(target_h * orig_ratio)

        # リサイズ
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 中央に配置して余白を追加
        result = Image.new("RGB", target_size, (255, 255, 255))
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        result.paste(image, (paste_x, paste_y))

        return result


# =============================================================================
# Step 4: Audio Synthesis (Gemini TTS)
# =============================================================================

class AudioSynthesizer:
    """Gemini TTSを使用した音声合成"""

    MODEL = "gemini-2.5-flash-preview-tts"

    VOICES = {
        "default": "Kore",
        "bright": "Puck",
        "calm": "Charon",
        "warm": "Aoede",
    }

    def __init__(self, output_dir: Path, api_key: Optional[str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("API key required")

        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"AudioSynthesizer initialized: {self.output_dir}")

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "default"
    ) -> float:
        """
        テキストを音声に変換

        Args:
            text: 読み上げテキスト
            output_path: 出力WAVファイルパス
            voice: 音声タイプ

        Returns:
            音声の長さ（秒）
        """
        voice_name = self.VOICES.get(voice, self.VOICES["default"])
        logger.info(f"Synthesizing: {text[:30]}...")

        try:
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
                model=self.MODEL,
                contents=text,
                config=config
            )

            # PCMデータ抽出
            pcm_data = None
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        data = part.inline_data.data
                        pcm_data = base64.b64decode(data) if isinstance(data, str) else data
                        break

            if not pcm_data:
                raise ValueError("No audio data in response")

            # WAV変換・保存
            wav_data = self._pcm_to_wav(pcm_data)
            with open(output_path, 'wb') as f:
                f.write(wav_data)

            # 音声長計算（24kHz, 16bit mono）
            duration = len(pcm_data) / (24000 * 2)

            logger.info(f"Audio saved: {output_path} ({duration:.2f}s)")
            return duration

        except Exception as e:
            logger.error(f"Audio synthesis error: {e}")
            raise

    def _pcm_to_wav(
        self,
        pcm_data: bytes,
        sample_rate: int = 24000,
        channels: int = 1,
        sample_width: int = 2
    ) -> bytes:
        """PCMをWAVに変換"""
        import io
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_data)
        return buffer.getvalue()

    async def synthesize_all(
        self,
        slides: List[SlideData],
        voice: str = "default"
    ) -> List[SlideData]:
        """
        全スライドのスクリプトを音声化

        Args:
            slides: スライドリスト
            voice: 音声タイプ

        Returns:
            音声パスと長さが設定されたスライドリスト
        """
        logger.info(f"Synthesizing {len(slides)} audio files...")

        for slide in tqdm(slides, desc="Audio synthesis"):
            audio_path = self.output_dir / f"voice_{slide.page:02d}.wav"

            duration = await self.synthesize(
                slide.script,
                audio_path,
                voice
            )

            slide.audio_path = str(audio_path)
            slide.audio_duration = duration

        return slides


# =============================================================================
# Step 5: Video Assembly (MoviePy)
# =============================================================================

class VideoAssembler:
    """MoviePyを使用した動画生成"""

    def __init__(self, config: VideoConfig = None):
        self.config = config or VideoConfig()
        logger.info("VideoAssembler initialized")

    def create_video(
        self,
        slides: List[SlideData],
        output_path: Path
    ) -> Path:
        """
        スライドと音声から動画を生成

        Args:
            slides: スライドリスト（画像パス、音声パス、音声長を含む）
            output_path: 出力動画パス

        Returns:
            出力動画パス
        """
        logger.info(f"Assembling video from {len(slides)} slides...")

        clips = []

        for slide in tqdm(slides, desc="Creating clips"):
            # 表示時間 = 音声長 + パディング
            duration = slide.audio_duration + self.config.audio_padding

            # 最低3秒
            duration = max(duration, 3.0)

            # 画像クリップ
            img_clip = ImageClip(slide.image_path).set_duration(duration)
            img_clip = img_clip.resize((self.config.width, self.config.height))

            # 音声クリップ
            if slide.audio_path and Path(slide.audio_path).exists():
                audio_clip = AudioFileClip(slide.audio_path)
                img_clip = img_clip.set_audio(audio_clip)

            clips.append(img_clip)

            logger.debug(f"Slide {slide.page}: {duration:.2f}s")

        # 全クリップを結合
        logger.info("Concatenating clips...")
        final = concatenate_videoclips(clips, method="compose")

        # 動画出力
        logger.info(f"Rendering video to {output_path}...")
        final.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec='libx264',
            audio_codec='aac',
            bitrate='8000k',
            preset='medium',
            threads=4,
            logger=None
        )

        # クリーンアップ
        final.close()
        for clip in clips:
            clip.close()

        total_duration = sum(s.audio_duration + self.config.audio_padding for s in slides)
        logger.info(f"Video created: {output_path} ({total_duration:.1f}s)")

        return output_path


# =============================================================================
# Main Workflow Orchestrator
# =============================================================================

class MarpVideoWorkflow:
    """Marp動画生成ワークフロー全体を管理"""

    def __init__(self, output_dir: str = "output"):
        self.base_dir = Path(output_dir)
        self.work_dir = self.base_dir / "work"
        self.images_dir = self.base_dir / "images"
        self.audio_dir = self.base_dir / "audio"
        self.video_dir = self.base_dir / "videos"

        # ディレクトリ作成
        for d in [self.work_dir, self.images_dir, self.audio_dir, self.video_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # コンポーネント初期化
        self.content_gen = ContentGenerator()
        self.slide_renderer = SlideRenderer(self.work_dir)
        self.image_converter = ImageConverter(self.images_dir)
        self.audio_synth = AudioSynthesizer(self.audio_dir)
        self.video_assembler = VideoAssembler()

        logger.info(f"MarpVideoWorkflow initialized: {self.base_dir}")

    async def generate(
        self,
        blog_content: str,
        output_name: str = None,
        num_slides: int = 6,
        theme: str = "gaia",
        voice: str = "default"
    ) -> str:
        """
        ブログ記事から動画を生成

        Args:
            blog_content: ブログ記事テキスト
            output_name: 出力ファイル名
            num_slides: スライド枚数
            theme: Marpテーマ
            voice: 音声タイプ

        Returns:
            生成された動画のパス
        """
        if output_name is None:
            output_name = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info("=" * 60)
        logger.info("Marp Video Generation Workflow")
        logger.info("=" * 60)

        try:
            # Step 1: コンテンツ生成
            logger.info("\n[Step 1/5] Generating slide content (Gemini)...")
            slides = await self.content_gen.generate_slides(
                blog_content,
                num_slides,
                theme
            )

            # Step 2: スライドレンダリング
            logger.info("\n[Step 2/5] Rendering slides (Marp CLI)...")
            md_path = self.slide_renderer.create_markdown_file(slides, theme)
            pdf_path = self.slide_renderer.render_to_pdf(md_path)

            # Step 3: 画像変換
            logger.info("\n[Step 3/5] Converting PDF to images...")
            image_paths = self.image_converter.convert_pdf_to_images(pdf_path)

            # スライドに画像パスを設定
            for slide, img_path in zip(slides, image_paths):
                slide.image_path = str(img_path)

            # Step 4: 音声合成
            logger.info("\n[Step 4/5] Synthesizing audio (Gemini TTS)...")
            slides = await self.audio_synth.synthesize_all(slides, voice)

            # Step 5: 動画生成
            logger.info("\n[Step 5/5] Assembling video (MoviePy)...")
            output_path = self.video_dir / f"{output_name}.mp4"
            self.video_assembler.create_video(slides, output_path)

            # サマリー
            total_duration = sum(s.audio_duration for s in slides)
            logger.info("\n" + "=" * 60)
            logger.info("Workflow Complete!")
            logger.info("=" * 60)
            logger.info(f"Output: {output_path}")
            logger.info(f"Slides: {len(slides)}")
            logger.info(f"Duration: ~{total_duration:.1f}s")

            return str(output_path)

        except Exception as e:
            logger.error(f"\n[ERROR] Workflow failed at: {e}")
            raise

    async def generate_from_file(self, file_path: str, **kwargs) -> str:
        """ファイルから生成"""
        logger.info(f"Reading: {file_path}")
        content = Path(file_path).read_text(encoding="utf-8")
        return await self.generate(content, **kwargs)

    async def generate_from_url(self, url: str, **kwargs) -> str:
        """URLから生成"""
        import requests
        from html.parser import HTMLParser

        logger.info(f"Fetching: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # 簡易HTMLパーサー
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip = {'script', 'style', 'nav', 'header', 'footer'}
                self.tag = None

            def handle_starttag(self, tag, attrs):
                self.tag = tag

            def handle_data(self, data):
                if self.tag not in self.skip:
                    text = data.strip()
                    if text:
                        self.text.append(text)

        extractor = TextExtractor()
        extractor.feed(response.text)
        content = ' '.join(extractor.text)

        return await self.generate(content, **kwargs)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Marp Video Generator - Create slide-based videos from blog articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input "ブログ記事テキスト..."
  python main.py --file article.txt --slides 8
  python main.py --url "https://example.com/article" --theme default

Themes: gaia, default, uncover
Voices: default, bright, calm, warm
        """
    )

    # 入力ソース
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input', '-i', help='ブログテキスト（直接入力）')
    input_group.add_argument('--file', '-f', help='テキストファイルパス')
    input_group.add_argument('--url', '-u', help='ブログ記事URL')

    # オプション
    parser.add_argument('--output', '-o', default=None, help='出力ファイル名')
    parser.add_argument('--slides', '-s', type=int, default=6, help='スライド枚数（デフォルト: 6）')
    parser.add_argument('--theme', '-t', default='gaia', help='Marpテーマ（デフォルト: gaia）')
    parser.add_argument('--voice', '-v', default='default', help='音声タイプ（デフォルト: default）')
    parser.add_argument('--output-dir', default='output', help='出力ディレクトリ')

    args = parser.parse_args()

    async def run():
        workflow = MarpVideoWorkflow(args.output_dir)

        kwargs = {
            "output_name": args.output,
            "num_slides": args.slides,
            "theme": args.theme,
            "voice": args.voice
        }

        if args.input:
            return await workflow.generate(args.input, **kwargs)
        elif args.file:
            return await workflow.generate_from_file(args.file, **kwargs)
        elif args.url:
            return await workflow.generate_from_url(args.url, **kwargs)

    try:
        result = asyncio.run(run())
        print(f"\nSuccess! Video: {result}")
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
