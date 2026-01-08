"""
Gemini Video Generator Package

High-quality video generation using Gemini AI

Example:
    from video_generator import VideoGeneratorWorkflow

    workflow = VideoGeneratorWorkflow()
    video = await workflow.generate_from_text("Blog article...")
"""

from .main import (
    VideoGeneratorWorkflow,
    VideoConfig,
    GeminiVideoClient,
    VideoEditor,
    Scene
)

from .integrate import (
    generate_blog_video,
    generate_slide_video_enhanced,
    BlogVideoResult
)

__version__ = "1.0.0"
__all__ = [
    "VideoGeneratorWorkflow",
    "VideoConfig",
    "GeminiVideoClient",
    "VideoEditor",
    "Scene",
    "generate_blog_video",
    "generate_slide_video_enhanced",
    "BlogVideoResult"
]
