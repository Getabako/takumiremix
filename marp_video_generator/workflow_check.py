#!/usr/bin/env python3
"""
環境チェックスクリプト

Marp動画生成ワークフローに必要な依存関係をチェックします。

使用方法:
    python workflow_check.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class Colors:
    """ANSI colors"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")


def print_ok(text: str):
    print(f"  {Colors.GREEN}[OK]{Colors.END} {text}")


def print_ng(text: str):
    print(f"  {Colors.RED}[NG]{Colors.END} {text}")


def print_warn(text: str):
    print(f"  {Colors.YELLOW}[!!]{Colors.END} {text}")


def check_command(cmd: str, version_flag: str = "--version") -> tuple:
    """コマンドの存在と版を確認"""
    try:
        result = subprocess.run(
            [cmd, version_flag],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            return True, version
        return False, None
    except FileNotFoundError:
        return False, None
    except Exception as e:
        return False, str(e)


def check_python_package(package: str) -> bool:
    """Pythonパッケージの存在を確認"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def check_marp_cli() -> tuple:
    """Marp CLIの確認"""
    # npx経由で確認
    try:
        result = subprocess.run(
            ["npx", "@marp-team/marp-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except:
        pass

    # グローバルインストール確認
    try:
        result = subprocess.run(
            ["marp", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except:
        pass

    return False, None


def check_poppler() -> tuple:
    """Poppler (pdftoppm) の確認"""
    # Windows
    if sys.platform == "win32":
        # pdf2imageがpopplerを見つけられるか確認
        try:
            from pdf2image import convert_from_path
            # ダミーPDFで試行（存在しないので例外が出るが、popplerエラーかどうかで判断）
            try:
                convert_from_path("nonexistent.pdf")
            except Exception as e:
                if "poppler" in str(e).lower() or "pdftoppm" in str(e).lower():
                    return False, "Poppler not found"
                # ファイルが見つからないエラーならOK（popplerは存在する）
                return True, "Available"
        except ImportError:
            return False, "pdf2image not installed"

    # Linux/Mac
    return check_command("pdftoppm", "-v")


def check_ffmpeg() -> tuple:
    """FFmpegの確認"""
    return check_command("ffmpeg", "-version")


def check_fonts() -> bool:
    """日本語フォントの確認"""
    if sys.platform == "win32":
        # Windowsは基本的にフォントあり
        return True

    # Linux: fonts-noto-cjkを確認
    font_paths = [
        "/usr/share/fonts/opentype/noto",
        "/usr/share/fonts/truetype/noto",
        "/usr/share/fonts/noto-cjk",
        "/usr/share/fonts/google-noto-cjk",
    ]
    for path in font_paths:
        if Path(path).exists():
            return True

    # fc-listでも確認
    try:
        result = subprocess.run(
            ["fc-list", ":lang=ja"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            return True
    except:
        pass

    return False


def main():
    print_header("Marp Video Generator - Environment Check")

    all_ok = True
    critical_failed = False

    # 1. Python
    print(f"\n{Colors.BOLD}1. Python Environment{Colors.END}")
    print_ok(f"Python {sys.version.split()[0]}")

    # 2. Pythonパッケージ
    print(f"\n{Colors.BOLD}2. Python Packages{Colors.END}")

    packages = [
        ("google.generativeai", "google-generativeai"),
        ("pdf2image", "pdf2image"),
        ("moviepy.editor", "moviepy"),
        ("pydub", "pydub"),
        ("PIL", "Pillow"),
        ("numpy", "numpy"),
    ]

    for import_name, package_name in packages:
        module_name = import_name.split('.')[0]
        if check_python_package(module_name):
            print_ok(package_name)
        else:
            print_ng(f"{package_name} - pip install {package_name}")
            all_ok = False

    # 3. 外部ツール
    print(f"\n{Colors.BOLD}3. External Tools{Colors.END}")

    # Node.js
    ok, version = check_command("node")
    if ok:
        print_ok(f"Node.js: {version}")
    else:
        print_ng("Node.js not found - https://nodejs.org/")
        all_ok = False
        critical_failed = True

    # Marp CLI
    ok, version = check_marp_cli()
    if ok:
        print_ok(f"Marp CLI: {version}")
    else:
        print_ng("Marp CLI not found")
        print_warn("  Install: npm install -g @marp-team/marp-cli")
        all_ok = False
        critical_failed = True

    # Poppler
    ok, version = check_poppler()
    if ok:
        print_ok(f"Poppler (pdf2image): {version}")
    else:
        print_ng("Poppler not found")
        if sys.platform == "win32":
            print_warn("  Download: https://github.com/oschwartz10612/poppler-windows/releases")
            print_warn("  Add to PATH or set POPPLER_PATH environment variable")
        else:
            print_warn("  Install: apt-get install poppler-utils (Ubuntu)")
            print_warn("           brew install poppler (Mac)")
        all_ok = False
        critical_failed = True

    # FFmpeg
    ok, version = check_command("ffmpeg")
    if ok:
        version_line = version.split('\n')[0] if version else "Available"
        print_ok(f"FFmpeg: {version_line[:50]}")
    else:
        print_ng("FFmpeg not found")
        print_warn("  Install: apt-get install ffmpeg (Ubuntu)")
        print_warn("           brew install ffmpeg (Mac)")
        all_ok = False
        critical_failed = True

    # 4. 日本語フォント
    print(f"\n{Colors.BOLD}4. Japanese Fonts{Colors.END}")

    if check_fonts():
        print_ok("Japanese fonts available")
    else:
        print_warn("Japanese fonts not found")
        print_warn("  Install: apt-get install fonts-noto-cjk (Ubuntu)")
        print_warn("  PDFs may have missing characters (tofu)")

    # 5. API Key
    print(f"\n{Colors.BOLD}5. API Configuration{Colors.END}")

    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print_ok(f"API Key: {masked}")
    else:
        print_ng("API Key not found")
        print_warn("  Set GOOGLE_AI_API_KEY environment variable")
        all_ok = False

    # Summary
    print_header("Summary")

    if critical_failed:
        print(f"\n{Colors.RED}{Colors.BOLD}CRITICAL: Required tools are missing!{Colors.END}")
        print("Please install the missing dependencies before running the workflow.")
        return 1
    elif all_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed! Ready to generate videos.{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Some optional dependencies are missing.{Colors.END}")
        print("The workflow may work with reduced functionality.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
