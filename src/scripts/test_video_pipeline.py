#!/usr/bin/env python3
"""
動画生成パイプラインのテストスクリプト

テスト内容:
1. TTS音声生成が動作するか
2. 画像生成が動作するか
3. Remotionレンダリングが動作するか
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.gemini_client import GeminiClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_tts():
    """TTS音声生成をテスト"""
    logger.info("=" * 60)
    logger.info("TEST 1: TTS音声生成")
    logger.info("=" * 60)

    try:
        client = GeminiClient()

        # 短いテキストでテスト
        test_text = "こんにちは。これはテスト音声です。動画生成システムの音声合成機能をテストしています。"

        logger.info(f"テキスト: {test_text}")
        logger.info(f"文字数: {len(test_text)}文字")

        result = await client.generate_audio(
            text=test_text,
            voice="default"
        )

        if result and result.audio_data:
            audio_size = len(result.audio_data)
            logger.info(f"✓ 音声生成成功!")
            logger.info(f"  サイズ: {audio_size:,} bytes")
            logger.info(f"  推定時間: {result.duration_seconds:.1f}秒")

            # WAVヘッダー確認
            if audio_size >= 12:
                is_wav = result.audio_data[:4] == b'RIFF' and result.audio_data[8:12] == b'WAVE'
                logger.info(f"  WAV形式: {'✓ 有効' if is_wav else '✗ 無効'}")

            # テストファイルに保存
            test_audio_path = Path(__file__).parent.parent.parent / "output" / "test_audio.wav"
            test_audio_path.parent.mkdir(parents=True, exist_ok=True)
            with open(test_audio_path, "wb") as f:
                f.write(result.audio_data)
            logger.info(f"  保存先: {test_audio_path}")

            return True
        else:
            logger.error("✗ 音声データが空です")
            return False

    except Exception as e:
        logger.error(f"✗ TTS生成エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_image_generation():
    """画像生成をテスト"""
    logger.info("=" * 60)
    logger.info("TEST 2: 画像生成")
    logger.info("=" * 60)

    try:
        client = GeminiClient()

        prompt = """Generate a simple 16:9 LANDSCAPE anime-style illustration.
        Theme: Education and learning
        Style: Modern Japanese anime, clean lines
        Content: A student studying at a desk with books
        Colors: Blue and green tones, dark navy background
        NO text or letters in the image."""

        logger.info(f"プロンプト: {prompt[:100]}...")

        result = await client.generate_image(prompt)

        if result and result.images:
            logger.info(f"✓ 画像生成成功!")
            logger.info(f"  画像数: {len(result.images)}")

            # テストファイルに保存
            test_image_path = Path(__file__).parent.parent.parent / "output" / "test_image.png"
            test_image_path.parent.mkdir(parents=True, exist_ok=True)

            image_data = result.images[0]
            if isinstance(image_data, bytes):
                with open(test_image_path, "wb") as f:
                    f.write(image_data)
                logger.info(f"  サイズ: {len(image_data):,} bytes")
            elif isinstance(image_data, dict) and "data" in image_data:
                import base64
                data = image_data["data"]
                if isinstance(data, str):
                    data = base64.b64decode(data)
                with open(test_image_path, "wb") as f:
                    f.write(data)
                logger.info(f"  サイズ: {len(data):,} bytes")

            logger.info(f"  保存先: {test_image_path}")
            return True
        else:
            logger.error("✗ 画像データが空です")
            return False

    except Exception as e:
        logger.error(f"✗ 画像生成エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_slide_narration():
    """スライドナレーション生成をテスト"""
    logger.info("=" * 60)
    logger.info("TEST 3: スライドナレーション生成")
    logger.info("=" * 60)

    try:
        client = GeminiClient()

        # テスト用スライドデータ
        test_slides = [
            {"type": "title", "heading": "AIの最新動向", "subheading": "2025年のトレンド"},
            {"type": "content", "heading": "生成AIの進化", "points": ["テキスト生成", "画像生成"]},
            {"type": "ending", "heading": "まとめ", "subheading": "詳しくはブログで"}
        ]

        logger.info(f"スライド数: {len(test_slides)}")

        result = await client.generate_slide_narration(
            slides=test_slides,
            title="AIの最新動向",
            topic="ai_tools",
            voice="default",
            slide_duration=5
        )

        if result.get("status") == "success":
            logger.info(f"✓ ナレーション生成成功!")
            logger.info(f"  スクリプト長: {len(result.get('script', ''))}文字")
            logger.info(f"  音声サイズ: {result.get('audio_size_bytes', 0):,} bytes")
            logger.info(f"  スクリプト冒頭: {result.get('script', '')[:100]}...")

            # 音声を保存
            audio_data = result.get("audio_data")
            if audio_data:
                test_narration_path = Path(__file__).parent.parent.parent / "output" / "test_narration.wav"
                with open(test_narration_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"  保存先: {test_narration_path}")

            return True
        else:
            logger.error(f"✗ ナレーション生成失敗: {result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"✗ ナレーション生成エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """メインテスト実行"""
    logger.info("=" * 60)
    logger.info("動画生成パイプライン テスト開始")
    logger.info("=" * 60)

    results = {
        "tts": False,
        "image": False,
        "narration": False
    }

    # TTS テスト
    results["tts"] = await test_tts()

    # 画像生成テスト
    results["image"] = await test_image_generation()

    # ナレーション生成テスト
    results["narration"] = await test_slide_narration()

    # 結果サマリー
    logger.info("=" * 60)
    logger.info("テスト結果サマリー")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n全テスト合格！動画生成の準備が整っています。")
    else:
        logger.error("\n一部テストが失敗しました。ログを確認してください。")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
