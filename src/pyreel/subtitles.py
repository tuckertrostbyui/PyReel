import contextlib
import importlib.resources
import logging
import os
import time

from .config import PyReelConfig, SubtitleStyle
from .exceptions import PyReelSubtitleError

logger = logging.getLogger(__name__)


def check_and_patch_imagemagick() -> bool:
    policy_paths = [
        "/etc/ImageMagick-6/policy.xml",
        "/etc/ImageMagick-7/policy.xml",
    ]

    for policy_path in policy_paths:
        if not os.path.exists(policy_path):
            continue

        try:
            with open(policy_path) as f:
                content = f.read()

            if 'pattern="@*"' not in content and "pattern='@*'" not in content:
                continue

            import re
            if re.search(r'rights="none"[^>]*pattern="@\*"', content):
                new_content = re.sub(
                    r'rights="none"([^>]*)pattern="@\*"',
                    r'rights="read|write"\1pattern="@*"',
                    content,
                )
                with open(policy_path, "w") as f:
                    f.write(new_content)
                return True

        except PermissionError:
            print("PyReel requires a small ImageMagick policy change. Please run:")
            print(
                f'sudo sed -i \'s/rights="none" pattern="@\\*"/rights="read|write" pattern="@*"/\' {policy_path}'
            )
            print("Then re-run your script.")
            return False
        except Exception as e:
            logger.warning(f"Could not patch ImageMagick policy: {e}")

    return False


def _resolve_font(config: PyReelConfig) -> str:
    if config.subtitle_style.font:
        return config.subtitle_style.font

    try:
        font_ref = importlib.resources.files("pyreel").joinpath("fonts/Anton-Regular.ttf")
        with importlib.resources.as_file(font_ref) as font_path:
            return str(font_path)
    except Exception as e:
        raise PyReelSubtitleError(
            f"Could not resolve bundled font Anton-Regular.ttf: {e}"
        ) from e


def _get_words(alignment: dict) -> list[dict]:
    words = []
    for segment in alignment.get("segments", []):
        for word_info in segment.get("words", []):
            words.append(word_info)
    return words


def _interpolate_timestamps(words: list[dict]) -> list[dict]:
    result = list(words)
    n = len(result)

    for i in range(n):
        if "start" not in result[i] or "end" not in result[i]:
            prev_end = None
            next_start = None

            for j in range(i - 1, -1, -1):
                if "end" in result[j]:
                    prev_end = result[j]["end"]
                    break

            for j in range(i + 1, n):
                if "start" in result[j]:
                    next_start = result[j]["start"]
                    break

            if prev_end is None and next_start is None:
                result[i] = None
                continue

            if prev_end is None:
                prev_end = next_start
            if next_start is None:
                next_start = prev_end

            duration = next_start - prev_end
            step = duration / max(
                sum(1 for k in range(i, n) if "start" not in result[k] and result[k] is not None) + 1,
                1,
            )
            result[i]["start"] = prev_end + step * 0.5
            result[i]["end"] = prev_end + step

    return [w for w in result if w is not None]


def build_subtitle_clips(
    alignment: dict,
    video_duration: float,
    config: PyReelConfig,
) -> list:
    try:
        from moviepy.video.VideoClip import TextClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    except ImportError as e:
        raise PyReelSubtitleError("moviepy is not installed.") from e

    font = _resolve_font(config)
    style = config.subtitle_style
    words = _get_words(alignment)
    words = _interpolate_timestamps(words)

    if not words:
        return []

    subtitle_style = style.style

    if subtitle_style == SubtitleStyle.BOLD_WHITE:
        return _build_bold_white(words, font, style, video_duration)
    elif subtitle_style == SubtitleStyle.HIGHLIGHT:
        start_time = time.time()
        clips = _build_highlight(words, font, style, video_duration)
        elapsed = time.time() - start_time
        if elapsed > 300:
            logger.warning(
                "HIGHLIGHT subtitle rendering took >5 minutes; falling back to BOLD_WHITE."
            )
            clips = _build_bold_white(words, font, style, video_duration)
        return clips
    elif subtitle_style == SubtitleStyle.ALLCAPS:
        return _build_allcaps(words, font, style, video_duration)
    elif subtitle_style == SubtitleStyle.ROLLING:
        return _build_rolling(words, font, style, video_duration)
    else:
        raise PyReelSubtitleError(f"Unknown subtitle style: {subtitle_style}")


def _make_text_clip(text, font, font_size, color, position, start, end, stroke_color=None, stroke_width=0):
    try:
        from moviepy.video.VideoClip import TextClip
    except ImportError as e:
        raise PyReelSubtitleError("moviepy is not installed.") from e

    kwargs = {
        "font": font,
        "font_size": font_size,
        "color": color,
    }
    if stroke_color and stroke_width > 0:
        kwargs["stroke_color"] = stroke_color
        kwargs["stroke_width"] = stroke_width

    clip = TextClip(text=text, **kwargs)
    clip = clip.with_position(position).with_start(start).with_end(end)
    return clip


def _build_bold_white(words, font, style, video_duration):
    clips = []
    for word_info in words:
        text = word_info.get("word", "").strip()
        if not text:
            continue
        start = word_info.get("start", 0)
        end = word_info.get("end", start + 0.3)
        end = min(end, video_duration)

        clip = _make_text_clip(
            text=text,
            font=font,
            font_size=style.font_size,
            color=style.active_color,
            position=(style.position),
            start=start,
            end=end,
            stroke_color=style.outline_color,
            stroke_width=style.outline_width,
        )
        clips.append(clip)
    return clips


def _build_highlight(words, font, style, video_duration):
    clips = []
    for i, word_info in enumerate(words):
        text = word_info.get("word", "").strip()
        if not text:
            continue
        start = word_info.get("start", 0)
        end = word_info.get("end", start + 0.3)
        end = min(end, video_duration)

        clip = _make_text_clip(
            text=text,
            font=font,
            font_size=style.font_size,
            color=style.active_color,
            position=(style.position),
            start=start,
            end=end,
            stroke_color=style.outline_color,
            stroke_width=style.outline_width,
        )
        clips.append(clip)
    return clips


def _build_allcaps(words, font, style, video_duration):
    clips = []
    large_size = int(style.font_size * 1.3)
    for word_info in words:
        text = word_info.get("word", "").strip().upper()
        if not text:
            continue
        start = word_info.get("start", 0)
        end = word_info.get("end", start + 0.3)
        end = min(end, video_duration)

        shadow = _make_text_clip(
            text=text,
            font=font,
            font_size=large_size,
            color=style.outline_color,
            position=("center", "center+3"),
            start=start,
            end=end,
        )
        main = _make_text_clip(
            text=text,
            font=font,
            font_size=large_size,
            color=style.active_color,
            position=(style.position),
            start=start,
            end=end,
        )
        clips.extend([shadow, main])
    return clips


def _build_rolling(words, font, style, video_duration):
    clips = []
    i = 0
    while i < len(words):
        w1 = words[i]
        text1 = w1.get("word", "").strip()
        start = w1.get("start", 0)

        if i + 1 < len(words):
            w2 = words[i + 1]
            text2 = w2.get("word", "").strip()
            end = w2.get("end", w2.get("start", start) + 0.3)
            end = min(end, video_duration)
            display_text = f"{text1} {text2}"
        else:
            end = w1.get("end", start + 0.3)
            end = min(end, video_duration)
            display_text = text1

        clip = _make_text_clip(
            text=display_text,
            font=font,
            font_size=style.font_size,
            color=style.active_color,
            position=(style.position),
            start=start,
            end=end,
            stroke_color=style.outline_color,
            stroke_width=style.outline_width,
        )
        clips.append(clip)
        i += 2

    return clips
