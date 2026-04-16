import os
import random

from .config import CropStrategy, PyReelConfig
from .exceptions import PyReelCropError

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920


def crop_to_portrait(input_path: str, output_path: str, config: PyReelConfig) -> str:
    try:
        from moviepy import VideoFileClip
    except ImportError as e:
        raise PyReelCropError("moviepy is not installed.") from e

    try:
        clip = VideoFileClip(input_path)

        # Apply a random start offset so the same source video yields different clips.
        # Leave at least 30 s of footage at the end; if the video is that short, start at 0.
        min_remaining = 30.0
        max_start = max(0.0, clip.duration - min_remaining)
        if max_start > 0:
            start = random.uniform(0, max_start)
            clip = clip.subclipped(start)

        source_width, source_height = clip.size

        strategy = config.crop.strategy

        if strategy == CropStrategy.CENTER:
            if source_height > source_width:
                cropped = clip
            else:
                crop_width = int(source_height * 9 / 16)
                x_offset = (source_width - crop_width) // 2
                cropped = clip.cropped(
                    x1=x_offset,
                    y1=0,
                    x2=x_offset + crop_width,
                    y2=source_height,
                )

        elif strategy == CropStrategy.CUSTOM:
            x = config.crop.custom_x or 0
            y = config.crop.custom_y or 0
            crop_width = int(source_height * 9 / 16)
            cropped = clip.cropped(
                x1=x,
                y1=y,
                x2=x + crop_width,
                y2=y + source_height,
            )
        else:
            raise PyReelCropError(f"Unknown crop strategy: {strategy}")

        final = cropped.resized(new_size=(TARGET_WIDTH, TARGET_HEIGHT))

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            bitrate="4000k",
            logger=None,
        )
        clip.close()
        cropped.close()
        final.close()

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise PyReelCropError("Crop produced empty or missing output file.")

        return output_path

    except PyReelCropError:
        raise
    except Exception as e:
        raise PyReelCropError(f"Crop failed: {e}") from e
