#!/usr/bin/env python3
"""
動画生成パイプライン診断スクリプト

問題箇所を特定するための詳細な診断を実行:
1. 画像生成の確認
2. Base64変換の確認
3. JSONファイルの確認
4. Remotionへの受け渡しの確認
"""
import asyncio
import json
import logging
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_base64_data_url(data_url: str, name: str) -> bool:
    """Base64データURLの検証"""
    if not data_url:
        logger.error(f"  {name}: NULL or empty")
        return False

    if not isinstance(data_url, str):
        logger.error(f"  {name}: Not a string (type={type(data_url)})")
        return False

    if not data_url.startswith('data:'):
        logger.error(f"  {name}: Does not start with 'data:'")
        return False

    try:
        # Parse data URL
        header, data = data_url.split(',', 1)
        mime_match = header.replace('data:', '').replace(';base64', '')

        # Decode Base64
        decoded = base64.b64decode(data)

        logger.info(f"  {name}: VALID")
        logger.info(f"    - MIME: {mime_match}")
        logger.info(f"    - Base64 length: {len(data):,} chars")
        logger.info(f"    - Decoded size: {len(decoded):,} bytes")
        return True
    except Exception as e:
        logger.error(f"  {name}: INVALID - {e}")
        return False


async def run_diagnostic():
    """診断を実行"""
    logger.info("=" * 60)
    logger.info("動画生成パイプライン診断")
    logger.info("=" * 60)

    # テスト用記事データ
    test_article = {
        "title": "テスト動画生成 - 診断用",
        "content": "これはテスト用の記事です。動画生成パイプラインの診断を行います。",
        "topic_id": "ai_tools"
    }

    project_root = Path(__file__).parent.parent.parent
    remotion_dir = project_root / "remotion"
    public_dir = remotion_dir / "public"
    output_dir = project_root / "output"

    logger.info(f"Project root: {project_root}")
    logger.info(f"Remotion dir: {remotion_dir}")
    logger.info(f"Public dir: {public_dir}")

    # ==============================
    # Step 1: 既存の画像ファイルを確認
    # ==============================
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: 既存ファイルの確認")
    logger.info("=" * 60)

    slides_dir = public_dir / "slides"
    if slides_dir.exists():
        images = list(slides_dir.glob("*.png"))
        logger.info(f"public/slides/ に {len(images)} 個の画像あり")
        for img in images[:5]:
            logger.info(f"  - {img.name}: {img.stat().st_size:,} bytes")
    else:
        logger.warning("public/slides/ ディレクトリが存在しません")

    narration_file = public_dir / "narration.wav"
    if narration_file.exists():
        logger.info(f"narration.wav: {narration_file.stat().st_size:,} bytes")
    else:
        logger.warning("narration.wav が存在しません")

    # ==============================
    # Step 2: 画像のBase64変換テスト
    # ==============================
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Base64変換テスト")
    logger.info("=" * 60)

    # テスト用画像を探す
    test_images = []

    # outputディレクトリの画像
    output_images = output_dir / "images"
    if output_images.exists():
        test_images.extend(list(output_images.glob("*.png"))[:3])

    # slidesディレクトリの画像
    if slides_dir.exists():
        test_images.extend(list(slides_dir.glob("*.png"))[:3])

    if not test_images:
        logger.warning("テスト用の画像が見つかりません")
        # ダミー画像を作成
        logger.info("ダミーのテスト画像を作成します...")
        import struct
        import zlib

        def create_test_png(width=100, height=100, color=(255, 128, 0)):
            """シンプルなテストPNG画像を生成"""
            def png_chunk(chunk_type, data):
                return (struct.pack('>I', len(data)) +
                        chunk_type + data +
                        struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff))

            # IHDR
            ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)

            # IDAT (simple colored image)
            raw_data = b''
            for y in range(height):
                raw_data += b'\x00'  # filter byte
                for x in range(width):
                    raw_data += bytes(color)

            compressed = zlib.compress(raw_data)

            # Build PNG
            png = b'\x89PNG\r\n\x1a\n'
            png += png_chunk(b'IHDR', ihdr_data)
            png += png_chunk(b'IDAT', compressed)
            png += png_chunk(b'IEND', b'')

            return png

        # テスト画像を作成
        test_png_dir = output_dir / "test_diagnostic"
        test_png_dir.mkdir(parents=True, exist_ok=True)

        for i, color in enumerate([(255, 100, 100), (100, 255, 100), (100, 100, 255)]):
            test_path = test_png_dir / f"test_slide_{i+1:02d}.png"
            test_path.write_bytes(create_test_png(400, 225, color))
            test_images.append(test_path)
            logger.info(f"  作成: {test_path.name}")

    # Base64変換テスト
    base64_results = []
    for img_path in test_images[:6]:
        logger.info(f"\n画像: {img_path.name}")
        try:
            with open(img_path, 'rb') as f:
                data = f.read()

            base64_data = base64.b64encode(data).decode('utf-8')
            data_url = f"data:image/png;base64,{base64_data}"

            valid = check_base64_data_url(data_url, img_path.name)
            base64_results.append({
                "path": str(img_path),
                "data_url": data_url if valid else None,
                "valid": valid
            })
        except Exception as e:
            logger.error(f"  変換エラー: {e}")
            base64_results.append({
                "path": str(img_path),
                "data_url": None,
                "valid": False
            })

    valid_count = sum(1 for r in base64_results if r["valid"])
    logger.info(f"\nBase64変換結果: {valid_count}/{len(base64_results)} 成功")

    # ==============================
    # Step 3: propsのJSON保存テスト
    # ==============================
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: JSON保存テスト")
    logger.info("=" * 60)

    # テスト用props
    test_slides = [
        {"type": "title", "heading": "テストタイトル", "subheading": "サブタイトル"},
        {"type": "content", "heading": "コンテンツ1", "points": ["ポイント1", "ポイント2"]},
        {"type": "content", "heading": "コンテンツ2", "points": ["ポイント3", "ポイント4"]},
        {"type": "ending", "heading": "まとめ", "subheading": "詳しくはブログで"}
    ]

    test_props = {
        "title": "テスト動画",
        "slides": test_slides,
        "topic": "ai_tools",
        "authorName": "if(塾) Blog",
        "audioUrl": None,
        "audioDataUrl": None,
        "slideImagePrefix": "test_slide_",
        "slideDuration": 5,
        "slideImages": [r["data_url"] for r in base64_results[:4] if r["valid"]]
    }

    # JSON保存
    props_file = remotion_dir / "props_diagnostic.json"
    try:
        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(test_props, f, ensure_ascii=False, indent=2)

        file_size = props_file.stat().st_size
        logger.info(f"JSONファイル保存成功: {props_file}")
        logger.info(f"  ファイルサイズ: {file_size:,} bytes")

        # 読み込みテスト
        with open(props_file, "r", encoding="utf-8") as f:
            loaded_props = json.load(f)

        logger.info(f"  読み込み成功")
        logger.info(f"  slides count: {len(loaded_props.get('slides', []))}")
        logger.info(f"  slideImages count: {len(loaded_props.get('slideImages', []))}")

        # slideImagesの検証
        for i, img_url in enumerate(loaded_props.get('slideImages', [])):
            if img_url:
                check_base64_data_url(img_url, f"loaded slideImages[{i}]")

    except Exception as e:
        logger.error(f"JSON保存/読み込みエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # ==============================
    # Step 4: Remotion render テスト
    # ==============================
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Remotion render テスト")
    logger.info("=" * 60)

    # Node.js確認
    import subprocess
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        logger.info(f"Node.js version: {result.stdout.strip()}")
    except:
        logger.error("Node.js が見つかりません")
        return

    # Remotionのテストレンダリング（短いダミー）
    output_video = output_dir / "diagnostic_video.mp4"

    logger.info(f"テストレンダリングを実行...")
    logger.info(f"  Props file: {props_file}")
    logger.info(f"  Output: {output_video}")

    try:
        render_script = remotion_dir / "render.mjs"
        cmd = [
            "node",
            str(render_script),
            "SlideVideo",
            str(output_video),
            str(props_file)
        ]

        process = subprocess.run(
            cmd,
            cwd=str(remotion_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5分タイムアウト
        )

        logger.info("\n--- Remotion Output ---")
        for line in process.stdout.split('\n'):
            if line.strip():
                logger.info(f"  {line}")

        if process.stderr:
            logger.info("\n--- Remotion Errors ---")
            for line in process.stderr.split('\n'):
                if line.strip():
                    logger.error(f"  {line}")

        if process.returncode == 0:
            if output_video.exists():
                logger.info(f"\n成功! 動画が生成されました")
                logger.info(f"  パス: {output_video}")
                logger.info(f"  サイズ: {output_video.stat().st_size:,} bytes")
            else:
                logger.error("レンダリング成功したが、ファイルが見つかりません")
        else:
            logger.error(f"レンダリング失敗 (exit code: {process.returncode})")

    except subprocess.TimeoutExpired:
        logger.error("タイムアウト (5分以上かかりました)")
    except Exception as e:
        logger.error(f"エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # クリーンアップ
        if props_file.exists():
            props_file.unlink()

    # ==============================
    # 診断結果サマリー
    # ==============================
    logger.info("\n" + "=" * 60)
    logger.info("診断結果サマリー")
    logger.info("=" * 60)
    logger.info(f"Base64変換: {valid_count}/{len(base64_results)} 成功")

    if output_video.exists():
        logger.info(f"動画生成: 成功 ({output_video.stat().st_size:,} bytes)")
    else:
        logger.info("動画生成: 失敗")


if __name__ == "__main__":
    asyncio.run(run_diagnostic())
