from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BrollSource(str, Enum):
    YTDLP = "yt-dlp"
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    LOCAL = "local"


class StoryMode(str, Enum):
    FETCH = "fetch"
    LLM_REWRITE = "rewrite"
    LLM_WRITE = "write"
    LLM_SUMMARIZE = "summarize"


class SeriesMode(str, Enum):
    SINGLE = "single"
    SPLIT = "split"


class SubtitleStyle(str, Enum):
    BOLD_WHITE = "bold_white"
    HIGHLIGHT = "highlight"
    ALLCAPS = "allcaps"
    ROLLING = "rolling"


class CropStrategy(str, Enum):
    CENTER = "center"
    CUSTOM = "custom"


@dataclass
class SubtitleStyleConfig:
    style: SubtitleStyle = SubtitleStyle.BOLD_WHITE
    font: Optional[str] = None
    font_size: int = 80
    active_color: str = "white"
    inactive_color: str = "#888888"
    outline_color: str = "black"
    outline_width: int = 3
    position: str = "center"
    words_per_segment: int = 1


@dataclass
class CropConfig:
    strategy: CropStrategy = CropStrategy.CENTER
    custom_x: Optional[int] = None
    custom_y: Optional[int] = None


@dataclass
class PyReelConfig:
    # Story
    story_mode: StoryMode = StoryMode.FETCH
    series_mode: SeriesMode = SeriesMode.SINGLE
    max_duration: int = 60

    # Reddit
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "pyreel/0.1.0"

    # LLM (opt-in)
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None

    # TTS
    tts_voice: str = "en-US-GuyNeural"
    tts_rate: str = "+0%"

    # WhisperX
    whisper_model: str = "base"
    whisper_device: str = "cpu"

    # B-roll
    broll_source: BrollSource = BrollSource.YTDLP
    broll_keyword: Optional[str] = None
    broll_local_path: Optional[str] = None
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None
    broll_min_duration: int = 300
    broll_candidates: int = 3

    # Crop
    crop: CropConfig = field(default_factory=CropConfig)

    # Subtitles
    subtitle_style: SubtitleStyleConfig = field(default_factory=SubtitleStyleConfig)
    burn_subtitles: bool = True

    # Output
    output_dir: str = "./output"
    keep_artifacts: bool = False
    nsfw_filter: bool = True
    dry_run: bool = False
