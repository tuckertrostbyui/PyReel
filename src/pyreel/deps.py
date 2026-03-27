import shutil
import sys
from typing import Optional

from .config import BrollSource, PyReelConfig, StoryMode
from .exceptions import PyReelDepsError


def check_dependencies(config: Optional[PyReelConfig] = None) -> dict:
    issues = []
    warnings = []

    # 1. FFmpeg
    if not shutil.which("ffmpeg"):
        issues.append(
            "FFmpeg not found. Install it:\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )

    # 2. ImageMagick
    if not shutil.which("convert"):
        issues.append(
            "ImageMagick not found. Install it:\n"
            "  macOS:   brew install imagemagick\n"
            "  Ubuntu:  sudo apt install imagemagick\n"
            "  Windows: https://imagemagick.org/script/download.php"
        )

    # 3. Python >= 3.11
    if sys.version_info < (3, 11):
        issues.append(
            f"Python >= 3.11 required. Current version: {sys.version}"
        )

    if config is not None:
        # 4. Reddit credentials
        if config.story_mode == StoryMode.FETCH:
            if not config.reddit_client_id:
                issues.append(
                    "story_mode=FETCH requires reddit_client_id in PyReelConfig."
                )
            if not config.reddit_client_secret:
                issues.append(
                    "story_mode=FETCH requires reddit_client_secret in PyReelConfig."
                )

        # 5. LLM config
        llm_modes = {StoryMode.LLM_REWRITE, StoryMode.LLM_WRITE, StoryMode.LLM_SUMMARIZE}
        if config.story_mode in llm_modes:
            if not config.llm_provider:
                issues.append(
                    f"story_mode={config.story_mode.value} requires llm_provider in PyReelConfig."
                )
            if not config.llm_api_key:
                issues.append(
                    f"story_mode={config.story_mode.value} requires llm_api_key in PyReelConfig."
                )

        # 6. Pexels key
        if config.broll_source == BrollSource.PEXELS:
            if not config.pexels_api_key:
                issues.append(
                    "broll_source=PEXELS requires pexels_api_key in PyReelConfig."
                )

        # 7. Pixabay key
        if config.broll_source == BrollSource.PIXABAY:
            if not config.pixabay_api_key:
                issues.append(
                    "broll_source=PIXABAY requires pixabay_api_key in PyReelConfig."
                )

        # 8. Local path
        if config.broll_source == BrollSource.LOCAL:
            import os
            if not config.broll_local_path:
                issues.append(
                    "broll_source=LOCAL requires broll_local_path in PyReelConfig."
                )
            elif not os.path.exists(config.broll_local_path):
                issues.append(
                    f"broll_local_path does not exist: {config.broll_local_path}"
                )

    for warning in warnings:
        print(f"[PyReel WARNING] {warning}")

    result = {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}

    if issues:
        raise PyReelDepsError(
            "Dependency check failed:\n" + "\n".join(f"  - {i}" for i in issues)
        )

    return result
