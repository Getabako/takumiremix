#!/usr/bin/env python3
"""
Video Generation V2 - 動画専用コンテンツ生成ワークフロー

ブログ記事とは別に、動画専用のスクリプト・スライドを生成し、
音声付き解説動画を確実に出力する。

Workflow:
1. Video Script Generation - 動画専用スクリプト生成
2. Slide Image Generation - 全スライドの画像生成（フォールバック付き）
3. Audio Synthesis - ナレーション音声生成
4. Video Assembly - 音声同期した動画生成

Usage:
    from generate_video_v2 import VideoGeneratorV2

    generator = VideoGeneratorV2()
    result = await generator.generate(
        research_data=research_result,
        topic="ai_tools",
        topic_info=topic_info
    )
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field
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

# Third-party
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-generativeai not installed")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Error: Pillow not installed")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: numpy not installed")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class VideoConfig:
    """動画設定"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    num_slides: int = 6
    slide_duration: float = 5.0  # デフォルト表示時間
    audio_padding: float = 0.5  # 音声後の余韻


# トピック別カラースキーム
TOPIC_COLORS = {
    "psychology": ("#2b6cb0", "#4299e1", "#ebf8ff"),
    "education": ("#2f855a", "#48bb78", "#f0fff4"),
    "startup": ("#c05621", "#ed8936", "#fffaf0"),
    "investment": ("#744210", "#d69e2e", "#fffff0"),
    "ai_tools": ("#1a365d", "#3182ce", "#ebf8ff"),
    "inclusive_education": ("#285e61", "#38b2ac", "#e6fffa"),
    "weekly_summary": ("#553c9a", "#805ad5", "#faf5ff"),
}


# =============================================================================
# Video Script Generator (Agent Implementation)
# =============================================================================

class VideoScriptGenerator:
    """動画専用スクリプト生成 - video-script-agent の実装"""

    MODEL = "gemini-3-flash-preview"  # Updated: Gemini 3 Flash (thinking off)

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY required")
        self.client = genai.Client(api_key=self.api_key)
        logger.info("VideoScriptGenerator initialized")

    async def generate(
        self,
        research_data: str,
        topic: str,
        topic_info: Dict[str, Any],
        num_slides: int = 6
    ) -> Dict[str, Any]:
        """
        リサーチ結果から動画専用スクリプトを生成

        Args:
            research_data: リサーチ結果テキスト
            topic: トピックID
            topic_info: トピック詳細情報
            num_slides: スライド数

        Returns:
            動画スクリプトJSON
        """
        logger.info(f"Generating video script for topic: {topic}, slides: {num_slides}")

        topic_name = topic_info.get("name", topic)
        topic_desc = topic_info.get("description", "")

        prompt = f"""あなたは解説動画のスクリプトライターです。
以下のリサーチ結果を元に、{num_slides}枚のスライドで構成される解説動画のスクリプトを生成してください。

## トピック
- 名前: {topic_name}
- 説明: {topic_desc}

## リサーチ結果
{research_data[:8000]}

## 出力形式（厳密にこのJSON形式で出力）
```json
{{
  "title": "動画タイトル（30文字以内）",
  "description": "動画の説明（100文字以内）",
  "slides": [
    {{
      "slide_id": 1,
      "type": "title",
      "heading": "メインタイトル",
      "subheading": "サブタイトル",
      "points": [],
      "narration": "みなさんこんにちは。今回は〇〇について解説します。",
      "image_prompt": "Professional title slide with modern gradient background, blue and teal colors, clean minimalist design, 16:9 aspect ratio, no text"
    }},
    {{
      "slide_id": 2,
      "type": "content",
      "heading": "ポイント1のタイトル",
      "subheading": "",
      "points": ["要点A（15文字以内）", "要点B（15文字以内）", "要点C（15文字以内）"],
      "narration": "まず最初のポイントは〇〇です。これは...",
      "image_prompt": "Abstract infographic illustration, icons representing [concept], professional clean design, soft gradient background, 16:9 aspect ratio, no text"
    }}
  ],
  "total_narration_chars": 800,
  "audio_style": "calm"
}}
```

## 重要なルール

### スライド構成
1. slide_id=1: type="title" - タイトルスライド（導入ナレーション）
2. slide_id=2〜{num_slides-1}: type="content" - 内容スライド
3. slide_id={num_slides}: type="ending" - まとめスライド（CTA含む）

### ナレーション
- 話し言葉で自然に（「です・ます」調）
- 1スライド100〜150文字程度
- 視聴者に語りかけるトーン
- 絵文字は使用しない

### 画像プロンプト（英語で記述）
- 必ず「16:9 aspect ratio」を含める
- 「no text」を必ず含める（テキストは別途オーバーレイ）
- 具体的な視覚要素を指定
- 禁止: 人物の顔、著作権のあるキャラクター、文字

### pointsの要点
- 各要点は15文字以内
- 3つまで
- 具体的で簡潔に

## 注意
- JSONのみを出力（説明文不要）
- スライド数は必ず{num_slides}枚
"""

        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=4096,
                response_mime_type="application/json"
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.MODEL,
                contents=prompt,
                config=config
            )

            text = response.text.strip()

            # コードブロック除去
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            script = json.loads(text)

            # 検証
            if len(script.get("slides", [])) != num_slides:
                logger.warning(f"Slide count mismatch: expected {num_slides}, got {len(script.get('slides', []))}")
                # スライド数を調整
                script = self._adjust_slide_count(script, num_slides)

            logger.info(f"Video script generated: {len(script['slides'])} slides")
            return script

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            # フォールバックスクリプト
            return self._create_fallback_script(topic, topic_info, num_slides)

    def _adjust_slide_count(self, script: Dict, target: int) -> Dict:
        """スライド数を調整"""
        slides = script.get("slides", [])

        if len(slides) < target:
            # 不足分を追加
            while len(slides) < target:
                idx = len(slides) + 1
                slides.append({
                    "slide_id": idx,
                    "type": "content" if idx < target else "ending",
                    "heading": f"追加ポイント{idx - 1}",
                    "subheading": "",
                    "points": ["詳細は本編で解説"],
                    "narration": "続いてのポイントをご紹介します。",
                    "image_prompt": "Abstract professional background, soft gradient, minimalist design, 16:9 aspect ratio, no text"
                })
        elif len(slides) > target:
            # 超過分を削除
            slides = slides[:target]

        # 最後のスライドをendingに
        if slides:
            slides[-1]["type"] = "ending"

        script["slides"] = slides
        return script

    def _create_fallback_script(self, topic: str, topic_info: Dict, num_slides: int) -> Dict:
        """フォールバックスクリプト"""
        topic_name = topic_info.get("name", topic)

        slides = []
        for i in range(1, num_slides + 1):
            if i == 1:
                slide_type = "title"
                heading = topic_name
                narration = f"今回は{topic_name}について解説します。"
            elif i == num_slides:
                slide_type = "ending"
                heading = "まとめ"
                narration = "以上が今回のまとめです。ぜひブログもご覧ください。"
            else:
                slide_type = "content"
                heading = f"ポイント{i - 1}"
                narration = f"ポイント{i - 1}について説明します。"

            slides.append({
                "slide_id": i,
                "type": slide_type,
                "heading": heading,
                "subheading": "",
                "points": [],
                "narration": narration,
                "image_prompt": "Abstract professional background, soft gradient, minimalist design, 16:9 aspect ratio, no text"
            })

        return {
            "title": topic_name,
            "description": f"{topic_name}の解説動画",
            "slides": slides,
            "audio_style": "calm"
        }


# =============================================================================
# Slide Image Generator (Skill Implementation)
# =============================================================================

class SlideImageGenerator:
    """スライド画像生成 - video-slide-generation スキルの実装"""

    MODEL = "gemini-2.5-flash-preview-05-20"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY required")
        self.client = genai.Client(api_key=self.api_key)
        logger.info("SlideImageGenerator initialized")

    async def generate_all(
        self,
        slides: List[Dict],
        topic_id: str,
        output_dir: Path
    ) -> List[Dict]:
        """
        全スライドの画像を生成（フォールバック付き）

        Args:
            slides: スライドリスト
            topic_id: トピックID
            output_dir: 出力ディレクトリ

        Returns:
            画像パス・Base64が追加されたスライドリスト
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        result_slides = []
        successful = 0
        fallback_count = 0

        for slide in slides:
            slide_id = slide["slide_id"]
            image_path = output_dir / f"slide_{slide_id:02d}.png"

            # Gemini画像生成を試行
            success = await self._generate_image_gemini(
                prompt=slide.get("image_prompt", ""),
                output_path=image_path
            )

            if success:
                successful += 1
                method = "gemini"
            else:
                # フォールバック画像生成
                logger.warning(f"Slide {slide_id}: Using fallback image")
                self._create_fallback_image(
                    slide=slide,
                    topic_id=topic_id,
                    output_path=image_path
                )
                fallback_count += 1
                method = "fallback"

            # Base64エンコード
            image_base64 = self._to_base64(image_path)

            result_slides.append({
                **slide,
                "image_path": str(image_path),
                "image_base64": image_base64,
                "generation_method": method
            })

            # レート制限対策
            await asyncio.sleep(0.5)

        logger.info(f"Image generation complete: {successful} gemini, {fallback_count} fallback")

        # 検証: スライド数 = 画像数
        assert len(result_slides) == len(slides), "Image count mismatch!"

        return result_slides

    async def _generate_image_gemini(self, prompt: str, output_path: Path) -> bool:
        """Gemini画像生成"""
        if not prompt:
            return False

        try:
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.MODEL,
                contents=prompt,
                config=config
            )

            # 画像抽出
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        data = part.inline_data.data
                        if isinstance(data, str):
                            data = base64.b64decode(data)

                        # PIL画像に変換
                        import io
                        img = Image.open(io.BytesIO(data))
                        img = img.convert('RGB')

                        # 16:9にリサイズ
                        img = self._resize_to_16_9(img)
                        img.save(str(output_path), 'PNG', quality=95)

                        logger.info(f"Generated: {output_path.name}")
                        return True

            return False

        except Exception as e:
            logger.error(f"Gemini image error: {e}")
            return False

    def _resize_to_16_9(self, img: Image.Image) -> Image.Image:
        """16:9にリサイズ"""
        target_w, target_h = 1920, 1080
        img_w, img_h = img.size

        # アスペクト比計算
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h

        if img_ratio > target_ratio:
            new_w = target_w
            new_h = int(target_w / img_ratio)
        else:
            new_h = target_h
            new_w = int(target_h * img_ratio)

        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 背景に配置
        result = Image.new('RGB', (target_w, target_h), (30, 30, 50))
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        result.paste(img, (paste_x, paste_y))

        return result

    def _create_fallback_image(
        self,
        slide: Dict,
        topic_id: str,
        output_path: Path
    ):
        """フォールバック画像（グラデーション背景）"""
        colors = TOPIC_COLORS.get(topic_id, ("#1a1a2e", "#4a4a6e", "#e0e0e0"))
        primary, secondary, _ = colors

        # グラデーション背景
        img = self._create_gradient(1920, 1080, primary, secondary)

        # タイトルを追加
        draw = ImageDraw.Draw(img)
        heading = slide.get("heading", "")

        try:
            font = ImageFont.truetype("arial.ttf", 72)
        except:
            font = ImageFont.load_default()

        # テキストを中央に配置
        if heading:
            bbox = draw.textbbox((0, 0), heading, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (1920 - text_w) // 2
            y = (1080 - text_h) // 2 - 50

            # 影
            draw.text((x + 3, y + 3), heading, fill=(0, 0, 0, 100), font=font)
            # テキスト
            draw.text((x, y), heading, fill="white", font=font)

        img.save(str(output_path), 'PNG')
        logger.info(f"Fallback created: {output_path.name}")

    def _create_gradient(
        self,
        width: int,
        height: int,
        color1: str,
        color2: str
    ) -> Image.Image:
        """グラデーション画像を生成"""
        # カラーコードをRGBに変換
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        c1 = hex_to_rgb(color1)
        c2 = hex_to_rgb(color2)

        # グラデーション生成
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        for y in range(height):
            ratio = y / height
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            for x in range(width):
                pixels[x, y] = (r, g, b)

        return img

    def _to_base64(self, image_path: Path) -> str:
        """画像をBase64 Data URLに変換"""
        with open(image_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{data}"


# =============================================================================
# Audio Synthesizer
# =============================================================================

class AudioSynthesizerV2:
    """音声合成 - Gemini TTS"""

    MODEL = "gemini-2.5-flash-preview-tts"

    VOICES = {
        "calm": "Kore",
        "bright": "Puck",
        "warm": "Aoede",
        "default": "Kore"
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY required")
        self.client = genai.Client(api_key=self.api_key)

    async def synthesize_all(
        self,
        slides: List[Dict],
        audio_style: str,
        output_dir: Path
    ) -> Tuple[List[Dict], str]:
        """
        全スライドのナレーションを合成

        Returns:
            (slides with audio info, combined audio path)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        voice = self.VOICES.get(audio_style, self.VOICES["default"])
        all_audio_data = []

        for slide in slides:
            slide_id = slide["slide_id"]
            narration = slide.get("narration", "")

            if not narration:
                slide["audio_duration"] = 3.0  # 最低表示時間
                continue

            audio_path = output_dir / f"audio_{slide_id:02d}.wav"

            try:
                duration, audio_data = await self._synthesize(narration, voice, audio_path)
                slide["audio_duration"] = duration
                slide["audio_path"] = str(audio_path)
                all_audio_data.append(audio_data)
                logger.info(f"Audio {slide_id}: {duration:.1f}s")
            except Exception as e:
                logger.error(f"Audio {slide_id} failed: {e}")
                slide["audio_duration"] = 5.0  # フォールバック

            await asyncio.sleep(0.3)

        # 全音声を結合
        combined_path = output_dir / "narration.wav"
        if all_audio_data:
            self._combine_audio(all_audio_data, combined_path)

        return slides, str(combined_path) if combined_path.exists() else None

    async def _synthesize(self, text: str, voice: str, output_path: Path) -> Tuple[float, bytes]:
        """単一テキストを音声化"""
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
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

        # PCM抽出
        pcm_data = None
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    data = part.inline_data.data
                    pcm_data = base64.b64decode(data) if isinstance(data, str) else data
                    break

        if not pcm_data:
            raise ValueError("No audio data")

        # WAV保存
        wav_data = self._pcm_to_wav(pcm_data)
        with open(output_path, 'wb') as f:
            f.write(wav_data)

        duration = len(pcm_data) / (24000 * 2)
        return duration, pcm_data

    def _pcm_to_wav(self, pcm: bytes, rate: int = 24000) -> bytes:
        """PCM -> WAV"""
        import io
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        return buf.getvalue()

    def _combine_audio(self, audio_list: List[bytes], output_path: Path):
        """複数の音声を結合"""
        combined = b''.join(audio_list)
        wav_data = self._pcm_to_wav(combined)
        with open(output_path, 'wb') as f:
            f.write(wav_data)


# =============================================================================
# Video Assembler (Remotion Integration)
# =============================================================================

class VideoAssemblerV2:
    """Remotion統合による動画生成"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.remotion_dir = self.project_root / "remotion"

    async def assemble(
        self,
        slides: List[Dict],
        audio_path: Optional[str],
        output_path: Path,
        config: VideoConfig
    ) -> str:
        """
        スライドと音声から動画を生成

        Args:
            slides: 画像・音声情報付きスライドリスト
            audio_path: 結合済み音声パス
            output_path: 出力動画パス
            config: 動画設定

        Returns:
            出力動画パス
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # propsを準備
        props = self._build_props(slides, audio_path, config)

        # props.jsonを保存
        props_path = self.remotion_dir / "public" / "props_video_v2.json"
        props_path.parent.mkdir(parents=True, exist_ok=True)
        with open(props_path, 'w', encoding='utf-8') as f:
            json.dump(props, f, ensure_ascii=False, indent=2)

        logger.info(f"Props saved: {props_path}")

        # Remotionでレンダリング
        result = await self._render_remotion(props_path, output_path)

        return result

    def _build_props(
        self,
        slides: List[Dict],
        audio_path: Optional[str],
        config: VideoConfig
    ) -> Dict:
        """Remotion用propsを構築"""
        # スライドデータを正規化
        normalized_slides = []
        slide_images = []

        for slide in slides:
            normalized = {
                "type": slide.get("type", "content"),
                "heading": slide.get("heading", ""),
                "subheading": slide.get("subheading", ""),
                "points": slide.get("points", []),
                "duration": slide.get("audio_duration", config.slide_duration) + config.audio_padding
            }
            normalized_slides.append(normalized)

            # Base64画像
            image_base64 = slide.get("image_base64", "")
            slide_images.append(image_base64)

        # 音声Base64
        audio_base64 = ""
        if audio_path and Path(audio_path).exists():
            with open(audio_path, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')
                audio_base64 = f"data:audio/wav;base64,{audio_data}"

        # 合計時間を計算
        total_duration = sum(s["duration"] for s in normalized_slides)

        props = {
            "slides": normalized_slides,
            "slideImages": slide_images,
            "audioDataUrl": audio_base64,
            "slideDuration": config.slide_duration,
            "totalDuration": total_duration,
            "fps": config.fps,
            "width": config.width,
            "height": config.height
        }

        # 検証ログ
        logger.info(f"Props: {len(normalized_slides)} slides, {len(slide_images)} images")
        logger.info(f"Total duration: {total_duration:.1f}s")

        return props

    async def _render_remotion(self, props_path: Path, output_path: Path) -> str:
        """Remotionでレンダリング"""
        render_script = self.remotion_dir / "render.mjs"

        if not render_script.exists():
            raise FileNotFoundError(f"render.mjs not found: {render_script}")

        cmd = [
            "node",
            str(render_script),
            "SlideVideo",
            str(output_path),  # render.mjs expects: outputPath as args[1]
            str(props_path)    # render.mjs expects: propsFile as args[2]
        ]

        logger.info(f"Rendering: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.remotion_dir),
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                logger.error(f"Render error: {result.stderr}")
                raise RuntimeError(f"Remotion failed: {result.stderr}")

            if not output_path.exists():
                raise RuntimeError("Video not created")

            logger.info(f"Video created: {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Render timeout")


# =============================================================================
# Main Workflow
# =============================================================================

class VideoGeneratorV2:
    """動画生成V2 - 完全なワークフロー"""

    def __init__(self, output_base: str = "output"):
        self.output_base = Path(output_base)
        self.config = VideoConfig()

        # コンポーネント初期化
        self.script_gen = VideoScriptGenerator()
        self.image_gen = SlideImageGenerator()
        self.audio_gen = AudioSynthesizerV2()
        self.assembler = VideoAssemblerV2()

        logger.info("VideoGeneratorV2 initialized")

    async def generate(
        self,
        research_data: str,
        topic: str,
        topic_info: Dict[str, Any],
        num_slides: int = 6
    ) -> Dict[str, Any]:
        """
        リサーチ結果から動画を生成

        Args:
            research_data: リサーチ結果
            topic: トピックID
            topic_info: トピック詳細
            num_slides: スライド数

        Returns:
            生成結果
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.output_base / "videos" / f"{topic}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("Video Generation V2 Workflow")
        logger.info("=" * 60)

        result = {
            "status": "error",
            "video_path": None,
            "slides_count": 0,
            "duration": 0
        }

        try:
            # Step 1: 動画スクリプト生成
            logger.info("\n[Step 1/4] Generating video script...")
            script = await self.script_gen.generate(
                research_data=research_data,
                topic=topic,
                topic_info=topic_info,
                num_slides=num_slides
            )

            # Step 2: スライド画像生成
            logger.info("\n[Step 2/4] Generating slide images...")
            slides = await self.image_gen.generate_all(
                slides=script["slides"],
                topic_id=topic,
                output_dir=output_dir / "images"
            )

            # Step 3: 音声生成
            logger.info("\n[Step 3/4] Synthesizing audio...")
            slides, audio_path = await self.audio_gen.synthesize_all(
                slides=slides,
                audio_style=script.get("audio_style", "calm"),
                output_dir=output_dir / "audio"
            )

            # Step 4: 動画生成
            logger.info("\n[Step 4/4] Assembling video...")
            video_path = output_dir / f"{script['title'][:30]}_{topic}.mp4"
            video_path = await self.assembler.assemble(
                slides=slides,
                audio_path=audio_path,
                output_path=video_path,
                config=self.config
            )

            # 結果
            total_duration = sum(s.get("audio_duration", 5) for s in slides)

            result = {
                "status": "success",
                "video_path": video_path,
                "slides_count": len(slides),
                "duration": total_duration,
                "title": script["title"],
                "output_dir": str(output_dir)
            }

            logger.info("\n" + "=" * 60)
            logger.info("Video Generation Complete!")
            logger.info(f"Output: {video_path}")
            logger.info(f"Duration: {total_duration:.1f}s")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            import traceback
            traceback.print_exc()
            result["error"] = str(e)

        return result


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Video Generator V2")
    parser.add_argument("--topic", default="ai_tools", help="Topic ID")
    parser.add_argument("--slides", type=int, default=6, help="Number of slides")
    parser.add_argument("--test", action="store_true", help="Run test")
    args = parser.parse_args()

    async def main():
        generator = VideoGeneratorV2()

        # テストデータ
        research_data = """
        2026年のAIツール最新動向について解説します。

        ## 主要なトピック
        1. 生成AIの進化 - GPT-5, Claude 4, Gemini 3.0が登場
        2. マルチモーダルAI - 画像・音声・動画を統合的に処理
        3. AIエージェント - 自律的にタスクを実行するAI
        4. ローカルAI - プライバシー重視のオンデバイス処理
        5. AI規制 - EU AI法、日本のAI法制化の動き

        ## 注目のツール
        - Claude Code: コード生成・レビューの自動化
        - Midjourney V7: 高品質画像生成
        - Sora: 動画生成AI
        """

        topic_info = {
            "name": "AIツール最新動向",
            "description": "2026年のAIツール・技術トレンド"
        }

        result = await generator.generate(
            research_data=research_data,
            topic=args.topic,
            topic_info=topic_info,
            num_slides=args.slides
        )

        print(f"\nResult: {json.dumps(result, ensure_ascii=False, indent=2)}")

    asyncio.run(main())
