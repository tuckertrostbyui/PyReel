import json
import os

import pytest

import pyreel
from pyreel.history import PostHistory


class TestPostHistoryInit:
    def test_fresh_path_starts_empty(self, tmp_path):
        h = PostHistory(str(tmp_path / "history.json"))
        assert h.used_ids == set()

    def test_existing_file_loaded(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps({"entries": [
            {"post_id": "abc", "title": "T", "url": "U", "used_at": "2026-01-01", "run_id": "r1"}
        ]}))
        h = PostHistory(str(path))
        assert h.used_ids == {"abc"}

    def test_corrupt_file_resets_to_empty(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text("not valid json{{")
        h = PostHistory(str(path))
        assert h.used_ids == set()


class TestPostHistoryContains:
    def test_unknown_id_returns_false(self, tmp_path):
        h = PostHistory(str(tmp_path / "history.json"))
        assert not h.contains("xyz")

    def test_known_id_returns_true(self, tmp_path):
        h = PostHistory(str(tmp_path / "history.json"))
        h.record("abc", "Title", "http://url", "run1")
        assert h.contains("abc")


class TestPostHistoryRecord:
    def test_creates_file_on_first_write(self, tmp_path):
        path = tmp_path / "history.json"
        h = PostHistory(str(path))
        h.record("abc", "Title", "http://url", "run1")
        assert path.exists()

    def test_file_has_correct_schema(self, tmp_path):
        path = tmp_path / "history.json"
        h = PostHistory(str(path))
        h.record("abc", "My Title", "http://reddit.com/abc", "run_123")
        data = json.loads(path.read_text())
        assert "entries" in data
        entry = data["entries"][0]
        assert entry["post_id"] == "abc"
        assert entry["title"] == "My Title"
        assert entry["url"] == "http://reddit.com/abc"
        assert entry["run_id"] == "run_123"
        assert "used_at" in entry

    def test_used_ids_updated_immediately(self, tmp_path):
        h = PostHistory(str(tmp_path / "history.json"))
        h.record("abc", "T", "U", "r")
        assert "abc" in h.used_ids

    def test_idempotent_same_id_twice(self, tmp_path):
        path = tmp_path / "history.json"
        h = PostHistory(str(path))
        h.record("abc", "T", "U", "r1")
        h.record("abc", "T", "U", "r2")
        data = json.loads(path.read_text())
        assert len(data["entries"]) == 1

    def test_multiple_ids_appended(self, tmp_path):
        path = tmp_path / "history.json"
        h = PostHistory(str(path))
        h.record("abc", "T1", "U1", "r1")
        h.record("def", "T2", "U2", "r2")
        data = json.loads(path.read_text())
        assert len(data["entries"]) == 2

    def test_auto_creates_parent_directories(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "history.json"
        h = PostHistory(str(path))
        h.record("abc", "T", "U", "r")
        assert path.exists()


class TestPostHistoryPersistence:
    def test_recorded_id_visible_in_new_instance(self, tmp_path):
        path = str(tmp_path / "history.json")
        PostHistory(path).record("abc", "T", "U", "r")
        h2 = PostHistory(path)
        assert h2.contains("abc")


class TestPostHistoryClear:
    def test_clear_empties_used_ids(self, tmp_path):
        path = str(tmp_path / "history.json")
        h = PostHistory(path)
        h.record("abc", "T", "U", "r")
        h.clear()
        assert h.used_ids == set()
        assert not h.contains("abc")

    def test_clear_updates_file(self, tmp_path):
        path = tmp_path / "history.json"
        h = PostHistory(str(path))
        h.record("abc", "T", "U", "r")
        h.clear()
        data = json.loads(path.read_text())
        assert data["entries"] == []

    def test_clear_on_fresh_instance_does_not_crash(self, tmp_path):
        path = str(tmp_path / "history.json")
        PostHistory(path).clear()


class TestLoadHistoryHelper:
    def test_returns_post_history_instance(self, tmp_path):
        h = pyreel.load_history(str(tmp_path / "history.json"))
        assert isinstance(h, PostHistory)

    def test_nonexistent_path_returns_empty_history(self, tmp_path):
        h = pyreel.load_history(str(tmp_path / "does_not_exist.json"))
        assert h.used_ids == set()


class TestClearHistoryHelper:
    def test_clears_existing_file(self, tmp_path):
        path = str(tmp_path / "history.json")
        PostHistory(path).record("abc", "T", "U", "r")
        pyreel.clear_history(path)
        h = PostHistory(path)
        assert h.used_ids == set()
