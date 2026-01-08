#!/usr/bin/env python3
"""
if-blog-auto セットアップスクリプト

このスクリプトは、ローカル開発環境をセットアップします:
1. python-dotenv のインストール
2. .env ファイルの作成
3. 依存関係の確認
4. VOICEPEAK の確認

使用方法:
    python setup.py
"""
import os
import subprocess
import sys
from pathlib import Path


def print_header(text: str):
    """ヘッダーを表示"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def check_python_dotenv() -> bool:
    """python-dotenvがインストールされているか確認"""
    try:
        import dotenv
        return True
    except ImportError:
        return False


def install_python_dotenv():
    """python-dotenvをインストール"""
    print("python-dotenv をインストール中...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "python-dotenv"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("  [OK] python-dotenv インストール完了")
        return True
    else:
        print(f"  [NG] インストール失敗: {result.stderr}")
        return False


def create_env_file(project_root: Path) -> bool:
    """対話的に.envファイルを作成"""
    env_path = project_root / ".env"
    env_example = project_root / ".env.example"

    if env_path.exists():
        print(f"  .env ファイルは既に存在します: {env_path}")
        response = input("  上書きしますか？ (y/N): ").strip().lower()
        if response != 'y':
            print("  スキップしました")
            return True

    # APIキーを取得
    print("\n  Google AI API キーを入力してください")
    print("  (取得方法: https://aistudio.google.com/app/apikey)")
    api_key = input("  API Key: ").strip()

    if not api_key:
        print("  [NG] APIキーが入力されませんでした")
        return False

    # .envファイルを作成
    env_content = f"""# Google AI API Key (Required)
GOOGLE_AI_API_KEY={api_key}

# GitHub Pages Settings (Auto-configured)
# Repository: takubon0202/if-blog-auto
# Public URL: https://takubon0202.github.io/if-blog-auto/

# Git Config (Optional - for local testing)
# GIT_USER_NAME=your_name
# GIT_USER_EMAIL=your_email@example.com

# VOICEPEAK Path (Optional - Windows only)
# VOICEPEAK_PATH=C:\\Program Files\\VOICEPEAK\\voicepeak.exe
"""

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"  [OK] .env ファイルを作成しました: {env_path}")
    return True


def check_voicepeak() -> str | None:
    """VOICEPEAKの存在を確認"""
    paths = [
        r"C:\Program Files\VOICEPEAK\voicepeak.exe",
        r"C:\Program Files (x86)\VOICEPEAK\voicepeak.exe",
    ]

    for path in paths:
        if Path(path).exists():
            return path

    return None


def check_nodejs() -> bool:
    """Node.jsの存在を確認"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False


def check_remotion(project_root: Path) -> bool:
    """Remotionパッケージの存在を確認"""
    remotion_bundler = project_root / "remotion" / "node_modules" / "@remotion" / "bundler"
    return remotion_bundler.exists()


def install_remotion(project_root: Path) -> bool:
    """Remotionパッケージをインストール"""
    remotion_dir = project_root / "remotion"
    print("  Remotion パッケージをインストール中...")
    print("  (これには数分かかる場合があります)")

    result = subprocess.run(
        ["npm", "install"],
        cwd=str(remotion_dir),
        capture_output=True,
        text=True,
        timeout=600
    )

    if result.returncode == 0:
        print("  [OK] Remotion インストール完了")
        return True
    else:
        print(f"  [NG] インストール失敗")
        print("  手動で実行してください: cd remotion && npm install")
        return False


def main():
    project_root = Path(__file__).parent

    print_header("if-blog-auto セットアップ")
    print(f"プロジェクトルート: {project_root}")

    # 1. python-dotenv
    print_header("Step 1: python-dotenv")
    if check_python_dotenv():
        print("  [OK] python-dotenv インストール済み")
    else:
        install_python_dotenv()

    # 2. .env ファイル
    print_header("Step 2: .env ファイル設定")
    env_path = project_root / ".env"
    if env_path.exists():
        print(f"  [OK] .env ファイルが存在します")

        # APIキーを確認
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except:
            pass

        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if api_key and api_key != "your_google_ai_api_key_here":
            masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(f"  [OK] API キー設定済み: {masked}")
        else:
            print("  [NG] API キーが未設定または無効です")
            create_env_file(project_root)
    else:
        create_env_file(project_root)

    # 3. VOICEPEAK
    print_header("Step 3: VOICEPEAK (オプション)")
    voicepeak_path = check_voicepeak()
    if voicepeak_path:
        print(f"  [OK] VOICEPEAK: {voicepeak_path}")
    else:
        print("  [--] VOICEPEAK: 未インストール")
        print("       高品質な日本語音声を使用する場合はインストールしてください")
        print("       インストーラー: voicepeak_6nare_dl\\VOICEPEAK...\\Windows\\voicepeak-downloader.exe")

    # 4. Node.js
    print_header("Step 4: Node.js")
    if check_nodejs():
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"  [OK] Node.js: {result.stdout.strip()}")
    else:
        print("  [NG] Node.js: 未インストール")
        print("       https://nodejs.org/ からインストールしてください")

    # 5. Remotion
    print_header("Step 5: Remotion")
    if check_remotion(project_root):
        print("  [OK] Remotion: インストール済み")
    else:
        print("  [--] Remotion: 未インストール")
        response = input("  インストールしますか？ (y/N): ").strip().lower()
        if response == 'y':
            install_remotion(project_root)
        else:
            print("  スキップしました")
            print("  手動で実行: cd remotion && npm install")

    # サマリー
    print_header("セットアップ完了")
    print("次のコマンドでテストを実行できます:")
    print()
    print("  # 基本テスト（環境確認）")
    print("  python src/scripts/test_full_pipeline.py --skip-video")
    print()
    print("  # 音声テスト付き")
    print("  python src/scripts/test_full_pipeline.py --with-audio")
    print()
    print("  # フルテスト（動画生成含む）")
    print("  python src/scripts/test_full_pipeline.py --with-audio")
    print()


if __name__ == "__main__":
    main()
