#!/usr/bin/env python3
"""
VOICEPEAK Text-to-Speech Client

VOICEPEAK 商用可能 6ナレーターセット対応
高品質な日本語音声合成をコマンドラインから実行

使用方法:
    client = VoicepeakClient()
    result = await client.generate_audio("こんにちは", narrator="female1")

必要条件:
    - VOICEPEAK がインストールされていること
    - 環境変数 VOICEPEAK_PATH にVOICEPEAK.exeのパスを設定
    - または、デフォルトパスにインストール

コマンドライン引数:
    -s, --say Text      : 読み上げるテキスト
    -t, --text File     : テキストファイル
    -o, --out File      : 出力ファイルパス（WAV形式）
    -n, --narrator Name : ナレーター名
    -e, --emotion Expr  : 感情表現 (例: happy=50,sad=50)
    --speed Value       : 速度 (50-200、デフォルト100)
    --pitch Value       : ピッチ (-300 to 300、デフォルト0)
"""
import asyncio
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VoicepeakResult:
    """VOICEPEAK音声生成結果"""
    audio_data: bytes
    narrator: str
    text: str
    duration_seconds: float
    output_path: str


class VoicepeakClient:
    """
    VOICEPEAK Text-to-Speech クライアント

    VOICEPEAK 商用可能 6ナレーターセット対応
    """

    # デフォルトのVOICEPEAKパス（Windowsの一般的なインストール先）
    DEFAULT_PATHS = [
        r"C:\Program Files\VOICEPEAK\voicepeak.exe",
        r"C:\Program Files (x86)\VOICEPEAK\voicepeak.exe",
        r"C:\Users\琢己の自作PC\Downloads\voicepeak_6nare_dl\VOICEPEAK 商用可能 6ナレーターセット ダウンロード版\voicepeak.exe",
    ]

    # ナレーター設定（VOICEPEAK 商用可能 6ナレーターセット）
    # 実際のナレーター名はインストールされているセットに依存
    NARRATORS = {
        "female1": "Japanese Female 1",   # 女性1号
        "female2": "Japanese Female 2",   # 女性2号
        "female3": "Japanese Female 3",   # 女性3号
        "male1": "Japanese Male 1",       # 男性1号
        "male2": "Japanese Male 2",       # 男性2号
        "male3": "Japanese Male 3",       # 男性3号
        "default": "Japanese Female 1",   # デフォルト
    }

    # トピック別推奨ナレーター
    TOPIC_NARRATORS = {
        "psychology": "female1",      # 落ち着いた女性の声
        "education": "female1",       # 教育的な女性の声
        "startup": "male1",           # エネルギッシュな男性の声
        "investment": "male2",        # 信頼感のある男性の声
        "ai_tools": "male1",          # テック系の男性の声
        "inclusive_education": "female2",  # 優しい女性の声
        "weekly_summary": "female1",  # 落ち着いた女性の声
    }

    def __init__(self, voicepeak_path: str = None):
        """
        VOICEPEAKクライアントを初期化

        Args:
            voicepeak_path: VOICEPEAK実行ファイルのパス（省略時は自動検出）
        """
        self.voicepeak_path = voicepeak_path or self._find_voicepeak()
        self._available = self.voicepeak_path is not None

        if self._available:
            logger.info(f"VOICEPEAK found: {self.voicepeak_path}")
        else:
            logger.warning("VOICEPEAK not found. TTS will fall back to Gemini.")

    def _find_voicepeak(self) -> Optional[str]:
        """VOICEPEAKの実行ファイルを検索"""
        # 環境変数を最優先
        env_path = os.getenv("VOICEPEAK_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        # デフォルトパスを検索
        for path in self.DEFAULT_PATHS:
            if Path(path).exists():
                return path

        return None

    @property
    def is_available(self) -> bool:
        """VOICEPEAKが利用可能かどうか"""
        return self._available

    def get_narrator_for_topic(self, topic: str) -> str:
        """トピックに応じたナレーターを取得"""
        narrator_key = self.TOPIC_NARRATORS.get(topic, "default")
        return self.NARRATORS.get(narrator_key, self.NARRATORS["default"])

    async def generate_audio(
        self,
        text: str,
        narrator: str = "default",
        speed: int = 100,
        pitch: int = 0,
        emotion: str = None,
        output_path: str = None
    ) -> Optional[VoicepeakResult]:
        """
        VOICEPEAKで音声を生成

        Args:
            text: 読み上げるテキスト
            narrator: ナレーター名またはキー（default, female1, male1など）
            speed: 速度 (50-200)
            pitch: ピッチ (-300 to 300)
            emotion: 感情表現 (例: "happy=50,sad=50")
            output_path: 出力ファイルパス（省略時は一時ファイル）

        Returns:
            VoicepeakResult: 生成結果（音声バイナリデータを含む）
        """
        if not self._available:
            logger.error("VOICEPEAK is not available")
            return None

        # ナレーター名を解決
        narrator_name = self.NARRATORS.get(narrator, narrator)

        # 一時ファイルまたは指定パス
        if output_path is None:
            temp_dir = tempfile.mkdtemp()
            output_path = str(Path(temp_dir) / "voicepeak_output.wav")

        logger.info(f"Generating audio with VOICEPEAK: {text[:50]}...")
        logger.info(f"  Narrator: {narrator_name}")
        logger.info(f"  Speed: {speed}, Pitch: {pitch}")

        # コマンドを構築
        cmd = [
            self.voicepeak_path,
            "--say", text,
            "--out", output_path,
            "--narrator", narrator_name,
            "--speed", str(speed),
            "--pitch", str(pitch),
        ]

        if emotion:
            cmd.extend(["--emotion", emotion])

        try:
            # 非同期でサブプロセス実行
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120  # 2分タイムアウト
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"VOICEPEAK error: {error_msg}")
                return None

            # 出力ファイルを読み込み
            output_file = Path(output_path)
            if not output_file.exists():
                logger.error(f"Output file not created: {output_path}")
                return None

            audio_data = output_file.read_bytes()
            file_size = len(audio_data)

            # WAVファイルの長さを概算（24kHz, 16bit, mono想定）
            # 実際のサンプルレートはVOICEPEAKの設定に依存
            duration_seconds = (file_size - 44) / (44100 * 2)  # 44.1kHz, 16bit

            logger.info(f"VOICEPEAK audio generated: {file_size:,} bytes, ~{duration_seconds:.1f}s")

            return VoicepeakResult(
                audio_data=audio_data,
                narrator=narrator_name,
                text=text,
                duration_seconds=duration_seconds,
                output_path=output_path
            )

        except asyncio.TimeoutError:
            logger.error("VOICEPEAK timed out")
            return None
        except Exception as e:
            logger.error(f"VOICEPEAK error: {e}")
            return None

    async def generate_narration(
        self,
        script: str,
        topic: str = "ai_tools",
        speed: int = 110,  # 少し速めがちょうどいい
        pitch: int = 0
    ) -> Optional[VoicepeakResult]:
        """
        ナレーション音声を生成（トピック別ナレーター自動選択）

        Args:
            script: ナレーションスクリプト
            topic: トピックID
            speed: 速度
            pitch: ピッチ

        Returns:
            VoicepeakResult: 生成結果
        """
        narrator = self.TOPIC_NARRATORS.get(topic, "default")
        return await self.generate_audio(
            text=script,
            narrator=narrator,
            speed=speed,
            pitch=pitch
        )

    def list_narrators(self) -> List[str]:
        """利用可能なナレーターのリストを取得"""
        return list(self.NARRATORS.values())


# エクスポート用関数
async def generate_voicepeak_audio(
    text: str,
    narrator: str = "default",
    topic: str = None
) -> Optional[bytes]:
    """
    VOICEPEAKで音声を生成（シンプルなインターフェース）

    Args:
        text: 読み上げるテキスト
        narrator: ナレーター
        topic: トピック（ナレーター自動選択用）

    Returns:
        WAV形式の音声バイナリデータ
    """
    client = VoicepeakClient()

    if not client.is_available:
        return None

    if topic:
        narrator = client.TOPIC_NARRATORS.get(topic, narrator)

    result = await client.generate_audio(text, narrator)
    return result.audio_data if result else None


if __name__ == "__main__":
    # テスト実行
    async def test():
        client = VoicepeakClient()

        if not client.is_available:
            print("VOICEPEAK is not available")
            return

        print(f"VOICEPEAK path: {client.voicepeak_path}")
        print(f"Available narrators: {client.list_narrators()}")

        # テスト音声生成
        result = await client.generate_audio(
            "こんにちは。これはVOICEPEAKによるテスト音声です。",
            narrator="default"
        )

        if result:
            print(f"Audio generated: {len(result.audio_data):,} bytes")
            print(f"Duration: {result.duration_seconds:.1f}s")
            print(f"Output: {result.output_path}")

    asyncio.run(test())
