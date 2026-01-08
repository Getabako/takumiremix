#!/usr/bin/env python3
"""
Gemini Video Generator - High Quality Explanation Video Creator
================================================================

ブログ記事から高品質な解説動画を自動生成するワークフロー

Features:
- Gemini 3.0 Pro Preview: シーン構成・脚本生成
- Gemini 2.5 Flash image: 高品質画像生成
- Gemini TTS: 自然な音声生成
- Ken Burns Effect: 動的な映像演出
- 完璧な音声同期

Usage:
    python main.py --input "ブログ記事テキスト"
    python main.py --url "https://example.com/blog-article"
    python main.py --file article.txt
"""

import os
import sys
import json
import asyncio
import argparse
import base64
import struct
import wave
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Third-party imports
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips, TextClip, ColorClip
    )
    from moviepy.video.fx.all import resize, crop
except ImportError:
    print("Error: moviepy not installed. Run: pip install moviepy")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    print("Error: Pillow or numpy not installed. Run: pip install Pillow numpy")
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
class Scene:
    """シーンデータ"""
    scene_id: int
    narration_script: str
    image_prompt: str
    overlay_text: str
    audio_path: Optional[str] = None
    audio_duration: float = 0.0
    image_path: Optional[str] = None


@dataclass
class VideoConfig:
    """動画設定"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    audio_sample_rate: int = 24000
    ken_burns_zoom: float = 1.1  # 1.0 -> 1.1 zoom
    scene_padding: float = 0.5  # 余韻（秒）
    font_size: int = 48
    font_color: str = "white"
    text_bg_color: Tuple[int, int, int, int] = (0, 0, 0, 180)


# =============================================================================
# Gemini Client
# =============================================================================

class GeminiVideoClient:
    """Gemini API クライアント（動画生成専用）"""

    # Model IDs
    MODEL_SCRIPT = "gemini-2.5-pro-preview-06-05"  # 脚本生成
    MODEL_IMAGE = "gemini-2.5-flash-preview-05-20"  # 画像生成
    MODEL_TTS = "gemini-2.5-flash-preview-tts"  # 音声生成

    # TTS Voice options
    TTS_VOICES = {
        "default": "Kore",
        "bright": "Puck",
        "calm": "Charon",
        "warm": "Aoede",
        "energetic": "Fenrir",
        "friendly": "Leda"
    }

    def __init__(self, api_key: Optional[str] = None):
        """初期化"""
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set GOOGLE_API_KEY or GOOGLE_AI_API_KEY environment variable."
            )

        self.client = genai.Client(api_key=self.api_key)
        logger.info("GeminiVideoClient initialized")

    async def generate_script(self, blog_content: str, num_scenes: int = 6) -> List[Scene]:
        """
        ブログ記事からシーンリストを生成

        Args:
            blog_content: ブログ記事のテキスト
            num_scenes: 生成するシーン数

        Returns:
            Scene オブジェクトのリスト
        """
        logger.info(f"Generating script with {num_scenes} scenes...")

        prompt = f"""あなたは解説動画の脚本家です。
以下のブログ記事を分析し、{num_scenes}シーンの解説動画用脚本をJSON形式で出力してください。

## ブログ記事:
{blog_content[:8000]}

## 出力形式 (厳密にこのJSON形式で出力):
```json
[
  {{
    "scene_id": 1,
    "narration_script": "（10〜20秒で読める自然な話し言葉のナレーション。視聴者に語りかけるように。）",
    "image_prompt": "（Gemini画像生成用の詳細な英語プロンプト。16:9 aspect ratio, professional, high quality, modern design を含める）",
    "overlay_text": "（画面に表示する15文字以内の要約テロップ）"
  }},
  ...
]
```

## 重要な指示:
1. scene_id は 1 から {num_scenes} まで連番
2. narration_script は話し言葉で自然に（10〜20秒で読める長さ）
3. image_prompt は英語で、16:9アスペクト比、高品質を指定
4. overlay_text は日本語で簡潔に（15文字以内）
5. シーン1はタイトル・導入、最終シーンはまとめ・CTA
6. JSONのみを出力（説明文不要）
"""

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.MODEL_SCRIPT,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=4096
                )
            )

            # JSONを抽出
            text = response.text

            # コードブロックからJSON抽出
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            scenes_data = json.loads(text.strip())

            scenes = []
            for data in scenes_data:
                scene = Scene(
                    scene_id=data["scene_id"],
                    narration_script=data["narration_script"],
                    image_prompt=data["image_prompt"],
                    overlay_text=data["overlay_text"]
                )
                scenes.append(scene)

            logger.info(f"Generated {len(scenes)} scenes")
            return scenes

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response text: {text[:500]}")
            raise
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            raise

    async def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: str = "default"
    ) -> float:
        """
        テキストから音声を生成

        Args:
            text: ナレーションテキスト
            output_path: 出力WAVファイルパス
            voice: 音声タイプ

        Returns:
            音声の長さ（秒）
        """
        voice_name = self.TTS_VOICES.get(voice, self.TTS_VOICES["default"])
        logger.info(f"Generating audio with voice '{voice_name}': {text[:30]}...")

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
                model=self.MODEL_TTS,
                contents=text,
                config=config
            )

            # PCMデータを抽出
            pcm_data = None
            if response.candidates and len(response.candidates) > 0:
                parts = response.candidates[0].content.parts
                for part in parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        data = part.inline_data.data
                        if isinstance(data, str):
                            pcm_data = base64.b64decode(data)
                        else:
                            pcm_data = data
                        break

            if not pcm_data:
                raise ValueError("No audio data in response")

            # PCM -> WAV 変換
            wav_data = self._pcm_to_wav(pcm_data)

            # ファイル保存
            with open(output_path, 'wb') as f:
                f.write(wav_data)

            # 音声長を計算
            duration = len(pcm_data) / (24000 * 2)  # 24kHz, 16bit
            logger.info(f"Audio generated: {duration:.2f}s, {len(wav_data):,} bytes")

            return duration

        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            raise

    def _pcm_to_wav(
        self,
        pcm_data: bytes,
        sample_rate: int = 24000,
        channels: int = 1,
        sample_width: int = 2
    ) -> bytes:
        """PCMデータをWAV形式に変換"""
        import io

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)

        return buffer.getvalue()

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080
    ) -> bool:
        """
        プロンプトから画像を生成

        Args:
            prompt: 画像生成プロンプト
            output_path: 出力PNGファイルパス
            width: 画像幅
            height: 画像高さ

        Returns:
            成功したかどうか
        """
        logger.info(f"Generating image: {prompt[:50]}...")

        # 16:9 アスペクト比を強調
        enhanced_prompt = f"{prompt}, 16:9 aspect ratio, {width}x{height} resolution, ultra high quality, professional photography, sharp focus"

        try:
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.MODEL_IMAGE,
                contents=enhanced_prompt,
                config=config
            )

            # 画像データを抽出
            if response.candidates and len(response.candidates) > 0:
                parts = response.candidates[0].content.parts
                for part in parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)

                        # 画像をリサイズして保存
                        img = Image.open(io.BytesIO(image_data))
                        img = img.convert('RGB')
                        img = img.resize((width, height), Image.Resampling.LANCZOS)
                        img.save(output_path, 'PNG', quality=95)

                        logger.info(f"Image saved: {output_path}")
                        return True

            logger.warning("No image data in response")
            return False

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            # フォールバック: プレースホルダー画像を生成
            self._create_placeholder_image(output_path, prompt, width, height)
            return True

    def _create_placeholder_image(
        self,
        output_path: str,
        text: str,
        width: int,
        height: int
    ):
        """プレースホルダー画像を生成"""
        img = Image.new('RGB', (width, height), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)

        # テキストを中央に配置
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()

        # テキストを折り返し
        max_chars = 40
        lines = [text[i:i+max_chars] for i in range(0, len(text[:200]), max_chars)]

        y_offset = height // 2 - len(lines) * 30
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y_offset), line, fill='white', font=font)
            y_offset += 60

        img.save(output_path, 'PNG')
        logger.info(f"Placeholder image saved: {output_path}")


# =============================================================================
# Video Editor with Ken Burns Effect
# =============================================================================

class VideoEditor:
    """動画編集エンジン（Ken Burns Effect対応）"""

    def __init__(self, config: VideoConfig = None):
        """初期化"""
        self.config = config or VideoConfig()
        logger.info("VideoEditor initialized")

    def create_ken_burns_clip(
        self,
        image_path: str,
        duration: float,
        zoom_start: float = 1.0,
        zoom_end: float = None
    ) -> ImageClip:
        """
        Ken Burns Effect付きの画像クリップを作成

        Args:
            image_path: 画像ファイルパス
            duration: 表示時間（秒）
            zoom_start: 開始時のズーム倍率
            zoom_end: 終了時のズーム倍率

        Returns:
            Ken Burns Effect付きのImageClip
        """
        if zoom_end is None:
            zoom_end = self.config.ken_burns_zoom

        # 画像読み込み
        img = Image.open(image_path)
        img = img.convert('RGB')
        img_array = np.array(img)

        # ベースクリップ
        base_clip = ImageClip(img_array).set_duration(duration)

        # Ken Burns Effect: 時間に応じてズーム
        def ken_burns_effect(get_frame, t):
            # 線形補間でズーム率を計算
            progress = t / duration
            current_zoom = zoom_start + (zoom_end - zoom_start) * progress

            frame = get_frame(t)
            h, w = frame.shape[:2]

            # 新しいサイズを計算
            new_w = int(w * current_zoom)
            new_h = int(h * current_zoom)

            # リサイズ
            pil_img = Image.fromarray(frame)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 中央クロップ
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            pil_img = pil_img.crop((left, top, left + w, top + h))

            return np.array(pil_img)

        # エフェクト適用
        ken_burns_clip = base_clip.fl(ken_burns_effect)

        return ken_burns_clip

    def add_text_overlay(
        self,
        clip: ImageClip,
        text: str,
        position: str = "bottom"
    ) -> CompositeVideoClip:
        """
        テロップを追加

        Args:
            clip: ベースクリップ
            text: テロップテキスト
            position: 位置（"bottom", "top", "center"）

        Returns:
            テロップ付きのCompositeVideoClip
        """
        duration = clip.duration

        # テキスト背景（半透明黒帯）
        bg_height = self.config.font_size + 40
        bg_clip = ColorClip(
            size=(self.config.width, bg_height),
            color=(0, 0, 0)
        ).set_opacity(0.7).set_duration(duration)

        # 位置設定
        if position == "bottom":
            bg_position = ("center", self.config.height - bg_height - 20)
            text_position = ("center", self.config.height - bg_height // 2 - 30)
        elif position == "top":
            bg_position = ("center", 20)
            text_position = ("center", 20 + bg_height // 2 - 10)
        else:
            bg_position = ("center", "center")
            text_position = ("center", "center")

        bg_clip = bg_clip.set_position(bg_position)

        # テキストクリップ
        try:
            text_clip = TextClip(
                text,
                fontsize=self.config.font_size,
                color=self.config.font_color,
                font='Arial-Bold',
                method='caption',
                size=(self.config.width - 100, None)
            ).set_duration(duration).set_position(text_position)
        except Exception as e:
            logger.warning(f"TextClip creation failed, using simple method: {e}")
            # フォールバック: PIL で画像として作成
            text_clip = self._create_text_image_clip(text, duration, text_position)

        # 合成
        composite = CompositeVideoClip([
            clip,
            bg_clip,
            text_clip
        ], size=(self.config.width, self.config.height))

        return composite

    def _create_text_image_clip(
        self,
        text: str,
        duration: float,
        position: tuple
    ) -> ImageClip:
        """PILでテキスト画像を作成"""
        # 透明背景の画像を作成
        img = Image.new('RGBA', (self.config.width, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", self.config.font_size)
        except:
            font = ImageFont.load_default()

        # テキストを中央に配置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.config.width - text_width) // 2
        draw.text((x, 20), text, fill='white', font=font)

        return ImageClip(np.array(img)).set_duration(duration).set_position(position)

    def create_scene_clip(
        self,
        scene: Scene,
        audio_clip: Optional[AudioFileClip] = None
    ) -> CompositeVideoClip:
        """
        シーンからクリップを作成

        Args:
            scene: シーンデータ
            audio_clip: 音声クリップ（オプション）

        Returns:
            完成したシーンクリップ
        """
        # 表示時間を決定（音声長 + パディング）
        if audio_clip:
            duration = audio_clip.duration + self.config.scene_padding
        else:
            duration = scene.audio_duration + self.config.scene_padding

        # 最低3秒は表示
        duration = max(duration, 3.0)

        logger.info(f"Creating scene {scene.scene_id} clip: {duration:.2f}s")

        # Ken Burns Effect付き画像クリップ
        image_clip = self.create_ken_burns_clip(
            scene.image_path,
            duration
        )

        # テロップ追加
        clip_with_text = self.add_text_overlay(
            image_clip,
            scene.overlay_text
        )

        # 音声追加
        if audio_clip:
            clip_with_text = clip_with_text.set_audio(audio_clip)

        return clip_with_text

    def create_final_video(
        self,
        scenes: List[Scene],
        output_path: str
    ) -> str:
        """
        全シーンを結合して最終動画を作成

        Args:
            scenes: シーンリスト
            output_path: 出力ファイルパス

        Returns:
            出力ファイルパス
        """
        logger.info(f"Creating final video with {len(scenes)} scenes...")

        clips = []

        for scene in tqdm(scenes, desc="Processing scenes"):
            # 音声クリップを読み込み
            audio_clip = None
            if scene.audio_path and os.path.exists(scene.audio_path):
                audio_clip = AudioFileClip(scene.audio_path)

            # シーンクリップを作成
            scene_clip = self.create_scene_clip(scene, audio_clip)
            clips.append(scene_clip)

        # 全クリップを結合
        final_clip = concatenate_videoclips(clips, method="compose")

        # 動画を書き出し
        logger.info(f"Rendering video to {output_path}...")
        final_clip.write_videofile(
            output_path,
            fps=self.config.fps,
            codec='libx264',
            audio_codec='aac',
            bitrate='8000k',
            preset='medium',
            threads=4,
            logger=None  # MoviePyの詳細ログを抑制
        )

        # クリーンアップ
        final_clip.close()
        for clip in clips:
            clip.close()

        logger.info(f"Video saved: {output_path}")
        return output_path


# =============================================================================
# Main Workflow
# =============================================================================

class VideoGeneratorWorkflow:
    """動画生成ワークフロー"""

    def __init__(self, output_dir: str = "output"):
        """初期化"""
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.audio_dir = self.output_dir / "audio"
        self.video_dir = self.output_dir / "videos"

        # ディレクトリ作成
        self._setup_directories()

        # クライアント初期化
        self.gemini = GeminiVideoClient()
        self.editor = VideoEditor()

        logger.info(f"VideoGeneratorWorkflow initialized: {self.output_dir}")

    def _setup_directories(self):
        """出力ディレクトリを作成"""
        for dir_path in [self.images_dir, self.audio_dir, self.video_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        logger.info("Output directories created")

    async def generate_from_text(
        self,
        blog_content: str,
        output_name: str = None,
        num_scenes: int = 6,
        voice: str = "default"
    ) -> str:
        """
        ブログテキストから動画を生成

        Args:
            blog_content: ブログ記事テキスト
            output_name: 出力ファイル名（拡張子なし）
            num_scenes: シーン数
            voice: 音声タイプ

        Returns:
            生成された動画のパス
        """
        if output_name is None:
            output_name = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info("=" * 60)
        logger.info("Starting Video Generation Workflow")
        logger.info("=" * 60)

        # Step 1: 脚本生成
        logger.info("\n[Step 1/4] Generating script...")
        scenes = await self.gemini.generate_script(blog_content, num_scenes)

        # Step 2: 音声生成
        logger.info("\n[Step 2/4] Generating audio...")
        for scene in tqdm(scenes, desc="Audio generation"):
            audio_path = self.audio_dir / f"scene_{scene.scene_id:02d}.wav"
            duration = await self.gemini.generate_audio(
                scene.narration_script,
                str(audio_path),
                voice
            )
            scene.audio_path = str(audio_path)
            scene.audio_duration = duration

        # Step 3: 画像生成
        logger.info("\n[Step 3/4] Generating images...")
        for scene in tqdm(scenes, desc="Image generation"):
            image_path = self.images_dir / f"scene_{scene.scene_id:02d}.png"
            await self.gemini.generate_image(
                scene.image_prompt,
                str(image_path)
            )
            scene.image_path = str(image_path)

        # Step 4: 動画生成
        logger.info("\n[Step 4/4] Creating video...")
        output_path = self.video_dir / f"{output_name}.mp4"
        final_path = self.editor.create_final_video(scenes, str(output_path))

        # 結果サマリー
        logger.info("\n" + "=" * 60)
        logger.info("Video Generation Complete!")
        logger.info("=" * 60)
        logger.info(f"Output: {final_path}")
        logger.info(f"Scenes: {len(scenes)}")
        total_duration = sum(s.audio_duration for s in scenes)
        logger.info(f"Total duration: ~{total_duration:.1f}s")

        return final_path

    async def generate_from_url(
        self,
        url: str,
        output_name: str = None,
        num_scenes: int = 6,
        voice: str = "default"
    ) -> str:
        """
        URLからブログ記事を取得して動画を生成

        Args:
            url: ブログ記事のURL
            output_name: 出力ファイル名
            num_scenes: シーン数
            voice: 音声タイプ

        Returns:
            生成された動画のパス
        """
        import requests
        from html.parser import HTMLParser

        logger.info(f"Fetching content from: {url}")

        # URLからコンテンツを取得
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # HTMLからテキストを抽出（簡易版）
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.in_body = False
                self.skip_tags = {'script', 'style', 'nav', 'header', 'footer'}
                self.current_tag = None

            def handle_starttag(self, tag, attrs):
                self.current_tag = tag
                if tag == 'body':
                    self.in_body = True

            def handle_endtag(self, tag):
                if tag == 'body':
                    self.in_body = False
                self.current_tag = None

            def handle_data(self, data):
                if self.in_body and self.current_tag not in self.skip_tags:
                    text = data.strip()
                    if text:
                        self.text.append(text)

        extractor = TextExtractor()
        extractor.feed(response.text)
        blog_content = ' '.join(extractor.text)

        logger.info(f"Extracted {len(blog_content)} characters from URL")

        return await self.generate_from_text(
            blog_content,
            output_name,
            num_scenes,
            voice
        )

    async def generate_from_file(
        self,
        file_path: str,
        output_name: str = None,
        num_scenes: int = 6,
        voice: str = "default"
    ) -> str:
        """
        ファイルからブログ記事を読み込んで動画を生成

        Args:
            file_path: テキストファイルパス
            output_name: 出力ファイル名
            num_scenes: シーン数
            voice: 音声タイプ

        Returns:
            生成された動画のパス
        """
        logger.info(f"Reading content from: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            blog_content = f.read()

        logger.info(f"Read {len(blog_content)} characters from file")

        if output_name is None:
            output_name = Path(file_path).stem

        return await self.generate_from_text(
            blog_content,
            output_name,
            num_scenes,
            voice
        )


# =============================================================================
# CLI Entry Point
# =============================================================================

import io  # Add missing import at top level

def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Gemini Video Generator - Create high-quality explanation videos from blog articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input "AIについての記事テキスト..."
  python main.py --url "https://example.com/blog/ai-article"
  python main.py --file article.txt --scenes 8 --voice warm

Voices: default, bright, calm, warm, energetic, friendly
        """
    )

    # 入力ソース（排他的）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--input', '-i',
        type=str,
        help='ブログ記事のテキスト（直接入力）'
    )
    input_group.add_argument(
        '--url', '-u',
        type=str,
        help='ブログ記事のURL'
    )
    input_group.add_argument(
        '--file', '-f',
        type=str,
        help='ブログ記事のテキストファイルパス'
    )

    # オプション
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='出力ファイル名（拡張子なし）'
    )
    parser.add_argument(
        '--scenes', '-s',
        type=int,
        default=6,
        help='シーン数（デフォルト: 6）'
    )
    parser.add_argument(
        '--voice', '-v',
        type=str,
        default='default',
        choices=['default', 'bright', 'calm', 'warm', 'energetic', 'friendly'],
        help='音声タイプ（デフォルト: default）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='出力ディレクトリ（デフォルト: output）'
    )

    args = parser.parse_args()

    # ワークフロー実行
    async def run():
        workflow = VideoGeneratorWorkflow(args.output_dir)

        if args.input:
            return await workflow.generate_from_text(
                args.input,
                args.output,
                args.scenes,
                args.voice
            )
        elif args.url:
            return await workflow.generate_from_url(
                args.url,
                args.output,
                args.scenes,
                args.voice
            )
        elif args.file:
            return await workflow.generate_from_file(
                args.file,
                args.output,
                args.scenes,
                args.voice
            )

    try:
        result = asyncio.run(run())
        print(f"\nSuccess! Video created: {result}")
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
