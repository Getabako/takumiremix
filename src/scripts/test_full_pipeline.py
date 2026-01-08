#!/usr/bin/env python3
"""
完全なパイプラインテストスクリプト

以下をテスト:
1. 環境設定（API キー、VOICEPEAK）
2. Gemini TTS
3. VOICEPEAK TTS
4. 動画レンダリング（音声付き）
5. フルパイプライン統合

使用方法:
    python test_full_pipeline.py
    python test_full_pipeline.py --with-audio  # 音声生成も含む
"""
import asyncio
import argparse
import json
import base64
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import sys

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Setup] Loaded .env from: {env_path}")
    else:
        print(f"[Setup] No .env file found at: {env_path}")
except ImportError:
    print("[Setup] python-dotenv not installed, using environment variables directly")

sys.path.insert(0, str(Path(__file__).parent.parent))


class PipelineTester:
    """パイプラインテスター"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.remotion_dir = self.project_root / "remotion"
        self.output_dir = self.project_root / "output"
        self.results: Dict[str, Any] = {}

    def test_environment(self) -> bool:
        """環境設定をテスト"""
        print("\n" + "=" * 60)
        print("TEST 1: 環境設定")
        print("=" * 60)

        # GOOGLE_AI_API_KEY
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if api_key:
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(f"  [OK] GOOGLE_AI_API_KEY: {masked_key}")
            self.results["api_key"] = True
        else:
            print("  [NG] GOOGLE_AI_API_KEY: 未設定")
            print("       .env ファイルに GOOGLE_AI_API_KEY=your_key を追加してください")
            self.results["api_key"] = False

        # VOICEPEAK
        voicepeak_paths = [
            os.getenv("VOICEPEAK_PATH"),
            r"C:\Program Files\VOICEPEAK\voicepeak.exe",
            r"C:\Program Files (x86)\VOICEPEAK\voicepeak.exe",
        ]
        voicepeak_found = None
        for path in voicepeak_paths:
            if path and Path(path).exists():
                voicepeak_found = path
                break

        if voicepeak_found:
            print(f"  [OK] VOICEPEAK: {voicepeak_found}")
            self.results["voicepeak"] = voicepeak_found
        else:
            print("  [NG] VOICEPEAK: 未インストール")
            print("       VOICEPEAKダウンローダーを実行してインストールしてください")
            self.results["voicepeak"] = None

        # Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  [OK] Node.js: {result.stdout.strip()}")
                self.results["nodejs"] = True
            else:
                print("  [NG] Node.js: エラー")
                self.results["nodejs"] = False
        except Exception as e:
            print(f"  [NG] Node.js: {e}")
            self.results["nodejs"] = False

        # Remotion packages
        remotion_bundler = self.remotion_dir / "node_modules" / "@remotion" / "bundler"
        if remotion_bundler.exists():
            print(f"  [OK] Remotion: インストール済み")
            self.results["remotion"] = True
        else:
            print("  [NG] Remotion: 未インストール")
            print("       cd remotion && npm install を実行してください")
            self.results["remotion"] = False

        return self.results.get("api_key", False) or self.results.get("voicepeak") is not None

    async def test_gemini_tts(self) -> bool:
        """Gemini TTSをテスト"""
        print("\n" + "=" * 60)
        print("TEST 2: Gemini TTS")
        print("=" * 60)

        if not self.results.get("api_key"):
            print("  [SKIP] API キーが未設定のためスキップ")
            return False

        try:
            from lib.gemini_client import GeminiClient

            client = GeminiClient()
            print("  GeminiClient初期化: OK")

            # 短いテスト音声を生成
            print("  音声生成中...")
            result = await client.generate_audio(
                text="これはテスト音声です。",
                voice="default"
            )

            if result and result.audio_data:
                # WAVヘッダーを確認
                is_wav = (
                    len(result.audio_data) >= 12
                    and result.audio_data[:4] == b'RIFF'
                    and result.audio_data[8:12] == b'WAVE'
                )
                print(f"  [OK] Gemini TTS: {len(result.audio_data):,} bytes")
                print(f"       WAV形式: {'有効' if is_wav else '無効'}")
                print(f"       推定長: ~{result.duration_seconds:.1f}秒")
                self.results["gemini_tts"] = result.audio_data
                return True
            else:
                print("  [NG] Gemini TTS: 音声データなし")
                return False

        except Exception as e:
            print(f"  [NG] Gemini TTS: {e}")
            return False

    async def test_voicepeak_tts(self) -> bool:
        """VOICEPEAK TTSをテスト"""
        print("\n" + "=" * 60)
        print("TEST 3: VOICEPEAK TTS")
        print("=" * 60)

        if not self.results.get("voicepeak"):
            print("  [SKIP] VOICEPEAKが未インストールのためスキップ")
            return False

        try:
            from lib.voicepeak_client import VoicepeakClient

            client = VoicepeakClient()

            if not client.is_available:
                print("  [NG] VOICEPEAK: 利用不可")
                return False

            print(f"  VOICEPEAKパス: {client.voicepeak_path}")
            print("  音声生成中...")

            result = await client.generate_audio(
                text="これはボイスピークによるテスト音声です。",
                narrator="default",
                speed=100
            )

            if result and result.audio_data:
                print(f"  [OK] VOICEPEAK TTS: {len(result.audio_data):,} bytes")
                print(f"       推定長: ~{result.duration_seconds:.1f}秒")
                self.results["voicepeak_tts"] = result.audio_data
                return True
            else:
                print("  [NG] VOICEPEAK TTS: 音声データなし")
                return False

        except Exception as e:
            print(f"  [NG] VOICEPEAK TTS: {e}")
            return False

    def test_video_render_with_audio(self) -> bool:
        """音声付き動画レンダリングをテスト"""
        print("\n" + "=" * 60)
        print("TEST 4: 動画レンダリング（音声付き）")
        print("=" * 60)

        if not self.results.get("remotion"):
            print("  [SKIP] Remotionが未インストールのためスキップ")
            return False

        # 音声データを取得（Gemini優先、なければVOICEPEAK）
        audio_data = self.results.get("gemini_tts") or self.results.get("voicepeak_tts")
        audio_data_url = None

        if audio_data:
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            audio_data_url = f"data:audio/wav;base64,{audio_base64}"
            print(f"  音声データ: {len(audio_data):,} bytes")
        else:
            print("  音声データ: なし（無音で生成）")

        # テストスライド画像を取得
        slide_dir = self.output_dir / "slides"
        latest_slide_dir = None
        if slide_dir.exists():
            subdirs = sorted([d for d in slide_dir.iterdir() if d.is_dir()], reverse=True)
            if subdirs:
                latest_slide_dir = subdirs[0] / "images"

        slide_images_base64 = []
        if latest_slide_dir and latest_slide_dir.exists():
            for i in range(1, 7):
                img_path = latest_slide_dir / f"slide_{i:02d}.png"
                if img_path.exists():
                    with open(img_path, 'rb') as f:
                        data = f.read()
                    b64 = base64.b64encode(data).decode('utf-8')
                    slide_images_base64.append(f"data:image/png;base64,{b64}")
                    print(f"  スライド画像 {i}: {len(data):,} bytes")

        # Props作成
        slides = [
            {"type": "title", "heading": "パイプラインテスト", "subheading": "音声付き動画生成"},
            {"type": "content", "heading": "テスト内容", "points": ["環境設定", "TTS生成", "動画レンダリング"]},
            {"type": "content", "heading": "使用技術", "points": ["Gemini API", "Remotion", "Base64エンコード"]},
            {"type": "ending", "heading": "テスト完了", "subheading": "成功"}
        ]

        # スライド画像が足りない場合は調整
        while len(slide_images_base64) < len(slides):
            slide_images_base64.append(None)
        slide_images_base64 = slide_images_base64[:len(slides)]

        props = {
            "title": "パイプラインテスト",
            "slides": slides,
            "topic": "ai_tools",
            "authorName": "Test",
            "audioDataUrl": audio_data_url,
            "slideImagePrefix": "test_",
            "slideDuration": 3,
            "slideImages": [img for img in slide_images_base64 if img]
        }

        # Props保存
        props_file = self.remotion_dir / "test_pipeline_props.json"
        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        print(f"  Props: {props_file.stat().st_size:,} bytes")

        # レンダリング
        output_path = self.output_dir / "videos" / "test_pipeline_video.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("  レンダリング開始...")
        try:
            result = subprocess.run(
                [
                    "node",
                    str(self.remotion_dir / "render.mjs"),
                    "SlideVideo",
                    str(output_path),
                    str(props_file)
                ],
                cwd=str(self.remotion_dir),
                capture_output=True,
                text=True,
                timeout=300
            )

            # クリーンアップ
            if props_file.exists():
                props_file.unlink()

            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                print(f"  [OK] 動画生成成功: {file_size:,} bytes")
                print(f"       出力: {output_path}")
                self.results["video_with_audio"] = str(output_path)
                return True
            else:
                print(f"  [NG] 動画生成失敗")
                if result.stderr:
                    for line in result.stderr.split('\n')[:10]:
                        if line.strip():
                            print(f"       {line}")
                return False

        except subprocess.TimeoutExpired:
            print("  [NG] タイムアウト")
            return False
        except Exception as e:
            print(f"  [NG] エラー: {e}")
            return False

    def print_summary(self):
        """テスト結果のサマリーを表示"""
        print("\n" + "=" * 60)
        print("テスト結果サマリー")
        print("=" * 60)

        checks = [
            ("API キー", self.results.get("api_key", False)),
            ("VOICEPEAK", self.results.get("voicepeak") is not None),
            ("Node.js", self.results.get("nodejs", False)),
            ("Remotion", self.results.get("remotion", False)),
            ("Gemini TTS", self.results.get("gemini_tts") is not None),
            ("VOICEPEAK TTS", self.results.get("voicepeak_tts") is not None),
            ("動画生成", self.results.get("video_with_audio") is not None),
        ]

        all_critical_ok = True
        for name, status in checks:
            icon = "[OK]" if status else "[NG]"
            print(f"  {icon} {name}")
            if name in ["Remotion", "動画生成"] and not status:
                all_critical_ok = False

        # TTS状況
        has_tts = self.results.get("gemini_tts") or self.results.get("voicepeak_tts")
        print()
        if has_tts:
            tts_source = "Gemini TTS" if self.results.get("gemini_tts") else "VOICEPEAK"
            print(f"  音声生成: {tts_source} を使用")
        else:
            print("  音声生成: 利用不可（動画は無音で生成されます）")

        print()
        if all_critical_ok:
            print("  システム状態: 正常")
        else:
            print("  システム状態: 要修正")

        # 出力動画
        if self.results.get("video_with_audio"):
            print(f"\n  生成動画: {self.results['video_with_audio']}")


async def main():
    parser = argparse.ArgumentParser(description="パイプラインテスト")
    parser.add_argument("--with-audio", action="store_true", help="音声生成テストを含む")
    parser.add_argument("--skip-video", action="store_true", help="動画生成をスキップ")
    args = parser.parse_args()

    tester = PipelineTester()

    # 環境テスト
    tester.test_environment()

    # 音声テスト（オプション）
    if args.with_audio:
        await tester.test_gemini_tts()
        await tester.test_voicepeak_tts()

    # 動画テスト
    if not args.skip_video:
        tester.test_video_render_with_audio()

    # サマリー
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
