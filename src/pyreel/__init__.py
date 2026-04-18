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
    PyReelHistoryError,
)
from .history import PostHistory
from .deps import check_dependencies
from .pipeline import run_pipeline


def load_history(path: str) -> PostHistory:
    """Load (or create) a PostHistory from the given JSON file path."""
    return PostHistory(path)


def clear_history(path: str) -> None:
    """Clear all entries from the history file at *path*."""
    PostHistory(path).clear()


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
    "PostHistory",
    "PyReelHistoryError",
    "load_history",
    "clear_history",
]
