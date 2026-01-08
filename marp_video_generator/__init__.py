"""
Marp Video Generator Package

Marpスライドベースの動画自動生成ワークフロー

Workflow:
1. Content Generation (Gemini) - Marp Markdown + スクリプト生成
2. Slide Rendering (Marp CLI) - Markdown → PDF変換
3. Image Conversion (pdf2image) - PDF → PNG画像変換
4. Audio Synthesis (Gemini TTS) - スクリプト → 音声変換
5. Video Assembly (MoviePy) - 画像+音声を同期して動画生成

Example:
    from marp_video_generator import MarpVideoWorkflow

    workflow = MarpVideoWorkflow()
    video = await workflow.generate("Blog article...")
"""

from .main import (
    MarpVideoWorkflow,
    VideoConfig,
    ContentGenerator,
    SlideRenderer,
    ImageConverter,
    AudioSynthesizer,
    VideoAssembler,
    SlideData
)

__version__ = "1.0.0"
__all__ = [
    "MarpVideoWorkflow",
    "VideoConfig",
    "ContentGenerator",
    "SlideRenderer",
    "ImageConverter",
    "AudioSynthesizer",
    "VideoAssembler",
    "SlideData"
]
