"""
Dedup service - uses OpenCV for processing and moviepy for audio preservation
"""
import asyncio
import cv2
import logging
import math
import numpy as np
import os
import subprocess
import sys
import tempfile
import uuid
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID
from typing import Optional, Union, Tuple, List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..services.task_manager import task_manager, TaskStatus
from ..config import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Try to import moviepy for audio handling
try:
    from moviepy import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("moviepy not installed, audio will not be preserved")

# Try to import Whisper for subtitle generation
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("whisper not installed, subtitles will not be generated")

# Try to import PIL for subtitle rendering
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not installed, subtitle burning may not work")

# Try to import OCR for subtitle detection
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


# Color name to BGR tuple mapping
COLOR_MAP = {
    'white': (255, 255, 255),
    'black': (0, 0, 0),
    'red': (0, 0, 255),
    'green': (0, 255, 0),
    'blue': (255, 0, 0),
    'yellow': (0, 255, 255),
    'cyan': (255, 255, 0),
    'magenta': (255, 0, 255),
    'orange': (0, 165, 255),
    'purple': (128, 0, 128),
}


def parse_color(color_value: Union[str, Tuple[int, int, int], list]) -> Tuple[int, int, int]:
    """Parse color value from config - handles string names, tuples, and lists"""
    if color_value is None:
        return (255, 255, 255)

    if isinstance(color_value, (tuple, list)) and len(color_value) == 3:
        return tuple(int(x) for x in color_value)

    if isinstance(color_value, str):
        color_lower = color_value.lower()
        if color_lower in COLOR_MAP:
            return COLOR_MAP[color_lower]
        try:
            cleaned = color_lower.replace('rgb', '').replace('(', '').replace(')', '')
            parts = [int(x.strip()) for x in cleaned.split(',')]
            if len(parts) == 3:
                return tuple(parts)
        except:
            pass

    return (255, 255, 255)


def format_time(seconds: float) -> str:
    """Convert seconds to SRT time format HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class SubtitleGenerator:
    """Generate subtitles using Whisper"""

    FFMPEG_PATH = "E:/InfiniteTalk 视频生成 项目/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe"

    @staticmethod
    def _set_ffmpeg_env():
        """Set FFmpeg path in environment for Whisper"""
        import os
        ffmpeg_dir = os.path.dirname(SubtitleGenerator.FFMPEG_PATH)
        if 'PATH' in os.environ:
            if ffmpeg_dir not in os.environ['PATH']:
                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
        else:
            os.environ['PATH'] = ffmpeg_dir

    @staticmethod
    def generate_subtitles(input_file: str, model_name: str = 'base') -> str:
        """Generate SRT subtitle file from video using Whisper"""
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper is not installed")

        SubtitleGenerator._set_ffmpeg_env()

        model = whisper.load_model(model_name)
        result = model.transcribe(input_file, verbose=False, language='zh')

        srt_fd, srt_path = tempfile.mkstemp(suffix='.srt')
        os.close(srt_fd)

        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(result['segments']):
                start = segment['start']
                end = segment['end']
                text = segment['text'].strip()

                f.write(f"{i + 1}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")

        logger.info(f"Generated subtitle file: {srt_path}")
        return srt_path


class SubtitleRenderer:
    """Render subtitles onto video frames using PIL"""

    @staticmethod
    def load_srt(srt_path: str) -> List[dict]:
        """Load SRT file into list of subtitle entries"""
        subtitles = []
        if not os.path.exists(srt_path):
            return subtitles

        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = content.strip().split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                time_line = lines[1]
                text = '\n'.join(lines[2:])
                times = time_line.split(' --> ')
                if len(times) == 2:
                    start_time = SubtitleRenderer._parse_srt_time(times[0])
                    end_time = SubtitleRenderer._parse_srt_time(times[1])
                    subtitles.append({
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
        return subtitles

    @staticmethod
    def _parse_srt_time(time_str: str) -> float:
        """Parse SRT time string to seconds"""
        time_str = time_str.strip().replace(',', '.')
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        return 0.0

    @staticmethod
    def add_subtitle_to_frame(frame: np.ndarray, text: str, font_size: int = 24,
                             color: Tuple[int, int, int] = (255, 255, 255),
                             bg_color: Tuple[int, int, int] = (0, 0, 0),
                             position: str = 'bottom') -> np.ndarray:
        """Add subtitle text to a video frame"""
        if not PIL_AVAILABLE:
            return frame

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_img)

        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "arial.ttf",
        ]
        font = None
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                continue
        if font is None:
            font = ImageFont.load_default()

        lines = text.split('\n')
        max_width = max(draw.textlength(line, font=font) for line in lines) if lines else 0
        line_height = font.getbbox('Ay')[3] - font.getbbox('Ay')[1] + 8 if lines else font_size + 8

        padding = 15
        text_width = int(max_width) + padding * 2
        text_height = len(lines) * line_height + padding * 2

        img_width, img_height = pil_img.size
        x = (img_width - text_width) // 2
        y = img_height - text_height - 30

        draw.rectangle([x, y, x + text_width, y + text_height], fill=(0, 0, 0))

        text_color_rgb = (color[2], color[1], color[0])
        for i, line in enumerate(lines):
            line_y = y + padding + i * line_height
            draw.text((x + padding, line_y), line, font=font, fill=text_color_rgb)

        frame_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return frame_bgr


class DedupService:

    @staticmethod
    def _run_dedup(task_id: UUID, input_file: str, output_file: str, config_dict: dict):
        """Run dedup using OpenCV"""

        async def _update(progress: int, log: str, status: TaskStatus = None, result: dict = None, error: str = None):
            await task_manager.update_progress(task_id, progress=progress, log=log)
            if status:
                await task_manager.set_status(task_id, status, result=result, error=error)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_update(10, "Starting dedup processing..."))
                loop.run_until_complete(task_manager.set_status(task_id, TaskStatus.RUNNING))

                out_dir = os.path.dirname(output_file)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)

                if not os.path.exists(input_file):
                    raise Exception(f"Input file not found: {input_file}")

                loop.run_until_complete(_update(20, f"Input: {input_file}"))
                loop.run_until_complete(_update(30, f"Output: {output_file}"))

                # Get video info
                cap = cv2.VideoCapture(input_file)
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                loop.run_until_complete(_update(40, f"Video: {width}x{height}, {fps:.1f}fps, {total_frames} frames"))

                # === Transform settings ===
                flip_horizontal = config_dict.get('flip_horizontal', False)
                rotation_angle = config_dict.get('rotation_angle', 0)
                crop_percentage = config_dict.get('crop_percentage', 0.0)
                fade_in_frames = config_dict.get('fade_in_frames', 0)
                fade_out_frames = config_dict.get('fade_out_frames', 0)

                # === Color settings ===
                enable_sbc = config_dict.get('enable_sbc', True)
                saturation = config_dict.get('saturation', 1.0)
                brightness = config_dict.get('brightness', 0.0)
                contrast = config_dict.get('contrast', 1.0)

                # === Watermark settings ===
                include_watermark = config_dict.get('include_watermark', True)
                watermark_text = config_dict.get('watermark_text', 'YANQU')
                watermark_opacity = config_dict.get('watermark_opacity', 0.06)
                watermark_color = parse_color(config_dict.get('watermark_color', 'white'))

                # === Title settings ===
                include_titles = config_dict.get('include_titles', False)
                top_title = config_dict.get('top_title', '')
                bottom_title = config_dict.get('bottom_title', '')
                titles_color = parse_color(config_dict.get('titles_color', 'red'))
                titles_opacity = config_dict.get('titles_opacity', 0.10)
                top_title_margin = config_dict.get('top_title_margin', 5)
                bottom_title_margin = config_dict.get('bottom_title_margin', 5)

                # === Subtitle settings ===
                include_subtitles = config_dict.get('include_subtitles', False)
                subtitles_color = config_dict.get('subtitles_color', 'white')
                use_whisper = config_dict.get('use_whisper', True)
                whisper_model = config_dict.get('whisper_model_name', 'base')

                # === PIP settings ===
                include_hzh = config_dict.get('include_hzh', False)
                hzh_opacity = config_dict.get('hzh_opacity', 0.1)
                hzh_scale = config_dict.get('hzh_scale', 1.0)
                hzh_video_file = config_dict.get('hzh_video_file', '')

                # === Blur settings ===
                blur_background_enabled = config_dict.get('blur_background_enabled', False)
                top_blur_percentage = config_dict.get('top_blur_percentage', 3)
                bottom_blur_percentage = config_dict.get('bottom_blur_percentage', 3)
                side_blur_percentage = config_dict.get('side_blur_percentage', 3)

                # === Effects settings ===
                enable_frame_swap = config_dict.get('enable_frame_swap', False)
                frame_swap_interval = config_dict.get('frame_swap_interval', 15)
                enable_color_shift = config_dict.get('enable_color_shift', False)
                color_shift_range = config_dict.get('color_shift_range', 3)
                enable_blur_edge = config_dict.get('enable_blur_edge', False)

                # === Audio settings ===
                include_background_music = config_dict.get('include_background_music', False)
                background_music_file = config_dict.get('background_music_file', '')
                background_music_volume = config_dict.get('background_music_volume', 0.1)

                # Generate subtitles if enabled
                subtitle_file = None
                subtitles_list = []

                if include_subtitles and use_whisper and WHISPER_AVAILABLE:
                    loop.run_until_complete(_update(42, "Generating subtitles with Whisper..."))
                    try:
                        subtitle_file = SubtitleGenerator.generate_subtitles(input_file, whisper_model)
                        if subtitle_file and os.path.exists(subtitle_file):
                            subtitles_list = SubtitleRenderer.load_srt(subtitle_file)
                            loop.run_until_complete(_update(45, f"Generated {len(subtitles_list)} subtitle segments"))
                    except Exception as sub_err:
                        logger.warning(f"Subtitle generation failed: {sub_err}")
                        loop.run_until_complete(_update(45, f"Subtitle generation failed: {sub_err}"))

                # Setup video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

                # Load PIP video if enabled
                pip_cap = None
                if include_hzh and hzh_video_file and os.path.exists(hzh_video_file):
                    pip_cap = cv2.VideoCapture(hzh_video_file)

                frame_idx = 0
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame is None or frame.size == 0:
                        continue

                    h, w = frame.shape[:2]

                    # === Horizontal flip ===
                    if flip_horizontal:
                        frame = cv2.flip(frame, 1)

                    # === Rotation ===
                    if rotation_angle != 0:
                        angle = rotation_angle % 360
                        if angle == 90:
                            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                        elif angle == 180:
                            frame = cv2.rotate(frame, cv2.ROTATE_180)
                        elif angle == 270:
                            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

                    # === Crop ===
                    if crop_percentage > 0 and crop_percentage < 0.5:
                        curr_h, curr_w = frame.shape[:2]
                        crop_x = min(int(curr_w * crop_percentage), curr_w // 4)
                        crop_y = min(int(curr_h * crop_percentage), curr_h // 4)
                        if crop_x > 0 and crop_y > 0 and curr_h > crop_y * 2 and curr_w > crop_x * 2:
                            cropped = frame[crop_y:curr_h-crop_y, crop_x:curr_w-crop_x]
                            if cropped.size > 0:
                                frame = cv2.resize(cropped, (curr_w, curr_h))

                    # === Color adjustment (SBC) ===
                    if enable_sbc:
                        frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness * 255)
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
                        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
                        hsv[:, :, 1] = hsv[:, :, 1].astype(np.uint8)
                        frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

                    # === Blur edges ===
                    if enable_blur_edge:
                        blur_kernel = max(3, int(min(h, w) * 0.02) | 1)
                        blurred = cv2.GaussianBlur(frame, (blur_kernel, blur_kernel), 0)
                        # Apply blur to edges only
                        frame = blurred

                    # === Fade in ===
                    if fade_in_frames > 0 and frame_idx < fade_in_frames:
                        alpha = frame_idx / fade_in_frames
                        frame = cv2.addWeighted(frame, alpha, np.zeros_like(frame), 1 - alpha, 0)

                    # === Fade out ===
                    if fade_out_frames > 0 and frame_idx >= total_frames - fade_out_frames:
                        fade_out_idx = frame_idx - (total_frames - fade_out_frames)
                        alpha = 1 - (fade_out_idx / fade_out_frames)
                        frame = cv2.addWeighted(frame, alpha, np.zeros_like(frame), 1 - alpha, 0)

                    # === Frame swap effect ===
                    if enable_frame_swap and frame_idx % frame_swap_interval == 0 and frame_idx > 0:
                        # Swap red and blue channels briefly
                        b, g, r = cv2.split(frame)
                        frame = cv2.merge([r, g, b])

                    # === Color shift effect ===
                    if enable_color_shift and frame_idx % 30 < 15:
                        # Slight hue shift
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
                        hsv[:, :, 0] = (hsv[:, :, 0] + color_shift_range) % 180
                        frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

                    # === Watermark ===
                    if include_watermark and watermark_text:
                        overlay = frame.copy()
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 1.5
                        thickness = 2
                        x, y = 20, 40
                        cv2.putText(overlay, watermark_text, (x, y), font, font_scale, (0, 0, 0), thickness + 2)
                        cv2.putText(overlay, watermark_text, (x, y), font, font_scale, watermark_color, thickness)
                        frame = cv2.addWeighted(overlay, watermark_opacity, frame, 1 - watermark_opacity, 0)

                    # === Titles ===
                    if include_titles:
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        if top_title:
                            cv2.putText(frame, top_title, (top_title_margin, 50), font, 1.2, titles_color, 2)
                        if bottom_title:
                            cv2.putText(frame, bottom_title, (bottom_title_margin, h - 20), font, 1.2, titles_color, 2)

                    # === Subtitles ===
                    if subtitles_list:
                        current_time = frame_idx / fps
                        for sub in subtitles_list:
                            if sub['start'] <= current_time <= sub['end']:
                                sub_color = parse_color(subtitles_color)
                                frame = SubtitleRenderer.add_subtitle_to_frame(
                                    frame, sub['text'],
                                    font_size=24,
                                    color=sub_color,
                                    bg_color=(0, 0, 0),
                                    position='bottom'
                                )
                                break

                    # === PIP (Picture in Picture) ===
                    if pip_cap is not None and pip_cap.isOpened():
                        pip_ret, pip_frame = pip_cap.read()
                        if not pip_ret:
                            pip_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            pip_ret, pip_frame = pip_cap.read()

                        if pip_ret:
                            pip_h, pip_w = pip_frame.shape[:2]
                            # Scale PIP
                            new_pip_w = int(pip_w * hzh_scale)
                            new_pip_h = int(pip_h * hzh_scale)
                            pip_frame = cv2.resize(pip_frame, (new_pip_w, new_pip_h))

                            # Position PIP in top-right corner
                            pi_x, pi_y = w - new_pip_w - 20, 20

                            # Create overlay
                            overlay = frame.copy()
                            roi = overlay[pi_y:pi_y+new_pip_h, pi_x:pi_x+new_pip_w]
                            cv2.addWeighted(roi, 1-hzh_opacity, pip_frame, hzh_opacity, 0, roi)
                            frame = overlay

                    # Ensure frame matches writer dimensions
                    if frame.shape[:2] != (height, width):
                        frame = cv2.resize(frame, (width, height))

                    out.write(frame)
                    frame_idx += 1

                    if frame_idx % 30 == 0:
                        progress = int(45 + (frame_idx / total_frames) * 45)
                        loop.run_until_complete(_update(progress, f"Processing frame {frame_idx}/{total_frames}..."))

                cap.release()
                if pip_cap:
                    pip_cap.release()
                out.release()

                # Clean up subtitle file
                if subtitle_file and os.path.exists(subtitle_file):
                    try:
                        os.unlink(subtitle_file)
                    except:
                        pass

                # Preserve audio using FFmpeg (more reliable than moviepy)
                loop.run_until_complete(_update(95, "Preserving audio..."))
                final_output = output_file

                try:
                    # Use FFmpeg to merge original audio with processed video
                    temp_output = output_file.replace('.mp4', '_temp.mp4')
                    os.rename(output_file, temp_output)

                    ffmpeg_cmd = [
                        'E:/InfiniteTalk 视频生成 项目/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe',
                        '-i', temp_output,
                        '-i', input_file,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-map', '0:v:0',
                        '-map', '1:a:0',
                        '-shortest',
                        '-y',
                        output_file
                    ]

                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)

                    if os.path.exists(output_file):
                        os.unlink(temp_output)
                        loop.run_until_complete(_update(100, "Processing complete with audio!"))
                    else:
                        os.rename(temp_output, output_file)
                        loop.run_until_complete(_update(100, "Processing complete (audio merge failed)!"))

                except Exception as audio_err:
                    logger.warning(f"Audio preservation failed: {audio_err}")
                    loop.run_until_complete(_update(100, "Processing complete!"))

                loop.run_until_complete(task_manager.set_status(task_id, TaskStatus.COMPLETED, result={"output_file": output_file}))

            finally:
                loop.close()

        except Exception as e:
            error = f"Dedup error: {str(e)}"
            logger.exception(error)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(task_manager.set_status(task_id, TaskStatus.FAILED, error=error))
            finally:
                loop.close()

    @staticmethod
    async def run_dedup(task_id: UUID, input_file: str, output_file: Optional[str], config_dict: dict):
        """Start dedup task in thread pool"""
        if not output_file:
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}_dedup{input_path.suffix}")

        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)

        await task_manager.update_progress(task_id, progress=0, log=f"Starting dedup task...")

        loop.run_in_executor(executor, DedupService._run_dedup, task_id, input_file, output_file, config_dict)
