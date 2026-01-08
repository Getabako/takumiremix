#!/usr/bin/env python3
"""
スライドベース動画生成スクリプト - 統合ワークフロー

ブログ記事から高品質なスライド解説動画を自動生成:

【重要: 処理フロー（この順序で実行）】
Step 1: スライド生成（Gemini 3 Pro + 2.5 Flash image）
        - 記事からスライド構成を生成
        - 各スライドの画像を生成
Step 2: 音声生成（Gemini 2.5 Flash TTS）
        - スライド内容を元にナレーションスクリプトを生成
        - TTS音声を生成（WAV形式）
Step 3: ファイル配置
        - スライド画像をpublic/slides/にコピー
        - 音声ファイルをpublic/narration.wavに保存
Step 4: 動画レンダリング（Remotion）
        - スライド画像と音声を統合
        - MP4動画を出力

注意:
- 動画は30秒以内に制限（6スライド x 5秒）
- 品質評価は行わない（記事のみ品質評価対象）
- 音声生成に失敗した場合も動画は生成される（無音）

使用方法:
    python generate_slide_video.py --article-file "output/posts/article.json"
"""
import asyncio
import argparse
import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

# Load .env file for local development
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.timezone import get_timestamp_jst, format_date
from lib.gemini_client import GeminiClient
from scripts.generate_slides import generate_slides

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# トピック別推奨TTS音声
TOPIC_VOICES = {
    "psychology": "default",
    "education": "default",
    "startup": "bright",
    "investment": "default",
    "ai_tools": "bright",
    "inclusive_education": "calm",
    "weekly_summary": "warm"
}


class SlideVideoGenerator:
    """スライドベース動画生成クラス"""

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent.parent / "output"
        self.remotion_dir = Path(__file__).parent.parent.parent / "remotion"
        self.public_dir = self.remotion_dir / "public"
        self.gemini_client = None

    def _get_gemini_client(self) -> GeminiClient:
        """GeminiClientを取得"""
        if self.gemini_client is None:
            self.gemini_client = GeminiClient()
        return self.gemini_client

    def _check_dependencies(self) -> Dict[str, bool]:
        """依存関係をチェック"""
        deps = {
            "node": False,
            "remotion": False,
            "marp_cli": False
        }

        # Node.js チェック
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=10
            )
            deps["node"] = result.returncode == 0
        except Exception:
            pass

        # Remotion チェック
        node_modules = self.remotion_dir / "node_modules"
        deps["remotion"] = node_modules.exists()

        # Marp CLI チェック
        try:
            result = subprocess.run(
                ["npx", "@marp-team/marp-cli", "--version"],
                capture_output=True, text=True, timeout=30
            )
            deps["marp_cli"] = result.returncode == 0
        except Exception:
            pass

        return deps

    async def _step1_generate_slides(
        self,
        article: Dict,
        target_slides: int
    ) -> Dict[str, Any]:
        """
        Step 1: スライド生成

        Args:
            article: 記事データ
            target_slides: 目標スライド枚数

        Returns:
            スライド生成結果
        """
        logger.info("=" * 60)
        logger.info("STEP 1: スライド生成")
        logger.info("=" * 60)
        logger.info(f"  目標スライド数: {target_slides}枚")

        slides_result = await generate_slides(article, target_slides)

        if slides_result.get("status") == "error":
            logger.error(f"  スライド生成失敗: {slides_result.get('error')}")
            return slides_result

        slides = slides_result.get("slides", [])
        slide_images = slides_result.get("slide_images", [])

        logger.info(f"  生成スライド数: {len(slides)}枚")
        logger.info(f"  生成画像数: {len(slide_images)}枚")

        # 各スライドの内容をログ
        for i, slide in enumerate(slides):
            logger.info(f"  スライド{i+1}: {slide.get('type', 'content')} - {slide.get('heading', '')[:30]}...")

        return slides_result

    async def _generate_narration_script(
        self,
        slides: List[Dict],
        title: str,
        topic: str,
        slide_duration: int
    ) -> str:
        """
        スライド内容からナレーションスクリプトを生成

        Args:
            slides: スライドデータ
            title: 記事タイトル
            topic: トピックID
            slide_duration: 各スライドの表示時間

        Returns:
            ナレーションスクリプト
        """
        client = self._get_gemini_client()

        # スライド情報を整理
        slides_info = "\n".join([
            f"スライド{i+1} ({s.get('type', 'content')}): {s.get('heading', '')} - {', '.join(s.get('points', []))}"
            for i, s in enumerate(slides)
        ])

        total_duration = len(slides) * slide_duration
        target_chars = total_duration * 4  # 1秒あたり約4文字

        prompt = f"""以下のプレゼンテーションスライドを解説するナレーションスクリプトを作成してください。

【タイトル】
{title}

【スライド構成】
{slides_info}

【スクリプト作成ルール】
1. 合計{total_duration}秒（約{target_chars}文字）で、各スライドを{slide_duration}秒程度で解説
2. 自然な話し言葉で、プレゼンテーション解説者のように
3. 構成:
   - タイトルスライド: 導入と期待感を醸成
   - コンテンツスライド: 各ポイントを簡潔に説明
   - エンディング: まとめと次のアクションを促す
4. スライド間の接続詞を適切に使用
5. 絵文字や記号は使用しない
6. 専門的だが親しみやすいトーンで

【出力形式】
ナレーションスクリプト全文のみを出力してください。"""

        result = await client.generate_content(
            prompt=prompt,
            model=client.MODEL_FLASH,
            temperature=0.7
        )
        return result.text.strip()

    async def _step2_generate_audio(
        self,
        slides: List[Dict],
        title: str,
        topic: str,
        voice: str,
        slide_duration: int
    ) -> Dict[str, Any]:
        """
        Step 2: 音声生成（VOICEPEAK優先、Gemini TTSフォールバック）

        優先順位:
        1. VOICEPEAK（ローカル環境で利用可能な場合）
        2. Gemini 2.5 Flash TTS（GitHub Actions等）

        Args:
            slides: スライドデータ
            title: 記事タイトル
            topic: トピックID
            voice: 音声タイプ
            slide_duration: 各スライドの表示時間

        Returns:
            音声生成結果（audio_dataを含む）
        """
        logger.info("=" * 60)
        logger.info("STEP 2: 音声生成（スライド内容からナレーション）")
        logger.info("=" * 60)
        logger.info(f"  スライド数: {len(slides)}枚")
        logger.info(f"  目標時間: {len(slides) * slide_duration}秒")

        # まずナレーションスクリプトを生成
        try:
            script = await self._generate_narration_script(
                slides=slides,
                title=title,
                topic=topic,
                slide_duration=slide_duration
            )
            logger.info(f"  スクリプト生成完了: {len(script)}文字")
            logger.info(f"  スクリプト冒頭: {script[:100]}...")
        except Exception as e:
            logger.error(f"  スクリプト生成失敗: {e}")
            return {
                "status": "error",
                "error": f"Script generation failed: {e}",
                "audio_data": None
            }

        # ===================================================
        # 音声生成（VOICEPEAK優先）
        # ===================================================
        audio_data = None
        tts_source = None

        # 1. VOICEPEAKを試行（ローカル環境）
        try:
            from lib.voicepeak_client import VoicepeakClient
            voicepeak = VoicepeakClient()

            if voicepeak.is_available:
                logger.info("  TTS: VOICEPEAKを使用")
                result = await voicepeak.generate_narration(
                    script=script,
                    topic=topic,
                    speed=110  # 少し速め
                )
                if result and result.audio_data:
                    audio_data = result.audio_data
                    tts_source = "voicepeak"
                    logger.info(f"  ✓ VOICEPEAK音声生成成功: {len(audio_data):,} bytes")
        except ImportError:
            logger.info("  VOICEPEAK client not available")
        except Exception as e:
            logger.warning(f"  VOICEPEAK失敗: {e}")

        # 2. Gemini TTSにフォールバック
        if audio_data is None:
            logger.info("  TTS: Gemini 2.5 Flash TTSを使用（フォールバック）")
            client = self._get_gemini_client()
            try:
                audio_result = await client.generate_audio(
                    text=script,
                    voice=voice
                )
                if audio_result and audio_result.audio_data:
                    audio_data = audio_result.audio_data
                    tts_source = "gemini"
                    logger.info(f"  ✓ Gemini TTS音声生成成功: {len(audio_data):,} bytes")
            except Exception as e:
                logger.warning(f"  Gemini TTS失敗: {e}")

        # ===================================================
        # 結果の返却
        # ===================================================
        if audio_data:
            # WAVヘッダーの検証
            is_wav = False
            if len(audio_data) >= 12:
                is_wav = audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'

            logger.info(f"  ✓ 音声生成完了 ({tts_source or 'unknown'})")
            logger.info(f"  音声サイズ: {len(audio_data):,} bytes")
            logger.info(f"  WAV形式: {'✓ 有効' if is_wav else '✗ 無効'}")

            return {
                "status": "success",
                "audio_data": audio_data,
                "script": script,
                "audio_size_bytes": len(audio_data),
                "voice": voice,
                "tts_source": tts_source
            }
        else:
            logger.warning("  ✗ 音声生成失敗（全TTSソース失敗）")
            return {
                "status": "failed",
                "error": "All TTS sources failed",
                "audio_data": None,
                "script": script
            }

    async def _step3_prepare_files(
        self,
        slide_images: List[str],
        audio_data: Optional[bytes],
        slides_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Step 3: ファイル配置（public/ディレクトリにファイルを配置）

        重要: AI生成画像を優先使用（PDF変換は不安定なため）

        Args:
            slide_images: スライド画像パスのリスト
            audio_data: 音声バイナリデータ（WAV形式）
            slides_result: スライド生成結果全体（代替画像パス用）

        Returns:
            配置されたファイル情報
        """
        logger.info("=" * 60)
        logger.info("STEP 3: ファイル配置")
        logger.info("=" * 60)

        result = {
            "audio_file": None,
            "slide_files": [],
            "slides_dir": None,
            "has_audio": False
        }

        # publicディレクトリを確保
        self.public_dir.mkdir(parents=True, exist_ok=True)

        # slidesディレクトリを作成（既存があれば削除）
        slides_dir = self.public_dir / "slides"
        if slides_dir.exists():
            shutil.rmtree(slides_dir)
        slides_dir.mkdir(parents=True, exist_ok=True)
        result["slides_dir"] = str(slides_dir)
        logger.info(f"  スライドディレクトリ: {slides_dir}")

        # ===========================================
        # 画像収集（優先順位: AI生成画像 > PDF変換画像）
        # ===========================================
        available_images = []

        # 1. まずAI生成画像を試す（generated_images - 常に存在するはず）
        if slides_result:
            generated = slides_result.get("generated_images", [])
            logger.info(f"  AI生成画像リスト: {len(generated)}件")
            for path in generated:
                if path:
                    p = Path(path)
                    if p.exists():
                        available_images.append(str(p))
                        logger.info(f"  ✓ AI生成画像: {p.name} ({p.stat().st_size:,} bytes)")
                    else:
                        logger.warning(f"  ✗ AI生成画像が存在しません: {path}")

        # 2. AI生成画像がない場合、slide_imagesを試す
        if len(available_images) == 0:
            logger.info(f"  AI生成画像なし。slide_imagesを確認...")
            logger.info(f"  slide_imagesリスト: {len(slide_images)}件")
            for path in slide_images:
                if path:
                    p = Path(path)
                    if p.exists():
                        available_images.append(str(p))
                        logger.info(f"  ✓ スライド画像: {p.name} ({p.stat().st_size:,} bytes)")
                    else:
                        logger.warning(f"  ✗ スライド画像が存在しません: {path}")

        logger.info(f"  利用可能な画像数: {len(available_images)}")

        if len(available_images) == 0:
            logger.error("  エラー: 利用可能な画像が1枚もありません！")
            # デバッグ情報を出力
            if slides_result:
                logger.error(f"  slides_result keys: {slides_result.keys()}")
                logger.error(f"  generated_images: {slides_result.get('generated_images', 'なし')}")
                logger.error(f"  slide_images: {slides_result.get('slide_images', 'なし')}")

        # スライド画像をコピー
        copied_count = 0
        for i, image_path in enumerate(available_images):
            try:
                source = Path(image_path)
                if source.exists():
                    dest = slides_dir / f"slide_{i+1:02d}.png"
                    shutil.copy(str(source), str(dest))
                    result["slide_files"].append(str(dest))
                    copied_count += 1
                    logger.info(f"  コピー完了: {source.name} → {dest.name}")
            except Exception as e:
                logger.error(f"  画像コピー失敗: {image_path} - {e}")

        logger.info(f"  コピーした画像数: {copied_count}/{len(available_images)}")

        # 音声ファイルを保存（より緩い検証）
        if audio_data:
            audio_path = self.public_dir / "narration.wav"
            try:
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"  音声ファイル保存: {audio_path} ({len(audio_data):,} bytes)")

                # WAVファイルの検証（ヘッダー確認のみ、サイズは問わない）
                file_size = audio_path.stat().st_size
                is_valid_audio = False

                # WAVヘッダーを確認（サイズに関係なく）
                with open(audio_path, "rb") as f:
                    header = f.read(12)
                    if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                        logger.info(f"  WAVファイル検証: 有効なWAVフォーマット ({file_size:,} bytes)")
                        is_valid_audio = True
                        if file_size < 10000:
                            logger.info(f"  注意: 音声ファイルは小さいですが有効です")
                    else:
                        logger.warning(f"  警告: WAVヘッダーが不正です (header: {header[:4]}...{header[8:12]})")

                if is_valid_audio:
                    result["audio_file"] = "narration.wav"
                    result["has_audio"] = True
                    logger.info(f"  ✓ 音声ファイル: 有効")
                else:
                    # ヘッダーが無効でもファイルは残す（Remotionで再検証）
                    logger.warning(f"  音声ファイル: ヘッダー無効だがファイルは保持")
                    result["audio_file"] = "narration.wav"
                    result["has_audio"] = True

            except Exception as e:
                logger.error(f"  音声ファイル保存失敗: {e}")
                import traceback
                logger.error(f"  トレースバック: {traceback.format_exc()}")
                result["audio_file"] = None
                result["has_audio"] = False
        else:
            logger.warning("  ✗ 音声データなし（無音動画になります）")
            result["audio_file"] = None
            result["has_audio"] = False

        return result

    def _normalize_slides_for_remotion(self, slides: List[Dict]) -> List[Dict]:
        """
        スライドデータをRemotionのSlideVideoコンポーネント用に正規化

        SlideVideo.tsxが期待する形式:
        - heading: string
        - subheading?: string
        - points?: string[]
        - type: "title" | "content" | "ending"
        - imageUrl?: string (自動生成されるのでオプション)
        - narrationText?: string
        """
        normalized = []
        for i, slide in enumerate(slides):
            # typeの正規化（title, content, ending のいずれかに）
            original_type = slide.get("type", "content")
            if i == 0:
                # 最初のスライドは必ずtitle
                slide_type = "title"
            elif i == len(slides) - 1:
                # 最後のスライドは必ずending
                slide_type = "ending"
            elif original_type in ["title", "ending"]:
                # 中間スライドでtitleやendingが指定されていたらcontentに
                slide_type = "content"
            else:
                slide_type = "content"

            normalized_slide = {
                "heading": slide.get("heading", f"スライド {i+1}"),
                "subheading": slide.get("subheading", ""),
                "points": slide.get("points", []),
                "type": slide_type
            }

            # narrationTextがあれば追加
            if slide.get("narrationText"):
                normalized_slide["narrationText"] = slide["narrationText"]

            normalized.append(normalized_slide)
            logger.info(f"  スライド{i+1}: type='{original_type}' → '{slide_type}', heading='{normalized_slide['heading'][:30]}...'")

        return normalized

    def _file_to_data_url(self, file_path: Path, mime_type: str = None) -> Optional[str]:
        """
        ファイルをBase64データURLに変換（DailyInstagramの方式）

        Args:
            file_path: ファイルパス
            mime_type: MIMEタイプ（指定なしの場合は拡張子から推測）

        Returns:
            Base64データURL または None
        """
        try:
            if not file_path.exists():
                logger.warning(f"ファイルが存在しません: {file_path}")
                return None

            # MIMEタイプを推測
            if mime_type is None:
                ext = file_path.suffix.lower()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".wav": "audio/wav",
                    ".mp3": "audio/mpeg",
                }
                mime_type = mime_types.get(ext, "application/octet-stream")

            # Base64エンコード
            import base64
            with open(file_path, "rb") as f:
                data = f.read()

            base64_data = base64.b64encode(data).decode("utf-8")
            data_url = f"data:{mime_type};base64,{base64_data}"

            logger.info(f"  Base64変換: {file_path.name} ({len(data):,} bytes → {len(data_url):,} chars)")
            return data_url

        except Exception as e:
            logger.error(f"  Base64変換エラー: {file_path} - {e}")
            return None

    async def _step4_render_video(
        self,
        slides: List[Dict],
        output_path: str,
        topic: str,
        audio_file: Optional[str],
        slide_duration: int,
        slide_image_paths: List[str] = None,
        audio_data: bytes = None
    ) -> bool:
        """
        Step 4: Remotionでスライド動画をレンダリング

        DailyInstagramと同様にBase64データURLを使用して
        ファイルシステムの問題を回避する

        Args:
            slides: スライドデータ
            output_path: 出力パス
            topic: トピックID
            audio_file: 音声ファイル名（publicディレクトリ内）- フォールバック用
            slide_duration: 各スライドの表示時間
            slide_image_paths: スライド画像のパスリスト（Base64変換用）
            audio_data: 音声バイナリデータ（Base64変換用）

        Returns:
            成功かどうか
        """
        logger.info("=" * 60)
        logger.info("STEP 4: 動画レンダリング（Remotion）")
        logger.info("=" * 60)

        # スライドデータをRemotionの期待する形式に正規化
        logger.info("スライドデータを正規化中...")
        normalized_slides = self._normalize_slides_for_remotion(slides)

        # ===================================================
        # Base64データURL変換（DailyInstagramの方式）
        # ===================================================
        logger.info("Base64データURL変換中...")

        # スライド画像をBase64に変換
        slide_images_base64 = []
        if slide_image_paths:
            for img_path in slide_image_paths:
                if img_path:
                    data_url = self._file_to_data_url(Path(img_path))
                    if data_url:
                        slide_images_base64.append(data_url)
                    else:
                        slide_images_base64.append(None)
                else:
                    slide_images_base64.append(None)

        # 音声をBase64に変換
        audio_data_url = None
        if audio_data:
            import base64
            base64_audio = base64.b64encode(audio_data).decode("utf-8")
            audio_data_url = f"data:audio/wav;base64,{base64_audio}"
            logger.info(f"  音声Base64変換: {len(audio_data):,} bytes → {len(audio_data_url):,} chars")
        elif audio_file:
            # フォールバック: publicディレクトリのファイルを変換
            audio_path = self.public_dir / audio_file
            audio_data_url = self._file_to_data_url(audio_path, "audio/wav")

        logger.info(f"  Base64画像数: {len([x for x in slide_images_base64 if x])}/{len(slide_images_base64)}")
        logger.info(f"  Base64音声: {'あり' if audio_data_url else 'なし'}")

        # propsを準備（Base64データURLを含む）
        props = {
            "title": normalized_slides[0].get("heading", "Presentation") if normalized_slides else "Presentation",
            "slides": normalized_slides,
            "topic": topic,
            "authorName": "if(塾) Blog",
            "audioUrl": audio_file,  # フォールバック用
            "audioDataUrl": audio_data_url,  # Base64音声（優先）
            "slideImagePrefix": "slide_",
            "slideDuration": slide_duration,
            "slideImages": slide_images_base64  # Base64画像（優先）
        }

        logger.info(f"  タイトル: {props['title']}")
        logger.info(f"  スライド数: {len(slides)}")
        logger.info(f"  各スライド: {slide_duration}秒")
        logger.info(f"  音声: {'Base64' if audio_data_url else (audio_file or 'なし')}")
        logger.info(f"  出力先: {output_path}")

        # propsをJSONファイルに保存
        props_file = self.remotion_dir / "props_slides.json"
        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        logger.info(f"  Props保存: {props_file}")

        render_script = self.remotion_dir / "render.mjs"
        cmd = [
            "node",
            str(render_script),
            "SlideVideo",
            output_path,
            str(props_file)
        ]

        logger.info(f"  レンダリングコマンド: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.remotion_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if stdout:
                for line in stdout.decode().split('\n'):
                    if line.strip():
                        logger.info(f"  [Remotion] {line}")

            if process.returncode == 0:
                logger.info(f"  レンダリング成功!")
                return True
            else:
                logger.error(f"  レンダリング失敗:")
                for line in stderr.decode().split('\n'):
                    if line.strip():
                        logger.error(f"  [Remotion Error] {line}")
                return False

        except Exception as e:
            logger.error(f"  レンダリングエラー: {e}")
            return False
        finally:
            if props_file.exists():
                props_file.unlink()

    def _cleanup_public_files(self):
        """public/ディレクトリをクリーンアップ"""
        logger.info("クリーンアップ中...")

        for item in ["narration.wav"]:
            path = self.public_dir / item
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    logger.warning(f"  クリーンアップ失敗: {e}")

        slides_dir = self.public_dir / "slides"
        if slides_dir.exists():
            try:
                shutil.rmtree(slides_dir)
            except Exception as e:
                logger.warning(f"  Slidesディレクトリ削除失敗: {e}")

    async def generate_slide_video(
        self,
        article: Dict,
        target_slides: int = 6,
        slide_duration: int = 5
    ) -> Dict[str, Any]:
        """
        記事からスライド動画を生成

        処理フロー:
        Step 1: スライド生成 → Step 2: 音声生成 → Step 3: ファイル配置 → Step 4: 動画レンダリング

        Args:
            article: 記事データ
            target_slides: 目標スライド枚数（デフォルト6枚 = 30秒）
            slide_duration: 各スライドの表示時間（秒）

        Returns:
            生成結果
        """
        timestamp = get_timestamp_jst()
        topic = article.get("topic_id") or article.get("topic", "ai_tools")
        title = article.get("title", "Untitled")

        # 30秒以内に制限（最大6スライド x 5秒 = 30秒）
        MAX_VIDEO_DURATION = 30
        max_slides = MAX_VIDEO_DURATION // slide_duration
        target_slides = min(target_slides, max_slides)

        logger.info("=" * 60)
        logger.info("スライドベース動画生成開始")
        logger.info("=" * 60)
        logger.info(f"タイトル: {title}")
        logger.info(f"トピック: {topic}")
        logger.info(f"目標スライド数: {target_slides}枚")
        logger.info(f"各スライド表示時間: {slide_duration}秒")
        logger.info(f"最大動画長: {MAX_VIDEO_DURATION}秒")

        result = {
            "status": "in_progress",
            "topic": topic,
            "generated_at": timestamp,
            "target_duration": target_slides * slide_duration
        }

        # 依存関係チェック
        deps = self._check_dependencies()
        logger.info(f"依存関係: {deps}")
        if not deps.get("node"):
            result["status"] = "error"
            result["error"] = "Node.js is not available"
            return result

        try:
            # ========================================
            # Step 1: スライド生成
            # ========================================
            slides_result = await self._step1_generate_slides(article, target_slides)

            if slides_result.get("status") == "error":
                result["status"] = "error"
                result["error"] = slides_result.get("error")
                return result

            slides = slides_result.get("slides", [])
            slide_images = slides_result.get("slide_images", [])

            # スライド数を30秒以内に制限
            if len(slides) > max_slides:
                logger.info(f"スライドを{len(slides)}枚から{max_slides}枚に制限")
                slides = slides[:max_slides]
                slide_images = slide_images[:max_slides]

            result["slides"] = slides_result

            # ========================================
            # Step 2: 音声生成（スライド内容を元に）
            # ========================================
            voice = TOPIC_VOICES.get(topic, "default")
            audio_result = await self._step2_generate_audio(
                slides=slides,
                title=title,
                topic=topic,
                voice=voice,
                slide_duration=slide_duration
            )

            audio_data = audio_result.get("audio_data")
            result["narration"] = {
                "status": audio_result.get("status"),
                "script": audio_result.get("script"),
                "audio_size_bytes": audio_result.get("audio_size_bytes"),
                "voice": voice
            }

            # ========================================
            # Step 3: ファイル配置
            # ========================================
            public_files = await self._step3_prepare_files(
                slide_images,
                audio_data,
                slides_result  # バックアップ画像パス用
            )

            # ========================================
            # Step 4: 動画レンダリング
            # ========================================
            videos_dir = self.output_dir / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)
            video_path = videos_dir / f"slide_video_{timestamp}_{topic}.mp4"

            # スライド画像パスを取得（Base64変換用）
            # 優先順位: generated_images > slide_files > slide_images
            slide_image_paths = []
            if slides_result.get("generated_images"):
                slide_image_paths = slides_result.get("generated_images", [])
            elif public_files.get("slide_files"):
                slide_image_paths = public_files.get("slide_files", [])
            else:
                slide_image_paths = slide_images

            render_success = await self._step4_render_video(
                slides=slides,
                output_path=str(video_path),
                topic=topic,
                audio_file=public_files.get("audio_file"),
                slide_duration=slide_duration,
                slide_image_paths=slide_image_paths,  # Base64変換用
                audio_data=audio_data  # Base64変換用
            )

            # 結果の設定
            if render_success and video_path.exists():
                actual_duration = len(slides) * slide_duration
                result["video"] = {
                    "status": "success",
                    "path": str(video_path),
                    "resolution": "1920x1080",
                    "duration": actual_duration,
                    "size_bytes": video_path.stat().st_size,
                    "has_audio": public_files.get("has_audio", False),
                    "slide_count": len(slides)
                }
                result["status"] = "success"

                logger.info("=" * 60)
                logger.info("動画生成完了!")
                logger.info("=" * 60)
                logger.info(f"  動画パス: {video_path}")
                logger.info(f"  動画長: {actual_duration}秒")
                logger.info(f"  スライド数: {len(slides)}枚")
                logger.info(f"  音声: {'あり' if public_files.get('has_audio') else 'なし'}")
                logger.info(f"  ファイルサイズ: {video_path.stat().st_size:,} bytes")
            else:
                result["video"] = {"status": "error", "error": "Render failed"}
                result["status"] = "error"
                logger.error("動画レンダリング失敗")

        except Exception as e:
            logger.error(f"動画生成エラー: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        finally:
            # クリーンアップ
            self._cleanup_public_files()

        return result


async def generate_slide_video(
    article: Dict,
    target_slides: int = 6,
    slide_duration: int = 5
) -> Dict[str, Any]:
    """
    スライド動画生成のエントリーポイント

    処理フロー:
    1. スライド生成（記事からスライド構成 + 画像を生成）
    2. 音声生成（スライド内容からTTSナレーション）
    3. ファイル配置（スライド画像 + 音声をpublic/に配置）
    4. 動画レンダリング（Remotionで統合）

    Args:
        article: 記事データ
        target_slides: 目標スライド枚数（デフォルト6枚 = 30秒）
        slide_duration: 各スライドの表示時間

    Returns:
        生成結果
    """
    generator = SlideVideoGenerator()
    return await generator.generate_slide_video(
        article=article,
        target_slides=target_slides,
        slide_duration=slide_duration
    )


def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Generate slide-based video from blog article"
    )
    parser.add_argument("--article-file", "-f", type=str,
                        help="Path to article JSON file")
    parser.add_argument("--title", "-t", type=str,
                        help="Article title (if not using file)")
    parser.add_argument("--content", "-c", type=str,
                        help="Article content (if not using file)")
    parser.add_argument("--topic", type=str, default="ai_tools",
                        help="Topic ID")
    parser.add_argument("--slides", "-n", type=int, default=6,
                        help="Target slide count (max 6 for 30s video)")
    parser.add_argument("--duration", "-d", type=int, default=5,
                        help="Slide duration in seconds")
    parser.add_argument("--output", "-o", type=str,
                        help="Output directory")

    args = parser.parse_args()

    # 記事データの読み込み
    if args.article_file:
        article = json.loads(Path(args.article_file).read_text(encoding="utf-8"))
    else:
        if not args.title or not args.content:
            print("Error: --article-file or both --title and --content required")
            sys.exit(1)
        article = {
            "title": args.title,
            "content": args.content,
            "topic_id": args.topic
        }

    result = asyncio.run(generate_slide_video(
        article=article,
        target_slides=args.slides,
        slide_duration=args.duration
    ))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
