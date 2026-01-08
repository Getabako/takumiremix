#!/usr/bin/env python3
"""
動画生成ワークフローのテストスクリプト

使用方法:
    python test_workflow.py
    python test_workflow.py --quick  # 簡易テスト（2シーンのみ）
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# 環境変数読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Setup] Loaded .env from: {env_path}")
except ImportError:
    print("[Setup] python-dotenv not installed, using environment variables")


def check_environment():
    """環境をチェック"""
    print("\n" + "=" * 60)
    print("Environment Check")
    print("=" * 60)

    # API Key
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"  [OK] API Key: {masked}")
    else:
        print("  [NG] API Key: Not found")
        print("       Set GOOGLE_AI_API_KEY or GOOGLE_API_KEY environment variable")
        return False

    # Dependencies
    try:
        from google import genai
        print("  [OK] google-generativeai")
    except ImportError:
        print("  [NG] google-generativeai not installed")
        return False

    try:
        import moviepy
        print("  [OK] moviepy")
    except ImportError:
        print("  [NG] moviepy not installed")
        return False

    try:
        from PIL import Image
        print("  [OK] Pillow")
    except ImportError:
        print("  [NG] Pillow not installed")
        return False

    return True


async def run_test(quick: bool = False):
    """テストを実行"""
    from main import VideoGeneratorWorkflow

    # テスト用ブログ記事
    test_article = """
# AIが変える教育の未来

近年、人工知能（AI）技術の急速な発展により、教育分野にも大きな変革が訪れています。

## パーソナライズド学習

AIを活用することで、一人ひとりの学習ペースや理解度に合わせた個別最適化された学習体験が可能になります。
従来の一斉授業では難しかった、生徒個人に寄り添った指導が実現できます。

## 教師の負担軽減

採点や事務作業の自動化により、教師は本来の仕事である「生徒と向き合う時間」を増やすことができます。
AIは教師の代わりではなく、教師を支援するパートナーとして機能します。

## 今後の展望

2025年以降、さらに多くの学校でAI活用が進むと予想されています。
テクノロジーと人間の強みを組み合わせた、新しい教育の形が生まれつつあります。
"""

    print("\n" + "=" * 60)
    print("Running Video Generation Test")
    print("=" * 60)

    num_scenes = 2 if quick else 4
    print(f"Mode: {'Quick (2 scenes)' if quick else 'Standard (4 scenes)'}")

    workflow = VideoGeneratorWorkflow("test_output")

    try:
        result = await workflow.generate_from_text(
            test_article,
            output_name="test_video",
            num_scenes=num_scenes,
            voice="default"
        )

        print("\n" + "=" * 60)
        print("Test Results")
        print("=" * 60)
        print(f"  [OK] Video generated: {result}")
        print(f"  [OK] Scenes: {num_scenes}")

        # ファイルサイズ確認
        if Path(result).exists():
            size_mb = Path(result).stat().st_size / (1024 * 1024)
            print(f"  [OK] File size: {size_mb:.2f} MB")

        return True

    except Exception as e:
        print(f"\n  [NG] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test video generation workflow")
    parser.add_argument("--quick", action="store_true", help="Quick test with 2 scenes")
    parser.add_argument("--check-only", action="store_true", help="Only check environment")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Gemini Video Generator - Test Suite")
    print("=" * 60)

    # 環境チェック
    if not check_environment():
        print("\n[NG] Environment check failed. Please fix the issues above.")
        sys.exit(1)

    if args.check_only:
        print("\n[OK] Environment check passed!")
        sys.exit(0)

    # テスト実行
    success = asyncio.run(run_test(quick=args.quick))

    if success:
        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[NG] Some tests failed.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
