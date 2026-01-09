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

        # ## で分割
        pattern = r'^##\s+(.+?)$'
        parts = re.split(pattern, content, flags=re.MULTILINE)

        # イントロ（最初の##の前）
        if parts[0].strip():
            sections.append({
                "title": "はじめに",
                "content": self._clean_content(parts[0])[:400]
            })

        # セクション
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                sections.append({
                    "title": parts[i].strip(),
                    "content": self._clean_content(parts[i + 1])[:400]
                })

        return sections[:8]  # 最大8セクション

    def _clean_content(self, text: str) -> str:
        """マークダウン記法を除去"""
        # 見出し、リンク、強調などを除去
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # リンク
        text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)  # 強調
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # 見出し
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)  # リスト
        return text.strip()

# ============================================================================
# Marp Slide Generator
# ============================================================================

class MarpSlideGenerator:
    """Marpスライド生成"""

    def generate(self, title: str, sections: List[Dict], output_path: Path) -> str:
        """Marpマークダウンを生成"""
        slides = []

        # タイトルスライド
        slides.append(f"""---
marp: true
theme: default
paginate: false
backgroundColor: #1a1a2e
color: #ffffff
style: |
  section {{
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  }}
  h1 {{
    color: #00d4ff;
    font-size: 2.2em;
    text-align: center;
    margin-top: 180px;
  }}
  h2 {{
    color: #00d4ff;
    border-bottom: 3px solid #00d4ff;
    padding-bottom: 10px;
    font-size: 1.8em;
  }}
  p {{
    font-size: 1.2em;
    line-height: 1.6;
  }}
  ul {{
    font-size: 1.1em;
    line-height: 1.8;
  }}
---

# {title}

""")

        # コンテンツスライド
        for section in sections:
            # ポイントを抽出
            points = self._extract_points(section["content"])
            points_md = "\n".join([f"- {p}" for p in points[:4]])

            slides.append(f"""---

## {section["title"]}

{points_md}

""")

        # エンディングスライド
        slides.append("""---

# ご視聴ありがとうございました

**if(塾) Blog**

詳しくはブログ記事をご覧ください

""")

        markdown = "\n".join(slides)
        output_path.write_text(markdown, encoding='utf-8')
        return markdown

    def _extract_points(self, content: str) -> List[str]:
        """コンテンツからポイントを抽出"""
        # 文を分割
        sentences = re.split(r'[。！？\n]', content)
        points = []
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and len(s) < 60:
                points.append(s)
        return points[:4] if points else ["詳細はブログで"]

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
        """PDF → PNG"""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(pdf_path), dpi=150)
            paths = []
            for i, img in enumerate(images):
                out = output_dir / f"slide_{i:02d}.png"
                img.save(str(out), "PNG")
                paths.append(out)
            return paths
        except Exception as e:
            logger.error(f"PDF to image error: {e}")
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
    """統合動画生成ワークフロー"""

    def __init__(self):
        self.section_extractor = SectionExtractor()
        self.marp_generator = MarpSlideGenerator()
        self.slide_renderer = SlideRenderer()
        self.narration_generator = NarrationGenerator()
        self.audio_generator = GTTSAudioGenerator()
        self.timing_generator = TimingGenerator()
        self.remotion_renderer = RemotionRenderer()

    async def generate(self, blog_content: str, title: str, topic: str) -> Dict:
        """ブログ記事から動画を生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent.parent / "output" / "videos" / f"{timestamp}_{topic}"
        output_dir.mkdir(parents=True, exist_ok=True)

        slides_dir = output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(exist_ok=True)

        try:
            # Step 1: セクション抽出
            logger.info("Step 1: Extracting sections...")
            sections = self.section_extractor.extract(blog_content)
            logger.info(f"Extracted {len(sections)} sections")

            # Step 2: Marpスライド生成
            logger.info("Step 2: Generating Marp slides...")
            marp_path = slides_dir / "slides.md"
            self.marp_generator.generate(title, sections, marp_path)

            # Step 3: PDF → PNG変換
            logger.info("Step 3: Rendering slides to images...")
            pdf_path = slides_dir / "slides.pdf"
            if not self.slide_renderer.render_to_pdf(marp_path, pdf_path):
                return {"status": "error", "error": "PDF rendering failed"}

            slide_images = self.slide_renderer.pdf_to_images(pdf_path, slides_dir)
            if not slide_images:
                return {"status": "error", "error": "PDF to image conversion failed"}
            logger.info(f"Created {len(slide_images)} slide images")

            # Step 4: ナレーションスクリプト生成
            logger.info("Step 4: Generating narration scripts...")
            scripts = await self.narration_generator.generate(title, sections)

            # Step 5: gTTSで音声生成
            logger.info("Step 5: Generating audio with gTTS...")
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

            # Step 6: タイミング情報生成
            logger.info("Step 6: Generating timing information...")
            timings = self.timing_generator.generate(audio_files)

            # Step 7: Remotionでレンダリング
            logger.info("Step 7: Rendering video with Remotion...")
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
            video_path = output_dir / f"video_{topic}.mp4"
            concat_file = output_dir / "concat.txt"

            # 各スライドを動画に変換して結合
            temp_videos = []
            with open(concat_file, 'w') as f:
                for i, (img, audio_info) in enumerate(zip(slide_images, audio_files)):
                    temp_video = output_dir / f"temp_{i:02d}.mp4"
                    duration = audio_info["duration"]
                    audio_path = audio_info["audio_file"]

                    cmd = [
                        "ffmpeg", "-y",
                        "-loop", "1", "-i", str(img),
                        "-i", str(audio_path),
                        "-c:v", "libx264", "-tune", "stillimage",
                        "-c:a", "aac", "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-t", str(duration),
                        str(temp_video)
                    ]
                    subprocess.run(cmd, capture_output=True)

                    if temp_video.exists():
                        f.write(f"file '{temp_video.name}'\n")
                        temp_videos.append(temp_video)

            # 結合
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(video_path)
            ]
            subprocess.run(concat_cmd, capture_output=True)

            # 一時ファイル削除
            for tv in temp_videos:
                tv.unlink()
            concat_file.unlink()

            return video_path if video_path.exists() else None

        except Exception as e:
            logger.error(f"Fallback render error: {e}")
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
