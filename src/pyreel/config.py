from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


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
    position: Union[str, tuple] = ("center", 1350)  # str or (x, y) tuple — passed to moviepy with_position()


@dataclass
class CropConfig:
    strategy: CropStrategy = CropStrategy.CENTER
    custom_x: Optional[int] = None
    custom_y: Optional[int] = None


@dataclass
class TitleCardConfig:
    enabled: bool = True
    username: Optional[str] = None       # None = use Reddit author; falls back to "Anonymous"
    avatar_color: str = "#FF4500"        # Reddit orange; ignored when avatar_image is set
    avatar_image: Optional[str] = None   # Path to an image file to use as the avatar
    emoji_row: str = "🎭😱💔🤯🌟😤🔥"    # set to "" to hide the row
    vote_count: str = "99+"
    duration: float = 5.0               # seconds the card is visible
    font: Optional[str] = None          # None = auto-detect system sans-serif
    show_verified: bool = True
    card_position: str = "bottom"       # "bottom", "center", or "top"


@dataclass
class PyReelConfig:
    # Story
    story_mode: StoryMode = StoryMode.FETCH
    series_mode: SeriesMode = SeriesMode.SINGLE
    min_duration: Optional[int] = None
    max_duration: int = 60

    # Reddit
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "pyreel/0.1.0"
    history_file: Optional[str] = None  # path to per-account post history JSON

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
    broll_local_path: Optional[str] = None  # None = auto-discover from ./data/broll/

    # Crop
    crop: CropConfig = field(default_factory=CropConfig)

    # Subtitles
    subtitle_style: SubtitleStyleConfig = field(default_factory=SubtitleStyleConfig)
    burn_subtitles: bool = True

    # Title card
    title_card: TitleCardConfig = field(default_factory=TitleCardConfig)

    # Output
    output_dir: str = "./output"
    keep_artifacts: bool = False
    nsfw_filter: bool = True
    dry_run: bool = False
