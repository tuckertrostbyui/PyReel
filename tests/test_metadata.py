import json
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from pyreel.config import PyReelConfig, StoryMode
from pyreel.metadata import generate_metadata, _heuristic_metadata


class TestHeuristicMetadata:
    def test_title_from_first_sentence(self):
        story = "I went to the store today. It was a great experience. Nothing more."
        meta = _heuristic_metadata(story)
        assert meta["title"] == "I went to the store today"

    def test_title_truncated_to_80_chars_with_ellipsis(self):
        long_sentence = "A" * 100
        story = long_sentence + ". Second sentence."
        meta = _heuristic_metadata(story)
        assert meta["title"].endswith("...")
        assert len(meta["title"]) == 83  # 80 chars + "..."

    def test_description_contains_first_two_sentences(self):
        story = "First sentence. Second sentence. Third sentence."
        meta = _heuristic_metadata(story)
        assert "First sentence" in meta["description"]
        assert "Second sentence" in meta["description"]

    def test_hashtags_non_empty(self):
        meta = _heuristic_metadata("Some story text here.")
        assert isinstance(meta["hashtags"], list)
        assert len(meta["hashtags"]) > 0

    def test_hashtags_contain_expected_items(self):
        meta = _heuristic_metadata("Some story text here.")
        hashtags = meta["hashtags"]
        assert "reddit" in hashtags
        assert "story" in hashtags
        assert "tiktok" in hashtags

    def test_platforms_always_correct(self):
        meta = _heuristic_metadata("Some story.")
        assert set(meta["platforms"]) == {"tiktok", "reels", "shorts"}

    def test_no_hash_symbols_in_hashtags(self):
        meta = _heuristic_metadata("Some story.")
        for tag in meta["hashtags"]:
            assert not tag.startswith("#"), f"Hashtag should not have # prefix: {tag}"


class TestGenerateMetadata:
    def setup_method(self):
        self.config = PyReelConfig()
        self.story = "I had the weirdest day. My neighbor knocked on my door at 3am."

    def test_heuristic_fallback_structure(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        result = generate_metadata(
            story=self.story,
            title="Test Title",
            run_id="run_test_001",
            config=self.config,
            output_path=output_path,
        )
        assert "title" in result
        assert "description" in result
        assert "hashtags" in result
        assert "platforms" in result
        assert "generated_at" in result
        assert "story_mode" in result
        assert "source_url" in result
        assert "run_id" in result

    def test_generated_at_is_valid_iso8601(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        result = generate_metadata(
            story=self.story,
            title="Test Title",
            run_id="run_test_001",
            config=self.config,
            output_path=output_path,
        )
        ts = result["generated_at"]
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None

    def test_run_id_in_output(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        result = generate_metadata(
            story=self.story,
            title="Test Title",
            run_id="run_abc_123",
            config=self.config,
            output_path=output_path,
        )
        assert result["run_id"] == "run_abc_123"

    def test_story_mode_in_output(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        result = generate_metadata(
            story=self.story,
            title="Test Title",
            run_id="run_test",
            config=self.config,
            output_path=output_path,
        )
        assert result["story_mode"] == "fetch"

    def test_platforms_always_contains_all_three(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        result = generate_metadata(
            story=self.story,
            title="Test Title",
            run_id="run_test",
            config=self.config,
            output_path=output_path,
        )
        assert "tiktok" in result["platforms"]
        assert "reels" in result["platforms"]
        assert "shorts" in result["platforms"]

    def test_json_file_written(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        generate_metadata(
            story=self.story,
            title="Test Title",
            run_id="run_test",
            config=self.config,
            output_path=output_path,
        )
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        with open(output_path) as f:
            data = json.load(f)
        assert "title" in data

    def test_llm_path_called_when_provider_set(self, tmp_path):
        config = PyReelConfig(llm_provider="openai/gpt-4o", llm_api_key="sk-test")
        output_path = str(tmp_path / "metadata.json")

        llm_result = {
            "title": "LLM Title",
            "description": "LLM description here.",
            "hashtags": ["test", "llm"],
            "platforms": ["tiktok", "reels", "shorts"],
        }

        with patch("pyreel.llm.generate_metadata", return_value=llm_result):
            result = generate_metadata(
                story=self.story,
                title="Test",
                run_id="run_test",
                config=config,
                output_path=output_path,
            )

        assert result["title"] == "LLM Title"
        assert "generated_at" in result

    def test_source_url_stored(self, tmp_path):
        output_path = str(tmp_path / "metadata.json")
        result = generate_metadata(
            story=self.story,
            title="Test",
            run_id="run_test",
            config=self.config,
            source_url="https://reddit.com/r/test/abc",
            output_path=output_path,
        )
        assert result["source_url"] == "https://reddit.com/r/test/abc"
