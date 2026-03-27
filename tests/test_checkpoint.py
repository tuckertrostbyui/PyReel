import json
import os

import pytest

from pyreel.checkpoint import (
    clear_checkpoint,
    init_checkpoint,
    load_checkpoint,
    save_checkpoint,
    stage_complete,
)
from pyreel.config import PyReelConfig


class TestLoadCheckpoint:
    def test_returns_none_when_no_file(self, tmp_path):
        result = load_checkpoint(str(tmp_path))
        assert result is None

    def test_returns_dict_when_file_exists(self, tmp_path):
        data = {
            "run_id": "run_test",
            "completed_stages": ["deps_check"],
            "failed_stage": None,
            "config_hash": "abc123",
        }
        cp_path = tmp_path / ".checkpoint"
        cp_path.write_text(json.dumps(data))

        result = load_checkpoint(str(tmp_path))
        assert result is not None
        assert result["run_id"] == "run_test"
        assert "deps_check" in result["completed_stages"]

    def test_returns_none_on_corrupt_json(self, tmp_path):
        cp_path = tmp_path / ".checkpoint"
        cp_path.write_text("{not valid json}")
        result = load_checkpoint(str(tmp_path))
        assert result is None


class TestSaveCheckpoint:
    def test_creates_checkpoint_file(self, tmp_path):
        save_checkpoint(str(tmp_path), "deps_check")
        cp_path = tmp_path / ".checkpoint"
        assert cp_path.exists()

    def test_stage_added_to_completed(self, tmp_path):
        save_checkpoint(str(tmp_path), "deps_check")
        save_checkpoint(str(tmp_path), "story_fetch")

        data = load_checkpoint(str(tmp_path))
        assert "deps_check" in data["completed_stages"]
        assert "story_fetch" in data["completed_stages"]

    def test_no_duplicate_stages(self, tmp_path):
        save_checkpoint(str(tmp_path), "deps_check")
        save_checkpoint(str(tmp_path), "deps_check")

        data = load_checkpoint(str(tmp_path))
        assert data["completed_stages"].count("deps_check") == 1

    def test_writes_correct_json(self, tmp_path):
        save_checkpoint(str(tmp_path), "tts_generate")
        data = load_checkpoint(str(tmp_path))
        assert isinstance(data, dict)
        assert "completed_stages" in data
        assert "tts_generate" in data["completed_stages"]


class TestStageComplete:
    def test_returns_false_when_no_checkpoint(self, tmp_path):
        assert stage_complete(str(tmp_path), "story_fetch") is False

    def test_returns_false_when_stage_not_in_checkpoint(self, tmp_path):
        save_checkpoint(str(tmp_path), "deps_check")
        assert stage_complete(str(tmp_path), "story_fetch") is False

    def test_returns_false_when_artifact_missing(self, tmp_path):
        save_checkpoint(str(tmp_path), "story_fetch")
        # story_raw.txt does not exist
        assert stage_complete(str(tmp_path), "story_fetch") is False

    def test_returns_false_when_artifact_empty(self, tmp_path):
        save_checkpoint(str(tmp_path), "story_fetch")
        artifact = tmp_path / "story_raw.txt"
        artifact.write_text("")
        assert stage_complete(str(tmp_path), "story_fetch") is False

    def test_returns_true_when_both_conditions_met(self, tmp_path):
        save_checkpoint(str(tmp_path), "story_fetch")
        artifact = tmp_path / "story_raw.txt"
        artifact.write_text("Some story content here.")
        assert stage_complete(str(tmp_path), "story_fetch") is True

    def test_returns_true_for_stage_without_artifact(self, tmp_path):
        save_checkpoint(str(tmp_path), "deps_check")
        assert stage_complete(str(tmp_path), "deps_check") is True

    def test_artifact_map_stages(self, tmp_path):
        artifact_stages = {
            "story_fetch": "story_raw.txt",
            "story_sanitize": "story_clean.txt",
            "story_prepare": "story_final.txt",
            "tts_generate": "audio.wav",
            "whisper_align": "alignment.json",
            "broll_fetch": "broll_raw.mp4",
            "broll_crop": "broll_cropped.mp4",
            "video_compose": "final_video.mp4",
            "metadata_generate": "metadata.json",
        }
        for stage, artifact in artifact_stages.items():
            sub = tmp_path / stage
            sub.mkdir()
            save_checkpoint(str(sub), stage)
            # Without artifact: False
            assert stage_complete(str(sub), stage) is False
            # With non-empty artifact: True
            (sub / artifact).write_bytes(b"fake content")
            assert stage_complete(str(sub), stage) is True

    def test_stages_without_artifact_in_list(self, tmp_path):
        no_artifact_stages = ["deps_check", "subtitles_render", "output_finalize"]
        for stage in no_artifact_stages:
            sub = tmp_path / stage
            sub.mkdir()
            save_checkpoint(str(sub), stage)
            assert stage_complete(str(sub), stage) is True


class TestClearCheckpoint:
    def test_removes_checkpoint_file(self, tmp_path):
        save_checkpoint(str(tmp_path), "deps_check")
        assert (tmp_path / ".checkpoint").exists()
        clear_checkpoint(str(tmp_path))
        assert not (tmp_path / ".checkpoint").exists()

    def test_does_nothing_when_no_file(self, tmp_path):
        clear_checkpoint(str(tmp_path))


class TestInitCheckpoint:
    def test_creates_checkpoint_with_run_id(self, tmp_path):
        config = PyReelConfig()
        init_checkpoint(str(tmp_path), "run_test_id", config)
        data = load_checkpoint(str(tmp_path))
        assert data["run_id"] == "run_test_id"
        assert data["completed_stages"] == []
        assert data["failed_stage"] is None
        assert "config_hash" in data
