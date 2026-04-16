from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pyreel")
except PackageNotFoundError:
    __version__ = "0.1.0"

from .config import (
    PyReelConfig,
    SubtitleStyle,
    SubtitleStyleConfig,
    StoryMode,
    SeriesMode,
    CropStrategy,
    CropConfig,
    TitleCardConfig,
)
from .exceptions import (
    PyReelError,
    PyReelPipelineError,
    PyReelConfigError,
    PyReelDepsError,
    PyReelRedditError,
    PyReelLLMError,
    PyReelTTSError,
    PyReelAlignError,
    PyReelBrollError,
    PyReelCropError,
    PyReelSubtitleError,
    PyReelComposeError,
    PyReelTitleCardError,
)
from .deps import check_dependencies
from .pipeline import run_pipeline


def generate(
    subreddit: str | None = None,
    post_id: str | None = None,
    prompt: str | None = None,
    config: PyReelConfig | None = None,
) -> list[str]:
    return run_pipeline(
        subreddit=subreddit,
        post_id=post_id,
        prompt=prompt,
        config=config,
    )


__all__ = [
    "generate",
    "check_dependencies",
    "PyReelConfig",
    "SubtitleStyle",
    "SubtitleStyleConfig",
    "StoryMode",
    "SeriesMode",
    "CropStrategy",
    "CropConfig",
    "PyReelError",
    "PyReelPipelineError",
    "PyReelConfigError",
    "PyReelDepsError",
    "PyReelRedditError",
    "PyReelLLMError",
    "PyReelTTSError",
    "PyReelAlignError",
    "PyReelBrollError",
    "PyReelCropError",
    "PyReelSubtitleError",
    "PyReelComposeError",
    "TitleCardConfig",
    "PyReelTitleCardError",
]
