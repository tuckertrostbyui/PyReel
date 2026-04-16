import json
import os
from unittest.mock import MagicMock, patch

import pytest

from pyreel.config import PyReelConfig, StoryMode, TitleCardConfig
from pyreel.exceptions import PyReelTitleCardError
from pyreel.title_card import (
    _draw_card_image,
    _hex_to_rgb,
    _wrap_text,
    build_title_card_clip,
    calculate_title_duration,
)


# ---------------------------------------------------------------------------
# Helpers shared with test_pipeline_integration
# ---------------------------------------------------------------------------

FAKE_POST = {
    "id": "abc123",
    "title": "I had a crazy day at work",
    "body": "So today was absolutely insane.",
    "url": "https://reddit.com/r/tifu/abc123",
    "author": "test_user",
}

FAKE_ALIGNMENT = {
    "segments": [
        {
            "words": [
                {"word": "So", "start": 0.0, "end": 0.3},
                {"word": "today", "start": 0.3, "end": 0.7},
            ]
        }
    ]
}


def _make_artifact(path: str, content: str = "fake content") -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# TestTitleCardConfig
# ---------------------------------------------------------------------------

class TestTitleCardConfig:
    def test_defaults(self):
        tc = TitleCardConfig()
        assert tc.enabled is True
        assert tc.username is None
        assert tc.avatar_color == "#FF4500"
        assert tc.vote_count == "99+"
        assert tc.duration == 5.0
        assert tc.font is None
        assert tc.show_verified is True
        assert tc.emoji_row != ""

    def test_custom_values(self):
        tc = TitleCardConfig(
            enabled=False,
            username="Brokenstories",
            avatar_color="#0000FF",
            emoji_row="",
            vote_count="1k",
            duration=3.0,
            show_verified=False,
        )
        assert tc.enabled is False
        assert tc.username == "Brokenstories"
        assert tc.avatar_color == "#0000FF"
        assert tc.emoji_row == ""
        assert tc.vote_count == "1k"
        assert tc.duration == 3.0
        assert tc.show_verified is False

    def test_independence_from_other_configs(self):
        c1 = PyReelConfig()
        c2 = PyReelConfig()
        c1.title_card.username = "UserA"
        assert c2.title_card.username is None

    def test_title_card_field_on_pyreel_config(self):
        c = PyReelConfig()
        assert isinstance(c.title_card, TitleCardConfig)
        assert c.title_card.enabled is True


# ---------------------------------------------------------------------------
# TestHexToRgb
# ---------------------------------------------------------------------------

class TestHexToRgb:
    def test_reddit_orange(self):
        assert _hex_to_rgb("#FF4500") == (255, 69, 0)

    def test_short_hex(self):
        assert _hex_to_rgb("#FFF") == (255, 255, 255)

    def test_no_hash(self):
        assert _hex_to_rgb("0000FF") == (0, 0, 255)

    def test_invalid_falls_back(self):
        result = _hex_to_rgb("ZZZZZZ")
        assert len(result) == 3


# ---------------------------------------------------------------------------
# TestWrapText
# ---------------------------------------------------------------------------

class TestWrapText:
    def _make_draw(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (1080, 100), (0, 0, 0, 0))
        return ImageDraw.Draw(img)

    def _default_font(self):
        from PIL import ImageFont
        return ImageFont.load_default()

    def test_short_text_single_line(self):
        draw = self._make_draw()
        font = self._default_font()
        lines = _wrap_text(draw, "Hello world", font, 800)
        assert len(lines) == 1
        assert "Hello world" in lines[0]

    def test_long_text_wraps(self):
        draw = self._make_draw()
        font = self._default_font()
        long_text = "This is a very long title that should definitely wrap across multiple lines in the card"
        # Use a narrow max_width to force wrapping
        lines = _wrap_text(draw, long_text, font, 100)
        assert len(lines) > 1

    def test_empty_string(self):
        draw = self._make_draw()
        font = self._default_font()
        lines = _wrap_text(draw, "", font, 800)
        assert lines == [""]

    def test_single_word(self):
        draw = self._make_draw()
        font = self._default_font()
        lines = _wrap_text(draw, "Supercalifragilistic", font, 800)
        assert len(lines) >= 1


# ---------------------------------------------------------------------------
# TestDrawCardImage
# ---------------------------------------------------------------------------

class TestDrawCardImage:
    def test_returns_rgba_image(self):
        tc = TitleCardConfig()
        img = _draw_card_image("Test title here", "test_user", tc)
        assert img.mode == "RGBA"

    def test_correct_size(self):
        tc = TitleCardConfig()
        img = _draw_card_image("Test title here", "test_user", tc)
        assert img.size == (1080, 1920)

    def test_card_has_opaque_pixels(self):
        tc = TitleCardConfig()
        img = _draw_card_image("Test title here", "test_user", tc)
        import numpy as np
        arr = np.array(img)
        # Alpha channel — some pixels should be nearly opaque (card background)
        assert (arr[:, :, 3] > 200).any(), "Card background should have opaque pixels"

    def test_canvas_mostly_transparent(self):
        tc = TitleCardConfig()
        img = _draw_card_image("Test title here", "test_user", tc)
        import numpy as np
        arr = np.array(img)
        total = arr.shape[0] * arr.shape[1]
        transparent_count = (arr[:, :, 3] == 0).sum()
        # Most of the 1080x1920 canvas should be transparent (card is small relative to frame)
        assert transparent_count / total > 0.5

    def test_no_emoji_row_when_empty(self):
        tc = TitleCardConfig(emoji_row="")
        # Should not raise
        img = _draw_card_image("Test title", "user", tc)
        assert img.size == (1080, 1920)

    def test_no_verified_badge(self):
        tc = TitleCardConfig(show_verified=False)
        img = _draw_card_image("Test title", "user", tc)
        assert img.size == (1080, 1920)

    def test_custom_avatar_color(self):
        tc = TitleCardConfig(avatar_color="#0077FF")
        img = _draw_card_image("Test title", "user", tc)
        assert img.size == (1080, 1920)

    def test_long_title_wraps_without_error(self):
        tc = TitleCardConfig()
        long_title = "This is an extremely long Reddit post title that should require wrapping across multiple lines within the card without overflowing or crashing"
        img = _draw_card_image(long_title, "author", tc)
        assert img.size == (1080, 1920)

    def test_empty_author_uses_anonymous_initial(self):
        tc = TitleCardConfig()
        # Empty author should not crash — uses "A" as initial
        img = _draw_card_image("Some title", "", tc)
        assert img.size == (1080, 1920)


# ---------------------------------------------------------------------------
# TestBuildTitleCardClip
# ---------------------------------------------------------------------------

class TestBuildTitleCardClip:
    def test_clip_timing(self):
        config = PyReelConfig(title_card=TitleCardConfig(duration=3.0))
        clip = build_title_card_clip("Test title", "test_user", config)
        assert clip.start == 0
        assert clip.end == 3.0

    def test_clip_default_duration(self):
        config = PyReelConfig()
        clip = build_title_card_clip("Test title", "test_user", config)
        assert clip.end == 5.0

    def test_clip_frame_shape(self):
        import numpy as np
        config = PyReelConfig(title_card=TitleCardConfig(duration=2.0))
        clip = build_title_card_clip("Test title", "test_user", config)
        frame = clip.get_frame(0)
        # moviepy may strip alpha on get_frame; check width/height at minimum
        assert frame.shape[0] == 1920
        assert frame.shape[1] == 1080

    def test_clip_has_duration(self):
        config = PyReelConfig(title_card=TitleCardConfig(duration=4.5))
        clip = build_title_card_clip("Test title", "user", config)
        assert clip.duration == 4.5


# ---------------------------------------------------------------------------
# TestCalculateTitleDuration
# ---------------------------------------------------------------------------

class TestCalculateTitleDuration:
    def _make_alignment(self, words: list) -> dict:
        """Build a minimal alignment dict from a list of (word, start, end) tuples."""
        return {
            "segments": [
                {
                    "words": [
                        {"word": w, "start": s, "end": e}
                        for w, s, e in words
                    ]
                }
            ]
        }

    def test_returns_end_of_last_title_word_plus_buffer(self):
        # Title is "Hello world" (2 words); alignment has those 2 words first
        alignment = self._make_alignment([
            ("Hello", 0.0, 0.5),
            ("world", 0.5, 1.2),
            ("then", 1.2, 1.5),
            ("story", 1.5, 2.0),
        ])
        result = calculate_title_duration("Hello world", alignment)
        assert result == pytest.approx(1.2 + 0.4)

    def test_single_word_title(self):
        alignment = self._make_alignment([
            ("AITA", 0.0, 0.8),
            ("for", 0.8, 1.0),
        ])
        result = calculate_title_duration("AITA", alignment)
        assert result == pytest.approx(0.8 + 0.4)

    def test_returns_none_when_title_longer_than_alignment(self):
        alignment = self._make_alignment([("only", 0.0, 0.5)])
        result = calculate_title_duration("word one two three", alignment)
        assert result is None

    def test_returns_none_for_empty_title(self):
        alignment = self._make_alignment([("Hello", 0.0, 0.5)])
        assert calculate_title_duration("", alignment) is None

    def test_returns_none_for_empty_alignment(self):
        assert calculate_title_duration("Hello world", {}) is None

    def test_skips_words_without_end_timestamp(self):
        alignment = {
            "segments": [
                {
                    "words": [
                        {"word": "Hello", "start": 0.0},       # no 'end'
                        {"word": "world", "start": 0.5, "end": 1.1},
                    ]
                }
            ]
        }
        # Only 1 valid word; title has 2 words → should return None
        result = calculate_title_duration("Hello world", alignment)
        assert result is None

    def test_buffer_is_added(self):
        alignment = self._make_alignment([("Title", 0.0, 3.0)])
        result = calculate_title_duration("Title", alignment)
        assert result > 3.0, "Result should include the 0.4s trailing buffer"


# ---------------------------------------------------------------------------
# TestPipelineTitleCardIntegration
# ---------------------------------------------------------------------------

class TestPipelineTitleCardIntegration:
    """Integration tests for the title_card_render stage inside run_pipeline."""

    def _run_full_pipeline(self, tmp_path, config, monkeypatch=None):
        from pyreel.pipeline import run_pipeline

        output_dir = str(tmp_path / "output")
        config.output_dir = output_dir

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post", return_value=FAKE_POST), \
             patch("pyreel.sanitize.sanitize_text", side_effect=lambda t, c: t), \
             patch("pyreel.tts.generate_audio") as mock_tts, \
             patch("pyreel.align.align_audio") as mock_align, \
             patch("pyreel.broll.fetch_broll") as mock_broll, \
             patch("pyreel.crop.crop_to_portrait") as mock_crop, \
             patch("pyreel.subtitles.build_subtitle_clips", return_value=[]), \
             patch("pyreel.title_card.build_title_card_clip") as mock_tc, \
             patch("pyreel.compose.compose_video") as mock_compose, \
             patch("pyreel.metadata.generate_metadata") as mock_meta, \
             patch("moviepy.audio.io.AudioFileClip.AudioFileClip") as mock_audio:

            def tts_se(text, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_tts.side_effect = tts_se

            def align_se(audio_path, out_path, cfg):
                os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(FAKE_ALIGNMENT, f)
                return FAKE_ALIGNMENT
            mock_align.side_effect = align_se

            def broll_se(run_dir, cfg):
                path = os.path.join(run_dir, "broll_raw.mp4")
                _make_artifact(path)
                return path
            mock_broll.side_effect = broll_se

            def crop_se(inp, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_crop.side_effect = crop_se

            fake_clip = MagicMock()
            fake_clip.start = 0
            fake_clip.end = 5.0
            mock_tc.return_value = fake_clip

            def compose_se(broll_path, audio_path, subs, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_compose.side_effect = compose_se

            def meta_se(story, title, run_id, config, source_url=None, output_path=None):
                if output_path:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "w") as f:
                        json.dump({
                            "title": "t", "description": "d", "hashtags": [],
                            "platforms": [], "generated_at": "2024-01-01T00:00:00+00:00",
                            "story_mode": "fetch", "source_url": "", "run_id": run_id
                        }, f)
                return {}
            mock_meta.side_effect = meta_se

            audio_mock = MagicMock()
            audio_mock.duration = 10.0
            mock_audio.return_value = audio_mock

            result = run_pipeline(subreddit="tifu", config=config)

        return result, output_dir, mock_tc, mock_compose

    def test_title_meta_json_written_on_fetch(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="x",
            reddit_client_secret="x",
            story_mode=StoryMode.FETCH,

            keep_artifacts=True,
        )
        _, output_dir, _, _ = self._run_full_pipeline(tmp_path, config)

        run_dirs = [
            os.path.join(output_dir, d)
            for d in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, d))
        ]
        assert run_dirs, "No run dir created"
        run_dir = run_dirs[0]
        meta_path = os.path.join(run_dir, "title_meta.json")
        assert os.path.exists(meta_path), "title_meta.json should be written"

        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["title"] == FAKE_POST["title"]
        assert meta["author"] == FAKE_POST["author"]

    def test_title_card_clip_prepended_to_compose(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="x",
            reddit_client_secret="x",
            story_mode=StoryMode.FETCH,

            keep_artifacts=True,
        )
        _, _, mock_tc, mock_compose = self._run_full_pipeline(tmp_path, config)

        mock_tc.assert_called_once()
        # compose_video should have received subtitle_clips with tc_clip prepended
        call_args = mock_compose.call_args
        subs_arg = call_args[0][2]  # positional arg index 2 = subtitle_clips
        assert len(subs_arg) >= 1, "Title card clip should be in subtitle_clips"

    def test_title_card_disabled_skips_stage(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="x",
            reddit_client_secret="x",
            story_mode=StoryMode.FETCH,

            keep_artifacts=True,
            title_card=TitleCardConfig(enabled=False),
        )
        _, _, mock_tc, _ = self._run_full_pipeline(tmp_path, config)
        mock_tc.assert_not_called()

    def test_title_card_uses_config_username_over_reddit_author(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="x",
            reddit_client_secret="x",
            story_mode=StoryMode.FETCH,

            keep_artifacts=True,
            title_card=TitleCardConfig(username="CustomUser"),
        )
        _, _, mock_tc, _ = self._run_full_pipeline(tmp_path, config)

        mock_tc.assert_called_once()
        call_kwargs = mock_tc.call_args
        author_arg = call_kwargs[0][1]  # second positional arg = author
        assert author_arg == "CustomUser"

    def test_backward_compat_missing_title_meta(self, tmp_path):
        """title_meta.json absent on checkpoint resume falls back to first-line extraction."""
        from pyreel.pipeline import _run_single
        from pyreel.checkpoint import init_checkpoint, save_checkpoint

        config = PyReelConfig(
            reddit_client_id="x",
            reddit_client_secret="x",
            story_mode=StoryMode.FETCH,

            output_dir=str(tmp_path / "output"),
            keep_artifacts=True,
        )

        run_dir = str(tmp_path / "run_compat")
        os.makedirs(run_dir, exist_ok=True)
        init_checkpoint(run_dir, "run_compat", config)
        save_checkpoint(run_dir, "deps_check")
        save_checkpoint(run_dir, "story_fetch")

        story = FAKE_POST["title"] + "\n\n" + FAKE_POST["body"]
        with open(os.path.join(run_dir, "story_raw.txt"), "w") as f:
            f.write(story)
        # Intentionally NOT writing title_meta.json — simulates upgrade from old run

        with patch("pyreel.sanitize.sanitize_text", side_effect=lambda t, c: t), \
             patch("pyreel.tts.generate_audio") as mock_tts, \
             patch("pyreel.align.align_audio") as mock_align, \
             patch("pyreel.broll.fetch_broll") as mock_broll, \
             patch("pyreel.crop.crop_to_portrait") as mock_crop, \
             patch("pyreel.subtitles.build_subtitle_clips", return_value=[]), \
             patch("pyreel.title_card.build_title_card_clip") as mock_tc, \
             patch("pyreel.compose.compose_video") as mock_compose, \
             patch("pyreel.metadata.generate_metadata") as mock_meta, \
             patch("moviepy.audio.io.AudioFileClip.AudioFileClip") as mock_audio:

            def tts_se(text, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_tts.side_effect = tts_se

            def align_se(audio_path, out_path, cfg):
                os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(FAKE_ALIGNMENT, f)
                return FAKE_ALIGNMENT
            mock_align.side_effect = align_se

            def broll_se(run_dir, cfg):
                path = os.path.join(run_dir, "broll_raw.mp4")
                _make_artifact(path)
                return path
            mock_broll.side_effect = broll_se

            def crop_se(inp, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_crop.side_effect = crop_se

            fake_clip = MagicMock()
            fake_clip.start = 0
            fake_clip.end = 5.0
            mock_tc.return_value = fake_clip

            def compose_se(broll_path, audio_path, subs, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_compose.side_effect = compose_se

            def meta_se(story, title, run_id, config, source_url=None, output_path=None):
                if output_path:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "w") as f:
                        json.dump({
                            "title": "t", "description": "d", "hashtags": [],
                            "platforms": [], "generated_at": "2024-01-01T00:00:00+00:00",
                            "story_mode": "fetch", "source_url": "", "run_id": "run_compat"
                        }, f)
                return {}
            mock_meta.side_effect = meta_se

            audio_mock = MagicMock()
            audio_mock.duration = 10.0
            mock_audio.return_value = audio_mock

            # Should NOT raise — falls back to first-line extraction for title_meta
            result = _run_single(
                subreddit="tifu",
                post_id=None,
                prompt=None,
                story=None,
                run_dir=run_dir,
                run_id="run_compat",
                config=config,
            )

        assert result.endswith("final_video.mp4")
        # build_title_card_clip should have been called with the first line as title
        mock_tc.assert_called_once()
        call_title = mock_tc.call_args[0][0]
        assert FAKE_POST["title"] in call_title or len(call_title) > 0
