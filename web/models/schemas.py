"""
Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class DownloadRequest(BaseModel):
    url: str = Field(..., description="TikTok video or profile URL")
    config_file: Optional[str] = None
    time_range: Optional[str] = Field(None, description="Time range: start|end, e.g. 2025-05-01 00-00-00|2025-05-02 00-00-00")


class DedupRequest(BaseModel):
    input_file: str = Field(..., description="Input video path")
    output_file: Optional[str] = Field(None, description="Output video path (auto-generated if not provided)")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="VideoConfig parameters")


class UploadRequest(BaseModel):
    platform: str = Field(..., description="Platform: tiktok, wechat, douyin, bilibili, kuaishou")
    account_name: str = Field(..., description="Account name")
    video_file: str = Field(..., description="Video file path")
    publish_type: int = Field(0, description="0=immediate, 1=scheduled")
    schedule_time: Optional[str] = Field(None, description="Schedule time in YYYY-MM-DD HH:MM format")


class ConfigUpdateRequest(BaseModel):
    content: Dict[str, Any] = Field(..., description="Configuration content")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    logs: List[str] = []
    result: Optional[Any] = None
    error: Optional[str] = None


class VideoConfigSchema(BaseModel):
    """Schema for VideoConfig grouped options"""
    # GPU
    enable_gpu: bool = False

    # Subtitles
    include_subtitles: bool = False
    subtitles_opacity: float = 0.10
    use_whisper: bool = True
    whisper_model_name: str = "base"
    subtitles_file: str = "assets/subtitles.srt"
    subtitles_color: str = "yellow"
    subtitles_duration: int = 5

    # Titles
    include_titles: bool = False
    titles_opacity: float = 0.10
    top_title: str = "YANQU"
    top_title_margin: int = 5
    bottom_title: str = "YANQU"
    bottom_title_margin: int = 5
    titles_color: str = "red"

    # Watermark
    include_watermark: bool = True
    watermark_opacity: float = 0.06
    watermark_direction: str = "random"
    watermark_color: str = "white"
    watermark_text: str = "YANQU"
    watermark_type: str = "image"
    watermark_image_path: str = "assets/watermark.png"
    watermark_video_path: str = ""

    # Font
    custom_font_enabled: bool = True
    font_file: str = "assets/fonts/simkai.ttf"
    text_border_size: int = 1

    # Audio
    enable_silence_check: bool = False
    silence_retention_ratio: float = 0.5
    silence_threshold: int = -50
    silent_duration: int = 500
    include_background_music: bool = True
    background_music_file: str = "assets/bgm.mp3"
    background_music_volume: float = 0.1

    # Transform
    flip_horizontal: bool = False
    rotation_angle: int = 0
    crop_percentage: float = 0.0
    fade_in_frames: int = 5
    fade_out_frames: int = 20

    # PIP
    include_hzh: bool = True
    hzh_opacity: float = 0.1
    hzh_scale: float = 1.0
    hzh_video_file: str = "assets/hzh.mp4"

    # Color
    enable_sbc: bool = True
    saturation: float = 1.05
    brightness: float = 0.05
    contrast: float = 1.05

    # Blur
    blur_background_enabled: bool = True
    top_blur_percentage: int = 3
    bottom_blur_percentage: int = 3
    side_blur_percentage: int = 3

    # Effects
    gaussian_blur_interval: int = 15
    gaussian_blur_kernel_size: int = 3
    gaussian_blur_area_percentage: int = 15
    enable_frame_swap: bool = True
    frame_swap_interval: int = 15
    enable_color_shift: bool = True
    color_shift_range: int = 3
    scramble_frequency: float = 0.0
    enable_texture_noise: bool = False
    texture_noise_strength: float = 0.5
    enable_blur_edge: bool = True


# Grouped config for UI display (中文标签)
VIDEO_CONFIG_GROUPS = {
    "subtitles": {
        "label": "字幕设置",
        "fields": ["include_subtitles", "subtitles_opacity", "use_whisper", "whisper_model_name", "subtitles_color", "subtitles_duration"]
    },
    "titles": {
        "label": "标题水印",
        "fields": ["include_titles", "titles_opacity", "top_title", "top_title_margin", "bottom_title", "bottom_title_margin", "titles_color"]
    },
    "watermark": {
        "label": "水印设置",
        "fields": ["include_watermark", "watermark_type", "watermark_text", "watermark_opacity", "watermark_direction", "watermark_color"]
    },
    "audio": {
        "label": "音频处理",
        "fields": ["enable_silence_check", "silence_threshold", "silence_retention_ratio", "silent_duration", "include_background_music", "background_music_volume"]
    },
    "transform": {
        "label": "视频变换",
        "fields": ["flip_horizontal", "rotation_angle", "crop_percentage", "fade_in_frames", "fade_out_frames"]
    },
    "pip": {
        "label": "画中画",
        "fields": ["include_hzh", "hzh_opacity", "hzh_scale"]
    },
    "color": {
        "label": "颜色调整",
        "fields": ["enable_sbc", "saturation", "brightness", "contrast"]
    },
    "blur": {
        "label": "模糊效果",
        "fields": ["blur_background_enabled", "top_blur_percentage", "bottom_blur_percentage", "side_blur_percentage", "gaussian_blur_interval", "gaussian_blur_kernel_size", "gaussian_blur_area_percentage"]
    },
    "effects": {
        "label": "动态特效",
        "fields": ["enable_frame_swap", "frame_swap_interval", "enable_color_shift", "color_shift_range"]
    },
    "advanced": {
        "label": "高级特效",
        "fields": ["scramble_frequency", "enable_texture_noise", "texture_noise_strength", "enable_blur_edge"]
    },
    "font": {
        "label": "字体设置",
        "fields": ["custom_font_enabled", "font_file", "text_border_size"]
    }
}
