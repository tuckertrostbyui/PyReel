import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyreel.config import PyReelConfig, StoryMode
from pyreel.exceptions import PyReelDepsError, PyReelPipelineError
from pyreel.pipeline import run_pipeline


FAKE_POST = {
    "id": "abc123",
    "title": "I had a crazy day at work",
    "body": "So today was absolutely insane. My boss called me into the office.",
    "url": "https://reddit.com/r/tifu/abc123",
    "author": "test_user",
}

FAKE_ALIGNMENT = {
    "segments": [
        {
            "words": [
                {"word": "So", "start": 0.0, "end": 0.3},
                {"word": "today", "start": 0.3, "end": 0.7},
                {"word": "was", "start": 0.7, "end": 1.0},
            ]
        }
    ]
}


def _make_artifact(path: str, content: str = "fake content") -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _make_artifact_side_effect(artifact_path: str, return_value=None):
    def side_effect(*args, **kwargs):
        _make_artifact(artifact_path)
        return return_value or artifact_path
    return side_effect


def _make_json_artifact_side_effect(artifact_path: str, data: dict):
    def side_effect(*args, **kwargs):
        os.makedirs(os.path.dirname(os.path.abspath(artifact_path)), exist_ok=True)
        with open(artifact_path, "w") as f:
            json.dump(data, f)
        return data
    return side_effect


def _meta_side_effect(story, title, run_id, config, source_url=None, output_path=None):
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump({
                "title": "t", "description": "d", "hashtags": [],
                "platforms": [], "generated_at": "2024-01-01T00:00:00+00:00",
                "story_mode": "fetch", "source_url": "", "run_id": run_id,
            }, f)
    return {}


@pytest.fixture
def basic_config(tmp_path):
    return PyReelConfig(
        reddit_client_id="test_id",
        reddit_client_secret="test_secret",
        story_mode=StoryMode.FETCH,
    
        output_dir=str(tmp_path / "output"),
        keep_artifacts=True,
    )


def _patch_all_stages(config, monkeypatch_or_patch=None):
    """Returns a dict of patch targets."""
    return {
        "pyreel.deps.check_dependencies": MagicMock(
            return_value={"passed": True, "issues": []}
        ),
        "pyreel.subtitles.check_and_patch_imagemagick": MagicMock(return_value=False),
        "pyreel.reddit.fetch_post": MagicMock(return_value=FAKE_POST),
        "pyreel.sanitize.sanitize_text": MagicMock(side_effect=lambda text, cfg: text),
    }


class TestPipelineSingleMode:
    def test_returns_list_of_strings(self, tmp_path, basic_config):
        output_dir = str(tmp_path / "output")
        basic_config.output_dir = output_dir

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post", return_value=FAKE_POST), \
             patch("pyreel.sanitize.sanitize_text", side_effect=lambda t, c: t), \
             patch("pyreel.tts.generate_audio") as mock_tts, \
             patch("pyreel.align.align_audio") as mock_align, \
             patch("pyreel.broll.fetch_broll") as mock_broll, \
             patch("pyreel.crop.crop_to_portrait") as mock_crop, \
             patch("pyreel.subtitles.build_subtitle_clips", return_value=[]), \
             patch("pyreel.compose.compose_video") as mock_compose, \
             patch("pyreel.metadata.generate_metadata") as mock_meta, \
             patch("moviepy.audio.io.AudioFileClip.AudioFileClip") as mock_audio:

            # Set up side effects that create artifact files
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

            def compose_se(broll_path, audio_path, subs, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_compose.side_effect = compose_se

            mock_meta.side_effect = _meta_side_effect

            audio_mock = MagicMock()
            audio_mock.duration = 10.0
            mock_audio.return_value.__enter__ = MagicMock(return_value=audio_mock)
            mock_audio.return_value.__exit__ = MagicMock(return_value=False)
            mock_audio.return_value = audio_mock

            result = run_pipeline(subreddit="tifu", config=basic_config)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], str)
        assert result[0].endswith("final_video.mp4")

    def test_dry_run_returns_empty_list(self, tmp_path):
        config = PyReelConfig(
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False):
            result = run_pipeline(subreddit="tifu", config=config)

        assert result == []

    def test_dry_run_skips_all_processing_stages(self, tmp_path):
        config = PyReelConfig(
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        )

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post") as mock_reddit, \
             patch("pyreel.tts.generate_audio") as mock_tts:

            result = run_pipeline(subreddit="tifu", config=config)

        assert result == []
        mock_reddit.assert_not_called()
        mock_tts.assert_not_called()

    def test_pipeline_error_raised_on_stage_failure(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="test_id",
            reddit_client_secret="test_secret",
            story_mode=StoryMode.FETCH,
            output_dir=str(tmp_path / "output"),
            keep_artifacts=True,
        )

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post", side_effect=Exception("Reddit API down")):

            with pytest.raises(PyReelPipelineError) as exc_info:
                run_pipeline(subreddit="tifu", config=config)

        assert "story_fetch" in str(exc_info.value)

    def test_pipeline_error_contains_stage_name_tts(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="test_id",
            reddit_client_secret="test_secret",
            story_mode=StoryMode.FETCH,
            output_dir=str(tmp_path / "output"),
            keep_artifacts=True,
        )

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post", return_value=FAKE_POST), \
             patch("pyreel.sanitize.sanitize_text", side_effect=lambda t, c: t), \
             patch("pyreel.tts.generate_audio", side_effect=Exception("TTS failed")):

            with pytest.raises(PyReelPipelineError) as exc_info:
                run_pipeline(subreddit="tifu", config=config)

        assert "tts_generate" in str(exc_info.value)

    def test_deps_error_raises_pipeline_error(self, tmp_path):
        config = PyReelConfig(
            output_dir=str(tmp_path / "output"),
        )

        with patch("pyreel.deps.check_dependencies", side_effect=PyReelDepsError("FFmpeg not found")):
            with pytest.raises(PyReelPipelineError) as exc_info:
                run_pipeline(subreddit="tifu", config=config)

        assert "deps_check" in str(exc_info.value)


class TestCheckpointSkipping:
    def test_checkpoint_skips_completed_stage(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="test_id",
            reddit_client_secret="test_secret",
            story_mode=StoryMode.FETCH,
            output_dir=str(tmp_path / "output"),
            keep_artifacts=True,
        )

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post", return_value=FAKE_POST) as mock_reddit, \
             patch("pyreel.sanitize.sanitize_text", side_effect=lambda t, c: t), \
             patch("pyreel.tts.generate_audio") as mock_tts, \
             patch("pyreel.align.align_audio") as mock_align, \
             patch("pyreel.broll.fetch_broll") as mock_broll, \
             patch("pyreel.crop.crop_to_portrait") as mock_crop, \
             patch("pyreel.subtitles.build_subtitle_clips", return_value=[]), \
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

            def compose_se(broll_path, audio_path, subs, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_compose.side_effect = compose_se

            mock_meta.side_effect = _meta_side_effect

            audio_mock = MagicMock()
            audio_mock.duration = 10.0
            mock_audio.return_value = audio_mock

            result = run_pipeline(subreddit="tifu", config=config)

        # reddit.fetch_post should have been called exactly once
        mock_reddit.assert_called_once()

    def test_run_config_json_written(self, tmp_path):
        config = PyReelConfig(
            reddit_client_id="test_id",
            reddit_client_secret="test_secret",
            story_mode=StoryMode.FETCH,
            output_dir=str(tmp_path / "output"),
            keep_artifacts=True,
        )

        with patch("pyreel.deps.check_dependencies", return_value={"passed": True, "issues": []}), \
             patch("pyreel.subtitles.check_and_patch_imagemagick", return_value=False), \
             patch("pyreel.reddit.fetch_post", return_value=FAKE_POST), \
             patch("pyreel.sanitize.sanitize_text", side_effect=lambda t, c: t), \
             patch("pyreel.tts.generate_audio") as mock_tts, \
             patch("pyreel.align.align_audio") as mock_align, \
             patch("pyreel.broll.fetch_broll") as mock_broll, \
             patch("pyreel.crop.crop_to_portrait") as mock_crop, \
             patch("pyreel.subtitles.build_subtitle_clips", return_value=[]), \
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

            def compose_se(broll_path, audio_path, subs, out_path, cfg):
                _make_artifact(out_path)
                return out_path
            mock_compose.side_effect = compose_se

            mock_meta.side_effect = _meta_side_effect

            audio_mock = MagicMock()
            audio_mock.duration = 10.0
            mock_audio.return_value = audio_mock

            result = run_pipeline(subreddit="tifu", config=config)

        # Find the run directory
        output_dir = str(tmp_path / "output")
        run_dirs = [
            os.path.join(output_dir, d)
            for d in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, d))
        ]
        assert len(run_dirs) >= 1
        run_dir = run_dirs[0]
        run_config_path = os.path.join(run_dir, "run_config.json")
        assert os.path.exists(run_config_path), "run_config.json should be written"
        assert os.path.getsize(run_config_path) > 0
