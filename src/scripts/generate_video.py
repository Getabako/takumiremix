#!/usr/bin/env python3
"""
動画生成スクリプト - Remotion Edition with TTS

ブログ記事の内容からRemotionを使用して動画を自動生成します。
- 標準動画（30秒、1920x1080）+ TTS音声 + ヒーロー画像
- ショート動画（15秒、1080x1920 縦型）- デフォルトでスキップ

使用方法:
    python generate_video.py --title "記事タイトル" --summary "記事概要" --topic ai_tools
"""
import asyncio
import json
import sys
import argparse
import logging
import subprocess
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.timezone import get_timestamp_jst, format_date
from lib.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoGenerationError(Exception):
    """動画生成エラー"""
    pass


class AudioGenerationError(Exception):
    """音声生成エラー"""
    pass


# トピック別推奨TTS音声
TOPIC_VOICES = {
    "psychology": "default",       # Kore - 落ち着いた声
    "education": "default",
    "startup": "bright",           # Puck - 明るい声
    "investment": "default",
    "ai_tools": "bright",
    "inclusive_education": "calm", # Charon - 静かな声
    "weekly_summary": "warm"       # Aoede - 温かみのある声
}


class BlogVideoGenerator:
    """ブログ用動画生成クラス（TTS対応）"""

    def __init__(self):
        self.remotion_dir = Path(__file__).parent.parent.parent / "remotion"
        self.public_dir = self.remotion_dir / "public"
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.gemini_client = None

    def _get_gemini_client(self) -> GeminiClient:
        """GeminiClientを取得（遅延初期化）"""
        if self.gemini_client is None:
            self.gemini_client = GeminiClient()
        return self.gemini_client

    def _check_dependencies(self) -> bool:
        """依存関係をチェック"""
        # Node.jsのチェック
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error("Node.js is not installed")
                return False
            logger.info(f"Node.js version: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Node.js is not found in PATH")
            return False

        # node_modulesのチェック
        node_modules = self.remotion_dir / "node_modules"
        if not node_modules.exists():
            logger.warning("node_modules not found. Installing dependencies...")
            try:
                subprocess.run(
                    ["npm", "install"],
                    cwd=str(self.remotion_dir),
                    check=True
                )
                logger.info("Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install dependencies: {e}")
                return False

        return True

    def _extract_points_from_content(self, content: str, max_points: int = 3) -> List[str]:
        """記事コンテンツからポイントを抽出"""
        points = []

        # 見出し（##）からポイントを抽出
        lines = content.split('\n')
        for line in lines:
            if line.startswith('## ') and not line.startswith('### '):
                point = line[3:].strip()
                # 特定のセクションをスキップ
                skip_keywords = ['まとめ', '参考', 'はじめに', '導入', '結論', '目次', '概要']
                if not any(kw in point for kw in skip_keywords):
                    points.append(point)
                    if len(points) >= max_points:
                        break

        # 見出しが足りない場合は箇条書きから抽出
        if len(points) < max_points:
            for line in lines:
                if line.strip().startswith('- ') or line.strip().startswith('* '):
                    point = line.strip()[2:].strip()
                    if len(point) > 10 and len(point) < 100:
                        points.append(point)
                        if len(points) >= max_points:
                            break

        return points[:max_points]

    async def _generate_narration(
        self,
        title: str,
        summary: str,
        points: List[str],
        topic: str,
        duration_seconds: int = 30,
        full_content: str = ""
    ) -> Dict:
        """
        Gemini TTSでナレーション音声を生成（記事全体を分析）

        Args:
            title: 記事タイトル
            summary: 記事概要
            points: 主要ポイントのリスト
            topic: トピックID（音声選択用）
            duration_seconds: 動画の長さ
            full_content: 記事全文（より良いナレーション生成用）

        Returns:
            ナレーション結果（audio_data, script, article_analysis）
        """
        logger.info(f"Generating TTS narration for: {title[:50]}...")
        if full_content:
            logger.info(f"Using full article content ({len(full_content)} chars) for enhanced narration")

        try:
            client = self._get_gemini_client()
            voice = TOPIC_VOICES.get(topic, "default")

            narration = await client.generate_video_narration(
                title=title,
                summary=summary,
                points=points,
                duration_seconds=duration_seconds,
                voice=voice,
                full_content=full_content,
                analyze_content=bool(full_content)  # コンテンツがある場合は分析を有効化
            )

            if narration.get("status") == "success" and narration.get("audio_data"):
                logger.info(f"Narration generated: {narration.get('audio_size_bytes', 0)} bytes, voice: {voice}")
                if narration.get("article_analysis"):
                    logger.info(f"Article analysis: {len(narration.get('article_analysis', {}).get('video_points', []))} video points extracted")
                return narration
            else:
                logger.warning(f"TTS generation failed: {narration.get('error', 'Unknown error')}")
                return {"status": "error", "audio_data": None, "script": None}

        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return {"status": "error", "audio_data": None, "script": None, "error": str(e)}

    def _prepare_public_files(
        self,
        audio_data: Optional[bytes],
        hero_image_path: Optional[str]
    ) -> Dict[str, Optional[str]]:
        """
        public/ディレクトリに音声・画像ファイルを配置

        Args:
            audio_data: 音声バイナリデータ
            hero_image_path: ヒーロー画像のパス

        Returns:
            staticFile参照用のファイル名
        """
        result = {"audio_file": None, "hero_image_file": None}

        # 音声ファイル保存
        if audio_data:
            audio_path = self.public_dir / "narration.wav"
            try:
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                result["audio_file"] = "narration.wav"
                logger.info(f"Audio saved to: {audio_path}")
            except Exception as e:
                logger.error(f"Failed to save audio: {e}")

        # ヒーロー画像コピー
        if hero_image_path and Path(hero_image_path).exists():
            hero_dest = self.public_dir / "hero.png"
            try:
                shutil.copy(hero_image_path, hero_dest)
                result["hero_image_file"] = "hero.png"
                logger.info(f"Hero image copied to: {hero_dest}")
            except Exception as e:
                logger.error(f"Failed to copy hero image: {e}")

        return result

    def _cleanup_public_files(self):
        """public/ディレクトリの一時ファイルをクリーンアップ"""
        for filename in ["narration.wav", "hero.png"]:
            filepath = self.public_dir / filename
            if filepath.exists():
                try:
                    filepath.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup {filename}: {e}")

    async def generate_video(
        self,
        title: str,
        summary: str,
        points: List[str],
        topic: str,
        date: Optional[str] = None,
        author_name: str = "if(塾) Blog",
        generate_short: bool = False,  # デフォルトでスキップ
        generate_audio: bool = True,
        hero_image_path: Optional[str] = None,
        full_content: str = ""
    ) -> Dict:
        """
        ブログ動画を生成（TTS音声付き・記事全体分析対応）

        Args:
            title: 記事タイトル
            summary: 記事要約
            points: 主要ポイントのリスト
            topic: トピックID
            date: 日付文字列
            author_name: 著者名
            generate_short: ショート動画も生成するか（デフォルト: False）
            generate_audio: TTS音声を生成するか（デフォルト: True）
            hero_image_path: ヒーロー画像のパス
            full_content: 記事全文（より良い動画生成用）

        Returns:
            生成結果の辞書
        """
        logger.info(f"Generating video for: {title}")
        logger.info(f"  - Generate audio: {generate_audio}")
        logger.info(f"  - Generate short: {generate_short}")
        logger.info(f"  - Hero image: {hero_image_path or 'None'}")
        logger.info(f"  - Full content: {len(full_content)} chars")

        # 依存関係チェック
        if not self._check_dependencies():
            raise VideoGenerationError("Dependencies not satisfied")

        # 日付の設定
        if not date:
            date = format_date(fmt='%Y年%m月%d日')  # JST

        timestamp = get_timestamp_jst()

        result = {
            "status": "success",
            "videos": {},
            "narration": {},
            "generated_at": timestamp
        }

        # TTS音声生成（記事全体を分析）
        audio_data = None
        narration_script = None
        article_analysis = None
        if generate_audio:
            narration = await self._generate_narration(
                title=title,
                summary=summary,
                points=points,
                topic=topic,
                duration_seconds=30,
                full_content=full_content  # 記事全文を渡して分析
            )
            article_analysis = narration.get("article_analysis")
            if narration.get("status") == "success":
                audio_data = narration.get("audio_data")
                narration_script = narration.get("script")
                # 記事分析から拡張されたポイントを使用
                enhanced_points = narration.get("enhanced_points", points)
                if enhanced_points and len(enhanced_points) > len(points):
                    logger.info(f"Using enhanced points from analysis: {len(enhanced_points)} points")
                    points = enhanced_points
                result["narration"] = {
                    "script": narration_script,
                    "audio_size_bytes": len(audio_data) if audio_data else 0,
                    "voice": TOPIC_VOICES.get(topic, "default"),
                    "article_analysis": article_analysis
                }
            else:
                logger.warning("Audio generation failed, continuing without audio")
                result["narration"] = {"status": "skipped", "reason": narration.get("error", "Unknown")}

        # public/ディレクトリにファイル配置
        public_files = self._prepare_public_files(audio_data, hero_image_path)

        # propsデータを準備
        props_data = {
            "title": title,
            "summary": summary,
            "points": points,
            "topic": topic,
            "date": date,
            "authorName": author_name,
            "audioUrl": public_files.get("audio_file"),
            "heroImageUrl": public_files.get("hero_image_file")
        }

        # ショート用props
        props_data_short = {
            **props_data,
            "isShort": True
        }

        # propsをJSONファイルに保存
        props_file = self.remotion_dir / "props.json"
        props_short_file = self.remotion_dir / "props_short.json"

        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props_data, f, ensure_ascii=False, indent=2)

        if generate_short:
            with open(props_short_file, "w", encoding="utf-8") as f:
                json.dump(props_data_short, f, ensure_ascii=False, indent=2)

        try:
            # 標準動画をレンダリング
            standard_output = self.output_dir / f"blog_video_{timestamp}_{topic}.mp4"
            logger.info("Rendering standard video (30s, 1920x1080)...")

            await self._render_video(
                composition_id="BlogVideo",
                output_path=str(standard_output),
                props_file=str(props_file)
            )

            result["videos"]["standard"] = {
                "path": str(standard_output),
                "duration": 30,
                "resolution": "1920x1080",
                "size_bytes": os.path.getsize(standard_output) if standard_output.exists() else 0,
                "has_audio": audio_data is not None,
                "has_hero_image": public_files.get("hero_image_file") is not None
            }
            logger.info(f"Standard video saved: {standard_output}")

            # ショート動画をレンダリング（デフォルトでスキップ）
            if generate_short:
                short_output = self.output_dir / f"blog_video_short_{timestamp}_{topic}.mp4"
                logger.info("Rendering short video (15s, 1080x1920)...")

                await self._render_video(
                    composition_id="BlogVideoShort",
                    output_path=str(short_output),
                    props_file=str(props_short_file)
                )

                result["videos"]["short"] = {
                    "path": str(short_output),
                    "duration": 15,
                    "resolution": "1080x1920",
                    "size_bytes": os.path.getsize(short_output) if short_output.exists() else 0
                }
                logger.info(f"Short video saved: {short_output}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Video rendering failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        finally:
            # クリーンアップ
            if props_file.exists():
                props_file.unlink()
            if props_short_file.exists():
                props_short_file.unlink()
            self._cleanup_public_files()

        return result

    async def _render_video(
        self,
        composition_id: str,
        output_path: str,
        props_file: str
    ):
        """Remotionで動画をレンダリング"""
        render_script = self.remotion_dir / "render.mjs"

        cmd = [
            "node",
            str(render_script),
            composition_id,
            output_path,
            props_file
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.remotion_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # 出力をログに記録
        if stdout:
            for line in stdout.decode().split('\n'):
                if line.strip():
                    logger.info(f"[Remotion] {line}")

        if stderr:
            stderr_text = stderr.decode()
            for line in stderr_text.split('\n'):
                if line.strip():
                    logger.warning(f"[Remotion stderr] {line}")

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Remotion render failed with exit code {process.returncode}")
            logger.error(f"Error details: {error_msg}")

            # エラー解析
            self._analyze_error(error_msg)

            raise subprocess.CalledProcessError(
                process.returncode,
                cmd,
                output=stdout,
                stderr=stderr
            )

    def _analyze_error(self, error_msg: str):
        """エラーメッセージを解析して原因を特定"""
        error_patterns = {
            "Target closed": {
                "cause": "Chromium/Puppeteerがクラッシュしました",
                "solution": "Chrome依存ライブラリ(libasound2t64等)がインストールされているか確認してください"
            },
            "libasound": {
                "cause": "オーディオライブラリが見つかりません",
                "solution": "Ubuntu 24.04ではlibasound2t64を使用してください"
            },
            "ENOENT": {
                "cause": "必要なファイルまたはディレクトリが見つかりません",
                "solution": "node_modulesが存在するか確認してください"
            },
            "Cannot find module": {
                "cause": "Node.jsモジュールが見つかりません",
                "solution": "npm installを実行してください"
            },
            "out of memory": {
                "cause": "メモリ不足",
                "solution": "タイムアウトを延長するか、動画の解像度を下げてください"
            },
            "timeout": {
                "cause": "レンダリングがタイムアウトしました",
                "solution": "タイムアウト値を延長してください"
            },
            "audio": {
                "cause": "音声ファイル関連のエラー",
                "solution": "音声ファイルの形式を確認してください（WAV推奨）"
            }
        }

        for pattern, info in error_patterns.items():
            if pattern.lower() in error_msg.lower():
                logger.error(f"[Error Analysis] 原因: {info['cause']}")
                logger.error(f"[Error Analysis] 解決策: {info['solution']}")
                return

        logger.error("[Error Analysis] 未知のエラーです。詳細なログを確認してください。")


async def generate_video(
    article: Dict,
    output_dir: Optional[str] = None,
    generate_short: bool = False,  # デフォルトでスキップ
    generate_audio: bool = True
) -> Dict:
    """
    記事データから動画を生成（メインエントリーポイント）

    Args:
        article: 記事データ
            - title: 記事タイトル
            - summary/description: 記事概要
            - content: 記事本文（ポイント抽出用）
            - points: 主要ポイント（オプション）
            - topic_id/topic: トピックID
            - hero_image_path: ヒーロー画像パス（オプション）
        output_dir: 出力ディレクトリ（オプション）
        generate_short: ショート動画も生成するか（デフォルト: False）
        generate_audio: TTS音声を生成するか（デフォルト: True）

    Returns:
        生成結果
    """
    generator = BlogVideoGenerator()

    if output_dir:
        generator.output_dir = Path(output_dir)
        generator.output_dir.mkdir(parents=True, exist_ok=True)

    title = article.get("title", "Untitled Article")
    summary = article.get("summary") or article.get("description", "")
    topic = article.get("topic_id") or article.get("topic", "ai_tools")
    content = article.get("content", "")
    hero_image_path = article.get("hero_image_path")

    # ポイントの取得または抽出
    points = article.get("points", [])
    if not points and content:
        points = generator._extract_points_from_content(content)

    # ポイントが空の場合はデフォルト
    if not points:
        points = [
            "最新トレンドの分析",
            "実践的なアドバイス",
            "今後の展望"
        ]

    try:
        result = await generator.generate_video(
            title=title,
            summary=summary,
            points=points,
            topic=topic,
            generate_short=generate_short,
            generate_audio=generate_audio,
            hero_image_path=hero_image_path,
            full_content=content  # 記事全文を渡して分析・動画生成
        )
        return result
    except VideoGenerationError as e:
        logger.error(f"Video generation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Generate blog video with Remotion and TTS"
    )
    parser.add_argument("--title", "-t", required=True, help="Article title")
    parser.add_argument("--summary", "-s", required=True, help="Article summary")
    parser.add_argument("--topic", type=str, default="ai_tools",
                        help="Topic ID (e.g., ai_tools, psychology)")
    parser.add_argument("--points", "-p", type=str,
                        help="JSON array of key points")
    parser.add_argument("--output", "-o", type=str, help="Output directory")
    parser.add_argument("--hero-image", type=str, help="Path to hero image")
    parser.add_argument("--with-short", action="store_true",
                        help="Also generate short video (default: skip)")
    parser.add_argument("--no-audio", action="store_true",
                        help="Skip TTS audio generation")

    args = parser.parse_args()

    article = {
        "title": args.title,
        "summary": args.summary,
        "topic_id": args.topic,
        "hero_image_path": args.hero_image
    }

    if args.points:
        try:
            article["points"] = json.loads(args.points)
        except json.JSONDecodeError:
            logger.warning("Invalid points JSON, using defaults")

    result = asyncio.run(generate_video(
        article=article,
        output_dir=args.output,
        generate_short=args.with_short,
        generate_audio=not args.no_audio
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
