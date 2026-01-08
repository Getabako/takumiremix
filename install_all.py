#!/usr/bin/env python3
"""
if-blog-auto 完全インストールスクリプト

このスクリプトは以下を自動的にセットアップします:
1. Python依存関係のインストール
2. .envファイルの作成（APIキー設定）
3. VOICEPEAKのインストール（ダウンローダー起動）
4. Node.js / Remotionのインストール
5. Gemini TTSの動作確認
6. フルパイプラインテスト

使用方法:
    python install_all.py
    python install_all.py --skip-voicepeak  # VOICEPEAKインストールをスキップ
    python install_all.py --api-key YOUR_KEY  # APIキーを直接指定
"""
import asyncio
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """ヘッダーを表示"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")


def print_step(step: int, total: int, text: str):
    """ステップを表示"""
    print(f"\n{Colors.BOLD}[Step {step}/{total}] {text}{Colors.END}")


def print_ok(text: str):
    """成功メッセージ"""
    print(f"  {Colors.GREEN}[OK]{Colors.END} {text}")


def print_ng(text: str):
    """失敗メッセージ"""
    print(f"  {Colors.RED}[NG]{Colors.END} {text}")


def print_warn(text: str):
    """警告メッセージ"""
    print(f"  {Colors.YELLOW}[!!]{Colors.END} {text}")


def print_info(text: str):
    """情報メッセージ"""
    print(f"  {Colors.BLUE}[i]{Colors.END} {text}")


class FullInstaller:
    """完全インストーラー"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.remotion_dir = self.project_root / "remotion"
        self.env_file = self.project_root / ".env"
        self.results = {}

        # VOICEPEAK paths
        self.voicepeak_downloader = Path(
            r"c:\Users\琢己の自作PC\Downloads\voicepeak_6nare_dl"
            r"\VOICEPEAK 商用可能 6ナレーターセット ダウンロード版\Windows\voicepeak-downloader.exe"
        )
        self.voicepeak_install_paths = [
            Path(r"C:\Program Files\VOICEPEAK\voicepeak.exe"),
            Path(r"C:\Program Files (x86)\VOICEPEAK\voicepeak.exe"),
        ]

    def step_1_python_deps(self) -> bool:
        """Step 1: Python依存関係"""
        print_step(1, 6, "Python依存関係のインストール")

        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            print_ng("requirements.txt が見つかりません")
            return False

        try:
            # python-dotenv を先にインストール
            print_info("python-dotenv をインストール中...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "python-dotenv", "-q"],
                capture_output=True,
                text=True,
                timeout=120
            )

            # 全依存関係をインストール
            print_info("全依存関係をインストール中...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-q"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print_ok("Python依存関係インストール完了")
                self.results["python_deps"] = True
                return True
            else:
                print_ng(f"インストール失敗: {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            print_ng("タイムアウト")
            return False
        except Exception as e:
            print_ng(f"エラー: {e}")
            return False

    def step_2_env_file(self, api_key: str = None) -> bool:
        """Step 2: .envファイル作成"""
        print_step(2, 6, ".env ファイル設定")

        if self.env_file.exists():
            print_info(".env ファイルが既に存在します")

            # APIキーを確認
            try:
                from dotenv import load_dotenv
                load_dotenv(self.env_file)
            except:
                pass

            existing_key = os.getenv("GOOGLE_AI_API_KEY")
            if existing_key and existing_key != "your_google_ai_api_key_here":
                masked = existing_key[:8] + "..." + existing_key[-4:] if len(existing_key) > 12 else "***"
                print_ok(f"APIキー設定済み: {masked}")
                self.results["api_key"] = existing_key
                return True
            else:
                print_warn("APIキーが未設定または無効です")

        # APIキーを取得
        if api_key:
            key = api_key
        else:
            print()
            print_info("Google AI API キーを入力してください")
            print_info("取得方法: https://aistudio.google.com/app/apikey")
            key = input("  API Key: ").strip()

        if not key or key == "your_google_ai_api_key_here":
            print_ng("有効なAPIキーが必要です")
            return False

        # .envファイル作成
        env_content = f"""# Google AI API Key (Required)
GOOGLE_AI_API_KEY={key}

# GitHub Pages Settings (Auto-configured)
# Repository: takubon0202/if-blog-auto
# Public URL: https://takubon0202.github.io/if-blog-auto/

# VOICEPEAK Path (Auto-detected)
# VOICEPEAK_PATH=C:\\Program Files\\VOICEPEAK\\voicepeak.exe
"""

        self.env_file.write_text(env_content, encoding="utf-8")
        print_ok(f".env ファイル作成完了: {self.env_file}")

        # 環境変数にも設定
        os.environ["GOOGLE_AI_API_KEY"] = key
        self.results["api_key"] = key
        return True

    def step_3_voicepeak(self, skip: bool = False) -> bool:
        """Step 3: VOICEPEAKインストール"""
        print_step(3, 6, "VOICEPEAK インストール")

        if skip:
            print_info("VOICEPEAKインストールをスキップ")
            print_info("Gemini TTSがフォールバックとして使用されます")
            self.results["voicepeak"] = None
            return True

        # 既存インストールを確認
        for path in self.voicepeak_install_paths:
            if path.exists():
                print_ok(f"VOICEPEAK インストール済み: {path}")
                self.results["voicepeak"] = str(path)
                return True

        # ダウンローダーを確認
        if not self.voicepeak_downloader.exists():
            print_warn(f"VOICEPEAKダウンローダーが見つかりません")
            print_info(f"想定パス: {self.voicepeak_downloader}")
            print_info("Gemini TTSをフォールバックとして使用します")
            self.results["voicepeak"] = None
            return True

        print_info("VOICEPEAKダウンローダーを起動します")
        print_info("インストール完了後、このスクリプトは自動的に続行します")
        print()

        response = input("  VOICEPEAKをインストールしますか？ (Y/n): ").strip().lower()
        if response == 'n':
            print_info("スキップしました。Gemini TTSを使用します")
            self.results["voicepeak"] = None
            return True

        try:
            # ダウンローダーを起動（別プロセス）
            print_info("ダウンローダーを起動中...")
            subprocess.Popen(
                [str(self.voicepeak_downloader)],
                shell=True
            )

            print()
            print_warn("VOICEPEAKインストーラーが起動しました")
            print_info("インストールを完了してから、Enterキーを押してください")
            input("  [Enter] インストール完了後に続行...")

            # インストール確認
            for path in self.voicepeak_install_paths:
                if path.exists():
                    print_ok(f"VOICEPEAK インストール確認: {path}")
                    self.results["voicepeak"] = str(path)

                    # .envに追記
                    self._update_env_voicepeak(path)
                    return True

            print_warn("VOICEPEAKが見つかりません。インストールパスを確認してください")
            print_info("Gemini TTSをフォールバックとして使用します")
            self.results["voicepeak"] = None
            return True

        except Exception as e:
            print_ng(f"エラー: {e}")
            print_info("Gemini TTSをフォールバックとして使用します")
            self.results["voicepeak"] = None
            return True

    def _update_env_voicepeak(self, voicepeak_path: Path):
        """VOICEPEAKパスを.envに追記"""
        if self.env_file.exists():
            content = self.env_file.read_text(encoding="utf-8")
            if "VOICEPEAK_PATH=" not in content or "# VOICEPEAK_PATH=" in content:
                # コメントアウトされた行を実際の値に置換
                path_str = str(voicepeak_path).replace("\\", "\\\\")
                if "# VOICEPEAK_PATH=" in content:
                    content = content.replace(
                        "# VOICEPEAK_PATH=",
                        f"VOICEPEAK_PATH={path_str}\n# "
                    )
                else:
                    content += f"\nVOICEPEAK_PATH={path_str}\n"
                self.env_file.write_text(content, encoding="utf-8")
                print_info(f"VOICEPEAKパスを.envに追加しました")

    def step_4_nodejs_remotion(self) -> bool:
        """Step 4: Node.js / Remotion"""
        print_step(4, 6, "Node.js / Remotion セットアップ")

        # Node.js確認
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print_ok(f"Node.js: {result.stdout.strip()}")
                self.results["nodejs"] = True
            else:
                print_ng("Node.js が見つかりません")
                print_info("https://nodejs.org/ からインストールしてください")
                return False
        except Exception as e:
            print_ng(f"Node.js エラー: {e}")
            return False

        # Remotion確認/インストール
        remotion_bundler = self.remotion_dir / "node_modules" / "@remotion" / "bundler"
        if remotion_bundler.exists():
            print_ok("Remotion: インストール済み")
            self.results["remotion"] = True
            return True

        print_info("Remotion をインストール中...")
        print_info("(これには数分かかる場合があります)")

        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(self.remotion_dir),
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                print_ok("Remotion インストール完了")
                self.results["remotion"] = True
                return True
            else:
                print_ng(f"Remotion インストール失敗")
                print_info("手動で実行: cd remotion && npm install")
                return False

        except subprocess.TimeoutExpired:
            print_ng("タイムアウト")
            return False
        except Exception as e:
            print_ng(f"エラー: {e}")
            return False

    async def step_5_verify_tts(self) -> bool:
        """Step 5: TTS動作確認"""
        print_step(5, 6, "TTS (音声合成) 動作確認")

        # .envをリロード
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_file, override=True)
        except:
            pass

        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            print_ng("APIキーが設定されていません")
            return False

        # Gemini TTS テスト
        print_info("Gemini TTS をテスト中...")
        try:
            sys.path.insert(0, str(self.project_root / "src"))
            from lib.gemini_client import GeminiClient

            client = GeminiClient()
            result = await client.generate_audio(
                text="これはテスト音声です。システムが正常に動作しています。",
                voice="default"
            )

            if result and result.audio_data:
                # WAVヘッダー確認
                is_wav = (
                    len(result.audio_data) >= 12
                    and result.audio_data[:4] == b'RIFF'
                    and result.audio_data[8:12] == b'WAVE'
                )
                print_ok(f"Gemini TTS: {len(result.audio_data):,} bytes (WAV: {'有効' if is_wav else '無効'})")
                self.results["gemini_tts"] = True
            else:
                print_ng("Gemini TTS: 音声データなし")
                self.results["gemini_tts"] = False

        except Exception as e:
            print_ng(f"Gemini TTS エラー: {e}")
            self.results["gemini_tts"] = False

        # VOICEPEAK テスト
        if self.results.get("voicepeak"):
            print_info("VOICEPEAK をテスト中...")
            try:
                from lib.voicepeak_client import VoicepeakClient

                client = VoicepeakClient()
                if client.is_available:
                    result = await client.generate_audio(
                        text="ボイスピークのテストです。",
                        narrator="default",
                        speed=100
                    )

                    if result and result.audio_data:
                        print_ok(f"VOICEPEAK: {len(result.audio_data):,} bytes")
                        self.results["voicepeak_tts"] = True
                    else:
                        print_warn("VOICEPEAK: 音声データなし")
                        self.results["voicepeak_tts"] = False
                else:
                    print_warn("VOICEPEAK: 利用不可")
                    self.results["voicepeak_tts"] = False
            except Exception as e:
                print_warn(f"VOICEPEAK エラー: {e}")
                self.results["voicepeak_tts"] = False
        else:
            print_info("VOICEPEAK: 未インストール（Gemini TTSを使用）")
            self.results["voicepeak_tts"] = False

        # 最低1つのTTSが利用可能か確認
        if self.results.get("gemini_tts") or self.results.get("voicepeak_tts"):
            return True
        else:
            print_warn("警告: TTSが利用できません。動画は無音で生成されます")
            return True  # 続行は可能

    def step_6_test_pipeline(self) -> bool:
        """Step 6: パイプラインテスト"""
        print_step(6, 6, "パイプラインテスト")

        if not self.results.get("remotion"):
            print_warn("Remotion が未インストールのためテストをスキップ")
            return True

        print_info("動画レンダリングをテスト中...")

        test_script = self.project_root / "src" / "scripts" / "test_full_pipeline.py"
        if not test_script.exists():
            print_warn("テストスクリプトが見つかりません")
            return True

        try:
            # 簡易テスト（動画生成あり、音声なし）
            result = subprocess.run(
                [sys.executable, str(test_script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print_ok("パイプラインテスト完了")
                self.results["pipeline_test"] = True
            else:
                print_warn("パイプラインテストで一部エラー")
                self.results["pipeline_test"] = False

            # 結果の一部を表示
            for line in result.stdout.split('\n')[-15:]:
                if line.strip():
                    print(f"    {line}")

            return True

        except subprocess.TimeoutExpired:
            print_warn("テストタイムアウト")
            return True
        except Exception as e:
            print_warn(f"テストエラー: {e}")
            return True

    def print_summary(self):
        """結果サマリー"""
        print_header("インストール完了サマリー")

        checks = [
            ("Python依存関係", self.results.get("python_deps", False)),
            ("APIキー設定", self.results.get("api_key") is not None),
            ("Node.js", self.results.get("nodejs", False)),
            ("Remotion", self.results.get("remotion", False)),
            ("Gemini TTS", self.results.get("gemini_tts", False)),
            ("VOICEPEAK", self.results.get("voicepeak_tts", False)),
            ("パイプラインテスト", self.results.get("pipeline_test", False)),
        ]

        all_critical_ok = True
        for name, status in checks:
            if status:
                print_ok(name)
            else:
                if name in ["Python依存関係", "APIキー設定", "Remotion"]:
                    print_ng(name)
                    all_critical_ok = False
                else:
                    print_warn(f"{name} (オプション)")

        print()

        # TTS状況
        if self.results.get("voicepeak_tts"):
            print_info("音声生成: VOICEPEAK (高品質)")
        elif self.results.get("gemini_tts"):
            print_info("音声生成: Gemini TTS (クラウド)")
        else:
            print_warn("音声生成: 利用不可（動画は無音）")

        print()

        if all_critical_ok:
            print(f"{Colors.GREEN}{Colors.BOLD}セットアップ完了！システムは正常に動作します{Colors.END}")
            print()
            print("次のコマンドでブログ生成を開始できます:")
            print()
            print(f"  {Colors.CYAN}python src/scripts/main.py --topic ai_tools --publish{Colors.END}")
            print()
        else:
            print(f"{Colors.RED}{Colors.BOLD}セットアップに問題があります{Colors.END}")
            print("上記のエラーを確認してください")


async def main():
    parser = argparse.ArgumentParser(description="if-blog-auto 完全インストール")
    parser.add_argument("--api-key", help="Google AI APIキーを直接指定")
    parser.add_argument("--skip-voicepeak", action="store_true", help="VOICEPEAKインストールをスキップ")
    parser.add_argument("--skip-test", action="store_true", help="パイプラインテストをスキップ")
    args = parser.parse_args()

    print_header("if-blog-auto 完全インストール")
    print(f"プロジェクト: {Path(__file__).parent}")

    installer = FullInstaller()

    # Step 1: Python依存関係
    if not installer.step_1_python_deps():
        print_ng("セットアップを中断します")
        return

    # Step 2: .env設定
    if not installer.step_2_env_file(api_key=args.api_key):
        print_ng("セットアップを中断します")
        return

    # Step 3: VOICEPEAK
    installer.step_3_voicepeak(skip=args.skip_voicepeak)

    # Step 4: Node.js / Remotion
    installer.step_4_nodejs_remotion()

    # Step 5: TTS確認
    await installer.step_5_verify_tts()

    # Step 6: パイプラインテスト
    if not args.skip_test:
        installer.step_6_test_pipeline()

    # サマリー
    installer.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
