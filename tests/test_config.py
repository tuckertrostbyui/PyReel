import pytest

from pyreel.config import (
    CropConfig,
    CropStrategy,
    PyReelConfig,
    SeriesMode,
    StoryMode,
    SubtitleStyle,
    SubtitleStyleConfig,
)


class TestEnums:
    def test_story_mode_values(self):
        assert StoryMode.FETCH == "fetch"
        assert StoryMode.LLM_REWRITE == "rewrite"
        assert StoryMode.LLM_WRITE == "write"
        assert StoryMode.LLM_SUMMARIZE == "summarize"

    def test_series_mode_values(self):
        assert SeriesMode.SINGLE == "single"
        assert SeriesMode.SPLIT == "split"

    def test_subtitle_style_values(self):
        assert SubtitleStyle.BOLD_WHITE == "bold_white"
        assert SubtitleStyle.HIGHLIGHT == "highlight"
        assert SubtitleStyle.ALLCAPS == "allcaps"
        assert SubtitleStyle.ROLLING == "rolling"

    def test_crop_strategy_values(self):
        assert CropStrategy.CENTER == "center"
        assert CropStrategy.CUSTOM == "custom"

    def test_enums_are_strings(self):
        for enum_cls in [StoryMode, SeriesMode, SubtitleStyle, CropStrategy]:
            for member in enum_cls:
                assert isinstance(member, str), f"{member} should be a str"


class TestSubtitleStyleConfig:
    def test_defaults(self):
        s = SubtitleStyleConfig()
        assert s.style == SubtitleStyle.BOLD_WHITE
        assert s.font is None
        assert s.font_size == 80
        assert s.active_color == "white"
        assert s.inactive_color == "#888888"
        assert s.outline_color == "black"
        assert s.outline_width == 3
        assert s.position == ("center", 1350)

    def test_custom_values(self):
        s = SubtitleStyleConfig(style=SubtitleStyle.ALLCAPS, font_size=100)
        assert s.style == SubtitleStyle.ALLCAPS
        assert s.font_size == 100


class TestCropConfig:
    def test_defaults(self):
        c = CropConfig()
        assert c.strategy == CropStrategy.CENTER
        assert c.custom_x is None
        assert c.custom_y is None

    def test_custom_values(self):
        c = CropConfig(strategy=CropStrategy.CUSTOM, custom_x=100, custom_y=200)
        assert c.strategy == CropStrategy.CUSTOM
        assert c.custom_x == 100
        assert c.custom_y == 200


class TestPyReelConfig:
    def test_defaults(self):
        c = PyReelConfig()
        assert c.story_mode == StoryMode.FETCH
        assert c.series_mode == SeriesMode.SINGLE
        assert c.max_duration == 60
        assert c.reddit_client_id is None
        assert c.reddit_client_secret is None
        assert c.reddit_user_agent == "pyreel/0.1.0"
        assert c.llm_provider is None
        assert c.llm_api_key is None
        assert c.tts_voice == "en-US-GuyNeural"
        assert c.tts_rate == "+0%"
        assert c.whisper_model == "base"
        assert c.whisper_device == "cpu"
        assert c.broll_local_path is None
        assert c.burn_subtitles is True
        assert c.output_dir == "./output"
        assert c.keep_artifacts is False
        assert c.nsfw_filter is True
        assert c.dry_run is False

    def test_nested_crop_default(self):
        c = PyReelConfig()
        assert isinstance(c.crop, CropConfig)
        assert c.crop.strategy == CropStrategy.CENTER

    def test_nested_subtitle_style_default(self):
        c = PyReelConfig()
        assert isinstance(c.subtitle_style, SubtitleStyleConfig)
        assert c.subtitle_style.style == SubtitleStyle.BOLD_WHITE

    def test_nested_configs_are_independent(self):
        c1 = PyReelConfig()
        c2 = PyReelConfig()
        c1.crop.custom_x = 42
        assert c2.crop.custom_x is None

    def test_override_fields(self):
        c = PyReelConfig(
            story_mode=StoryMode.LLM_REWRITE,
            max_duration=30,
            dry_run=True,
        )
        assert c.story_mode == StoryMode.LLM_REWRITE
        assert c.max_duration == 30
        assert c.dry_run is True
